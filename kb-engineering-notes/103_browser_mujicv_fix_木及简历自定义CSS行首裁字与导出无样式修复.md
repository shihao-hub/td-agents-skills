---
name: kb-mujicv-css-clip-fix
description: 木及简历(mujicv.com)预览与导出PDF行首行尾字符被裁半、自定义CSS导出不生效的根因与修复。何时查阅：编辑器预览或导出PDF每行第一个/最后一个字缺半截、贴了自定义CSS但导出PDF仍是默认模板样式、CSS保存后刷新又失效。
version: 1.0.0
status: verified
created: 2026-10-27
last_verified: 2026-10-27
superseded_by: null
deprecation_reason: null
compatibility:
  os: ["windows"]
  site: ["mujicv.com"]
falsification_signals:
  - "若预览/ PDF 裁切只出现在某一页的局部而非所有行首，或行是竖排错位而非水平缺字，说明不是本根因，退出本 SOP"
  - "若「设置 CSS」弹窗里本来就为空且从未保存过任何 CSS，先走保存路径再说"
invocation:
  auto_trigger: true
  trigger_keywords: ["木及简历", "mujicv", "简历导出裁字", "行首被裁", "导出PDF没有样式", "自定义CSS不生效"]
---

# 木及简历自定义CSS被平台动态margin裁字与导出无样式修复

## 一、现象与报错直击

木及简历编辑器（mujicv.com/editor）中三个症状同时或分别出现：

1. **预览与导出 PDF 中，每行行首/行尾字符被纸边裁掉约半个字**：`AI Agent 工程师` 显示成 `AL Agent`、电话 `19576213383` 首位缺失、`东南大学` 缺"东"、右列日期 `2023.06 - 至今` 的"今"被切。h2 标题反而有正常缩进不裁。
2. **自定义 CSS 导出后不生效**：编辑器预览里竖线/宋体都在，导出的 PDF 却是平台默认主题（蓝色 h2），所有自定义排版丢失。
3. 用户视角"贴了修复 CSS 也不行"——因为贴入的位置/保存动作不对，见第三节。

无控制台报错，纯布局缺陷。

## 二、底层根因剖析

MCP Chrome (chrome-devtools MCP) 实测 DOM 结构（关键发现）：

- 页面同时存在 **3 个 `.rs-view`**：1 个 794px 宽、`opacity:0` 的**隐藏正本**（`.rs-view-inner` 内），加 N 个**可见渲染层**（`.rs-page-item` 内，视觉宽 678.4px = 794 × scale(0.854408)，缩放挂在 `.rs-page-preview` 的内联 `transform` 上，origin 左上角）。
- **裁字根因**：木及 JS 会在加载/切主题/换字体时，向 `.rs-view-inner` **动态写入内联样式 `margin-left: 84.8px`**（错误计算值，约等于"面板宽-纸宽"差的 1.6 倍）。内容整体左移后，被 `.rs-view` 自身的 `overflow-x: hidden` 边界隐性裁掉行首；导出渲染复用同一正本层，PDF 同样裁字。刷新页面该值必然被重写回——不是偶发。
- **导出无样式根因**：自定义 CSS 只有通过官方「设置 CSS」弹窗（`custom-style-modal`，顶栏 `</>` 图标，svg use `#icon-CSSyangshi`）**点「保 存」**后才会同步进账号配置；导出管线读取的是账号里保存的那份。直接贴在页面其它位置、或只贴不保存，导出一律不带。
- **为什么普通 CSS 修复"不行"**：JS 写的是内联 style，普通规则盖不过内联声明；**必须 `!important`**（CSS 规范：author !important > 内联非 important）。

## 三、标准解决与修复 SOP

> 完整「墨线」CSS 的 **canonical 来源**：`sh-user-skills/sh-muji-resume/assets/ink-rule.css`（12 段含本修复）；项目仓库里的副本以它为准同步。

### 3.1 修复 CSS（追加到自定义 CSS 末尾，两段都是关键）

```css
/* 11. 竖线伪元素出血修复：h2::before left:-16px 会把内容盒撑出纸边 */
.rs-view h2 { padding-left: 16px !important; }
.rs-view h2::before { left: 0 !important; }

/* 12. 动态 margin 裁字修复：压制 JS 写入的内联 margin-left */
.rs-view-inner { margin-left: 0 !important; margin-right: 0 !important; }
.rs-page-preview { transform: none !important; }
```

### 3.2 正确保存路径（人工）

预览面板顶部图标条第 5 个 `</>` → 「设置 CSS」弹窗 → `Ctrl+A` 全选删除旧内容 → 粘贴完整 CSS → 点 **「保 存」** → 刷新页面复核。

### 3.3 正确保存路径（AI / chrome-devtools MCP）

```js
// textarea 是 React 受控组件，必须原生 setter + input 事件
const modal = document.querySelector('.custom-style-modal');
const ta = modal.querySelector('textarea');
const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
setter.call(ta, cssText);
ta.dispatchEvent(new Event('input', { bubbles: true }));
// 然后点弹窗内「保 存」按钮（textContent 去空白 === '保存'）
```

## 四、验证与防复发闭环

刷新页面后逐项检查（evaluate）：

```js
getComputedStyle(document.querySelector('.rs-view-inner')).marginLeft === '0px'  // 修复仍压制中
[...document.querySelectorAll('style')].some(s => s.textContent.includes('.rs-view-inner'))  // CSS 已持久注入
```

- 截图目检：所有行行首/行尾完整；h2 有竖线；导出 PDF 的 h2 颜色 = 自定义 CSS 中的颜色（可在 CSS 里故意用一个特征色验证导出链路是否带上样式）。
- **防复发**：每次切换主题/字体会触发 JS 重写 margin，只要保存过的 CSS 在账号里，`!important` 会持续压制，无需重贴。
- 相关踩坑（自动化操作细节）见 `104_agent_dsh_fix_MCP浏览器自动化antd表单与文件上传踩坑.md`。
