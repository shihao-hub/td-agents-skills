# install-profile.ps1 — 一键写入 atuin「当前目录最近命令」PowerShell profile
# 用法: powershell -ExecutionPolicy Bypass -File install-profile.ps1 [-AutoShow]
# 行为: 已有 $PROFILE 先备份为 .bak-时间戳；写入带 UTF-8 BOM 的新 profile
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
function Show-CwdHistory {
    param([int]$Count = 5)
    $lines = atuin search --cwd . --limit $Count --format "{exit}`t{command}" 2>$null
    if ($lines) {
        Write-Host "`n[当前目录上次执行的命令]" -ForegroundColor Cyan
        $validCommands = @()
        foreach ($line in $lines) {
            $parts = $line -split "`t", 2
            if ($parts.Count -eq 2 -and $parts[0] -match '^\d+$') {
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

# atuin 配置：enter_accept=false 让搜索界面选中后放回输入行编辑，而不是立即执行
$cfgDir = Join-Path $env:USERPROFILE '.config\atuin'
$cfg = Join-Path $cfgDir 'config.toml'
if (-not (Test-Path -LiteralPath $cfg)) {
    New-Item -ItemType Directory -Path $cfgDir -Force | Out-Null
    [System.IO.File]::WriteAllText($cfg, "enter_accept = false`r`n", (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "已创建 $cfg（enter_accept = false）"
}
else {
    $t = [System.IO.File]::ReadAllText($cfg)
    if ($t -match '(?m)^\s*enter_accept\s*=\s*true\s*$') {
        $t = [regex]::Replace($t, '(?m)^\s*enter_accept\s*=\s*true\s*$', 'enter_accept = false')
        [System.IO.File]::WriteAllText($cfg, $t, (New-Object System.Text.UTF8Encoding($false)))
        Write-Host "已将 $cfg 的 enter_accept 改为 false"
    }
    elseif ($t -notmatch '(?m)^\s*enter_accept\s*=') {
        [System.IO.File]::WriteAllText($cfg, $t.TrimEnd() + "`r`nenter_accept = false`r`n", (New-Object System.Text.UTF8Encoding($false)))
        Write-Host "已在 $cfg 追加 enter_accept = false"
    }
}

$bytes = [System.IO.File]::ReadAllBytes($PROFILE)
$head = ($bytes[0..2] | ForEach-Object { $_.ToString('X2') }) -join ' '
Write-Host "已写入 $PROFILE（前3字节: $head，应为 EF BB BF）"
Write-Host "重开终端窗口生效；之后敲 hh 显示当前目录最近命令（默认5条），hh 20 显示 20 条。"
