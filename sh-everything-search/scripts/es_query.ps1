# es_query.ps1 - Everything query wrapper (part of the sh-everything-search skill).
#
# 1. Starts the Everything index process on demand (-startup, no window) and
#    waits until IPC answers, when no main instance is already running.
# 2. Refreshes the activity timestamp used by the idle-exit scheduled task
#    (%APPDATA%\language_projects\sh-everything-search\last_use.txt).
# 3. Runs es.exe with every argument passed through unchanged
#    (same stdout / stderr / exit code).
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File es_query.ps1 -n 30 ext:log
#   powershell -NoProfile -ExecutionPolicy Bypass -File "D:\...\es_query.ps1" -get-result-count

# Native commands write readiness errors to stderr while Everything loads;
# keep those non-terminating and rely on $LASTEXITCODE instead.
$ErrorActionPreference = 'Continue'

$esExe = 'D:\Program Files\Everything\es.exe'
$everythingExe = 'D:\Program Files\Everything\Everything.exe'
$stateDir = Join-Path $env:APPDATA 'language_projects\sh-everything-search'
$lastUseFile = Join-Path $stateDir 'last_use.txt'
$mainMinBytes = 50MB

$main = Get-Process -Name Everything -ErrorAction SilentlyContinue |
    Sort-Object WorkingSet64 -Descending |
    Select-Object -First 1 |
    Where-Object { $_.WorkingSet64 -gt $mainMinBytes }

if (-not $main) {
    Start-Process $everythingExe -ArgumentList '-startup'
    $ready = $false
    for ($i = 0; $i -lt 80; $i++) {
        & $esExe -timeout 500 -get-result-count *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Milliseconds 250
    }
    if (-not $ready) {
        Write-Error 'Everything did not become ready within ~20s (IPC timeout).'
        exit 70
    }
}

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
[System.IO.File]::WriteAllText($lastUseFile, [DateTime]::UtcNow.ToString('o'))

& $esExe @args
exit $LASTEXITCODE
