# Plan: sh-redis-skills Redis 与 Iris 全域技能族路由器与资产同步脚本

📋 Plan for: "收归 8 个官方散装 redis-* 与 iris-* 技能至 sh-redis-skills 路由器，并编写自动化迁移、一键复原与 AI 深度协同机制"

## 问题陈述

`~/.agents/skills` 根目录下常驻 8 个 Redis/Iris 官方最佳实践技能：
1. `iris-development` (Redis AI 智能体长短期记忆 RAM / 长期记忆 LTM / 会话事件流)
2. `redis-core` (核心数据结构选型 String/Hash/List/Set/ZSet/JSON/Vector Set 与键名规范)
3. `redis-connections` (连接池、管道、客户端缓存 RESP3、慢查询规避)
4. `redis-clustering` (集群分片、哈希标签 hash tags、跨槽规避、副本只读扩展)
5. `redis-search` (RediSearch 索引、FT.CREATE、混合向量检索、DIALECT 2)
6. `redis-security` (生产安全、ACL 细粒度权限、TLS 加密、危险命令禁用)
7. `redis-observability` (指标监控、SLOWLOG/INFO/MEMORY DOCTOR 故障排查)
8. `redis-semantic-cache` (LangCache 大模型语义缓存、相似度阈值调优)

仅这 8 个技能 frontmatter 的 `description` 就占用了 **3,808 字符（约 1,500+ tokens）**，无条件注入所有 Agent（Claude Code、Codex、Opencode、Gemini、Cursor 等）的 System Prompt。不仅造成巨大的提示词开销，而且日常普通编码时极易发生与常规数据库或缓存设计的误触发。

用户希望参照飞书技能路由器的成熟架构，将其移出根目录，收拢为统一顶层分流路由器 `sh-redis-skills`，同时保留各子模块的完整自治性。

---

## 核心设计哲学：脚本归脚本，AI 归 AI（AI-in-the-Loop 闭环）

> 💡 **用户核心指导思想**：  
> 「你的脚本归脚本，但是归根结底，到时候还是需要 AI 参与的。而且你要记住如何把那些技能复原，因为路由之后，我要测试的，不需要你测试，我会测试，然后要是不精准导致 skill 无法调用，我会继续让你优化。」

### 1. 职责边界与协作模型

| 维度 | 自动化脚本 `sync_redis_skills.py` (肢体与防波堤) | AI Agent (感知中枢与决策大脑) |
| :--- | :--- | :--- |
| **定位** | 确定性操作、原子文件搬运、根目录清理、双向一键复原(`--restore`)、结构化 JSON 输出 | 意图识别、精准消歧、文档解读、向用户主动提醒与汇报、持续优化路由规则 |
| **测试权** | 脚本只做确定性目录与探针自检 | **完全由用户亲自测试与验证**，AI 随时根据测试反馈优化消歧规则 |
| **复原保障**| 提供 `python sync_redis_skills.py --restore`，秒级无损移回根目录散装形态 | 铭记复原路径，若测试不满意支持随时一键回退并重新演进 |

### 2. 三大 AI 深度参与场景

```text
               ┌────────────────────────────────────────────────────────┐
               │           1. AI 日常交互感知 (Redis / 缓存相关意图)     │
               └──────────────────────────┬─────────────────────────────┘
                                          │ 触发分流路由
                                          ▼
               ┌────────────────────────────────────────────────────────┐
               │         2. 查阅 sh-redis-skills 路由表与消歧指南        │
               │        按需只读加载对应子模块 (如 redis-search/SKILL.md)│
               └──────────────────────────┬─────────────────────────────┘
                                          │ 遇到更新/新增
                   ┌──────────────────────┴──────────────────────┐
                   ▼                                             ▼
       [场景 A: 社区/官方新增子域技能]                [场景 B: 官方一体化套件就绪]
  ┌─────────────────────────────────┐           ┌─────────────────────────────────┐
  │ • 脚本探针上报 [NEW DOMAIN]     │           │ • 脚本探针上报 [OFFICIAL SUITE] │
  │ • AI 深度阅读新增 Skill 文档    │           │ • AI 研判原生套件功能与上下文   │
  │ • AI 总结业务意图与消歧规则     │           │ • AI 向用户发起「平退官方」建议 │
  │ • AI 动态更新顶层 SKILL.md 路由 │           │ • 用户同意后 AI 辅助平滑切换    │
  └─────────────────────────────────┘           └─────────────────────────────────┘
```

---

## 需求与设计决策

- **统一路由器命名**：`sh-redis-skills`（符合用户系统 `sh-*` 前缀规范，顶层统一管控 Redis 与 Iris）
- **内部组织结构**：完整保留 8 个子模块的原生目录结构与内部所有 `references/` / `SKILL.md`，采用自治嵌套风格：
  ```text
  ~/.agents/skills/
  ├── sh-redis-skills/                   # 顶层唯一暴露的 Redis 全域技能
  │   ├── SKILL.md                      # 路由入口、8 域分流表、消歧规则、AI 维护协议 (For Agent)、一键复原说明
  │   ├── iris-development/            # 完整保留 Iris AI 记忆数据面
  │   │   ├── SKILL.md
  │   │   └── references/
  │   ├── redis-clustering/            # 完整保留集群与分片
  │   ├── redis-connections/           # 完整保留连接池与客户端缓存
  │   ├── redis-core/                  # 完整保留数据结构与命名
  │   ├── redis-observability/         # 完整保留监控与慢查询排查
  │   ├── redis-search/                # 完整保留全文与向量检索
  │   ├── redis-security/              # 完整保留安全与 ACL
  │   └── redis-semantic-cache/        # 完整保留 LangCache 语义缓存
  ```
- **双向迁移与同步脚本**：编写独立脚本 `sync_redis_skills.py`
  - 默认执行收拢：识别根目录下散装的 8 个 `redis-*` / `iris-*` 目录，移入 `sh-redis-skills/`；
  - **【一键复原】`--restore`**：将 `sh-redis-skills/` 内的所有子目录完整移回根目录，恢复散装形态；
  - `--check`：仅检查当前散装残留、已收拢数量与探针诊断；
  - `--dry-run`：预览将要发生的操作；
  - `--json`：输出结构化 JSON，供任何接入的 AI Agent 直接机器解析；
  - **探针机制**：
    - `[NEW DOMAIN]`：发现新增未收录的 Redis 相关业务域；
    - `[OFFICIAL SUITE READY]`：探针检测是否出现官方原生集成套件。
- **批处理联动**：
  - 更新 `sync_skills.bat`，增加对 `sync_redis_skills.py` 的自动检测调用；
  - 联动 `sync_skills.py`，自动刷新 Codex per-skill junction（移除旧的 8 个散装 link，建立单个 `sh-redis-skills` link）。
- **Git 镜像与版本回退保障**：
  - 操作前打下只读快照标签 `pre-redis-router-snapshot`；
  - 完成后按规范提交并推送到远端仓库。

---

## 任务分解 (Task Breakdown)

### Task 1: 编写 `sync_redis_skills.py` 资产迁移、探针诊断与双向复原脚本
- **文件**：`C:/Users/29580/.gemini/config/skills/sync_redis_skills.py`
- **实现**：
  1. 识别 8 个目标官方技能（7 个 `redis-*` + 1 个 `iris-development`）；
  2. 原子移动与增量覆盖收拢至 `sh-redis-skills/`；
  3. **一键复原 `--restore`** 实现：将子目录全部原样退回根目录；
  4. 支持 `--check`、`--dry-run`、`--json`；
  5. 内置 `[NEW DOMAIN]` 与 `[OFFICIAL SUITE READY]` 探针检测。
- **验证**：运行 `python sync_redis_skills.py --dry-run` 预览操作，校验准确识别 8 个技能，0 误伤其它技能。

### Task 2: 执行全量迁移并构建含「AI 协同协议」的 `sh-redis-skills/SKILL.md`
- **文件**：
  - `C:/Users/29580/.gemini/config/skills/sh-redis-skills/SKILL.md`
  - `C:/Users/29580/.gemini/config/skills/sh-redis-skills/*`（8 个子目录）
- **实现**：
  1. 执行 `python sync_redis_skills.py` 完成物理收拢；
  2. 编写高质量 `sh-redis-skills/SKILL.md`，包含：
     - 8 域官方能力路由表（核心职责、触发场景、子模块路径）；
     - 典型消歧决策指南（Core vs Search vs Cache；Clustering vs Connections；Iris vs Semantic Cache 等）；
     - 《AI 维护与生命周期治理协议 (For Agent)》；
     - 《一键复原与回滚指南》。
- **验证**：检查根目录下 `redis-*` 和 `iris-*` 为空；检查 `sh-redis-skills/` 包含完整 8 个子目录。

### Task 3: 适配 `sync_skills.bat` 联动与多 Agent 软链刷新
- **文件**：
  - `C:/Users/29580/.gemini/config/skills/sync_skills.bat`
- **实现**：
  1. 在 `sync_skills.bat` 中加入 `sync_redis_skills.py` 自动检查；
  2. 运行 `sync_skills.bat`，刷新 Codex、Claude、Gemini、Opencode、Cursor、Pi 的软链；
  3. 确认 Codex per-skill junction 正确新增 `sh-redis-skills` 并移除失效的 8 个散装 junction。
- **验证**：运行 `sync_skills.bat` 输出 0 错误，Codex 目录结构整齐。

### Task 4: Git 提交、远端推送与用户测试交接
- **文件**：Git 仓库所有变动
- **实现**：
  1. 验证 `git status` 识别全部变动为 Rename / Move 与新脚本；
  2. 提交规范 Commit（如 `feat(redis): 收归 8 个官方 redis-* 与 iris-* 技能至 sh-redis-skills 路由器并提供一键复原脚本`）；
  3. 执行 `git push origin main` 推送至 GitHub；
  4. 不做任何多余的主动测试，将测试权交由用户，并在报告中清晰列出一键复原指令与消歧支持说明。

---

### Critical Files for Implementation
1. `C:/Users/29580/.gemini/config/skills/sync_redis_skills.py`
2. `C:/Users/29580/.gemini/config/skills/sh-redis-skills/SKILL.md`
3. `C:/Users/29580/.gemini/config/skills/sync_skills.bat`
4. `C:/Users/29580/.gemini/config/skills/plans-03-sh-redis-skills-router.md`
