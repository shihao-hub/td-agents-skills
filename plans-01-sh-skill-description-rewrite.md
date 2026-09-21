# Plan: sh-* skill description 重写（23 个，仅 frontmatter）

📋 Plan for: "sh-* skill 整改——只重写 description，不改名/不动正文"

## 问题陈述

67 个 skill 的 description 常驻每个会话的 system prompt（合计 20,791 字符），其中 26 个 sh-* 合计 9,482 字符，且普遍为"触发词穷举 + 必须使用本 skill 即使只说 X 也要触发"的军备竞赛写法。用户实际使用模式为**直接点名 skill name**（AI 几乎不需要自主触发），长 description 因此是纯负资产：每会话付 token 成本，同时扩大 AI 误触发面。目标：把 23 个 sh-* 的 description 压成一行功能语义（预期 9,482 → ~1,900 字符），删除全部触发套话；plan 三件套本轮不动。

## 需求（含用户原话决策）

- 只动 frontmatter 的 `description` 一行，**其余一律不动**："名字不用改"
- 不转 command（"除了 opencode 其他 agent 也会使用，目前发现 skills 是最统一的"）、不迁项目级、不加 `disable-model-invocation` 字段（"我主要使用 opencode"）
- plan 三件套（sh-claude-plan-mode、sh-plan-driven-development、sh-spec-driven-development）延后处理
- lark-*/redis-* 等外部 skill 本轮不动（延后积压）
- 两个 repo 绑定型（cluacpp-build、sql-query-builder）description 通用化措辞
- description 优化目标：帮用户扫目录 + 防 AI 误触发；点名类结尾带"点名使用"，auto 类保留触发语义但划清边界

## 背景

- `~/.agents/skills` 是真实目录，`~/.config/opencode/skills` 与 `~/.claude/skills` 是指向它的 Junction——改一处即三处生效
- sh-* 正文结构健康（15+/26 有 references/、11 有 scripts/、5 有 evals/），正文按需加载，不是本轮对象
- opencode 约束：description 1–1024 字符；frontmatter 其他字段不动即无连带
- git 工作区当前干净，HEAD 即回滚基线

## 方案

### 改写模板

- **点名类（21 个）**：一句话功能语义；按性质加"装机：/配置：/排障："前缀；结尾"点名使用"；删除全部"必须使用本 skill""即使只说 X 也要触发"语句
- **auto 类（2 个）**：保留"何时用"触发语义，划清边界（何时不用），去军备竞赛语言
- 改写前后示例（sh-pwsh7-install，279 字符 → ~40 字符）：
  - 旧：`在 Windows 上零影响安装 PowerShell 7.x（跨平台 pwsh）：ZIP 绿色版……删除文件夹即卸载。当用户提到安装/升级 PowerShell 7、pwsh、PS7……即使只说"装个新版 powershell"也应触发。`
  - 新：`装机：PowerShell 7 绿色版 ZIP 安装，零影响可卸干净。点名使用`

### 新 description 全表（23 条，审批对象）

| # | skill | 新 description |
|---|---|---|
| 1 | sh-atuin-pwsh-history | 装机/排障：Windows atuin 命令历史配置与 profile 修复（hh、Ctrl+r、上下键召回）。点名使用 |
| 2 | sh-bruno-collection | 为 HTTP 接口生成 Bruno API 测试集合（.bru）。点名使用 |
| 3 | sh-cc-switch-db | 直接读写 cc-switch SQLite，绕过 UI 配置各应用供应商。点名使用 |
| 4 | sh-chrome-devtools-mcp-setup | 装机：opencode 配置 chrome-devtools-mcp 浏览器控制。点名使用 |
| 5 | sh-cluacpp-build | C/C++/Lua 项目工具链与构建手册：LLVM/Ninja/MSVC、CMake Presets、FetchContent 集成 Lua、clangd、编译报错速查。点名使用 |
| 6 | sh-github-coexist | 装机：个人 GitHub 与公司 GitLab 共存，SSH key+includeIf 身份自动切换+批量推仓库。点名使用 |
| 7 | sh-github-repo-cleanup | GitHub 仓库大扫除：审计→fork 转 Star→mirror 备份→批量删除/归档。点名使用 |
| 8 | sh-image-watermark-removal | 去水印/角标：PIL+numpy 局部修补，擅长水印压在图案笔画上的复杂情形。点名使用 |
| 9 | sh-lark-chat-archive | 飞书聊天记录归档为单文件 HTML（私聊/群聊/话题，纸面排版+图注+lightbox）。点名使用 |
| 10 | sh-opencode-glm-auth | 排障：opencode 连 GLM 报 401/身份验证失败；apiKey 优先级、双端点 key 矩阵。点名使用 |
| 11 | sh-pwsh7-install | 装机：PowerShell 7 绿色版 ZIP 安装，零影响可卸干净。点名使用 |
| 12 | sh-pystand-pack | PyStand+嵌入式 Python 把 Python 项目打包成免安装绿色文件夹。点名使用 |
| 13 | sh-sql-query-builder | 重构 SOP：把 SQLAlchemy Core 嵌套只读查询抽取为文本 SQL 模板+builder，适用任意 Python 后端项目。点名使用 |
| 14 | sh-sublime-menu | 装机：Sublime 右键菜单添加/删除/检查，Win11 菜单样式切换。点名使用 |
| 15 | sh-video-transcribe | 视频/音频提取字幕并总结：ffmpeg 抽音轨→faster-whisper 本地转写 SRT/TXT→AI 总结。点名使用 |
| 16 | sh-web-archive | 公开网页存档为离线三 tab 页面（原文转录+AI 总结+可编辑），媒体本地化；仅限无鉴权页面。点名使用 |
| 17 | sh-zed-acp-agent-env | 排障：Zed ACP 外部 agent（antigravity/codex/claude/opencode）登录失败、代理/CA 不生效、改 env 不起效（旧进程复用）；附 stdio 认证探针。点名使用 |
| 18 | sh-zed-lsp-config | 配置：给项目目录配 Zed .zed/settings.json LSP 白名单，按项目开启省内存。点名使用 |
| 19 | sh-zed-lsp-install | 排障：Zed 语言服务器下载失败/rename os error 5；杀毒竞态根因+手工安装。点名使用 |
| 20 | sh-zed-opencode-setup | 配置：Zed 的 opencode agent 安装修复、思考档位、供应商配置、cc-switch 迁移。点名使用 |
| 21 | sh-zed-session-db | 排障：Zed 会话丢失/恢复/归档，直接查 SQLite sidebar_threads 表。点名使用 |
| 22 | sh-backend-design | 方法论：新功能/系统从需求分析到接口、表结构、工程结构设计。用户要设计新功能或分析新需求时使用；单点实现问题不用 |
| 23 | sh-tech-doc-writing | 方法论：写 PRD/技术方案/架构/排期等研发文档，读者视角、去 AI 味。用户要求写正式文档或抱怨文档质量时使用 |

不改动：sh-claude-plan-mode、sh-plan-driven-development、sh-spec-driven-development（延后）；lark-*/redis-* 等外部 skill（延后）。

## 任务分解

Task 1: 确认 git 回滚基线
  - 文件：无（仓库级操作）
  - 实现：确认 `~/.agents/skills` 工作区干净（落盘时已确认）；若有未提交变更则整体 commit 一次作快照
  - 验证：`git status --porcelain` 输出为空；否则记录快照 commit hash
  - Demo：明确回滚点，失败可 `git checkout -- .` 一键还原

Task 2: 重写 23 个 SKILL.md 的 description 行
  - 文件（相对 `~/.agents/skills/`，同一改动模式跨多文件，逐个替换 frontmatter 中 `description:` 单行，正文与其余 frontmatter 不动）：
    sh-atuin-pwsh-history/SKILL.md、sh-bruno-collection/SKILL.md、sh-cc-switch-db/SKILL.md、sh-chrome-devtools-mcp-setup/SKILL.md、sh-cluacpp-build/SKILL.md、sh-github-coexist/SKILL.md、sh-github-repo-cleanup/SKILL.md、sh-image-watermark-removal/SKILL.md、sh-lark-chat-archive/SKILL.md、sh-opencode-glm-auth/SKILL.md、sh-pwsh7-install/SKILL.md、sh-pystand-pack/SKILL.md、sh-sql-query-builder/SKILL.md、sh-sublime-menu/SKILL.md、sh-video-transcribe/SKILL.md、sh-web-archive/SKILL.md、sh-zed-acp-agent-env/SKILL.md、sh-zed-lsp-config/SKILL.md、sh-zed-lsp-install/SKILL.md、sh-zed-opencode-setup/SKILL.md、sh-zed-session-db/SKILL.md、sh-backend-design/SKILL.md、sh-tech-doc-writing/SKILL.md
  - 实现：按上表 23 条逐一替换；保持单行 YAML 格式，不引入换行
  - 验证：`git diff --stat` 显示恰好 23 个文件各 1 行增 1 行删；`git diff` 抽查 3 个确认只动 description 行
  - Demo：任选一个 skill 目录 cat SKILL.md，frontmatter 干净一行

Task 3: 全量校验
  - 文件：无（只读校验）
  - 实现：PowerShell 扫描全部 26 个 sh-*：description ≤1024 字符、不含"必须使用"与"也要触发"、frontmatter name 仍与目录名一致（未误改）
  - 验证：`$bad = Get-ChildItem "$env:USERPROFILE\.agents\skills" -Directory -Filter 'sh-*' | ForEach-Object { $raw = Get-Content (Join-Path $_.FullName 'SKILL.md') -Raw -Encoding UTF8; $name = if ($raw -match '(?m)^name:\s*(.+)$') { $Matches[1].Trim() }; $desc = if ($raw -match '(?m)^description:\s*(.+)$') { $Matches[1] }; [PSCustomObject]@{ dir=$_.Name; len=$desc.Length; badPhrase=($desc -match '必须使用|也要触发'); nameMismatch=($name -ne $_.Name) } } | Where-Object { $_.len -gt 1024 -or $_.badPhrase -or $_.nameMismatch }; $bad` 输出 0 行
  - Demo：空输出即全部合规

Task 4: evals 影响检查（只报告，不修改）
  - 文件：5 个带 evals/ 的 skill 目录下 eval 文件
  - 实现：grep eval 文件中按旧触发语言写的用例（含"必须使用/也要触发"或长触发短语），列出清单
  - 验证：`rg -l "必须使用|也要触发" --glob "evals/**"` 于 `~/.agents/skills` 输出受影响文件清单（含 lark-* 等非本轮范围的仅记录）
  - Demo：报告哪些 eval 用例会按设计失效，交用户决定是否延后批量更新

Task 5: 前后对比收尾
  - 文件：无（统计输出）
  - 实现：重跑 description 字符统计，输出 sh-* 合计与全目录合计
  - 验证：统计命令输出 sh-* 26 个合计 ≤2,600 字符（23 个新写 ~1,900 + 3 个 plan 三件套原样 ~1,307）
  - Demo：一屏前后对比数字（9,482 → 目标值），全目录 20,791 → ~13,300

## 延后积压（记录在案，本轮不动）

- plan 三件套处置（触发域重叠、合并或划界）
- lark-*/redis-* 等外部 skill description 压缩（~12k 字符）
- evals 用例按新 description 批量更新
- 未来 50+ skill 时路由器（mega-skill）试点

---
**最后更新：** 2026-09-21
**作者：** AI & User
**版本：** v1
