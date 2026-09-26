# install-profile.ps1 — 一键写入 atuin「当前目录最近命令」PowerShell profile + atuin 配置
# 用法: powershell -ExecutionPolicy Bypass -File install-profile.ps1 [-AutoShow]
# 行为: 已有 $PROFILE 先备份为 .bak-时间戳；写入带 UTF-8 BOM 的新 profile
#       config.toml 幂等确保: enter_accept=false / filter_mode="directory"
#                            / [search].filters 目录优先（TUI 里 Ctrl+r 目录 ↔ 全局一键切换）
# 注意: 本脚本文件本身必须保持 UTF-8 with BOM 保存，否则 PS 5.1 解析时中文会按 GBK 误读，
#       here-string 里的中文横幅会被写成乱码。
param([switch]$AutoShow)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command atuin -ErrorAction SilentlyContinue)) {
    Write-Warning "未找到 atuin 命令。请先运行: winget install AtuinSh.Atuin ，然后重开终端再执行本脚本。"
}

if (-not $PROFILE) { throw '无法定位 $PROFILE（非控制台宿主?）' }
$dir = Split-Path -Parent $PROFILE
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

if (Test-Path -LiteralPath $PROFILE) {
    $bak = "$PROFILE.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item -LiteralPath $PROFILE -Destination $bak -Force
    Write-Host "已备份旧 profile -> $bak"
}

$content = @'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 先初始化 atuin（这一步才会设置 ATUIN_SESSION，必须在 search 之前）
Invoke-Expression (& { (atuin init powershell) -join "`n" })

# 上/下键恢复经典行为：召回上/下一条命令到输入行，可直接编辑（必须写在 init 之后才能覆盖 atuin 的绑定）
# atuin 全屏搜索保留在 Ctrl+r
Set-PSReadLineKeyHandler -Chord UpArrow -Function PreviousHistory
Set-PSReadLineKeyHandler -Chord DownArrow -Function NextHistory

# 显示当前目录最近执行过的命令；敲 hh 刷新（默认5条），hh 20 显示20条（h 是系统内置别名，别用）
# --filter-mode global 是保险：hh 自己用 --cwd 精确过滤，不受 config.toml 里 filter_mode 影响
function Show-CwdHistory {
    param([int]$Count = 5)
    $lines = atuin search --filter-mode global --cwd $PWD.Path --limit $Count --format "{exit}`t{command}" 2>$null
    if ($lines) {
        Write-Host "`n[当前目录上次执行的命令]" -ForegroundColor Cyan
        $validCommands = @()
        foreach ($line in $lines) {
            $parts = $line -split "`t", 2
            if ($parts.Count -eq 2 -and $parts[0] -match '^-?\d+$') {
                $cmd = $parts[1].Trim()
                if ($cmd -and ($cmd -notmatch '^[@{]') -and ($cmd.Length -lt 120)) {
                    $validCommands += $cmd
                }
            }
        }
        $validCommands | Select-Object -Last $Count | ForEach-Object {
            Write-Host "  > $_" -ForegroundColor DarkGray
        }
        Write-Host ""
    }
}
Set-Alias hh Show-CwdHistory
'@

if ($AutoShow) {
    $content += "`r`n# 开新窗口时自动显示一次`r`nShow-CwdHistory`r`n"
}

# UTF-8 带 BOM —— PS 5.1 读取中文必需
[System.IO.File]::WriteAllText($PROFILE, $content, (New-Object System.Text.UTF8Encoding($true)))

# ---------- atuin config.toml ----------
# 顶层键插到第一个 [section] 之前，避免追加到文件尾时落进别的段
function Add-TopLevelLine([string]$Text, [string]$Line) {
    if ([string]::IsNullOrWhiteSpace($Text)) { return "$Line`r`n" }
    $m = [regex]::Match($Text, '(?m)^\[')
    if ($m.Success) { return $Text.Insert($m.Index, "$Line`r`n") }
    return $Text.TrimEnd() + "`r`n$Line`r`n"
}

$cfgDir = Join-Path $env:USERPROFILE '.config\atuin'
$cfg    = Join-Path $cfgDir 'config.toml'
$filtersLine = 'filters = ["directory", "global", "host", "session", "workspace", "session-preload"]'

if (-not (Test-Path -LiteralPath $cfg)) {
    New-Item -ItemType Directory -Path $cfgDir -Force | Out-Null
    $newCfg = "enter_accept = false`r`nfilter_mode = `"directory`"`r`n`r`n[search]`r`n$filtersLine`r`n"
    [System.IO.File]::WriteAllText($cfg, $newCfg, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "已创建 $cfg（enter_accept=false, filter_mode=directory, filters 目录优先）"
}
else {
    $t = [System.IO.File]::ReadAllText($cfg, [System.Text.Encoding]::UTF8)
    $orig = $t

    # enter_accept = false（顶层键；true 改写，缺行则插入）
    if ($t -match '(?m)^[ \t]*enter_accept[ \t]*=') {
        $t = [regex]::Replace($t, '(?m)^[ \t]*enter_accept[ \t]*=[ \t]*true[ \t]*(?=\r|\n|$)', 'enter_accept = false')
    }
    else {
        $t = Add-TopLevelLine $t 'enter_accept = false'
    }

    # filter_mode = "directory"（顶层键；已有则覆盖，注释默认行则原地启用，缺行则插入）
    if ($t -match '(?m)^[ \t]*filter_mode[ \t]*=') {
        $t = [regex]::Replace($t, '(?m)^[ \t]*filter_mode[ \t]*=[^\r\n]*', 'filter_mode = "directory"')
    }
    elseif ($t.Contains('# filter_mode = "global"')) {
        $t = $t.Replace('# filter_mode = "global"', 'filter_mode = "directory"')
    }
    else {
        $t = Add-TopLevelLine $t 'filter_mode = "directory"'
    }

    # [search].filters：directory 排第一（Ctrl+r 循环：directory → global → ...）
    if ($t -match '(?m)^[ \t]*filters[ \t]*=') {
        $t = [regex]::Replace($t, '(?m)^[ \t]*filters[ \t]*=[^\r\n]*', $filtersLine)
    }
    elseif ($t.Contains('# filters = ["global", "host", "session", "workspace", "directory", "session-preload"]')) {
        $t = $t.Replace('# filters = ["global", "host", "session", "workspace", "directory", "session-preload"]', $filtersLine)
    }
    elseif ($t -match '(?m)^\[search\][ \t]*\r?$') {
        $t = [regex]::Replace($t, '(?m)^\[search\][ \t]*(?=\r|\n|$)', "`$0`r`n$filtersLine", 1)
    }
    else {
        $t = $t.TrimEnd() + "`r`n`r`n[search]`r`n$filtersLine`r`n"
    }

    if ($t -ne $orig) {
        [System.IO.File]::WriteAllText($cfg, $t, (New-Object System.Text.UTF8Encoding($false)))
        Write-Host "已更新 $cfg（enter_accept=false, filter_mode=directory, filters 目录优先）"
    }
    else {
        Write-Host "$cfg 已是最新，无需修改"
    }
}

$bytes = [System.IO.File]::ReadAllBytes($PROFILE)
$head = ($bytes[0..2] | ForEach-Object { $_.ToString('X2') }) -join ' '
Write-Host "已写入 $PROFILE（前3字节: $head，应为 EF BB BF）"
Write-Host "重开终端窗口生效；敲 hh 显示当前目录最近命令（默认5条），hh 20 显示 20 条。"
Write-Host "Ctrl+r 打开搜索默认 [ DIRECTORY ]，在搜索界面里再按 Ctrl+r 切到 [ GLOBAL ]。"
