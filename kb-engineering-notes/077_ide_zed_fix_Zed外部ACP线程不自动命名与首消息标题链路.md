---
name: kb-zed-acp-thread-auto-title
description: |
  Zed 外部 ACP 线程（openma-pi / pi-acp 等）标题恒为占位「New Agent Thread」、不再按首条消息自动命名：Zed 的占位命名要求「发送首条消息时线程内尚无任何 entry」，而 pi-acp 在 session/new 阶段抢先推送的启动横幅（startup banner）恰好成为第一条 entry，把该条件永久破坏；同时 pi 自身从不生成会话名，适配器只转发它。含标题链路源码锚点、横幅/插件取舍、agent 侧命名插件 auto-session-title 实现与双模式验证、以及 --quiet-startup 规避法。
version: 1.0.0
created: 2026-10-19
updated: 2026-10-19
id: "077"
domain: ide
scope: zed
type: fix
slug: "Zed外部ACP线程不自动命名与首消息标题链路"
status: verified
last_verified: "2026-10-20"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: true
---

# ide_fix_077_Zed外部ACP线程不自动命名与首消息标题链路

> **条目定位**：Type A 疑难排障型条目（含 Type B 插件落地）
> **结论版本锚点**：**验证于 Zed 1.24.3 / commit `2a857f5f2ec368745c1af5209d49836968fe75b8`、`@openma/pi-acp` 0.1.8、pi 1.3.0（`@earendil-works/pi-coding-agent`）**（2026-10-19）。三方任一升级后请按「四、自查」重跑。
> **关联条目**：openma-pi-acp 内存直载与管道排障见 `074_agent_pi_fix_Zed集成PiCodingAgent双层管道难用与openma内存直载SOP.md`；自定义代理图标见 `076_ide_zed_fix_Zed自定义ACP代理图标机制与注册表兜底.md`；按 SHA 取上游源码的方法论见 `075_dev_core_flow_发行版二进制嵌SHA溯源与上游源码取证.md`。

---

## 一、现象与诉求直击

### 典型现象
1. 在 Zed 里新建 openma-pi（或其它 pi 系）线程，标题**永远是占位「New Agent Thread」**，对话进行到几十轮也不变；
2. **第一次**给某个新 agent 条目（或当天第一次）发消息时命名正常，之后每次新建线程都失效——“最开始好像支持自动起名，后来就不行了”；
3. 线程正文顶部会先出现一张启动横幅卡片：`pi v1.3.0 via openma-pi-acp v0.1.8` + `Context` / `Skills` / `Prompts` / `Extensions` / `Model` 清单；
4. 手动 `/rename 名字`（pi 侧）或侧栏重命名（Zed 侧）**立刻生效**，说明“显示标题”这条通路本身是好的，只有自动命名不触发。

### 诉求（本机最终取向）
- 自动命名要恢复；
- 启动横幅**保留**（它是每次会话的上下文/技能/模型自检信息，有价值）；
- 命名只作用于 Zed/ACP 场景，**不改动 pi TUI 的交互体验**。

---

## 二、底层根因剖析

### 1. 外部 ACP 线程的标题链路（Zed 侧唯一来源）

| 环节 | 位置（v1.24.3 / `2a857f5f`） | 行为 |
|:---|:---|:---|
| 线程标题取值 | `crates/acp_thread/src/acp_thread.rs:3808` | `title()` = **agent 推来的标题** → 否则 **本地占位标题**（`provisional_title`），都没有就 `None` |
| 占位标题写入 | `crates/acp_thread/src/acp_thread.rs:5189` | `set_provisional_title()`：仅本地显示，不回传 agent |
| 占位标题判定 | `crates/agent_ui/src/conversation_view/thread_view.rs:2036-2052` | 条件为 **`is_first_message && thread.title().is_none()`**；取发送内容里 `Text`/`ResourceLink` 块 `join(" ")` 后的**首行**、`trim`、截 200 字符 |
| “是否首条消息” | `crates/acp_thread/src/acp_thread.rs:3766`、`:3819` | `is_draft_thread() = entries().is_empty()`，即**按下回车那一刻线程里必须一条 entry 都没有** |
| 渲染兜底 | `crates/agent_ui/src/conversation_view.rs:1749-1755` | 没有标题就显示 `DEFAULT_THREAD_TITLE` = 「New Agent Thread」 |
| agent 标题入口 | `crates/acp_thread/src/acp_thread.rs`（`AgentMessageChunk` 等 update 处理） | `session/update` → `session_info_update.title` 会设置真标题，并**清掉**占位标题 |

结论：**自动命名是一条 Zed 内部的“首条消息启发式”，条件苛刻**（线程必须干净 + agent 没给过标题），并不是 agent 的能力。

### 2. pi 侧从来不生成会话名
- pi 只有 `setSessionName()` 一条写入口（`/name`、`/rename`、扩展 API `pi.setSessionName()`），写入会话文件里的 `session_info` 条目；pi 本体**没有**任何 LLM 起名逻辑；
- `@openma/pi-acp` 0.1.8 只做转发：`dist/chunk-5IXHVFXW.js:1403-1410` 的 `case "session_info_changed"` → `session_info_update{ title }`；启动回放里也只在会话**已有名字**时才推标题（`:3203`）；
- `session/list`（历史线程列表）的标题是 `会话名 || 首条消息首行(80 字符)`（`:4182-4188`）——**只影响列表展示，不会写进线程标题**。

所以：`/rename` 能让标题出现（agent 侧真标题），但没人自动去写它。

### 3. 真正的元凶：启动横幅抢跑，把“线程干净”这个前提吃掉了
`@openma/pi-acp` 在 `session/new` 阶段会 `publishSurfaces(session, { startup: true })`：

```js
// dist/chunk-5IXHVFXW.js:4461-4467
if (options.startup === true && this.settings.quietStartup !== true) {
  const quiet = session.session.settingsManager.getQuietStartup();
  if (!quiet) session.text(buildStartupInfo(session.session, session.diagnostics));  // ← 一条 agent_message_chunk
}
```

这条 `agent_message_chunk` 在 Zed 侧会**生成一条 assistant entry**（`push_assistant_content_block_with_message_id`），于是：

```
session/new  →  横幅 entry 落库  →  entries 非空  →  线程不再是 draft
            →  用户按回车时 is_first_message = false  →  占位命名分支永不进入
            →  标题永远空  →  「New Agent Thread」
```

**实测证据（ACP 抓包探针）**：

| 场景 | `session/new` 之后立刻收到的 `session/update` |
|:---|:---|
| 默认（`PI_ACP_QUIET_STARTUP=0`） | `session_info_update`(仅 _meta) → `available_commands_update` → **`agent_message_chunk` = 启动横幅** |
| 加 `--quiet-startup` / `PI_ACP_QUIET_STARTUP=1` | 只有前两条，**没有 `agent_message_chunk`** |

**旁证（Zed 侧栏 sqlite `%LOCALAPPDATA%\Zed\db\0-stable\db.sqlite` → `sidebar_threads`）**：

- 存在 `agent_id='openma-pi'`、`session_id` 非空但 **pi 会话目录里根本没有对应 `.jsonl`** 的线程行：按 `is_draft_thread() = entries().is_empty()` 反推，它们之所以不算 draft，只能是因为**横幅那条 entry**——证明横幅确实在用户发言前就进了线程；
- 正常命名过的那条线程，`title` 里带着 Zed `join(" ")` 的特有 **双空格签名**（`你看一下  @skills  目录的 git 历史…`），可反证它就是 Zed 的占位命名产物；
- 另一条 `title='zed custome'` 的行来自 pi 侧 `/rename`（`string=session_info`），说明 agent 标题通路正常。

### 4. 为什么“第一次正常、之后全部失效”
占位命名是**竞态**：只要你在横幅投递到线程之前按下回车，`entries` 还是空的，就能命名成功。首次给某 agent 条目建会话时初始化更慢（模型/扩展/首轮握手），窗口更大，容易抢到；之后连接已热，横幅几乎瞬时落到线程上（甚至在你打开线程、还没输入时就已经贴上），于是稳定失败。这也解释了本机实测里“新加一个 agent 第一次正常、随后每次都不行”。

### 5. 为什么别的 agent 不受影响
opencode / claude-acp / codex-acp / antigravity-acp 的适配器**自己会推 `session_info_update.title`**（agent 侧真标题），根本不依赖 Zed 的启发式；只有 pi 系（pi 无自动命名 + 适配器只转发）会暴露这个坑。

---

## 三、标准修复 SOP

### 方案 A（本机落地，推荐）：pi 侧插件 `auto-session-title`
用 **agent 侧真标题**绕开 Zed 启发式的所有前置条件：标题一旦由 agent 推送，Zed 直接采用、并清掉占位标题，且**写入 pi 会话文件**（可持久、可被 `/rename` 覆盖、恢复会话后仍在）。

- 源码：`D:\Users\pi-local-plugins\auto-session-title\index.ts`
- 挂载（与 `collapse-tools` 同规格，Junction）：`~/.pi/agent/extensions/auto-session-title`
- 作用域：**仅 `mode === "rpc"`**（pi-acp 等 SDK/ACP 集成与 `pi --mode rpc` 都绑这个 mode），**pi TUI 与 `--print` 完全不受影响**

```ts
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const MAX_TITLE_LENGTH = 60;

function toTitle(prompt: string): string | undefined {
	const firstLine = prompt.split("\n").find((line) => line.trim().length > 0);
	if (firstLine === undefined) return undefined;
	const collapsed = firstLine.replace(/\s+/g, " ").trim();
	if (collapsed.length === 0) return undefined;
	if (collapsed.length <= MAX_TITLE_LENGTH) return collapsed;
	return `${collapsed.slice(0, MAX_TITLE_LENGTH - 1)}…`;
}

export default function (pi: ExtensionAPI) {
	pi.on("before_agent_start", async (event, ctx) => {
		if (ctx.mode !== "rpc") return;          // 只服务 ACP/SDK 集成，不动 pi TUI
		if (event.messageType !== "user") return;
		if (pi.getSessionName()) return;         // 已有名字（/name、恢复的历史会话）不覆盖
		const title = toTitle(event.prompt ?? "");
		if (title !== undefined) pi.setSessionName(title);
	});
}
```

机制链：`before_agent_start` → `pi.setSessionName()` → pi 发 `session_info_changed` → pi-acp 转 `session_info_update{title}` → Zed `AcpThread::title()` 变真标题。**不调模型、零额外 token**。
生效方式：扩展在会话创建时加载，改完插件需**重启 Zed**（或让 agent 进程重连）后新开线程验证。

> **边界：`mode` 门禁的代价（本机已知取舍）**
> 因为只在 `mode === "rpc"` 时命名，**在 pi TUI / `--print` 里起头的会话不会带会话名**。这些会话之后拿到 Zed 里打开时，依旧会显示占位「New Agent Thread」——原因是 Zed 自带的占位命名仍被启动横幅卡着（见第二节第 3 点），而 agent 侧又没写过名字。两条处理路径：
> 1. 保留门禁，遇到这类会话手动 `/rename <名字>`（写入 pi 会话名，一次生效、永久保留）；
> 2. 想要「TUI 起头也自动命名」，删掉 `if (ctx.mode !== "rpc") return;` 那一行（代价：pi TUI 的会话也会被自动命名，footer/会话选择器里会多出一个名字）。

改这个插件吃什么参数（后续扩展点）：

| 想要的效果 | 改法 |
|:---|:---|
| 标题长度 / 省略号风格 | `MAX_TITLE_LENGTH`、`slice` 尾部 |
| 跳过 `@` 提及、`<skill>` 块等噪声前缀 | 在 `toTitle` 里先做正则清洗 |
| 用模型生成摘要式标题 | 在同一个 handler 里调一次模型（代价：一次请求 + 延迟） |
| 只在 ACP 生效 / 连 TUI 一起命名 | 保留或删掉 `ctx.mode !== "rpc"` 那一行 |
| 全部会话统一加项目前缀 | 在 `title` 前拼 `【项目名】`（项目名取自 `ctx.cwd`） |

### 方案 B（可选叠加，与 A 不冲突）：去掉启动横幅
```jsonc
// %APPDATA%\Zed\settings.json → agent_servers.<agent>
"args": ["C:/Users/<user>/.bun/install/global/node_modules/@openma/pi-acp/dist/bin.js", "--quiet-startup"],
// 或
"env": { "PI_ACP_QUIET_STARTUP": "1" }
```
- 效果：线程在首条消息前保持干净 → **Zed 自带的占位命名恢复**（等于不装插件也能自动命名），同时线程顶部不再被那张大卡片占据；
- 代价：**丢掉每次会话的 Context/Skills/Model 自检信息**；等价替代是 `~/.pi/agent/settings.json` 里 `"quietStartup": true`（连 pi TUI 的启动输出一起安静）；
- 本机取向：**保留横幅**（要自检信息）→ 只用方案 A。

### 方案 C：不改代码的临时手段
- 线程内发 `/rename <名字>`（写入 pi 会话名，跨重启保留）；
- 或 Zed 侧栏重命名（写入 `thread_override`，只影响 Zed 显示）。

### 方案对比

| 方案 | 标题来源 | 是否写进 pi 会话文件 | 失效风险 | 代价 |
|:---|:---|:---:|:---|:---|
| A 插件 | pi `setSessionName()` | ✅ | 极低（不依赖 Zed 判断） | 需维护一个本地插件；TUI 起头的会话不带名（`mode` 门禁代价，见上） |
| B 去横幅 | Zed 占位命名（首行 ≤200） | ❌ | 只要再有别的 entry 抢先就再次失效 | 丢自检卡片 |
| C 手动 | 人 | ✅（pi 侧）/ ❌（Zed 侧） | 无 | 每次手工 |

### 不推荐
改 Zed 二进制 / 打补丁：升级即失效，且属于跨条目污染，不进入常规方案。真要治本应向上游提 FR：让外部 agent 的首条消息也能触发命名（或在 `session/new` 响应里接受初始 `title`）。

---

## 四、验证与防复发闭环

### 验证（三层，任一层失败即可定位）
```powershell
# 1) agent 侧：插件是否真的写入会话名（rpc 模式应命名、print 模式不应命名）
$pi = "C:/Users/<user>/.bun/install/global/node_modules/@earendil-works/pi-coding-agent/dist/cli.js"
# rpc：喂一行 prompt 后保持 stdin 打开 ~30s，让首轮跑完
'{"id":"1","type":"prompt","message":"命名探针：只回答 OK"}' > $env:TEMP\probe.jsonl
(cat $env:TEMP\probe.jsonl; sleep 35) | node $pi --mode rpc --no-tools --session-dir "$env:TEMP\pi-title-rpc" --model <provider/model>
node $pi --print --no-tools --session-dir "$env:TEMP\pi-title-print" --model <provider/model> "print 模式不应命名"
# 再读两个 session-dir 里的 *.jsonl，只应有 rpc 那条含 "type":"session_info","name":"命名探针…"

# 2) 协议侧：session/new 后是否还有横幅 chunk（决定方案 B 是否可用）
#    以 ACP 客户端身份 spawn dist/bin.js，发 initialize + session/new，打印 session/update：
#    默认应有 agent_message_chunk（横幅）；带 --quiet-startup / PI_ACP_QUIET_STARTUP=1 时应消失

# 3) Zed 侧：新线程发首条消息，看 Threads Sidebar；必要时对账 sqlite
#    %LOCALAPPDATA%\Zed\db\0-stable\db.sqlite → sidebar_threads(title, title_override, session_id)
#    标题 = 占位/真标题；title_override = 手动重命名；session_id 为空 = 尚未建会话的草稿
```

### 防复发（三个版本锚点，任一漂移都要重跑）
0. **先确认边界是否还成立**：`mode` 门禁下，TUI 起头的会话无名字属于**预期行为**（不是 bug）；若人类反馈“TUI 里的会话拿到 Zed 没名字”，先复看上方「边界」小节再动手。
1. **Zed**：占位命名条件是否仍是 `is_first_message && title().is_none()`（`thread_view.rs` 的 `send_content` 内）；`is_draft_thread()` 是否仍等于 `entries().is_empty()`。新版 Zed 已在 main 分支加入更宽松的 provisional title 逻辑，升级后可能自然修复，**别沿用旧结论**。
2. **pi-acp**：`publishSurfaces` 的启动横幅条件（是否新增默认安静、是否改成 notice 而非 message entry）、`session/new` 是否开始直接返回/推送初始标题。
3. **pi**：是否新增自动命名（一旦有，插件即可退场，删掉 junction 与源目录即可回滚）。

### 回滚
```powershell
Remove-Item "$env:USERPROFILE\.pi\agent\extensions\auto-session-title" -Force   # 断开 Junction
# 源目录 D:\Users\pi-local-plugins\auto-session-title 保留（可随时重新挂载）
```
