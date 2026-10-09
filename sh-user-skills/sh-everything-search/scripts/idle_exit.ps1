# idle_exit.ps1 - Exit Everything after a period without wrapper activity.
# Run by scheduled task "sh-everything-idle-exit" every 5 minutes (no window).
# Register/re-register via scripts/register_task.ps1 (conhost.exe --headless wrapper;
# do NOT register powershell.exe directly - Windows console handoff would flash a
# PowerShell tab inside the running Windows Terminal on every run).
#
# Exits only when ALL of these hold:
#   - a main Everything instance is running
#   - no visible Everything window (the user is not looking at the GUI)
#   - no es.exe process in flight
#   - last_use.txt is older than $idleMinutes
#   - the process was not started after the last recorded activity
#     (an instance started later was most likely launched manually -> leave it)

# Native commands may emit stderr (e.g. IPC race); keep them non-terminating.
$ErrorActionPreference = 'Continue'

$esExe = 'D:\Program Files\Everything\es.exe'
$stateDir = Join-Path $env:APPDATA 'language_projects\sh-everything-search'
$lastUseFile = Join-Path $stateDir 'last_use.txt'
$logFile = Join-Path $stateDir 'idle_exit.log'
$idleMinutes = 15
$mainMinBytes = 50MB

$main = Get-Process -Name Everything -ErrorAction SilentlyContinue |
    Sort-Object WorkingSet64 -Descending |
    Select-Object -First 1 |
    Where-Object { $_.WorkingSet64 -gt $mainMinBytes }
if (-not $main) { exit 0 }

if ($main.MainWindowHandle -ne 0) { exit 0 }
if (Get-Process -Name es -ErrorAction SilentlyContinue) { exit 0 }
if (-not (Test-Path $lastUseFile)) { exit 0 }

$lastUse = [DateTime]::Parse(([System.IO.File]::ReadAllText($lastUseFile)).Trim()).ToUniversalTime()
$idleActual = ([DateTime]::UtcNow - $lastUse).TotalMinutes
if ($idleActual -lt $idleMinutes) { exit 0 }

try {
    if ($main.StartTime.ToUniversalTime() -gt $lastUse) { exit 0 }
} catch { exit 0 }

& $esExe -exit *> $null
if ($LASTEXITCODE -eq 0) {
    New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
    Add-Content -Path $logFile -Value ('{0} idle {1:N0} min -> exited' -f (Get-Date -Format o), $idleActual)
}
exit 0
