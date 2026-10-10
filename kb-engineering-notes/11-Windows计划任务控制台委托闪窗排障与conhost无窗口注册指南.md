---
name: kb-windows-console-handoff-flash
description: Windows 11 计划任务触发时，已运行的 Windows Terminal 内闪现并激活一个空白 PowerShell 标签页（弹终端；-WindowStyle Hidden 与任务"隐藏"属性无效、窗口事件钩子不可见）。含控制台委托 handoff 根因、WT 标题轮询/录屏检测法、conhost --headless 无窗口注册与一条命令手动配置；想手动重注册无窗口任务时查阅。
---

# Windows 计划任务控制台委托闪窗排障与 conhost 无窗口注册指南

## 一、 现象与报错直击

1. **每 N 分钟（与任务周期一致）终端"闪一下"**：
   - 已常驻的 Windows Terminal 窗口内，**新开并激活一个空白 PowerShell 标签页**（标签标题为其命令行，如 `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`），约 1~2 秒后自动关闭，终端焦点被短暂抢走；
   - 用户描述为"每隔几分钟弹一次终端 / 闪屏"。
2. **三条"直觉排查路"全部撞墙**（本次实测）：
   - 任务属性勾选"隐藏" → **无效**（只隐藏任务列表条目）；
   - 任务动作加 `-WindowStyle Hidden` → **无效**（标签页照闪）；
   - WinEvent 钩子（EVENT_OBJECT_CREATE/SHOW/HIDE）与所有窗口枚举轮询 → **完全看不到任何窗口**（它不是窗口，而是"既有 WT 窗口内的一次标签页变化"，不产生任何顶层窗口事件）；
   - 唯一机器可观测的痕迹：钩子日志里一个 `PseudoConsoleWindow`（visible=False）——ConPTY 交接桩，见下节。
3. **录屏才能实锤**：ffmpeg 整屏录制在触发瞬间抽帧，能看到 WT 标签数 1→2→1、内容切黑再恢复（本次即以此钉死现象）。

## 二、 底层根因剖析

### 1. 机制全链（Windows 11 控制台委托 / console handoff）

```text
[任务计划 / 服务等"无控制台父进程"]
        │ CreateProcess（powershell.exe，控制台子系统程序，无控制台可继承）
        ▼
[内核需为它新建控制台] → 查询 HKCU\Console\%%Startup 的委托配置
   - DelegationConsole / DelegationTerminal 全零 GUID =「让 Windows 决定」
   - Windows 11 的决定：交给正在运行的 Windows Terminal（WT）
        ▼
[WT 按自身 windowingBehavior 处理（本机 settings.json: "useExisting"）]
   - useExisting → 在现有 WT 窗口内新开标签页，并激活
   - 标签标题 = 控制台标题（即 powershell 命令行）
        ▼
[命令结束 → 标签页自动关闭]；全程无独立窗口、无窗口事件
```

- **ConPTY 交接桩**：委托发生时 conhost 会创建一个 `PseudoConsoleWindow`（隐藏、无 WS_VISIBLE），它是该机制在窗口事件层面唯一可见的指纹；只出现在钩子日志里，用户不可见。
- **为什么 `-WindowStyle Hidden` 无效**：它会隐藏"属于该控制台的窗口"——但控制台已被交给 WT 标签页，没有独立窗口可隐藏；且隐藏动作在时序上也不可能阻止委托发生。
- **为什么任务"隐藏"勾选无效**：它只控制任务在计划程序列表中的可见性，与窗口/标签页无关。

### 2. 对照组实验（分辨"是不是它"的决定性方法）

用 40ms 轮询 WT 主窗口标题（`GetWindowText`）做对照：

| 启动方式 | WT 标题变化 | 结论 |
| :--- | :--- | :--- |
| `powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File x.ps1`（旧式直注册） | `taskmon → C:\...\powershell.exe → Windows PowerShell → taskmon` | **触发委托**，标签闪现 |
| `conhost.exe --headless powershell.exe -NoProfile -File x.ps1` | 无任何变化 | **不触发委托**（修复方案） |
| `Start-Process powershell -WindowStyle Hidden`（STARTF SW_HIDE 于创建时生效） | 无任何变化 | 脚本互拉场景可用 |

> [!IMPORTANT]
> "conhost 在进程启动早期先画出控制台窗口、`-WindowStyle Hidden` 隐藏太晚"是**另一类**经典闪窗（从可见终端启动、或非委托环境），网上不少老方案针对的是它；本条的"WT 标签页闪现"由**委托**驱动，只能用本条的检测与修复口径。

## 三、 标准解决与抢救 SOP

### 步骤一：检测（怀疑时手动跑，一条命令）

```powershell
# WT 标题轮询器：40ms 采样，日志记录每一次标题变化；零变化=没有委托标签闪现
powershell -NoProfile -ExecutionPolicy Bypass -File "D:/Users/language_projects/.agents/skills/sh-user-skills/sh-everything-search/scripts/verify_wt_tab_flash.ps1" -Seconds 360

# 结束后看日志（默认 %TEMP%\verify_wt_tab_flash.log）：
#   POLL END ... changes=0               → 正常
#   出现 title -> 'C:\Windows\System32\' → 有委托标签闪现
```

- **配合触发时刻**：`Get-ScheduledTaskInfo -TaskName <任务名> | Select-Object NextRunTime` 推算下一次触发，把轮询窗口盖住它；
- **正对照（证明检测器有效）**：轮询运行期间手动跑一次旧式启动（`powershell -NoProfile -WindowStyle Hidden -File 任意脚本`），标题应立刻翻转——翻转即检测器正常；
- **终极取证（可选）**：ffmpeg 录屏 + 逐帧差异：

  ```powershell
  ffmpeg -y -f gdigrab -framerate 30 -i desktop -t 75 -vf "scale=1600:-2" -c:v libx264 -preset ultrafast -crf 20 C:\path\capture.mp4
  # 触发后找差异帧（tblend 差异均值，逐帧打印 lavfi.signalstats.YAVG）：
  ffmpeg -hide_banner -ss 31 -t 3 -i C:\path\capture.mp4 -vf "fps=5,tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG" -f null -
  ```

- **别用它做判据**：WinEvent 钩子（`verify_task_window.ps1`）只能限定"无可见窗口"，对本机制**天然为 0**——别把 0 当结论，必须用标题轮询/录屏。

### 步骤二：修复（任务动作 → conhost --headless 包装）

把任务动作从"直接拉起 powershell"改为"经显式 headless 控制台宿主拉起"：

```text
Execute   : C:\Windows\System32\conhost.exe
Arguments : --headless "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "<你的脚本>.ps1"
```

headless 控制台不参与委托；进程仍在用户会话内（桌面窗口检测、会话内 IPC 等语义全部不受影响）。

### 步骤三：手动执行命令配置任务（本机 Everything 案例）

```powershell
# 查看状态
Get-ScheduledTask -TaskName sh-everything-idle-exit | Select-Object TaskName, State

# 手动注册 / 重注册（幂等安全；任务丢失、技能目录搬移、换机后执行这一条即可）
powershell -NoProfile -ExecutionPolicy Bypass -File "D:/Users/language_projects/.agents/skills/sh-user-skills/sh-everything-search/scripts/register_task.ps1"

# 注销
powershell -NoProfile -ExecutionPolicy Bypass -File "D:/Users/language_projects/.agents/skills/sh-user-skills/sh-everything-search/scripts/register_task.ps1" -Unregister
```

`register_task.ps1` 要点：注册前先注销同名任务（幂等）；脚本路径由 `$PSScriptRoot` 推导（技能目录再搬移也不会失效）；逐项复刻验证过的设置（见下）。

### 步骤四：通用配方（任何"无窗口计划任务"都可照抄）

```powershell
$conhost = Join-Path $env:SystemRoot 'System32\conhost.exe'
$psExe   = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$script  = 'D:\path\to\your_task.ps1'

$action    = New-ScheduledTaskAction -Execute $conhost -Argument ('--headless "{0}" -NoProfile -ExecutionPolicy Bypass -File "{1}"' -f $psExe, $script)
$trigger   = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)   # 每 5 分钟无限重复
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -Hidden

Register-ScheduledTask -TaskName 'my-task-name' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description '...' -Force
```

### 备选与否决（别走弯路）

| 方案 | 结论 |
| :--- | :--- |
| `conhost.exe --headless` 包装 | **首选**，实测零标签闪现，语义无损 |
| `Start-Process -WindowStyle Hidden` | 脚本之间互拉子脚本时可用（创建期 SW_HIDE 不触发委托）；作为"任务动作"不如 headless 直接 |
| wscript + VBS `Run(..., 0, ...)` 薄壳 | 旧系统/旧场景兜底；VBScript 已被微软宣布弃用，不新增 |
| 任务 Principal 改 S4U（"不管用户是否登录"） | **否决**：session 0 看不到用户桌面窗口、够不到用户会话内的实例 IPC（检测/退出逻辑全断） |
| 改全局默认终端 / Delegation 注册表 | **否决**：影响全机所有控制台程序，破坏既有使用习惯 |

## 四、 验证与防复发建议

1. **验收口径（三件套）**：
   - WT 标题轮询跨 ≥2 次自然触发 `changes=0`；
   - 钩子 `verify_task_window.ps1` 无可见窗口（辅证）；
   - 各次 `Get-ScheduledTaskInfo` 的 `LastTaskResult=0`，且脚本功能闭环真实跑通一次（如闲置自动退出类任务要实测触发一次真行为）。
2. **防复发**：
   - 新任务/改任务一律走 `register_task.ps1` 这类"注册脚本"，不要手改任务动作；
   - 任务脚本内引用路径一律 `$PSScriptRoot` 推导（本次吃过"技能目录搬移后任务动作路径失效"的亏，一并修复）；
   - Windows 功能更新后抽测一次标题轮询。
3. **本机制专属坑位速查**：

| 坑 | 正解 |
| :--- | :--- |
| 以为任务"隐藏"属性 / `-WindowStyle Hidden` 能防闪 | 都无效；必须消除"可被委托的新建控制台"（headless 包装） |
| 用窗口事件钩子验证"没闪" | 标签页不产生窗口事件，天然为 0；用 WT 标题轮询/录屏 |
| 用窗口轮询找证据 | 对标签页永远查不到；对短命窗口也易漏采——瞬态/隐性 UI 一律事件级或标题级检测 |
| PowerShell 5.1 读无 BOM 的 `.ps1` 中文注释报解析错误 | 脚本注释一律 ASCII/英文（本系列 3 个 `.ps1` 均如此） |
| 重注册后 StartBoundary 重置、触发相位变化 | 预期行为（`-Once -At (Get-Date)` + 5 分钟重复） |
| 任务禁用状态下目录搬移后动作仍指向旧位置 | 动作是静态字符串；目录搬移后必须重跑注册脚本 |

## 五、 本次实战档案（2026-10-10）

- 对象：`sh-everything-idle-exit`（Everything 闲置退出的每 5 分钟检查任务）；
- 时间线：用户长期目击每 5 分钟"弹终端" → 禁用任务后消失（A/B 实证）→ 屏幕录制实锤"WT 新标签" → 对照实验定位委托 → `conhost --headless` 重注册 → 4 次自然触发零翻转 + 闲置 18 分钟自动退出 Everything 功能闭环；
- 交付物（均在 `sh-user-skills/sh-everything-search/scripts/`）：`register_task.ps1`（幂等注册）、`verify_wt_tab_flash.ps1`（标题轮询检测）、`verify_task_window.ps1`（窗口钩子辅证）；
- 提交：子仓 `91d1371`（修复+脚本）与 `f71f80f`（计划收尾）；父仓指针 `e11a1a5`；完整计划与实施说明见 `plans-06-everything-search-idle-task-no-window.md`。

---
**最后更新：** 2026-10-10
