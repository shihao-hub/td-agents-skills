---
name: kb-wt-pe-patch-defender-false-positive
description: Windows Terminal 定制版 PE 资源图标注入后数字签名失效，触发 Windows Defender 实时保护云端机器学习启发式木马误杀（Trojan:Win32/Bearfoos.A!ml）排障。当定制版 WT 无故消失、快捷方式报错“WindowsTerminal.exe 已经更改或移动”时查阅。
version: 1.0.0
created: 2026-10-16
id: "061"
domain: ide
scope: terminal
type: fix
slug: "WinTerminal定制版PE图标损坏Defender误杀排障"
status: verified
last_verified: "2026-10-20"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: true
---

# 61-WindowsTerminal定制版PE图标注入签名破损触发Defender启发式木马Bearfoos误杀排障指南

> **适用场景**：
> 当部署并运行独立免安装定制版 Windows Terminal（通过 Win32 API `BeginUpdateResourceW` 注入自定义 ICO 图标，如 `titanium` 钛金款或 `pure_dark` 极简黑款）后，终端突然无故消失；点击桌面或任务栏快捷方式弹出系统错误对话框：**“该快捷方式所指向的项目‘WindowsTerminal.exe’已经更改或移动，因此该快捷方式无法正常工作。是否删除该快捷方式？”**。
> 本手记基于真实生产环境事件日志与 Defender 威胁遥测记录，讲透 Win32 PE 资源重写导致的微软签名断裂机理、Defender 云端机器学习启发式查杀特征，以及标准还原与白名单排除防线 SOP。

---

## 一、现象与报错直击

### 1. 桌面交互表象
用户此前正常使用的定制版 Windows Terminal 突然无法打开，点击任务栏或开始菜单图标时，Windows 资源管理器弹出经典失效对话框：

```text
[快捷方式存在问题]
该快捷方式所指向的项目“WindowsTerminal.exe”已经更改或移动，因此该快捷方式无法正常工作。
是否删除该快捷方式？
[ 是(Y) ]   [ 否(N) ]
```

同时查看独立版部署目录（如 `D:\Users\Softwares\WindowsTerminal\`），发现原本的 `WindowsTerminal.exe` 离奇消失，仅残留未被直接拦截的 `wt.exe` 启动代理及其他 DLL。

### 2. Windows Defender 威胁遥测现场取证
通过 PowerShell 查询 Defender 实时拦截记录：

```powershell
Get-MpThreatDetection | Select-Object -First 1 | Format-List
```

输出确定性取证数据：

```text
ActionSuccess                  : True
AMProductVersion               : 4.18.26090.9
CleaningActionID               : 2 (Quarantine / 隔离)
CurrentThreatExecutionStatusID : 3
InitialDetectionTime           : 2026/10/16 11:51:07
LastThreatStatusChangeTime     : 2026/10/16 11:51:35
ProcessName                    : D:\Users\Softwares\WindowsTerminal\WindowsTerminal.exe
Resources                      : {file:_C:\Users\...\Start Menu\Programs\Terminal.lnk,
                                 file:_D:\Users\Softwares\WindowsTerminal\WindowsTerminal.exe}
ThreatID                       : 2147731250
ThreatName                     : Trojan:Win32/Bearfoos.A!ml
```

同时 Defender 操作事件日志（`Microsoft-Windows-Windows Defender/Operational`，事件 ID 1116）显示：
- 检测来源：**实时保护（Real-time Protection）**；
- 严重级别：**严重（Severity: 5）**；
- 触发前因：Defender 刚于几秒前（11:50:49）拉取了云端安全智能更新（`1.461.41.1`）。

---

## 二、底层根因剖析

### 1. 微软官方数字签名与 PE 校验链断裂
- 官方发布的 Windows Terminal 便携免安装包内的 `WindowsTerminal.exe` 带有由 `Microsoft Corporation` 颁发的合法 Authenticode 数字签名，PE 头中记录了签名证书表（Security Directory / `IMAGE_DIRECTORY_ENTRY_SECURITY`）与整个二进制文件的原始哈希摘要。
- 为了彻底解决 Windows 11 深色/浅色/高对比度模式下图标反弹问题，定制脚本调用了 Win32 核心资源 API（`BeginUpdateResourceW` / `UpdateResourceW` / `EndUpdateResourceW`），物理重写了 PE 资源段中的 `Group 101 (IDI_APPICON)`、`Group 102`、`Group 103` 及各个子图标数据。
- **后果**：向已签名的 PE 文件直接写入字节会使整个文件的哈希值改变，PE 头校验和与数字签名证书不匹配。此时二进制文件处于**“声明自己是微软官方程序、但签名已失效损坏”**的状态。

### 2. 云端机器学习模型启发式误杀（`!ml` 判定机制）
- 报毒名称 `Trojan:Win32/Bearfoos.A!ml` 中的 **`!ml`** 后缀代表 **Machine Learning（机器学习启发式检测）**，而非基于已知样本的静态 MD5 特征码。
- 微软 Defender 云保护引擎（Cloud Protection Engine）具备严格的防篡改启发式策略：
  1. 文件名标识为 Windows 原生核心组件（如 `WindowsTerminal.exe`、`explorer.exe` 等）；
  2. PE 内部元数据保留有微软版权声明；
  3. 但 Authenticode 签名失效或被非法注入资源段。
- 在杀软防御视角中，这种特征与特洛伊木马常用的“注入系统可执行文件进行白加黑劫持”行为高度吻合。因此在云端智能库更新或触发展开扫描时，模型给予其最高危险评级（Severe），并执行强制隔离（CleaningActionID: 2），连同其开始菜单的快捷方式作为受污染对象一并隐藏/移除。

---

## 三、标准抢救与修复 SOP

### 步骤 1：保护快捷方式（切勿点“是”）
在遇到“快捷方式存在问题”弹窗时，**必须点击“否(N)”**，保留原有快捷方式的链接属性。

### 步骤 2：从 Windows 安全中心快速还原被隔离文件
1. 按快捷键 `Win + S` 输入并打开 **“Windows 安全中心”**（Windows Security）；
2. 依次点击：**“病毒和威胁防护”** $\to$ **“保护历史记录”**；
3. 找到最近一次时间点被隔离的严重威胁：`Trojan:Win32/Bearfoos.A!ml`；
4. 点击展开详情，确认受影响文件路径为：
   `D:\Users\Softwares\WindowsTerminal\WindowsTerminal.exe`；
5. 点击右下角 **“操作”**（Actions）下拉菜单，选择 **“还原”**（Restore）（或“在设备上允许”）。

还原后，`WindowsTerminal.exe` 将无损释放回原目录，开始菜单和任务栏图标即可重新正常双击启动。

### 步骤 3：配置 Defender 白名单排除项（彻底免疫）
为防止 Defender 下一次拉取云端智能定义库时再度误杀，必须将独立版目录设为排除项。

#### 途径 A：图形界面操作（推荐）
1. 在 PowerShell 终端中执行系统协议命令，秒级直达设置页并复制目录路径：
   ```powershell
   Start-Process "windowsdefender://threatsettings"
   Set-Clipboard -Value "D:\Users\Softwares\WindowsTerminal"
   ```
2. 在打开的“病毒和威胁防护设置”页面中，向下滑动找到 **“排除项”** $\to$ 点击 **“添加或删除排除项”**；
3. 点击 **“添加排除项”** $\to$ 选择 **“文件夹”**（触发 UAC 弹窗时点“是”）；
4. 在路径选择窗口中按 `Ctrl + V` 粘贴路径并确认。

#### 途径 B：管理员命令行操作
以管理员身份启动 PowerShell（`Win + X` 然后按 `A`），运行：

```powershell
Add-MpPreference -ExclusionPath "D:\Users\Softwares\WindowsTerminal"
```

---

## 四、验证与防复发闭环

### 1. 验证目标文件状态与排除项
执行验证命令，确认可执行文件就位且排除项已登记：

```powershell
# 1. 校验二进制文件完整性
Test-Path "D:\Users\Softwares\WindowsTerminal\WindowsTerminal.exe"
Get-Item "D:\Users\Softwares\WindowsTerminal\WindowsTerminal.exe" | Select-Object Name, Length, LastWriteTime

# 2. 校验快捷方式目标是否自愈
$sh = New-Object -ComObject WScript.Shell
$sh.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Terminal.lnk").TargetPath
```

### 2. 灾后全自动重装与重新注入流水线（兜底容灾）
若文件在隔离区已被彻底清空无法还原，在完成上述**步骤 3 白名单配置**后，直接调用现有资产库脚本重放全流程，即可 100% 幂等恢复：

```powershell
# 自动拉取官方最新免安装包 -> 部署目录 -> PE资源物理重烧录 -> 刷新外壳缓存
uv run "D:\Users\language_projects\go_projects\taskbarguard\scripts\wt\patch_wt_icon.py" --auto-setup --style titanium --restart-explorer
```
