# sublime-menu.ps1 — Sublime Text Windows 右键菜单管理
# 用法: powershell.exe -NoProfile -ExecutionPolicy Bypass -File sublime-menu.ps1 [status|add|remove|classic-on|classic-off] [-ExePath <路径>] [-Label <文案>]
# 只写 HKCU，无需管理员。add/remove/status 不改 Win11 菜单样式；classic-on/off 才会切换并重启资源管理器。
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('status', 'add', 'remove', 'classic-on', 'classic-off')]
    [string]$Action = 'status',
    [string]$ExePath = '',
    [string]$Label = '用 Sublime Text 打开'
)

$ErrorActionPreference = 'Stop'
$verb  = 'SublimeText'
$clsid = 'HKCU:\Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}'

function Find-SublimeExe {
    if ($ExePath) {
        if (Test-Path -LiteralPath $ExePath) { return $ExePath }
        throw "指定的 -ExePath 不存在: $ExePath"
    }
    $candidates = @(
        "$env:ProgramFiles\Sublime Text\sublime_text.exe",
        "${env:ProgramFiles(x86)}\Sublime Text\sublime_text.exe",
        "$env:LOCALAPPDATA\Programs\Sublime Text\sublime_text.exe"
    )
    foreach ($c in $candidates) { if (Test-Path -LiteralPath $c) { return $c } }
    throw '未找到 sublime_text.exe（试过 Program Files / Program Files (x86) / LOCALAPPDATA），请用 -ExePath 指定完整路径'
}

# 四类右键目标: 任意文件 / 文件夹 / 文件夹空白处 / 磁盘。空白处必须用 %V
$targets = @(
    @{ Sub = '*';                    Arg = '%1'; Name = '任意文件' },
    @{ Sub = 'Directory';            Arg = '%1'; Name = '文件夹' },
    @{ Sub = 'Directory\Background'; Arg = '%V'; Name = '文件夹空白处' },
    @{ Sub = 'Drive';                Arg = '%1'; Name = '磁盘' }
)

function Test-Entry([string]$sub) {
    Test-Path -LiteralPath "HKCU:\Software\Classes\$sub\shell\$verb"
}

function Add-Entries {
    $exe = Find-SublimeExe
    foreach ($t in $targets) {
        # `*` 键只能走 reg.exe（注册表 provider 把 * 当通配符）；/d 值内嵌引号必须写成 \"，PS 5.1 不自动转义
        $key    = "HKCU\Software\Classes\$($t.Sub)\shell\$verb"
        $cmdVal = '\"' + $exe + '\" \"' + $t.Arg + '\"'
        reg add $key /ve /d $Label /f | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "reg add 失败: $key" }
        reg add $key /v Icon /t REG_SZ /d "$exe,0" /f | Out-Null
        reg add $key /v Position /t REG_SZ /d 'Top' /f | Out-Null
        reg add "$key\command" /ve /d $cmdVal /f | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "reg add 失败: $key\command" }
    }
    Write-Output "已添加右键菜单 [$Label]，exe: $exe"
}

function Remove-Entries {
    foreach ($t in $targets) {
        if (Test-Entry $t.Sub) {
            reg delete "HKCU\Software\Classes\$($t.Sub)\shell\$verb" /f | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "reg delete 失败: $($t.Sub)" }
        }
    }
    Write-Output '已删除全部 Sublime 右键菜单项'
}

function Restart-Explorer {
    Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Start-Process explorer.exe
}

function Show-Status {
    Write-Output '=== Sublime 右键菜单状态 ==='
    try   { Write-Output "exe: $(Find-SublimeExe)" }
    catch { Write-Output "exe: 未找到（用 -ExePath 指定）" }
    foreach ($t in $targets) {
        $state = if (Test-Entry $t.Sub) { '已添加' } else { '未添加' }
        Write-Output ("{0,-16} {1}" -f $t.Name, $state)
    }
    $classic = Test-Path -LiteralPath "$clsid\InprocServer32"
    $style = if ($classic) { '经典（已切换，classic-off 可恢复）' } else { 'Win11 新版（默认，未改动）' }
    Write-Output "Win11 菜单样式: $style"
}

switch ($Action) {
    'status' { Show-Status }
    'add'    { Add-Entries;    Show-Status }
    'remove' { Remove-Entries; Show-Status }
    'classic-on' {
        # 注册表 provider 对此路径无通配符问题，直接建键并把默认值设为空串
        New-Item -Path "$clsid\InprocServer32" -Force | Out-Null
        Set-ItemProperty -Path "$clsid\InprocServer32" -Name '(default)' -Value ''
        Restart-Explorer
        Write-Output '已切换为经典右键菜单（右键直接显示完整菜单），资源管理器已重启'
        Show-Status
    }
    'classic-off' {
        if (Test-Path -LiteralPath $clsid) {
            Remove-Item -Path $clsid -Recurse -Force
        }
        Restart-Explorer
        Write-Output '已恢复 Win11 新版右键菜单，资源管理器已重启'
        Show-Status
    }
}
