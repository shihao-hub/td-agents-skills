---
name: grill-me
description: 无状态需求拷问入口：启动无情审问流程，通过单问单选与推荐答案快速对齐设计概念。
disable-model-invocation: true
---

# Grill Me: 需求拷问访谈（用户入口）

本技能是 Matt Pocock 需求审问流程的快捷用户入口。

## 执行说明
无需复杂的初始化，直接载入并执行 **[`grilling`](../grilling/SKILL.md)** 核心引擎：
1. 分析用户当前提出的想法或需求；
2. 建立初步设计树，计算第一批 Frontier；
3. 以单问模式抛出第 1 题（包含选项与推荐答案）；
4. 逼出共识后，产出《设计概念共识书》，并引导流转至 **[`domain-modeling`](../domain-modeling/SKILL.md)** 或 **[`to-spec`](../to-spec/SKILL.md)**。
