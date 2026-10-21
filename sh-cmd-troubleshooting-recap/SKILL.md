---
name: sh-cmd-troubleshooting-recap
description: 排障复盘：把一次排障/解题过程按「做了什么 → 怎么想的 → 在哪碰壁 → 怎么解决」四段精炼呈现。当用户要求复盘、想听定位过程，或问"你怎么思考、怎么碰壁、怎么解决的"时使用。点名使用
disable-model-invocation: true
---

# sh-cmd-troubleshooting-recap (Command Facade)

> 本技能为用户直调命令门面包装器（Command Wrapper Facade）。  
> 调度真身：`sh-user-skills/sh-troubleshooting-recap/README.md`

## 命令派发协议

当用户通过 `/skill:sh-cmd-troubleshooting-recap` 或显式输入点名唤起本命令时，AI 请遵循以下调度动作：

1. **直接载入真身 SOP**：
   使用文件查看工具载入执行真身：
   `D:\Users\language_projects\.agents\skills\sh-user-skills\sh-troubleshooting-recap\README.md`
2. **保持原语执行**：
   严格按照真身文档所定义的前置检查、分步 SOP 步骤与确认门禁逐步推进，无需重复发问。
