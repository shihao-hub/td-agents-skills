---
name: kb-zed-terminal-agy-history-restore
description: Zed 终端无会话滚动恢复机制导致 agy 历史会话 ID 丢失排障：剖析 PTY 进程生命周期与无缓冲区落盘机理、PowerShell 外部命令对象属性传参解析陷阱、history.jsonl 孤儿输入聚合空 ID 幽灵会话根因，以官方 conversation_summaries.db 数据库为权威主真相源封装 agl 交互式会话选择器（默认工作区聚焦、-a 全局漫游、单轮会话 100% 捕获、0 幽灵组与回车秒恢复）。当 Zed 重启后终端空白找不到上轮 agy 会话、列表出现空 ID 或 agy --conversation 报错时查阅。
version: 1.1.0
created: 2026-10-16
updated: 2026-10-17
---

# Zed 终端无会话恢复 agy 历史 ID 丢失排障与 PowerShell 交互选号恢复指南

> **适用场景**：在 Zed 编辑器中使用内置终端运行 Antigravity CLI（`agy`），退出会话或重启 Zed 后，由于 Zed 缺乏类似 Windows Terminal 的会话滚动历史恢复（Session Restoration），屏幕输出被彻底清空，无法通过向上滚屏查看上一轮的 `Resume with -c: agy --conversation=<id>`；且通过脚本自动传参启动时，踩中 PowerShell 外部程序对象属性解析陷阱导致报 `conversation "@{Id=...}.Id" not found`；或者因依赖 `history.jsonl` 聚合踩中孤儿记录陷阱，导致列表第一项出现 `Title: /model`、`Prompt: /resume`、`ID: ` 为空的幽灵假会话，回车恢复直接误开空白新会话，且单轮真实会话彻底漏单；急需以官方 SQLite 数据库为权威主源、带 AI 精炼业务标题（Title）并支持快捷选号秒恢复的终极工作流。

---

## 一、现象与报错直击

### 1. 现场一：Zed 重启后终端空白，历史会话 ID 随滚屏丢失
在 Windows Terminal (WT) 中，重启后界面会自动插入灰色分割标记并恢复先前的屏幕文字：
```text
Resume with -c (or command below):
agy --conversation=84a813d6-15cf-408d-af49-8875b49aba06
PS C:\Users\29580>
[已还原 2026/10/14 20:43:37]
```
但在 Zed 终端中固定（Pin）标签页后，下次重启 Zed 仅仅拉起一个空白的冷启动 Shell，屏幕历史完全没有保存。开发者想要重新接续上次特定的会话，无法凭记忆获知那串 36 位的 UUID。

### 2. 现场二：PowerShell 对象属性传参展开陷阱
在封装自动化恢复脚本时，尝试执行：
```powershell
$target = $top[2] # 包含 Id 属性的 PSCustomObject
agy --conversation=$target.Id
```
系统未抛出语法错误，但 `agy` 报错拒绝并中断：
```text
正在启动会话: 5939b044-bb06-4441-bdf8-0f1fffb0305c...
warning: conversation "@{Id=5939b044-bb06-4441-bdf8-0f1fffb0305c; Time=2026-10-15 23:36; Workspace=D:\Users\language_projects; Prompt=帮我提交; RawTime=1792078583708}.Id" not found
```

### 3. 现场三：仅看 Prompt 无法区分会话业务背景
会话推进到后期时，用户的末轮输入通常高度简略（如 `帮我提交`、`继续`、`/resume`、`可以`），若仅打印末轮 Prompt，列表完全失去业务可读性，无法判断对应的是哪个功能模块。

### 4. 现场四：history.jsonl 孤儿输入聚合出空 ID 幽灵组与单轮会话漏单
在初版 `agl` 脚本中，终端列表中常常出现一条极其诡异的第 [1] 项：
```text
[1] 2026-10-16 23:18 (language_projects [当前项目])
    Title  : /model
    Prompt : /resume
    ID     : 

请选择要恢复的会话 [1-5] (直接回车进 [1]，输入 q 退出): 1
正在启动会话: ...
```
* **表象一（空 ID 幽灵）**：`Title` 变成了不相干的斜杠命令 `/model`，`Prompt` 是刚才输入的 `/resume`，而 `ID` 后面空空如也；
* **表象二（冷启动空会话）**：直接回车进 [1]，屏幕打印 `正在启动会话: ...`（冒号后为空），随后 `agy` 忽略空参数直接冷启动了一个全新空白会话；
* **表象三（单轮会话彻底漏单）**：刚刚退出的真实会话（如 `4c4a2e24`）明明真实存在，但在列表中完全没有显示出来。

---

## 二、底层根因剖析

### 1. Zed 与 Windows Terminal 的终端持久化架构差异
* **Zed 的 PTY 生命周期**：Zed 的内置终端基于 Rust 的 `alacritty_terminal` 渲染组件。终端 PTY 会话作为 Zed 窗口进程的直系子进程存在。窗口或应用退出时，操作系统向下分发进程终止信号。目前 Zed **未实现终端滚动缓冲区（Scrollback Buffer）落盘序列化机制**，Zed 自身的 `db.sqlite` 仅记录 Pane 元数据（如路径、Pin 状态），重启时仅执行全新的 `spawn("pwsh.exe")` 冷启动。
* **Windows Terminal 的 Buffer 快照机制**：WT v1.20+ 拥有完备的 `Session Restoration`，在退出时将字符网格完整序列化落盘，重启后原样反序列化重绘并打上 `[已还原 ...]` 标记，再挂载新会话。

### 2. agy 本地存储架构与「主次数据源倒置」致命缺陷
`agy` 本地维护了两类存储，但两者的职责具有天壤之别：
1. **输入按键流水账（`~/.gemini/antigravity-cli/history.jsonl`）**：
   * **本质**：纯粹面向终端 CLI 行编辑器（Readline/Prompt-Toolkit）的**输入历史（Input History）**，供用户按键盘上下箭头恢复敲过的文字。
   * **缺陷**：它**不是会话索引库**！所有斜杠命令（`/resume`、`/model`、`/permissions` 等）以及新会话冷启动敲下的第一句 Prompt（此时前台尚未收到后端分配的会话 ID），写入该文件时 **`conversationId` 均为 null 或缺省**！
   * **孤儿聚合 Bug**：初版脚本以 `history.jsonl` 为主源执行 `$allList | Group-Object conversationId`，PowerShell 会将全机所有缺少 `conversationId` 的记录强行揉入同一个 `$null` / `""` 组。该组最早的一条输入是 `/model`（成为 Title），最近一条是刚敲的 `/resume`（成为 Prompt 且时间最新），于是霸占第 [1] 名；传空 ID 启动 `agy --conversation=""` 即误开新会话；而像 `4c4a2e24` 这样只单轮交互就退出的真实会话，因首行未记 ID 被错归入孤儿组，在列表中彻底成为盲区。
2. **官方元数据主库（`~/.gemini/antigravity-cli/conversation_summaries.db`，唯一真相源）**：
   * **本质**：标准的 SQLite 数据库，核心表 `conversation_summaries` 才是官方真正且唯一的会话资产主库。
   * **优势**：只要会话创建，无论执行了 1 步还是 100 步，在库中均有唯一非空的 `conversation_id`、AI 精炼 `title`、输入摘要 `preview`、准确的所属 `workspace_uris` 与 `last_modified_time`。
   * **治本之道**：必须**颠倒主次依赖**——直接以 `conversation_summaries.db` 为主查询源，`history.jsonl` 仅作为提取最近一次用户输入打字记录的辅助只读映射。

### 3. PowerShell 外部命令参数解析陷阱
PowerShell 解析命令行时具有双重语法上下文（表达式模式 vs 参数模式）：
* 在给外部 Win32 原生可执行文件（如 `agy.exe`）传参时，参数处于**参数解析模式**。
* 当书写 `--conversation=$target.Id` 时，解析器将 `$target` 识别为一个独立变量并调用其 `.ToString()`（产生 `@{Id=...}` 散列文本），随后把 `.Id` 作为普通字符字面量拼在后面。
* **正确做法**：必须先赋值给强类型纯标量变量（`$targetId = $target.Id; agy --conversation=$targetId`），或使用子表达式引号界定（`"--conversation=$($target.Id)"`）。

### 4. 终端外壳与多 Shell 内核的 Profile 映射
终端外壳（Zed、官方 WT、独立版 WT）只负责前端渲染，真正执行指令的是内核 Shell。Windows 上存在两套独立的 PowerShell Profile：
* **PowerShell 7 (`pwsh.exe`)**：`Documents\PowerShell\Microsoft.PowerShell_profile.ps1`（Zed 默认调用的绿色版）。
* **Windows PowerShell 5.1 (`powershell.exe`)**：`Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`。
若两套 Profile 未同步，在不同宿主或不同版本 Shell 间切换会导致命令丢失。此外，Profile 文件若包含中文注释，**必须以带有 UTF-8 BOM 签名的格式保存**，否则 Windows PowerShell 5.1 在默认代码页（GBK / CP936）下解析多字节字符可能出现引号截断错位。

---

## 三、标准抢救与环境配置 SOP

### 1. 零记忆负担的原生快速恢复
若仅需继续当前目录下最近一次的会话，无需查找 ID，在当前项目路径下直接执行：
```powershell
agy -c
# 等价于 agy --continue
```
`agy` 会自动根据当前 Working Directory 智能拉起最新的一次历史会话。

### 2. 封装增强型会话选择器 `agy-list`（别名 `agl`）
将以下函数注入 PowerShell Profile，实现以官方 SQLite 数据库为唯一权威真相源、项目作用域聚焦、AI 标题渲染、跨项目漫游与交互式选号秒恢复：

```powershell
# ==================== agy 会话管理快捷命令 ====================
# 查看 agy 会话记录（官方 SQLite 数据库权威驱动版：彻底杜绝幽灵组，单轮会话 100% 捕获，支持选号/回车秒恢复；加 -a 或 -All 展示全部项目）
function agy-list {
    [CmdletBinding()]
    param(
        [Parameter(Position = 0)]
        [int]$Count = 5,

        [Parameter()]
        [Alias('a')]
        [switch]$All
    )

    $dbFile = "$HOME\.gemini\antigravity-cli\conversation_summaries.db"
    $histFile = "$HOME\.gemini\antigravity-cli\history.jsonl"
    $currentDir = (Get-Location).Path.TrimEnd('\', '/')
    $curUri = 'file:///' + ($currentDir -replace '\\', '/').TrimEnd('/')

    $sqliteCmd = Get-Command sqlite3 -ErrorAction SilentlyContinue

    # ---------------- 优先主路径：以官方 SQLite 数据库为主真相源 ----------------
    if ((Test-Path $dbFile) -and $sqliteCmd) {
        $limit = if ($All) { [Math]::Max($Count, 30) } else { 50 }
        $query = "SELECT conversation_id, title, preview, last_modified_time, workspace_uris FROM conversation_summaries ORDER BY last_modified_time DESC LIMIT $limit;"
        $rows = & $sqliteCmd.Source $dbFile -separator '|||' $query 2>$null

        $dbList = [System.Collections.Generic.List[object]]::new()
        foreach ($r in $rows) {
            $parts = $r -split '\|\|\|', 5
            if ($parts.Count -lt 5) { continue }
            $cid = $parts[0].Trim()
            if ([string]::IsNullOrWhiteSpace($cid)) { continue } # 强过滤空 ID

            $title = $parts[1].Trim()
            $preview = $parts[2].Trim()
            $timeStr = $parts[3].Trim()
            $uris = $parts[4].Trim()

            # 时间转本地时间
            $localTime = $timeStr
            try {
                $dto = [DateTimeOffset]::Parse($timeStr)
                $localTime = $dto.LocalDateTime.ToString("yyyy-MM-dd HH:mm")
            } catch {}

            # 项目作用域判定
            $isMatchWs = $false
            $wsPath = ""
            if ($uris) {
                if ($uris.Contains($curUri)) {
                    $isMatchWs = $true
                    $wsPath = $currentDir
                } elseif ($uris -match 'file:///([^",]+)') {
                    $wsPath = $Matches[1] -replace '/', '\'
                }
            }

            if (-not $All -and -not $isMatchWs) { continue }

            $dbList.Add([PSCustomObject]@{
                Id        = $cid
                Title     = $title
                Preview   = $preview
                Time      = $localTime
                Workspace = $wsPath
                IsCurrent = $isMatchWs
            })

            if ($dbList.Count -ge $Count) { break }
        }

        if ($dbList.Count -gt 0) {
            # 辅助提取：从 history.jsonl 获取最新 Prompt（若有）
            $lastPrompts = @{}
            if (Test-Path $histFile) {
                try {
                    $targetIds = [System.Collections.Generic.HashSet[string]]::new([string[]]($dbList | ForEach-Object { $_.Id }))
                    $lines = Get-Content $histFile -Encoding utf8
                    foreach ($line in $lines) {
                        if ([string]::IsNullOrWhiteSpace($line)) { continue }
                        $obj = $line | ConvertFrom-Json
                        if ($obj.conversationId -and $targetIds.Contains($obj.conversationId)) {
                            $p = ($obj.display -replace "[\r\n]+", " ").Trim()
                            if ($p.Length -gt 42) { $p = $p.Substring(0, 39) + "..." }
                            $lastPrompts[$obj.conversationId] = $p
                        }
                    }
                } catch {}
            }

            $top = @($dbList)
            $wsName = Split-Path $currentDir -Leaf
            $header = if ($All) { "=== 全局所有项目最近的 $($top.Count) 条 agy 会话记录 ===" } else { "=== 当前项目 ($wsName) 最近的 $($top.Count) 条 agy 会话记录 ===" }
            Write-Host "`n$header" -ForegroundColor Cyan

            for ($i = 0; $i -lt $top.Count; $i++) {
                $item = $top[$i]
                $itemWs = if ($item.Workspace) { Split-Path $item.Workspace -Leaf } else { "未知" }
                $curTag = if ($item.IsCurrent) { " [当前项目]" } else { "" }
                Write-Host "[$($i + 1)] $($item.Time) ($itemWs$curTag)" -ForegroundColor Yellow

                $showTitle = if ($item.Title) { $item.Title } elseif ($item.Preview) { $item.Preview } else { "无标题会话" }
                $showPrompt = if ($lastPrompts.ContainsKey($item.Id)) { $lastPrompts[$item.Id] } elseif ($item.Preview) { $item.Preview } else { $showTitle }

                Write-Host "    Title  : $showTitle" -ForegroundColor Green
                Write-Host "    Prompt : $showPrompt" -ForegroundColor White
                Write-Host "    ID     : $($item.Id)" -ForegroundColor DarkGray
                if ($i -lt ($top.Count - 1)) { Write-Host "" }
            }
            Write-Host ""

            # 交互式选择恢复
            Write-Host "请选择要恢复的会话 [1-$($top.Count)] (直接回车进 [1]，输入 q 退出): " -NoNewline -ForegroundColor Green
            $choice = Read-Host
            if ($choice -match '^[qQ]$') { return }
            if ([string]::IsNullOrWhiteSpace($choice)) { $choice = "1" }

            if ($choice -match '^\d+$' -and [int]$choice -ge 1 -and [int]$choice -le $top.Count) {
                $targetId = $top[[int]$choice - 1].Id
                if (-not [string]::IsNullOrWhiteSpace($targetId)) {
                    Write-Host "正在启动会话: $targetId..." -ForegroundColor Cyan
                    agy --conversation=$targetId
                } else {
                    Write-Host "错误: 会话 ID 为空，已中止启动。" -ForegroundColor Red
                }
            } else {
                Write-Host "输入无效，已取消操作。" -ForegroundColor Red
            }
            return
        }
    }

    # ---------------- 兜底回退分支：从 history.jsonl 提取（带严格合法 ID 过滤） ----------------
    if (-not (Test-Path $histFile)) {
        Write-Host "未找到历史记录文件: $histFile" -ForegroundColor Red
        return
    }

    $lines = Get-Content $histFile -Encoding utf8
    $validList = [System.Collections.Generic.List[object]]::new()
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try {
            $obj = $line | ConvertFrom-Json
            if ($obj.conversationId -and (-not [string]::IsNullOrWhiteSpace($obj.conversationId)) -and ($obj.type -ne 'slash_command')) {
                $validList.Add($obj)
            }
        } catch {}
    }

    $groups = $validList | Group-Object conversationId
    $results = foreach ($g in $groups) {
        $sorted = @($g.Group | Sort-Object timestamp)
        $firstItem = $sorted[0]
        $lastItem = $sorted[-1]
        $time = [DateTimeOffset]::FromUnixTimeMilliseconds($lastItem.timestamp).LocalDateTime.ToString("yyyy-MM-dd HH:mm")
        
        $lastPrompt = ($lastItem.display -replace "[\r\n]+", " ").Trim()
        if ($lastPrompt.Length -gt 38) { $lastPrompt = $lastPrompt.Substring(0, 35) + "..." }

        $firstPrompt = ($firstItem.display -replace "[\r\n]+", " ").Trim()
        if ($firstPrompt.Length -gt 38) { $firstPrompt = $firstPrompt.Substring(0, 35) + "..." }

        [PSCustomObject]@{
            Id          = $g.Name
            Time        = $time
            Workspace   = $lastItem.workspace
            LastPrompt  = $lastPrompt
            FirstPrompt = $firstPrompt
            RawTime     = $lastItem.timestamp
        }
    }

    if (-not $All) {
        $candidates = @($results | Where-Object {
            $_.Workspace -and ($_.Workspace.TrimEnd('\', '/') -eq $currentDir)
        })
        if ($candidates.Count -eq 0) {
            $wsName = Split-Path $currentDir -Leaf
            Write-Host "`n当前项目 ($wsName) 暂无 agy 会话记录。可用 'agl -a' 查看全部。`n" -ForegroundColor Yellow
            return
        }
        $top = @($candidates | Sort-Object RawTime -Descending | Select-Object -First $Count)
        $wsName = Split-Path $currentDir -Leaf
        Write-Host "`n=== 当前项目 ($wsName) 最近的 $($top.Count) 条 agy 会话记录 ===" -ForegroundColor Cyan
    } else {
        $candidates = $results
        if ($candidates.Count -eq 0) {
            Write-Host "`n暂无任何 agy 会话记录。`n" -ForegroundColor Gray
            return
        }
        $top = @($candidates | Sort-Object RawTime -Descending | Select-Object -First $Count)
        Write-Host "`n=== 全局所有项目最近的 $($top.Count) 条 agy 会话记录 ===" -ForegroundColor Cyan
    }

    for ($i = 0; $i -lt $top.Count; $i++) {
        $item = $top[$i]
        $itemWs = if ($item.Workspace) { Split-Path $item.Workspace -Leaf } else { "未知" }
        $isCurrent = if ($item.Workspace -and ($item.Workspace.TrimEnd('\', '/') -eq $currentDir)) { " [当前项目]" } else { "" }
        Write-Host "[$($i + 1)] $($item.Time) ($itemWs$isCurrent)" -ForegroundColor Yellow
        Write-Host "    Title  : $($item.FirstPrompt)" -ForegroundColor Green
        Write-Host "    Prompt : $($item.LastPrompt)" -ForegroundColor White
        Write-Host "    ID     : $($item.Id)" -ForegroundColor DarkGray
        if ($i -lt ($top.Count - 1)) { Write-Host "" }
    }
    Write-Host ""

    Write-Host "请选择要恢复的会话 [1-$($top.Count)] (直接回车进 [1]，输入 q 退出): " -NoNewline -ForegroundColor Green
    $choice = Read-Host
    if ($choice -match '^[qQ]$') { return }
    if ([string]::IsNullOrWhiteSpace($choice)) { $choice = "1" }

    if ($choice -match '^\d+$' -and [int]$choice -ge 1 -and [int]$choice -le $top.Count) {
        $targetId = $top[[int]$choice - 1].Id
        if (-not [string]::IsNullOrWhiteSpace($targetId)) {
            Write-Host "正在启动会话: $targetId..." -ForegroundColor Cyan
            agy --conversation=$targetId
        } else {
            Write-Host "错误: 会话 ID 为空，已中止启动。" -ForegroundColor Red
        }
    } else {
        Write-Host "输入无效，已取消操作。" -ForegroundColor Red
    }
}
Set-Alias agl agy-list
# ==============================================================
```

### 3. 双端 Profile 同步与 UTF-8 BOM 固化部署
在终端中执行以下 PowerShell 片段，确保将配置以带 BOM 的 UTF-8 编码写入 PS7 和 PS5.1：
```powershell
$utf8Bom = [System.Text.UTF8Encoding]::new($true)
$p1 = "$HOME\Documents\PowerShell\Microsoft.PowerShell_profile.ps1"
$p2 = "$HOME\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1"

# 分别读取并更新 $p1 与 $p2
# 写入后立即热加载：
. $PROFILE
```

---

## 四、验证与防复发闭环

### 1. 验证清单
1. **默认当前项目聚焦验证**：在任意项目根目录输入 `agl`，验证输出仅包含当前目录下的记录，标题行显示绿色 `Title`。
2. **全局漫游验证**：执行 `agl -a`，验证能检索出跨工作区的全部历史会话，且当前项目带高亮标签。
3. **单轮会话 100% 捕获验证**：即使某会话仅输入一轮即退出、在 `history.jsonl` 中未记录 ID，也能在 `agl` 中精准按修改时间正确展示，绝不漏单。
4. **0 幽灵组与空 ID 拦截验证**：检查列表前排绝不会出现 `Title: /model` 或 `ID : ` 为空的记录；选择序号启动时若 ID 异常为空有明确拦截红字，不会误开空白会话。
5. **交互选择验证**：
   * 按回车直接调起第 `[1]` 项；
   * 输入有效序号（如 `3`）调起对应会话，检查终端输出参数是否干净，无 `@{Id=...}` 字符串污染；
   * 输入 `q` 退出无异常副作用。
6. **宿主通吃验证**：分别在 Zed 内置终端、微软官方 Windows Terminal、独立定制版 WT 中启动会话，验证 `agl` 行为完全一致。

### 2. 核心避坑红线
* **严禁以 history.jsonl 作为会话主驱动源**：`history.jsonl` 本质是按键历史（含斜杠命令与无 ID 孤儿行），绝对不可用来 `Group-Object` 作为会话索引主表；会话权威源必须以 `conversation_summaries.db` 为主表，`history.jsonl` 仅作辅助查 Prompt。
* **严禁裸写属性传参**：向任何 CLI 传参时，严禁 `cli --param=$obj.Field`，务必通过纯字符串标量解耦传递。
* **避免直接修改或独占 SQLite 库**：`conversation_summaries.db` 由客户端并发读写，读取时仅进行快照式 `SELECT` 查询，避免长事务占用锁库。
* **Profile 编码红线**：只要 Profile 包含中文字符串，必须严格保持 UTF-8 BOM 签名，杜绝编码错位引发的解析瘫痪。
