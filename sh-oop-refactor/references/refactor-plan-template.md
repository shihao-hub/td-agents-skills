# Refactor Plan: [Refactor Target Name]

## 1. 坏味道诊断与问题背景 (Problem & Smells)
- **待重构模块/文件**：path/to/legacy_module.py
- **主要坏味道**：God Function、大面积 switch 分支、全局状态依赖
- **预期重构目标**：按单一职责原则解耦，引入策略模式与依赖注入，保持可测性。

## 2. 领域建模与设计方案 (Design & Patterns)
- **设计模式选型**：Strategy Pattern + Factory Method
- **接口与类职责**：
  - IHandler：统一行为接口
  - ConcreteStrategyA / B：拆分出来的独立策略
  - HandlerFactory：工厂根据配置或输入参数分发策略

``mermaid
classDiagram
    class IHandler {
        <<interface>>
        +execute(context)
    }
    class ConcreteStrategyA {
        +execute(context)
    }
    class ConcreteStrategyB {
        +execute(context)
    }
    IHandler <|.. ConcreteStrategyA
    IHandler <|.. ConcreteStrategyB
``

## 3. 行为保护网与验证方式 (Test Seams)
- **测试命令**：pytest tests/test_legacy.py
- **基线用例**：5 个典型输入 scenario，测试全部处于通过状态。

## 4. 任务清单 (Tasks)
- [ ] Task 1: 声明新接口与数据结构
  - 文件：src/interfaces/handler.py
  - 验证：运行单元测试确认接口定义语法正确
  - Demo：能够正常导入新接口
- [ ] Task 2: 提炼第一个策略类并实现接口
  - 文件：src/strategies/strategy_a.py
  - 验证：针对 strategy_a 运行新增单测
  - Demo：单独调用 strategy_a 成功产出结果
- [ ] Task 3: 改造老入口，接入策略分发（双轨并存）
  - 文件：src/entrypoint.py
  - 验证：运行全量回归测试
  - Demo：老入口能够正确走通 strategy_a 分支
- [ ] Task 4: 迁移剩余分支并清理废弃老代码
  - 文件：src/entrypoint.py
  - 验证：运行全量回归测试，全部通过
  - Demo：老入口内已无历史冗余分支代码
