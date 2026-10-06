# Plan: sh-lark-skills 飞书全域技能族路由器与资产同步脚本

📋 Plan for: "收归 28 个官方散装 lark-* 技能至 sh-lark-skills 路由器，并编写自动化迁移与 AI 深度参与的协同同步机制"

## 问题陈述

`~/.agents/skills` 根目录下常驻 28 个官方 `lark-*` 技能，仅 frontmatter 的 `description` 即占用 5,848 字符（约 2,500+ tokens），无条件注入所有 Agent（Claude Code、Opencode、Codex、Gemini、Cursor 等）的 System Prompt，造成严重上下文浪费并增加误触发面。用户希望将这些官方技能移出根目录，收拢为单一顶层分流路由器 `sh-lark-skills`，同时保留各域 Schema 与 Reference 的完整性。

---

## 核心设计哲学：脚本归脚本，AI 归 AI（AI-in-the-Loop 闭环机制）

> 💡 **用户核心指导思想（2026-10-06 强化）**：  
> 「记得强化一下，因为那个自动更新的时候，一般是 AI 会提示我更新。如果官方新增了什么技能，或者说官方的套件技能彻底实现，那么那时候 AI 应该也能检测到。所以说，**你的脚本归脚本，但是归根结底，到时候还是需要 AI 参与的。**」

### 1. 职责边界与协作模型

| 维度 | 自动化脚本（肢体与防波堤） | AI Agent（感知中枢与大脑） |
| :--- | :--- | :--- |
| **定位** | 确定性操作、原子文件搬运、哈希校验、目录结构隔离 | 交互感知、意图理解、主动提醒、语义消歧、架构研判 |
| **优势** | 快速、无状态、跨平台、幂等执行、0 遗漏 | 拥有自然语言理解力、能读懂文档、能与用户人机对话 |
| **边界** | 机械执行，无法理解新技能是干什么的，无法自己做架构决策 | 归根结底的核心参与者，推动整个更新与维护闭环 |

### 2. 三大 AI 深度参与的关键场景

```text
               ┌────────────────────────────────────────────────────────┐
               │          1. AI 日常交互感知 (_notice.update / skills)   │
               └──────────────────────────┬─────────────────────────────┘
                                          │ 捕获到飞书 CLI 更新信号
                                          ▼
               ┌────────────────────────────────────────────────────────┐
               │         2. AI 主动向用户汇报，征求是否执行升级/收拢      │
               └──────────────────────────┬─────────────────────────────┘
                                          │ 用户批准授权
                                          ▼
               ┌────────────────────────────────────────────────────────┐
               │    3. AI 驱动执行脚本: python sync_lark_skills.py --json│
               │   (物理隔离散装、保留子结构、执行探针检测、输出结构化诊断) │
               └──────────────────────────┬─────────────────────────────┘
                                          │ 脚本输出变更诊断
                   ┌──────────────────────┴──────────────────────┐
                   ▼                                             ▼
       [场景 A: 官方新增独立域技能]                  [场景 B: 官方套件彻底成熟就绪]
  ┌─────────────────────────────────┐           ┌─────────────────────────────────┐
  │ • 脚本探针上报 [NEW DOMAIN]     │           │ • 脚本探针上报 [OFFICIAL SUITE] │
  │ • AI 深度阅读官方新增 Skill 文档 │           │ • AI 研判原生套件功能与上下文   │
  │ • AI 总结业务意图与消歧规则     │           │ • AI 向用户发起「平退官方」建议 │
  │ • AI 动态更新顶层 SKILL.md 路由 │           │ • 用户同意后 AI 辅助平滑切换    │
  └─────────────────────────────────┘           └─────────────────────────────────┘
```

- **场景 1：更新提示始于 AI（Update Awareness）**  
  官方 `lark-cli` 不会自动在后台修改磁盘，更新提示通常藏在 API 调用的 stderr/JSON 返回（如 `_notice.update`）。用户日常不会手动去跑检查命令。**AI 是整个更新闭环的起点**：AI 在日常对话中捕获到 notice 时，主动向用户汇报并提供升级选项。

- **场景 2：新技能的语义收割与路由自愈归于 AI（New Domain Semantic Ingestion）**  
  当官方版本新增了前所未见的业务域（如 `lark-ai-agent`、`lark-table` 等）时：
  1. 脚本负责底层的搬移与隔离，并在 `--json` / 报告中明确标注 `[NEW DOMAIN: <name>]`；
  2. **AI 必须参与**：AI 深入阅读新技能的 `SKILL.md` 和 references 文档，理解其功能定位，用高度精炼的一句话提炼其路由特征与消歧规则，追加写入 `sh-lark-skills/SKILL.md` 的路由表中，实现路由系统的自主演进。

- **场景 3：官方原生套件就绪的研判与平退归于 AI（Official Suite Readiness Evaluation）**  
  如果未来官方版本彻底实现了集成式套件（Native Lark Suite），消除了散装 28 个技能的臃肿问题：
  1. 脚本探针检测到 `[OFFICIAL SUITE READY]`；
  2. **AI 必须参与**：AI 负责对比评估官方原生套件与自建路由器的能力差异、上下文占用以及平替可行性，主动向用户提交评估建议。在用户批准后，AI 负责协同退役自研路由层，无痛回归官方原生。

---

## 需求（含用户原话决策）

- **统一路由器命名**：`sh-lark-skills`（用户决策：`1=sh-lark-skills`）
- **内部组织结构**：完整保留子模块独立结构（用户决策：`2=a`），采用 `sh-agy-skills` 风格，各域如 `sh-lark-skills/lark-im/` 拥有完整自治的 `SKILL.md` 与 `references/`，顶层仅负责分流引导
- **自动化同步机制**：独立脚本 `sync_lark_skills.py`（用户决策：`3=a`），并在 `sync_skills.bat` 中支持一键联动，自动识别官方散装目录、转移/更新至路由器内部、自动维护路由索引并清理根目录
- **个人自研飞书技能**：`sh-lark-chat-archive` 与 `sh-lark-session-doc` 保持作为独立 `sh-*` 技能留在根目录（用户决策：`1=a`），顶层路由表将其作为生态工具建立联动索引
- **人机协同与 AI 深度参与（强化决策）**：
  - 同步脚本必须提供结构化接口（`--json`）以及人机两用诊断报告，便于 AI 机器读取与解析；
  - 路由器 `sh-lark-skills/SKILL.md` 必须内置《AI 维护与生命周期治理协议 (For Agent)》，指导未来所有接入的 AI 无论在哪个终端都能读懂并执行这套更新协作闭环。
- **多 Agent 兼容**：确保 `sync_skills.py` 正确处理 Codex 的 per-skill junction 以及 Claude/Opencode/Gemini/Cursor 的全局目录 junction

---

## 背景与现况

- `~/.agents/skills` 是唯一真实源，也是 Git 仓库（`git@github.com:shihao-hub/td-agents-skills.git`）
- Agent 扫描机制（依 `SKILL-AUTHORING-RULES.md`）：仅扫描 `~/.agents/skills/<name>/SKILL.md` 顶层第一层目录，嵌套子目录（如 `sh-lark-skills/lark-im/`）不会被注册为全局技能。将 28 个散装目录移入子目录后，Agent 视野内仅剩单个 `sh-lark-skills`，Prompt 字符数从 5,848 骤降至 ~60 字符
- 官方 `lark-cli` 行为：日常运行命令只报 notice，不写磁盘；更新通常由 AI 在看到 notice 后发起提示。当运行 `lark-cli update` 重新释放官方 skill 时，由 AI 执行同步脚本实现无痛收割与演进

---

## 方案设计

### 1. 目录架构

```text
~/.agents/skills/
├── sh-lark-skills/                      # 顶层唯一暴露的飞书技能
│   ├── SKILL.md                         # 路由入口、28 域分流表、消歧规则、AI 维护协议 (For Agent)
│   ├── lark-approval/                   # 完整保留官方 approval 域
│   │   ├── SKILL.md
│   │   └── references/
│   ├── lark-im/                         # 完整保留官方 im 域
│   │   ├── SKILL.md
│   │   └── references/
│   ├── ...                              # 其余 26 个官方域
│   └── lark-workflow-standup-report/
├── sh-lark-chat-archive/                # 用户自研技能（保留在根目录）
├── sh-lark-session-doc/                 # 用户自研技能（保留在根目录）
├── sync_lark_skills.py                  # 飞书技能迁移、AI 探针感知与防刷同步器
├── sync_skills.py                       # 多 Agent 分发同步器（更新 Codex 映射）
└── sync_skills.bat                      # 一键自动化脚本
```

### 2. 脚本 `sync_lark_skills.py` 增强设计（AI 友好型设计）

1. **动态识别官方组件**：
   - 读取 `~/.lark-cli/skills-state.json` 的 `official_skills` 列表，动态与根目录目录匹配，严格忽略 `sh-*`。
2. **迁移与增量覆盖**：
   - 转移或覆盖更新至 `sh-lark-skills/lark-*`，确保升级带来的最新 reference 文件被同步。
   - 清理根目录已同步成功的官方散装目录。
3. **AI 专属感知探针（面向 AI 解析设计）**：
   - **新增 Domain 检测**：若发现官方新增了之前未见过的业务域（如 `lark-xx`），输出 `[NEW DOMAIN: lark-xx]`，并在 `--json` 输出中包含该 domain 的基本路径，提示 AI 介入阅读并提炼路由。
   - **官方原生 suite 就绪探针**：检查根目录或 `lark-cli` 是否已经实现或释放了官方原生集成套件（如 `lark-suite`、`lark-all` 或在 config 中声明套件已完备），输出 `[OFFICIAL SUITE READY]`，提示 AI 协助用户决策是否切换回官方原生。
4. **自动化路由表校验与辅助更新**：
   - 提供 `--check` 和 `--refresh-table` 选项，抽取内部各子模块的 description，辅助校验 `sh-lark-skills/SKILL.md` 的路由表完整性。
5. **多模式输出**：
   - `--dry-run`：预览将要发生的操作，不修改任何文件；
   - `--check`：仅检查状态，返回当前散装残留、新增域、套件就绪情况；
   - `--json`：输出结构化 JSON，供任何接入的 AI Agent 零正则直接解析。

### 3. `sh-lark-skills/SKILL.md` 维护协议（For Agent）设计

在顶层 `SKILL.md` 中专门规划「AI 维护协议（For Agent）」专章，向后续所有接手的 AI 明确工作流规范：
- **触发与感知**：当 AI 在任何命令输出中捕获 `_notice.update` / `_notice.skills` 时，告知用户可执行升级。
- **升级后动作**：执行 `lark-cli update` 后，AI 应紧随其后运行 `python sync_lark_skills.py --json`，并根据探针反馈执行后续动作：
  - 若有 `new_domains`：AI 主动读取新域的 `SKILL.md`，将意图总结并写入顶层路由表；
  - 若有 `official_suite_ready`：AI 主动向用户发起切换可行性评估报告；
- **演进路线与生命周期管理**：若某天官方原生套件成熟稳定，指导 AI 如何向用户汇报并平滑过渡，避免路由工具变成遗留死代码。

---

## 任务分解

- [ ] Task 1: 编写 `sync_lark_skills.py` 资产迁移、探针诊断与 AI 友好同步脚本
  - 文件：`C:/Users/29580/.gemini/config/skills/sync_lark_skills.py`
  - 实现：官方 skill 动态识别、覆盖迁移、根目录清理、新增 Domain 诊断、官方原生 suite 探针、`--dry-run` / `--check` / `--status` / `--json` 支持
  - 验证：运行 `python sync_lark_skills.py --dry-run`，准确预览 28 个官方 skill 的迁移计划，0 误伤 `sh-lark-*`，并给出当前无新增域与原生 suite 探测结果
  - Demo：终端展示对 AI 友好的格式化分析预览报告与 `--json` 数据流

- [ ] Task 2: 执行全量迁移并构建含「AI 深度协同协议」的 `sh-lark-skills/SKILL.md`
  - 文件：
    - `C:/Users/29580/.gemini/config/skills/sh-lark-skills/SKILL.md`
    - `C:/Users/29580/.gemini/config/skills/sh-lark-skills/lark-*/`（28个子目录）
  - 实现：执行 `python sync_lark_skills.py` 完成物理移动；编写高质量 `sh-lark-skills/SKILL.md`，包含 28 个域意图路由表、消歧规则、动态加载方式、自研技能联动、以及「AI 维护与演进协议（For Agent）」专章
  - 验证：运行 PowerShell 校验 `Get-ChildItem -Path $HOME\.agents\skills -Filter 'lark-*' -Directory` 为空；检查 `sh-lark-skills/SKILL.md` 结构完备且包含 AI 协议
  - Demo：根目录整洁清爽，`sh-lark-skills` 具备全域分流与自我维护指引

- [ ] Task 3: 适配 `sync_skills.py` 与 `sync_skills.bat` 联动
  - 文件：
    - `C:/Users/29580/.gemini/config/skills/sync_skills.py`
    - `C:/Users/29580/.gemini/config/skills/sync_skills.bat`
  - 实现：在 `sync_skills.bat` 中加入 `sync_lark_skills.py` 调用；运行 `sync_skills.py` 刷新 Codex per-skill junctions（移除已失效的 28 个独立 link，新增 `sh-lark-skills` junction）
  - 验证：运行 `sync_skills.bat`，所有 agent 均成功同步，Codex 目录下仅有 `sh-lark-skills` 而无散装失效 junction
  - Demo：运行批处理一键完成资产收割与多 agent 软链分发

- [ ] Task 4: 端到端功能校验、模拟更新演练与 AI 参与闭环演练
  - 文件：所有相关文件
  - 实现：
    1. 检查 Agent 识别到的 skills 列表；模拟分流读取子模块 `sh-lark-skills/lark-im/SKILL.md`；
    2. 模拟创建一个伪官方目录 `lark-test-domain` 触发同步脚本，验证脚本的新增域捕获、`--json` 输出以及 AI 认知更新闭环；
    3. 模拟官方原生套件探针触发逻辑，验证探针告警与 AI 汇报机制；
    4. 再次运行验证幂等性。
  - 验证：全局 skills 列表仅有 `sh-lark-skills`；脚本与探针准确工作；AI 参与链路完备；幂等性 100% 达标
  - Demo：全链路闭环演练成功

---
**最后更新：** 2026-10-06  
**作者：** AI & User  
**版本：** v1.2.0 (已根据用户指导强化「脚本归脚本，AI 归 AI」深度协同与探针闭环)
