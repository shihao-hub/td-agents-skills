<#
.SYNOPSIS
    Windows 内存压力与虚拟内存 (Pagefile) 只读体检脚本
.DESCRIPTION
    探测物理内存 (RAM)、提交配额 (Commit Charge)、页面文件 (Pagefile)、磁盘空间、
    提交内存归因 (按 PrivateMemorySize64 排序，捞出"已换出冷数据")、内存硬件与扩容可行性。
    关键认知：物理 WorkingSet 排名 ≠ 提交内存排名，提交压力的真凶常在物理榜上完全隐形。
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

# 4. 提交内存归因：捞出"看不见的换出大户"
# 依据：物理 WorkingSet 榜会整体漏掉"已全量换出到 pagefile 的冷数据"
#      （典型：遗留模型服务 ComfyUI / 推理后端，私有提交数 GB，物理 WS 仅十几 MB）
Write-Host "`n[5. 提交内存归因 Top 8 进程 (按私有提交排序)]" -ForegroundColor Yellow
$topCommit = Get-Process | Sort-Object -Property PrivateMemorySize64 -Descending | Select-Object -First 8
foreach ($p in $topCommit) {
    $privMB = [math]::Round($p.PrivateMemorySize64 / 1MB, 1)
    $wsMB   = [math]::Round($p.WorkingSet64 / 1MB, 1)
    # 私有 >= 500MB 且 物理/私有 < 10% => 近乎全量换出，物理榜上不可见
    $swapped = ($privMB -ge 500) -and (($wsMB / [math]::Max($privMB, 1)) -lt 0.10)
    $tag = if ($swapped) { '   <== 疑似换出冷数据(仅占提交不占物理)' } else { '' }
    $color = if ($swapped) { 'Magenta' } else { 'Gray' }
    Write-Host ("  PID: {0,-6} | 私有提交: {1,8} MB | 物理: {2,7} MB | 进程: {3}{4}" -f $p.Id, $privMB, $wsMB, $p.ProcessName, $tag) -ForegroundColor $color
}

# 5. 物理内存占用 Top 8 进程
Write-Host "`n[6. 物理内存占用 Top 8 进程]" -ForegroundColor Yellow
$topProcs = Get-Process | Sort-Object -Property WorkingSet64 -Descending | Select-Object -First 8
foreach ($p in $topProcs) {
    $wsMB = [math]::Round($p.WorkingSet64 / 1MB, 1)
    Write-Host ("  PID: {0,-6} | 内存: {1,7} MB | 进程: {2}" -f $p.Id, $wsMB, $p.ProcessName)
}

# 6. 内存硬件与扩容可行性
Write-Host "`n[7. 内存硬件与扩容可行性]" -ForegroundColor Yellow
$dimms = Get-CimInstance Win32_PhysicalMemory
$array = Get-CimInstance Win32_PhysicalMemoryArray
if ($dimms) {
    foreach ($m in $dimms) {
        $slotName = ("{0} {1}" -f $m.BankLabel, $m.DeviceLocator).Trim()
        Write-Host ("  {0,-22} | {1,4} GB | {2,-14} | {3} MHz | {4}" -f `
            $slotName, [math]::Round($m.Capacity / 1GB, 0), $m.Manufacturer, $m.Speed, $m.PartNumber)
    }
    $slotsUsed  = ($dimms | Measure-Object).Count
    $slotsTotal = if ($array -and $array.MemoryDevices) { $array.MemoryDevices } else { $slotsUsed }
    Write-Host ("  插槽占用 : {0} / {1}" -f $slotsUsed, $slotsTotal)
    if ($array -and $array.MaxCapacityEx) {
        Write-Host ("  平台上限 : {0} GB (SMBIOS MaxCapacityEx)" -f [math]::Round($array.MaxCapacityEx / 1MB, 0))
    }
    if ($slotsUsed -ge $slotsTotal) {
        Write-Host "  提示：插槽已满 —— 扩容只能【成对替换】整组换掉，不可加装单条。" -ForegroundColor Yellow
        Write-Host "        严禁只换一条凑容量：会破坏双通道，核显机型尤其吃亏。" -ForegroundColor Yellow
    }
} else {
    Write-Host "  未读取到内存条信息。" -ForegroundColor Gray
}

# 7. 综合健康评估（口径：先归因，再决定是否扩容）
Write-Host "`n[8. 综合诊断结论]" -ForegroundColor Yellow
$pfSetting = Get-CimInstance Win32_PageFileSetting | Select-Object -First 1
$pfMaxMB   = if ($pfSetting -and $pfSetting.MaximumSize -gt 0) { $pfSetting.MaximumSize } else { 0 }
$pfAllocMB = if ($pageFiles) { ($pageFiles | Select-Object -First 1).AllocatedBaseSize } else { 0 }

if ($commitPercent -ge 90) {
    Write-Host "  [危险] 提交配额已超 90%！有 OOM 闪退/崩溃风险。" -ForegroundColor Red
    Write-Host "  第一步：看上方 [5. 提交内存归因]，定位是谁占的提交（多为已换出的冷数据/遗留服务）。" -ForegroundColor Red
    Write-Host "  第二步：能在 [5] 里定位到可关闭进程的，关掉即回收，无需动虚拟内存。" -ForegroundColor Red
    Write-Host "  第三步：确实无法归因、且页面文件已顶到上限，才按 Step 3.1 扩容虚拟内存。" -ForegroundColor Red
} elseif ($ramPercent -ge 88) {
    Write-Host "  [预警] 物理内存已饱和（>88%），但提交配额充足。" -ForegroundColor Yellow
    Write-Host "  现状：系统已借助虚拟内存进行冷热页置换。可能会有窗口切换或硬盘读写微卡，但【绝不会死机】。" -ForegroundColor Yellow
    Write-Host "  建议：确保 C 盘保持 30GB 以上空闲；若追求极致防闪退，可手动锁定 32G~48G 虚拟内存。" -ForegroundColor Green
} else {
    Write-Host "  [正常] 内存负荷在健康范围内，运行平稳。" -ForegroundColor Green
}

# 修正旧口径：commit limit 会随 pagefile 在"初始值~最大值"区间内自动增长，
# 因此"剩余提交 < 8GB"不等于必须立即扩容虚拟内存。
if ($pfMaxMB -gt 0 -and $pfAllocMB -gt 0 -and $commitFreeGB -lt 8) {
    Write-Host ("  页面文件自动增长余量：当前分配 {0} MB / 上限 {1} MB —— 提交上限会随之自动抬升。" -f $pfAllocMB, $pfMaxMB) -ForegroundColor Gray
    Write-Host "  故【剩余提交 <8GB】应优先做 [5] 归因排查，而非直接扩容虚拟内存。" -ForegroundColor Gray
}
if ($pfMaxMB -eq 0) {
    Write-Host "  页面文件由系统完全托管，提交上限自动伸缩。" -ForegroundColor Gray
}
Write-Host "============================================================`n" -ForegroundColor Cyan
