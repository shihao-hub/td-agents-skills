---
name: kb-windows-process-launch-forensics
description: Windows 进程"谁拉起的"取证方法论：explorer 父进程 + 无参数 ≠ 用户手动启动，只有排除法收敛价值。含 UserAssist（已被清空则取证能力缺失）、Run 键/计划任务/右键集成/Nilesoft/Win+R/Win+E 接管/事件日志（7001 登录、1000 崩溃）逐一排查清单，及 sh-everything-search idle_exit 保护条件无时效上限导致实例驻留 8.6 小时的永生漏洞与修复。排查后台常驻"不记得开过"的程序时查阅。
---

# Windows 进程启动来源取证与 Everything 闲置退出保护永生实例漏洞排障指南

## 一、 现象与结论直击

1. **现象**：2026-10-10 16:45:49 一个**无任何参数**的 `Everything.exe`（PID 28856）由 explorer.exe 拉起，以托盘形式驻留 **8.6 小时**，直到 2026-10-11 01:24 用户重新登录会话才随旧会话消失。用户记忆中未手动打开过。
2. **结论**：把所有自动拉起机制穷尽排除后，唯一站得住的解释是**经 shell 的手动/半手动启动**（开始菜单点击或 Win+S 搜 "everything" 回车，用完关窗留托盘、事后遗忘）。"用户不记得"与结论不矛盾——这是最无感的一类启动动作。
3. **无法 100% 实锤的根因**：最有力的取证键 UserAssist 在本机**已被清空**（见三-8）。

## 二、 完整时间线（交叉验证后的证据表）

| 时间（+08:00） | 事件 | 证据 |
| :--- | :--- | :--- |
| 10-10 03:25:17 | idle_exit 正常杀掉一个技能实例 | `idle_exit.log` 最后一条记录 |
| 10-10 04:00:50 | **最后一次** es_query 技能调用 | `last_use.txt`（此后再未更新） |
| 10-10 16:45:49 | 无参数实例由 explorer 拉起 | Win32_Process（CreationDate + ParentProcessId） |
| 10-10 16:44~16:45 | 仅 IsolatedUserMode 事件 | System 日志（无 boot/logon/唤醒 → 非系统级时刻） |
| 10-11 00:45± | 首轮排查确认 28856 存活 | "约 8 小时前启动" |
| 10-11 01:24:41 | GCUService.exe 崩溃（Application 1000） | 与 Everything/explorer 无关 |
| 10-11 01:24:43 | User32 事件 7001（用户登录通知） | System 日志 |
| 10-11 01:24:44 | explorer 重启（新 PID 8140），28856 随旧会话终止 | 当前进程表 + LastBootUpTime 未变（机器没重启，是**会话重登**） |

> [!IMPORTANT]
> 机器 2026-10-04 18:08 开机后**从未重启**（`Get-CimInstance Win32_OperatingSystem | Select LastBootUpTime`），而 explorer 换了实例 → 必然发生了**注销重登 / 会话切换**，而非开机。登录会话（User32 7001）会终止旧会话全部用户进程——这是 28856 消失的真正原因，与 idle_exit 无关（log 无新记录可证）。

## 三、 取证手段清单（本次全部实测）

| # | 手段 | 查法 | 本次结论 |
| :--- | :--- | :--- | :--- |
| 1 | 父进程 + 命令行 | `Get-CimInstance Win32_Process`（CommandLine、ParentProcessId、CreationDate） | explorer 父 + 无参 → 只能证明"经 shell"，**不能证明"手动"** |
| 2 | HKCU/HKLM Run 键 | `Get-ItemProperty ...\CurrentVersion\Run` | 无 Everything → 排除注册表自启动 |
| 3 | 计划任务式自启动 | `Get-ScheduledTask \| Where TaskName -match Everything` | 无 → 排除（Everything 新版自启动用计划任务而非 Run 键，**只查 Run 键不够**） |
| 4 | Explorer 右键集成 | ini 的 `context_menu_type` + `HKCR\Directory\shell` 与 `...\shellex\ContextMenuHandlers` | 未启用 → 排除"右键 Search Everything"由 explorer 直启的路径 |
| 5 | 第三方菜单集成 | Nilesoft Shell 的 `*.nss` 配置 grep everything | 无配置 → 排除（Nilesoft 会重构整个右键菜单，是常见隐藏入口） |
| 6 | Win+R 历史 | `HKCU\...\Explorer\RunMRU` | 无 everything → 削弱 Win+R 假设 |
| 7 | Win+E 接管 | `HKCU\Software\Classes\Folder\shell` + 版本 | Everything **1.4.1 无此功能**（1.5 alpha 才有）→ 排除 |
| 8 | **UserAssist**（shell 启动计数） | `HKCU\...\Explorer\UserAssist\{CEBFF5CD-...}\Count`（值名 ROT13） | **整个键不存在（已被清空）** → 取证能力缺失，无法实锤也无法证伪 |
| 9 | 事件日志 | Application 1000/1001/1002（崩溃/挂起）+ System 7001/7002（登录/注销）+ Winlogon | 定位实例终止原因（会话重登）与排除崩溃 |
| 10 | 应用自身状态 | `last_use.txt` + `idle_exit.log` 交叉时间线 | 证明 16:45 实例**不是**技能拉的（无 `-startup` 参数 + 技能 04:00 后再无活动） |
| 11 | Prefetch | `C:\Windows\Prefetch\*.pf` 文件时间 | **普通用户无读取权限**（需管理员），本次不可用 |

> [!IMPORTANT]
> **explorer 父进程 + 无参数的等价来源**：双击桌面/开始菜单/任务栏图标、Win+S 搜索回车、Win+R、右键菜单项（含第三方菜单扩展）、`.lnk`/`.efu` 关联双击、以及程序显式 `explorer.exe <exe>` 代启。**它们在进程层面不可区分**——AI 排查报告若直接写"父进程是 explorer → 用户手动启动"，属于排除法收敛冒充实证，必须要求它补全上述清单。

## 四、 idle_exit 保护永生漏洞（本次真正的收获）

### 1. 漏洞

`sh-everything-search/scripts/idle_exit.ps1` 原保护条件：

```powershell
if ($main.StartTime.ToUniversalTime() -gt $lastUse) { exit 0 }   # 实例比最后技能活动新 → 视为手动 → 永不杀
```

条件**没有时效上限**：手动实例一旦出现且技能之后没被再次调用（`lastUse` 不再更新），它就**永生**——本次实例驻留 8.6 小时直到注销会话。设计意图是"别杀用户正在用的"，实际效果是"用户遗忘的实例无限期占 ~430MB"。

### 2. 修复（2026-10-11 已落地）

保护仅对"年轻"实例生效，超龄照常 `es -exit` 并在 `idle_exit.log` 记 `(protect expired)`：

```powershell
$protectHours = 2   # 顶部参数区，与 $idleMinutes 并列
...
$protectExpired = ($startedAt -gt $lastUse) -and (([DateTime]::UtcNow - $startedAt).TotalHours -ge $protectHours)
if (-not $protectExpired) { exit 0 }
```

### 3. 遗留盲区（未修，风险可控）

`es_query.ps1` 的顺序是"先 `Start-Process -startup` → 等就绪（最长 ~20s）→ 再写 `last_use.txt`"，窗口内 idle_exit 会把技能实例误判为手动。但该窗口同时被 idle_exit 的"**es.exe 进程在飞即退出**"条件（就绪探测循环会产生 es 进程）天然覆盖，残余竞态窗口仅毫秒级，不值得为此加复杂度。

## 五、 方法论沉淀

1. **"谁拉起的"排查先画时间线再归因**：`last_use.txt`/`idle_exit.log` 这类应用侧状态文件与系统事件日志交叉，比单点进程快照有力得多（本次正是时间线排掉了"技能拉起"并锁定了终止时刻）。
2. **AI 生成的进程分析报告要核查其排除清单的完备性**：只查 Run 键 + 启动文件夹就断言"手动"是不够的（漏计划任务自启动、右键集成、第三方菜单、UserAssist）。
3. **UserAssist 一旦被隐私清理工具清空，shell 启动取证永久失效**——本机 {CEBFF5CD} 键整个不存在。日常若保留取证能力，应避免清理该键。
4. **机器没重启但 explorer 换实例 = 会话重登/切换**（用 LastBootUpTime + User32 7001/7002 判定），旧会话用户进程随之全灭——排查"进程怎么没了"时先想到这一层。
