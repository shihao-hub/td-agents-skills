<#
.SYNOPSIS
    kb_timeline.ps1 - kb-engineering-notes 时序演进感知辅助脚本
.DESCRIPTION
    利用 ID 逻辑时钟（001~999 绝对单调递增）或物理修改时间，秒级输出条目时序列表。
.PARAMETER Top
    仅展示最新的前 N 条（默认展示全部）
.PARAMETER Domain
    按领域过滤 (win, git, ide, agent, browser, dev, media)
.PARAMETER Scope
    按受控实体/软件范围过滤 (zed, cursor, sublime, terminal, ahk, ps, docx, uv, wails, etc.)
.PARAMETER Type
    按形态过滤 (fix, flow)
.PARAMETER SortBy
    排序字段: Id (默认), LastWriteTime, Created
.PARAMETER Descending
    降序排列（ID 最大 / 最新创建排在最前）
.EXAMPLE
    .\kb_timeline.ps1 -Top 5 -Descending
    .\kb_timeline.ps1 -Domain git
    .\kb_timeline.ps1 -Scope zed
#>
param(
    [int]$Top = 0,
    [string]$Domain,
    [string]$Scope,
    [ValidateSet('fix', 'flow')][string]$Type,
    [ValidateSet('Id', 'LastWriteTime', 'Created')][string]$SortBy = 'Id',
    [switch]$Descending
)

$kbDir = Split-Path $PSScriptRoot -Parent

# 收集所有笔记文件（兼容五段式 ID置顶 <id>_<dom>_<scp>_<typ>_<slug>.md、历史前置 <dom>_... 及 0N-*.md）
$allFiles = Get-ChildItem -Path $kbDir -Recurse -Filter "*.md" | Where-Object {
    $_.Name -ne "SKILL-DRAFT.md" -and $_.Name -ne "SKILL.md" -and $_.Name -ne "README.md" -and
    ($_.Name -match '^\d{2,3}_' -or $_.Name -match '^\d{2}-' -or $_.Name -match '^[a-z]+_([a-z0-9]+_)?(fix|flow)_\d{3}_')
}

$records = [System.Collections.Generic.List[PSCustomObject]]::new()

foreach ($file in $allFiles) {
    $name = $file.Name
    $id = 0
    $dom = "-"
    $scp = "-"
    $typ = "-"
    $slug = ""
    $created = $file.CreationTime.ToString("yyyy-MM-dd")

    if ($name -match '^(?<id>\d{3})_(?<dom>[a-z]+)_(?<scp>[a-z0-9]+)_(?<typ>fix|flow)_(?<slug>.+)\.md$') {
        # 新标准：ID 置顶五段式
        $id = [int]$Matches['id']
        $dom = $Matches['dom']
        $scp = $Matches['scp']
        $typ = $Matches['typ']
        $slug = $Matches['slug']
    } elseif ($name -match '^(?<dom>[a-z]+)_(?<scp>[a-z0-9]+)_(?<typ>fix|flow)_(?<id>\d{3})_(?<slug>.+)\.md$') {
        # 兼容：ID 在中间五段式
        $id = [int]$Matches['id']
        $dom = $Matches['dom']
        $scp = $Matches['scp']
        $typ = $Matches['typ']
        $slug = $Matches['slug']
    } elseif ($name -match '^(?<dom>[a-z]+)_(?<typ>fix|flow)_(?<id>\d{3})_(?<slug>.+)\.md$') {
        # 兼容：旧四段式
        $id = [int]$Matches['id']
        $dom = $Matches['dom']
        $typ = $Matches['typ']
        $slug = $Matches['slug']
    } elseif ($name -match '^(?<num>\d{2})-(?<title>.+)\.md$') {
        # 兼容：历史 0N-*.md
        $id = [int]$Matches['num']
        $slug = $Matches['title']
        $head = Get-Content -LiteralPath $file.FullName -TotalCount 20 -Encoding UTF8 -ErrorAction SilentlyContinue
        foreach ($line in $head) {
            if ($line -match '^created:\s*(\d{4}-\d{2}-\d{2})') {
                $created = $Matches[1]
                break
            }
        }
    } else {
        continue
    }

    if ($Domain -and $dom -ne "-" -and $dom -ne $Domain.ToLower()) {
        continue
    }

    if ($Scope -and $scp -ne "-" -and $scp -ne $Scope.ToLower()) {
        continue
    }

    if ($Type -and $typ -ne "-" -and $typ -ne $Type.ToLower()) {
        continue
    }

    $records.Add([PSCustomObject]@{
        Id            = ("{0:D3}" -f $id)
        IdNum         = $id
        Domain        = $dom
        Scope         = $scp
        Type          = $typ
        Title         = $slug
        Created       = $created
        LastModified  = $file.LastWriteTime.ToString("yyyy-MM-dd HH:mm")
        FileName      = $name
        RelativePath  = (Resolve-Path -Path $file.FullName -Relative)
    })
}

if ($SortBy -eq 'Id') {
    $sorted = $records | Sort-Object -Property IdNum -Descending:$Descending
} elseif ($SortBy -eq 'LastWriteTime') {
    $sorted = $records | Sort-Object -Property LastModified -Descending:$Descending
} elseif ($SortBy -eq 'Created') {
    $sorted = $records | Sort-Object -Property Created, IdNum -Descending:$Descending
}

if ($Top -gt 0) {
    $sorted = $sorted | Select-Object -First $Top
}

Write-Host "=== kb-engineering-notes 条目时序感知视图 (共 $($sorted.Count) 篇) ===" -ForegroundColor Cyan
$sorted | Format-Table -Property Id, Domain, Scope, Type, Title, LastModified -AutoSize
