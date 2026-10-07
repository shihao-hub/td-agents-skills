# 文本 SQL 的坑（写模板前必读）

本文的实测结论都在本项目的 SQLAlchemy 版本上验证过（`text(sql)._bindparams.keys()` 直接观察占位符提取结果）。不要凭印象改这些结论。

## 1. `text()` 的占位符解析边界

SQLAlchemy 用正则扫 `:name`，规则是「冒号后紧跟标识符字符」。实测哪些会被当占位符：

| SQL 片段 | 被提取的占位符 | 说明 |
|---|---|---|
| `b.id::text` | 无 | 双冒号强转安全，`::` 不匹配 |
| `NULL::text` | 无 | 同上 |
| `CAST(:domain AS text)` | `domain` | 正常参数 |
| `a ILIKE :p ESCAPE '\'` | `p` | `ESCAPE '\'` 不干扰解析 |
| `metadata ->> 'thread_id'` | 无 | JSONB 操作符安全 |
| `now() - INTERVAL '1 day'` | 无 | 安全 |
| `tag = 'a:b'` | 无 | 字符串字面量里的冒号后跟字符，**不会**被提取 |
| `tag = ' :b'` | **`b`** | ⚠️ 冒号前有空格时**会**被误提取成占位符 |

最后一行是唯一的真陷阱：**字符串字面量里出现「空格 + 冒号 + 字母」会被误认为占位符**。写模板时如果要在字面量里放冒号（比如生成带前缀的展示文本），避开 ` :x` 形式，或者干脆把整个字面量做成 `:param` 传进去。

`::text` 安全这一点很重要——PostgreSQL 强转在这类查询里到处都是，如果它会被误解析，整套抽取方案就不成立。实测确认安全。

## 2. rows / count 共用一个 params 字典

分页查询要跑两条 SQL：取当前页 + 取总数。count SQL 里没有 `:skip` / `:page_size`，但可以安全地传同一个字典：

```python
# 实测：compiled.construct_params({"owner_id": "u1", "skip": 0, "page_size": 20})
# → {'owner_id': 'u1'}   多余的键被忽略，不报错
```

反向则不行：**缺少占位符对应的键会抛 `InvalidRequestError`**。所以 builder 必须保证「凡是插入了 `:x` 占位符，就往 params 里放 `x`」。这是 builder 内部的不变量，也是测试该覆盖的第一件事（见 `03-testing.md` 的参数覆盖检查）。

实践上就是让两条 SQL 共享一个 `params`：

```python
return cte_sql + GROUP_ROWS_PAGE_SQL, cte_sql + GROUP_ROWS_COUNT_SQL, params
```

## 3. 条件不生效时不要留下占位符

最容易犯的错：模板里无条件写了 `:domain`，但 domain 为空时没往 params 放值 → `InvalidRequestError`。

所以「占位符是否出现」必须和「参数是否设置」同步。做法是让**结构本身**跟着变：

```python
single_domain_expr = "CAST(:domain AS text)" if normalized_domain else "NULL::text"
```

无 domain 过滤时，SQL 里连 `:domain` 都不会出现。这比「无条件放占位符 + 传 None」更好：传 `None` 会让 `t.domain = NULL` 恒为假，静默返回空结果，比报错难查得多。

## 4. LIKE / ILIKE 通配符转义

用户搜索词里的 `%` `_` 会被当通配符。搜 `50%` 会匹配到 `50` 开头的一切。

```python
def escape_like_pattern(value: str) -> str:
    """转义 LIKE / ILIKE 通配符（配合 ``ESCAPE '\\'`` 使用）。"""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
```

反斜杠必须**先**转义，否则会把自己新加的转义符再转一遍。SQL 侧必须显式声明转义符：

```sql
t.subject ILIKE :query_pattern ESCAPE '\'
```

不写 `ESCAPE` 子句，PostgreSQL 默认转义符恰好也是 `\`，但显式写出来才能让复制到客户端的 SQL 行为确定，也提示读者这里的模式是转义过的。

## 5. asyncpg 不支持 `IN :tuple`

不能把列表绑成一个参数。必须展开为多个命名参数（项目里 `marketing_benchmark_query.build_filter_conditions` 就是这么做的）：

```python
placeholders = []
for i, v in enumerate(value):
    p_name = f"{param_name}_{i}"
    placeholders.append(f":{p_name}")
    params[p_name] = v
conditions.append(f"{field} IN ({', '.join(placeholders)})")
```

或者用 PostgreSQL 数组：`field = ANY(:values)`，值传 Python list。后者 SQL 更短、可读性更好，代价是复制到客户端时需要手写数组字面量 `ANY('{a,b}')`。按「哪种更容易复现」来选。

## 6. 列名插值必须过白名单

动态 `ORDER BY` / `GROUP BY` 的列名不能参数化（占位符只能出现在值的位置）。唯一安全做法是白名单校验后插值：

```python
VALID_GROUP_BY_DIMENSIONS: set[str] = {"media_platform", "country_code", ...}

if field not in VALID_FILTER_FIELDS:
    raise ValueError(f"非法筛选字段: '{field}'。合法字段: {sorted(VALID_FILTER_FIELDS)}")
```

抛 `ValueError` 而不是静默忽略：静默忽略会让「筛选没生效」表现为「返回了全量数据」，在权限相关的筛选上这是安全问题。

⚠️ 项目里 `market_insight_query._escape_sql_string`（只做 `'` → `''`）是**遗留写法，不要在新代码里模仿**。它把用户输入直接拼进 SQL 文本，虽然转义了单引号，但比 `:param` 脆弱得多（漏一个调用点就是注入）。新代码统一用绑定参数。

## 7. UNION ALL 的列契约

UNION 两侧必须投影**同名、同序、同类型**的列。文本 SQL 里没有编译器帮你对齐，写错了要么运行时报类型错，要么更糟——列串位，静默返回错误数据。

防御手段是让两侧的投影列表**字面相同**，并用测试断言这一点（见 `03-testing.md`）：

```sql
group_rows AS (
    SELECT group_id, group_type, domain, subject, body_text, from_address,
           status, total_count, created_at, last_message_at, thread_count
    FROM batch_groups
    UNION ALL
    SELECT group_id, group_type, domain, subject, body_text, from_address,
           status, total_count, created_at, last_message_at, thread_count
    FROM single_group
)
```

NULL 列必须带类型标注（`NULL::text`）。不标注时 PostgreSQL 推断为 `text` 往往碰巧能跑，但一旦另一侧是 `uuid` / `timestamptz` 就报错，且报错信息指向 UNION 而非真正的那一列。

## 8. ORM 属性名 ≠ 数据库列名

```python
extra_data = Column("metadata", JSONB)   # 属性 extra_data，列名 metadata
```

Core 表达式里写 `EmailSend.extra_data["thread_id"].astext`，文本 SQL 里必须写 `s.metadata ->> 'thread_id'`。

这类映射（`Column("db_name", ...)`、`__tablename__`、schema 前缀）**只有编译输出能告诉你**。所以抽取流程第 1 步先打印编译结果不是可选项：

```python
print(stmt.compile(compile_kwargs={"literal_binds": True}))
```
