---
name: sh-oop-refactor
description: 运用 OOP 思想与设计模式重构项目：代码坏味道诊断、接缝测试、架构方案到小步执行。点名使用
version: 1.0.0
created: 2026-10-03
updated: 2026-10-03
---

# OOP 重构最佳落地工作流（SOP）

本 Skill 提供将遗留项目或过程式代码重构为高内聚、低耦合、面向对象与设计模式架构的标准化落地流程。

## 核心原则

1. **组合优于继承（Composition over Inheritance）**：优先使用接口、委托与策略注入，严禁深层类继承。
2. **拒绝过度设计（KISS & YAGNI）**：重构是为了应对实际变化点，严禁脱离真实业务诉求凭空捏造无意义的抽象层。
3. **无测试不重构**：严禁在没有任何行为保护网的情况下直接修改业务逻辑。
4. **小步安全演进**：严禁一次性重写整个项目，必须拆解为可独立运行、随时可验证的微步骤。
## 阶段零：前置环境与依赖 Skills 检查

本工作流依赖两类支持：**开源生态 Skills** 与 **本地核心工作流 Skills**。在进入诊断前，必须首先检查环境可用性：

### 1. 本地内置工作流判定（绑定）
- **sh-plan-driven-development**：用于实施方案的单文件落盘与强制关卡把关。
- **环境检查**：检查本地是否存在 ~/.agents/skills/sh-plan-driven-development。
  - 若已存在：方案设计阶段自动采用该规范。
  - 若处于全新机器或该 skill 不存在：回退到本 SOP 内置的 plans/{NN}-{name}.md 简易落盘模板与硬性审批门。

### 2. 社区开源 Skills 检查与安装确认
工作流推荐配合以下 3 个开源 Skills（提升诊断精度与模式参考）：
- clean-code（sickn33/agentic-awesome-skills@clean-code）：坏味道识别与 Uncle Bob 整洁标准。
- improve-codebase-architecture（mattpocock/skills@improve-codebase-architecture）：深模块与接缝设计。
- python-design-patterns / architecture-patterns（wshobson/agents）：架构与经典设计模式选型。

**缺项确认机制**：
若检测到当前环境缺少上述任一开源 skill，**必须主动向用户展示说明并确认是否安装**：
`
检测到当前环境未安装辅助 Skill:
- clean-code: 代码坏味道诊断与单一职责规范
- improve-codebase-architecture: 深模块与接口接缝设计
- architecture-patterns / python-design-patterns: 架构与经典设计模式参考

是否通过 npx skills 自动为您安装这些辅助技能？
a. 全部安装 (推荐)
b. 仅使用内置 SOP 执行，跳过安装
c. 自由回答
`
用户同意后，运行安装命令：
`ash
npx skills add sickn33/agentic-awesome-skills@clean-code -g -y
npx skills add mattpocock/skills@improve-codebase-architecture -g -y
npx skills add wshobson/agents@architecture-patterns -g -y
`

---

## 阶段一：坏味道诊断与领域边界梳理（Diagnosis & Modeling）

在不动任何业务代码的前提下，进行静态分析与领域映射：

1. **识别典型代码坏味道**：
   - **God Class / God Function**：单文件/函数超长、混杂大量无关业务与底层 IO 操作。
   - **数据与行为分离（贫血模型）**：一堆无方法的数据载体配合漫天飞舞的工具类（Util/Helper）。
   - **硬编码分流**：随处可见的 if-else / switch 判断类型并执行不同分支逻辑。
   - **深层参数穿透**：底层方法需要的参数层层透传 4~5 层函数调用。
2. **提取领域对象（Entities & Value Objects）**：
   - 梳理业务中的核心名词，将散落在函数间的原始数据（Primitive Obsession）打包为带验证与行为的高内聚对象。
3. **输出诊断清单**：
   - 列出本次重构涉及的模块边界、高危坏味道点及预期的接口边界。

---

## 阶段二：建立行为保护网（Test Seams）

重构必须保证外部可见行为等价：

1. **梳理基线用例**：
   - 找出待重构模块的公开 API 或关键入口函数。
2. **补充端到端/黑盒特征测试（Characterization Tests）**：
   - 在不修改内部代码的情况下，编写覆盖典型输入与边界情况的集成测试。
   - 运行并确保全部测试通过（Green），记录此时的基准输出。
3. **设置自动化验证指令**：
   - 确立项目标准的测试运行命令（如 pytest、npm test、cargo test）。后续每个小步提交都必须能通过该测试。

---

## 阶段三：设计模式方案权衡与实施计划落盘（Plan & Design）

基于“组合优于继承”与“开闭原则（OCP）”制定重构设计，并严格执行落盘与审批门：

1. **设计模式选型决策**：
   - 分支判断消除 -> **策略模式（Strategy）** 或查找表映射。
   - 复杂对象构造解耦 -> **建造者（Builder）** 或 **工厂模式（Factory）**。
   - 跨系统适配与第三方解耦 -> **适配器模式（Adapter / Ports & Adapters）**。
   - 行为监听与解耦 -> **观察者模式（Observer）** 或发布订阅。
2. **架构类图绘制**：
   - 使用 Mermaid 类图明确类之间的职责关系、接口定义与依赖注入方向。
3. **实施计划落盘与审批门**：
   - 按 plans/{NN}-refactor-{target}.md 格式落盘实施计划（参见 references/refactor-plan-template.md）。
   - 将重构拆解为多个顺序依赖的 Task（例如：1.引入接口抽象 -> 2.封装第一个策略类 -> 3.替换调用方 -> 4.移除旧分支）。
   - **硬性关卡**：落盘后停止并向用户汇报，获得用户明确批准（例如“同意/执行”）后，方可进入实施阶段。

---

## 阶段四：小步递进重构与对抗审查（Execution & Review）

严格按照获批的任务列表递进执行：

1. **微步实施规范（Tiny Steps）**：
   - 每个 Task 仅完成一处结构调整，保持老代码与新代码在过渡期双轨共存（Parallel Run / Branch by Abstraction）。
   - 每完成一个 Task，立即运行测试网验证：保持系统始终处于可构建且测试全绿状态。
   - 勾选任务清单 [x] 并记录遇到的实际偏差。
2. **对抗性审查（Adversarial Self-Review）**：
   - 在全部改造完成前，以批判视角检查：
     - 是否存在**过度设计**？（例如只有一种业务场景却写了一整套抽象工厂）
     - 是否存在**伪面向对象**？（仅仅是将过程式函数塞进一个 Class，依然全局共享静态状态）
     - 是否破坏了迪米特法则？（调用链路是否存在连续方法穿透 a.b.c.doSomething()）
3. **交付总结**：
   - 汇报重构前后架构对比（代码行数、圈复杂度、扩展新类型的代价）。
   - 输出更新后的测试报告与使用范例。
