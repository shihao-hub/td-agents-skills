---
name: kb-flat-filename-metadata-spec
description: Windows平铺知识库文件名元数据嵌入规范与双端自解释架构。涵盖下划线分面槽位语法、受控词汇表、Explorer自动聚类排序、正则秒级无损提取，以及全库批量平滑迁移与回滚SOP。
---

# 50-Windows平铺知识库文件名元数据嵌入架构与双端自解释命名规范

> **条目定位**：Type B 方案与流水线型条目  
> **适用场景**：单目录平铺（零子目录）知识库在文章规模达到 50~100+ 篇时，解决 Windows 资源管理器排序割裂、长标题截断、机器无法正则提取分类标签等元数据缺失问题。

---

## 一、业务场景与元数据痛点

在坚持**“单目录完全平铺（Flat Structure，无子目录嵌套）”**的知识库架构下，随着条目从数十篇生长至上百篇，原有 `0N-目标技术核心问题与解决目标.md` 的单一流水号命名法暴露出严重的工程缺陷：

1. **同类领域割裂（排序失控）**：
   - 依赖纯数字序号（`01~49`）前缀，导致在 Windows 资源管理器（按名称排序）中，相同主题的条目被强行拆散。例如 Git 相关手记散落在 `01`、`02`、`03`、`06`、`27`、`31`；Sublime 相关手记散落在 `01`、`16`、`33`、`34`、`44`、`47`。
   - 人类浏览时必须逐行通读冗长汉字，缺乏领域聚合块（Visual Chunks）。
2. **条目属性隐匿（形态缺失）**：
   - 无法直接通过文件名判断条目属于 **Type A（疑难报错排障）**、**Type B（端到端实现流水线）** 还是 **纯环境配置/改键（Config）**。
3. **机器消费高昂（正则与提取困难）**：
   - 外部 Agent、PowerShell 脚本或搜索工具无法零 I/O 成本提取元数据，必须加载文档全文读取 frontmatter 才能建立分类索引，大幅消耗上下文与文件读取配额。
4. **Explorer 视窗截断**：
   - 传统长标题动辄 40~50 个中文字符，在 Windows 详细信息视窗或分屏窗口中，关键动作往往被尾部 `...` 截断。

---

## 二、底层设计难点与 Windows 文件系统约束

构建“人机双端自解释”的平铺文件名，必须在 Windows 物理文件系统约束与开发体验之间取得严格平衡：

### 1. Windows 文件名硬性红线
* **绝对保留字符禁止**：严禁出现 `\ / : * ? " < > |`。**这意味着不可使用冒号作为键值对分隔符（如 `type:fix` 在 Windows 上属于非法文件名）**。
* **大小写不敏感（Case-Preserving Case-Insensitive）**：Windows 底层 NTFS 默认忽略文件名大小写，因此不可通过 CamelCase 大小写切换来作为语义识别切分标记。
* **CLI 与 Shell 逃逸友好性**：若使用方括号 `[tag]`、括号 `(tag)` 或井号 `#tag`，在 PowerShell、Bash、Glob 通配符中均属于特殊控制符，命令行处理时极易发生转义错误；下划线 `_` 和连字符 `-` 对所有 Shell 均 100% 安全免转义。

### 2. 双重分隔符机制（Dual-Delimiter Pattern）
借鉴科学数据命名规范（如 BIDS / POSIX Portable Filenames）：
* **槽位分隔符（Field Delimiter）**：统一采用 **下划线 `_`**。专门负责切分不同维度的元数据字段；
* **语义内连接符（Word Delimiter）**：统一采用 **连字符 `-`** 或汉字短语。负责连接同一槽位内部的复合词。

### 3. Explorer 自然排序权重（Natural Sort Weight）
Windows 资源管理器按名称升序排序时，遵循 ASCII 字符字典序：`0-9` 优于 `a-z`。通过为槽位规定定长前缀，可彻底锁定 Explorer 中的可视聚合结构。

---

## 三、标准规范实现：分面槽位分词法（Faceted Kebab-Snake）

### 1. 语法结构定义
平铺知识库文件名由 4 个固定槽位组成，语法定义如下：

```text
<领域Domain>_<形态Type>_<三位定长序号ID>_<核心问题与解决目标Title>.md
```

* **正则表达式（无损提取校验）**：
  ```regex
  ^(?<domain>[a-z]{2,8})_(?<type>[a-z]{3,5})_(?<id>\d{3})_(?<title>[^_\/\\:\*\?"<>\|]+)\.md$
  ```

---

### 2. 槽位 1：受控领域词典（Domain Vocabulary）
严格限制在 3~6 个纯小写英文字母。**在 Windows Explorer 中，同领域条目将自动整齐聚类在一起**：

| 领域标识 | 含义与归属范围 | 现有条目归属示例 |
| :--- | :--- | :--- |
| **`git`** | 版本控制、Merge、Rebase、Worktree、SSH 多账号、GitLG | `git_fix_002_变基文件锁排障与Abort安全恢复.md`<br>`git_cfg_027_多Git账号SSH与IncludeIf配置.md` |
| **`win`** | Windows 系统底层、C盘空间、音频爆音、网络回环、计划任务、Everything、软链接 | `win_fix_011_计划任务控制台委托闪窗与conhost注册.md`<br>`win_fix_020_C盘空间排查与软链接重定向.md` |
| **`ide`** | 常用编辑器与 IDE（Sublime、Zed、Cursor、VSCode、Terminal、Pi） | `ide_cfg_004_Cursor预览独立标签页切换.md`<br>`ide_fix_022_Zed语言服务器重命名与杀毒竞态.md`<br>`ide_fix_048_WinTerminal分屏窗格判定与关闭误触.md` |
| **`browser`**| 浏览器底层、扩展注入机制、SNSS 会话恢复、DevTools MCP 联动 | `browser_fix_009_Chrome关闭标签丢失SNSS快照找回.md`<br>`browser_fix_049_Chrome与Firefox静默安装迅雷与BT替代.md` |
| **`agent`** | AI 客户端、OpenCode、CLI 管道防挂起、模型供应商配置、API Key 治理 | `agent_fix_021_opencode连接GLM鉴权401与端点排障.md`<br>`agent_flow_045_全机AI密钥清点与供应商指纹脱敏.md` |
| **`dev`** | 跨语言环境配置、工程架构、构建流水线（Python-docx、uv、Java、Maven、OOP 重构） | `dev_flow_015_docx自动化生成试卷与排版流水线.md`<br>`dev_cfg_007_uv统一全机Python与新机引导复现.md`<br>`dev_flow_040_AI辅助面向对象OOP重构与模式演进.md` |
| **`media`** | 媒资处理、音频下载、声学降噪掩蔽、视频字幕 | `media_flow_013_降噪耳机人声泄露声学掩蔽与公有音频.md` |

---

### 3. 槽位 2：条目形态词典（Type Vocabulary）
直接映射 `SKILL-AUTHORING-RULES.md` 的条目形态，一目了然区分实战性质：

| 形态标识 | 对应规范章节 | 核心特征与四段论结构 |
| :--- | :--- | :--- |
| **`fix`** | **Type A 疑难排障** | 包含错误报错直击、系统底层根因、原子化抢救 SOP、防复发验证 |
| **`flow`** | **Type B 方案/流水线** | 包含业务场景输入输出、核心技术解析、完整可复用脚本、交付验收断言 |
| **`cfg`** | **环境配置与调优** | 包含配置文件模板、快捷键/改键集成、免安装绿色化配置 |
| **`guide`** | **架构设计与方法论** | 包含权衡原则、模式演进、对比选型、防坑红线 |

---

### 4. 槽位 3：三位定长序号（ID）
* 采用 `001` ~ `999` 格式（如 `001`、`049`）。
* **彻底根除 Windows 字典序倒挂**：避免出现传统 `1, 10, 11, 2, 20` 混乱插入现象，同时保留全局唯一编号，与历史引用和外部映射严格兼容。

---

### 5. 槽位 4：人读自解释主题（Human Slug）
* **精炼原则**：删除无实义尾缀（如“...指南.md”、“...实战.md”全部剔除），直接表达“**核心问题 + 解决核心/产物**”；
* **长度控制**：中文控制在 25 字符以内，确保在 Windows 资源管理器详细信息列表模式下 100% 完整显示不换行。

---

## 四、双端消费实证对比

### 1. 人类视角：Windows 文件资源管理器效果
在平铺目录下按“名称”排序，文件呈现出**天然的分块聚合目录感**：

```text
kb-engineering-notes/
├── SKILL-DRAFT.md
├── agent_fix_021_opencode连接GLM鉴权401与端点排障.md
├── agent_fix_042_多Agent全局规则生效与CLI管道防挂起.md
├── agent_fix_043_OpenCodeGo模型提速与关闭思考reasoningEffort.md
├── agent_flow_045_全机AI密钥清点与供应商指纹脱敏.md
├── browser_fix_009_Chrome关闭标签丢失SNSS快照找回.md
├── browser_fix_049_Chrome与Firefox静默安装迅雷与BT替代.md
├── dev_cfg_007_uv统一全机Python与新机引导复现.md
├── dev_cfg_008_Win下Java与Maven便携配置及Zed集成.md
├── dev_flow_015_docx自动化生成试卷与排版流水线.md
├── dev_flow_040_AI辅助面向对象OOP重构与模式演进.md
├── git_cfg_027_多Git账号SSH与IncludeIf配置.md
├── git_fix_001_SublimeMerge非相邻提交Squash合并重排.md
├── git_fix_002_变基PermissionDenied文件锁排障与安全恢复.md
├── git_fix_003_变基Rescheduled队列挂起与冲突解析.md
├── git_flow_006_Worktree跨语言依赖复用与环境隔离权衡.md
├── ide_cfg_004_Cursor预览独立标签页切换.md
├── ide_cfg_005_Cursor免审批YOLO模式与沙箱网络.md
├── ide_fix_022_Zed语言服务器重命名与杀毒竞态.md
├── ide_fix_048_WinTerminal分屏窗格判定与关闭误触.md
├── win_fix_011_计划任务控制台委托闪窗与conhost注册.md
├── win_fix_018_Win代理下微软商店与UWP回环豁免.md
├── win_fix_020_C盘空间排查与软链接重定向.md
└── win_flow_050_平铺知识库文件名元数据规范与迁移SOP.md
```

### 2. 机器视角：PowerShell 零成本秒级无损提取

```powershell
# 1. 极速提取元数据（无需解析任何正文，开销趋近于 0）
$file = "browser_fix_049_Chrome与Firefox静默安装迅雷与BT替代.md"
$domain, $type, $id, $title = $file.Split('_', 4)

# 机器获取的对象结构：
[PSCustomObject]@{
    Domain = $domain  # "browser"
    Type   = $type    # "fix"
    ID     = $id      # "049"
    Title  = $title   # "Chrome与Firefox静默安装迅雷与BT替代.md"
}

# 2. Agent 命令行一键精准检索
# 仅筛选所有 Git 疑难排障手记：
Get-ChildItem -Filter "git_fix_*"

# 仅筛选所有自动化生成流水线：
Get-ChildItem -Filter "*_flow_*"
```

---

## 五、全库批量平滑迁移与安全回滚 SOP

为了在不破坏知识库正常运行的前提下完成历史文档的升级，提供带 **试跑（DryRun）** 与 **一键回滚（Rollback）** 的安全迁移脚本参考实现。

### 自动化迁移脚本参考实现（按需创建临时脚本执行）

> 💡 **设计说明**：为保持单目录平铺知识库的干净纯粹，避免在知识库子目录下存放非持久化运行的代码资产，本迁移脚本作为**随需即用（On-demand）的 SOP 代码块**内置归档于本文档中。如未来需执行物理批量迁移，只需在知识库根目录下临时创建 `migrate_kb_filenames.ps1` 执行，跑完并验证映射后即可随时删除。

```powershell
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
```

---

## 六、交付验证与扩展建议

1. **零破坏渐进式推进**：
   * 本规范已直接固化落盘为知识库第 50 项，无需立即执行物理重命名，随时可作为团队或个人知识治理的标准规范查阅；
   * 后续新增条目（如 51 项起）可选择直接采用新语法 `git_fix_051_...`，或在准备就绪时运行附带的迁移脚本一键完成 01~50 项全量规整。
2. **`SKILL-DRAFT.md` 同步保障**：
   * 迁移脚本在执行重命名时，会联动对 `SKILL-DRAFT.md` 内部的所有超链接路径执行全局正则替换，确保内部两级感知路由体系完全不中断。
