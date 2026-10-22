---
name: kb-claude-code-upgrade-opencode-router-fix
description: |
  Claude Code 升级后连接 OpenCode/第三方网关报 400 inference_failed、ModelProtocolUnsupported、双鉴权头冲突与 CC Switch 路由代理排障：Claude Code 强制携带 adaptive thinking 与大量 anthropic-beta 扩展参数导致第三方网关拒收；直连 Cloudflare 1010 拦截；Zed Claude ACP 弹窗 auto-mode-classifier-billing 警告；通过 CC Switch 路由代理（15721）开启 openai_chat 协议翻译桥接、注入 x-opencode-session 路由会话头、清洗双键鉴权（Bearer vs API Key）、抑制非必要流量与 1M 上下文（[1M] / Fable 档位）全套实战落地 SOP。
version: 1.1.0
created: 2026-10-22
updated: 2026-10-22
id: "092"
domain: agent
scope: ccswitch
type: fix
slug: "ClaudeCode升级参数冲突与OpenCode路由翻译"
status: verified
last_verified: "2026-10-22"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: true
  trigger_keywords: ["claude code 400 inference_failed", "ModelProtocolUnsupported", "Go requires a credential", "Both ANTHROPIC_AUTH_TOKEN and ANTHROPIC_API_KEY set", "Header is managed by the local proxy and cannot be overridden", "opencode glm 400", "claude code 1m 上下文", "claude code cc-switch 路由", "auto-mode-classifier-billing", "Claude reported a warning", "requests go through 127.0.0.1:15721"]
---

# agent_ccswitch_fix_092_ClaudeCode升级参数冲突与OpenCode路由翻译

> **条目定位**：**Type A 疑难排障条目（Claude Code 新版扩展参数 × OpenCode 网关协议分立 × CC Switch 路由代理桥接）**  
> **危险评级**：★★★☆☆（导致 Claude Code 彻底无法连接下游第三方模型、请求秒拒 400/401/403，配置不当引发双键冲突告警与 UI 校验锁死）  
> **验证环境**：Windows 11、Claude Code v2.1.294 ~ v2.1.303、CC Switch v4.0.5+、OpenCode Go 网关。  
> **关联条目**：CC Switch 数据库读写见 `029_agent_ccswitch_flow_cc-switch直接读写SQLite模型迁移.md`；OpenCode Go 模型访问提速与 reasoning 调优见 `043_agent_opencode_fix_OpenCodeGo模型提速与关闭思考reasoningEffort.md`；opencode 鉴权 401 排障见 `021_agent_opencode_fix_opencode连接GLM鉴权401与端点排障.md`。

---

## 一、现象与报错直击

### 1. 核心现场：Claude Code 直连 OpenCode 报 400 `inference_failed` 或 `ModelProtocolUnsupported`

在 Claude Code 升级到 v2.1.294+ 后，若直连 OpenCode Go 的 Anthropic 端点（`https://opencode.ai/zen/go/v1/messages`）并指定 `glm-5.3-flash` 时：
- 终端发起提问，请求在 60~80ms 内被立即拒绝；
- OpenCode 控制台 Logs 记录：
  ```text
  Status: 400 Rejected
  Error: inference_failed: The inference request failed.
  Endpoint: /inference/go/anthropic/v1/messages
  Model: glm-5.3-flash
  Reasoning: adaptive · max
  ```
- 若使用纯原生 API 测试该端点，上游直接返回协议拒收：
  ```json
  {"type":"error","error":{"type":"ModelProtocolUnsupported","message":"Model does not support this protocol."}}
  ```

### 2. 衍生现场 A：CC Switch 开启路由模式代理直发海外报 403 `error code: 1010`

在 CC Switch 开启本地代理（127.0.0.1:15721）后，代理向 OpenCode 转发请求时，被 Cloudflare WAF 识别为非合规客户端签名直接阻断：
```text
Provider OpenCode Go 请求失败: 上游 HTTP 403: error code: 1010
```

### 3. 衍生现场 B：Claude Code 启动抛出双鉴权头冲突黄色告警

```text
⚠️Both ANTHROPIC_AUTH_TOKEN and ANTHROPIC_API_KEY set · auth may not work as expected
  · to use ANTHROPIC_AUTH_TOKEN: Unset the ANTHROPIC_API_KEY environment variable...
  · to use ANTHROPIC_API_KEY: Unset the ANTHROPIC_AUTH_TOKEN environment variable.
```

### 4. 衍生现场 C：在 CC Switch「Header 覆盖」手动填写认证头被 UI 拦截

在 CC Switch UI 界面的「Header 覆盖」中输入 `x-api-key` 或 `Authorization` 时，下方弹出红字报错：
```text
Header 覆盖格式错误: Header "x-api-key" is managed by the local proxy and cannot be overridden
```
且若缺少 `x-opencode-session` 报 `400 MissingSessionID`；认证头格式不匹配报 `401 Upstream request failed: Go requires a credential`。

### 5. 衍生现场 D：Zed Claude ACP 弹窗黄色警告 `Claude reported a warning`

在 Zed 中通过 `@agentclientprotocol/claude-agent-acp` 唤起 Claude Agent 时，顶部弹窗黄色警告框：
```text
⚠️ Claude reported a warning
We're changing auto mode to no longer charge for classifier requests in Claude Code. However, this session isn't eligible because your requests go through 127.0.0.1:15721, which isn't compatible with this update. Nothing breaks: auto mode keeps working, and its classifier requests are billed as before. To fix it and access the new version of auto mode, ask your gateway to implement: https://code.claude.com/docs/en/auto-mode-classifier-billing
```

---

## 二、底层根因剖析

### 1. Claude Code 客户端升级引入强制性扩展参数（参数代沟）
新版 Claude Code CLI 默认在请求体与 Header 中携带大量专有特性：
- `thinking: { "type": "adaptive", "display": "updates" }`（自适应思考）
- `output_config: { "effort": "max" }`
- 请求头包含 10 余项 `anthropic-beta`（`interleaved-thinking`, `effort-2025-11-24`, `context-1m-2025-08-07` 等）。

智谱 GLM 模型的思考机制原生采用 `reasoning_content`，参数仅支持 `low/high/max`，根本不具备 Anthropic 的 `adaptive` 状态机。OpenCode 的 `/messages` 转换网关在收到不支持的扩展字段后直接报 400 失败。

### 2. OpenCode Go 网关协议分立（端点限制）
经实测对比确认：
- **Anthropic 协议端点（`/zen/go/v1/messages`）**：OpenCode 仅开放了 `deepseek-v4-flash` 等原生兼容模型，对 GLM 模型硬编码返回 `ModelProtocolUnsupported`。
- **OpenAI 兼容端点（`/zen/go/v1/chat/completions`）**：原生完全支持 `glm-5.3-flash`，且支持完整的上下文与流式思考输出。

### 3. 认证标头协议对立（Bearer vs API Key）
- Anthropic 原生端点（`/messages`）要求必须携带 `x-api-key`，携带 `Bearer` 会被拒绝；
- OpenAI 标准端点（`/chat/completions`）强制要求 `Authorization: Bearer <token>`，只带 `x-api-key` 会报错 `Go requires a credential`。
- 此外，OpenCode 网关路由必须依赖 `x-opencode-session` 标头定位会话。

### 4. 本地代理出站直连陷阱
CC Switch 本地代理默认以宿主直连方式发起外部请求，未继承系统环境变量代理（`HTTP_PROXY`），导致直连海外被 Cloudflare 1010 拦截。

### 5. Claude Code auto 模式专属 classifier 计费协议豁免与第三方网关握手缺失
新版 Claude Code 上线了分类器免费机制（用于在 `auto` 模式下预判权限与意图分类轻量请求免计费），要求网关端点实现 `auto-mode-classifier-billing` 专属计费豁免协议。
- 当流量经过 `127.0.0.1:15721` 本地代理时，SDK 检测到非原生端点未实现该计费协议，遂抛出告知性 Warning；
- 官方明确标注 **`Nothing breaks: auto mode keeps working`**（功能完全无损，分类请求仅按普通请求计费）；
- 但对于通过 CC Switch 转接 **OpenCode（GLM / DeepSeek）** 等第三方模型体系的用户而言，Token 消耗完全走第三方计费，Anthropic 官方体系内的自营分类器免计费机制天然无关，该 Warning 仅为 UI 视觉噪音。

---

## 三、标准解决与修复 SOP

### 步骤 1：整库备份（原则先行）

```powershell
node "D:\Users\study_projects\older\.agents\skills\sh-cc-switch-db\scripts\cc-db.mjs" backup
```

### 步骤 2：配置 CC Switch 全局上游代理（破除 1010 拦截）

退出 CC Switch 进程（`Stop-Process -Name cc-switch -Force`），在 `~/.cc-switch/cc-switch.db` 的 `settings` 表中插入上游科学上网代理：
```sql
INSERT OR REPLACE INTO settings (key, value) VALUES ('global_proxy_url', 'http://127.0.0.1:7897');
```

### 步骤 3：开启本地代理协议翻译（`openai_chat`）

将 OpenCode Go 供应商的 `meta.apiFormat` 从 `anthropic` 改为 `openai_chat`。  
此模式下，CC Switch 代理层会自动将 Claude Code 的 Anthropic Messages 协议请求转换为 OpenCode 原生支持的 `/chat/completions` 格式，并将 GLM 返回的思考内容转译回 Claude 的 `type: "thinking"`。

### 步骤 4：配置鉴权头与 Session 标头覆盖

在供应商的 `meta.localProxyRequestOverrides` 中**仅注入自定义标头**（严禁写 `x-api-key` 避免 UI 报红）：
```json
{
  "apiFormat": "openai_chat",
  "customUserAgent": "Claude-Code/2.1.303 (Windows NT 10.0; Win64; x64)",
  "impersonateClaudeCode": true,
  "localProxyRequestOverrides": {
    "headers": {
      "x-opencode-session": "claude-code-session"
    }
  }
}
```

在供应商的 `settings_config.env` 中配置 `ANTHROPIC_AUTH_TOKEN` 与网关免扰环境变量：
```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://opencode.ai/zen/go",
    "ANTHROPIC_AUTH_TOKEN": "oc_sk_...",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "glm-5.3-flash[1m]",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "glm-5.3-flash[1m]",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-5.3-flash[1m]",
    "ANTHROPIC_DEFAULT_FABLE_MODEL": "glm-5.3-flash[1m]",
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "1000000",
    "CLAUDE_CODE_AUTO_MODE_SERVER": "0",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "API_TIMEOUT_MS": "3000000"
  }
}
```

### 步骤 5：同步客户端配置与 1M 上下文（消除双键告警与分类器弹窗）

更新 `~/.claude/settings.json`，**彻底移除 `ANTHROPIC_API_KEY`，仅保留 `ANTHROPIC_AUTH_TOKEN: "PROXY_MANAGED"`**，补齐 Fable 档位、`[1M]` 上下文标识以及 `CLAUDE_CODE_AUTO_MODE_SERVER: "0"`：

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:15721",
    "ANTHROPIC_AUTH_TOKEN": "PROXY_MANAGED",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-haiku-4-5",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-sonnet-5[1M]",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-5[1M]",
    "ANTHROPIC_DEFAULT_FABLE_MODEL": "claude-fable-5[1M]",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL_NAME": "glm-5.3-flash",
    "ANTHROPIC_DEFAULT_SONNET_MODEL_NAME": "glm-5.3-flash",
    "ANTHROPIC_DEFAULT_OPUS_MODEL_NAME": "glm-5.3-flash",
    "ANTHROPIC_DEFAULT_FABLE_MODEL_NAME": "glm-5.3-flash",
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "1000000",
    "CLAUDE_CODE_AUTO_MODE_SERVER": "0",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "API_TIMEOUT_MS": "3000000"
  }
}
```

### 步骤 6：脱离进程树重启 CC Switch

```powershell
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = '"D:\Users\29580\AppData\Local\Programs\CC Switch\cc-switch.exe"' }
```

### 步骤 7：收敛原则：由 CC Switch 统管，禁止污染下游 IDE（如 Zed ACP）

- **统一中心化原则**：所有环境变量一律由 CC Switch 供应商配置统一注入至 `~/.claude/settings.json`，下游所有消费者（包括 Claude Code 原生终端 CLI、Zed Claude ACP、Cursor 等）自动继承；
- **下游零污染原则**：Zed 的 `agent_servers.claude-acp` 保持原生默认配置（开箱即用 `type: "registry"`），**严禁在 Zed `settings.json` 中随意硬编码添加 `env`**，防止供应商切换时下游配置脱节或导致 ACP 进程行为分叉。

---

## 四、验证与防复发闭环

### 1. 代理链路端到端验证

发送包含思考的测试消息验证本地翻译代理：
```python
import urllib.request, json
url = "http://127.0.0.1:15721/v1/messages"
headers = {"x-api-key": "PROXY_MANAGED", "anthropic-version": "2023-06-01", "content-type": "application/json"}
payload = {"model": "claude-opus-5[1M]", "max_tokens": 100, "messages": [{"role": "user", "content": "1+1等于几"}]}
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
with opener.open(req) as resp:
    print(resp.status, resp.read().decode("utf-8"))
```
**断言**：返回 `Status: 200`，`model` 字段为 `glm-5.3-flash`，且正常包含 `type: "thinking"`。

### 2. 客户端菜单与 1M 容量验证

1. 终端启动 `claude`，不再弹出黄色 `⚠️Both ANTHROPIC_AUTH_TOKEN and ANTHROPIC_API_KEY set` 警告；
2. 输入 `/model` 命令，四个档位（Opus、Fable、Sonnet、Haiku）均正常显示为 `(1M context)` 并映射到 `glm-5.3-flash`；
3. 输入 `/context`，上下文总容量上限确认显示为 **1,000,000 tokens**。

### 3. Zed Claude ACP 弹窗闭环验证

1. 打开 Zed 的 Agent Panel，切换至 Claude Agent；
2. 若保留 `auto` 模式，该弹窗属通知型非阻塞 Warning，点击右上角 `×` 即可直接关闭，后续多轮对话代码生成与工具调用均不受任何影响；
3. 若切换至 `acceptEdits` 模式，会话启动时零弹窗，全程静默。
