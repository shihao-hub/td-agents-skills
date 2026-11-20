---
name: sh-cmd-transcript-reader
description: 字幕与访谈转写稿转杂志风精读本 HTML：解析 SRT/TXT、提炼认知模型与金句、内置划词加粗/四色背景高亮、右侧全局标注抽屉跳转、自定义 Chrome 标签页标题与自包含 HTML 导出，按去 AI 味排版生成语义规范命名的独立阅读单页。点名使用
disable-model-invocation: true
---

# sh-cmd-transcript-reader (Command Facade)

> 本技能为用户直调命令门面包装器（Command Wrapper Facade）。  
> 调度真身：`sh-user-skills/sh-transcript-reader/README.md`

## 命令派发协议

当用户通过 `/skill:sh-cmd-transcript-reader` 或显式输入点名唤起本命令时，AI 请遵循以下调度动作：

1. **直接载入真身 SOP**：
   使用文件查看工具载入执行真身：
   `D:\Users\language_projects\.agents\skills\sh-user-skills\sh-transcript-reader\README.md`
2. **保持原语执行**：
   严格按照真身文档所定义的前置检查、分步 SOP 步骤与确认门禁逐步推进，无需重复发问。
