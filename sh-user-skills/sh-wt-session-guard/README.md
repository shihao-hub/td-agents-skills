---
name: sh-wt-session-guard
description: Windows Terminal (wt) 与 agy CLI 会话保持与恢复双保险守卫引擎：右上角关闭全部标签页时双保险保底追加恢复命令、无窗口静默守护、开机自启动治理与会话生命周期追踪。点名使用
version: 1.0.0
created: 2026-10-13
updated: 2026-10-13
disable-model-invocation: true
---

# sh-wt-session-guard：Windows Terminal 与 agy CLI 会话恢复双保险守卫引擎

> 针对定制版 / 原生 Windows Terminal (WT) 在点击窗口右上角 `[X]` 并在弹窗中选择【全部关闭】时，各 Tab 内运行的 Google Antigravity CLI (`agy`) 任务会被直接强制终结、导致下次 WT 重启恢复标签页时丢失 `agy --conversation=<uuid>` 恢复命令的问题，本技能提供一整套**零侵入、零黑框弹窗、免 Python 环境依赖、支持 Windows 开机自启**的独立二进制守护引擎与运维 SOP。

---

## 一、核心定位与解决痛点

| 痛点场景 | 传统表现 | 本守卫引擎解决方式 |
| :--- | :--- | :--- |
| **习惯点击右上角 `[X]`** | 终端强制杀死控制台进程，`agy` 来不及输出优雅停机提示 | 实时感知 WT 进程树，在 WT 退出落盘瞬间以 UTF-16LE 原子补写 `Resume with -c` 恢复命令块 |
| **手滑误点关闭弹窗【取消】** | 若提前拦截发送 Ctrl+C 会导致误杀正在工作的会话 | **退出确认后才收敛**：只有在确认点击【全部关闭】、WT 进程彻底退出后才触发补写，无任何误杀风险 |
| **多 Tab / 多项目并发工作** | 重启 WT 后所有 Tab 历史丢失会话 ID，`/resume` 容易串项目 | 跨进程树精准提取各 Tab 的 `WT_SESSION` GUID，精确反查对应工作区的真实会话 UUID，100% 精准对应 |
| **后台常驻弹出黑框控制台** | 传统 Python/CLI 后台进程每次启动都会在桌面弹出黑框窗口 | 编译为 PE Subsystem=2 (GUI) 兼容二进制 + Win32 句柄隐藏保底，启动与运行全局 0 闪烁 0 黑框 |
| **电脑重启后守护失效** | 每次系统重启都需要手动重新启动守护进程 | 内置 `autostart` 子命令，一键注册/卸载 `HKCU` 注册表静默自启动，开机全自动护航 |

---

## 二、架构与双保险机制解析

```mermaid
flowchart TD
    subgraph Windows Terminal 交互层
        WT["WindowsTerminal.exe (定制版)"]
        Tab1["Tab 1: powershell.exe<br/>WT_SESSION: 14D3...<br/>运行 agy (会话 A)"]
        Tab2["Tab 2: powershell.exe<br/>WT_SESSION: BBC...<br/>运行 agy (会话 B)"]
        CloseBtn["右上角 [X] ➔ 确认【全部关闭】"]
    end

    subgraph 守卫引擎 (wt_session_guard.exe)
        Daemon["后台守护进程 (PID 常驻)"]
        Tracker["活跃追踪器: scan_wt_agy_sessions()<br/>缓存 wt_session_guid ➔ 会话 UUID"]
        Detector["进程退出监听器: known_wt_pids ➔ empty"]
        Patcher["原子补丁引擎: patch_buffer_file()<br/>追加 UTF-16LE 恢复指令块"]
    end

    subgraph WT 磁盘持久化
        Buf1["buffer_14D3...txt"]
        Buf2["buffer_BBC...txt"]
        Restore["下次启动 WT ➔ 恢复标签页<br/>底部直接展示 agy --conversation=..."]
    end

    WT --> Tab1 & Tab2
    Daemon --> Tracker --> Detector
    CloseBtn -->|WT 进程销毁| Detector
    Detector -->|触发保底收敛| Patcher
    Patcher -->|原子追加| Buf1 & Buf2
    Buf1 & Buf2 --> Restore
```

### 1. 缓冲区底层机制
Windows Terminal 在会话结束时，会将各个标签页的屏幕文本序列化落盘至：
`%LOCALAPPDATA%\Microsoft\Windows Terminal\buffer_<WT_SESSION_GUID>.txt`（UTF-16LE 编码）。
下次 WT 启动还原会话时，WT 会忠实地读取该文件内容并渲染在各 Tab 历史缓冲区尾部。

### 2. 精准防重复补写（Anti-False-Positive Invariant）
守卫引擎严格仅检测缓冲区**最底部的最后 6 行有效文本**：
- 只有当真正的 `Resume with -c` 及目标会话 UUID 紧贴光标尾部时才判定无需补写；
- 避免聊天历史或代码中包含教学用词时引发假阴性漏补。

---

## 三、CLI 常用命令速查

产物位置：[`dist/wt_session_guard.exe`](file:///D:/Users/language_projects/.agents/skills/sh-user-skills/sh-wt-session-guard/dist/wt_session_guard.exe) 或单脚本 [`scripts/wt_session_guard.py`](file:///D:/Users/language_projects/.agents/skills/sh-user-skills/sh-wt-session-guard/scripts/wt_session_guard.py)。

### 1. 核心运行命令

```powershell
$guard = "D:\Users\language_projects\.agents\skills\sh-user-skills\sh-wt-session-guard\dist\wt_session_guard.exe"

# 1. 启动后台静默守护引擎（推荐日常使用）
& $guard guard --daemon

# 2. 查询当前守护状态与在线受保护的会话列表
& $guard status

# 3. 停止后台守护进程
& $guard stop-guard

# 4. 扫描并详细列出当前各 WT 窗口、Shell、Tab GUID 与挂载的 agy 会话
& $guard scan

# 5. 手动模拟校对当前各标签页 buffer 文件（可 dry-run 预览）
& $guard patch-all --dry-run
& $guard patch-all

# 6. 主动向当前全部 agy 会话广播真实 Win32 Ctrl+C 信号优雅停机
& $guard stop-all
```

---

## 四、开机自启配置与治理（Windows Startup）

为了保证电脑重启或注销登录后无需手动启动守护，守卫内置了开机自启动管理功能。

### 1. 方式一：CLI 一键开关（推荐）

```powershell
$guard = "D:\Users\language_projects\.agents\skills\sh-user-skills\sh-wt-session-guard\dist\wt_session_guard.exe"

# 开启开机自启
& $guard autostart on

# 查询开机自启配置状态
& $guard autostart status

# 关闭开机自启
& $guard autostart off
```

### 2. 方式二：PowerShell 原生注册表治理

该自启项基于 Windows 官方标准的当前用户运行项（`HKCU Run`），无需管理员权限：

- **注册表路径**：`HKCU:\Software\Microsoft\Windows\CurrentVersion\Run`
- **键名**：`WindowsTerminalSessionGuard`
- **键值**：`"D:\Users\language_projects\.agents\skills\sh-user-skills\sh-wt-session-guard\dist\wt_session_guard.exe" guard --daemon`

**手动添加/查看命令**：
```powershell
# 开启自启
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" `
  -Name "WindowsTerminalSessionGuard" `
  -Value '"D:\Users\language_projects\.agents\skills\sh-user-skills\sh-wt-session-guard\dist\wt_session_guard.exe" guard --daemon'

# 检查项是否存在
Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "WindowsTerminalSessionGuard"

# 移除自启
Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "WindowsTerminalSessionGuard" -ErrorAction SilentlyContinue
```

> **系统级校验**：配置完成后，可在 Windows 任务管理器（Task Manager）➔【启动应用】（Startup Apps）标签页中直接看到并随时开关 `WindowsTerminalSessionGuard`。

---

## 五、环境与编译打包 SOP

当修改了 `scripts/wt_session_guard.py` 源码需要重新生成单文件二进制时：

### 1. 依赖与环境
- 运行时：Python 3.12+ / `uv`
- 核心库：`psutil`（需随单文件二进制一并打包）
- 编译器：MSVC `cl.exe` (Visual Studio 2022 Build Tools)

### 2. 编译打包命令
```powershell
cd "D:\Users\language_projects\.agents\skills\sh-user-skills\sh-wt-session-guard"

# 使用 uv 驱动 Nuitka 单文件编译（必须包含 psutil 依赖）
uv run --with nuitka --with psutil python -m nuitka `
  --standalone `
  --onefile `
  --output-dir=dist `
  --remove-output `
  scripts/wt_session_guard.py
```

---

## 六、故障排查与日志诊断

- **运行日志文件**：`%LOCALAPPDATA%\Microsoft\Windows Terminal\session_guard.log`
- **守护 PID 锁文件**：`%LOCALAPPDATA%\Microsoft\Windows Terminal\session_guard.pid`

### 常见症状排查

1. **执行 `guard --daemon` 报错 `[WinError 2] 系统找不到指定的文件`**：
   - 根因：Nuitka onefile 单文件模式下 `sys.executable` 虚构指向临时解压目录中不存在的 `python.exe`；
   - 解决方案：已在代码中采用 `kernel32.GetModuleFileNameW(0)` 与 `sys.argv[0]` 锚定磁盘真实的 `wt_session_guard.exe`。
2. **终端历史未出现恢复命令**：
   - 查阅 `session_guard.log`：检查是否有“检测到全部 Windows Terminal 窗口已关闭退出”日志；
   - 检查对应 Tab 是否已包含恢复命令（避免重复追加）。
3. **彻底清理与重置**：
   ```powershell
   & $guard stop-guard
   Remove-Item "$env:LOCALAPPDATA\Microsoft\Windows Terminal\session_guard.pid" -Force -ErrorAction SilentlyContinue
   ```
