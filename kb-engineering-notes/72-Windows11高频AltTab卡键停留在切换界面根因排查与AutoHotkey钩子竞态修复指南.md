---
name: kb-win11-alt-tab-stuck-ahk-hook-race
description: Windows 11高频快速按Alt+Tab切换窗口卡在任务切换界面不消失的底层根因排查与AutoHotkey低级钩子竞态彻底修复指南。深度剖析Win32k消息流、Ctrl+Alt+Tab原生粘滞切换器、A_MenuMaskKey默认Ctrl注入、SendInput时序破坏、XamlExplorerHostIslandWindow焦点转移丢失KeyUp及多钩子超时旁路机理，给出零副作用的AHK生产级重构代码。
version: 1.0.0
created: 2026-10-17
updated: 2026-10-17
---

# 72-Windows 11 高频 Alt+Tab 卡键停留在切换界面根因排查与 AutoHotkey 钩子竞态修复指南

> **适用场景**：在 Windows 11 环境下快速、连续按 <kbd>Alt</kbd> + <kbd>Tab</kbd> 切换窗口时，系统任务切换界面（Task Switcher）突然“卡死”在屏幕中央，即使双手已经完全离开键盘，缩略图网格依然常驻不退，宛如物理“卡键”；用户现场常驻 AutoHotkey v2（配置了多组 Alt 快捷键及 Chrome 菜单抑制规则 `~LAlt::Send "{Blind}{vkE8}"`）、豆包输入法（占用 `RAlt` 语音）及 Windhawk 代码注入。当出现 Alt 键逻辑粘滞、快速切窗口界面停滞或修饰键状态混乱时查阅。

---

## 一、现象与报错直击

### 1. 现场实况还原
- **操作行为**：用户双手在键盘上以极高频率（1 秒内 2~4 次）快速敲击并释放 <kbd>Alt</kbd> + <kbd>Tab</kbd> 进行多窗口往复盲切。
- **故障现象**：在切到某一瞬间（现场截图中背景正停留于 Google Chrome 窗口上空），屏幕中央的 Windows 11 现代任务切换界面（XAML 悬浮岛）瞬间定格；用户**完全松开键盘所有按键**，切换界面依然如同“钉”在屏幕上纹丝不动，鼠标移动虽有缩略图高亮响应，但无法自动隐退。
- **伴随症状**：
  - 单击桌面空白处或按 <kbd>Esc</kbd> / <kbd>Enter</kbd> 界面可强行关闭；
  - 故障发生后，有时伴随键盘打字异常（如按普通字母键触发软件系统菜单或属性面板，表明系统仍认为 <kbd>Alt</kbd> 处于逻辑按下状态）；有时则按键完全正常，唯独切换器“驻留不退”。

### 2. 关键视觉特征与机制辨析（真假“卡键”）
Windows 11 上的该现象存在两种本质截然不同但视觉极度相似的底层表现：

| 现象类型 | 核心表现 | 根本机理 | 系统真实按键状态 |
|---|---|---|---|
| **类型 A：粘滞切换器模式 (Sticky Mode)** | 任务切换器常驻，按方向键/鼠标能正常选窗口，按 Enter/点击能正常进入 | 误触或被注入触发了 Windows 原生 **`Ctrl + Alt + Tab`** 辅助功能持久态 | **无物理或逻辑卡键**；系统按键状态完全正常，单纯处于 Sticky 交互模式 |
| **类型 B：逻辑按键卡死 (Logical Key Stuck)** | 任务切换器常驻，且全局所有按键输入被 Win32k 视为带 Alt 修饰 | `explorer.exe` 或活动线程未收到 `WM_SYSKEYUP` (VK_MENU)，键盘状态机失步 | **VK_MENU 处于逻辑按下态**（`GetKeyState` 或 `GetAsyncKeyState` 报告 Down） |

---

## 二、底层根因深度剖析（全景透视）

```text
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ 物理按键: Alt Down ──> Tab Down ──> Tab Up ──> Alt Up (高频快速敲击, 周期 < 80ms)      │
 └────────────────────────────────────────┬───────────────────────────────────────────────┘
                                          │
                                          ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ Windows 内核输入栈 (win32k.sys / Raw Input Thread)                                     │
 │  ├── 1. 硬件扫描码解析 (kbdclass -> i8042prt/hidusb)                                   │
 │  ├── 2. 同步调用全局低级键盘钩子链 (WH_KEYBOARD_LL)                                    │
 │  │    ├── Hook 1: Windhawk 注入层 (DWM / Explorer 内部拦截)                           │
 │  │    ├── Hook 2: 豆包输入法引擎 (tsf-oime 监听 RAlt 语音)                             │
 │  │    └── Hook 3: AutoHotkey v2 主进程 (~LAlt / ~RAlt / !1~!x 规则)                   │
 │  │           │                                                                         │
 │  │           ├──【致命缺陷 1】未定义 A_MenuMaskKey -> 默认注入 vk11 (Left Control)     │
 │  │           │    ==> Alt + Tab + Injected Ctrl ===> 触发系统原生 Ctrl+Alt+Tab 粘滞模式!│
 │  │           │                                                                         │
 │  │           └──【致命缺陷 2】~LAlt 触发 SendInput("{Blind}{vkE8}")                     │
 │  │                ==> 在 Alt 与 Tab 之间强行插入 vkE8 Down/Up                          │
 │  │                ==> SendInput 破坏硬件时序 + 触发二次钩子重入                        │
 │  │                                                                                     │
 │  └── 3. 消息投递与焦点转移 (Cross-Process SetForegroundWindow)                         │
 │       ├── Chrome 窗口失去前台焦点 (WinActive 动态判定翻滚失效)                         │
 │       ├── 激活 Windows 11 现代 XAML 宿主 (XamlExplorerHostIslandWindow)                │
 │       └──【致命缺陷 3】Alt Up 消息在跨进程路由中丢失，造成局部线程 GetKeyState 逻辑死锁│
 └────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 1. 维度一：Windows 原生“粘滞任务切换器”（`Ctrl+Alt+Tab`）与 AHK 默认掩码陷阱

#### (1) 原生粘滞切换机制的判定状态机
自 Windows Vista 起，微软为单手操作、残障辅助及触控用户引入了**粘滞任务切换器（Sticky Task Switcher）**：
- **瞬态切换（`Alt + Tab`）**：
  - 触发：按住 `VK_MENU`，敲击 `VK_TAB`；
  - 退出契约：**释放 `VK_MENU` 是唯一的隐式关闭信号**。当 Win32k 检测到 `WM_SYSKEYUP`（VK_MENU），切换器立即把高亮窗口置顶并自毁。
- **粘滞模式（`Ctrl + Alt + Tab`）**：
  - 触发：当用户按下 `Tab` 的瞬间，若系统键盘状态表中 **`VK_MENU`（Alt）与 `VK_CONTROL`（Ctrl）同时处于按下状态**，Windows 切换器立即升格为“持久挂起模式”；
  - 退出契约：**彻底禁用“松开 Alt 自动隐退”逻辑**！手松开全部按键后，界面永久停留，必须等待显式输入：<kbd>Enter</kbd>（切入）、<kbd>Esc</kbd>（取消）、鼠标点击缩略图或空白区。

#### (2) AutoHotkey 的默认隐式注入：`A_MenuMaskKey`
在 AutoHotkey 内部架构中，为了防止用户自定义的 Win/Alt 快捷键在释放时触发 Windows 原生菜单（开始菜单或窗口横向菜单栏），AHK 的底层钩子（`source/hook.cpp`）内置了**修饰键掩码机制（Menu Mask Key）**：
- **默认掩码键**：AutoHotkey 源码与官方文档明确规定，`A_MenuMaskKey` 的全局默认值为 **`vk11sc01D`（即键盘左侧的 `Left Control`）**！
- **注入时机**：只要脚本中存在包含 Alt 的快捷键（本机 `app_switcher.ahk` 中包含 `!1`, `!2`, `!3`, `!g`, `!f`, `!r`, `!w`, `!x` 及 `~LAlt`），每当该快捷键执行完成或修饰键状态发生迁移，AHK 钩子就会向系统事件流中**静默注入一次合成的 Left Control 按下与释放**。
- **碰撞升格**：当用户以每秒数次的频率高速敲击 <kbd>Alt</kbd> + <kbd>Tab</kbd> 时，AHK 钩子为保护 Alt 快捷键而注入的 `Left Control` 微秒级脉冲，极易与用户物理按住的 `Alt` 及刚按下的 `Tab` **物理对撞**。
  系统底层的 RIT 读出：`Physical Alt Down` + `Injected LCtrl Down` + `Physical Tab Down`。
  **Windows Shell 判定：用户触发了 `Ctrl + Alt + Tab`！切换器被瞬间强制推入 Sticky 粘滞模式**。此时即便用户松手，界面也绝不可能消失！

---

### 2. 维度二：Win32 键盘输入流与“逻辑卡键”（Lost KeyUp）

#### (1) Win32 消息流与双状态机模型
Win32 子系统的键盘状态由两层完全不同的数据结构维护：
1. **全局异步硬件状态表（`gafAsyncKeyState`）**：由内核 `win32k.sys` 的原始输入线程（Raw Input Thread, RIT）维护，直接反映驱动层上报的硬件通断状态，供 `GetAsyncKeyState()` 查询；
2. **线程局部虚拟状态表（`gafPhysKeyState`）**：每个 GUI 线程独立的 256 字节虚拟按键数组，仅在线程从自身消息队列取出 `WM_KEYDOWN` / `WM_KEYUP` / `WM_SYSKEYDOWN` / `WM_SYSKEYUP` 时由 `GetMessage` 同步更新，供 `GetKeyState()` 查询。

#### (2) 跨进程焦点转移（`SetForegroundWindow`）下的“丢失 KeyUp”竞态
在快速敲击 Alt+Tab 的极端场景中（按键按下到释放间隔仅 30~50 毫秒）：
1. 用户在 Chrome 窗口内按下 <kbd>Alt</kbd>；
2. 用户按下 <kbd>Tab</kbd>，系统 Shell 唤起 `explorer.exe` 的任务切换器窗口；
3. **焦点发生跨进程迁移**：Win32k 介入，调用 `SetForegroundWindow` 将焦点从 `chrome.exe` 的 UI 线程剥离，准备挂接至 Explorer 切换器线程；
4. 就在这几毫秒的线程输入队列切换窗口期，**用户的物理手指已经快速松开了 <kbd>Alt</kbd> 键**；
5. 内核生成 `WM_SYSKEYUP`（VK_LMENU）：
   - 若此时活动窗口已被卸载或处于未决决断期，该 KeyUp 消息往往被残留投递给即将休眠的 `chrome.exe` 队列；
   - **`explorer.exe` 的切换器线程压根没有从自己的消息泵中取出这个 `WM_SYSKEYUP`**！
6. 结果：Explorer 切换器线程的局部按键状态表（`GetKeyState`）中，`VK_MENU` 的最高位永久保持为 `1`（Down）。切换器根据自身线程状态判定“用户还在按着 Alt”，从而陷入无限等待死锁。

---

### 3. 维度三：AutoHotkey `~LAlt::Send "{Blind}{vkE8}"` 的致命竞态

本机常驻脚本 `app_switcher.ahk` 中包含此前为抑制 Chrome 三点菜单而编写的规则：
```ahk
#HotIf WinActive("ahk_exe chrome.exe")
~RAlt::Send "{Blind}{vkE8}"
~LAlt::Send "{Blind}{vkE8}"
#HotIf
```

#### (1) `SendInput` 插入与系统输入队列时序污染
- 当用户在 Chrome 内按 <kbd>Alt</kbd> 时，`~LAlt` 匹配触发；
- 波浪号 `~` 确保物理 `LAlt Down` 透传给系统；但紧接着 AHK 在后台执行 `Send "{Blind}{vkE8}"`；
- AHK 的 `Send` 底层调用 Win32 `SendInput` API。微软 MSDN 官方契约明示：
  > *“SendInput 将输入事件以串行方式插入全局键盘或鼠标输入流中，不可被其他输入打断；执行期间发生的物理输入会被延迟排在 SendInput 之后。”*
- 结果：原本纯净的硬件事件序列：
  `[Alt Down] -> [Tab Down]`
  被硬生生污染成：
  `[Alt Down] -> [vkE8 Down] -> [vkE8 Up] -> [Tab Down]`。
- **副作用**：Windows Shell 的 Alt+Tab 状态机对输入流中穿插的非导航键极其敏感。在部分 Windows 内部构建版本中，Alt 期间检测到其他虚拟键码会导致内部修饰键跟踪重置，产生“Alt 状态抖动”。

#### (2) `#HotIf WinActive` 的前台状态翻滚撕裂
- `#HotIf WinActive("ahk_exe chrome.exe")` 是**动态条件判定**；
- 每次按下按键时，AHK 的全局钩子线程必须同步调用 `GetForegroundWindow()` 并向系统查询其所属进程名；
- **高频盲切时的时序崩溃**：
  - 第 1 次 Alt+Tab：前台为 Chrome，`WinActive` 返回 True，`~LAlt` 执行，注入 `vkE8`；
  - 任务切换器弹出的瞬间，前台窗口变为 `explorer.exe`；
  - 用户紧接着按第 2 次 Alt（快速往复切）：此时前台已经**不是** Chrome，`WinActive` 瞬间变为 False，`~LAlt` **不触发**，没有注入 `vkE8`；
  - 窗口切到下一个目标（如 Zed/VS Code），再切回 Chrome……
- **这种在数十毫秒内“一会儿注入 vkE8、一会儿不注入 vkE8”的非对称输入流，彻底打乱了 Windows 切换器对用户连击动作的归一化预测**。

#### (3) 低级钩子链与 `LowLevelHooksTimeout` 超时旁路
- 本机同时常驻：**Windhawk 代码注入** + **豆包输入法（全局 WH_KEYBOARD_LL 捕获 RAlt）** + **AutoHotkey v2（全局 WH_KEYBOARD_LL）**；
- 键盘物理事件到达驱动后，必须**同步线性串行穿透这 3 个全局钩子**；
- AHK 在钩子回调中频繁跨进程查询 `GetForegroundWindow`，遭遇高频按键引发的系统消息峰值时极易产生微秒级阻塞；
- Windows 注册表中存在 `LowLevelHooksTimeout`（默认通常仅 1000ms 或更短）：**一旦钩子链耗时超标，Windows 内核会静默跳过（Bypass）钩子，甚至强行移除钩子**。这会导致后续关键的 `Alt Up` 事件在钩子层被腰斩，产生不可逆的按键状态丢失。

---

### 4. 维度四：Windows 11 现代 XAML 任务切换器（`XamlExplorerHostIslandWindow`）并发缺陷

不同于 Windows XP/7 时代极简高效的 GDI 模态对话框（`TaskSwitcherWnd`），Windows 11 将 Alt+Tab 彻底重构成**基于 XAML Islands 的现代视觉组件**：
- **宿主载体**：由 `explorer.exe` 进程承载，窗口类名为 `XamlExplorerHostIslandWindow`；
- **渲染管线**：深度集成 DirectComposition、Mica（云母）背景模糊与 WinRT XAML 视觉状态机（`Windows.UI.Xaml.dll`）；
- **动画状态机竞态死锁**：
  - 切换器被唤起时，XAML 引擎启动淡入缩放的故事板动画（Storyboard: `Opening` 态）；
  - 正常情况下动画走完进入 `Interactive` 态，接收 KeyUp 并过渡到 `Closing` 态隐退；
  - **微软已知 Shell 竞态**：若用户敲击过快（按键释放在 50ms 内完成），`Alt Up` 到达切换器宿主时，XAML 的 `Opening` 动画**尚未执行完毕**。由于早期事件分发状态机中缺少挂起队列（Pending State），该 `Dismiss` 指令直接被 XAML 动画管道抛弃！
  - 动画播放完毕后，切换器停留在静止态，而物理手指早离键盘，系统再无新的 KeyUp 消息派发，导致界面永久卡滞孤立。

---

### 5. 维度五：硬件 Ghosting 与键盘矩阵扫描机理

在非全键无冲（NKRO）的标准薄膜键盘或部分笔记本键盘上：
- 键盘物理矩阵采用行线（Row）与列线（Column）交叉扫描；
- <kbd>Left Alt</kbd>、<kbd>Tab</kbd> 与附近的 <kbd>Ctrl</kbd>、<kbd>Shift</kbd>、<kbd>Q</kbd>、<kbd>W</kbd> 往往共用扫描线；
- 当手掌极速敲击 Alt+Tab 并伴随小拇指微弱搭放或误触时，键盘内部单片机为防止电路出现“幻影按键（Ghost Key）”，会强行执行按键屏蔽（Key Blocking）；
- 在极个别硬件时钟抖动下，键盘固件向 USB 总线上报 `Alt Make`（按下 0x38）后，在高速切换下漏报了 `Alt Break`（释放 0xB8），导致从硬件层面就未曾向操作系统发过松键信号。

---

## 三、抢救与彻底修复 SOP

### 1. 现场紧急脱困手段（快速恢复工作流）
当切换器已经卡在屏幕上时，**切勿强制重启电脑或结束资源管理器**，使用以下方式瞬间复原：

| 操作级别 | 快捷键 / 动作 | 底层生效机理 |
|---|---|---|
| **首选（最轻量）** | 轻按一次 <kbd>Esc</kbd> | 向前台 `XamlExplorerHostIslandWindow` 派发取消指令，安全关闭 XAML 岛 |
| **次选（确认切入）** | 轻按一次 <kbd>Enter</kbd> 或鼠标单击任意窗口缩略图 | 强制触发切换器确认提交逻辑，激活选定窗口并销毁切换器 |
| **按键重置** | 单独轻按一下 **物理左 Alt**，再单独轻按一下 **物理右 Alt** | 强制向内核 RIT 注入一对新的 Down/Up，刷新并对齐系统的 `gafAsyncKeyState` |
| **底线兜底** | <kbd>Win</kbd> + <kbd>Tab</kbd> 进入 Task View 再退出 | 唤起全局多任务视图，强制重置所有前台 Shell 切换组件 |

---

### 2. 根治方案设计：彻底消除 AHK 钩子竞态

排查确认，引发卡键的最直接破坏源是 `app_switcher.ahk` 中的两大致命配置：
1. **未设置 `A_MenuMaskKey := "vkE8"`**：导致 AHK 在所有 Alt 快捷键收尾时盲发默认的 `Left Control`，与快速 Alt+Tab 撞击触发 Sticky 粘滞模式；
2. **在 `~LAlt` 上绑定了 Down 状态的 `Send "{Blind}{vkE8}"`**：破坏了高频 Alt+Tab 的系统输入流时序与焦点转移。

#### 核心治理决策：
- **豆包输入法语音仅使用【右侧 Alt (RAlt)】**，日常生活与打字绝无使用【左侧 Alt (LAlt)】进行语音输入的场景；
- **Alt+Tab 99.9% 依赖【左侧 Alt (LAlt)】**；
- **方案 A（最强壮推荐）**：**彻底废除对 `~LAlt` 的 Down 劫持**，仅保留 `~RAlt` 掩码透传。左 Alt 回归 100% 纯净系统原生输入流，杜绝任何 Alt+Tab 竞态；
- **方案 B（完美兼顾）**：若用户仍希望保留“单按左 Alt 不弹出 Chrome 菜单”，**改用 `~LAlt Up` 并在其内部借助 `A_PriorKey` 进行严密判定**：只有当上一个按下的按键**确属 LAlt 本身**（即没有按过 Tab、没有按过 1~3，纯单按释放）时才发 `vkE8`。当用户按 Alt+Tab 时，`A_PriorKey` 必定为 `"Tab"`，该分支被完全短路跳过，实现零干扰！

---

### 3. 生产级实战修复代码（针对 `app_switcher.ahk`）

对 `C:\Users\29580\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\app_switcher.ahk` 进行终极重构：

```ahk
#Requires AutoHotkey v2.0
#SingleInstance Force

; ========================================================
; 核心架构设置：全局修饰键掩码安全声明（彻底根治 Sticky 粘滞升格）
; --------------------------------------------------------
; AHK 默认掩码键为 vk11sc01D (Left Control)！
; 极速按 Alt+Tab 时，AHK 自动注入的 Left Ctrl 会与用户的 Alt+Tab 发生物理碰撞，
; 导致 Windows 将其判定为 Ctrl+Alt+Tab，瞬间升格为原生“粘滞任务切换器”，表现为松手不关！
; 显式重定向为微软保留的未分配键码 vkE8，彻底杜绝 Ctrl 污染。
; ========================================================
A_MenuMaskKey := "vkE8"

; ========================================================
; 窗口切换与最小化 Toggle 核心函数
; ========================================================
ToggleApp(exeName) {
    target := 'ahk_exe ' . exeName
    
    if !WinExist(target) {
        return
    }

    if WinActive(target) {
        winList := WinGetList(target)
        if (winList.Length <= 1) {
            WinMinimize('A')
            return
        }
        
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
        WinActivate(target)
    }
}

; ========================================================
; 文件资源管理器专用 Toggle 函数 (CabinetWClass)
; ========================================================
ToggleExplorer() {
    target := 'ahk_class CabinetWClass ahk_exe explorer.exe'
    
    if !WinExist(target) {
        Run('explorer.exe')
        return
    }

    if WinActive(target) {
        winList := WinGetList(target)
        if (winList.Length <= 1) {
            WinMinimize('A')
            return
        }
        
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
        WinActivate(target)
    }
}

; ========================================================
; 快捷键注册表 (Alt + 字符)
; ========================================================
!1::ToggleApp('Zed.exe')
!2::ToggleApp('sublime_merge.exe')
!3::ToggleApp('sublime_text.exe')
!g::ToggleApp('Antigravity.exe')
!f::ToggleApp('Feishu.exe')
!r::ToggleApp('chrome.exe')
!w::ToggleApp('WindowsTerminal.exe')
!x::ToggleExplorer()

; ========================================================
; 全局应急解卡键安全网 (Emergency Reset)
; 遇到任何外部全屏游戏、XAML 死锁或第三方钩子导致修饰键卡死时，
; 按 Ctrl + Alt + F12 一键强行复位所有系统修饰键物理逻辑状态
; ========================================================
^!F12:: {
    Send("{Ctrl Up}{Alt Up}{Shift Up}{Win Up}")
    ToolTip("已强制复位所有修饰键状态 (Modifiers Cleared)")
    SetTimer(() => ToolTip(), -1500)
}

; ========================================================
; Chrome 专区：消除三点菜单抢焦点 & 豆包输入法右 Alt 语音透传
; --------------------------------------------------------
; 1. 豆包输入法仅使用【右侧 Alt (RAlt)】，必须维持 ~RAlt 透传；
; 2. 严禁在 ~LAlt Down 时盲发 SendInput！改用 ~LAlt Up + A_PriorKey 守卫；
; 3. 只有当用户确实【单按并松开 LAlt】且中途未触发任何组合键时才发 vkE8；
; 4. 当用户按 Alt+Tab 时，A_PriorKey 必定为 "Tab"，LAlt Up 分支直接短路，
;    输入流 100% 保持纯净物理信号，彻底消灭 Alt+Tab 界面卡滞死锁！
; ========================================================
#HotIf WinActive("ahk_exe chrome.exe")
; 豆包输入法语音录入透传与三点菜单消除
~RAlt::Send "{Blind}{vkE8}"

; 左 Alt 防菜单安全守卫 (单按释放才掩码，Alt+Tab 零干扰)
~LAlt Up:: {
    if (A_PriorKey = "LAlt") {
        Send("{Blind}{vkE8}")
    }
}
#HotIf
```

---

## 四、验证与防复发闭环

### 1. 确定性排障验收测试矩阵

脚本保存并重新加载（右键托盘图标 Reload Script）后，依次执行以下 4 项极限验收：

- [ ] **测试 1：高频 Alt+Tab 连击抗压测试（核心故障复测）**
  - 打开 Chrome、Zed、文件管理器等 3~4 个窗口；
  - 聚焦 Chrome 界面，左手以极快频率（连续敲击 10~20 次）疯狂按 <kbd>Alt</kbd> + <kbd>Tab</kbd> 并快速完全松手；
  - **断言**：任务切换器每次随手指松开而**即刻隐退**并精准切入目标窗口，**零卡死、零常驻、零 Sticky 升格**。
- [ ] **测试 2：豆包输入法长按 RAlt 语音转写上屏**
  - 在 Chrome 网页输入框（如 Google 搜索框）内长按 <kbd>RAlt</kbd> 录音，说完松手；
  - **断言**：文字精准流式上屏，Chrome 右上角三点菜单**绝不高亮**，光标稳固停留在文本末尾。
- [ ] **测试 3：Chrome 单按左 Alt 抑制效果**
  - 在 Chrome 网页中随意轻按一下 <kbd>左 Alt (LAlt)</kbd> 并松手；
  - **断言**：右上角三点菜单无任何响应，网页输入焦点不丢失。
- [ ] **测试 4：紧急安全网触发验证**
  - 按下 <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>F12</kbd>；
  - **断言**：屏幕右下角弹出气泡 `已强制复位所有修饰键状态 (Modifiers Cleared)` 并在 1.5 秒后自动隐退。

---

### 2. 架构防复发工程铁律

1. **凡定义任何修饰键快捷键，置顶必写 `A_MenuMaskKey := "vkE8"`**：
   AutoHotkey 历史包袱采用 `Ctrl` 作为掩码键是大量系统级快捷键（尤其是 Win 键、Alt 键组合）诡异冲突的万恶之源。新编写任何 AHK 脚本一律在文件第 1 行显式声明 `vkE8`，绝不裸奔使用默认值。
2. **严禁在基础修饰键（`LAlt` / `LCtrl` / `LShift` / `LWin`）的 Down 事件中无条件使用 `SendInput`**：
   系统级高频快捷键（如 Alt+Tab、Win+D、Ctrl+C）在 Win32k 内核中有极高优先级状态机。在修饰键 Down 阶段插入任何虚拟键都会严重破坏时序。如确需判断单按，一律推迟至 `Up` 事件配合 `A_PriorKey` 判定。
3. **分清输入法专属按键与通用系统按键的物理界限**：
   豆包输入法等国产 AI 语音引擎在 Windows 下固定绑定 `RAlt`。脚本规则必须严格按 `RAlt` 单独挂载，绝不要主观臆断将 `LAlt` 与 `RAlt` 粗暴合并编写，避免污染属于全系统命脉的左侧修饰键。
