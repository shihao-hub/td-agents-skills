# Chapter 1: 重构，第一个示例（Refactoring: A First Example）

## Core Idea
通过一个完整走完的"戏剧演出团账单"示例演示重构的真实节奏：以微小的、行为保持不变的步骤（每步编译、测试、提交）逐步给代码添加结构，使后续需求（HTML 输出、新增剧种）变得容易。好代码的检验标准是人们能否轻而易举地修改它。

## Frameworks Introduced
本章按示例演进顺序演示的手法链：
- **提炼函数（Extract Function, 106）**：当一段代码可以按意图命名时，把它抽成独立函数。流程：检查离开作用域的变量 → 不修改的作参数传入、被修改的作返回值 → 每次提炼后立刻编译、测试、提交。
- **内联变量（Inline Variable, 123）**：当临时变量只被赋值一次且妨碍提炼时，用表达式直接替换变量。临时变量鼓励长函数，是提炼的障碍。
- **以查询取代临时变量（Replace Temp with Query, 178）**：当变量由一次计算得到且处处可用时，提炼成查询函数（如 `playFor(aPerformance)`），并在调用方内联。
- **改变函数声明（Change Function Declaration, 124）**：分两步走——先让函数体改用新途径，再删旧参数/旧声明（示例中借此移除 `amountFor` 的 `play` 参数）。
- **搬移函数（Move Function, 198）**：当函数与数据属于另一上下文（中转数据结构、PerformanceCalculator 类）时，复制到新家、原函数改造成委托、再内联。
- **拆分循环（Split Loop, 227）+ 移动语句（Slide Statements, 223）**：处理累加变量的前置步骤——先把累加过程从主循环分离，再把声明挪到紧邻使用处，为提炼扫清障碍。
- **以管道取代循环（Replace Loop with Pipeline, 231）**：求和类循环可用 `reduce` 等集合管道改写，更表意。
- **拆分阶段（Split Phase, 154）**：当代码混着两种关注（计算 vs 渲染）时，拆成"创造中转数据结构"（`createStatementData`）和"渲染"（`renderPlainText`/`renderHtml`）两个阶段，使计算逻辑被多种输出格式复用。
- **以子类取代类型码（Replace Type Code with Subclasses, 362）+ 以工厂函数取代构造函数（Replace Constructor with Factory Function, 334）**：为引入多态铺路——建继承体系，用工厂函数根据类型码返回对应子类。
- **以多态取代条件表达式（Replace Conditional with Polymorphism, 272）**：当多个函数依赖同一套类型码分支时，把各分支下移到子类（TragedyCalculator/ComedyCalculator），超类留 `throw new Error('subclass responsibility')`。

## Key Concepts
- **statement 函数**：起始的长函数（44 行），混合计费计算、积分计算与文本渲染三种关注点，是一切重构的靶子。
- **中转数据结构（statementData）**：拆分阶段后第一阶段产出、传给渲染阶段的普通对象，用计算结果（play、amount、volumeCredits）填充，使渲染逻辑与原始输入解耦。
- **演出计算器（PerformanceCalculator）**：承载单场演出计算逻辑的类，是引入多态前的落脚点——先把分散的计算函数集中到一处，再子类化。
- **不可变性（immutable data）**：`Object.assign({}, aPerformance)` 返回浅副本再扩充，避免修改传入参数——可变状态会很快变成烫手山芋。
- **营地法则（Campground Rule）**：保证离开时的代码库比来时更健康；捡垃圾式清理即可，不追求一步到位。
- **重构节奏（refactoring rhythm）**：小步修改 → 编译 → 测试 → 提交；步子越小，出错时排查范围越小。
- **命名即文档**：返回值统一叫 `result`；动态语言参数名带类型（`aPerformance`）；名不恰当时随时换更好的。
- **性能直觉不可靠**：为可读性重复的查询/循环多数影响可忽略；先完成重构，再做基于度量的性能调优。

## Mental Models
- 当需要给程序添加特性但代码不易改时，先重构使修改容易，再做修改（先往北 20 公里上高速，再往东 100 公里）。
- 当一段代码在脑海中"看得懂它干什么"时，立刻把这个理解固化成命名的函数——理解是转瞬即逝的灵光，代码才是持久的载体。
- 当修改会扩散到多个相似分支（如各剧种的计费与积分）时，把按类型分歧的逻辑集中到一个类再多态化——依赖同一套类型的多态函数越多，继承方案越有益。
- 当担心重构影响性能时，默认忽略它——结构良好的代码事后调优容易得多，且多数"重复执行"损耗可忽略。

## Anti-patterns
- **复制整个函数改一份 HTML 版**：计费规则一变就要同步改两处，重复逻辑是长期隐患。
- **一次迈大步**：改动太多后测试失败会陷入大范围调试；步子大不等于快。
- **为性能提前优化**：在重构中因"循环执行了 3 次"而放弃内联/提炼——程序 90% 的优化是白费的，直觉常错。
- **留下误导性注释**：代码结构清晰后，"add volume credits"这类注释应随提炼删除。
- **无测试就动手**：没有自我检验的测试集，任何重构都是赌博。

## Code Examples
重构前——单个长函数，计算与渲染混杂：
```js
function statement (invoice, plays) {
  let totalAmount = 0;
  let volumeCredits = 0;
  let result = `Statement for ${invoice.customer}\n`;
  const format = new Intl.NumberFormat("en-US",
                        { style: "currency", currency: "USD",
                          minimumFractionDigits: 2 }).format;
  for (let perf of invoice.performances) {
    const play = plays[perf.playID];
    let thisAmount = 0;
    switch (play.type) {
    case "tragedy":
      thisAmount = 40000;
      if (perf.audience > 30) {
        thisAmount += 1000 * (perf.audience - 30);
      }
      break;
    case "comedy":
      thisAmount = 30000;
      if (perf.audience > 20) {
        thisAmount += 10000 + 500 * (perf.audience - 20);
      }
      thisAmount += 300 * perf.audience;
      break;
    default:
        throw new Error(`unknown type: ${play.type}`);
    }
    volumeCredits += Math.max(perf.audience - 30, 0);
    if ("comedy" === play.type) volumeCredits += Math.floor(perf.audience / 5);
    result += ` ${play.name}: ${format(thisAmount/100)} (${perf.audience} seats)\n`;
    totalAmount += thisAmount;
  }
  result += `Amount owed is ${format(totalAmount/100)}\n`;
  result += `You earned ${volumeCredits} credits\n`;
  return result;
}
```
重构后——拆分阶段 + 多态计算器，statement 只剩一行编排：
```js
function statement (invoice, plays) {
  return renderPlainText(createStatementData(invoice, plays));
}

// createStatementData.js（计算阶段）
export default function createStatementData(invoice, plays) {
  const result = {};
  result.customer = invoice.customer;
  result.performances = invoice.performances.map(enrichPerformance);
  result.totalAmount = totalAmount(result);
  result.totalVolumeCredits = totalVolumeCredits(result);
  return result;
  function enrichPerformance(aPerformance) {
    const calculator = createPerformanceCalculator(aPerformance, playFor(aPerformance));
    const result = Object.assign({}, aPerformance);
    result.play = calculator.play;
    result.amount = calculator.amount;
    result.volumeCredits = calculator.volumeCredits;
    return result;
  }
}

function createPerformanceCalculator(aPerformance, aPlay) {
    switch(aPlay.type) {
    case "tragedy": return new TragedyCalculator(aPerformance, aPlay);
    case "comedy" : return new ComedyCalculator(aPerformance, aPlay);
    default:
        throw new Error(`unknown type: ${aPlay.type}`);
    }
}
class PerformanceCalculator {
  constructor(aPerformance, aPlay) {
    this.performance = aPerformance;
    this.play = aPlay;
  }
  get amount() { throw new Error('subclass responsibility'); }
  get volumeCredits() {
    return Math.max(this.performance.audience - 30, 0);
  }
}
```
演示了什么：同一个函数从"计算+渲染+类型分支混杂的长函数"演化为"计算阶段（多态计算器填充中转数据）/渲染阶段（可替换为 HTML）两文件分离"的结构——全程每步行为不变、测试通过。

## Reference Tables
| 重构节点 | 解决的问题 | 核心手法 |
|---|---|---|
| 分解长函数 | 理解代码、分离关注点 | 提炼函数 + 内联变量 + 以查询取代临时变量 |
| 拆分阶段 | 计算与文本/HTML 渲染复用 | 拆分阶段 + 搬移函数 + 中转数据结构 |
| 按类型重组计算 | 新增剧种只需加子类 | 以多态取代条件表达式 + 工厂函数 |
| 代码量 44→70 行 | 行数增加但可读性、可扩展性大增 | —— |

## Worked Example
影片出租店/戏剧演出团 statement 示例的完整重构路线图（每步之间都是：编译 → 测试 → 提交）：

1. **起点**：`statement(invoice, plays)` 44 行，switch 计费 + 积分累加 + 字符串拼接混在一个循环里。即将到来的需求：HTML 输出、更多剧种——两者都会让现状迅速恶化。
2. **建立测试**：用几张手工核对过的账单做自我检验的字符比对测试，一行命令可运行。
3. **提炼 amountFor**：把 switch 计费块抽成 `amountFor(perf, play)`；`perf`/`play` 作参数，被修改的 `thisAmount` 作返回值。
4. **改名**：`thisAmount`→`result`；`perf`→`aPerformance`（动态语言参数名带类型）。
5. **移除 play 变量**：提炼 `playFor(aPerformance)` 查询函数 → 内联 `play` 临时变量 → 改变函数声明删除 `amountFor` 的 `play` 参数 → 内联 `thisAmount`。理由：局部临时变量越少，后续提炼越容易。
6. **提炼 volumeCreditsFor**：累加变量棘手，整块抽成函数直接返回积分。
7. **移除 format 变量**：函数赋值给临时变量改成具名函数 `usd(aNumber)`，并把 /100 的整除搬进去（金额以美分整数存储是常见惯例）。
8. **移除 volumeCredits 累加变量**（4 小步）：拆分循环分离累加 → 移动语句让声明贴近循环 → 提炼 `totalVolumeCredits()` → 内联变量。对 totalAmount 重复同样流程（提炼时先临时叫 `appleSauce` 以避开名字冲突，再改名 `totalAmount()`）。
9. **节点一：大量嵌套函数**——statement 顶层只剩 7 行渲染逻辑，计算全部下沉为嵌套函数，代码意图清晰。
10. **拆分阶段**：把渲染整体提炼为 `renderPlainText` → 引入中转对象 `statementData` → 逐字段搬家（customer、performances）→ `enrichPerformance` 以浅副本填充 play、amount、volumeCredits（保持数据不可变）→ 搬移计算函数到第一阶段 → 求和改用 reduce → 最终提炼成独立函数 `createStatementData(invoice, plays)` 并搬到单独文件。
11. **节点二：两文件两阶段**——statement.js 只有编排与渲染；新增 `htmlStatement`/`renderHtml` 只需复用同一 `createStatementData`，零重复计算逻辑。代码 44→70 行，但模块化大幅提升。
12. **为多态铺路**：新建 `PerformanceCalculator` 类，经搬移函数把 amount/volumeCredits 计算搬进类（原函数改造成委托再内联）。
13. **节点三：多态计算器**——以工厂函数取代构造函数（JS 构造函数无法返回子类）→ 以子类取代类型码建 TragedyCalculator/ComedyCalculator → 以多态取代条件表达式把各分支的 `get amount()` 下移到子类，超类改为 `throw new Error('subclass responsibility')`；积分的通用部分（观众 -30）留超类，喜剧差异用 `super.volumeCredits` 覆盖。
14. **收尾**：新增剧种 = 加一个子类 + 工厂里一行分支；依赖同一套类型码的多态函数越多，此设计收益越大。测试始终全绿。

## Key Takeaways
- 重构前先确保有一套能自我检验的测试；每个小步后立刻编译、测试、提交，出错时只需检查最近一小步。
- 遇到测试失败且无法立即定位时：回滚到最近一次可工作的提交，用更小的步子重做。
- 提炼前先移除局部临时变量（以查询取代临时变量 + 内联），提炼会容易得多。
- 累加变量的标准分解路径：拆分循环 → 移动语句 → 提炼函数 → 内联变量。
- 重构会临时增加代码行数（包装成本），换来的是可辨识的模块边界和可复用的计算阶段——可演化的软件以明确为贵。
- 当多个函数按同一套类型码分支时，把类型分歧集中到一个类再多态化；新增类型只碰一处。
- 重构期忽略性能问题；若真有损耗，先完成重构，再用度量工具找热点做调优。

## Connects To
- 第 2 章：本章的直觉在"重构的原则"中系统化（何谓重构、两顶帽子、何时重构）。
- 第 4 章：构筑测试体系——本章"自我检验的测试"的完整展开。
- 手法名录：提炼函数（106）、内联变量（123）、改变函数声明（124）、搬移函数（198）、拆分阶段（154）、以多态取代条件表达式（272）等在本章首次实战演示。
- 外部：TDD 的 red-green-refactor 循环；Martin Fowler 的"先让修改变容易，再做修改"（Kent Beck 语）。
