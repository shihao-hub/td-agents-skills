---
name: kb-autohotkey-app-switcher
description: Windows 单手盲切与抽屉式 Toggle 应用窗口的 AutoHotkey v2 自动化实践指南。解决任务栏应用过多鼠标甩动疲劳、原生 Alt+Tab 轮转不可预测、PowerToys 强制冷启动应用、Chrome PWA 独立应用与浏览器底层进程冲突、原生客户端/PWA/普通Chrome固定标签页「三模优先级平滑降级」调度，以及终端 Job Object 强杀与 WMI 脱钩热重载 SOP。
id: "014"
domain: win
scope: ahk
type: flow
slug: "Win单手盲切与抽屉式Toggle窗口AHK配置"
status: verified
created: "2026-09-22"
last_verified: "2026-10-27"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: true
---

# Windows 单手盲切与抽屉式 Toggle 应用窗口自动化配置指南 (AutoHotkey v2)

> 本指南针对多常驻开发工具（IDE、终端、Git客户端、IM等）场景下，解决任务栏图标拥挤、鼠标大幅横移甩手腕、Windows 原生 Alt+Tab 记忆成本高、PowerToys 键盘管理器强制冷启动应用的痛点，提供基于 **AutoHotkey v2** 的终极纯左手快捷键 Toggle 解决方案。

---

## 一、现象与核心痛点直击

日常开发工作流中常驻 8~10+ 个应用（Zed、Sublime Text/Merge、VS Code、IDEA、Windows Terminal、Cursor、Antigravity IDE、Chrome、飞书等）时，传统窗口切换方式面临核心矛盾：

1. **鼠标大幅横移与手腕疲劳**：任务栏排列过长时，鼠标需要从屏幕左侧主力区频繁横跨大半个屏幕甩到右端点击，一天数十上百次切换，手腕负荷极大；若全部挤在左侧，图标严重挤压，辨识与瞄准成本极高。
2. **Windows 原生 Alt+Tab 缺乏肌肉记忆**：基于 MRU（最近使用时间）线性轮替，次频使用的工具常被挤到很靠后的层级，每次需要按不同次数的 Tab 才能切中目标，无法形成稳定的盲切手感。
3. **PowerToys Keyboard Manager（“运行程序”）的缺陷**：
   - **强制冷启动**：若目标软件未开启，按快捷键会强行冷启动程序，容易误触卡顿；
   - **重复弹出新窗口**：对于 Windows Terminal 等应用，每次调用都会强行开启一个全新的终端窗口；
   - **不支持抽屉式 Toggle**：再次按下相同快捷键无法自动最小化收起。

---

## 二、底层机制剖析：为什么不需要配路径与全局查找原理

很多用户习惯了“启动器（Launcher）”思维，误以为必须配置 `D:\Software\...\xxx.exe` 路径。而本方案的本质是**窗口切换器（Window Switcher & Toggler）**。

### 1. 窗口管理器（DWM / Win32 子系统）与全局句柄登记簿
当任何软件在 Windows 中启动并创建顶层可见界面时，系统内核就会在桌面窗口列表登记：
- **HWND（窗口句柄）**：全局唯一的十六进制标识；
- **PID / 进程名**：如 `Code.exe`、`idea64.exe`；
- **窗口状态**：激活、后台、最小化。

### 2. AHK 窗口过滤匹配机制
脚本中使用 `ahk_exe <进程名.exe>`：
```autohotkey
ToggleApp(exeName) {
    target := 'ahk_exe ' . exeName
    if !WinExist(target) {
        return ; 软件未开 -> 彻底静默，绝不启动
    }
    ; ...
}
```
- AHK 底层通过 `EnumWindows` + `GetWindowThreadProcessId` 直接向系统查询是否存在该进程名的窗口，查询耗时不到 1 毫秒；
- **无需关注安装路径**：不论装在 C 盘、D 盘、绿色免安装版还是移动硬盘，只要在内存中有窗口即可全局瞬间捕获；
- **状态机流转**：
  - **未运行**：直接 return，保持彻底静默，绝不自动冷启动；
  - **在后台**：调用 `WinActivate` 瞬间激活置顶并获取焦点；
  - **在前台**：再次按下相同的快捷键，调用 `WinMinimize` 最小化收起（抽屉式呼之即来、挥之即去）；
  - **多窗口场景**：同一软件打开多个实例时，通过 `WinGetList` 依次轮替各个子窗口，全部查看完毕后最后一次按下最小化。

---

## 三、标准实现与配置 SOP

### 步骤 1：安装 AutoHotkey v2
AutoHotkey 常驻后台内存仅 2~3MB，可通过以下任意方式安装：
- **命令行一键安装**：
  ```powershell
  winget install AutoHotkey.AutoHotkey
  ```
- **官网下载**：访问 [AutoHotkey 官网](https://www.autohotkey.com/) 下载 v2.0+ 安装包。

### 步骤 2：部署核心脚本到系统启动目录（实现开机自启）
Windows 用户自启目录快捷路径为 `shell:startup`（对应 `C:\Users\<用户名>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup`）。

直接在该目录下创建或编辑 `app_switcher.ahk`，写入完整脚本：

```autohotkey
#Requires AutoHotkey v2.0
#SingleInstance Force

; ========================================================
; 窗口切换与最小化 Toggle 核心函数
; 1. 软件未运行 -> 彻底无反应（绝不自动冷启动）
; 2. 软件在后台 -> 激活并置顶到最前
; 3. 软件当前已在最前 -> 再次按下则最小化收起
; 4. 多窗口处理：若有多个窗口，依次轮换，最后一个最小化收起
; ========================================================
ToggleWin(target, runCmd := "") {
    ; 1. 软件未运行
    if !WinExist(target) {
        if (runCmd != "") {
            try Run(runCmd)
        }
        return
    }

    ; 2. 如果当前激活窗口正是该目标
    if WinActive(target) {
        winList := WinGetList(target)
        ; 单窗口：直接最小化收起
        if (winList.Length <= 1) {
            WinMinimize('A')
            return
        }
        
        ; 多窗口：依次轮换各个窗口，轮换完最后一个后最小化收起
        currentId := WinGetID('A')
        nextId := 0
        loop winList.Length {
            if (winList[A_Index] = currentId) {
                if (A_Index < winList.Length) {
                    nextId := winList[A_Index + 1]
                }
                break
            }
        }
        
        if (nextId) {
            WinActivate('ahk_id ' . nextId)
        } else {
            WinMinimize('ahk_id ' . currentId)
        }
    } else {
        ; 3. 软件在后台：立即置顶激活
        WinActivate(target)
    }
}

; 基础进程名快速包装
ToggleApp(exeName) => ToggleWin('ahk_exe ' . exeName)

; ========================================================
; 文件资源管理器专用 Toggle 函数 (Explorer)
; 1. 窗口未运行 -> 启动打开资源管理器 (Run "explorer.exe")
; 2. 窗口在后台 -> 激活并置顶到最前
; 3. 窗口已在最前 -> 再次按下则最小化收起 (抽屉式 Toggle)
; 4. 多窗口处理 -> 依次轮换各个文件夹窗口，最后一个最小化收起
; 注意：不能使用 ahk_exe explorer.exe（会误匹配桌面与任务栏）
; 必须使用 ahk_class CabinetWClass 精准匹配文件夹窗口
; ========================================================
ToggleExplorer() {
    target := 'ahk_class CabinetWClass ahk_exe explorer.exe'
    
    ; 1. 未打开任何资源管理器窗口：直接启动打开
    if !WinExist(target) {
        Run('explorer.exe')
        return
    }

    ; 2. 如果当前激活窗口正是资源管理器
    if WinActive(target) {
        winList := WinGetList(target)
        ; 单窗口：直接最小化收起
        if (winList.Length <= 1) {
            WinMinimize('A')
            return
        }
        
        ; 多窗口：依次轮换各个窗口，轮换完最后一个后最小化收起
        currentId := WinGetID('A')
        nextId := 0
        loop winList.Length {
            if (winList[A_Index] = currentId) {
                if (A_Index < winList.Length) {
                    nextId := winList[A_Index + 1]
                }
                break
            }
        }
        
        if (nextId) {
            WinActivate('ahk_id ' . nextId)
        } else {
            WinMinimize('ahk_id ' . currentId)
        }
    } else {
        ; 3. 资源管理器在后台：立即置顶激活
        WinActivate(target)
    }
}

; ========================================================
; ========================================================
; Tinta 专用 Toggle 函数 (Markdown 阅读器，兼容 tina.exe 拼写)
; 1. 软件未运行 -> 启动打开 Tinta (若存在便携路径则直接拉起)
; 2. 软件在后台 -> 激活并置顶到最前
; 3. 软件已在最前 -> 再次按下则最小化收起 (抽屉式 Toggle)
; 4. 多窗口处理 -> 依次轮换各个窗口，最后一个最小化收起
; ========================================================
ToggleTinta() {
    target := WinExist('ahk_exe tina.exe') ? 'ahk_exe tina.exe' : 'ahk_exe tinta.exe'
    
    ; 1. 未运行：直接启动打开
    if !WinExist(target) {
        path := FileExist('D:\Users\Softwares\Tinta\tinta.exe') ? 'D:\Users\Softwares\Tinta\tinta.exe' : (FileExist('D:\Users\Softwares\Tinta\tina.exe') ? 'D:\Users\Softwares\Tinta\tina.exe' : 'tinta.exe')
        try Run(path)
        return
    }

    ; 2. 软件运行中：交由通用 ToggleApp 轮替/最小化
    exeName := WinExist('ahk_exe tina.exe') ? 'tina.exe' : 'tinta.exe'
    ToggleApp(exeName)
}

; 全局纯左手单手快捷键映射配置（! 代表 Alt 键）
; 提示：以下为常用工具全量映射字典；个人日常若暂不使用某软件，可在行首加 `;` 注释（如 Cursor、IDEA 等）
; ========================================================

; Alt + 1 -> Zed 编辑器
!1::ToggleApp('Zed.exe')

; Alt + 2 -> Sublime Merge
!2::ToggleApp('sublime_merge.exe')

; Alt + 3 -> Sublime Text
!3::ToggleApp('sublime_text.exe')

; Alt + G -> Antigravity IDE
!g::ToggleApp('Antigravity IDE.exe')

; Alt + C -> Cursor AI 代码编辑器
!c::ToggleApp('Cursor.exe')

; ========================================================
; DeepSeek Harness 专用三模 Toggle 函数 (桌面端 -> PWA独立应用 -> 普通Chrome专属标签页直达)
; 1. 优先检测原生桌面客户端 (ahk_exe DeepSeek Harness.exe) 窗口
;    - 若存在 -> 执行 Toggle (置顶/最小化/轮换)
; 2. 原生桌面端不存在时 -> 检测 Chrome PWA 独立窗口
;    - 匹配标识: "DeepSeek Harness ahk_exe chrome.exe"
;    - 严密反向排除: 排除包含 " - Google Chrome" 的普通标签页，绝不串台
;    - 若存在 -> 执行 Toggle (置顶/最小化/轮换)
; 3. 前两者均不存在时 -> 接管普通 Chrome 浏览器中的本地标签页 (127.0.0.1:11111)
;    - 联动 DSH Tab Switcher 扩展 (内部命令键: Ctrl+Shift+9)
;    - 若前台非 Chrome -> 瞬间激活 Chrome 并切到 127.0.0.1:11111 标签页
;    - 若前台已是 Chrome -> 发送信号保持锁定 DSH 页面，杜绝其他 DeepSeek 标签页串台
; ========================================================
ToggleDsh() {
    targetDesk := 'ahk_exe DeepSeek Harness.exe'
    targetChromeApp := 'DeepSeek Harness ahk_exe chrome.exe'
    targetChrome := ' - Google Chrome ahk_exe chrome.exe'

    ; 1. 原生桌面客户端存在：优先对其生效
    if WinExist(targetDesk) {
        ToggleWin(targetDesk)
        return
    }

    ; 2. Chrome PWA 独立应用存在：对其生效 (通过 ExcludeTitle 杜绝误匹配普通 Chrome)
    if WinExist(targetChromeApp, , ' - Google Chrome') {
        ToggleWin(targetChromeApp)
        return
    }

    ; 3. 前两者都不在，但普通 Chrome 窗口存在：联动 Chrome 扩展直达标签页
    if WinExist(targetChrome) {
        if !WinActive(targetChrome) {
            WinActivate(targetChrome)
            Sleep(30)
        }
        Send('^+9')
        return
    }
}

; ========================================================
; Google Chrome 专用 Toggle 函数 (纯净浏览器窗口)
; 1. 核心过滤：匹配 " - Google Chrome ahk_exe chrome.exe"
; 2. 物理隔离：彻底排除 Chrome PWA 独立应用 (如 DeepSeek Harness, docsearch 等)
; 3. Alt+R 专心服务日常网页浏览，绝不串台独立应用
; ========================================================
ToggleChrome() {
    target := ' - Google Chrome ahk_exe chrome.exe'
    ToggleWin(target)
}

; Alt + D -> DeepSeek Harness (桌面端优先，Chrome 应用兜底)
!d::ToggleDsh()

; Alt + E -> IntelliJ IDEA
!e::ToggleApp('idea64.exe')

; Alt + F -> 飞书
!f::ToggleApp('Feishu.exe')

; Alt + R -> Google Chrome 浏览器 (已排除 PWA 独立应用)
!r::ToggleChrome()

; Alt + V -> VS Code
!v::ToggleApp('Code.exe')

; Alt + W -> Windows Terminal
!w::ToggleApp('WindowsTerminal.exe')

; Alt + X -> 资源管理器 (未开启则启动，已开启则盲切/Toggle)
!x::ToggleExplorer()

; Alt + T -> Tinta Markdown 阅读器 (兼容 tina.exe；未开启则启动，已开启则盲切/Toggle)
!t::ToggleTinta()

; ========================================================
; 修复 Chrome 中单按 Alt (特别是豆包输入法占用右 Alt / RAlt) 导致右上角三点菜单被高亮选中的问题
; 1. ~ 修饰符代表按键透传，豆包输入法仍能正常捕获 RAlt/LAlt 的按下与长按录音
; 2. Send "{Blind}{vkE8}" 向系统发送无害未分配键码，消除 Windows 菜单栏激活 (SC_KEYMENU) 机制
; ========================================================
#HotIf WinActive("ahk_exe chrome.exe")
~RAlt::Send "{Blind}{vkE8}"
~LAlt::Send "{Blind}{vkE8}"
#HotIf
```

### 步骤 3：重载脚本使配置生效（WMI 脱钩热重载 SOP）
AHK 脚本加载进内存后，修改文件不会自动热更新，需通过以下方式重载：
- **托盘右键**：在任务栏右下角找到绿色“H”图标，右键选择 **Reload Script**；
- **终端远程热重启（严禁裸跑 Start-Process，详见第 095 篇 SOP）**：
  在 Agent、CI 或远程 PowerShell 下，若使用 `Start-Process`，子进程会被捆绑进当前终端的 **Job Object（作业对象）** 树中，命令退出时 **AHK 会被系统连带掐死**。必须通过 WMI 创建脱钩的独立后台常驻守护：
  ```powershell
  # 1. 优雅终止旧实例
  Stop-Process -Name AutoHotkey64 -Force -ErrorAction SilentlyContinue
  Start-Sleep -Milliseconds 300

  # 2. 构造启动命令行并借 WMI 脱钩常驻
  $ahkExe = "$env:LOCALAPPDATA\Programs\AutoHotkey\v2\AutoHotkey64.exe"
  $scriptPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\app_switcher.ahk"
  $cmd = "`"$ahkExe`" `"$scriptPath`""
  Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd }
  ```

---

## 四、排坑指南与进阶经验

### 1. 快捷键热键修改陷阱
- **分号 `;` 只是注释**：如果修改为 `; Alt + 4 -> 飞书`，但下一行仍然是 `!f::`，实际生效的热键仍然是 <kbd>Alt</kbd> + <kbd>F</kbd>。必须同步修改热键本体为 `!4::`。

### 2. 真实可执行进程名排查（避免启动器别名陷阱）
- **Windows Terminal**：命令行输入 `wt.exe` 即可启动，但 `wt.exe` 只是启动器别名，内存常驻窗口的真实进程名为 `WindowsTerminal.exe`。写 `wt.exe` 会导致 `WinExist` 永远匹配不到；
- **IntelliJ IDEA**：64 位 Windows 下进程名通常为 `idea64.exe`，而非 `idea.exe`；
- **排查方法**：运行目标程序后，打开任务管理器（<kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>Esc</kbd>）切到“详细信息”页，核对“映像名称”即可。

### 3. PowerToys 键盘管理器按键拦截冲突
若之前在 PowerToys 的“键盘管理器”中配置了相同按键（如 Alt+1），PowerToys 拥有更高的底层键盘钩子优先级，会抢先吞掉按键导致 AHK 无法捕获。需在 PowerToys 设置中关闭键盘管理器或删除对应冲突项。

### 4. 特权窗口（管理员权限）拦截问题
依据 Windows UIPI（用户界面特权隔离）机制，若前台正在运行以管理员权限启动的窗口（如管理员 PowerShell），普通权限的 AHK 将无法拦截该窗口上的热键或向其发送激活信号。
- **解决方案**：右键 `app_switcher.ahk` 创建快捷方式，在快捷方式属性“高级”中勾选“以管理员身份运行”，放入启动目录。

### 5. 飞书知识库同步富文本陷阱
将 AHK 脚本指南同步至飞书文档（Lark Docx）时，若使用 `lark-cli docs +update --doc-format markdown`，当代码块中包含 `<` 或 `>`（例如 `winList.Length <= 1`）时，服务端解析器容易降级报错（`degrade_code=3001` XML tokenization error）或截断代码。
- **解决方案**：统一转换为飞书 DocxXML 格式写入，将代码块包裹在 `<pre><code>` 内，并对 `<`（`&lt;`）、`>`（`&gt;`）、`&`（`&amp;`）做实体转义，安全幂等覆盖。

### 6. Windows 资源管理器（Explorer）特殊过滤与缺省拉起机制
- **不能裸传 `explorer.exe`**：桌面（`WorkerW` / `Progman`）和任务栏（`Shell_TrayWnd`）均隶属于 `explorer.exe` 进程。若使用 `ToggleApp('explorer.exe')`，`WinExist` 永远命中桌面，激活时会跳回桌面，最小化时甚至会尝试最小化桌面导致界面异常；
- **精准过滤窗口类名**：必须使用复合选择器 `ahk_class CabinetWClass ahk_exe explorer.exe` 精准匹配文件夹窗口；
- **缺省自动启动（Run）**：不同于常驻大型开发工具（未开则静默），文件管理器在当前没有任何窗口打开时，用户按热键（如 Alt+X）本意正是“打开资源管理器”，因此在 `!WinExist` 时应调用 `Run('explorer.exe')` 自动创建窗口，兼顾冷启动与热 Toggle 盲切。

### 7. Chrome 单按 Alt 激活三点菜单与豆包输入法右 Alt 语音冲突（详见第 64 篇）
在 Windows 下，单按 Alt 键会触发系统的 `SC_KEYMENU` 菜单栏激活机制，导致 Chrome 右上角“三点”菜单被高亮选中抢夺焦点；若同时使用豆包输入法等需要长按右 Alt 触发语音输入的软件，松开 Alt 时极易意外弹开 Chrome 菜单或中断输入。
- **解决方案**：在脚本末尾加入 `#HotIf WinActive("ahk_exe chrome.exe")` 作用域，使用带 `~` 透传修饰符的按键监听，并发送 `{Blind}{vkE8}`（未分配给任何实际功能的虚拟键码）使系统判定存在组合键输入，静默消除菜单激活，完美共存。

### 8. Chrome PWA / 独立应用与普通浏览器底层进程冲突与标题特征物理隔离
- **现象与混淆**：通过 Chrome「将网页安装为应用」或「创建快捷方式 -> 作为窗口打开」（如 DeepSeek Harness、ZedHub、docsearch）后，其底层宿主进程**依然是 `chrome.exe`**。若 AHK 使用简单的 `ahk_exe chrome.exe`，按 <kbd>Alt</kbd> + <kbd>R</kbd> 时系统会将独立应用也误当成 Chrome 浏览器唤起，多窗口轮换时也会把独立应用排进浏览器轮换队列，造成严重“串台”；
- **底层根因**：Windows 下普通 Chrome 浏览器窗口标题无论语言环境，结尾必定包含全局品牌后缀 ` - Google Chrome`；而 Chrome 独立应用（PWA / Standalone）窗口标题直接为应用名，**绝不包含** ` - Google Chrome`；
- **双向物理隔离方案（防假阳性串台绝对红线）**：
  - 普通浏览器使用复合选择器：`target := ' - Google Chrome ahk_exe chrome.exe'`；
  - 独立应用使用专属标题 + 反向排除：`WinExist('DeepSeek Harness ahk_exe chrome.exe', , ' - Google Chrome')`；
  - **避坑警示**：AHK v2 默认使用模糊匹配（`SetTitleMatchMode 2`）。若独立应用只写 `'DeepSeek Harness ahk_exe chrome.exe'` 而不传入第三个参数 `ExcludeTitle`，当普通浏览器中打开了包含 `"DeepSeek Harness"` 的标签页（如 GitHub 仓库、文档或搜索页）时，窗口标题会变成 `... DeepSeek Harness ... - Google Chrome`，此时 AHK 会严重误判，将普通 Chrome 误当成独立应用强行置顶或最小化！

### 9. 原生客户端、Web PWA 与浏览器常驻标签「三模优先级平滑降级」调度模式
- **场景痛点**：对于既有本地独立客户端（如 `DeepSeek Harness.exe`）、Chrome Web PWA 版本，又经常在普通 Chrome 浏览器中常驻固定标签页（如 `http://127.0.0.1:11111/`）的工具，若分配不同按键会极大破坏盲切手感；而若未运行程序时盲目冷启动，又极易在服务未开时唤出浏览器报错窗口；
- **三模调度架构**：
  1. **第一优先（原生桌面端）**：通过 `WinExist('ahk_exe DeepSeek Harness.exe')` 检测桌面端是否在运行，若存在则优先对其生效（置顶激活 / 最小化收起）；
  2. **第二优先（Web PWA 独立应用）**：若桌面端未开启，检测并接管 Chrome PWA 独立窗口（通过 `ExcludeTitle: ' - Google Chrome'` 反向精准隔离）；
  3. **第三兜底（普通 Chrome 专属固定标签页直达）**：若前两者均未打开，但普通 Chrome 窗口存在，激活 Chrome 并派发内部命令信号（如 <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>9</kbd>），联动内核级 Chrome 扩展直接原地切至 `127.0.0.1:11111` 标签页；
  4. **全工具一致性静默**：若以上全部未运行，彻底保持静默，绝不盲目调用外部快捷方式冷启动。

### 10. 终端远程热重载 AHK 的 Job Object 强杀陷阱与 WMI 脱钩规范（参见第 095 篇）
- **致命陷阱**：在 Agent、CI 或远程 PowerShell 终端中执行修改后，若直接使用常规的 `Start-Process` 或 `& AutoHotkey64.exe` 重启脚本，子进程会被自动绑定到**当前终端会话的 Job Object（作业对象）树**中。当远程命令执行完毕、子进程退出时，Windows **会将整棵作业树下的所有子进程（包括刚刚启动的 AHK）连带强行杀死**，表现为终端提示启动成功但实际界面立刻退出的假象；
- **标准解法**：必须执行第 095 篇 SOP，使用 WMI `Invoke-CimMethod -ClassName Win32_Process -MethodName Create` 将 AHK 进程从终端树中彻底脱钩剥离，创建真正的系统独立后台常驻守护。

### 11. 浏览器标签页精准直达的架构选型与踩坑复盘
- **为什么外部 Win32 / UIA 无法做到**：当 Chrome 切到其他标签页时，Win32 窗口标题与地址栏显示的是“当前标签页”的信息；未激活后台标签页的 URL 在 Win32 与 UIAutomation (UIA) 树中完全不透明，且垂直侧边栏插件会破坏标准 Chromium Tab 控件树，外部轮询极易失灵或串台；
- **内核扩展 API 直达优势**：编写仅几十行代码的本地解包 Chrome MV3 扩展（`dsh-tab-switcher`），借助 `chrome.commands` 监听内部命令，通过 `chrome.tabs.query` 读取标签列表并在运行时以 `url.startsWith('http://127.0.0.1:11111/')` 纯前缀过滤，毫秒级直接激活目标 Tab，零界面闪烁，且绝对不会误切任何带 `deepseek` 前缀的外部网页；
- **单向锁定直达 vs 双向 Toggle 抉择**：实践证明，按快捷键唤起核心生产力工具时，用户心智模型是“立刻看到并锁定该界面”。若在扩展中加入“再次按下跳回上一个网页”的双向逻辑，极易产生“按 Alt+D 找 DSH 却被擅自切走”的违和感。保持单向坚决直达是最稳健的工程选择。

## 五、验证标准

1. **静默测试**：未启动某软件时（如未开 IDEA），按下 <kbd>Alt</kbd> + <kbd>E</kbd>，系统无任何卡顿，无任何新窗口弹出；
2. **Toggle 抽屉测试**：启动某软件并置于后台，按下对应快捷键，窗口瞬间置顶激活；再次按下，窗口自动最小化，无缝露出底层工作区；
3. **多实例轮换测试**：打开 2 个以上的 Windows Terminal 标签或独立窗口，连续按下 <kbd>Alt</kbd> + <kbd>W</kbd>，窗口依次在前台轮换，切完最后一轮后自动最小化；
4. **开机自启验证**：重启电脑或在任务管理器“启动应用”标签页中确认 `AutoHotkey` 处于“已启用”状态。
