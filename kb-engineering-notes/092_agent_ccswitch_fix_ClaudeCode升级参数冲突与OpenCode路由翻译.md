---
name: kb-claude-code-upgrade-opencode-router-fix
description: |
  Claude Code 升级后连接 OpenCode/第三方网关报 400 inference_failed、ModelProtocolUnsupported、双鉴权头冲突与 CC Switch 路由代理排障：Claude Code 强制携带 adaptive thinking 与大量 anthropic-beta 扩展参数导致第三方网关拒收；直连 Cloudflare 1010 拦截；Zed Claude ACP 弹窗 auto-mode-classifier-billing 警告；ACP v0.97.0+ 鉴权守卫拦截仅保留 AUTH_TOKEN 导致 Zed 报 Authentication required 并在后台死锁 auth login --console 致 Authenticating to Claude Agent... 永久转圈；通过 CC Switch 路由代理（15721）开启 openai_chat 协议翻译桥接、注入 x-opencode-session 路由会话头、清洗双键鉴权（Bearer vs API Key）、Zed ACP 显式注入代理及伪装通行凭证全套实战落地 SOP。
version: 1.2.0
created: 2026-10-22
updated: 2026-10-27
id: "092"
domain: agent
scope: ccswitch
type: fix
slug: "ClaudeCode升级参数冲突与OpenCode路由翻译"
status: verified
last_verified: "2026-10-27"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: true
  trigger_keywords: ["claude code 400 inference_failed", "ModelProtocolUnsupported", "Go requires a credential", "Both ANTHROPIC_AUTH_TOKEN and ANTHROPIC_API_KEY set", "Header is managed by the local proxy and cannot be overridden", "opencode glm 400", "claude code 1m 上下文", "claude code cc-switch 路由", "auto-mode-classifier-billing", "Claude reported a warning", "requests go through 127.0.0.1:15721", "Authenticating to Claude Agent...", "session account carries no identity signal", "Authentication required", "auth login --console", "claude acp 转圈", "@zed-industries/claude-code-acp", "@agentclientprotocol/claude-agent-acp", "claude acp 弃用", "claude acp 静默升级"]
---

# agent_ccswitch_fix_092_ClaudeCode升级参数冲突与OpenCode路由翻译

> **条目定位**：**Type A 疑难排障条目（Claude Code 新版扩展参数 × OpenCode 网关协议分立 × CC Switch 路由代理桥接）**  
> **危险评级**：★★★☆☆（导致 Claude Code 彻底无法连接下游第三方模型、请求秒拒 400/401/403，配置不当引发双键冲突告警与 UI 校验锁死）  
> **验证环境**：Windows 11、Claude Code v2.1.294 ~ v2.1.303、CC Switch v4.0.5+、OpenCode Go 网关。  
> **关联条目**：CC Switch 数据库读写见 `029_agent_ccswitch_flow_cc-switch数据库机制模型迁移与避坑指南.md`；OpenCode Go 模型访问提速与 reasoning 调优见 `043_agent_opencode_fix_OpenCodeGo模型提速与关闭思考reasoningEffort.md`；opencode 鉴权 401 排障见 `021_agent_opencode_fix_opencode连接GLM鉴权401与端点排障.md`。

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

### 6. 衍生现场 E：Zed Claude ACP 升级 0.97.0+ 底部转圈 `Authenticating to Claude Agent...` 且后台卡死 `auth login --console`

在遵照步骤 5 从 `~/.claude/settings.json` 中移除 `ANTHROPIC_API_KEY`、仅保留 `ANTHROPIC_AUTH_TOKEN` 后，终端 CLI 运行完全正常，但 Zed 内置的 Claude Agent（升级至 `@agentclientprotocol/claude-agent-acp@0.97.0+` 后）出现以下现象：
- Zed 界面底部状态栏永久转圈：`ⓘ Authenticating to Claude Agent...`，对话框输入消息无响应；
- 查看 `%LOCALAPPDATA%\Zed\logs\Zed.log`，记录以下错误：
  ```text
  [agent_servers::acp::transport] agent stderr: [session/query] sessionId=... resume=none apiType=native baseUrl=native
  [agent_servers::acp::transport] agent stderr: [authStatus] session account carries no identity signal; keeping probe
  [acp_thread] Error in run turn: Authentication required
  ```
- 检查系统运行进程，发现 Zed 在后台静默生成了无窗口的孤儿登录进程并陷入永久等待：
  ```powershell
  # Win32_Process 取证
  ProcessId: 7860  node.exe ... claude-agent-acp\dist/index.js --cli auth login --console
  ProcessId: 11864 claude.exe auth login --console
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

### 6. ACP v0.97.0+ 鉴权守卫（`holdsNonSubscriptionCredential`）对双键的严苛分流与 Zed 脱节
新版 `@agentclientprotocol/claude-agent-acp` 增加了严格的单会话鉴权拦截机制（`refuseClaudeSubscriptionTurn` 与 `auth-status.js`）：
- **鉴权判定逻辑（`accountInfoHasIdentitySignal`）**：
  必须具备以下三者之一才算“已认证有效身份”：
  1. `account.apiKeySource` 有效（如 `ANTHROPIC_API_KEY`、`apiKeyHelper`）；
  2. `account.subscriptionType` 有效（Claude 官方 Pro/Max 网页订阅）；
  3. `apiProvider` 为非 `firstParty`（Bedrock / Vertex / Gateway）。
- **`ANTHROPIC_AUTH_TOKEN` 的断层陷阱**：
  步骤 5 移除 `ANTHROPIC_API_KEY` 后，`claude.exe auth status --json` 仅返回 `authMethod: "oauth_token"`，既不包含 `subscriptionType`，也不包含 `apiKeySource`。ACP 内部判定 `holdsNonSubscriptionCredential(account)` 为 `false`，遂在每次发送 prompt 前拦截并直接抛出 `RequestError.authRequired`。
- **Zed 进程隔离脱节与后台盲拉死锁**：
  Zed 启动的 `claude-acp` 是独立 Node.js 进程，若未显式配置 `env`，它走 `apiType=native baseUrl=native`（未读取 `127.0.0.1:15721` 代理）。接收到 `authRequired` 后，Zed 自动调用 `terminal-auth` 启动 `claude.exe auth login --console`，在 Windows 无终端窗口的环境下永久死锁，造成前端无限卡在 `Authenticating to Claude Agent...`。

### 7. 实体迁移与静默升级陷阱：`@zed-industries` 弃用与 `@agentclientprotocol` 动态静默更新
- **包名变迁与假性停更陷阱（Anti-Pattern）**：
  - 早期历史包：`@zed-industries/claude-code-acp` 已于 2026 年 2 月被官方正式废弃，npm 显式声明：`"This package has been renamed to @agentclientprotocol/claude-agent-acp. Please migrate to continue receiving updates."`，版本永久停留在 `v0.16.2`；
  - 官方现役包：**`@agentclientprotocol/claude-agent-acp`**（由 Anthropic、Zed Industries 与 JetBrains 联合成立的 Agent Client Protocol 组织共同维护），版本已演进至 `v0.97.0`；
  - **AI 查错包警示**：排查时若仅按历史经验检索 `@zed-industries/claude-code-acp`，会误得出“该包停留在 2 月份已数月未维护”的严重假象。
- **Zed Registry 动态静默 Hydrate 机制（零操作暴雷归因）**：
  - Zed 的外部 Agent（`type: "registry"`）通过内置注册表与 `npx` 机制动态解析远端最新版本；
  - 2026-10-26 12:48 UTC 上游刚发布 `v0.97.0`，用户次日冷启动 Zed 时被自动拉取覆盖，无需任何显式升级命令；
  - 这种“远端日更 + 宿主静默 Hydrate”机制解释了为什么原本正常的配置会在一夜之间突发鉴权拦截死锁（Zero-action Regression）。

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

### 步骤 7：修正：下游 IDE（Zed ACP）对接代理的必备环境注入

> ⚠️ **2026-10-27 机制演进修正（防转圈死锁）**：  
> 原“下游零污染”假设在 ACP v0.97.0+ 升级后被证伪。由于 Zed 的外部 ACP Agent 作为独立 Node.js 进程运行，且新版 ACP 引入了对 `apiKeySource` 的强校验守卫，**必须在 Zed 配置文件中显式注入代理地址与伪装通行凭证**。

在 `%APPDATA%\Zed\settings.json` 的 `agent_servers.claude-acp` 中显式添加 `env`：
```json
"claude-acp": {
  "default_config_options": {
    "fast": true,
    "effort": "max",
    "model": "default",
    "mode": "auto"
  },
  "type": "registry",
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:15721",
    "ANTHROPIC_API_KEY": "sk-ccswitch-dummy"
  }
}
```
- **参数说明**：
  - `ANTHROPIC_BASE_URL`：确保 Zed 的 ACP 子进程请求准确发往 CC Switch 本地端口（`15721`），而非直连官方；
  - `ANTHROPIC_API_KEY`：填入任意占位字符串即可（如 `sk-ccswitch-dummy`）。作用是使底层 `claude.exe auth status --json` 输出 `apiKeySource: "ANTHROPIC_API_KEY"`，令 ACP 鉴权守卫直接放行；且请求发送给 CC Switch 本地代理时，由代理层完成真实鉴权转译，不会干扰内部 token 路由。

### 步骤 8：清理后台孤儿登录进程与 Zed 验证

修改配置前/后，必须清理后台遗留的无窗口死锁进程：
```powershell
Get-Process | Where-Object { $_.ProcessName -in 'claude', 'node' -and $_.CommandLine -like '*claude-agent-acp*' } | Stop-Process -Force
```
彻底退出并重启 Zed 编辑器即可恢复就绪。

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

### 4. Zed Claude ACP 无鉴权卡死与代理流通断言

1. 重启 Zed 后打开 Claude Agent，底部 `Authenticating to Claude Agent...` 立即消失，直接呈可用就绪态；
2. 任务管理器无残留的 `claude.exe auth login --console` 孤儿进程；
3. 发送任意对话消息，请求经 `127.0.0.1:15721` 代理转发至 OpenCode Go，正常获得模型流式回答。
