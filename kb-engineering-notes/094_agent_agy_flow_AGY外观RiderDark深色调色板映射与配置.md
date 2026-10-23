---
name: kb-agy-appearance-rider-dark-theme
description: 针对 Google Antigravity 桌面端应用（Antigravity App / agy app）外观主题定制方案，通过将 JetBrains Rider Dark 调色板与 DSW token 体系映射为 Background、Foreground、Accent 三元色值，消除默认纯黑刺眼高反差，实现舒适护眼的 JetBrains 质感外观配置流水线与落盘验证。
version: 1.0.0
created: "2026-10-23"
updated: "2026-10-23"
id: "094"
domain: agent
scope: agy
type: flow
slug: "AGY外观RiderDark深色调色板映射与配置"
status: verified
last_verified: "2026-10-23"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: true
  trigger_keywords: ["agy app 主题", "Antigravity 外观", "rider-theme", "Appearance", "Dark Theme", "JetBrains Rider", "Antigravity 深色配色"]
---

# 94-Antigravity 桌面端外观 Rider Dark 调色板映射与配置流水线

> **核心摘要**：
> Google Antigravity 桌面应用（Antigravity App / agy app）内置的深色主题（Default Dark）默认采用纯黑冷硬调底色（`#101010` 背景 + `#CCCCCC` 灰字 + `#007ACC` 微软蓝）。长时间进行复杂代码审查与 Agent 对话时，过高的边缘反差容易引发视觉疲劳。
> 本手记基于本地工程 `rider-theme` 插件（移植自 Zed 官方 `jetbrains-rider` 调色板）中定义的 116 个色彩型 `--dsw-*` 变量体系，解析出 Antigravity 桌面端外观设置（Appearance）中 **Background**、**Foreground**、**Accent** 三元基石色值的映射契约，实现开箱即用的 JetBrains Rider / Darcula 经典质感与无损落地。

---

## 一、业务场景与生成需求

### 1. 业务痛点
1. **默认配色生硬刺眼**：Antigravity 默认的 Dark Theme 背景底色为 `#101010`，属于接近 OLED 纯黑的冷死灰，与高亮文字产生强烈的生硬切割感，在非暗室弱光环境下极易造成眼部酸胀；
2. **缺乏 IDE 一致性质感**：开发者日常习惯了 JetBrains 系列（IDEA / Rider / CLion）经典柔和的 Darcula / Rider Dark 灰阶体系，Antigravity 默认的主题在风格上与现有开发环境割裂；
3. **Accent 风格错配**：默认 Accent 为 `#007ACC`（VS Code 标志性青蓝色），与 JetBrains 标志性的皇家蓝（Royal Blue）调性不符。

### 2. 目标交付物
- 将复杂主题包的 116 个 CSS Token 收敛抽象为 Antigravity 桌面端仅开放的 3 个核心色值；
- 确立 **Background**、**Foreground**、**Accent** 与 **Contrast** 的精确取值，并提供一键复用 SOP；
- 完成真机视觉核验与状态持久化确认。

---

## 二、排版/技术核心难点与底层剖析

### 1. 复杂 Token 与三元基石色彩通道的映射收敛
在本地插件 `@local/rider-theme`（`rider-theme/client.js`）中，调色板体系完整覆盖了 116 个色彩型 `--dsw-*` 变量（涵盖 surfaces、borders、brands、buttons、interactive states、labels、markdown 等）：

```javascript
// rider-theme/client.js 核心色值采样
const TOKENS = {
  // surfaces（基底与工作区）
  '--dsw-alias-bg-base': pair('#262626'),
  '--dsw-alias-bg-layer-1': pair('#2b2b2b'),
  '--dsw-alias-bg-layer-2': pair('#2b2b2b'),
  '--dsw-specific-sidebar-fill': pair('#2b2b2b'),

  // labels（文本色）
  '--dsw-alias-label-primary': pair('#dfdfdf'),
  '--dsw-alias-label-secondary': pair('#cecece'),

  // brand & buttons（品牌高亮与激活）
  '--dsw-alias-brand-primary': pair('#3574f0'),
  '--dsw-alias-button-primary-fill': pair('#3574f0'),
  '--dsw-focus-ring-color': pair('#3574f0'),
};
```

而 Antigravity 桌面端应用前端是基于现代 Web/Electron 架构构建，其 **Appearance** 设置层并不要求用户手写百条 CSS 变量，而是采用了类似 Design Tokens 顶层抽象模型的**三元基石色彩通道**：
- **Background**（基底色）
- **Foreground**（主文本色）
- **Accent**（强调色）

系统会在运行时基于这三个通道，配合内置算法自动计算派生各种半透明浮层、Hover 态、焦点环、边框阴影以及代码块背景色。

### 2. 核心参数映射归因

| 配置通道 | Antigravity 默认值 | Rider Dark 映射值 | 底层机制与视觉归因 |
| :--- | :---: | :---: | :--- |
| **Background** | `#101010` | **`#262626`** <br>*(备选 `#2B2B2B`)* | 消除生硬纯黑，采用 JetBrains 标志性的深中灰。Antigravity 会以该色为基准，自动向下/向上派生侧边栏与卡片面板的阶梯灰阶，整体色调瞬间沉稳温和。 |
| **Foreground** | `#CCCCCC` | **`#DFDFDF`** | 对应 Rider 调色板的主文本标签色 `--dsw-alias-label-primary`。相比默认发暗的 `#CCCCCC`，`#DFDFDF` 更加清澈明快，在 `#262626` 灰底下保持最佳无损对比度。 |
| **Accent** | `#007ACC` | **`#3574F0`** | 对应 Rider 的 `--dsw-alias-brand-primary` 与 `--dsw-focus-ring-color`。将微软系 VS Code 青蓝替换为纯正的 JetBrains 皇家蓝（Royal Blue），激活态与开关瞬间具有 Rider 辨识度。 |
| **Contrast** | `Default` | **`Default`** | 必须维持 `Default`。Rider Dark 风格依靠细腻优雅的灰阶梯度，开启 `Strong` 会导致计算对比度暴力拉大，破坏灰阶柔和感。 |

---

## 三、标准配置 SOP 与落盘步骤

### 1. GUI 界面操作路径
1. 打开 Antigravity 桌面端主窗口；
2. 点击左下角头像/齿轮入口，进入 **Settings** 面板；
3. 左侧导航选择 **Appearance**；
4. 检查顶部 **Appearance** 区域：
   - **Theme**：选择月亮图标（🌙 **Dark**）；
   - **Contrast**：保持为 **Default**；
5. 进入下方 **Dark Theme** 配置区域，依次填入对应 HEX 色值：
   - **Preset**：下拉框显示为 `Default Dark`（编辑色值后会自动出现撤销小图标，表示处于自定义覆盖态）；
   - **Background**：在输入框填入 `262626`（前缀带 `#`）；
   - **Foreground**：在输入框填入 `DFDFDF`；
   - **Accent**：在输入框填入 `3574F0`。

```text
┌──────────────────────────────────────────────────────────┐
│ Appearance                                               │
│                                                          │
│ Theme:     [ 💻 ] [ ☀️ ] [ 🌙✓]                           │
│ Contrast:  [ Default✓] [ Strong ]                        │
│                                                          │
│ Dark Theme                                               │
│ Preset:    [ ↺ Default Dark ▾ ]                          │
│                                                          │
│ Background:  [ █ #262626 ]                               │
│ Foreground:  [ █ #DFDFDF ]                               │
│ Accent:      [ █ #3574F0 ]                               │
│                                                          │
│ // Greet a user by name                                  │
│ const greet = (name: string) => {                        │
│   return `Hello, ${name}!`;                              │
│ };                                                       │
└──────────────────────────────────────────────────────────┘
```

6. 观察下方实时代码预览区：代码块背景与高亮色会自动响应重绘；
7. 点击面板右上角 **`✕`** 关闭窗口，配置自动保存生效。

---

## 四、交付验证与扩展建议

### 1. 真机验证断言
- **色值持久化验证**：重启 Antigravity 客户端后再次打开 Settings -> Appearance，确认 **Background**、**Foreground**、**Accent** 依然保持 `#262626`、`#DFDFDF`、`#3574F0`；
- **视觉层级验证**：
  - 会话列表与聊天气泡卡片呈现层次丰富的深灰层次，不再有纯黑带来的生硬边缘；
  - 聚焦光标、输入框边框、选中的 Tab、开关组件（如 Verbose Agent Chat）呈现饱满的 JetBrains 皇家蓝；
  - 代码高亮中的字符串、关键字与注释在 `#262626` 底色下对比清晰自然。

### 2. 扩展建议
- 若希望界面整体更接近 JetBrains 工具窗（Tool Window）而不是编辑区基底，可将 **Background** 调整为 **`#2B2B2B`**；
- 建议将此三元组记录至个人配置清单或自动化初始化脚本，在多机环境部署 Antigravity 时保持统一的视觉工作流。
