---
name: sh-agy-skills
description: antigravity 斜杠命令技能族路由器：点名使用后，按用户后续内容自动分流到子目录 skill（goal/schedule/browser/grill-me/teamwork/learn/boost/plan）。不确定时列候选向用户确认。本 skill 自身不执行任务，只做指引分流
version: 1.0.0
created: 2026-09-25
updated: 2026-09-25
---

# sh-agy-skills：指引式路由入口

> 版本 v1.0.0 ｜ 本目录是 antigravity 斜杠命令技能族：每个子目录是一个完整独立的 skill（含自己的 SKILL.md，可单独拆出使用）。本顶层文件是唯一注册入口，只负责把用户的认知内容分流到对应子目录。

## 定位

本 skill **没有执行逻辑**。用户点名 `sh-agy-skills`（或"用 agy 那套技能"等同义表达）之后，后续内容交给路由表判断，分流到子目录 skill 执行。所谓分流 = 定位到子目录，加载该子目录的 SKILL.md 并严格按其执行。

## 路由协议

1. **取内容**：点名词之后同一条消息里的内容即路由对象；点名后没有实质内容的，等下一条消息再路由，不抢跑。
2. **匹配**：按下方路由表 + 消歧规则判断内容指向哪个子 skill。
3. **分流执行**（三选一）：
   - **唯一高置信匹配** → 加载对应子 skill → 向用户宣告"已分流到 sh-agy-xxx" → 严格按其 SKILL.md 执行，本文件使命结束。
   - **多候选或拿不准** → 列出候选子 skill（各附一句理由，给推荐），向用户确认后再分流。
   - **零匹配** → 用路由表的一句话职责清单向用户汇报 8 个子 skill，请用户指认。
4. **加载方式**：若当前环境已把某子 skill 注册为可调用技能，直接用 skill 工具加载；否则用 read 工具读取 `<本目录>/sh-agy-xxx/SKILL.md` 全文并严格遵循。两条路等价，后者是常态。
5. **组合分流**：内容明确要求叠加时支持组合（如 boost+goal = 深度强化并跑到完全交付），按依赖顺序执行；拿不准是否要组合时，问用户。

## 路由表

| 子 skill | 路径 | 一句话职责 | 典型触发信号 |
|---|---|---|---|
| sh-agy-goal | `sh-agy-goal/SKILL.md` | 长任务自治托管：执行→验证→修复循环，交付物证据审计直到完全达成 | "跑到达成为止""通宵跑""托管""全自动做完再停" |
| sh-agy-schedule | `sh-agy-schedule/SKILL.md` | 定时与调度：延时提醒、周期性任务（Windows schtasks 适配） | "10 分钟后""每小时""每天早上""定时""周期性监控" |
| sh-agy-browser | `sh-agy-browser/SKILL.md` | 浏览器智能体：真实浏览器交互、动态页抓取、UI/E2E 测试 | "打开网页操作""模拟点击/填表""看实际渲染效果""E2E" |
| sh-agy-grill-me | `sh-agy-grill-me/SKILL.md` | 拷问访谈：AI 逐题提问（每题附推荐答案）对齐需求 | "我有个想法还没想透""先问我问题理清" |
| sh-agy-teamwork | `sh-agy-teamwork/SKILL.md` | 多智能体协同：9 步打磨任务书后委派子代理团队分工 | "超大工程""多模块并行""团队式分工开发" |
| sh-agy-learn | `sh-agy-learn/SKILL.md` | 经验沉淀：把纠正与成功经验固化为 rule/skill 提案 | "记住这个教训""沉淀下来""以后别再犯" |
| sh-agy-boost | `sh-agy-boost/SKILL.md` | 深度思考增强：方案权衡+对抗审查+独立验证多遍强化 | "这道难题不容有失""并发/死锁""核心算法""要对抗审查" |
| sh-agy-plan | `sh-agy-plan/SKILL.md` | 慎密规划：先出实施计划获批再动代码（含 walkthrough 收尾） | "先出方案确认再动手""先规划再改" |

## 消歧规则

易混对的判定依据（优先级从上到下）：

- **goal vs plan**：需求已明确、要自治跑到交付 → goal（执行导向）；动手前先产出计划给人审 → plan（审阅导向）。
- **goal vs boost**：要长时间跑到完成 → goal；单点高难要做对（质量强化）→ boost。两者都命中且用户要求"又难又要跑到底"→ 组合 boost+goal。
- **plan vs grill-me**：需求已清楚、产出结构化计划 → plan；需求本身没想透、先访谈理清 → grill-me（grill-me 收敛后可转 plan）。
- **teamwork vs boost**：规模大到要拆分工 → teamwork；难度高到要深挖验证 → boost。
- **schedule vs goal**：按时间触发才做 → schedule；立即开跑直到完成 → goal。
- **learn 永远是事后**：复盘沉淀资产，不解决当前任务；用户在推进任务途中提到"记一下"时，先问是"现在就沉淀（learn）"还是"做完再说"。

## 溯源

子 skill 均移植自 Google Antigravity 斜杠命令，原始提示词与工具描述提取自 language_server.exe（2026-09-23 构建），全文见 `references/agy-extracted-prompts.md`（含二进制提取夹带的 proto 碎片，作原始证据原样保留，不清理）。

## 边界

- 本文件只分流，不执行；分流宣告后一切以子 skill 的 SKILL.md 为准。
- 子 skill 均为完整独立单元：frontmatter 与正文原样保留，可单独拆出目录使用。
- 新增子 skill 时：建子目录放 SKILL.md，并在上方路由表加一行、必要时补消歧规则。
