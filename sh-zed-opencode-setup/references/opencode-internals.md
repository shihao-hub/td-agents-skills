# opencode 内部机制全记录（版本锚点：opencode 1.18.25 / 1.18.32，@ai-sdk/anthropic 3.0.82）

排障时实测得出的源码结论。**opencode 升级后若任务 B/B3 验证失败，按本文对照新源码重新定位**（仓库 github.com/anomalyco/opencode，raw 直链 `https://raw.githubusercontent.com/anomalyco/opencode/<tag>/packages/opencode/src/...` 也可）。

## 1. 请求选项合并链（effort 如何生效）

`session/llm/request.ts:91`：
```ts
const options = mergeOptions(mergeOptions(mergeOptions(base, input.model.options), input.agent.options), variant)
```
优先级：`variant > agent.options > model.options(配置里的) > base`。
- 没选变体时 `variant = {}` → 配置里模型级 `options` 直接生效（这就是"默认 max"的立足点）。
- 选了变体 → 变体参数**覆盖**配置（用户被 low 顶掉 max 的原因）。

## 2. effort 下拉框从哪来（Zed 看到的）

ACP 适配层 `acp/config-option.ts`：
- 模型有 variants → 给 Zed 暴露 `id: "effort"` 的下拉配置项；模型列表里每个变体是 `provider/model/variant` 条目。
- `selectVariant()`（199 行）回退逻辑：
  ```ts
  if (variant && variants.includes(variant)) return variant
  if (variants.includes("default")) return "default"
  return variants[0]        // ← 没选就是第一项；Claude 系变体顺序 [low,medium,high,xhigh,max] → 默认 low
  ```
- **`default` 哨兵（1.18.32 复核仍在此处，`DEFAULT_VARIANT_VALUE`）**：effort 下拉选项 = `[...new Set([...variants, "default"])]`——**永远包含 Default 选项**；模型选择列表的变体条目会过滤 `default`（`variant !== DEFAULT_VARIANT_VALUE`），不会多出 `(Default)` 模型条目。这是任务 B3 的立足点，详见 §11。
- 数据来源：`acp/service.ts:732` 调 **`/config/providers`** HTTP 端点。

## 3. 双端点差异（最大的坑）

| 端点 | 用途 | 对 `reasoning:false` | 对 `variants.disabled` |
|---|---|---|---|
| `/api/model` | 内部模型列表 | 生效（variants 清空） | 生效 |
| `/config/providers` | **ACP/Zed 实际读取** | **不生效**（照常生成 5 档变体） | **生效（唯一可靠开关）** |

验证配置时必须查 `/config/providers`。两个 handler 都走 Provider 服务但变体计算路径不同（`provider/provider.ts` 约 1563 行的 config 模型构建里，`mergeDeep(variants, model.variants)` 后 `pickBy(!v.disabled)` 剔除——这是 `disabled` 的作用点）。

## 4. 变体表怎么生成的（provider/transform.ts）

- `variants()` 第一行 `if (!model.capabilities.reasoning) return {}`。
- GLM 特判：**非 glm-5.2 的 GLM 模型直接返回空**（所以 GLM 天然无下拉框）。
- Anthropic 路径（`anthropicAdaptiveEfforts`）：现代自适应模型（opus-5 等）→ `["low","medium","high","xhigh","max"]`，low 排第一。
- models.dev 目录模型另有 `reasoningVariants()` **优先执行**（读 `reasoning_options` 元数据）：`provider.ts` 的 `fromModelsDevModel` 里 `ProviderTransform.reasoningVariants(model, base) ?? ProviderTransform.variants(base)`——**只要目录元数据带 `reasoning_options`（含 `type:"effort"`），变体 key 就是其 `values` 数组本身，`variants()` 的全部特判（含 GLM/Qwen 早退）被整体绕过**；`reasoning_options` 为空数组时返回 `{}`（也压掉回退），仅 `undefined` 才让位给 `variants()`。
- ⚠️ **1.18.32 更正**：2026-09-14 的"glm-5.3 无变体（GLM 天然无下拉）"已过时——那只是当时 models.dev 元数据缺 `reasoning_options`。实测 1.18.32：models.dev 给 GLM/Qwen 等补了元数据后，opencode-go（openai-compatible）下的 glm-5.3 / glm-5.3-flash / qwen3.8-flash 都生成 [low,high,max] / [low,medium,xhigh] 下拉；zhipu-glm 自定义段无变体是因为它的模型来自用户 config 而非目录。**结论不变：想要确定性就显式写模型级 variants（禁用或 default），别赌目录元数据。**
- **变体匹配按模型 ID，不看 provider id**（2026-09-14 实测，opencode 1.18.30）：自定义 provider `deepseek-max`（非目录 id）下，`deepseek-flash` 仍生成 [low,medium,high]、`deepseek-v4-pro` 生成 [low,medium,high,max]。→ 结论：禁用变体一律在模型级写 `variants` 全档 disabled，改名 provider id 规避无效。

## 5. SDK 选项名（键名写错 = 静默无效）

| npm 包 | 选项名 | 合法值 |
|---|---|---|
| `@ai-sdk/openai-compatible` | `reasoningEffort` | Zhipu coding API 实测：`none, minimal, low, medium, high, xhigh, max`（严格校验，传错报 1210） |
| `@ai-sdk/anthropic` 3.0.82 | `effort` | zod 枚举 `["low","medium","high","xhigh","max"]`；包内**不存在** `reasoningEffort` |

## 6. opencode 回写 opencode.json

在 Zed 里选模型会触发 opencode 把解析后的配置整体回写 `~/.config/opencode/opencode.json`：
- 实测把 `reasoning: false` 翻回 `true`（回写的是旧解析态）、模型 `name` 规范化为 ID。
- **对策**：让解析态本身正确（variants 全禁用 + reasoning:false）后，回写的就是正确态，稳定；cc-switch 侧 `settings_config` 同步更新，避免切换时写回旧配置。

## 7. 安装失败竞态（任务 A 根因）

下载 zip → 解压出 179MB exe 到 `.tmp-github-download-*` → rename 成 `v_<版本>_<hash>_<hash>` 目录。Windows 要求目录内**所有文件无打开句柄**才能 rename；杀毒/企业安全（Defender、CorpLink 等）实时扫描新 exe 时持有句柄 → Access Denied → Zed 删临时目录 → 重试从头下载 → 再输竞态。概率性：可能重试几次自己成功。

## 8. 其他实测事实

- Zhipu coding 端点（open.bigmodel.cn/api/coding/paas/v4）：`reasoning_effort` 传 `max` 返回 `reasoning_content`；不传参数思考也默认开（档位未知，配置写死 max 即可）。
- Anthropic 官方 API 的 `effort` 为自适应思考：简单问题可以 0 思考 token，属正常。
- 中转站可能吞 effort/thinking 参数（实测某中转：非法值 banana 不报错、native thinking 参数 0 思考 token、max vs none 无差异）——端到端不生效时先测中转，别怀疑配置。

## 9. 四层验证法与 DeepSeek V4 事实（2026-09-14，opencode 1.18.30）

「配置说 max」≠「请求发 max」≠「服务商真跑 max」，四层各自可证：

1. **配置层**：`verify-opencode-effort.mjs` 查 `/config/providers`（variants 空 + effort/reasoningEffort=max）。
2. **发线层**：`verify-wire-effort.mjs`——真实 opencode.json 的目标 provider 复制到 XDG 隔离环境（`XDG_CONFIG_HOME`/`XDG_DATA_HOME` 等重定向到临时目录，baseURL 换 `http://127.0.0.1:<port>/v1`、apiKey 换假值），`opencode run -m <provider/model> "..."` 发一次真请求，回显服务器记录请求体。实测 deepseek-max/deepseek-flash：`POST /v1/chat/completions` 请求体含 `"reasoning_effort": "max"`，且 opencode run 内部两笔请求（先无 tools、后带 tools）都带。**不动真实配置、不花钱**。
3. **API 行为层**：官方 API 同 prompt A/B（reasoning_effort low vs max），对比 `usage.completion_tokens_details.reasoning_tokens`。DeepSeek flash 实测：low=279 / max=379（简单数学题；题目越难差距越大）。
4. **体验层**：Zed 无 effort 下拉框、难题思考段明显变长。

DeepSeek V4 API（官方文档 2026-09 核实）：
- 模型：`deepseek-flash`（V4.1-Flash，原生多模态 text+image 输入，1M 上下文）与 `deepseek-v4-pro`（V4-Pro-0813，纯文本）。旧名 deepseek-chat/deepseek-reasoner 退役中；deepseek-v4-flash 等旧名仍可调但实际由新模型服务、按 Flash 计费。
- `reasoning_effort`（openai 兼容请求体顶层）：取值 **low/high/max**，默认 high；medium→high、xhigh→max 映射（不报错但归档）。思考默认开；关闭用 `thinking: {"type": "disabled"}`（OpenAI SDK 需放 extra_body）。
- 思维链走 `reasoning_content`（流式 `delta.reasoning_content`），与 Zhipu coding 端点同构——opencode 的 `interleaved: {field: "reasoning_content"}` 直接照搬 GLM 模板。
- 带 tools 的请求必须完整回传历史轮次的 `reasoning_content`，否则 400。

## 10. 上下文用量上报链（usage_update，2026-09-21 实测，opencode 1.18.31 / Zed 1.20.2）

- Zed「当前上下文」指示器由 ACP `session/update`（`sessionUpdate: "usage_update"`，字段 `used/size/cost`）驱动。协议时间线：0.10.8（2026-02-04）unstable 引入 → 0.13.6（2026-06-05）stabilize（v1 schema）；Zed 1.20.2 workspace 锁 `agent-client-protocol = "=2.0.0"`（含 unstable feature），协议层无障碍。
- opencode `packages/opencode/src/acp/usage.ts`（v1.18.31 已存在，仓库 anomalyco/opencode）：
  - `used = tokens.input + cache.read + cache.write`（不含 output/reasoning token）
  - `size = providers[providerID]?.models[modelID]?.limit.context`（走内部 Provider.list，与 `/config/providers` 同源）
  - **闸门：`if (!size) return` → limit.context=0 永不发 usage_update**；另要求最后一条 assistant 消息带 providerID/modelID（正常会话都满足）。
- **limit 与 variants 不对称（本次最大坑）**：`variants()` 按模型 ID 从 models.dev 生成（§4）；`limit` 无此合并——自定义 provider 模型不显式写就是 `{context:0, output:0}`（/config/providers 实测）。内置 provider 有目录值：zhipuai-coding-plan 的 glm-5.3 / glm-5.3-flash = 1000000/131072；deepseek 的 deepseek-flash / deepseek-v4-pro = 1000000/384000。
- 探测注：`/config/providers` 返回 `{providers: [...], default}`——providers 是**数组**（按 `id` 找），模型挂在 `provider.models.<modelID>`（**对象**），limit 在 `.limit.context`。
- UI 行为：Zed 指示器在**首条 usage_update 到达后才渲染**（发一条消息后才出现，空会话没有属正常）；opencode 自家 TUI 的上下文显示不走 ACP 链路，TUI 能显示 ≠ Zed 链路通。
- **触发时机**（service.ts 实证）：每轮 turn 结束才发一次——普通 prompt 返回后、已知 command 返回后、compact 后各一个调用点（`sendUsageUpdate`）。流式中不发。
- **Zed 侧渲染**（thread_view.rs `render_token_usage`）：`token_usage()` 为 None → 整个不渲染；有值就渲染 16px ring + `round(used/max*100)%`，**无最小阈值**；`TokenUsageRatio`（≥0.8 Warning / ≥1.0 Exceeded）只控制颜色，tooltip 含 used/max 与 cost。
- **显示 0% 的根因**：被打断/异常的 turn 在 opencode 留下 tokens 全 0 的 assistant 消息行；`latestAssistantMessage` 取最后一条不过滤 0 → used=0。dev 分支同款。再正常跑一轮即自愈。
- **opencode 1.18.x 数据探查**：storage 文件已迁 SQLite——`~/.local/share/opencode/opencode.db`（实测 1.8GB，WAL 活跃）。只读 `DatabaseSync(path,{readOnly:true})` 并发读安全；`message` 表 `data` JSON 含 per-message tokens（input/output/cache.read/cache.write/reasoning/cost），`session` 表有聚合列。opencode.log 只记 permission 评估，别指望它有 usage 线索。
- 升级后复验入口：GitHub `anomalyco/opencode` 对应 tag 的 `packages/opencode/src/acp/usage.ts` + `/config/providers` handler；ACP 侧看 agentclientprotocol/agent-client-protocol 的 CHANGELOG（usage/session 相关行）。

## 11. default 变体哨兵与插件边界（2026-09-26 实测，opencode 1.18.32，任务 B3 依据）

**variant 在 session 层的解析与合并**（`session/llm/request.ts`）：
```ts
const variant =
  !input.small && input.model.variants && input.user.model.variant
    ? input.model.variants[input.user.model.variant]   // key 不存在 → undefined → mergeOptions 视为 {}
    : {}
const options = mergeOptions(mergeOptions(mergeOptions(base, input.model.options), input.agent.options), variant)
```
优先级不变：`variant > agent.options > model.options > base`；variant key 查不到**不报错**，只是无覆盖（落到 model.options——这就是 options 双写能兜底的原因）。

**ACP 层 default 哨兵语义**（`acp/config-option.ts` + `acp/service.ts`）：
- `DEFAULT_VARIANT_VALUE = "default"`；effort 下拉选项永远含 Default（`[...new Set([...variants, "default"])]`）；`selectVariant()`：模型 `variants.default` 存在 → 返回 `"default"`，否则回退 `Object.keys(variants)[0]`。
- `hasVariant()`：`variant === "default" || Object.hasOwn(variants, variant)`——**"default" 永远可设置**（哨兵 = "无显式覆盖"的持久化表示），set_config_option(effort) 对它永不过滤。
- `selectModelVariant()`（切模型时）优先级：URL 式条目自带 `selected.variant` > **同一模型**且当前 variant 合法则保持（手选档位只在同模型内保持）> `selectVariant()` → **跨模型切换单向回 Default**。
- newSession / loadSession / resumeSession / prompt 全部经 `selectVariant` 或恢复持久化 variant → 配好 `variants.default` 后**所有入口默认都是 Default**。
- `configOptions()` 把 `currentVariant === "default"` 原样广播给 Zed（下拉显示 "Default" 被选中）；模型列表条目过滤 default，不产生 `(Default)` 模型条目。

**配置方法**：模型级同时写 `variants.default` 与 `options`（同一份载荷：default 载荷优先级最高、options 兜底）。载荷**必须从 `/config/providers` 实测复制**，键名不统一：

| 模型（实测 1.18.32） | default 载荷 |
|---|---|
| 大多数 openai-compatible（glm/deepseek/kimi/longcat/hy3/hy4…） | `{"reasoningEffort":"<最高档>"}` |
| qwen3.8-flash | `{"effort":"xhigh"}`（键名是 `effort`！） |
| grok-4.6/4.7、gpt-5.6-luna、gpt-6-luna、muse-spark | `{"reasoningEffort":"<档>","reasoningSummary":"auto","include":["reasoning.encrypted_content"]}` |
| minimax-m3（开关型，变体 [none,thinking]） | `{"thinking":{"type":"adaptive"}}` |

最高档选取规则：`max > xhigh > high > medium > low`（`none` 不算档位）；开关型选 `thinking`。

**Zed 侧**：`agent_servers.opencode.default_config_options.effort` 写 `"default"`（哨兵值对所有模型合法）；写具体档位（如 max）会在新会话对该模型下发 set_config_option，无此档的模型（grok 系）被 opencode 拒（InvalidEffortError）。

**工具脚本**：`scripts/apply-default-variant.mjs`（dry-run 默认 / `--apply` 自动备份幂等写入 / `--verify` 复查），从临时 serve 的 `/config/providers` 逐模型取最高档载荷批量落配置。

**插件边界（为什么不能靠插件做"全局默认档"）**：
- plugin 的 `config` hook 只被"通知"（`(hook as any).config?.(cfg)`，返回值被丢弃），**不能改配置**。
- `provider` hook（`models?: (provider, ctx) => Promise<Record<string, ModelV2>>`）理论可全量改写模型（含 variants），但设计语义是给 provider 补模型目录，覆盖既有模型的行为未验证，不建议依赖。
- `chat.params` hook 可在请求层改 options（merge 链之后触发），能强制实际档位，但**改不了 Zed 的 effort 下拉显示**——治标不治本。
- provider/transform 层**没有** provider 级或全局的 variants 开关；模型级合并点是 `configProvider?.models?.[modelID]?.variants` → `mergeDeep` 后 `pickBy(!v.disabled)` 剔除 + `omit(v, ["disabled"])`（任务 B 的 `disabled` 作用点，1.18.32 复核仍在）。
