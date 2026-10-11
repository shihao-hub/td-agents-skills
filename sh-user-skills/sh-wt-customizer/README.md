---
name: sh-wt-customizer
description: Windows Terminal (wt) 免安装独立版部署、PE 图标烧录、任务栏守卫、右键菜单与 Win+R 注册表全链路接管及一键原生复原 SOP。点名使用
version: 1.0.0
created: 2026-10-11
updated: 2026-10-11
---

# sh-wt-customizer：Windows Terminal (wt) 独立版定制、图标注入与全链路接管 SOP

> **核心设计哲学与安全边界**：  
> 1. **100% 保护 Store 原版**：绝不暴力篡改或硬刚 `C:\Program Files\WindowsApps` 微软商店受保护目录，规避数字签名失效、系统更新覆盖与 SFC 冲突；  
> 2. **100% 官方原生秒级复原**：全链路采用“状态备份 + 影子重定向 + 无损回退”机制，任何时候仅需一条 `--revert` 命令即可完全回归微软官方纯净状态；  
> 3. **全链路闭环，不留盲区**：彻底攻克任务栏、开始菜单、环境变量、`Win + R` 运行框、Windows 11 右键菜单（Nilesoft Shell）及 DefTerm 调度链中的所有硬编码陷阱。

---

## 一、全链路 7 层调度机制与排障认知深度解构

在 Windows 11 环境下，为 Windows Terminal 修改图标并完全接管系统入口是一个**跨越 7 个操作系统子系统**的精密工程。若仅修改快捷方式或环境变量，必然会在 `Win + R`、右键菜单或控制台进程唤起时露馅。以下为本架构攻克的完整底层逻辑：

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

### Layer 2: PE 可执行文件图标资源物理烧录
- **原理**：使用 `rcedit.exe` 向 `WindowsTerminal.exe` 与 `wt.exe` 的 PE 资源段（`RT_GROUP_ICON` / `RT_ICON`）直接写入定制 ICO 图标。
- **【核心踩坑：文件独占锁（File Lock）】**：  
  Windows 内核对正在运行的可执行文件施加独占执行锁。如果桌面上已开有任何 Windows Terminal 窗口，`rcedit` 写入必报失败或静默无视。  
  **规则**：**在执行 PE 图标注入前，必须彻底关闭屏幕上正在运行的所有 Windows Terminal 进程**。

---

### Layer 3: 任务栏与开始菜单快捷方式守卫
- **原理**：通过 `WScript.Shell` COM 组件生成并更新快捷方式：
  - 任务栏：`%APPDATA%\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\Windows Terminal.lnk`；
  - 开始菜单：`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Windows Terminal.lnk`。
- 将快捷方式的目标指向独立版 exe，并将 `IconLocation` 指向定制 ICO 路径。
- 通过更新快捷方式文件的修改时间戳（`os.utime`），触发 Windows 外壳侦听更新。

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
- **原理**：在 Windows 11 中，控制台子系统程序（`IMAGE_SUBSYSTEM_WINDOWS_CUI = 3`，如 `agy.exe`）在启动控制台会话时，会被 Windows 内核的 **DefTerm（Default Terminal Application）** 机制自动接管并唤醒注册的 UWP 终端包。
- **现象**：当某些后台工具（如 `agy`）衍生控制台子进程时，弹出的窗口依然是 Store 原版灰白小窗。
- **应对方案**：
  1. 系统级：若希望彻底接管，可进入系统「设置」->「系统」->「开发者选项」->「终端」；
  2. 业务级防御：如 `agyquota` 项目的实践，采用 **PE Subsystem 自动缓存补丁**（将 CUI 改为 GUI 子系统 2），从根源杜绝控制台弹窗与焦点抢占。

---

### Layer 7: 右键菜单深度接管（Nilesoft Shell 与原生集成）
在使用了第三方现代右键增强工具（如 **Nilesoft Shell**）的系统中，右键菜单由其自身的 `.nss` 引擎独立渲染：
- **【核心踩坑 1：`modify` 只换皮不换心】**：  
  如果仅在 Nilesoft 中编写 `modify(find=... image=...)`，右键菜单显示的图标确实会变，但**点击它触发的后台动作依然是 Windows 11 原始的 `WindowsTerminalShellExt.dll`**，一点击依然拉起 Store 原版终端！因为 Nilesoft Shell 的 `modify()` 指令仅用于修改已有项的外观，无法覆盖其执行动作。
- **【核心踩坑 2：`find` 语法的匹配陷阱】**：  
  Nilesoft Shell 的 `find` 属性中：
  - `*foo` 表示以 `foo` 结尾；`foo*` 表示以 `foo` 开头；
  - 菜单实际文字带有 Windows 加速键后缀：`在终端中打开(T)`；
  - 若写 `find="*在终端中打开*"` 会导致解析失真、无法命中；
  - **标准语法**：必须使用**纯字符串包含匹配**：`find='在终端中打开|open in terminal'`，它会自动匹配包含该子串的任意菜单项。
- **【终极解决方案：隐藏原版 + 注入独立版启动器】**：
  在 `D:\Program Files\Nilesoft Shell\imports\modify.nss` 中：
  ```nss
  // 1. 彻底隐藏原版 Store 扩展项
  modify(mode=mode.multiple find='在终端中打开|open in terminal' vis=vis.remove)

  // 2. 注入独立版真正启动器（图标与命令双重接管）
  item(type='dir|drive|back' title='在终端中打开(T)' pos=4 image='D:\Users\Softwares\WindowsTerminal\WindowsTerminal.exe' cmd='D:\Users\Softwares\WindowsTerminal\wt.exe' arg='-d "@sel.path\."')
  ```
- **【内存缓存刷新】**：Nilesoft Shell 注入在 `explorer.exe` 进程中，修改后必须执行资源管理器重启（`Stop-Process -Name explorer -Force`）或桌面 `Ctrl + 右键` 才能释放旧缓存。

---

## 二、前置要求与物资保障机制

在任何 Windows 10/11 机器上，**无需用户提前手动下载、搜寻或解压任何物资**。技能内已集成自给自足的物资保障流水线：

1. **操作系统**：Windows 11 / Windows 10 (x64)；
2. **执行环境**：Python 3.10+（系统已装 `python` 或 `uv` 均可）；
3. **物资自愈机制（自动化流水线）**：
   - **`rcedit.exe`**：无需提前准备。脚本缺失时会自动从 GitHub Release（带国内加速镜像回退）下载 `rcedit-x64.exe` 并存入脚本目录；
   - **Windows Terminal 独立免安装版**：无需提前准备。脚本缺失时会自动查询 GitHub API 获取最新版 `Microsoft.WindowsTerminal_xxx_x64.zip`，下载并解压到目标目录，且自动将路径置顶写入用户环境变量 `Path`；
   - **内置图标库**（已随本技能 `icons/` 目录分发入库，无需额外下载）：
     - `pure_dark.ico`：极简深黑哑光（推荐，极客质感）；
     - `titanium.ico`：钛金极客银白；
     - `underlit_chrome.ico`：机械发光赛博；
     - `dark_blue.ico`：经典深海微光；
     - `cyan_matrix.ico`：极客青矩阵。

---

## 三、部署执行 SOP（两种模式）

### 模式 A：新电脑 AI 全自治一键极速部署（推荐，0 手工介入）

**适用场景**：任何全新机器、未安装过独立版终端的电脑、或交给 AI 自动完成全流程。

关闭当前打开的所有终端窗口，执行**单条一键自适应命令**：

```powershell
# 推荐（带 uv）：
uv run D:\path\to\sh-wt-customizer\scripts\patch_wt.py --auto-setup --style pure_dark --restart-explorer

# 若未装 uv，纯 Python 环境亦可直接执行：
python D:\path\to\sh-wt-customizer\scripts\patch_wt.py --auto-setup --style pure_dark --restart-explorer
```

> **该命令在后台全自动完成的闭环动作**：
> 1. **自动获取 rcedit**：检测并自动从官方源下载 `rcedit.exe`；
> 2. **自动获取免安装终端**：查询 GitHub 最新 Release，自动下载并解压至 `D:\Users\Softwares\WindowsTerminal`（若无 D 盘则智能落地至 `%LOCALAPPDATA%\Programs\WindowsTerminal`）；
> 3. **自动配置环境变量**：通过 Win32 API 将安装路径置顶写入用户级 `Path` 并广播系统环境变更；
> 4. **物理烧录 PE 资源**：使用选定的 `pure_dark.ico` 图标烧录至 `WindowsTerminal.exe` 与 `wt.exe` 的 PE 资源段；
> 5. **接管 Win + R 运行框**：在注册表 `HKCU\...\App Paths\wt.exe` 写入独立版路径，阻断系统向 Store 版的偏航；
> 6. **生成定制快捷方式**：同步更新任务栏与开始菜单的高清深黑图标快捷方式；
> 7. **右键菜单自适应接管**：自动检测 Nilesoft Shell，若已安装则安全生成 `.bak` 备份并注入独立版接管项；若未安装则平稳跳过；
> 8. **重启 Explorer 刷新缓存**：平稳重启 Windows 资源管理器，所有入口即刻热生效。

---

### 模式 B：已有环境本地指定部署

**适用场景**：本地已手动下载解压好免安装终端，或想指定任意自定义目录。

```powershell
uv run scripts/patch_wt.py --target-dir "D:\CustomPath\WindowsTerminal" --style pure_dark --restart-explorer
```

---

### 步骤 4：全功能验收测试

无论采用哪种模式，完成后即可立即验收 4 大入口：
1. **任务栏测试**：点击任务栏图标，启动窗口与任务栏高亮图标均为深黑极客图标；
2. **Win + R 测试**：按 `Win + R` 输入 `wt` 回车，直接唤起定制独立版终端；
3. **右键菜单测试**：在任意文件夹或空白处右键，查看「在终端中打开(T)」显示深黑图标，点击后直接在当前路径打开独立版终端；
4. **配置继承测试**：历史命令记录、自定义配色和 settings.json 完好继承。

---

## 四、100% 官方原生无损复原 SOP（Revert SOP）

如果未来需要彻底停用独立版，完全恢复成微软官方自带的 Windows Terminal，只需执行单条撤销命令：

```powershell
uv run D:\path\to\sh-wt-customizer\scripts\patch_wt.py --revert --remove-path --restart-explorer
```

> **自动完成的 4 项无损复原动作**：
> 1. **注册表复原**：自动将 `HKCU\...\App Paths\wt.exe` 还原回官方商店原版路径；
> 2. **右键菜单复原**：自动将 Nilesoft Shell 的 `modify.nss` 和 `terminal.nss` 从 `.bak` 备份中完整还原，清理注入规则，并删除 `.bak` 临时文件；
> 3. **快捷方式清理**：自动清理任务栏与开始菜单定制的 `.lnk` 文件；
> 4. **环境变量清理**：自动将独立版目录从用户级环境变量 `Path` 中移除；
> 5. **外壳刷新**：自动清除图标缓存并平稳重启 Explorer。
> 
> *（可选）* 直接物理删除 `WindowsTerminal` 文件夹即可。系统恢复为出厂纯净 Store 终端，原版文件从未受过任何破坏。

---

## 五、脚本参数与常见故障排查清单

### 脚本指令速查

```powershell
# 1. 查看可用图标风格
uv run scripts/patch_wt.py --list-styles

# 2. 新电脑一键全自动部署（AI 推荐标准指令）
uv run scripts/patch_wt.py --auto-setup --style pure_dark --restart-explorer

# 3. 指定自定义安装目录与 rcedit 路径
uv run scripts/patch_wt.py --target-dir "C:\Tools\WindowsTerminal" --rcedit "C:\Tools\rcedit.exe" --style pure_dark --restart-explorer

# 4. 一键彻底复原原生状态（连带清理 PATH）
uv run scripts/patch_wt.py --revert --remove-path --restart-explorer
```

### 常见故障排查表

| 症状 / 报错 | 根因剖析 | 标准抢救 SOP |
|---|---|---|
| `[-] 注入 PE 图标失败` | WindowsTerminal 进程正在运行，Windows 锁定了 exe | 关闭桌面上所有终端窗口后重新执行脚本 |
| `Win + R wt` 依旧弹默认原版 | 注册表 `App Paths\wt.exe` 仍指向 WindowsApps | 运行脚本自动重定向，或手动在 `HKCU\...\App Paths\wt.exe` 写入独立版路径 |
| 右键菜单图标变了但点击仍开原版 | Nilesoft 的 `modify` 无法修改原有扩展的 `cmd` | 改用隐藏原版项（`vis.remove`）+ 动态 `item(...)` 接管的方案 |
| 右键菜单图标迟迟不刷新 | Explorer 内存缓存了旧图标 | 在桌面按住 `Ctrl` 键同时鼠标右键，或重启 Explorer |
| 外部程序启动时仍唤醒原版 | Windows 11 DefTerm 默认终端绑定了 UWP 包 | 参考 `agyquota` 实践，为对应外部 CUI 程序打 Subsystem 2 GUI 补丁 |
