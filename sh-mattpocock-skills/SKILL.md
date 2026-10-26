---
name: sh-mattpocock-skills
description: |
  Matt Pocock 官方技能库分流路由器：收录并管理 mattpocock/skills 官方全量原子技能（工程研发、效率工具、实验特性等）。当用户指定本技能时，动态感知已下载的官方技能清单，以决策树与交互式提问（Ask Matt 模式）主动询问用户想要做什么，精准分流并加载对应官方技能。点名使用。
version: 1.0.0
created: 2026-10-26
updated: 2026-10-26
---

# sh-mattpocock-skills: Matt Pocock 官方技能库与动态分流路由器

> **定位声明**：本技能是 Matt Pocock 官方技能生态（GitHub: `mattpocock/skills`）的本地归集与动态分流总枢纽。
>
> **核心契约**：全量官方技能均收纳于本目录下的 `skills/` 绝缘子目录中。当用户通过 `/sh-mattpocock-skills` 或点名唤起时，AI 动态感知当前已下载的官方技能列表，**以交互式提问（Ask Matt 模式）主动询问用户想要做什么**，并在确认后精准载入对应的官方子技能执行。

---

## 一、交互式分流协议（Ask Matt Interactive Protocol）

当用户唤起本技能时，AI 必须严格按以下两个场景执行：

### 场景 A：裸呼叫（用户未指定明确任务或仅呼叫 `/sh-mattpocock-skills`）
AI 必须**主动询问用户想要做什么**，并按照官方 Ask-Matt 流转拓扑给出清晰的选项指引：

> 💡 **请问您当前处于研发的哪个阶段，或希望执行什么任务？**
>
> 1. 🔍 **需求审问与共识对齐**：
>    - `grill-with-docs`：结合当前代码仓现状深入审问，将术语与决策固化入 `GLOSSARY.md` 与 ADR
>    - `grill-me`：无状态快速审问，一次一问并附带推荐选项，逼出清晰设计概念
>    - `wait-what`：上一步没听懂或偏差较大，叫停并重新梳理
> 2. 🗺️ **大图破雾与方案探索**：
>    - `wayfinder`：面对跨多会话的大型模糊工程，绘制决策工单地图
>    - `prototype`：构建一次性抛弃型原型（UI 或核心业务逻辑），先看效果再写生产代码
>    - `research`：针对第三方库或底层 API 进行权威第一手信源调研
> 3. 📐 **领域建模与规范制定**：
>    - `domain-modeling`：提炼领域模型、限界上下文与通用语言
>    - `to-spec`：将前期审问共识直接合成为高密度实施规范与测试接缝（Seams）
>    - `to-questionnaire`：将无法决断的问题转换为结构化问卷
> 4. 🎫 **垂直切片拆票**：
>    - `to-tickets`：按曳光弹原则将规范拆解为穿透全层的垂直切片与 DAG 依赖图
> 5. ⚡ **测试驱动与实现落地**：
>    - `tdd`：严格遵循红-绿-重构循环编写高质量可测代码
>    - `implement`：针对单个 Ticket 锁定 Seam 并在独立会话中完成实现
>    - `implement-spec`：基于任务依赖图自动化编排落地整个规范
> 6. 🔍 **代码审查与交付**：
>    - `code-review`：Standards 规范轴 + Spec 需求轴双轴独立审查 diff
>    - `pr`：撰写带有清晰变动、前后证据与单双向门决策的高质量 PR 说明
> 7. 🛠️ **排障、架构与复盘**：
>    - `diagnosing-bugs`：针对疑难 Bug 构建紧反馈闭环（Tight Feedback Loop）并根治
>    - `improve-codebase-architecture`：Git Commit 热点分析、Deletion Test 与深模块演进
>    - `retro`：复盘编码会话，提炼机器环境与编码规范的防错改进
> 8. 📚 **效率、分流与实验性工具**：
>    - `triage`（Bug 分诊与状态机）、`teach`（概念教学）、`writing-for-agents`（Agent 提示词编写）、`handoff`（跨会话交接）等。

---

### 场景 B：带意图呼叫（用户已输入具体需求，如 `我要做代码审查` 或 `帮我拆个票`）
1. **意图匹配**：AI 对照下方的 [官方技能全景速查表](#二官方技能全景速查表)，定位 1~2 个最匹配的官方技能；
2. **加载子模块**：通过文件读取工具读取对应的 `sh-mattpocock-skills/skills/<category>/<skill-name>/SKILL.md`；
3. **遵循执行**：严格按照官方子技能定义的流程、上下文规则与产出格式协助用户完成任务。

---

## 二、官方技能全景速查表 (Official Skills Inventory)

当前本地已完整收纳 **38 个官方技能**：

### 1. 工程研发类 (`engineering` - 20 个)

| 技能名称 | 核心职责与触发场景 | 子模块执行路径 |
| :--- | :--- | :--- |
| `ask-matt` | 官方主路由器：根据用户当前处境推荐适合的技能或流转路径 | `skills/engineering/ask-matt/SKILL.md` |
| `code-review` | 针对固定基准点的 diff 实施 Standards 轴 + Spec 轴双轴代码审查 | `skills/engineering/code-review/SKILL.md` |
| `codebase-design` | 基于《软件设计哲学》深模块理论设计厚接口与良好封装 | `skills/engineering/codebase-design/SKILL.md` |
| `diagnosing-bugs` | 疑难 Bug 与性能退化排障：建立秒级自动判断的紧反馈闭环 | `skills/engineering/diagnosing-bugs/SKILL.md` |
| `domain-modeling` | 提炼并打磨领域模型，生成 `CONTEXT.md`、`GLOSSARY.md` 与 ADR | `skills/engineering/domain-modeling/SKILL.md` |
| `grill-with-docs` | 在现有代码库中深度访谈，将共识持久化在术语表与决策记录中 | `skills/engineering/grill-with-docs/SKILL.md` |
| `implement` | 基于 Spec 或 Ticket 锁定测试接缝并进行单项实现 | `skills/engineering/implement/SKILL.md` |
| `implement-spec` | 基于 `to-spec` 与 `to-tickets` 的任务图，多任务编排实现整个规格 | `skills/engineering/implement-spec/SKILL.md` |
| `improve-codebase-architecture` | 扫描 Git 热点高摩擦代码，运行 Deletion Test 并提出深模块演进方案 | `skills/engineering/improve-codebase-architecture/SKILL.md` |
| `pr` | 撰写带有最小视觉证据、前后测试结果与决策评估的 Pull Request 正文 | `skills/engineering/pr/SKILL.md` |
| `prototype` | 构建一次性抛弃型原型（验证业务逻辑或 UI 触感），验证即扔 | `skills/engineering/prototype/SKILL.md` |
| `research` | 针对官方源码与第一手权威信源进行调研，输出带引用的调查笔记 | `skills/engineering/research/SKILL.md` |
| `retro` | 对编码会话实施复盘，将偶发错误转化为自动化规则与环境规范 | `skills/engineering/retro/SKILL.md` |
| `setup-matt-pocock-skills` | 为当前仓库配置 Matt Pocock 工程技能环境与脚本依赖 | `skills/engineering/setup-matt-pocock-skills/SKILL.md` |
| `tdd` | 测试驱动开发：严格执行红（失败测试） $\to$ 绿（最小实现） $\to$ 重构 | `skills/engineering/tdd/SKILL.md` |
| `to-spec` | 将对话中的共识与设计意图合成为无二义性的目的地技术规范 | `skills/engineering/to-spec/SKILL.md` |
| `to-tickets` | 垂直切片（Tracer Bullets）拆解任务，输出带 DAG 依赖关系的 Tickets | `skills/engineering/to-tickets/SKILL.md` |
| `triage` | 状态机流转外部 Issue 与 PR，将原始反馈整理为 Agent 可直接消费的工单 | `skills/engineering/triage/SKILL.md` |
| `wayfinder` | 面对迷雾庞大工程绘制决策地图，每次仅决断一个孤立决策项 | `skills/engineering/wayfinder/SKILL.md` |
| `wizard` | 生成可交互的 Bash Wizard 脚本，引导人类按步骤执行敏感流程 | `skills/engineering/wizard/SKILL.md` |

### 2. 生产力与对齐类 (`productivity` - 7 个)

| 技能名称 | 核心职责与触发场景 | 子模块执行路径 |
| :--- | :--- | :--- |
| `grill-me` | 无状态需求审问：一次一问且带推荐答案，直到扫清全部模糊假设 | `skills/productivity/grill-me/SKILL.md` |
| `grilling` | 底层审问原语驱动引擎：状态机 Frontier 决策树推进 | `skills/productivity/grilling/SKILL.md` |
| `handoff` | 将当前会话的上下文压缩生成交接文档，供新会话接续 | `skills/productivity/handoff/SKILL.md` |
| `teach` | 向用户耐心讲解特定技术概念或工程技能（概念、示例、动手练习） | `skills/productivity/teach/SKILL.md` |
| `to-questionnaire` | 将无法一口气决断的设计问题转化为交互式多选问卷 | `skills/productivity/to-questionnaire/SKILL.md` |
| `wait-what` | 及时叫停脱轨理解：要求 AI 换一种表达方式重新阐述 | `skills/productivity/wait-what/SKILL.md` |
| `writing-for-agents` | 编写面向 AI Agent 的高确定性文档、规范与提示词 | `skills/productivity/writing-for-agents/SKILL.md` |

### 3. 进行中探索类 (`in-progress` - 7 个)

| 技能名称 | 核心职责与触发场景 | 子模块执行路径 |
| :--- | :--- | :--- |
| `chief-of-staff` | 幕僚长模式：在单会话内通过子 Agent 编排推进长期大目标 | `skills/in-progress/chief-of-staff/SKILL.md` |
| `claude-handoff` | 将会话平滑交接至新鲜后台子会话 | `skills/in-progress/claude-handoff/SKILL.md` |
| `loop-me` | 审问工作流规格与循环编排 | `skills/in-progress/loop-me/SKILL.md` |
| `setup-ts-deep-modules` | 为 TypeScript 项目配置 dependency-cruiser 强制深模块边界检查 | `skills/in-progress/setup-ts-deep-modules/SKILL.md` |
| `writing-beats` | 写作开发：将素材碎片装配为日志叙事 | `skills/in-progress/writing-beats/SKILL.md` |
| `writing-fragments` | 写作探索：发掘原子观点碎片 | `skills/in-progress/writing-fragments/SKILL.md` |
| `writing-shape` | 写作提炼：将原始素材打磨成成型文章 | `skills/in-progress/writing-shape/SKILL.md` |

### 4. 辅助杂项类 (`misc` - 4 个)

| 技能名称 | 核心职责与触发场景 | 子模块执行路径 |
| :--- | :--- | :--- |
| `git-guardrails-claude-code` | 设置 Git 危险提交拦截守卫钩子 | `skills/misc/git-guardrails-claude-code/SKILL.md` |
| `migrate-to-shoehorn` | 迁移测试文件中的类型断言至 @total-typescript/shoehorn | `skills/misc/migrate-to-shoehorn/SKILL.md` |
| `scaffold-exercises` | 快速搭建交互式教学练习与题目目录骨架 | `skills/misc/scaffold-exercises/SKILL.md` |
| `setup-pre-commit` | 自动配置 Husky + lint-staged 提交前代码质量守卫 | `skills/misc/setup-pre-commit/SKILL.md` |

---

## 三、资产管理与一键更新协议 (Sync & Update SOP)

本目录内置了自动化同步管理工具 `sync_mattpocock_repo.py`：

```powershell
# 1. 检查本地与 GitHub 官方最新 Commit 差异：
python sync_mattpocock_repo.py --check

# 2. 列出本地已下载的全部技能及其分类：
python sync_mattpocock_repo.py --list

# 3. 一键从上游拉取更新并覆盖 skills/ 目录：
python sync_mattpocock_repo.py --update
```

当用户指示 **“更新 mattpocock 技能库”** 或 **“同步最新的官方技能”** 时，AI 直接执行 `python sync_mattpocock_repo.py --update` 即可全自动完成拉取并刷新版本记录。
