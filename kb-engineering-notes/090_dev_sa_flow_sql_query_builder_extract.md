---
name: kb-sqlalchemy-query-builder-extract
description: SQLAlchemy 复杂 Core 查询抽取为文本 SQL 模板与 Query Builder 层重构流水线：解决 ORM 表达式可读性倒挂、包含 CTE/分页共享 params、动态列白名单与占位符安全校验 SOP。后端复杂 SQL 重构与性能调优时查阅。
---

# 复杂 SQLAlchemy Core 查询抽取为 Query Builder 层重构流水线

> 本条目沉淀自将 Repository 层数十行紧密耦合的 SQLAlchemy Core 复杂表达式重构为“纯文本 SQL 模板 + Query Builder 参数装配函数”的工程范式。

---

## 一、业务痛点与重构动因

### 为什么抽？（可读性倒挂现象）
在 Python 后端（FastAPI / SQLAlchemy）开发中，使用 Core 表达式编写多表聚合、多 CTE（通用表表达式）复杂只读查询时，代码常膨胀至 100~200 行。开发者在排查线上故障时回答不了两个核心问题：
1. **这条 SQL 最终到底长什么样？**
2. **怎么把这段逻辑复制到数据库控制台（psql/DBeaver）里直接重现并 Explain？**

当 Core 表达式的认知与维护成本大幅超过它所提供的抽象保护时，就应当将复杂只读查询重构为**纯文本 SQL 模板 + 独立 Builder 函数**。

### 明确分界线：什么时候该抽？什么时候绝不要抽？

| 建议重构抽取（满足任一即抽） | 绝不要抽取（坚守 ORM） |
|---|---|
| Core 表达式单一查询函数 **> 60 行** | 单表标准 CRUD（增删改查） |
| 出现 **≥ 2 个 CTE**、或包含窗口函数、递归查询 | 涉及 ORM 实体状态跟踪与单元工作（Unit of Work）写操作 |
| 表达式条件内嵌复杂三元运算符（`X if cond else Y` 塞在 `and_` / `or_` 中） | `select(Model).where(Model.id == x)` 这类一眼可辨的简单查询 |
| 同一套业务过滤（租户隔离、权限归属、软删）在多处重复拼接 | 抽了之后只会平白增加一层抽象跳转的简单场景 |
| 需要同时执行当前页 `rows` 与统计总数 `count` 且共用同一组 CTE | |

---

## 二、目标架构与设计形态

重构后的模块骨架为两部分解耦：
1. **纯 SQL 模板文件**（或集中于模块顶部的纯文本常量常量）：业务条件用 `:param` 占位；
2. **Builder 装配函数**：只负责根据业务输入组装参数字典与动态片段，输出 `(rows_sql, count_sql, params)`。

```python
# Repository 调用层变得极度干净、可读：
rows_sql, count_sql, params = build_group_rows_query(
    source=context.source, owner_id=context.owner_id,
    domain=domain, query=query, page=page, page_size=page_size,
)
page_rows = (await self.session.execute(sa_text(rows_sql), params)).all()
total = (await self.session.execute(sa_text(count_sql), params)).scalar() or 0
```

---

## 三、核心技术踩坑与六大安全铁律

### 1. `text()` 占位符解析边界
SQLAlchemy 用正则扫描文本中的 `:name`。实测边界：
- `b.id::text`、`NULL::text`：**完全安全**，双冒号类型转换不会被误判；
- `metadata ->> 'thread_id'`：JSONB 操作符**安全**；
- `tag = 'a:b'`：字面量内紧跟冒号字符**不会**被提取；
- ⚠️ **唯一陷阱**：`tag = ' :b'`（字符串字面量中出现**空格 + 冒号 + 字母**）会被误认为占位符！若字面量含此类模式，必须通过 `:param` 参数化传入。

### 2. rows / count 共享同一个 params 字典
分页查询需跑两条 SQL（取分页行 + 算总数）。count SQL 内即便没有 `:skip` / `:page_size`，也能安全传入同一个字典（多余的 key 会被 SQLAlchemy 自动忽略）；
**反向则严格报错**：SQL 中声明的占位符如果在 params 中缺失，会立即抛出 `InvalidRequestError`。

### 3. 条件不生效时绝对不要留下悬空占位符
若查询条件可选（如 `domain` 为空时不筛选），切勿在 SQL 中硬编码 `WHERE t.domain = :domain` 并传入 `None`（`= NULL` 恒为假导致静默返回空集）；
必须让 SQL 片段与参数同步存在：
```python
if domain:
    conditions.append("t.domain = :domain")
    params["domain"] = domain
```

### 4. LIKE / ILIKE 通配符转义
用户搜索词中的 `%` 与 `_` 必须显式转义，且反斜杠优先转义：
```python
def escape_like_pattern(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

# SQL 模板中显式指定 ESCAPE
# t.subject ILIKE :query_pattern ESCAPE '\'
```

### 5. asyncpg 不支持 `IN :tuple`
无法直接将 Python 元组/列表绑定为单个参数。处理方式：
- **方案 A（展开具名参数）**：动态拼接 `:val_0, :val_1`；
- **方案 B（PostgreSQL 数组）**：`field = ANY(:values)`，直接传 Python list。

### 6. 动态排序列名与方向必须走白名单防御
动态 `ORDER BY` 的列名绝不能参数化，必须经由严格的白名单校验：
```python
VALID_SORT_FIELDS = {"created_at", "updated_at", "total_count"}
if sort_by not in VALID_SORT_FIELDS:
    raise ValueError(f"非法排序字段: {sort_by}")
```

---

## 四、单元测试断言标准

针对 Query Builder，编写轻量级的确定性单测，防止占位符遗漏：

```python
from sqlalchemy import text

def test_builder_params_coverage():
    rows_sql, count_sql, params = build_group_rows_query(...)
    # 断言 SQL 中的全部占位符均在 params 字典中有对应提供
    expected_rows_keys = set(text(rows_sql)._bindparams.keys())
    assert expected_rows_keys.issubset(set(params.keys()))
    
    expected_count_keys = set(text(count_sql)._bindparams.keys())
    assert expected_count_keys.issubset(set(params.keys()))
```
