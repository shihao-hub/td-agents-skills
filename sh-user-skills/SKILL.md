---
name: sh-user-skills
description: |
  个人技能库总入口与分流器：用户只有一句模糊需求、或忘记技能名时，在此按关键词匹配并加载对应子技能 SOP。覆盖五域：
  工程手记与避坑知识库（sh-engineering-notes 渐进式检索 kb-engineering-notes/ 38项单点排障/底层锁机制/环境配置）；
  开发与重构（后端系统设计、计划模式与计划/规格驱动、OOP 重构、SQL 模板 builder、C/C++/Lua 构建、前端去 AI 味、localhost PWA、Bruno 集合、Codex 插件、PyStand 打包、monorepo 提交推送、GitHub 仓库大扫除）；
  文档与交接（PRD/技术方案、书转 skill、跨 agent 交接、排障复盘）；
  检索与媒资归档（Everything 秒搜、抖音/B站/知乎下载、视频转写字幕、去水印、Office 提图、网页存档、飞书聊天与会话归档）；
  另有飞书、Redis/Iris、antigravity 三个族路由器；用户直接点名 `sh-*` 子技能（含拼写近似）时也由本入口解析；用户问“有哪些技能/技能库”时列出完整清单。
version: 1.1.0
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
   - **知识库总控路由**（`sh-engineering-notes`）：用户遇到底层报错、声卡/网络/内存排障、IDE 崩溃或环境配置时，载入 `sh-user-skills/sh-engineering-notes/README.md`，按两级渐进式感知协议查阅 `kb-engineering-notes/SKILL-DRAFT.md`；
   - **独立族路由器**（`sh-agy-skills`、`sh-lark-skills`、`sh-redis-skills`）：位于父级同级目录，按对应 `SKILL.md` 协议二次分流；
   - **收拢子技能**：均已收拢存放在本技能子目录中，且核心指导文件统一为 `README.md`（避免被 Agent 全局递归探测）。执行时，AI 使用 `view_file` 直接读取 `sh-user-skills/<skill-name>/README.md` 全文并严格按其 SOP 步骤执行。

### 🗣️ 口语说法 → 技能速查（优先命中）

| 用户口语说法（示例） | 技能 |
| :--- | :--- |
| 底层报错／排障手记／查阅避坑知识库／声卡爆音／代理下UWP打不开／C盘空间清理／内存防死机／GLM 401／Zed崩溃与LSP排障／多Git账号共存／Atuin历史丢失／VSCode搬插件 | `sh-engineering-notes`（两级渐进式检索 `kb-engineering-notes/`） |
| 把视频/音频转成字幕 | `sh-video-transcribe` |
| 抖音/B站无水印下载、知乎文章存 Markdown | `sh-zhangshihao-douyin-dl` |
| 图片去水印／去角标 | `sh-image-watermark-removal` |
| 从 PPT/Word 里抠出原图 | `sh-office-extract-media` |
| 网页存档／离线保存网页 | `sh-web-archive` |
| 飞书群聊记录导出成 HTML | `sh-lark-chat-archive` |
| 把这轮对话归档到飞书文档 | `sh-lark-session-doc` |
| 全盘找某个文件／找大文件 | `sh-everything-search` |
| 写 PRD／技术方案／排期 | `sh-tech-doc-writing` |
| 复盘一下你刚才定为排障的过程 | `sh-troubleshooting-recap` |
| 换一个 agent 接着做／交接 | `sh-agent-handoff` |
| 提交并推送这个 monorepo／submodule | `sh-monorepo-commit-push` |
| GitHub 仓库太多要清理/备份 | `sh-github-repo-cleanup` |
| 把本地服务改成独立窗口应用/PWA | `sh-localhost-pwa` |
| 页面一股 AI 味／重新设计界面 | `sh-frontend-deai` |
| 给接口生成 Bruno 测试集合 | `sh-bruno-collection` |
| 创建 Codex 插件目录与 manifest | `sh-codex-plugin-creator` |
| Python 项目打包成免安装绿色版 | `sh-pystand-pack` |
| C++ 编译报错／CMake 集成 Lua | `sh-cluacpp-build` |
| 把这个能力沉淀成 skill／书转 skill | `sh-book2skill-sop`（书/文档）或 `skill-creator` |
| 只读规划探索／方案获批后再写代码 | `sh-claude-plan-mode` 或 `sh-plan-driven-development` |

### ⚡ 领域技能族路由器（二级分流）

| 技能名称 | 核心职责与功能（一句话） |
| :--- | :--- |
| `sh-agy-skills` | antigravity 斜杠命令技能族路由器：点名使用后，按用户后续内容自动分流到子目录 skill（goal/schedule/browser/grill-me/teamwork/learn/boost/plan）。点名使用 |
| `sh-lark-skills` | 飞书全域技能族路由器：集成飞书 28 域原生能力（IM、文档、表格、多维表格、审批、任务、邮件、日历、会议、妙记等）。点名使用 |
| `sh-redis-skills` | Redis 与 Iris 全域技能族路由器：集成 Redis 官方核心建模、连接池、集群分片、全文/向量检索、监控排障与 Iris AI 长短期记忆库。点名使用 |

### 📚 工程手记与排障避坑知识库导航

| 技能名称 | 核心职责与功能（一句话） |
| :--- | :--- |
| `sh-engineering-notes` | 知识库：工程实战手记与避坑知识库 kb-engineering-notes/ 渐进式检索分流器（涵盖01~38项系统排障与底层机制）。点名使用 |

### 🏗️ 系统设计与工程开发

| 技能名称 | 核心职责与功能（一句话） |
| :--- | :--- |
| `sh-backend-design` | 后端系统设计：从需求分析到接口契约、表结构与工程分层全流程。点名使用 |
| `sh-plan-driven-development` | 轻量规划执行工作流：澄清需求、调研并落盘单文件实施计划，获批后连续执行。点名使用 |
| `sh-spec-driven-development` | Spec 驱动开发工作流：按 feature/bug 分流产出需求设计与任务清单，逐份获批后执行。点名使用 |
| `sh-claude-plan-mode` | 非平凡开发任务的计划模式：只读探索与澄清，方案获批后再实施。点名使用 |
| `sh-oop-refactor` | 运用 OOP 思想与设计模式重构项目：代码坏味道诊断、接缝测试、架构方案到小步执行。点名使用 |
| `sh-sql-query-builder` | 重构 SOP：把 SQLAlchemy Core 嵌套只读查询抽取为文本 SQL 模板+builder。点名使用 |
| `sh-cluacpp-build` | C/C++/Lua 项目工具链与构建手册：LLVM/Ninja/MSVC、CMake Presets、FetchContent 集成 Lua。点名使用 |
| `sh-localhost-pwa` | 本地 Web/CLI 服务改造为 Chrome/Edge 独立应用窗口（--app 模式）与 PWA 规范面板。点名使用 |
| `sh-frontend-deai` | 前端去 AI 味：反蓝紫渐变、暗底霓虹与模板化套路，场景导向设计界面。点名使用 |
| `sh-bruno-collection` | 为 HTTP 接口生成 Bruno API 测试集合（.bru）。点名使用 |
| `sh-codex-plugin-creator` | 脚手架创建 Codex 插件目录、manifest 与个人市场条目，含校验和更新流程。点名使用 |
| `sh-pystand-pack` | PyStand+嵌入式 Python 把 Python 项目打包成免安装绿色文件夹。点名使用 |
| `sh-monorepo-commit-push` | Monorepo 与 git submodule 项目逐项审查、提交并推送。点名使用 |
| `sh-github-repo-cleanup` | GitHub 仓库大扫除：审计→fork 转 Star→mirror 备份→批量删除/归档。点名使用 |

### 📖 技能沉淀与技术文档

| 技能名称 | 核心职责与功能（一句话） |
| :--- | :--- |
| `sh-book2skill-sop` | 把书/文档转成 agent skill：book-to-skill 全流程 SOP、扫描版 OCR 兜底与本机坑位速查。点名使用 |
| `sh-tech-doc-writing` | 技术文档写作：读者视角撰写 PRD、技术方案、架构与排期等研发文档。点名使用 |
| `sh-agent-handoff` | 跨 agent 会话交接：生成交接简报文件并给出路径，另一 agent 按路径接手继续。点名使用 |

### 🛠️ 全盘检索、多媒体与离线归档

| 技能名称 | 核心职责与功能（一句话） |
| :--- | :--- |
| `sh-everything-search` | 全盘/跨盘文件秒搜（Everything es.exe 一次性查询，查完即退）。点名使用 |
| `sh-zhangshihao-douyin-dl` | 本机抖音/B 站视频下载 + 知乎文章提取为 Markdown 与本地原图。点名使用 |
| `sh-video-transcribe` | 视频/音频提取字幕并总结：ffmpeg 抽音轨→faster-whisper 本地转写 SRT/TXT→AI 总结。点名使用 |
| `sh-image-watermark-removal` | 去水印/角标：PIL+numpy 局部修补，擅长水印压在图案笔画上的复杂情形。点名使用 |
| `sh-office-extract-media` | 提取 Word/PPT/Excel 内嵌原图：改后缀为 zip 进 media 目录取图。点名使用 |
| `sh-web-archive` | 公开网页存档为离线三 tab 页面（原文转录+AI 总结+可编辑），媒体本地化。点名使用 |
| `sh-lark-chat-archive` | 飞书聊天记录归档为单文件 HTML（私聊/群聊/话题，纸面排版+图注+lightbox）。点名使用 |
| `sh-lark-session-doc` | 用户提到把当前会话/对话导出或归档为飞书云文档时使用。点名使用 |
| `sh-troubleshooting-recap` | 排障复盘：把一次排障/解题过程按「做了什么 → 怎么想的 → 在哪碰壁 → 怎么解决」四段精炼呈现。点名使用 |
