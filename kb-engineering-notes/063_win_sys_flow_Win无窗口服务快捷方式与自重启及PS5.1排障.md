---
name: kb-windowless-service-launcher
description: Windows 一键无窗口启动常驻服务的落地骨架（快捷方式 + 幂等启动器 + 自重启 helper），及 PowerShell 5.1 静默失败链路排障。当要双击启动本地 Web 服务、消除黑框 conhost、给服务加重启按钮，或遇到 Start-Process NO_PROXY 重复键、EnvironmentVariables 为 null、参数名不匹配致脚本静默终止时查阅。
created: 2026-10-16
updated: 2026-10-18
---

# Windows 一键无窗口启动服务与自重启机制及 PowerShell 5.1 静默失败链路

> **一句话**：把「双击就起一个无窗口本地服务」和「服务能重启自己」做对，难点不在功能，而在 **窗口语义的保持** 与 **PowerShell 5.1 的一连串静默失败**。

---

## 一、业务场景与需求拆解（Type B 输入）

**典型诉求**：本地跑一个长期驻留的 Web 服务（如 `dsh web --port 11111`），希望：

| # | 需求 | 反面体验 |
|:--|:--|:--|
| R1 | 双击桌面快捷方式即启动 | 要开终端手敲命令 |
| R2 | **全程无控制台窗口** | 弹黑框，关掉窗口=杀掉服务 |
| R3 | **幂等**：已在跑就只开界面 | 重复启动撞端口 `EADDRINUSE` |
| R4 | 复用指定的浏览器应用窗口（PWA） | 每次开普通标签页 |
| R5 | 服务能**重启自己**（改配置/插件后一键生效） | 手动找 PID + 杀 + 重启 |
| R6 | 日志可查、失败可诊断 | 静默不生效，无从下手 |

**输入源**：一条服务启动命令 + 一个浏览器入口。
**交付目标**：1 个桌面快捷方式 + 2 个脚本 + 1 个服务内重启端点，任意一条路径都不产生可见窗口。

> R2 与 R5 是本条目的两条主线，也是绝大多数坑的产地。
---

## 二、技术核心难点与底层剖析

### 2.1 进程三权分立：谁启动、谁被杀、谁重启

任何"无窗口 + 可自重启"的方案都必须先想清这三件事：

```text
【启动链】wscript.exe(Hidden) → powershell.exe(Start-DshWeb.ps1) → cmd /c bat → node(服务)
   ↑ 每个环节的窗口设置都会向下影响子进程

【重启链】服务内插件 → powershell -EncodedCommand → WMI Win32_Process.Create
                                                      ↓
                                    helper.ps1（脱离服务进程树！）
                                                      ↓
                                        taskkill /F /T 服务 → 重放命令行
```

**铁律一：重启 helper 绝不能是服务进程的后代。**
helper 若在服务进程树内，`taskkill /F /T <服务PID>` 会连 helper 自己一起杀掉，形成"杀了但起不回来"的死局。Windows 上让新进程脱离进程树的可靠手段是 **WMI 创建**（`Win32_Process.Create`），其父进程是 WMI provider 而非调用者。

**铁律二：杀掉目标用 `/T`（只向下不向上）。**
`taskkill /T` 杀"该 PID 及其子孙"，**不会**向上波及其父进程。所以 `taskkill /F /T <服务PID>` 对"从终端手敲启动的服务"是安全的——终端是它的父，不在 `T` 的范围内。这与"杀父进程树"语义完全相反，务必分清。

### 2.2 无窗口的本质：控制台是「继承」还是「新建」

这是本条目的核心机制，也是黑框 bug 的根因。

| 场景 | 控制台来源 | 结果 |
|:--|:--|:--|
| 终端里手敲 `dsh web` | 终端自己提供 | 有窗口（正常） |
| `cmd /c start /b` + `CreateNoWindow` | **继承**已隐藏的控制台 | **无窗口** |
| `Start-Process node.exe`（不带 `-WindowStyle`） | **新建**一个控制台 | **有黑框** |
| `Start-Process -WindowStyle Hidden` | 新建但隐藏 | 无窗口 |

关键点：`node.exe` 是**控制台子系统程序**。当它被 `Start-Process` 拉起且未指定窗口样式时，Windows 会为它**新建一个可见控制台**——继承关系在此断裂。

**由此得出 bug 的精确表述**：服务本来是"无窗口出生"的，**重启动作把这个性质弄丢了**。

```powershell
# ❌ 丢失窗口性质：新服务带黑框，MCP 子进程 stdout 全部涌入
$launchArgs = @{ FilePath = $ExePath; ArgumentList = @($RelaunchArgs) }

# ✅ 保持无窗口性质
$launchArgs = @{ FilePath = $ExePath; ArgumentList = @($RelaunchArgs); WindowStyle = 'Hidden' }
```

对应的**冷启动侧**则是：

```powershell
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName        = "$env:WINDIR\System32\cmd.exe"
$psi.Arguments       = '/d /c "' + $batFile + '"'
$psi.UseShellExecute = $false
$psi.CreateNoWindow  = $true                                          # 关键
$psi.WindowStyle     = [System.Diagnostics.ProcessWindowStyle]::Hidden  # 关键
[void][System.Diagnostics.Process]::Start($psi)
```

> **窗口机制更深的原理**（PE 子系统 2 GUI 镜像、DefTerm 控制台委托断层、`SW_HIDE` 不等于不分配控制台）见 `52-` 与 `57-` 两条，此处不重复展开。

### 2.3 幂等性：用「端口反查」而不是「PID 文件」

进程 PID 每次重启都变，PID 文件还会过期。**监听端口才是稳定锚点**：

```powershell
# 谁在监听目标端口 → 既是"是否已在运行"的判据，也是"该杀谁"的答案
$conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
$ownerPid = if ($conn) { [int]$conn.OwningProcess } else { 0 }
```

**自重启还能进一步复用目标的命令行**，实现参数零漂移：

```powershell
# 从监听进程反查它自己的完整命令行，重启时原样重放
$p = Get-CimInstance Win32_Process -Filter ("ProcessId = " + $ownerPid)
# $p.CommandLine   -> "node.exe" "...\bin.js" web --port 11111 --no-open
# $p.ExecutablePath -> D:\...\node.exe     （重启所需）
```

**多实例场景的坑**：若同时跑多个服务实例，千万别用"扫端口找第一个像样的"。应从 HTTP 请求的 `Host` 头取自己的端口——那才是无歧义的自我标识。

```js
// 反例：扫描所有监听端口，可能认错实例
// 正解：端口来自请求本身
const port = portFromHost(req.headers.host);   // "127.0.0.1:11111" -> 11111
```

同时要处理无端口形态（`localhost` 默认 80）与 IPv6（`[::1]:11111`）。

### 2.4 Web 服务自重启的固有难题：页面永远等不到答案

```text
浏览器 ──POST /restart──> 服务进程 ──200 OK──> 浏览器
                              │
                              └─ 1.2s 后 helper 杀掉服务进程 ← 就是它自己
```

承载页面的那个进程自杀了，**没有任何实体能回来通知页面**。而且新实例的会话 token 通常重新随机生成，旧页面手里的 token 已失效，用旧 token 问任何东西都会 403。所以「等待重启」不能靠外部通知，只能**页面自我轮询 + 自动重载**：

```js
async function waitForWebRestart(port) {
  const deadline = Date.now() + 90000;
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 1000));
    try {
      const res = await fetch(ROUTE + '/status', { cache: 'no-store', headers: { accept: 'application/json' } });
      if (!res.ok) continue;
      const next = await res.json();
      if (next && next.ok === true && (typeof port !== 'number' || next.port === port)) {
        window.location.reload();
        return;
      }
    } catch { /* 仍不可达，继续等 */ }
  }
}
```

注意三点：轮询期间的连接失败是**预期**（catch 静默继续，不弹错误）；桌面模式下窗口本身会被关掉，所以该分支只在 web 模式启用；**`/quit` 绝不能轮询** —— 它同样杀掉服务却不再拉起，轮询的前提（目标会自行回到同一可观测状态）不成立，只会白转 90 秒，必须按 `action === 'restart'` 区分。
---

## 三、标准实现流水线与代码骨架

### 3.1 第一层：VBS 无窗口包装（消掉启动瞬间的闪窗）

`.lnk` 直接指向 `powershell.exe` 必然闪出控制台。用 `wscript` + `Run(..., 0, False)` 从出生即隐藏：

```vbscript
' Launch-DshWeb.vbs —— 只做一件事：以完全隐藏的方式拉起 PowerShell 启动器
Option Explicit
Dim shell, fso, psScript, cmd
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
psScript = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "Start-DshWeb.ps1")
If Not fso.FileExists(psScript) Then
    MsgBox "Launcher script not found: " & psScript, 16, "Launcher"
    WScript.Quit 1
End If
cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & psScript & """"
shell.Run cmd, 0, False    ' 0 = 隐藏窗口, False = 不等待
```

### 3.2 第二层：幂等启动器骨架（`Start-DshWeb.ps1`）

```powershell
[CmdletBinding()]
param([int]$Port = 11111, [int]$TimeoutSec = 60)

$ErrorActionPreference = 'Stop'
$LogDir     = Join-Path $env:TEMP 'dsh-web-launcher'
$LogFile    = Join-Path $LogDir 'launcher.log'
# 服务日志必须按端口隔离（见 §4.6 的争用坑）
$SvcLogFile = Join-Path $LogDir ('dsh-web.p' + $Port + '.log')

function Write-Diag([string]$Message) {
    # 最佳努力：日志坏了绝不能阻断服务启动
    try {
        if (-not (Test-Path -LiteralPath $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
        Add-Content -LiteralPath $LogFile -Value ('[' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '] ' + $Message) -Encoding utf8
    } catch { }
}
# 分支一：已在运行 → 只开界面，绝不重启（保护用户当前会话）
if ([bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)) {
    Write-Diag ('port ' + $Port + ' already listening; reuse, no restart')
    Start-ChromeApp -Url $Url
    exit 0
}

# 分支二：冷启动 —— 用 bat 中转，让 cmd 负责重定向，
# 启动器因此不持有任何流句柄，退出后服务照样能写日志
$batBody = '@echo off' + "`r`n" +
           'start "" /b "<node.exe 绝对路径>" "<bin.js 绝对路径>" web --port ' + $Port +
           ' --no-open >> "' + $SvcLogFile + '" 2>&1' + "`r`n"
[System.IO.File]::WriteAllText($batFile, $batBody, [System.Text.ASCIIEncoding]::new())

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName        = Join-Path $env:WINDIR 'System32\cmd.exe'
$psi.Arguments       = '/d /c "' + $batFile + '"'
$psi.UseShellExecute = $false
$psi.CreateNoWindow  = $true
$psi.WindowStyle     = [System.Diagnostics.ProcessWindowStyle]::Hidden
$proc = [System.Diagnostics.Process]::Start($psi)   # 注意：不用 Start-Process（见 §4.2）

# 就绪判定用 TCP 连通，比等进程存活可靠
foreach ($i in 1..(($TimeoutSec * 5))) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $a = $c.BeginConnect('127.0.0.1', $Port, $null, $null)
        if ($a.AsyncWaitHandle.WaitOne(500, $false) -and $c.Connected) { $c.Close(); Start-ChromeApp; exit 0 }
        $c.Close()
    } catch { }
    Start-Sleep -Milliseconds 200
}
Write-Diag 'TIMEOUT waiting for port'
exit 1
```

**三条设计要点**：

1. **幂等优先于重启**：端口已被占用时**不杀**任何进程——那可能是用户正在用的会话。
2. **窗口设置贯穿全链**：`CreateNoWindow` + `WindowStyle Hidden`，缺一即闪窗。
3. **绝对路径**：`cmd /c` 的工作目录不可控，`node` 必须写绝对路径（nvm 环境下尤甚）。

### 3.3 第三层：自重启 helper（脱离进程树 + 保持无窗口）

```powershell
# 由服务内插件以 WMI 方式拉起；父进程是 WMI provider，故不在服务进程树内
param(
    [Parameter(Mandatory = $true)][string]$ExePath,   # node.exe 绝对路径
    [Parameter(Mandatory = $true)][int]$MainPid,
    [int]$HostPid = 0, [switch]$TreeKill, [switch]$NoRelaunch, [int]$DelayMs = 1200,
    [int]$Port = 0,                                   # >0 即 web 模式
    [string]$RelaunchArgs = '',
    [string]$WorkingDir = ''                          # 注意：调用方必须写 -WorkingDir
)

Start-Sleep -Milliseconds $DelayMs      # 先让 HTTP 响应冲刷到浏览器

# 从端口反查当前监听者（而非依赖过期 PID）
$conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
$targetPid = if ($conn) { [int]$conn.OwningProcess } else { $MainPid }

# 只杀目标及其子孙；/T 不向上，故不会碰到用户的终端
& taskkill.exe /F /T /PID $targetPid

# 必须等端口真正释放，否则新实例 EADDRINUSE
$deadline = (Get-Date).AddSeconds(20)
while ((Get-Date) -lt $deadline) {
    if (-not (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)) { break }
    Start-Sleep -Milliseconds 300
}

if ($NoRelaunch) { exit 0 }

$launchArgs = @{ FilePath = $ExePath; ArgumentList = @($RelaunchArgs); WindowStyle = 'Hidden' }
if ($WorkingDir -ne '' -and (Test-Path -LiteralPath $WorkingDir)) { $launchArgs['WorkingDirectory'] = $WorkingDir }
Start-Process @launchArgs
```

**WMI 拉起 helper 的标准写法**（让 helper 从出生即隐藏）：

```powershell
$cl = @'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\...\helper.ps1" -ExePath "D:\...\node.exe" -MainPid 0 -HostPid 1234 -DelayMs 1200 -Port 11111 -RelaunchArgs "\"D:\...\bin.js\" web --port 11111 --no-open" -WorkingDir "D:\..." -TreeKill
'@
$startup = ([WMIClass]"Win32_ProcessStartup").CreateInstance()
$startup.ShowWindow = 0            # SW_HIDE：出生即隐藏，避免 -WindowStyle 解析前的闪窗
$r = ([WMIClass]"Win32_Process").Create($cl, $null, $startup)
# ReturnValue = 0 即成功；$r.ProcessId 为 helper 的 PID
```

### 3.4 第四层：桌面快捷方式

| 属性 | 值 |
|:--|:--|
| 目标 | `C:\Windows\System32\wscript.exe` |
| 参数 | `"C:\...\Launch-DshWeb.vbs"` |
| 起始位置 | VBS 所在目录 |
| 图标 | 可沿用原应用的 `.ico` |
| 运行方式 | 最小化（配合 VBS 的 `Run(...,0,...)` 彻底无窗） |

```powershell
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut("$([Environment]::GetFolderPath('Desktop'))\服务名.lnk")
$sc.TargetPath       = "$env:WINDIR\System32\wscript.exe"
$sc.Arguments        = '"C:\...\Launch-DshWeb.vbs"'
$sc.WorkingDirectory = 'C:\...'
$sc.WindowStyle      = 7
$sc.Save()
```
---

## 四、PowerShell 5.1 静默失败链路（本条最值钱的部分）

> 这一节的所有报错都真实发生过，且**每一条都伪装成别的问题**。共同特征：**失败得很安静**。

### 4.1 UTF-8 无 BOM + 中文注释 → 解析器崩溃，报错完全误导

**现象**：脚本执行报

```text
The Try statement is missing its Catch or Finally block.
Unexpected token '}' in expression or statement.
```

指向一个**语法完全正确**的 `try/catch`，而且行号还会随文件其他部分的改动而漂移。

**根因**：Windows PowerShell 5.1 对**无 BOM 的 UTF-8** 文件按系统 ANSI（中文环境为 GBK）解码。中文注释的多字节序列被误读，破坏了引号/括号配对的词法结构，解析器于是在别处报错。

**修复**（任选其一）：

```powershell
# 方案 A（推荐）：被 5.1 执行的脚本一律保持纯 ASCII
$bytes = [System.IO.File]::ReadAllBytes($path)
@($bytes | Where-Object { $_ -gt 127 }).Count      # 必须为 0

# 方案 B：确实要写中文，就带 BOM（5.1 见 BOM 会按 UTF-8 解码）
[System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($true))
```

> 该目录的规范里也强调过 UTF-8 BOM 相关问题，参见 `10-`（`invalid character '\ufeff'`）与本条形成互证：**BOM 在别处是祸、在 PS 5.1 读中文脚本时是解药**。

### 4.2 `Start-Process` 撞上大小写重复的环境变量

**现象**：

```text
Start-Process : Item has already been added. Key in dictionary: 'NO_PROXY'  Key being added: 'no_proxy'
```

**根因**：机器上同时存在 `NO_PROXY` 与 `no_proxy`。PS 5.1 的 `Start-Process` 构建环境块时用了**大小写敏感的字典**，于是同一逻辑键被插入两次而抛错。`Start-Process` 直接不可用。

**修复**：绕开 `Start-Process`，改用 `[System.Diagnostics.Process]::Start(...)`（它自己构建环境块，能容忍重复键）。

### 4.3 `ProcessStartInfo.EnvironmentVariables` 在 5.1 下是 `null`

**现象**：想手动规整环境变量，于是写

```powershell
$psi.EnvironmentVariables.Clear()
$psi.EnvironmentVariables[$key] = $value
```

结果依次报：

```text
You cannot call a method on a null-valued expression.
Cannot index into a null array.
```

**根因**：实测探针证明，在 PS 5.1 下 `UseShellExecute = $false` 时 `$psi.EnvironmentVariables` **返回 `null`**（不是空集合，是 `null`）。所以"自己修环境变量"这条路根本不通。

```powershell
# 一行探针即可自证
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.UseShellExecute = $false
$null -eq $psi.EnvironmentVariables     # -> True
```

**修复**：环境变量的事交给 `cmd` 中转（cmd 用系统 API 构建环境块，天然容忍重复键），PowerShell 侧不碰环境变量。

### 4.4 `Set-Content -Value $array` 用分号连接元素 → 命令被注释吞掉

**现象**：生成的 `.cmd` 内容看起来"差不多对"，但执行后**什么都没发生**，退出码为 1。

**根因**：`Set-Content` 接收数组时，用当前分隔符（PS 5.1 下是 `;`）把元素**连成一行**。于是

```powershell
$batLines = @(
    '@echo off',
    'rem Generated by launcher.',
    'start "" /b "node.exe" "bin.js" web --port 11111 >> log 2>&1'
)
Set-Content -LiteralPath $bat -Value $batLines -Encoding Ascii
```

生成的是**一行**：

```bat
@echo off;rem Generated by launcher.;start "" /b "node.exe" ...
```

`rem` 把后面整条 `start` 命令注释掉了 —— 服务**永远不会启动**，且毫无提示。

**修复**：显式构造带 `CRLF` 的单一字符串，用 `WriteAllText` 落地。

```powershell
$crlf = [string][char]13 + [string][char]10
$batBody = '@echo off' + $crlf + 'rem Generated.' + $crlf + 'start "" /b "..."' + $crlf
[System.IO.File]::WriteAllText($batFile, $batBody, [System.Text.ASCIIEncoding]::new())
```

> 同类陷阱：**反引号续行**在 5.1 下也容易被解析器误判为语句结束。稳妥做法是改用 splatting 传参，不写跨行续行。

### 4.5 参数名不匹配 → 参数绑定阶段终止；且 WMI 启动成功 ≠ 脚本成功

**现象**：helper **完全没有执行痕迹**（连它自己第一行的日志都没有），而调用方收到的却是 WMI 的"启动成功"。

**根因**：helper 声明的是 `$WorkingDir`，调用方传的是 `-WorkingDirectory`。PowerShell 对参数名做前缀匹配，但这个差异太大匹配不上，于是：

```text
找不到与参数名称"WorkingDirectory"匹配的参数。
NamedParameterNotFound
```

脚本在**参数绑定阶段**就终止了，根本没进入函数体，所以"没有任何日志"。

**由此得到一条更普适的判据**：`Win32_Process.Create` 返回 `0 <PID>` 只说明**进程被创建**，**不代表脚本执行成功**。判断"到底有没有干活"，必须看**它自己产出的证据**（日志、副作用、端口状态），不能拿启动返回值替代。

**定位手法**（关键）：把 helper 的 stdio 重定向到文件，错误才现形。

```powershell
$cmdLine = 'cmd.exe /d /s /c "' + $psLine + ' > "' + $rawLog + '" 2>&1"'
# 再用 WMI 拉起这个 cmd，就能拿到 helper 的真实报错
```

**修复**：调用方与被调用方的参数名**逐字对齐**，并把"返回值为 0"与"真的干活了"当作两件事验证。

### 4.6 日志文件被服务句柄长期占用 → 新服务重定向失败

**现象**：跨端口/跨实例冷启动时，新服务**静默起不来**，cmd 退出码 1：

```text
The process cannot access the file because it is being used by another process.
```

**根因**：服务日志固定叫 `dsh-web.log` 时，**cmd 会持有该文件句柄直到服务退出**。新实例想往同名文件重定向就被拒绝，服务随即启动失败。

**修复**：服务日志**按端口（或按实例）隔离**：

```powershell
$SvcLogFile = Join-Path $LogDir ('dsh-web.p' + $Port + '.log')
```

并且**启动器自身日志与服务日志分开两个文件**——否则 `Add-Content` 也会撞上同一句柄。

### 4.7 一个反面模式：运行中的热重载脚本 ≠ 冷启动脚本

**现象**：同一份代码，**冷启动的实例一切正常，运行中被热重载的实例却静默失效**（`/status` 这类读路径正常，真正干活的写路径不执行）。

**教训**：修复脚本后**必须让宿主重新加载**再验证；拿热重载实例的失败去反推代码 bug，会浪费大量时间。这也是为什么下面的 §5 强调"修复后用冷启动实例复测"。
---

## 五、验证与防复发 SOP

### 5.1 客观判据（别靠肉眼）

| 验证项 | 命令 / 判据 |
|:--|:--|
| 脚本语法（按**目标解释器**校验） | 用 PS 5.1 自己的解析器：`[System.Management.Automation.Language.Parser]::ParseFile($p,[ref]$t,[ref]$e)`，要求 `$e.Count -eq 0` |
| 被 5.1 执行的脚本是否纯 ASCII | `@([IO.File]::ReadAllBytes($p) \| ? { $_ -gt 127 }).Count -eq 0` |
| 无窗口是否成立 | 新进程 `MainWindowHandle -eq 0`（辅助判据）|
| 幂等分支 | 服务已在跑时点快捷方式：**目标端口监听 PID 不变**、node 进程数不增 |
| 冷启动分支 | 用**独立测试端口**（如 11112）验证，别拿生产端口试 |
| 自重启是否真的换进程 | 重启前后 **监听 PID 改变** + helper 日志出现 `listener is back` |
| 参数名是否对齐 | 提取 helper 的参数声明集合，与调用方传入集合求差集，必须为空 |

### 5.2 诊断纪律（本次踩过、代价最大的三条）

1. **日志要读完整的，别读太早。** `listener is back` 通常在重启后 3 秒才写入；在 2 秒时读会误判成"重启失败"，进而去改本来正确的代码。
2. **不要把自己的输出截断当作事实。** 用 `Substring` 截断命令行后，"没看到参数"会得出"参数丢失"的错误结论——实际完整命令行里参数都在。
3. **绝不拿生产宿主做破坏性诊断。** 在"自己正跑在上面"的服务上执行 `taskkill`，等于把自己踢下线。破坏性验证一律放到**独立测试端口/独立实例**上做。

### 5.3 防复发清单

- [ ] 所有会被 PS 5.1 执行的脚本：**纯 ASCII** 或**带 BOM**
- [ ] 不使用 `Start-Process` 拉起（环境变量字典陷阱），改用 `Process.Start(ProcessStartInfo)`
- [ ] **不依赖** `ProcessStartInfo.EnvironmentVariables`
- [ ] 生成 `.cmd`/`.bat` 一律 `WriteAllText` + 显式 CRLF
- [ ] 调用方与被调用方参数名**逐字核对**
- [ ] 服务日志按端口隔离；启动器日志与服务日志分开
- [ ] 重启 helper 通过 **WMI** 创建，确保脱离服务进程树
- [ ] 重启后**等端口真正释放**再拉起新实例
- [ ] 重启拉起新进程时带 `WindowStyle = 'Hidden'`，保持"无窗口出生"
- [ ] web 自重启的前端必须**自我轮询 + 自动重载**
---

## 六、附：本次落地的最小可复用资产清单

| 资产 | 作用 |
|:--|:--|
| `Launch-<服务>.vbs` | 无窗口包装器（wscript → powershell，`Run(...,0,False)`）|
| `Start-<服务>.ps1` | 幂等启动器（端口反查 + 仲裁 + 轮询就绪 + 日志）|
| `launch-<服务>.p<port>.cmd` | 由启动器生成，负责 `start /b` 与重定向 |
| `dsh-app-restart-helper.ps1` | 自重启 helper（WMI 拉起，脱离进程树，保持无窗口）|
| 桌面 `.lnk` | 指向 `wscript.exe` + VBS |
| 服务内 `/plugin/<x>/status` `/restart` `/quit` | 供前端调用的重启端点（含 token 一次性校验）|

> 端点安全要点：token 一次性（防重放）、同源校验（防跨站 drive-by POST）、无 CORS 头（跨源读不到 token）。
