# OpenCode Go 访问 DeepSeek V4.1 Flash 提速实测报告

> 实测环境：Windows 11 + opencode 1.18.35（`D:\nvm4w\nodejs\opencode`）／provider `opencode-go`／model `deepseek-v4.1-flash`／本地代理 `127.0.0.1:7897`
> 实测日期：2026-10-11　数据来源：官方文档 + 官方 endpoint 直连压测 + 本机 opencode 二进制反编译

---

## 结论速览（TL;DR）

| 候选杠杆 | 实测结论 | 是否建议动手 |
|:---|:---|:---|
| 官方 Console 配置页 | **没有任何加速开关**，只有计费/额度/团队授权 | ❌ 不用改 |
| 本地 Clash 代理（7897） | n=10 交替 A/B：直连 1.060s vs 代理 1.024s，**无显著差异** | ❌ 不用改 |
| `x-opencode-session` 头 | opencode 1.18.35 **已自动发送**（反编译源码证实） | ❌ 不用改 |
| **`reasoningEffort: "none"`** | 思考 token 2000 → **0**，同一任务总耗时 **12.99s → 4.94s** | ✅ **唯一真杠杆** |
| 上下文体积 / session 稳定性 | 150k 上下文下，换 session id 使 TTFT **2.1s → 4.5s**（翻倍） | ✅ 使用习惯上要守 |
| `OPENCODE_DISABLE_MODELS_FETCH=1` | 省掉 5.4MB models.dev 目录拉取 ≈ **2.2s 启动时间** | ✅ 可选 |

---

## 一、问题界定：这两个名词分别是什么

| 名词 | 实际身份 | 一手来源 |
|:---|:---|:---|
| "opencode go" | provider id `opencode-go`，即 **OpenCode Go** 订阅服务 | 本机 `~/.local/share/opencode/auth.json` 中的 `opencode-go` 条目；`~/.cache/opencode/models.json` 中 `api=https://opencode.ai/zen/go/v1` |
| "deepseek v4.1 flash" | model id `deepseek-v4.1-flash`，1M 上下文 / 384k 输出，$0.15 in、$0.6 out、$0.003 cache read | `https://opencode.ai/docs/go` Endpoints 表；`https://opencode.ai/zen/go/v1/models`；`https://models.dev/api.json` |

该模型 `reasoning: true`，models.dev 登记的 `reasoning_options` 为 `[{type:"effort", values:["low","high","max"]}]`。
**注意：登记值里没有 `none`，但它其实是后端接受的合法值** —— 见第三节 3.4。

---

## 二、官方配置页面（OpenCode Console）：没有能变快的开关

`https://opencode.ai/docs/go` 全文核查，Console 侧可配置项只有：

- 订阅 Go（$10/月）或 Go Plus（$40/月）、复制 API key
- **Use balance**：Go 额度耗尽后回退到 Zen 余额，而不是直接拒答（属**可用性**，不是速度）
- 团队/角色/模型授权、billing / auto-reload、月度限额

> 原文（`/docs/go`）：「If you also have credits on your Zen balance, you can enable the **Use balance** option in the console.」
> 这是 Console 上唯一与"能不能用"相关、与"快不快"无关的选项。

额度规则（会间接表现为"卡住/失败"而非"慢"）：每月额度按美元计，**5 小时窗口 = 月度额度的 20%**，周 = 50%，月 = 100%。

---

## 三、本机环境实测（全部为官方 endpoint 直连压测）

### 3.1 本地代理不是瓶颈 —— 推翻直觉

方法：同一长前缀 + 全新 nonce，直连与走 `127.0.0.1:7897` 交替发起，n=10，先各自预热连接。

| 通道 | TTFT 中位数 | 均值 | 最小 | 最大 |
|:---|---:|---:|---:|---:|
| 直连（`--noproxy`） | 1.060s | 1.023s | 0.688s | 1.320s |
| 本地代理 7897 | 1.024s | 1.046s | 0.710s | 1.571s |

- 两者**地板一致（≈0.71s）**，差异落在抖动区间内，不构成"代理拖慢"的证据。
- 补充：models.dev 目录（5.4MB）直连 2.16s / 代理 2.16s，亦无差异。
- 结论：**不要为了提速去改代理或加 NO_PROXY 白名单**（`NO_PROXY=localhost,127.0.0.1` 仍必须保留，这是官方要求的防 TUI 回环，见 `/docs/network`）。

### 3.2 上下文体积与 session 稳定性才是主因

方法：构造 ~1k / ~40k / ~150k token 的稳定前缀，同 session 连发两次（第二次必命中缓存），再换一个新 session id 发第三次。

| 上下文 | 冷（同 session） | 热（同 session） | 热（换 session id） |
|:---|---:|---:|---:|
| ~1k tok | 0.955s（cached 0/943） | 0.842s（cached 896） | 1.094s |
| ~40k tok | 1.570s（cached 0） | 1.226s（cached 35456） | **2.662s** |
| ~150k tok | 4.874s（cached 0） | 2.052s（cached 133376） | **4.476s** |

聚焦复核（~153k tok，n=3 交替顺序，消除次序偏差）：

| 头部 | TTFT 三次实测 | cached_tokens |
|:---|:---|---:|
| `x-opencode-session` = 固定 | 2.12 / 2.25 / 1.81s | 135936（全命中） |
| `x-opencode-session` = 每次换 | **4.59 / 4.53 / 4.54s** | 135936（**同样全命中**） |

**两个关键事实**：
1. **前缀缓存是内容寻址的、与 session id 无关**（换 session 也报 `cached_tokens` 命中）。
2. **但 session id 决定路由亲和性**：缓存命中的同时，TTFT 依然翻倍。这正是官方要求携带稳定 session 头的原因。

> 官方原文（`/docs/go`）："Send a stable session ID in `x-opencode-session` for each conversation so we can optimize routing and prompt caching."

缺失该头会直接失败（实测）：`HTTP 400 {"type":"error","error":{"type":"MissingSessionID","message":"Request is missing x-opencode-session and cannot be routed efficiently..."}}`

### 3.3 opencode 客户端无需配置：session 头已自动发送

从本机 `opencode.exe`（1.18.35）反编译出的请求构造代码：

```js
headers: {
  "x-opencode-session-id": e.sessionID,
  ...(e.parentSessionID ? { "x-opencode-parent-session-id": e.parentSessionID } : {}),
  ...(e.model.providerID.startsWith("opencode")
        ? { ...(k ? { "x-opencode-project": k } : {}),
            "x-opencode-session": e.sessionID,      // ← 官方要求的那个头
            "x-opencode-request": e.user.id,
            "x-opencode-client":  e.flags.client,
            "User-Agent": _i }
        : { "x-session-affinity": e.sessionID, "X-Session-Id": e.sessionID, ... })
}
```

- `providerID.startsWith("opencode")` 同时覆盖 `opencode` 与 `opencode-go`，故 `x-opencode-session` 会自动带上。
- 同一段代码还把 `promptCacheKey = sessionID` 设为默认（`setCacheKey !== false` 时），即**缓存键默认就是当前 session**，无需配置。
- 反向验证：`x-opencode-session-id`（另一个名）**不能**替代 `x-opencode-session`，单独发它会 400。所以不要在任何自建脚本/网关里改名或丢弃该头。

### 3.4 唯一真正的加速开关：`reasoningEffort: "none"`

前提验证（参数是否被后端认真对待）：

| 请求 | HTTP |
|:---|:---|
| 完全未知参数 `totally_unknown_param` | 200（被静默忽略） |
| `reasoning_effort: "bogus"` | **400**（参数被识别并校验） |

即 `reasoning_effort` 是被后端识别的真实参数，而非被忽略的野参数。

同一道难题（"证明 n 与 2n 之间必有素数"）实测：

| `reasoning_effort` | completion tokens | reasoning tokens | 总耗时 | finish_reason |
|:---|---:|---:|---:|:---|
| 不传（默认） | 2000 | **2000** | 12.99s | length（思考打满） |
| `low` | 2000 | **2000** | 14.77s | length |
| `max` | 2000 | **2000** | 12.85s | length |
| **`none`** | 627 | **0** | **4.94s** | **stop（正常收尾）** |

**结论**：
- `low` / `high` / `max` 对 deepseek-v4.1-flash **几乎没有区别**（都一路思考到 token 上限）→ 想靠"调低 reasoning 档位"提速是无效的。
- `reasoningEffort: "none"` 能**彻底关闭思考阶段**，同一任务 12.99s → 4.94s（**约 2.6 倍**），且输出正常结束。
- 但 models.dev 登记值只有 `low/high/max`，opencode 自动生成的 variant 里**没有 `none`**（生成逻辑：`W.variants = Object.fromEntries(reasoning_options.flatMap(g => g.values.map(k => [k ?? "none", {reasoningEffort: k}])))`），因此必须在 `opencode.json` 手写，或自定义一个 variant。

### 3.5 次要项

- `OPENCODE_DISABLE_MODELS_FETCH=1`：本机 models.dev 目录 5.4MB，实测拉取 **2.16s**；opencode 还会每 60 分钟后台刷新一次。设该环境变量可省掉启动时的目录拉取（代价：只能靠本地缓存识别新模型）。
- `small_model`：本机目前指向 `zhipuai-coding-plan/glm-4.7`，而主模型是 `zhipuai-coding-plan/glm-5`。若切到 `opencode-go/deepseek-v4.1-flash`，建议把 `small_model` 一并换成 opencode-go 上的快速模型，避免标题/摘要生成跨供应商等待。
- 单次实测中，一条琐碎提问的 `tokens.total ≈ 27099`（系统提示 + 工具 + AGENTS.md 约 **25k**）。前缀越稳定、缓存命中率越高，TTFT 越低 —— 这就是"别在会话中途开关 MCP/切换 agent/改 AGENTS.md"的量化理由（工具集已排序后进前缀，任何增删都会让缓存整段失效）。

---

## 四、可直接落地的配置

`~/.config/opencode/opencode.json` 增加（**只加 provider 块，不要动已有的 model / small_model**）：

```jsonc
{
  "provider": {
    "opencode-go": {
      "models": {
        "deepseek-v4.1-flash": {
          "options": { "reasoningEffort": "none" }
        }
      }
    }
  }
}
```

若想保留"可随时切回来思考"，用自定义 variant 而不是写死 options：

```jsonc
{
  "provider": {
    "opencode-go": {
      "models": {
        "deepseek-v4.1-flash": {
          "variants": {
            "fast":    { "reasoningEffort": "none" },
            "deep":    { "reasoningEffort": "high" }
          }
        }
      }
    }
  }
}
```

配合 TUI 的 `variant.cycle` 键位或 `/variants` 命令切换；CLI 侧 `opencode run --variant fast -m opencode-go/deepseek-v4.1-flash "..."`。

**使用习惯侧（零成本、收益最大）**：
1. 同一会话别频繁 fork / 开新会话（大上下文下 TTFT 直接翻倍）。
2. 会话中途不要开关 MCP、切换 agent、改 `AGENTS.md` —— 会击穿整段前缀缓存。
3. 长会话及时开新会话收窄上下文：~150k 上下文即使全命中缓存也要 2.0s TTFT，冷请求 4.9s。

---

## 五、本机历史故障（当前已不复现，仅备查）

按天聚合 `~/.local/share/opencode/log/opencode.log` 中 `opencode-go` 相关日志：

| 日期 | 日志行数 | ERROR |
|:---|---:|---:|
| 2026-10-03 | 599 | **77**（其中 74 条 `AI_APICallError: Token rate limit exceeded`） |
| 2026-10-05 | 443 | 7（`Invalid credential`） |
| 2026-10-06 | 476 | 2（`socket connection was closed unexpectedly`、`unknown certificate verification error`） |
| 2026-10-07 ~ 10-11 | 22 ~ 186 | **0** |

- `Token rate limit exceeded` = Go 的 5 小时窗口限流（月度额度 20%），此时表现为**失败/重试**，属配额问题，只能错峰或换模型；开启 Console 的 **Use balance** 可让额度耗尽后回退而非被拒。
- cert / socket 两类是当时本地代理链路的 TLS 抖动，10-07 之后未再出现。

---

## 六、复现方法

1. 官方文档：`https://opencode.ai/docs/go`、`/docs/config`、`/docs/models`、`/docs/network`（加 `.md` 后缀可直接取 Markdown 原文）。
2. 官方模型元数据：`https://models.dev/api.json`（本机缓存于 `~/.cache/opencode/models.json`）、`https://opencode.ai/zen/go/v1/models`（需 `Authorization: Bearer <key>`）。
3. 延迟压测：用 Python 标准库 `http.client.HTTPSConnection`（走代理时 `set_tunnel`）发 `stream:true` + `stream_options.include_usage` 请求，分别计时「首个 SSE 字节」与「总耗时」，读 `usage.prompt_tokens_details.cached_tokens` 判断缓存命中。关键控制项：交替顺序消除次序偏差、连接预热、`max_tokens` 取小值。
4. 客户端行为取证：`strings`/正则扫 `opencode.exe` 提取请求构造源码片段；`OPENCODE_CONFIG_CONTENT` 环境变量可在**不改动用户配置**的前提下注入内联配置做 A/B。

---

## 七、未决问题

- [ ] `reasoningEffort: "none"` 经 opencode 的 `@ai-sdk/openai-compatible` 通道是否**端到端**透传（API 层已证实参数被识别并生效，opencode 端到端那一次 A/B 未跑完，被手动中断）。
- [ ] 关闭思考后，复杂重构/排障任务的实际正确率下降多少（当前只测了延迟，未做质量回归）。
