---
name: kb-cc-switch-db
description: 直接读写 cc-switch 的 SQLite 数据库，绕过 UI 批量配置与跨应用模型供应商迁移指南。
version: 1.2.0
created: 2026-09-06
updated: 2026-10-20
---

# cc-switch 配置 SQLite 直接读写与跨应用模型迁移指南

沉淀自 2026-09-06 实操（cc-switch v3.20.0，Windows，SQLite 版），关键结论经源码交叉验证（farion1231/cc-switch）。cc-switch 升级后表结构可能变化——用 `cc-db.mjs tables` 先核对再动手。
2026-09-14 增补：改既有条目/改 id 两脚本（cc-update-provider-config / cc-rename-provider-id）、**providers.id 外键坑**（见总原则 9）、DeepSeek→opencode 段默认 max 实战案例（app-config-shapes.md）。
2026-09-21 增补：opencode 段模型级 `limit` 坑——自定义 provider 的 `limit.context=0` 会让 Zed 永不显示上下文指示器（limit 不从 models.dev 合并；机制、实测值与修法见 sh-zed-opencode-setup 任务 B2）。实战用 `cc-update-provider-config.mjs` 同步 zhipu-glm / deepseek-max 两条 settings_config。
2026-09-23 增补：codex 段代理翻译坑——`meta.apiFormat` 决定本地代理透传还是翻译（GLM 无 `/responses`，必须 `openai_chat` + `codexChatReasoning`）；模型目录 `modelCatalog.inputModalities` 控制 Codex 应用贴图能力；新增 `cc-update-meta.mjs`（改 meta 通用脚本）。
2026-09-24 增补：**codex 段思考深度坑**——GLM-5.3/flash 始终思考、`thinking.type` 仅 `enabled`，深度唯一参数是 `reasoning_effort`（low/high/max，默认 max）；chat 翻译路径**必须** `supportsEffort:true` + `effortParam:"reasoning_effort"`，否则档位静默失效（只发 thinking，从不发 effort；UI 开关从关闭切到打开也不会自动补 `effortParam`）。另：cc-switch **公共配置** `settings.common_config_codex` 里的 `model_reasoning_effort` 会合并进 live config.toml、覆盖 catalog 默认档位，CLI 默认档位要改这里（直接改 live 文件会被接管/异常退出恢复覆盖）。原生 Responses 端点是 `https://open.bigmodel.cn/api/v1`（官方预设路径），与 chat 端点 `/api/coding/paas/v4` 协议不互通。
2026-09-25 增补：**DeepSeek 官方 Codex 原生透传与识图多模态避坑**——DeepSeek 官方规范（`wire_api="responses"` + `https://api.deepseek.com`）由 `meta.apiFormat="openai_responses"` 直通代理层，免 chat 翻译；多模态识图必须在 catalog 中显式声明 `"inputModalities": ["text", "image"]`（否则 Codex 禁用贴图）；第三方网关（如 OpenCode Go）中的 `deepseek-v4-flash` 实测为纯文本模型（发图 400），多模态模型名必须为 `deepseek-flash`；严禁在 CC Switch 环境中运行官方 `codex-deepseek-setup.ps1` 脚本覆写 `config.toml`。详见 `references/deepseek-codex-integration.md`。
2026-10-19 增补：**密钥轮换 SOP 与 cc-switch 回写反噬**——`cc-update-provider-config.mjs` 新增 `--set <dotted.path>=<value>` 定点改字段（不再需要落临时 JSON），换 token 一条命令搞定；**实测被回滚案例**：改库双写成功后，隔日 cc-switch 启动把 `providers.settings_config` 与投影文件 `~/.claude/settings.json` **一起**重写回旧 key（两文件 mtime 同一秒），故新增任务 D 流程。另：只按 `cc-switch.exe` 探测进程会假阴性（真实镜像名含空格），见环境表。
2026-10-20 增补：**OpenCode 官方供应商 npm 校验死锁与恢复 SOP**——官方直连 provider（如 DeepSeek）在被移出 `opencode.json` 或放入 `disabled_providers` 后，CC Switch 依据 live config 做二元判定将其视作“新自定义供应商”，点击 `+` 触发强制校验报错（`A new OpenCode provider ID requires an npm package and at least one model; only an existing ID in the live config may inherit defaults`；源码 `live.rs`）；破局无需在 UI 折腾，直接在 `opencode.json` 移除黑名单并补齐 provider，`auth.json` 注入 key，CC Switch 热感知后即自动移入“已添加”。见任务 G。

## 总原则（每次先读）

1. **探查一律只读**：`new DatabaseSync(path, { readOnly: true })`，绝不无备份写库。
2. **写库前必备份**：整库复制到 `~/.cc-switch/backups/`（脚本自动做，也要会手工做）。
3. **写真实库前退出 cc-switch**：运行中的实例持有配置内存态且不热加载，写库会冲突或被覆盖。`Get-Process cc-switch` 检查，`Stop-Process -Name cc-switch -Force` 结束。
4. **默认 dry-run，用户确认后 --apply**：先打印将要写入的完整行，确认与预期一致再写。事务包裹，失败 ROLLBACK，写后回读验证。
5. **写完提醒用户重启 cc-switch**；涉及 opencode 段的还要注意 opencode.json 双向同步（见 sh-zed-opencode-setup）。
6. **用 node 不用 python**：PATH 里的 python 可能是 Windows 商店 stub（静默失败）；node v22+ 自带 `node:sqlite`（DatabaseSync）。
7. **PowerShell 内联转义坑**：`node -e "..."` 里的单引号 SQL 常被吃掉。复杂查询写成临时 .mjs 脚本执行，或用 `String.fromCharCode(39)` 代替引号。另：PowerShell 5.1 `Set-Content -Encoding UTF8` 写出的 JSON **带 BOM**，`JSON.parse` 会挂——读 JSON 文件先 `replace(/^\uFEFF/, '')`（本 skill 脚本已处理）。
8. **测试写操作用沙箱**：复制一份 db 到临时目录，脚本传 `--db <沙箱路径>`，验证通过再对真实库执行。
9. **改 providers.id 会触发外键**（2026-09-14 实测）：`provider_endpoints` 和 `provider_health` 都引用 `providers(id, app_type)`，事务内无论先改主表还是先改子表都会立即违规。解法：`BEGIN` 前执行 `PRAGMA defer_foreign_keys = ON`（提交时统一校验），主表+两张子表一起改，COMMIT 后跑 `PRAGMA foreign_key_check` 核验——`cc-rename-provider-id.mjs` 已内置此流程。

## 环境路径（按机器解析）

| 项 | 路径 |
|---|---|
| cc-switch 数据库 | `~/.cc-switch/cc-switch.db`（SQLite，表 `providers` 主键 `(id, app_type)`） |
| 备份目录 | `~/.cc-switch/backups/` |
| cc-switch 程序 | 每用户安装，可能在非 C 盘（实测 `D:\Users\<user>\AppData\Local\Programs\CC Switch\cc-switch.exe`）。**探测别只 match `cc-switch.exe`**：镜像名可能是 `CC Switch.exe`（带空格），`tasklist /FI "IMAGENAME eq cc-switch.exe"` 会假阴性并导致"以为没运行"从而白改库。用 `Get-Process \| Where-Object ProcessName -match '(?i)cc.?switch'` 或 `Get-CimInstance Win32_Process` 同名过滤 |
| opencode 配置 | `~/.config/opencode/opencode.json`（Additive 联动，见 sh-zed-opencode-setup） |
| pi 配置 | `~/.pi/agent/`：`models.json`（cc-switch 唯一管理的文件）、`settings.json`、`auth.json`（cc-switch 绝不碰） |

## 快速上手：脚本

```bash
# 只读探查 + 备份（默认连真实库，--db 可指向沙箱副本）
node scripts/cc-db.mjs tables                    # 全部表 + 行数 + 列名
node scripts/cc-db.mjs list [app_type]           # 供应商列表
node scripts/cc-db.mjs show <app_type> <id>      # 单条完整行（settings_config/meta 已解析）
node scripts/cc-db.mjs settings                  # settings 表全量
node scripts/cc-db.mjs endpoints [app_type]      # provider_endpoints 表
node scripts/cc-db.mjs backup                    # 备份到 ~/.cc-switch/backups/

# 通用新增供应商（任意 app 段；默认 dry-run，--apply 写库）
node scripts/cc-add-provider.mjs --app pi --id zhipu-glm --config cfg.json \
  --name "Zhipu GLM" --endpoint https://... [--icon zhipu --icon-color '#0F62FE' \
  --category cn_official --meta meta.json --db 沙箱.db --apply]

# 改既有条目的 settings_config（任意 app 段；默认 dry-run）
node scripts/cc-update-provider-config.mjs --app opencode --id deepseek-max --config cfg.json [--db 沙箱.db --apply]

# 定点改单个字段（--set 可重复；value 先按 JSON 解析，失败当字符串；基底为库中现值）
node scripts/cc-update-provider-config.mjs --app claude --id <id> \
  --set env.ANTHROPIC_AUTH_TOKEN=<新key> [--db 沙箱.db --apply]

# 改既有条目的 meta（任意 app 段；默认 dry-run）
node scripts/cc-update-meta.mjs --app codex --id <id> --meta meta.json [--db 沙箱.db --apply]

# 改供应商 id（providers 主键 + provider_endpoints/provider_health 外键一起迁移；内置 defer FK）
node scripts/cc-rename-provider-id.mjs --app opencode --from deepseek-official --to deepseek-max [--db 沙箱.db --apply]
```

## 任务 A：只读探查

先 `cc-db.mjs tables` 核对表结构（防版本变化），再 `list`/`show` 定位目标条目。各表用途与列语义见 `references/db-schema.md`。改任何东西前，把目标行的 `show` 输出留存作为参照。

## 任务 B：新增供应商到任意 app 段

1. `cc-db.mjs backup` 备份。
2. 按目标段的 `settings_config` 形状准备 JSON（**各段形状完全不同**，速查 `references/app-config-shapes.md`：claude 段是 env 块、codex 段是 auth+TOML、opencode 段是完整 provider JSON、pi 段是 models.json provider 节点）。
3. 沙箱自测：复制 db 到临时目录，`cc-add-provider.mjs ... --db 沙箱.db --apply`，`cc-db.mjs show ... --db 沙箱.db` 回读验证。
4. 退出 cc-switch，对真实库 `--apply`，回读一致性确认。
5. 提醒用户重开 cc-switch 验证 UI 显示。

## 任务 C：Pi 段专属机制（重点坑）

- **cc-switch 对 pi 只管 `~/.pi/agent/models.json`**（Additive 模式：多个 provider 共存于该文件，按存在性即成员）。DB 的 `settings_config` = 写入该文件的 provider 节点（`name/baseUrl/apiKey/api/models[]/modelOverrides`）。
- **cc-switch 绝不碰 pi 的 `settings.json` / `auth.json`**（源码测试明确保证）。所以 pi 的默认模型/默认思考档位等改动必须直接编辑 `~/.pi/agent/settings.json`，cc-switch 帮不上。
- **models.json 是权威数据源**：cc-switch 打开 Pi 段时会把 models.json 同步回 DB（native 优先）。DB 与 models.json 内容保持一致可避免 sync 抖动。
- **pi 默认思考档位**：settings.json 的 `defaultThinkingLevel`（全局）或 `modelThinkingLevels`（按 `"provider/modelId"` 键精准覆盖）；级联后 clamp 到模型 `thinkingLevelMap` 能力。模型定义没有 reasoningEffort 这类请求参数字段——与 opencode 的机制完全不同，不能照搬。
- 完整实战案例（Zhipu GLM → pi 段 + 默认思考 max）见 `references/app-config-shapes.md`。

## 任务 D：备份与回滚

```powershell
# 备份
Copy-Item "$env:USERPROFILE\.cc-switch\cc-switch.db" "$env:USERPROFILE\.cc-switch\backups\cc-switch-<时间戳>.db"
# 回滚（先关 cc-switch）
Copy-Item "<备份文件>" "$env:USERPROFILE\.cc-switch\cc-switch.db" -Force
```

## 任务 E：Codex 段代理翻译与模型目录（2026-09-23~24 实战）

cc-switch 开本地代理（`enableLocalProxy`）后 codex live 配置被接管：`base_url=http://127.0.0.1:15721/v1` + `wire_api="responses"` + `experimental_bearer_token="PROXY_MANAGED"`，上游实际发什么由 provider `meta` 决定：

- `meta.apiFormat="openai_responses"` → 代理透传 `{base_url}/responses`（上游须原生支持 Responses API）
- `meta.apiFormat="openai_chat"` → 代理把 Responses 请求翻译成 `{base_url}/chat/completions`，响应转回；推理映射看 `meta.codexChatReasoning`

**智谱 GLM 两个协议分立的端点**：chat 端点 `https://open.bigmodel.cn/api/coding/paas/v4`（只有 `/chat/completions`，打 `/responses` 实测 404）、原生 Responses 端点 `https://open.bigmodel.cn/api/v1`（cc-switch 官方预设走这条，`apiFormat=openai_responses`）。两套协议不互通（`/api/v1/chat/completions` 实测 403 model_access_denied）。`provider_endpoints` 混挂两个不同协议候选 + `endpointAutoSelect=true` 是坑：自动选到不匹配的端点就 404/403。

走 chat 翻译（`apiFormat=openai_chat`）时 **`codexChatReasoning` 必须开 effort 转发**，否则 Codex 选任何档位都只发 `thinking:{type:"enabled"}`、`reasoning_effort` 一个都不发（源码 `transform_codex_chat.rs::apply_reasoning_options`：`!supports_effort` 直接 return）：

```json
"codexChatReasoning": {
  "supportsThinking": true,
  "supportsEffort": true,
  "thinkingParam": "thinking",
  "effortParam": "reasoning_effort",
  "outputFormat": "reasoning_content"
}
```

UI 上把「支持 effort」开关从关闭切到打开**不会**自动修好——handler 是 `effortParam: checked ? (effortParam ?? "reasoning_effort") : "none"`，旧值 `"none"` 非 null 会原样保留；必须显式改成 `"reasoning_effort"`（翻译层只认 `reasoning_effort` / `reasoning.effort`，其他值走 `_ => {}` 不写）。GLM 思考语义：始终开启、`thinking.type` 仅 `enabled`（不能禁用），深度 = `reasoning_effort`（low/high/max，默认 max）；实测经代理 low≈15-20 / medium≈94-138 / high≈1600-1900 / max≈1200-2500 reasoning tokens。chat 端点对非法值静默忽略，原生 `/api/v1/responses` 严格校验（非法值 400，合法枚举 none/minimal/low/medium/high/xhigh/max）。

排查：直连上游对比 `/responses` vs `/chat/completions` → `curl` 代理 `http://127.0.0.1:15721/v1/responses` → `tail ~/.cc-switch/logs/cc-switch.log | grep '\[Codex\] >>> 请求目标'` 看实际转发。

`modelCatalog.models[].inputModalities` 控制 Codex 应用贴图（`["text","image"]`；能力先直连 API 实测，智谱 glm-5.3-flash ✅ / glm-5.3 ❌ 报 1210）；改完 settings_config 重启 cc-switch 会重新生成 `~/.codex/cc-switch-model-catalog.json`，Codex 应用还需重启重载。改 meta 用 `cc-update-meta.mjs`（dry-run/备份/回读）。完整字段表与验证命令见 `references/app-config-shapes.md` codex 段。

**公共配置会覆盖 catalog 默认档位**（2026-09-24 实测）：`settings` 表 `common_config_codex` 的 TOML 会合并进每个 codex 供应商的 live config。里面若有 `model_reasoning_effort`，它会覆盖 model catalog 的 `default_reasoning_level`（影响 CLI/读 config.toml 的客户端；Desktop 用自选档位、Zed 用自身设置）。直接改 `~/.codex/config.toml` 会在 cc-switch 接管或异常退出恢复时被覆盖——要持久改必须改 `common_config_codex`（settings 表）。

## 任务 F：密钥轮换（换 API Key / token）

最常做的一件事，但有反噬风险，按顺序走：

1. **先确认 cc-switch 已退出**——用环境表里的 `ProcessName -match '(?i)cc.?switch'` 探测，别只试 `cc-switch.exe`。运行中的实例会把内存态刷回库，改完等于白改（本坑已踩过两次）。
2. `node scripts/cc-db.mjs list claude` 取目标 provider 的 `id`。
3. 沙箱试写：`cp ~/.cc-switch/cc-switch.db $TEMP/sandbox.db`，对沙箱 `--apply` 后回读，确认 token 变了而 `ANTHROPIC_BASE_URL` / 模型名 / effort 等**其余字段全部保留**（`--set` 是深合并不是整体替换，这一点靠这步兜底）。
4. 对真实库 `--apply`（脚本自带备份 + 事务 + round-trip 深比较）。
5. **同步投影文件**：`is_current=1` 的条目会投影到客户端活配置，claude 段即 `~/.claude/settings.json` 的 `env.ANTHROPIC_AUTH_TOKEN`。**改库不会自动更新投影**，必须手工写入同一把 key，否则库与生效值不一致。
6. 端到端验证：`POST {ANTHROPIC_BASE_URL}/v1/messages`（`max_tokens` 给小值，`x-api-key` 带新 key）→ **200 即通**；401 = key 无效；400 带 `1211 模型不存在` = 模型名问题、与 key 无关（`glm-5.3[1M]` 这类带方括号的写法直连 API 会被拒，Claude Code 客户端会自行剥离后缀，属正常）。
7. **改完必须回读 + 告知用户核对**，别假定一次写入长期有效。反例（2026-10-18 → 10-19 实测）：库与投影双写、回读均 PASS 且 API 200，次日 cc-switch 启动仍把**库和投影一起**重写回旧 key（两文件 mtime 落在同一秒）。用户可能自己在 UI 里切过，也可能启动期做了回写——结论是密钥轮换必须闭环到"用户确认当前生效值"。

> 旧 key 建议留档：`~/.claude/backups/claude-token-backup-<date>.txt`（新旧对照）+ 库/投影各自的时间戳快照，回滚时按快照还原而不是靠记忆。

## 任务 G：OpenCode 段 live config 二元判定与 npm 校验死锁（2026-10-20 实战）

### 1. 现象与报错直击

在 CC Switch 界面管理 OpenCode 供应商时，官方直连供应商（如 `deepseek`）出现在“可添加”列表中，点击右侧 `+` 试图添加时弹出报错：
```text
切换失败
切换失败: 新的 OpenCode 供应商标识需要填写 npm 包和至少一个模型；只有配置中已有的同名供应商可以沿用默认定义 (A new OpenCode provider ID requires an npm package and at least one model; only an existing ID in the live config may inherit defaults)
```
而在 OpenCode 命令行中执行 `opencode models deepseek` 报：
```text
Error: Provider not found: deepseek
```

### 2. 底层机理归因（CC Switch 源码 live.rs 取证）

1. **CC Switch 的二元判定机制**：
   - CC Switch 以后台生效的 `~/.config/opencode/opencode.json`（live config）的 `provider` 键作为基准真值；
   - 存在于 live config 的 provider 归为“已添加”；存在于 `cc-switch.db` 但不在 live config 中的归为“可添加”。
2. **校验分支死锁**：
   - 当点击 `+` 把供应商写入 live config 时，CC Switch 检查当前 live config：
     - **已存在同名 ID**：允许沿用默认定义（inherit defaults，官方内置 provider 如 DeepSeek 原生内置无需填写 npm 包）；
     - **不存在同名 ID**：判定为“全新自定义供应商”，强制走校验分支（源码 `cc_switch_lib::services::provider::live.rs`，要求 `must contain 'npm' or 'options'`）并必须填写 npm 包与至少一个模型。
   - 官方直连 provider 原生内置，配置中只有模型列表（无需 npm 包）。一旦它曾被从 `opencode.json` 中移除，或被列入 `disabled_providers`，CC Switch 便将其误判为新供应商并拦截，而在 UI 上又无法补充该字段，形成闭环死锁。
3. **OpenCode 的三大配置层级**：
   - `disabled_providers`（黑名单拦截层）：优先级极高，在此列表中则完全不加载；
   - `provider.<id>.models`（模型白名单与参数覆盖层）；
   - `~/.local/share/opencode/auth.json`（独立凭据层）：结构为 `{"<provider_id>": {"type": "api", "key": "..."}}`。

### 3. 确定性恢复 SOP

不要在 CC Switch 界面反复点击，直接底层对齐：

1. **编辑 `~/.config/opencode/opencode.json`**：
   - 从 `disabled_providers` 中剔除目标 provider（若无其他禁用项可整块移除）；
   - 在 `provider` 字典中补全同名定义（可包含官方主流模型与自定义推理参数）：
     ```json
     "deepseek": {
       "models": {
         "deepseek-chat": {},
         "deepseek-reasoner": {},
         "deepseek-flash": { "options": { "reasoningEffort": "max" } },
         "deepseek-v4-pro": { "options": { "reasoningEffort": "max" } }
       }
     }
     ```
2. **编辑 `~/.local/share/opencode/auth.json`**：
   - 注入 API Key：
     ```json
     "deepseek": {
       "type": "api",
       "key": "<sk-xxx>"
     }
     ```
3. **验证与热感知**：
   - 命令行执行 `opencode providers list`，确认显示 `● DeepSeek api`；
   - 执行 `opencode models deepseek`，确认列出可用模型；
   - **CC Switch 界面热刷新**：切到左侧其他 App（如 Claude/Codex）再点回 OpenCode（或在窗口中按 `Ctrl+R`），CC Switch 调用 `get_opencode_live_provider_ids` 重新感知 live config，目标 provider 自动进入“已添加”列表。

## 与 sh-zed-opencode-setup 的分工

- 本 skill：cc-switch 数据库通用机制（表结构/读写/备份/各段形状/pi 机制）。
- sh-zed-opencode-setup：opencode 侧思考档位（effort/reasoningEffort、variants 禁用）、模型 `limit`（Zed 上下文指示器）、opencode.json 回写行为、claude→opencode 迁移脚本（cc-switch-migrate.mjs）。动 opencode 段时两个都读。

## 深入资料

- `scripts/` —— 5 个可直接执行的本条目配套脚本（`cc-db` / `cc-add-provider` / `cc-update-provider-config` / `cc-update-meta` / `cc-rename-provider-id`），与 `kb_timeline.ps1`、`organize_subdirs.ps1` 同目录；统一 `node <脚本>` 直跑，默认 dry-run。
- `references/db-schema.md` —— 全部 18 张表清单、providers 表逐列详解、meta JSON 字段、settings 表已知键。
- `references/app-config-shapes.md` —— 各 app_type 的 settings_config 形状、Switch vs Additive 同步模式、codex 代理翻译与模型目录（apiFormat/codexChatReasoning/inputModalities）、pi 深挖（models.json schema、thinking 级联）、完整实战案例。
- `references/deepseek-codex-integration.md` —— DeepSeek 官方接入 Codex 规范全文对比、一键脚本与 CC Switch 冲突分析、原生 Responses 透传配置模板与端到端验证命令。
