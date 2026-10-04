---
name: book-kerievsky-refactoring-patterns
description: 知识库：《重构与模式》（Refactoring to Patterns，Joshua Kerievsky 著，中文版）。当你需要在重构与设计模式之间架桥——识别代码坏味道并选择模式导向的重构手法（Creation Method/Factory、Strategy/Command/State 替换条件逻辑、Template Method/Composite/Interpreter、Null Object、适配统一接口、聚集操作等）、规划演进式设计、或查询书中概念时使用。私有版权书衍生库，不入公开仓库。
---

# 《重构与模式》知识库

Joshua Kerievsky（Industrial Logic）著。核心命题：**模式不是起点而是终点——通过重构"实现、趋向和去除"模式，而非预先设计模式**。本书是模式导向重构（Refactoring to Patterns）的手法目录 + 演进式设计哲学。

## 使用方式

1. 有具体代码问题 → 查 [cheatsheet.md](cheatsheet.md) 按"坏味道 → 重构手法"速查。
2. 想系统学习某主题 → 读对应 [chapters/](chapters/) 章摘要。
3. 术语不熟 → 查 [glossary.md](glossary.md)。
4. 需要原文细节 → 按 chapters 摘要中标注的主题回到 `_ocr_work` 原文行号区间。

## 章节地图（中文版 11 章）

| 章 | 主题 | 摘要 |
|---|---|---|
| 1 | 本书的写作缘由（过度设计/模式万灵丹/设计不足） | [chapters/ch01-yuanqi.md](chapters/ch01-yuanqi.md) |
| 2 | 重构（何谓重构、循序渐进、设计欠账、复合重构） | [chapters/ch02-refactoring.md](chapters/ch02-refactoring.md) |
| 3 | 模式（实现/趋向/去除模式，模式知识） | [chapters/ch03-patterns.md](chapters/ch03-patterns.md) |
| 4 | 代码坏味（12 种坏味道及重构方向） | [chapters/ch04-code-smells.md](chapters/ch04-code-smells.md) |
| 5 | 模式导向的重构目录（格式、学习顺序） | [chapters/ch05-catalog.md](chapters/ch05-catalog.md) |
| 6 | 创建（Creation Method、Factory 封装） | [chapters/ch06-creation.md](chapters/ch06-creation.md) |
| 7 | 简化（组合方法、Strategy/Command/State/Null Object） | [chapters/ch07-simplification.md](chapters/ch07-simplification.md) |
| 8 | 泛化（Template Method、提取继承层次、Composite、Interpreter） | [chapters/ch08-generalization.md](chapters/ch08-generalization.md) |
| 9 | 保护（类型代码、Singleton、Null Object） | [chapters/ch09-protection.md](chapters/ch09-protection.md) |
| 10 | 聚集操作（Collecting Parameter、Visitor） | [chapters/ch10-accumulation.md](chapters/ch10-accumulation.md) |
| 11 | 实用重构（链构造函数、统一接口、提取参数） | [chapters/ch11-pragmatic.md](chapters/ch11-pragmatic.md) |

## 核心思想速览

- **演进式设计**：用 TDD + 持续重构让设计逐渐浮现；绿条像陀螺仪，红条超过几分钟说明步子太大。
- **设计欠账**（Design Debt，Ward Cunningham）：去除重复、简化代码、澄清意图这三件事欠着不还，利息（滞纳金）按复利累积成大泥球。
- **循序渐进**：小而安全的步骤比大步骤更快达标；多个重构可以复合成大步骤，但必须由测试护栏兜底。
- **模式的三个动作**：实现（realize）、趋向（move towards）、去除（remove）——模式会引入复杂度，不适合时要去掉。
- **模式知识 vs 模式应用**：先掌握模式的代价与收益，再决定是否用。
