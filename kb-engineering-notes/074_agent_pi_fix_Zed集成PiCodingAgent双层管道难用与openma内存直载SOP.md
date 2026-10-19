---
name: kb-pi-acp-openma-inprocess
description: |
  解决 Zed 编辑器使用官方 Registry 的 svkozak/pi-acp 桥接难用、卡顿挂起、事件丢失与 pi.cmd 管道断开问题。通过 openma-ai/pi-acp 实现 In-Process SDK 内存直载，并规避 Bun 未签名 exe 启动器垫片引发 Windows Defender 实时拦截与 CPU/内存暴涨，零转接损耗无缝接入原版 Pi。
version: 1.3.0
created: 2026-10-19
updated: 2026-10-19
---

# Zed 集成 Pi Coding Agent 双层管道难用排障与 openma-pi-acp 内存直载 SOP

> **关联条目**：本条目只解决「能不能顺畅跑起来」；线程标题恒为「New Agent Thread」、启动横幅与自动命名的关系、以及 agent 侧命名插件 `auto-session-title`，见 `077_ide_zed_fix_Zed外部ACP线程不自动命名与首消息标题链路.md`。

## 1. 现象与报错特征

### 典型痛点现象
1. **输入与响应卡顿挂起**：在 Zed 的 Agent 面板向 Pi 提问时，界面长时间无响应或流式输出中断，后台进程挂死。
2. **取消（Stop）信号丢失**：在 Zed 中点击中断当前轮次，前端看似停止，但底层 `pi.cmd` 仍在后台疯狂占用 CPU 和 Token，无法及时阻断。
3. **思考链与消息混杂**：模型推理（Thought/Reasoning）无法作为独立流显示，常常混进最终输出中。
4. **Windows Defender 实时扫描风暴（核心性能暗税）**：
   - 任务管理器中 `Microsoft Defender Antimalware Service`（`MsMpEng.exe`）CPU 突增至 68%~70%，磁盘吞吐达 20MB/s+，甚至驻留内存飙升到 3.6GB。
   - 事件查看器记录事件 ID 2010（安全智能更新 / 启发式分析扫描）。
   - 只要在 Zed 敲字、发起对话或切 Tab，整机风扇狂转、系统瞬间卡顿。
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

### 2.4 底层踩坑：Bun 垫片 .exe 与 Node.js 直跑的实质差异与资源影响

很多开发者误以为“包管理工具生成了 `.exe`，直接填 `.exe` 肯定最快”。但在 Windows + IDE 场景下，这正是引发 Defender 狂飙的元凶：

| 对比维度 | Bun 生成的 `.exe` 垫片（Trampoline） | 直接使用 `node.exe dist/bin.js`（最优解） |
| :--- | :--- | :--- |
| **底层本质** | 本地编译的无数字签名 C++ 跳板二进制 | 系统官方安装、带微软信任签名的真实 Node 解释器 |
| **进程调用链** | `Zed -> powershell -> openma-pi-acp.exe -> node`（4层套娃） | `Zed -> node.exe`（单层直达，极简） |
| **内存与常驻** | 额外占用一个几 MB 的裸 exe 进程常驻后台 | 仅一个 Node 进程（40~50MB），零冗余 |
| **Defender 行为** | 判定为未知裸 exe 高频读写 stdio，触发最高级启发式监控（CPU 飙至 70%） | 官方已知可信进程白名单，I/O 完全免检，CPU 瞬间归零（<1%） |
| **管道稳定性** | 垫片转发 stdio，高频下偶尔缓冲截断死锁 | 零垫片转接，原生 IPC 管道 |

> **关于 Defender 内存驻留缓存机制（Working Set Retention）**：
> 杀毒软件在扫描峰值过后，CPU 会迅速回落（0%~4%），但内存可能依然显示几 GB。这是 Defender 保护机制中的特征库缓存常驻，并不会持续吃 CPU，系统内存紧张时会自动回收，无需恐慌。

---

## 3. 确定性配置与落地 SOP

### 步骤 1：安装 In-Process 适配器
推荐使用 Bun 或全局 npm 下载依赖包：
```powershell
# 通过 bun 全局安装（仅用于获取 node_modules）
bun install -g @openma/pi-acp

# 或通过 npm 全局安装
npm install -g @openma/pi-acp
```

### 步骤 2：彻底清理无用的垫片二进制（防杀毒误抓）
如果之前使用了 bun，请直接删除 `bin` 目录下的无签名 `.exe` 垫片，避免后台留存暗税：
```powershell
Remove-Item "$HOME\.bun\bin\openma-pi-acp*" -Force -ErrorAction SilentlyContinue
```

### 步骤 3：在 Zed settings.json 中配置直连 node
打开 Zed 配置文件（`%APPDATA%\Zed\settings.json`），在 `agent_servers` 下新增独立条目（**切记使用 `node` 直接指向 `dist/bin.js`**）：

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
> **注意（关于网络代理）**：除非模型网关必须走特定本地代理，否则**不要**在 `env` 中硬编码 `HTTP_PROXY: 7897`，避免直连国内模型（如 DeepSeek / OpenCode-Go）在代理断开时报 `ECONNREFUSED` 或产生无谓延迟。

### 步骤 4：验证与会话多路复用表现
1. **多会话单例（同窗口多路复用）**：
   - 在同一个 Zed 工程窗口内开启多个对话 Tab，底层只会常驻**1 个 Node 进程**（`openma-ai/pi-acp` 内部通过 `Map<sessionId, SessionHandler>` 管理会话），内存仅约 40~50MB。
2. **CPU 与进程审计**：
   - 提问测试，观察任务管理器中 Node 进程平稳运行，`MsMpEng.exe` 不再狂飙，流式与取消中断均秒级响应。