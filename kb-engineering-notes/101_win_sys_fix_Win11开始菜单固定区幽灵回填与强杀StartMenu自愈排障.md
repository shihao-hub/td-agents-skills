---
id: "101"
domain: "win"
scope: "sys"
type: "fix"
slug: "Win11开始菜单固定区幽灵回填与强杀StartMenu自愈排障"
status: "verified"
created: "2026-10-25"
last_verified: "2026-10-29"
superseded_by: null
deprecation_reason: null
compatibility:
  os: ["windows"]
falsification_signals:
  - "若整个开始菜单无法打开或点击无响应，属于 XAML 宿主崩溃或 AppX 注册表断裂，非本篇固定项幽灵回填"
  - "若固定项中的自定义应用全丢且 LocalState 只剩 start2.bin（0 字节）与 24 项默认 JSON 快照，仍属本篇 explorer 强杀连坐的终态，按 §三步骤 4 重建布局处理，不要误判为磁盘损坏"
invocation:
  auto_trigger: true
  trigger_keywords: ["开始菜单固定项变多", "莫名其妙再次显示", "被重置了的感觉", "画图计算器记事本又冒出来了", "开始菜单幽灵回填", "重启资源管理器后开始菜单还原", "explorer 重启", "restart-explorer", "taskbarguard", "StartMenuExperienceHost", "ContentDeliveryManager", "OemPreInstalledAppsEnabled", "start2.bin", "88000963", "模板无料化", "删除回填清单"]
---

# 101-Windows 11 开始菜单固定区幽灵回填与强杀 StartMenu 进程自愈排障

> **适用场景**：在 Windows 11 环境下，用户自定义固定的开始菜单应用原本整洁有序，但最近“偶尔会莫名其妙在下方多出一整排官方默认应用”（如画图、计算器、时钟、记事本、截图工具、OneNote、机械革命等 OEM 工具、Solitaire 纸牌游戏）。用户手动取消固定后，过一段时间或执行图标刷新后又再次“复活”，给人一种被“静默重置”的困扰。通过现场逆向取证，剖析 `StartMenuExperienceHost.exe` 进程强杀引发 `start2.bin` 脏退出自愈，以及系统 `ContentDeliveryManager` 策略回填通道的双重诱因，给出彻底根治加固方案。

---

## 一、现象与报错直击

### 1. 现场实况还原
- **视觉特征**：
  - 用户自定义钉选的应用（如 `AlwaysBindWindow`、`Alt-Tab Terminator`、`DeepSeek Harness`、`ZedHub`、`docsearch` 等）**完好保留在第一排**；
  - 但在自定义应用正下方，整整齐齐追加冒出一整排系统出厂预装项：
    > **画图、计算器、时钟、记事本、截图工具、OneNote、文件资源管理器、机械革命 (OEM)、Solitaire & Casual Games (休闲纸牌)**
- **行为特征**：
  - 用户在图标上右键选择“从'开始'屏幕取消固定”将其清理干净；
  - 但在后续进行系统重启、应用商店静默更新、或运行某些任务栏/图标刷新脚本后，这批官方应用**再次幽灵般重新回填到固定区底部**；
  - 现象表现为“局部追加”而非“全盘重置”，说明系统底层的固定数据并未彻底损坏，而是触发了增量补齐。

### 2. 现场注册表与系统状态取证
通过 PowerShell 查询当前用户注册表 `HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager`，现场捕获到系统策略全开：

```powershell
Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
```

| 注册表键值 | 实测现场值 | 机制解释 |
|---|:---:|---|
| **`OemPreInstalledAppsEnabled`** | `1` (开启) | **允许系统向开始菜单推送 OEM 厂商应用（“机械革命”由此回填）** |
| **`PreInstalledAppsEnabled`** | `1` (开启) | **允许系统向开始菜单推送内置工具（画图、计算器、记事本等）** |
| **`SilentInstalledAppsEnabled`** | `1` (开启) | **允许静默下载并固定推广应用（“Solitaire & Casual Games”由此回填）** |
| **`SubscribedContent-338389Enabled`** | `1` (开启) | **开始菜单固定区订阅推荐与自动合并通道** |
| **`SystemPaneSuggestionsEnabled`** | `1` (开启) | 系统面板建议通知 |

同时检查 `%LocalAppData%\Packages\Microsoft.Windows.StartMenuExperienceHost_cw5n1h2txyewy\LocalState`，发现 `start2.bin` 的修改时间与外部脚本执行时间存在强相关吻合。

### 3. 第二种触发路径实况（2026-10-26 现场，explorer 连坐）

用户反馈「重启资源管理器后开始屏幕又还原」，`taskbarguard --restart-explorer` 图标换肤后复现。只读取证结果：

| 取证项 | 实测值 | 判读 |
|---|---|---|
| `ContentDeliveryManager` 五个推送键 | 全部 `0`（加固仍生效） | 本次**不是** CDM 静默回填，根治配置没丢 |
| `explorer.exe` / `StartMenuExperienceHost.exe` 启动时间 | 同为 `20:41:45` | 强杀 explorer 时**开始菜单宿主被连坐重启** |
| `LocalState\88000963`（JSON，24H2+ 布局快照） | 7806 B，`20:41:46` 被改写，`items[]` 仅 24 项出厂默认（Edge/Office/Store/设置/OEMPrimary/OEMSecondary/照片/纸牌/画图/计算器/时钟/记事本/截图/OneNote/资源管理器） | 宿主重启后第 1 秒执行自愈合并，把默认模板写进快照 |
| `LocalState\start2.bin` | **0 字节**，`20:56:21` | 写盘事务被切断，留下空文件；下次宿主启动会按布局缺失再合并一轮（本机后续实测：再强杀一次可自动重建为 39292 B 健康文件） |

> `88000963` 的 head 是 `7b226974656d733a5b7b226170706c69636174696f6e49`（`{"items":[{"applicationI`），是 24H2 起新增的 JSON 布局快照，与旧 `start2.bin` 并存。排查时两个文件都要看。

---

## 二、底层根因深度剖析

```text
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ 诱因一：外部脚本或优化工具强杀 StartMenuExperienceHost.exe                              │
 │   taskkill /F /IM StartMenuExperienceHost.exe                                          │
 │   或其连坐源：taskkill /F /IM explorer.exe / Stop-Process -Name explorer -Force         │
 └────────────────────────────────────────┬───────────────────────────────────────────────┘
                                          │  （内存中 start2.bin 事务被硬切断，未正常落盘）
                                          ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ Windows 11 开始菜单宿主异常死亡与冷启动自愈                                           │
 │   1. 再次唤醒时，检测到上次进程属“非正常终止 (Abnormal Termination)”                  │
 │   2. 容错逻辑判定：当前用户固定列表完整性存疑，进入 Fallback 流程                     │
 │   3. 读取系统预置模板: DefaultLayouts.xml (含 OEM 厂商定制分区与预装工具)             │
 └────────────────────────────────────────┬───────────────────────────────────────────────┘
                                          │
                                          ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ 诱因二：ContentDeliveryManager 后台回填通道全开                                         │
 │   OemPreInstalledAppsEnabled = 1 / SilentInstalledAppsEnabled = 1                       │
 │   ==> 系统执行 Layout Merge，将出厂默认项整排“追加合并”至用户已有自定义项下方          │
 └────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1. 为什么“强杀 StartMenuExperienceHost”会成为直接触发点？
- **数据持有模型**：Windows 11 的开始菜单是独立的 XAML/UWP 宿主应用（`StartMenuExperienceHost.exe`），其固定项数据并不散落在桌面文件夹，而是由该宿主集中维护于二进制文件 `start2.bin` 中。
- **脏退出代价**：很多图标刷新或任务栏守卫脚本盲目调用 `taskkill /F /IM StartMenuExperienceHost.exe` 试图让开始菜单重新加载图标。但是，当该进程持有写入句柄、或刚响应过用户界面点击而未完全 Flush 脏数据时，`/F` 强制切断会导致写入断裂。
- **容错合并机制**：Windows 诊断机制将其记录为崩溃。当下一次用户点击开始菜单、系统重新拉起 `StartMenuExperienceHost.exe` 时，系统为了防止“用户开始菜单全空变砖”，会自动执行 **`EnsureDefaultPinnedItems()` 自愈补全**，将系统的默认布局模板与当前文件进行差集合并。

### 2. 为什么“被追加”的全是出厂预装与推广应用？
- 微软在 Windows 11 中内置了内容分发管理器（`ContentDeliveryManager`）。在 OEM 品牌电脑（如机械革命、联想、戴尔）出厂时，厂商会将自家控制中心集成进系统的 `DefaultLayouts.xml`。
- 一旦上述自愈逻辑触发，或者后台发生 Windows Update 静默维护与微软商店应用更新，由于注册表中的 `OemPreInstalledAppsEnabled`、`SilentInstalledAppsEnabled` 均为 `1`，系统便获得了“将出厂默认清单重新塞回开始菜单”的合法授权。

### 3. 外壳图标刷新的真正规范：根本无需杀 StartMenu
Windows 11 刷新任务栏图标、桌面图标或开始菜单图标，**核心依赖外壳 Shell 通知与位图缓存重建**：
1. `os.utime(lnk_path, None)`：刷新快捷方式物理文件时间戳；
2. `ie4uinit.exe -show`：Windows 原生内置的图标缓存刷新接口；
3. `SHChangeNotify(0x08000000, 0x1000, 0, 0)`（`SHCNE_ASSOCCHANGED` + `SHCNF_FLUSH`）：全局广播文件关联与外壳更新。
以上三步均为**只读与非侵入式广播**，毫秒级生效且绝对不会中断 `StartMenuExperienceHost.exe` 的事务，强杀该进程是完全错误且有害的做法。

### 4. 补充诱因：强杀 `explorer.exe` 同样连坐（比直接杀 StartMenu 更隐蔽）

- **连坐链**：`Stop-Process -Name explorer -Force` / `taskkill /F /IM explorer.exe` → 外壳 COM 与 Shell 服务宿主被拆 → `StartMenuExperienceHost.exe` 随之异常终止（实测两者重启时间戳完全相同）→ 宿主重启时判定上次异常退出 → 读 `DefaultLayouts.xml` + `LayoutModification.json` 做**增量合并自愈**。
- **危害不在"多几个图标"，而在写盘**：自愈同时重写布局文件；若 Explorer 与开始菜单被反复强杀，`start2.bin` 会被截断成 **0 字节**，此后每次登录都按"布局缺失"再合并一次，表现为「怎么删都会还原」。
- **OEM 加速项**：本机 `%LocalAppData%\Microsoft\Windows\Shell\LayoutModification.json` 仍含 `primaryOEMPins`（机械革命 `ControlCenter3_wrbgcf7aesyd8!App`），`DefaultLayouts.xml`（64 KB，2024/4/1）含 OEM 与预装分区；即便 CDM 推送键全为 0，自愈合并仍会把这两份模板里的条目补回来。
- **常见肇事代码**（本机 `go_projects/taskbarguard` 5 个 patch 脚本）：`subprocess.run(["powershell","-NoProfile","-Command","Stop-Process -Name explorer -Force"])`；`wt`、`deepseek_harness`、`antigravity`、`idea`、`vscode` 五份均已命中，改动其一别忘同改其余四份。

---

## 三、标准抢救与修复 SOP

### 步骤 1：关闭系统 ContentDeliveryManager 自动回填通道（一键注册表加固）
在普通 PowerShell 终端中执行以下命令，彻底封死 Windows 11 在后台静默回填 OEM 和推广应用的通道：

```powershell
# 1. 禁用 ContentDeliveryManager 预装与推广回填
$cdmPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
Set-ItemProperty -Path $cdmPath -Name "OemPreInstalledAppsEnabled" -Value 0 -Type DWord
Set-ItemProperty -Path $cdmPath -Name "PreInstalledAppsEnabled" -Value 0 -Type DWord
Set-ItemProperty -Path $cdmPath -Name "SilentInstalledAppsEnabled" -Value 0 -Type DWord
Set-ItemProperty -Path $cdmPath -Name "SubscribedContent-338389Enabled" -Value 0 -Type DWord
Set-ItemProperty -Path $cdmPath -Name "SystemPaneSuggestionsEnabled" -Value 0 -Type DWord

# 2. 禁用云端消费类体验推送策略 (CloudContent)
$cloudPolicy = "HKCU:\Software\Policies\Microsoft\Windows\CloudContent"
if (!(Test-Path $cloudPolicy)) { New-Item -Path $cloudPolicy -Force | Out-Null }
Set-ItemProperty -Path $cloudPolicy -Name "DisableWindowsConsumerFeatures" -Value 1 -Type DWord
```

### 步骤 2：下线自动化工具与脚本中的 StartMenu + Explorer 强杀指令
检查所有本地或项目内的任务栏维护、外壳刷新脚本（如 `taskbarguard`、`wt-customizer` 等）：
- **彻底删除**：`taskkill /F /IM StartMenuExperienceHost.exe`
- **同样彻底删除**：`Stop-Process -Name explorer -Force` / `taskkill /F /IM explorer.exe`（运行在用户交互态时连坐开始菜单，运行在计划任务非交互态时还会黑屏假死）
- **`--restart-explorer` 参数处置**：仅保留 `utime` + `ie4uinit` + `SHChangeNotify` 的常规刷新；确需重建 `iconcache*.db` 时改为**改完后手动重启电脑/注销**，不要由脚本在线强杀 Explorer
- **规范保留**：纯粹使用以下无副作用三连击完成刷新：
  ```python
  # 1. 触碰快捷方式时间戳
  os.utime(lnk_path, None)

  # 2. 唤醒系统原生 ie4uinit
  subprocess.run(["ie4uinit.exe", "-show"], check=False)

  # 3. 广播 SHChangeNotify 外壳关联变更
  ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x1000, 0, 0)
  ```

### 步骤 3：拔掉回填清单（根治手段，2026-10-29 本机三次强杀实测有效）

只封 CDM 通道、只禁强杀都不够——宿主崩溃自愈还会读本机「回填清单」。三处一起清（先全部备份到 `%APPDATA%\language_projects\startmenu-layout-backup\<日期>\`）：

1. **清空出厂布局模板** `%LocalAppData%\Microsoft\Windows\Shell\DefaultLayouts.xml`（出厂 64707 B）→ 替换为最小空模板：

   ```xml
   <?xml version="1.0" encoding="utf-8"?>
   <FullDefaultLayoutTemplate
       xmlns="http://schemas.microsoft.com/Start/2014/FullDefaultLayout"
       xmlns:start="http://schemas.microsoft.com/Start/2014/StartLayout"
       Version="1">
     <StartLayout>
       <Group Name="DesktopApplicationGroup" />
     </StartLayout>
     <SecondaryTileLayout />
   </FullDefaultLayoutTemplate>
   ```

2. **清空 OEM 追加项** `%LocalAppData%\Microsoft\Windows\Shell\LayoutModification.json`（原文件只含 `primaryOEMPins` → 机械革命 `ControlCenter3_wrbgcf7aesyd8!App`）→ 写入 `{}`；

3. **删除回填清单缓存** `%LocalAppData%\Packages\Microsoft.Windows.StartMenuExperienceHost_cw5n1h2txyewy\LocalState\88000963`（7806 B JSON，`{"items":[{"applicationId":...}]}` 共 24 项默认应用）。**删掉后宿主不会自动重建**。

> **关键认知**：`88000963` 是「默认应用清单缓存」而非当前布局。用户自定义固定项与取消固定结果都保存在 `start2.bin`（二进制，正常约 38–40 KB）。实测删掉 `88000963` 后连续强杀 explorer 三次，开始菜单自定义项完好、`start2.bin` 从 39292 B 缩到 38236 B（忠实记录取消操作），默认项零复活。

### 步骤 4：修复已被写成 0 字节的布局文件（防"每次登录都还原"）

先做只读取证：

```powershell
$ls = "$env:LOCALAPPDATA\Packages\Microsoft.Windows.StartMenuExperienceHost_cw5n1h2txyewy\LocalState"
Get-ChildItem $ls -File | Select-Object Name, Length, LastWriteTime
```

判读与处置：

- `start2.bin` 长度 **0** 且同目录存在数字命名的 JSON 快照（如 `88000963`，`{"items":[...]}`）：属宿主事务中断后的残局。**不要直接删 `start2.bin`**（删除会让系统按模板全量重建）；
- 处置顺序：先执行步骤 1、2 封死推送与强杀 → 打开开始菜单，随便固定/取消固定一个应用，让宿主写出一份健康布局（`start2.bin` 恢复为几百字节到数 KB）→ 再逐一取消固定多余默认项 → **正常注销或重启一次**，确认布局稳定；
- 若自定义项已全丢且手头有旧布局备份（`start2.bin` / `88000963` 的历史副本），停掉 `StartMenuExperienceHost.exe` 前**先备份现有两份文件**再回填，回填后同样走一次正常注销。

### 步骤 5：最后一次清理并固化
1. 打开 Windows 11 开始菜单；
2. 对当前残留的画图、计算器、记事本、机械革命、纸牌等图标逐一右键选择 **“从'开始'屏幕取消固定”**；
3. 由于策略已封死且再无外部脚本强杀中断事务，此时 `start2.bin` 将安全完成最终状态持久化，不再复发。

---

## 四、验证与防复发闭环

### 1. 策略落地断言验证
执行以下 PowerShell 查询，验证所有推送开关均已被锁定为 `0`：

```powershell
Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" |
  Select-Object OemPreInstalledAppsEnabled, PreInstalledAppsEnabled, SilentInstalledAppsEnabled, SubscribedContent-338389Enabled
```

**预期输出**：
```text
OemPreInstalledAppsEnabled       : 0
PreInstalledAppsEnabled          : 0
SilentInstalledAppsEnabled       : 0
SubscribedContent-338389Enabled  : 0
```

### 2. 实机防复发压力测试
1. 运行 `taskbarguard run --style 8_underlit_chrome deepseek_harness` 执行图标换肤；
2. 观察控制台输出，确认没有任何针对 `StartMenuExperienceHost.exe` 或 `explorer.exe` 的强杀日志；
3. 打开开始菜单，验证固定项仅保留用户自定义应用，下方无任何幽灵回填；
4. 即使重启电脑或系统处于网络联机闲置状态，出厂默认布局永不再现。

### 3. 连坐型复发的快速判定（30 秒）

```powershell
Get-Process explorer, StartMenuExperienceHost | Select-Object Name, Id, StartTime
$ls = "$env:LOCALAPPDATA\Packages\Microsoft.Windows.StartMenuExperienceHost_cw5n1h2txyewy\LocalState"
Get-ChildItem $ls -File | Select-Object Name, Length, LastWriteTime
```

- 两者 `StartTime` 完全相同 → 本次发生过 explorer 强杀连坐；
- 数字快照文件 `LastWriteTime` 紧贴该时刻（+1 秒内）→ 自愈合并已完成，追加的就是 `DefaultLayouts.xml` + `LayoutModification.json` 里的条目；
- `start2.bin` 长度为 0 → 还欠一次健康写盘，按 §三步骤 4 收尾，否则下次登录继续还原。

### 4. 根治验收记录（2026-10-29，本机三次强杀实测）

| 阶段 | 操作 | 结果 |
|---|---|---|
| 基线 | 备份并清空两份模板 + 备份 88000963 | `DefaultLayouts.xml` 64707→356 B，`LayoutModification.json` 106→3 B，均无 BOM、XML/JSON 校验通过 |
| 实验一 | 清空模板后强杀 explorer | 模板未被重建；`88000963` 被重写仍为 24 项；`start2.bin` 由 0 B 修复为 39292 B；自定义项未丢 |
| 实验二 | 删除 `88000963` 后强杀 | 文件未重建（MISSING）；`start2.bin` 保持 39292 B |
| 实验三 | 用户取消固定 14 项默认应用后再强杀 | `88000963` 仍 MISSING；`start2.bin` 39292→38236 B；默认项**零复活**，自定义项完好 |

**边界与复检**：

- `C:\Users\Default\AppData\Local\Microsoft\Windows\Shell\` 下还有一套同源模板（64707 B / 106 B，新用户模板，需管理员权限），运行时自愈未读取它；若日后复发，先查这里是否被回灌；
- `Settings\settings.dat` 被宿主独占，无法离线解析；布局真实数据以 `start2.bin` 二进制为准（正常 38 KB 量级，0 字节即异常）；
- 系统大版本更新或功能更新后复检 `88000963` 是否再生、两份模板是否被还原；一旦被还原，重跑 §三步骤 3。
