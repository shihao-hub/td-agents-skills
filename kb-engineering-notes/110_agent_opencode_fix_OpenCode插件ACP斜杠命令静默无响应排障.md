---
name: kb-opencode-acp-slash-command-silence-fix
description: |
  OpenCode v2 插件注册 skills 为斜杠命令致 Zed ACP 客户端静默无响应与流式中断排障：OpenCode 插件将 skills 动态注册为 command 后，在 Zed ACP 界面输入斜杠命令回车后无任何反应、无 Thinking、无文本、无报错，而去斜杠后可正常对话；深度揭示两重核心机制：1) OpenCode ACP 层（acp_turn.ts）对 command 在 submit 后执行 `if (prompt.command) return "succeeded"` 提前终结 Turn 并关闭事件流；2) 插件 execute 回调中若未 await `ctx.session.wait`，导致在数毫秒内即刻结案导致 Zed 0 token 接收。以及插件在 transform 中抛出未捕获异常导致整机插件被 disabled 导致 `/` 菜单只剩内置 4 条命令的时序坑；提供带 `ctx.session.wait` 的标准修复 SOP 与日志校验。
version: 1.0.0
created: 2026-11-03
updated: 2026-11-03
id: "110"
domain: agent
scope: opencode
type: fix
slug: "OpenCode插件ACP斜杠命令静默无响应排障"
status: verified
last_verified: "2026-11-03"
compatibility:
  os: ["windows"]
falsification_signals:
  - "若不带斜杠的消息也无法获得任何回复，说明是网络、API Key 或后端服务未启动问题，非本条目 ACP 拦截问题"
  - "若 Zed / 菜单中完全没有出现自定义命令，且确认没有安装或开启该插件，属于插件未加载范畴"
invocation:
  auto_trigger: true
  trigger_keywords: ["opencode skill 无响应", "opencode 斜杠命令没反应", "opencode 输入后没反应", "skills-as-commands", "session.wait", "acp_turn", "detectSlashCommand", "editor.add", "CommandEditor", "Zed ACP 命令失效", "availableCommands"]
---

# agent_opencode_fix_110_OpenCode插件ACP斜杠命令静默无响应排障

> **条目定位**：**Type A 疑难排障条目（OpenCode v2 插件系统 CommandEditor 契约 × ACP 协议斜杠命令提前终结机制）**  
> **危险评级**：★★☆☆☆（导致客户端输入的斜杠命令完全不触发任何界面输出、无思考状态且不抛错误，极易误判为网络假死或模型挂起）  
> **验证环境**：Windows 11、Zed 1.26.2+、OpenCode v2.2.5+（ACP 模式接入）。  
> **关联条目**：Zed ACP 架构与拦截见 `106_agent_acp_flow_ACP代理架构与ZedMode拦截及默认YOLO安全手刹.md`；OpenCode Go 模型与配置见 `043_agent_opencode_fix_OpenCodeGo模型提速与关闭思考reasoningEffort.md`。

---

## 一、现象与报错直击

### 1. 核心现场：Zed 中输入斜杠命令发送后“石沉大海”

在 Zed Assistant Panel（接入 OpenCode ACP）中：
1. 用户输入斜杠命令，例如 `/sh-cmd-monorepo-commit-push`，或者带参数 `/sh-cmd-monorepo-commit-push 使用` 并回车发送；
2. **现象**：发送后输入框内容被提交，面板下方**无任何响应**——没有 `💡 Thinking` 思考指示器、没有文本输出，也没有弹出任何错误提示（看起来就像点击被直接吞掉）；
3. **对比验证**：用户在同一会话中去掉前导斜杠，输入纯文本 `sh-cmd-monorepo-commit-push 使用这个 skill`，界面立刻恢复正常，显示 `💡 Thinking ...` 并正常输出模型回复。

```text
[用户输入] /sh-cmd-monorepo-commit-push           -> [结果] 完全无反应，输入框归位，无输出
[用户输入] /sh-cmd-monorepo-commit-push 使用      -> [结果] 完全无反应，输入框归位，无输出
[用户输入] sh-cmd-monorepo-commit-push 使用这个 skill -> [结果] 正常触发 💡 Thinking ... 并流式输出
```

### 2. 伴生现象：`/` 菜单中自定义命令突然全部消失，只剩 4 个内置命令

在尝试修改插件排障时，若在插件回调中引入了未捕获异常（如调用了不存在的方法），用户在 Zed 中按 `/` 时，菜单下拉框中原本加载的 40+ 个自定义技能命令全部消失，仅显示：
- `init`
- `review`
- `goal`
- `compact`

---

## 二、底层根因深度剖析

该故障由 OpenCode v2 的 **ACP 运行时提前终结（Turn Eager Exit）**、**`ctx.session.prompt` 异步入列特性** 以及 **插件异常整机禁用机制** 三重时序交织导致。

### 1. 根因一：OpenCode ACP 层对斜杠命令的提前终结机制（Eager Return）

查阅 OpenCode v2.2.5 ACP 核心实现 `acp_turn.ts:281-294`：

```ts
const execute = (attached: Attached, prompt: ACPPrompt.Prepared, turn: Turn) =>
  Effect.gen(function* () {
    const connected = yield* take(turn.subscription)
    if (connected.type !== "server.connected")
      return yield* Effect.die(new Error(`expected server.connected, got ${connected.type}`))
    
    // 1. 在后台 fork 一个 fiber 消费会话事件（负责把流式 token/thinking 推送给 Zed）
    const events = yield* consume(turn).pipe(Effect.forkScoped)

    return yield* Effect.gen(function* () {
      yield* submit(attached, prompt)
      // 2. 致命判定：如果输入的是 command，在 submit 执行完后直接 return "succeeded"！
      if (prompt.command) return "succeeded" as const
      // 3. 只有普通消息才会真正等待 events 消费完成！
      return yield* Fiber.join(events)
    }).pipe(Effect.onInterrupt(() => windDown(turn, events)))
  }).pipe(Effect.scoped)
```

对照两种输入的执行路径差异：
- **普通文本输入（无前导 `/`）**：`prompt.command` 为 `undefined`，代码执行到 `Fiber.join(events)`，ACP 保持当前 Turn 打开，持续接收服务端推送的 `part.delta`（思考过程与文本块），并通过 ACP `session/update` 通知 Zed 渲染 `💡 Thinking` 与 Markdown。
- **斜杠命令输入（带前导 `/`）**：`prompt.command` 命中，执行完 `submit` 后**立刻返回 `"succeeded"`**，提前结束当前 Turn！

### 2. 根因二：`ctx.session.prompt` 仅异步入列，未等待导致数毫秒内结案

当 `acp_turn.ts` 执行 `submit` 时，它会调用 `input.client.session.command(...)`，从而触发插件的 `execute` 回调：

```ts
// 插件原始写法
execute: async (input: any) => {
  await ctx.session.prompt({
    sessionID: input.sessionID,
    text: body,
    skills: [{ id }],
    delivery: input.delivery, // "steer"
  })
}
```

- 在 OpenCode 服务端，`ctx.session.prompt` 的作用仅是将 UserPayload 打包放入 `session_inbox`（异步入列），**大约 5 毫秒即可返回**，它**不会**等待模型生成完成；
- 由于插件在调用完 `ctx.session.prompt` 后直接退出 `execute`，整个 `submit` 在 5ms 内即判定完成；
- `acp_turn.ts` 随即触发 `if (prompt.command) return "succeeded"`，返回 `{ stopReason: "end_turn" }` 给 Zed 并**销毁当前 Turn 的 `events` 订阅**；
- 50ms 之后模型才刚刚连上 API 开始推理，但 Zed 这边的 Turn 已经关门结案，所有后续流式事件全部丢失！在 Zed 看来就是“输入了命令，但没有任何响应”。
- （在 OpenCode 底层 `opencode.db` 的 `session_message` 中实际能查到模型在后台完整生成了回复，只是 Zed 前端未建立连接）。

### 3. 根因三：插件 transform 异常导致插件被整机禁用

OpenCode 对插件 `command.transform` 的执行具有严格的保护机制。若在插件回调中误用了错误 API（例如误调不存在的 `draft.update` 抛出 `TypeError: draft.update is not a function`）：
- OpenCode 日志中会记录：`disabled plugin after transform failure plugin.id=skills-as-commands`；
- 该插件在当前运行进程中被**整体禁用**；
- 结果：ACP 的 `available_commands_update` 重新广播，所有由该插件注册的自定义命令被全部撤回，Zed 菜单回退到仅剩官方 4 个内置命令（`init`, `review`, `goal`, `compact`）。

---

## 三、排障与标准修复 SOP

### 1. 明确 OpenCode v2 Promise SDK 的真正接口

查阅 `@opencode/plugin` v2.2.5 官方源码（`promise_command.ts` / `packages_plugin_src_promise_adapter.ts`）：
- `command.transform` 传入的参数是 **`editor: CommandEditor`**；
- 其唯一合法方法是 **`editor.add(definition: CommandDefinition)`**，签名：
  ```ts
  editor.add({
    name: string,
    description?: string,
    execute: (input: CommandInvocation) => Promise<void>
  })
  ```
- **切勿臆测或误用** `draft.update` 等不存在的接口。

### 2. 在 `execute` 回调中加入 `ctx.session.wait` 阻塞保证流式传输

修复核心：在 `execute` 内提交 prompt 后，**显式调用 `await ctx.session.wait({ sessionID: input.sessionID })`**。
这样 `execute` 会阻塞直到该会话的大模型生成完成、会话重新进入 idle 状态。在此期间，`submit` 保持挂起，ACP 的 `events` fiber 可以持续不断地将 Thinking 与文本流推送到 Zed！

```ts
execute: async (input: any) => {
  const text = typeof input?.prompt?.text === "string" ? input.prompt.text.trim() : ""
  const body = text || `加载 ${id} skill，然后按它的指引执行。`

  // 1. 提交 Prompt 入列
  try {
    await ctx.session.prompt({
      sessionID: input.sessionID,
      text: body,
      skills: [{ id }],
      delivery: input.delivery,
    })
  } catch {
    await ctx.session.prompt({
      sessionID: input.sessionID,
      text: `加载 \`${id}\` skill，然后按它的指引执行。\n\n${body}`,
      delivery: input.delivery,
    })
  }

  // 2. 关键防护：等待会话生成完成，阻塞 submit 防止 acp_turn 提前结案掐断流
  try {
    if (typeof ctx.session?.wait === "function") {
      await ctx.session.wait({ sessionID: input.sessionID })
    }
  } catch {}
}
```

### 3. 完整生产级插件实现（`skills-as-commands/index.ts`）

```ts
import { Plugin } from "@opencode/plugin"

const RESERVED = new Set(["init", "review", "goal", "compact", "skill"])
const BUILTIN = new Set(["opencode", "report", "browser"])
const REFRESH = new Set(["skill.updated", "config.updated", "plugin.updated"])

export default Plugin.define({
  id: "skills-as-commands",
  async setup(ctx: any) {
    let entries = new Map<string, string>()
    let timer: ReturnType<typeof setInterval> | undefined
    let stopped = false
    let attempts = 0

    // 只注册一次 transform；回调每次读取最新的 entries 快照
    await ctx.command.transform((editor: any) => {
      for (const [id, description] of entries) {
        editor.add({
          name: id,
          description,
          execute: async (input: any) => {
            const text = typeof input?.prompt?.text === "string" ? input.prompt.text.trim() : ""
            const body = text || `加载 ${id} skill，然后按它的指引执行。`
            try {
              await ctx.session.prompt({
                sessionID: input.sessionID,
                text: body,
                skills: [{ id }],
                delivery: input.delivery,
              })
            } catch {
              await ctx.session.prompt({
                sessionID: input.sessionID,
                text: `加载 \`${id}\` skill，然后按它的指引执行。\n\n${body}`,
                delivery: input.delivery,
              })
            }

            // 保持 ACP 握手连接存活，确保流式推送到 Zed
            try {
              if (typeof ctx.session?.wait === "function") {
                await ctx.session.wait({ sessionID: input.sessionID })
              }
            } catch {}
          },
        })
      }
    })

    const same = (a: Map<string, string>, b: Map<string, string>) =>
      a.size === b.size && [...a].every(([k, v]) => b.get(k) === v)

    const refresh = async (): Promise<boolean> => {
      if (stopped) return false
      let rawResponse: any = null
      try {
        rawResponse = await ctx.skill.list()
      } catch {
        return false
      }

      const data: any[] = Array.isArray(rawResponse) ? rawResponse : (rawResponse?.data ?? [])
      const next = new Map<string, string>()
      for (const skill of data) {
        const id = typeof skill?.id === "string" ? skill.id : ""
        if (!id || RESERVED.has(id) || BUILTIN.has(id)) continue
        if (!skill?.description) continue
        next.set(id, String(skill.description).slice(0, 240))
      }
      if (next.size === 0) return false
      if (same(next, entries)) return true

      entries = next
      await ctx.command.reload()
      return true
    }

    const stopTimer = () => {
      if (timer) clearInterval(timer)
      timer = undefined
    }

    const tick = () => {
      void refresh()
        .then((done) => {
          if (stopped) return
          if (done) stopTimer()
          else if (++attempts > 60) stopTimer()
        })
        .catch(() => {})
    }

    // 严禁 await：让 setup 立即返回，不阻塞后续 ConfigSkillPlugin 激活
    timer = setInterval(tick, 1000)
    setTimeout(tick, 0)

    // 订阅配置与插件更新事件
    void (async () => {
      try {
        for await (const event of ctx.event.subscribe()) {
          const type = (event as { type?: string })?.type ?? ""
          if (!REFRESH.has(type)) continue
          attempts = 0
          if (!timer) timer = setInterval(tick, 1000)
          tick()
        }
      } catch {}
    })()

    return () => {
      stopped = true
      stopTimer()
    }
  },
})
```

---

## 四、验证与防复发检视

1. **热加载验证**：保存插件代码后无需重启 Zed，OpenCode 会自动触发热重载；
2. **菜单补全测试**：在 Zed 对话框中输入 `/`，确认出现 `40+` 个以 `sh-*` / `kb-*` 开头的自定义命令列表（非仅有 4 个内置命令）；
3. **流式执行测试**：选择任一命令（如 `/sh-user-skills`）回车发送，确认面板立即显示 `💡 Thinking` 思考气泡，并在生成完毕后正常流式输出排版完好的回复内容；
4. **数据库落地检查**：通过查询 `%USERPROFILE%\.local\share\opencode\opencode.db` 的 `session_message` 表，确认 `user` 提问与 `assistant` 回复时间戳及内容完整入库。
