# Plan: 以 disable-model-invocation 强化"点名直调"语义（机制 + 文案双保险）

📋 Plan for: "3 个提级暴露位（sh-plan-driven-development / sh-spec-driven-development / sh-skill-authoring-rules）缺少 `disable-model-invocation` 硬约束，仅靠 description 内'点名使用'四字软劝阻，会与 `sh-user-skills` 分流器争夺自动路由。补机制、留文案兜底、同步修订创作规范。"

## 问题陈述

1. **暴露位职责漂移**：`expose_user_skill.py` 的设计目的是把高频子技能提级到根级，供用户 `/skill:<name>` 直调、省去"先调分流器再打字"的摩擦。但暴露后即进入全局清单，若不加 `disable-model-invocation`，模型会自动路由这些技能，与 `sh-user-skills`（模糊需求分流器）形成双入口竞争。
2. **软约束不可靠**：description 结尾的"点名使用"四字是写给模型看的劝告，模型可忽略；机制层拦截才 100% 确定（pi 已验证 `formatSkillsForPrompt` 直接 filter 掉该字段为 true 的技能）。
3. **跨 Harness 兼容性未知**：`disable-model-invocation` 是 Agent Skills 规范字段，pi 已实现；OpenCode / Codex / Antigravity 是否识别未实测。故不可单靠机制，需保留文案兜底。

## 需求确认（含用户决策）

- **双保险策略**：加 `disable-model-invocation: true` 的同时，description 保留"点名使用"四字，作为不识别该字段的 Harness 的兜底。用户原话："*确实很有可能不认的*"。
- **`sh-agy-skills` 暂不处理**：其"点名使用"与卷一 §2 路由器例外条款的矛盾，本轮不解决。用户原话："*先不管*"。
- **提交拆分**：两次独立提交——① 缺陷修复（已完成）；② 本次规范化改造。用户原话："*可以的*"。
- **32 个 README 子技能不动**：它们以 `README.md` 绝缘全局探测，永不进入 skills 注册表，`disable-model-invocation` 写在那里不被任何解析器读取，属纯装饰。

## 背景现状

- 根级技能 40 个，其中 7 个已带 `disable-model-invocation`（`grill-me`、`grill-with-docs`、`wayfinder`、`implement`、`improve-codebase-architecture`、`to-spec`、`to-tickets`，均为第三方引入）。
- 3 个提级暴露位当前 **0 个**带该字段；其中 `sh-plan-driven-development`(102 字符)、`sh-spec-driven-development`(53 字符) 的 description 含"点名使用"，`sh-skill-authoring-rules`(305 字符) 不含。
- pi 实现细节（已读源码 `dist/core/skills.js`）：`disableModelInvocation: frontmatter["disable-model-invocation"] === true`（严格布尔），`formatSkillsForPrompt` 用 `filter(s => !s.disableModelInvocation)` 排除；但 `/skill:name` 命令注册遍历全量 skills，不受该字段影响 → 直调能力保留。
- 当前可见清单 33 个，改造后预期降为 30 个。

## 任务分解

- [x] Task 1: 修订创作规范 `sh-user-skills/sh-skill-authoring-rules/README.md`
  - 文件：`sh-user-skills/sh-skill-authoring-rules/README.md`（真身，暴露位为软链自动跟随）
  - 实现：
    - 卷一 §2「description 编写标准」首条：保留"结尾固定 `点名使用`"，补充"若该技能已被 Harness 注册且期望仅直调，须同时声明 `disable-model-invocation: true`，文案仅作跨端兜底"
    - 卷二 §4「提级暴露机制」：在三条硬约束后新增第 4 条——暴露后必须在真身 frontmatter 声明 `disable-model-invocation: true`，否则将参与自动路由并与 `sh-user-skills` 竞争
    - 卷二 §4 已暴露位清单处：标注三者均已 disable
    - 附录 Checklist：新增一项"提级暴露位是否已声明 `disable-model-invocation: true`？"
    - 版本号 `2.6.0` → `2.7.0`，`updated` 改 `2026-10-19`
  - 验证：`rg -n "disable-model-invocation" sh-user-skills/sh-skill-authoring-rules/README.md` 命中 ≥4 处
  - Demo：规范中"机制 + 文案双保险"表述可直接对照执行

- [x] Task 2: 三个暴露位真身加字段
  - 文件：`sh-user-skills/sh-plan-driven-development/README.md`、`sh-user-skills/sh-spec-driven-development/README.md`、`sh-user-skills/sh-skill-authoring-rules/README.md`
  - 实现：在各 frontmatter 的 `description` 之后插入 `disable-model-invocation: true`；不动 description 文案（保留"点名使用"兜底）
  - 验证：`uv run expose_user_skill.py <name> --check` 三者均通过（链接未失联）
  - Demo：`/skill:sh-plan-driven-development` 仍可调用，但不再出现在自动路由清单

- [x] Task 3: 机制验证与回归
  - 文件：无（只读校验）
  - 实现：调用 pi 的 `loadSkillsFromDir` 复核加载结果
  - 验证：加载总数 40、DISABLED 10（7+3）、可见 30；三个暴露位均标记 DISABLED 且 `filePath` 指向真实软链目标
  - Demo：可见清单缩减但直调能力完整

- [x] Task 4: 按范围隔离提交（两笔）
  - 文件：`.agents/skills` 子模块（`td-agents-skills`）
  - 实现：
    - 提交 A（缺陷修复，已完成内容）：`fix: 修复 sh-lark-session-doc BOM 与 frontmatter 缺项，修正规范模板重复文案`
    - 提交 B（本次改造）：`refactor: 暴露位补 disable-model-invocation 并同步创作规范`
    - 本计划文件 `plans-10-*.md` 按仓库强约束单独成第三笔：`docs(plans): 新增暴露位点名机制强化计划`
  - 验证：`git status` 三条提交各自文件范围互不交叉
  - Demo：history 清晰可回溯

## 未决问题与阻塞确认清单

- [x] 跨 Harness 兼容性：已决策保留文案兜底，不做实测
- [x] `sh-agy-skills` 矛盾：本轮搁置
- [x] **提交 C 顺序**：已按 GLOBAL.md「计划落盘须立即独立提交」执行，计划先于实现成笔
