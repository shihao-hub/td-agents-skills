# 只读体检：不改任何设置。默认输出、端点清单、PnP 状态、服务、近3天错误日志、判型提示
[CmdletBinding()] param()
. "$PSScriptRoot\audio-common.ps1"

$roleNames = @{ 0 = 'eConsole(系统)'; 1 = 'eMultimedia(多媒体)'; 2 = 'eCommunications(通信)' }

'================ 1. 默认端点（关键判定点） ================'
foreach ($r in 0, 1, 2) {
    $d = [AudioKit]::GetDefault(0, $r)
    if ($d) {
        $tag = ''
        if (Test-VirtualAudioDevice $d) { $tag = '   <<< 虚拟设备，声音到不了物理喇叭' }
        '{0,-22}: {1}  [{2}]{3}' -f $roleNames[$r], $d.Name, (Get-StateText $d.State), $tag
        '{0,-22}  {1}' -f '', $d.Id
    } else {
        '{0,-22}: (无默认设备)' -f $roleNames[$r]
    }
}
'音量/静音               : ' + [AudioKit]::VolumeInfo()
$cap = [AudioKit]::GetDefault(1, 0)
if ($cap) { '默认录音设备            : ' + $cap.Name }

''
'================ 2. 输出端点清单 ================'
Get-RenderDevices | Sort-Object State, Name | ForEach-Object {
    $type = if (Test-VirtualAudioDevice $_) { '虚拟' } else { '物理' }
    [pscustomobject]@{
        状态 = Get-StateText $_.State
        类型 = $type
        名称 = $_.Name
        枚举器 = $_.Enumerator
        Id   = $_.Id
    }
} | Format-Table -AutoSize | Out-String -Width 320

'================ 3. 输入端点（仅 ACTIVE） ================'
Get-CaptureDevices | Where-Object { (($_.State -band 0xF) -eq 1) } | ForEach-Object {
    [pscustomobject]@{ 状态 = 'ACTIVE'; 类型 = $(if (Test-VirtualAudioDevice $_) { '虚拟' } else { '物理' }); 名称 = $_.Name; Id = $_.Id }
} | Format-Table -AutoSize | Out-String -Width 320

'================ 4. 音频设备 PnP 状态 ================'
Get-PnpDevice -Class MEDIA, AudioEndpoint -ErrorAction SilentlyContinue |
    Select-Object Status, Class, FriendlyName |
    Sort-Object Class, Status |
    Format-Table -AutoSize | Out-String -Width 220
'注：CMPROB_PHANTOM / Unknown 的历史设备属正常残留，不是故障。'

'================ 5. 音频服务 ================'
Get-Service Audiosrv, AudioEndpointBuilder -ErrorAction SilentlyContinue |
    Select-Object Name, Status, StartType | Format-Table -AutoSize | Out-String -Width 160

'================ 6. 近3天音频相关错误 ================'
$since = (Get-Date).AddDays(-3)
$found = $false
foreach ($log in 'Microsoft-Windows-Audio/Operational', 'Microsoft-Windows-Audio/PlaybackManager') {
    $events = Get-WinEvent -FilterHashtable @{ LogName = $log; StartTime = $since; Level = 1, 2, 3 } -ErrorAction SilentlyContinue
    if ($events) {
        $found = $true
        "--- $log ---"
        $events | Select-Object -First 15 TimeCreated, Id, LevelDisplayName, @{n = 'Msg'; e = { ($_.Message -replace '\s+', ' ') } } |
            Format-Table -AutoSize | Out-String -Width 300
    }
}
$crashes = Get-WinEvent -FilterHashtable @{ LogName = 'Application'; StartTime = $since; Id = 1000 } -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -match 'audiodg|Audio' }
if ($crashes) {
    $found = $true
    '--- Application 1000 (audiodg/音频程序崩溃) ---'
    $crashes | Select-Object -First 10 TimeCreated, @{n = 'Msg'; e = { ($_.Message -replace '\s+', ' ') } } |
        Format-Table -AutoSize | Out-String -Width 300
}
if (-not $found) { '(无警告/错误事件——日志干净不等于物理喇叭正常，继续看第 7 节判型)' }

''
'================ 7. 判型提示 ================'
$def = [AudioKit]::GetDefault(0, 0)
if (Test-VirtualAudioDevice $def) {
    '!! 默认输出是虚拟设备：' + $def.Name
    '   高概率是虚拟声卡（UU远程/远程桌面/直播/Broadcast/VB-Cable 等）抢占，物理喇叭被旁路。'
    '   处置：scripts/set-default-device.ps1  （不带参数自动选第一个 ACTIVE 物理设备）'
} else {
    '默认输出是物理设备：' + $def.Name
    '   若仍无声，按顺序检查：设备音量与静音 → 应用独占 → 应用音量合成器把输出路由到了别的设备。'
}
''
'提示：持续嗡嗡/爆音且重启自愈，优先怀疑音效 APO（Nahimic/Senary/Dolby）或虚拟声卡驱动卡死，不是喇叭硬件损坏。'
