---
name: sh-cmd-desktop-dual-channel
description: 桌面双通道应用脚手架（Go/Wails 与 Python/pywebview）：GUI 只开窗口、CLI 只跑终端，内嵌 WebUI、托盘常驻、关窗销毁重建、窗口几何记忆、dev/release 五维隔离与图标双通道。点名使用
disable-model-invocation: true
---

# sh-cmd-desktop-dual-channel (Command Facade)

> 本技能为用户直调命令门面包装器（Command Wrapper Facade）。  
> 调度真身：`sh-user-skills/sh-desktop-dual-channel/README.md`

## 命令派发协议

当用户通过 `/skill:sh-cmd-desktop-dual-channel` 或显式输入点名唤起本命令时，AI 请遵循以下调度动作：

1. **直接载入真身 SOP**：
   使用文件查看工具载入执行真身：
   `D:\Users\language_projects\.agents\skills\sh-user-skills\sh-desktop-dual-channel\README.md`
2. **保持原语执行**：
   严格按照真身文档所定义的前置检查、分步 SOP 步骤与确认门禁逐步推进，无需重复发问。
