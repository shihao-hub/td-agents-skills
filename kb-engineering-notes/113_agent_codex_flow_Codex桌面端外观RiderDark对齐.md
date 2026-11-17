---
name: kb-codex-app-appearance-rider-dark
description: |
  Codex 桌面应用（OpenAI.Codex / ChatGPT 壳）外观对齐 JetBrains Rider Dark 的配置流水线与能力边界：把默认 #181818/#FFFFFF 深色改成 Rider 的 #262626/#DFDFDF/#3574F0，记录外观模型（accent/surface/ink/fonts）、config.toml [desktop] 只存模式、颜色与字体走账号级同步，以及新机上如何复现与回滚。
version: 1.0.0
created: 2026-11-14
updated: 2026-11-14
id: "113"
domain: agent
scope: codex
type: flow
slug: "Codex桌面端外观RiderDark对齐"
status: verified
last_verified: "2026-11-14"
compatibility:
  os: ["windows"]
falsification_signals:
  - "若外观面板里没有『强调色/背景/前景/字体』这四行，说明版本过旧或不是 Codex 桌面应用，停止套用本流水线"
  - "若计划靠手改 ~/.codex/config.toml 改颜色，立即停止：该文件只落 appearanceTheme，颜色/字体是账号级外观"
invocation:
  auto_trigger: true
  trigger_keywords: ["Codex 外观", "Codex 主题", "ChatGPT 桌面端 主题", "appearanceTheme", "Codex Rider Dark", "config.toml desktop", "Codex 强调色", "Codex 背景色"]
---

# agent_codex_flow_113_Codex桌面端外观RiderDark对齐

> **条目定位**：**Type B 配置流水线（Codex 桌面应用外观 × JetBrains Rider Dark 调色板映射与能力边界）**  
> **输入源**：本地 DSH 插件 `rider-theme`（`client.js` 的 `TOKENS` 与 `SHIKI_CSS`）。  
> **交付物**：Codex「外观」页 5 项的值表 + 新机复现步骤 + 回滚方式。  
> **落盘路径**：`C:\Users\<user>\.codex\config.toml`（仅 `[desktop] appearanceTheme` 落盘；颜色/字体不落此文件）。

---

## 一、业务场景与生成需求

Codex 桌面应用（安装包 `OpenAI.Codex`，界面是 ChatGPT 壳）默认深色是 `#181818 / #FFFFFF / #339CFF`，与 JetBrains Rider 的 Darcula 灰阶割裂。目标是把它调成 Rider Dark：

| 目标 | 要求 |
| :--- | :--- |
| 页面背景 | `#262626`（Rider `--dsw-alias-bg-base`） |
| 正文/标题 | `#DFDFDF`（`--dsw-alias-label-primary`） |
| 链接 | `#5A89DA`（`--dsw-alias-link`，不可单独设，由主题推导） |
| 强调色 | `#3574F0`（`--dsw-alias-brand-primary`） |
| 范围 | 只对齐颜色与字体；布局、圆角、图标、打印格式不可改 |

界面入口：**设置 → 外观**，共 6 行：视觉风格/模式、主题、强调色、背景、前景、字体；展开「高级」还有分别设置浅色/深色、半透明侧边栏、代码字体、代码主题、字号。

---

## 二、技术核心难点与底层剖析

### 2.1 外观模型只有 10 个字段（从 `app.asar` 提取）

```
accent（强调色） / surface（背景） / ink（前景） / contrast（对比度）
fonts{ ui, code, content } / translucentSidebar / semanticColors{diffAdded,diffRemoved,skill}
```

默认深色主题（`sk.dark`）就是截图里的值：

| 字段 | 默认值 |
| :--- | :--- |
| `accent` | `#339CFF` |
| `surface` | `#181818` |
| `ink` | `#FFFFFF` |
| `contrast` | `60` |
| `opaqueWindows` | `false` |

另有一个 `chatgpt` 预设（`sE.dark`）：`accent #3A83F7 / surface #000000 / ink #EDEDED`。所以「主题：ChatGPT」和「深色」是两套底子，**先定主题再改色**——换主题会把三项颜色重置回预设。

### 2.2 落盘位置：config.toml 只有模式

`~/.codex/config.toml` 的 `[desktop]` 段实测只有：

```toml
[desktop]
appearanceTheme = "dark"   # system | light | dark
```

**颜色、字体不在此文件**：它们是 ChatGPT 账号级外观（面板里有 `customAccent.syncError` 文案：「您的自定义颜色已保存，但未能同步到其他设备」），改本地配置不会生效，且可能被账号同步覆盖。

### 2.3 为什么「主题」行带导入/导出图标

主题是可分享的字符串（`chromeTheme.export/import`）。改完颜色后该行可导出，换机时粘贴导入即可复现整套外观。

---

## 三、标准自动化流水线与代码实现

### 3.1 新机复现（纯 UI，5 步）

1. 设置 → 外观 → **视觉风格/模式**：选「深色」那张卡（不要纯黑、不要浅色；Rider 调色板只有深色）。
2. **主题**：保持 `ChatGPT`（先定主题，后面三项才不会被重置）。
3. **强调色**：下拉选「自定义」→ 填 `#3574F0`。
4. **背景**：填 `#262626`（要更接近 Rider 面板/侧栏可换 `#2B2B2B`）。
5. **前景**：填 `#DFDFDF`。
6. **字体**：选 `系统`；要完全贴 Rider 就先装 `Inter`（界面）与 `JetBrains Mono`（代码），重启 Codex 后字体下拉里才会出现。

### 3.2 「高级」里的补充项

| 项 | 建议 | 理由 |
| :--- | :--- | :--- |
| 分别设置浅色和深色模式 | 关 | Rider 只有深色，开了反而要维护两套 |
| 半透明侧边栏 | 关 | Rider 面板是实色 |
| 代码字体 | `JetBrains Mono`（装了才可选） | Rider 默认编辑器字体 |
| 代码字号 | `13` | 与 Rider 默认相近 |

### 3.3 不要做的事

- **不要手改 `~/.codex/config.toml` 加颜色键**：不在 schema 里，写了不生效。
- **不要用脚本改 Codex 的渲染**：它是 Electron + 账号同步，本地补丁会被覆盖。

---

## 四、交付验证与工程扩展建议

### 4.1 验收断言

- 外观页「背景」显示 `#262626`、「前景」`#DFDFDF`、强调色色块为 `#3574F0`；
- 侧栏/会话列表由近黑变成灰，正文不再刺白；
- 切换主题再切回来，三项颜色仍是自定义值（说明写入成功）。

### 4.2 能力边界（必须如实告知）

- 只能对齐 `accent/surface/ink/fonts`；Rider 的边框、hover、diff 红绿、菜单浮层等 token 没有入口；
- 布局、圆角、图标、标题栏不可改；
- 强调色是账号级，会同步到其它设备/网页版；不想影响就别登录同账号改。

### 4.3 回滚

外观页底部「重置为默认设置」；或把强调色改回「默认」、背景 `#181818`、前景 `#FFFFFF`。

### 4.4 扩展

同一套 Rider 色板已分别落到三个端：Antigravity（见 `094`）、Codex（本篇）、Tinta（见 `097` 第六章 CSS 主题）。色值来源统一为 `rider-theme/client.js`，改动时三处一起改。
