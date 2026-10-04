# Chapter 10: 简化条件逻辑（Simplifying Conditional Logic）

## Core Idea
程序的威力与复杂度都大量来自条件逻辑；重构的目标是让条件结构的"形状"表达意图——复杂的布尔表达式提炼成命名的函数、同果的条件合并为一、罕见的分支用卫语句提前退场、按类型分叉的 switch 升级为多态、对特殊值的重复处理收拢为特例对象。

## Frameworks Introduced

- **分解条件表达式（Decompose Conditional）**
  - 动机：复杂条件让代码"说了发生什么，却说不清为什么"；本质是提炼函数（Extract Function，106）在条件逻辑上的重点应用。
  - 做法：对条件判断、每个分支分别提炼函数，用名字说明"这个分支为什么存在"；提炼后常可换成三元表达式。
  - 安全要点：纯提取不改逻辑，逐个函数小步做。

- **合并条件表达式（Consolidate Conditional Expression）**
  - 动机：一连串检查结果相同，其实只是"一次检查、多个并列条件"，合并后用意更清晰，也为提炼函数做准备。
  - 做法：先确认条件无副作用（必要时先用将查询函数和修改函数分离，306）；顺序检查用 `||` 合并、嵌套 if 用 `&&` 合并；合并后再提炼成函数。
  - 安全要点：若各检查确实彼此独立、并非同一次检查，就不要合并。

- **合并重复的条件片段（Consolidate Duplicate Conditional Fragments）**
  - 动机：各分支中重复的代码应搬到条件语句之外，让分支只呈现真正的差异。
  - 做法：识别分支内相同的片段，移到 if/else 之前或之后；本章以概述形式提及（详见对应条目）。
  - 安全要点：只搬真正在所有路径上都执行的相同代码。

- **以卫语句取代嵌套条件表达式（Replace Nested Conditional with Guard Clauses）**
  - 动机：if-then-else 暗示"两条分支同等重要"；卫语句表达"这是罕见情况，处理后立刻退出"，把主逻辑放到函数顶层。
  - 做法：从最外层条件开始，逐个替换为卫语句并提前 return，每步测试；条件方向不顺时先反转条件（先加 `!` 再化简）；所有卫语句同果则再合并条件表达式。
  - 安全要点：放下"单一出口"教条——代码清晰才是唯一标准；卫语句处理后常可删掉充当双重责任的 `result` 变量。

- **以多态取代条件表达式（Replace Conditional with Polymorphism）**
  - 动机：多个函数都按同一类型代码 switch，或存在"基础逻辑 + 变体"时，用类与多态承载分叉；但作者明确反对"所有条件逻辑都该多态化"。
  - 做法：先用函数组合成类（Combine Functions into Class，144）建立类结构 → 工厂函数（`createBird` / `createRating`）按类型/条件返回实例 → 逐个分支复制到子类覆写，超类对应分支改抛异常，全部完成后超类只留默认逻辑。
  - 安全要点：一次只迁一个分支、迁完即测试；变体逻辑先用提炼函数隔离出可覆写的钩子函数，再在子类覆写，避免整函数复制。

- **引入特例（Introduce Special Case）**（曾用名：引入 Null 对象 Introduce Null Object）
  - 动机：多处客户端以同样方式检查同一个特殊值（如 `"unknown"`），应把应对逻辑收拢到一个特例对象；Null 对象是特例的特例。
  - 做法：加 `isUnknown` 标记属性（正常 `false` / 特例 `true`）→ 对特例比对代码提炼全局函数（可放"陷阱"断言捕捉意外值）→ 逐个客户端改用该函数 → 容器开始返回特例对象 → 把通用应对（默认名字、默认套餐、空支付记录）搬进特例，删除客户端条件。三种实现形态：特例类、字面量对象（`Object.freeze` 冻结）、变换函数（enrichSite 深复制时注入特例）。
  - 安全要点：特例对象是值对象、必须不可变（替代可变对象时设值函数留空实现）；特例返回关联对象时，被返回的通常也是特例（NullPaymentHistory）；个别客户端要用不同值时，保留该处的 `isUnknown` 检查。

- **引入断言（Introduce Assertion）**
  - 动机：代码隐含"执行到此处某条件必为真"的假设；断言把它显式化，既是交流也是调试手段。
  - 做法：在假设处加入 `assert`，永远行为保持；优先放在设值函数/数据入口处，让非法值在源头即失败。
  - 安全要点：断言失败不应被任何地方捕捉，程序有无断言行为完全一致；只检查"必须为真"而非所有"应为真"；只用于防程序员错误——外部输入校验是一等公民代码，不能用断言代替。

## Key Concepts
- 卫语句（guard clauses）——罕见分支的提前退场
- 条件反转（reverse conditional）——卫语句改造的常用辅助
- 类型代码（type code）switch——多态化的典型征兆
- 基础逻辑与变体（basic + variation）——继承表达"大体类似但有差异"
- 特例模式（Special Case）/ Null 对象（Null Object）
- 特例对象三形态：特例类、字面量对象、变换注入
- 断言的交流价值——显式化程序状态假设
- 工厂函数（factory function）——引入多态行为的入口

## Mental Models
- **分支的形状表达重要性**：if/else = 同等重要；卫语句 = "这不关本函数核心的事，收拾一下就退场"。
- **"做什么"换成"为什么"**：把布尔表达式提炼成 `summer()`、`isNotEligibleForDisability()`，读者看到的是意图而非算式。
- **类是多态的最小载体**：先把散落的函数组合成类，再用工厂 + 子类逐分支搬迁；JavaScript 中甚至不必有类型层级，有超类只是为了表达领域关系。
- **特例即默认值供应者**：与其到处问"是不是 unknown"，不如让 unknown 对象自己答出 "occupant"、基础套餐、0 欠费。

## Anti-patterns
- 深层嵌套的 if/else 金字塔 + 承担双重责任的 `result` 变量。
- 多个函数对同一类型代码各写一套 switch，新增类型要改 N 处。
- 同一个哨兵值（如 `"unknown"`）的比对与应对逻辑散落几十处客户端。
- 用逻辑非堆出"把脑袋拧成一团麻"的复合条件——应化简反转。
- 滥用断言做输入校验，或在生产代码里捕捉断言失败。
- 认为"一切条件逻辑都应多态化"。

## Code Examples
以卫语句取代嵌套条件表达式（payAmount）：

Before:
```js
function payAmount(employee) {
  let result;
  if (employee.isSeparated) {
    result = {amount: 0, reasonCode: "SEP"};
  } else {
    if (employee.isRetired) {
      result = {amount: 0, reasonCode: "RET"};
    } else {
      // 主逻辑埋在两层嵌套深处
      result = someFinalComputation();
    }
  }
  return result;
}
```
After:
```js
function payAmount(employee) {
  if (employee.isSeparated) return {amount: 0, reasonCode: "SEP"};
  if (employee.isRetired)   return {amount: 0, reasonCode: "RET"};
  return someFinalComputation(); // 主逻辑置于顶层，result 变量随之消失
}
```

## Reference Tables
本章无速查表；重构索引（页码）：分解条件表达式 260、合并条件表达式 263、以卫语句取代嵌套条件表达式 266、以多态取代条件表达式 272、引入特例 289（曾用名：引入 Null 对象）、引入断言 302。常用配套：提炼函数 106、函数组合成类 144、函数组合成变换 149、内联函数 115、将查询函数和修改函数分离 306。

## Key Takeaways
- 条件重构的第一问：这些分支同等重要吗？同等用 if/else 并提炼命名函数，不等重就用卫语句提前返回。
- "单一出口"不是规则，可读性才是；卫语句常让你顺手消灭 `result` 可变变量。
- 合并条件前先确认无副作用，顺序条件用 `||`、嵌套条件用 `&&`，合并后再提炼命名。
- switch 按同一类型分叉出现在多个函数中 = 多态化的信号；走"组合成类 → 工厂 → 逐分支搬迁"的节奏。
- 同一特殊值的多处相同应对 → 特例对象；按读写需求选类、冻结字面量或变换注入三种形态。
- 断言用来显式化"必须为真"的内部假设并放在数据入口，绝不用于外部输入校验。

## Connects To
- 第 3 章坏味道：过长函数、重复 switch、特例检查遍地。
- 第 9 章：引入断言在本章是验证与交流工具（见以查询取代派生变量）。
- 第 11 章：API 设计中条件逻辑的收敛（工厂函数、参数对象）。
- 《重构与模式》（Kerievsky）：Replace Conditional with Polymorphism 的模式化延伸——Strategy/State/Null Object 替换条件逻辑。
