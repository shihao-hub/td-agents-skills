# Chapter 6: 第一组重构（A First Set of Refactorings）

## Core Idea
本章给出作者最常用的一组重构，覆盖一条完整的工作流：用提炼/内联（函数与变量）雕刻代码、用改名与改变函数声明调整"关节"、用封装变量驯服数据，再把这些小块组合成类、变换或界限分明的阶段。核心精神是小步、测试、以"意图与实现分开"为命名准绳。

## Frameworks Introduced
- **提炼函数（Extract Function，曾用名 Extract Method）**：动机——把"做什么"与"怎么做"分开；判断标准不是函数长度或复用次数，而是"是否需要花时间才能看懂"，好注释常是好函数名。做法要点：以意图命名；优先提炼成嵌套函数以规避作用域问题；只读局部变量作参数传入；被赋值的局部变量是难点——尽量让新函数变成查询并返回该值；多个被赋值变量时先考虑拆分变量/以查询取代临时变量，甚至放弃提炼。安全要点：提炼后测试，并搜索重复代码考虑以函数调用取代内联代码。函数超过 6 行就"散发臭味"，1 行函数也完全正常。
- **内联函数（Inline Function，曾用名 Inline Method）**：动机——函数本体与名字同样清晰时，或间接层过多全是无意义委托时，去掉间接。做法要点：确认函数不具多态性（有子类覆盖就不能内联）；逐个调用点替换并测试；复杂情况（递归、多返回点）干脆不要内联；难内联时每次一行，用搬移语句到调用者拆步。
- **提炼变量（Extract Variable，曾用名 Introduce Explaining Variable）**：动机——给复杂表达式的一部分命名，便于理解与调试。做法要点：确认表达式无副作用；声明不可变变量并替换所有出现。决策点：名字若在更宽上下文有意义，应改用提炼函数暴露成方法（类中尤佳）——对象为共享逻辑提供上下文。
- **内联变量（Inline Variable，曾用名 Inline Temp）**：动机——名字不比表达式本身更有表现力，或妨碍周边重构。做法要点：确认右侧无副作用；先改为不可变确认只赋值一次；逐处替换并测试。
- **改变函数声明（Change Function Declaration；别名 函数改名 Rename Function / 修改签名 Change Signature，曾用名 Rename Method、Add Parameter、Remove Parameter）**：动机——函数声明是软件系统的"关节"；好名字一眼见意图（技巧：先写一句用途注释，再把注释变成名字）；参数列表决定函数与外部世界的耦合面。两套做法：**简单做法**——能一步改完所有调用者就直接改（改名与增参分两步做）；**迁移式做法**——提炼函数→（增参）→测试→内联旧函数（逐个改调用者）→改回名字；多态函数需在每个实现上加转发；已发布 API 可将旧函数标 deprecated 渐进迁移。安全技巧：用引入断言（如 `assert(isPriority === true || isPriority === false)`）捕捉漏改的调用方。
- **封装变量（Encapsulate Variable，曾用名 Self-Encapsulate Field、Encapsulate Field）**：动机——函数可留转发、数据不能；数据作用域越大越要封装，把"重组数据"的难题转化为"重组函数"的简单任务；封装还提供监控与验证钩子。做法要点：创建取值/设值函数→逐一改引用并测试→限制变量可见性（或改名探漏）。进阶决策：只封装引用不够时，取值函数返回副本（尤其列表），或用封装记录阻止内部修改；不可变数据是"强大的代码防腐剂"。作者反对 JavaScript 的"重载取值/设值函数"（同一名字靠有无参数区分）。
- **变量改名（Rename Variable）**：动机——好命名是整洁编程的核心；作用域越广名字越重要（lambda 参数可用单字母，跨函数字段最需用心；动态类型语言常把类型信息放进名字如 `aCustomer`）。做法要点：广泛使用的变量先封装变量再改名（且通常保持封装不再内联）；常量或只读导出变量用"复制到新名→逐一迁移→删旧名"的渐进法；跨代码库的"已发布变量"不能改。
- **引入参数对象（Introduce Parameter Object）**：动机——数据泥团（总是结伴出没的参数）代之以数据结构，缩短参数列表、统一命名；更深远的价值是催生新抽象（如"范围"类），让行为有处安放。做法要点：新建类（非裸对象，便于后续放行为）、尽量做成值对象→用改变函数声明加新参数→逐个调用方传入→逐项替换并删除旧参数。后续：把 `contains` 等行为搬进类，向真正的值对象演化。
- **函数组合成类（Combine Functions into Class）**：动机——一组函数形影不离地操作同一块数据（常作参数传来传去）时，组成类提供共用环境、减少传参、便于传递。做法要点：先封装记录（数据未成记录则先引入参数对象）→对每个函数用搬移函数移入新类→去除已是成员的参数。优点：客户端改核心数据时派生数据自动一致（派生值用计算属性，符合统一访问原则）。优于嵌套函数：好测试、可暴露多个函数。
- **函数组合成变换（Combine Functions into Transform）**：动机——派生数据的计算逻辑散落多处重复，收拢到一个变换函数，输入源记录、深复制后把派生值作为字段填入返回（命名习惯：增强原对象用 "enrich"，生成新对象用 "transform"）。做法要点：变换不修改原记录——为此写测试断言输入不变。关键决策：**源数据会被更新就改用函数组合成类**，否则派生记录与源数据不一致；只读上下文或语言支持不可变数据时变换才合适。
- **拆分阶段（Split Phase）**：动机——一段代码同时处理两件不同的事（典型如编译器：词法分析→语法树→优化→生成目标码）就拆成顺序阶段，修改时只需聚焦一个主题。线索：上下几段代码各自使用不同的一组数据和函数。做法要点：先把第二阶段提炼成函数→引入中转数据结构作参数→逐个检查参数，凡第一阶段创建/使用的就移入中转结构→最后把第一阶段提炼成返回中转结构的函数。

## Key Concepts
- 意图与实现分开（ separating intention from implementation）
- 婴儿学步 / 小步前进（small steps）
- 关节（joints）——函数声明作为系统的连接点
- 转发函数（forwarding function）与迁移式做法（gradual migration）
- 数据泥团（data clump）与值对象（Value Object）
- 统一访问原则（Uniform Access Principle）
- 已发布 API / 已发布变量（published API / variable）——无权修改调用方时的约束
- 中转数据结构（intermediate data structure）
- 不可变性作为防腐剂（immutability as preservative）

## Mental Models
- **提炼/内联是一对呼吸**：理解加深就提炼，理解错了就内联回去重来——提炼失败不是浪费，是学习。
- **数据比函数难搬**：函数有调用这一唯一入口可做转发；数据没有，所以先用封装把数据问题转化为函数问题；数据被使用得越广，越值得花精力封装。
- **命名的上下文决定形式**：名字只在函数内有意义→提炼变量；在更宽上下文（整个类）有意义→提炼成方法/函数；一组名字 + 行为聚在一起→类或变换。
- **组合的三条路径**：函数 + 数据 → 类（数据会变时）；函数 + 数据 → 变换（只读时）；两块异质逻辑 → 拆分阶段（用中转结构衔接）。

## Anti-patterns
- 用"一屏显示"或"复用次数"决定是否提炼函数——正确准绳是意图与实现分离。
- 担心短函数的调用开销而写长函数——现代编译器下问题罕见，遵循一般性能优化准则，别过早优化。
- 保留迷惑人的函数名"反正只是个名字"——发现更好的名字就尽快改。
- 对递归、多返回点、无访问能力的对象强行内联函数——遇到这些复杂情况就别用该手法。
- JavaScript 中用同一函数名做重载取值/设值（Overloaded Getter Setter）——作者强烈反对。
- 源数据会被修改的场景使用变换（enrich record）——派生数据会与源不一致，应改用类。
- 无条件自封装字段（类内部也走访问器）——类大到需要自封装时先考虑拆小。
- 迁移式重构中不给新函数加断言就批量改调用方——漏改难以察觉。

## Code Examples
最能体现机械步骤的范例：**拆分阶段**——先提炼第二阶段、引入中转数据结构、把第一阶段产物全部收拢其中：

Before（一段代码混算商品价格与运费）：
```js
function priceOrder(product, quantity, shippingMethod) {
  const basePrice = product.basePrice * quantity;
  const discount = Math.max(quantity - product.discountThreshold, 0)
      * product.basePrice * product.discountRate;
  const shippingPerCase = (basePrice > shippingMethod.discountThreshold)
      ? shippingMethod.discountedFee : shippingMethod.feePerCase;
  const shippingCost = quantity * shippingPerCase;
  const price = basePrice - discount + shippingCost;
  return price;
}
```

After（两个界限分明的阶段，靠 `priceData` 中转结构衔接）：
```js
function priceOrder(product, quantity, shippingMethod) {
  const priceData = calculatePricingData(product, quantity);
  return applyShipping(priceData, shippingMethod);
}
function calculatePricingData(product, quantity) {
  const basePrice = product.basePrice * quantity;
  const discount = Math.max(quantity - product.discountThreshold, 0)
      * product.basePrice * product.discountRate;
  return {basePrice: basePrice, quantity: quantity, discount: discount};
}
function applyShipping(priceData, shippingMethod) {
  const shippingPerCase = (priceData.basePrice > shippingMethod.discountThreshold)
      ? shippingMethod.discountedFee : shippingMethod.feePerCase;
  const shippingCost = priceData.quantity * shippingPerCase;
  return priceData.basePrice - priceData.discount + shippingCost;
}
```

## Reference Tables
本章开头给出整组手法的选用地图（无表格原文，据 6 章导语与各手法反向关系整理）：

| 目的 | 手法 | 反向 |
|---|---|---|
| 把代码按意图分块 | 提炼函数（106） | 内联函数（115） |
| 给表达式命名 | 提炼变量（119） | 内联变量（123） |
| 改名 / 增删参数 | 改变函数声明（124） | — |
| 驯服可变数据 | 封装变量（132） | — |
| 改数据名 | 变量改名（137）（广用先封装） | — |
| 收拢结伴参数 | 引入参数对象（140） | — |
| 函数 + 数据聚成环境 | 函数组合成类（144） | — |
| 收拢派生计算（只读） | 函数组合成变换（149） | — |
| 分离异质逻辑 | 拆分阶段（154） | — |

注：任务清单中提及的"查询代替函数""提炼类/内联类/隐藏委托关系/移除中间人"不在本章范围——第 6 章实际止于拆分阶段；封装记录、提炼类、隐藏委托等属第 7 章"封装"（本章多处前向引用：封装记录 162、提炼类 182、内联类 186、隐藏委托关系 189）。

## Key Takeaways
- 提炼函数是最高频重构；判断准绳是"是否需要花时间理解"，而非长度或复用；注释常是函数名的最佳来源。
- 局部变量是提炼的主要阻力：只读→传参；被赋值→让新函数返回该值；多个被赋值→先拆分变量/以查询取代临时变量，或暂缓提炼。
- 改函数声明优先用迁移式做法（提炼→内联→改名），配合断言捕捉漏改；已发布 API 用 deprecated 渐进迁移。
- 作用域超出单函数的可变数据一律封装；封装不足时返回副本或用封装记录堵住内部修改；能不可变就不可变。
- 广泛使用的变量改名前先封装；常量改名用"复制新名→迁移→删旧"。
- 数据泥团是引入参数对象的信号，而参数对象只是起点——真正的收益是把行为搬进去形成新抽象（如范围类、值对象）。
- 组合手段的选择看数据可变性：会变→类；只读→变换；两件事混在一起→拆分阶段（中转数据结构是关键工件）。

## Connects To
- 第 7 章（封装）：本章的封装变量是封装记录/封装集合/以对象取代基本类型的前奏；提炼类/内联类/隐藏委托关系在本章导语中被预告。
- 第 3 章（坏味道）：数据泥团→引入参数对象；过长函数→提炼函数；重复的派生计算→函数组合成类/变换。
- 第 6 章手法间高度复用：改变函数声明以提炼函数为迁移式核心；函数组合成类/变换都以搬移函数为操作单元。
