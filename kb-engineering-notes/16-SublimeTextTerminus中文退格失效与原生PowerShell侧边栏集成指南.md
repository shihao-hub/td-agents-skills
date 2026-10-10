---
name: kb-sublime-terminus-powershell
description: Sublime Text 终端插件 Terminus 中文输入吞字/光标错位、Backspace 无法退格删除、右键侧边栏默认启动 CMD 假借 PowerShell 外壳的底层根因剖析，以及内置终端轻量化治愈与原生英文侧边栏一键拉起 Windows Terminal/PowerShell 的双轨集成实战 SOP。
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


class OpenExternalTerminalCommand(sublime_plugin.WindowCommand):
    """
    在当前选中的文件或目录上下文，唤出系统原生终端（Windows Terminal / PowerShell）
    """
    def run(self, paths=[]):
        target_dir = None
        if paths and len(paths) > 0:
            target_dir = paths[0]
        else:
            vars = self.window.extract_variables()
            target_dir = vars.get("file_path") or vars.get("folder")

        if not target_dir:
            target_dir = os.path.expanduser("~")

        # 若右键选中的是单个文件，自动退回其所在父级目录
        if os.path.isfile(target_dir):
            target_dir = os.path.dirname(target_dir)

        # 优先检测并使用现代 Windows Terminal (wt.exe)，并显式指定运行 powershell.exe
        wt_path = shutil.which("wt.exe") or os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe")
        if os.path.exists(wt_path):
            try:
                subprocess.Popen([wt_path, "-d", target_dir, "powershell.exe"], shell=False)
                return
            except Exception:
                pass

        # 降级备选：直接唤出原生 powershell.exe 独立窗口并切换至目标目录
        subprocess.Popen(
            ["powershell.exe", "-NoExit", "-Command", f"Set-Location -LiteralPath '{target_dir}'"],
            cwd=target_dir,
            shell=False
        )

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
> - 脚本内部显式传递参数 `powershell.exe` 给 `wt.exe`，避免 Windows Terminal 内部的全局默认配置为 CMD 时再次跑偏。

---

## 四、 验证与工程选型心法

### 1. 验证清单

| 验证项 | 预期行为 | 判定标准 |
|:---|:---|:---|
| **右键侧边栏菜单** | 侧边栏出现 `Open PowerShell here...` 选项 | 纯英文无缝融入 Sublime UI，无视觉违和 |
| **外部终端拉起** | 点击后弹出 Windows Terminal 窗口，提示符为 `PS <选中目录路径>>` | 100% 锁定进入 PowerShell，且工作目录一致 |
| **外部中文与补全** | 敲拼音输入中文、按 Tab 自动补全、按 Backspace 退格 | 原生 GPU 渲染，输入法候选框精确跟随，删除无残影 |
| **内置 Terminus 启动** | 点击 `Open Terminus here...` | 进入带 UTF-8 的 PowerShell 模式 |
| **内置 Terminus 退格** | 敲入任意英文字符并快速连续按 Backspace | 字符顺畅删除，屏幕无任何残留幽灵字符 |

### 2. 编辑器终端选型工程心法

* **何时必须使用外部终端（Windows Terminal）**：
  * 需要输入中文 commit 信息、中文参数或路径时；
  * 需要使用 `fzf`、`lazygit`、`k9s` 等复杂 TUI（终端用户界面）工具时；
  * 需要重度依赖 `PSReadLine` 的历史预测匹配和高阶编辑时。
* **何时适合使用内置 Terminus**：
  * 执行单行无交互命令：如 `git status`、`pytest`、`npm test`、`python script.py`；
  * 配合 Sublime Text 构建系统（`"target": "terminus_exec"`），在底部面板输出带 ANSI 彩色高亮的编译运行日志。

---

**归档说明：** 本条目沉淀自 Sublime Text 4 在 Windows 平台下集成内置终端时的典型架构踩坑，给出了兼顾纯英文 UI 美学与全功能终端能力的双轨落地标准。
