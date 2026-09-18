# 测试迁移

抽取会让原有测试**编译不出预期字符串而失败**，这是必然的，不是回归。断言对象要从
「编译后的 SQL」换成「文本 SQL + params 字典」。

## 1. 断言对象的变化

抽取前测试断言编译产物，字符串里带表名和字面量：

```python
sql = _compiled(session, call_index=0)
assert "email_batches.email_source = 'openapi_mail'" in sql
assert "email_batches.owner_id = 'user-1'" in sql
assert "email_threads.owner_id = 'user-1'" in sql
```

抽取后 SQL 里只有占位符，值在 params 里，所以拆成两半断言：

```python
rows_sql, params = _text_sql(session, call_index=0)
assert "b.email_source = :source AND b.owner_id = :owner_id" in rows_sql
assert "s.email_source = :source AND s.owner_id = :owner_id" in rows_sql
assert "t.email_source = :source AND t.owner_id = :owner_id" in rows_sql
assert params["source"] == "openapi_mail"
assert params["owner_id"] == "user-1"
```

这样反而更强：断言的是**三个别名各自都带了归属条件**，漏掉任何一个表都会失败。
抽取前的写法只能确认「某处出现过这个条件」。

## 2. session mock 要按调用次序给结果

rows / count 是两次 `execute`，不能再用单一 `return_value`：

```python
def _group_rows_session() -> tuple[MailWorkspaceRepository, AsyncMock]:
    """list_group_rows 执行两条文本 SQL：第 0 次取当前页，第 1 次取总数。"""
    repo, session = _make_repo()
    rows_result = MagicMock()
    rows_result.all.return_value = []
    count_result = MagicMock()
    count_result.scalar.return_value = 0
    session.execute.side_effect = [rows_result, count_result]
    return repo, session


def _text_sql(session: AsyncMock, call_index: int = 0) -> tuple[str, dict]:
    call = session.execute.call_args_list[call_index]
    return str(call.args[0]), call.args[1]
```

⚠️ 如果原来的 count 走 `session.scalar()`，抽取后改成 `session.execute(...).scalar()`，
必须同步改 mock —— 否则 `session.scalar.return_value = 0` 静默失效，`total` 变成 MagicMock，
断言 `result.total == 0` 会以令人困惑的方式失败。

## 3. 用户输入不进 SQL 文本（最该写的一条）

这是抽取方案的安全底线，必须有测试守住：

```python
@pytest.mark.asyncio
async def test_list_group_rows_binds_domain_and_query_as_params() -> None:
    """用户输入必须走参数绑定，不得拼进 SQL 文本。"""
    repo, session = _group_rows_session()

    await repo.list_group_rows(OPENAPI_CTX, "Mail.Example.COM", "hel%lo", 2, 20)

    rows_sql, params = _text_sql(session, call_index=0)
    assert "mail.example.com" not in rows_sql
    assert "hel" not in rows_sql
    assert params["domain"] == "mail.example.com"
    assert params["domain_suffix"] == "%@mail.example.com"
    assert params["query_pattern"] == "%hel\\%lo%"
    assert params["skip"] == 20
    assert params["page_size"] == 20
```

同时覆盖了四件事：值不在文本里、大小写归一化、LIKE 通配符已转义、分页偏移算对。

⚠️ 选断言用的输入值时要选**在模板里不可能自然出现的**。用 `"he"` 之类的短串做
`not in` 断言是无效断言——它会碰巧出现在 `the` / `other` 里，测试永远通过。宁可用
`"zzunlikely"` 这种，或者像上面一样对 params 做精确等值断言。

## 4. Admin / 租户两条路径都要覆盖

`owner_id is None` 走的是完全不同的 SQL 分支，必须单独一条用例：

```python
@pytest.mark.asyncio
async def test_list_group_rows_admin_requires_null_owner() -> None:
    repo, session = _group_rows_session()

    await repo.list_group_rows(ADMIN_CTX, None, None, 1, 20)

    rows_sql, params = _text_sql(session, call_index=0)
    assert "b.email_source = :source AND b.owner_id IS NULL" in rows_sql
    assert "s.email_source = :source AND s.owner_id IS NULL" in rows_sql
    assert "t.email_source = :source AND t.owner_id IS NULL" in rows_sql
    assert params["source"] == "admin_light_mail"
    assert "owner_id" not in params
```

`assert "owner_id" not in params` 很关键：占位符没出现时参数也不该出现，
这守住了「占位符 ⇔ 参数」的不变量。反向的用例（`:owner_id` 出现时 params 必须有键）
由上一节的租户用例覆盖。

## 5. 行分类逻辑要独立覆盖

builder 之外，repo 还剩「把 UNION 结果分成 batch_ids / single_in_page」的逻辑。
用 `SimpleNamespace` 造行时，字段名必须和 SQL 投影的列名一致：

```python
    rows_result.all.return_value = [
        SimpleNamespace(group_type="batch", group_id=str(batch_id)),
        SimpleNamespace(group_type="single", group_id="single"),
    ]
```

⚠️ 只造被测代码实际访问的字段。造多了没坏处，造少了会得到
`AttributeError: 'types.SimpleNamespace' object has no attribute 'xxx'`，
而这个报错看起来像生产代码 bug，实际是 stub 不全。

## 6. 参数覆盖检查（可选但推荐）

想机械地保证「凡是插了占位符就有参数」，可以直接问 SQLAlchemy：

```python
from sqlalchemy import text

rows_sql, count_sql, params = build_group_rows_query(...)
for sql in (rows_sql, count_sql):
    text(sql).bindparams()  # 解析
    required = set(text(sql)._bindparams)
    assert required <= set(params), f"缺少参数: {required - set(params)}"
```

params 多出来的键（count SQL 用不到 `skip` / `page_size`）是允许的，
所以断言方向是 `required <= provided`，不是相等。

把这个检查套在参数化用例上，覆盖 domain/query/owner 的各种组合（有/无 × 有/无 × 租户/Admin），
一次就能扫掉「某个分支忘了传参数」这类错误。

## 7. UNION 列契约断言

文本 SQL 没有编译器帮你对齐 UNION 两侧的列。加一条断言把投影列表钉住：

```python
PROJECTION = (
    "SELECT group_id, group_type, domain, subject, body_text, from_address,\n"
    "           status, total_count, created_at, last_message_at, thread_count"
)
assert GROUP_ROWS_CTE_TEMPLATE.count(PROJECTION) == 2
```

⚠️ 缩进是断言的一部分。CTE 内部的续行缩进（11 空格）和外层 `GROUP_ROWS_PAGE_SQL`
的续行缩进（7 空格）不同，所以同一个列清单在 CTE 模板里出现 2 次、在尾部 SQL 里 1 次。
写这条断言时先数清楚缩进，否则会得到一个「数字对不上」的假失败——我第一次就数错了。

更稳的写法是把缩进归一后再比：

```python
def _normalize(sql: str) -> str:
    return " ".join(sql.split())

assert _normalize(GROUP_ROWS_CTE_TEMPLATE).count(_normalize(PROJECTION)) == 2
```

## 8. 与 Core 侧同口径的断言

如果同一个归属语义在 Core 和文本 SQL 两侧都存在（收敛不彻底的过渡态），
加一条测试断言两者产出一致，防止将来只改一侧：

```python
core_sql = str(
    select(EmailBatch).where(*repo._ownership_conditions(EmailBatch, OPENAPI_CTX))
    .compile(compile_kwargs={"literal_binds": True})
)
assert "email_source" in core_sql and "owner_id" in core_sql
assert "owner_id = :owner_id" in build_space_clause("b", OPENAPI_CTX.owner_id)
```

两侧字符串形态不同，无法直接比较，所以断言的是「都约束了这两列」。
真正的一致性保障是「只有一份实现」，测试只是提醒。

## 9. 本项目的运行约定

项目规则**禁止 AI 直接运行 backend / frontend 测试**。改完后向用户说明建议命令，
由用户自行运行：

```bash
# cwd: backend/
uv run pytest tests/unit/infrastructure/orm/repo/outreach/test_mail_workspace_repository.py -q
uv run ruff check src/infrastructure/orm/query/ src/infrastructure/orm/repo/outreach/
uv run ruff format --check src/infrastructure/orm/query/
```

需要自行验证 builder 输出时，写独立的 `uv run python` 脚本打印 SQL 与 params
（不走 pytest），验证完删掉临时脚本。这条路不受上面的禁令限制，且比读代码可靠。

按 `backend-infra-reuse.md` 的规定，`infrastructure/` 下新增 public 符号
（`build_group_rows_query` / `build_space_clause` / `build_space_params` / `escape_like_pattern`）
需要同步登记到 `docs/backend/infra/`。
