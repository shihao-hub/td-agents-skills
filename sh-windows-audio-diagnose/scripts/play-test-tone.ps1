# 在"当前默认输出"上播放 5 段已知测试音，用于硬件可用性的可闻判据。
#   play-test-tone.ps1                  # 原音量直接播
#   play-test-tone.ps1 -Volume 40       # 先设为 40% 再播（推荐）
#   play-test-tone.ps1 -NoPlay          # 只显示默认设备与播放清单，不发声
[CmdletBinding()]
param(
    [ValidateRange(-1, 100)][int]$Volume = -1,
    [switch]$NoPlay
)
. "$PSScriptRoot\audio-common.ps1"

$d = [AudioKit]::GetDefault(0, 0)
if (-not $d) { '没有默认输出设备，先运行 audio-triage.ps1 检查。'; exit 1 }
'当前默认输出: ' + $d.Name
'           Id: ' + $d.Id
'当前音量    : ' + [AudioKit]::VolumeInfo()

if ($Volume -ge 0) {
    '设置音量    : ' + [AudioKit]::SetVolume($Volume / 100.0, $false)
}

if ($NoPlay) {
    '(-NoPlay：仅演练，不发声) 播放清单：1kHz/2s、200Hz/1.5s、4kHz/1.5s、60→500Hz/4s、2k→12kHz/4s'
    return
}

Start-Sleep -Milliseconds 300
'--- 开始播放测试音，请听目标设备 ---'
'[1/5] 1kHz 正弦 2 秒';            [AudioKit]::PlayTone(1000, 2.0, 0.20, 44100)
'[2/5] 200Hz 正弦 1.5 秒';         [AudioKit]::PlayTone(200, 1.5, 0.20, 44100)
'[3/5] 4kHz 正弦 1.5 秒';          [AudioKit]::PlayTone(4000, 1.5, 0.15, 44100)
'[4/5] 低频扫频 60 -> 500Hz 4 秒'; [AudioKit]::PlaySweep(60, 500, 4.0, 0.20, 44100)
'[5/5] 高频扫频 2k -> 12kHz 4 秒'; [AudioKit]::PlaySweep(2000, 12000, 4.0, 0.12, 44100)
'--- 播放完毕 ---'
'听感判读：干净有声=硬件正常；有声但破音/沙沙=查音效 APO；完全无声=回 audio-triage.ps1 看默认端点是否又被抢占或静音。'
