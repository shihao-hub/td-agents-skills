---
name: sh-wt-customizer
description: Windows Terminal (wt) 独立版定制、图标注入、任务栏守卫、右键菜单与 Win+R 全链路接管、独立版幂等版本升级（--update）及一键原生复原 SOP（依托 taskbarguard 资产库与引擎）。点名使用
version: 1.2.0
created: 2026-10-11
updated: 2026-10-12
disable-model-invocation: true
---

# sh-wt-customizer：Windows Terminal (wt) 独立版定制、图标注入与全链路接管 SOP

> **架构定位与依赖关系**：  
> 本技能是 **Windows Terminal (wt) 独立版全链路定制与排障的工程操作手册（SOP）**。  
> 技能本身不重复冗余存储任何二进制图标或补丁代码，**统一依赖仓内任务栏守卫工程 `go_projects/taskbarguard`**：  
> - **图标资产单一真身**：`D:\Users\language_projects\go_projects\taskbarguard\scripts\wt\custom_icons/`  
> - **补丁调度核心脚本**：`D:\Users\language_projects\go_projects\taskbarguard\scripts\wt\patch_wt_icon.py`  
> - **守卫与 CLI 调度器**：`D:\Users\language_projects\go_projects\taskbarguard`（`go run . run wt` / `taskbarguard-dev.exe`）

---

## 一、全链路 7 层调度机制与排障认知深度解构

在 Windows 11 环境下，为 Windows Terminal 修改图标并完全接管系统入口是一个**跨越 7 个操作系统子系统**的精密工程。若仅修改快捷方式或环境变量，必然会在 `Win + R`、右键菜单或控制台进程唤起时露馅。以下为底层完整调度关系：

```
                       用户触发行为
        ┌──────────────┬──────────────┬──────────────┐
        │              │              │              │
     任务栏/快捷方式     Win + R 运行框    文件右键菜单     外部控制台程序(如 agy)
        │              │              │              │
        ▼              ▼              ▼              ▼
   Layer 3 快捷方式   Layer 5 AppPaths  Layer 7 Nilesoft   Layer 6 DefTerm 机制
   指向独立版 wt.exe  重定向为独立版     隐藏原版/注入新项   内核默认委托机制
        └──────────────┴──────────────┴──────────────┘
                               │
                               ▼
                   Layer 1 独立免安装版部署
                 (D:\Users\Softwares\WindowsTerminal)
                               │
                               ▼
                   Layer 2 PE 图标资源物理注入
                 (WindowsTerminal.exe & wt.exe)
                               │
                               ▼
                   Layer 4 环境变量 PATH 优先捕获
```

---

### Layer 1: 独立免安装版的部署与环境隔离
- **为什么必须用独立免安装版？**  
  系统自带的 Windows Terminal 位于 `%ProgramFiles%\WindowsApps\`，属 UWP / MSIX 受保护沙箱，目录只读且受 Windows Defender 强签名完整性校验。直接修改其 PE 资源会触发访问拒绝或应用崩溃。
- **免安装版的优势**：从微软官方 GitHub Releases 下载解压（如 `D:\Users\Softwares\WindowsTerminal`），是纯正的 Win32 应用程序，完全可写且无沙箱束缚。
- **配置与历史无缝继承**：独立版与 Store 原版共享本地用户配置：
  - 设置文件：`%LOCALAPPDATA%\Microsoft\Windows Terminal\settings.json`；
  - PowerShell 历史记录：`%APPDATA%\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt`；
  - 启动后配色、分屏、字体、历史命令记录 100% 自动继承，无任何割裂感。
- **【核心排障与最佳实践：便携版 Shell（PowerShell 7 / Git Bash）与 Atuin 目录历史集成】**：
  - **动态生成器断层**：独立免安装版缺少 MSIX 包身份，且绿色便携版 PowerShell 7（`pwsh.exe`）未注册系统全局安装项，WT 无法自动扫描。需在 `settings.json` 的 `profiles.list` 中显式静态登记 PowerShell 7（GUID: `{574e775e-4f2a-5b96-ac1e-a2962a402336}`）与 Git Bash（`--login -i`）。
  - **Atuin 命令历史与 `$PROFILE` 双端同步**：PowerShell 5.1 与 7 的 `$PROFILE` 物理路径相互独立（分别位于 `Documents\WindowsPowerShell` 与 `Documents\PowerShell`）。需确保双端均配置 Atuin 初始化、PATH 缺失自愈与 OSC 9;9 目录上报，使 `Ctrl+R`（当前目录命令历史搜索）与 `hh` 在定制版终端内跨 Shell 无缝生效。

---

### Layer 2: PE 可执行文件图标资源物理烧录与运行中热替换
- **原理**：调用 Win32 核心资源 API（`BeginUpdateResourceW` / `UpdateResourceW` / `EndUpdateResourceW`）向 `WindowsTerminal.exe` 与 `wt.exe` 的 PE 资源段（`RT_GROUP_ICON` / `RT_ICON`）直接写入定制 ICO 图标，彻底摆脱对 `rcedit.exe` 等第三方工具的依赖。
- **【核心踩坑 1：3 套图标资源组盲区（Group 101 vs 102 vs 103）】**：  
  Windows Terminal 内部并非只有 1 个图标，而是内置了 3 套资源组：
  - `Group 101`（`IDI_APPICON`）：默认主图标；
  - `Group 102`（`IDI_APPICON_HC_BLACK`）：高对比度深色模式图标；
  - `Group 103`（`IDI_APPICON_HC_WHITE`）：高对比度浅色模式图标。  
  若仅修改 Group 101，一旦系统处于特定对比度或外壳按索引枚举，旧版黑白原版图标就会死灰复燃！**规则：必须全量将 101、102、103 同步烧录为选定款式，并同步覆盖 `Images/` 目录下的物理对比度 ico 文件**。
- **【核心踩坑 2：运行中文件独占锁与原子热替换机制】**：  
  Windows 内核对正在运行的可执行文件施加写入锁（报 `ERROR_ACCESS_DENIED = 5`）。若用户当前桌面上开着常驻终端（如挂着后台服务或命令行会话），直接覆写必败。  
  **优雅方案（无需杀用户进程）**：Windows 内核**允许对正在运行的 EXE 进行同分区重命名**！引擎采用“临时副本完整烧录 ➔ 原子重命名旧运行实例为 `.old_running` ➔ 将全新补丁 EXE 原位就位”的流水线，实现零中断平滑热替换。新打开的窗口或子进程将即刻加载全新版本。

---

### Layer 3: 开始菜单快捷方式守卫与深度离线缓存重构（严禁强写任务栏目录）
- **原理与避坑铁律（Windows 11 任务栏固定机制）**：
  - 开始菜单：更新 `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Windows Terminal.lnk`，目标指向独立版 `WindowsTerminal.exe`，并绑定定制 ICO。
  - **【致命反模式警示：严禁强写 `User Pinned\TaskBar\`】**：在 Windows 11 中，任务栏固定项必须由 Taskband 注册表与系统 COM API 协同维护。若代码强行在 `User Pinned\TaskBar\` 下丢未注册的 `.lnk`，会导致“物理文件存在但注册表未登记”，进而导致任务栏右键菜单丢失【固定到任务栏】与【从任务栏取消固定】，退化成只剩 `[ ✕ 关闭窗口 ]` 的死锁！必须仅通过开始菜单快捷方式或运行中的原生窗口由用户/系统正常固定，脚本自动检测并清理孤立的 TaskBar 快捷方式以解除死锁。
- **【核心踩坑：Windows 11 任务栏固定项死守旧缓存】**：  
  在 Windows 11 中，任务栏固定项深度缓存于 `%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache_*.db`。若仅调用普通重启 Explorer，系统会直接重载旧数据库，任务栏图标顽固不刷新！  
  **终极解法**：在关闭 `explorer.exe` 的间隙，离线暴力删除全部 30 个 `iconcache_*.db`、`thumbcache_*.db` 与 `%LOCALAPPDATA%\IconCache.db`，再拉起 Explorer 并广播 `SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_FLUSH)`，强制外壳 100% 重新从最新 PE 与快捷方式提取生成高清质感图标！

---

### Layer 4: 环境变量 PATH 优先级调控
- 将独立版目录（如 `D:\Users\Softwares\WindowsTerminal`）插入到用户级环境变量 `Path` 的最顶端。
- 确保它在系统中的优先级高于系统级默认的 `%LOCALAPPDATA%\Microsoft\WindowsApps`（该路径内包含原版 Store 的别名指针）。
- 写入后通过 Windows API 广播 `WM_SETTINGCHANGE` 消息通知外壳。

---

### Layer 5: `Win + R` 运行机制与 App Paths 抢占
- **【核心踩坑：Win+R 绕过 PATH】**：  
  按 `Win + R` 输入 `wt` 时，Windows Explorer（`explorer.exe`）解析程序名的第一顺位**不是环境变量 PATH**，而是注册表中的 `App Paths`！
  - 注册表位置：`HKCU\Software\Microsoft\Windows\CurrentVersion\App Paths\wt.exe`；
  - 默认值被原版 Store 写死为 `C:\Program Files\WindowsApps\...\wt.exe`。
- **解法**：必须将该键值重定向至独立免安装版的 `wt.exe`，才能确保 `Win + R wt` 不会被系统劫持回原版。同时在状态文件中持久化记录原版路径，供复原时使用。

---

### Layer 6: Windows 11 DefTerm 默认终端委托与 CUI 瞬态生命周期机制（以 agy 为例）

> **通道层面的完整剖析**：为何绿色免安装版在底层机制上**无法**被注册为系统全局 DefTerm（内核走进程外 COM 服务器激活，与 PATH / App Paths 命令行通道完全割裂）、以及 CUI/GUI 子系统与无窗口镜像方案，见知识库条目 `52-Windows原生PE控制台委托DefTerm断层与MCP服务无窗口镜像机制指南.md`。
- **DefTerm 委托与为什么此前会弹出原版 WT**：  
  在 Windows 11 中，控制台子系统程序（PE Subsystem = 3, CUI，如 `agy.exe`）如果在无现成终端宿主的环境下启动（如 Win+R、运行框、桌面快捷方式），会被内核的 **DefTerm（Default Terminal Application）** 与外壳协议调度接管。此前由于注册表 `App Paths\wt.exe` 与 PATH 被微软 Store 版绑定，DefTerm 会强行唤醒沙箱内的 Store 原版 WT；**在完成 Layer 4 & Layer 5 的抢占后，所有系统级终端呼叫均被严格重定向至独立免安装版，彻底阻断了原版 WT 的唤醒**。
- **【核心排障认知：为什么外部启动 CLI 会“一闪而过”？】**：  
  许多 CLI 工具（如 `agy`、`python` 等）本身是控制台进程，没有自己的 GUI 消息循环窗口。当从外部环境裸启动该进程时：
  1. Windows 操作系统必须为其临时分配一个控制台宿主（如 `conhost.exe`）；
  2. 控制台黑框瞬间弹出，CLI 进程启动；
  3. 若命令执行完毕、或检测到无标准输入（TTY）管道重定向（非交互模式）而退出，**子进程生命周期即告终结**；
  4. **Windows 内核机制：操作系统会在控制台子进程退出时立即销毁其宿主窗口**！肉眼看到的就是一个黑框“一闪而过”。
- **【优雅方案：利用定制独立版 wt 实现常驻弹窗启动】**：  
  若需要在运行框、桌面或脚本中一键唤起独立终端并保持交互窗口不退出，应通过接管后的 `wt.exe` 结合 PowerShell 的 `-NoExit` 参数启动：
  ```powershell
  wt.exe -d "D:\Users\language_projects" powershell -NoExit -Command "agy --conversation=<conversation-id>"
  ```
  这样既能确保窗口具备 `pure_dark` 定制质感图标，又能在命令执行完后始终驻留在 Shell 中。
- **【核心排障认知 2：DefTerm 对 Git Bash / 后台静默脚本的过度委托与焦点劫持反模式】**：  
  - **致命现象**：在 Git Bash（MSYS2 / MinGW）、Node.js/Python 无窗口子进程、定时任务或 AI Agent（如 Claude / OpenCode / AGY）中执行 `powershell.exe -NoProfile -Command "..."` 时，屏幕上突然弹出一个 Windows Terminal 窗口并强行夺取全局前台焦点（Foreground Window）。在测试 Alt+Tab、Win+Tab、`XamlExplorerHostIslandWindow` 等系统级 XAML 切换界面时，WT 弹窗会瞬间击溃正在测试的焦点状态！
  - **底层机制**：Git Bash 基于 POSIX pipe/pty 仿真，无 Win32 原生控制台宿主（`CONIN$` / `CONOUT$`）。原生 `powershell.exe` 启动时判定无控制台依附，系统强制触发 `AllocConsole()`。而在 Win11 默认配置下（`HKCU\Console\%%Startup` 的 `DelegationTerminal` 为 `{00000000-...}` 即“让 Windows 决定”），系统自动将新控制台委托给 Windows Terminal。WT 作为现代 GUI 应用程序，只要接活就必须弹出一个 XAML 窗口，哪怕只是跑一句静默的 `-Command`！
  - **开发者黄金法则（DefTerm 最佳实践）**：
    1. **系统级根治（强烈推荐开发者环境）**：运行 `uv run ... patch_wt_icon.py --defterm conhost`，或在系统设置（开发者选项 ➔ 终端）中将“默认终端应用程序”改回【Windows 控制台主机】（`conhost.exe`，GUID: `{B23D10C0-E52E-411E-9D5B-C09FDF709C7D}`）。
       > **重要认知澄清**：日常主动使用独立版 WT（桌面快捷方式、开始菜单、Win+R `wt`、右键菜单）丝毫不受影响，依然秒开定制版 WT；改回 conhost 仅切断了“后台静默命令行被强行委托弹窗抢焦点”的流氓行为。
    2. **代码级防御（子进程编程）**：在 Python / Go / C# 启动后台 PowerShell 子进程时，显式传递 `CREATE_NO_WINDOW = 0x08000000` 标志，告知内核无需分配控制台，彻底绕过 `AllocConsole()` 与 DefTerm 委托。
    3. **命令行级阻断**：在 Git Bash 中通过 `conhost.exe powershell.exe -NoProfile -Command "..."` 包装执行。

---

### Layer 7: Windows 11 右键菜单（Nilesoft Shell）深度定制
- **【核心踩坑：Nilesoft Shell 换皮不换心】**：  
  若仅在 `modify.nss` 写 `modify(find='在终端中打开' image='...')`，右键虽换了图标，但点击唤起的仍是微软原版 DLL，最终弹出的依旧是未定制的 Store 版！
- **正确解法**：
  ```nss
  // 1. 彻底隐藏原版 Store 扩展项
  modify(mode=mode.multiple find='在终端中打开|open in terminal' vis=vis.remove)

  // 2. 注入独立版真正启动器（图标与命令双重接管）
  item(type='dir|drive|back' title='在终端中打开(T)' pos=4 image='D:\Users\Softwares\WindowsTerminal\WindowsTerminal.exe' cmd='D:\Users\Softwares\WindowsTerminal\wt.exe' arg='-d "@sel.path\."')
  ```

---

### Layer 8: Windows 登录开机自启动机制接管与 UWP StartupTask 隔离
- **【核心踩坑：WT 界面自启动开关硬绑定微软商店原版】**：  
  在 Windows Terminal 设置界面「启动 ➔ 在计算机启动时启动（登录到 Windows 时自动启动终端）」是一个 WinRT UWP API 开关。
  - 其底层调用 `StartupTask.RequestEnableAsync()`，将自启动注册在 `HKCU\Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel\SystemAppData\Microsoft.WindowsTerminal_8wekyb3d8bbwe\StartTerminalOnLoginTask`；
  - **后果**：登录时 Windows 操作系统直接拉起微软应用商店原版 UWP 包（`Microsoft.WindowsTerminal_8wekyb3d8bbwe`），完全无视用户环境变量 `Path` 和 `App Paths`，导致开机启动的依然是原版未定制图标的 WT！
- **正确解法（双步闭环）**：
  1. **关闭原版 UWP 自启动**：在 WT 设置中将该开关切为【关】（或将上述注册表项的 `State` 设为 `0` 彻底禁用）；
  2. **注册独立版 Win32 开机启动项**：通过当前用户的 Run 注册表键挂载独立版 `wt.exe`：
     ```powershell
     Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "WindowsTerminalCustom" -Value '"D:\Users\Softwares\WindowsTerminal\wt.exe"'
     ```
  3. **效果**：开机登录时 100% 自动拉起独立定制版 Windows Terminal，完美保持 `pure_dark` 极简深黑哑光图标！

---

## 二、前置要求与物资保障机制

在任何 Windows 10/11 机器上，**无需用户提前手动下载、搜寻或解压任何物资**：

1. **操作系统**：Windows 11 / Windows 10 (x64)；
2. **执行环境**：Python 3.10+ / Go 1.25+；
3. **物资自愈机制（自动化流水线）**：
   - **零第三方 PE 工具依赖**：直接基于 Windows 原生 Win32 API（`BeginUpdateResourceW` / `UpdateResourceW`）进行精确 PE 资源注入；
   - **Windows Terminal 独立免安装版**：无需提前准备。脚本缺失时传入 `--auto-setup` 会自动查询 GitHub API 获取最新版 `Microsoft.WindowsTerminal_xxx_x64.zip`，下载并解压到目标目录，且自动将路径置顶写入用户环境变量 `Path`；
   - **图标资产真身**（集中保存在 `go_projects/taskbarguard/scripts/wt/custom_icons/`）：
     - `pure_dark.ico`：极简深黑哑光（推荐，极客质感）；
     - `titanium.ico`：钛金极客银白；
     - `underlit_chrome.ico`：机械发光赛博；
     - `dark_blue.ico`：经典深海微光；
     - `cyan_matrix.ico`：极客青矩阵。

---

## 三、部署执行 SOP（两种模式）

### 模式 A：依托 TaskbarGuard CLI 调度（推荐）

在 `go_projects/taskbarguard` 目录下直接调度：

```powershell
cd D:\Users\language_projects\go_projects\taskbarguard

# 1. 查看可用款式与状态
go run . list

# 2. 应用极简深黑哑光款 (推荐)
go run . run --style pure_dark wt

# 3. 批量应用所有已启用守护应用
go run . apply wt
```

> 注意：CLI 目前只包装了应用/复原/DefTerm 等动作，**版本升级（`--update`）仅暴露在 Python 引擎中**，需要升级请直接用下方模式 B 的命令。

---

### 模式 B：直接调度 Python 驱动引擎（支持离线缓存重构与自安装）

可在任意目录下使用 `uv run` 直接执行核心脚本：

```powershell
# 1. 本机极速应用并彻底离线重建图标缓存
uv run D:\Users\language_projects\go_projects\taskbarguard\scripts\wt\patch_wt_icon.py --style pure_dark --restart-explorer

# 2. 新电脑 0 物资全自动一键部署 (自动下载最新独立版终端 + 配置 PATH + 注入图标 + 离线刷新缓存)
uv run D:\Users\language_projects\go_projects\taskbarguard\scripts\wt\patch_wt_icon.py --auto-setup --style pure_dark --restart-explorer

# 3. 查看可用款式列表
uv run D:\Users\language_projects\go_projects\taskbarguard\scripts\wt\patch_wt_icon.py --list-styles

# 4. 配置系统默认终端为 conhost (阻断静默脚本弹窗抢焦点，推荐开发者必配)
uv run D:\Users\language_projects\go_projects\taskbarguard\scripts\wt\patch_wt_icon.py --defterm conhost

# 5. 幂等升级独立版到 GitHub 最新稳定版（已是最新则直接退出 0），并自动重放全链路定制
uv run D:\Users\language_projects\go_projects\taskbarguard\scripts\wt\patch_wt_icon.py --update
```

---

## 四、独立免安装版的版本升级与幂等守卫（`--update`）

### 1. 为什么“定制版更新”必须显式处理

- **独立免安装版不带自动更新器**：只有 Store / MSIX 版才由系统静默升级，而 Store 版正是被本 SOP 拒绝的“影子入口”。因此独立版**永远不会自己变新**，升级必须由人或脚本显式触发。
- **升级会静默摧毁 Layer 2 的成果**：新版本包解压覆盖后，`WindowsTerminal.exe` 的 Group 101/102/103 与 `wt.exe` 的 Group 101 全部回到官方原版图标，`Images/terminal_contrast-*.ico` 也被包内原版覆盖。
- **但绝大部分接管不用重做**：PATH、`App Paths\wt.exe`、DefTerm、Nilesoft 规则、开始菜单快捷方式、`settings.json` 与 PSReadLine 历史均不受影响（路径与注册表键未变，见 Layer 1）。

### 2. 【致命认知陷阱】`--auto-setup` 在已装机上不会升级

引擎的执行顺序是：

```text
find_target_exes()  →  目录里已有 exe 就直接用它
                    →  只有目录为空时，才调用 auto_setup_windows_terminal() 联网部署
```

所以 `--auto-setup` 是**双重语义**：新机 = 部署器；老机 = 普通 patch（只重放定制，**不联网也不升级**）。把它当“更新命令”用会**静默无效**——脚本不报错，版本纹丝不动（最坏的失败模式：看起来成功了）。引擎现已在检测到现有安装时显式打印警告并指向 `--update`。

### 3. 【致命认知陷阱 2】跑在 Windows Terminal 里的 Agent 会“自杀”

`--update` 必须关闭 WT 并重命名其安装目录，而 `taskkill /F /IM WindowsTerminal.exe /T` 的 `/T` 会终结**整棵子进程树**。若调用方本身就跑在某个 WT 窗口里（AI Agent、交互式 CLI、WT 内的任意 shell），结果就是：**会话在自己被杀中中断，升级流程半途夭折**。

**实测判据**：WT 会向所有子进程注入环境变量 `WT_SESSION`，进程祖先链顶端即为 `WindowsTerminal.exe`。

引擎的处置（两层闸门）：

| 闸门 | 位置 | 行为 |
|:---|:---|:---|
| 闸门 1 | `ensure_wt_processes_closed()` | 命中 `WT_SESSION` → **跳过** taskkill 并打印警示；PE 注入自动转走“原子重命名热替换”路径（该类操作本就不需要关终端） |
| 闸门 2 | `update_windows_terminal()` | 命中 `WT_SESSION` → **在下载之前就中止**（exit 1，零修改、零下载），并给出两条绕行方式 |

所以“AI 自动更新”的正确姿势是：**由非 WT 宿主的进程执行**（conhost、Win+R 独立窗口、任务计划），或先手动关掉所有 WT 窗口再从其他终端跑。已是最新版本时闸门不会触发（`exit 0` 短路在前）。

### 4. `--update` 契约（幂等，可安全重复执行）

| 步骤 | 行为 |
|:---|:---|
| ① 定位 | `--target-dir` → 否则读 `state.json` 的 `installed_dir_wt` → 否则 `DEFAULT_TARGET_DIRS`；找不到则直接退出 1（**不联网**） |
| ② 比对 | 本地 `WindowsTerminal.exe` 的 Win32 `VersionInfo`（四段）vs GitHub `releases/latest` 资产名中的版本号 |
| ③ 短路 | 本地 ≥ 远端 → 打印 `已是最新版本` 并 **exit 0**（幂等，可反复跑） |
| ④ 升级 | 下载 → 解压到 `WindowsTerminal.new` 暂存 → 校验 `WindowsTerminal.exe` / `wt.exe` 齐全 → **自动关闭 WT 进程** → 目录级原子重命名换入（旧目录 → `.old` 后删除）。若检测到调用方自身就在 WT 会话内，则**在下载前直接中止**（见上文陷阱 2） |
| ⑤ 回滚 | 任一步失败（下载/解压/缺文件/换入异常）→ 旧目录原地保留或自动回滚，**旧版始终可用**；`.new` / `.old` 残留下次运行自动清理 |
| ⑥ 重放 | 复用完整 patch 流程：重注入 101/102/103 与 `Images/` 对比度 ico、App Paths、Nilesoft、开始菜单、`state.json`、图标缓存刷新 |
| ⑦ 款式 | 优先级：`--style` 显式指定 → `state.json.style_wt` → `pure_dark`。**不会把用户已选款式改回默认** |

> **为何必须关进程**：Windows 不允许重命名含运行中 exe 的目录，因此引擎会自动 `taskkill`。这正是选择“整目录换入”而非“逐文件替换”的原因——避免新版本 DLL 与旧 exe 混搭。
> **`.bak` 自动重置**：整目录换入会连同上一版 `Images/*.ico.bak` 一起丢弃，所以后续 `--revert` 只会还原与当前版本匹配的原版图标。

### 5. 升级丢失面一览

| 对象 | 升级后 | 是否需干预 |
|:---|:---|:---|
| `WindowsTerminal.exe` 图标（101/102/103）、`wt.exe` 图标（101） | 被官方原版覆盖 | ✅ `--update` 自动重注入 |
| `Images/terminal_contrast-{black,white}.ico` | 被包内原版覆盖 | ✅ `--update` 自动同步 |
| 用户 `Path`、`App Paths\wt.exe`、DefTerm、Nilesoft `modify.nss`、开始菜单 `.lnk` | 不变 | ❌ 无需重做 |
| `settings.json`、PSReadLine 历史 | 不变 | ❌ 无需重做 |
| `state.json`（`version_wt` / `installed_dir_wt` / `style_wt`） | 自动更新 | ❌ 自动维护 |

### 6. 自动化 / Agent 调用约定

`state.json` 中已记有 `installed_dir_wt` 与 `style_wt`，因此 `--update` 是一条**无需附加参数即可安全执行**的幂等命令 —— 这正是“点名 skill 让他更新”能可靠落地的前提：版本比对、进程关闭、款式重放全在脚本内，调用方（人或 Agent）无需临场判断。

**但 Agent 必须先确认自己的宿主环境**（这一步不能省）：

1. 读环境变量 `WT_SESSION`；
2. **为空**（Agent 跑在 conhost / 任务计划 / 非 WT 宿主）→ 直接执行 `--update`，按退出码与版本行报告结果；
3. **非空**（Agent 本就在 WT 会话内）→ **不要执行**，而是把下面这条命令交给用户手动跑（并告知先关闭全部 WT 窗口）：

```powershell
# 最小调用（推荐给 Agent / 定时任务；可附加 --restart-explorer 一并重建图标缓存）
uv run D:\Users\language_projects\go_projects\taskbarguard\scripts\wt\patch_wt_icon.py --update
```

**判定依据永远是脚本退出码与打印的版本行，而不是“看起来跑完了”。**

---

## 五、100% 官方原生无损复原 SOP（Revert SOP）

如果需要彻底停用独立版，完全恢复成微软官方自带的 Windows Terminal，只需执行单条撤销命令：

```powershell
# 通过 TaskbarGuard
cd D:\Users\language_projects\go_projects\taskbarguard
go run . revert wt

# 或通过底层脚本（连带清理 PATH 并重启 Explorer）
uv run D:\Users\language_projects\go_projects\taskbarguard\scripts\wt\patch_wt_icon.py --revert --remove-path --restart-explorer
```

> **自动完成的 7 项无损复原动作**：
> 1. **注册表 App Paths 复原**：自动将 `HKCU\...\App Paths\wt.exe` 还原回官方商店原版路径；
> 2. **默认终端 DefTerm 复原**：自动将 `HKCU\Console\%%Startup` 恢复为原版默认委托设置；
> 3. **开机自启动清理**：自动清理 `HKCU\...\Run\WindowsTerminalCustom` Win32 自启动项；
> 4. **右键菜单复原**：自动将 Nilesoft Shell 的 `modify.nss` 和 `terminal.nss` 从 `.bak` 备份中完整还原，清理注入规则，并删除 `.bak` 临时文件；
> 5. **Images 资源复原**：自动将 `terminal_contrast-*.ico` 还原为原版；
> 6. **快捷方式清理**：自动清理开始菜单定制的 `.lnk` 文件；
> 7. **环境变量清理**：自动将独立版目录从用户级环境变量 `Path` 中移除。

---

## 六、常见故障排查表

| 症状 / 报错 | 根因剖析 | 标准抢救 SOP |
|---|---|---|
| 任务栏右键菜单丢失【固定到任务栏】/【取消固定】，只剩单行【关闭窗口】 | 往 `%APPDATA%\...\User Pinned\TaskBar\` 强写了未注册快捷方式导致 Taskband 注册表脱节 | 脚本已自动清理孤立快捷方式；仅通过开始菜单快捷方式承接，并在窗口运行时通过系统原生固定 |
| `[-] 注入 PE 图标失败` / 文件被占用 | WindowsTerminal 进程正在运行，Windows 锁定了 exe | 引擎已内置“原子重命名热替换”机制，自动平滑替换就位，无需手动强杀进程 |
| `Win + R wt` 依旧弹默认原版 | 注册表 `App Paths\wt.exe` 仍指向 WindowsApps | 脚本已自动重定向，或手动在 `HKCU\...\App Paths\wt.exe` 写入独立版路径与 Path |
| 右键菜单图标变了但点击仍开原版 | Nilesoft 的 `modify` 无法修改原有扩展的 `cmd` | 改用隐藏原版项（`vis.remove`）+ 动态 `item(...)` 接管的方案 |
| 右键菜单图标迟迟不刷新 | Explorer 内存缓存了旧图标 | 在桌面按住 `Ctrl` 键同时鼠标右键，或重启 Explorer |
| 任务栏仍显示原版图标 / 外部工具唤醒旧图标 | 1) 旧实例常驻且 WT 为单实例机制；2) 遗漏 102/103 资源组；3) Win11 图标缓存未离线清空 | 运行带 `--restart-explorer` 参数的脚本，引擎将全量烧录 101/102/103 并离线彻底清空 `iconcache_*.db`；在方便时重启一次终端即可彻底纯净 |
| 外部启动器/运行框直接执行 CLI（如 `agy`）一闪而过 | CLI 程序属于 CUI 进程，裸启动后由于无现成 Shell 托管，执行完毕或转入后台时系统会销毁控制台宿主 | 改由独立版 `wt` 托管并带 `-NoExit`：`wt.exe -d "<目录>" powershell -NoExit -Command "agy ..."` |
| Git Bash / Agent / 后台脚本调用 `powershell.exe` 频繁弹出 WT 窗口并抢占焦点 | Win11 DefTerm 默认将无 Win32 Console 的 CUI 进程委托给 WT，WT 必须弹出 GUI 窗口接管，破坏前台焦点（如 Alt+Tab / `XamlExplorerHostIslandWindow` 测试） | 1) 运行 `uv run patch_wt_icon.py --defterm conhost` 或在系统设置中将“默认终端应用程序”设为【Windows 控制台主机】（不影响日常用 WT）；2) 脚本启动子进程时显式带 `CREATE_NO_WINDOW (0x08000000)` |
| 电脑开机/用户登录时自动拉起的 Windows Terminal 仍是微软商店原版而非定制版 | WT 设置中的“在计算机启动时启动”走的是 Windows UWP 专属的 `StartupTask` WinRT API，硬绑定了微软商店包名（`Microsoft.WindowsTerminal_8wekyb3d8bbwe`），完全无视 PATH 与 App Paths | 1) 在 WT 设置中将“在计算机启动时启动”切为【关】；2) 运行命令为定制版注册真正的 Win32 开机启动项：`Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "WindowsTerminalCustom" -Value '"D:\Users\Softwares\WindowsTerminal\wt.exe"'` |
| `--update` 打印“检测到当前进程运行在 Windows Terminal 会话内”并 exit 1 | 安全闸门：升级需关闭 WT，而当前会话就在 WT 进程树内，`taskkill /T` 会连自己一起杀 | **这是预期保护，不是故障**。先关闭全部 WT 窗口，再从 conhost / Win+R 独立窗口执行 |
| `--auto-setup` 跑完但版本没变 | `find_target_exes` 先命中现有 exe，只有目录为空才联网部署 | 升级请用 `--update`；`--auto-setup` 只负责**首次**部署 |
| `--update` 报“未发现已部署的独立版终端” | 未传 `--target-dir` 且 `state.json` 无 `installed_dir_wt` 记录 | 首次部署用 `--auto-setup`，或用 `--target-dir` 指向实际安装目录 |
| `--update` 报目录换入失败 | WT 进程占用安装目录（引擎已自动 taskkill，但外部宿主可能旋即重新拉起） | 关闭全部 Windows Terminal 窗口后重跑；引擎会自动回滚，旧版不受损 |
| 外部程序（Sublime、脚本、快捷方式）拉起的 wt 又是原版图标/版本 | 调用方要么硬编码了 `%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe`（Store 影子别名），要么进程 `os.environ['PATH']` 是 PATH 变更前的陈旧快照 | **只传 `wt.exe` 名字交给 PATH 解析**（PATH 顶端即独立版），并在命中 `\WindowsApps\` 时回读注册表 `HKCU\Environment` / `HKLM\...\Session Manager\Environment` 的 `Path` 重新解析；同时重启调用方进程。严禁硬编码 Store 路径 |
