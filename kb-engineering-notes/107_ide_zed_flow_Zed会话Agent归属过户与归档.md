---
name: kb-zed-session-agent-adoption
description: |
  Zed 侧历史 Agent 会话的归属迁移与批量归档：把散落在官方 antigravity-acp（或任意 agent 条目）名下的
  历史会话，就地过户到自建代理条目（如 Google Antigravity (auto-title)），使其统一由共享 daemon 承载并
  复用自动标题；同时给出 sidecar 备份、dry-run 与回滚流水线。何时查阅：Zed 会话列表里混着多个 agent 条目、
  想把旧会话收编到代理名下、或需要批量归档某个 agent 的历史线程。
version: 1.0.0
id: "107"
domain: "ide"
scope: "zed"
type: "flow"
slug: "Zed会话Agent归属过户与归档"
status: "verified"
created: "2026-11-01"
last_verified: "2026-11-01"
superseded_by: null
deprecation_reason: null
compatibility:
  os: ["windows"]
falsification_signals:
  - "若 sidebar_threads 表不存在或缺少 agent_id 列，说明 Zed 存储结构已变，立即停止并按新 schema 重新取证"
  - "若目标 agent 未出现在 settings.json 的 agent_servers 中，过户后会话将无法打开，先补配置再迁移"
  - "若会话数据目录（~/.gemini/antigravity-acp/conversations/）缺少对应 <sid>.db，迁移只会得到一个空壳入口"
invocation:
  auto_trigger: true
  trigger_keywords: ["Zed 会话归属", "agent_id 迁移", "sidebar_threads", "agy threads", "会话归档", "antigravity-acp 历史会话", "Google Antigravity (auto-title)", "Zed 多 agent 分组"]
---

# ide_zed_flow_107_Zed会话Agent归属过户与归档

> **条目定位**：**Type B 方案流水线条目（Zed SQLite 会话索引改写 × agent 归属过户 × 批量归档）**
> **危险评级**：★★☆☆☆（写库前若未退出 Zed，改动会被内存缓存覆盖；误改 agent_id 会导致会话打不开，但有备份可回滚）
> **验证环境**：Windows 11、Zed（`0-stable` channel）、`acp-title-proxy` 自带 `agy threads` 子命令、Antigravity ACP 1.4.5。
> **关联条目**：ACP 代理整体架构与 Mode 拦截见 `106_agent_acp_flow_ACP代理架构与ZedMode拦截及默认YOLO安全手刹.md`；会话丢失抢救见 `025_ide_zed_fix_Zed会话丢失提取与SQLite解析抢救.md`；外部线程不自动命名见 `077_ide_zed_fix_Zed外部ACP线程不自动命名与首消息标题链路.md`。

---

## 一、业务场景与需求

同一个后端（Antigravity）在 Zed 里往往存在**两条并行的 agent 条目**：

| 条目 | 来源 | 特点 |
|---|---|---|
| `antigravity-acp` | Zed registry 官方条目 | 每个 panel 独立拉起后端，标题为占位符 |
| `Google Antigravity (auto-title)` | `settings.json` 里的 custom 代理 | 共享 daemon、自动标题、`/skill:` 注入 |

历史会话按创建时的条目落位，于是会话列表被割裂成两堆：官方名下几百条、代理名下十几条。用户想做的事有三件：

1. **归档**：把不再使用的官方条目历史线程从列表清走（可恢复，不是删除）；
2. **过户**：让旧会话改由代理条目承载，点开时走共享 daemon，而不是再起一个后端；
3. **可回滚**：任何批量写库都要有 dry-run、快照与还原路径。

> **关键认知**：归档 ≠ 过户。`archived=1` 只是从列表隐藏，点开仍然由原 agent 加载，会再起一个独立后端进程。要真正收编，必须改写归属。

---

## 二、技术难点与底层剖析

### 1. 归属只有一个落点：`sidebar_threads.agent_id`

Zed 的会话索引在 `%LOCALAPPDATA%\Zed\db\0-stable\db.sqlite`，核心表只有一张：

```text
sidebar_threads(
  thread_id BLOB PRIMARY KEY,   -- 索引行主键，可随意新建
  session_id TEXT,              -- 外部锚点，永不修改
  agent_id TEXT,                -- ★ 归属：取值就是 settings.json 里 agent_servers 的键名
  title TEXT, title_override TEXT,
  archived INTEGER,             -- 0/1，UI 的“归档”
  folder_paths TEXT, updated_at TEXT, ...
)
```

实测该库里 `agent_id` 同时存在 `antigravity-acp`（官方）与 `Google Antigravity (auto-title)`（custom），**后者证明 custom 条目直接以人可读的名字入库**，不需要额外映射表。

### 2. 对话正文不在 Zed 本地

整库 37 张表，没有任何 ACP 消息表。Zed 打开一个历史线程时，一律向 agent 发 `session/load`，由 agent 侧回放 `session/update`。因此改 `agent_id` 不会丢内容——内容从来就不在 Zed 这边。

### 3. 过户能成立的三个前提（缺一不可）

```text
① session_id 不变          → Zed 用它定位会话
② 后端读同一份会话库        → agy: ~/.gemini/antigravity-acp/conversations/<sid>.db
③ agent 声明 loadSession    → initialize 返回 loadSession: true，Zed 才会走 load 回放
```

实测对官方条目创建的 session 直连代理发 `session/load`，返回 `configOptions/models/modes` 并回放 22 个 `tool_call` + 22 个 `tool_call_update`，历史完整。

### 4. `session/load` 与 `session/resume` 不能混用

| 方法 | 结果 | 是否回放历史 |
|---|---|---|
| `session/load` | 成功 | ✅ 回放完整 `session/update` |
| `session/resume` | 成功 | ❌ 静默返回，无任何通知 |

agy 的 `sessionCapabilities` 里只声明了 `resume`，但 `agentCapabilities.loadSession = true`。Zed 依据后者走 `load`，所以**别被 sessionCapabilities 的字段名误导**——判断标准是 `loadSession` 布尔值。

### 5. 写库必须独占：Zed 有内存缓存

Zed 启动时把线程元数据读进内存，运行期以内存为准回写。Zed 开着改库，退出时会被覆盖，表现为“改了没生效”或“改完更乱”。因此写前必须 `tasklist` 确认 `Zed.exe` 已全部退出。

---

## 三、标准自动化流水线

`acp-title-proxy` 内置 `agy threads` 子命令（`internal/zedthreads` + `cmd/acp-title-proxy/threads.go`），三个动作全部**默认 dry-run**。

### 1. 体检：先看分布（Zed 开着也能跑，只读）

```powershell
cd D:\Users\language_projects\go_projects\acp-title-proxy
.\bin\acp-title-proxy.exe agy threads list
```

典型输出（真实数据）：

```text
AGENT                                    TOTAL  ACTIVE  ARCHIVED  NO-SID  LAST
antigravity-acp                            237     110       127       9  2026-11-01 06:31
Google Antigravity (auto-title)             19      10         9       5  2026-11-01 07:05
```

`NO-SID` 是无 `session_id` 的空 thread（新建未发消息），没有会话可载，迁移时应跳过。

### 2. 先迁 1 条验证（强烈建议）

```powershell
# 完全退出 Zed 后
.\bin\acp-title-proxy.exe agy threads adopt --limit 1 --apply
```

然后打开 Zed，切到目标 agent 条目，点开那条会话：历史消息、工具调用、继续追问都应正常。**这一步是唯一能验证 Zed 完整链路的环节，别跳过。**

### 3. 全量过户 + 清理空 thread

```powershell
.\bin\acp-title-proxy.exe agy threads adopt --apply                 # 迁剩余的全部
.\bin\acp-title-proxy.exe agy threads archive --agent antigravity-acp --apply
```

第二条只归档“仍挂在该条目下、且未归档”的行——过户走完后就只剩那批无 `session_id` 的空 thread。

### 4. 写库安全链路（工具内部实现）

```text
进程检查 → VACUUM INTO 一致性快照 → 单事务 UPDATE → wal_checkpoint(PASSIVE) → 复查
```

- 快照落在 `%APPDATA%\language_projects\acp-title-proxy\backups\threads-<时间戳>\db.sqlite`；
- 用 `VACUUM INTO` 而不是复制文件，是因为它自动合并 `-wal`，得到一个自洽单文件；
- 事务按 `thread_id`（BLOB）逐行更新，不用 `session_id` 做条件，避免同会话多入口时误伤。

### 5. 回滚

```powershell
$bak = Get-ChildItem "$env:APPDATA\language_projects\acp-title-proxy\backups\threads-*" |
       Sort-Object Name -Descending | Select-Object -First 1
Copy-Item "$($bak.FullName)\db.sqlite" "$env:LOCALAPPDATA\Zed\db\0-stable\db.sqlite" -Force
Remove-Item "$env:LOCALAPPDATA\Zed\db\0-stable\db.sqlite-wal",
            "$env:LOCALAPPDATA\Zed\db\0-stable\db.sqlite-shm" -ErrorAction SilentlyContinue
```

必须连 `-wal`/`-shm` 一起删，否则旧 WAL 会把恢复出来的库再次覆盖。

---

## 四、交付验证与扩展建议

### 验证断言

| 检查项 | 期望 |
|---|---|
| `agy threads list` | 目标 agent 的 ACTIVE 数增加对应条数，源 agent 的 ACTIVE 归零 |
| Zed 会话列表 | 旧会话出现在目标条目下，标题保持不变 |
| 点开旧会话 | 历史消息完整、可继续提问、无“连接丢失”提示 |
| 进程视角 | 全局仍只有一个 `agy_acp_server`（共享 daemon 生效） |

### 三条容易踩空的认知

1. **过户不降内存**。每个被打开的会话仍有独立 `localharness`（约 110–170MB），省掉的是重复的 `agy_acp_server` 实例（约 190MB/份）。别把“统一归属”当成“内存优化”。
2. **标题不会被重写**。自动标题只在 `session/new` 触发，`session/load` 不触发，旧会话保留原 `title` / `title_override`。
3. **官方条目不要删**。`settings.json` 里保留 `antigravity-acp` 条目，代理出问题时还能退回官方入口；只是不再有活跃线程挂在它名下。

### 扩展方向

- **双向迁移**：同一套 `adopt` 逻辑可反向执行（代理 → 官方），排查代理问题时用得上；
- **与 zedhub 的 `sessions link` 合并**：后者解决“会话不在 Zed 索引里”，本条目解决“在索引里但归属不对”，两者都只动 `sidebar_threads`，可收敛成一个会话运维入口；
- **跨机迁移**：`session_id` 不变 + `conversations/<sid>.db` 整文件搬运，即可把会话带到另一台机器后重新登记。
