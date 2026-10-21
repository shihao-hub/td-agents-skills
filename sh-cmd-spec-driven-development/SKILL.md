---
name: sh-cmd-spec-driven-development
description: Kiro Spec 驱动开发工作流（Kiro Quick Spec / Feature / Bug Fix）：产出 requirements.md、design.md、tasks.md 三件套并落盘至 docs/specs/，逐份获批后执行。当用户提及 spec、quick spec、kiro、规格驱动时使用。点名使用
disable-model-invocation: true
---

# sh-cmd-spec-driven-development (Command Facade)

> 本技能为用户直调命令门面包装器（Command Wrapper Facade）。  
> 调度真身：`sh-user-skills/sh-spec-driven-development/README.md`

## 命令派发协议

当用户通过 `/skill:sh-cmd-spec-driven-development` 或显式输入点名唤起本命令时，AI 请遵循以下调度动作：

1. **直接载入真身 SOP**：
   使用文件查看工具载入执行真身：
   `D:\Users\language_projects\.agents\skills\sh-user-skills\sh-spec-driven-development\README.md`
2. **保持原语执行**：
   严格按照真身文档所定义的前置检查、分步 SOP 步骤与确认门禁逐步推进，无需重复发问。
