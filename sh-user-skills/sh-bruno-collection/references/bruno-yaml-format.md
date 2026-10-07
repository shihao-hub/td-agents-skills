# Bruno OpenCollection YAML 格式参考

Bruno 3.0+ 的请求存储格式（MIT 开源，规范见 spec.opencollection.com）。与旧 `.bru` 格式可在同一 collection 共存，但生成新文件时保持与目标 collection 现有格式一致。

## 1. Collection 目录结构

```
my-collection/
├── opencollection.yml     # collection 根配置（旧格式是 bruno.json）
├── environments/
│   └── local.yml          # 环境文件（旧格式 .bru）
├── <folder>/
│   ├── folder.yml         # 文件夹配置（vars / auth / 默认 headers）
│   ├── 01-request-a.yml   # 请求文件，一文件一请求
│   └── 02-request-b.yml
└── <subfolder>/
    └── folder.yml
```

`opencollection.yml` 最小内容（通常已存在，不要动）：

```yaml
opencollection: 1.0.0

info:
  name: creativault
```

## 2. 请求文件完整结构

五个顶层 key：`info` / `http` / `runtime` / `settings` / `docs`。

```yaml
info:
  name: 发送单封邮件          # 侧边栏显示名
  type: http
  seq: 2                     # UI 排序

http:
  method: post               # 大写动词
  url: "{{base_url}}/openapi/v1/mail/send"
  params:                    # query / path 参数（可选）
    - name: user_id
      value: "1"
      type: query            # query 或 path
  headers:
    - name: X-API-Key
      value: "{{api_key}}"
    - name: Content-Type
      value: application/json
  body:
    type: json               # json / text / xml / form-urlencoded / multipart-form / graphql
    data: |-                 # JSON 时 data 是字符串块，内部可插值 {{var}}
      {
        "domain": "{{mail_domain}}",
        "idempotency_key": "{{$randomUUID}}"
      }
  auth: inherit              # 见 §7 认证

runtime:
  scripts:
    - type: before-request   # 请求前
      code: |-
        bru.setVar("timestamp", Date.now());
    - type: after-response   # 响应后：提取字段写入变量（请求链关键）
      code: |-
        if (res.status === 200 && res.body && res.body.success && res.body.data) {
          bru.setVar("thread_id", res.body.data.thread_id);
          console.log("thread_id ->", res.body.data.thread_id);
        }
    - type: tests            # Chai 断言
      code: |-
        test("should return 200 and success", function() {
          expect(res.status).to.equal(200);
          expect(res.body.success).to.equal(true);
        });
  assertions:                # 声明式断言（可选，无需 JS）
    - expression: res.status
      operator: eq
      value: "200"

settings:
  encodeUrl: false
  timeout: 0                 # 毫秒，0 不限时
  followRedirects: true
  maxRedirects: 5

docs: |-                     # 纯字符串块（禁止 docs.content 嵌套对象，Bruno 会报 schema 错）
  ## 接口说明（Markdown）
```

注意 `type: tests` 是复数（不是 `test`）。

### multipart 文件上传（官方 samples 未覆盖，格式经 bruno-converters 源码确认）

```yaml
http:
  method: post
  url: "{{base_url}}/openapi/v1/xxx/upload"
  headers:                   # 只放认证头；禁止手动写 Content-Type
    - name: X-API-Key
      value: "{{api_key}}"
  body:
    type: multipart-form
    data:
      - name: file           # 表单字段名 = 后端参数名（如 FastAPI UploadFile 的形参名）
        type: file           # 文件项必须是 file；普通文本项默认 text
        value: ./hello.txt   # 本地文件路径（相对 collection 根或绝对路径）
        description: 首次使用请在 Bruno UI 中重新选择本地文件
      - name: remark         # 同一表单里的文本字段示例
        value: hello
  auth: inherit
```

- **不要手动设置 Content-Type header**：Bruno 自动携带含 boundary 的 `multipart/form-data`，手写反而破坏 boundary。
- YAML 里的文件路径只是占位：外部工具生成后，用户需在 Bruno UI 中打开请求重新选择本地文件。
- 提取脚本与 JSON 接口写法一致（`after-response` 里 `bru.setVar("attachment_id", res.body.data.attachment_id)`）。

## 3. folder.yml（文件夹配置 / 文件夹变量）

```yaml
info:
  name: atomic-light-mail
  type: folder
  seq: 4

request:
  auth: inherit
  variables:                 # 文件夹级变量（GUI 里是 Folder Settings → Vars）
    - name: api_key
      value: cv_live_xxx
    - name: mail_domain
      value: lightmail-test-01.creativault.studio
```

带类型的变量值（number / boolean / object）：

```yaml
  variables:
    - name: fold_num
      value:
        type: number
        data: "200"
    - name: fold_obj
      value:
        type: object
        data: '{"scope":"folder"}'
```

`request` 下还可配 `headers`（该文件夹请求的默认头）。文件夹变量在脚本里只读：`bru.getFolderVar("api_key")`。

## 4. 环境文件 environments/\<name\>.yml

```yaml
name: local
variables:
  - name: base_url
    value: http://localhost:8000
```

环境切换在 Bruno UI 右上角选择器。`{{base_url}}` 全 collection 可插值。

## 5. 变量系统

优先级（高 → 低）：**Runtime → Request → Folder → Collection → Environment**

| 操作 | API | 持久化 |
|---|---|---|
| 运行时变量 | `bru.setVar(k, v)` / `bru.getVar(k)` / `bru.deleteVar(k)` / `bru.hasVar(k)` | 否（内存，run 内共享） |
| 环境变量 | `bru.setEnvVar(k, v)` / `bru.getEnvVar(k)` | 是（写回环境文件） |
| collection 变量 | `bru.setCollectionVar(k, v)` | 是 |
| 全局变量 | `bru.setGlobalEnvVar(k, v)` | 是 |
| request 变量 | `bru.getRequestVar(k)` | 只读 |
| folder 变量 | `bru.getFolderVar(k)` | 只读 |

插值语法 `{{var}}`，按优先级解析——`after-response` 里 `bru.setVar` 写入的运行时变量能覆盖 folder 同名变量，正好用于"接口响应自动更新默认值"。

## 6. 动态变量（每次请求运行时求值）

语法 `{{$camelCase}}`，大小写敏感，可用于 url / headers / body 等任何字符串字段。

| 变量 | 生成 |
|---|---|
| `{{$randomUUID}}` / `{{$guid}}` | 随机 UUID（幂等键首选） |
| `{{$timestamp}}` / `{{$isoTimestamp}}` | 当前时间戳（unix / ISO） |
| `{{$randomInt}}` | 随机整数 |
| `{{$randomEmail}}` / `{{$randomExampleEmail}}` | 随机邮箱 |
| `{{$randomAlphaNumeric}}` / `{{$randomNanoId}}` | 随机字符串 |
| `{{$randomFirstName}}` / `{{$randomFullName}}` | 随机姓名 |

完整列表：docs.usebruno.com/testing/script/dynamic-variables（Faker.js 驱动）。

## 7. 认证类型

```yaml
  auth: inherit                          # 继承 folder/collection（默认推荐）
  auth: none
  auth:
    type: bearer
    token: "{{token}}"
  auth:
    type: apikey                         # 自定义 Header 认证
    key: X-API-Key
    value: "{{api_key}}"
    placement: header
  auth:
    type: basic
    username: user
    password: pass
```

其余支持：digest / oauth1 / oauth2 / awsv4 / ntlm / wsse。简单 Header 认证也可以不配 auth，直接在 `http.headers` 写死头（与 collection 现有惯例保持一致即可）。

## 8. 脚本 API 速查

请求前脚本（`before-request`）可用：`req`（`req.setUrl` / `req.setHeader` / `req.setBody` / `req.getBody`）、`bru.*`（除 res 外全部）。

响应后/测试脚本（`after-response` / `tests`）额外可用 `res`：

```javascript
res.status            // 状态码（也有 res.getStatus()）
res.body              // 已解析的 JSON（res.body.data.xxx）
res.body              // 非调用时用 res.getBody()
res.statusText / res.headers / res.getHeader(name)
res.getResponseTime() // 毫秒
```

测试：`test("描述", fn)` + Chai `expect(x).to.equal(y)` / `.to.be.a("string")` 等。

请求链跳转：`bru.setNextRequest("请求名")`（collection runner 中按名执行下一个）。

## 9. .bru 旧格式对照（遇到老 collection 时）

```
meta { name: 发送单封邮件; type: http; seq: 2 }
post { url: {{base_url}}/xxx; body: json; auth: inherit }
headers { X-API-Key: {{api_key}} }
body:json { {"domain": "{{mail_domain}}"} }
scripts:post-res { bru.setVar("thread_id", res.body.data.thread_id); }
tests { test("ok", function() { expect(res.status).to.equal(200); }); }
```

## 10. 官方文档索引

- OpenCollection YAML 概览：https://docs.usebruno.com/opencollection-yaml/overview
- 结构参考：https://docs.usebruno.com/opencollection-yaml/structure-reference
- 变量：https://docs.usebruno.com/variables/overview（folder-variables / collection-variables 等子页）
- 脚本 API：https://docs.usebruno.com/testing/script/javascript-reference
- 动态变量：https://docs.usebruno.com/testing/script/dynamic-variables
- 规范与 JSON Schema：https://spec.opencollection.com/ / https://schema.opencollection.com/
- **字段结构事实来源（schema 疑难杂症查这里）**：https://github.com/usebruno/bruno/tree/main/packages/bruno-converters/src/opencollection —— YAML ↔ Bruno 内部模型的互转代码，覆盖度高于官方 samples（如 multipart 文件项、docs 字符串类型的最终裁决以此为准）
