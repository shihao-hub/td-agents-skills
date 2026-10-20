---
id: "080"
domain: "agent"
scope: "skills"
type: "fix"
slug: "过度disable致Agent规范失盲与时序元数据防腐治理"
status: "verified"
created: "2026-10-20"
last_verified: "2026-10-20"
superseded_by: null
deprecation_reason: null
compatibility:
  os: ["windows", "linux", "darwin"]
  tools:
    agent_framework: ["antigravity", "opencode", "claude-code", "codex"]
falsification_signals:
  - "若技能属于一次性极低频纯手动排障脚本且无需被自然语言意图感知，可保留点名直调"
  - "若平台不支持 frontmatter 解析，本状态机机制降级为纯文本兜底"
invocation:
  auto_trigger: true
  trigger_keywords: ["disable-model-invocation", "规范失盲", "知识库过时", "元数据", "Kiro Spec"]
---

# 080-过度disable致Agent规范失盲与时序元数据防腐治理

## 一、核心痛点与事故复盘

在 Agent 技能与知识库生态演进中，曾存在一种过度防御性设计假设：
> *“为了防止大模型在日常闲聊中误触技能，或防止暴露位与分流器（`sh-user-skills`）竞争自动路由，将提级暴露的子技能统一预置 `disable-model-invocation: true`，强制要求用户必须手动输入 `/skill:<name>` 点名唤起。”*

### 致命后果（2026-10-20 踩坑实证）
1. **语义断层与物理级失盲**：当用户在自然语言交互中提出 *“...按 kiro quick spec 开发”* 时，底层 harness 识别到 `disable-model-invocation: true`，直接将 `sh-spec-driven-development` 从模型的可用技能列表中剥离。
2. **规范彻底失效，野生自由发挥**：AI 在看不到该规范的情况下，仅凭通用公网模糊记忆，将原本刚性约束为三件套（`requirements.md` / `design.md` / `tasks.md`）且必须落盘在 `docs/specs/{NN}-{feature}/` 的规格流程，篡改为了在代码根目录下随手生成一个单一的 `SPEC.md`，导致工程交付基线被严重破坏。
3. **“提级暴露”与“彻底隐藏”逻辑自相矛盾**：既然一个技能重要到需要提级至全局根目录，却反手剥夺 AI 感知它的权利，彻底架空了提级的价值。

---

## 二、架构根因分析

| 维度 | 错误认知（过度防御） | 正确认知（实战导向） |
| :--- | :--- | :--- |
| **可见性** | 认为 AI 见到技能就会乱调，必须关进小黑屋 | 核心规约、交付工作流与架构设计技能**必须对模型可见**，充当工程交付的安全护栏。 |
| **Token 预算** | 担忧提级技能的 description 膨胀导致 Context 爆炸 | 核心规范技能的 description 均在 100~200 字符内，消耗 token 极小，收益与成本完全不成比例。 |
| **触发机制** | 强行要求用户每次都如机器般键入 `/skill:...` | 依靠精准的语义关键词集群（如 `kiro`、`spec`、`plan`、`规格驱动`）由 AI 在自然对话中精准唤醒。 |

---

## 三、知识库防腐与时序元数据标准契约

为解决“知识库随着时间推移出现过时、错误、僵化误导”的问题，参考业界成熟体系（Zep 双时间图谱、Mem0 衰减遗忘机制），所有知识库条目文件头统一引入**时序防腐元数据契约（YAML Frontmatter）**：

```yaml
---
# 基础定位
id: "080"
domain: "agent"
scope: "skills"
type: "fix"                        # [fix 故障修复 | flow 方案流程 | rule 硬性规约]
slug: "过度disable致Agent规范失盲与时序元数据防腐治理"

# 状态机：解决过时与错误的核心！
status: "verified"                 # [verified 已验证 | draft 草案 | suspect 存疑 | deprecated 已废弃]
created: "2026-10-20"
last_verified: "2026-10-20"        # 最后一次实机验证通过时间
superseded_by: null                # 若废弃，指向替代者的 ID（如 "095"）
deprecation_reason: null           # 废弃原因说明

# 可证伪信号：告诉 AI 什么时候果断放弃/停止盲从本知识！
falsification_signals:
  - "出现现场报错与知识库现象不一致时，优先以现场命令输出为准，不得强行套用"

# 触发意图声明
invocation:
  auto_trigger: true
  trigger_keywords: ["disable-model-invocation", "规范失盲", "知识库自愈"]
---
```

### 状态流转规则：
1. **时序软失效（不删物理文件）**：
   - 当某条经验或规约被证明过时或有害时，严禁物理删除文件（删除会导致历史信息蒸发，后人容易重蹈覆辙）。
   - 将其置为 `status: "deprecated"`，并标注 `superseded_by` 与 `deprecation_reason`。AI 检索到该条目时，会将其视为**负向反思教训（Negative Constraints）**进行避坑提示。
2. **遇坑即修（谁碰壁，谁修路）**：
   - 现场排障若推翻了知识库既有断言，必须顺手更新该条目的 `status` 为 `suspect` 或更新文档内容并刷新 `last_verified`。

---

## 四、落地实施 SOP

1. **松绑提级暴露位**：
   检查并彻底移除 `sh-spec-driven-development`、`sh-plan-driven-development`、`sh-skill-authoring-rules` 中的 `disable-model-invocation: true`。
2. **触发词强化**：
   在 description 中增加实战别名（例如 `kiro`、`quick spec`、`plan`、`规格驱动`），确保自然语言直接唤醒。
3. **入库索引回填**：
   同步在 `kb-engineering-notes/SKILL.md` 路由表中注册条目 `080`。