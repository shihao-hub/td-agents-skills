# 各 app 段 settings_config 形状与同步语义（实测 v3.20.0）

`settings_config` 是 JSON 文本，**形状随 app_type 完全不同**。改库前先 `cc-db.mjs show <app> <id>` 看一段现成条目作参照。

## claude 段

切换时写 `~/.claude/settings.json` 的 env 块：

```json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "sk-...",
    "ANTHROPIC_BASE_URL": "https://.../",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "glm-5.3[1M]",
    "ANTHROPIC_MODEL": "glm-5.3[1M]"
  },
  "permissions": { "allow": ["Bash(*)"], "defaultMode": "default" }
}
```

## codex 段（Switch 型）

`auth`（对象）+ `config`（**TOML 文本**）+ `modelCatalog`：

```json
{
  "auth": { "OPENAI_API_KEY": "sk-..." },
  "config": "model_provider = \"custom\"\nmodel = \"glm-5.3\"\n\n[model_providers.custom]\nname = \"zhipu_glm\"\nbase_url = \"https://...\"\nwire_api = \"responses\"\nrequires_openai_auth = true\n",
  "modelCatalog": { "models": [{ "model": "glm-5.3", "displayName": "GLM-5.3", "contextWindow": 1000000, "reasoningLevels": ["max"], "defaultReasoningLevel": "max" }] }
}
```

### 代理模式下的 live 形状（enableLocalProxy=true，2026-09-23 实测）

切换/启动时 cc-switch 接管 `~/.codex/config.toml`：`[model_providers.custom].base_url` 被改写为 `http://127.0.0.1:15721/v1`、追加 `experimental_bearer_token = "PROXY_MANAGED"`、`model_catalog_json = "cc-switch-model-catalog.json"`；`~/.codex/auth.json` 保留官方 OAuth（`preserveCodexOfficialAuthOnSwitch`）。settings_config 里的 `base_url` 仍是直连上游地址，只存 DB。

### meta.apiFormat：代理透传 vs 翻译（重点坑）

| apiFormat | 代理行为 | 适用 |
|---|---|---|
| `openai_responses` | 透传 `{base_url}/responses` | 上游原生支持 Responses API |
| `openai_chat` | 翻译为 `{base_url}/chat/completions`，响应转回 Responses 格式 | 上游只有 chat completions（**智谱 GLM**） |

智谱 coding 端点（`https://open.bigmodel.cn/api/coding/paas/v4`）**没有 `/responses`（实测 404）**。GLM 渠道配成 `openai_responses` 时代理直接透传并报 `upstream_status: HTTP 404; path /v4/responses`；正确配置：

```json
"apiFormat": "openai_chat",
"codexChatReasoning": {
  "supportsThinking": true,           // 启用思考
  "supportsEffort": false,            // 不向智谱发 reasoning_effort（GLM 不支持）
  "thinkingParam": "thinking",        // 上游思考参数名
  "effortParam": "none",
  "outputFormat": "reasoning_content" // 从响应 reasoning_content 读思考内容
}
```

### modelCatalog 与图片支持

`modelCatalog.models[]` 生成 `~/.codex/cc-switch-model-catalog.json`，Codex 应用据此决定模型能力/UI：

| DB 字段 | live catalog 字段 | 说明 |
|---|---|---|
| model / displayName | slug / display_name | 模型 ID 与显示名 |
| contextWindow | context_window / max_context_window | |
| inputModalities | input_modalities | **`["text","image"]` 才允许贴图**；仅 text 时应用报「此模型不支持图像输入」 |
| reasoningLevels | supported_reasoning_levels | 可选思考档位 |
| defaultReasoningLevel | default_reasoning_level | 缺省时 cc-switch 自己回落（实测 fallback=max） |
| supportsParallelToolCalls | supports_parallel_tool_calls | |

改完 settings_config 重启 cc-switch，live catalog 自动重新生成；**Codex 应用需重启才会重载**。模型是否真支持视觉必须实测——直连发 `image_url` content，智谱对不支持的模型回 `1210 参数非法`（实测 glm-5.3-flash ✅「红色圆形」、glm-5.3 ❌）。

### 排查与验证命令（GLM 实战）

```bash
# 1) 上游能力：chat 通、responses 404
curl -s https://open.bigmodel.cn/api/coding/paas/v4/responses -H "Authorization: Bearer $KEY" -d '{"model":"glm-5.3","input":"hi"}'
# 2) 代理链路（修复后应返回 Responses 对象而非 upstream 404）
curl -s -X POST http://127.0.0.1:15721/v1/responses -H "Authorization: Bearer PROXY_MANAGED" \
  -H 'Content-Type: application/json' -d '{"model":"glm-5.3","input":"hi"}'
# 3) 日志确认实际转发目标（应命中 /chat/completions）
tail ~/.cc-switch/logs/cc-switch.log | grep '\[Codex\] >>> 请求目标'
# 4) 端到端（图片：glm-5.3-flash + -i；提示走 stdin 传入）
printf '%s' '描述图片' | codex exec --model glm-5.3-flash -i test.png
```

图片在代理翻译中为 Responses `input_image` → chat `image_url`，已验证；流式 SSE（`response.reasoning_summary_text.delta` 等）亦正常。

## opencode 段（Additive）

就是写进 `~/.config/opencode/opencode.json` `provider.<id>` 的完整 JSON：

```json
{
  "npm": "@ai-sdk/openai-compatible",
  "name": "Zhipu GLM",
  "options": { "baseURL": "https://open.bigmodel.cn/api/coding/paas/v4", "apiKey": "..." },
  "models": {
    "glm-5.3": {
      "name": "glm-5.3",
      "interleaved": { "field": "reasoning_content" },
      "options": { "reasoningEffort": "max" },
      "reasoning": true
    }
  }
}
```

要点：
- `meta.liveConfigManaged: true` 时与 opencode.json **双向同步**，两侧 `name` 等字段必须一致，否则互相改回。
- effort/variants 深层机制（reasoningEffort vs effort 键名、variants.disabled）归 sh-zed-opencode-setup，动 opencode 段必读该 skill。
- opencode 会回写 opencode.json（选一次模型就把解析后配置整体回写）。

## pi 段（Additive，重点）

= 写入 `~/.pi/agent/models.json` `providers.<id>` 的节点：

```json
{
  "name": "Zhipu GLM",
  "baseUrl": "https://open.bigmodel.cn/api/coding/paas/v4",
  "apiKey": "79dec...<同 opencode 段复用>",
  "api": "openai-completions",
  "models": [
    {
      "id": "glm-5.3",
      "name": "GLM-5.3",
      "reasoning": true,
      "thinkingLevelMap": { "off": null, "minimal": null, "low": "low", "medium": null, "high": "high", "xhigh": null, "max": "max" },
      "input": ["text"],
      "cost": { "input": 1.4, "output": 4.4, "cacheRead": 0.26, "cacheWrite": 0 },
      "compat": {
        "supportsStore": false, "supportsDeveloperRole": false,
        "supportsReasoningEffort": true, "maxTokensField": "max_tokens",
        "thinkingFormat": "zai", "zaiToolStream": true
      },
      "contextWindow": 1000000,
      "maxTokens": 131072
    }
  ]
}
```

### models.json schema（ModelDefinitionSchema，typebox 校验）

- 顶层：`{ "providers": { "<providerKey>": ProviderConfig } }`（支持 JSON 注释与 BOM）
- ProviderConfig：`name, baseUrl, apiKey, api, oauth, headers, compat, authHeader, models[], modelOverrides{}`
- 模型字段：`id(必填), name, api, baseUrl, reasoning, thinkingLevelMap, input[], cost, contextWindow, maxTokens, samplingParams, headers, compat`
- compat 常用键（openai-completions）：`thinkingFormat`（zai 格式对智谱必配）、`supportsReasoningEffort`、`maxTokensField`、`zaiToolStream` 等

### pi 的机制（源码验证，farion1231/cc-switch + badlogic/pi-mono）

1. **cc-switch 只管理 models.json**；membership = 该文件中存在此 provider key。打开 Pi 段时 native（models.json）单向同步回 DB，native 优先。
2. **cc-switch 绝不写 pi 的 `settings.json` / `auth.json`**（测试 `provider_membership_never_changes_pi_auth_or_defaults` 明确保证）。增删 provider 不影响默认模型选择与密钥。
3. **pi 内置供应商来自 models.dev 目录**（缓存在 `~/.pi/agent/models-store.json`）+ `auth.json` 存 API key。自定义供应商才走 models.json。
4. **默认思考档位在 `~/.pi/agent/settings.json`**：
   - `defaultThinkingLevel`：全局默认（"off|minimal|low|medium|high|xhigh|max"）
   - `modelThinkingLevels`：按 `"provider/modelId"` 键精准覆盖，如 `{"zai-coding-cn/glm-5.3": "max"}`
   - 级联：显式参数 → 会话恢复 → modelThinkingLevels → defaultThinkingLevel → 内置 "medium" → **clamp 到模型 thinkingLevelMap 能力**
   - 模型定义里**没有** reasoningEffort 之类请求参数字段（与 opencode 本质不同）；档位 → 请求参数的映射由 `thinkingLevelMap` + `compat.thinkingFormat` 完成
5. pi 版本锚点：实测 pi 0.85.1。

## 实战案例：Zhipu GLM → pi 段 + 默认思考 max（2026-09-06 全流程）

需求：pi 默认模型 glm-5.3 / glm-5.3-flash 思考档位 max，并在 cc-switch Pi 段有可管理条目。

1. 备份 `~/.pi/agent/settings.json`（同目录 .bak）+ 整库备份 cc-switch.db。
2. `Stop-Process -Name cc-switch -Force`（写库前退出）。
3. `settings.json` 增加（两个 provider 前缀都配，多余键无害）：
   ```json
   "modelThinkingLevels": {
     "zai-coding-cn/glm-5.3": "max",
     "zai-coding-cn/glm-5.3-flash": "max",
     "zhipu-glm/glm-5.3": "max",
     "zhipu-glm/glm-5.3-flash": "max"
   }
   ```
4. 创建 `~/.pi/agent/models.json`：providers.zhipu-glm 节点（上文模板），模型定义从 `models-store.json` 的 zai-coding-cn 目录原样拷贝（保证 thinkingLevelMap/compat/cost 正确）。
5. 写 DB：providers 插行（id=zhipu-glm, app_type=pi, name=Zhipu GLM, category=cn_official, icon=zhipu/#0F62FE, settings_config=models.json 节点原文）；provider_endpoints 插行 (zhipu-glm, pi, baseURL)。
6. 验证：JSON.parse 两个文件；DB 回读 settings_config 与 models.json 深比较一致；用户重开 cc-switch 看 Pi 段、启动 pi 用 `/thinking` 确认 max。

关键教训：
- **「默认思考 max」的开关在 pi 自己的 settings.json，cc-switch 数据库配不了**——先搞清目标应用的配置边界再动库。
- DB settings_config 与 models.json 必须内容一致，避免 cc-switch 同步抖动。
- 显示名（name）是用户偏好，别擅自改成 id。

## 实战案例：DeepSeek → opencode 段默认 max + flash 多模态（2026-09-14 全流程）

需求：opencode 段 DeepSeek（`deepseek-flash` 多模态 + `deepseek-v4-pro`）默认 max 思考，参照 zhipu-glm 模板。最终条目 id=`deepseek-max`、显示名 "DeepSeek Max"。

踩坑实录（按发生顺序）：

1. **旧条目 id=deepseek 是 opencode 内置目录 id** → 计划改名规避变体。但**改名后 verify 仍 FAIL**：opencode 的 effort 变体**按模型 ID 生成**（deepseek-flash/pro 是 models.dev 已知模型），自定义 provider id 规避无效——flash 带 [low,medium,high]、pro 带 [low,medium,high,max]，未选变体回落第一档 low 顶掉 options 的 max。→ 模型级 `variants` 五档全 `disabled` 才是正解（机制归 sh-zed-opencode-setup，2026-09-14 已修正该 skill 的旧归因）。
2. **改 id 撞外键**：`UPDATE providers SET id` 报 FOREIGN KEY constraint failed（provider_endpoints/provider_health 引用主键）。→ `PRAGMA defer_foreign_keys = ON` + 三表一起改 + `foreign_key_check` 核验（见 db-schema.md）。
3. **显示名与内置重复**：name "DeepSeek" 在 Zed 选择器里和内置官方 DeepSeek 分不开 → 用户定为 "DeepSeek Max"；DB `name` 列 + `settings_config.name` + opencode.json `provider.<id>.name` 三处一起改（liveConfigManaged 要求两侧一致）。
4. **auth.json 激活内置供应商**：`~/.local/share/opencode/auth.json` 里的 deepseek 条目（key 与自定义配置相同）会让内置 deepseek 照样出现在选择器——清掉才不重复（key 配置里另有，无损失）。

最终 settings_config（opencode 段）：

```json
{
  "npm": "@ai-sdk/openai-compatible",
  "name": "DeepSeek Max",
  "options": { "baseURL": "https://api.deepseek.com/v1", "apiKey": "sk-..." },
  "models": {
    "deepseek-flash": {
      "name": "DeepSeek V4 Flash",
      "reasoning": true,
      "interleaved": { "field": "reasoning_content" },
      "options": { "reasoningEffort": "max" },
      "modalities": { "input": ["text", "image"], "output": ["text"] },
      "variants": { "low": { "disabled": true }, "medium": { "disabled": true }, "high": { "disabled": true }, "xhigh": { "disabled": true }, "max": { "disabled": true } }
    },
    "deepseek-v4-pro": {
      "name": "DeepSeek V4 Pro",
      "reasoning": true,
      "interleaved": { "field": "reasoning_content" },
      "options": { "reasoningEffort": "max" },
      "variants": { "…同上五档全禁…" }
    }
  }
}
```

验证四层（详见 sh-zed-opencode-setup 任务 B）：配置层 verify-opencode-effort.mjs PASS；发线层 verify-wire-effort.mjs 抓到 2 笔 POST 请求体均含 `"reasoning_effort": "max"`；API 行为层 DeepSeek A/B low=279 vs max=379 reasoning tokens；体验层 Zed 无下拉框。

关键教训：
- **换 provider id 不能规避 opencode 变体生成**（按模型 ID）；"自定义就没事"是错觉，glm-5.3 只是恰好无档位元数据。
- opencode 段每次改库必须同步 opencode.json 同名节点（两侧深比较），否则 liveConfigManaged 双向同步会互相顶。
- 用户重启后 opencode 会回写 opencode.json（新增 mcp 键等）——只要解析态本身正确，回写的就是正确态，别和它对抗。
