---
name: sh-wt-customizer
description: Windows Terminal (wt) 独立版定制、图标注入、任务栏守卫、右键菜单与 Win+R 全链路接管及一键原生复原 SOP（依托 taskbarguard 资产库与引擎）。点名使用
version: 1.1.0
created: 2026-10-11
updated: 2026-10-11
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

### Layer 6: Windows 11 DefTerm 默认终端委托机制
- 在 Windows 11 中，控制台子系统程序（如 `agy.exe`）在启动控制台会话时，会被内核的 **DefTerm（Default Terminal Application）** 机制自动接管并唤醒注册的终端。
- 独立版与 Store 原版在 DefTerm 内部共享应用包名注册表键，因此独立版接管后，控制台委托同样自然生效。

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
```

---

## 四、100% 官方原生无损复原 SOP（Revert SOP）

如果需要彻底停用独立版，完全恢复成微软官方自带的 Windows Terminal，只需执行单条撤销命令：

```powershell
# 通过 TaskbarGuard
cd D:\Users\language_projects\go_projects\taskbarguard
go run . revert wt

# 或通过底层脚本（连带清理 PATH 并重启 Explorer）
uv run D:\Users\language_projects\go_projects\taskbarguard\scripts\wt\patch_wt_icon.py --revert --remove-path --restart-explorer
```

> **自动完成的 5 项无损复原动作**：
> 1. **注册表复原**：自动将 `HKCU\...\App Paths\wt.exe` 还原回官方商店原版路径；
> 2. **右键菜单复原**：自动将 Nilesoft Shell 的 `modify.nss` 和 `terminal.nss` 从 `.bak` 备份中完整还原，清理注入规则，并删除 `.bak` 临时文件；
> 3. **Images 资源复原**：自动将 `terminal_contrast-*.ico` 还原为原版；
> 4. **快捷方式清理**：自动清理开始菜单定制的 `.lnk` 文件；
> 5. **环境变量清理**：自动将独立版目录从用户级环境变量 `Path` 中移除。

---

## 五、常见故障排查表

| 症状 / 报错 | 根因剖析 | 标准抢救 SOP |
|---|---|---|
| 任务栏右键菜单丢失【固定到任务栏】/【取消固定】，只剩单行【关闭窗口】 | 往 `%APPDATA%\...\User Pinned\TaskBar\` 强写了未注册快捷方式导致 Taskband 注册表脱节 | 脚本已自动清理孤立快捷方式；仅通过开始菜单快捷方式承接，并在窗口运行时通过系统原生固定 |
| `[-] 注入 PE 图标失败` / 文件被占用 | WindowsTerminal 进程正在运行，Windows 锁定了 exe | 引擎已内置“原子重命名热替换”机制，自动平滑替换就位，无需手动强杀进程 |
| `Win + R wt` 依旧弹默认原版 | 注册表 `App Paths\wt.exe` 仍指向 WindowsApps | 脚本已自动重定向，或手动在 `HKCU\...\App Paths\wt.exe` 写入独立版路径与 Path |
| 右键菜单图标变了但点击仍开原版 | Nilesoft 的 `modify` 无法修改原有扩展的 `cmd` | 改用隐藏原版项（`vis.remove`）+ 动态 `item(...)` 接管的方案 |
| 右键菜单图标迟迟不刷新 | Explorer 内存缓存了旧图标 | 在桌面按住 `Ctrl` 键同时鼠标右键，或重启 Explorer |
| 任务栏仍显示原版图标 / 外部工具唤醒旧图标 | 1) 旧实例常驻且 WT 为单实例机制；2) 遗漏 102/103 资源组；3) Win11 图标缓存未离线清空 | 运行带 `--restart-explorer` 参数的脚本，引擎将全量烧录 101/102/103 并离线彻底清空 `iconcache_*.db`；在方便时重启一次终端即可彻底纯净 |
