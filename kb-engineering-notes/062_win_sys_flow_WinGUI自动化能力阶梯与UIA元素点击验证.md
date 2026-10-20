---
name: kb-windows-gui-automation
description: Windows GUI 自动化能力阶梯与脚本：UIA 无障碍树定位与 Invoke 点击、窗口枚举/还原/DPI 感知、PrintWindow 截图；含 Win32/WPF/Qt/WebView2 等栈对照与“只能模拟鼠标”边界。当需要脚本或 Agent 自动操作桌面软件、验证 GUI 行为，或遇到点不准/截图被裁/坐标错位/窗口最小化启动时查阅。
id: "062"
domain: win
scope: sys
type: flow
slug: "WinGUI自动化能力阶梯与UIA元素点击验证"
status: verified
created: "2026-09-22"
last_verified: "2026-10-20"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: true
---

# Windows GUI 自动化：能力阶梯、UIA 点击与窗口取证截图

> 适用读者：想用脚本自动操作或验证 Windows 桌面软件的开发者（含 AI Agent）。
> 本文所有代码均在 Windows 10/11 + PowerShell 5.1 实测通过（WebView2 应用与原生控件均已验证）。
> 源起：AI Agent 修改 Wails v3 (WebView2) 桌面应用后，需要自己切 Provider、点按钮、截图验证 GUI 行为。

---

## 一、业务场景与需求

这些场景会用到本文：

- **Agent 自验证 GUI**：改完界面代码后，AI 需要自己完成一次「切页签 → 点按钮 → 截图核对」，证明功能真的生效（而不是只跑单测）；
- **批量 / 无人值守操作**：定时任务里点掉弹窗、自动导出、循环执行重复点击；
- **取证与回归截图**：把固定操作流截成图片作为交付证据；
- **无障碍 / 替代输入**：用键盘与 UIA 代替鼠标完成操作流程。

先记住一句话，后面的一切都由此展开：
**在 Windows 上"操作别人的窗口"不需要任何特权**——同一用户、同一登录会话里的进程，天然可以枚举窗口、模拟输入、读取无障碍树；唯一挡路的是"跨权限级别"（提权程序，见 4.2）。

---

## 二、核心概念与底层剖析

### 2.1 UI Automation（UIA）是什么

- **人话**：这是 Windows 给"读屏软件"做的**程序结构读心术**。应用把界面里每个控件（按钮、输入框、菜单）注册成一棵"元素树"；每个元素带**名字、控件类型、状态**，并支持一组"控制模式（Pattern）"。
- **自动化 = 找到元素 + 用模式代理用户操作**。常用模式：

| 想干的事 | UIA 模式（Pattern） |
|---|---|
| 点按钮 | `InvokePattern` |
| 往输入框填字 | `ValuePattern` |
| 勾选 / 取消勾选 | `TogglePattern` |
| 展开下拉 / 折叠 | `ExpandCollapsePattern` |

- **为什么比模拟鼠标稳**：不用管像素坐标、窗口在哪、被谁遮挡、屏幕缩放多少——你在跟"语义"打交道（"点名为『登录』的按钮"），而不是跟"位置"打交道。

### 2.2 网页内容为什么也能被 UIA 点到（WebView2 / Chromium / Electron）

- 浏览器把 DOM 和 ARIA 语义映射成一棵**无障碍树（AXTree）**，再暴露给 UIA；
- Chromium 系（Chrome / Edge / WebView2 / Electron）的树是**惰性构建**的：只有当有 UIA 客户端连上来时才生成——所以**第一次查询可能"找不到元素"，重试几秒即可**（实测第一次找"OpenCode Go"按钮，重试第 2~3 次命中）；
- 网页控件会保留 DOM 语义：`<button>` → UIA Button + Invoke 模式；`<input>` → Edit + Value 模式。所以对 WebView2 应用，UIA 几乎和原生应用一样好使。

### 2.3 各技术栈可自动化程度对照

| 技术栈 | 自动化途径 | 备注 |
|---|---|---|
| Win32 标准控件 / WinForms | UIA（系统内置 provider） | 最完整：按钮/菜单/列表/文本框全支持 |
| WPF | UIA 原生一等支持 | 无额外配置 |
| Electron / WebView2 / CEF | Chromium AXTree → UIA | 惰性构建树，注意重试 |
| Qt 5.7+ / 6 | QAccessible → MSAA/UIA | 自绘控件可能没有节点 |
| Java Swing / AWT | Java Access Bridge → UIA | 需启用 jaccess |
| Flutter | Semantics 树 → UIA | 需开启 accessibility |
| 游戏 / 自绘引擎 / 远程桌面画面 | 只能 OCR/视觉 + 输入注入 | 没有语义树，坐标模拟是唯一路 |

**结论：不是"只有 WebView2 才能 UIA"，恰恰相反——原生控件通常比网页更好自动化；真正"只能模拟鼠标"的是完全自绘、没有无障碍树的应用。**

### 2.4 能力阶梯：从最稳到最通用

1. **UIA 模式调用**（首选，稳定、抗位移）；
2. **键盘流**：Tab / Enter / 快捷键（配合 UIA 定位焦点）；
3. **鼠标坐标模拟**：`SetCursorPos` + `SendInput`/`mouse_event`（通用兜底，脆弱）；
4. **OCR / 模板匹配 / 视觉定位**（自绘 UI 的最后一招）；
5. **程序自带 API / CLI**（只要存在，永远优先，别跟界面较劲）。

### 2.5 三个必踩的坑及其机制（照抄规避）

**坑 1：窗口"最小化启动"**
从隐藏 / 最小化的控制台父进程（AI Agent 的终端就属此类）启动 GUI 程序时，子进程会**继承父进程 STARTUPINFO 的 `wShowWindow` 标志**，窗口一出生就是最小化。表现：`EnumWindows` 里看到一个 199x34 的诡异矩形、坐标约 -32000，看起来像"窗口不存在"。
**解法**：拿到句柄后 `ShowWindow(hwnd, SW_RESTORE)`（值 9）还原。

**坑 2：DPI 虚拟化（截图缺一块、点击偏移的元凶）**
DPI-unaware 进程调用 `GetWindowRect` 得到的是**虚拟化逻辑坐标**——1920 物理像素宽的窗口只会报 1536（125% 缩放下）。拿它去分配截图位图或算点击点，必然裁切 / 偏移。
**解法**：脚本**第一件事**就 `SetProcessDPIAware()`，此后所有坐标统一为物理像素。

**坑 3：首次点击被"激活"吃掉**
`SetForegroundWindow` 对后台进程有限制（Windows 防抢焦点），窗口未激活时，**第一下点击只用于激活窗口**，不会落在按钮上。
**解法**：先点一次中性空白区（窗口中间），隔 300~500ms 再点目标；或先 `SetForegroundWindow` + 等待。

---

## 三、标准流水线与代码实现（PowerShell 实测骨架）

> 全部通过 `Add-Type` 现场 P/Invoke，**零安装**：UIA 客户端与 System.Drawing 都是 PowerShell 5.1 自带。
> ⚠️ 脚本文件若含中文，**必须存为「UTF-8 带 BOM」**，否则 PS 5.1 按 ANSI 读会乱码报解析错误。

### 3.1 全流程六步

1. 定位进程与主窗口（`EnumWindows` 按 PID + 可见性筛选，别迷信 `MainWindowHandle`）；
2. 还原窗口（`SW_RESTORE`）并置前台；
3. 读窗口矩形（此时已是物理像素）；
4. UIA 按名字找元素 → `InvokePattern.Invoke()` 点它；
5. 找不到则降级：先激活、再坐标点击；
6. `PrintWindow` 截图 → 读图验证。

### 3.2 Win32 桥（P/Invoke 一次性声明）

```powershell
Add-Type @'
using System; using System.Text; using System.Runtime.InteropServices;
public class Win {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int m);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, UIntPtr e);
  public struct RECT { public int Left, Top, Right, Bottom; }
  // 挑出该进程"面积最大的可见窗口"作为主窗；可按 GetClassName 进一步过滤
  public static IntPtr FindMain(uint pid) {
    IntPtr found = IntPtr.Zero; int best = 0;
    EnumWindows((h, l) => {
      uint p; GetWindowThreadProcessId(h, out p);
      if (p == pid && IsWindowVisible(h)) {
        RECT r; GetWindowRect(h, out r);
        int area = (r.Right - r.Left) * (r.Bottom - r.Top);
        if (area > best) { best = area; found = h; }
      }
      return true;
    }, IntPtr.Zero);
    return found;
  }
  public static void Click(int x, int y) {
    SetCursorPos(x, y); System.Threading.Thread.Sleep(120);
    mouse_event(0x0002, 0, 0, 0, UIntPtr.Zero);  // 左键按下
    System.Threading.Thread.Sleep(60);
    mouse_event(0x0004, 0, 0, 0, UIntPtr.Zero);  // 左键抬起
  }
}
'@
[Win]::SetProcessDPIAware() | Out-Null   # 坑 2 的解药，必须最先执行
```

### 3.3 UIA 查找与点击（首选路径）

```powershell
$proc = Get-Process -Name "your-app" | Select-Object -First 1
$h = [Win]::FindMain([uint32]$proc.Id)
[Win]::ShowWindow($h, 9) | Out-Null          # 坑 1：SW_RESTORE
[Win]::SetForegroundWindow($h) | Out-Null

Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::FromHandle($h)
$cond = New-Object System.Windows.Automation.PropertyCondition(
  [System.Windows.Automation.AutomationElement]::NameProperty, "要点的按钮名")
$el = $null
for ($i = 0; $i -lt 10 -and -not $el; $i++) {   # 坑：WebView2 树惰性构建，必须重试
  try { $el = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $cond) } catch {}
  if (-not $el) { Start-Sleep -Milliseconds 600 }
}
if ($el) {
  $el.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
  Write-Output "invoked: 要点的按钮名"
} else {
  Write-Output "NOT FOUND: 要点的按钮名"      # 别静默失败
}
```

### 3.4 降级路径：坐标点击（先激活、后点击）

```powershell
$r = New-Object Win+RECT
[Win]::GetWindowRect($h, [ref]$r) | Out-Null
[Win]::Click([int](($r.Left + $r.Right)/2), [int](($r.Top + $r.Bottom)/2))  # 坑 3：先点中性区激活
Start-Sleep -Milliseconds 400
[Win]::Click($r.Right - 100, $r.Top + 137)   # 再点目标坐标（坐标系：窗口左上 + 物理像素）
```

### 3.5 全内容截图（取证）

```powershell
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System; using System.Runtime.InteropServices;
public class Cap {
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  public struct RECT { public int Left, Top, Right, Bottom; }
}
'@
$r = New-Object Cap+RECT
[Cap]::GetWindowRect($h, [ref]$r) | Out-Null
$bmp = New-Object System.Drawing.Bitmap(($r.Right - $r.Left), ($r.Bottom - $r.Top))
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
[Cap]::PrintWindow($h, $hdc, 2) | Out-Null   # flags=2 即 PW_RENDERFULLCONTENT：
$g.ReleaseHdc($hdc)                          # GPU 合成的窗口（Chromium/WebView2）也能完整重绘
$bmp.Save("$env:TEMP\capture.png", [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose(); $g.Dispose()
```

### 3.6 实战案例要点（本文沉淀的源起）

- 应用：Wails v3（WebView2）桌面程序；目标：Agent 自动「切 Provider → 点采样 → 截图核对布局」。
- 战果：UIA 成功定位并点击了网页里的「OpenCode Go / 历史走势 / 仪表盘」按钮；「立即采样」因窗口未激活被吃一次点击 → 采用 3.4 先激活后点成功。
- 两个坑的现场指纹：窗口 199x34（最小化启动）；截图 1150x700 被裁成 920x560（DPI 未感知）。

---

## 四、交付验证与扩展建议

### 4.1 验证清单

- [ ] 点击后**目标状态真的变了**：再截一张图对比，或用 UIA 读回控件文本（`ValuePattern` / `Name`）；
- [ ] 截图尺寸 == 窗口物理尺寸（说明 DPI 感知已生效）；
- [ ] 日志里能看到 `invoked: xxx`（**注意：别让 `| Out-Null` 把函数的 Write-Output 吞掉**，本次实战踩过）；
- [ ] 副证据：进程/文件/网络等可观测副作用。

### 4.2 边界与安全

- 只能操作**同一用户会话、同一完整性级别**的窗口；管理员提权窗口会被 UIPI 拦截（点不动是正常现象，不是 bug）；
- 自动化会**真的触发真实操作**（真的发请求、真的删文件），别对着用户正在干活的窗口乱点；
- 验证脚本用完即删（放系统临时目录），不要污染项目目录。

### 4.3 不想手搓 P/Invoke 时的工具生态

| 工具 | 层次 | 适合 |
|---|---|---|
| pywinauto / FlaUI / WinAppDriver | UIA 封装（Python / .NET） | 复杂界面的自动化测试 |
| AutoHotkey v2 | 输入 / 快捷键 / 窗口管理 | 日常效率脚本 |
| pyautogui / OpenCV | 坐标 + 视觉 | 自绘 UI / 无无障碍树程序 |
| Playwright / CDP | 浏览器内部 | 纯 Web 场景（根本不用碰桌面自动化） |
