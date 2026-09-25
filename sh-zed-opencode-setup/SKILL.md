---
name: sh-zed-opencode-setup
description: 配置：Zed 的 opencode agent 安装修复、思考档位、供应商配置、cc-switch 迁移。点名使用
---

# Zed + opencode 配置与修复手册

本 skill 沉淀自 2026-08-28 的一次完整排障会话，已在 opencode **1.18.25** + Zed 1.17.2 + cc-switch（SQLite 版）上验证。
2026-09-14 增补 DeepSeek 默认 max 实战（opencode 1.18.30 实测）：**变体按模型 ID 生成（与 provider 是否内置无关）**、四层验证法（含发线层抓包脚本 verify-wire-effort.mjs）。
2026-09-21 增补 antigravity-acp（Google ACP registry agent）安装实战：**目标目录名可离线推算**（逆向 Zed 源码 `versioned_archive_cache_dir`，双实例验证），任务 A 适用所有 registry agent（含 dl.google.com 等非 GitHub 直链），不限 opencode。
2026-09-21 增补（二）：**Zed「当前上下文」指示器**由 ACP `usage_update` 驱动，opencode 只在模型 `limit.context > 0` 时上报；**`limit` 与 variants 正相反、不按模型 ID 从 models.dev 合并**，自定义 provider 必须显式写（任务 B2，实战 zhipu-glm/deepseek-max 补 limit）。
2026-09-21 增补（三）：antigravity 等 ACP agent 的**登录排障**（OAuth 成功页≠登录成功、代理/CA env 注入、旧进程复用、stdio 认证探针）已独立成 skill **sh-zed-acp-agent-env**——本 skill 任务 A 只管安装竞态，登录问题去那边。
2026-09-25 增补（四）：**权限模型（任务 D）**——「YOLO/auto 模式」是 `--auto` 权限开关、与 Build/Plan agent 无关；按 agent 开 `external_directory` 放行项目外目录（实测 opencode 1.18.32，全局配置 `agent.build.permission` 生效）。
涉及 opencode 内部行为的修复**依赖其源码实现**（详见 `references/opencode-internals.md`），版本升级后可能失效——所以每个任务都带**实证验证步骤**，改完必须验证，不要盲信配置。

## 总原则（每次使用先读）

1. **改任何东西前先备份**：opencode.json 改前 `cp` 一份；cc-switch.db 改前必须整库复制到 `~/.cc-switch/backups/`。
2. **涉及 cc-switch 的操作（尤其 Claude Code → opencode 迁移）必须先向用户展示计划并确认**，默认只 dry-run，用户明确同意后才 `--apply`。这是写数据库的操作，搞砸会影响用户所有供应商配置。
3. **opencode 会回写 opencode.json**：在 Zed 里选一次模型，opencode 就把"解析后的配置"整体回写 opencode.json——手动改的文件可能被覆盖（实测把 `reasoning: false` 翻回 `true`、把 name 规范化成 ID）。所以：改完 opencode.json 后让用户**完全退出 Zed 再打开**验证；cc-switch 侧的同名条目也要同步更新（`liveConfigManaged` 双向同步）。
4. **Zed 不会因开关 agent 面板、新建线程或改 `agent_servers.*.env` 重启 ACP agent 进程（opencode/antigravity/codex-acp 等一律如此）**，只有 Zed 完全退出或手动杀进程才会——改 env 后不杀旧进程，新配置永不生效（详见 sh-zed-acp-agent-env）。排障时用 `tasklist | grep -i opencode` 看进程是否是旧的（对比启动时间）。
5. Windows Git Bash 坑：**curl 发中文会按 GBK 编码**导致 JSON parse error（用纯 ASCII payload）；PATH 里的 `python` 可能是 Windows 商店占位 stub（静默失败），脚本一律用 `node`（v22+ 自带 `node:sqlite`）；**`bash` 命令可能解析到 WSL**（读不到 `C:/` 路径、无 `$LOCALAPPDATA`，报 "No such file or directory"）——调 Git Bash 脚本要显式用 bash.exe 全路径，路径按机器探测（勿写死盘符）：`$bash = (Get-Command git).Source -replace '\\cmd\\git\.exe$','\bin\bash.exe'; if (-not (Test-Path $bash)) { $bash = "$env:ProgramFiles\Git\bin\bash.exe" }`，然后 `& $bash <script> <args>`（PowerShell 下脚本路径用正斜杠）。

## 环境路径（按机器解析，不要硬编码）

| 项 | 路径 |
|---|---|
| opencode 配置 | `~/.config/opencode/opencode.json`（Git Bash 下 `C:/Users/<user>/.config/opencode/opencode.json`） |
| Zed 外部 agent 注册表 | `$LOCALAPPDATA/Zed/external_agents/registry/<agent>/<v_版本_哈希>/` |
| Zed 日志 | `$LOCALAPPDATA/Zed/logs/Zed.log`（含 github_download 下载记录、ACP 错误） |
| cc-switch 数据库 | `~/.cc-switch/cc-switch.db`（SQLite，表 `providers` 主键 `(id, app_type)`） |

---

## 任务 A：Zed 装 opencode 报 "renaming .tmp-github-download-xxx to v_xxx" 失败

**根因**：Zed 流程是 下载 zip → 解压 179MB exe 到临时目录 → rename 成版本目录。Windows 下若杀毒/企业安全软件（如 CorpLink）正在扫描刚解压的 exe（持有句柄），rename 就 Access Denied；Zed 失败后删临时目录、重试又从头下载，反复输掉竞态。

**诊断**（确认属于此问题）：
```bash
ls "$LOCALAPPDATA/Zed/external_agents/registry/opencode/"   # 失败后通常无 .tmp-* 残留（Zed 已清理）
grep "github_download" "$LOCALAPPDATA/Zed/logs/Zed.log" | tail -3   # 看下载 URL 和重试次数
```

**修复**（绕过 rename，直接解压到最终目录名）：
用 `scripts/zed-agent-install`，三个参数全部来自报错信息和日志：
```bash
bash scripts/zed-agent-install <agent名> <zip地址> <目标目录名>
# 例: bash scripts/zed-agent-install opencode \
#   https://github.com/anomalyco/opencode/releases/download/v1.18.25/opencode-windows-x64.zip \
#   v_1.18.25_39ba1e44b4d80431_34afed0bf30609c5
```
zip 地址从 Zed.log 的 `github_download` 行拿；agent 名和目标目录名从报错 `renaming ".../registry/<agent>/.tmp-github-download-x" to ".../registry/<agent>/<目标目录名>"` 拿。**拿不到报错也没关系，目标目录名可离线推算**（见下）。
装完让用户**完全重启 Zed**——它会认这个目录、不再下载，并自动清掉旧版本目录。

若 `scripts/` 不可用，手工等效：`curl -L --retry 5 -C - -o` 下载 → `unzip -t` 校验 → `mkdir 目标目录 && unzip -o zip -d 目标目录` → 运行一次 `exe --version`（让杀毒扫完 + 验证；个别 agent 如 antigravity 不支持 `--version`，直接看 Zed.log 有无启动日志即可）。

**目标目录名推算（2026-09-21 逆向 Zed 源码 `crates/project/src/agent_server_store.rs` 的 `versioned_archive_cache_dir()`，双实例验证）**：
```
v_{版本}_{sha256(版本字符串)前16hex}_{sha256(zip完整URL)前16hex}
```
- 输入来源：版本号 = 本地 `external_agents/registry/registry.json` 的 agents 数组里该 agent 的 `version`；zip URL = Zed.log `github_download` 行。
- 第二个哈希**仅当** manifest 目标带 `sha256`（哈希前拼 `\0sha256:<小写digest>`）或 URL 是 GitHub release（查 release API 的 asset digest）时才混入；**非 GitHub 直链（如 dl.google.com）→ 纯 URL 哈希**。
- 校验法：拿本机已装好的 agent 目录名反验。实测：opencode 1.18.31 → sha256("1.18.31")[..16]=`63d6aa92d4dda7e4` 命中；antigravity 1.1.1 → `v_1.1.1_c5752c93158aa0bc_fceef341456e3fe9` 与 Zed 自行安装的目录名一字不差。
- 版本目录**不需要任何 metadata 文件**：Zed 只查 `is_dir(版本目录)` 与 `is_file(cmd 指向的 exe)`（cmd 见 registry.json，如 `./agy_acp_server.exe`）；目录存在即整体跳过下载直接启动。
- PowerShell 一行算哈希：`(Get-FileHash -InputStream ([IO.MemoryStream]::new([Text.Encoding]::UTF8.GetBytes("1.1.1")))).Hash.Substring(0,16).ToLower()`

**实测案例（2026-09-21，antigravity-acp，dl.google.com 直链）**：竞态输掉后 Zed 反复重下（30 分钟内 5+ 次），残留 48MB 半解压 tmp 目录；用户再试一次时 Zed 自行成功。坑：该 zip 含两个 exe（agy_acp_server.exe 430MB + localharness_external.exe 130MB，解压慢、杀软扫描窗口更长，更容易输竞态）；失败残留的 `.tmp-*` 目录 Zed 通常自删，偶尔留空壳/半解压目录，可手动清。

---

## 任务 B：思考档位默认 max、不出现 effort 下拉框

**用户诉求**：在 Zed 里选模型就是 max，不需要（也不要出现）思考深度选择器。

**机制（依赖源码，升级需重验）**：opencode 给有"变体"的模型在 Zed 里暴露 effort 下拉框；没选变体时回退到**变体列表第一项**（Claude 系是 low），且变体参数会覆盖模型 options 里的 effort。变体表**按模型 ID 生成**（models.dev 已知模型就带），与 provider 是否内置目录无关——2026-09-14 实测：自定义 provider `deepseek-max`（非目录 id）下 `deepseek-flash` 照样生成 [low,medium,high]、`deepseek-v4-pro` 生成 [low,medium,high,max]；glm-5.3 无变体只是该模型元数据没有档位，**不是**"自定义 provider 天然无变体"。解法是把模型的 `variants` 全部 `disabled`，变体表清空 → 无下拉框 → 永远用 options 里的 max。GLM 走 `@ai-sdk/openai-compatible` + `reasoningEffort`；Claude 走 `@ai-sdk/anthropic` + `effort`（键名不同，写错会被静默忽略！）。

**opencode.json 模板**（供应商级 `name` 必须等于其 id，见任务 C）：

GLM（zhipu coding 端点）：
```json
"zhipu-glm": {
  "name": "zhipu-glm",
  "npm": "@ai-sdk/openai-compatible",
  "options": { "apiKey": "<key>", "baseURL": "https://open.bigmodel.cn/api/coding/paas/v4" },
  "models": {
    "glm-5.3": {
      "name": "glm-5.3",
      "limit": { "context": 1000000, "output": 131072 },
      "interleaved": { "field": "reasoning_content" },
      "options": { "reasoningEffort": "max" },
      "reasoning": true
    }
  }
}
```

DeepSeek（V4 官方 API，openai-compatible + 多模态 flash，2026-09-14 实测。注意：即使自定义 provider id，这两个模型 ID 也会生成变体表，必须禁用）：
```json
"deepseek-max": {
  "name": "DeepSeek Max",
  "npm": "@ai-sdk/openai-compatible",
  "options": { "apiKey": "<key>", "baseURL": "https://api.deepseek.com/v1" },
  "models": {
    "deepseek-flash": {
      "name": "DeepSeek V4 Flash",
      "limit": { "context": 1000000, "output": 384000 },
      "reasoning": true,
      "interleaved": { "field": "reasoning_content" },
      "options": { "reasoningEffort": "max" },
      "modalities": { "input": ["text", "image"], "output": ["text"] },
      "variants": { "low": { "disabled": true }, "medium": { "disabled": true }, "high": { "disabled": true }, "xhigh": { "disabled": true }, "max": { "disabled": true } }
    },
    "deepseek-v4-pro": {
      "name": "DeepSeek V4 Pro",
      "limit": { "context": 1000000, "output": 384000 },
      "reasoning": true,
      "interleaved": { "field": "reasoning_content" },
      "options": { "reasoningEffort": "max" },
      "variants": { "…同上五档全禁…" }
    }
  }
}
```
DeepSeek V4 API 事实（官方文档 2026-09 核实）：`reasoning_effort` 取值 **low/high/max**（默认 high，medium→high、xhigh→max 映射）；思维链走 `reasoning_content`（与 Zhipu coding 端点同构，`interleaved` 照搬 GLM 模板）；思考默认开；flash（V4.1）多模态 text+image、pro 纯文本；带 tools 的请求必须完整回传历史 `reasoning_content` 否则 400。

Claude 中转（Anthropic 兼容端点，如 subclaude）：
```json
"subclaude-xxx": {
  "name": "subclaude-xxx",
  "npm": "@ai-sdk/anthropic",
  "options": { "authToken": "sk-...", "baseURL": "https://<中转域名>/v1" },
  "models": {
    "claude-opus-5": {
      "name": "claude-opus-5",
      "limit": { "context": 1000000, "output": 128000 },
      "modalities": { "input": ["text", "image", "pdf"], "output": ["text"] },
      "options": { "effort": "max" },
      "reasoning": false,
      "variants": {
        "low": { "disabled": true }, "medium": { "disabled": true },
        "high": { "disabled": true }, "xhigh": { "disabled": true },
        "max": { "disabled": true }
      }
    },
    "claude-sonnet-5": { "…同上…" }
  }
}
```

**视觉能力要点**：`vision: true` 是无效遗留字段（当前版本解析代码不读它）；生效的是模型级 `modalities.input` 含 `"image"`（无此块则 image 默认 false，贴图会被替换成 "model does not support image input" 错误文本，模型根本收不到图）。支持视觉的模型一律显式配 `modalities`。

**关键细节**：
- `variants.disabled` 是唯一对 `/config/providers`（Zed 实际读取的端点）生效的开关；**只设 `reasoning: false` 不够**（该端点不看它）。两处一起写。
- GLM 模型保持 `reasoning: true`（思考内容显示需要）；Claude 中转设 `false`（中转本来不回思考内容）。
- `reasoningEffort`（GLM）与 `effort`（Claude）键名不可混用。

**验证（必做，防 opencode 升级后行为变化）**：
```bash
node scripts/verify-opencode-effort.mjs <opencode.exe路径> [端口] [--only 供应商ID子串]
# 例: node scripts/verify-opencode-effort.mjs "$LOCALAPPDATA/Zed/external_agents/registry/opencode/v_*/opencode.exe" --only subclaude
```
脚本起临时 `opencode serve`，查 `/config/providers`，断言：目标模型 `variants` 为空、options 里 effort/reasoningEffort=max。注意要查 `/config/providers` 而**不是** `/api/model`——两者数据不同，前者才是 ACP/Zed 用的。**变体按模型 ID 生成，与 provider id 是否内置无关**——覆盖内置 id（如 zai-coding-plan、deepseek）时在 opencode.json 加同 id provider 段配 `variants.disabled` 合并生效；全新自定义 id 同样要在自己的模型级写 `variants` 全档 disabled，别指望改名规避。若验证失败，对照 `references/opencode-internals.md` 检查 opencode 新源码（重点：`acp/config-option.ts` 的 `selectVariant`、`provider/transform.ts` 的 `variants()`、`/config/providers` handler）。

**四层验证法**（2026-09-14 新增——只验配置层不够，"配置说 max" ≠ "请求发 max" ≠ "服务商真跑 max"）：
1. **配置层**：上面的 `verify-opencode-effort.mjs`。
2. **发线层**：`verify-wire-effort.mjs`——把目标 provider 配置复制到 XDG 隔离环境（baseURL 换本地回显服务器、假 key），跑一次真实 `opencode run`，抓 POST 请求体断言 `reasoning_effort` 真的是 max。不动真实配置、不花钱：
   ```bash
   node scripts/verify-wire-effort.mjs <opencode.exe> deepseek-max/deepseek-flash --expect max
   ```
3. **API 行为层**：直接调官方 API 同 prompt A/B（reasoning_effort=low vs max），对比 `usage.completion_tokens_details.reasoning_tokens`——证明服务商端档位有真实区别（DeepSeek flash 实测 low 279 vs max 379 tokens，简单题；难题差距更大）。
4. **体验层**：Zed 里无 effort 下拉框、难题思考段明显变长。

---

## 任务 B2：Zed 显示「当前上下文」指示器（模型 `limit`，2026-09-21 实测 opencode 1.18.31 / Zed 1.20.2）

**症状**：Zed agent 面板输入框下方的上下文百分比环永不出现；opencode 自家 TUI/客户端却能看到上下文用量。

**机制链**：Zed 指示器 ← ACP `sessionUpdate: "usage_update"`（`used/size/cost`；0.10.8 引入 unstable、0.13.6 于 2026-06 转正；Zed 1.20.2 workspace 锁 `agent-client-protocol = "=2.0.0"` 已支持，协议层无障碍）← opencode `acp/usage.ts`：`size = 模型 limit.context`，**`if (!size) return`——limit 为 0 就永不上报**（Zed 侧无法可配，只能 opencode 侧修）。

**关键坑（与 variants 正相反）**：变体按模型 ID 从 models.dev 生成（自定义 provider 也生成，见任务 B）；**`limit` 不做此合并**——自定义 provider 的模型不显式写 `limit`，`/config/providers` 里就是 `{"context":0,"output":0}`。内置 provider 有目录值可抄。

**实测值（2026-09-21 从内置 provider /config/providers 抄写）**：
- glm-5.3 / glm-5.3-flash（内置 zhipuai-coding-plan）→ `{ "context": 1000000, "output": 131072 }`
- deepseek-flash / deepseek-v4-pro（内置 deepseek）→ `{ "context": 1000000, "output": 384000 }`

**修复**：opencode.json 模型级补 `limit`（任务 B 模板已含）→ cc-switch 同名条目 `settings_config` 同步（`cc-update-provider-config.mjs`，见 sh-cc-switch-db；`liveConfigManaged` 双向同步，漏一侧会被写回旧值）→ 完全重启 Zed。

**三态诊断（2026-09-21 深挖，读 Zed thread_view.rs / opencode service.ts 源码实证）**：
- **完全不显示** = 该线程从没收到过 usage_update（Zed `token_usage()` 为 None 直接不渲染）。修复 limit 只影响**新完成的 turn**——旧轮次不会补发。处置：在该线程里完整跑一轮。
- **显示 0%** = 收到过，但最后一次 `used=0`。opencode 每轮 turn 结束才发一次（service.ts 的 prompt/command/compact 三个返回点），`used` 取**最后一条 assistant 消息**的 input+cacheRead+cacheWrite；被打断/异常的 turn 会留下 tokens=0 的空消息行（opencode.db `message` 表可见），不过滤 0 → 发 used=0。处置：再正常完整跑一轮即覆盖。dev 分支同款逻辑（未修）。
- **正常百分比** = 完整 turn 后的真实值。**无最小阈值**：Zed 显示 `round(used/max*100)%`，TokenUsageRatio 只管变色（≥80% 警告色）。
- opencode TUI 能显示上下文**不代表** Zed 链路通（TUI 不走 ACP）；「没到上下文限制就不显示」是误解，不存在阈值。

**验证**：起 `opencode serve --port <p>` 查 `GET /config/providers`（返回 `{providers:[数组], default}`——providers 是**数组**按 `id` 找，模型挂 `provider.models.<modelID>`（**对象**），看 `.limit.context` 非 0）；Zed 发一条消息后指示器才出现（**首条 usage_update 到达才渲染**，空会话不显示属正常）。注意 opencode TUI 能显示上下文**不代表** Zed 链路通（TUI 不走 ACP）。

---

## 任务 C：cc-switch 与 opencode 配置同步 / Claude Code → opencode 迁移

**⚠️ 此任务动 cc-switch 的 SQLite 数据库，必须先 dry-run 展示计划、经用户确认后再 `--apply`。**

**背景**：cc-switch 的 opencode 段每个供应商的 `settings_config` 就是切换时写进 opencode.json `provider.<id>` 的完整 JSON。对 `liveConfigManaged: true` 的条目还有双向同步——**opencode.json 和 cc-switch 两侧必须一致**（尤其 `name`），否则互相把对方改回去。

**名称约定**：供应商标识（id / opencode.json 的 provider key）用 slug 风格（如 `subclaude-dzw`、`zhipu-glm`）；**显示名（name）是用户偏好，不要擅自改**（例：用户明确要求 zhipu-glm 的显示名保持 "Zhipu GLM"，曾被我错误地强制改成标识而被骂）。仅当用户明确要求统一名称时才改。

**迁移脚本**（把 claude 段的中转供应商复制为 opencode 段条目，照已验证的模式生成 models 配置）：
```bash
node scripts/cc-switch-migrate.mjs          # dry-run：打印将要新增/修改的条目
node scripts/cc-switch-migrate.mjs --apply  # 用户确认后执行（自动备份 db 到 ~/.cc-switch/backups/）
```
脚本逻辑与库表结构见 `references/cc-switch-migration.md`。要点：读 claude 段各条目的 `env.ANTHROPIC_AUTH_TOKEN/BASE_URL` → 生成 opencode 段 `settings_config`（任务 B 的 Claude 模板）→ 同步更新已存在的 opencode 条目（name==id、补 variants 禁用）→ 插入 `providers` + `provider_endpoints` 行。跳过官方 OAuth 型条目和已有的 zhipu-glm（避免重复）。

**写入后**：让用户**重启 cc-switch**（运行中的实例不会热加载新数据）。同时检查 opencode.json 里对应供应商的 `name` 是否已是标识风格，不一致就一起改。

---

## 任务 D：权限模型——auto 模式（"YOLO"）与外部目录访问（2026-09-25 实测 opencode 1.18.32）

**概念纠偏**：社区说的「YOLO 模式」在 opencode 官方文档里叫 **Auto mode**，是**权限审批开关**，与 Build/Plan agent 无关（agent 是工具集/身份，auto 是"ask 时自动放行"）。两者正交：Build 里可以开 auto，Plan 里也可以。

**三种审批结果**：每条 permission 规则解析为 `allow`（直接执行）/ `ask`（弹确认，选项 once=仅本次、always=本会话内匹配模式均放行、reject=拒绝）/ `deny`（拦截）。

**auto 模式入口**：
- CLI：`opencode --auto` 或 `opencode run --auto "..."`——自动批准**未被显式 deny** 的 ask 请求；显式 `deny` 仍然生效。
- TUI：命令面板选 **Enable/Disable auto-approve permissions**，激活时当前 agent 名旁有 `auto` 灰标。

**默认值矩阵**（不写任何 permission 配置时）：大多数权限键默认 `allow`；**`external_directory` 和 `doom_loop` 默认 `ask`**；`read` 默认 allow 但 `*.env`/`*.env.*` 默认 deny（`*.env.example` 例外）。权限键按工具名：`read`/`edit`（覆盖 edit+write+patch）/`glob`/`grep`/`bash`（按解析出的命令串匹配，如 `git *`）/`task`/`skill`/`lsp`/`question`/`webfetch`/`websearch`/`external_directory`/`doom_loop`。

**外部目录（external_directory）**：凡工具调用触及启动工作目录之外的路径（read/edit/glob/grep 及部分 bash 命令）就命中该权限。`~/...` 只是写法展开，**不会**让外部路径变成工作区内，仍需显式放行。⚠️ 别指望 `--auto`：默认 ask → auto 会直接放行**任意**外部路径，等于敞开读写的还有 bash/edit。要"只放行某目录"用对象语法（模式匹配，**最后匹配的规则胜出**，catch-all `"*"` 放最前）：
```json
"external_directory": { "~/projects/personal/**": "allow" }
```
被放行的目录继承工作区默认值（read 默认 allow 即连带放开）；想"只读放行"再叠一条 `"edit": { "<同路径>": "deny" }`。只列信任目录，别整盘放开。

**按 agent 覆盖（本次实战采用的方案）**：agent 级 permission 与全局合并、**agent 规则优先**。只给 Build 开外部目录、其余 agent 保持默认 ask——写入全局 `~/.config/opencode/opencode.json`：
```json
"agent": {
  "build": {
    "permission": { "external_directory": "allow" }
  }
},
```
（位置随意，与其他顶层键并列即可；改后需按总原则 3/4：完全退出 Zed 或杀掉旧 opencode 进程再验证。验证法：TUI/会话里让 Build 读一个项目外文件，不再弹权限询问即生效；Zed 面板里 Tab 切 Plan 读同一文件应仍询问。）

**配置优先级速记**：全局 `permission` < `agent.<name>.permission`（agent 胜出）；`--auto` 只改变"本会 ask"的请求的结果，不改变 `deny`。

---

## 常见坑速查

| 症状 | 原因/处理 |
|---|---|
| `Failed to initialize provider: xxx` | `@ai-sdk/anthropic` 的 options **同时有 `apiKey` 和 `authToken` 时直接抛异常**（"Please use only one authentication method"）。cc-switch UI 编辑易产生双 key。anthropic 系只留 `authToken`（Bearer 头）；openai-compatible 系（zhipu）用 `apiKey`。opencode.json 和 cc-switch 库两侧都要清 |
| 改了 opencode.json 不生效 | opencode 进程是旧的（Zed 没完全退出）；或已被 opencode 回写覆盖，diff 一下 |
| Zed 模型下拉里出现 "(Low)…(Max)" 后缀条目 | 模型 variants 没禁用，走任务 B；验证用 /config/providers |
| 自定义 provider id 也出现下拉框/被顶回 low | 变体**按模型 ID** 生成（models.dev 已知模型就带），换 provider id 规避无效；模型级 `variants` 全档 disabled（2026-09-14 实测踩坑） |
| 努力改成 max 但请求还是 low | 选了 low 变体（变体覆盖 options）；禁用变体后重选 plain 模型 |
| Zed 里「当前上下文」指示器永不出现 | 模型 `limit.context=0`：自定义 provider 的 **limit 不从 models.dev 合并**（与 variants 相反）；模型级显式写 `limit` 并同步 cc-switch，完全重启 Zed，见任务 B2 |
| Build 读项目外文件反复弹权限询问 | `external_directory` 默认 `ask`（见任务 D）；按 agent 放行写 `agent.build.permission.external_directory`，别用全局 `--auto`（会放开所有工具的所有外部路径） |
| `subclaude-xxx/claude-opus-5 is not a valid value` 警告 | Zed 侧对自定义模型 ID 的校验提示，无害可无视 |
| 装 antigravity 等 ACP registry agent 反复重下 / 卡 rename | 同任务 A 竞态，**适用所有 registry agent**（含非 GitHub 直链）；目录名可推算（见任务 A），`zed-agent-install` 照用 |
| Zed 里 antigravity（或其它 ACP agent）登录：浏览器显示认证成功但 Zed 仍要求登录 / 日志反复 `onboarding_failed` | agent 进程没拿到代理/CA 环境变量 + 旧进程复用；`agent_servers.<id>.env` 注入并杀旧进程，见 **sh-zed-acp-agent-env** |
| bash 跑脚本报 No such file or directory（`C:/` 路径明明存在） | `bash` 解析到了 WSL；显式用探测到的 Git Bash 全路径：`(Get-Command git).Source` 把 `cmd\git.exe` 换成 `bin\bash.exe`，探测失败退 `"$env:ProgramFiles\Git\bin\bash.exe"`（见总原则 5） |
| curl 报 JSON Invalid UTF-8 | Git Bash 中文按 GBK 发送，payload 换 ASCII |
| node 脚本调 sqlite | 用 `require('node:sqlite')` 的 `DatabaseSync`，v22+ 可用 |

## 深入资料

- `references/opencode-internals.md` —— opencode 内部机制全记录（请求合并链、变体计算、双端点差异、SDK 选项名、用量上报链 usage_update/limit、版本锚点）。**opencode 升级后任务 B/B2 验证失败时必读**。
- `references/cc-switch-migration.md` —— cc-switch 数据库表结构、settings_config 形状、迁移脚本设计与回滚。
