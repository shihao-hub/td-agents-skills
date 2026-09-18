---
name: sh-zed-session-db
description: 通过 Zed 编辑器本地 SQLite 数据库（%LOCALAPPDATA%\Zed\db\0-stable\db.sqlite 的 sidebar_threads 等表）排查、恢复和管理 agent 会话记录。当用户提到「Zed 会话/历史丢失、不见了、找不到、清空了」「恢复/找回 Zed 会话」「归档/解档/删除/清理会话」「改会话标题」「合并项目/换工作区后历史消失」「agent 面板历史是空的」，或要求查询、统计、导出、迁移 Zed agent 会话列表时，务必使用本 skill——即使用户没提"数据库"或"sqlite"也要触发。只管理 Zed 侧的会话元数据；会话正文在 opencode 等外部 agent 自己的存储里，不归本 skill 管。
---

# Zed Agent 会话数据库操作

## 核心认知（先读这个，"丢失"几乎都不是真丢）

- 存储位置：`%LOCALAPPDATA%\Zed\db\0-stable\db.sqlite`（SQLite，WAL 模式）。表 `sidebar_threads` 是所有 agent 会话的元数据索引（含 opencode / codex-acp / claude-acp 等外部 agent 的会话）。
- **会话按 `folder_paths`（窗口打开的文件夹组合）归档**。多根工作区多个路径用换行符分隔，`*_order` 列形如 `'0,1'`。Zed 的历史列表按当前窗口的工作区组合过滤——合并或拆分项目文件夹后，会话会"分家"到不同路径键下，看起来就像丢了。
- `archived = 1` 的会话在历史列表默认隐藏。
- Zed 崩溃重启后自动恢复的窗口可能不是用户之前用的工作区组合（对照 `workspaces` 表和 `scoped_kv_store` 的 `multi_workspace_state`），又多一层"看不见"。
- 排查顺序永远是：**先查库确认数据在不在，再谈恢复**。实测绝大多数情况数据完好无损。

## 安全铁律

1. **读**：把三件套 `db.sqlite` + `db.sqlite-wal` + `db.sqlite-shm` 复制到临时目录再读副本。WAL 里往往有最新数据，只复制主文件会读到旧数据；直接连原库则有锁冲突风险。
2. **写**：必须 ① 确认 Zed 完全退出（`Get-Process | Where-Object { $_.Name -like '*zed*' }` 无结果）；② 带时间戳目录备份三件套；③ 用参数化 SQL（防路径反斜杠/换行符坑）；④ 改完执行 `PRAGMA wal_checkpoint(TRUNCATE)` 把 WAL 落盘；⑤ 重开连接复查校验。绝不在 Zed 运行时写。
3. schema 无官方保证，版本升级会迁移表结构（`migrations` 表即证据）。写库前先 `PRAGMA table_info(sidebar_threads)` 核对列名仍然存在且含义未变。

## Windows 环境实操

- 本机没有裸 `python`，统一用 `uv run -q python <script.py>`。
- PowerShell 内联引号极易炸：**一律写 .py 脚本文件再执行**，不用 `-c` 内联。
- 中文输出乱码时：`uv run -q python x.py 2>&1 | Out-File -Encoding utf8 out.txt` 后再读文件。

## sidebar_threads 关键字段

| 字段 | 说明 |
|---|---|
| `thread_id` | BLOB 16 字节，**不要改** |
| `session_id` | 外部 agent 的会话 id（opencode 形如 `ses_xxx`），正文用它去外部 agent 存储里对应 |
| `agent_id` | `opencode` / `codex-acp` / `claude-acp` 等 |
| `title` / `title_override` | 标题；`title_override` 优先显示，可为 NULL |
| `folder_paths` / `folder_paths_order` | 工作区路径组合，换行分隔 / `'0,1'` |
| `main_worktree_paths` / `main_worktree_paths_order` | 与 folder_paths 同格式，一并改 |
| `archived` | 1 = 历史列表隐藏 |
| `created_at` / `updated_at` / `interacted_at` | UTC ISO 格式字符串 |

相关表：`workspaces`（窗口/工作区状态）、`scoped_kv_store`（`namespace='agent_panel'` 按工作区存面板状态：选中 agent、last_active_thread；`multi_workspace_state` 存多根窗口组合）、`editors`/`items`（打开的文件）、`sidebar_terminal_threads`。

## 常用查询（复制即用，改条件即可）

```python
# 按项目列会话（最近优先）
select updated_at, agent_id, archived, title, folder_paths
from sidebar_threads
where folder_paths like '%<项目名>%'
order by updated_at desc;

# 路径组合分布（判断"分家"）
select folder_paths, archived, count(*) c
from sidebar_threads
where folder_paths like '%<项目名>%'
group by folder_paths, archived;

# 按标题模糊找回
select * from sidebar_threads where title like '%<关键词>%';
```

## 修复套路（实战沉淀）

症状「历史全丢失」三步定位：
1. `group by folder_paths, archived` 看会话挂在哪些路径组合、归档分布；
2. 查 `workspaces` / `scoped_kv_store.multi_workspace_state` 确认当前窗口是哪个组合、面板选中了哪个 agent；
3. 与用户确认目标布局后修复。

**路径归还模板**（把双路径会话归还单路径，Zed 已关闭 + 已备份）：

```python
COMBINED = "C:\\WorkingProjects\\aaa\nC:\\WorkingProjects\\bbb"  # 换行符分隔
SINGLE = "C:\\WorkingProjects\\aaa"
cur.execute(
    """update sidebar_threads
       set folder_paths = ?, folder_paths_order = '0',
           main_worktree_paths = ?, main_worktree_paths_order = '0'
       where folder_paths = ? and folder_paths_order = '0,1'""",
    (SINGLE, SINGLE, COMBINED),
)
con.commit(); cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
```

其它可行操作（同样遵守写库铁律）：`archived` 0/1 批量切换、`title_override` 批量改名、按 `updated_at` 清理草稿行、跨机器迁移会话（同行 BLOB 原样复制）。

## 边界（不要越界断言）

- 本库只是**元数据索引**。会话正文在外部 agent 自己的存储（如 opencode 在 `~/.local/share/opencode`）。删 Zed 侧行 ≠ 删正文；删正文 ≠ 删 Zed 行，都会产生僵尸条目。操作前向用户说明影响范围。
- 内置（原生）agent 的会话正文存储位置本 skill 未验证，不要凭空断言。
- Zed 运行时历史列表的内存态可能滞后于库；写库修复后让用户完全重启 Zed 验证。
