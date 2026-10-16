---
name: kb-zed-terminal-agy-history-restore
description: Zed 终端无会话滚动恢复机制导致 agy 历史会话 ID 丢失排障：剖析 PTY 进程生命周期与无缓冲区落盘机理、PowerShell 外部命令对象属性传参解析陷阱、agy 本地 history.jsonl 与 conversation_summaries.db 存储架构，封装 agl 交互式会话选择器（默认工作区聚焦、-a 全局漫游、AI 业务标题提取与回车秒恢复）。当 Zed 重启后终端空白找不到上轮 agy 会话、或 agy --conversation 报错时查阅。
version: 1.0.0
created: 2026-10-16
updated: 2026-10-16
---

# Zed 终端无会话恢复 agy 历史 ID 丢失排障与 PowerShell 交互选号恢复指南

> **适用场景**：在 Zed 编辑器中使用内置终端运行 Antigravity CLI（`agy`），退出会话或重启 Zed 后，由于 Zed 缺乏类似 Windows Terminal 的会话滚动历史恢复（Session Restoration），屏幕输出被彻底清空，无法通过向上滚屏查看上一轮的 `Resume with -c: agy --conversation=<id>`；且通过脚本自动传参启动时，踩中 PowerShell 外部程序对象属性解析陷阱导致报 `conversation "@{Id=...}.Id" not found`；或者仅看 Prompt 难以辨识会话任务，急需在终端中查看带 AI 精炼业务标题（Title）并支持快捷选号秒恢复的工作流。

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

---

## 二、底层根因剖析

### 1. Zed 与 Windows Terminal 的终端持久化架构差异
* **Zed 的 PTY 生命周期**：Zed 的内置终端基于 Rust 的 `alacritty_terminal` 渲染组件。终端 PTY 会话作为 Zed 窗口进程的直系子进程存在。窗口或应用退出时，操作系统向下分发进程终止信号。目前 Zed **未实现终端滚动缓冲区（Scrollback Buffer）落盘序列化机制**，Zed 自身的 `db.sqlite` 仅记录 Pane 元数据（如路径、Pin 状态），重启时仅执行全新的 `spawn("pwsh.exe")` 冷启动。
* **Windows Terminal 的 Buffer 快照机制**：WT v1.20+ 拥有完备的 `Session Restoration`，在退出时将字符网格完整序列化落盘，重启后原样反序列化重绘并打上 `[已还原 ...]` 标记，再挂载新会话。

### 2. agy 客户端的双层本地持久化架构
`agy` 并非易失性运行，其在本地维护了清晰的双层数据资产：
1. **交互流水账（`~/.gemini/antigravity-cli/history.jsonl`）**：
   每轮用户输入追加一条 JSON，包含 `workspace`（绝对路径）、`conversationId`（UUID）、`timestamp`（毫秒时间戳）以及 `display`（原始输入文本）。
2. **结构化元数据（`~/.gemini/antigravity-cli/conversation_summaries.db`）**：
   标准的 SQLite 数据库，核心表 `conversation_summaries` 包含：
   * `conversation_id`：主键。
   * `title`：后台大模型根据对话意图**异步提炼生成的精炼业务标题**（如 `VS Code 图标脚本排障`、`Opencode Go Quota Check Feature`）。
   * `preview`、`workspace_uris`、`last_modified_time` 等。

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
将以下函数注入 PowerShell Profile，实现项目作用域聚焦、AI 标题渲染、跨项目漫游与交互式选号恢复：

```powershell
# ==================== agy 会话管理快捷命令 ====================
# 查看 agy 会话记录（默认只展示当前项目最近 5 条，带 AI 提炼标题，支持选号/回车直接恢复；加 -a 或 -All 展示全部项目）
function agy-list {
    [CmdletBinding()]
    param(
        [Parameter(Position = 0)]
        [int]$Count = 5,

        [Parameter()]
        [Alias('a')]
        [switch]$All
    )

    $histFile = "$HOME\.gemini\antigravity-cli\history.jsonl"
    $dbFile = "$HOME\.gemini\antigravity-cli\conversation_summaries.db"
    if (-not (Test-Path $histFile)) {
        Write-Host "未找到历史记录文件: $histFile" -ForegroundColor Red
        return
    }

    $lines = Get-Content $histFile -Encoding utf8
    $allList = [System.Collections.Generic.List[object]]::new()
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try { $allList.Add(($line | ConvertFrom-Json)) } catch {}
    }

    $currentDir = (Get-Location).Path.TrimEnd('\', '/')

    # 按会话去重聚合并提取首末轮交互
    $groups = $allList | Group-Object conversationId
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

    # 作用域过滤：默认锁定当前项目，-All 跨项目漫游
    if (-not $All) {
        $candidates = @($results | Where-Object {
            $_.Workspace -and ($_.Workspace.TrimEnd('\', '/') -eq $currentDir)
        })
        if ($candidates.Count -eq 0) {
            $wsName = Split-Path $currentDir -Leaf
            Write-Host "`n当前项目 ($wsName) 暂无 agy 会话记录。" -ForegroundColor Yellow
            Write-Host "提示: 输入 'agl -a' 或 'agl -All' 可查看其他所有项目的会话。`n" -ForegroundColor DarkGray
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

    # 尝试读取数据库中由 AI 自动提炼的会话精炼标题
    $titles = @{}
    if (Test-Path $dbFile) {
        $sqliteCmd = Get-Command sqlite3 -ErrorAction SilentlyContinue
        if ($sqliteCmd) {
            $idList = ($top | ForEach-Object { "'$($_.Id)'" }) -join ","
            if ($idList) {
                $query = "SELECT conversation_id, title FROM conversation_summaries WHERE conversation_id IN ($idList);"
                $rows = & $sqliteCmd.Source $dbFile $query 2>$null
                foreach ($row in $rows) {
                    $parts = $row -split '\|', 2
                    if ($parts.Count -eq 2 -and $parts[1]) {
                        $titles[$parts[0].Trim()] = $parts[1].Trim()
                    }
                }
            }
        }
    }

    # 渲染清晰清单
    for ($i = 0; $i -lt $top.Count; $i++) {
        $item = $top[$i]
        $itemWs = if ($item.Workspace) { $item.Workspace.TrimEnd('\', '/') } else { "" }
        $isCurrent = if ($itemWs -eq $currentDir) { " [当前项目]" } else { "" }
        $wsName = if ($item.Workspace) { Split-Path $item.Workspace -Leaf } else { "未知" }
        
        $title = if ($titles.ContainsKey($item.Id) -and $titles[$item.Id]) { $titles[$item.Id] } else { $item.FirstPrompt }

        $headerLine = "[$($i + 1)] " + $item.Time + " (" + $wsName + $isCurrent + ")"
        Write-Host $headerLine -ForegroundColor Yellow
        Write-Host "    Title  : $title" -ForegroundColor Green
        Write-Host "    Prompt : $($item.LastPrompt)" -ForegroundColor White
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
        $target = $top[[int]$choice - 1]
        $targetId = $target.Id
        Write-Host "正在启动会话: $targetId..." -ForegroundColor Cyan
        agy --conversation=$targetId
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
3. **交互选择验证**：
   * 按回车直接调起第 `[1]` 项；
   * 输入有效序号（如 `3`）调起对应会话，检查终端输出参数是否干净，无 `@{Id=...}` 字符串污染；
   * 输入 `q` 退出无异常副作用。
4. **宿主通吃验证**：分别在 Zed 内置终端、微软官方 Windows Terminal、独立定制版 WT 中启动会话，验证 `agl` 行为完全一致。

### 2. 核心避坑红线
* **严禁裸写属性传参**：向任何 CLI 传参时，严禁 `cli --param=$obj.Field`，务必通过纯字符串标量解耦传递。
* **避免直接修改或独占 SQLite 库**：`conversation_summaries.db` 由客户端并发读写，读取时仅进行快照式 `SELECT` 查询，避免长事务占用锁库。
* **Profile 编码红线**：只要 Profile 包含中文字符串，必须严格保持 UTF-8 BOM 签名，杜绝编码错位引发的解析瘫痪。
