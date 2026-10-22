---
name: sh-standby-skills
description: |
  备用与低频技能收拢库：集中存放架构模式(architecture-patterns)、整洁代码(clean-code)、前端设计(frontend-design)、Git高级流(git-advanced-workflows)、Python设计模式(python-design-patterns)、代码库wiki(zread)等暂不使用但保留备查的技能。点名使用。
disable-model-invocation: true
version: 1.0.0
created: 2026-10-22
updated: 2026-10-22
---

# sh-standby-skills: 备用与低频技能收拢库

> **核心定位**：非永久废弃（Non-Archived），而是**“按需唤醒的备用抽屉”**。  
> 核心目标是**极大减少日常 AI 会话的上下文占用**。平常零常驻加载、零提示词污染；仅在用户明确需要参考对应设计模式、架构理论或代码库提取时按需单点调入。

---

## 调取与执行协议

当用户明确点名或提及调取本库内的某项技能时：
1. AI 使用专用读文件工具（`read_file`）单点加载对应子目录下的 `SKILL.md`；
2. 严格按其 SOP 步骤执行，执行完成后释放，绝不污染全局常驻上下文；
3. 执行时提示用户该技能已处于备用库模式。

---

## 备用技能清单（不作多余分类，扁平收拢）

| 技能名称 | 原始核心职责与领域 | 物理寻址路径 |
| :--- | :--- | :--- |
| `architecture-patterns` | Clean Architecture、六边形架构、DDD 分层模式与解耦 | `sh-standby-skills/architecture-patterns/SKILL.md` |
| `clean-code` | Robert C. Martin 整洁代码原则、函数精炼与重构习惯 | `sh-standby-skills/clean-code/SKILL.md` |
| `frontend-design` | 前端界面设计、视觉层次、排版美学与避免模版味 | `sh-standby-skills/frontend-design/SKILL.md` |
| `git-advanced-workflows` | 交互式变基、Cherry-pick、二分排障与 Worktree 高阶操作 | `sh-standby-skills/git-advanced-workflows/SKILL.md` |
| `python-design-patterns` | KISS、关注点分离、单一职责等 Python 面向对象设计模式 | `sh-standby-skills/python-design-patterns/SKILL.md` |
| `zread` | 代码库结构化提取为本地 Wiki 文档与架构鸟瞰 | `sh-standby-skills/zread/SKILL.md` |

---

## 资产运维与双向迁移

本仓库配有双向自动化同步工具 `sync_standby_skills.py`（对齐 `sync_mattpocock_skills.py` 标准）：
- **状态检查**：`uv run sync_standby_skills.py --check`
- **一键收拢**：`uv run sync_standby_skills.py`
- **一键复原至根目录**：`uv run sync_standby_skills.py --restore`
- **JSON 探针输出**：`uv run sync_standby_skills.py --json`
