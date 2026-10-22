---
name: sh-standby-skills
description: |
  备用与低频技能收拢库：集中存放暂不使用但保留备查的各类通用技能（architecture-patterns, clean-code, frontend-design, git-advanced-workflows, python-design-patterns, zread）。点名使用。
disable-model-invocation: true
version: 1.0.0
created: 2026-10-22
updated: 2026-10-23
---

# sh-standby-skills: 备用与低频技能收拢库

> **核心定位**：非永久废弃（Non-Archived），而是**“按需唤醒的备用抽屉”**。  
> 核心目标是**极大减少日常 AI 会话的上下文占用**。平常零常驻加载、零提示词污染；仅在用户明确需要参考对应设计模式、架构理论或代码库提取时按需单点调入。

---

## 调取与执行协议

当用户明确点名或提及调取本库内的某项技能时：
1. AI 使用专用读文件工具（`read_file`）单点加载对应子目录下的入口文档；
2. 严格按其 SOP 步骤执行，执行完成后释放，绝不污染全局常驻上下文；
3. 执行时提示用户该技能已处于备用库模式。

---

## 备用技能清单（不作多余分类，扁平收拢，共 6 项）

| 技能名称 | 原始核心职责与领域 | 物理寻址路径 |
| :--- | :--- | :--- |
| `architecture-patterns` | Implement proven backend architecture patterns including Clean Ar | `sh-standby-skills/architecture-patterns/SKILL.md` |
| `clean-code` | This skill embodies the principles of \"Clean Code\" by Robert C. | `sh-standby-skills/clean-code/SKILL.md` |
| `frontend-design` | Guidance for distinctive, intentional visual design when building | `sh-standby-skills/frontend-design/SKILL.md` |
| `git-advanced-workflows` | Master advanced Git workflows including rebasing, cherry-picking, | `sh-standby-skills/git-advanced-workflows/SKILL.md` |
| `python-design-patterns` | Python design patterns including KISS, Separation of Concerns, Si | `sh-standby-skills/python-design-patterns/SKILL.md` |
| `zread` | Produce and consume a wiki-style knowledge base for a code reposi | `sh-standby-skills/zread/SKILL.md` |

---

## 资产运维与双向迁移

本仓库配有双向自动化同步工具 `sync_standby_skills.py`：
- **将技能移入备用库**：`uv run sync_standby_skills.py move <skill1> [skill2 ...]`
- **将技能还原至根目录**：`uv run sync_standby_skills.py restore <skill1> [skill2 ...]`
- **一键全量还原**：`uv run sync_standby_skills.py --restore-all`
- **状态检查**：`uv run sync_standby_skills.py --check`
- **自动对齐刷新路由表**：`uv run sync_standby_skills.py`
