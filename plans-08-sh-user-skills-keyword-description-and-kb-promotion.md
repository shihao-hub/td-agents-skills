# Plan: sh-user-skills 描述关键词化扩容与知识库提级暴露

📋 Plan for: "把 sh-user-skills 的 description 扩容为关键词集群形态（知识库第一优先 + 症状词钩子，≤1024），把 sh-engineering-notes 提级暴露到根级以获得独立常驻描述，并在 SKILL-AUTHORING-RULES.md 固化『路由器关键词集群』规范与点名模板豁免。"

## 问题陈述

1. **知识库钩子薄弱**：`kb-engineering-notes/`（49 篇）与 `sh-engineering-notes` 均不被 harness 注册，整库在全局 prompt 中的唯一常驻钩子 = `sh-user-skills` 的 description。当前 description 实测仅 501/1024 字符，首句自我定位偏窄（"模糊需求/忘记技能名"），不含症状词；用户直接报症状（如"喇叭爆音"）时缺乏触发引导。
2. **正文钩子停更**：口语速查表知识库行关键词停更在早期条目，后续沉淀（PowerShell7 绿色部署、字体渲染、右键菜单、WT 分屏、迅雷插件等）缺席；`sh-engineering-notes/README.md` 覆盖分类仍使用编号区间（`01~03, 06, 27`），违反卷三"外部解耦、禁写编号区间"原则。
3. **结构矛盾**：知识库持续生长 → 父级路由器钩子必然过期；关键词维护权应随知识库自身走。
4. **规范缺口**：卷一要求 description"≤70 字符一句话 + 结尾点名使用"，而路由器实际采用"关键词集群 + 点名兜底"形态，属未写入规范的既成事实，易被后续"压缩优化"反复破坏。

## 需求（含用户决策）

- 描述扩容改造（关键词集群、知识库第一优先、≤1024）：用户确认（"描述也要改造，知识库地位需要提升……不超过 1024 就够了"）；
- 提级暴露 `sh-engineering-notes` 到根级（与 plan/spec-driven 同款机制）：用户确认"这个不错"；
- 规范固化：关键词集群合法形态 + 点名模板豁免 + 暴露位登记：用户确认"这个不错"。

## 方案

1. `sh-user-skills/sh-engineering-notes/README.md`：description 关键词化（症状词/工具词集群 + 触发说明，≤1024）；覆盖分类去编号区间、补全近期领域；版本升 1.1.0。
2. `uv run expose_user_skill.py sh-engineering-notes`：生成根级暴露位（`.gitkeep`/`.gitignore` 入库，链接产物不入库），使知识库拥有自己的常驻 description，关键词维护权随知识库走。
3. `sh-user-skills/SKILL.md`：description 扩容为"定位 + 知识库第一优先关键词集群 + 四域 + 族路由器 + 点名兜底"；正文新增「知识库优先原则」专区，更新速查表知识库行与导航区；版本升 1.2.0。
4. `SKILL-AUTHORING-RULES.md`：卷一新小节「路由器与知识库入口例外（关键词集群形态）」；〇节登记表增补"提级暴露位"行；卷二增补提级暴露机制说明；附录清单增补对应检查项；版本升 2.1.0。

## 任务分解

- [x] Task 1: 改造 `sh-user-skills/sh-engineering-notes/README.md`（描述关键词化 + 去编号区间）
- [x] Task 2: 暴露 `sh-engineering-notes` 到根级并验证链接可用
- [x] Task 3: 改造 `sh-user-skills/SKILL.md`（描述扩容 + 知识库优先正文）
- [x] Task 4: 修订 `SKILL-AUTHORING-RULES.md`（关键词集群规范 + 点名豁免 + 暴露位登记）
- [x] Task 5: 全量校验（`description ≤1024`、无编号区间、链接有效）
- [x] Task 6: 拟定分范围提交命令（已拟定，待用户确认执行）

## 实施说明（2026-10-11）

- **描述实测**：`sh-user-skills/SKILL.md` 501 → **789 字符**（≤1024 通过）；`sh-engineering-notes/README.md` **390 字符**（提级后进入全局清单）；`SKILL-AUTHORING-RULES.md` 2.0.0 → 2.1.0。
- **提级暴露**：`uv run expose_user_skill.py sh-engineering-notes` 生成根级 `sh-engineering-notes/SKILL.md`（SymbolicLink → 真身 README.md，改真身即生效）；`.gitkeep`/`.gitignore` 占位入库；`--check` 复验 0 动作 / 3 跳过，链接完好。
- **正文强化**：新增「知识库优先原则（最高优先级）」callout；交互协议知识库条目升级为"最高优先 + 可点名直达"；口语速查表知识库行补齐近期条目症状词；导航区更名为「第一优先」。
- **规范固化**：卷一新增「路由器与知识库入口例外（关键词集群形态）」（显式豁免 ≤70 字符 + 点名使用模板，同时守住反军备竞赛与外部解耦红线）；〇节登记表新增「提级暴露位」行；卷二新增「提级暴露机制（expose_user_skill）」；附录清单同步更新。
- **校验结果**：三份 description 字符数实测（789 / 390 / 301）；三文件 CRLF 行尾保真、无 BOM；去编号区间检查通过（规则文件自身引用示例的命中共视为预期）；根级符号链接内容复读无误。
- **未做（另案）**：plans-07 勾选状态收尾；KB 预存量改动（44 修改、49 未跟踪，属其他会话范畴）未触碰。

---
**最后更新：** 2026-10-11
**作者：** AI & User
**版本：** v1
