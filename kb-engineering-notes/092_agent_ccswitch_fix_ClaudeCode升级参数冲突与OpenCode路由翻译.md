---
name: kb-claude-code-upgrade-opencode-router-fix
description: |
  Claude Code 升级后连接 OpenCode/第三方网关报 400 inference_failed、ModelProtocolUnsupported、双鉴权头冲突与 CC Switch 路由代理及零内存纯直连排障：Claude Code 强制携带 adaptive thinking 与大量 anthropic-beta 扩展参数导致第三方网关拒收；直连 Cloudflare 1010 拦截；Zed Claude ACP 弹窗 auto-mode-classifier-billing 警告；ACP v0.97.0~v0.99.0 鉴权守卫拦截仅保留 AUTH_TOKEN 导致 Zed 报 Authentication required 并在后台死锁 auth login --console 致 Authenticating to Claude Agent... 永久转圈；2026-10-29 实测确认上游已原生支持 glm-5.3-flash 与 deepseek-v4.1-flash 走 Anthropic 协议与思考块；提供摆脱 600MB CC Switch 的 Zed 零内存纯直连方案（注入安眠药凭据与出站代理）及 CC Switch 路由转译全套落地 SOP；2026-10-29 夜间再确认 `/zen/go` 旧路径对 Bearer 鉴权挑剔、官方已迁移至 `/inference/go/anthropic`，并补上 503 `Endpoint is unavailable` 的按模型归因法、`[1m]` 后缀排除法与 cc-switch `providers` + `provider_endpoints` 双表同步 SOP。
version: 1.4.0
created: 2026-10-22
updated: 2026-10-29
id: "092"
domain: agent
scope: ccswitch
type: fix
slug: "ClaudeCode升级参数冲突与OpenCode路由翻译"
status: verified
last_verified: "2026-10-29"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: true
  trigger_keywords: ["claude code 400 inference_failed", "ModelProtocolUnsupported", "Go requires a credential", "503 Upstream request failed", "Endpoint is unavailable", "Model is unavailable", "inference/go/anthropic", "zen/go 401", "opencode.ai/zen", "provider_endpoints", "endpointAutoSelect", "cc-switch 改了 settings.json 又变回去", "status.opencode.ai", "Both ANTHROPIC_AUTH_TOKEN and ANTHROPIC_API_KEY set", "Header is managed by the local proxy and cannot be overridden", "opencode glm 400", "claude code 1m 上下文", "claude code cc-switch 路由", "auto-mode-classifier-billing", "Claude reported a warning", "requests go through 127.0.0.1:15721", "Authenticating to Claude Agent...", "session account carries no identity signal", "Authentication required", "auth login --console", "claude acp 转圈", "@zed-industries/claude-code-acp", "@agentclientprotocol/claude-agent-acp", "claude acp 弃用", "claude acp 静默升级", "claude acp 零内存纯直连", "cc-switch 600mb 内存", "hide-claude-auth"]
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

### 2. OpenCode Go 网关协议分立与上游演进解除
- **历史限制（2026-10-22）**：Anthropic 协议端点（`/zen/go/v1/messages`）对 GLM 模型硬编码返回 `ModelProtocolUnsupported`，迫使用户必须开启 CC Switch 代理将流量翻译为 `/chat/completions`。
- **最新演进（2026-10-29 实测确认）**：OpenCode Go 官方已完成端点升级，Anthropic 原生端点现已**原生支持 `glm-5.3-flash` 与 `deepseek-v4.1-flash`**！直连返回 HTTP 200 且原生返回 `{"type": "thinking", ...}` 思考块。协议转译的必要性已彻底消除，具备了完全抛弃 600MB CC Switch 桌面端、实现纯直连的先决条件。
- **路径迁移（2026-10-29 夜间更正）**：官方文档现给出 `/inference/go/anthropic/v1/messages` 作为 Go 的 Anthropic 入口，旧 `/zen/go/v1/messages` 仍可用但对鉴权头挑剔（实测仅带 `Authorization: Bearer` 时偶发 `401 Go requires a credential`，带 `x-api-key` 或走新路径稳定 200）。**新配置一律写新路径**，详见 §五。

### 3. 认证标头协议对立（Bearer vs API Key）
- 旧路径 `/zen/go/v1/messages`：只认 `x-api-key`，仅带 `Bearer` 会偶发 `401 Upstream request failed: Go requires a credential`；
- 新路径 `/inference/go/anthropic/v1/messages`：`x-api-key` 与 `Authorization: Bearer` **均可**（实测两条均 200），兼容性更好；
- OpenAI 标准端点（`/chat/completions`）只认 `Authorization: Bearer <token>`，只带 `x-api-key` 会报 `Go requires a credential`；
- 此外，OpenCode 网关路由必须依赖 `x-opencode-session` 标头定位会话，缺失时报 `400 MissingSessionID`。

### 4. 本地代理与 GUI 进程出站直连陷阱（Cloudflare 1010 拦截）
无论是 CC Switch 本地代理默认直连海外，还是 Zed 作为 Windows GUI 桌面软件拉起的外部 ACP 孤儿 Node.js 进程，均**不继承终端的会话级代理环境变量**。在直连 OpenCode 海外服务器时，直接出站会被 Cloudflare WAF 识别拦截，抛出 HTTP 403 `error code: 1010`。因此必须在配置中显式注入 `HTTP_PROXY / HTTPS_PROXY` 指向本地常驻的科学上网端口（如 Clash `127.0.0.1:7897`）。

### 5. Claude Code auto 模式专属 classifier 计费协议豁免与第三方网关握手缺失
新版 Claude Code 上线了分类器免费机制（用于在 `auto` 模式下预判权限与意图分类轻量请求免计费），要求网关端点实现 `auto-mode-classifier-billing` 专属计费豁免协议。
- 当流量经过 `127.0.0.1:15721` 本地代理时，SDK 检测到非原生端点未实现该计费协议，遂抛出告知性 Warning；
- 官方明确标注 **`Nothing breaks: auto mode keeps working`**（功能完全无损，分类请求仅按普通请求计费）；
- 但对于通过 CC Switch 转接 **OpenCode（GLM / DeepSeek）** 等第三方模型体系的用户而言，Token 消耗完全走第三方计费，Anthropic 官方体系内的自营分类器免计费机制天然无关，该 Warning 仅为 UI 视觉噪音。

### 6. ACP v0.97.0~v0.99.0 鉴权守卫（`hide-claude-auth.js`）的“两头堵”神坑根因
新版 `@agentclientprotocol/claude-agent-acp`（v0.97.0 至 v0.99.0）增加了严格的单会话鉴权拦截机制（`refuseClaudeSubscriptionTurn` 与 `auth-status.js`）：
- **深层代码取证（`accountInfoHasIdentitySignal`）**：
  ```javascript
  // node_modules/@agentclientprotocol/claude-agent-acp/dist/auth-status.js
  export function accountInfoHasIdentitySignal(account) {
      if (!account) return false;
      return Boolean(account.apiKeySource ||
          account.subscriptionType ||
          (account.apiProvider && account.apiProvider !== "firstParty"));
  }
  ```
  该函数显式声明：`tokenSource is deliberately not a signal`！
- **CLI 能用而 Zed ACP 报错的反常理真相（“两头堵”）**：
  1. 为了让终端里的 `claude` CLI 正常运行且不报双键警告（现场 B），凭据必须写入 `~/.claude/settings.json` 的 `ANTHROPIC_AUTH_TOKEN`；
  2. 但 Zed 拉起 ACP 时执行 `claude auth status --json`，输出中仅包含 `authMethod: "oauth_token"`，既无 `subscriptionType`，也无 `apiKeySource`；
  3. ACP 内部判定该账户**“不携带任何身份标识”（`session account carries no identity signal`）**，在每次发送 prompt 前拦截并直接抛出 `RequestError.authRequired`；
  4. Zed 收到后自动触发 `terminal-auth` 在后台盲拉无窗口的 `claude.exe auth login --console` 挂死，导致界面永久卡在 `Authenticating to Claude Agent...` 转圈；
  5. **解法本质**：在 Zed 的 `claude-acp.env` 中显式塞入 `ANTHROPIC_API_KEY`，纯粹是作为一颗**“安眠药”**骗过守卫的本地检查，放行请求。

### 7. 实体迁移与静默升级陷阱：`@zed-industries` 弃用与 `@agentclientprotocol` 动态静默更新
- **包名变迁与假性停更陷阱（Anti-Pattern）**：
  - 早期历史包：`@zed-industries/claude-code-acp` 已于 2026 年 2 月被官方正式废弃，npm 显式声明：`"This package has been renamed to @agentclientprotocol/claude-agent-acp. Please migrate to continue receiving updates."`，版本永久停留在 `v0.16.2`；
  - 官方现役包：**`@agentclientprotocol/claude-agent-acp`**（由 Anthropic、Zed Industries 与 JetBrains 联合成立的 Agent Client Protocol 组织共同维护），版本已演进至 `v0.99.0`；
  - **AI 查错包警示**：排查时若仅按历史经验检索 `@zed-industries/claude-code-acp`，会误得出“该包停留在 2 月份已数月未维护”的严重假象。
- **Zed Registry 动态静默 Hydrate 机制与 npm 挂死**：
  - Zed 的外部 Agent（`type: "registry"`）通过内置注册表与 `npx` 机制动态解析远端最新版本（`"@agentclientprotocol/claude-agent-acp@0.0.0 - 0.99.0"`）；
  - 2026-10-28 23:23 UTC 宿主自动拉取覆盖，冷启动时后台 npm 进程易因代理或网络震荡挂起（如 PID 24532 挂死超 40 分钟）；
  - 这种“远端日更 + 宿主静默 Hydrate”机制解释了为什么原本正常的配置会在一夜之间突发鉴权拦截死锁（Zero-action Regression）。
  - **AI 查错包警示**：排查时若仅按历史经验检索 `@zed-industries/claude-code-acp`，会误得出“该包停留在 2 月份已数月未维护”的严重假象。
- **Zed Registry 动态静默 Hydrate 机制（零操作暴雷归因）**：
  - Zed 的外部 Agent（`type: "registry"`）通过内置注册表与 `npx` 机制动态解析远端最新版本；
  - 2026-10-26 12:48 UTC 上游刚发布 `v0.97.0`，用户次日冷启动 Zed 时被自动拉取覆盖，无需任何显式升级命令；
  - 这种“远端日更 + 宿主静默 Hydrate”机制解释了为什么原本正常的配置会在一夜之间突发鉴权拦截死锁（Zero-action Regression）。

---

## 三、标准解决与修复 SOP

### 方案 A：Zed 零内存纯直连架构（2026-10-29 推荐首选，0 额外常驻进程）

> 💡 **架构设计思想**：  
> 随着上游 OpenCode Go 原生支持 GLM/DeepSeek 走 Anthropic 协议，原 CC Switch 代理层的 `openai_chat` 转译已无必要。由于 CC Switch 为 Electron 桌面应用，闲置常驻内存高达 **300~600MB**；采用纯直连方案可直接将额外内存与后台常驻进程归零，同时一劳永逸解除 ACP 鉴权守卫。

#### 步骤 A1：清理后台挂起与孤儿进程（防锁死）
```powershell
# 终止长时挂起的 npm 安装进程（如 PID 24532）与无窗口死锁的 auth login
Get-Process | Where-Object { $_.ProcessName -in 'claude', 'node' -and ($_.CommandLine -like '*claude-agent-acp*' -or $_.CommandLine -like '*login*') } | Stop-Process -Force -ErrorAction SilentlyContinue
```

#### 步骤 A2：在 Zed 配置文件中注入直连环境与安眠药凭据
备份并编辑 `%APPDATA%\Zed\settings.json`，在 `agent_servers.claude-acp` 中显式配置：
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
    "ANTHROPIC_BASE_URL": "https://opencode.ai/inference/go/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "oc_sk_xxx（本机凭据，勿入库）",
    "ANTHROPIC_API_KEY": "oc_sk_xxx（安眠药凭据，与 AUTH_TOKEN 同值）",
    "HTTP_PROXY": "http://127.0.0.1:7897",
    "HTTPS_PROXY": "http://127.0.0.1:7897"
  }
}
```
- **配置攻防精义**：
  1. `ANTHROPIC_BASE_URL`：直连 OpenCode Go 官方网关，零中间跳点；
  2. `ANTHROPIC_API_KEY`：专用于向 ACP v0.99.0 的 `hide-claude-auth.js` 守卫提供 `account.apiKeySource`，直接使 `holdsNonSubscriptionCredential` 返回 `true`，阻止其触发无窗口 `auth login --console` 挂死（安眠药凭据）；
  3. `HTTP_PROXY / HTTPS_PROXY`：补偿 Windows GUI 进程不继承终端环境变量的缺陷，使子进程请求准确经由本地 Clash（7897）出站，彻底规避 Cloudflare 1010 WAF 拦截。

#### 步骤 A3：对齐 CLI 客户端配置 (`~/.claude/settings.json`)
确保终端 `claude` 命令同样直连且不触发双键警告：
```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://opencode.ai/inference/go/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "oc_sk_xxx（本机凭据，勿入库）",
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

#### 步骤 A4：同步回写 CC Switch 数据库解除协议转译
若本机曾配置过 CC Switch，通过配套脚本更新 meta，将 `apiFormat` 从 `openai_chat` 改回原生 `anthropic`：
```powershell
node "C:\Users\29580\.agents\skills\kb-engineering-notes\scripts\cc-update-meta.mjs" --app claude --id <opencode-go-provider-id> --meta meta_anthropic.json --apply
```

---

### 方案 B：CC Switch 路由代理转译模式（历史兼容 / 需协议转译场景备选）

> 当未来某天上游再次发生协议代沟、或必须由本地代理强制剥离 Claude Code 某些专有扩展参数时使用。

#### 步骤 B1：整库备份（原则先行）
```powershell
node "D:\Users\study_projects\older\.agents\skills\sh-cc-switch-db\scripts\cc-db.mjs" backup
```

#### 步骤 B2：配置 CC Switch 全局上游代理（破除 1010 拦截）
退出 CC Switch 进程（`Stop-Process -Name cc-switch -Force`），在 `~/.cc-switch/cc-switch.db` 的 `settings` 表中插入上游科学上网代理：
```sql
INSERT OR REPLACE INTO settings (key, value) VALUES ('global_proxy_url', 'http://127.0.0.1:7897');
```

#### 步骤 B3：开启本地代理协议翻译（`openai_chat`）
将 OpenCode Go 供应商的 `meta.apiFormat` 从 `anthropic` 改为 `openai_chat`。此模式下代理层自动转换 `/chat/completions`。

#### 步骤 B4：配置鉴权头与 Session 标头覆盖
在供应商的 `meta.localProxyRequestOverrides` 中注入：
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

#### 步骤 B5：同步客户端指向本地代理端口
更新 `~/.claude/settings.json`：
```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:15721",
    "ANTHROPIC_AUTH_TOKEN": "PROXY_MANAGED"
  }
}
```

#### 步骤 B6：Zed 注入本地代理与伪装凭据
在 `%APPDATA%\Zed\settings.json` 中配置：
```json
"claude-acp": {
  "type": "registry",
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:15721",
    "ANTHROPIC_API_KEY": "sk-ccswitch-dummy"
  }
}
```

---

## 四、验证与防复发闭环

### 1. 直连端点能力验证（零代理）
通过 Clash 代理直接调用 OpenCode Anthropic 端点验证原生思考返回：
```python
import urllib.request, json
opener = urllib.request.build_opener(urllib.request.ProxyHandler({'http': 'http://127.0.0.1:7897', 'https': 'http://127.0.0.1:7897'}))
headers = {
    "x-api-key": "oc_sk_...",
    "anthropic-version": "2023-06-01",
    "content-type": "application/json",
    "User-Agent": "Claude-Code/2.1.303 (Windows NT 10.0; Win64; x64)",
    "x-opencode-session": "claude-code-session"
}
req = urllib.request.Request("https://opencode.ai/inference/go/anthropic/v1/messages", data=json.dumps({
    "model": "glm-5.3-flash", "max_tokens": 50, "messages": [{"role": "user", "content": "hi"}]
}).encode("utf-8"), headers=headers, method="POST")
with opener.open(req) as resp:
    print(resp.status, resp.read().decode("utf-8"))
```
**断言**：返回 `Status: 200`，输出中包含 `{"type":"thinking", ...}`。

### 2. 严格配置写后必检（Post-Write Invariant）
- 检查 `%APPDATA%\Zed\settings.json` 前 3 字节绝不含 `EF BB BF`（BOM）；
- 执行 JSON/JSONC 语法解析器确认无语法硬伤。

### 3. Zed Claude ACP 零卡死就绪断言
1. 重启 Zed 编辑器；
2. 打开 Agent 面板切换到 Claude Agent；
3. 底部 `Authenticating to Claude Agent...` 在 1 秒内消失，直接呈现可输入就绪状态；
4. 任务管理器确认无残留的 `claude.exe auth login` 孤儿进程，且 **CC Switch 未启动，系统无任何 600MB 冗余内存常驻**。

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

---

## 五、2026-10-29 夜间增补：`503 Endpoint is unavailable` 归因与 Go 端点迁移（cc-switch 双表同步）

> **触发场景**：Zed Claude Agent 报
> `API Error: 503 Upstream request failed: Endpoint is unavailable. This is a server-side issue, usually temporary — try again in a moment. If it persists, check your inference gateway (opencode.ai).`
> 用户以为"配置坏了/账号挂了"，反复换 key、重装客户端，实际是**单模型上游端点瞬时不可用**。

### 5.1 现场取证：不是整站故障，也不是账号故障

`%LOCALAPPDATA%\Zed\logs\Zed.log`：

```text
2026-10-29T01:49:24+08:00 ERROR [acp_thread] Error in run turn: Internal error: API Error: 503 Upstream request failed: Endpoint is unavailable...
  "errorKind": "server_error"
2026-10-29T01:55:04+08:00  （同一错误）
2026-10-29T02:02:39+08:00  （同一错误）
```

- 三次间隔 ≈ 6~7 分钟 = **手动重试节奏**，说明是持续十几分钟的窗口，不是单次抖动；
- **同一分钟**用 opencode CLI（`opencode-go/deepseek-v4.1-flash`）跑同一账号，`~/.local/share/opencode/log/opencode.log` 上游错误计数为 **0**；
- 结论：网关按 **模型/上游** 粒度降级，DeepSeek 那路正常、GLM 那路当时不可用。

### 5.2 同一网关的五类错误（混治必翻车）

| 报错文本 | HTTP | 归因 | 处置 |
|:---|:---:|:---|:---|
| `Upstream request failed: Endpoint is unavailable.` | 503 | 该模型的上游端点瞬时摘除/不可达 | 重试；连撞两次直接换模型（不同模型走不同上游） |
| `Upstream request failed: Model is unavailable.` | 400 | 模型 ID 不存在/未开通（含 `xxx[1m]` 这类非法后缀） | 改模型名，别改 key |
| `Upstream request failed: Go requires a credential` | 401 | 鉴权头与路径不匹配（`/zen/go` 只认 `x-api-key`；`/chat/completions` 只认 `Bearer`） | 补齐对应头，或迁到 `/inference/go/anthropic` |
| `{"type":"error","error":{"type":"MissingSessionID"...}}` | 400 | 缺 `x-opencode-session` | 补会话头 |
| `[ttft_admission_refused] the cell is at capacity; retry shortly (after 8 s)` | 503 | 网关容量准入拒绝（限流） | 等 8s+ 重试 |
| `Model access is disabled` | 403 | 工作区隐私/区域策略未授权（如 DeepSeek 需在 Settings›Privacy 选 Global） | 去 Console 改隐私设置 |

> 记忆锚点：**503 = 上游端点；400 = 你的参数；401 = 你的头；403 = 你的权限**。

### 5.3 30 秒归因法（三步对照，不猜）

1. **看官方状态页的模型粒度**（`incidents[].models` 直接写是哪个模型挂了）：
   ```python
   import json, urllib.request
   d = json.load(urllib.request.urlopen("https://status.opencode.ai/api/status", timeout=20))
   for i in d["incidents"][:10]:
       print(i["service"], i["status"], i["reason"], i["models"])
   ```
2. **同 key / 同模型，两条路径 × 两种鉴权头做矩阵**（见 5.4 脚本骨架，断言只看状态码）；
3. **同分钟换一个 provider 对照**（`opencode run -m opencode-go/deepseek-v4.1-flash "只回复 OK"`），用来区分"网关全挂"与"单模型挂"。

### 5.4 修复 SOP：cc-switch 必须改"双表"，否则白改

**权威源是 DB，不是 `~/.claude/settings.json`**（后者是切换 provider 时生成的产物）：

| 表/字段 | 作用 | 不改的后果 |
|:---|:---|:---|
| `providers.settings_config` | 切换 provider 时整体写回 `~/.claude/settings.json` | 改完实文件，下次切换即回滚 |
| `provider_endpoints.url` | 端点自动选择（`meta.endpointAutoSelect=true`） | 自动选回旧 `/zen/go`，表现为"改了又变回去" |

```python
# 骨架：备份 → 双表 UPDATE → 同步实文件 → 自检（token 只在内存，不打印）
import json, shutil, sqlite3, os, pathlib
db = pathlib.Path(os.path.expanduser("~/.cc-switch/cc-switch.db"))
shutil.copy2(db, db.with_name(f"backups/db_backup_{...}.db"))   # 先备份
con = sqlite3.connect(db, timeout=10)
with con:
    cfg = con.execute("select settings_config from providers where id=? and app_type='claude'",
                      (PROVIDER_ID,)).fetchone()[0]
    new = cfg.replace("https://opencode.ai/zen/go",
                      "https://opencode.ai/inference/go/anthropic")
    assert json.loads(new)["env"]["ANTHROPIC_AUTH_TOKEN"]          # token 未被破坏
    con.execute("update providers set settings_config=? where id=? and app_type='claude'", (new, PROVIDER_ID))
    con.execute("update provider_endpoints set url=? where provider_id=? and app_type='claude'",
                ("https://opencode.ai/inference/go/anthropic", PROVIDER_ID))
con.close()
```

配套注意：
- **必须先确认 cc-switch 未运行**，再写 DB（`sqlite3.connect(..., timeout=2)` 试写事务，失败即中止）；
- 实文件 `~/.claude/settings.json`、`%APPDATA%\Zed\settings.json` 的 `claude-acp.env` 三处 base URL 必须一致；
- Zed 侧保留 `ANTHROPIC_API_KEY` 作为 ACP 鉴权守卫的"安眠药"（见 §二.6），但**值必须与 AUTH_TOKEN 相同**，且不要额外制造双键告警；
- 改完 **重启 Zed**：ACP 子进程只在启动时读 `env`，热改无效。

### 5.5 排除法：`[1m]` 后缀不背 503 的锅

`ANTHROPIC_DEFAULT_SONNET_MODEL: "glm-5.3-flash[1m]"` 看似可疑，实测**无害**：Claude Code 会在发送前把它拆成模型名 + beta 头。用本地假端点抓真实请求即可验证（隔离 `CLAUDE_CONFIG_DIR`，不动用户配置）：

```python
# HTTPServer 收到 POST 后打印 payload["model"] 与 anthropic-beta 头，再回一个最小 message JSON
# 关键断言（2026-10-29 实测）：
#   model=glm-5.3-flash
#   anthropic-beta=...,context-1m-2025-08-07,...
```

即：`[1m]` 只是客户端语法，网关永远不会见到这个后缀；它最多在 stderr 留一条 `[claude-code:unrecognized_model]` 警告。**看到这条警告就去改别名 = 治错了病。**

### 5.6 验证与防复发

1. **矩阵断言**（全部 200 才算通）：`/inference/go/anthropic` × {`x-api-key`, `Bearer`} × `glm-5.3-flash`，含 `stream:true` 时首包 <3s；
2. **对照断言**：`/zen/go` 只带 Bearer 若返回 401 `Go requires a credential`，说明仍在旧路径，按 5.4 迁移；
3. **一致性断言**：DB `settings_config` / DB `provider_endpoints` / `~/.claude/settings.json` / Zed `claude-acp.env` 四处 base URL 完全相同；
4. **时间窗对齐**：把 `Zed.log` 的报错时间换算成 UTC，去 `status.opencode.ai` 对 incident（页面按 UTC 展示），能直接判定"平台事故"还是"本地配置"；
5. **凭据红线**：本条目及任何知识库文件禁止落明文 token；排障脚本一律"读文件→内存持有→不打印"。

