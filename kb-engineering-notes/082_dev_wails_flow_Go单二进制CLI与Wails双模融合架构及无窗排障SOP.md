---
name: kb-go-cli-wails-dual-mode
description: |
  [已转正] 原「Go 单二进制 CLI + Wails v3 双模融合架构与无窗排障」条目，正文已迁移至技能 sh-go-wails-desktop；本条目仅保留检索入口与历史锚点。
version: 1.4.0
created: 2026-10-20
updated: 2026-10-21
id: "082"
domain: dev
scope: wails
type: flow
slug: "Go单二进制CLI与Wails双模融合架构及无窗排障SOP"
status: deprecated
last_verified: "2026-10-21"
superseded_by: "sh-go-wails-desktop"
deprecation_reason: "已转正为独立技能 sh-go-wails-desktop，正文与脚本迁移至 sh-user-skills/sh-go-wails-desktop/"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: false
---

# dev_flow_082_Go单二进制CLI与Wails双模融合架构及无窗排障SOP（已转正）

> **状态：deprecated（2026-10-21 转正）**
> **替代者：`sh-go-wails-desktop`**（真身目录：`sh-user-skills/sh-go-wails-desktop/`）

## 迁移说明

本条目原为 Type B 方案流水线，已从知识库转正为个人子技能，按「SOP + references + evals」三层拆分：

| 原内容 | 现位置 |
|---|---|
| 四位一体蓝图、目录树、PE manifest/info.json、`gui.go` 全文 | `sh-user-skills/sh-go-wails-desktop/references/architecture.md` |
| 通道隔离五件套、图标双通道、`render_icon.py` / `build.py` 全文 | `sh-user-skills/sh-go-wails-desktop/references/build-pipeline.md` |
| 任务栏白框、HWND 时序、AttachConsole、门禁拒绝、数据迁移排障 | `sh-user-skills/sh-go-wails-desktop/references/troubleshooting.md` |
| 分步 SOP、验收清单、回滚 | `sh-user-skills/sh-go-wails-desktop/README.md` |

**保留检索关键词**（便于按症状仍能找到这里）：Go CLI Wails 二合一、单二进制、-H windowsgui、无控制台看日志、AttachConsole、logf 落盘、WebView2 DevTools、任务栏 PE 图标、dev release 通道隔离、地鼠图标、anatomymanager。

**使用指引**：需要落地时不要按本文件执行，直接加载 `sh-go-wails-desktop`；本文件仅作历史锚点与迁移记录。
