# Plan: 子技能统一预置 disable-model-invocation（暴露即生效）

📋 Plan for: "把 `disable-model-invocation: true` 预置进全部 32 个 `sh-user-skills/<name>/README.md`，使 `expose_user_skill.py` 的建链动作自动携带'仅直调'语义；同步修订创作规范与暴露脚本校验。"

## 问题陈述

1. **语义依赖人工补刀**：上一轮改造需在暴露后手工给 3 个真身补 `disable-model-invocation: true`，暴露动作本身不携带来语义，新增子技能容易遗漏（静默参与自动路由）。
2. **收敛目标**：`sh-user-skills` 下所有子技能一律"点名直调"；未暴露者通过 `sh-user-skills/SKILL.md` 路由表分流，暴露者通过 `/skill:<name>` 直调，两者都不参与模型自动路由。
3. **脚本无守护**：`expose_user_skill.py` 只建链、不校验 frontmatter，无法阻止"字段缺失仍被暴露"的无声失败。

## 需求确认（含用户决策）

- **全部加，无例外**：包括原「主动触发类（Auto）例外」的 `sh-backend-design`。用户原话："*全部加，没关系*"。
- **预置而非暴露后补**：字段写在真身 `README.md` 内，暴露后软链使 `SKILL.md` 指向同一文件，字段即时生效。
- **脚本只校验不写文件**：保持 `expose_user_skill.py` 单一职责（仅建链），缺失字段时警告。

## 背景现状

- 32 个子技能中 3 个已含字段（`sh-plan-driven-development`、`sh-spec-driven-development`、`sh-skill-authoring-rules`），29 个待加。
- 文件格式分布：CRLF 23 个、LF 9 个；`sh-agent-handoff` 额外含 `argument-hint`；17 个缺 `version/created/updated`（本轮不处理，避免范围膨胀）。
- 插入点统一取 frontmatter 结束的 `---` 之前，不受字段顺序与块标量 description 影响。
- `sh-user-skills/SKILL.md` 路由表已覆盖全部 32 项，无需改动。

## 任务分解

- [x] Task 1: 批量预置字段（29 个文件）
  - 文件：`sh-user-skills/*/README.md`
  - 实现：脚本按文件原换行符切分，在第二个 `---` 前插入 `disable-model-invocation: true`；已有则跳过（幂等）
  - 验证：重跑扫描脚本，32 项全部 `HAS`；`git diff --stat` 恰为 29 个文件
  - Demo：任一子技能暴露后 `/skill:` 可用且不进自动路由清单

- [x] Task 2: 规范修订 `sh-skill-authoring-rules/README.md`
  - 文件：`sh-user-skills/sh-skill-authoring-rules/README.md`
  - 实现：卷二 §1 增"预置字段 = 暴露即生效"原理；§2 模板加该字段；§4 第 4 条改写为"字段已在真身预置，暴露无需二次改动"；版本 `2.7.0 → 2.8.0`
  - 验证：`rg -n "disable-model-invocation"` 命中点与条款语义一致
  - Demo：新子技能照模板创建即天然合规

- [x] Task 3: 暴露脚本加校验
  - 文件：`expose_user_skill.py`
  - 实现：建链前解析 `src/README.md` frontmatter，缺字段则打印警告（不阻断、不改文件）
  - 验证：临时造一个缺字段的假目录跑 `--check`，确认只警告不失败
  - Demo：新增子技能忘写字段时暴露过程可见提示

- [x] Task 4: 回归验证与提交
  - 文件：无 / 子模块提交
  - 实现：`loadSkillsFromDir` 复核（加载 40 / DISABLED 10 / 可见 30 保持不变，因未暴露者不进注册表）；分两笔提交（改造、脚本+规范可合并为同一语义范围）
  - 验证：工作区干净，`git log` 可回溯
  - Demo：机制与文案双保险在全库统一

## 未决问题与阻塞确认清单

- [x] `sh-backend-design` 是否例外：已决策全部加
- [ ] **17 个缺 `version/created/updated` 的文件**是否顺带补齐？本轮默认不处理（保持提交范围单一），如需补齐建议另起一笔
