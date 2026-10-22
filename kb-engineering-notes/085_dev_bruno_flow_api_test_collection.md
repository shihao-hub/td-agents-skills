---
name: kb-bruno-api-collection
description: 为后端 HTTP 接口生成 Bruno API 测试集合（OpenCollection YAML/.bru）与请求链流水线：包含路由挂载链提取、认证隔离、断言与语法校验 SOP。接口测试生成与自动化回归时查阅。
id: "085"
domain: dev
scope: bruno
type: flow
slug: api_test_collection
status: verified
created: "2026-09-22"
last_verified: "2026-10-22"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: true
---

# Bruno 接口测试集合生成流水线 (OpenCollection YAML)

> 本条目沉淀自后端 API 测试集合（Bruno）的工程化落地经验。
> 涵盖路由前缀挂载链追查、身份认证与敏感凭据隔离、跨接口请求链变量传递（`after-response`）、以及 OpenCollection YAML 格式严苛校验流水线。

---

## 一、业务场景与需求

在微服务或单体后端（FastAPI / Flask / Spring Boot / NestJS 等）交付与回归测试中，手工编写接口测试脚本极易遗漏参数或写错前缀。本流水线旨在将“给一批接口做 Bruno 测试脚本”变为标准工程闭环：
1. **输入源**：后端路由代码、OpenAPI / Swagger 文档、或开发者口述接口清单；
2. **生成目标**：符合 Bruno 3.0+ 规范的 OpenCollection YAML 脚本文件（一请求一文件，支持目录级环境变量与认证继承）；
3. **交付验收**：无环境变量泄漏、挂载链 100% 吻合、并通过本地 YAML 语法与 schema 自动化断言。

*注：完整 YAML 格式规范参考文档已归档在 `references/bruno-yaml-format.md`。*

---

## 二、架构难点与踩坑铁律 (八大防翻车红线)

1. **URL 前缀必须追溯完整挂载链**：
   - 路由文件里的 `@router.post("/send")` 绝不是完整路径；
   - 必须向上追踪 `include_router(router, prefix="/v1/mail")`，再追踪 `app.mount("/openapi", ...)`，拼接出完整的 `/openapi/v1/mail/send`；
   - **绝对不要轻信代码注释或 docstring 里写的路径**，一切以代码执行期的挂载链为准。
2. **认证方式从代码确认，杜绝臆测**：
   - 检查路由依赖（如 `Depends(get_tenant)`、`Header(alias="X-API-Key")`）或全局中间件，确认 Header 键名与格式（如 `X-API-Key: xxx`、`Authorization: Bearer xxx`）；认证方式错误会导致全量 401。
3. **响应后提取字段（`after-response`）需下钻 service 层**：
   - docstring 或 schema 写返回 `email_send_id`，但 service 层实际返回 dict 的 key 可能是 `id`；
   - 写提取脚本前，必须 grep 到 service/serializer 层的 `return {...}` 逐字段核对。
4. **遵循目标 Collection 的现有格式规范**：
   - 目标目录若存在 `opencollection.yml` + `.yml` → 采用 OpenCollection YAML 格式；
   - 若存在 `bruno.json` + `.bru` → 采用经典 `.bru` 格式；环境文件同理（`environments/local.yml` vs `environments/local.bru`）。
5. **敏感 Token 绝不落盘生产真实值**：
   - API Key 优先由环境或开发者显式提供；
   - 若从测试数据库代查，必须跳过外部集成凭证，使用测试专用 key，并在注释注明。
6. **落盘后必须执行 YAML 语法校验**：
   - 缩进是 YAML 最常见的崩溃点；生成后必须通过脚本校验。
   - 验证解析时不要通过 PowerShell 管道转 JSON（易损坏 UTF-8 编码），推荐使用 Node 子进程按 buffer 读取。
7. **`docs` 必须为纯字符串块，multipart 禁止手动设置 Content-Type**：
   - `docs: |-` 后直接写 Markdown；写成 `docs:\n  content: ...` 对象时 js-yaml 校验照样通过，但 Bruno 加载时会报 `request.docs must be a 'string' type`；
   - `multipart/form-data` 请求切勿手动写 Content-Type header（Bruno 发送时会自动携带含 boundary 的 header）。
8. **跨接口请求链依赖（Chaining）**：
   - 必须先识别产出资源 ID 的前序接口（如创建任务、发送邮件），通过 `bru.setVar("entity_id", res.body.data.id)` 写入运行时变量，再在后续接口中使用 `{{entity_id}}`。

---

## 三、标准自动化生成流水线 SOP

### Step 1: 提取接口契约清单

| 检查项 | 核对源头 | 关键防错点 |
|---|---|---|
| 完整 URL | 挂载链 mount → include_router → 路由装饰器 | 追完整绝对路径前缀 |
| HTTP 方法 | 装饰器 `@router.get/post/put/delete` | POST+JSON 的 RPC 风格接口参数在 body 内，无 query 参数 |
| 认证 Header | 依赖注入 / 中间件 / Header alias | 明确 `X-API-Key` 还是 `Bearer Token` |
| 请求 Body | Pydantic / DTO / Schema 定义 | 必填/可选/默认值/枚举值合法 |
| 响应结构 | 统一响应模型（如 `{success, data, error}`） | 决定 tests 断言与提取路径 |
| 变量传递 | service 层 `return {...}` 提取字段 | 确认为后续接口提供的上下文变量 |

### Step 2: 模板生成（OpenCollection YAML 标准样本）

在 `my-collection/<folder>/01-send-mail.yml` 落盘：

```yaml
info:
  name: 发送测试邮件
  type: http
  seq: 1

http:
  method: post
  url: "{{base_url}}/openapi/v1/mail/send"
  headers:
    - name: X-API-Key
      value: "{{api_key}}"
    - name: Content-Type
      value: application/json
  body:
    type: json
    data: |-
      {
        "recipient": "test@example.com",
        "subject": "Automated Smoke Test",
        "idempotency_key": "{{$randomUUID}}"
      }
  auth: inherit

runtime:
  scripts:
    - type: before-request
      code: |-
        bru.setVar("req_timestamp", Date.now());
    - type: after-response
      code: |-
        if (res.status === 200 && res.body && res.body.success && res.body.data) {
          bru.setVar("mail_id", res.body.data.id);
          console.log("mail_id captured ->", res.body.data.id);
        }
    - type: tests
      code: |-
        test("Status code is 200 and success is true", function() {
          expect(res.status).to.equal(200);
          expect(res.body.success).to.equal(true);
        });

settings:
  encodeUrl: false
  timeout: 0
  followRedirects: true
  maxRedirects: 5

docs: |-
  ## 发送邮件接口
  - 认证方式：Header `X-API-Key`
  - 响应后提取 `data.id` 存入 `mail_id` 变量供后续状态查询接口使用。
```

---

## 四、交付断言与工程校验

生成请求文件后，必须在终端执行语法与格式自检：

```bash
# 1. YAML 语法校验（Node.js / npx）
node -e "
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');
const dir = process.argv[2] || '.';
fs.readdirSync(dir).filter(f => f.endsWith('.yml')).forEach(f => {
  try {
    yaml.load(fs.readFileSync(path.join(dir, f), 'utf8'));
    console.log('✓ OK:', f);
  } catch (e) {
    console.error('✗ FAIL:', f, e.message);
    process.exit(1);
  }
});
" ./my-collection/<folder>
```

```powershell
# 2. 检查生成的占位符与敏感凭据残留（PowerShell）
Get-ChildItem -Path "./my-collection" -Filter "*.yml" -Recurse | ForEach-Object {
    $content = [System.IO.File]::ReadAllText($_.FullName, [System.Text.Encoding]::UTF8)
    if ($content -match "replace-me|cv_live_") {
        Write-Warning "文件 $($_.Name) 中包含待确认占位符或疑似真实生产凭据，请复核！"
    }
}
```
