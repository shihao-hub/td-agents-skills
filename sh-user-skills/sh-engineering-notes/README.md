---
name: sh-engineering-notes
description: 知识库：工程实战手记与避坑知识库 kb-engineering-notes/ 渐进式检索分流器。点名使用
version: 1.0.0
created: 2026-10-10
updated: 2026-10-10
---

# sh-engineering-notes：工程实战手记与避坑知识库导航

> 本技能是 **`kb-engineering-notes/` 避坑知识库** 的渐进式感知入口与分流器。
> 解决单点疑难排障、系统底层机制避坑、Windows 硬件与环境配置等全量工程实战手记检索问题。

---

## 一、两级渐进式感知查阅协议

为了避免几十篇长篇排障笔记污染全局上下文，知识库采用了 **两级渐进式感知架构**：

1. **第一级（总路由表）**：
   - 当遇到系统底层报错、环境配置、避坑求助时，AI 首先读取知识库总控路由：
     [kb-engineering-notes/SKILL-DRAFT.md](file:///D:/Users/language_projects/.agents/skills/kb-engineering-notes/SKILL-DRAFT.md)
   - 该文件维护了完整的 现象/报错关键词 到 对应编号条目 的映射表。
2. **第二级（按需读取编号实战条目）**：
   - 查阅 `SKILL-DRAFT.md` 命中对应条目后，使用 `view_file` **仅读取具体的 0N-*.md 文件**。
   - 每个条目均遵循「现象直击 -> 底层根因 -> 抢救 SOP -> 验证防复发」的标准四段论结构。

---

## 二、覆盖领域分类速览

知识库持续沉淀专项实战条目（条目全量索引与动态路由见 `kb-engineering-notes/SKILL-DRAFT.md`），主要覆盖：
- **Git 与版本控制** (01~03, 06, 27)：Sublime Merge 跨提交合并、Windows Git 变基 Permission Denied、Rescheduled 队列挂起、Git Worktree 依赖隔离、多账号 GitHub/GitLab 共存。
- **IDE、编辑器与扩展** (04, 05, 08, 22~26, 30~34)：Cursor Markdown 预览与免审沙箱、VS Code 提交图、Zed 语言服务器下载与杀毒竞态、ACP 子进程池堆积、SQLite 会话恢复、LSP 白名单内存优化、Sublime 字体与右键菜单。
- **命令行与终端** (10~12, 28, 32, 35~38)：Antigravity CLI 粘图改键 Kitty 协议、计划任务无窗口委托闪退、Antigravity CLI YOLO 免审配置、Atuin 历史命令同步、PowerShell 7 绿色部署、Pi 终端改键、Git Bash 终端切换。
- **系统、网络与硬件** (14, 17~20)：Windows 声卡爆音/无声、代理下 UWP 与应用商店回环豁免、内存防死机与 Commit 归因、C 盘空间清理与软链接重定向、单手盲切 AutoHotkey 窗口。
- **模型鉴权与自动化** (21, 29, 37)：opencode GLM 401 报错排查、cc-switch SQLite 直接读写、chrome-devtools-mcp 浏览器控制。
- **办公与进阶自动化** (09, 13, 15, 16)：Chrome 固定标签 SNSS 快照抢救、降噪耳机人声掩蔽与音频下载、python-docx 格式精细排版、Sublime Terminus 中文退格。

---

## 三、AI 执行 SOP

当用户通过 `sh-engineering-notes` 或口语模糊需求呼叫排障手记时，AI 严格执行以下步骤：
1. 第一步：使用 `view_file` 读取 `D:\Users\language_projects\.agents\skills\kb-engineering-notes\SKILL-DRAFT.md`；
2. 第二步：比对用户的具体报错或诉求，匹配命中具体的 `0N-*.md` 文档；
3. 第三步：使用 `view_file` 读取该目标条目全文，并按照其标准 SOP 步骤向用户提供解决方案或执行操作。
