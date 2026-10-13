---
name: kb-manggo-shortcut-ctrlc-altshift
description: 桌面划词工具（Manggo等）全局快捷键通过 SendInput 盲发 Ctrl+C 抓词致终端 CLI 会话中断、黑名单不生效与进程别名陷阱，以及 Windows 默认 Alt+Shift 幽灵切换纯英文键盘排障指南。当按划词热键终端退出、按完热键输入法失效打不出中文时查阅。
version: 1.0.0
created: 2026-10-13
updated: 2026-10-13
---

# Manggo 划词工具快捷键盲发 Ctrl+C 误杀终端会话与 Windows 默认 Alt+Shift 切语言排障指南

> **适用场景**：在 Windows Terminal（WT）的 PowerShell 或 CLI（如 `agy`、`pi`、交互式脚本）中按下某个全局快捷键（如 <kbd>Alt</kbd> + <kbd>Shift</kbd> + <kbd>D</kbd>），终端突然产生类似 <kbd>Ctrl</kbd> + <kbd>C</kbd> 的清行效果，连续按两次甚至直接杀死会话退出（提示 `Resume with -c`）；在划词软件（如 Manggo）中配置了应用黑名单却毫无效果；测试完按键后突然全系统打不出中文、只能敲纯英文字母。

---

## 一、现象与报错直击

### 1. 现场一：终端内按键直接中断/杀死前台 CLI 会话

在 Windows Terminal 内运行 Antigravity CLI（`agy`）或任意交互式命令行时：
- 按下划选翻译快捷键（如 <kbd>Alt</kbd> + <kbd>Shift</kbd> + <kbd>D</kbd>），命令行正在输入的文本瞬间被清空丢弃并换行；
- 连续按两次，`agy` 收到双击终止信号直接崩溃退出：
  ```text
  Resume with -c (or command below):
  agy --conversation=e7e01f68-0dd4-45c9-b7de-0c7ff8e84502
  PS C:\Users\29580>
  ```

### 2. 现场二：划词软件设置了黑名单依然穿透生效

用户在 Manggo 的「应用过滤」中添加了黑名单，将终端路径 `D:\Users\Softwares\WindowsTerminal\wt.exe` 加入名单，但按下快捷键时依然盲发中断，黑名单完全形同虚设。

### 3. 现场三：测试完快捷键后，突然打不出汉字

用户测完按键后，在任何聊天框或编辑器中打字突然全部变成纯英文字母，按 <kbd>Shift</kbd> 也无法唤出拼音候选框；若配合任务栏语言指示器隐藏（如 Windhawk），用户看不到右下角的 `ENG` 图标，极易误判为“输入法后台崩溃/被连带卸载”。

---

## 二、底层根因剖析

### 1. 桌面划词工具的“盲发 Ctrl+C”机制与终端 SIGINT 碰撞

Windows 操作系统**没有提供任何通用的跨进程即时读取文本选区 API**（UI Automation 协议速度慢且对终端 GPU 渲染支持极差）。因此，市面上绝大多数桌面划词/AI 助手工具（如 Manggo、Pot、沙拉查词、有道等）的核心取词实现完全相同：

```text
用户按下划词快捷键
       │
       ▼
调用 Win32 API: SendInput (模拟按下 Ctrl + C)
       │
   ┌───┴────────────────────────────────────────┐
   ▼ 焦点在普通窗口 (Word/Chrome)                 ▼ 焦点在命令行终端 (WT/PowerShell)
有选区 -> 复制文本到剪贴板                       有选区 -> WT 判定为复制文本 (安全)
无选区 -> 剪贴板无变化，软件静默退出              无选区 -> WT 判定为发送 SIGINT 中断信号！
                                                      (清空当前行；CLI 连按两次直接退出！)
```

### 2. 划词工具黑名单的“作用域陷阱”与“进程别名陷阱”

通过逆向反汇编 `Manggo.exe`（Qt6 架构）PE 导入表与汇编调用链发现两条致命断层：

#### (1) 作用域断层：黑名单只管“鼠标助手”，不管“全局快捷键”
- **鼠标划选助手（`selectionAssistant`）**：通过底层鼠标钩子（`WH_MOUSE_LL`）监听，在鼠标抬起时调用 `QueryFullProcessImageNameW` 获取前台进程名，比对 `selectionAssistant/applicationFilter`。若在黑名单中，则不弹出悬浮条；
- **全局快捷键（`shortcuts`）**：通过 Windows 系统原生 `RegisterHotKey` 注册。收到系统 `WM_HOTKEY` 消息后，**直接跳转至取词函数无条件调用 `SendInput` 发送 <kbd>Ctrl</kbd> + <kbd>C</kbd>**，完全没有前置的前台进程黑名单校验！
- Manggo 设置界面文案亦写明：*“划词助手不会在名单中的应用内运行”*，语义仅限悬浮助手。

#### (2) 进程别名断层：`wt.exe` ≠ `WindowsTerminal.exe`
- 用户在名单中填入 `wt.exe`；
- 但 `wt.exe` 仅为启动桩（Launcher Stub），负责将实际的终端宿主拉起后即退出；
- 持有前台桌面窗口句柄的真实进程名为 **`WindowsTerminal.exe`**。即使软件支持快捷键黑名单，按 `wt.exe` 匹配也注定落空。

### 3. Windows 默认输入法切换热键幽灵生效（Alt+Shift）

Windows 系统自 Windows 95 起便默认保留了一组极易误触的历史全局热键：

| 快捷键 | 默认绑定的 Windows 系统动作 | 注册表对应项 |
|---|---|---|
| **<kbd>Left Alt</kbd> + <kbd>Shift</kbd>** | **切换输入语言（Switch input language）** | `HKCU\Control Panel\Input Method\Hot Keys\00000070` |
| **<kbd>Ctrl</kbd> + <kbd>Shift</kbd>** | **切换键盘布局（Switch keyboard layout）** | `HKCU\Control Panel\Input Method\Hot Keys\00000071` |

- 当用户按下复合快捷键 <kbd>Alt</kbd> + <kbd>Shift</kbd> + <kbd>D</kbd> 时，由于手指释放顺序微小的毫秒差，系统极易判定为**按下并释放了 <kbd>Alt</kbd> + <kbd>Shift</kbd>**；
- 系统立刻触发语言轮换，将当前线程的键盘布局句柄（HKL）从中文（`0x0804`）静默切为 **`0x04090409`（en-US，纯英文美式键盘）**；
- 在纯英文键盘下，按任何键都直接输出英文字母，按 <kbd>Shift</kbd> 无中英切换效果；若配合任务栏语言指示图标隐藏，用户便会陷入“输入法凭空消失”的恐慌。

---

## 三、标准解决与抢救 SOP

### Step 1：彻底禁用 Windows 系统默认的 Alt+Shift 切换语言

直接通过 PowerShell 修改注册表并广播系统环境刷新，彻底根治误触：

```powershell
# 1. 设置 Keyboard Layout\Toggle 下的三项热键为 "3"（未分配 / 彻底禁用）
$togglePath = "HKCU:\Keyboard Layout\Toggle"
if (!(Test-Path $togglePath)) { New-Item -Path $togglePath -Force | Out-Null }
Set-ItemProperty -Path $togglePath -Name "Hotkey" -Value "3" -Type String
Set-ItemProperty -Path $togglePath -Name "Language Hotkey" -Value "3" -Type String
Set-ItemProperty -Path $togglePath -Name "Layout Hotkey" -Value "3" -Type String

# 2. 清空 00000070 与 00000071 的底层热键修饰符与虚拟键码
$zeroBytes = [byte[]]@(0, 0, 0, 0)
Set-ItemProperty -Path "HKCU:\Control Panel\Input Method\Hot Keys\00000070" -Name "Key Modifiers" -Value $zeroBytes
Set-ItemProperty -Path "HKCU:\Control Panel\Input Method\Hot Keys\00000070" -Name "Virtual Key" -Value $zeroBytes
Set-ItemProperty -Path "HKCU:\Control Panel\Input Method\Hot Keys\00000071" -Name "Key Modifiers" -Value $zeroBytes
Set-ItemProperty -Path "HKCU:\Control Panel\Input Method\Hot Keys\00000071" -Name "Virtual Key" -Value $zeroBytes

# 3. 向系统广播 WM_SETTINGCHANGE 使配置即时生效
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinMsg {
    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
    public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint Msg, UIntPtr wParam, string lParam, uint fuFlags, uint uTimeout, out UIntPtr lpdwResult);
}
"@
$result = [UIntPtr]::Zero
[WinMsg]::SendMessageTimeout([IntPtr]0xffff, 0x001A, [UIntPtr]::Zero, "intl", 2, 5000, [ref]$result) | Out-Null
Write-Host "已彻底禁用 Alt+Shift 与 Ctrl+Shift 系统切语言热键。"
```

### Step 2：紧急切回中文输入法（恢复打字）

若当前处于打不出中文状态，按下：
```text
Win + Space （Windows 徽标键 + 空格键）
```
在弹出的半透明语言列表中，松开切回中文输入法（如豆包输入法），中文录入立即恢复。

### Step 3：终端内防划词工具盲发 Ctrl+C 治理策略

针对桌面划词软件无法靠内置黑名单拦截全局快捷键的硬伤，推荐采用以下策略治理：

1. **顺应终端机制（最推荐、无需额外工具）**：
   - 划词翻译的本质是“先选词、后翻译”；
   - 在终端里欲翻译日志时，**必须先用鼠标左键拖选高亮文本，然后再按快捷键**；
   - 此时 Windows Terminal 的 `Terminal.CopyToClipboard` 会判定存在有效选区，将模拟的 <kbd>Ctrl</kbd> + <kbd>C</kbd> 内部消化为合法的文本复制，**绝不会向底层 CLI 进程发射 SIGINT 中断信号**。
2. **改绑划词工具快捷键**：
   - 在划词工具设置中，避免使用易误触的组合，改用右手单手或独立的功能键。

---

## 四、验证与防复发闭环

### 1. 注册表禁用状态验证脚本

运行以下脚本，核对真值：

```powershell
Get-ItemProperty -Path "HKCU:\Keyboard Layout\Toggle" | Select-Object Hotkey, "Language Hotkey", "Layout Hotkey"
$k70 = Get-ItemProperty -Path "HKCU:\Control Panel\Input Method\Hot Keys\00000070"
Write-Output "70 Modifiers: $([System.BitConverter]::ToString($k70.'Key Modifiers'))"
```

**断言标准**：
- `Hotkey`、`Language Hotkey`、`Layout Hotkey` 必须全为 `3`；
- `70 Modifiers` 必须全为 `00-00-00-00`。

### 2. 当前键盘布局句柄（HKL）验证

检测当前前台窗口的输入法语言：

```powershell
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class KbdHelper {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, IntPtr ProcessId);
    [DllImport("user32.dll")] public static extern IntPtr GetKeyboardLayout(uint idThread);
}
"@
$hwnd = [KbdHelper]::GetForegroundWindow()
$tid = [KbdHelper]::GetWindowThreadProcessId($hwnd, [IntPtr]::Zero)
$hkl = [KbdHelper]::GetKeyboardLayout($tid).ToInt64()
"当前活动键盘布局 HKL: 0x{0:X}" -f $hkl
```

- 若输出为 `0x4090409`：当前处于纯英文美式键盘；
- 若输出含 `0804`（如 `0x8040804` 或包含中文 IME GUID）：说明处于中文输入状态。

### 3. 一页避坑防复发速查表

| 踩坑表现 | 错误归因 | 底层真实原因 | 正确应对方案 |
|---|---|---|---|
| 终端按热键会清行或杀 CLI | 误以为是终端快捷键配置冲突 | 划词软件底层无脑 `SendInput` 盲发 `Ctrl+C` 取词 | 有选区时再按；无选区不要按热键 |
| 划词软件黑名单加了 `wt.exe` 没用 | 误以为黑名单失效 Bug | 黑名单只管鼠标划选浮窗，不管全局快捷键；且前台真进程是 `WindowsTerminal.exe` | 了解作用域边界，不要指望用黑名单防热键 |
| 按完快捷键打不出汉字 | 误以为输入法后台崩溃/被卸载 | 误触了 Windows 默认的 `Alt+Shift` 切换语言切到了美式键盘 | 按 `Win+Space` 切回；执行注册表脚本将该热键设为 3 彻底禁用 |
