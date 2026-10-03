# 切换默认输出端点。默认只挑 ACTIVE + 物理设备；不指定 -Match/-Id 且候选不唯一时只列出候选。
# 例：
#   set-default-device.ps1 -List
#   set-default-device.ps1 -Match 'Senary'
#   set-default-device.ps1 -Id '{0.0.0.00000000}.{4e4c5022-...}'
#   set-default-device.ps1 -Match 'UU远程' -IncludeVirtual
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$Match,
    [string]$Id,
    [ValidateSet('Console', 'Multimedia', 'Communications', 'All')]
    [string]$Role = 'All',
    [switch]$List,
    [switch]$IncludeInactive,
    [switch]$IncludeVirtual
)
. "$PSScriptRoot\audio-common.ps1"

$all = @(Get-RenderDevices)

function Show-Devices($devices) {
    foreach ($d in $devices) {
        $type = if (Test-VirtualAudioDevice $d) { '虚拟' } else { '物理' }
        '{0,-10} {1,-4} {2}' -f (Get-StateText $d.State), $type, $d.Name
        '           Id: ' + $d.Id
    }
}

if ($List) {
    '全部输出端点：'
    Show-Devices ($all | Sort-Object State, Name)
    return
}

$candidates = $all
if ($Id) { $candidates = @($candidates | Where-Object { $_.Id -eq $Id }) }
elseif ($Match) { $candidates = @($candidates | Where-Object { $_.Name -match $Match -or $_.Desc -match $Match }) }
if (-not $IncludeInactive) { $candidates = @($candidates | Where-Object { (($_.State -band 0xF) -eq 1) }) }
if (-not $IncludeVirtual) { $candidates = @($candidates | Where-Object { -not (Test-VirtualAudioDevice $_) }) }

if ($candidates.Count -eq 0) {
    '未找到符合条件的输出设备。'
    if ($Match -and -not $IncludeVirtual) { '提示：若目标是虚拟设备，加 -IncludeVirtual。' }
    if (-not $IncludeInactive) { '提示：若设备未插入/未启用，加 -IncludeInactive 查看。' }
    '可用设备：'
    Show-Devices ($all | Sort-Object State, Name)
    exit 1
}

if (-not $Id -and $candidates.Count -gt 1) {
    '有多个候选设备，请用 -Match 缩小范围或用 -Id 精确指定：'
    Show-Devices $candidates
    exit 2
}

$target = $candidates[0]
$type = if (Test-VirtualAudioDevice $target) { '虚拟' } else { '物理' }
'目标设备: [{0}] {1}' -f $type, $target.Name
'       Id: ' + $target.Id

$roleList = if ($Role -eq 'All') { @(0, 1, 2) } else { @(@{ Console = 0; Multimedia = 1; Communications = 2 }[$Role]) }
foreach ($r in $roleList) {
    if ($PSCmdlet.ShouldProcess("role=$r", "SetDefaultEndpoint -> $($target.Name)")) {
        $hr = [AudioKit]::SetDefault($target.Id, $r)
        'SetDefaultEndpoint(role={0}) hr=0x{1:X8}' -f $r, $hr
    }
}

Start-Sleep -Milliseconds 800
'切换后默认(eConsole): ' + [AudioKit]::GetDefault(0, 0).Name
'音量/静音           : ' + [AudioKit]::VolumeInfo()
'下一步验证：scripts/play-test-tone.ps1 -Volume 40'
