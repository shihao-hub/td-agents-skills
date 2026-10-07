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
| **顶层路由器 description** | `sh-user-skills/SKILL.md` 的 description 是**唯一常驻全局 prompt 的分流入口**：硬上限 1024 字符，只写「按场景分组的关键词/症状词」，**禁止罗列子技能名清单**（见第二节·补） |

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

## 二·补、顶层分流器 description 规范（防截断，2026-10-07 新增）

分流器的 description 是**唯一常驻每个会话的全局路由入口**（子技能用 `README.md` 存，本就不出现在全局 prompt），因此它必须**同时满足两条**：不超限、关键词覆盖全。

1. **硬上限 1024 字符，改完必须实测**：

   ```powershell
   $f = "D:\Users\language_projects\.agents\skills\sh-user-skills\SKILL.md"
   $raw = Get-Content -Encoding UTF8 $f -Raw
   ([regex]::Match($raw, '(?ms)^description: \|\r?\n(.*?)^version:').Groups[1].Value).Length   # 必须 <= 1024
   ```

   超限的后果（实测）：harness 报 `[Skill conflicts] ... description exceeds 1024 characters` 并按 1024 截断——**尾部技能在全局 prompt 中直接失联**，自动分流退化为纯点名。历史上 2514 字符版本只放得下 20/52 个技能名。

2. **禁止罗列子技能名清单**：名字对中文口语匹配几乎无效（用户说“喇叭爆音”时 `sh-windows-audio-diagnose` 帮不上忙），却要占满预算；只写**用户会说的关键词/症状词**，按场景（装机与环境／排障／开发与重构／文档与交接／检索与媒资归档）分组。
3. **保留一条名字兜底子句**：`用户直接点名 sh-* 子技能（含拼写近似）时也由本入口解析`——保证点名路径不因去掉清单而失效；正文再配“目录名模糊匹配”兜底。
4. **口语说法对照表放正文**（`### 🗣️ 口语说法 → 技能速查`），不放 description：正文不占常驻预算，按需加载即可用。
5. **关键词回填闭环**：新建子技能时，若它引入了一个**既有分组关键词未覆盖**的新领域，必须回到分流器 description 的对应分组里补词；已覆盖则无需改动。

## 三、正文结构与资源组织

- **正文须含两张表**：场景分类表（技能名 → 一句话职责）+ 口语说法速查表（症状/口语 → 技能名）；
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
   - 在对应表格中追加一行：`| <name> | <一句话功能职责> |`；
   - 在“口语说法 → 技能速查”表中补一行该技能最可能被口语触发的说法；
   - 若新技能引入了既有分组关键词未覆盖的新领域，同步在 frontmatter description 的对应分组补关键词；
   - **校验**：description 仍 <= 1024 字符（见第二节·补的实测命令），且未混入子技能名清单。
4. **Step 4: 提交与推送**
   - 在 `D:\Users\language_projects\.agents\skills` 执行 `git add sh-user-skills/`；
   - 提交符合规范的 commit 并 push 到远程仓库（description 超限属规范违反，提交前必须已校验 <= 1024）。
