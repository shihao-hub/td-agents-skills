---
name: sh-lark-skills
description: 飞书全域技能族路由器：集成飞书 28 域原生能力（IM、文档、表格、多维表格、审批、任务、邮件、日历、会议、妙记等），按用户意图精准分流加载对应子模块。当涉及任何飞书操作时点名或自动路由使用。
---

# sh-lark-skills: 飞书全域技能族分流路由器

集成飞书官方全域 28 个原子业务能力，采用统一入口路由器模式。通过意图识别按需加载子模块，将全局 Prompt 消耗降至最低，避免不同能力间的提示词污染与误触发。

---

## 路由工作流

当用户提出飞书相关的请求时：
1. **意图匹配**：查阅下方的 [28 域官方能力路由表](#28-域官方能力路由表) 与 [消歧决策指南](#消歧决策指南)。
2. **加载子技能**：通过 `view_file` 读取对应子目录的 `sh-lark-skills/<domain>/SKILL.md`（必要时读取其 `references/`）。
3. **执行与反馈**：严格遵循子技能说明中的命令格式与参数规范执行操作。

---

## 28 域官方能力路由表

| 业务域 (Domain) | 核心职责与触发场景 | 子模块路径 |
| :--- | :--- | :--- |
| `lark-im` | 消息收发、群聊管理、单聊/群聊记录搜索、交互卡片、加急 | `sh-lark-skills/lark-im/SKILL.md` |
| `lark-doc` | 云文档（Docx/Wiki）正文读写、局部编辑、插入下载附件图片、思维笔记 | `sh-lark-skills/lark-doc/SKILL.md` |
| `lark-sheets` | 电子表格（Sheets）：单元格读写、行列操作、样式、公式、图表、本地 Excel 导入导出 | `sh-lark-skills/lark-sheets/SKILL.md` |
| `lark-base` | 多维表格（Base/bitable）：数据表、字段、记录 CRUD、视图、公式、BaseApp 模式 | `sh-lark-skills/lark-base/SKILL.md` |
| `lark-wiki` | 知识库（Wiki）：知识空间、空间成员、目录树节点移动与创建 | `sh-lark-skills/lark-wiki/SKILL.md` |
| `lark-drive` | 云空间（Drive）：文件/文件夹上传下载、移动复制删除、权限管理、文件格式导入 | `sh-lark-skills/lark-drive/SKILL.md` |
| `lark-mail` | 飞书邮箱：起草、发送、回复、转发邮件、查阅邮件与文件夹标签 | `sh-lark-skills/lark-mail/SKILL.md` |
| `lark-calendar`| 日程与日历：创建/查看/更新日程、管理参会人、查询忙闲、预定会议室 | `sh-lark-skills/lark-calendar/SKILL.md` |
| `lark-meeting` | 视频会议产物：会议纪要、妙记逐字稿搜索与下载、会中实时问答与聊天 | `sh-lark-skills/lark-meeting/SKILL.md` |
| `lark-task` | 飞书任务与待办：创建待办、更新状态、拆分子任务、清单组织、任务附件 | `sh-lark-skills/lark-task/SKILL.md` |
| `lark-approval`| 飞书审批：查询审批待办/已办、查看审批实例详情、发起原生审批流程 | `sh-lark-skills/lark-approval/SKILL.md` |
| `lark-attendance`| 考勤打卡：查询个人的考勤与打卡记录 | `sh-lark-skills/lark-attendance/SKILL.md` |
| `lark-contact` | 通讯录：姓名/邮箱解析为 open_id、反查个人资料/部门信息、搜索可用机器人 | `sh-lark-skills/lark-contact/SKILL.md` |
| `lark-okr` | OKR 目标管理：查看/编辑 OKR 周期、目标、关键结果、对齐关系与进展 | `sh-lark-skills/lark-okr/SKILL.md` |
| `lark-slides` | 幻灯片：创建与读取演示文稿、单页管理、页面内容局部更新 | `sh-lark-skills/lark-slides/SKILL.md` |
| `lark-whiteboard`| 云文档画板：导出画板为预览图片、导出节点结构、更新画板内容 | `sh-lark-skills/lark-whiteboard/SKILL.md` |
| `lark-markdown`| 飞书原生 Markdown：查看、创建、上传、比对飞书云端与本地的 Markdown 文件 | `sh-lark-skills/lark-markdown/SKILL.md` |
| `lark-apps` | 妙搭应用（Spark/Miaoda）：全栈开发托管、数据库、原型设计、触发器编排 | `sh-lark-skills/lark-apps/SKILL.md` |
| `lark-event` | 实时事件流监听：通过 `lark-cli event consume` 以 NDJSON 监听消息/审批/会议变更 | `sh-lark-skills/lark-event/SKILL.md` |
| `lark-shared` | 认证与配置中心：`lark-cli` 登录/状态/退出、用户与应用身份切换、权限 scope 修复 | `sh-lark-skills/lark-shared/SKILL.md` |
| `lark-openapi-explorer`| 原生 OpenAPI 探索：挖掘未被 CLI 封装的官方原生 OpenAPI 接口契约 | `sh-lark-skills/lark-openapi-explorer/SKILL.md` |
| `lark-skill-maker`| 自定义技能制作：将多步飞书 API 操作封装为可复用的 CLI 自定义 Skill | `sh-lark-skills/lark-skill-maker/SKILL.md` |
| `lark-workflow-meeting-summary` | 工作流：汇总指定时间范围内的会议纪要并输出结构化周报/简报 | `sh-lark-skills/lark-workflow-meeting-summary/SKILL.md` |
| `lark-workflow-standup-report` | 工作流：聚合日历日程与未完成任务，生成每日/每周站会待办摘要 | `sh-lark-skills/lark-workflow-standup-report/SKILL.md` |
| `lark-minutes` | 统一重定向：妙记操作统流至 `sh-lark-skills/lark-meeting/SKILL.md` | `sh-lark-skills/lark-meeting/SKILL.md` |
| `lark-note` | 统一重定向：会议笔记统流至 `sh-lark-skills/lark-meeting/SKILL.md` | `sh-lark-skills/lark-meeting/SKILL.md` |
| `lark-vc` | 统一重定向：视频会议统流至 `sh-lark-skills/lark-meeting/SKILL.md` | `sh-lark-skills/lark-meeting/SKILL.md` |
| `lark-vc-agent`| 统一重定向：视频会议智能体统流至 `sh-lark-skills/lark-meeting/SKILL.md` | `sh-lark-skills/lark-meeting/SKILL.md` |

---

## 消歧决策指南

| 场景 | 推荐子模块 | 排除理由与区分边界 |
| :--- | :--- | :--- |
| **文档正文 vs 知识库结构** | `lark-doc` | 若要修改或读取文档内容，走 `lark-doc`；若只是管理空间节点树或移动页面归属，走 `lark-wiki`。 |
| **电子表格 vs 多维表格** | `lark-sheets` / `lark-base` | 传统行列单元格计算/Excel 迁移走 `lark-sheets`；数据库结构/记录关联/看板看板走 `lark-base`。 |
| **云盘文件管理 vs 文档内容** | `lark-drive` | 文件上传/下载/移动/重命名走 `lark-drive`；不要尝试用 drive 去解析修改 docx 内部段落。 |
| **待办事项 vs 审批流程** | `lark-task` / `lark-approval` | 个人或协同清单/截止时间走 `lark-task`；需要组织内流转审批/加签/驳回的正式表单走 `lark-approval`。 |
| **即时通讯 vs 邮件沟通** | `lark-im` / `lark-mail` | 群聊/私聊/富文本卡片通知走 `lark-im`；正式邮件撰写与发送走 `lark-mail`。 |
| **会议日程预定 vs 会议纪要妙记**| `lark-calendar` / `lark-meeting` | 开会前订会议室/查冲突走 `lark-calendar`；开会后查录音/逐字稿/妙记纪要走 `lark-meeting`。 |

---

## 个人自研飞书生态工具

除上述官方能力外，根目录下保留了针对高频场景的自研专属工具，顶层支持直接联动：
- **`sh-lark-chat-archive`**：将飞书聊天记录一键导出归档为排版精美的单文件离线 HTML（含图注与 Lightbox）。
- **`sh-lark-session-doc`**：将当前 Agent 研讨会话一键原封不动沉淀为飞书云文档。

---

## 核心机制：AI 维护与生命周期治理协议 (For Agent)

> 💡 **核心原则：脚本归脚本，AI 归 AI**  
> 脚本提供机械确定的文件搬移与探针诊断，而 AI 则是感知中枢与决策中枢。所有后续接手的 AI Agent 必须遵守本协议：

### 1. 更新感知与用户提示
- 官方 `lark-cli` 在运行时若发现新版本或组件更新，会在输出中返回 `_notice.update` 或 `_notice.skills`。
- **AI 动作**：当在工具执行结果中看到 notice 时，必须主动向用户汇报（如：“检测到飞书官方 CLI/技能有新更新，是否为您执行升级？”），获批后由用户或 AI 运行 `lark-cli update`。

### 2. 更新收割与脚本联动
- 官方升级通常会将新的散装 `lark-*` 重新释放到根目录。
- **AI 动作**：升级完成后，AI 应紧接着运行：
  ```bash
  python sync_lark_skills.py --json
  ```
- 脚本会自动将散装组件重新收归至 `sh-lark-skills/`，并给出结构化诊断结果。

### 3. 新增域 (New Domain) 自愈与路由更新
- 当诊断输出包含 `new_domains`（例如官方新增了 `lark-table`）：
- **AI 动作**：
  1. AI 必须通过 `view_file` 深入阅读 `sh-lark-skills/<new-domain>/SKILL.md`；
  2. 理解其核心职责，提炼出一句话精准定位与消歧规则；
  3. 将新条目主动追加到本文件的 **[28 域官方能力路由表]** 与 **[消歧决策指南]** 中，保持路由系统自我演进。

### 4. 官方一体化套件 (Official Suite Ready) 研判与平退建议
- 当诊断输出中出现 `[OFFICIAL SUITE READY]`（即官方原生已经具备了完善的单体套件结构）：
- **AI 动作**：
  1. AI 负责评估官方原生套件是否已经能完全覆盖现有能力，且提示词消耗是否合理；
  2. 向用户提交《官方套件成熟度与平替评估报告》；
  3. 若用户同意切换，AI 协助安全下线 `sh-lark-skills`，无缝回归官方原生生态。

---

## 【重要】一键复原与回滚指南 (Rollback Guide)

如果您在测试过程中发现某个技能路由不精准或无法正常调用，需要立即把所有官方技能恢复成原本的散装形态：

### 快速一键复原命令
```powershell
# 在 skills 根目录执行以下任一命令：
python sync_lark_skills.py --restore

# 随后刷新多 Agent 软链映射：
python sync_skills.py
```

### 复原效果
1. `sh-lark-skills/` 下所有的子技能目录会被完整移回 `~/.agents/skills/` 根目录。
2. 恢复为官方原本的 28 个独立散装形态。
3. `sync_skills.py` 会自动为 Codex 重新挂载这 28 个散装 junction。
4. 如需再次收拢或继续优化，只需重新运行 `python sync_lark_skills.py` 即可，整个过程完全幂等、安全无损。
