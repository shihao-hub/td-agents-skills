---
name: sh-cmd-agent-handoff
description: 跨 agent 会话交接：生成贯穿全会话生命周期的自包含交接简报，另一 agent 按路径或模糊描述接手继续。点名使用；接管侧必须完成状态检查与回写打标。点名使用
disable-model-invocation: true
---

# sh-cmd-agent-handoff (Command Facade)

> 本技能为用户直调命令门面包装器（Command Wrapper Facade）。  
> 调度真身：`sh-user-skills/sh-agent-handoff/README.md`

## 命令派发协议

当用户通过 `/skill:sh-cmd-agent-handoff` 或显式输入点名唤起本命令时，AI 请遵循以下调度动作：

1. **直接载入真身 SOP**：
   使用文件查看工具载入执行真身：
   `D:\Users\language_projects\.agents\skills\sh-user-skills\sh-agent-handoff\README.md`
2. **保持原语执行**：
   严格按照真身文档所定义的前置检查、分步 SOP 步骤与确认门禁逐步推进，无需重复发问。
