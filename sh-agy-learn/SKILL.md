---
name: sh-agy-learn
description: antigravity 的 /learn 经验沉淀：把纠正与成功经验固化为 rule/skill 提案。速查表：刚踩坑排错完毕不想以后再犯。点名使用
version: 1.0.0
---

# sh-agy-learn：经验总结与沉淀

> 版本 v1.0.0 ｜ 移植自 Google Antigravity 斜杠命令 /learn，<LEARN> 提示词提取自 language_server.exe（2026-09-23 构建）

## 功能介绍

Antigravity 的 /learn：官方释义 "Reflect on recent successes or corrections to capture reusable skills or rules."。把单次经验固化为可持续复用的资产：反思会话中的曲折、踩坑排错、用户正向纠偏或成功经验，提取为规则（Rules）或技能（Skills）保存。

适用：刚解决棘手的配置/环境报错，希望"永远记住这个经验"；纠正了 agent 的编码偏好，想沉淀为通用准则。

## 执行协议（原版提示词全文适配）

把近期交互中的可复用行为（纠正、约束、成功经验）持久化；先与用户交互澄清要保留什么，再动手。

### 1. 识别要学什么

1. **分析用户消息**：优先找显式纠正、约束、否决、指示（"不"、"换成"、"那个失败了"）。
2. **定位关键修复**：对比失败尝试与最终成功解法，隔离出起决定性的一步。
3. **根因与范围**：解决底层问题而非表面症状；判断是通用规律还是特定领域。
4. **验证是否需要学习**：本次交互没有暴露新的可复用行为/约束时，向用户说明并退出，不提任何变更。

### 2. 分类：Rule 还是 Skill

- **Rule（规则）**：普适行为护栏、硬性约束、格式不变量 → 写入项目 `AGENTS.md`。
- **Skill（技能）**：可操作的多步工具链、复杂 flag 组合、速查手册 → 新建/更新 `~/.agents/skills/<name>/SKILL.md`。

### 3. 更新优先，创建从严

- **优先更新已有**：某 Rule/Skill 被用过但失败、过时、漏边界、与成功做法脱节 → 更新它。
- **只在全新领域**才创建新的。

### 4. 强制提案流程（红线：不得立即改配置文件）

1. 盘点现有 skills/rules，找候选更新对象。
2. 生成 `learning_proposal.md`（工作目录）：分类、理由、精确的文本增改（diff 形式）。
3. 请用户审阅提案。
4. **用户明确批准后**才执行文件修改。

## 与原版的差异

- 原版写 Antigravity 自家的 skills/rules 配置；本版写入 `~/.agents/skills` 与 AGENTS.md 体系，提案流程不变。
