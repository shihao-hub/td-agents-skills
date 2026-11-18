---
name: kb-go-cli-wails-dual-mode
description: |
  [历史方案，已取代] 单二进制双模不再作为新项目实施依据；当前使用 sh-desktop-dual-channel 双通道方案。本条目仅保留旧链接与检索锚点。
version: 1.4.1
created: 2026-10-20
updated: 2026-11-18
id: "082"
domain: dev
scope: wails
type: flow
slug: "Go单二进制CLI与Wails双模融合架构及无窗排障SOP"
status: deprecated
last_verified: "2026-10-21"
superseded_by: "sh-desktop-dual-channel"
deprecation_reason: "已转正为独立技能 sh-desktop-dual-channel，正文与脚本迁移至 sh-user-skills/sh-desktop-dual-channel/"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: false
---

# 082：历史单二进制方案，已由双通道方案取代

> **状态：deprecated（2026-10-21 转正）**
> **替代者：`sh-desktop-dual-channel`**（真身目录：`sh-user-skills/sh-desktop-dual-channel/`）
> 当前采用 CLI、GUI 两个 exe；新 Go 项目先读父仓《[Go 项目统一结构](../../../docs/projects/go_projects/Go 项目统一结构.md)》，再读 [双通道 Go SOP](../sh-user-skills/sh-desktop-dual-channel/references/go-wails.md)。旧文件名仅为链接兼容保留。

## 迁移说明

本条目原为 Type B 方案流水线，已从知识库转正为个人子技能，按「SOP + references + evals」三层拆分：

| 原内容 | 现位置 |
|---|---|
| 四位一体蓝图、目录树、PE manifest/info.json、`gui.go` 全文 | `sh-user-skills/sh-desktop-dual-channel/references/go-architecture.md` |
| 通道隔离五件套、图标双通道、`render_icon.py` / `build.py` 全文 | `sh-user-skills/sh-desktop-dual-channel/references/go-build-pipeline.md` |
| 任务栏白框、HWND 时序、AttachConsole、门禁拒绝、数据迁移排障 | `sh-user-skills/sh-desktop-dual-channel/references/go-troubleshooting.md` |
| 分步 SOP、验收清单、回滚 | `sh-user-skills/sh-desktop-dual-channel/references/go-wails.md` |

**保留检索关键词**（便于按症状仍能找到这里）：Go CLI Wails 二合一、单二进制、-H windowsgui、无控制台看日志、AttachConsole、logf 落盘、WebView2 DevTools、任务栏 PE 图标、dev release 通道隔离、地鼠图标、anatomymanager。

**使用指引**：需要落地时不要按本文件执行，直接加载 `sh-desktop-dual-channel`；本文件仅作历史锚点与迁移记录。
