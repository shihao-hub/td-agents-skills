---
name: kb-engineering-notes
description: 开发者通用工程实战手记与硬核排障知识库。收录在实际开发中沉淀的工具高阶交互、系统底层机制（Windows 文件锁、进程冲突、异常调度）以及经过严格验证的标准排障 SOP。当遇到复杂 Git 跨提交整理、Sublime Merge 操作困惑、Windows 下 Permission Denied 变基卡死、Rescheduled 队列异常或 Cursor/VS Code Markdown 预览模式切换时查阅本指南。
---

# 工程实战手记与疑难排障知识库 (Engineering Notes Playbook)

> **注意（隔离与转正说明）**：
> 本文件当前命名为 `SKILL-DRAFT.md`，用于确保在草稿与沉淀阶段**不被外部 Agent 自动注册为活跃技能**。
> 本文件架构完全遵循 `/skill-creator` 规范，未来转正只需执行：
> `git mv SKILL-DRAFT.md SKILL.md`

---

## 1. 知识库架构与设计哲学

本知识库采用**两级渐进式感知架构（Two-stage Progressive Disclosure）**：

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
└── ...（后续顺次扩充）
```

- **文件名自解释（Self-describing Filename）**：每个知识文件均以`【编号 + 目标工具 + 核心问题场景 + 解决目标】`命名，AI 或开发者仅需浏览文件名列表，即可 100% 判断该文件是否适用于当前上下文，无需逐个打开探查。
- **单一职责与实战保真**：每个文件只深入解决一个具体核心痛点，内容必须源于真实生产/开发踩坑，包含精准排查命令、界面现象对照和确定性操作 SOP。
- **条目即技能（隐形技能约定）**：每个 `0N-*.md` 条目在元数据上都视为一个独立 skill，必须带 skill-creator 规范的 frontmatter（`name` + `description`），正文保持单文件 ≤500 行、以 SOP 体为主。

### 条目即技能：为什么"是技能"却检测不到

靠的是两条命名约束，别去动它们：

- harness 在子目录里只认名为 `SKILL.md` 的文件；本目录条目一律用 `0N-主题.md`，因此永不注册（实测：同层的 `SKILL-DRAFT.md` 带完整 frontmatter，也从未出现在技能目录里）；
- 总控文件用 `SKILL-DRAFT.md` 而非 `SKILL.md`，将来转正只需改这一个文件名。

### 条目元数据规范

- `name` 取 `kb-<英文主题短横线>`（如 `kb-git-worktree-deps`），**不带编号**：编号只是排序外壳，`name` 才是将来独立成 skill 时沿用的稳定标识，定了就别改，免得引用失效；
- `description` 按 skill-creator 写法：一句话功能语义 + "何时查阅"的触发场景，控制在 200 字符内，关键词尽量用用户真会说的症状词与报错串；
- 本目录的 description 面向**路由与检索**。若某条目将来真要转正为全局技能，除改名建目录外，还必须按 `SKILL-AUTHORING-RULES.md` 把 description 重写成点名触发式（≤70 字符、结尾 `点名使用`）。

---

## 2. 场景路由表（快速匹配）

| 当前遇到的问题或诉求 | 建议读取的条目文档 | 典型现象 / 报错关键词 |
|:---|:---|:---|
| 想在 Sublime Merge 里把两个不相邻的提交合并为一个 | [`01-SublimeMerge非相邻提交Squash合并与移动重排操作指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/01-SublimeMerge非相邻提交Squash合并与移动重排操作指南.md) | 非相邻 commit, 拖拽没反应, Ctrl 多选, Move Commit Down, Squash / Fixup |
| 做了合并操作，界面没报错也没弹窗，怀疑没生效 | [`01-SublimeMerge非相邻提交Squash合并与移动重排操作指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/01-SublimeMerge非相邻提交Squash合并与移动重排操作指南.md) | 误以为没反应, 提交数减少, Stats 文件变化, HEAD 平移 |
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
| Antigravity CLI 或 Pi 终端中，粘贴图片快捷键 Alt+V 被占想改 Alt+Shift+V，改完终端没反应，或 keybindings.json 报 `invalid character '\ufeff'` | [`10-AntigravityCLI粘贴图片改键Windows终端Kitty协议透传与BOM排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/10-AntigravityCLI粘贴图片改键Windows终端Kitty协议透传与BOM排障指南.md) | 粘图片快捷键, edit.paste, app.clipboard.pasteImage, Alt+Shift+V, sendInput, 118;4u, Kitty CSI-u, ufeff, UTF-8 BOM, keybindings.json |

---

## 3. 知识扩充规范（追加新知识时遵循）

当你在开发中遇到新的典型踩坑（如 Docker 卷权限、Python 编译依赖、网络代理截断等）需要归档时：
1. **确定文件名与 `name`**：文件名遵循 `编号-目标技术核心问题场景与解决目标.md`，序号顺延（如 `08-DockerDesktop卷挂载Windows符号链接失效排障.md`）；同时在 frontmatter 里定一个 `kb-<英文短横线>` 的 `name`；
2. **文档结构标准**：
   - **YAML frontmatter**：`name` + `description`（skill-creator 规范，见第 1 节「条目即技能」），缺了它这条目就不算合规；
   - **一、现象与报错直击**：贴出真实终端输出或 UI 截图文字；
   - **二、底层根因剖析**：讲透为什么会发生（操作系统机制、并发锁、协议冲突等）；
   - **三、标准解决与抢救 SOP**：提供原子化、可直接复制执行的命令与操作步骤；
   - **四、验证与防复发建议**：如何确认已彻底解决；
3. **更新本路由表**：在上面的路由表格中添加新条目的索引行。
