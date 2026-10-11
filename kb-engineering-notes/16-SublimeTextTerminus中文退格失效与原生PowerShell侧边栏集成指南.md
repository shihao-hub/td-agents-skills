---
name: kb-sublime-terminus-powershell
description: Sublime Text 终端插件 Terminus 中文输入吞字/光标错位、Backspace 无法退格删除、右键侧边栏默认启动 CMD 假借 PowerShell 外壳的底层根因剖析，以及内置终端轻量化治愈、原生英文侧边栏经 PATH 优先解析拉起独立定制版 Windows Terminal/PowerShell 的双轨集成实战 SOP。
---

# Sublime Text Terminus 中文退格失效与原生 PowerShell 侧边栏集成指南

## 一、 现象与报错直击

1. **中文输入法（IME）按键截断与 CJK 双宽字符错位**：
   - 在 Sublime Text 的 Terminus 内置终端中切换中文输入法敲拼音时，输入法的预编辑候选状态与 Terminus 的物理按键监听严重冲突，导致拼音直接上屏、字词丢失或重复吞字；
   - 输入中文后，由于中文字符占用 2 个终端单元格（Double-width），Terminus 内置终端引擎（pyte/pty）与 Sublime Text 文本视图的光标步进脱节，出现光标定位偏移、汉字被半边覆盖或渲染残影。
2. **Backspace（退格键）完全无法删除字符**：
   - 在终端命令行输入任何英文字符或路径，按下 `Backspace` 键毫无反应，或者光标向左移动但原本的字符依然停留在屏幕上无法被擦除，陷入“敲错一个字母只能整行重输”的恶劣交互体验。
3. **右键侧边栏打开终端，看似 PowerShell 实际是 CMD.exe**：
   - 在 Sublime Text 侧边栏右键文件夹点击 `Open Terminus here...`，弹出的命令行前缀为 `C:\Users\xxx>`（**没有** PowerShell 标志性的 `PS` 前缀）；
   - 在较新的 Windows 10/11 系统中，因为系统默认终端托管机制，该 CMD 经常被包装在一个黑底、现代标签页的 Windows Terminal 窗口中运行，极易让开发者产生“打开了 PowerShell 外壳，但里面跑的却是 CMD”的认知混淆。
4. **非官方扩展菜单的中文本地化破坏原生英文一致性**：
   - Sublime Text 官方原生未做界面全域本地化，若在侧边栏右键菜单中生硬插入中文项（如“在外部终端打开”），会在全英文的上下文环境（`Open Containing Folder...`、`Find in Folder...`）中显得格格不入。

---

## 二、 底层根因剖析

### 1. 架构死局：Sublime Text 文本引擎与虚拟终端字符网格的本质冲突

Sublime Text 是顶级的文本排版编辑器，但**不是原生的终端仿真器**。Terminus 在其内部运行依赖于巧妙但脆弱的“模拟翻译层”：

```text
[物理键盘击键 / IME 输入法]
         │
         ▼
[Sublime Text View (文本编辑视图)] ─── (无系统 IME 组合态暴露 API) ───┐
         │                                                            │
         ▼                                                            ▼
[Terminus 事件监听 (on_text_command)]                           输入法拼音被直接
         │                                                      当作终端原始字节发送
         ▼                                                            │
[pyte (Python 模拟 VT100/ANSI 状态机)]                                 ▼
  ├── 严格依赖 2D 网格单元（Cell Grid）：英文字符 1 列，中文字符 2 列     【汉字乱窜/吞字】
  └── 计算光标绝对坐标 (Row, Col)
         │
         ▼
[Sublime Text TextPoint 偏移量重绘] ─── (双宽字符步进换算脱节) ───► 【光标错位/残影】
```

- **缺乏 IME API 支持**：现代专业终端（如 VS Code 内置终端基于的 `xterm.js`、Windows Terminal）能够完整监听操作系统的 `CompositionStart`、`CompositionUpdate`、`CompositionEnd` 事件，并在输入法上屏前挂起终端输入。Sublime Text 的 Python API **根本没有暴露 IME 组合态接口**，Terminus 只能粗暴截获按键，导致输入法候选过程被强行打断；
- **字符网格与文本流的不匹配**：ANSI 终端标准要求每个汉字独占 2 个等宽单元格，而 Sublime Text 基于字符逻辑偏移量渲染。当终端试图擦除一个 2 列字符时，Sublime 内部的 TextPoint 选区缩进与虚拟终端光标步进不一致，退格或覆盖时必然出现留存残影。

### 2. Backspace 删不动的真正罪魁祸首：PowerShell `PSReadLine`

在 Windows 平台下，PowerShell 默认加载并启用了 **`PSReadLine`** 模块：
- `PSReadLine` 负责实现命令行的语法高亮、历史搜索、预测补全与复杂行编辑。它为了接管输入输出，自行实现了一套控制台屏幕重绘算法；
- 在真实的 Windows Console / Windows Terminal 中，`PSReadLine` 运作良好；但当它面对 Terminus 通过 WinPTY / ConPTY 封装的伪终端管道时，其针对控制字符（`\x08` BackSpace 与 `\x7f` DEL）的重绘响应会产生管道死锁与缓冲区脱节；
- 结果就是：底层的 PowerShell 实际上可能已经收到了退格信号，但屏幕渲染被 `PSReadLine` 阻断，导致屏幕上的字符纹丝不动。

### 3. Terminus 默认配置锁定 `"Command Prompt"`

在 Terminus 的默认包配置文件（`Terminus.sublime-package` 中的 `Terminus.sublime-settings`）中，Windows 平台默认 Shell 明确硬编码为：
```json
"default_config": {
    "linux": null,
    "osx": null,
    "windows": "Command Prompt"
}
```
如果没有在用户的 `Packages/User/Terminus.sublime-settings` 中显式覆盖，任何通过侧边栏或命令面板触发的缺省终端，都会默认唤起 `cmd.exe`。

### 4. Windows 11 控制台委托（Console Handoff）造成的视觉欺骗

Windows 11 引入了“默认终端应用程序（Default Terminal Application）”的全局委托机制：
- 当一个程序请求启动传统的 `cmd.exe` 控制台子系统时，操作系统不再拉起旧版的 `conhost.exe` 黑框，而是自动将其托管到 **Windows Terminal**（`wt.exe`）的多标签页窗口内；
- 很多开发者习惯将 Windows Terminal 称为“PowerShell 窗口”（因为其首个标签页通常是 PowerShell）。当看到 Windows Terminal 外壳弹出来、但里面的提示符却是 `C:\Users\xxx>` 时，就会产生“为什么我的 PowerShell 变成了 CMD”的错觉。

### 5. 独立免安装版 WT 接管后的新现实：机器上不止一个 `wt.exe`

执行过自定义图标 / 任务栏守卫（见 `sh-wt-customizer`）的机器上，磁盘里同时躺着**两个 `wt.exe`**：

| 身份 | 本机路径 | 性质 |
|:---|:---|:---|
| **独立定制版（真身）** | `D:\Users\Softwares\WindowsTerminal\wt.exe` | 官方 GitHub Releases 解压的纯 Win32 免安装版，图标已定制、目录可写 |
| **Store 沙箱原版（影子）** | `%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe` → `C:\Program Files\WindowsApps\Microsoft.WindowsTerminal_*\wt.exe` | 0 字节 AppExecutionAlias 重解析点，指向只读、受签名完整性保护的 MSIX 包 |

- **谁被叫起来，完全由 PATH 顺序决定**：定制脚本已把独立版目录插到用户级 `Path` 最顶端（优先于 `%LOCALAPPDATA%\Microsoft\WindowsApps`），并把 `HKCU\...\App Paths\wt.exe` 一并重定向；
- **`shutil.which` / `os.path.exists` 天生分不清真身与影子**（本机实测）：影子入口表现为 `os.path.isfile()=True`、`os.path.getsize()=0`、`os.path.islink()=False` —— 它是 AppExecutionAlias 重解析点而非符号链接，任何“文件存在性检查”都会把它当合法终端放行，**唯一可行判据是路径中是否含 `\WindowsApps\`**；
- **因此集成代码里任何形如 `os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe")` 的硬编码兜底都是致命反模式**：一旦它被触发，用户就会被悄悄打回未定制的 Store 原版 —— 图标、版本、Nilesoft 右键菜单、DefTerm 委托全部露馅，且现象是“偶尔变回原版”这种极难复现的玄学；
- **正确姿势**：只把 `wt.exe` 这个**名字**交给 PATH 解析，再对「调用方进程 PATH 陈旧」与「只命中 Store 影子」两类失效做防御（见轨道二代码）；
- **DefTerm 设为 conhost 不影响本链路**：独立版定制 SOP 推荐把默认终端应用程序改回 conhost 以阻断后台静默脚本弹窗抢焦点，但那是管“无人托管的新控制台委托”，与代码里**显式点名 `wt.exe`** 是两条独立通路 —— 显式调用永远秒开定制版 WT。

---

## 三、 标准解决与双轨集成 SOP

针对上述问题，工程上的最佳实践是**双轨并行**：
1. **轨道一（轻量化治愈）**：将内置 Terminus 改造为纯净 ASCII / 脚本执行器，治愈退格键 Bug 并强制 UTF-8，仅用来跑构建与看日志；
2. **轨道二（原生外部直通）**：在 Sublime Text 侧边栏注入符合原生 UI 风格的 `Open PowerShell here...` 菜单，一键唤出真正的 Windows Terminal / PowerShell，彻底绕开内嵌终端的所有字符限制。

---

### 轨道一：Terminus 内置终端轻量化配置

在 Sublime Text 用户配置目录中新建并写入 `Terminus.sublime-settings`：
- **配置文件路径**：`%APPDATA%\Sublime Text 3\Packages\User\Terminus.sublime-settings`（Sublime Text 4 兼容此路径）

```json
{
    // 1. 将 Windows 默认终端明确指派为 PowerShell
    "default_config": {
        "linux": null,
        "osx": null,
        "windows": "PowerShell"
    },

    // 2. 覆盖并定制 PowerShell 启动参数：卸载 PSReadLine + 强制 UTF-8
    "shell_configs": [
        {
            "name": "PowerShell",
            "cmd": [
                "powershell.exe",
                "-NoExit",
                "-Command",
                "chcp 65001 >$null; Remove-Module PSReadLine -ErrorAction SilentlyContinue"
            ],
            "env": {
                "LANG": "zh_CN.UTF-8",
                "PYTHONIOENCODING": "utf-8"
            },
            "enable": true,
            "platforms": ["windows"]
        },
        {
            "name": "Command Prompt",
            "cmd": "cmd.exe",
            "env": {},
            "enable": true,
            "platforms": ["windows"]
        },
        {
            "name": "PowerShell (Raw)",
            "cmd": "powershell.exe",
            "env": {},
            "enable": true,
            "platforms": ["windows"]
        },
        {
            "name": "WSL Login Shell",
            "cmd": "wsl.exe",
            "env": {},
            "enable": true,
            "platforms": ["windows"]
        }
    ]
}
```

#### 关键参数原理解析：
* `Remove-Module PSReadLine -ErrorAction SilentlyContinue`：在 PowerShell 启动瞬间静默卸载行编辑模块。**执行此操作后，Terminus 内按下 Backspace 删除字符立即恢复 100% 灵敏**；
* `chcp 65001 >$null`：强制将控制台活动代码页设置为 UTF-8，彻底解决非 ASCII 路径和日志输出时的多字节乱码问题。

---

### 轨道二：Sublime 原生右键侧边栏扩展（直通 Windows Terminal）

为解决中文输入法与重度命令行交互诉求，使用 2 个原子文件在侧边栏扩展纯正英文的 `Open PowerShell here...` 菜单。

#### 1. 编写后端执行插件：`open_external_terminal.py`
创建文件于：`%APPDATA%\Sublime Text 3\Packages\User\open_external_terminal.py`

```python
import os
import shutil
import subprocess
import sublime
import sublime_plugin

WT_EXE = "wt.exe"
WINDOWSAPPS_MARK = "\\windowsapps\\"


def _is_store_shadow(exe_path):
    """Store 版 wt.exe 被关在受保护的 WindowsApps 沙箱内，是未定制的影子入口"""
    return WINDOWSAPPS_MARK in exe_path.lower()


def _which_in_path_value(exe_name, path_value):
    for raw_dir in path_value.split(os.pathsep):
        directory = raw_dir.strip().strip('"')
        if not directory:
            continue
        candidate = os.path.join(directory, exe_name)
        if os.path.isfile(candidate):
            return candidate
    return None


def _registry_path_value():
    """回读注册表 PATH：调用方进程启动早于 PATH 变更时，os.environ 只是陈旧快照"""
    if os.name != "nt":
        return ""
    import winreg

    locations = (
        (winreg.HKEY_CURRENT_USER, "Environment"),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        ),
    )
    collected = []
    for hive, sub_key in locations:
        try:
            with winreg.OpenKey(hive, sub_key) as key:
                value, _ = winreg.QueryValueEx(key, "Path")
        except OSError:
            continue
        collected.append(os.path.expandvars(value))
    return os.pathsep.join(collected)


def resolve_wt_exe():
    """优先取 PATH 里的 wt.exe（PATH 顶端即独立定制版），拒绝回退到 Store 沙箱影子入口"""
    from_path = shutil.which(WT_EXE)
    if from_path and not _is_store_shadow(from_path):
        return from_path

    from_registry = _which_in_path_value(WT_EXE, _registry_path_value())
    if from_registry and not _is_store_shadow(from_registry):
        return from_registry

    return from_path or from_registry


class OpenExternalTerminalCommand(sublime_plugin.WindowCommand):
    """
    在当前选中的文件或目录上下文，唤出系统原生终端（Windows Terminal / PowerShell）
    """

    def run(self, paths=[]):
        target_dir = self._target_dir(paths)

        # 只把 wt.exe 这个"名字"交给 PATH 解析；严禁硬编码
        # %LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe —— 那是未定制的 Store 影子入口
        wt_exe = resolve_wt_exe()
        if wt_exe:
            try:
                # 显式传递 powershell.exe，避免 WT 全局默认 Profile 被改成 CMD 时再次跑偏
                subprocess.Popen([wt_exe, "-d", target_dir, "powershell.exe"], shell=False)
                return
            except OSError:
                pass

        # 降级备选：直接唤出原生 powershell.exe 独立窗口并切换至目标目录
        subprocess.Popen(
            [
                "powershell.exe",
                "-NoExit",
                "-Command",
                f"Set-Location -LiteralPath '{target_dir}'",
            ],
            cwd=target_dir,
            shell=False,
        )

    def _target_dir(self, paths):
        if paths and len(paths) > 0:
            target_dir = paths[0]
        else:
            variables = self.window.extract_variables()
            target_dir = variables.get("file_path") or variables.get("folder")

        if not target_dir:
            target_dir = os.path.expanduser("~")

        # 若右键选中的是单个文件，自动退回其所在父级目录
        if os.path.isfile(target_dir):
            target_dir = os.path.dirname(target_dir)

        return target_dir

    def is_visible(self, paths=[]):
        return True
```

#### 2. 注入侧边栏英文菜单：`Side Bar.sublime-menu`
创建文件于：`%APPDATA%\Sublime Text 3\Packages\User\Side Bar.sublime-menu`

```json
[
    {
        "caption": "Open PowerShell here...",
        "command": "open_external_terminal",
        "args": {"paths": []}
    }
]
```

> **设计要点**：
> - 命名严格采用 Sublime Text 原生命名规范 `Open PowerShell here...`（带省略号 `...` 表示将调起外部交互操作），与系统的 `Open Containing Folder...`、`Find in Folder...` 在视觉、语言与留白风格上保持绝对一致；
> - **只解析名字、不写死路径**：`shutil.which("wt.exe")` 优先，PATH 顶端即独立定制版；硬编码 `WindowsApps` 兜底会在 PATH 失效时把用户打回未定制的 Store 原版；
> - **双防线抗 PATH 失效**：先看进程 `os.environ['PATH']`，若只命中 Store 影子（或干脆没命中），再回读注册表 `HKCU\Environment` + `HKLM\...\Session Manager\Environment` 的 `Path` 重新解析；解析结果一旦落在 `\WindowsApps\` 内即判定为影子入口并拒绝；
> - **改完 PATH 必须重启 Sublime Text**：插件宿主是独立子进程，`os.environ` 只是它启动那一刻的快照，注册表回读防线只兜底、不替代重启；
> - 脚本内部显式传递参数 `powershell.exe` 给 `wt.exe`，避免 Windows Terminal 内部的全局默认配置为 CMD 时再次跑偏（若 WT 默认 Profile 已换成别的 Shell，此处按需同步）。

---

## 四、 验证与工程选型心法

### 1. 验证清单

| 验证项 | 预期行为 | 判定标准 |
|:---|:---|:---|
| **右键侧边栏菜单** | 侧边栏出现 `Open PowerShell here...` 选项 | 纯英文无缝融入 Sublime UI，无视觉违和 |
| **外部终端拉起** | 点击后弹出 Windows Terminal 窗口，提示符为 `PS <选中目录路径>>` | 100% 锁定进入 PowerShell，且工作目录一致 |
| **拉起的是独立定制版** | 同机存在两个 `wt.exe` 时点击菜单 | 解析结果为 `D:\Users\Softwares\WindowsTerminal\wt.exe`（非 `%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe`），窗口/任务栏图标为定制款 |
| **外部中文与补全** | 敲拼音输入中文、按 Tab 自动补全、按 Backspace 退格 | 原生 GPU 渲染，输入法候选框精确跟随，删除无残影 |
| **内置 Terminus 启动** | 点击 `Open Terminus here...` | 进入带 UTF-8 的 PowerShell 模式 |
| **内置 Terminus 退格** | 敲入任意英文字符并快速连续按 Backspace | 字符顺畅删除，屏幕无任何残留幽灵字符 |

### 2. 外部终端拉起的三个必踩坑

| 坑 | 现象 | 正解 |
|:---|:---|:---|
| **硬编码 `WindowsApps` 兜底** | 大多数时候正常，偶尔变回旧图标 / 旧版本的“原版终端” | 只传 `wt.exe` 名字交由 PATH 解析，并显式拒绝 `\WindowsApps\` 内命中 |
| **调用方进程 PATH 陈旧** | 明明已把独立版置顶 PATH，脚本却还是拉出原版 | 回读注册表 `HKCU\Environment` / `HKLM\...\Session Manager\Environment` 的 `Path` 重新解析；长效解法是重启调用方进程（Sublime 需重启，Explorer 需接收 `WM_SETTINGCHANGE`） |
| **在 Git Bash 里手工 `PATH="C:/..."` 造环境验证** | `shutil.which("wt.exe")` 诡异地返回 `None`，误以为解析逻辑坏了 | MSYS2 的 path-list 转换会把**盘符的冒号**当成路径列表分隔符：`PATH="C:/Users/..."` 传到子进程变成 `'C;D:\Program Files\Git\Users\...'`，两段都不存在。**验证 PATH 行为请在 PowerShell 里做，勿在 Git Bash 用赋值式 PATH** |
| **误把 DefTerm 当成拦路虎** | 为“让 `wt.exe` 能被叫起来”而把默认终端改回 WT，结果后台脚本又开始弹窗抢焦点 | 澄清两条独立通路：DefTerm 只管无人托管的新控制台委托，**显式点名 `wt.exe` 不受其影响**，开发者环境应保持 conhost |

### 3. 编辑器终端选型工程心法

* **何时必须使用外部终端（Windows Terminal）**：
  * 需要输入中文 commit 信息、中文参数或路径时；
  * 需要使用 `fzf`、`lazygit`、`k9s` 等复杂 TUI（终端用户界面）工具时；
  * 需要重度依赖 `PSReadLine` 的历史预测匹配和高阶编辑时。
* **何时适合使用内置 Terminus**：
  * 执行单行无交互命令：如 `git status`、`pytest`、`npm test`、`python script.py`；
  * 配合 Sublime Text 构建系统（`"target": "terminus_exec"`），在底部面板输出带 ANSI 彩色高亮的编译运行日志。

---

**归档说明：** 本条目沉淀自 Sublime Text 4 在 Windows 平台下集成内置终端时的典型架构踩坑，给出了兼顾纯英文 UI 美学与全功能终端能力的双轨落地标准。

**后续更新（本机 WT 已换为独立定制版）：** 原版文档的 `open_external_terminal.py` 曾以 `%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe` 作硬编码兜底，在 WT 独立版接管后已属反模式（详见 二.5）；现已改为**只解析名字 + 注册表 PATH 回读 + Store 影子拒绝**，侧边栏拉起 100% 命中定制版。完整的独立版部署/图标注入/PATH 与 App Paths 接管/DefTerm 治理见 `sh-wt-customizer`。
