# sh-user-skills 子技能创作规范（USER SKILL AUTHORING RULES）

> 本文件是后续新建/维护个人沉淀类技能（收敛于 `sh-user-skills` 体系内）的**强制规范**。  
> **核心原则**：所有个人技能统一归拢在 `sh-user-skills/` 内部管理，核心指导文件使用 `README.md` 别名，**彻底屏蔽 Agent 的递归自动探测**，仅通过顶层总分流器按需调度。

---

## 一、硬约束（收敛与防探测机制）

| 约束项 | 内容与要求 |
|---|---|
| **存放路径** | `~/.agents/skills/sh-user-skills/<name>/`，一律禁止散落在 `~/.agents/skills/` 根目录 |
| **指导文件名** | **必须为 `README.md`，严禁命名为 `SKILL.md`**（防止 Agent 递归扫描在全局会话 Prompt 中误注册） |
| **目录命名** | 目录名即技能名，正则 `^sh-[a-z0-9]+(-[a-z0-9]+)*$`（必须以 `sh-` 开头，纯小写字母数字+单连字符） |
| **顶层路由器登记** | **强制同步**：新建技能后，必须在 `sh-user-skills/SKILL.md` 的对应场景分类表格中追加登记一行 |
| **加载模式** | 仅供用户点名或经 `sh-user-skills` 意图匹配后，由 AI 通过 `view_file` 按需读取执行，无需也无法全局常驻 |

---

## 二、README.md 结构与 Description 规范

子技能的 `README.md` 顶部必须保留完整的 YAML frontmatter，便于分流器提取元数据：

```yaml
---
name: sh-example-name
description: 一句话功能语义，结尾固定点名使用。点名使用
version: 1.0.0
created: 2026-10-07
updated: 2026-10-07
---
```

### description 规范（核心）
1. **一句话功能语义**：目标 ≤70 字符（简明概括解决什么问题、产出什么结果）；
2. **性质前缀**：装机类 `装机：`、配置类 `配置：`、排障类 `排障：`；任务/工程类不加前缀，直接动词短语开头；
3. **保留核心关键词**：任务类保留任务语义（如“去水印/提取原图”），排障类保留症状词（如“401/内存溢出/无声”）；
4. **结尾固定**：必须以 `点名使用` 结尾；
5. **严禁**：穷举触发词、使用“必须使用本技能”等对抗性指令。

---

## 三、正文结构与资源组织

- **正文精炼（≤250 行）**：
  - 优先采用“可从头到尾逐步执行”的 **SOP 体**（步骤清晰、先检查后执行、附验证命令）；
  - 或“即查即用”的 **速查手册体**。
- **资源分层（就近存放）**：
  - `sh-user-skills/<name>/references/`：长篇背景文档、原理解析、坑位速查（按需加载，不占首屏上下文）；
  - `sh-user-skills/<name>/scripts/`：可执行的 Python/PowerShell/Shell 辅助脚本；
  - `sh-user-skills/<name>/evals/evals.json`：评测用例（任务描述 + 预期输出）。

---

## 四、新建子技能完整标准流程（SOP）

当用户要求“把某能力沉淀为 skill”或“新建一个个人 skill”时，必须严格执行以下四步：

1. **Step 1: 创建子技能目录与核心文件**
   - 创建目录 `D:\Users\language_projects\.agents\skills\sh-user-skills/<name>/`；
   - 编写 `README.md`（包含合规 frontmatter 与精炼正文）。
2. **Step 2: 组织脚本与支撑材料（如有）**
   - 如有辅助代码，放入子目录下的 `scripts/`；
   - 如有长篇原理，放入 `references/`。
3. **Step 3: 顶层分流器登记（不可遗漏）**
   - 编辑 `D:\Users\language_projects\.agents\skills\sh-user-skills/SKILL.md`；
   - 评估技能所属领域（装机配置、系统排障、工程开发、技能文档、多媒体检索）；
   - 在对应表格中追加一行：`| <name> | <一句话功能职责> |`。
4. **Step 4: 提交与推送**
   - 在 `D:\Users\language_projects\.agents\skills` 执行 `git add sh-user-skills/`；
   - 提交符合规范的 commit 并 push 到远程仓库。
