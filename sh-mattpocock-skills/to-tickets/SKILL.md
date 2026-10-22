---
name: to-tickets
description: 将规范拆解为穿透全层的垂直切片（Tracer Bullets）与 DAG 看板，声明 blocked by 依赖，确保单切片可在单次干净会话内交付。
disable-model-invocation: true
---

# To Tickets: 垂直切片（曳光弹）与 DAG 看板拆解

> **基本功法则（《程序员修炼之道》曳光弹思维）**：  
> **垂直切片，坚决拒绝水平分层！**  
> AI 的本能是“先把数据库层建好、再建 API 层、最后建前端界面”，这会导致直到最后阶段才有反馈。  
> **第一个 Ticket 就必须穿透所有层（改 schema + 加服务 + 最简界面/可观测入口）**，一次打通端到端，这就是“曳光弹”。

---

## 一、切片核心原则（The 4 Rules of Tracer Bullets）

1. **窄而完整（Narrow but Complete）**：每个切片横切所有层（Schema/存储、核心业务、API、界面/交互契约、测试），切片交付后立即可以独立演示或端到端验证；
2. **上下文隔离尺寸（Sized for One Fresh Context）**：单个 Ticket 的任务范围必须严格限制在**单个干净的会话窗口内即可完成**；
3. **依赖显式化（DAG Blocking Edges）**：每个 Ticket 必须显式声明其依赖的阻断项（`blocked by`）；没有前置依赖的 Ticket 属于当前 Frontier，可立即或并行推进；
4. **重构先行（Prefactor First）**：遇到大改动时遵循“先让修改变得容易，再做容易的修改”（Make the change easy, then make the easy change）。

---

## 二、切片拆解工作流

### 1. 拟定垂直切片清单
从 `to-spec` 产出的规范文档中提取核心用户故事，按曳光弹推进顺序拆解为编号工单：

```markdown
# Ticket NN: <切片标题>

**核心交付 (What it delivers):**
从用户或调用方视角的端到端可验证行为（一句话目标）。

**测试接缝 (The Seam):**
本切片在哪个预先确定的公共接缝处编写测试。

**前置依赖 (Blocked by):**
- Ticket XX（若无可立即开始，标记为 "None"）

**验收条件 (Acceptance Criteria):**
- [ ] 1. 触发 X 条件下，在测试接缝处捕获到正确响应；
- [ ] 2. 界面/终端能感知到该状态变化；
- [ ] 3. 现有老功能完全不受破坏（通过既有测试）。
```

### 2. 向用户请示审查（Quiz the User）
在落盘前向用户展示切片清单，重点请示 3 个问题：
- 粒度是否合适？（单个 Ticket 会不会太大超过一个会话？会不会过细？）
- 阻塞边（`blocked by`）是否准确？是否有可以并行跑的独立 Ticket？
- 第 1 个 Ticket 是否确实穿透了全层构成有效曳光弹？

### 3. 落盘发布
审核通过后，输出至项目任务路径（如 `.scratch/issues/<NN>-<slug>.md` 或项目的任务管理系统中）。

---

## 三、下游关联流转指引（Next Transitions）

切片清单生成并确认后：
- 👉 **挑选当前 Frontier 中无阻塞（Blocked by: None）的第一个切片**；
- 👉 **关键纪律**：**建议新开独立会话或执行 `/clear` 清空历史沉淀**，将该切片交给 **[`implement`](../implement/SKILL.md)**，结合 **[`tdd`](../tdd/SKILL.md)** 开始推进实现；
- ⚠️ **红线警告**：严禁在一个长会话中一口气把全部切片做完！一个切片交付后必须清空上下文再做下一个！
