param(
    [switch]$Execute,   # 显式指定才执行物理改名，默认仅预览 (DryRun)
    [switch]$Rollback   # 一键从 mapping.json 恢复原始文件名
)

$kbDir = Split-Path $PSScriptRoot -Parent
$mapFile = Join-Path $PSScriptRoot "rename_mapping.json"
$draftFile = Join-Path $kbDir "SKILL-DRAFT.md"

if ($Rollback) {
    if (-not (Test-Path $mapFile)) {
        Write-Error "未找到回滚映射表 $mapFile"
        exit 1
    }
    $map = Get-Content $mapFile -Raw -Encoding UTF8 | ConvertFrom-Json
    $draftContent = if (Test-Path $draftFile) { [System.IO.File]::ReadAllText($draftFile, [System.Text.Encoding]::UTF8) } else { $null }

    foreach ($item in $map) {
        $oldPath = Join-Path $kbDir $item.NewName
        $origPath = Join-Path $kbDir $item.OldName
        if (Test-Path $oldPath) {
            Rename-Item -Path $oldPath -NewName $item.OldName -Force
            Write-Host "已恢复: $($item.NewName) -> $($item.OldName)" -ForegroundColor Yellow
        }
        if ($draftContent) {
            $draftContent = $draftContent.Replace($item.NewName, $item.OldName)
        }
    }
    if ($draftContent) {
        [System.IO.File]::WriteAllText($draftFile, $draftContent, [System.Text.Encoding]::UTF8)
        Write-Host "SKILL-DRAFT.md 链接已同步回滚。" -ForegroundColor Yellow
    }
    exit 0
}

# 领域与形态规则字典
$ruleMap = @{
    "01" = @{ Dom = "git";     Type = "fix";  Title = "SublimeMerge非相邻提交Squash合并重排.md" }
    "02" = @{ Dom = "git";     Type = "fix";  Title = "变基PermissionDenied文件锁排障与安全恢复.md" }
    "03" = @{ Dom = "git";     Type = "fix";  Title = "变基Rescheduled队列挂起与暂存区冲突.md" }
    "04" = @{ Dom = "ide";     Type = "cfg";  Title = "Cursor预览独立标签页切换.md" }
    "05" = @{ Dom = "ide";     Type = "cfg";  Title = "Cursor免审批YOLO模式与沙箱网络.md" }
    "06" = @{ Dom = "git";     Type = "flow"; Title = "Worktree跨语言依赖复用与环境隔离权衡.md" }
    "07" = @{ Dom = "dev";     Type = "cfg";  Title = "uv统一全机Python与新机引导复现.md" }
    "08" = @{ Dom = "dev";     Type = "cfg";  Title = "Win下Java与Maven便携配置及Zed集成.md" }
    "09" = @{ Dom = "browser"; Type = "fix";  Title = "Chrome关闭标签丢失SNSS会话快照找回.md" }
    "10" = @{ Dom = "ide";     Type = "fix";  Title = "CLI粘贴图片Kitty透传与BOM排障.md" }
    "11" = @{ Dom = "win";     Type = "fix";  Title = "计划任务控制台委托闪窗与conhost注册.md" }
    "12" = @{ Dom = "agent";   Type = "cfg";  Title = "CLI执行模式与免批YOLO排障.md" }
    "13" = @{ Dom = "media";   Type = "flow"; Title = "降噪耳机人声泄露声学掩蔽与公有音频.md" }
    "14" = @{ Dom = "win";     Type = "cfg";  Title = "Win单手盲切与抽屉式Toggle窗口AHK配置.md" }
    "15" = @{ Dom = "dev";     Type = "flow"; Title = "docx自动化生成试卷与排版流水线.md" }
    "16" = @{ Dom = "ide";     Type = "fix";  Title = "SublimeTerminus退格失效与原生终端集成.md" }
    "17" = @{ Dom = "win";     Type = "fix";  Title = "Win声卡爆音无声与虚拟音频抢占排查.md" }
    "18" = @{ Dom = "win";     Type = "fix";  Title = "Win代理下微软商店与UWP回环豁免.md" }
    "19" = @{ Dom = "win";     Type = "fix";  Title = "Win内存防死机与Pagefile提交归因优化.md" }
    "20" = @{ Dom = "win";     Type = "fix";  Title = "Win系统C盘空间不足排查与软链接重定向.md" }
    "21" = @{ Dom = "agent";   Type = "fix";  Title = "opencode连接GLM鉴权401与端点排障.md" }
    "22" = @{ Dom = "ide";     Type = "fix";  Title = "Zed语言服务器重命名与杀毒竞态.md" }
    "23" = @{ Dom = "ide";     Type = "fix";  Title = "Zed与IDEA外接ACP代理失效与进程堆积.md" }
    "24" = @{ Dom = "ide";     Type = "fix";  Title = "Zed面板InternalError会话中断与锁竞态.md" }
    "25" = @{ Dom = "ide";     Type = "fix";  Title = "Zed会话丢失提取与SQLite解析抢救.md" }
    "26" = @{ Dom = "ide";     Type = "cfg";  Title = "Zed项目级LSP白名单与内存优化.md" }
    "27" = @{ Dom = "git";     Type = "cfg";  Title = "多Git账号SSH与IncludeIf配置.md" }
    "28" = @{ Dom = "ide";     Type = "fix";  Title = "Win终端Atuin历史同步与Profile修复.md" }
    "29" = @{ Dom = "agent";   Type = "cfg";  Title = "cc-switch直接读写SQLite模型迁移.md" }
    "30" = @{ Dom = "ide";     Type = "cfg";  Title = "VSCode扩展跨分支IDE手动搬运.md" }
    "31" = @{ Dom = "git";     Type = "cfg";  Title = "VSCode底部面板GitLG配色调优.md" }
    "32" = @{ Dom = "win";     Type = "cfg";  Title = "Win便携PowerShell7绿色部署.md" }
    "33" = @{ Dom = "ide";     Type = "cfg";  Title = "YaHeiConsolasHybrid字体渲染与Sublime配置.md" }
    "34" = @{ Dom = "ide";     Type = "cfg";  Title = "Win11右键菜单注册Sublime与注册表快捷管理.md" }
    "35" = @{ Dom = "ide";     Type = "fix";  Title = "Pi终端改键与滚轮协议冲突修复.md" }
    "36" = @{ Dom = "agent";   Type = "cfg";  Title = "各Agent客户端终端机制与GitBash切换.md" }
    "37" = @{ Dom = "browser"; Type = "cfg";  Title = "opencode集成chrome-devtools-mcp浏览器控制.md" }
    "38" = @{ Dom = "agent";   Type = "cfg";  Title = "Zed集成opencodeAgent思考档位与供应商迁移.md" }
    "39" = @{ Dom = "agent";   Type = "flow"; Title = "无搜索API时DDG端点核查与一手信源收敛.md" }
    "40" = @{ Dom = "dev";     Type = "flow"; Title = "AI辅助面向对象OOP重构与模式演进.md" }
    "41" = @{ Dom = "win";     Type = "fix";  Title = "Win跨盘单文件软链接权限与Junction排障.md" }
    "42" = @{ Dom = "agent";   Type = "fix";  Title = "多Agent全局规则生效与CLI管道防挂起.md" }
    "43" = @{ Dom = "agent";   Type = "fix";  Title = "OpenCodeGo模型提速与关闭思考reasoningEffort.md" }
    "44" = @{ Dom = "ide";     Type = "fix";  Title = "SublimeMarkdown预览抢焦点与静默改键.md" }
    "45" = @{ Dom = "agent";   Type = "flow"; Title = "全机AI密钥清点与供应商指纹脱敏.md" }
    "46" = @{ Dom = "win";     Type = "fix";  Title = "Win进程启动来源取证与Everything闲置保护.md" }
    "47" = @{ Dom = "ide";     Type = "fix";  Title = "Sublime全局搜索穿透Gitignore慢查排障.md" }
    "48" = @{ Dom = "ide";     Type = "fix";  Title = "WinTerminal分屏窗格判定与关闭误触.md" }
    "49" = @{ Dom = "browser"; Type = "fix";  Title = "Chrome与Firefox静默安装迅雷与BT替代.md" }
    "50" = @{ Dom = "win";     Type = "flow"; Title = "平铺知识库文件名元数据规范与迁移SOP.md" }
}

$plan = [System.Collections.Generic.List[PSCustomObject]]::new()
$files = Get-ChildItem -Path $kbDir -Filter "*.md" | Where-Object { $_.Name -match "^\d{2}-" }

foreach ($f in $files) {
    $num = $f.Name.Substring(0, 2)
    if ($ruleMap.ContainsKey($num)) {
        $meta = $ruleMap[$num]
        $padNum = $num.PadLeft(3, '0')
        $newName = "$($meta.Dom)_$($meta.Type)_$padNum`_$($meta.Title)"
        $plan.Add([PSCustomObject]@{
            OldName = $f.Name
            NewName = $newName
            OldPath = $f.FullName
            NewPath = (Join-Path $kbDir $newName)
        })
    }
}

if (-not $Execute) {
    Write-Host "=== 试跑模式 (DryRun) - 共计划转换 $($plan.Count) 个文件 ===" -ForegroundColor Cyan
    $plan | Format-Table -Property OldName, NewName -AutoSize
    Write-Host "提示：如需物理执行迁移，请运行: .\migrate_kb_filenames.ps1 -Execute" -ForegroundColor Yellow
} else {
    $plan | ConvertTo-Json -Depth 3 | Set-Content -Path $mapFile -Encoding UTF8
    $draftContent = if (Test-Path $draftFile) { [System.IO.File]::ReadAllText($draftFile, [System.Text.Encoding]::UTF8) } else { $null }

    foreach ($p in $plan) {
        Rename-Item -Path $p.OldPath -NewName $p.NewName -Force
        Write-Host "已重命名: $($p.OldName) -> $($p.NewName)" -ForegroundColor Green
        if ($draftContent) {
            $draftContent = $draftContent.Replace($p.OldName, $p.NewName)
        }
    }
    if ($draftContent) {
        [System.IO.File]::WriteAllText($draftFile, $draftContent, [System.Text.Encoding]::UTF8)
        Write-Host "SKILL-DRAFT.md 链接已全量同步替换。" -ForegroundColor Green
    }
    Write-Host "全量迁移完毕，映射已保存至 $mapFile" -ForegroundColor Green
}
