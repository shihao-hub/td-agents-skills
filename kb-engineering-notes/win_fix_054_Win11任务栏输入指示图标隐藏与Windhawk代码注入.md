---
name: kb-windows11-ime-tray-icon-windhawk
description: Windows 11 25H2 任务栏「输入指示」图标（豆包输入法头像与「英」语言栏）无法用原生设置隐藏的排障与 Windhawk 代码注入方案：剖析设置项移除、TSF 语言栏项在 explorer 内绘制与注册表被系统回写的根因，给出 Windhawk 安装、mod 配置、UIA 验证脚本与回滚路径。当任务栏出现删不掉的输入法图标、设置里没有「输入指示器」时查阅。
version: 1.0.0
created: 2026-10-13
updated: 2026-10-13
---

# Windows 11 豆包输入法任务栏「输入指示」图标隐藏与 Windhawk 运行时代码注入指南

> **适用场景**：Windows 11 25H2（实测 build 26200.9457）任务栏通知区域常驻两个「任务栏输入指示」按钮——豆包输入法头像与 `英` 语言栏图标，鼠标悬停显示 `任务栏输入指示`。个性化设置里既找不到「输入指示器」开关，改语言栏注册表、杀输入法进程、删键盘布局全部无效，图标按 `Win+Space` 后还会自己长回来。本文记录从零定位到用 Windhawk 注入代码彻底隐藏的完整过程。

---

## 一、现象与报错直击

### 1. 任务栏实况（UIA 取证）

系统托盘里出现**两个**同名前缀按钮，肉眼只能看到豆包头像与 `英` 两个字，无法判断谁是谁。用 UI Automation 遍历 `SystemTray.NormalButton` 读出真实 tooltip 才区分开：

```text
任务栏输入指示 单击右键打开豆包输入法设置                    ← 豆包头像（IME 语言栏附加图标）
任务栏输入指示 简体中文(中国大陆) / 豆包输入法 / 若要切换输入法，请按 Windows 键 + 空格键。  ← 英（Windows 语言栏主图标）
```

取证脚本（PowerShell 原生 UIA，无需任何依赖）：

```powershell
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::RootElement
$cond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ClassNameProperty, 'Shell_TrayWnd')
$tray = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $cond)
$b = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ClassNameProperty, 'SystemTray.NormalButton')
$btns = $tray.FindAll([System.Windows.Automation.TreeScope]::Descendants, $b)
"NormalButton count: $($btns.Count)"
$btns | ForEach-Object { if ($_.Current.Name) { "  [$($_.Current.Name -replace "`r`n", ' / ')]" } }
```

**这条脚本同时是全程唯一可信的验收手段**：图标会随 `Win+Space` 动态增删，肉眼与截图都不可靠，只看按钮数量与 tooltip 字符串。

### 2. 排查轨迹：被实测排除的五条死路

| # | 尝试的路线 | 实测结果 | 结论 |
|---|---|---|---|
| 1 | 设置 → 个性化 → 任务栏 → 其他系统托盘图标 →「输入指示器」 | 25H2 该设置项**已不存在**，只剩「语言栏」相关残留文本 | 原生 UI 路线被砍 |
| 2 | 语言栏选项隐藏：写 `HKCU\Software\Microsoft\CTF\LangBar` 的 `ShowStatus=3` + `ExtraIconsOnMinimized=0`，重启 explorer / ctfmon | 图标**纹丝不动**，且这两个值被系统改回 `0` / `1` | 注册表面板路线被堵 |
| 3 | 删掉「ENG 英语(美国) 美式键盘」布局 | 它**不在**「已安装的键盘」列表里（列表只有豆包），设置界面删不掉 | 无操作入口 |
| 4 | 改豆包自身配置 `%APPDATA%\DoubaoIme\conf\config.json` 的 `appearance.showStatus=false` 并重启 `ImeService` | 托盘图标不受影响 | 图标不是豆包自绘托盘图标 |
| 5 | 杀掉 `ImeService.exe` + `ImeWatchdog.exe`，重启 explorer / ctfmon | 图标**仍在** | 也不是输入法进程挂的托盘图标 |

### 3. 关键复现条件

- **重启后一开始没有图标，但只要按一次 `Win+Space` 切换一次键盘布局，图标立即被创建并常驻**；
- 25H2 设置资源字符串交叉验证（`C:\Windows\SystemResources\Windows.UI.SettingsAppThreshold\pris\Windows.UI.SettingsAppThreshold.zh-CN.pri`）：

```python
data = open(r"C:\Windows\SystemResources\Windows.UI.SettingsAppThreshold\pris"
            r"\Windows.UI.SettingsAppThreshold.zh-CN.pri", "rb").read()
print(data.count("输入指示器".encode("utf-16-le")))  # 0 —— 设置项确实已被移除
print(data.count("语言栏".encode("utf-16-le")))      # 4 —— 只剩语言栏相关文案
```

---

## 二、底层根因剖析

### 1. 两个图标属于两套不同的注册源，必须**分别**关闭

| 图标 | 身份 | TSF 侧来源 | 对应 mod 开关 |
|---|---|---|---|
| 豆包头像 | IME **语言栏附加图标**（Supplementary icon） | 豆包通过 TSF `ITfLangBarItem` 注册的图像项 | `hideLanguageSupplementaryIcons` |
| `英` | Windows **语言栏主图标** | 系统语言栏本体（LanguageText/Image icon） | `hideLanguageBar` |

**这是本次最大的实操坑**：两者由不同开关控制，只开一个只会消失一个（实测 `hideLanguageBar=1` 后按钮数 6 → 5，`英` 消失而豆包头像仍在）。

### 2. 真正绘制图标的是 `explorer.exe`，不是 `ctfmon.exe`，更不是输入法进程

实测 explorer 进程内加载的模块：

```text
tsf-oime.dll            C:\Windows\System32\tsf-oime.dll                                  ← 豆包 TSF 注册入口
tsf-oime-core.dll       C:\Program Files\DoubaoIME\versions\v0.9.1.22\tsf-oime-core.dll
doubaoime-rpc-new.dll   C:\Program Files\DoubaoIME\versions\v0.9.1.22\doubaoime-rpc-new.dll
```

核查命令：

```powershell
Get-Process explorer | ForEach-Object {
    $_.Modules | Where-Object { $_.ModuleName -match 'tsf|oime|MSCTF' } |
        Select-Object ModuleName, FileName
}
```

- Windows 11 把任务栏输入指示的绘制搬进了 **explorer 的 XAML 托盘**（`SystemTray` 命名空间），`ctfmon.exe` 内并未加载豆包 TSF 模块；
- 图标对应 XAML 类名（mod 源码中的 Hook 锚点）为 `SystemTray.LanguageTextIconContent`、`SystemTray.LanguageImageIconContent`（语言栏）与 `SystemTray.ImageIconContent`（附加图标）；
- 因此「杀输入法进程」「杀 ctfmon」注定无效——**图标是 explorer 自己画的**，输入法只是通过 TSF 提交了「我要一个语言栏项」的注册。

### 3. `Win+Space` 为何是触发器

TSF 语言栏项在输入法/键盘布局**发生切换时才被重新枚举与创建**。系统启动后在没有任何切换动作时，explorer 尚未向语言栏索取图标列表，所以表现为「重启后干净、切一次就长出来」。这也是所有「改完注册表重启 explorer 看起来好了、一按 `Win+Space` 又回来」现象的物理原因。

### 4. 语言栏注册表为何被系统回写

`HKCU\Software\Microsoft\CTF\LangBar` 的 `ShowStatus` / `ExtraIconsOnMinimized` 是 **TSF 运行时状态槽**而非持久化配置：只要仍有 IME 通过 TSF 注册了语言栏项，TSF 在下一轮初始化时就会把这两个值归一化回它认为的当前状态（本机稳定为 `ShowStatus=0`、`ExtraIconsOnMinimized=1`）。所以在「有图标存在」的前提下改它，等于和 TSF 抢写一变量，必然被覆盖。

### 5. 结论：原生 API 层已无出口，只能在上层「不画」

25H2 移除了用户态开关，注册表又被 TSF 接管，唯一可控的切口是**任务栏渲染层**——在 explorer 进程内 Hook 掉这两个语言栏图标的创建逻辑。这正是 Windhawk 这类「运行时代码注入框架」的用武之地。

---

## 三、标准解决 SOP

### Step 0：Windhawk 是什么，为什么选它

**Windhawk**（Ramen Software 出品，作者 m417z）是一个**Windows 运行时代码注入（mod）框架**：

- 后台以**服务**形式常驻（服务名 `Windhawk`，`LocalSystem` / 自动启动），按 mod 声明的 `@include` 目标进程列表，把编译好的 DLL 注入进去；
- 所谓 **mod** 就是一份带元数据头的 C++ 源码（`.wh.cpp`），用 `// ==WindhawkMod==` 声明 `@id / @name / @include explorer.exe / @architecture x86-64`，正文写 Hook 逻辑；UI 里点「安装」后由框架本地编译成 DLL 注入，**不需要自备编译环境**；
- **零系统文件改动**：不替换 `explorer.exe`、不打系统补丁，关掉开关即恢复原状，Windows 更新不会冲掉（更新后 explorer 重新注入即可）；
- 选它而不是 ExplorerPatcher 类方案的核心理由：单一 mod 就能**只**关这两个图标、粒度可控、随时 disable 且卸载干净（自带 `uninstall.exe`）。

常用命令行开关（安装目录 `command-line.txt` 有载）：

```powershell
windhawk.exe -tray-only     # 只留托盘图标，不开主窗口
windhawk.exe -exit -wait    # 退出
windhawk.exe -restart       # 重启引擎
windhawk.exe -safe-mode     # 安全模式：不加载任何 mod（mod 把 explorer 搞崩时的救命绳）
```

### Step 1：下载官方安装包并校验

```powershell
# 官方 Release 直链（实测 1.7.3 为当前最新）
$url = 'https://github.com/ramensoftware/windhawk/releases/download/v1.7.3/windhawk_setup.exe'
Invoke-WebRequest $url -OutFile 'D:\Users\Softwares\windhawk_setup.exe'
(Get-FileHash 'D:\Users\Softwares\windhawk_setup.exe' -Algorithm SHA256).Hash
# 期望：5116CC1703384AAC88B8D7A3B57F172AEA5DA32B6DF7355FB2F8247D23813C8F
```

### Step 2：静默安装（**注意 `/D=` 实测被忽略**）

```powershell
# 管理员 PowerShell 执行
Start-Process -FilePath 'D:\Users\Softwares\windhawk_setup.exe' `
  -ArgumentList '/S','/D=D:\Users\Softwares\Windhawk' -Verb RunAs -Wait
```

**实测坑**：安装包确认为 NSIS 打包（`Nullsoft` 标识）、二进制内也不含硬编码 `C:\Program Files` 路径，但 `/D=` 依然被忽略，实际落点为 **`D:\Program Files\Windhawk`**。要指定目录就在向导里手选，别指望 `/S /D=`：

```powershell
# 安装落点核查（不要用 Test-Path 猜目录，直接问服务与卸载注册项）
(Get-CimInstance Win32_Service -Filter "Name='Windhawk'").PathName
# → "D:\Program Files\Windhawk\windhawk.exe" -service
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*' |
    Where-Object DisplayName -like '*Windhawk*' |
    Select-Object DisplayName, DisplayVersion, InstallLocation, UninstallString
```

### Step 3：安装 mod `Taskbar tray system icon tweaks`

1. 打开 `windhawk.exe` → **Mods** → 「浏览Mods」（需联网访问 windhawk.net）→ 搜索 **`Taskbar tray system icon tweaks`**（作者 `m417z`，Win11 专用，实测 v1.3.1）→ **Install**（首次会本地编译数秒）；
2. 联网不可用时的**离线兜底**：Mods 页右下角「**新建Mod**」，把该 mod 的 `.wh.cpp` 源码整份粘贴进去即可本地安装；源码可取
   `https://raw.githubusercontent.com/ramensoftware/windhawk-mods/main/mods/taskbar-tray-system-icon-tweaks.wh.cpp`。

源码级核对结论（安装前可自行确认 Hook 锚点，避免装错 mod）：

```text
hideLanguageBar                  → SystemTray.LanguageTextIconContent / LanguageImageIconContent  （＝英）
hideLanguageSupplementaryIcons   → SystemTray.ImageIconContent                                    （＝豆包头像）
@include explorer.exe            @architecture x86-64
```

### Step 4：勾选两个开关（**一个都不能少**）

进入该 mod 的 **设置**，只打开下面两项，其余（音量/网络/电池/麦克风/GPS/Studio Effects/Recall/铃铛/显示桌面按钮宽度）**保持不动**，避免顺手改掉别的托盘图标：

```text
☑ Hide language bar                  → 干掉「英」
☑ Hide language supplementary icons   → 干掉豆包头像
```

点 **保存设置**，explorer 会由引擎自动重启注入（屏幕闪一下正常）。没生效就手动 `Stop-Process -Name explorer -Force`（会自动拉起）。

设置项落盘位置（可用于脚本化核对/批量下发）：

```powershell
Get-ItemProperty 'HKLM:\SOFTWARE\Windhawk\Engine\Mods\taskbar-tray-system-icon-tweaks\Settings' |
    Select-Object hideLanguageBar, hideLanguageSupplementaryIcons
# 期望：hideLanguageBar = 1 且 hideLanguageSupplementaryIcons = 1
```

### Step 5：Windhawk 关键落点速查（排障/备份用）

| 用途 | 路径 |
|---|---|
| 主程序 / 卸载器 | `D:\Program Files\Windhawk\windhawk.exe`、`uninstall.exe` |
| 安装配置 | 安装目录 `windhawk.ini`（`EnginePath`、`AppDataPath=%ProgramData%\Windhawk`、`RegistryKey=HKLM\SOFTWARE\Windhawk`） |
| mod 源码 | `C:\ProgramData\Windhawk\ModsSource\<mod-id>.wh.cpp` |
| 编译产物 DLL | `C:\ProgramData\Windhawk\Engine\Mods\64\<mod-id>_<版本>_<hash>.dll` |
| 注入状态 | `C:\ProgramData\Windhawk\Engine\ModsWritable\mod-status\`、`mod-task\` |
| 开关与启用态 | `HKLM\SOFTWARE\Windhawk\Engine\Mods\<mod-id>`（`Disabled` / `Settings` 子键） |

---

## 四、验证与防复发闭环

### 1. 主验收：UIA 按钮数与 tooltip 断言

保存设置后重跑第一节的 UIA 脚本，**必须同时满足**：

- `NormalButton count` 从 6 降为 **4**（只剩「显示隐藏的图标」、CPU 监控、CC Switch、Snipaste）；
- 输出中**不再出现任何** `任务栏输入指示` 字符串。

> 只降 1 个（6 → 5）说明两个开关只开了一个：剩下那条 tooltip 是 `单击右键打开豆包输入法设置` 即附加图标未关，是 `简体中文(中国大陆)…` 即语言栏主图标未关。

### 2. 触发条件复测（必做）

图标是**动态创建**的，静态验收不算数：

1. 按一次 **`Win+Space`** 切换键盘布局；
2. 再跑一次 UIA 脚本；
3. **断言**：按钮数仍为 4、`任务栏输入指示` 不再出现。

### 3. 回滚与应急

```powershell
# ① 临时停用全部 mod（explorer 被 mod 搞崩时首选）
& 'D:\Program Files\Windhawk\windhawk.exe' -safe-mode

# ② 只停用这一个 mod：UI 里把该 mod 关掉，或直接写注册表禁用位
Set-ItemProperty 'HKLM:\SOFTWARE\Windhawk\Engine\Mods\taskbar-tray-system-icon-tweaks' -Name Disabled -Value 1

# ③ 彻底卸载（保留/清理 ProgramData 见向导选项）
& 'D:\Program Files\Windhawk\uninstall.exe'
```

### 4. 防复发清单

- **Windows 大版本升级后检查一次**：explorer 被替换会重新注入，正常情况无需重配；若图标回归，先看 `HKLM\SOFTWARE\Windhawk\Engine\Mods\<id>` 的 `Disabled` 是否为 `0`、`Settings` 两项是否仍为 `1`；
- **不要再去碰** `HKCU\Software\Microsoft\CTF\LangBar`：那是 TSF 运行时状态槽，改了会被回写，纯属浪费轮次；
- **不要再杀** `ImeService.exe` / `ImeWatchdog.exe` / `ctfmon.exe` 试图去图标：绘制方是 explorer；
- **不要为「ENG 美式键盘」折腾**：它不在「已安装的键盘」列表内，界面无删除入口，且与这两个图标无因果关系；
- 验收一律以 **UIA 实测 + `Win+Space` 复测** 为准，截图与肉眼不可作为结论。
