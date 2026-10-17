<#
.SYNOPSIS
    organize_subdirs.ps1 - kb-engineering-notes 平铺与子目录物理分层双向切换工具
.DESCRIPTION
    依据虚拟路径契约：<domain>_<scope>_<type>_<id>_<slug>.md <-> <domain>/<scope>/<type>_<id>_<slug>.md（或 <domain>/<type>_<id>_<slug>.md）
    支持平铺下沉分层 (-ToSubdirs) 与分层逆向上浮平铺 (-ToFlat)，并自动同步更新 SKILL-DRAFT.md 链接。
.PARAMETER ToSubdirs
    将平铺文件按领域归入对应子目录：<domain>/<scope>_<type>_<id>_<slug>.md
.PARAMETER ToFlat
    将子目录文件逆向恢复为根目录平铺：<domain>_<scope>_<type>_<id>_<slug>.md
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
        if ($name -match '^(?<dom>[a-z]+)_(?<scp>[a-z0-9]+)_(?<typ>fix|flow)_(?<id>\d{3})_(?<slug>.+)\.md$') {
            $dom = $Matches['dom'].ToLower()
            $scp = $Matches['scp']
            $typ = $Matches['typ']
            $id = $Matches['id']
            $slug = $Matches['slug']
            if ($validDomains -contains $dom) {
                $subName = "$($scp)_$($typ)_$($id)_$($slug).md"
                $targetDir = Join-Path $kbDir $dom
                $targetPath = Join-Path $targetDir $subName
                $plan.Add([PSCustomObject]@{
                    Direction  = "ToSubdirs"
                    SourceFile = $file.FullName
                    TargetFile = $targetPath
                    TargetDir  = $targetDir
                    OldRelLink = "$name"
                    NewRelLink = "$dom/$subName"
                })
            }
        }
    }
} elseif ($ToFlat) {
    # 模式 2: 子目录逆向上浮到根目录
    foreach ($dom in $validDomains) {
        $subDir = Join-Path $kbDir $dom
        if (Test-Path -LiteralPath $subDir) {
            $subFiles = Get-ChildItem -Path $subDir -File -Filter "*.md"
            foreach ($file in $subFiles) {
                $name = $file.Name
                if ($name -match '^(?<scp>[a-z0-9]+)_(?<typ>fix|flow)_(?<id>\d{3})_(?<slug>.+)\.md$') {
                    $flatName = "$($dom)_$name"
                    $targetPath = Join-Path $kbDir $flatName
                    $plan.Add([PSCustomObject]@{
                        Direction  = "ToFlat"
                        SourceFile = $file.FullName
                        TargetFile = $targetPath
                        TargetDir  = $kbDir
                        OldRelLink = "$dom/$name"
                        NewRelLink = "$flatName"
                    })
                }
            }
        }
    }
}

Write-Host "=== organize_subdirs.ps1 计划清单 (共 $($plan.Count) 个动作) ===" -ForegroundColor Cyan
if ($isDryRun) {
    Write-Host "[DryRun 模式] 未进行任何磁盘写入与文件移动。如需执行，请追加 -Execute 参数。" -ForegroundColor Yellow
} else {
    Write-Host "[Execute 模式] 开始执行文件物理移动并同步 SKILL-DRAFT.md 链接..." -ForegroundColor Green
}

$plan | Format-Table -Property Direction, OldRelLink, NewRelLink -AutoSize

if (-not $isDryRun -and $plan.Count -gt 0) {
    # 1. 执行文件物理移动
    foreach ($item in $plan) {
        if (-not (Test-Path -LiteralPath $item.TargetDir)) {
            New-Item -ItemType Directory -Path $item.TargetDir -Force | Out-Null
        }
        Move-Item -LiteralPath $item.SourceFile -Destination $item.TargetFile -Force
    }

    # 2. 同步更新 SKILL-DRAFT.md 超链接
    if (Test-Path -LiteralPath $draftFile) {
        $content = [System.IO.File]::ReadAllText($draftFile, [System.Text.Encoding]::UTF8)
        foreach ($item in $plan) {
            $content = $content.Replace($item.OldRelLink, $item.NewRelLink)
        }
        [System.IO.File]::WriteAllText($draftFile, $content, [System.Text.Encoding]::UTF8)
        Write-Host "已同步更新 SKILL-DRAFT.md 中的相对引用链接。" -ForegroundColor Green
    }

    # 3. 清理可能变空的空目录
    if ($ToFlat) {
        foreach ($dom in $validDomains) {
            $subDir = Join-Path $kbDir $dom
            if ((Test-Path -LiteralPath $subDir) -and (Get-ChildItem -Path $subDir).Count -eq 0) {
                Remove-Item -LiteralPath $subDir -Force
            }
        }
    }

    Write-Host "操作全部完成！" -ForegroundColor Green
}
