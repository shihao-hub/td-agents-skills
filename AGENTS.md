# Agent Context Pointer

> **CRITICAL**:
> All base conventions, Git commit rules, and environment guidelines are inherited from:
> `file://D:\Users\language_projects\AGENTS.md`

**SKILL AUTHORING GUIDELINES**:
All root skills, user sub-skills (`sh-user-skills/`), and engineering knowledge base notes (`kb-engineering-notes/`) MUST strictly adhere to:
`file://D:\Users\language_projects\.agents\skills\sh-skill-authoring-rules\SKILL.md`

**ACTION REQUIRED**: Before executing any code changes or git commands, you MUST read and follow the conventions.

## 技能暴露层（根级相对软链）铁律

部分根级技能目录（`sh-plan-driven-development/`、`sh-spec-driven-development/`、`sh-skill-authoring-rules/`）并非真身，而是指向 `sh-user-skills/<name>/` 的**相对软链暴露位**，链接本身随仓入库（git `mode 120000`）。

- **建链/校验**：`uv run expose_user_skill.py <name> [--check]`；链接形态、Windows 分隔符限制与三条硬约束见 `sh-skill-authoring-rules/SKILL.md` 卷二·4；
- **本仓必须 `git config core.symlinks true`**（Windows 首次克隆/换机后执行一次；否则 git 会把入库链接检出成内容为路径文本的普通文件，技能静默失联）：

  ```powershell
  git config core.symlinks true
  ```

- **暴露目录内严禁放 `.gitignore` 屏蔽 `SKILL.md`**：Harness 技能发现复用 gitignore 语义（pi 的 `loadSkillsFromDir` 直接读 `.gitignore`/`.ignore`/`.fdignore`），被屏蔽者无告警消失且 `/skill:name` 一并失效。
