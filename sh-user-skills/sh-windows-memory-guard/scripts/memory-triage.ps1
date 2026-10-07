<#
.SYNOPSIS
    Windows 内存压力与虚拟内存 (Pagefile) 只读体检脚本
.DESCRIPTION
    探测物理内存 (RAM)、提交配额 (Commit Charge)、页面文件 (Pagefile)、磁盘空间及 Top 内存进程。
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'SilentlyContinue'

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "         Windows 内存与虚拟内存 (Pagefile) 体检报告         " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. 物理内存与提交配额
$os = Get-CimInstance Win32_OperatingSystem
$totalRamGB    = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
$freeRamGB     = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
$usedRamGB     = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / 1MB, 2)
$ramPercent    = [math]::Round(($usedRamGB / $totalRamGB) * 100, 1)

$commitLimitGB = [math]::Round($os.TotalVirtualMemorySize / 1MB, 2)
$commitFreeGB  = [math]::Round($os.FreeVirtualMemory / 1MB, 2)
$committedGB   = [math]::Round(($os.TotalVirtualMemorySize - $os.FreeVirtualMemory) / 1MB, 2)
$commitPercent = [math]::Round(($committedGB / $commitLimitGB) * 100, 1)

Write-Host "`n[1. 物理内存 (RAM)]" -ForegroundColor Yellow
$ramColor = if ($ramPercent -ge 90) { 'Magenta' } elseif ($ramPercent -ge 80) { 'Yellow' } else { 'Green' }
Write-Host ("  总物理内存 : {0} GB" -f $totalRamGB)
Write-Host ("  已用物理   : {0} GB ({1}%)" -f $usedRamGB, $ramPercent) -ForegroundColor $ramColor
Write-Host ("  可用物理   : {0} GB" -f $freeRamGB)

Write-Host "`n[2. 提交配额 / 虚拟内存 (Commit Charge)]" -ForegroundColor Yellow
$commitColor = if ($commitPercent -ge 90) { 'Red' } elseif ($commitPercent -ge 75) { 'Yellow' } else { 'Green' }
Write-Host ("  总提交配额 (物理+虚拟) : {0} GB" -f $commitLimitGB)
Write-Host ("  当前已提交 (Committed) : {0} GB ({1}%)" -f $committedGB, $commitPercent) -ForegroundColor $commitColor
Write-Host ("  剩余可用提交配额       : {0} GB" -f $commitFreeGB)

# 2. 页面文件 (Pagefile) 详情
Write-Host "`n[3. 页面文件 (Pagefile)]" -ForegroundColor Yellow
$pageFiles = Get-CimInstance Win32_PageFileUsage
if ($pageFiles) {
    foreach ($pf in $pageFiles) {
        Write-Host ("  文件路径 : {0}" -f $pf.Name)
        Write-Host ("  分配大小 : {0} MB | 峰值使用 : {1} MB" -f $pf.AllocatedBaseSize, $pf.PeakUsage)
    }
} else {
    Write-Host "  未检测到独立页面文件实例（由系统完全动态托管）。" -ForegroundColor Gray
}

# 3. 关键磁盘剩余空间（虚拟内存依赖所在盘）
Write-Host "`n[4. 磁盘剩余空间]" -ForegroundColor Yellow
$disks = Get-CimInstance Win32_LogicalDisk | Where-Object { $_.DriveType -eq 3 }
foreach ($d in $disks) {
    $sizeGB = [math]::Round($d.Size / 1GB, 1)
    $freeGB = [math]::Round($d.FreeSpace / 1GB, 1)
    $diskColor = if ($freeGB -lt 20) { 'Red' } elseif ($freeGB -lt 40) { 'Yellow' } else { 'Green' }
    Write-Host ("  盘符 {0}  总量: {1} GB | 剩余: {2} GB" -f $d.DeviceID, $sizeGB, $freeGB) -ForegroundColor $diskColor
}

# 4. 内存占用 Top 8 进程
Write-Host "`n[5. 物理内存占用 Top 8 进程]" -ForegroundColor Yellow
$topProcs = Get-Process | Sort-Object -Property WorkingSet64 -Descending | Select-Object -First 8
foreach ($p in $topProcs) {
    $wsMB = [math]::Round($p.WorkingSet64 / 1MB, 1)
    Write-Host ("  PID: {0,-6} | 内存: {1,7} MB | 进程: {2}" -f $p.Id, $wsMB, $p.ProcessName)
}

# 5. 综合健康评估
Write-Host "`n[6. 综合诊断结论]" -ForegroundColor Yellow
if ($commitPercent -ge 90) {
    Write-Host "  [危险] 提交配额已超过 90%！极度接近系统上限，有 OOM 闪退/崩溃风险！" -ForegroundColor Red
    Write-Host "  建议：立即通过 sysdm.cpl 手动扩大虚拟内存页面文件（建议 +16GB~32GB）。" -ForegroundColor Red
} elseif ($ramPercent -ge 88) {
    Write-Host "  [预警] 物理内存已饱和（>88%），但提交配额充足。" -ForegroundColor Yellow
    Write-Host "  现状：系统已借助虚拟内存进行冷热页置换。可能会有窗口切换或硬盘读写微卡，但【绝不会死机】。" -ForegroundColor Yellow
    Write-Host "  建议：确保 C 盘保持 30GB 以上空闲；若追求极致防闪退，可手动锁定 32G~48G 虚拟内存。" -ForegroundColor Green
} else {
    Write-Host "  [正常] 内存负荷在健康范围内，运行平稳。" -ForegroundColor Green
}
Write-Host "============================================================`n" -ForegroundColor Cyan
