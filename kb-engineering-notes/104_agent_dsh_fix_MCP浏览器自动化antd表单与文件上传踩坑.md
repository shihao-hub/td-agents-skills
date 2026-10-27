---
name: kb-mcp-browser-automation-pitfalls
description: chrome-devtools MCP 操作 React/AntD 网站的五类踩坑与标准解法：el.click()无响应、下拉菜单自动收起、React受控textarea写入、upload_file沙箱路径拒绝、页面主线程卡死截图超时。何时查阅：MCP浏览器自动化中点击/表单/上传/截图任一环节"程序成功但页面无反应"。
version: 1.0.0
status: verified
created: 2026-10-27
last_verified: 2026-10-27
superseded_by: null
deprecation_reason: null
compatibility:
  os: ["windows"]
  tools: ["chrome-devtools-mcp", "dsh"]
falsification_signals:
  - "若 evaluate_script 连 {alive:true} 都超时且持续超过 60 秒，可能是 MCP 连接本身断了，先 list_pages 确认再考虑重启浏览器，不要继续等"
  - "若目标页面不是 React/AntD 技术栈，受控组件写入方式需换原生事件派发验证"
invocation:
  auto_trigger: true
  trigger_keywords: ["mcp 点击没反应", "el.click 无效", "下拉菜单收起", "upload_file 拒绝", "截图超时", "React 受控组件", "ant-modal 写入"]
---

# MCP 浏览器自动化操作 React/AntD 网站五类踩坑与标准解法

## 一、现象与报错直击

chrome-devtools MCP 驱动 Chrome 操作 React + Ant Design 站点（实例：mujicv.com 简历编辑器）时，以下现象全部实测复现：

1. `el.click()` / `dispatchEvent(new MouseEvent('click'))` 返回成功，**页面毫无反应**（导出按钮、下拉触发器）。
2. AntD Dropdown 菜单点开后**几秒自动收起**，等截图/快照回来菜单已经没了。
3. 弹窗里的 `textarea`（React 受控组件）直接设 `value` 后 React state 不同步，点保存等于没写。
4. `upload_file` 报 `Access denied: path ... is not within any of the configured workspace roots`——工作区里的文件传不了。
5. 页面偶发**主线程卡死**：`take_screenshot` / `evaluate_script` 连续超时（连 `{alive:true}` 都回不来）。

## 二、底层根因剖析

1. **合成事件 vs 真实输入**：React 用合成事件委托到 root；`el.click()` 理论上可触发 onClick，但 AntD 部分触发器（dropdown trigger、带 mousedown 逻辑的按钮）监听的是完整指针序列或对 `isTrusted` 有依赖。**CDP 的 `click` 工具走真实输入管线（trusted event），必成功**。
2. **Dropdown 收起机制**：AntD dropdown 监听 document 级 click/focusout 自动关闭；MCP 工具往返间隔（截图→读图→下一调用）远超其关闭延迟。解法不是"快点"，而是**打开后用页内脚本轮询等待目标元素出现并在同一脚本内完成点击**。
3. **受控组件**：React 重渲染时 value 由 state 回写，直接赋 `ta.value` 会在下一次渲染被冲掉。必须用原型 setter 绕过 React 的 value tracker，再派发 `input` 让 onChange 同步 state。
4. **MCP 沙箱路径白名单**：`upload_file` 只允许配置过的 workspace 根（如 `%TEMP%`）；项目工作区盘符路径不在白名单。与 `take_screenshot` 的 `filePath`（允许 TEMP）白名单不同。
5. **卡死**：站点自身 JS 长任务（大弹窗渲染/自动保存）阻塞主线程，CDP evaluate 排队等不到执行。等待通常自愈；持续超时才 reload。

## 三、标准解法 SOP（可直接抄）

### 3.1 点击：优先 CDP，其次完整指针序列

```text
首选：take_snapshot 拿目标 uid → click(pageId, uid)           # 真实输入，永远优先
兜底：页内脚本按 Pointer→Mouse 顺序派发完整序列：
  pointerdown → mousedown → pointerup → mouseup → click（都带 bubbles/cancelable/view/clientX/clientY）
```

### 3.2 短命菜单：打开后同脚本轮询点击（核心套路）

```js
// 1) CDP click 打开菜单；2) 立即 evaluate 轮询，找到即点，全程一个脚本内完成
for (let i = 0; i < 30; i++) {
  const leaf = [...document.querySelectorAll('*')].find(e =>
    e.children.length === 0 && (e.textContent || '').trim() === '目标菜单项');
  if (leaf) {
    const li = leaf.closest('li') || leaf.parentElement;
    const b = li.getBoundingClientRect();
    const o = { bubbles: true, cancelable: true, view: window, clientX: b.left + 10, clientY: b.top + 10, button: 0 };
    li.dispatchEvent(new PointerEvent('pointerdown', o));
    li.dispatchEvent(new MouseEvent('mousedown', o));
    li.dispatchEvent(new PointerEvent('pointerup', o));
    li.dispatchEvent(new MouseEvent('mouseup', o));
    li.dispatchEvent(new MouseEvent('click', o));
    return 'clicked';
  }
  await new Promise(r => setTimeout(r, 100));
}
```

### 3.3 React 受控 textarea/input 写入

```js
const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
setter.call(ta, text);                       // 绕过 value tracker
ta.dispatchEvent(new Event('input', { bubbles: true }));  // 触发 onChange 同步 state
```

### 3.4 文件上传路径

先 `Copy-Item <工作区文件> $env:TEMP\` 中转到 MCP 白名单内，再 `upload_file(pageId, uid, [TEMP 路径])`。

### 3.5 卡死处置

`evaluate_script` 设 `waitForStableDom: false` 仍超时 → 等 10 秒重试一次 → 仍超时 `navigate_page reload`（会弹 beforeunload，工具自动接受）。**reload 会清掉页内注入的实验样式，属预期行为**。

### 3.6 长内容跨页传递

需要在页面 A 用页面 B 的本地文件内容时，不要靠模型转录大文本（易错）：
- 让 B 页 `document.body.innerText` 读出后经 `evaluate_script` 的 `filePath` 参数落盘，再按需分段读回；或
- 用 `Copy-Item` + base64（`[Convert]::ToBase64String`）中转，页内 `atob` + `TextDecoder` 解码。

## 四、验证与防复发闭环

- 每类操作后用**轻量探针**确认生效：`{alive: Date.now()}`（主线程）、目标元素 `getBoundingClientRect().width > 0`（菜单/弹窗）、受控组件 `ta.value === 期望值`。
- 大文本写入后必须回读比对长度/哈希，防止 React 回写冲掉。
- 相关实战案例：`103_browser_mujicv_fix_木及简历自定义CSS行首裁字与导出无样式修复.md`。
