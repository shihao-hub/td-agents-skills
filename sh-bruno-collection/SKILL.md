---
name: sh-bruno-collection
description: 为 HTTP 接口生成 Bruno API 测试脚本（OpenCollection YAML / .bru 格式）。当用户要求创建 bruno 脚本、bruno collection、bruno 请求文件、把 FastAPI/后端接口做成 bruno 测试、给接口写调试脚本、维护 bruno 环境变量或文件夹变量，或者说"帮我写个 bruno 脚本测一下这些接口"、"把这个路由文件转成 bruno"、"接口调通了没，做个 bruno 集合"时使用此技能——即使用户没有明确说出 "bruno"，只要是想为一批接口生成可执行的测试请求集合，也应使用。
---

# sh-bruno-collection — 生成 Bruno 接口测试脚本

把"给一批接口做 bruno 测试脚本"变成一次可靠的执行：确定接口来源 → 提取接口契约 → 用户确认 → 探测 collection 现状 → 生成脚本 → 语法校验。不绑定具体后端框架（FastAPI / Flask / Spring / Nest 均可），接口契约从代码或文档中提取。

完整 YAML 格式规范（请求文件 schema、folder vars、脚本 API、动态变量）见 `references/bruno-yaml-format.md`，**生成文件前必须先读它**——本文件只讲流程和项目约定，格式细节都在 reference 里。

## 铁律（每条都来自真实踩坑）

1. **URL 前缀必须追完整挂载链**。路由文件里的 `@router.post("/send")` 不是完整路径：要向上追 `include_router(router, prefix="/v1/mail")`，再追 `app.mount("/openapi", ...)`，拼出 `/openapi/v1/mail/send`。不要相信路由文件 docstring 里写的路径——以代码挂载链为准（docstring 可能过时）。REST 客户端里 URL 错了，所有请求都会 404。
2. **认证方式从代码确认，不要臆测**。看路由依赖（如 `Depends(get_tenant)`、`Header(alias="X-API-Key")`）或认证中间件，确认 Header 名和格式（`X-API-Key: xxx`、`Authorization: Bearer xxx`、`apikey` query 参数）。认证错则全部 401。
3. **脚本要提取的响应字段名必须下钻确认**。路由 docstring 说返回 `email_send_id`，实际 service 层返回 dict 的 key 可能是 `id`。写 `after-response` 提取脚本前，grep 到 service/serializer 层的 `return {...}` 逐字段核对。
4. **遵循目标 collection 的现有格式**。目标目录先 `ls`：有 `opencollection.yml` + `.yml` 请求文件 → 用 OpenCollection YAML 格式；有 `bruno.json` + `.bru` 文件 → 用 .bru 格式（bruno 3.x 两者兼容，但同一 collection 内保持一致）。环境文件同理（`environments/local.yml` vs `environments/local.bru`）。
5. **敏感 token 不落生产值**。API key 优先让用户提供；从数据库帮用户查时，跳过生产集成 key（如 `cv_live_navos_*` 这类外部集成凭证），选测试用途的 key，并在注释里注明来源。用户明确给了 key 就直接用。
6. **生成后必须做 YAML 语法校验**：`for f in *.yml; do npx -y js-yaml "$f" > /dev/null 2>&1 && echo "OK $f" || echo "FAIL $f"; done`。缩进错误是 yml 最常见的翻车点。注意该校验**只覆盖 YAML 语法、不覆盖 Bruno schema**——字段类型写错（如 docs 嵌套成对象）语法上仍 OK，Bruno 加载时才报 `request.xxx must be a ... type`，此时对照 `references/bruno-yaml-format.md` 修字段结构。Windows PowerShell 下中文文件名在控制台显示乱码不影响实际文件（用 glob 工具取真实文件名）；验证解析结果时不要经 PowerShell 管道转 JSON（会坏 UTF-8），用 node 子进程按 buffer 读取。
7. **用户已明确给出的信息不要重复问**（目录、环境名、base_url、token 等在指令里说了就直接用）；信息缺口才需要确认。
8. **`docs` 必须是纯字符串块，multipart 不设 Content-Type**。`docs: |-` 后直接写 Markdown；写成 `docs:\n  content: ...` 对象时 js-yaml 校验照样通过，Bruno 加载才报 `request.docs must be a \`string\` type`。同理 multipart/form-data 请求不要手动写 Content-Type header（Bruno 自动携带 boundary）。字段结构拿不准时查 bruno-converters 源码（usebruno/bruno 仓库 `packages/bruno-converters/src/opencollection/`），它是 OpenCollection YAML ↔ Bruno 内部模型互转的事实来源，比官方文档 samples 更全。

## 工作流

### Step 1: 确定接口来源

三种情况，按用户说法判断：

- **用户给了接口文件路径**（如 `backend/src/openapi/.../mail.py`）：直接读。
- **用户说"你自己查"或只说了接口域名/功能**：在代码库中搜路由注册点——grep `include_router`、`APIRouter(`、`app.mount`、`@router.(get|post|put|delete)`，从功能关键词定位路由文件，并按铁律 1 追出完整前缀。
- **用户口述或给了文档/OpenAPI spec**：按口述整理，缺少的字段（认证方式、响应结构）能从代码补的就从代码补，补不了的在 Step 3 一并确认。

### Step 2: 提取接口契约（每个接口过一遍清单）

| 项 | 从哪确认 | 注意 |
|---|---|---|
| 完整 URL | 挂载链 mount → include_router → 装饰器路径 | 铁律 1 |
| HTTP 方法 | 路由装饰器 | POST + JSON Body 的 RPC 风格接口，参数都在 body 内，没有 query 参数 |
| 认证 | 依赖注入 / 中间件 / Header alias | 铁律 2 |
| 请求 body 模型 | Pydantic / DTO / schema 定义 | 记录必填/可选/默认值/枚举，body 示例要能过校验 |
| 响应包裹结构 | 统一响应模型（如 `{success, data, error, meta}`） | 决定 tests 断言写法 |
| 脚本要提取的字段 | service 层 `return {...}` | 铁律 3 |
| 错误码 | 异常处理器 / 文档 | 写进请求的 docs 说明 |

同时识别**请求链依赖**：哪些接口产出资源 ID（发送 → thread_id/batch_id/attachment_id），哪些接口消费它——这决定文件编号和提取脚本。

### Step 3: 向用户确认（信息缺口才问）

需要确认的内容（用户指令已给的跳过）：

1. **接口清单摘要**：路径 + 方法 + 用途一句话，让用户确认没有理解偏（自己查出来的接口尤其要确认）。
2. **目标 collection 目录**：新建还是已有文件夹（已有则遵循现有格式，铁律 4）。
3. **环境名和 base_url**：如 local → `http://localhost:8000`。
4. **认证 token 值**：用户提供，或征得同意后从测试库代查（铁律 5）。
5. **body 默认参数值**：域名、收件人之类的业务参数，能从库/配置查到可用值就预填，查不到用明显占位符（`replace-me@example.com`）并在总结里提醒用户手改。

确认方式：一次性列出全部缺口让用户批量回复，不要挤牙膏式逐个问。

### Step 4: 探测 collection 现状

- 根目录有没有 `opencollection.yml` / `bruno.json`（没有且用户指定的是子文件夹，说明 collection 在上层，去上层找）。
- 目标文件夹是否已有 `folder.yml`（有则只增改 `request.variables`，不动 `info`）。
- `environments/` 下已有环境文件：base_url 已存在且值正确就直接复用，不要重复创建。
- 现有请求文件的命名风格（kebab-case、数字前缀等），新文件保持一致。

### Step 5: 生成文件

变量分层（核心约定）：

| 层 | 放哪 | 放什么 |
|---|---|---|
| 环境 | `environments/<name>.yml` | `base_url`，以及随环境切换的值 |
| 文件夹 | `folder.yml` → `request.variables` | token / api_key、公共业务参数（域名、默认收件人等） |
| 运行时 | `after-response` 脚本 `bru.setVar()` | 请求链动态 ID（thread_id、batch_id……），后续请求 body 里 `{{var}}` 引用 |

每个请求文件统一包含：

- `info`：中文名（或与现有一致）、`type: http`、`seq`（从 1 递增，控制 UI 排序）；文件名用数字前缀表达调用链顺序（`01-domains.yml`、`02-send.yml`）。
- `http.headers`：认证头引用 `{{api_key}}`（或 folder auth 配置后 `auth: inherit`）+ `Content-Type: application/json`（multipart 请求**不加** Content-Type，见下）。
- `http.body`：JSON 请求用 `type: json` + `data` 字符串块；**multipart 文件上传**用 `type: multipart-form` + `data` 数组，文件项 `type: file`、`value` 填本地文件路径（如 `./hello.txt`，相对 collection 根或绝对路径），并在 description/docs 里提醒用户首次在 Bruno UI 中重选文件——路径在 YAML 里只是占位，Bruno 需要在 UI 中完成文件选择。
- 幂等键 / 需要每次不同的值：用动态变量 `{{$randomUUID}}`，避免重试触发业务幂等冲突。
- `runtime.scripts`：产出资源 ID 的请求加 `after-response` 提取脚本（先判断 `res.body.success` 之类的成功标志再 setVar）；统一加 `tests` 断言（status 200 + 业务 success 字段）。
- `docs`：纯字符串块（`docs: |-` 后直接写 Markdown），**禁止** `content:` 嵌套对象；内容含接口说明、参数取值说明、错误码、与其他请求的链路依赖。
- `settings`：与 collection 现有请求保持一致（通常 `encodeUrl: false`）。

具体字段写法、示例模板见 `references/bruno-yaml-format.md`。

### Step 6: 校验与总结

1. 跑铁律 6 的 YAML 校验，FAIL 的修复到全 OK。
2. 向用户口头总结（不创建文档文件）：生成的文件清单、变量分层、请求链提取关系、**需要用户手改的占位符**（如收件人邮箱）、验证建议。
