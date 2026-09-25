---
name: sh-agy-plan
description: antigravity 的 /plan 慎密规划模式：先出实施计划获批再动代码。速查表：需求明确但改动多，先出计划确认再动手。点名使用
version: 1.1.0
created: 2026-09-25
updated: 2026-09-25
---

# sh-agy-plan：慎密规划模式（先谋后动）

> 版本 v1.1.0 ｜ 移植自 Google Antigravity 斜杠命令 /plan，<PLAN> 提示词提取自 language_server.exe（2026-09-23 构建）

## 功能介绍

Antigravity 的 /plan：官方释义 "Plan carefully before executing a task."。先规划审阅、后动手写代码，防止 agent 没吃透上下文就盲改项目。原版工作流：只读研究 → 产出实施计划 artifact → 用户批准 → 才允许改代码 → 验证 → 产出 walkthrough 总结。

适用：中大型功能开发、多文件修改、核心架构重构、对变更有高审查要求的任务。

## 执行协议

### 1. 对齐理解

- 有歧义、需求欠明确、隐含假设 → 先向用户澄清。
- 彻底研究代码库：相关组件、系统、依赖、架构；**研究过程中向用户实时同步步骤与思路**。

### 2. 产出实施计划

写入 `plans/{NN}-{plan_name}.md`，告知用户路径；**不要在对话里复述全文**。落盘规则与 sh-plan-driven-development 共用同一 `plans/` 目录与全局序列：

- 平铺不建子目录；`{plan_name}` 英文小写连字符，中文需求由你拟短词
- 取号：扫 `plans/` 下 `^\d+-` 文件名取最大 +1，空则 `01`；零填充；同号顺延；取号发生在落盘那一刻；无数字前缀的旧文件忽略
- 落位三步判定：已声明"文字归 docs/"→ `docs/plans/`；已有 docs/ 判语义（文档中心→`docs/plans/`，参考库→根 `plans/`）；判不清问用户
- 用户指定计划文件名/位置时以其为准

计划正文格式（无关段落可省，忠实原版）：

```markdown
## 目标描述
问题简述、背景上下文、本次变更达成什么。

## 需要用户审阅
破坏性变更、重大设计决策；用 > [!IMPORTANT] / > [!WARNING] / > [!CAUTION] 突出。

## 待澄清问题
影响实现方案的澄清/设计问题；同样用 alert 突出。

## 变更方案
按组件分组（package/功能域/依赖层），依赖在前，组件间用水平线分隔。
### [组件名]
变更摘要 + 明确代码片段和 diff。文件用 #### [MODIFY]/[NEW]/[DELETE] 文件名 标记。

## 验证方案
### 自动化测试
可运行的精确命令。
### 人工验证
用户需手动确认的事项。
```

### 3. 等待批准

用户明确批准前，不改任何代码、不跑任何有副作用的命令（写 plans/ 下文件除外）。

### 4. 执行与验证

按计划实施；完成后跑单测/构建等验证，验证不过不许宣称完成。

### 5. 产出 Walkthrough

验证通过后写 `plans/walkthrough-{NN}-{plan_name}.md`（复用计划的编号 NN，不占新号；`walkthrough-` 前缀非数字开头，不参与序列扫描）：做了什么变更 / 测了什么 / 验证结果；UI 变更嵌入截图。相关后续工作更新已有 walkthrough 而不是新建。

## 与原版的差异

- 原版 artifact 带 request_feedback 元数据自动推送用户审阅；本版改为落盘 plans/ 并告知路径，命名与编号对齐 sh-plan-driven-development 的全局序列（共用目录、共用取号）。
- 与 sh-claude-plan-mode / sh-plan-driven-development 精神一致；本 skill 忠实复刻 antigravity 原版格式（GitHub alert、组件分组、walkthrough）。
