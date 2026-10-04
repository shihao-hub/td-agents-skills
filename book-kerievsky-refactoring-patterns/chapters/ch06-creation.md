# 第6章 创建

> 来源：《重构与模式》（Joshua Kerievsky, *Refactoring to Patterns*）中文版第6章（OCR 行 2273–4350）。忠实压缩，OCR 错字已按上下文修正。

本章针对各种创建代码中的设计问题：构造函数过多、构造逻辑过于复杂、不必要的 Singleton 等，共 6 个重构。

**核心概念辨析**（本书自定义术语）：
- **Creation Method（创建方法）**：类中创建并返回对象实例的静态或非静态方法。无命名限制，可清晰表达所创建对象的性质。这是本书自定义的模式级术语——所有 Factory Method 都是 Creation Method，反之不尽然；可替代 Fowler 的"工厂函数"、Bloch 的"静态工厂函数"。
- **Factory（工厂）**：实现一个或多个 Creation Method 的类（定义宽泛但明确）。不必是 AbstractFactory；不必专门实现，可让现有类实现 Factory 接口。
- **Factory Method [DP]**：类层次（超类+子类）中实现的、支持多态创建的非静态方法，返回基类/接口类型。
- **AbstractFactory [DP]**：无需指定具体类而创建一系列相关对象的接口，可在运行时替换。每个 AbstractFactory 都是 Factory，反之不然。

避免过度使用 Factory：如果直接 `new` 即可，Factory 只会复杂化设计；除非它确实改善设计，或能以直接实例化做不到的方式创建/配置对象，否则不要引入。

---

## 用 Creation Method 替换构造函数（Replace Constructor with Creation Method, 6.1）

**坏味道/动机**：类中有多个构造函数，难以决定调用哪一个。构造函数必须与类同名（Java/C++），无法有效表达意图；构造函数越多越容易选错；无法添加签名相同但创建对象不同的新构造函数；"死构造函数"（无调用者却残留）使类膨胀。若能通过提炼类/提炼子类减少职责从而减少构造函数，应先做那一步；否则用本重构澄清意图。
- 优点：比构造函数更能表达所创建实例的种类；避开构造函数局限（两构造函数参数不能完全相同）；更容易发现无用的创建代码。
- 缺点：创建方式非标准（有的类用 new、有的用 Creation Method 实例化）。

**做法**：
1. 先找出**全包含构造函数**（catch-all constructor，功能完整、其他构造函数向它委托；没有则先应用"链构造函数 11.1"）。找一段客户代码中对该构造函数的调用，应用提炼函数生成公共静态方法（即 Creation Method），再搬移函数到包含所选构造函数的类中。编译测试。
2. 找出所有调用同一构造函数创建同种实例的代码，改为调用 Creation Method。编译测试。
3. 若所选构造函数链接到另一构造函数，让 Creation Method 直接调用被链接者（内联构造函数）。编译测试。
4. 对每个要转换的构造函数重复 1–3。
5. 对类外无调用的构造函数改为非公共。编译。

**示例**：Loan 类 5 个构造函数支持定期贷款/循环贷款/RCTL 等 7 种贷款；重构后为 `createTermLoan(...)`、`createRevolver(...)`、`createRCTL(...)` 等 Creation Method，全包含构造函数设为私有。注意：向构造函数传 null 表达"无此参数"是坏味道；重载同名 Creation Method（如带 CapitalStrategy 参数的两个 createTermLoan）即可区分时不必造唯一名字。

**变体**：
- **参数化 Creation Method**：不必为每种配置各写一个方法；常用配置用 Creation Method，其余留公共构造函数，或用参数减少方法数。
- **提取 Factory**：若 Creation Method 过多、喧宾夺主，把相关 Creation Method 重构为一个 Factory 类（如 LoanFactory）。注意 LoanFactory 不是 AbstractFactory——Factory 不应太复杂。

---

## 将创建知识搬移到 Factory（Move Creation Knowledge to Factory, 6.2）

**坏味道/动机**：实例化一个类所需的数据和代码散布在多个类中——**创建蔓延**（creation sprawl，解决方案蔓延的一种）：创建职责被放在了不该承担它的类里。典型蛮力做法是配置选项逐层传递，导致创建代码到处都是。Factory 用一个类合并创建逻辑与实例化/配置选项：客户代码配置 Factory 实例，运行时由同一实例执行创建（如 NodeFactory 可配置为用 DecodingStringNode 装饰所创建的 StringNode）。
- 优点：合并创建逻辑和实例化/配置选项；将客户代码与创建逻辑解耦。
- 缺点：若可以直接实例化，会使设计复杂化。
- 若 Factory 创建逻辑因支持太多选项而过于复杂，可改为 AbstractFactory[DP]（如 StandardNodeFactory / DecodingNodeFactory）。

**做法**（假设 Factory 实现为类而非接口）：
1. 使实例化类（与其他类协作创建产品的类）通过 Creation Method 实例化产品（必要时修改产品类）。编译测试。
2. 创建新类作为工厂（如 NodeFactory）。编译。
3. 应用搬移函数把 Creation Method 搬到工厂类；静态方法可顺势改为非静态。编译。
4. 更新实例化类为实例化工厂并经它获取产品；对所有编译失败的客户代码同样处理。编译测试。
5. 把散落在其他类（如 Parser）中参与创建的数据/方法尽可能搬进工厂，使其尽量多承担创建工作（可能需要先提炼类、再内联合并、最后改名——如 Parser 的解析选项经 StringNodeParsingOption 提炼后与 NodeFactory 合并）。编译测试。

**示例**：HTML Parser 项目中，StringNode 的创建知识散布在 Parser / StringParser / StringNode 三处；重构后由 NodeFactory 统一承担 StringNode 的实例化与配置（解码、转义字符删除等选项）。

---

## 用 Factory 封装类（Encapsulate Classes with Factory, 6.3）

**坏味道/动机**：客户代码直接实例化同一包结构中、实现同一接口的多个类。若客户其实不需要知道这些类的存在（同包、同接口、少变动），可用 Factory 把它们与包外客户隔离：构造函数改为非公共，由 Factory 创建并返回实例（示例：descriptors 包的 AttributeDescriptor 层次，客户提供 `forBoolean/forClass/forDate/forInteger/forString` 等 Creation Method）。
- 优点：以意图导向的 Creation Method 简化不同种类实例的创建；强制执行"面向接口编程，而不是面向实现"；隐藏不需公共可见的类，减少客户需要了解的类数量（也减少实例化错子类/错参数——如 int vs Integer——的机会）。
- 缺点：创建新种类实例时必须新建/更新 Creation Method（依赖循环：子类或构造函数一变，Factory 就要变）；客户只能拿到 Factory 二进制码时无法定制。若变动频繁，可只封装最常用的子类、其余让客户直接创建。若某类既是 Factory 又是实现类导致职责模糊，考虑提取 Factory（6.1 变体）。

**做法**：
1. 从客户代码中对构造函数的调用提炼出公共静态 Creation Method，搬移函数到这些类的**超类**中（返回类型改为通用接口/超类类型）。编译测试。
2. 找出所有创建同种实例的构造函数调用，改为调用 Creation Method。编译测试。
3. 对该构造函数能创建的所有实例种类重复 1–2。
4. 把类的构造函数声明为非公共。编译。
5. 对所有需封装的类重复 1–4。

**变体——封装内部类（Encapsulating Inner Classes）**：`java.util.Collections` 是范例——不可修改/同步的代理（Proxy 的保护形式）全部定义为非公共内部类，Collections 通过一组 Creation Method（synchronizedCollection、unmodifiableList 等）返回通用接口类型，既提供功能又减少程序员需了解的类数。Collections 本身就是一个 Factory。

---

## 用 Factory Method 引入多态创建（Introduce Polymorphic Creation with Factory Method, 6.4）

**坏味道/动机**：类层次中的多个类相似地实现了同一个方法，只有对象创建的步骤不同（如 XMLBuilderTest 与 DOMBuilderTest 中 9 个几乎相同的测试方法，仅 `new DOMBuilder(...)` 与 `new XMLBuilder(...)` 之别）。重构到 Factory Method[DP]：创建唯一超类版本的方法，它调用 Factory Method 处理实例化；各子类实现 Factory Method 决定实例化什么。Factory Method 常被 Template Method 调用，二者协作消除层次中的重复。
- 优点：减少因创建自定义对象产生的重复代码；清楚表达创建发生在哪、如何重写。
- 缺点：强制所有实现者实现统一类型；可能向部分实现者传递不必要的参数（统一签名所致）。
- 适用于两种情形：兄弟子类有相似方法；超类与子类有相似方法（做法同理）。

**做法**：
1. 在含相似方法的子类中，把创建代码提炼为一个实例化方法（命名通用，如 createBuilder；返回通用类型），方法其余部分改为调用它。编译测试。
2. 对所有兄弟子类重复，得到签名一致的实例化方法。编译测试。
3. 修改（或用提炼超类新建）兄弟子类的公共超类。编译测试。
4. 对相似方法应用"形成 Template Method"（8.1），进而函数上移；上移时把实例化方法声明为超类的抽象方法（Fowler 建议），各子类的实现即为 Factory Method: ConcreteCreator。编译测试。
5. 对其他可受益的相似方法重复 1–4。
6. 若大多数 ConcreteCreator 的工厂方法实现相同，把抽象方法改为具体的默认实现（仅当能减少重复时）。编译测试。

**示例**：AbstractBuilderTest（提炼自 JUnit TestCase 之上的测试类）持有 `protected OutputBuilder builder` 和抽象 `createBuilder(...)`，testAddAboveRoot 上移其中；DOMBuilderTest / XMLBuilderTest 分别返回 new DOMBuilder / new XMLBuilder。

---

## 用 Builder 封装 Composite（Encapsulate Composite with Builder, 6.5）

**坏味道/动机**：构造 Composite[DP] 重复、复杂、易出错（实例化新结点→初始化→挂到正确双亲，容易漏挂或挂错双亲）；客户代码与 Composite 实现紧耦合（如直接操作 org.w3c.dom 的 Document/Element/Text，升级 DOM 版本要改遍系统的构造代码）。用 Builder[DP] 代替客户执行繁重构造步骤：简化客户代码、解耦、并可创建不同表示（DOMBuilder 接口只收字符串返回 void，内部组装 DOM；换 JDOM/TagNode 只需接口相同的新 Builder）。
- 优点：简化构造 Composite 的客户代码；减少重复与出错；客户与 Composite 松耦合；可创建不同表示。
- 缺点：接口可能不会清楚表达意图（Builder 在幕后做了很多简化工作）。

**做法**（建议测试驱动开发；假设已有 Composite 构造代码）：
1. 创建生成器（未来的 Builder），使其能构造单一结点的 Composite，并提供返回结果的方法（如 toXml()）。编译测试。
2. 使生成器可创建子结点并提供便捷布置方法（addChild / addSibling / addToParent——addToParent 按双亲标签名沿父链查找，属 Chain of Responsibility 思想；找不到双亲应报错）。编译测试。
3. 若被替换代码需设置结点属性/值，给生成器加 addAttribute / addValue。编译测试。
4. 反思生成器对客户是否足够简单，使其更简单。
5. 把 Composite 构造代码改为使用生成器——客户代码成为 Builder:Client 与 Builder:Director。编译测试。

**示例**：TagBuilder 封装 TagNode（XML Composite）。性能改进变体：按加入内容累计缓冲区长度，用精确长度实例化 StringBuffer，避免自动增长。**变体——基于模式的 Builder（Schema-Based Builder）**：用 TreeSchema（tab 缩进字符串定义标签父子映射）驱动单一 `add(tagName)` 方法自动布置结点（SchemaBasedTagBuilder），适合庞大 XML；重名标签可用 `add(child, parent)` 显式指定。

---

## 内联 Singleton（Inline Singleton, 6.6）

**坏味道/动机**：代码需要访问一个对象，但不需要全局入口。"Singletonitis"（沉迷于 Singleton）制造了大量不必要的 Singleton。判断要点：**能通过设计避免 Singleton 时，它就是不必要的**——把对象引用传给需要它的对象更简单时；只为无关紧要的内存/性能改进时；深层次代码访问不同层资源时。引 Ward Cunningham（全局变量应极少）、Kent Beck（Singleton 让你逃避思考对象可见性；显式传参半小时的重构带来更清晰设计、稳定测试）、Martin Fowler（Registry 是最后手段，"任何全局数据在被证明无害之前都是有害的"）。若确有充分理由（如真实性能提升，见 9.2 用 Singleton 限制实例化），才用 Singleton。
- 优点：使对象协作更明显、更明确；无需特殊代码即保护单一实例。
- 缺点：当在许多层次间传递实例较困难时，会使设计复杂化。

**做法**（与将类内联化[F]相同；吸收类 = 承担 Singleton 职责的类）：
1. 在吸收类中声明 Singleton 的公共方法，先委托到 Singleton，去掉静态声明。
2. 把客户代码对 Singleton 的引用改为对吸收类的引用。编译测试。
3. 应用搬移函数/搬移字段把 Singleton 的全部功能搬入吸收类，除掉方法与字段的所有 static 声明。编译测试。
4. 删除 Singleton。

**示例**：二十一点游戏中 Console 以静态方式保存 HitStayResponse（事实上的 Singleton）；Blackjack 及其测试都在同一层，完全可显式传引用，故把 Console 内联进 Blackjack 后删除。
