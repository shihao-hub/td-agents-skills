---
name: kb-engineering-notes
description: 开发者通用工程实战手记、自动化流水线与硬核排障知识库。兼具「疑难排障（Windows 文件锁、进程池堆积、闪窗、网络代理）」与「工程实现/生成流水线（文档与试卷自动化排版、脚手架、复杂脚本设计）」两翼实战 SOP。当遇到疑难报错或需要落地工程自动化流水线时查阅本指南。
---

# 工程实战手记与疑难排障知识库 (Engineering Notes Playbook)

> **注意（隔离与转正说明）**：
> 本文件当前命名为 `SKILL-DRAFT.md`，用于确保在草稿与沉淀阶段**不被外部 Agent 自动注册为活跃技能**。
> 本文件架构完全遵循 `/skill-creator` 规范，未来转正只需执行：
> `git mv SKILL-DRAFT.md SKILL.md`

---

## 1. 知识库架构与设计哲学

本知识库采用**两级渐进式感知架构（Two-stage Progressive Disclosure）**，涵盖**疑难排障（Type A）**与**工程方案/自动化生成流水线（Type B）**两翼：

```text
kb-engineering-notes/
├── SKILL-DRAFT.md                                    # [Stage 1: 元数据与路由总纲] 本文件，负责总览与场景分流
├── 01-SublimeMerge非相邻提交Squash合并与移动重排操作指南.md # [Stage 2: 专项实战] 针对 GUI 提交合并
├── 02-Windows下Git变基PermissionDenied文件锁排障与Abort安全恢复.md # [Stage 2: 专项排障] 针对权限锁与抢救
├── 03-Git变基Rescheduled队列挂起与暂存区冲突深度解析.md # [Stage 2: 专项机制] 针对队列重调度与避坑
├── 04-CursorMarkdown预览独立标签页与侧边栏切换指南.md # [Stage 2: 专项技巧] 针对编辑器 Markdown 预览模式
├── 05-Cursor免审批YOLO模式与沙箱网络配置指南.md # [Stage 2: 专项配置] 针对 Agent 免审批自动运行与网络管控
├── 06-GitWorktree依赖复用与跨语言环境隔离权衡指南.md # [Stage 2: 专项权衡] 针对 Worktree 依赖共享与跨语言环境隔离
├── 07-uv统一全机Python环境与新电脑一键引导复现指南.md # [Stage 2: 专项环境] 针对多 Python 来源统一与新机一键复现
├── 08-Windows下Java与Maven便携子目录配置及Zed任务调试集成指南.md # [Stage 2: 专项配置] 针对 Java/Maven 便携隔离、C 盘防膨胀与 Zed 任务调试
├── 09-Chrome手动关闭窗口固定标签丢失的SNSS会话快照解析与找回指南.md # [Stage 2: 专项抢救] 针对 SNSS 快照解析、独占锁规避与丢失窗口/固定标签找回
├── 10-AntigravityCLI粘贴图片改键Windows终端Kitty协议透传与BOM排障指南.md # [Stage 2: 专项配置] 针对 CLI 粘贴图片改键、Windows Terminal 扩展协议与 UTF-8 BOM 报错
├── 11-Windows计划任务控制台委托闪窗排障与conhost无窗口注册指南.md # [Stage 2: 专项排障] 针对计划任务触发 WT 标签页闪窗（控制台委托 handoff）与无窗口任务手动注册
├── 12-AntigravityCLI执行模式辨析与免批YOLO及配置面板排障指南.md # [Stage 2: 专项配置] 针对 CLI 执行模式、YOLO 权限免审批与配置面板
├── 13-降噪耳机人声泄露声学掩蔽与公有领域高音质音频下载实战指南.md # [Stage 2: 专项实战] 针对降噪耳机人声泄露掩蔽、Commons API 下载与纯 Python 音频合成
├── 14-Windows单手盲切与抽屉式Toggle应用窗口AutoHotkey配置指南.md # [Stage 2: 专项效率] 针对 Windows 多常驻窗口盲切、左手单手 Toggle 与 AutoHotkey v2 自动化
├── 15-python-docx自动化生成举一反三试卷与格式精细排版指南.md # [Stage 2: 专项实现] 针对教辅试卷生成、东亚字体分离(w:eastAsia)与 python-docx 精细排版流水线
├── 16-SublimeTextTerminus中文退格失效与原生PowerShell侧边栏集成指南.md # [Stage 2: 专项排障] 针对 Sublime 内置终端退格失效/中文吞字根因与原生侧边栏 PowerShell 扩展
├── 17-Windows声卡爆音无声与虚拟音频抢占排查指南.md # [Stage 2: 专项排障] 针对设备占用、默认输出抢占与修复
├── 18-Windows代理下微软商店与UWP回环网络豁免排障指南.md # [Stage 2: 专项排障] 针对 CheckNetIsolation 回环豁免
├── 19-Windows内存防死机与Pagefile提交内存归因优化指南.md # [Stage 2: 专项排障] 针对 Pagefile 调优与 Commit 归因
├── 20-Windows系统C盘空间不足排查与安全清理软链接重定向指南.md # [Stage 2: 专项排障] 针对 C 盘清理与环境变量重定向
├── 21-opencode连接GLM模型401鉴权失败与端点排障指南.md # [Stage 2: 专项排障] 针对 GLM 401 报错与 key 映射
├── 22-Zed语言服务器下载失败文件重命名占用与杀毒竞态排障指南.md # [Stage 2: 专项排障] 针对 LSP 下载失败与文件独占锁
├── 23-Zed与IDEA外接ACP代理环境失效与子进程池累积排查指南.md # [Stage 2: 专项排障] 针对 ACP 子进程池堆积与代理失效
├── 24-Zed面板InternalError会话中断与ACP线程锁竞态归因指南.md # [Stage 2: 专项排障] 针对 Panel 报错与锁竞态归因
├── 25-Zed会话丢失提取与SQLite数据库表解析抢救指南.md # [Stage 2: 专项抢救] 针对 SQLite 历史会话恢复
├── 26-Zed项目级LSP白名单配置与内存占用规避指南.md # [Stage 2: 专项配置] 针对 LSP 项目白名单与内存优化
├── 27-多Git账号GitHub与GitLab共存及SSHIncludeIf配置指南.md # [Stage 2: 专项配置] 针对多账号 SSH 与 includeIf 切换
├── 28-Windows终端Atuin命令历史同步与PwshProfile排障指南.md # [Stage 2: 专项排障] 针对 Atuin 历史丢失与 profile 修复
├── 29-cc-switch配置SQLite直接读写与跨应用模型迁移指南.md # [Stage 2: 专项配置] 针对 cc-switch 数据库直接读写
├── 30-VSCode扩展跨分支IDE手动搬运与注册生效指南.md # [Stage 2: 专项配置] 针对扩展跨 IDE 搬运生效
├── 31-VSCode底部面板Git提交图与分支配色调优配置指南.md # [Stage 2: 专项配置] 针对 GitLG 面板与分支配色
├── 32-Windows便携免安装PowerShell7绿色部署与环境初始化指南.md # [Stage 2: 专项配置] 针对 Pwsh7 绿色部署与环境变量
├── 33-YaHeiConsolasHybrid字体安装与Sublime界面高清字体渲染配置指南.md # [Stage 2: 专项配置] 针对字体安装与渲染调优
├── 34-Windows11右键菜单注册Sublime与注册表快捷管理指南.md # [Stage 2: 专项配置] 针对 Win11 右键菜单注册表项
├── 35-Pi终端快捷键映射改键与滚轮协议冲突修复指南.md # [Stage 2: 专项排障] 针对按键映射与滚轮误触修复
├── 36-Windows各Agent客户端终端机制与GitBash环境切换指南.md # [Stage 2: 专项配置] 针对各 Agent 终端机制与 Git Bash
├── 37-opencode集成chrome-devtools-mcp浏览器控制调试配置指南.md # [Stage 2: 专项配置] 针对浏览器控制与 MCP 调试
├── 38-Zed集成opencodeAgent环境思考档位与供应商迁移指南.md # [Stage 2: 专项配置] 针对 opencode 思考档位与供应商迁移
└── ...（后续顺次扩充）
```

- **文件名自解释（Self-describing Filename）**：每个知识文件均以`【编号 + 目标工具 + 核心问题场景 + 解决目标】`命名，AI 或开发者仅需浏览文件名列表，即可 100% 判断该文件是否适用于当前上下文，无需逐个打开探查。
- **排障与工程实现双翼**：
  - **Type A（疑难排障型）**：解决踩坑、文件锁、底层冲突，包含精准排查命令、界面现象对照和确定性操作 SOP；
  - **Type B（方案与生成流水线型）**：解决端到端工程实现、内容/试卷/文档自动化生成、样式排版引擎落地，包含业务输入输出、底层技术剖析、代码实现与交付验证模板。
- **条目即技能（隐形技能约定）**：每个 `0N-*.md` 条目在元数据上都视为一个独立 skill，必须带 skill-creator 规范的 frontmatter（`name` + `description`），正文保持单文件 ≤500 行、以 SOP 体为主。

### 条目即技能：为什么“是技能”却检测不到

靠的是两条命名约束，别去动它们：

- harness 在子目录里只认名为 `SKILL.md` 的文件；本目录条目一律用 `0N-主题.md`，因此永不注册（实测：同层的 `SKILL-DRAFT.md` 带完备 frontmatter，也从未出现在技能目录里）；
- 总控文件用 `SKILL-DRAFT.md` 而非 `SKILL.md`，将来转正只需改这一个文件名。

### 条目元数据规范

- `name` 取 `kb-<英文主题短横线>`（如 `kb-docx-practice-generator`），**不带编号**：编号只是排序外壳，`name` 才是将来独立成 skill 时沿用的稳定标识，定了就别改，免得引用失效；
- `description` 按 skill-creator 写法：一句话功能语义 + "何时查阅"的触发场景，控制在 200 字符内，关键词尽量用用户真会说的症状词、技术词或目标交付词；
- 本目录的 description 面向**路由与检索**。若某条目将来真要转正为全局技能，除改名建目录外，还必须按 `SKILL-AUTHORING-RULES.md` 把 description 重写成点名触发式（≤70 字符、结尾 `点名使用`）。

---

## 2. 场景路由表（快速匹配）

| 当前遇到的问题或诉求 | 建议读取的条目文档 | 典型现象 / 报错关键词 |
|:---|:---|:---|
| 想在 Sublime Merge 里把两个不相邻的提交合并为一个 | [`01-SublimeMerge非相邻提交Squash合并与移动重排操作指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/01-SublimeMerge非相邻提交Squash合并与移动重排操作指南.md) | 非相邻 commit, 拖拽没反应, Ctrl 多选, Move Commit Down, Squash / Fixup |
| 做了合并操作，界面没报错也没弹窗，怀疑没生效 | [`01-SublimeMerge非相邻提交Squash合并与移动重排操作指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/01-SublimeMerge非相邻提交Squash合并与移动重排操作指南.md) | 误以为没反应, 提交数量少, Stats 文件变化, HEAD 平移 |
| Windows 下变基失败，提示 `Permission denied` 无法写日志 | [`02-Windows下Git变基PermissionDenied文件锁排障与Abort安全恢复.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/02-Windows下Git变基PermissionDenied文件锁排障与Abort安全恢复.md) | `unable to append to logs/HEAD`, Permission denied, 文件锁占用, abort 回滚 |
| 变基失败后停留在 `(onto <hash>)` 状态，暂存区有残留文件 | [`02-Windows下Git变基PermissionDenied文件锁排障与Abort安全恢复.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/02-Windows下Git变基PermissionDenied文件锁排障与Abort安全恢复.md) | rebase in progress, Staged Files, git rebase --abort, 抢救工作区 |
| 变基提示 `It has been rescheduled`，todo 列表混乱 | [`03-Git变基Rescheduled队列挂起与暂存区冲突深度解析.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/03-Git变基Rescheduled队列挂起与暂存区冲突深度解析.md) | rescheduled, git-rebase-todo 重复 pick, 交互变基挂起 |
| Cursor / VS Code 预览 Markdown 默认在侧边栏，想用独立标签页全屏查看 | [`04-CursorMarkdown预览独立标签页与侧边栏切换指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/04-CursorMarkdown预览独立标签页与侧边栏切换指南.md) | Markdown 预览, Ctrl+Shift+V, 侧边栏, 独立标签页, Open Preview |
| Cursor Agent 总弹批准框，想开 YOLO 免审批 / 限制沙箱网络访问 | [`05-Cursor免审批YOLO模式与沙箱网络配置指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/05-Cursor免审批YOLO模式与沙箱网络配置指南.md) | Run Everything, YOLO, Auto-review, sandbox.json, networkPolicy, 批准 |
| 需开 Git Worktree 隔离开发，纠结依赖是否该软链接、担心环境与端口冲突 | [`06-GitWorktree依赖复用与跨语言环境隔离权衡指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/06-GitWorktree依赖复用与跨语言环境隔离权衡指南.md) | git worktree, 软链接, .venv, node_modules, target, editable 倒挂, WinError 32, sccache, pnpm, GOMODCACHE |
| 新电脑只装了 uv，要把全局 `python`/`pip` 与 `uv run` 项目工作流统一成同一套配置 | [`07-uv统一全机Python环境与新电脑一键引导复现指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/07-uv统一全机Python环境与新电脑一键引导复现指南.md) | uv_shim, .uv-global, UV_PYTHON, 一键引导, 新机复现, anaconda 卸载 |
| 全局 `pip install` 报 `externally-managed-environment`，或 venv 里 `python -m pip` 报 `No module named pip` | [`07-uv统一全机Python环境与新电脑一键引导复现指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/07-uv统一全机Python环境与新电脑一键引导复现指南.md) | PEP 668, externally-managed, No module named pip, seed pip |
| Windows 下安装 Java/Maven 导致 C 盘膨胀、Zed 编辑器硬编码 JDK 路径或缺乏调试能力 | [`08-Windows下Java与Maven便携子目录配置及Zed任务调试集成指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/08-Windows下Java与Maven便携子目录配置及Zed任务调试集成指南.md) | Java, Maven, C 盘空间, settings.xml, localRepository, Corretto, jdtls, tasks.json, JDWP, 远程调试 |
| Chrome「继续浏览上次打开的网页」只恢复了一个窗口，手动关闭的窗口（含固定标签页）整体找不回 | [`09-Chrome手动关闭窗口固定标签丢失的SNSS会话快照解析与找回指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/09-Chrome手动关闭窗口固定标签丢失的SNSS会话快照解析与找回指南.md) | 固定标签丢失, 只恢复一个窗口, 最近关闭, 继续浏览上次打开的网页 |
| Chrome 的 Sessions 快照文件被锁无法读取（Device or resource busy / Permission denied），想不重启就解析会话数据、提取固定标签清单 | [`09-Chrome手动关闭窗口固定标签丢失的SNSS会话快照解析与找回指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/09-Chrome手动关闭窗口固定标签丢失的SNSS会话快照解析与找回指南.md) | Device or resource busy, Sessions, Session_, Tabs_, SNSS, cmd5, 固定标签清单 |
| Antigravity CLI 或 Pi 终端中，粘贴图片快捷键 Alt+V 被占想改 Alt+Shift+V，改完终端没反应，或 keybindings.json 报 `invalid character '\ufeff'` | [`10-AntigravityCLI粘贴图片改键Windows终端Kitty协议透传与BOM排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/10-AntigravityCLI粘贴图片改键Windows终端Kitty协议透传与BOM排障指南.md) | 粘贴图片快捷键, edit.paste, app.clipboard.pasteImage, Alt+Shift+V, sendInput, 118;4u, Kitty CSI-u, ufeff, UTF-8 BOM, keybindings.json |
| Windows 计划任务/定时脚本每次触发时，已运行的 Windows Terminal 里闪出一个空白 PowerShell 标签页（“弹终端”），任务“隐藏”属性与 `-WindowStyle Hidden` 都无效 | [`11-Windows计划任务控制台委托闪窗排障与conhost无窗口注册指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/11-Windows计划任务控制台委托闪窗排障与conhost无窗口注册指南.md) | 弹终端, 闪窗, WT 标签页闪现, 控制台委托, handoff, conhost --headless, PseudoConsoleWindow, -WindowStyle Hidden 无效 |
| 需要一条命令手动注册/重配置“无窗口”计划任务（防止终端闪标签页），或任务目录搬移后动作路径失效 | [`11-Windows计划任务控制台委托闪窗排障与conhost无窗口注册指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/11-Windows计划任务控制台委托闪窗排障与conhost无窗口注册指南.md) | register_task.ps1, conhost --headless, New-ScheduledTaskAction, 手动配置, 幂等注册, $PSScriptRoot |
| Antigravity CLI 执行模式（plan/accept-edits）与免批 YOLO 权限混淆、状态栏无 yolo、/permissions 规则为空、/config 面板与免审启动参数配置 | [`12-AntigravityCLI执行模式辨析与免批YOLO及配置面板排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/12-AntigravityCLI执行模式辨析与免批YOLO及配置面板排障指南.md) | Antigravity CLI, YOLO, accept-edits, plan, /permissions, /config, Tool Permission, --dangerously-skip-permissions |
| 佩戴降噪耳机仍能听到人声谈话、轻音乐休止符间隙漏音打断心流，需要构建抗干扰声床、免鉴权下载公有领域名曲或合成立体声褐噪音/自然雨声 | [`13-降噪耳机人声泄露声学掩蔽与公有领域高音质音频下载实战指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/13-降噪耳机人声泄露声学掩蔽与公有领域高音质音频下载实战指南.md) | 降噪耳机, 隔绝人声, 听觉掩蔽, 褐噪音, Brown Noise, 白噪音, 雨声, Wikimedia Commons, 公有领域轻音乐, 萨蒂, 肖邦, 卡农, 巴赫 |
| Windows 常驻应用多（IDE/终端/浏览器/IM）、鼠标跨屏甩动疲劳、Alt+Tab 轮转顺序不稳定、PowerToys 快捷键误触冷启动 | [`14-Windows单手盲切与抽屉式Toggle应用窗口AutoHotkey配置指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/14-Windows单手盲切与抽屉式Toggle应用窗口AutoHotkey配置指南.md) | AutoHotkey, AHK v2, 窗口切换, 盲切, 单手快捷键, Toggle, 前台置顶, 任务栏, PowerToys 缺陷 |
| 需要基于 python-docx 批量生成 Word 试卷或教辅练习题，处理东亚中文字体分离(w:eastAsia)、页边距、行间距微调、化学式上下标排版或自动化装配流水线 | [`15-python-docx自动化生成举一反三试卷与格式精细排版指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/15-python-docx自动化生成举一反三试卷与格式精细排版指南.md) | python-docx, 试卷生成, 举一反三, eastAsia, 宋体回退, 行距, 上下标, 批量生成流水线, Word 排版 |
| Sublime Text 终端插件 Terminus 中文吞字、按 Backspace 无法删除字符、侧边栏右键打开终端看似 PowerShell 实际是 CMD | [`16-SublimeTextTerminus中文退格失效与原生PowerShell侧边栏集成指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/16-SublimeTextTerminus中文退格失效与原生PowerShell侧边栏集成指南.md) | Sublime Text, Terminus, Backspace删不掉, 中文输入法, PSReadLine, Open Terminus here, Open PowerShell here, wt.exe |
| Windows 扬声器/耳机无声、高频或周期性噼啪爆音、默认音频输出设备被虚拟声卡（如 Voicemeeter）静默抢占 | [`17-Windows声卡爆音无声与虚拟音频抢占排查指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/17-Windows声卡爆音无声与虚拟音频抢占排查指南.md) | 声卡爆音, 无声, 默认设备抢占, 虚拟声卡, Voicemeeter, 音频端点, 独占模式 |
| 开启系统/梯子代理时，微软应用商店无法打开、UWP 应用无网络连接或无法初始化 | [`18-Windows代理下微软商店与UWP回环网络豁免排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/18-Windows代理下微软商店与UWP回环网络豁免排障指南.md) | 微软商店打不开, UWP 代理, 回环豁免, CheckNetIsolation, AppContainer, LoopbackExempt |
| 电脑频繁卡死或假死、没开大软件但物理内存使用率居高不下、不确定该不该加物理内存条 | [`19-Windows内存防死机与Pagefile提交内存归因优化指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/19-Windows内存防死机与Pagefile提交内存归因优化指南.md) | 内存防死机, 内存爆满, Commit Charge, 提交大小, Pagefile, 虚拟内存扩容, 内存条判断 |
| C 盘空间告急、红色预警、Temp/缓存/WSL 虚拟硬盘膨胀，需要无损安全腾挪空间 | [`20-Windows系统C盘空间不足排查与安全清理软链接重定向指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/20-Windows系统C盘空间不足排查与安全清理软链接重定向指南.md) | C 盘清理, 空间不足, 软链接重定向, mklink, 环境变量重定向, WSL 迁移, 清理缓存 |
| opencode 等工具调用智谱 GLM 模型接口报 401 身份验证失败、API Key 怎么配都不生效 | [`21-opencode连接GLM模型401鉴权失败与端点排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/21-opencode连接GLM模型401鉴权失败与端点排障指南.md) | GLM 401, opencode 鉴权失败, bigmodel, API Key 优先级, 编码端点冲突 |
| Zed 下载或更新语言服务器时报 `rename os error 5`、下载解压中断或由于杀毒软件占用卡死 | [`22-Zed语言服务器下载失败文件重命名占用与杀毒竞态排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/22-Zed语言服务器下载失败文件重命名占用与杀毒竞态排障指南.md) | Zed LSP 下载失败, rename os error 5, 杀毒竞态, 手工安装 LSP, 文件独占锁 |
| Zed 或 IntelliJ IDEA 外接 ACP agent（如 codex/antigravity）登录失败、代理/CA 证书失效或子进程池堆积吃满内存 | [`23-Zed与IDEA外接ACP代理环境失效与子进程池累积排查指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/23-Zed与IDEA外接ACP代理环境失效与子进程池累积排查指南.md) | ACP agent 登录失败, 代理不生效, 子进程池膨胀, 孤儿进程堆积, stdio 认证 |
| Zed Agent Panel 界面报 `Internal error`、`Invalid request` 或 `Session is closing`，不知从何定位 | [`24-Zed面板InternalError会话中断与ACP线程锁竞态归因指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/24-Zed面板InternalError会话中断与ACP线程锁竞态归因指南.md) | Agent Panel Internal error, Session is closing, telemetry.log, Zed.log 对齐, thread-writer-lock |
| Zed 崩溃或误操作导致历史对话列表空白、重要上下文找不回，需要底层数据恢复 | [`25-Zed会话丢失提取与SQLite数据库表解析抢救指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/25-Zed会话丢失提取与SQLite数据库表解析抢救指南.md) | Zed 会话丢失, sidebar_threads, SQLite 对话恢复, 会话归档抢救 |
| Zed 同时打开多个项目导致各个语言服务器全量拉起吃满内存，需要针对特定项目精细管控 LSP | [`26-Zed项目级LSP白名单配置与内存占用规避指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/26-Zed项目级LSP白名单配置与内存占用规避指南.md) | Zed LSP 白名单, .zed/settings.json, 按项目开 LSP, 内存优化 |
| 既有个人 GitHub 账号又有公司 GitLab 账号，SSH 密钥冲突或提交邮箱身份串号 | [`27-多Git账号GitHub与GitLab共存及SSHIncludeIf配置指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/27-多Git账号GitHub与GitLab共存及SSHIncludeIf配置指南.md) | GitHub GitLab 共存, 多 SSH Key, includeIf, 身份自动切换, .gitconfig 隔离 |
| Windows 下 Atuin 历史命令不同步、Ctrl+R 无法呼出或 PowerShell Profile 报错打架 | [`28-Windows终端Atuin命令历史同步与PwshProfile排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/28-Windows终端Atuin命令历史同步与PwshProfile排障指南.md) | Atuin 历史丢失, Ctrl+R 搜索历史, PSReadLine 冲突, profile.ps1 修复 |
| cc-switch 界面操作卡顿或需要直接通过脚本批量迁移/读写应用模型配置 | [`29-cc-switch配置SQLite直接读写与跨应用模型迁移指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/29-cc-switch配置SQLite直接读写与跨应用模型迁移指南.md) | cc-switch SQLite, 直接修改供应商, 跨应用模型迁移, 绕过 UI 配置 |
| 在 Cursor、Antigravity IDE 或 Trae 中需要用到某个只有 VS Code 插件市场才有的扩展 | [`30-VSCode扩展跨分支IDE手动搬运与注册生效指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/30-VSCode扩展跨分支IDE手动搬运与注册生效指南.md) | VS Code 插件搬运, Cursor 安装离线扩展, Trae 扩展移植, extensions.json 注册 |
| VS Code 缺乏像 IntelliJ IDEA 那样直观清晰的 Git 提交树图谱，希望在底部面板集成 | [`31-VSCode底部面板Git提交图与分支配色调优配置指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/31-VSCode底部面板Git提交图与分支配色调优配置指南.md) | VS Code 提交图, GitLG, 分支配色, 底部面板终端, IDEA 视图复刻 |
| 新电脑没有管理员权限或不想污染系统，需要免安装绿色便携部署 PowerShell 7 | [`32-Windows便携免安装PowerShell7绿色部署与环境初始化指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/32-Windows便携免安装PowerShell7绿色部署与环境初始化指南.md) | PowerShell 7 绿色安装, Pwsh 便携部署, 零系统残留, 用户级环境变量 |
| Sublime Text 或 Sublime Merge 代码中文乱码、字体发虚或想使用清晰的等宽混合字体 | [`33-YaHeiConsolasHybrid字体安装与Sublime界面高清字体渲染配置指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/33-YaHeiConsolasHybrid字体安装与Sublime界面高清字体渲染配置指南.md) | YaHei Consolas Hybrid, Sublime 字体设置, 字体发虚, UI 字体补丁 |
| Windows 11 下希望为文件和文件夹添加“Open with Sublime Text”经典与新型右键菜单 | [`34-Windows11右键菜单注册Sublime与注册表快捷管理指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/34-Windows11右键菜单注册Sublime与注册表快捷管理指南.md) | Sublime 右键菜单, Win11 注册表右键, 经典右键菜单, Open with Sublime |
| 使用 Pi 终端时快捷键冲突、滚轮误触发历史命令或需要自定义按键动作 | [`35-Pi终端快捷键映射改键与滚轮协议冲突修复指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/35-Pi终端快捷键映射改键与滚轮协议冲突修复指南.md) | Pi 终端改键, 按键映射, 滚轮翻历史, 终端按键协议, keybindings |
| Windows 各 AI Agent 终端默认是 CMD 或 PowerShell，经常乱码或脚本语法报错，希望统一走 Git Bash | [`36-Windows各Agent客户端终端机制与GitBash环境切换指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/36-Windows各Agent客户端终端机制与GitBash环境切换指南.md) | Agent 终端乱码, 切换 Git Bash, Codex 终端设置, OpenCode 终端 |
| opencode 需要通过 chrome-devtools-mcp 控制本机浏览器，遇到远程端口连不上或握手失败 | [`37-opencode集成chrome-devtools-mcp浏览器控制调试配置指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/37-opencode集成chrome-devtools-mcp浏览器控制调试配置指南.md) | chrome-devtools-mcp, 浏览器自动化控制, opencode 浏览器插件, 调试端口 |
| Zed 的 opencode 插件思考档位失灵、服务进程断连或无法成功读取自定义 API 配置 | [`38-Zed集成opencodeAgent环境思考档位与供应商迁移指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/38-Zed集成opencodeAgent环境思考档位与供应商迁移指南.md) | Zed opencode, 思考档位, 供应商配置迁移, opencode 启动脚本 |

---

## 3. 知识扩充规范（追加新知识时遵循）

当你开发中遇到新的典型踩坑或沉淀出高价值工程实现流水线需要归档时：
1. **确定文件名与 `name`**：文件名遵循 `编号-目标技术核心问题场景与解决目标.md`，序号顺延（如 `16-DockerDesktop卷挂载Windows符号链接失效排障.md`）；同时在 frontmatter 里定一个 `kb-<英文短横线>` 的 `name`；
2. **文档结构标准（双轨结构）**：
   - **通用 YAML frontmatter**：`name` + `description`（skill-creator 规范，见第 1 节「条目即技能」），缺了它这条目就不算合规；
   - **Type A：疑难排障型条目**：
     - 一、现象与报错直击：贴出真实终端输出或 UI 截图文字；
     - 二、底层根因剖析：讲透为什么会发生（操作系统机制、并发锁、协议冲突等）；
     - 三、标准解决与抢救 SOP：提供原子化、可直接复制执行的命令与操作步骤；
     - 四、验证与防复发建议：如何确认已彻底解决；
   - **Type B：方案与生成流水线型条目**：
     - 一、业务场景与生成需求：输入源、生成目标与最终交付格式；
     - 二、排版/技术核心难点与底层剖析：格式规范、底层引擎机制（如 XML 命名空间、编码标准）；
     - 三、标准自动化生成流水线与代码实现：可直接复用的完整脚本骨架与核心装配函数；
     - 四、交付验证与工程扩展建议：产物校验断言与新场景复用 SOP；
3. **更新本路由表**：在上面的路由表格中添加新条目的索引行。
