---
name: sh-agy-session-governance
description: Google Antigravity (App 与 CLI 双端) 会话标题批量治理与汉化工具 SOP。支持查看导出英文会话、AI 协同智能翻译生成中文标题、SQLite 字段与 Protobuf raw_summary / agyhub_summaries_proto.pb / annotations 四重原子双写更新、自动前置快照备份与一键还原。点名使用
version: 1.2.0
created: 2026-10-13
updated: 2026-10-30
disable-model-invocation: true
---

# sh-agy-session-governance — Antigravity (App & CLI) 会话标题批量治理与汉化 SOP

基于对 Google Antigravity Desktop App (`language_server.exe` / `Antigravity.exe`) 与 `agy` CLI (`agy.exe`) 底层会话持久化与展示机制的完整逆向工程结论，提供的一套轻量、安全、高效的会话标题批量治理与自动化汉化工具。

产物形态包含 PEP 723 单文件 Python 脚本（`scripts/agy_titles.py`）与免安装单文件 Windows 可执行程序（`dist/agy_titles.exe`，基于 `sh-nuitka-pack` 编译，秒开缓存加速）。

---

## 核心机制与逆向工程结论

### 1. 双端多源持久化架构
- **Antigravity Desktop App**（桌面 GUI 应用，位于 `~/.gemini/antigravity/`）：
  - 核心后台 `language_server.exe` 采用 `jetbox_summaries_store.RecordToSummary` 读取会话列表；
  - **关键机制**：若 SQLite 数据库中存在 `raw_summary` 二进制 BLOB，应用会优先反序列化 `raw_summary`（`CascadeTrajectorySummary` Protobuf）读取标题（Field 1 与 Field 15），**若仅修改 SQLite 的 `title` 文本列，桌面端依然会回退显示 `raw_summary` 中的旧标题**；
  - 同时，桌面端使用 `agyhub_summaries_proto.pb` 作为备用快照/降级数据源，并在 `annotations/<id>.pbtxt` 维护用户级注释。
- **agy CLI**（命令行终端工具，位于 `~/.gemini/antigravity-cli/`）：
  - `/resume` 命令通过 SQLite 索引（`conversation_summaries.db`）与 `annotations/<id>.pbtxt` 读取会话标题。

### 2. 四重原子双写一致性保障
本工具（v1.1.0+）内置纯标准库实现的 Protobuf Wire 编解码引擎（零第三方依赖），在改写会话标题时执行四重原子更新：
1. **SQLite `title` 列**：更新文本索引列；
2. **SQLite `raw_summary` BLOB**：原子重打包 Protobuf 二进制，同步更新 Field 1（标题）与 Field 15（注释子消息标题）；
3. **`agyhub_summaries_proto.pb`**：同步更新 Protobuf 字典中的 `CascadeTrajectorySummary` 映射项；
4. **`annotations/<id>.pbtxt`**：同步写入标准文本注解。

### 3. 运行中内存缓存覆写与官方 ConnectRPC 实时热推送
- **后台常驻覆写风险**：当 Antigravity Desktop App 处于打开状态时，常驻进程 `language_server.exe` 会在内存维护全量会话缓存，并在后台定时触发 `summary store: starting background reconciliation`，将旧内存状态强行刷回磁盘。若仅进行离线磁盘修改，会被语言服务器反向覆盖回滚！
- **官方 ConnectRPC 接口突破**：
  - 协议端点：`http://127.0.0.1:<port>/exa.language_server_pb.LanguageServerService/UpdateConversationAnnotations`；
  - 动态探测：工具自动通过 WMI 探测 `language_server.exe` 进程，解析其启动命令行获取 `--csrf_token`，并扫描本地监听端口建立 HTTP 通信；
  - 热推送更新：调用 `UpdateConversationAnnotations` 载入 `{"cascadeIds": [...], "annotations": {"title": "..."}, "mergeAnnotations": true}`，直接驱使语言服务器在内存中更新状态并写回 SQLite，彻底根绝覆写冲突。

### 4. 启发式标签剥离与伪中文识别盲区消除（v1.2.0+）
- **误判盲区**：很多会话带有业务分类前缀（如 `【知识】Douyin Video Summary And Insights` 或 `【待办】Vibe Coding Skill Recommendations`）。旧正则只要在全串中命中任意一个汉字（如“知”、“待”）即判定为已汉化，导致主体全为英文的会话漏网。
- **剥离研判算法**：
  - 采用正则 `^[\[【](.*?)[\]】]\s*` 剥离分类标签前缀，提取纯主体字符串；
  - 严格分析主体文本中的汉字数与多字符英文单词占比，若主体无汉字或汉字过少且含英文单词，强制判定为未汉化，消灭混血伪中文。

### 5. SQLite WAL 事务截断检查点（WAL Checkpoint Invariant）
- **WAL 模式驻留风险**：Antigravity 数据库默认开启 WAL（Write-Ahead Logging）模式，离线更新若仅停留在 `-wal` 临时日志中未并入主库，后台 `language_server.exe` 触发定期内存协调时极易用旧主本覆写主库并截断 WAL，导致修改丢失。
- **强制落盘截断**：工具在所有单次或批量 SQLite 事务提交后，显式执行：
  ```sql
  PRAGMA wal_checkpoint(TRUNCATE);
  ```
  强制将 WAL 事务完整同步写入主数据库文件并清空 WAL，确保磁盘数据状态具备最高确定性。

### 6. 自动前置快照备份与一键回滚
- 任何写入操作执行前，工具均会自动对受影响环境中的 SQLite 数据库、`.pb` 文件与 `.pbtxt` 创建时间戳快照并存入对应目录下的 `backups/titles/`；
- 用户可随时通过 `agy_titles.exe restore --list` 与 `agy_titles.exe restore <snapshot>` 一键秒级复原。

---

## 工具命令速查 (CLI Reference)

| 命令 | 说明 | 常见参数示例 |
|---|---|---|
| `list` | 列出会话（默认列出 App + CLI 全环境） | `agy_titles.exe list --english-only --limit 20` |
| `list --target` | 指定目标环境过滤 | `agy_titles.exe list --target app --english-only` |
| `list --json` | 导出 JSON（供 AI 解析） | `agy_titles.exe list --target all --english-only --json` |
| `get` | 查看单个会话跨环境详情 | `agy_titles.exe get <ID前缀>` |
| `rename` | 重命名单个会话 | `agy_titles.exe rename <ID> "新中文标题"` |
| `rename --dry-run` | 预览单条重命名 | `agy_titles.exe rename <ID> "新中文标题" --dry-run` |
| `batch-rename` | 批量重命名 | `agy_titles.exe batch-rename '<JSON>'` 或 `--file <PATH>` |
| `batch-rename --dry-run` | 预览批量重命名 | `agy_titles.exe batch-rename '<JSON>' --dry-run` |
| `backup` | 手动创建环境快照备份 | `agy_titles.exe backup --target all` |
| `restore --list` | 列出历史快照 | `agy_titles.exe restore --list` |
| `restore <snapshot>` | 恢复指定快照 | `agy_titles.exe restore backup_20261017_044241_585` |

> `--target` 支持四个取值：`all`（默认，覆盖全部已存在环境）、`app`（仅 Antigravity 桌面应用）、`cli`（仅 agy CLI）、`ide`（若存在 Antigravity IDE）。

---

## AI 协同治理工作流 SOP

当用户发出“帮我把会话标题中文化”或“antigravity app 不支持，迭代一下”时，AI 严格按以下 4 步执行：

### Step 1: 导出待治理会话数据
AI 执行只读命令导出全环境未汉化的英文会话：
```powershell
.\dist\agy_titles.exe list --target all --english-only --json
```

### Step 2: AI 智能生成专业中文标题
AI 结合原有英文标题、工作区上下文及首轮 Prompt 预览（`preview`），遵循命名规范：
- **专有名词保留**：技术名称、库名、工具名保持英文（如 `VS Code`、`PowerShell`、`Nuitka`、`Git`、`Windows Terminal`、`SQLite`、`xmake` 等）；
- **动词与语境汉化**：汉化行为动作与功能语境（如 `Debugging` ➔ `调试/排障`、`Migration` ➔ `迁移`、`Setting` ➔ `设置`、`Review` ➔ `审查`）；
- **字数克制精炼**：控制在 4 ~ 15 个字内，清晰传达会话主旨，绝不冗余。

### Step 3: 格式化装配并安全执行
AI 将翻译好的映射组装为 JSON，并调用 `batch-rename`：
```powershell
.\dist\agy_titles.exe batch-rename --target all --file "$env:TEMP\rename_payload.json"
```

### Step 4: 提示用户查验与界面刷新
- 告知用户写入成功、涉及的环境（`app` 与 `cli`）以及自动快照路径；
- **Antigravity Desktop App 查验（核心步骤）**：
  - 由于 Antigravity 桌面端是基于 Electron/Webview 的单页应用（SPA），侧边栏 Projects 会话列表已渲染在 DOM 树中，后台 RPC 更新后前端不会自动触发全量重绘；
  - **必须提醒用户在 Antigravity 界面按快捷键 `Ctrl + R`**（或按 `F1` 输入 `Developer: Reload Window` 重载窗口），侧边栏即会瞬间从语言服务器重新获取最新数据并渲染中文；
- **agy CLI 查验**：在终端运行 `/resume` 查验终端选号列表。
