---
name: sh-cmd-plan-driven-development
description: 计划与规划模式总入口：统一分发实施交付计划（默认 kiro 单文件 plans/）、只读探索规划（--claude 方案比选与 Critical Files 对齐）、并预留 agy/dsh 渠道。当用户提及 plan、项目计划、方案规划。点名使用
disable-model-invocation: true
---

# sh-cmd-plan-driven-development (Command Facade)

> 本技能为用户直调命令门面包装器（Command Wrapper Facade）。  
> 调度真身：`sh-user-skills/sh-plan-driven-development/README.md`

## 命令派发协议

当用户通过 `/skill:sh-cmd-plan-driven-development` 或显式输入点名唤起本命令时，AI 请遵循以下调度动作：

1. **直接载入真身 SOP**：
   使用文件查看工具载入执行真身：
   `D:\Users\language_projects\.agents\skills\sh-user-skills\sh-plan-driven-development\README.md`
2. **保持原语执行**：
   严格按照真身文档所定义的前置检查、分步 SOP 步骤与确认门禁逐步推进，无需重复发问。
