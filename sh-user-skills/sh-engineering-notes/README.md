---
name: sh-engineering-notes
description: |
  工程实战手记与避坑知识库入口（kb-engineering-notes 两级渐进式检索分流器）：用户报出底层报错、系统/IDE/终端异常或环境配置疑难时优先查阅。覆盖 Windows 声卡爆音无声、代理下 UWP/微软商店回环、C 盘空间清理、内存防死机、文件锁 Permission denied、Git 变基 rescheduled、多 Git 账号 SSH 共存、Zed/Cursor/VSCode 崩溃与 LSP/ACP/会话恢复、终端改键与 Atuin 历史、PowerShell7 绿色部署、字体渲染与右键菜单、浏览器静默插件、Word/试卷自动化排版、无 API 事实核查、跨盘软链接机制、进程启动来源取证等。检索协议：先读知识库总路由表，再按命中条目查看全文；条目持续生长，全量索引以总路由表为准；遇到上述报错或疑难、或用户点名查阅避坑知识库时使用本入口。
version: 1.1.0
created: 2026-10-10
updated: 2026-10-11
---

# sh-engineering-notes：工程实战手记与避坑知识库导航

> 本技能是 **`kb-engineering-notes/` 避坑知识库** 的渐进式感知入口与分流器。
> 解决单点疑难排障、系统底层机制避坑、Windows 硬件与环境配置等全量工程实战手记检索问题。

---

## 一、两级渐进式感知查阅协议

为避免长篇排障笔记批量占用全局上下文，知识库采用 **两级渐进式感知架构**：

1. **第一级（总路由表）**：
   - 当遇到系统底层报错、环境配置、避坑求助时，AI 首先读取知识库总控路由：
     [kb-engineering-notes/SKILL-DRAFT.md](file:///D:/Users/language_projects/.agents/skills/kb-engineering-notes/SKILL-DRAFT.md)
   - 该文件维护了完整的 现象/报错关键词 到 对应编号条目 的映射表。
2. **第二级（按需读取编号实战条目）**：
   - 查阅 `SKILL-DRAFT.md` 命中对应条目后，使用 `view_file` **仅读取具体的 `0N-*.md` 文件**。
   - 每个条目均遵循「现象直击 -> 底层根因 -> 抢救 SOP -> 验证防复发」的标准四段论结构。

---

## 二、覆盖领域分类速览

知识库条目持续生长（全量索引与动态路由以 `kb-engineering-notes/SKILL-DRAFT.md` 为准），主要覆盖：

- **Git 与版本控制**：Sublime Merge 跨提交合并、Windows Git 变基 Permission Denied 文件锁、Rescheduled 队列挂起、Git Worktree 依赖隔离、多账号 GitHub/GitLab 共存。
- **IDE、编辑器与扩展**：Cursor Markdown 预览与免审沙箱、VS Code 提交图与扩展跨分支搬运、Zed 语言服务器下载竞态、ACP 子进程池堆积、SQLite 会话恢复、LSP 白名单内存优化、Sublime 字体渲染与右键菜单、Terminus 中文退格。
- **命令行与终端**：Antigravity CLI 粘图改键与 YOLO 免审、计划任务控制台委托闪窗、Atuin 历史同步、PowerShell 7 绿色部署、Pi 终端改键、Git Bash 环境切换、Windows Terminal 分屏治理。
- **系统、网络与硬件**：Windows 声卡爆音/无声、代理下 UWP 与应用商店回环豁免、内存防死机与 Commit 归因、C 盘空间清理与软链接重定向、单手盲切 AutoHotkey 窗口、跨盘单文件软链接与 Junction 机制、进程启动来源取证。
- **模型鉴权与自动化**：opencode GLM 401 排查、cc-switch SQLite 读写、chrome-devtools-mcp 浏览器控制、opencode 思考档位与供应商迁移、全机 AI 密钥清点。
- **办公与进阶自动化**：Chrome 固定标签 SNSS 快照抢救、降噪耳机人声掩蔽与音频下载、python-docx 试卷精细排版、无搜索 API 事实核查流水线、浏览器静默插件清理。

---

## 三、AI 执行 SOP

当用户通过 `sh-engineering-notes` 或口语模糊需求呼叫排障手记时，AI 严格执行以下步骤：
1. 第一步：使用 `view_file` 读取 `D:\Users\language_projects\.agents\skills\kb-engineering-notes\SKILL-DRAFT.md`；
2. 第二步：比对用户的具体报错或诉求，匹配命中具体的 `0N-*.md` 文档；
3. 第三步：使用 `view_file` 读取该目标条目全文，并按照其标准 SOP 步骤向用户提供解决方案或执行操作。
