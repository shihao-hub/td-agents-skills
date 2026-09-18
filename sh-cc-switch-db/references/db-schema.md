# cc-switch 数据库 Schema（实测于 v3.20.0，2026-09-06）

库：`~/.cc-switch/cc-switch.db`。用 node 操作：

```js
import { DatabaseSync } from 'node:sqlite';
const db = new DatabaseSync(dbPath, { readOnly: true }); // 探查一律 readOnly
```

## 表清单（18 张）

| 表 | 用途 |
|---|---|
| **providers** | 核心：各应用段供应商条目，主键 `(id, app_type)` |
| **provider_endpoints** | 每供应商一条端点记录（测速/展示用） |
| settings | 各应用通用配置（common_config_* 等 key/value） |
| mcp_servers | 统一 MCP 服务器定义 + 各应用启用标志 |
| prompts | 提示词模板 |
| skills / skill_repos | 技能仓库管理 |
| profiles | 配置文件（Profiles） |
| proxy_config | 各应用代理/故障转移配置 |
| proxy_request_logs / proxy_live_backup | 代理请求日志与接管备份 |
| provider_health | 供应商健康状态（连续失败计数等） |
| stream_check_logs | 流式检测日志 |
| model_pricing | 模型定价表（计费用） |
| session_log_sync / session_usage_dedup | 会话用量同步与去重 |
| usage_daily_rollups | 每日用量汇总 |
| sqlite_sequence | SQLite 自增内部表 |

## providers 表（核心）

列：`id, app_type, name, settings_config, website_url, category, created_at, sort_index, notes, icon, icon_color, meta, is_current, in_failover_queue, cost_multiplier, limit_daily_usd, limit_monthly_usd, provider_type`

| 列 | 说明 |
|---|---|
| id + app_type | 联合主键。Switch 型应用 id 是 UUID；**Additive 型（opencode/pi 等）id 是 providerKey slug**（如 `zhipu-glm`） |
| app_type | 已见取值：`claude` `claude-desktop` `codex` `gemini` `opencode` `pi`；mcp_servers/skills 表的 enabled_* 列还预留 `hermes` `grokbuild` |
| settings_config | JSON 文本，**形状随 app_type 完全不同**，见 app-config-shapes.md |
| created_at | 毫秒时间戳 |
| sort_index | 段内排序（新增取该段 MAX+1） |
| category | `official` / `custom` / `cn_official` 等；official 是 OAuth 型通常无法搬 |
| icon / icon_color | UI 图标（如 `zhipu` / `#0F62FE`；pi 段导入默认 `pi`） |
| meta | JSON 文本，见下节 |
| is_current | 当前激活（Additive 段语义弱，成员=存在性） |
| in_failover_queue | pi 段强制 0（不支持故障转移队列） |
| cost_multiplier | TEXT '1.0'（注意是字符串） |
| limit_daily_usd / limit_monthly_usd / provider_type / notes / website_url | 通常 NULL |

## meta JSON 已知字段

```json
{
  "usage_script": {            // 余额/用量查询脚本
    "enabled": true, "language": "javascript", "code": "",
    "timeout": 10, "templateType": "token_plan",
    "autoQueryInterval": 5, "codingPlanProvider": "zhipu"
  },
  "endpointAutoSelect": true,  // 端点自动选择
  "liveConfigManaged": true    // opencode 段：与 opencode.json 双向同步，两侧必须一致（尤其 name）
}
```

注意：pi 段保存时 cc-switch 会剥离不支持的 meta 键（只留 usage_script / is_partner / partner_promotion_key）。

## provider_endpoints 表

`id(自增), provider_id, app_type, url, added_at(毫秒)`。新增供应商时通常补插一条。不插也不影响功能（部分段没有）。

## 外键约束（2026-09-14 实测，改 id 前必读）

`provider_endpoints` 和 `provider_health` 都带指向 `providers(id, app_type)` 的外键（SQLite FK 强制开启）。**直接 `UPDATE providers SET id=...` 会报 `FOREIGN KEY constraint failed`**——事务内无论先改主表还是先改子表都有一侧违规：

```js
db.exec('PRAGMA defer_foreign_keys = ON'); // BEGIN 前设置：FK 延迟到 COMMIT 统一校验
db.exec('BEGIN');
db.prepare('UPDATE providers SET id=? WHERE app_type=? AND id=?').run(newId, app, oldId);
db.prepare('UPDATE provider_endpoints SET provider_id=? WHERE app_type=? AND provider_id=?').run(newId, app, oldId);
db.prepare('UPDATE provider_health SET provider_id=? WHERE app_type=? AND provider_id=?').run(newId, app, oldId);
db.exec('COMMIT');
db.prepare('PRAGMA foreign_key_check').all(); // 必须返回 []
```

替代方案是"INSERT 新行 + 子表改指向 + DELETE 旧行"三步（无中间违规），但 defer FK 一条路更直。删行同理：先删子表行再删主表行（cc-add-provider/del 类脚本已有此序）。`proxy_request_logs` 无外键（历史日志），残留旧 id 无害。

## settings 表已知键（key/value，value 多为 JSON 文本）

| key | 内容 |
|---|---|
| common_config_claude / common_config_codex / common_config_opencode | 各应用"通用配置"（切供应商时合并写入） |
| official_providers_seeded / *_legacy_migrated_v1 / default_skill_repos_initialized | 迁移标记位 |

## 同步模式：Switch vs Additive

- **Switch 型**（claude/codex/gemini 等）：仅当前激活供应商写入目标应用生效配置（单一生效语义）。
- **Additive 型**（opencode/pi/openclaw/hermes）：多供应商共存于原生配置文件，cc-switch 只写单个 provider 条目不覆盖整个文件；**跳过实时同步管道**。

## 写库安全规约（模板）

1. 备份整库到 `~/.cc-switch/backups/`。
2. 退出 cc-switch（`Get-Process cc-switch` / `Stop-Process -Name cc-switch -Force`）。
3. 事务包裹 INSERT/UPDATE，异常 ROLLBACK。
4. 写后回读：SELECT 目标行，`JSON.parse(settings_config)` 与源 JSON 深比较。
5. 提醒重启 cc-switch（运行实例不热加载）。
