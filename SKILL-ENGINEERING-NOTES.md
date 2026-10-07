# SKILL-ENGINEERING-NOTES：工程实战手记与疑难排障知识库总控引导

> 本文件是知识库专区 `kb-engineering-notes/` 的外部引导与感知指针。
> 当用户在对话中指定本文件（或提到该知识库）时，AI 应立即根据本文件了解该知识库的定位、目录结构与索引规则，并引导读取内部对应的实战文档。

---

## 一、知识库定位与核心价值

- **目录位置**：`~/.agents/skills/kb-engineering-notes/`（等价于 `.agents/skills/kb-engineering-notes/`）
- **定位**：**长期生长的通用工程实战手记与避坑排障知识库**。不同于一次性的临时文档，这里沉淀的是在真实开发过程中遇到的高成本踩坑、GUI 与 CLI 工具高阶交互、系统底层机制（文件锁、进程冲突、异常调度）以及经过血泪验证的标准操作 SOP。
- **与正式 Skill 的关系**：
  - **当前状态**：作为独立知识库存在，内部总控文件命名为 `SKILL-DRAFT.md`（非标准 `SKILL.md`），因此**绝不会被任何 AI Agent 自动注册为活跃技能**，避免污染常规指令上下文；
  - **未来转正**：内部所有规范与元数据 100% 遵循 `/skill-creator` 标准；未来若需转正为自动调用的技能，只需将 `SKILL-DRAFT.md` 重命名为 `SKILL.md` 即可秒级生效。

---

## 二、内部总控文件：`SKILL-DRAFT.md` 是做什么的？

位于 `kb-engineering-notes/SKILL-DRAFT.md`，它是整个知识库的**“大脑索引与技能母版”**：

1. **技能元数据（YAML Frontmatter）**：定义了本知识库未来转正时的技能名称（`name: kb-engineering-notes`）与精准触发描述（`description`）；
2. **场景路由表**：当开发者或 AI 遇到特定技术问题时，负责将问题精确映射到内部具体的 `01-xxx.md`、`02-xxx.md` 条目；
3. **渐进式感知协议**：定义了 AI 查阅该知识库时的两阶段读取规则（先读文件名判断相关性，再读正文执行操作）。

---

## 三、当前已收录的实战手记条目（自解释清单）

内部文档统一采用 **【编号 + 目标工具 + 核心问题场景 + 解决目标】** 的高信息密度命名，AI 扫一眼文件名即可知道其用途：

| 条目文件 | 核心解决场景 | AI 识别与触发关键词 |
|:---|:---|:---|
| **[`01-SublimeMerge非相邻提交Squash合并与移动重排操作指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/01-SublimeMerge非相邻提交Squash合并与移动重排操作指南.md)** | 非相邻提交合并、拖拽不可用破局、Ctrl多选合并、Move Down重排、后台无感变基生效判定 | Sublime Merge, 跨提交合并, squash, fixup, 拖拽没反应 |
| **[`02-Windows下Git变基PermissionDenied文件锁排障与Abort安全恢复.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/02-Windows下Git变基PermissionDenied文件锁排障与Abort安全恢复.md)** | `logs/HEAD: Permission denied`、Windows 独占句柄锁根因、进程占用排查、`git rebase --abort` 安全回滚 | Permission denied, logs/HEAD, 变基文件锁, rebase abort, 暂存区抢救 |
| **[`03-Git变基Rescheduled队列挂起与暂存区冲突深度解析.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/03-Git变基Rescheduled队列挂起与暂存区冲突深度解析.md)** | `It has been rescheduled` 重调度机制、todo 队列混乱、变基暂停在中间 commit、避免重复 pick | rescheduled, git-rebase-todo, rebase挂起, onto commit |
| **[`04-CursorMarkdown预览独立标签页与侧边栏切换指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/04-CursorMarkdown预览独立标签页与侧边栏切换指南.md)** | Cursor/VS Code Markdown 预览默认侧边栏、想用独立标签页全屏查看、快捷键与 Alt 修饰键 | Markdown 预览, Ctrl+Shift+V, 侧边栏, 独立标签页, Open Preview |
| **[`05-Cursor免审批YOLO模式与沙箱网络配置指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/05-Cursor免审批YOLO模式与沙箱网络配置指南.md)** | Cursor Agent 免审批 YOLO 三档模式、总是弹窗根因、sandbox.json 网络管控 | Run Everything, YOLO, Auto-review, sandbox.json, networkPolicy, 批准 |

---

## 四、AI 使用指引（当用户指定本文件时）

1. **建立全局认知**：确认本仓库下存在 `kb-engineering-notes/` 知识库专区；
2. **场景分流**：
   - 若用户咨询或正在处理 Git / Sublime Merge 的提交整理或权限报错，**优先直接读取对应的 `01-xxx.md` ~ `03-xxx.md` 知识文档**；
   - 若用户需要扩充新知识，查阅 `SKILL-DRAFT.md` 的规范，按 `04-中文描述.md` 顺次追加并更新索引；
   - 若用户要求“转为技能”，指导执行 `git mv kb-engineering-notes/SKILL-DRAFT.md kb-engineering-notes/SKILL.md`。
