---
name: sh-windows-agent-shell
description: 配置：Windows 多 Agent（Codex/Claude/OpenCode/Pi/AGY）终端机制与 Git Bash 切换。点名使用
---

# Windows 多 Agent 终端机制与 Git Bash 切换手册

本手册沉淀自 2026-09-24 对 Windows 下主流 AI 编程助手（pi、Claude Code、OpenCode、Codex、Antigravity/agy）终端机制的逆向探测与实测排障。用于指导在 Windows 宿主下排查各 Agent 的默认终端（Shell）类型，以及将终端环境规范统一为 Git Bash（MSYS2）的 SOP。

---

## 零、致命暗坑：WSL bash 劫持（必须先读）

在 Windows 系统中，直接在命令行中运行 `bash` 或依赖 PATH 探测 `bash.exe`，极大概率会优先命中：
`C:\Windows\System32\bash.exe`（Windows 自带的 WSL 启动转发 stub）。

若 WSL 未配置或子系统内部无 bash，会直接报底层错误：
```text
<3>WSL (11 - Relay) ERROR: CreateProcessCommon:798: execvpe(/bin/bash) failed: No such file or directory
```

**铁律**：凡是调用 Git Bash，**一律使用探测到的绝对路径**，不可仅写 `bash`。
* 本机 Git Bash 标准路径：`D:/Program Files/Git/bin/bash.exe`（或随机器检测）
* PowerShell 动态安全探测一行命令：
  ```powershell
  $bash = (Get-Command git -ErrorAction SilentlyContinue).Source -replace '\\cmd\\git\.exe$','\bin\bash.exe'
  if (-not (Test-Path $bash)) { $bash = "$env:ProgramFiles\Git\bin\bash.exe" }
  ```

---

## 一、五大 Agent 默认终端与支持矩阵

| Agent | 界面交互终端 | 后台 Agent 自动化执行终端 | 能否完全统一为 Git Bash？ | 核心底层机制 |
| :--- | :--- | :--- | :---: | :--- |
| **pi** | Git Bash | **Git Bash** | ✅ **天然是** | 源码写死探测 `%ProgramFiles%\Git\bin\bash.exe`，直接以 `bash -c` 执行 |
| **Claude Code** | Git Bash | **Git Bash** | ✅ **天然是** | 官方核心工具仅设计为 `Bash`，Windows 强制依赖并挂载 Git Bash/MSYS2 快照 |
| **OpenCode** | PowerShell | **PowerShell** | ✅ **原生配置支持** | `opencode.json` 原生提供 `shell` 字段，填绝对路径即可一键切换 |
| **Codex** | **Git Bash** (已支持) | **PowerShell** (硬编码) | ⚠️ **仅界面可改** | 桌面端支持 `integratedTerminalShell`；但后台 Agent 沙箱硬编码 Rust 原生 PowerShell 管道 |
| **Antigravity** | PowerShell | **PowerShell** (宿主绑定) | ⚠️ **仅界面可改** | IDE 基于 VS Code 可配终端 Profile；底层 Agent 任务调度与信号绑定在 PowerShell 宿主 |

---

## 二、各 Agent 配置与切换 SOP

### 1. OpenCode (`opencode-ai`)
OpenCode 在 Windows 下未声明 `shell` 时，会自动探测并回退到 `pwsh.exe` 或 `powershell.exe`。

**切换步骤**：
1. 编辑配置文件 `~/.config/opencode/opencode.json`（Windows 路径 `C:/Users/<User>/.config/opencode/opencode.json`）。
2. 在根对象中加入 `shell` 字段，必须填 Git Bash 绝对路径（用正斜杠或转义双反斜杠）：
   ```json
   {
     "$schema": "https://opencode.ai/config.json",
     "shell": "D:/Program Files/Git/bin/bash.exe",
     "mcp": { ... }
   }
   ```
3. 验证配置解析：
   ```powershell
   opencode debug config
   ```
   检查输出中的 `"shell"` 字段是否正确指向 Git Bash。

---

### 2. Codex (`@openai/codex`)
Codex 架构上严格区分“桌面端交互终端”与“后台 Agent 执行沙箱”。

#### A. 桌面界面交互终端（可改 Git Bash）
编辑 `~/.codex/config.toml`：
```toml
[desktop]
integratedTerminalShell = "gitBash"
```
保存后重启 Codex 桌面端，窗口内置终端即为 Git Bash。

#### B. 后台 Agent 执行工具（不可直接修改）
* **限制原因**：Codex 原生二进制（`codex-win32-x64`）中的命令沙箱隔离机制基于 Win32 Job Objects 和 Windows Token，在 Rust 源码中硬编码调用了 `powershell.exe -NoProfile` 或 `pwsh.exe`。
* **避开 PowerShell 的方案**：
  * **方案 1（官方推荐，彻底解法）**：在 WSL2 Linux 容器中安装并运行 Codex CLI，内部完全是原生 Linux Bash 环境。
  * **方案 2（Rules 约束法）**：在 `~/.codex/AGENTS.md` 或项目级 `AGENTS.md` 中增加系统约束：
    > "You are running on a Windows system. Do not use native PowerShell cmdlets. Always wrap command-line executions inside Git Bash: `& 'D:/Program Files/Git/bin/bash.exe' -c '<command>'`."

---

### 3. Claude Code (`@anthropic-ai/claude-code`)
* **运行机制**：Anthropic 官方核心工具为 `Bash` 工具。Windows 启动时自动检索 Git for Windows 安装路径，并将命令执行环境映射为 MSYS2 POSIX 树。
* 在 `~/.claude/shell-snapshots/snapshot-bash-*.sh` 可见其注入的 PATH 均为 `/c/...`、`/usr/bin` 格式。
* **维护结论**：**保持现状即可**，Claude Code 永远不会在 Windows 下生成 PowerShell 命令。

---

### 4. pi (`@earendil-works/pi-coding-agent`)
* **运行机制**：位于 `dist/utils/shell.js`：
  ```javascript
  function isLegacyWslBashPath(path) { ... }
  if (process.platform === "win32") {
      paths.push(`${process.env.ProgramFiles}\\Git\\bin\\bash.exe`);
      paths.push(`${process.env["ProgramFiles(x86)"]}\\Git\\bin\\bash.exe`);
      ...
  }
  ```
* **维护结论**：**保持现状即可**，它原生只跑 Git Bash，遇到 WSL stub 会自动跳过。

---

### 5. Google Antigravity (`agy`)
Antigravity 同样分层处理：

#### A. IDE 交互终端面板（可改 Git Bash）
Antigravity IDE 内核基于 VS Code，编辑其用户设置 `AppData/Roaming/Antigravity IDE/User/settings.json`：
```json
{
  "terminal.integrated.defaultProfile.windows": "Git Bash"
}
```

#### B. Agent 底层执行器 (`run_command`)
* **限制原因**：当前 Windows 版本的 Antigravity Agent 底层异步通信、长命令挂起管理与 `manage_task` 信号拦截绑定在 PowerShell 解释器流管道中（系统提示词固定声明 `Operating System: windows. Shell: powershell.`）。
* **避开 PowerShell 语法的处理方案**：
  在全局规则（`.gemini/antigravity/`）或项目的 `.agents/rules` 中明确约束：
  > "用户不接受纯 PowerShell 命令语法（如 Get-ChildItem、Select-String 等）。需要执行文本检索、过滤或复杂操作时，优先调用 `& 'D:/Program Files/Git/bin/bash.exe' -c '<bash command>'` 或生成 `.sh` 脚本执行。"

---

## 三、常见故障速查表

| 症状 / 报错 | 根因分析 | 修复方案 |
| :--- | :--- | :--- |
| `WSL ERROR: execvpe(/bin/bash) failed` | 命令直接调用 `bash`，命中了 System32 下损坏或未初始化的 WSL stub | 配置和脚本中禁止裸调 `bash`，统一换成 `D:/Program Files/Git/bin/bash.exe` |
| OpenCode 依然调用 PowerShell 跑命令 | `opencode.json` 漏配了 `shell`，或填了相对名 `bash` 导致回退 | 检查 `opencode.json` 根级是否配置了全路径，运行 `opencode debug config` 确认 |
| Codex 桌面终端还是 cmd / powershell | `config.toml` 中 `[desktop]` 未配或拼写错误 | 确保在 `[desktop]` 段下配置 `integratedTerminalShell = "gitBash"` 并完全重启应用 |
| Antigravity Agent 执行 bash 命令报路径不存在 | 在 PowerShell 宿主中混用了 Linux 风格根路径 `/d/...` | 在传给 `bash.exe -c` 时使用标准正斜杠路径 `D:/path/to/file` 或让 MSYS2 自动挂载转换 |
