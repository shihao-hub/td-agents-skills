---
id: "112"
domain: "agent"
scope: "claude"
type: "flow"
slug: "ClaudeCode接入DS双通道配置"
name: "ClaudeCode接入DS双通道配置"
description: "DeepSeek 官方直连与 OpenCode Go 两套 Claude Code 接入配方，新机一键落地并验证 1M 上下文。"
status: "verified"
created: "2026-11-14"
last_verified: "2026-11-14"
updated: "2026-11-14"
superseded_by: null
deprecation_reason: null
compatibility:
  os: ["windows", "macos", "linux"]
falsification_signals:
  - "若 claude -p 的 modelUsage.contextWindow 仍为 200000，说明 [1m] 未生效或会话落在了不带后缀的档位，立即按本条目第三节重配"
  - "若返回 Model is unavailable，说明模型 ID 不属于当前端点命名空间（官方 deepseek-flash vs OpenCode Go deepseek-v4.1-flash），不要互换"
invocation:
  auto_trigger: true
  trigger_keywords: ["Claude Code 接入 DeepSeek", "opencode go 接 deepseek", "deepseek-flash[1m]", "Claude Code 200k 上下文", "Claude Code 1m 上下文", "claude settings.json 配置"]
---

# Claude Code 接入 DeepSeek 双通道配置（官方直连 / OpenCode Go）

> 关联条目：[`029`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/029_agent_ccswitch_flow_cc-switch数据库机制模型迁移与避坑指南.md)（CC Switch 数据库机制）、[`092`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/092_agent_ccswitch_fix_ClaudeCode升级参数冲突与OpenCode路由翻译.md)（Claude Code 参数冲突与路由翻译）。

## 一、业务场景与生成需求

新电脑或新环境，需要 agent 一次性把 Claude Code 接到 DeepSeek，按通道二选一：

| 方案 | Base URL | 凭证 | 适用 |
|---|---|---|---|
| A 官方直连 | `https://api.deepseek.com/anthropic` | DeepSeek API Key（`sk-...`） | 有官方 Key，按量计费，能力最新 |
| B OpenCode Go | `https://opencode.ai/inference/go/anthropic` | OpenCode Go Token（`oc_sk_...`） | 有 Go 订阅，额度制，可复用现有额度 |

**交付物**：

1. 一份可用的 `~/.claude/settings.json`（env + 可选的顶层 `effortLevel`）；
2. 通过 `claude -p --output-format json` 验证 `contextWindow=1000000`；
3. 若用 CC Switch 管理，要求 provider 记录与 live 配置完全一致（见 3.3）。

## 二、技术难点与底层剖析

### 2.1 `[1m]` 是 Claude Code 的客户端标记，不是 API 参数

- Claude Code 对**内置模型表之外**的模型一律假设 200k 窗口，并强制 auto-compact。
- 模型名末尾的 `[1m]` 会被 Claude Code 解析为 `contextWindow: 1000000`，**发请求前剥离**，所以抓包/会话记录里看到的模型名不带 `[1m]`。
- 因此：**会话记录里没有 `[1m]` 不能证明配置错了**，唯一可信判据是 `modelUsage.contextWindow` 或 TUI 的 `/context`。

### 2.2 两个端点的模型命名空间不能互换

| 端点 | 可用模型 ID | 备注 |
|---|---|---|
| DeepSeek 官方 | `deepseek-flash` / `deepseek-v4-pro` | 支持 Claude 名映射：opus→v4-pro，haiku/sonnet→flash |
| OpenCode Go | `deepseek-v4.1-flash` / `deepseek-v4-pro` | **不认** `deepseek-flash`，传了直接 400 `Model is unavailable` |

官方文档的 `deepseek-flash[1m]` 只适用于官方端点；接到 OpenCode Go 时必须换成 `deepseek-v4.1-flash[1m]`。两个模型的上下文都是 1M（models.dev 可查）。

### 2.3 官方推荐变量集（9 条）与两处工程修正

官方文档给出的变量：

```text
ANTHROPIC_BASE_URL            端点
ANTHROPIC_AUTH_TOKEN          凭证
ANTHROPIC_MODEL               主模型
ANTHROPIC_DEFAULT_OPUS_MODEL
ANTHROPIC_DEFAULT_SONNET_MODEL
ANTHROPIC_DEFAULT_HAIKU_MODEL
CLAUDE_CODE_SUBAGENT_MODEL
CLAUDE_CODE_EFFORT_LEVEL      max
CLAUDE_CODE_AUTO_COMPACT_WINDOW 786432（1M 的 75%）
```

两处修正（多次实测踩出来的）：

1. **haiku / subagent 也补 `[1m]`**：官方写法不带后缀，前提是它们只跑小任务；但实际会话或子代理会落到这些档位，一旦落进去就退回 200k。统一带 `[1m]` 可消除死角。
2. **CC Switch 会丢弃它不认识的 env 键**：`CLAUDE_CODE_EFFORT_LEVEL` 不在 CC Switch 的已知变量表里，切换 provider 重写 `settings.json` 时会丢失。用 Claude Code 原生 settings 字段 `"effortLevel": "max"` 兜底（与 env 双写）。

### 2.4 验证不得用裸 curl

裸 HTTP 探测缺 `User-Agent: Claude-Code/...`、`anthropic-beta` 等头，会被 Cloudflare 挡成 403 `error code: 1010`，或把 `[1m]` 误判成 400。**唯一可信验证是走 Claude Code 自身**：

```bash
claude -p "reply OK" --strict-mcp-config --output-format json
# 读 modelUsage.<model>.contextWindow，必须为 1000000
```

## 三、标准自动化流水线

### 3.1 选择方案并收集参数

向用户确认后确定三项：`BASE_URL`、`AUTH_TOKEN`、`MODEL_ID`。

| 参数 | 方案 A 官方 | 方案 B OpenCode Go |
|---|---|---|
| BASE_URL | `https://api.deepseek.com/anthropic` | `https://opencode.ai/inference/go/anthropic` |
| AUTH_TOKEN | DeepSeek Key | `oc_sk_...` |
| MODEL_ID | `deepseek-flash` | `deepseek-v4.1-flash` |

**凭证红线**：token 只从用户处获取或从现有配置读取，禁止写入条目、日志或命令行回显。

### 3.2 生成 `~/.claude/settings.json`

推荐用 Python 一次写入（无 BOM、UTF-8、写后自检）：

```python
import json, os

BASE = "https://opencode.ai/inference/go/anthropic"   # 方案 A 换成 api.deepseek.com/anthropic
TOKEN = "<用户提供的 token>"
MODEL = "deepseek-v4.1-flash"                          # 方案 A 换成 deepseek-flash
M = f"{MODEL}[1m]"

settings = {
    "env": {
        "ANTHROPIC_BASE_URL": BASE,
        "ANTHROPIC_AUTH_TOKEN": TOKEN,
        "ANTHROPIC_MODEL": M,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": M,
        "ANTHROPIC_DEFAULT_SONNET_MODEL": M,
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": M,
        "ANTHROPIC_DEFAULT_FABLE_MODEL": M,
        "CLAUDE_CODE_SUBAGENT_MODEL": M,
        "CLAUDE_CODE_EFFORT_LEVEL": "max",
        "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "786432",
        "CLAUDE_CODE_AUTO_MODE_SERVER": "0",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "API_TIMEOUT_MS": "3000000",
    },
    "effortLevel": "max",
}

path = os.path.expanduser("~/.claude/settings.json")
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w", encoding="utf-8", newline="\n") as f:
    json.dump(settings, f, ensure_ascii=False, indent=2)
    f.write("\n")

raw = open(path, "rb").read()
assert raw[:3] != b"\xef\xbb\xbf", "BOM 污染"
json.loads(raw.decode("utf-8"))
print("ok")
```

> `ANTHROPIC_DEFAULT_FABLE_MODEL`、`AUTO_MODE_SERVER`、`DISABLE_NONESSENTIAL_TRAFFIC`、`API_TIMEOUT_MS` 超出官方 9 条，但分别用于补全新版 Fable 档位与通道稳定性，保留无害。

### 3.3 若由 CC Switch 管理 provider

CC Switch 的 provider 记录存于 `~/.cc-switch/cc-switch.db` 的 `providers` 表，`settings_config` 即 settings.json 内容。要点：

1. 先退出 CC Switch 再写库，避免内存旧值覆盖；
2. 新增 provider 采用**复制现有行 + 换 id/name/env**，不要改现有行（`is_current` 保持原状）；
3. `meta` 必须原样继承：`customUserAgent`（缺了会被 Cloudflare 403）、额度查询脚本、`localProxyRequestOverrides`；
4. `provider_endpoints` 同步插入一条同 URL；
5. 顶层 `effortLevel` 写进 `settings_config`，防止 env 被过滤后 effort 失效；
6. 排序用 `sort_index` 插到末尾，避免其他条目位置变化。

### 3.4 验证清单

```bash
# 1) 默认模型与窗口
claude -p "reply OK" --strict-mcp-config --output-format json
# 期望：modelUsage 的 canonicalModel 含 [1m]，contextWindow = 1000000

# 2) 交互式会话
claude
# 进去后 /context 应显示 xx/1000k；/model 里 Default (recommended) 应解析到 [1m] 档
```

## 四、交付验证与扩展建议

- **新开会话验证**：`[1m]` 只在会话启动时读取，旧会话继续跑仍沿用旧窗口，必须新开或 `/model` 重选。
- **常见误判**：
  - 状态栏/会话记录模型名不带 `[1m]` → 正常，标记已被剥离；
  - `/context` 显示 200k → 真问题，检查是否落在未加后缀的档位；
  - 400 `Model is unavailable` → 模型 ID 与端点不匹配。
- **换端点 Checklist**：只替换 `BASE_URL`、`AUTH_TOKEN`、`MODEL_ID` 三项，其余变量保持；不要把 `deepseek-flash` 与 `deepseek-v4.1-flash` 混用。
- **成本提示**：每次 `claude -p` 验证约 2.4 万 input tokens（系统提示），验证一次即可，无需反复跑。
