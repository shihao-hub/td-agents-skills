---
name: sh-user-skills
description: |
  个人技能库总入口与分流器：用户只有一句模糊需求、或忘记技能名时，在此按关键词匹配并加载对应子技能 SOP。覆盖五域：
  装机与环境（PowerShell7 绿色安装、uv/Python 环境统一、atuin 命令历史、多 Agent 终端与 Git Bash、内存防死机/虚拟内存/提交内存归因/内存条扩容判断、pi 快捷键与滚轮、终端字体、Sublime 右键菜单、VS Code 提交图与插件搬运、Zed LSP 白名单与 opencode 配置、chrome-devtools-mcp、Antigravity CLI YOLO与权限策略）；
  排障（C 盘空间不足、声卡无声/爆音、代理下 UWP 与商店、Zed 语言服务器下载失败、ACP 登录与代理、Agent Panel 报错、Zed 会话丢失、GLM 401）；
  开发与重构（后端系统设计、计划模式与计划/规格驱动、OOP 重构、SQL 模板 builder、C/C++/Lua 构建、前端去 AI 味、localhost PWA、Bruno 集合、Codex 插件、PyStand 打包、monorepo 提交推送、GitHub 仓库大扫除、GitHub/GitLab 共存、cc-switch 供应商读写）；
  文档与交接（PRD/技术方案、书转 skill、跨 agent 交接、排障复盘）；
  检索与媒资归档（Everything 秒搜、抖音/B站/知乎下载、视频转写字幕、去水印、Office 提图、网页存档、飞书聊天与会话归档）；
  另有飞书、Redis/Iris、antigravity 三个族路由器；用户直接点名 `sh-*` 子技能（含拼写近似）时也由本入口解析；用户问“有哪些技能/技能库”时列出完整清单。
version: 1.0.0
created: 2026-10-07
updated: 2026-10-10
---

# sh-user-skills：个人技能库总目录与分流导航

> 本技能是 `sh-*` 个人技能体系的**顶层总入口与单一真理服务台**。
> 当您**忘记具体技能名称**，或**只有一句模糊需求**时，直接呼叫本技能即可。

## 交互与分流协议

1. **裸呼叫（未带具体任务）**：
   - 用户仅唤起 `sh-user-skills` 或 “查看我的技能” 时，**完整呈现下方分类索引表**，告知用户可直接点名或指定目标。
2. **带意图呼叫（带有一句模糊需求）**：
   - 用户输入 `sh-user-skills <需求>` 时，AI 查阅下表匹配最契合的 **1~2 个专属技能**，给出推荐理由，并向用户确认或直接载入执行：
     - **唯一高置信匹配** → 告知用户并载入对应技能文档开始执行；
     - **多候选匹配** → 列出候选及对比依据，供用户点名确认。
3. **文件寻址与加载规则**：
   - **独立族路由器**（`sh-agy-skills`、`sh-lark-skills`、`sh-redis-skills`）：位于父级同级目录，按对应 `SKILL.md` 协议二次分流；
   - **收敛子技能**（其他全部 49 个技能）：均已收敛存放在本技能子目录中，且核心指导文件已统一改别名为 `README.md`（避免被 Agent 全局递归探测）。执行时，AI 使用 `view_file` 直接读取 `sh-user-skills/<skill-name>/README.md` 全文并严格按其 SOP 步骤执行。
   - **名字兜底**：用户点名的 `sh-*` 名不在下方表格、或只有拼写近似时，**不要放弃**——直接列出 `sh-user-skills/` 子目录做模糊匹配（`ls sh-user-skills/` 或 `rg --files sh-user-skills -g 'README.md'`），按语义最接近的目录读其 `README.md`。

### 🗣️ 口语说法 → 技能速查（优先命中）

用户往往只会说症状或任务，不会说技能名；先查本表，命中即直接读对应 `README.md` 执行。

| 用户口语说法（示例） | 技能 |
| :--- | :--- |
| 喇叭没声音／嗡嗡爆音／默认声卡被抢 | `sh-windows-audio-diagnose` |
| C 盘满了／空间不够／想清理 C 盘 | `sh-disk-space-cleanup` |
| 开着代理时商店打不开／UWP 不能联网 | `sh-uwp-proxy-loopback` |
| Zed 装不上语言服务器／rename os error 5 | `sh-zed-lsp-install` |
| Zed 里 agent 登录失败／改了 env 不生效 | `sh-zed-acp-agent-env` |
| Agent Panel 报 Internal error／Session is closing | `sh-zed-agent-triage` |
| Zed 越用越占内存／agent 进程攒了十几个 | `sh-zed-acp-agent-env` |
| Zed 的会话/对话找不到了 | `sh-zed-session-db` |
| opencode 连 GLM 报 401 | `sh-opencode-glm-auth` |
| 电脑卡死／内存爆了／加虚拟内存／没开什么软件但内存很高／该不该加内存条 | `sh-windows-memory-guard` |
| 装个 PowerShell 7／pwsh | `sh-pwsh7-install` |
| Python 环境太乱／卸 anaconda／用 uv 装包 | `sh-uv-python-env` |
| 命令历史丢了／Ctrl+r 搜不了历史 | `sh-atuin-pwsh-history` |
| 终端里乱码／让 agent 走 Git Bash | `sh-windows-agent-shell` |
| pi 里改快捷键／滚轮翻历史 | `sh-pi-keybindings` |
| 个人 GitHub 和公司 GitLab 打架 | `sh-github-coexist` |
| 给某个项目单独开 Zed 的 LSP | `sh-zed-lsp-config` |
| 把视频/音频转成字幕 | `sh-video-transcribe` |
| 抖音/B站无水印下载、知乎文章存 Markdown | `sh-zhangshihao-douyin-dl` |
| 图片去水印／去角标 | `sh-image-watermark-removal` |
| 从 PPT/Word 里抠出原图 | `sh-office-extract-media` |
| 网页存档／离线保存网页 | `sh-web-archive` |
| 飞书群聊记录导成 HTML | `sh-lark-chat-archive` |
| 把这轮对话归档到飞书文档 | `sh-lark-session-doc` |
| 全盘找某个文件／找大文件 | `sh-everything-search` |
| 写 PRD／技术方案／排期 | `sh-tech-doc-writing` |
| 复盘一下你刚才是怎么定位的 | `sh-troubleshooting-recap` |
| 换一个 agent 接着做／交接 | `sh-agent-handoff` |
| 提交并推送这个 monorepo／submodule | `sh-monorepo-commit-push` |
| GitHub 仓库太多要清理/备份 | `sh-github-repo-cleanup` |
| 换个供应商／读 cc-switch 配置 | `sh-cc-switch-db` |
| 把本地服务改成独立窗口应用/PWA | `sh-localhost-pwa` |
| 页面一股 AI 味／重新设计界面 | `sh-frontend-deai` |
| 给接口生成 Bruno 测试集合 | `sh-bruno-collection` |
| Python 项目打包成免安装绿色版 | `sh-pystand-pack` |
| C++ 编译报错／CMake 集成 Lua | `sh-cluacpp-build` |
| 把这个能力沉淀成 skill／书转 skill | `sh-book2skill-sop`（书/文档）或 `skill-creator` |
| antigravity cli 没有 yolo／cli 只有 plan 和 accept／agy permissions 怎么配 | `sh-agy-cli-permissions` |

### ⚡ 领域技能族路由器（二级分流）
涉及特定垂直生态（Antigravity、飞书、Redis）时，由族路由器进一步按 8~28 个子领域精准下发：

| 技能名称 | 核心职责与功能（一句话） |
| :--- | :--- |
| `sh-agy-skills` | antigravity 斜杠命令技能族路由器：点名使用后，按用户后续内容自动分流到子目录 skill（goal/schedule/browser/grill-me/teamwork/learn/boost/plan）。不确定时列候选向用户确认。本 skill 自身不执行任务，只做指引分流 |
| `sh-lark-skills` | 飞书全域技能族路由器：集成飞书 28 域原生能力（IM、文档、表格、多维表格、审批、任务、邮件、日历、会议、妙记等），按用户意图精准分流加载对应子模块。当涉及任何飞书操作时点名或自动路由使用。 |
| `sh-redis-skills` | Redis 与 Iris 全域技能族路由器：集成 Redis 官方核心建模、连接池、集群分片、全文/向量检索、监控排障、生产安全、语义缓存以及 Iris AI 智能体长短期记忆库。按用户意图精准分流加载对应子模块。 |

### 💻 系统装机与环境配置
用于系统级软件、Shell、终端工具、Python/C++ 环境与 IDE 插件安装及配置：

| 技能名称 | 核心职责与功能（一句话） |
| :--- | :--- |
| `sh-pwsh7-install` | 装机：PowerShell 7 绿色版 ZIP 安装，零影响可卸干净。点名使用 |
| `sh-uv-python-env` | uv 统一管理 Python 环境——全局 python/pip 走专用 venv，uv 默认锁 3.12.5，卸载 anaconda/多 python。点名使用 |
| `sh-atuin-pwsh-history` | 装机/排障：Windows atuin 命令历史配置与 profile 修复（hh、Ctrl+r、上下键召回）。点名使用 |
| `sh-windows-agent-shell` | 配置：Windows 多 Agent（Codex/Claude/OpenCode/Pi/AGY）终端机制与 Git Bash 切换。点名使用 |
| `sh-windows-memory-guard` | 配置/排障：Windows 内存过载防死机、虚拟内存(Pagefile)扩容调优、提交内存归因（揪出只占提交不占物理的换出冷数据）与内存条扩容判断。点名使用 |
| `sh-pi-keybindings` | 配置：pi 快捷键改键、终端按键协议排障与滚轮变输入历史修复。点名使用 |
| `sh-github-coexist` | 装机：个人 GitHub 与公司 GitLab 共存，SSH key+includeIf 身份自动切换+批量推仓库。点名使用 |
| `sh-chrome-devtools-mcp-setup` | 装机：opencode 配置 chrome-devtools-mcp 浏览器控制。点名使用 |
| `sh-sublime-font` | 装机/配置：YaHei Consolas Hybrid 字体下载安装，Sublime Text/Merge 字体配置及 UI 补丁。点名使用 |
| `sh-sublime-menu` | 装机：Sublime 右键菜单添加/删除/检查，Win11 菜单样式切换。点名使用 |
| `sh-vscode-gitlg-panel` | 配置：VS Code 底部面板 Git 提交图（GitLG/IDEA体验）与分支颜色调优。点名使用 |
| `sh-vscode-fork-ext-port` | 把 VS Code 系插件/扩展跨分支 IDE 手工搬运并注册生效（Cursor/Antigravity IDE/Trae）。点名使用 |
| `sh-zed-lsp-config` | 配置：给项目目录配 Zed .zed/settings.json LSP 白名单，按项目开启省内存。点名使用 |
| `sh-zed-opencode-setup` | 配置：Zed 的 opencode agent 安装修复、思考档位、供应商配置、cc-switch 迁移。点名使用 |
| `sh-agy-cli-permissions` | 配置：Antigravity CLI 执行模式（plan/accept）辨析、YOLO 免审与 Tool Permission 配置。点名使用 |

### 🔧 系统与运行排障
磁盘、网络代理、声卡、模型鉴权、IDE 崩溃与会话丢失诊断：

| 技能名称 | 核心职责与功能（一句话） |
| :--- | :--- |
| `sh-disk-space-cleanup` | 排障：C 盘空间不足排查与清理（空间去向扫描、Temp/缓存/WSL 等安全释放，以移代删与软链接/环境变量重定向）。点名使用 |
| `sh-windows-audio-diagnose` | 排障：Windows 喇叭无声/嗡嗡爆音/默认输出被虚拟声卡抢占的排查与修复。点名使用 |
| `sh-uwp-proxy-loopback` | 排障：Windows 代理下微软商店与 UWP 初始化失败/无法联网，CheckNetIsolation 回环豁免。点名使用 |
| `sh-opencode-glm-auth` | 排障：opencode 连 GLM 报 401/身份验证失败；apiKey 优先级、双端点 key 矩阵。点名使用 |
| `sh-zed-lsp-install` | 排障：Zed 语言服务器下载失败/rename os error 5；杀毒竞态根因+手工安装。点名使用 |
| `sh-zed-acp-agent-env` | 排障：IDE（Zed/IntelliJ IDEA）ACP 外部 agent（antigravity/codex/claude）登录失败、代理/CA 不生效、旧进程复用、子进程池累积吃内存；附 stdio 认证探针。点名使用 |
| `sh-zed-agent-triage` | 排障：Zed Agent Panel 报 Internal error/Invalid request/Session is closing 等 agent 侧错误的定位归因：telemetry.log 事件定位 agent 与线程、Zed.log 拿绝对时间、进程 StartTime 与锁文件时间线对齐；含 codex-acp thread-writer-lock 竞态速查与 agent 子进程池膨胀排查。点名使用 |
| `sh-zed-session-db` | 排障：Zed 会话丢失/恢复/归档，直接查 SQLite sidebar_threads 表。点名使用 |
| `sh-troubleshooting-recap` | 排障复盘：把一次排障/解题过程按「做了什么 → 怎么想的 → 在哪碰壁 → 怎么解决」四段精炼呈现。当用户要求复盘、想听定位过程，或问"你怎么思考、怎么碰壁、怎么解决的"时使用。点名使用 |

### 🏗️ 系统设计与工程开发
后端架构、规划执行、代码重构、编译构建与应用桌面化：

| 技能名称 | 核心职责与功能（一句话） |
| :--- | :--- |
| `sh-backend-design` | 后端系统设计：从需求分析到接口契约、表结构与工程分层全流程。点名使用 |
| `sh-plan-driven-development` | 轻量规划执行工作流：澄清需求、调研并落盘单文件实施计划，获批后连续执行。点名使用 |
| `sh-spec-driven-development` | Spec 驱动开发工作流：按 feature/bug 分流产出需求设计与任务清单，逐份获批后执行。点名使用 |
| `sh-claude-plan-mode` | 非平凡开发任务的计划模式：只读探索与澄清，方案获批后再实施。点名使用 |
| `sh-oop-refactor` | 运用 OOP 思想与设计模式重构项目：代码坏味道诊断、接缝测试、架构方案到小步执行。点名使用 |
| `sh-sql-query-builder` | 重构 SOP：把 SQLAlchemy Core 嵌套只读查询抽取为文本 SQL 模板+builder，适用任意 Python 后端项目。点名使用 |
| `sh-cluacpp-build` | C/C++/Lua 项目工具链与构建手册：LLVM/Ninja/MSVC、CMake Presets、FetchContent 集成 Lua、clangd、编译报错速查。点名使用 |
| `sh-localhost-pwa` | 本地 Web/CLI 服务改造为 Chrome/Edge 独立应用窗口（--app 模式）与 PWA 规范面板。点名使用 |
| `sh-frontend-deai` | 前端去 AI 味：反蓝紫渐变、暗底霓虹与模板化套路，场景导向设计界面。点名使用 |
| `sh-bruno-collection` | 为 HTTP 接口生成 Bruno API 测试集合（.bru）。点名使用 |
| `sh-codex-plugin-creator` | 脚手架创建 Codex 插件目录、manifest 与个人市场条目，含校验和更新流程。点名使用 |
| `sh-pystand-pack` | PyStand+嵌入式 Python 把 Python 项目打包成免安装绿色文件夹。点名使用 |
| `sh-monorepo-commit-push` | Monorepo 与 git submodule 项目逐项审查、提交并推送。点名使用 |
| `sh-github-repo-cleanup` | GitHub 仓库大扫除：审计→fork 转 Star→mirror 备份→批量删除/归档。点名使用 |

### 📚 技能沉淀与技术文档
书转技能、会话跨 Agent 交接、PRD 与技术方案撰写、供应商配置：

| 技能名称 | 核心职责与功能（一句话） |
| :--- | :--- |
| `sh-book2skill-sop` | 把书/文档转成 agent skill：book-to-skill 全流程 SOP、扫描版 OCR 兜底与本机坑位速查。点名使用 |
| `sh-tech-doc-writing` | 技术文档写作：读者视角撰写 PRD、技术方案、架构与排期等研发文档。点名使用 |
| `sh-agent-handoff` | 跨 agent 会话交接：生成交接简报文件并给出路径，另一 agent 按路径接手继续。点名使用；用户贴出「sh-agent-handoff: <路径>」或提到接管交接简报时即接管侧点名，必须走本 skill 完成状态检查与回写打标 |
| `sh-cc-switch-db` | 直接读写 cc-switch SQLite，绕过 UI 配置各应用供应商。点名使用 |

### 🛠️ 全盘检索、多媒体与离线归档
秒搜全盘、抖音/B站/知乎内容抓取、音视频转写、去水印与网页/飞书归档：

| 技能名称 | 核心职责与功能（一句话） |
| :--- | :--- |
| `sh-everything-search` | 全盘/跨盘文件秒搜（Everything es.exe 一次性查询，查完即退）：按文件名、扩展名、大小、修改时间、正则定位文件，支持计数与 JSON/CSV 导出。当任务要在整个磁盘或跨盘范围找文件时使用（全盘搜索、找大文件、找最近改动的文件、不记得放哪的文件、磁盘清理候选）；仓内找文件或搜文件内容用 rg/glob，不用本 skill。 |
| `sh-zhangshihao-douyin-dl` | 本机抖音/B 站视频下载 + 知乎文章提取：用本机打包好的 douyin_dl.exe（Nuitka 产物，路径仅在本机 ZHANGSHIHAO 有效）下载抖音无水印视频、B 站视频（含多 P），并把知乎回答/专栏文章提取为 Markdown + 本地原图。用户提到抖音分享文案、无水印下载、BV 号/b23.tv/bilibili 链接、知乎回答或专栏文章提取/存成 Markdown 时使用。点名使用 |
| `sh-video-transcribe` | 视频/音频提取字幕并总结：ffmpeg 抽音轨→faster-whisper 本地转写 SRT/TXT→AI 总结。点名使用 |
| `sh-image-watermark-removal` | 去水印/角标：PIL+numpy 局部修补，擅长水印压在图案笔画上的复杂情形。点名使用 |
| `sh-office-extract-media` | 提取 Word/PPT/Excel 内嵌原图：改后缀为 zip 进 media 目录取图。点名使用 |
| `sh-web-archive` | 公开网页存档为离线三 tab 页面（原文转录+AI 总结+可编辑），媒体本地化；仅限无鉴权页面。点名使用 |
| `sh-lark-chat-archive` | 飞书聊天记录归档为单文件 HTML（私聊/群聊/话题，纸面排版+图注+lightbox）。点名使用 |
| `sh-lark-session-doc` | 用户提到把当前会话/对话导出或归档为飞书云文档时使用，直接原封不动存入个人文档库；非导出当前会话或要导出本地已有文件时不使用 |

---
## 维护规则
- 每次新建或重构 `sh-*` 技能后，须在此分类表中同步登记一行；
- 保持各技能一句话职责明确，便于模糊检索与语义定位。