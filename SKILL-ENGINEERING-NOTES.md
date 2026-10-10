---
name: skill-engineering-notes
description: |
  工程实战手记、自动化流水线与避坑知识库 kb-engineering-notes/ 的入口与查阅协议：讲清知识库定位、两级渐进式感知架构（先读内部 SKILL-DRAFT.md 路由表，再读编号条目）与双轨条目扩充规范（Type A 疑难排障 + Type B 工程实现/生成流水线），并建立系统级坑位与方案查阅协议。当用户点名本文件、提到"工程手记/知识库/避坑指南"，或正在处理 Git 跨提交整理、变基 Permission denied 文件锁、Rescheduled 队列挂起、Cursor/VS Code 预览与 YOLO 沙箱配置、Git Worktree 依赖隔离、uv 统一 Python 环境、Antigravity 粘图快捷键与 Kitty 协议透传、计划任务触发终端闪标签页（控制台委托 handoff）与 conhost 无窗口注册、降噪耳机人声掩蔽与音频下载、AutoHotkey 窗口单手盲切、python-docx 试卷变式题生成与东亚字体排版、Sublime Text Terminus 中文退格失效与侧边栏 PowerShell 扩展等问题时，先读本文件定位条目。
version: 1.2.0
created: 2026-10-08
updated: 2026-10-10
---

# SKILL-ENGINEERING-NOTES：工程实战手记知识库入口

> 本文件是知识库专区 `kb-engineering-notes/` 的引导指针。它本身只负责"定位与分流"，**具体知识一律在编号条目里**——按需读取，不把正文搬进来。

## 一、知识库定位与核心价值

- **目录位置**：`~/.agents/skills/kb-engineering-notes/`（等价于 `.agents/skills/kb-engineering-notes/`）
- **定位**：长期生长的通用工程实战手记、自动化生成流水线与避坑知识库。区别于一次性的临时文档，这里沉淀的是真实开发中高成本踩坑、GUI/CLI 工具高阶交互、系统底层机制（文件锁、进程冲突、异常调度）、端到端工程自动化流水线（如教辅试卷生成、排版引擎、脚本集成），以及经过血泪验证的标准操作 SOP 与架构最佳实践。
- **排障与实现双翼（Type A / Type B）**：
  - **Type A（疑难排障型）**：针对操作系统底层、并发文件锁、网络/环境踩坑，遵循确定性抢救与防复发闭环；
  - **Type B（方案与生成流水线型）**：针对内容/文档/试卷批量自动化生成、脚手架与通用工程流水线，提供输入输出建模、核心代码模板与交付验证规范。
- **与正式 Skill 的关系**：
  - **当前状态**：知识库内部总控文件命名为 `SKILL-DRAFT.md`（非标准 `SKILL.md`），因此**不会被自动注册为活跃技能**，避免污染常规指令上下文——机制细节见 [SKILL-AUTHORING-RULES.md](file:///D:/Users/language_projects/.agents/skills/SKILL-AUTHORING-RULES.md) 第〇节；
  - **未来转正**：内部规范与元数据已 100% 遵循 `/skill-creator` 标准；若某天需要它被自动调用，只需把 `SKILL-DRAFT.md` 改名为 `SKILL.md` 即可生效。

## 二、两级渐进式感知：先路由，再读正文

知识库刻意分成两层，为的是"扫一眼就能判断要不要读"：

1. **第一级｜元数据与路由（`kb-engineering-notes/SKILL-DRAFT.md`）**：定义技能名称与 description、维护"问题 → 条目"的路由表，是**唯一权威索引**；
2. **第二级｜专项实战（`0N-` 编号条目）**：每个文件只深入解决一个核心痛点或交付方案，并自带 skill-creator 规范的 `name`/`description` frontmatter——即"条目即技能"的隐形形态，命名不改就永远不会被注册。

因此查阅顺序固定为：**本文件 → `SKILL-DRAFT.md` 路由表 → 命中的编号条目**。本文件第三节的清单只是速览，条目增删以 `SKILL-DRAFT.md` 为准，新增条目时不必须回来同步本表。

## 三、当前已收录条目速览

内部文档统一采用 **【编号 + 目标工具 + 核心问题场景 + 解决目标】** 的高信息密度命名，扫一眼文件名即可判断用途：

| 条目文件 | 核心解决场景 | 识别关键词 |
|:---|:---|:---|
| **[`01-SublimeMerge非相邻提交Squash合并与移动重排操作指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/01-SublimeMerge非相邻提交Squash合并与移动重排操作指南.md)** | 非相邻提交合并、拖拽不可用破局、Ctrl 多选合并、Move Down 重排、后台无感变基生效判定 | Sublime Merge, 跨提交合并, squash, fixup, 拖拽没反应 |
| **[`02-Windows下Git变基PermissionDenied文件锁排障与Abort安全恢复.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/02-Windows下Git变基PermissionDenied文件锁排障与Abort安全恢复.md)** | `logs/HEAD: Permission denied`、Windows 独占句柄锁根因、进程占用排查、`git rebase --abort` 安全回滚 | Permission denied, logs/HEAD, 变基文件锁, rebase abort, 暂存区抢救 |
| **[`03-Git变基Rescheduled队列挂起与暂存区冲突深度解析.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/03-Git变基Rescheduled队列挂起与暂存区冲突深度解析.md)** | `It has been rescheduled` 重调度机制、todo 队列混乱、变基暂停在中间 commit、避免重复 pick | rescheduled, git-rebase-todo, rebase挂起, onto commit |
| **[`04-CursorMarkdown预览独立标签页与侧边栏切换指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/04-CursorMarkdown预览独立标签页与侧边栏切换指南.md)** | Cursor/VS Code Markdown 预览默认侧边栏、想用独立标签页全屏查看、快捷键与 Alt 修饰键 | Markdown 预览, Ctrl+Shift+V, 侧边栏, 独立标签页, Open Preview |
| **[`05-Cursor免审批YOLO模式与沙箱网络配置指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/05-Cursor免审批YOLO模式与沙箱网络配置指南.md)** | Cursor Agent 免审批 YOLO 三档模式、总是弹窗根因、sandbox.json 网络管控 | Run Everything, YOLO, Auto-review, sandbox.json, networkPolicy, 批准 |
| **[`06-GitWorktree依赖复用与跨语言环境隔离权衡指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/06-GitWorktree依赖复用与跨语言环境隔离权衡指南.md)** | Git Worktree 隔离开发、依赖软链接可行性、两端冲突规避（Editable 源码倒挂/排他锁）与跨生态工程实践 | git worktree, 软链接, .venv, node_modules, target, editable 倒挂, WinError 32, sccache, pnpm, GOMODCACHE |
| **[`07-uv统一全机Python环境与新电脑一键引导复现指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/07-uv统一全机Python环境与新电脑一键引导复现指南.md)** | 多 Python 来源治理、uv_shim 全局转发架构、`UV_PYTHON` 锁版语义、PEP 668 / venv 无 pip 排坑、新电脑一键复现 SOP | uv, python, pip, uv_shim, UV_PYTHON, externally-managed, No module named pip, anaconda 卸载 |
| **[`08-Windows下Java与Maven便携子目录配置及Zed任务调试集成指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/08-Windows下Java与Maven便携子目录配置及Zed任务调试集成指南.md)** | Windows 下安装 Java/Maven 导致 C 盘膨胀、Zed 编辑器硬编码 JDK 路径或缺乏调试能力 | Java, Maven, C 盘空间, settings.xml, localRepository, Corretto, jdtls, tasks.json, JDWP, 远程调试 |
| **[`09-Chrome手动关闭窗口固定标签丢失的SNSS会话快照解析与找回指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/09-Chrome手动关闭窗口固定标签丢失的SNSS会话快照解析与找回指南.md)** | Chrome「继续浏览上次打开的网页」只恢复一个窗口，手动关闭窗口的固定标签丢失找回、独占锁规避与 SNSS 快照解析 | Chrome, 固定标签丢失, SNSS, TabRestoreService, Sessions, Session_, Tabs_ |
| **[`10-AntigravityCLI粘贴图片改键Windows终端Kitty协议透传与BOM排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/10-AntigravityCLI粘贴图片改键Windows终端Kitty协议透传与BOM排障指南.md)** | Antigravity CLI / Pi 粘贴图片快捷键改 Alt+Shift+V、Windows Terminal Kitty CSI-u 扩展协议透传、PowerShell 写入 UTF-8 BOM 报错排查 | 粘贴图片快捷键, edit.paste, app.clipboard.pasteImage, Alt+Shift+V, sendInput, 118;4u, Kitty CSI-u, ufeff, UTF-8 BOM, keybindings.json |
| **[`11-Windows计划任务控制台委托闪窗排障与conhost无窗口注册指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/11-Windows计划任务控制台委托闪窗排障与conhost无窗口注册指南.md)** | 计划任务/定时脚本触发时 Windows Terminal 闪空白 PowerShell 标签页（弹终端）、`-WindowStyle Hidden` 无效的排障；含 conhost --headless 无窗口注册与手动配置命令 | 弹终端, 闪窗, WT 标签页, 控制台委托, handoff, conhost --headless, PseudoConsoleWindow, register_task.ps1, 手动配置任务 |
| **[`12-AntigravityCLI执行模式辨析与免批YOLO及配置面板排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/12-AntigravityCLI执行模式辨析与免批YOLO及配置面板排障指南.md)** | Antigravity CLI 执行模式（plan/accept-edits）与免批 YOLO 权限辨析、状态栏无 yolo 认知重塑、/permissions 与 /config 面板排障、--dangerously-skip-permissions 启动参数 | Antigravity CLI, YOLO, accept-edits, plan, /permissions, /config, Tool Permission, --dangerously-skip-permissions |
| **[`13-降噪耳机人声泄露声学掩蔽与公有领域高音质音频下载实战指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/13-降噪耳机人声泄露声学掩蔽与公有领域高音质音频下载实战指南.md)** | 主动降噪耳机无法消除突发人声交谈、轻音乐休止符漏音痛点，利用听觉掩蔽（Auditory Masking）构建抗干扰声床；含 Wikimedia Commons API 免鉴权检索下载公有领域名曲与纯 Python 无依赖合成立体声褐噪音/雨声完整 SOP | 降噪耳机, 隔绝人声, 听觉掩蔽, 褐噪音, Brown Noise, 白噪音, 雨声, Wikimedia Commons, 公有领域轻音乐, 萨蒂, 肖邦, 卡农, 巴赫 |
| **[`14-Windows单手盲切与抽屉式Toggle应用窗口AutoHotkey配置指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/14-Windows单手盲切与抽屉式Toggle应用窗口AutoHotkey配置指南.md)** | Windows 常驻应用多（IDE/终端/浏览器/IM）、鼠标跨屏甩动疲劳、Alt+Tab 轮转顺序不稳定、PowerToys 快捷键误触冷启动 | AutoHotkey, AHK v2, 窗口切换, 盲切, 单手快捷键, Toggle, 前台置顶, 任务栏, PowerToys 缺陷 |
| **[`15-python-docx自动化生成举一反三试卷与格式精细排版指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/15-python-docx自动化生成举一反三试卷与格式精细排版指南.md)** | 基于 python-docx 的试卷与教辅「举一反三」变式题自动化生成与精细排版 SOP：原题考点映射、中西文字体分离(w:eastAsia)、行距间距设置、化学式上下标排版与批量生成流水线 | python-docx, 试卷生成, 举一反三, eastAsia, 宋体回退, 行距, 上下标, 批量生成流水线, Word 排版 |
| **[`16-SublimeTextTerminus中文退格失效与原生PowerShell侧边栏集成指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/16-SublimeTextTerminus中文退格失效与原生PowerShell侧边栏集成指南.md)** | Sublime Text 终端插件 Terminus 中文输入吞字/光标错位、Backspace 无法退格删除、右键侧边栏默认启动 CMD 假借 PowerShell 外壳的底层根因剖析，以及内置终端轻量化治愈与原生英文侧边栏一键拉起 Windows Terminal/PowerShell 的双轨集成实战 SOP | Sublime Text, Terminus, Backspace删不掉, 中文输入法, PSReadLine, Open Terminus here, Open PowerShell here, wt.exe |

## 四、AI 使用指引（当用户指定本文件或命中上述关键词时）

1. **建立全局认知**：确认存在 `kb-engineering-notes/` 知识库专区，并记住"路由在 `SKILL-DRAFT.md`、知识在编号条目"这一分层；
2. **场景分流**：
   - Git / Sublime Merge 提交整理与权限报错 → 直接读 `01-` ~ `03-`；
   - Cursor / VS Code 预览与 Agent 免审批、沙箱网络 → 读 `04-`、`05-`；
   - Git Worktree 依赖隔离、多 Python 环境统一、Java/Maven/Zed 便携集成 → 读 `06-`、`07-`、`08-`；
   - Chrome 会话丢失与固定标签抢救 → 读 `09-`；
   - 终端改键透传 / 计划任务弹窗闪退 → 读 `10-`、`11-`；
   - Antigravity CLI 执行模式与 YOLO 权限免审 → 读 `12-`；
   - 降噪耳机人声掩蔽与专注音乐/环境声下载合成 → 读 `13-`；
   - Windows 窗口单手盲切与 AHK v2 Toggle 自动化 → 读 `14-`；
   - python-docx 试卷与文档批量生成流水线、排版中文字体设置 → 读 `15-`；
   - Sublime Text Terminus 中文退格失效、侧边栏集成原生 PowerShell / WT → 读 `16-`；
   - 命中不明确时，先看 `SKILL-DRAFT.md` 的路由表再定；
3. **扩充新知识**：按 `SKILL-DRAFT.md` 第 3 节的规范，以 `0N-中文描述.md` 顺次新增条目（支持 Type A 排障型与 Type B 方案流水线型），并更新内部路由表；
4. **外部解耦原则**：知识库为自治生长体系，全量索引唯一维护在 `kb-engineering-notes/SKILL-DRAFT.md`。外部分流器（如 `sh-user-skills` 及 `sh-engineering-notes`）一律采用领域定性描述，严禁绑定条目总数或静态区间；新增条目无需向上同步修改父级描述；
5. **要求转正为自动技能时**：执行 `git mv kb-engineering-notes/SKILL-DRAFT.md kb-engineering-notes/SKILL.md`。

---

**最后更新：** 2026-10-10
