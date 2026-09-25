# DeepSeek 官方 Codex 接入与 CC Switch 纳管实战

沉淀自 2026-09-24~25 实战。针对 DeepSeek 官方 Codex 接入规范、多模态识图权限与 CC Switch 本地代理纳管机制。

---

## 1. 官方文档源与契约核心

- **官方文档地址**：[接入 Codex | DeepSeek API Docs](https://api-docs.deepseek.com/zh-cn/quick_start/agent_integrations/codex)
- **协议契约**：DeepSeek API **原生支持 OpenAI Responses API**，无需本地代理做 Chat Completions 协议翻译。
  - 端点：`https://api.deepseek.com`（或 `https://api.deepseek.com/`）
  - 协议类型：`wire_api = "responses"`
  - 官方支持模型列表：
    - `deepseek-flash`：最新前沿编程与多模态模型，支持图片输入与深度推理，上下文 1,048,576 (1M)。
    - `deepseek-v4-pro`：旗舰级深度推理代码模型，纯文本输入，上下文 1,048,576 (1M)。
  - 推理档位：支持 `low`、`high`、`max`，默认推荐 `high`。

---

## 2. 官方一键脚本与 CC Switch 架构冲突分析（避坑必读）

官方文档提供了两种配置方式：
1. 一键脚本：`irm https://cdn.deepseek.com/api-docs/codex-deepseek-setup.ps1 | iex`
2. 手动写入 `~/.codex/config.toml` 与 `~/.codex/models.json`

### 为什么在 CC Switch 环境下严禁直接跑官方脚本？

在 CC Switch 开启本地代理接管（`enableLocalProxy = true`）的架构下：
1. **代理旁路破坏**：CC Switch 接管时会将 `~/.codex/config.toml` 中的 `[model_providers.custom].base_url` 改写为 `http://127.0.0.1:15721/v1`，并通过代理层实现凭据注入、用量统计、会话统一（`unifyCodexSessionHistory`）和无缝切换。官方脚本会将 `config.toml` 直接改为直连 `https://api.deepseek.com` 并修改 `model_provider = "deepseek"`，绕过了本地代理。
2. **状态竞争与覆盖**：CC Switch 具备异常退出检测与配置热切换恢复机制。一旦 CC Switch 重启或检测到配置不匹配，会直接用 DB 中已备份的 Live 快照覆盖 `config.toml`，导致官方脚本写入的改动被静默冲掉。
3. **正确解法**：**将官方推荐的全部规范沉淀到 CC Switch 数据库中**，作为 `app_type = "codex"` 的一个独立供应商（例如 ID `9abb2307-ffb7-471c-9b79-f40432c41017`，名称 `DeepSeek`）。由 CC Switch 统一分发到 `cc-switch-model-catalog.json` 并通过本地代理透传。

---

## 3. CC Switch 中的标准配置形态

### A. 数据库中的 `settings_config` 完整模板

```json
{
  "auth": {
    "OPENAI_API_KEY": "sk-1574d0cdb52c411d9426b50d635116b2"
  },
  "config": "model_provider = \"custom\"\nmodel = \"deepseek-flash\"\nmodel_reasoning_effort = \"high\"\n\n[model_providers.custom]\nname = \"deepseek\"\nbase_url = \"https://api.deepseek.com\"\nwire_api = \"responses\"\nrequires_openai_auth = true\n",
  "modelCatalog": {
    "models": [
      {
        "model": "deepseek-flash",
        "displayName": "DeepSeek-Flash",
        "contextWindow": 1048576,
        "inputModalities": [
          "text",
          "image"
        ],
        "supportsParallelToolCalls": true,
        "reasoningLevels": [
          "low",
          "high",
          "max"
        ],
        "defaultReasoningLevel": "high"
      },
      {
        "model": "deepseek-v4-pro",
        "displayName": "DeepSeek-V4-Pro",
        "contextWindow": 1048576,
        "inputModalities": [
          "text"
        ],
        "supportsParallelToolCalls": true,
        "reasoningLevels": [
          "low",
          "high",
          "max"
        ],
        "defaultReasoningLevel": "high"
      }
    ]
  }
}
```

> **注意**：如果用户仅需要 Flash 模型，可只保留 `deepseek-flash` 节点。

### B. 数据库中的 `meta` 完整模板

因为 DeepSeek 原生支持 Responses API，因此 `apiFormat` 必须使用 **`openai_responses`**，代理层直接透传请求，不走本地 chat 翻译：

```json
{
  "commonConfigEnabled": true,
  "usage_script": {
    "enabled": true,
    "language": "javascript",
    "code": "",
    "timeout": 10,
    "templateType": "balance",
    "autoQueryInterval": 5
  },
  "endpointAutoSelect": true,
  "apiFormat": "openai_responses"
}
```

---

## 4. 关键机制与实测暗坑

### 坑 1：Codex 贴图与多模态权限 (`inputModalities`)

- **机制**：Codex 客户端（无论是 CLI 还是 Desktop）在启动时读取 `model_catalog_json`。只有当模型的 `input_modalities` 包含 `"image"`（即 `["text", "image"]`）时，Codex 才会开放客户端界面的截图粘贴、拖入图片和 `-i` 参数。如果缺失该字段，Codex 直接报错：`此模型不支持图像输入`。
- **UI 盲区**：CC Switch 前端“模型映射”表格只有（菜单显示名、实际请求模型、上下文窗口、思考等级）4 列，没有模态勾选框。若由 UI 重新编辑并保存，可能丢失 `inputModalities`。必须在 DB 的 `settings_config.modelCatalog.models[]` 中显式保证 `"inputModalities": ["text", "image"]`。

### 坑 2：第三方聚合（如 OpenCode Go）中的模型命名陷阱

在通过第三方 OpenAI 兼容网关（如 OpenCode Go `https://opencode.ai/zen/go/v1`，走 `meta.apiFormat = "openai_chat"` 翻译层）调用 DeepSeek 时：

| 模型名 | 实测状态 | 多模态能力 | 说明 |
|---|---|---|---|
| **`deepseek-flash`** | **200 OK** | ✅ 支持图片 (`image_url`) | **推荐**：既能识图又有完整思考链 |
| **`deepseek-v4-flash-vision-exp`** | **200 OK** | ✅ 支持图片 | 实验性多模态版本 |
| **`deepseek-v4-flash`** | **400 报错** | ❌ **纯文本模型** | 上游报错：`[400] Model only supports text input; received unsupported content type 'image_url'` |

**避坑结论**：只要在 Codex 中需要 DeepSeek 识图，实际请求模型名务必写 `deepseek-flash`，不要写 `deepseek-v4-flash`。

---

## 5. 验证与排查命令

### 1) 官方 API 直连探针（验证 Key 与原生多模态支持）
```bash
# 验证模型列表与能力返回
curl -s https://api.deepseek.com/v1/models \
  -H "Authorization: Bearer sk-..." | jq .

# 直连测试识图（传入 1x1 像素微型 PNG base64）
curl -s -X POST https://api.deepseek.com/chat/completions \
  -H "Authorization: Bearer sk-..." \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-flash",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "Describe this"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="}}
      ]
    }]
  }' | jq .
```

### 2) CC Switch 代理透传验证
```bash
# 验证本地代理 Responses 透传（返回 Responses 对象格式）
curl -s -X POST http://127.0.0.1:15721/v1/responses \
  -H "Authorization: Bearer PROXY_MANAGED" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-flash",
    "input": "1+1=",
    "reasoning": {"effort": "high"}
  }' | jq .
```

### 3) 查验生成的 Live Catalog
```powershell
# 验证 input_modalities 是否包含 image
Get-Content "$env:USERPROFILE\.codex\cc-switch-model-catalog.json" | Select-String -Pattern "input_modalities" -Context 0,2
```
