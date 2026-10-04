---
name: sh-agy-browser
description: antigravity 的 /browser 浏览器智能体：真实浏览器交互、动态页抓取、UI 测试。速查表：需要操作网页、抓取动态页或做 UI 测试。点名使用
version: 1.0.0
---

# sh-agy-browser：浏览器智能体

> 版本 v1.0.0 ｜ 来源：Google Antigravity 斜杠命令 /browser。原版为独立 browser agent（系统提示词 "You are a browser agent."），底层是 chrome-devtools-mcp，与 opencode 环境自带的 chrome-devtools 工具同源，直接编排即可。

## 功能介绍

Antigravity 的 /browser：官方释义 "Invoke a browser agent for web tasks."。拥有真实浏览器控制权的智能体：打开页面、处理 JS 动态渲染、模拟点击、填表单、截屏审查、下载资源、UI 验证。

场景：查阅需要动态加载/交互的在线文档与控制台；Web 应用端到端 UI 流程测试；在浏览器里观察实际渲染效果排查前端问题。

## 执行协议

### 1. 打开目标

- `list_pages` 看现有页面；需要干净会话用 `new_page`（isolatedContext 做无 cookie 测试），否则复用页面 `navigate_page` 到目标 URL。
- 长任务先 `resize_page` 到合适视口。

### 2. 读取页面

- 优先 `take_snapshot`（a11y 树 + uid），比截图更适合定位可交互元素；需要肉眼看效果才 `take_screenshot`。
- 动态内容：`wait_for` 等文本出现，或 `evaluate_script` 取 DOM/数据。

### 3. 交互

- 单元素 `click` / `fill` / `hover` / `press_key`；**表单优先 `fill_form` 一次填多字段**（更快更稳）。
- 弹窗用 `handle_dialog`；上传用 `upload_file`。

### 4. 验证与排查（UI 测试/E2E 核心）

- `list_network_requests` + `get_network_request` 查请求/响应与状态码。
- `list_console_messages` 查报错。
- `evaluate_script` 断言页面状态（返回 JSON 可序列化结果）。
- 关键步骤 `take_screenshot` 留证据。

### 红线

- 不在 `evaluate_script` 或表单里明文泄露/打印用户凭据与 cookie。
- 不对未知第三方页面盲目执行下载/运行类操作。

## 与原版的差异

- 原版是独立子代理进程；本版直接编排当前环境的 chrome-devtools 工具，能力同源无降级。
