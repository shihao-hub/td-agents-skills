---
name: sh-redis-skills
description: Redis 与 Iris 全域技能族路由器：集成 Redis 官方核心建模、连接池、集群分片、全文/向量检索、监控排障、生产安全、语义缓存以及 Iris AI 智能体长短期记忆库。按用户意图精准分流加载对应子模块。
---

# sh-redis-skills: Redis 与 Iris 全域技能族分流路由器

集成 Redis 官方与 Iris AI 体系的 8 个原子业务能力，采用统一入口路由器模式。通过意图识别按需加载子模块，将全局 Prompt 消耗降低 98%（字符数由 3,808 骤降至 ~60），彻底消除不同 Redis 领域间的提示词污染与误触发。

---

## 路由工作流

当用户提出 Redis 或相关缓存、向量数据库、AI 记忆请求时：
1. **意图匹配**：查阅下方的 [8 域能力路由表](#8-域能力路由表) 与 [消歧决策指南](#消歧决策指南)。
2. **加载子技能**：通过 `view_file` 读取对应子目录的 `sh-redis-skills/<domain>/SKILL.md`（必要时按需读取其 `references/`）。
3. **执行与反馈**：严格遵循对应子技能的工程规范与参数指导完成任务。

---

## 8 域能力路由表

| 业务域 (Domain) | 核心职责与触发场景 | 子模块路径 |
| :--- | :--- | :--- |
| `iris-development` | **AI 智能体记忆数据面**：Redis Agent Memory (RAM) 云端记忆架构、记录会话事件 (session events)、长短期记忆 (LTM) 创建与检索、记忆存储配置与后台记忆提拔调优。 | `sh-redis-skills/iris-development/SKILL.md` |
| `redis-core` | **核心数据结构选型与建模**：选择合适的数据结构（String, Hash, List, Set, Sorted Set, JSON, Stream, Vector Set）、设计冒号分隔键名规范（如 `user:1000:profile`）、缓存对象对比（Hash vs JSON）。 | `sh-redis-skills/redis-core/SKILL.md` |
| `redis-connections` | **客户端连接与性能调优**：客户端配置（redis-py, Jedis, Lettuce 等）、连接池配置、指令管道 pipelining 批量化、RESP3 客户端缓存（Client-side caching）、超时设置与慢命令规避（避免 KEYS / HGETALL）。 | `sh-redis-skills/redis-connections/SKILL.md` |
| `redis-clustering` | **集群分片与多键路由**：Redis Cluster 分片架构、哈希标签（`{user:1000}:profile`）避免 CROSSSLOT 错误、跨槽事务规避、只读副本路由分流（扩展高并发读场景）。 | `sh-redis-skills/redis-clustering/SKILL.md` |
| `redis-search` | **全文与向量检索 (RediSearch)**：FT.CREATE 索引模式设计（TEXT, TAG, NUMERIC, VECTOR 等）、DIALECT 2 语法、HNSW / FLAT 向量相似度 KNN 检索、词法与向量混合检索（Hybrid Search）、RAG 检索管道。 | `sh-redis-skills/redis-search/SKILL.md` |
| `redis-security` | **生产安全防线与加固**：生产环境部署安全、requirepass 与 ACL 最小权限用户体系、TLS 加密连接、网络绑定 bind 与受保护模式、防火墙规则、禁用或重命名高危命令。 | `sh-redis-skills/redis-security/SKILL.md` |
| `redis-observability` | **可观测性与生产故障排查**：生产环境指标监控（内存、连接数、命中率、ops/sec、拒绝连接数）、排障指令实操（SLOWLOG, INFO, MEMORY DOCTOR, CLIENT LIST, FT.PROFILE）、Redis Insight 配合。 | `sh-redis-skills/redis-observability/SKILL.md` |
| `redis-semantic-cache` | **LLM 语义应答缓存 (LangCache)**：通过 Redis 云端 LangCache 缓存大模型（OpenAI / Anthropic）生成结果以削减 API 成本与延迟、相似度阈值精细调优、按任务类型隔离 Cache。 | `sh-redis-skills/redis-semantic-cache/SKILL.md` |

---

## 消歧决策指南

| 场景需求 | 推荐子模块 | 排除理由与区分边界 |
| :--- | :--- | :--- |
| **基础对象存储 vs 向量检索/RAG** | `redis-core` vs `redis-search` | 简单的键值对、哈希字段读取或原生计数器走 `redis-core`；如需根据内容相似度、多维字段复合过滤或向量匹配检索，必须走 `redis-search`。 |
| **大模型应答缓存 vs 智能体长期记忆** | `redis-semantic-cache` vs `iris-development` | 如果是为了避免重复调用大模型而按 Prompt 语义做 Cache-Aside，走 `redis-semantic-cache`；如果是为了让 AI 智能体记住跨会话的用户偏好、过往经历并提拔为长期记忆，走 `iris-development`。 |
| **单实例连接池调优 vs 分片集群 CROSSSLOT** | `redis-connections` vs `redis-clustering` | 解决客户端 Socket 连接耗尽、批处理批量吞吐走 `redis-connections`；排查分片集群下的跨节点计算错误或 Hash Tag 分布走 `redis-clustering`。 |
| **安全审计与 ACL 权限 vs 性能慢查询排查** | `redis-security` vs `redis-observability` | 限制应用用户命令权限、配置 TLS 证书走 `redis-security`；定位 Redis 实例 CPU 飙高、内存溢出或慢日志分析走 `redis-observability`。 |

---

## 核心机制：AI 维护与生命周期治理协议 (For Agent)

> 💡 **核心原则：脚本归脚本，AI 归 AI**  
> 自动化脚本负责底层的确定性操作与探针告警，而 AI 则是感知中枢与决策大脑。所有后续接入的 AI Agent 必须遵守本协议：

### 1. 结构化诊断与探针感知
- 当在维护或升级时，AI 可以通过执行以下命令获取结构化诊断信息：
  ```bash
  python sync_redis_skills.py --json
  ```
- 脚本会返回包含当前散装残留量、已收拢子模块清单、新域检测与套件就绪探针的 JSON 数据。

### 2. 新增域 (New Domain) 自愈与路由更新
- 当诊断输出包含 `new_domains`（例如 Redis 官方新增了 `redis-graph` 或类似专项域）：
- **AI 动作**：
  1. AI 必须通过 `view_file` 深入阅读 `sh-redis-skills/<new-domain>/SKILL.md`；
  2. 理解其核心能力范围，提炼精准的一句话定位与消歧规则；
  3. 将新条目主动追加到本文件的 **[8 域能力路由表]** 与 **[消歧决策指南]** 中，保持路由系统自我演进。

### 3. 官方一体化套件 (Official Suite Ready) 研判与平退建议
- 当诊断输出中出现 `[OFFICIAL SUITE READY]`（即官方原生已经具备完善的集成单体套件结构）：
- **AI 动作**：
  1. AI 负责评估官方原生套件是否能完全平替当前的路由器架构，且提示词消耗是否合理；
  2. 向用户提交《官方套件成熟度与平替评估报告》；
  3. 若用户同意切换，AI 协助安全下线 `sh-redis-skills`，无缝回归官方原生生态。

---

## 【重要】一键复原与回滚指南 (Rollback Guide)

如果您在测试过程中发现某个 Redis 技能路由不精准或无法正常调用，需要立即把所有技能恢复成原本的散装形态：

### 快速一键复原命令
```powershell
# 在 skills 根目录执行以下任一命令：
python sync_redis_skills.py --restore

# 随后刷新多 Agent 软链映射：
python sync_skills.py
```

### 复原效果
1. `sh-redis-skills/` 下所有的子技能目录会被完整移回 `~/.agents/skills/` 根目录。
2. 恢复为官方原本的 8 个独立散装形态。
3. `sync_skills.py` 会自动为 Codex 重新挂载这 8 个散装 junction。
4. 如需再次收拢或继续优化，只需重新运行 `python sync_redis_skills.py` 即可，整个过程完全幂等、安全无损。
