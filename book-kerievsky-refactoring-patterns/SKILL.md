---
name: book-kerievsky-refactoring-patterns
description: 知识库：《重构与模式》（Refactoring to Patterns，Joshua Kerievsky 著，中文版）。当你需要在重构与设计模式之间架桥——识别代码坏味道并选择模式导向的重构手法（Creation Method/Factory、Strategy/Command/State 替换条件逻辑、Template Method/Composite/Interpreter、Null Object、适配统一接口、聚集操作等）、规划演进式设计、或查询书中概念时使用。私有版权书衍生库，不入公开仓库。
---

# 《重构与模式》知识库

Joshua Kerievsky（Industrial Logic）著。核心命题：**模式不是起点而是终点——通过重构“实现、趋向和去除”模式，而非预先设计模式**。本书是模式导向重构（Refactoring to Patterns）的手法目录 + 演进式设计哲学。

## 使用方式

1. **查坏味道对应手法** → 查 [cheatsheet.md](cheatsheet.md) 速查表（坏味道 ➔ 推荐重构手法）。
2. **重构手法决策与权衡** → 读 [patterns.md](patterns.md) 掌握 27 种手法的适用时机、具体步骤与权衡（When to use / How / Trade-offs）。
3. **系统精读或按章检索** → 读对应 [chapters/](chapters/) 章节精要。
4. **专业术语查证** → 查 [glossary.md](glossary.md)。

## 章节地图（中文版 11 章）

| 章 | 主题 | 摘要 |
|---|---|---|
| 1 | 本书的写作缘由（过度设计/模式万灵丹/设计不足） | [chapters/ch01-yuanqi.md](chapters/ch01-yuanqi.md) |
| 2 | 重构（何谓重构、循序渐进、设计欠账、复合重构） | [chapters/ch02-refactoring.md](chapters/ch02-refactoring.md) |
| 3 | 模式（实现/趋向/去除模式，模式知识） | [chapters/ch03-patterns.md](chapters/ch03-patterns.md) |
| 4 | 代码坏味（12 种坏味道及重构方向） | [chapters/ch04-code-smells.md](chapters/ch04-code-smells.md) |
| 5 | 模式导向的重构目录（格式、学习顺序） | [chapters/ch05-catalog.md](chapters/ch05-catalog.md) |
| 6 | 创建（Creation Method、Factory 封装、Builder） | [chapters/ch06-creation.md](chapters/ch06-creation.md) |
| 7 | 简化（组合方法、Strategy/Decorator/State/Command） | [chapters/ch07-simplification.md](chapters/ch07-simplification.md) |
| 8 | 泛化（Template Method、Composite、Observer、Adapter、Interpreter） | [chapters/ch08-generalization.md](chapters/ch08-generalization.md) |
| 9 | 保护（类型代码、Singleton 限制、Null Object） | [chapters/ch09-protection.md](chapters/ch09-protection.md) |
| 10 | 聚集操作（Collecting Parameter、Visitor） | [chapters/ch10-accumulation.md](chapters/ch10-accumulation.md) |
| 11 | 实用重构（链构造函数、统一接口、提取参数） | [chapters/ch11-pragmatic.md](chapters/ch11-pragmatic.md) |

## 核心心智模型与设计哲学（Core Frameworks）

- **演进式设计（Evolutionary Design）**：
  设计不是先验神启，而是随测试驱动（TDD）和小步重构自然浮现的过程。持续倾听代码坏味道，以绿条为陀螺仪保持代码健康。
- **模式的三个动作（Realize, Move Towards, Remove）**：
  - *实现模式*：当确凿需要模式的多态灵活性时，通过重构引入模式；
  - *趋向模式*：仅实现模式的核心骨架或接缝，不盲目追求完整模式复杂度；
  - *去除模式*：当模式带来的维护复杂度超过其实际收益时，果断重构抹除模式，回归简单设计。
- **设计欠账（Design Debt）**：
  Ward Cunningham 提出。未能及时清除重复、简化代码和澄清意图，相当于借取设计债务。利息以复合形式在后续每一次变更中惩罚团队。
- **重构安全网（Refactoring Safety Net）**：
  一切重构的前提是严密的单元测试。大重构必须分解为可独立编译、测试通过的微小安全步骤（Atomic Steps）。
- **拒绝过度设计与模式狂热（Pattern Fever）**：
  设计模式是优秀实践的结晶，绝非处处套用的“万灵丹”。最优秀的架构往往由简单的类和方法构成，只在真正需要变化和解耦的地方引入模式。
