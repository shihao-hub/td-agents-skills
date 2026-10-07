# 完整案例：mail_workspace 组列表抽取

真实改动，需要参照形态时读这里。

| | 抽取前 | 抽取后 |
|---|---|---|
| repo 方法体 | 140 行 Core 表达式 | 16 行（构建 + 执行 + 分类） |
| SQL 可见性 | 要在脑内编译才知道查了什么 | 文本模板可直接复制到客户端 |
| 归属条件实现份数 | 3 份 | 1 份 `build_space_clause` |
| 测试断言对象 | 编译后的 SQL 字符串 | 文本 SQL + params 字典 |

## 抽取前

方法内部依次构造：`batch_agg` 子查询（下推聚合）→ `batch_filters` 条件列表 → `batch_cols`
投影 → `single_filters` → `single_cols` 投影 → `union_all(...)` → 外层 `select().order_by().offset().limit()`
＋一条独立的 `select(func.count())`。

三个具体的痛点（都是「读代码读不出 SQL」的直接来源）：

```python
# 1. outer join 侧的归属条件内联展开，和 _ownership_conditions 是同一语义的第二份实现
or_(
    EmailSend.email_source.is_(None),
    and_(
        EmailSend.email_source == context.source,
        (
            EmailSend.owner_id == context.owner_id
            if context.owner_id is not None
            else EmailSend.owner_id.is_(None)
        ),
    ),
),

# 2. 投影列靠 label 对齐，UNION 两侧列序一致性全靠人眼
cast(EmailBatch.id, Text).label("group_id"),
literal("batch").label("group_type"),
func.coalesce(
    EmailBatch.extra_data["domain"].as_string(), EmailBatch.from_address
).label("domain"),

# 3. 条件是否生效散落在多个 if 后的 .where() 追加里，
#    读到最后不确定最终 WHERE 到底有几个条件
if batch_filters:
    batch_cols = batch_cols.where(and_(*batch_filters))
```

注意 `EmailBatch.extra_data["domain"]` —— ORM 属性叫 `extra_data`，数据库列叫 `metadata`
（`Column("metadata", JSONB)`）。这类映射只有编译输出会告诉你，所以第 1 步必须先打印编译 SQL。

## 抽取后：repo 只负责执行

```python
    """组分页：批次组（email_batches）+ 单笔组（batch_id IS NULL 的线程聚合）。

    单笔组作为固定一行参与 UNION ALL，与批次组统一按 last_message_at DESC 分页。
    SQL 模板见 ``orm/query/mail_workspace_query.GROUP_ROWS_CTE_TEMPLATE``。
    """
    rows_sql, count_sql, params = build_group_rows_query(
        source=context.source,
        owner_id=context.owner_id,
        domain=domain,
        query=query,
        page=page,
        page_size=page_size,
    )

    page_rows = (await self.session.execute(sa_text(rows_sql), params)).all()
    total = (await self.session.execute(sa_text(count_sql), params)).scalar() or 0
    # ↓ 以下是原有的行分类逻辑，未改动
```

docstring 里指向模板常量名，让读者知道 SQL 在哪。返回类型 `GroupPageResult` 完全不变，
service 层零改动——这是抽取能安全落地的前提。

`from sqlalchemy import union_all` 这个方法内的局部 import 一起删掉了；`Text` / `cast` /
`literal` / `null` 从模块顶部 import 移除（本次修改导致其变成未引用，属于必须清理的范围）。

## 抽取后：query 模块

### 模块 docstring 说清三件事

```python
"""邮件工作空间 SQL Query Builder。

所有 SQL 以文本形式集中在本模块，只做字符串构建与参数绑定，不执行查询、不持有
会话。用户输入（domain / query）全部走 `:param` 绑定，模板中插值的片段仅为固定
的归属条件与过滤开关。

模板可直接复制到数据库复现，只需自行提供 `:source` / `:owner_id` 等绑定值。
"""
```

「不执行、不持有会话」是这一层的边界；「用户输入全走绑定」是安全承诺；「可直接复制复现」
是这次抽取的验收标准。三句都要写，后来改这个文件的人才知道不该往里加什么。

### 模板：注释 + 对齐

```python
# 说明：
# - batch_agg     按批次下推聚合 last_message_at / thread_count
# - batch_groups  批次组行
# - single_group  batch_id IS NULL 的线程聚合为固定一行
# - group_rows    两个分支按列名对齐后 UNION ALL
GROUP_ROWS_CTE_TEMPLATE = """
WITH batch_agg AS (
    SELECT b.id                                       AS batch_id,
           MAX(COALESCE(s.sent_at, s.created_at))     AS last_message_at,
           COUNT(DISTINCT s.metadata ->> 'thread_id') AS thread_count
    FROM email_batches b
    LEFT JOIN email_sends s ON s.batch_id = b.id
    WHERE {batch_space_clause}
      -- 关联发送记录须同属一个邮件空间；email_source IS NULL 为历史数据兼容
      AND (s.email_source IS NULL OR ({send_space_clause}))
    GROUP BY b.id
),
```

模板头部的 CTE 清单是给读者的导航；`AS` 对齐让列名成一列可扫。
`email_source IS NULL` 那行注释解释的是**为什么**（历史数据兼容），而不是重述 SQL 在做什么。

CTE 与两个尾部 SQL 分开成三个常量，rows / count 拼接同一段 CTE：

```python
return cte_sql + GROUP_ROWS_PAGE_SQL, cte_sql + GROUP_ROWS_COUNT_SQL, params
```

### builder：条件收集 + 一次 format

```python
    batch_filters: list[str] = []
    single_filters: list[str] = []

    if normalized_domain:
        params["domain"] = normalized_domain
        params["domain_suffix"] = f"%@{normalized_domain}"
        batch_filters.append(
            "(b.from_address ILIKE :domain_suffix OR b.metadata ->> 'domain' = :domain)"
        )
        single_filters.append("t.domain = :domain")

    cte_sql = GROUP_ROWS_CTE_TEMPLATE.format(
        batch_space_clause=build_space_clause("b", owner_id),
        send_space_clause=build_space_clause("s", owner_id),
        thread_space_clause=build_space_clause("t", owner_id),
        batch_filters=_and_fragment(batch_filters),
        single_filters=_and_fragment(single_filters),
        single_domain_expr="CAST(:domain AS text)"
        if normalized_domain
        else "NULL::text",
    )
```

「设参数」和「加条件片段」在同一个 `if` 里紧挨着写——这是保证「占位符出现 ⇔ 参数已设」
不变量的最简手段。`single_domain_expr` 演示了另一种做法：条件不生效时连占位符都不出现。

## 三处归属实现收敛为一处

抽取前 `email_source = X AND owner_id = Y / IS NULL` 这个语义有三份实现：Core 侧的
`_ownership_conditions`、指标 SQL 侧的 `_owner_clause_sql` + `_base_source_clause`、
outer join 内联的那段 `or_(...)`。

收敛后指标侧退化为委托：

```python
    @staticmethod
    def _base_source_clause(context: MailAccessContext, alias: str = "e") -> str:
        """文本 SQL 的邮件空间归属条件（与 Core 侧 ``_ownership_conditions`` 同口径）。"""
        return build_space_clause(alias, context.owner_id)

    @staticmethod
    def _metrics_source_params(context: MailAccessContext) -> dict[str, Any]:
        return build_space_params(context.source, context.owner_id)
```

Core 侧的 `_ownership_conditions` 保留（其它方法还在用 Core），但 docstring 明确标注
与文本侧同口径，并有测试断言两者产出一致。**安全边界只留一份实现**比减少行数重要得多。

## 顺带发现但没改的行为

抽取过程会把隐藏在表达式里的行为暴露出来。这两个都属于「改了就变 API 响应」，
所以只在模板里加注释 + 向用户报告，没有自行修正：

- `single_group` 没有 `GROUP BY`，聚合查询恒返回一行 → `total` 永远 ≥ 1，
  搜索无关词时会出现一个空的 "Single Emails" 组。
- `thread_count` 两侧语义不同：批次侧是 `COUNT(DISTINCT s.metadata ->> 'thread_id')`
  （来自 `email_sends`），单笔侧是 `COUNT(*)`（来自 `email_threads`）。

这是抽取的附带价值：Core 表达式里看不出来的行为，写成文本 SQL 后一眼就能发现。
但发现 ≠ 顺手改——按手术刀原则单独报告。
