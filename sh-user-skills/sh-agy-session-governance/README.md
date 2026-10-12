---
name: sh-agy-session-governance
description: Google Antigravity CLI (agy) 会话标题批量治理与汉化工具 SOP。支持查看导出英文会话、AI 协同智能翻译生成中文标题、事务双写更新 SQLite 与 annotations 文件、自动前置快照备份与一键还原。点名使用
version: 1.0.0
created: 2026-10-13
updated: 2026-10-13
---

# sh-agy-session-governance — agy CLI 会话标题批量治理与汉化 SOP

基于对 `agy.exe` 底层会话管理机制（`conversation_summaries.db` 与 `annotations/<id>.pbtxt` 双写）的逆向工程结论，为 Google Antigravity CLI 提供的一套轻量、安全、高效的会话标题批量治理与自动化汉化工具。

产物形态包含 PEP 723 单文件 Python 脚本（`scripts/agy_titles.py`）与免安装单文件 Windows 可执行程序（`dist/agy_titles.exe`，基于 `sh-nuitka-pack` 编译，秒开缓存加速）。

---

## 核心机制与安全防线

1. **双写一致性保障**：
   - `agy` CLI 在运行时通过 SQLite（`~/.gemini/antigravity-cli/conversation_summaries.db`）维护会话列表缓存，同时在 `annotations/<id>.pbtxt` 维护各会话的持久化注释；
   - 本工具在写入时采用 SQLite 事务（`BEGIN IMMEDIATE`）与 `PRAGMA busy_timeout = 10000` 防并发读写冲突，并同步双写 `.pbtxt`，确保 `/resume` 与底层注释系统 100% 对齐。

2. **自动前置快照备份与一键回滚**：
   - 任何改写操作（单条 `rename` 或批量 `batch-rename`）执行前，工具均会自动对受影响的 SQLite 数据库与 `.pbtxt` 创建时间戳快照并存入 `~/.gemini/antigravity-cli/backups/titles/`；
   - 若写入过程中发生异常，立即触发事务回滚；用户也可随时通过 `agy_titles restore --list` 和 `agy_titles restore <snapshot>` 一键还原。

3. **Dry-Run 预览护栏**：
   - 所有写入指令均支持 `--dry-run` 标志，可在实际落盘前清晰预览拟修改的新旧标题对齐 Diff。

---

## 工具命令速查 (CLI Reference)

| 命令 | 说明 | 常见参数示例 |
|---|---|---|
| `list` | 列出会话 | `agy_titles.exe list --english-only --limit 20` |
| `list --json` | 导出 JSON（供 AI 解析） | `agy_titles.exe list --english-only --json --limit 30` |
| `get` | 查看单个会话详情 | `agy_titles.exe get <ID前缀>` |
| `rename` | 重命名单个会话 | `agy_titles.exe rename <ID> "新中文标题"` |
| `rename --dry-run` | 预览单条重命名 | `agy_titles.exe rename <ID> "新中文标题" --dry-run` |
| `batch-rename` | 批量重命名 | `agy_titles.exe batch-rename '<JSON>'` 或 `--file <PATH>` |
| `batch-rename --dry-run` | 预览批量重命名 | `agy_titles.exe batch-rename '<JSON>' --dry-run` |
| `backup` | 手动创建快照备份 | `agy_titles.exe backup` |
| `restore --list` | 列出历史快照 | `agy_titles.exe restore --list` |
| `restore <snapshot>` | 恢复指定快照 | `agy_titles.exe restore backup_20261013_021947` |

---

## AI 协同治理工作流 SOP

当用户发出“帮我把最近的英文会话治理为中文”或“把 agy 会话标题汉化一下”时，AI Agent 严格按以下 4 步执行：

### Step 1: 导出待治理会话数据
AI 执行只读命令导出未汉化的英文会话：
```powershell
.\dist\agy_titles.exe list --english-only --json --limit 20
```
工具将回传清晰的 JSON 数组：
```json
[
  {
    "id": "5939b044-bb06-4441-bdf8-0f1fffb0305c",
    "title": "Debugging VS Code Icon Script",
    "preview": "好，添加别名...",
    "last_modified": "2026-10-12 15:47:43.717204+00:00"
  }
]
```

### Step 2: AI 智能生成专业中文标题
AI 结合原有英文标题及首轮 Prompt 预览（`preview`），遵循以下命名规范：
- **专有名词保留**：技术名称、库名、工具名保持英文（如 `VS Code`、`PowerShell`、`Nuitka`、`Git`、`Windows Terminal`、`SQLite` 等）；
- **动词与语境汉化**：仅汉化行为动作与功能语境（如 `Debugging` ➔ `调试/排障`、`Migration` ➔ `迁移`、`Setting` ➔ `设置`）；
- **字数克制精炼**：控制在 4 ~ 15 个字内，清晰传达“这个会话是干什么的”，绝不冗余。

示例映射：
- `Debugging VS Code Icon Script` ➔ `VS Code 图标脚本排障`
- `Custom Windows Terminal Profiles Migration` ➔ `Windows Terminal 配置迁移`
- `Agy Cli Default Language Setting` ➔ `agy CLI 默认语言设置调研`

### Step 3: 格式化装配并安全执行
AI 将翻译好的映射组装为 JSON，并调用 `batch-rename`：
```powershell
.\dist\agy_titles.exe batch-rename '[{"id": "5939b044", "title": "VS Code 图标脚本排障"}]'
```

### Step 4: 提示用户查验
告知用户写入成功与自动快照路径，提示用户在 `agy` 终端中运行 `/resume` 查验中文展示效果。
