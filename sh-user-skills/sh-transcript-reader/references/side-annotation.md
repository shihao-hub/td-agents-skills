# 侧栏注解版（Margin Notes）实现标准

> 归属：`sh-transcript-reader` 的可选增强能力（默认关闭）。
> 触发词：**侧栏注解 / 页边注 / margin notes / 旁注 / 批注侧栏 / 注解版 / 逐句解释这段转写**。
> 沉淀来源：`为什么我不推荐下班学AI？人和人的差距从来不是工具！ - 南大教授刘嘉访谈_精读本.html` 第七幕（24 处标注，2026-11-15 实机验证）。

---

## 0. 何时启用

| 场景 | 是否启用 |
| --- | --- |
| 用户点名「侧栏注解 / 页边注 / margin notes / 注解版」 | ✅ |
| 用户说「这段看不懂 / 像音频转写错了 / 逐句解释」 | ✅ |
| 转写稿 ASR 噪声密集（同音误识、断句错位、繁体残留）且用户明确要注解 | ✅ |
| 普通精读本、用户只要求排版 | ❌ 默认不加 |
| 窄屏（< 1200px）为主场景 | ❌ 没有页边距可用，退回纯气泡或不做 |

**一句话判据**：注解是附属品，正文是主体；任何会让正文变窄、位移、断行变化的方案，一律不采纳。

---

## 1. 版式契约（四条硬约束）

1. **正文零位移**：注解版正文列宽、左边界、字号、行高必须与页面其他段落完全一致。
2. **侧栏脱离排版流**：侧栏放在「0 宽网格轨道」里向页边距溢出，并用 `position: sticky` 跟随；不占正文宽度。
3. **原文零改写**：只在原句上包 `<span>`，修正与解释写入 `data-fix` / `data-why`，正文文本不动一个字符。
4. **编号一一对应**：`data-anno="N"` 与侧栏 `#anno-item-N` 严格对应，连续不跳号。

> 验收口径：同一窗口下，`document.querySelector('.anno-main').getBoundingClientRect()` 的 `left/width` 必须与相邻普通段落（如 `.turn-content > p` 的父块）一致。

---

## 2. 结构骨架

```html
<div class="turn-content">
  <div class="anno-layout">
    <div class="anno-main">

      <p>
        <span class="asr-mark" data-anno="1"
              data-fix="他最近（那篇）文章"
              data-why="“近来”是副词，不能直接修饰“文章”；原始字幕写作“他今天文章”。">他近来文章</span>讲了非常多……
      </p>
      <p>……<span class="gloss-mark" data-anno="2"
              data-fix="外部机会的召唤"
              data-why="指别的公司抛来更好的待遇与机会，不是玄学意义上的感召。">外在的召唤</span>……</p>

      <!-- 引文留在正文列内，避免与正文列错位 -->
      <blockquote class="pull-quote">……</blockquote>
    </div>

    <aside class="anno-side" aria-label="本段注解">
      <div class="anno-side-head">
        <span class="anno-side-title">本段注解</span>
        <span class="anno-side-count">24 处 · 可滚动</span>
      </div>
      <div class="anno-tldr">一句话导读（这段到底在说什么）。</div>
      <div class="anno-legend">
        <span><i class="lg-asr"></i>赭色：转写校订（字形 / 断句）</span>
        <span><i class="lg-gloss"></i>松绿：语义注解（真正想说的）</span>
        <span>点编号可定位，悬停看气泡</span>
      </div>
      <details class="anno-notes">
        <summary>为什么这段读着卡？</summary>
        <ul>……四类噪声……</ul>
      </details>
      <ol class="anno-list">
        <li id="anno-item-1" data-anno="1">
          <span class="anno-idx">1</span>
          <div>
            <b class="anno-fix">他近来文章 → 他最近（那篇）文章</b>
            <span class="anno-why">“近来”是副词，不能直接修饰“文章”……</span>
          </div>
        </li>
        <li id="anno-item-2" data-anno="2" class="gloss">……</li>
      </ol>
      <p class="anno-foot">正文另已校订：……（可选，列出已在正文修好的项）。</p>
      <details class="anno-plain-details">
        <summary>顺读版（整段白话）</summary>
        <div class="anno-plain"><p>……</p></div>
      </details>
    </aside>
  </div>
</div>
```

> 侧栏条目**由标记的 `data-*` 派生**（`原文 → data-fix` + `data-why`），避免同一文案维护两份。

---

## 3. 核心 CSS

### 3.1 布局：0 宽轨道 + 溢出页边距（最关键）

```css
.anno-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 0; /* 第二轨 0 宽：侧栏不占正文宽度 */
  align-items: start;
}
.anno-main { min-width: 0; }

.anno-side {
  position: sticky; top: 72px; align-self: start;
  width: 300px; margin-left: 32px;          /* 从正文右缘再向右溢出 */
  max-height: min(calc(100vh - 96px), 820px);
  overflow-y: auto;
  padding: 2px 8px 10px 16px;
  border-left: 2px solid var(--ochre-mark, #E68A36);
  font-size: 12.5px; line-height: 1.64;
  scrollbar-width: thin;
}
.anno-side::-webkit-scrollbar { width: 6px; }
.anno-side::-webkit-scrollbar-thumb { background: var(--border-accent, #CBD5CA); border-radius: 3px; }

.anno-side-head {                            /* 面板内滚动时保留标题 */
  position: sticky; top: 0; z-index: 1;
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 8px; margin-bottom: 9px; padding: 2px 0 6px;
  background: var(--bg-canvas, #FBFBFA);
}
```

> `top: 72px` 是按「顶部有 sticky 工具栏」估的；若页面无工具栏改为 `24px`。
> 主题令牌（`--bg-canvas` / `--pine-mid` / `--clay-mid` / `--ochre-mark` / `--font-serif`）沿用精读本既有变量；目标页没有对应变量时，用代码块里的 fallback 色值即可。

### 3.2 行内标记（上标编号）

```css
.asr-mark, .gloss-mark {
  cursor: help;
  border-bottom: 1px dashed var(--clay-mid, #B0623B);
  padding-bottom: 1px;
  transition: background-color .15s ease;
}
.asr-mark   { background: linear-gradient(transparent 68%, rgba(230,138,54,.16) 68%); }
.gloss-mark {
  border-bottom-color: var(--pine-mid, #2A5E47);
  background: linear-gradient(transparent 68%, rgba(42,94,71,.12) 68%);
}
.asr-mark::after, .gloss-mark::after {
  content: attr(data-anno);
  font-family: var(--font-mono, Consolas, monospace);
  font-size: 9px; line-height: 0; vertical-align: super;
  margin-left: 1px; color: var(--clay-deep, #8E4A28);
}
.gloss-mark::after { color: var(--pine-mid, #2A5E47); }
.asr-mark:hover, .asr-mark:focus, .asr-mark.is-active,
.gloss-mark:hover, .gloss-mark:focus, .gloss-mark.is-active {
  background-color: var(--clay-light, #FBF2EC); outline: none;
}
.gloss-mark:hover, .gloss-mark:focus, .gloss-mark.is-active {
  background-color: var(--pine-light, #EBF3EE);
}
```

### 3.3 气泡（fixed 定位，不撑开布局）

```css
#anno-tip {
  position: fixed; top: 0; left: 0; z-index: 1200;
  width: max-content; max-width: min(340px, calc(100vw - 24px));
  background: #FFFDF9;
  border: 1px solid var(--border-accent, #CBD5CA);
  border-left: 3px solid var(--ochre-mark, #E68A36);
  border-radius: 6px; padding: 11px 13px;
  font-size: 13px; line-height: 1.64;
  box-shadow: 0 10px 28px rgba(28,34,30,.14);
  opacity: 0; transform: translateY(4px); pointer-events: none;
  transition: opacity .14s ease, transform .14s ease;
}
#anno-tip.gloss { border-left-color: var(--pine-mid, #2A5E47); }
#anno-tip.show  { opacity: 1; transform: translateY(0); }
#anno-tip .tip-kicker { font-size: 10.5px; font-weight: 600; letter-spacing: .12em; color: var(--clay-deep, #8E4A28); margin-bottom: 4px; }
#anno-tip .tip-kicker.gloss { color: var(--pine-mid, #2A5E47); }
#anno-tip .tip-fix  { font-family: var(--font-serif, serif); font-size: 14px; font-weight: 600; }
#anno-tip .tip-why  { margin-top: 4px; color: #56645D; }
```

### 3.4 侧栏条目

```css
.anno-side-title { font-family: var(--font-serif, serif); font-size: 14px; font-weight: 700; }
.anno-side-count { font-family: var(--font-mono, monospace); font-size: 10.5px; color: #85938B; }
.anno-tldr { font-size: 12.5px; line-height: 1.7; color: #1F3B2E;
  background: var(--pine-light, #EBF3EE); border-radius: 4px; padding: 9px 11px; margin-bottom: 10px; }
.anno-legend { display: flex; flex-direction: column; gap: 3px; font-size: 11px; color: #85938B; margin-bottom: 10px; }
.anno-legend span { display: flex; align-items: center; gap: 6px; }
.anno-legend i { display: inline-block; width: 16px; height: 2px; border-bottom: 1px dashed; flex-shrink: 0; }
.anno-legend i.lg-asr   { border-color: var(--clay-mid, #B0623B); background: rgba(230,138,54,.18); }
.anno-legend i.lg-gloss { border-color: var(--pine-mid, #2A5E47); background: rgba(42,94,71,.13); }

.anno-notes summary { cursor: pointer; color: var(--clay-deep, #8E4A28); font-size: 11.5px; padding: 3px 0; list-style: none; }
.anno-notes summary::-webkit-details-marker { display: none; }
.anno-notes summary::before { content: "▸ "; }
.anno-notes[open] summary::before { content: "▾ "; }

.anno-list { list-style: none; display: grid; gap: 2px; margin: 0; padding: 0; }
.anno-list li {
  display: grid; grid-template-columns: 20px 1fr; gap: 7px; padding: 6px 2px;
  border-top: 1px dashed #E5E9E3; cursor: pointer; border-radius: 3px;
  transition: background .15s ease;
}
.anno-list li:first-child { border-top: 0; }
.anno-list li:hover { background: #F4F6F3; }
.anno-list li.is-active { background: var(--clay-light, #FBF2EC); }
.anno-list li.is-active.gloss { background: var(--pine-light, #EBF3EE); }
.anno-idx { font-family: var(--font-mono, monospace); font-size: 10px; color: var(--clay-deep, #8E4A28);
  background: var(--clay-light, #FBF2EC); border-radius: 3px; height: 16px; line-height: 16px; text-align: center; }
.anno-list li.gloss .anno-idx { color: var(--pine-deep, #1A4432); background: var(--pine-light, #EBF3EE); }
.anno-fix { display: block; font-weight: 600; line-height: 1.55; }
.anno-why { display: block; color: #56645D; margin-top: 2px; }
.anno-foot { margin-top: 12px; padding-top: 8px; border-top: 1px dashed #E5E9E3; font-size: 11px; line-height: 1.6; color: #85938B; }

.anno-plain-details summary { cursor: pointer; list-style: none; font-family: var(--font-serif, serif);
  font-size: 12.5px; font-weight: 600; color: var(--pine-deep, #1A4432); padding: 4px 0; }
.anno-plain-details summary::-webkit-details-marker { display: none; }
.anno-plain-details summary::before { content: "▸ "; }
.anno-plain-details[open] summary::before { content: "▾ "; }
.anno-plain p { font-size: 12.5px; line-height: 1.8; text-indent: 2em; margin: 6px 0 0; }
```

### 3.5 响应式阶梯（保住页边距，不压字）

```css
@media (max-width: 1500px) { .anno-side { width: 272px; margin-left: 28px; } }
@media (max-width: 1380px) { .anno-side { width: 240px; margin-left: 22px; } }
@media (max-width: 1260px) { .anno-side { width: 214px; margin-left: 16px; } }
@media (max-width: 1200px) {                 /* 页边距真的不够：退回正文下方 */
  .anno-layout { display: block; }
  .anno-side {
    position: static; width: auto; margin: 24px 0 0;
    max-height: none; overflow: visible;
    padding: 14px 0 0 16px; border-left-width: 3px;
  }
}
```

### 3.6 打印

```css
@media print {
  #anno-tip, .anno-side { display: none !important; }
  .asr-mark, .gloss-mark { background: transparent; }
}
```

---

## 4. JavaScript（气泡 + 双向联动）

```js
(function initAnnotations() {
  const marks = document.querySelectorAll('.asr-mark, .gloss-mark');
  if (!marks.length) return;

  const tip = document.createElement('div');
  tip.id = 'anno-tip';
  tip.setAttribute('role', 'tooltip');
  document.body.appendChild(tip);

  const side = document.querySelector('.anno-side');
  let current = null;

  function position(mark) {
    const r = mark.getBoundingClientRect();
    const pad = 12, tw = tip.offsetWidth, th = tip.offsetHeight;
    let left = r.left + r.width / 2 - tw / 2;
    left = Math.max(pad, Math.min(left, window.innerWidth - tw - pad));
    let top = r.bottom + 8;
    if (top + th > window.innerHeight - pad) top = r.top - th - 8;
    if (top < pad) top = pad;
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
  }

  function show(mark, revealNote) {
    const isGloss = mark.classList.contains('gloss-mark');
    tip.className = isGloss ? 'gloss' : '';

    const kicker = document.createElement('div');
    kicker.className = 'tip-kicker' + (isGloss ? ' gloss' : '');
    kicker.textContent = '注 ' + mark.dataset.anno + ' · ' + (isGloss ? '语义注解' : '转写校订');

    const fix = document.createElement('div');
    fix.className = 'tip-fix';
    fix.textContent = mark.dataset.fix || '';

    const why = document.createElement('div');
    why.className = 'tip-why';
    why.textContent = mark.dataset.why || '';

    tip.replaceChildren(kicker, fix, why);
    tip.classList.add('show');
    position(mark);

    if (current !== mark) {
      clearActive();
      current = mark;
      mark.classList.add('is-active');
      const item = sideItem(mark.dataset.anno);
      if (item) {
        item.classList.add('is-active');
        if (revealNote) scrollSide(item);   // 只有点击才滚动侧栏，悬停不滚动
      }
    }
  }

  function clearActive() {
    if (!current) return;
    current.classList.remove('is-active');
    const item = sideItem(current.dataset.anno);
    if (item) item.classList.remove('is-active');
  }

  function hide() {
    tip.classList.remove('show');
    clearActive();
    current = null;
  }

  function sideItem(n) { return document.getElementById('anno-item-' + n); }

  function scrollSide(item) {
    if (!side || side.scrollHeight <= side.clientHeight + 4) return;
    const box = side.getBoundingClientRect();
    const rect = item.getBoundingClientRect();
    if (rect.top >= box.top && rect.bottom <= box.bottom) return;
    const delta = rect.top - box.top - side.clientHeight / 3;
    side.scrollTo({ top: Math.max(0, side.scrollTop + delta), behavior: 'smooth' });
  }

  marks.forEach(mark => {
    if (!mark.hasAttribute('tabindex')) mark.setAttribute('tabindex', '0');
    mark.addEventListener('mouseenter', () => show(mark));
    mark.addEventListener('mouseleave', hide);
    mark.addEventListener('focus', () => {
      if (mark.matches(':focus-visible')) show(mark, true);  // 键盘可达，鼠标点击不抢焦点
    });
    mark.addEventListener('blur', hide);
    mark.addEventListener('click', () => show(mark, true));
  });

  if (side) {
    side.querySelectorAll('.anno-list li').forEach(item => {
      item.addEventListener('click', () => {
        const mark = document.querySelector(
          '.asr-mark[data-anno="' + item.dataset.anno + '"], .gloss-mark[data-anno="' + item.dataset.anno + '"]'
        );
        if (!mark) return;
        mark.scrollIntoView({ block: 'center', behavior: 'smooth' });
        show(mark);
      });
    });
  }

  window.addEventListener('scroll', () => { if (current) position(current); }, { passive: true });
  window.addEventListener('resize', hide);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') hide(); });
  document.addEventListener('click', e => {
    if (!e.target.closest('.asr-mark, .gloss-mark, .anno-side')) hide();
  });
})();
```

---

## 5. 标注文案规范

| 类型 | class | 用途 | `data-fix` 写法 | `data-why` 写法 |
| --- | --- | --- | --- | --- |
| 转写校订 | `asr-mark` | 同音误识、断句错位、繁简残留、漏字 | 短句，如「他最近（那篇）文章」 | 给出依据：原始字幕写法、同音关系、上下文呼应 |
| 语义注解 | `gloss-mark` | 概念、口语压缩、需要背景的指代 | 一句话释义，如「外部机会的召唤」 | 解释「他真正想说的」，必要时给类比 |

**红线**：
- 不臆造事实；不确定一律写「疑为 / 可能」，不写死人物、时间、出处；
- 正文标点与口语重复照抄，**只包 span，不改字**；
- 一段（约 150~300 字）不超过 5 处标注，全篇不超过 ~30 处，避免满屏虚线；
- 数字编号按**文档顺序**连续分配，与侧栏条目同序；
- 词条优先解释「读者会卡住的地方」，而不是逐词翻译；
- 侧栏顶部先给一句话导读，再给图例，最后才是清单——让读者先有结论。

---

## 6. 落地 SOP（给已有/新生成精读本补侧栏）

1. **定目标**：选一轮 ASR 噪声最集中、或用户明确看不懂的长回答（通常一个 `.turn-block`）。
2. **建骨架**：给该轮 `.turn-content` 内插入 `.anno-layout > .anno-main + .anno-side`；引文（pull-quote）留在 `.anno-main` 内。
3. **标原文**：逐个片段包 `span`，补 `data-anno` / `data-fix` / `data-why`；编号从 1 连续。
4. **派生侧栏**：按标记顺序生成 `<li id="anno-item-N" data-anno="N">`，`anno-fix` 显示「原文 → data-fix」，`anno-why` 显示 `data-why`；顺读版放折叠项。
5. **注入 CSS/JS**：`<style>` 中加第 3 节，`<script>` 末尾加第 4 节（先判断 `marks.length`，无标记直接 return）。
6. **验收**：跑第 7 节断言 + 浏览器缩放到 1440 / 1366 / 1210 三个宽度看是否压字或出横向滚动条。

---

## 7. 验收断言

### 7.1 结构（Python，可单文件跑）

```python
import re
from html.parser import HTMLParser

html = open(path, encoding="utf-8").read()
nums = [int(n) for _, n in re.findall(r'class="(asr-mark|gloss-mark)" data-anno="(\d+)"', html)]
ids  = [int(a) for a, _ in re.findall(r'<li id="anno-item-(\d+)" data-anno="(\d+)"', html)]
assert nums == list(range(1, len(nums) + 1)), "标记编号必须从 1 连续"
assert nums == ids, "标记与侧栏条目必须一一对应"
assert html.count('class="anno-side"') == 1
assert 'anno-card' not in html, "不要退回文末大卡片方案"
assert not html.startswith("\ufeff")
```

### 7.2 几何（浏览器 Console）

```js
const box = el => { const r = el.getBoundingClientRect(); return { left: Math.round(r.left), width: Math.round(r.width), right: Math.round(r.right) }; };
const main  = box(document.querySelector('.anno-main'));
const side  = box(document.querySelector('.anno-side'));
const plain = box(document.querySelector('.turn-content > p').parentElement); // 相邻普通段落容器
console.table({ main, side, plain });
// 断言：main.width === plain.width 且 main.left === plain.left（正文未被挤动）
// 断言：side.right <= window.innerWidth - 16（侧栏不越界、不出横向滚动条）
```

### 7.3 交互

- [ ] 悬停任一标记：气泡出现，侧栏对应条高亮；
- [ ] 点击编号：气泡固定、侧栏滚到该条；
- [ ] 点侧栏条目：正文滚到该标记并高亮；
- [ ] `Esc` / 点击空白：气泡关闭；
- [ ] 侧栏内部滚动时，标题仍可见（sticky）。

---

## 8. 已知坑与反模式

| 反模式 | 后果 | 正确做法 |
| --- | --- | --- |
| `grid-template-columns: 1fr 300px` 放在 780 容器里 | 正文被挤到 440px，行宽突变 | 第二轨设为 `0`，侧栏 `width` 溢出到页边距 |
| `width: 1120px; margin-left: 50%; transform: translateX(-50%)` | 正文整体左移约 200px，与上下段落错位 | 不做整体居中/放大；正文列保持原宽 |
| 侧栏放在正文末尾（文末大卡片） | 打断阅读节奏，用户明确反感 | 侧栏固定在页边距，`sticky` 跟随 |
| 悬停即滚动侧栏 | 鼠标扫过多个标记时侧栏来回跳 | 只有**点击**才 `scrollSide`，悬停只高亮 |
| 侧栏祖先有 `overflow: hidden` | `sticky` 失效，变成普通块 | 检查 `.main-container` / `.turn-block` 链条 |
| 窄屏硬塞侧栏 | 横向滚动条或压字 | 用第 3.5 节阶梯，≤1200px 退回正文下方 |
| 强制暗色/阅读器反色 | sticky 标题底色露馅 | 标题底色用 `var(--bg-canvas)` 跟随主题 |
| 用 `mouseenter` 显示 + `click` 切换隐藏 | 触屏设备首次点击即被 focus 事件抢先，气泡闪没 | `click` 始终 `show`，关闭交给 `mouseleave` / `Esc` / 外部点击 |

---

## 9. 参考实现

- 文件：`D:\Users\appdata-agent-skills\sh-zhangshihao-douyin-dl\douyin\为什么我不推荐下班学AI？人和人的差距从来不是工具！ - 南大教授刘嘉访谈_精读本.html`
- 位置：第七幕 `[00:37:52]` 刘嘉关于「克制」的长回答，24 处标注（18 转写校订 + 6 语义注解）。
- 特征：正文列 780px 不变，侧栏贴在右页边距；1440 / 1366 / 1210 三档实测无压字、无横向滚动条。
