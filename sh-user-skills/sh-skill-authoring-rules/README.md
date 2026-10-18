---
name: sh-skill-authoring-rules
description: |
  技能与知识库创作总规范（三卷合一 Single Source of Truth）：涵盖公共根级技能与族路由器（卷一：目录/命名正则/1-1024字符description预算/点名与主动触发红线/evals）、个人收敛子技能（卷二：sh-user-skills/README.md防探测落位/双表结构/SOP编写/分流器登记、回填闭环与提级暴露）、以及工程实战避坑知识库（卷三：kb-*/ID置顶五段式分面命名与时序解耦/Type A与Type B极简双轨/虚拟路径分层契约/外部自治解耦/转正清单）。当新建或改造任何根级技能、族路由器、个人子技能、或沉淀排障流水线知识库条目时，必须严格查阅并遵循本规范。
version: 2.5.0
created: 2026-10-07
updated: 2026-10-17
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
| `~/.agents/skills/sh-user-skills/<name>/README.md` | ❌ | **个人沉淀类子技能**：通过 `README.md` 命名避开全局自动扫描，由 `sh-user-skills` 按需通过 `view_file` 调入 | **卷二** |
| `~/.agents/skills/<name>/`（junction 链出，真身 `sh-user-skills/<name>/`） | ✅ | **提级暴露的子技能**：需进全局清单的高频/关键入口（如 `sh-plan-driven-development`、`kb-engineering-notes`、`sh-skill-authoring-rules`），用 `uv run expose_user_skill.py <name>` 生成，链接产物不入库 | **卷二·4** |
| `~/.agents/skills/<kb-dir>/<name>.md`（分面槽位/历史0N知识库条目） | ❌ | **隐形技能 / 实战手记**：单点深度排障或工程实现，自带合规 frontmatter 但不命名为 `SKILL.md`，靠 `SKILL.md` 动态索引 | **卷三** |
| `<kb-dir>/SKILL.md` | ❌ | **知识库母版 / 动态路由表**：草稿与二级分流器，转正时 `git mv` 为 `SKILL.md` | **卷三** |
| 根目录下无 frontmatter 的 `.md`（`GUIDE-*`、`plans-*`） | ❌ | **纯文档与历史规划记事**：不参与任何技能注册 | - |

### 🎯 落位三步分诊法
1. **这是公共族路由器或全局核心枢纽吗？**  
   👉 **是**：进入 **卷一**，建立 `<name>/SKILL.md`。
2. **这是个人高频业务 SOP 或专属工作流，但无需污染每个日常会话吗？**  
   👉 **是**：进入 **卷二**，收敛在 `sh-user-skills/<name>/README.md`，并在总分流器登记。
3. **这是针对特定报错、环境底层机制或自动化排版流水线的实战手记/避坑指南吗？**  
   👉 **是**：进入 **卷三**，按 ID 置顶五段式分面槽位规范规整入 `kb-engineering-notes/`，绝不常驻全局。

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
- **路由器与知识库入口例外（关键词集群形态）**：`sh-user-skills`、族路由器与知识库入口（如 `kb-engineering-notes`）不适用首款模板（显式豁免“≤70 字符 + 点名使用”结尾）；其 description 允许并鼓励采用「定位语 + 用户真实会说的症状词/报错词/工具名关键词集群 + 触发或兜底说明」形态，用于启发式分流与主动查阅，**不视为“同义词堆砌”**；反军备竞赛红线仍然有效（禁对抗性触发语、禁无信息量重复）。此类 description 还须满足：
  - 关键词密度优先，不写长句铺陈，只写用户可能原样说出的词；
  - 分流器保留“点名 `sh-*` 子技能（含拼写近似）兜底解析”条款；知识库入口写明“报出症状即优先查阅”的触发语（属主动触发类，不写“点名使用”）；
  - 严格 ≤1024 字符，并按卷二第 3 节命令实测校验；
  - 严禁绑定条目总数或静态编号区间（沿用卷三外部解耦原则）。

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

### 4. 提级暴露机制（expose_user_skill）

子技能默认隐形；当某技能需要进入全局技能清单（高频点名，或需要常驻关键词钩子，如知识库入口 `kb-engineering-notes`）时，在仓库根执行：

```powershell
uv run expose_user_skill.py <name> --check   # 预演
uv run expose_user_skill.py <name>           # 实跑
```

脚本把 `sh-user-skills/<name>/` 以链接方式暴露为根级 `~/.agents/skills/<name>/`：`README.md` 改名链出为 `SKILL.md`，其余内容原名链出；`.gitkeep` 与 `.gitignore` 占位入库，链接产物不入库。暴露后：

- 该技能 description 进入全局 prompt，此后遵守卷一对根级技能的全部约束（≤1024、关键词集群规范等）；
- 真身仍在 `sh-user-skills/<name>/`，**一切修改只动真身**；改后重跑脚本（`--check` 探测链接失联）；
- 已暴露位：`sh-plan-driven-development`、`sh-spec-driven-development`、`kb-engineering-notes`、`sh-skill-authoring-rules`。

---

## 卷三：工程实战避坑知识库规范（kb-engineering-notes）

本卷约束 `kb-engineering-notes/` 及其同类隐形工程知识库的建设与扩充。

### 1. 两级渐进式感知架构
为防止数十篇长篇排障文档撑爆上下文，知识库实行两级感知：
1. **第一级（权威路由）**：`kb-engineering-notes/SKILL.md`，维护唯一的「问题/症状/报错关键词 -> 对应编号条目」映射表。
2. **第二级（专项条目）**：编号条目文件，每个条目针对单点技术痛点，AI 命中后使用 `view_file` 单篇加载。

### 2. 双轨条目结构与 ID 置顶五段式分面槽位命名（ID-First Faceted Pattern）
知识库条目采用**ID 置顶五段式分面槽位命名**，使编辑器侧边栏与文件列表天然按单调递增顺号对齐：

```text
语法结构：<id>_<domain>_<scope>_<type>_<slug>.md
正则校验：^(?<id>\d{3})_(?<domain>[a-z]{2,8})_(?<scope>[a-z0-9]{2,8})_(?<type>fix|flow)_(?<slug>[^_\/\\:\*\?"<>\|]+)\.md$
```

- **槽位 1 `<id>`（逻辑时钟置顶与唯一 UID，彻底锁定顺号排序）**：
  `001` ~ `999` 定长 3 位，全局单调递增，永不回收复用。**ID 越大等价于条目创建时间越新，列表最底部永远是最新手记**。
- **槽位 2 `<domain>`（受控领域，严格 7 枚举，对齐未来一级物理子目录）**：
  `win`（Windows底层/软链接/注册表）、`git`（版本控制/变基/Worktree/提交）、`ide`（编辑器/终端/Sublime/Zed/Cursor/WT）、`agent`（AI客户端/CLI/模型供应商/密钥）、`browser`（浏览器/扩展/DevTools）、`dev`（语言/构建/uv/OOP/排版流水线/daemon）、`media`（音视频/下载/声学）。
- **槽位 3 `<scope>`（受控软件实体/技术范围，严禁留空，使同款软件自动聚类）**：
  - **受控兜底词**：`sys`（Windows系统功能）、`core`（跨软件基础模式/设计哲学）、`fs`（文件系统/Junction软链接/C盘空间/文件锁）、`cli`（通用命令行管道/守护进程）。
  - **常见软件实体**：`zed`、`cursor`、`vscode`、`sublime`、`smerge`、`terminal`、`terminus`、`atuin`、`pi`、`ahk`、`windhawk`、`everything`、`conhost`、`ps`、`uwp`、`mem`、`audio`、`uv`、`docx`、`wails`、`web`、`rebase`、`worktree`、`ssh`、`chrome`、`firefox`、`devtools`、`opencode`、`agy`、`agyman`、`dsh`、`ccswitch`、`yolo`、`alist` 等。
- **槽位 4 `<type>`（极简双轨制收敛，彻底废除 guide/cfg 等弱词）**：
  - **`fix`**：**Type A 疑难排障型条目**（报错直击、底层根因、抢救 SOP、防复发闭环验证）；
  - **`flow`**：**Type B 方案与流水线型条目**（业务场景输入输出、核心技术剖析、完整自动化脚本实现、交付验收断言）。原偏排错排障归 `fix`，偏全新自动化配置与生成流水线归 `flow`。
- **槽位 5 `<slug>`（自解释主题短语）**：
  `[核心问题/技术词] + [解决动作/交付物]`，剔除“指南/实战”等空洞后缀，中文 $\le 25$ 字符。

正文严格执行双轨四段论：
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

### 3. 平铺虚拟路径契约与四维时间顺序感知体系
1. **平铺虚拟路径契约**：
   - 平铺文件名 `<id>_<domain>_<scope>_<type>_<slug>.md` 实质为序列化的虚拟相对路径，与未来物理分层路径 `<domain>/<id>_<scope>_<type>_<slug>.md` 1:1 双向无损映射。
   - **分层演进触发阈值**：当条目总规模达到 150+ 篇或单一领域条目 $\ge 30$ 篇时触发物理下沉分层。
   - 配套工具 `scripts/organize_subdirs.ps1` 支持 `-ToSubdirs` 与 `-ToFlat` 双向秒级无损转换，自动全局替换 `SKILL.md` 超链接，Git blame 完整保留，0 代码断裂、0 引用重构成本。
2. **四维时间顺序感知体系**：
   - **维 1：侧边栏与文件系统原生排序（ID 置顶）**：任何工具按名称升序排列即绝对等价于按创建时间顺序排列，列表最底部即最新条目；
   - **维 2：Explorer 视窗切换**：想看最近修改按“修改日期”列头排序；
   - **维 3：YAML Frontmatter 时间锚点**：每篇条目固化 `created: YYYY-MM-DD` 与 `updated: YYYY-MM-DD`，跨机 checkout 物理防漂移；
   - **维 4：SKILL-DRAFT 时间线索引**：总控文件文末维护《条目时序演进检索表》，一屏通览生命周期。

### 4. 外部自治与解耦原则（核心契约）
- **独立生长**：知识库为**完全自洽索引**体系，全量索引唯一维护在内部 `SKILL.md`。
- **严禁向外耦合**：外部路由器（如 `kb-engineering-notes` 及顶层 `sh-user-skills`）统一采用领域定性描述，**严禁绑定条目总数或静态区间（如禁止写“38项”、“01~38”）**。
- **新增条目免更新父级**：日常开发追加条目时，只需更新内部 `SKILL.md` 路由表与时序演进检索表，无需向上修改任何父级技能文件。

### 5. 转正清单（条目独立为正式全局技能时）
当某篇手记被频繁呼叫，需要转正为全局可调用的独立技能时：
1. 新建 `<name>/` 目录，将条目改名为该目录下的 `SKILL.md`；
2. 按卷一规范重写 description（≤70 字符，点名触发式）；
3. 从知识库 `SKILL.md` 路由表中摘除该条目；
4. 若整库转正，执行 `git mv kb-engineering-notes/SKILL.md kb-engineering-notes/SKILL.md`。

---

## 附录：创作合规性检查清单（Checklist）

新建或修改任何技能/手记前，逐项勾选确认：
- [ ] 属于哪一类？（卷一根级 / 卷二个人子技能 / 卷三知识库手记）
- [ ] 命名是否符合对应正则？（根级 `^[a-z0-9-]+$`；用户技能 `^sh-[a-z0-9-]+$`；知识库 `<id>_<domain>_<scope>_<type>_<slug>.md` 或历史 `0N-*.md`）
- [ ] 引导文件名是否正确？（根级 `SKILL.md`；个人技能 `README.md`；知识库 `SKILL.md`）
- [ ] description 是否存在军备竞赛词或对抗性触发语？（路由器/知识库入口的关键词集群不视为“冗余列表”）
- [ ] 顶层 `sh-user-skills/SKILL.md` 的 description 字符数是否严格 `≤ 1024`？
- [ ] 是否违反了知识库外部解耦原则（有无写死条目数）？
- [ ] 关联测试/执行命令是否已经过真实环境验证？
