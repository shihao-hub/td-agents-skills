# 术语表（中英对照）

## 核心概念

| 中文 | 英文 | 释义 |
|---|---|---|
| 模式导向的重构 | Refactoring to Patterns | 通过重构实现、趋向或去除模式的工作方式，本书主题 |
| 演进式设计 | Evolutionary Design | 设计随迭代逐渐浮现，而非预先定型 |
| 设计欠账 | Design Debt | 累积未偿还的设计缺陷；不还会按"复利"产生利息 |
| 大泥球 | Big Ball of Mud | 缺乏内在结构、纠缠一团的系统 |
| 代码坏味 | Code Smell | 指向深层设计问题的表面症状（见第 4 章 12 种） |
| 循序渐进 | Simplicity / small steps | 以小而安全的步骤重构，测试随时保持绿 |
| 复合重构 | Composite Refactoring | 多个底层重构复合成的一个大步骤 |
| 测试驱动的重构 | Test-Driven Refactoring | 在测试护栏下重构 |
| 模式万灵丹 | Pattern Fever / patterns as hammers | 把一切问题都用模式解决的倾向 |
| 模式痴迷 | Pattern Obsession | 过度追求"用了模式"而非解决真实问题 |
| 过度设计 | Overdesign | 不必要的灵活性带来的复杂度 |
| 设计不足 | Underdesign | 缺乏应对真实变化所需的设计 |
| 持续重构 | Continuous Refactoring | 在整个开发过程中不间断地小步重构 |
| 重构工具 | Refactoring Tools | 自动化重构的 IDE 支持（安全网之一） |

## 重构手法关键词

| 中文 | 英文 | 所在章 |
|---|---|---|
| 创建方法 | Creation Method | 6 |
| 工厂 | Factory（Method/类封装） | 6 |
| 组合方法 | Composed Method | 7 |
| 策略 | Strategy | 7 |
| 命令 | Command | 7 |
| 状态 | State | 7 |
| 空对象 | Null Object | 7 |
| 适配器 | Adapter | 7 |
| 模板方法 | Template Method | 8 |
| 组合模式 | Composite | 8 |
| 解释器 | Interpreter | 8 |
| 聚集操作 | Move Accumulation（to Collecting Parameter / to Visitor） | 10 |
| 拆包/嵌入类 | Unwrap / Embed Class | 11 |

## 相关人物/引用

| 名字 | 说明 |
|---|---|
| Ward Cunningham | 提出设计欠账隐喻 |
| Martin Fowler | 《重构》[F] 作者，本书手法与其一脉相承 |
| Gang of Four (GoF) | 《设计模式》四作者，本书大量引用其 23 个模式 |
| Kent Beck | TDD 与 Smalltalk 最佳实践来源 |
