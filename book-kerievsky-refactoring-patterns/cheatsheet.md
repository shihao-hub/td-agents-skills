# 坏味道 → 模式导向重构 速查表

先定位坏味道（第 4 章 12 种），再选重构手法。所有手法执行前确保测试绿、小步走。

## 12 种代码坏味道 → 处置方向

| 坏味道（中/英） | 典型信号 | 优先考虑的重构手法 |
|---|---|---|
| 重复代码 Duplicated Code | 相同逻辑多处出现 | Form Template Method（8）、Extract Superclass、Move Accumulation（10） |
| 过长方法 Long Method | 一屏放不下、注释当分节符 | Composed Method（7）、Extract Method |
| 条件逻辑太复杂 Conditional Complexity | 嵌套 if/switch 难懂 | Replace Conditional Logic with Strategy/Command/State（7） |
| 基本类型偏执 Primitive Obsession | 用 string/int 表达领域概念 | Extract Class、Replace Data Value with Object |
| 不恰当的暴露 Indecent Exposure | 内部实现泄漏到接口 | Encapsulate Classes with Factory（6）、信息隐藏 |
| 解决方案蔓延 Solution Sprawl | 一个改动要碰很多类 | Move Method/Field、聚合相关职责 |
| 异曲同工的类 Alternative Classes with Different Interfaces | 两个类做同一件事但接口不同 | Unify Interfaces with Adapter（8.5） |
| 冗赘类 Lazy Class | 类几乎不干活 | Inline Class、Collapse Hierarchy |
| 过大的类 Large Class | 职责过多、字段成堆 | Extract Class、拆分职责 |
| 分支语句 Switch Statement | 按 type/状态分支 | Replace Conditional with Polymorphism（7/8） |
| 组合爆炸 Combinatorial Explosion | 条件组合数量指数增长 | Replace Implicit Language with Interpreter（8）、Interpreter + Composite |
| 怪异解决方案 Oddball Solution | 同一问题多套解法并存 | 统一为一种实现（常配 Adapter，7） |

## 按主题索引的 27 个重构手法（本书目录全量）

### 创建（第 6 章）
- 用 Creation Method 替换构造函数 Replace Constructor with Creation Method（6.1）
- 将创建知识搬移到 Factory Move Creation Knowledge to Factory（6.2）
- 用 Factory 封装类 Encapsulate Classes with Factory（6.3）
- 用 Factory Method 引入多态创建 Introduce Polymorphic Creation with Factory Method（6.4）
- 用 Builder 封装 Composite Encapsulate Composite with Builder（6.5）
- 内联 Singleton Inline Singleton（6.6）

### 简化（第 7 章）
- 组合方法 Composed Method（7.1）
- 用 Strategy 替换条件逻辑 Replace Conditional Logic with Strategy（7.2）
- 将装饰功能搬移到 Decorator Move Embellishment to Decorator（7.3）
- 用 State 替换状态改变条件语句 Replace State-Altering Conditionals with State（7.4）
- 用 Composite 替换隐含树 Replace Implicit Tree with Composite（7.5）
- 用 Command 替换条件调度程序 Replace Conditional Dispatcher with Command（7.6）

### 泛化（第 8 章）
- 形成 Template Method Form Template Method（8.1）
- 提取 Composite Extract Composite（8.2）
- 用 Composite 替换一/多之分 Replace One/Many Distinctions with Composite（8.3）
- 用 Observer 替换硬编码的通知 Replace Hard-Coded Notifications with Observer（8.4）
- 通过 Adapter 统一接口 Unify Interfaces with Adapter（8.5）
- 提取 Adapter Extract Adapter（8.6）
- 用 Interpreter 替换隐式语言 Replace Implicit Language with Interpreter（8.7）

### 保护（第 9 章）
- 用类替换类型代码 Replace Type Code with Class（9.1）
- 用 Singleton 限制实例化 Limit Instantiation with Singleton（9.2）
- 引入 Null Object Introduce Null Object（9.3）

### 聚集操作（第 10 章）
- 将聚集操作搬移到 Collecting Parameter Move Accumulation to Collecting Parameter（10.1）
- 将聚集操作搬移到 Visitor Move Accumulation to Visitor（10.2）

### 实用重构（第 11 章）
- 链构造函数 Chain Constructors（11.1）
- 统一接口 Unify Interfaces（11.2）
- 提取参数 Extract Parameter（11.3）

## 执行纪律（每一步都要）

1. 测试先行/测试绿 → 2. 最小一步重构 → 3. 再跑测试 → 4. 提交。
红条持续几分钟 = 步子太大，回滚重来。多个手法可复合成大步骤，但仅当测试护栏足够时。
