---
name: code-review
description: 干净上下文下的双轴代码审查：由两个独立子代理并行审计 Standards 规范轴与 Spec 需求轴，杜绝自审盲区，为人工品味注入把关。
disable-model-invocation: true
---

# Code Review: 干净上下文下的双轴代码审查

> **审查法则（Matt Pocock Sand Castle 体系）**：  
> **审查必须在清空的独立会话中进行，绝不能让刚写完代码的那个会话自己审自己！**  
> 在清空的上下文里，Reviewer 处于完整的智慧区；双轴独立并行子代理（Standards 轴与 Spec 轴）避免相互掩盖。  
> **人工 QA 是你把“品味”注入代码的唯一窗口**：AI 审查通过后，人类开发者必须亲自跑一遍。

---

## 一、双轴核心模型

审查从目标分支基准点（如 `HEAD~1` 或 `main`）到 `HEAD` 的 diff，拆分为两个正交维度：

- **Standards 规范轴**：代码是否符合仓库现有工程规范？是否存在 Fowler 代码坏味道？
- **Spec 需求轴**：代码是否忠实实现了原始 issue/spec 的要求？是否存在漏项或范围蔓延（Scope Creep）？

两者由**两个独立的并行子代理（Parallel Sub-agents）**分别审查，互不污染。

---

## 二、执行流程

### 1. 确定比对基准点（Fixed Point）
确定比较的基准 commit（默认 `HEAD~1`，或用户传入的 commit SHA / 分支名）。
执行验证：`git diff <fixed-point>...HEAD`，确认 diff 存在且非空。

### 2. 定位原始规范来源（Originating Spec）
按以下顺序寻找对应的规范来源：
1. 提交信息中的 Issue 编号（如 `#12`、`Ticket-03`）；
2. 用户传入的 spec 路径；
3. `.scratch/specs/`、`.scratch/issues/` 或 `docs/specs/` 中匹配的规范文档。

### 3. Standards 坏味道基准（Fowler Smells Baseline）
除仓库既有规范文件外，并行 sub-agent 必须严格审查以下坏味道：
- **Mysterious Name**（命名晦涩）；
- **Duplicated Code**（代码重复）；
- **Feature Envy**（依恋情结：方法过度伸手访问其他对象数据）；
- **Data Clumps**（数据泥团：多处传递相同的几个零散字段）；
- **Primitive Obsession**（基本类型偏执：应包装为领域类型）；
- **Shotgun Surgery**（散弹式修改：一次逻辑变更触发零碎的多处改动）；
- **Speculative Generality**（夸夸其谈未来性：添加了 spec 未要求的臆想抽象）。

### 4. 派生独立并行子代理
- **Sub-agent A (Standards)**：聚焦规范违背与坏味道，以 `<file:line>: [Smell Name] 诊断与改进建议` 形式汇报（400 字以内）；
- **Sub-agent B (Spec)**：比对变更 diff 与原始 spec，逐条比对漏实现项、超范围蔓延项与实现错误项（400 字以内）。

### 5. 聚合呈现（不可合并评级）
分别以 `## 规范轴 (Standards)` 与 `## 需求轴 (Spec)` 独立呈现，严禁合并加权折衷，确保任何单轴瑕疵都不被掩盖。

---

## 三、人工品味注入门禁（Human Taste QA Gate）

审查报告给出后，发出人工验收提醒：
```markdown
🔎 双轴代码审查已完成。

⚠️ 【人工 QA 门禁】：
你亲手点一遍/跑一遍是必须的，跳过就等于放弃了品味注入！
请在本地验证端到端体验无误后，再推进下一步。
```

---

## 四、下游关联流转指引（Next Transitions）

- 👉 **验收通过且无硬伤**：返回 **[`to-tickets`](../to-tickets/SKILL.md)** 看板勾选该工单，清空会话推进下一个切片；
- 👉 **若在 QA 或测试中发现隐蔽 Bug / 性能衰退**：  
  调用 **[`diagnosing-bugs`](../diagnosing-bugs/SKILL.md)**，第一要务是建立 2 秒红灯紧反馈闭环；
- 👉 **若审查发现多处浅模块散落或架构摩擦**：  
  记录为重构需求，后续调用 **[`improve-codebase-architecture`](../improve-codebase-architecture/SKILL.md)** 进行深模块深化。
