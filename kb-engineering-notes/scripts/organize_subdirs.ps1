<#
.SYNOPSIS
    organize_subdirs.ps1 - kb-engineering-notes 平铺与子目录物理分层双向切换工具
.DESCRIPTION
    依据虚拟路径契约：<domain>_<type>_<id>_<slug>.md <-> <domain>/<type>_<id>_<slug>.md
    支持平铺下沉分层 (-ToSubdirs) 与分层逆向上浮平铺 (-ToFlat)，并自动同步更新 SKILL-DRAFT.md 链接。
.PARAMETER ToSubdirs
    将平铺文件按领域归入对应子目录：<domain>/<type>_<id>_<slug>.md
.PARAMETER ToFlat
    将子目录文件逆向恢复为根目录平铺：<domain>_<type>_<id>_<slug>.md
.PARAMETER Execute
    显式指定此开关才实际执行文件移动与链接写入；默认仅试跑预览 (DryRun)
.PARAMETER DryRun
    显式试跑预览（默认也是试跑模式）
.EXAMPLE
    .\organize_subdirs.ps1 -ToSubdirs           # 试跑预览下沉分层
    .\organize_subdirs.ps1 -ToSubdirs -Execute  # 物理执行下沉分层
    .\organize_subdirs.ps1 -ToFlat -Execute     # 物理执行恢复平铺
#>
param(
    [switch]$ToSubdirs,
    [switch]$ToFlat,
    [switch]$Execute,
    [switch]$DryRun
)

$kbDir = Split-Path $PSScriptRoot -Parent
$draftFile = Join-Path $kbDir "SKILL-DRAFT.md"
$validDomains = @("win", "git", "ide", "agent", "browser", "dev", "media")

if (-not $ToSubdirs -and -not $ToFlat) {
    Write-Host "错误: 必须指定 -ToSubdirs 或 -ToFlat 操作模式。" -ForegroundColor Red
    Write-Host "示例: .\organize_subdirs.ps1 -ToSubdirs (试跑预览)" -ForegroundColor Yellow
    exit 1
}

$isDryRun = (-not $Execute) -or $DryRun

$plan = [System.Collections.Generic.List[PSCustomObject]]::new()

if ($ToSubdirs) {
    # 模式 1: 平铺下沉到子目录
    # 扫描根目录下的 .md 文件
    $rootFiles = Get-ChildItem -Path $kbDir -File -Filter "*.md" | Where-Object {
        $_.Name -ne "SKILL-DRAFT.md" -and $_.Name -ne "SKILL.md" -and $_.Name -ne "README.md"
    }

    foreach ($file in $rootFiles) {
        $name = $file.Name
        if ($name -match '^(?<dom>[a-z]+)_(?<typ>fix|flow)_(?<id>\d{3})_(?<slug>.+)\.md$') {
            $dom = $Matches['dom'].ToLower()
            $typ = $Matches['typ']
            $id = $Matches['id']
            $slug = $Matches['slug']
            if ($validDomains -contains $dom) {
                $subName = "$($typ)_$($id)_$($slug).md"
                $targetDir = Join-Path $kbDir $dom
                $targetPath = Join-Path $targetDir $subName
                $plan.Add([PSCustomObject]@{
                    Direction  = "ToSubdirs"
                    Domain     = $dom
                    SourcePath = $file.FullName
                    TargetPath = $targetPath
                    OldRel     = $name
                    NewRel     = "$dom/$subName"
                })
            }
        }
    }
} elseif ($ToFlat) {
    # 模式 2: 从子目录逆向平铺到根目录
    foreach ($dom in $validDomains) {
        $subDir = Join-Path $kbDir $dom
        if (Test-Path $subDir) {
            $subFiles = Get-ChildItem -Path $subDir -File -Filter "*.md"
            foreach ($file in $subFiles) {
                $name = $file.Name
                if ($name -match '^(?<typ>fix|flow)_(?<id>\d{3})_(?<slug>.+)\.md$') {
                    $typ = $Matches['typ']
                    $id = $Matches['id']
                    $slug = $Matches['slug']
                    $flatName = "$($dom)_$($typ)_$($id)_$($slug).md"
                    $targetPath = Join-Path $kbDir $flatName
                    $plan.Add([PSCustomObject]@{
                        Direction  = "ToFlat"
                        Domain     = $dom
                        SourcePath = $file.FullName
                        TargetPath = $targetPath
                        OldRel     = "$dom/$name"
                        NewRel     = $flatName
                    })
                } elseif ($name -match '^(?<dom>[a-z]+)_(?<typ>fix|flow)_(?<id>\d{3})_(?<slug>.+)\.md$') {
                    # 子目录下已经是完整前缀命名的兼容情况
                    $targetPath = Join-Path $kbDir $name
                    $plan.Add([PSCustomObject]@{
                        Direction  = "ToFlat"
                        Domain     = $dom
                        SourcePath = $file.FullName
                        TargetPath = $targetPath
                        OldRel     = "$dom/$name"
                        NewRel     = $name
                    })
                }
            }
        }
    }
}

if ($plan.Count -eq 0) {
    Write-Host "未检测到符合条件的迁移条目（可能已是目标结构，或尚未重命名为规范分面命名）。" -ForegroundColor Yellow
    exit 0
}

if ($isDryRun) {
    Write-Host "=== organize_subdirs.ps1 试跑模式 (DryRun) - 计划操作 $($plan.Count) 个条目 ===" -ForegroundColor Cyan
    Write-Host "方向: $(if ($ToSubdirs) {'平铺 -> 子目录物理分层'} else {'子目录物理分层 -> 根目录平铺'})" -ForegroundColor Cyan
    $plan | Format-Table -Property Domain, OldRel, NewRel -AutoSize
    Write-Host "提示：如需物理执行迁移，请运行: .\organize_subdirs.ps1 $(if ($ToSubdirs) {'-ToSubdirs'} else {'-ToFlat'}) -Execute" -ForegroundColor Yellow
} else {
    Write-Host "=== organize_subdirs.ps1 开始执行物理迁移 ($($plan.Count) 个条目) ===" -ForegroundColor Green
    $draftContent = if (Test-Path $draftFile) { [System.IO.File]::ReadAllText($draftFile, [System.Text.Encoding]::UTF8) } else { $null }

    foreach ($item in $plan) {
        $parent = Split-Path $item.TargetPath -Parent
        if (-not (Test-Path $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        Move-Item -LiteralPath $item.SourcePath -Destination $item.TargetPath -Force
        Write-Host "已移动: $($item.OldRel) -> $($item.NewRel)" -ForegroundColor Green

        if ($draftContent) {
            # 同步更新 SKILL-DRAFT.md 中的路径引用
            $draftContent = $draftContent.Replace($item.OldRel, $item.NewRel)
            $oldUrl = $item.OldRel -replace '\\', '/'
            $newUrl = $item.NewRel -replace '\\', '/'
            $draftContent = $draftContent.Replace($oldUrl, $newUrl)
        }
    }

    if ($draftContent) {
        [System.IO.File]::WriteAllText($draftFile, $draftContent, [System.Text.Encoding]::UTF8)
        Write-Host "SKILL-DRAFT.md 链接已全量同步更新。" -ForegroundColor Green
    }

    # 如果是 ToFlat 且子目录已空，清理空目录
    if ($ToFlat) {
        foreach ($dom in $validDomains) {
            $subDir = Join-Path $kbDir $dom
            if (Test-Path $subDir) {
                $rem = Get-ChildItem -Path $subDir
                if ($rem.Count -eq 0) {
                    Remove-Item -Path $subDir -Force
                    Write-Host "已清理空目录: $dom" -ForegroundColor Gray
                }
            }
        }
    }

    Write-Host "物理迁移执行完毕！" -ForegroundColor Green
}