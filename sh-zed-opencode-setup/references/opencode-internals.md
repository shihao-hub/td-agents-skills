# opencode 内部机制全记录（版本锚点：opencode 1.18.25，@ai-sdk/anthropic 3.0.82）

排障时实测得出的源码结论。**opencode 升级后若任务 B 验证失败，按本文对照新源码重新定位**（仓库 github.com/sst/opencode，稀疏克隆 `packages/opencode/src` 即可）。

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
- models.dev 目录模型另有 `reasoningVariants()` 优先执行（读 `reasoning_options` 元数据）。
- **变体匹配按模型 ID，不看 provider id**（2026-09-14 实测，opencode 1.18.30）：自定义 provider `deepseek-max`（非目录 id）下，`deepseek-flash` 仍生成 [low,medium,high]、`deepseek-v4-pro` 生成 [low,medium,high,max]。glm-5.3 无变体是因为其模型元数据没有 reasoning_options，**与 provider 是否自定义无关**。→ 结论：禁用变体一律在模型级写 `variants` 全档 disabled，改名 provider id 规避无效。

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
