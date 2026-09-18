# cc-switch 迁移设计（SQLite 版 cc-switch，实测于 2026-08-28）

## 数据位置与表结构

库：`~/.cc-switch/cc-switch.db`。用 node 操作（PATH 里的 python 可能是商店 stub）：
```js
const { DatabaseSync } = require("node:sqlite");
const db = new DatabaseSync(dbPath, { readOnly: true }); // 探查一律 readOnly
```

### providers 表（主键 `(id, app_type)`）
关键列：`id, app_type('claude'|'opencode'|'codex'|…), name, settings_config(JSON文本), category, created_at(毫秒), sort_index, icon, icon_color, meta(JSON文本), is_current, in_failover_queue, cost_multiplier(默认'1.0'), website_url, provider_type`

### settings_config 形状（按 app_type）
- **claude 段**：`{"env": {"ANTHROPIC_AUTH_TOKEN": "sk-...", "ANTHROPIC_BASE_URL": "https://.../"}}`（智谱条目会多一排 ANTHROPIC_*_MODEL 环境变量）
- **opencode 段**：就是写进 opencode.json `provider.<id>` 的完整 JSON（npm/name/options/models）
- `meta` 里 `liveConfigManaged: true` 表示与 opencode.json 双向同步——两侧 name 等字段必须一致

### provider_endpoints 表
每供应商一条端点记录：`(provider_id, app_type, url, added_at)`。新增供应商时要补插。

**名称约定**：标识（id）用 slug；显示名是用户偏好，迁移时**沿用 claude 段的名字、不强制改成标识**（除非用户明确要求）。

## 迁移算法（cc-switch-migrate.mjs）

1. 读 claude 段全部条目，过滤出中转型（settings_config.env 里同时有 AUTH_TOKEN 和 BASE_URL 的）。
2. 对每个中转：
   - 已存在于 opencode 段（id 相同）→ **更新**：name 改为 id、settings_config 换成新模板（保留原 token/baseURL 派生值）
   - 不存在 → **插入**：id/name 用 claude 段的名字（slug 风格），settings_config 按模板生成
3. 模板（Claude 中转 → opencode）：
   ```js
   {
     npm: "@ai-sdk/anthropic",
     name: <id>,
     options: { baseURL: <ANTHROPIC_BASE_URL 去尾斜杠 + "/v1">, authToken: <token> },
     models: { claude-opus-5: MODEL, claude-sonnet-5: MODEL }
   }
   // MODEL = { name: <模型id>, limit:{context:1e6,output:128000},
   //           options:{effort:"max"}, reasoning:false,
   //           variants:{low/medium/high/xhigh/max 全部 {disabled:true}} }
   ```
   注意：claude 段 BASE_URL 是 `https://xxx/`，opencode 需要 `https://xxx/v1`。
4. 跳过：`category='official'`（OAuth 型，无法搬）、opencode 段已有的 zhipu-glm（避免与 coding 端点版本重复）。
5. 元数据照抄同型条目：icon=anthropic / #D4915D、meta=`{"endpointAutoSelect":true,"liveConfigManaged":true}`、is_current=0、cost_multiplier='1.0'。

## 安全规约（脚本内置）

- **默认 dry-run**：只打印计划（新增谁/改谁/跳过谁），不写库；`--apply` 才写。
- 写前自动备份：整库复制到 `~/.cc-switch/backups/cc-switch-before-migrate-<时间戳>.db`。
- 全部语句包在一个事务里，异常 ROLLBACK。
- 写后回读验证：列出 opencode 段全部条目，核对 name==id、models 的 variants 全禁用。
- 提醒用户**重启 cc-switch**（运行中的实例不热加载）。

## 回滚

把备份文件复制回 `~/.cc-switch/cc-switch.db`（先关 cc-switch）。
