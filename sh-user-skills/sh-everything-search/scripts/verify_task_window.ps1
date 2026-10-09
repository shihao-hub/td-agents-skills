param(
    [int]$Seconds = 300,
    [string]$OutFile = "$env:TEMP\verify_task_window.log",
    [switch]$PositiveControl
)

# verify_task_window.ps1 - WinEvent hook watcher for top-level window activity.
#
# Records every top-level window create/destroy/show/hide event
# (time / class / pid / visibility) for $Seconds and reports:
#   - console-related events (ConsoleWindowClass / CASCADIA / conhost / windowsterminal)
#   - other visible window shows/creates
# Events are flushed to $OutFile every 250ms so even an aborted run keeps evidence.
# Use -PositiveControl to spawn a visible cmd window mid-run as an instrument check.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File verify_task_window.ps1 -Seconds 300
#
# Part of the sh-everything-search skill (see README.md, lifecycle section).
$ErrorActionPreference = 'Continue'

Add-Type -TypeDefinition @'
using System;
using System.Collections.Concurrent;
using System.Text;
using System.Threading;
using System.Runtime.InteropServices;

public static class WinEventWatch
{
    public delegate void WinEventProc(IntPtr hWinEventHook, uint eventType, IntPtr hwnd, int idObject, int idChild, uint dwEventThread, uint dwmsEventTime);

    [DllImport("user32.dll")] static extern IntPtr SetWinEventHook(uint eventMin, uint eventMax, IntPtr hmodWinEventProc, WinEventProc lpfnWinEventProc, uint idProcess, uint idThread, uint dwFlags);
    [DllImport("user32.dll")] static extern bool UnhookWinEvent(IntPtr hWinEventHook);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")] static extern IntPtr GetParent(IntPtr hWnd);
    [DllImport("user32.dll")] static extern bool GetMessage(out MSG lpMsg, IntPtr hWnd, uint wMsgFilterMin, uint wMsgFilterMax);
    [DllImport("user32.dll")] static extern bool TranslateMessage(ref MSG lpMsg);
    [DllImport("user32.dll")] static extern IntPtr DispatchMessage(ref MSG lpMsg);
    [DllImport("user32.dll")] static extern bool PostThreadMessage(uint idThread, uint Msg, IntPtr wParam, IntPtr lParam);
    [DllImport("kernel32.dll")] static extern uint GetCurrentThreadId();

    [StructLayout(LayoutKind.Sequential)]
    public struct MSG { public IntPtr hwnd; public uint message; public IntPtr wParam; public IntPtr lParam; public uint time; public int ptX; public int ptY; }

    public class Evt {
        public string When;
        public string Kind;
        public long Hwnd;
        public string Cls;
        public string Title;
        public uint Pid;
        public bool Visible;
        public override string ToString() {
            return When + "\t" + Kind + "\t0x" + Hwnd.ToString("X") + "\t" + Cls + "\tpid=" + Pid + "\tvisible=" + Visible + "\t" + Title;
        }
    }

    public static ConcurrentQueue<Evt> Events = new ConcurrentQueue<Evt>();
    static WinEventProc _proc;
    static IntPtr _hook = IntPtr.Zero;
    static uint _threadId;
    static volatile bool _stop;

    static void Callback(IntPtr hWinEventHook, uint eventType, IntPtr hwnd, int idObject, int idChild, uint dwEventThread, uint dwmsEventTime)
    {
        try {
            if (idObject != 0 || idChild != 0) return;
            if (GetParent(hwnd) != IntPtr.Zero) return;
            var cls = new StringBuilder(256); GetClassName(hwnd, cls, 256);
            var title = new StringBuilder(256); GetWindowText(hwnd, title, 256);
            uint pid = 0; GetWindowThreadProcessId(hwnd, out pid);
            string kind = eventType == 0x8000 ? "create" : (eventType == 0x8001 ? "destroy" : (eventType == 0x8002 ? "show" : "hide"));
            var e = new Evt();
            e.When = DateTime.Now.ToString("HH:mm:ss.fff");
            e.Kind = kind;
            e.Hwnd = hwnd.ToInt64();
            e.Cls = cls.ToString();
            e.Title = title.ToString();
            e.Pid = pid;
            e.Visible = IsWindowVisible(hwnd);
            Events.Enqueue(e);
        } catch { }
    }

    public static void Start()
    {
        _stop = false;
        var t = new Thread(delegate() {
            _threadId = GetCurrentThreadId();
            _proc = new WinEventProc(Callback);
            _hook = SetWinEventHook(0x8000, 0x8003, IntPtr.Zero, _proc, 0, 0, 0);
            MSG msg;
            while (!_stop && GetMessage(out msg, IntPtr.Zero, 0, 0)) {
                TranslateMessage(ref msg);
                DispatchMessage(ref msg);
            }
            if (_hook != IntPtr.Zero) { UnhookWinEvent(_hook); _hook = IntPtr.Zero; }
        });
        t.IsBackground = true;
        t.Start();
        Thread.Sleep(300);
    }

    public static void Stop()
    {
        _stop = true;
        if (_threadId != 0) PostThreadMessage(_threadId, 0x0012, IntPtr.Zero, IntPtr.Zero);
    }
}
'@

$startTime = Get-Date
$logDir = Split-Path -Parent $OutFile
if ($logDir -and -not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }
[System.IO.File]::WriteAllText($OutFile, ("WATCH START {0} duration {1}s`r`n" -f $startTime.ToString('HH:mm:ss'), $Seconds))
Write-Output ("WATCH START {0} duration {1}s log={2}" -f $startTime.ToString('HH:mm:ss'), $Seconds, $OutFile)

[WinEventWatch]::Start()

$all = New-Object System.Collections.ArrayList
$deadline = $startTime.AddSeconds($Seconds)
$spawned = $false
while ((Get-Date) -lt $deadline) {
    if ($PositiveControl -and -not $spawned -and ((Get-Date) - $startTime).TotalSeconds -ge 45) {
        $spawned = $true
        [System.IO.File]::AppendAllText($OutFile, ("POSITIVE CONTROL spawn {0}`r`n" -f (Get-Date).ToString('HH:mm:ss.fff')))
        Start-Process cmd -ArgumentList '/c ping -n 4 127.0.0.1 >nul' | Out-Null
    }
    $sb = New-Object System.Text.StringBuilder
    $e = $null
    while ([WinEventWatch]::Events.TryDequeue([ref]$e)) { [void]$all.Add($e); [void]$sb.AppendLine($e.ToString()) }
    if ($sb.Length -gt 0) { [System.IO.File]::AppendAllText($OutFile, $sb.ToString()) }
    Start-Sleep -Milliseconds 250
}

[WinEventWatch]::Stop()
Start-Sleep -Milliseconds 300
$sb = New-Object System.Text.StringBuilder
$e = $null
while ([WinEventWatch]::Events.TryDequeue([ref]$e)) { [void]$all.Add($e); [void]$sb.AppendLine($e.ToString()) }
if ($sb.Length -gt 0) { [System.IO.File]::AppendAllText($OutFile, $sb.ToString()) }

$consoleRe = 'ConsoleWindowClass|CASCADIA|console|conhost|windowsterminal'
$console = @($all | Where-Object { $_.Cls -match $consoleRe })
$visibleOther = @($all | Where-Object { $_.Visible -and ($_.Kind -eq 'create' -or $_.Kind -eq 'show') -and $_.Cls -notmatch $consoleRe })
$summary = "WATCH END {0} events={1} console_events={2} other_visible={3}" -f (Get-Date).ToString('HH:mm:ss'), $all.Count, $console.Count, $visibleOther.Count
[System.IO.File]::AppendAllText($OutFile, ($summary + "`r`n"))
Write-Output $summary
