---
name: kb-reentrant-publish-stale-layer
description: 前端主题/皮肤/覆盖层切回基础配色后页面仍是旧样式、界面提示与实际渲染自相矛盾：宿主 API 同步 publish 重入、旧 disposer 被文档化为 no-op 导致生效层无人持有，含三方对照、控制组实验与受限擦除修法。
---

# 66-同步publish重入与陈旧句柄导致前端覆盖层擦不掉与视图分叉排障指南

## 一、现象与报错直击

**没有任何报错**（控制台干净、网络无异常、HTTP 全 200），但界面进入一个"擦不掉"的错配状态：

- 把外观切回**浅色**（或切换主题、皮肤、覆盖层）后，**页面仍保持旧配色**；反过来切深色也可能不生效。
- 同一块 UI 里，**行内提示文字与眼前渲染自相矛盾**：提示说"当前基座是浅色"，而整个页面明明是深色。
- 刷新偶尔恢复，但**一旦触发就再点也不回来**；重启应用可能失效、也可能又出现。
- 决定性旁证：**页面上有个别元素仍是"另一套"配色**（本例对话区的文件卡片仍是浅灰），而面板与侧栏是深色 —— 说明不是整体渲染崩了，而是**两套变量来源分叉**。

现场取证（浏览器控制台一行，读"值到底是谁写的"）：

```js
(() => {
  const b = document.body, c = getComputedStyle(b), P = (k) => c.getPropertyValue(k).trim();
  return JSON.stringify({
    attr: b.hasAttribute('data-ds-dark-theme'),   // 渲染层真正打的标记
    source: document.documentElement.dataset.dsThemeSource,
    scheme: document.documentElement.style.colorScheme,
    canvas: c.backgroundColor,                    // 画布（能被"另一套"留下）
    inline: (b.getAttribute('style') || '').replace(/\s+/g, ' ').slice(0, 700), // 关键：inline 变量
    base: P('--dsw-alias-bg-base'), layer1: P('--dsw-alias-bg-layer-1'),
    stat50: P('--dsw-static-neutral-50')          // 静态色：用于判断"两套来源"分叉
  }, null, 1);
})()
```

判读要点：**alias 变量（可被覆盖）是深色、static 变量仍是浅色、而 dark 标记不在** —— 三者不一致，就说明"有一层覆盖还在活着，但已经不属于任何持有者"。

## 二、底层根因剖析

这类框架把"主题/皮肤/覆盖层"实现成 **token 覆盖层（override layer）**，由宿主统一合成后再交给 presenter 写进 DOM。危险点有两处，且都不在业务代码里：

### 2.1 机制一：API 同步 publish 重入 + "调用返回后才记住 handle"

宿主 API（本例 `theme.overrideTokens(source, tokens)`）的文档语义是：

> `@returns disposer removing exactly the layer this call created;` **`a no-op once the source has re-overridden`**

即：**同一个 source 被再次覆盖后，旧那层的 disposer 永久变成 no-op**。而该调用内部会**同步 publish**（`emit('theme/change')`），从而**同步重入**调用方的事件回调。于是这条最自然的写法是错的：

```js
// ✗ 错的：赋值发生在调用返回之后，而调用内部已经同步重入过
const mountLayer = () => { if (layer === null) layer = theme.overrideTokens(SOURCE, TOKENS); };
```

重入路径：`mountLayer()` → `overrideTokens()`（注册第 1 层）→ 同步 publish → 回调 → `reconcile()` → `mountLayer()`（此时 `layer` **仍是 null**）→ 注册第 2 层（把第 1 层顶成 no-op）→ 再 publish → …… 层层覆盖。返回时按 **LIFO** 赋值，最终 `layer` 里留下的是**最旧那层**：

- 旧层的 disposer = 宿主文档化的 **no-op** → 调用它**什么也没删**；
- 真正在生效（最新）那层**无人持有** → 永远撤不掉 → 页面一直保持旧配色；
- 而"该不该画"的判断用的是**运行时视图**，它早已是"浅色" → 行内提示如实说"基座是浅色"，与渲染分叉。

> 症状形态：**提示文字是对的，页面是错的**；反过来的形态（提示错、页面对）也存在。

### 2.2 机制二：presenter"下一拍才撤回"inline 变量

presenter 把当前合成的 token 写成 **`<body>` 的 inline CSS 变量**（不是选择器），并在**下一次 apply** 时按名字逐个 `removeProperty` 撤回：

```js
for (const [name, value] of Object.entries(snapshot.active.tokens)) body.style.setProperty(name, value);
// 下一次 apply 才开始撤回上一批 appliedTokens
```

因此"**层已经没了、值还画着**"是合法存在的中间态（晚到/乱序/被重入打断的 apply 都会造成），必须由调用方自己兜。

### 2.3 受控实验：先证明是"宿主语义"而不是"宿主 bug"

不要急着改业务代码，先用**同一份输入做对照臂**，把语义钉死（这是本类问题的分水岭）：

```js
// 同一 source 注册两层，只调"旧"那层的 disposer
const first  = theme.overrideTokens('probe-control', witnessTokens);
const second = theme.overrideTokens('probe-control', witnessTokens);
first();
// 观察：注册表里仍有 probe-control，且 witness 值照旧画在 body 的 inline 变量上 → 陈旧层确实会存活
second();
// 观察：注册表清空、inline 值消失 → 只有"最新那层"的 disposer 有效
```

配套读出**注册表**（宿主侧真相）：

```js
[...theme.overrides.keys()]          // 谁还挂着
```

### 2.4 反面判据（血的教训）：不要用"画出来的颜色"判断该不该清理

第一版修复用"渲染出来的值是否等于我方调色板"作为触发条件，结果：只要有**别的 source** 恰好画了同样的值，清理永远无法收敛 —— 实测把页面**跑成死循环并炸栈**（`Maximum call stack size exceeded`）。

正确判据是**读注册表找我方 source**：

```js
theme.overrides.has(SOURCE) && /* 且本实例没有 handle */  → 才有残留层要清
```

## 三、标准抢救与修复 SOP

### Step 1 · 三方对照定性（先分清"谁的错"）

| 维度 | 读法 | 本例取值 |
|---|---|---|
| 文档（持久层） | 配置文件 / 服务端设置值 | `preference: light` |
| 运行时视图 | `theme.getTheme()`（含 `preference`、`active.colorScheme`、`active.tokens`） | `light` |
| 实际渲染 | `body` 上的标记 + `getComputedStyle(body)` 的 token 值 | 深色（且是"覆盖层"的颜色） |

三方不一致 ⇒ 十有八九是**覆盖层/句柄生命周期**问题，而不是配置没写进去（后者另有专门条目）。

### Step 2 · 控制组实验

用 §2.3 的对照臂确认：陈旧层存活、只有最新层可撤。**同一时刻**读 `theme.overrides`（注册表）与 `body` 的 inline 变量。

### Step 3 · 修法 A：在途守卫（治本，防再次产生陈旧层）

注册与撤除**各加一个在途布尔量**，让 handle 在同一次调用内定妥：

```js
let layer = null, mounting = false, cleaning = false;

const mountLayer = () => {
  if (layer !== null || mounting) return;      // 重入直接返回，避免层层覆盖
  mounting = true;
  try { layer = theme.overrideTokens(SOURCE, TOKENS); }   // 内部同步 publish，会重入
  finally { mounting = false; }
};

const dropLayer = () => {
  if (layer !== null) {
    const current = layer; layer = null;       // 先清 handle 再撤，避免重入重复撤除
    current();
    return;
  }
  if (cleaning || !theme.overrides.has(SOURCE)) return;   // 无 handle 但有残留层
  cleaning = true;
  try { theme.overrideTokens(SOURCE, TOKENS)(); }         // 重新注册再移除：新层 disposer 一定有效
  finally { cleaning = false; }
};
```

### Step 4 · 修法 B：受限擦除（治标，处理 presenter 晚写下的值）

判定"不该画"时，把**已经被写进 inline、且与我方值完全相同**的变量删掉。两个约束缺一不可：**见证 token 全部命中**才动手（不会误伤别人的调色板）、**只删与我方值相同的变量**：

```js
const WITNESSES = ['--alias-bg-base', '--alias-bg-layer-1', '--alias-border-l4', '--alias-label-primary'];

const scrubPaintedTokens = () => {
  const inline = document?.body?.style;
  if (!inline?.getPropertyValue || !inline?.removeProperty) return;
  // 只有"确认画的就是我方调色板"才动手
  if (!WITNESSES.every((n) => inline.getPropertyValue(n).trim() === TOKENS[n].light)) return;
  for (const [name, value] of Object.entries(TOKENS)) {
    if (inline.getPropertyValue(name).trim() === value.light) inline.removeProperty(name);
  }
};
```

**它不发布任何事件**，所以不会自激；调用点是"决定不画"的那条分支（撤销层之后）。

### Step 5 · 修法 C：延迟复判

事件之后 **再判一次**（本例 250ms），吸收 presenter 的晚到落笔；配合 Step 4，残留值会在一个节拍内被擦掉。复判必须**幂等**（重复进入不产生新副作用）。

### Step 6 · 测试桩必须"忠实模拟同步重入"

这类 bug 之所以能上线，是因为桩比真实宿主"温和"：

- `overrideTokens` 里**要同步 notify**（否则重入路径根本没被覆盖）；
- disposer **不要顺手把画上去的变量删掉**（真实 presenter 是下一拍才撤）；
- 桩要暴露**注册表**（`overrides`），让"残留层"可断言。

```js
overrideTokens(source, tokens) {
  const entry = { tokens };
  state.overrides.set(source, entry);
  writeToBody(tokens);                       // 模拟 presenter 落笔
  for (const notify of listeners) notify(state.snapshot);   // ★ 同步重入
  return () => {
    if (state.overrides.get(source) !== entry) return;      // ★ 陈旧 disposer = no-op
    state.overrides.delete(source);
    for (const notify of listeners) notify(state.snapshot);
    // ★ 故意不删画上去的变量：那是 presenter 的下一拍
  };
}
```

## 四、验证与防复发闭环

### 4.1 验证断言（缺一不可）

- [ ] 注入"无主的残留层"后，**注册表立刻回到空**；
- [ ] 一个节拍后 body 的 inline 变量**已被擦除**，计算值回到基础调色板；
- [ ] 清理**只发生一次**（替换次数 +1，不是递归）；页面前进/后退点几次都不再残留；
- [ ] **用户的持久化偏好未被改写**（清理是本地行为，不写设置文档）；
- [ ] 反向也成立：切到深色时调色板**正常挂载**（守卫没有把正常路径挡掉）。

### 4.2 防复发清单

1. **凡"注册即回调 / 同步 publish"的 API，handle 必须与注册同拍定妥** —— 绝不能"调用返回之后再赋值"。
2. **撤除时先清自己的 handle 再调用 disposer**，并给撤销路径也在途守卫；宿主文档若写了"旧 disposer 变 no-op"，就当它是必须处理的前提。
3. **判据分层**：要不要做（业务意图）读**自己的状态**；用户可见的结论（该画成什么样）用**视图 + 渲染的保守组合**（任一为深色即按深色绘制，"是浅色"只在两者都同意时才说）；清理动作读**注册表**。
4. **绝不用"渲染出来的颜色"当清理触发条件** —— 会被别的来源触碰而无法收敛（实测死循环炸栈）。
5. **测试桩不要比宿主温柔**：同步重入要模拟、撤回延迟要模拟、注册表要可断言。
6. 修复要能**幂等 + 幂等 + 幂等**：延迟复判、重入、重复事件都不应产生第二次副作用。
