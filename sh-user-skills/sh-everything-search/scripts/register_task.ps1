# register_task.ps1 - register / re-register the sh-everything-idle-exit scheduled task (no window).
#
# Usage (idempotent, safe to re-run; normal user rights are enough):
#   powershell -NoProfile -ExecutionPolicy Bypass -File register_task.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File register_task.ps1 -Unregister
#
# Design notes (verified 2026-10-10):
# - The task action MUST be wrapped in conhost.exe --headless. If powershell.exe is
#   registered directly (even with -WindowStyle Hidden), Windows 11 console handoff
#   delegates the console to the running Windows Terminal, which flashes an extra
#   PowerShell tab inside the user's existing terminal window every 5 minutes.
#   The headless wrapper does not trigger the handoff (verified with a WT window
#   title poller plus a WinEvent hook control experiment).
# - Trigger/Settings/Principal/Description replicate the original working task
#   (5-minute infinite repetition, Hidden, IgnoreNew, 5-minute time limit,
#   Interactive / Limited).
# - idle_exit.ps1 is located via $PSScriptRoot: re-run this script after moving the
#   skill directory or on a new machine.
param(
    [switch]$Unregister
)
$ErrorActionPreference = 'Stop'
$TaskName = 'sh-everything-idle-exit'
$Description = 'Exit Everything after 15 min idle (sh-everything-search skill)'

if ($Unregister) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        "UNREGISTERED: $TaskName"
    } else {
        "NOT FOUND: $TaskName"
    }
    exit 0
}

$conhost = Join-Path $env:SystemRoot 'System32\conhost.exe'
$psExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$scriptPath = Join-Path $PSScriptRoot 'idle_exit.ps1'
foreach ($f in @($conhost, $psExe, $scriptPath)) {
    if (-not (Test-Path $f)) { throw "required file missing: $f" }
}

$action = New-ScheduledTaskAction -Execute $conhost -Argument ('--headless "{0}" -NoProfile -ExecutionPolicy Bypass -File "{1}"' -f $psExe, $scriptPath)
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -Hidden

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description $Description | Out-Null

$t = Get-ScheduledTask -TaskName $TaskName
"REGISTERED: {0} state={1}" -f $t.TaskName, $t.State
$t.Actions | ForEach-Object { '  exec={0}' -f $_.Execute; '  args={0}' -f $_.Arguments }
$t.Triggers | ForEach-Object { '  start={0} interval={1}' -f $_.StartBoundary, $_.Repetition.Interval }
$t.Principal | ForEach-Object { '  user={0} logon={1} level={2}' -f $_.UserId, $_.LogonType, $_.RunLevel }
$t.Settings | ForEach-Object { '  hidden={0} ignoreNew={1} timeLimit={2} startWhenAvailable={3}' -f $_.Hidden, $_.MultipleInstances, $_.ExecutionTimeLimit, $_.StartWhenAvailable }
