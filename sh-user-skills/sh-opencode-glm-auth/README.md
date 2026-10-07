---
name: sh-opencode-glm-auth
description: 排障：opencode 连 GLM 报 401/身份验证失败；apiKey 优先级、双端点 key 矩阵。点名使用
---

# Skill: sh-opencode-glm-auth（opencode GLM 身份验证失败排查）

沉淀自 2026-09-11 实操（opencode 1.18.x，Windows，zhipuai-coding-plan 内置供应商 + zhipu-glm 自定义供应商，key 经 curl 实测可用但 opencode 内报"身份验证失败"）。核心教训：**opencode 实际发出的 key 未必是你以为的那个**。

## 核心结论（先背下来）

### 1. Key 生效优先级（实测）

内置供应商（如 zhipuai-coding-plan）的 key 有三处来源，优先级从高到低：

1. `~/.config/opencode/opencode.json` 的 `provider.<id>.options.apiKey` ← **最高，会静默覆盖下面两处**
2. `~/.local/share/opencode/auth.json`（`opencode auth login` 写入）
3. 环境变量 `ZHIPU_API_KEY`（models.dev 里 zhipuai-coding-plan 声明的 env 兜底，查 User/Machine/Process 三作用域）

推论：**auth login 后仍 401，九成是 opencode.json 里躺着一个死 key 在覆盖**。
自定义供应商（npm: @ai-sdk/openai-compatible 那种）只认自己 options 里的 apiKey，不吃 auth.json。

### 2. bigmodel.cn 双端点，key×端点要配对

| 端点 | 用途 | 混用表现 |
|---|---|---|
| `https://open.bigmodel.cn/api/coding/paas/v4` | 编码套餐（GLM Coding Plan） | 实测普通 key 也能调通 |
| `https://open.bigmodel.cn/api/paas/v4` | 标准按量计费 | 套餐/普通 key 不匹配时报 429 code 1113 "余额不足或无可用资源包" |

401 报文长这样：`{"error":{"code":"1000","message":"身份验证失败。"}}`——与 opencode 界面里的"身份验证失败"同源。

### 3. 配置只在启动时加载

改完 opencode.json / auth.json **必须重启 opencode**。运行中的实例持有内存态 key，修了凭证照样报错。同一日志文件里同一个 run 前后表现不同 = 中途改过凭证或切过供应商。

## 排查流程

### 第一步：日志定位是谁在报错

日志：`~\.local\share\opencode\log\opencode.log`（同目录还有按日期滚动的旧文件）。

```powershell
# 最近错误（中文消息在 PS 输出里是 GBK 乱码，"身份验证失败"会显示成乱码，属正常）
Select-String -Path "$env:USERPROFILE\.local\share\opencode\log\opencode.log" -Pattern 'level=ERROR' |
  Select-Object -Last 10 | ForEach-Object { $_.Line.Substring(0, [Math]::Min(320, $_.Line.Length)) }
```

每行错误带 `providerID=xxx modelID=xxx run=xxx`：
- **providerID 分清是 `zhipuai-coding-plan`（内置）还是 `zhipu-glm`（自定义）**——两者 key 来源不同，修法不同
- `run=` 是进程实例 ID，可判断报错的是不是同一个 opencode 窗口、何时启动的（搜 `run=<id>` 的 bootstrapping 行）

### 第二步：列出所有 key 来源，找出实际生效的那个

```powershell
# 三作用域环境变量
"User: [$([Environment]::GetEnvironmentVariable('ZHIPU_API_KEY','User'))]"
"Machine: [$([Environment]::GetEnvironmentVariable('ZHIPU_API_KEY','Machine'))]"
```

再读两处文件：`opencode.json` 的 provider 段、`auth.json`。三处的 key 逐个核对，不一致就是线索。auth.json 的 LastWriteTime 对照日志报错时间线，能还原"何时谁改过凭证"。

### 第三步：curl 实测 key×端点矩阵（判断 key 本身死活）

**PowerShell 5.1 两个坑**：`curl` 是 Invoke-WebRequest 的别名必须用 `curl.exe`；`-d` 内联 JSON 的反斜杠转义会被吃掉（服务端报 Jackson JSON parse error），**body 先写临时文件再 `--data "@file"`**：

```powershell
Set-Content -Path "$env:TEMP\body.json" -Value '{"model":"glm-5.3","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'
curl.exe -s -w "`nHTTP:%{http_code}" -X POST "https://open.bigmodel.cn/api/coding/paas/v4/chat/completions" `
  -H "Authorization: Bearer <待测key>" -H "Content-Type: application/json" --data "@$env:TEMP\body.json"
```

- 200 → key 是通的，问题在 opencode 的 key 选择/优先级（回第一、二步）
- 401 code 1000 → key 本身死了，换 key
- 429 code 1113 → key 活着但端点不匹配（标准端点没余额），换 coding 端点

### 第四步：修复

- 改 `opencode.json` 里对应 provider 的 `options.apiKey`（对内置供应商，这处优先级最高，改这里最彻底）
- 或 `opencode auth login` → 选供应商 → API Key → 粘贴（只动 auth.json，可能被配置文件覆盖）
- **重启 opencode**
- 供应商 key 处理完后，按下一节检查 MCP 里是否也埋着同一个死 key

## 别漏了 MCP 里的同款死 key（隐藏雷区）

opencode.json 的 `mcp` 段里，key 以两种形式存在：

- **远程 MCP**（`type: "remote"`）：`headers.Authorization: "Bearer <key>"`
- **本地 MCP**（`type: "local"`）：`environment` 里的 `Z_AI_API_KEY` 之类变量

换/删供应商 key 时这些不会跟着更新。它们失效时不报"身份验证失败"，而是 MCP server 连接失败、工具列表加载不出来或调用报错——症状隐蔽，容易被当成网络问题。实测 2026-09-11 事件中 4 个 MCP（web-reader、web-search-prime、zai-mcp-server、zread）全在用死 key。

处理方式二选一：

```jsonc
// 方式一：key 还有用 → 只替换 mcp 段里的 key（headers 和 environment 两处都要看）
// 方式二：MCP 不要了 → 整块删除 "mcp": { ... }，注意别破坏 JSON 结构
```

删完**必须读回文件校验 JSON 完整性**（括号/逗号），再重启 opencode。MCP 工具在会话启动时加载，正在运行的会话里已加载的 MCP 工具要重启后才消失。

## 快速判例表

| 现象 | 根因 | 修法 |
|---|---|---|
| curl 通、opencode 401 | opencode.json options.apiKey 死 key 覆盖 auth.json | 改 options.apiKey，重启 |
| auth login 后仍 401 | 同上（login 只写 auth.json，被覆盖） | 同上 |
| 某窗口一直 401、其他窗口正常 | 该实例启动时加载了旧凭证 | 重启那个窗口 |
| 401 + "key 是通的" | 先怀疑优先级，再怀疑端点配对 | 走第三步矩阵实测 |
| 429 "余额不足" | key 打到了标准端点 | 换 coding 端点或充值标准计费 |
| 模型列表里 "GLM-5.3 Zhipu AI Coding Plan" 报错 | 内置 zhipuai-coding-plan 供应商认证问题 | 本 skill 全流程 |
| 修完 key 后 MCP 工具连不上/不出现 | mcp 段 headers/environment 里还埋着死 key | 换 key 或删 mcp 块，校验 JSON 后重启 |
