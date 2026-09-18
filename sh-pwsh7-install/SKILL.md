---
name: sh-pwsh7-install
description: 在 Windows 上零影响安装 PowerShell 7.x（跨平台 pwsh）：ZIP 绿色版安装到用户目录，不写注册表、不改系统 PATH、不加右键菜单、绝不覆盖系统自带的 5.1，删除文件夹即卸载。当用户提到安装/升级 PowerShell 7、pwsh、PS7，想要绿色版/便携版/免安装 PowerShell，担心装了会影响现有系统、怕覆盖 5.1，问 5.1 和 7.x 的区别/共存关系，或说"帮我装 pwsh 但别动我系统"、"装个新版 powershell 但要能随时卸干净"时使用——即使只说"装个新版 powershell"也应触发。
---

# sh-pwsh7-install — PowerShell 7.x 零影响安装

把"Windows 上装 PowerShell 7.x 且不留系统痕迹"变成一次可靠的执行：检查现状 → 查最新版本 → 下载 ZIP → 解压到用户目录 → 双向验证 → 汇报。产物是 `%LOCALAPPDATA%\Programs\PowerShell\7\pwsh.exe`（或用户指定目录），删除文件夹即完全卸载。

## 背景知识（用户问区别时直接讲）

| | Windows PowerShell 5.1 | PowerShell 7.x |
|---|---|---|
| 运行时 | .NET Framework 4.x（仅 Windows） | .NET 8+（跨平台） |
| 可执行文件 | `powershell.exe` | `pwsh.exe` |
| 支持系统 | 仅 Windows | Windows / Linux / macOS / ARM |
| 关系 | 系统自带，不能卸 | 并存安装，互不影响 |

## 铁律（2026-09-14 全流程实测踩坑）

1. **零影响 = 只有 ZIP 绿色版**。MSI/winget/Store 安装会写注册表、改 PATH、可能加右键菜单；用户要"不影响系统"时一律用 GitHub release 的 `PowerShell-<ver>-win-<arch>.zip`。用户明确要机器级安装（全部用户可用、自动更新）才考虑 MSI，且要先说明影响面。
2. **PS 5.1 下联网必先设两行**：`[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12`（否则 GitHub API/下载可能直接失败）和 `$ProgressPreference='SilentlyContinue'`（5.1 的 Invoke-WebRequest 进度条会把下载拖慢 10 倍以上）。忘了这两行是最常见的"怎么这么慢/怎么报错"。
3. **URL 拼接规则**：API 返回的 tag 带 `v` 前缀（`v7.6.6`），zip 文件名不带（`PowerShell-7.6.6-win-x64.zip`）。下载慢或中断时用系统自带 `curl.exe -L -C - -o <file> <url>` 断点续传，不要重头下 100MB。
4. **zip 里 pwsh.exe 就在根目录**，直接 `Expand-Archive` 到目标目录即可，不要先解到临时目录再拷贝一遍。
5. **从 5.1 调 pwsh 验证时命令必须极简**。嵌套引号会让 5.1 先展开 `$PSVersionTable`、中文在 GBK 代码页下乱码、字符串拼接跨 shell 传递后解析成 `"7.6.6" + "Core"` 报 Int32 转换错误。验证就跑 `& pwsh -NoProfile -Command '$PSVersionTable'`（外层单引号防展开），打印整张表，别拼字符串。
6. **装完必须双向验证**：7 能跑 + 5.1 完好（`$PSVersionTable.PSVersion.ToString()`）。只验一边不算装完。
7. **目标目录被占用时 `Expand-Archive -Force` 会失败**：先 `Get-Process pwsh -ErrorAction SilentlyContinue` 查是否有 pwsh 在跑，有则提醒用户关闭或换目录。
8. **PATH 只加用户级、且先问**。默认不加（保持零影响）；用户想随处敲 `pwsh` 时，把安装目录追加到用户 PATH（`[Environment]::SetEnvironmentVariable('Path', ..., 'User')`），绝不碰系统 PATH。改前告知可逆方式。
9. **装完清理安装包**，别留 100MB 的 zip 在临时目录。

## 工作流

### Step 1: 确认参数（信息缺口才问，用户说了的直接用）

| 参数 | 默认 | 说明 |
|---|---|---|
| 安装目录 | `$env:LOCALAPPDATA\Programs\PowerShell\7` | 用户级约定位置，无需管理员；用户指定别的目录就直接用 |
| 版本 | GitHub latest release | API 实时获取，不硬编码 |
| 架构 | 自动探测 | `$env:PROCESSOR_ARCHITECTURE`：`AMD64`→`win-x64`，`ARM64`→`win-arm64` |

先跑现状检查（已有安装 / 架构 / 当前 5.1 版本）：

```powershell
Get-Command pwsh -ErrorAction SilentlyContinue
$env:PROCESSOR_ARCHITECTURE
$PSVersionTable.PSVersion.ToString()
```

已存在 pwsh 时：报告现有版本和路径，问用户要覆盖（同目录 `-Force` 解压）还是换目录，不要自作主张。

### Step 2: 获取最新版本号

```powershell
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$tag = (Invoke-RestMethod 'https://api.github.com/repos/PowerShell/PowerShell/releases/latest').tag_name
# 例如 v7.6.6
```

### Step 3: 下载 ZIP（约 100MB，给足超时）

```powershell
$ProgressPreference='SilentlyContinue'
$ver = $tag.TrimStart('v')
$arch = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'win-arm64' } else { 'win-x64' }
$zip = "$env:TEMP\pwsh7.zip"
$url = "https://github.com/PowerShell/PowerShell/releases/download/$tag/PowerShell-$ver-$arch.zip"
Invoke-WebRequest -Uri $url -OutFile $zip
(Get-Item $zip).Length / 1MB   # 应约 100MB，太小 = 下载失败
```

### Step 4: 解压

```powershell
$dest = "$env:LOCALAPPDATA\Programs\PowerShell\7"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Expand-Archive -Path $zip -DestinationPath $dest -Force
Test-Path "$dest\pwsh.exe"   # 必须 True
```

### Step 5: 双向验证 + 清理 + 汇报

```powershell
& "$dest\pwsh.exe" -NoProfile -Command '$PSVersionTable'   # PSVersion 7.x、PSEdition Core、OS 字段
$PSVersionTable.PSVersion.ToString()                        # 5.1 版本号原样，未被影响
Remove-Item $zip -Force
```

汇报用表格：7 的版本/Edition、安装路径、5.1 验证结果、零影响清单（注册表/系统PATH/右键菜单均未动）、启动方式（完整路径或 Windows Terminal 添加配置文件）、卸载方式（删目录）。最后主动提一句：需要的话可以加用户级 PATH（可逆），等用户确认。

## 不适用

- Linux / macOS 上的 PowerShell 安装（本 skill 只覆盖 Windows）
- 用户明确要求机器级 MSI 安装并接受系统变更（可作为对照说明，但流程不展开）
