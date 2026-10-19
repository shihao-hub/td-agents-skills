---
name: kb-pi-acp-openma-inprocess
description: |
  解决 Zed 编辑器使用官方 Registry 的 svkozak/pi-acp 桥接难用、卡顿挂起、事件丢失与 pi.cmd 管道断开问题。通过 openma-ai/pi-acp 实现 In-Process SDK 内存直载，并规避 Windows Defender 对未签名 exe 垫片的启发式扫描，零转接损耗无缝接入原版 Pi。
version: 1.1.0
created: 2026-10-19
updated: 2026-10-19
---

# Zed 集成 Pi Coding Agent 双层管道难用排障与 openma-pi-acp 内存直载 SOP

## 1. 现象与报错特征

### 典型痛点现象
1. **输入与响应卡顿挂起**：在 Zed 的 Agent 面板向 Pi 提问时，界面长时间无响应或流式输出中断，后台进程挂死。
2. **取消（Stop）信号丢失**：在 Zed 中点击中断当前轮次，前端看似停止，但底层 `pi.cmd` 仍在后台疯狂占用 CPU 和 Token，无法及时阻断。
3. **思考链与消息混杂**：模型推理（Thought/Reasoning）无法作为独立流显示，常常混进最终输出中。
4. **Windows Defender 实时扫描风暴**：
   - 任务管理器中 `Microsoft Defender Antimalware Service`（`MsMpEng.exe`）CPU 突增至 60%~70%，磁盘读取飙升。
   - 事件查看器记录事件 ID 2010（安全智能更新 / 启发式分析扫描）。
5. **Windows 路径与命令报错**：
   - `pi runtime is too old for pi-acp`
   - `spawn C:\Users\...\.pi\agent\bin\pi.cmd ENOENT / EPERM`
   - 依赖复杂的 `PI_ACP_PI_COMMAND` 环境变量修补。

---

## 2. 根因剖析（Root Cause）

### 2.1 架构阻抗失配：双层 stdio 子进程管道
Zed 官方 Registry 默认收录的 `svkozak/pi-acp` 是一个外部中继桥：
```text
【旧版 svkozak/pi-acp（双层转接）】
Zed Editor (ACP Client)
     ↕ [stdio 管道 1 (JSON-RPC 2.0)]
pi-acp 桥接进程 (Node.js)
     ↕ [stdio 管道 2 (子进程调用 pi.cmd --mode rpc)]
原版 pi 核心进程 (Mario Zechner / earendil-works/pi)
```
- **Windows stdio 极其脆弱**：Windows 上批处理包装（`.cmd`）经由双层管道转发时，极易因缓冲区满或 EOF 截断导致静默死锁。
- **取消信号无法传透**：ACP 的 `session/cancel` 信号在桥接层丢失，无法跨管道送达 `pi --mode rpc`。

### 2.2 为什么不是 oh-my-pi (omp)？
- `omp` 虽然自带原生 ACP，但它是 Pi 的重量级独立 Fork（重构了 AST 编辑、集成了 LSP/DAP），带来了多余工具链和额外的心智负担。

### 2.3 最优解：openma-ai/pi-acp（In-Process 内存直载）
`openma-ai/pi-acp`（npm: `@openma/pi-acp`）去除了底层的第二层子进程：
```text
【新版 openma-ai/pi-acp（内存直载）】
Zed Editor (ACP Client)
     ↕ [单层 stdio 管道 (JSON-RPC 2.0)]
[ openma-pi-acp 适配器进程 ]
     └── 直接在 Node.js 内存中调用 @earendil-works/pi-coding-agent SDK
```
- **零子进程、零管道开销**：所有事件直接是内存中的 JavaScript 函数回调，响应速度极快，彻底消除了 Windows 下管道断裂问题。
- **100% 原版 Pi 基因**：原生复用 `~/.pi/agent`（配置、密钥、扩展、会话完全一致），心智负担为 0。

### 2.4 Windows 踩坑：未签名 .exe 垫片引发 Defender 拦截
- 若直接在 Zed 中配置 `openma-pi-acp.exe`（由 Bun/pkg 编译的无签名垫片），Zed 启动时会走：
  `Zed.exe -> powershell.exe -C "openma-pi-acp.exe" -> openma-pi-acp.exe -> node.exe`
- 这种未签名二进制 + 深度嵌套进程链直接命中 Windows Defender 的高危行为规则，导致 `MsMpEng.exe` 频繁上报云端安全智能并在本地深度扫描，引发短时间高 CPU 挂死。
- **解法**：在 Zed 中**直接以官方签名的 `node.exe` 启动目标 `bin.js`**，彻底规避垫片。

---

## 3. 确定性配置与落地 SOP

### 步骤 1：安装 In-Process 适配器
推荐使用 Bun 或全局 npm 安装：
```powershell
# 通过 bun 全局安装
bun install -g @openma/pi-acp

# 或通过 npm 全局安装
npm install -g @openma/pi-acp
```

### 步骤 2：在 Zed settings.json 中配置直连 node
打开 Zed 配置文件（`%APPDATA%\Zed\settings.json`），在 `agent_servers` 下新增独立条目（**切记使用 `node` 直接指向 `dist/bin.js`，避免无签名 exe 触发杀毒扫描**）：

```json
"agent_servers": {
  "openma-pi": {
    "type": "custom",
    "command": "node",
    "args": [
      "C:/Users/29580/.bun/install/global/node_modules/@openma/pi-acp/dist/bin.js"
    ],
    "env": {}
  }
}
```
> **注意（关于代理）**：除非模型网关必须走特定本地代理，否则**不要**在 `env` 中硬编码 `HTTP_PROXY` / `HTTPS_PROXY`，避免直连国内模型时出现 `ECONNREFUSED` 或绕道延迟。

### 步骤 3：验证与会话单例表现
1. **多会话单例（同窗口多路复用）**：
   - 在同一个 Zed 工程窗口内开启多个对话 Tab，底层只会常驻**1 个 Node 进程**（`openma-ai/pi-acp` 内部维护 `Map<sessionId, SessionHandler>`），内存占用仅约 40~60MB。
2. **进程与 CPU 校验**：
   - 提问测试，观察任务管理器中 Node 进程平稳运行，`MsMpEng.exe` 不再狂飙，流式与取消中断均秒级响应。