---
name: sh-cc-switch-db
description: 直接读写 cc-switch 的 SQLite 数据库（~/.cc-switch/cc-switch.db）：探查表结构、查询/备份/回滚、绕过 UI 直改 providers/provider_endpoints/settings 表，向 claude/codex/gemini/opencode/pi 等任意应用段新增或修改供应商条目，并理解数据库与各应用原生配置文件（opencode.json、pi 的 models.json 等）的同步语义。当用户提到 cc-switch 数据库、写库、直改、备份或回滚 cc-switch、providers 表、把某供应商加到 pi 段/opencode 段/codex 段、cc-switch 里的数据、迁移供应商条目时必须使用——即使用户只说"帮我看看 cc-switch 里的数据"或"把 xx 配到 pi 段"也要触发。opencode 段的思考档位/variants 细节与 claude→opencode 迁移脚本归 sh-zed-opencode-setup，本 skill 负责通用数据库机制。
---

# Skill: sh-cc-switch-db（cc-switch 数据库直改手册）

沉淀自 2026-09-06 实操（cc-switch v3.20.0，Windows，SQLite 版），关键结论经源码交叉验证（farion1231/cc-switch）。cc-switch 升级后表结构可能变化——用 `cc-db.mjs tables` 先核对再动手。
2026-09-14 增补：改既有条目/改 id 两脚本（cc-update-provider-config / cc-rename-provider-id）、**providers.id 外键坑**（见总原则 9）、DeepSeek→opencode 段默认 max 实战案例（app-config-shapes.md）。

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
| cc-switch 程序 | 每用户安装，可能在非 C 盘（实测 `D:\Users\<user>\AppData\Local\Programs\CC Switch\cc-switch.exe`），用 `Get-Process cc-switch | select Path` 定位 |
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

## 与 sh-zed-opencode-setup 的分工

- 本 skill：cc-switch 数据库通用机制（表结构/读写/备份/各段形状/pi 机制）。
- sh-zed-opencode-setup：opencode 侧思考档位（effort/reasoningEffort、variants 禁用）、opencode.json 回写行为、claude→opencode 迁移脚本（cc-switch-migrate.mjs）。动 opencode 段时两个都读。

## 深入资料

- `references/db-schema.md` —— 全部 18 张表清单、providers 表逐列详解、meta JSON 字段、settings 表已知键。
- `references/app-config-shapes.md` —— 各 app_type 的 settings_config 形状、Switch vs Additive 同步模式、pi 深挖（models.json schema、thinking 级联）、完整实战案例。
