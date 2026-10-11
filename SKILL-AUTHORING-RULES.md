---
name: skill-authoring-rules
description: |
  技能与知识库创作总规范（三卷合一 Single Source of Truth）：涵盖公共根级技能与族路由器（卷一：目录/命名正则/1-1024字符description预算/点名与主动触发红线/evals）、个人收敛子技能（卷二：sh-user-skills/README.md防探测落位/双表结构/SOP编写/分流器登记与回填闭环）、以及工程实战避坑知识库（卷三：kb-*/0N-*.md两级渐进式感知/Type A排障与Type B流水线双轨结构/外部自治解耦/转正清单）。当新建或改造任何根级技能、族路由器、个人子技能、或沉淀排障流水线知识库条目时，必须严格查阅并遵循本规范。
version: 2.0.0
created: 2026-10-07
updated: 2026-10-11
---

# SKILL-AUTHORING-RULES：技能与工程知识库创作总规范

> **单一真理来源（Single Source of Truth）声明**：  
> 本文件为技能仓库（`~/.agents/skills/`）的**唯一权威创作与维护总规范**。统合了历史上的公共技能规则、个人子技能规则以及工程知识库协议。  
> 核心目标：**在海量技能（50+）与持续生长的排障手记场景下，严守全局 System Prompt 预算，杜绝模型认知冲突与误触发，保证高频工作流的确定性执行。**

---

## 〇、机制先行：Harness 注册机制与落位分诊

动手前先确认落位，放错地方要么技能失效，要么将全局 Prompt 预算烧穿或引起模型幻觉：

| 物理落位形态 | 是否被 Harness 注册为全局技能 | 定位与适用场景 | 对应规范章节 |
|---|:---:|---|---|
| `~/.agents/skills/<name>/SKILL.md` | ✅ | **公共根级技能 / 族路由器**：高频全局入口（如 `sh-user-skills`、`sh-lark-skills`、`sh-redis-skills`、`sh-agy-skills`） | **卷一** |
| `~/.agents/skills/SKILL-<NAME>.md`（根散装文件 + frontmatter） | ✅ | **系统治理类单文件技能**（本文件 `SKILL-AUTHORING-RULES.md` 即属于此形态） | **卷一** |
| `~/.agents/skills/sh-user-skills/<name>/README.md` | ❌ | **个人沉淀类子技能**：通过 `README.md` 命名避开全局自动扫描，由 `sh-user-skills` 按需通过 `view_file` 调入 | **卷二** |
| `~/.agents/skills/<kb-dir>/0N-*.md`（知识库条目） | ❌ | **隐形技能 / 实战手记**：单点深度排障或工程实现，自带合规 frontmatter 但不命名为 `SKILL.md`，靠 `SKILL-DRAFT.md` 动态索引 | **卷三** |
| `<kb-dir>/SKILL-DRAFT.md` | ❌ | **知识库母版 / 动态路由表**：草稿与二级分流器，转正时 `git mv` 为 `SKILL.md` | **卷三** |
| 根目录下无 frontmatter 的 `.md`（`GUIDE-*`、`plans-*`） | ❌ | **纯文档与历史规划记事**：不参与任何技能注册 | - |

### 🎯 落位三步分诊法
1. **这是公共族路由器或全局核心枢纽吗？**  
   👉 **是**：进入 **卷一**，建立 `<name>/SKILL.md`。
2. **这是个人高频业务 SOP 或专属工作流，但无需污染每个日常会话吗？**  
   👉 **是**：进入 **卷二**，收敛在 `sh-user-skills/<name>/README.md`，并在总分流器登记。
3. **这是针对特定报错、环境底层机制或自动化排版流水线的实战手记/避坑指南吗？**  
   👉 **是**：进入 **卷三**，按 `0N-*.md` 规整入 `kb-engineering-notes/`，绝不常驻全局。

---

## 卷一：公共根级技能与族路由器规范

本卷约束位于 `~/.agents/skills/<name>/SKILL.md` 的全局根级技能及 `sh-*-skills` 族路由器。

### 1. 物理约束与硬红线
- **目录结构**：`~/.agents/skills/<name>/SKILL.md`，Harness 仅扫描此层，嵌套子目录不自动发现。
- **命名规范**：目录名与 `name` 严格一致，纯小写字母数字与单连字符，正则 `^[a-z0-9]+(-[a-z0-9]+)*$`。
- **description 预算红线**：**1~1024 字符**。超限即被 Harness 截断并报错 `[Skill conflicts] ... exceeds 1024 characters`，导致尾部技能在全局 Prompt 中失联。
- **多端同步规范**：仅在 `D:\Users\language_projects\.agents\skills` 编辑；其他客户端目录（如 `~/.config/opencode/skills`、`~/.claude/skills`）为 Junction 软链，自动跟随，严禁多头修改。

### 2. description 编写标准
- **结构**：一句话功能语义（≤70 字符）+ 领域/性质前缀（如 `装机：`、`配置：`、`排障：`、`路由器：`）+ 核心关键词 + 结尾固定 `点名使用`。
- **反军备竞赛红线**：严禁出现“必须调用本技能”、“即使只说 X 也要使用”等对抗性提示词；严禁穷举同义词堆砌字数。
- **主动触发类（Auto）例外**：极少数需要 AI 自主根据上下文介入的方法论技能（如 `sh-backend-design`），不写“点名使用”，但必须显式划清正反边界（“用户需要 X 时使用；Y 场景不使用”）。

### 3. 正文与评测
- 正文保持精炼（≤250 行），遵循 SOP 体或速查手册体；深度背景下沉至 `references/`，辅助脚本放 `scripts/`。
- 评测必须编写任务式用例 `evals/evals.json`，只测任务完成效果，不测触发率断言。

---

## 卷二：个人沉淀类子技能创作规范（sh-user-skills）

本卷约束收敛在 `D:\Users\language_projects\.agents\skills\sh-user-skills/` 体系下的所有子技能。

### 1. 核心机制：以 `README.md` 绝缘全局探测
- **子技能入口**：`sh-user-skills/<name>/README.md`。**严禁命名为 `SKILL.md`**。
- **激活模式**：仅供用户点名或经 `sh-user-skills` 语义分流命中后，由 AI 借助 `view_file` 按需读入执行，执行完毕即释放，永不占用常驻上下文。

### 2. 子技能 README.md 标准结构
顶部必须包含完整 YAML frontmatter：
```yaml
---
name: sh-<name>
description: 一句话功能语义，结尾固定点名使用。点名使用
version: 1.0.0
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```
正文标准要素：
- **版本与来源对照**；
- **前置检查与环境准备**；
- **分步执行 SOP**（命令原子化、可直接复用、步骤带校验）；
- **常见踩坑与回滚指南**。

### 3. 顶层分流器登记与闭环回填（SOP）
新建或调整个人子技能时，**必须执行四步闭环**：
1. **新建目录与文件**：创建 `sh-user-skills/<name>/README.md`，脚本入 `scripts/`，长文档入 `references/`。
2. **总控表格登记**：在 `sh-user-skills/SKILL.md` 的对应分类表格追加一行 `| <name> | <一句话职责> |`。
3. **口语映射补全**：在 `### 🗣️ 口语说法 -> 技能速查` 表格中补充典型的自然语言提问模式。
4. **1024 字符校验与闭环回填**：若新技能引入了全新的业务领域，在顶层 description 对应分组补词，并执行 PowerShell 脚本实测验证字符数严格 `≤ 1024`：
   ```powershell
   $raw = Get-Content -Encoding UTF8 "D:\Users\language_projects\.agents\skills\sh-user-skills\SKILL.md" -Raw
   ([regex]::Match($raw, '(?ms)^description: \|?\r?\n(.*?)^version:').Groups[1].Value).Length
   ```

---

## 卷三：工程实战避坑知识库规范（kb-engineering-notes）

本卷约束 `kb-engineering-notes/` 及其同类隐形工程知识库的建设与扩充。

### 1. 两级渐进式感知架构
为防止数十篇长篇排障文档撑爆上下文，知识库实行两级感知：
1. **第一级（权威路由）**：`kb-engineering-notes/SKILL-DRAFT.md`，维护唯一的「问题/症状/报错关键词 -> 对应编号条目」映射表。
2. **第二级（专项条目）**：`0N-*.md` 编号条目，每个条目针对单点技术痛点，AI 命中后使用 `view_file` 单篇加载。

### 2. 双轨条目结构规范
所有手记条目命名为 `0N-目标技术核心问题与解决目标.md`，编号顺延，且必须具备合规 frontmatter（`name: kb-<topic>`，不带序号，供未来转正）。正文严格执行双轨四段论：

- **Type A：疑难排障型条目**：
  1. `一、现象与报错直击`（贴出真实终端错误文本、exit code 或 UI 截图）；
  2. `二、底层根因剖析`（讲透操作系统句柄锁、并发冲突、协议不兼容等机制）；
  3. `三、标准抢救与修复 SOP`（原子化步骤、直接可贴命令）；
  4. `四、验证与防复发闭环`（检查命令、规避建议）。
- **Type B：方案与生成流水线型条目**：
  1. `一、业务场景与生成需求`（输入源、生成目标与最终交付格式）；
  2. `二、排版/技术难点与底层剖析`（底层引擎机制、XML/编码规范）；
  3. `三、标准自动化流水线与代码实现`（可复用完整脚本骨架）；
  4. `四、交付验证与扩展建议`（校验断言、复用 SOP）。

### 3. 外部自治与解耦原则（核心契约）
- **独立生长**：知识库为**完全自洽索引**体系，全量索引唯一维护在内部 `SKILL-DRAFT.md`。
- **严禁向外耦合**：外部路由器（如 `sh-engineering-notes` 及顶层 `sh-user-skills`）统一采用领域定性描述，**严禁绑定条目总数或静态区间（如禁止写“38项”、“01~38”）**。
- **新增条目免更新父级**：日常开发追加 `0N-*.md` 时，只需更新内部 `SKILL-DRAFT.md` 路由表，无需向上修改任何父级技能文件。

### 4. 转正清单（条目独立为正式全局技能时）
当某篇手记被频繁呼叫，需要转正为全局可调用的独立技能时：
1. 新建 `<name>/` 目录，将条目改名为该目录下的 `SKILL.md`；
2. 按卷一规范重写 description（≤70 字符，点名触发式）；
3. 从知识库 `SKILL-DRAFT.md` 路由表中摘除该条目；
4. 若整库转正，执行 `git mv kb-engineering-notes/SKILL-DRAFT.md kb-engineering-notes/SKILL.md`。

---

## 附录：创作合规性检查清单（Checklist）

新建或修改任何技能/手记前，逐项勾选确认：
- [ ] 属于哪一类？（卷一根级 / 卷二个人子技能 / 卷三知识库手记）
- [ ] 命名是否符合对应正则？（根级 `^[a-z0-9-]+$`；用户技能 `^sh-[a-z0-9-]+$`；知识库 `0N-*.md`）
- [ ] 引导文件名是否正确？（根级 `SKILL.md`；个人技能 `README.md`；知识库 `SKILL-DRAFT.md`）
- [ ] description 是否存在军备竞赛词或冗余列表？
- [ ] 顶层 `sh-user-skills/SKILL.md` 的 description 字符数是否严格 `≤ 1024`？
- [ ] 是否违反了知识库外部解耦原则（有无写死条目数）？
- [ ] 关联测试/执行命令是否已经过真实环境验证？
