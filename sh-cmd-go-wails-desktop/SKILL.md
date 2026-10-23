---
name: sh-cmd-go-wails-desktop
description: Go 双通道桌面应用脚手架：GUI(-gui) 只开窗口不做 CLI、CLI(-cli) 只跑终端不开窗口，内嵌 WebUI 与 Wails v3 托盘、dev/release 通道隔离、PE 图标双通道与无控制台排障。点名使用
disable-model-invocation: true
---

# sh-cmd-go-wails-desktop (Command Facade)

> 本技能为用户直调命令门面包装器（Command Wrapper Facade）。  
> 调度真身：`sh-user-skills/sh-go-wails-desktop/README.md`

## 命令派发协议

当用户通过 `/skill:sh-cmd-go-wails-desktop` 或显式输入点名唤起本命令时，AI 请遵循以下调度动作：

1. **直接载入真身 SOP**：
   使用文件查看工具载入执行真身：
   `D:\Users\language_projects\.agents\skills\sh-user-skills\sh-go-wails-desktop\README.md`
2. **保持原语执行**：
   严格按照真身文档所定义的前置检查、分步 SOP 步骤与确认门禁逐步推进，无需重复发问。
