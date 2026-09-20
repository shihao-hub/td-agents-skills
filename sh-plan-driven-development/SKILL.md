---
name: sh-plan-driven-development
description: Kiro Autopilot 式阶段计划门控开发：把复杂任务拆成顺序 Stage、每个 Stage 独立可验证，计划以固定格式（📋 Plan for / Stage N: / 最后一行 [OPTION: Go | Go All | Cancel]）呈现并停在审批门，获批后逐 Stage 执行、Stage 内任务并行、Stage 间 checkpoint 汇报，Go All 自动推进、失败即停、每 Stage 最多 3 轮。当用户说 "autopilot"、"autopilot 这个"、"plan this"、"计划一下/拆解一下这个任务"、"先出方案再动手"、"分阶段推进 X"，或任务有多个相互依赖的阶段、跨多文件/系统、中途值得用户把关时使用——即使没说"计划"二字，只要是对话内多阶段推进都应触发本 skill。要产出计划文档（plans/ 落盘、只读调研后写文件）改用 sh-claude-plan-mode；要 requirements/design/tasks 三文档正式评审改用 sh-spec-driven-development。
version: 1.0.0
created: 2026-09-21
updated: 2026-09-21
---

# Plan-Driven Development（Autopilot）：阶段计划 → 批准 → 执行

## 版本信息

| 项 | 值 |
|---|---|
| 版本 | 1.0.0 |
| 创建 | 2026-09-21 |
| 更新 | 2026-09-21 |

本 skill 的机制提炼自 Kiro Crew 开源仓库（github.com/kirodotdev/KiroCrew，Apache-2.0）的 orchestrator/Autopilot 系统提示词 `src/kiro_crew/config/prompt-orchestrator.md`（2026-09 提取），适配到对话式 agent 环境：不依赖 KiroCrew 专属 MCP 工具，子代理可用可不用，规则不变。目录名沿用本位置先前的 sh-plan-driven-development；原 Claude plan mode 技能已让名并更名回 sh-claude-plan-mode，两者机制互相独立。

## 核心理念

Autopilot 是一条三段式纪律：**计划 → 批准 → 执行**。

- 复杂任务先拆成顺序 Stage、获用户批准、再动手。计划一旦批准就是唯一事实来源：不重新计划，只针对意外阻塞提针对性问题。
- **计划门是硬停止点**：发出计划（以 `[OPTION: Go | Go All | Cancel]` 结尾）后立即结束回合——不调工具、不做调研、不开始任何 Stage 工作。等待批准期间做的每一件事都在破坏门控。
- **判断复杂性看内在复杂度，不看步骤数量**。一个任务可以有很多步骤但依然简单（查点资料 → 提一个 PR）——直接做。别把单一连贯任务变成仪式。

## 何时计划（裁决规则）

**显式计划请求永远赢，任何语言都算**："autopilot"、"autopilot mode"、"autopilot 这个"、"计划一下"、"plan this"、"break this down"、"拆解这个任务"、"先出个方案"、"map out a strategy"。命中即必须出计划：再小的任务也拆 2-3 个聚焦 Stage、以验证 Stage 收尾，绝不直接开答或直接执行。

没有显式请求时，**三条全中**才计划：

1. 多个相互区分的依赖阶段（阶段之间有先后依赖）
2. 跨多个文件/系统
3. 存在有用的中间方向检查点（中途让用户把一次关是值得的）

对齐直觉，别对齐 Stage 数量。复杂工作先对齐方向；简单工作先做完再说。

**直接执行**（不需要计划）的清单：读取/问答/命令/查询类、中小型编辑、单文件或机械性改动、处理少量 review 意见、任何"唯一自然的检查点就是完成"的一次聚焦通过。几次工具调用本身不构成计划理由。

呈现计划之前允许做快速的范围调研（scoping research）；**计划获批之后不再允许"再调研一轮"**——那是重新计划的变体。

## 计划格式（强约束）

计划必须精确遵循以下结构：

```
📋 Plan for: "Migrate auth module to new API"

Stage 1: Analysis
  - Read current auth module and new API docs
  - Identify all endpoints that need changes

Stage 2: Implementation
  - Update auth.py with new API calls
  - Update config.py with new endpoints

Stage 3: Validation
  - Run existing tests
  - Fix any failures

Stage 4: Verification
  - Run full test suite to confirm nothing is broken

[OPTION: Go | Go All | Cancel]
```

格式规则：

1. 以 `📋 Plan for: "<描述>"` 开头
2. `Stage N: <标题>` 独立成行、从 1 顺序编号；每个 Stage 下面是缩进的 `- <任务>` bullet，各占一行，绝不把多个 Stage 合并到一行
3. 以 `[OPTION: Go | Go All | Cancel]` 作为**最后一行**收尾：恰好出现一次、其后**没有任何内容**。澄清问题、备注、上下文全部放在这一行**之前**
4. 计划门的 `[OPTION: …]` footer 与通用的 `[OPTIONS: …]` 选项行是**不同的标签**：一条消息里不得同时出现两者

格式不合规定的后果（对用户如实说明）：格式不正确的计划会被纠正重发；无法纠正的计划将被当作普通任务直接执行——那意味着失去阶段门，宁可一开始就写对。

### Stage 设计规则

- Stage 之间总是**顺序**：Stage 1 完成后 Stage 2 才开始；Stage 内的任务**并行**
- 每个 Stage **独立可验证**——进入下一个之前能检查它的产出
- **最后一个 Stage 必须是验证**：跑测试、检查结果、确认工作正确
- 限制的是单 Stage 的**复杂度**而不是 Stage 数量：每个 Stage 是一个聚焦、独立可验证的单元，理想情况一轮完成（上限 3 轮，见"执行"）。大 Stage 要拆；5-8 个简单 Stage 没问题，但别塞凑数的琐碎 Stage
- Stage 体量要能在合理时间内完成——宁可更多更小的 Stage，也不要一个巨型 Stage；不要把 Stage 挂在长轮询上干等外部事件（外部等待交给后台监控/定时任务，Stage 只做能推进的事）

## 审批门

**选项语义：**

- **Go** —— 执行下一个 Stage，之后在每个 Stage 前暂停再批
- **Go All** —— 自动执行全部剩余 Stage，不再逐个暂停；失败或触发升级条件即停
- **Cancel** —— 中止计划

门上纪律：

- 发出 `[OPTION: Go | Go All | Cancel]` 后**立即结束回合**：没有工具调用、没有调研、没有 Stage 工作
- 用户改计划 → 更新并重新呈现，重新过门；一旦批准 → **不再重新计划**，遇到意外阻塞问针对性问题
- 展示计划本身就是请求批准——不要在 footer 后追加"这个计划可以吗？"之类的问题（见常见坑）

## 执行

职责分工：**你拥有分解、排序与综合；繁重的读/写/命令交给子代理**。有子代理工具（如 Task）就并行派发；没有就按同样规则顺序自己做——分工逻辑不变，只是并发度不同。

- Stage 内的独立任务**一批**派发；有依赖的排到后续批次或留在父级。绝不派发需要"仍在运行中的结果"的任务
- 简单的读取/检查/小型调研自己做——快且省；单个不可分单元留在父级，除非需要专家模型或上下文隔离
- 派发后汇报"已派发什么"并**结束回合**；等**全部**结果回来再综合或派下一批。读的是实际产出，不是调度确认或进度摘要
- **Stage 可以多轮**：派一批、收结果、目标没达成就再派一批——每 Stage **最多 3 轮**；3 轮仍未达成 → 保存已有成果（checkpoint）并问用户
- **Stage 之间做 checkpoint**：完成后用一两行总结再继续，如 `✅ Stage 1 complete: Found 12 endpoints, 3 use deprecated auth flow. Proceeding to Stage 2...`
- **Stage 失败：停下问用户**——不盲目重试，不自动进入下一 Stage
- **Go All（自动模式）**下：checkpoint 后直接进入下一 Stage，不输出 `[OPTION]`；失败仍然停
- 长对话中如果环境提供会话账本/工作记录机制，把每 Stage 的目标、尝试与产出写进去——账本在上下文压缩后仍然可靠，胜过对先前轮次的回忆

## 何时求助（执行期裁决）

**已批准的执行期内：自己决定，继续干。** 可逆的判断/设计/范围选择——选最稳妥、最完整、保持工作正确的答案；倾向简单可逆的设计；带上必要的测试；用一行说明你选了什么；Go All 中也照常继续。**不要发明新的业务需求**。

只有四种情况打断用户：

1. **同一子任务 3 次尝试失败**：总结三次尝试，求指引。绝不静默地用同一思路重试超过 3 次
2. 缺凭证、权限或你拿不到的访问
3. 计划未覆盖的破坏性/不可逆动作（数据丢失、生产变更、force-push）
4. 子代理结果直接冲突且没有安全默认值

失败的 Stage 停止执行：告诉用户什么失败了、问一个**针对性**问题——绝不盲目继续，也不重新呈现整个计划。可枚举的选择用 `[OPTIONS: …]` 选项行提问；其余情况自己决定，不打断。

## 从回答中学习

用户在门上或求助时做出的每一次裁决，**立即记录**（项目笔记 / AGENTS.md / 环境的记忆机制，按可用性选）：写清"以后要做什么 + 避免什么"；只对单一代码库生效的纠正，注明作用范围。同一个问题不该问第二遍。

## 常见坑

- **footer 后面还有内容**：`[OPTION: Go | Go All | Cancel]` 必须是消息的最后一行；任何后缀（追问、客套、总结）都会破坏门控语义
- **计划门后继续调工具**：发出计划又"顺手查一下"——门形同虚设
- **把单一任务拆成仪式**：三次编辑能完成的事拆四个 Stage；判断标准是内在复杂度，不是步骤数
- **3 轮失败后静默重试第 4 轮**：违反求助规则，浪费的是用户的等待
- **Go All 期间频繁打断**：可逆决策自己拍板继续，四种情况之外别问
- **读调度确认当结果**：子代理"已启动/进行中"不是完成；收齐实际产出再综合
- **重新计划代替针对性提问**：批准后遇到阻塞，问具体问题，别把整个计划推倒重来
- **Stage 粒度过大**：一轮塞不下、目标含糊；拆小，让每个 Stage 的"完成"可判定

## 与相关 skill 的分工

- **本 skill**：对话内阶段计划门控（Autopilot 式 Go/Go All/Cancel，不落盘、轻量、Stage 循环）
- **sh-claude-plan-mode**：Claude plan mode 式只读调研 + `plans/{NN}-{name}.md` 文件落盘审批 + 逐 Phase 执行勾选
- **sh-spec-driven-development**：requirements/design/tasks 三文档正式评审流程
- 裁决：用户说 autopilot、要求对话内拆阶段推进 → 本 skill；要求"计划文件/文档化计划/先只读调研" → sh-claude-plan-mode；说出 "spec"、"三份文档" → sh-spec-driven-development

---
**最后更新：** 2026-09-21
**作者：** AI & User
**版本：** v1.0.0

## 变更记录

| 版本 | 日期 | 说明 |
|---|---|---|
| 1.0.0 | 2026-09-21 | 初版：机制提炼自 Kiro Crew 开源仓库（kirodotdev/KiroCrew，Apache-2.0）orchestrator/Autopilot 系统提示词（src/kiro_crew/config/prompt-orchestrator.md，2026-09 提取）：Stage 计划格式与强约束、[OPTION: Go/Go All/Cancel] 审批门、"显式请求永远赢 + 三条件"裁决、Stage 最多 3 轮、执行期四类求助、从裁决中学习；适配对话式 agent 环境（子代理可选、无 KiroCrew 专属工具）。目录名沿用本位置先前的 sh-plan-driven-development，原 Claude plan mode 技能已让名并更名回 sh-claude-plan-mode（其变更记录见该 skill 的 2.4.1 条目） |
