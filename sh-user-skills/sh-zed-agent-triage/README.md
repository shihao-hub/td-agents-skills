---
name: sh-zed-agent-triage
description: 排障：Zed Agent Panel 报 Internal error/Invalid request/Session is closing 等 agent 侧错误的定位归因：telemetry.log 事件定位 agent 与线程、Zed.log 拿绝对时间、进程 StartTime 与锁文件时间线对齐；含 codex-acp thread-writer-lock 竞态速查。点名使用
version: 1.0.0
---

# sh-zed-agent-triage：Zed Agent Panel 报错定位与归因

沉淀自 2026-09-25 实战：Zed Agent Panel 报 `Internal error: {"details": "thread <uuid> already has an active writer"}`（agent=codex-acp / codex-cli 0.154.0），从界面一句错误定位到上游进程竞态，全程实证。

适用：Zed 里外部 agent（codex-acp/opencode/claude-acp/antigravity-acp）面板报错、turn 失败、线程打不开或行为异常，需要定位是哪个组件、哪次交互、什么根因。登录/代理/CA/env 类问题走 sh-zed-acp-agent-env；Zed 自身会话库查证走 sh-zed-session-db。

## 数据源速查

| 数据源 | 路径 | 用途 |
|---|---|---|
| Zed 遥测事件 | `%LOCALAPPDATA%\Zed\logs\telemetry.log` | `Agent Panel Error Shown`（agent 名 + session/thread id + 原始 message + acp_error_code）、`Agent Thread Started`、`Agent Message Sent`、`Agent Turn Completed`（status=failure 与耗时） |
| Zed 主日志 | `%LOCALAPPDATA%\Zed\logs\Zed.log` | `WARN [agent_servers::acp] agent stderr: ...` 行 = agent 进程 stderr 原文，带绝对时间戳（时间锚点） |
| Zed 线程库 | `%LOCALAPPDATA%\Zed\threads\threads.db` | Zed 侧线程元数据（详见 sh-zed-session-db） |
| 外部 agent 注册表 | `%LOCALAPPDATA%\Zed\external_agents\registry\<agent>\v_*\` | 进程路径归属判断（只处置这棵树下的进程，防误杀） |
| codex 侧 | `~/.codex/` | `session_index.jsonl`（thread id ↔ 名称/时间）、`sessions/YYYY/MM/DD/rollout-<ts>-<thread>.jsonl`、`thread-writer-locks/`（每 thread 单写者锁）、`logs_2.sqlite` |
| opencode 侧 | `~/.local/share/opencode/log/opencode.log` | opencode agent 行为日志 |

## 定位流程

1. **排除自产代码**：错误原文先在当前仓库/项目源码里 grep，命中不了再进入宿主工具排查。
2. **telemetry 定位主体**：在 telemetry.log 里搜错误串关键字 → 拿 agent 名、session/thread uuid、前后事件链（Thread Started / Message Sent / Turn Completed status）。
3. **Zed.log 拿绝对时间**：用 thread id 或错误串搜 Zed.log；`agent stderr:` 行给出精确时间戳与底层错误原文（如 `RequestError: Invalid request`）。
4. **进程与文件时间对齐**：`Get-Process <agent-exe> | Select Id,StartTime,Path` + 锁文件/rollout 文件 mtime → 判断哪个进程、何时、持有什么资源。
5. **归因输出**：上游竞态 / 配置 / 账号资格 / 模型能力，并给处置建议。

## 实战样例（writer-lock 案时间线）

| 时间(+08) | 事件 |
|---|---|
| ~02:36 | 向 codex 线程 01a0cefd 发图 → `The current model does not support image input`，turn 486ms 失败 |
| 02:37:37 | Zed.log：`Prompt for session 01a0cefd failed: RequestError: Invalid request` |
| ~02:37 | 新建线程 → `Session 01a0cefd is closing`（旧 codex 会话仍在关闭中） |
| 02:38:05 | 新 codex.exe 启动，被要求 attach 同一 thread |
| ~02:38 | `thread 01a0cefd already has an active writer` ×2（旧 writer 未释放） |
| ~02:40+ | 旧进程释放 → 同 session 的 tool call 恢复正常（自愈） |

## 已知错误速查

| 错误 | 根因 | 处置 |
|---|---|---|
| `Internal error: {"details": "thread <uuid> already has an active writer"}`（codex-acp） | codex 每 thread 单写者（`~/.codex/thread-writer-locks/<uuid>.lock`）；turn 失败后快速新建/重启会话，旧进程 writer 未释放，新进程 attach 同一 thread 冲突 | 多数自愈；持续卡死 → 关对应线程或按 registry 路径过滤结束残留 `codex.exe`；lock 为 flock 型（进程退出自动释放），0 字节残留属正常勿手删；预防：turn 失败后等几秒再新建线程、发图换支持视觉的模型 |
| `The current model does not support image input` | 当前 codex 模型无视觉能力 | 换视觉模型或撤图 |
| `Session <uuid> is closing` | ACP 会话异步关闭中收到新请求 | 稍等重试；频发是 writer-lock 竞态前兆 |

## 坑

- **opencode.log 会回显自己的 grep 命令**（权限评估记录含命令原文）→ 搜错误串时排除 `message=evaluated` 行，别把自己的搜索当命中。
- **telemetry.log 无绝对时间**（`milliseconds_since_first_event` 相对值且会归零重计）→ 时间锚点一律用 Zed.log。
- Zed 复用后台 agent 进程，同种 agent 可多进程共存；**StartTime 与配置/锁文件 mtime 对齐**才能锁定嫌疑进程；结束进程按 registry 路径过滤防误杀。
