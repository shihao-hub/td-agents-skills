---
name: sh-mem0-skills
description: |
  Mem0 全域技能族分流路由器：集成 Mem0 官方 12 域原子能力。涵盖智能体跨会话长期记忆与检索（remember/search/status/forget/pause/resume）、核心 SDK 开发（Python/TS MemoryClient 与开源 Memory、LangChain/CrewAI/LangGraph 框架集成）、Vercel AI 适配、终端 CLI 运维（mem0 add/search/list）、以及仓库 TDD 目标集成与冒烟测试。按用户意图精准分流加载对应子模块。点名使用。
version: 1.0.0
created: 2026-10-27
updated: 2026-10-27
---

# sh-mem0-skills: Mem0 全域技能族与动态分流路由器

> **定位声明**：本技能是 Mem0 官方智能体记忆生态（GitHub: `mem0ai/mem0`）的本地归集与动态分流总枢纽。
> **核心契约**：将官方全部 12 个散装原子技能完整收纳于 `sh-mem0-skills/` 绝缘目录中。通过单一入口按需加载子模块，彻底消除 `remember`、`search`、`status`、`forget` 等通用词对全局 Prompt 与其他技能的关键词污染与误触发。

---

## 一、交互式分流协议（Ask Mem0 Interactive Protocol）

当用户唤起本技能时，AI 必须严格按以下两个场景执行：

### 场景 A：裸呼叫（用户未指定明确任务或仅呼叫 `/sh-mem0-skills`）

AI 必须**主动询问用户想要做什么？**，并按照 4 大功能维度给出清晰的选项指引：

> 💡 **请问您当前需要使用 Mem0 执行什么任务？**
>
> 1. 🧠 **智能体日常记忆交互（Agent Memory Lifecycle）**：
>    - `remember`：主动记住开发偏好、架构决策与事实（`/remember <内容>`）
>    - `search`：检索以往会话中的历史记忆与决策上下文（`/search <关键词>`）
>    - `status`：检查当前仓库/机器的 Mem0 记忆层工作状态与 API Key（`/status`）
>    - `forget`：遗忘或清空特定记忆 / 当前仓库记忆（`/forget`）
>    - `pause` / `resume`：临时暂停或恢复记忆捕获（隐私模式 / 敏感实验）
> 2. 💻 **应用开发与 SDK 编程（SDK & Frameworks）**：
>    - `mem0`：Python/TypeScript 核心 SDK 指南（Platform `MemoryClient` 与开源自托管 `Memory`，覆盖 LangChain, CrewAI, AutoGen, LangGraph, LlamaIndex 等集成）
>    - `mem0-vercel-ai-sdk`：Vercel AI SDK 适配器集成（`@mem0/vercel-ai-provider`、`createMem0`）
> 3. 🖥️ **命令行终端运维（CLI Tools）**：
>    - `mem0-cli`：终端 CLI 工具操作（`mem0 add`, `mem0 search`, `mem0 list`, `mem0 get`, `mem0 init`, `mem0 config`）
> 4. 🏗️ **工程集成与迁移验证（Repo Integration & Migration）**：
>    - `mem0-integrate`：通过目标驱动的 TDD 红绿流程为当前代码库自动化集成 Mem0
>    - `mem0-test-integration`：对已集成的 Mem0 代码执行自动化冒烟测试与校验评分
>    - `mem0-oss-to-platform`：将项目从开源本地自托管（`Memory`）平滑迁移至托管平台（`MemoryClient`）

---

### 场景 B：带意图呼叫（用户已输入具体需求，如 `帮我记住这个配置` 或 `在项目里集成 mem0`）

1. **意图匹配**：AI 对照下方的 [12 域能力路由速查表](#二12-域能力路由速查表) 与 [消歧决策指南](#三消歧决策指南) 定位最匹配的子技能；
2. **加载子模块**：通过文件读取工具读取对应的 `sh-mem0-skills/<subskill>/SKILL.md`；
3. **遵循执行**：严格按照官方子技能定义的流程、上下文规则与产出格式协助用户完成任务。

---

## 二、12 域能力路由速查表

全量 12 个子技能均已收纳在 `sh-mem0-skills/` 子目录中：

| 业务域分类 | 技能名称 | 核心职责与触发场景 | 子模块路径 |
| :--- | :--- | :--- | :--- |
| **日常记忆交互** | `remember` | 主动捕获并确认保存用户的偏好、规范或技术决定，供未来跨会话复用 | `sh-mem0-skills/remember/SKILL.md` |
| **日常记忆交互** | `search` | 搜索以前会话存入的记忆，避免重复阅读文件、搜索或重复实验 | `sh-mem0-skills/search/SKILL.md` |
| **日常记忆交互** | `status` | 检查 Mem0 在当前仓库的配置、捕获状态、待刷新队列及 API Key 是否有效 | `sh-mem0-skills/status/SKILL.md` |
| **日常记忆交互** | `forget` | 清除或擦除存储在当前仓库/用户维度的 Mem0 记忆条目 | `sh-mem0-skills/forget/SKILL.md` |
| **日常记忆交互** | `pause` | 暂停本地机器的 Mem0 记忆捕获（适用于涉密排查或一次性脏实验） | `sh-mem0-skills/pause/SKILL.md` |
| **日常记忆交互** | `resume` | 恢复此前被暂停的 Mem0 记忆捕获 | `sh-mem0-skills/resume/SKILL.md` |
| **核心 SDK 开发** | `mem0` | 默认 SDK 技能：Python/TS 客户端用法、多 Agent 框架集成及开源 Memory 选型 | `sh-mem0-skills/mem0/SKILL.md` |
| **核心 SDK 开发** | `mem0-vercel-ai-sdk` | Next.js 与 Vercel AI SDK 专用：`generateText` / `streamText` 语义记忆适配 | `sh-mem0-skills/mem0-vercel-ai-sdk/SKILL.md` |
| **命令行运维** | `mem0-cli` | 终端 Shell 脚本与命令行运维操作（查询、新增、配置与批量导入导出） | `sh-mem0-skills/mem0-cli/SKILL.md` |
| **工程集成迁移** | `mem0-integrate` | 针对当前仓库语言自动探测，以 TDD 编写测试先行的方式植入 Mem0 依赖与逻辑 | `sh-mem0-skills/mem0-integrate/SKILL.md` |
| **工程集成迁移** | `mem0-test-integration` | 配合 `mem0-integrate` 执行本地测试套件与端到端冒烟验证，输出集成计分卡 | `sh-mem0-skills/mem0-test-integration/SKILL.md` |
| **工程集成迁移** | `mem0-oss-to-platform` | 架构演进：从本地 Qdrant/向量存储配置迁移至官方云端托管平台 API | `sh-mem0-skills/mem0-oss-to-platform/SKILL.md` |

---

## 三、消歧决策指南

| 场景需求 | 推荐子模块 | 区分依据与排除理由 |
| :--- | :--- | :--- |
| **日常对话记偏好 vs 业务代码集成** | `remember` vs `mem0` / `mem0-integrate` | 若是当前对话让 AI 助手记住“以后写代码请遵循 X 规范”，走 `remember`；若是在当前代码库里编写调用 Mem0 API 的业务逻辑，走 `mem0` 或 `mem0-integrate`。 |
| **终端命令行快速调试 vs 应用程序开发** | `mem0-cli` vs `mem0` | 若需要在终端跑 bash/PowerShell 命令（如 `mem0 list --user-id 123`），走 `mem0-cli`；若是写 Python/TS 模块代码，走 `mem0`。 |
| **Vercel AI SDK 栈 vs 通用 Agent 框架** | `mem0-vercel-ai-sdk` vs `mem0` | Next.js 或使用 `@ai-sdk`、`generateText` 项目走 `mem0-vercel-ai-sdk`；LangChain、CrewAI、LlamaIndex 或原生 SDK 走 `mem0`。 |
| **新集成开发 vs 自托管上云迁移** | `mem0-integrate` vs `mem0-oss-to-platform` | 项目原本没有 Mem0 需从零加入走 `mem0-integrate`；项目已在使用本地 `Memory` 类与自建向量数据库，需切换为 `MemoryClient` 云端平台走 `mem0-oss-to-platform`。 |
| **敏感工作防记录 vs 彻底删除记忆** | `pause` vs `forget` | 只是当次临时做实验不想污染长期上下文走 `pause`（后续可 `resume`）；彻底销毁已有历史记忆数据走 `forget`。 |

---

## 四、资产同步与生命周期治理协议

本技能配套自动化同步与双向迁移脚本 [sync_mem0_skills.py](file:///D:/Users/language_projects/.agents/skills/sync_mem0_skills.py)：

```powershell
# 1. 执行收割迁移（将根目录散装 mem0 技能收拢入 sh-mem0-skills/）：
python sync_mem0_skills.py

# 2. 检查当前散装与收拢状态诊断：
python sync_mem0_skills.py --check

# 3. 【一键复原】若官方发布了原生 suite，可随时将子技能还原回根目录：
python sync_mem0_skills.py --restore
```
