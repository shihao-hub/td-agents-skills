---
name: sh-sql-query-builder
description: 重构 SOP：把 SQLAlchemy Core 嵌套只读查询抽取为文本 SQL 模板+builder，适用任意 Python 后端项目。点名使用
---

# 复杂 SQL 抽取到 Query Builder 层

## 这个 skill 解决什么问题

Repository 里用 SQLAlchemy Core 表达式拼出来的复杂查询，读代码的人回答不了两个最基本的问题：**这条 SQL 长什么样**、**怎么在数据库上复现它**。

真实病例（`mail_workspace_repository.list_group_rows`，抽取前 140 行）：

```python
batch_agg = (
    select(
        EmailBatch.id.label("batch_id"),
        func.max(func.coalesce(EmailSend.sent_at, EmailSend.created_at)).label("last_message_at"),
        func.count(func.distinct(EmailSend.extra_data["thread_id"].astext)).label("thread_count"),
    )
    .outerjoin(EmailSend, and_(
        EmailSend.batch_id == EmailBatch.id,
        or_(EmailSend.email_source.is_(None),
            and_(EmailSend.email_source == context.source,
                 EmailSend.owner_id.is_(None) if context.owner_id is None
                 else EmailSend.owner_id == context.owner_id)),
    ))
    .group_by(EmailBatch.id).cte("batch_agg")
)
```

要读懂它，得在脑子里跑一遍 SQLAlchemy 的编译器。线上出问题时，没人能把它粘到 psql 里验证。三元表达式嵌在 `and_` 里，鉴权口径这种最该被一眼看清的东西反而最难看清。

抽取后 SQL 是一整块文本，填上 `:source` / `:owner_id` 就能直接跑，repo 只剩执行：

```python
rows_sql, count_sql, params = build_group_rows_query(
    source=context.source, owner_id=context.owner_id,
    domain=domain, query=query, page=page, page_size=page_size,
)
page_rows = (await self.session.execute(sa_text(rows_sql), params)).all()
total = (await self.session.execute(sa_text(count_sql), params)).scalar() or 0
```

**这不是「文本 SQL 比 ORM 好」**。ORM 在单表 CRUD、需要跟着模型演进的地方仍然更优。分界线是可读性何时开始倒挂：当表达式的抽象成本超过它省下的拼接成本，就该换形态。

## 什么时候抽

满足任一即抽（这些阈值是为了让判断不靠感觉）：

- Core 表达式构成的单个查询方法 **超过 60 行**
- 出现 **≥ 2 个 CTE**，或 `union_all` / 窗口函数 / 递归
- 条件里出现 **内联三元表达式**（`X if cond else Y` 塞进 `and_` / `or_`）
- 同一份业务条件（鉴权归属、租户隔离、软删过滤）在文件里 **出现 ≥ 2 次**
- 需要 **rows + count 两条 SQL 共用同一套 CTE**

**不要抽**：单表增删改查、需要返回 ORM 实体并跟踪变更的写操作、`select(Model).where(Model.id == x)` 这类一眼可读的查询。抽了只会多一层跳转。

## 目标形态

```
backend/src/infrastructure/orm/
├── query/{module}_query.py     ← 纯字符串构建，不执行、不持有 session
└── repo/{module}/{x}_repository.py  ← 只负责 execute + 映射结果
```

`orm/query/` 是项目既有范式，不是新发明：`marketing_benchmark_query.py`、`app_gaming_query.py`、`market_insight_query.py` 都在这一层。`backend-orm-mandatory.md` 也把 `orm/query/` 列为复杂只读查询的合法归宿——所以抽取不会踩「禁止裸 SQL」那条规则，反而是把裸 SQL 收拢到它该在的地方。

query 模块的骨架：

```python
"""Mail Workspace Query Builder 层

纯 SQL 字符串构建，不执行查询，不持有数据库连接。

安全约定：用户输入（domain / query）一律走 :param 绑定；
模板里插值的只有固定的归属条件和过滤开关字符串。
"""

GROUP_ROWS_CTE_TEMPLATE = """..."""   # 结构占位符用 {name}
GROUP_ROWS_PAGE_SQL = """..."""       # 复用同一份 CTE
GROUP_ROWS_COUNT_SQL = """..."""

def build_space_clause(alias: str, owner_id: str | None) -> str: ...
def build_group_rows_query(*, ...) -> tuple[str, str, dict[str, Any]]: ...
```

三条约束让这一层保持纯净，也让它可以被单测直接调用而不需要数据库：

- **不 import session / AsyncSession**，不做 `execute`
- builder 返回 `(sql, params)` 或 `(rows_sql, count_sql, params)`，参数字典由 builder 自己攒齐
- 关键字参数（`*,`）传入，避免调用方按位置传错 `domain` / `query` 这类同类型参数

## 抽取流程

### 1. 先把当前 SQL 打印出来

不要凭读代码去手写目标 SQL——编译器的实际输出常和你以为的不一样（JSONB 取值、列别名、隐式 join 顺序）。先拿到基线：

```python
print(stmt.compile(compile_kwargs={"literal_binds": True}))
```

把输出格式化好，这就是你要抄进模板的东西。**ORM 属性名 ≠ 数据库列名**：`extra_data` 在模型里映射的是 `metadata` 列（`name="metadata"`），文本 SQL 必须写 `metadata ->> 'key'`。这类映射只有编译输出会告诉你。

### 2. 拆成 CTE 分段并加注释

把编译输出按 CTE 切段，每段之间空行，列投影按 `AS` 对齐。注释只写「为什么」，别复述 SQL 在做什么：

```sql
WHERE {batch_space_clause}
  -- 关联发送记录须同属一个邮件空间；email_source IS NULL 为历史数据兼容
  AND (s.email_source IS NULL OR ({send_space_clause}))
```

对齐不是洁癖：这块文本存在的意义就是被人复制到数据库客户端里读，读不顺就白抽了。

### 3. 区分两类占位符

这一步决定安全性，写错了就是 SQL 注入。

| 占位符 | 形式 | 放什么 | 谁来填 |
|---|---|---|---|
| 绑定参数 | `:domain` | **一切用户输入**：搜索词、ID、分页偏移、时间范围 | 驱动层，值不进 SQL 文本 |
| 结构插值 | `{batch_filters}` | 代码自己生成的固定片段：归属条件、过滤开关、白名单校验过的列名 | `str.format()` |

判据只有一条：**这个值是否可能来自 HTTP 请求体**。是 → `:param`，没有例外。

### 4. 动态条件用片段列表拼

```python
batch_filters: list[str] = []
if normalized_domain:
    params["domain"] = normalized_domain
    params["domain_suffix"] = f"%@{normalized_domain}"
    batch_filters.append(
        "(b.from_address ILIKE :domain_suffix OR b.metadata ->> 'domain' = :domain)"
    )

def _and_fragment(conditions: list[str]) -> str:
    """拼成可直接追加到 WHERE 之后的片段（无条件时返回空串）。"""
    if not conditions:
        return ""
    return "".join(f"\n      AND {condition}" for condition in conditions)
```

条件字符串是常量，值走参数——这样「有哪些可选过滤」在代码里一眼可数，同时用户数据不碰 SQL 文本。

无条件时返回空串而不是 `AND 1=1`，模板里写 `WHERE {clause}{filters}` 而不是 `WHERE 1=1 {filters}`：占位的真值条件会让复制出来的 SQL 多一行噪音，而且掩盖了「这里本来该有个必要条件」。

### 5. repo 侧退化为执行

repo 方法里只应剩下：调 builder、execute、映射结果。判断逻辑（哪些过滤生效、归属怎么算）全部下沉到 query 模块。**保持返回类型不变**（如 `GroupPageResult`）——文本 SQL 的 `Row` 同样支持属性访问，service 层可以零改动。这是抽取能安全落地的关键：契约不动，改动就锁死在两个文件里。

### 6. 验证

见 `references/03-testing.md`。核心是断言从「编译后的 Core SQL」换成「SQL 文本 + params」，并且必须有一条断言用户输入不出现在 SQL 文本里。

## 重复条件收敛为单一实现

抽取时最容易发现的既有问题：同一份鉴权/归属条件有多份实现。原文件里就有三份——Core 版 `_ownership_conditions`、文本版 `_owner_clause_sql` + `_owner_params`、以及 LEFT JOIN 里手抄的一份。

收敛成一对函数，Core 侧和文本侧共用：

```python
def build_space_clause(alias: str, owner_id: str | None) -> str:
    """邮件空间归属条件：source 恒定绑定，owner 为空表示 Admin 全局视图。"""
    owner_clause = (
        f"{alias}.owner_id IS NULL" if owner_id is None
        else f"{alias}.owner_id = :owner_id"
    )
    return f"{alias}.email_source = :source AND {owner_clause}"

def build_space_params(source: str, owner_id: str | None) -> dict[str, Any]:
    params: dict[str, Any] = {"source": source}
    if owner_id is not None:
        params["owner_id"] = owner_id
    return params
```

安全边界必须只有一份实现，这比减少行数重要得多：多份实现意味着某天只有一份被修好。注意 `owner_id is None` 时不要往 params 里塞 `owner_id` 键——SQL 里没有这个占位符，塞了就是给下一个读代码的人埋误导。

改动既有 `infrastructure/` 方法时，`backend-infra-reuse.md` §3 的测试义务生效：**跑被改动符号自身的测试 + 所有调用方的测试**。特别注意 mock 脆弱性——原来 mock 了 `_owner_clause_sql` 的测试会失效，即使签名没变。

## 收尾

- **登记能力**：`infrastructure/` 下新增 public 符号，必须同步登记到 `docs/backend/infra/README.md`（`backend-infra-reuse.md` §5 的强制要求）。写清能力名、模块、调用方式、复用场景。
- **不要顺手改行为**：抽取的目标是等价替换。发现真实 bug（比如某个 CTE 缺 `GROUP BY` 导致恒返回一行、同名字段两侧口径不一致）就在模板里加注释标注，单独向用户说明并让他决定——这类改动会变接口返回值，不能夹在重构里悄悄改。
- **格式化**：`uv run ruff format` 只会重排函数签名，不会动三引号里的 SQL 模板。跑完确认 SQL 文本没被改。

## 自检

- SQL 文本能否直接粘进数据库客户端，只补 `:param` 的值就跑通？
- 任何可能来自请求体的值，是否都走了 `:param`？（grep 模板里的 f-string 插值，逐个确认来源）
- 归属/租户/软删这类安全条件，实现是否只有一份？
- rows 和 count 是否共用同一份 CTE 模板？（两份会各自演进到不一致）
- service 层是否零改动？（改了说明返回契约被动了，需要单独说明）
- `docs/backend/infra/README.md` 是否登记了新 public 符号？

## 参考文件

- `references/01-text-sql-gotchas.md` — `text()` 占位符解析边界（含实测结果）、LIKE 转义、asyncpg IN 列表、UNION 列契约。**写模板前必读**，这里的坑不看会踩。
- `references/02-worked-example.md` — mail_workspace 完整前后对照：140 行 Core → 16 行执行 + 178 行 query 模块。需要参照真实形态时读。
- `references/03-testing.md` — 测试迁移：断言从编译 SQL 换成文本 SQL + params，参数化覆盖检查，UNION 列契约断言。
