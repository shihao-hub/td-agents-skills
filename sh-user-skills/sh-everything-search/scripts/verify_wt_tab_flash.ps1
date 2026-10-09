param(
    [int]$Seconds = 300,
    [string]$OutFile = "$env:TEMP\verify_wt_tab_flash.log"
)

# verify_wt_tab_flash.ps1 - detect console-handoff tab flashes in Windows Terminal.
#
# Polls the Windows Terminal main window title at 40ms and logs every change.
# A console-handoff tab (e.g. a scheduled task launching powershell.exe directly)
# activates a new tab whose title is the console command line, flipping the
# window title and then back. Zero flips during task trigger moments = no flash.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File verify_wt_tab_flash.ps1 -Seconds 360
#   powershell -NoProfile -ExecutionPolicy Bypass -File verify_wt_tab_flash.ps1 -Seconds 60 -OutFile "$env:TEMP\wt.log"
#
# Part of the sh-everything-search skill (see README.md, lifecycle section).
$ErrorActionPreference = 'Continue'

Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class WinTxt {
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowTextLength(IntPtr hWnd);
    public static string Get(IntPtr h) {
        var sb = new StringBuilder(GetWindowTextLength(h) + 2);
        GetWindowText(h, sb, sb.Capacity);
        return sb.ToString();
    }
}
'@

$dir = Split-Path -Parent $OutFile
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }

$wt = Get-Process WindowsTerminal -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $wt) { [System.IO.File]::WriteAllText($OutFile, "NO WT PROCESS`r`n"); exit 1 }

$hwnd = $wt.MainWindowHandle
$start = Get-Date
$initial = [WinTxt]::Get($hwnd)
$changes = 0
[System.IO.File]::WriteAllText($OutFile, ("POLL START {0} hwnd=0x{1:X} pid={2} title='{3}'`r`n" -f $start.ToString('HH:mm:ss.fff'), $hwnd.ToInt64(), $wt.Id, $initial))

$last = $initial
$deadline = $start.AddSeconds($Seconds)
while ((Get-Date) -lt $deadline) {
    $t = [WinTxt]::Get($hwnd)
    if ($t -ne $last) {
        $changes++
        [System.IO.File]::AppendAllText($OutFile, ("{0}  title -> '{1}'`r`n" -f (Get-Date).ToString('HH:mm:ss.fff'), $t))
        $last = $t
    }
    Start-Sleep -Milliseconds 40
}
[System.IO.File]::AppendAllText($OutFile, ("POLL END {0} final='{1}' changes={2}`r`n" -f (Get-Date).ToString('HH:mm:ss.fff'), $last, $changes))
Write-Output ("POLL END {0} final='{1}' changes={2} log={3}" -f (Get-Date).ToString('HH:mm:ss'), $last, $changes, $OutFile)
