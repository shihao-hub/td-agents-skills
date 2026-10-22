---
name: grill-with-docs
description: 结合现有代码仓与文档的深度需求拷问：在审问过程中同步提炼 ADR 与领域术语。
disable-model-invocation: true
---

# Grill With Docs: 带文档演进的仓内深度审问

当在已有代码库中发起复杂功能需求时使用本技能：
1. 先行扫描项目已有的 `CONTEXT.md`、`GLOSSARY.md` 与 `docs/adr/`，建立工程现状上下文；
2. 调度 **[`grilling`](../grilling/SKILL.md)** 核心引擎进行无情审问，针对与现有架构的冲突点、数据流分歧点提出针对性选择题；
3. 审问过程中 settled 的重大决策，实时调度 **[`domain-modeling`](../domain-modeling/SKILL.md)** 沉淀为 ADR 架构决策记录；
4. 审问完成后，引导流转至 **[`to-spec`](../to-spec/SKILL.md)** 生成完整目的地规范。
