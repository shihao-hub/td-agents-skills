# Chapter 3: 代码的坏味道（Bad Smells in Code）

## Core Idea（1–2 句）
知道"如何重构"不等于知道"何时重构"。坏味道（smell）是经验丰富的开发者识别出的、指示重构机会的代码结构信号——它不给出精确的度量标准，而是帮助你培养"何时该动手"的直觉，并指引你选择对应的重构手法。

## Frameworks Introduced（24 个坏味道：识别特征 → 对应重构手法）
核心判断哲学："如果尿布臭了，就换掉它。" 坏味道是迹象而非铁律；先判断闻到什么味道，再查建议的重构手法。

1. **神秘命名（Mysterious Name）**：命名无法清晰表达功能与用法。→ 改变函数声明（Change Function Declaration）、变量改名（Rename Variable）、字段改名（Rename Field）。想不出好名字，往往意味着背后潜藏更深的设计问题。
2. **重复代码（Duplicated Code）**：相同/相似结构出现在多处，修改时必须改所有副本。→ 相同则提炼函数（Extract Function）；相似先用移动语句（Slide Statements）重组再提炼；位于同超类不同子类则函数上移（Pull Up Method）。
3. **过长函数（Long Function）**：函数太长、语义距离（"做什么"与"如何做"）过大；需要注释说明的代码就是提炼信号。→ 主力是提炼函数；临时变量多用以查询取代临时变量（Replace Temp with Query）；参数多用引入参数对象（Introduce Parameter Object）、保持对象完整（Preserve Whole Object），杀手锏是以命令取代函数（Replace Function with Command）；条件用分解条件表达式（Decompose Conditional）；同条件多 switch 用以多态取代条件表达式（Replace Conditional with Polymorphism）；难命名的循环用拆分循环（Split Loop）。
4. **过长参数列表（Long Parameter List）**：参数多且令人迷惑。→ 以查询取代参数（Replace Parameter with Query）、保持对象完整、引入参数对象、移除标记参数（Remove Flag Argument）；多函数共用同批参数则函数组合成类（Combine Functions into Class）。
5. **全局数据（Global Data）**：任何角落可修改且无法追溯来源；类变量和单例同理。→ 封装变量（Encapsulate Variable），再搬入类/模块限制作用域；启动后只读的全局数据危害较小。
6. **可变数据（Mutable Data）**：一处更新、他处失效，罕见故障难排查。→ 封装变量、拆分变量（Split Variable）、移动语句/提炼函数分离副作用、将查询函数和修改函数分离（Separate Query from Modifier）、移除设值函数（Remove Setting Method）、以查询取代派生变量（Replace Derived Variable with Query）、函数组合成类/函数组合成变换（Combine Functions into Transform）、将引用对象改为值对象（Change Reference to Value）。作用域越大风险越大。
7. **发散式变化（Divergent Change）**：一个模块因不同原因朝不同方向变化（加数据库改 3 个函数、加金融工具改 4 个）。→ 变化方向有先后次序用拆分阶段（Split Phase）；来回调用多则建模块后搬移函数（Move Method）；类内混合逻辑先提炼函数再搬移，或提炼类（Extract Class）。核心：每次只关心一个上下文。
8. **霰弹式修改（Shotgun Surgery）**：一种变化需要在许多类里做许多小修改，容易漏改。→ 搬移函数、搬移字段（Move Field）收拢到同一模块；函数组合成类/函数组合成变换；拆分阶段；常用内联函数（Inline Function）、内联类（Inline Class）把不该分散的逻辑拽回一处（先合后拆）。
9. **依恋情结（Feature Envy）**：函数对别的模块的数据兴趣远超自己所在的模块（连环调用半打取值函数）。→ 搬移函数让函数与数据待在一起；只一部分依恋则先提炼函数再搬移。原则：数据最多的模块拥有该函数。例外：Strategy、Visitor、Self Delegation 等模式故意对抗发散式变化。
10. **数据泥团（Data Clumps）**：相同三四项数据反复在字段、参数签名中成群出现。→ 提炼类、引入参数对象、保持对象完整。评判法：删掉一项，其余若失去意义就该建新类。
11. **基本类型偏执（Primitive Obsession）**：钱、坐标、范围、电话号码等用基本类型/字符串表示（stringly typed）。→ 以对象取代基本类型（Replace Primitive with Object）；类型码用以子类取代类型码（Replace Type Code with Subclasses）+ 以多态取代条件表达式；成群出现按数据泥团处理。
12. **重复的 switch（Repeated Switches）**：同样的 switch/if-else 逻辑在多处反复出现，加分支时须逐一更新。→ 以多态取代条件表达式。（第 2 版从"switch 语句"改名：单一 switch 并非罪，重复才是。）
13. **循环语句（Loops）**：函数为一等公民的时代，显式循环不如管道清晰。→ 以管道取代循环（Replace Loop with Pipeline，filter/map）。
14. **冗赘的元素（Lazy Element）**：名字与实现一模一样的函数、只剩一个函数的类——不再承担结构职责的元素。→ 内联函数、内联类；继承体系中用折叠继承体系（Collapse Hierarchy）。
15. **夸夸其谈通用性（Speculative Generality）**：为"总有一天需要"预留的钩子、特殊参数、闲置抽象类。→ 折叠继承体系、内联函数/内联类、改变函数声明去掉无用参数；唯一用户是测试用例的元素，删测试后移除死代码（Remove Dead Code）。
16. **临时字段（Temporary Field）**：字段仅为特定情况而设，对象平时并不需要它。→ 提炼类给字段安家 + 搬移函数；用引入特例（Introduce Special Case）创建替代对象避免条件式代码。
17. **过长的消息链（Message Chains）**：a.getB().getC().getD()…，客户端与导航结构紧耦合。→ 隐藏委托关系（Hide Delegate）；更优做法：观察链末端对象的用途，提炼函数后搬移函数推入链中。不必视所有函数链为恶。
18. **中间人（Middle Man）**：类的接口一半以上函数都在单纯委托。→ 移除中间人（Remove Middle Man）直接打交道；少数几个用内联函数；中间人尚有其他行为则以委托取代超类（Replace Superclass with Delegate）或以委托取代子类（Replace Subclass with Delegate）。
19. **内幕交易（Insider Trading）**：模块间大量私下交换数据，增加耦合。→ 搬移函数、搬移字段减少交流；共同兴趣新建模块或隐藏委托关系做中介；继承密谋用以委托取代子类/超类切断。
20. **过大的类（Large Class）**：字段太多、代码太多，重复接踵而至。→ 提炼类（选相关变量；同前缀/后缀是线索）、提炼超类（Extract Superclass）、以子类取代类型码；观察使用者只用了哪些功能子集来决定怎么拆。
21. **异曲同工的类（Alternative Classes with Different Interfaces）**：功能相似但接口不一致，无法互换。→ 改变函数声明统一签名 + 反复搬移函数直至协议一致；有重复则提炼超类。
22. **纯数据类（Data Class）**：只有字段和取值/设值函数的哑容器，被其他类过分细琐操控。→ 封装记录（Encapsulate Record）、移除设值函数、搬移函数/提炼函数把行为搬进来。例外：拆分阶段产出的不可变中转数据结构，可直接暴露字段。
23. **被拒绝的遗赠（Refused Bequest）**：子类拒绝继承超类的函数和数据。→ 传统疗法：新建兄弟类 + 函数下移（Push Down Method）、字段下移（Push Down Field）。作者观点：味道通常很淡，不值得理睬；但若子类复用实现却拒绝支持超类接口，则很浓——用以委托取代子类/超类划清界限。
24. **注释（Comments）**：注释本身是香味，但常被当"除臭剂"使用——长注释往往标记着糟糕的代码。→ 需要注释解释一块代码就提炼函数；函数仍需解释就改变函数声明改名；说明约束就引入断言（Introduce Assertion）。良好用途：记述"为什么"、标记不确定区域、记录将来的打算。

## Key Concepts
- 坏味道（Bad Smell / Code Smell）：指示重构可能性的结构信号，非精确度量
- 语义距离（"做什么" vs "如何做"的差距）——提炼函数的核心判据
- 封装变量（Encapsulate Variable）：对付全局/可变数据的第一招
- 内聚上下文：将总是一起变化的东西放在一起（发散式变化 vs 霰弹式修改这对镜像）
- stringly typed（类字符串类型）：用字符串承载本应建模的领域概念
- 除臭剂式注释：用注释掩盖坏味道而非重构
- 不可变性约束：分离副作用代码、值对象、查询/修改分离

## Mental Models
- 当你看到需要注释来说明的代码时，用它作为提炼函数的定位器——注释指出语义距离。
- 当一个类因不同原因朝不同方向变化时（发散式变化），按上下文拆分；当一种变化散落在许多类里时（霰弹式修改），先内联收拢再重新提炼。
- 当函数对别的模块的数据比对自己的更感兴趣时，把函数搬到数据那里去（数据与行为同住）。
- 当你想写"总有一天会用到"的通用装置时，删掉它——用不上的装置只会挡路。

## Anti-patterns
- 用注释当除臭剂：注释解释烂代码，而不是先重构
- 为假想中的未来需求预留钩子、参数、抽象类（speculative generality）
- 无条件地"消灭一切 switch/一切循环"——问题在"重复"而非存在
- 全局可变数据随处修改、无处追溯
- 单例/类变量被当成"更体面的全局变量"使用
- 用继承复用实现却强迫子类支持不需要的接口（浓烈的被拒绝的遗赠）
- 测试用例是某函数/类的唯一使用者——那是夸夸其谈通用性的标志

## Code Examples
字符串培养皿是基本类型偏执的典型（书中观点片段）：

```js
// 坏味道：电话号码只是一串字符串（stringly typed）
const phone = "13812345678";
if (phone.length === 11 && phone.startsWith("13")) { ... }

// 重构方向：以对象取代基本类型，让概念拥有一致的逻辑
class PhoneNumber {
  constructor(value) { this._value = value; }
  get display() { return this._value.replace(/(\d{3})(\d{4})(\d{4})/, "$1-$2-$3"); }
  get isMobile() { return /^13\d{9}$/.test(this._value); }
}
```

## Reference Tables（坏味道 → 重构手法完整映射）

| # | 坏味道 | 对应重构手法 |
|---|--------|-------------|
| 1 | 神秘命名 Mysterious Name | 改变函数声明、变量改名、字段改名 |
| 2 | 重复代码 Duplicated Code | 提炼函数；移动语句（先重组）；函数上移（跨子类） |
| 3 | 过长函数 Long Function | 提炼函数；以查询取代临时变量；引入参数对象；保持对象完整；以命令取代函数；分解条件表达式；以多态取代条件表达式；拆分循环 |
| 4 | 过长参数列表 Long Parameter List | 以查询取代参数；保持对象完整；引入参数对象；移除标记参数；函数组合成类 |
| 5 | 全局数据 Global Data | 封装变量（+限制作用域到类/模块） |
| 6 | 可变数据 Mutable Data | 封装变量；拆分变量；移动语句；提炼函数；将查询函数和修改函数分离；移除设值函数；以查询取代派生变量；函数组合成类；函数组合成变换；将引用对象改为值对象 |
| 7 | 发散式变化 Divergent Change | 拆分阶段；搬移函数；提炼函数；提炼类 |
| 8 | 霰弹式修改 Shotgun Surgery | 搬移函数；搬移字段；函数组合成类；函数组合成变换；拆分阶段；内联函数；内联类 |
| 9 | 依恋情结 Feature Envy | 搬移函数；提炼函数（部分依恋时先提炼再搬） |
| 10 | 数据泥团 Data Clumps | 提炼类；引入参数对象；保持对象完整 |
| 11 | 基本类型偏执 Primitive Obsession | 以对象取代基本类型；以子类取代类型码；以多态取代条件表达式；提炼类；引入参数对象 |
| 12 | 重复的 switch Repeated Switches | 以多态取代条件表达式 |
| 13 | 循环语句 Loops | 以管道取代循环 |
| 14 | 冗赘的元素 Lazy Element | 内联函数；内联类；折叠继承体系 |
| 15 | 夸夸其谈通用性 Speculative Generality | 折叠继承体系；内联函数；内联类；改变函数声明；移除死代码 |
| 16 | 临时字段 Temporary Field | 提炼类；搬移函数；引入特例 |
| 17 | 过长的消息链 Message Chains | 隐藏委托关系；提炼函数 + 搬移函数 |
| 18 | 中间人 Middle Man | 移除中间人；内联函数；以委托取代超类；以委托取代子类 |
| 19 | 内幕交易 Insider Trading | 搬移函数；搬移字段；隐藏委托关系；以委托取代子类；以委托取代超类 |
| 20 | 过大的类 Large Class | 提炼类；提炼超类；以子类取代类型码 |
| 21 | 异曲同工的类 Alternative Classes with Different Interfaces | 改变函数声明；搬移函数；提炼超类 |
| 22 | 纯数据类 Data Class | 封装记录；移除设值函数；搬移函数；提炼函数 |
| 23 | 被拒绝的遗赠 Refused Bequest | 函数下移；字段下移；以委托取代子类；以委托取代超类 |
| 24 | 注释 Comments | 提炼函数；改变函数声明；引入断言（先重构，让注释变多余） |

## Key Takeaways
- 坏味道是"迹象提示"而非量化规则：没有任何量度规矩比得上见识广博者的直觉，判断力要自己培养。
- 最常用的三个动作：提炼函数（几乎所有味道的核心手段）、搬移函数/字段（收拢依恋与霰弹）、封装变量（对抗全局/可变数据）。
- 发散式变化与霰弹式修改是一对镜像：前者是"一个类服务太多上下文"，后者是"一个变化散落太多类"；疗法都是"将总是一起变化的东西放在一起"。
- 关键不在于函数/类的长度，而在于"做什么"与"如何做"之间的语义距离。
- 注释不是坏味道，但常是坏味道的定位器：先重构去除坏味道，注释常常随之变多余。
- 内联与提炼是互补的：霰弹式修改时先内联收拢，再拆成合理小块——重构途中出现大类/大函数不必恐慌。
- 有些味道（如被拒绝的遗赠）通常很淡，不值得每次都治；判断味道的浓度也是功力的一部分。

## Connects To
- 第 2 章重构的一般原则：本章回答第 1 章"何时重构"的问题，具体手法细节见第 6–11 章各条目页码。
- 第 4 章构筑测试体系：大规模消除坏味道前，先确保有测试保护网。
- 书后附"坏味道与重构手法速查表"：日常实操时的快速索引。
- 《重构与模式》（Kerievsky）：Strategy/Visitor 等"模式导向"的例外正是坏味道框架的延伸。
