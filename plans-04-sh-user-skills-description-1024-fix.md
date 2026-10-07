# Plan: sh-user-skills 分流器 description 超限修复（1024 字符硬约束）

📋 Plan for: "把超限的顶层分流器 description 压回 1024 字符内，同时保住全量子技能的模糊分流能力，并把该约束固化进创作规范"

## 问题陈述

DeepSeek harness 启动时报：

```
[Skill conflicts]
  auto (project) D:\Users\language_projects\.agents\skills\sh-user-skills\SKILL.md
    description exceeds 1024 characters (2515)
```

成因：commit `6d5ce52`（feat(sh-user-skills): description 补充全量子技能清单）把 52 行子技能名清单塞进 frontmatter，description 达 2514 字符（harness 口径 2515），超出 Agent Skills 规范的 1024 上限。

按 1024 切分当前 description 的实测截断后果：

| 指标 | 实测 |
| --- | --- |
| description 总长 | 2514 字符 |
| 其中出现的技能名 | 52 个 |
| 落在前 1024 字符内 | **20 个**（到 `sh-uwp-proxy-loopback` 为止） |
| 截断后失联 | **32 个**（GLM 401、Zed LSP/ACP/Agent Panel/会话、计划三件套、全部媒资与归档类） |

即超限不是"稍微超一点"：尾部 62% 的技能在全局 prompt 中根本不存在，**自动分流对它们已经完全失效**；若 harness 改为整体丢弃该 skill，则连路由入口本身都没了。

## 需求（含用户决策）

- 修 description（改关键词方案），正文场景表保留；用户原话："可以的，这样"
- 配套修订 `USER-SKILL-AUTHORING-RULES.md` 把约束固化，防止回潮；用户原话："是不是也可以编辑了"
- 不拆分路由器为多个兄弟 skill（保留"单一总入口"定位）
- 提交与推送由 AI 完成（skills 子模块真身，远端 `git@github.com:shihao-hub/td-agents-skills.git`）

## 背景

- `~/.agents/skills`（= `D:\Users\language_projects\.agents\skills`）是真身，opencode / claude / codex 等目录均为指向它的 junction 或镜像
- 子技能统一以 `README.md` 存放（防 Agent 递归探测），因此子技能名**本就不会**进入任何 agent 的全局 prompt
- 路由器的 description 是唯一常驻的分流入口：只有"关键词通道"，没有"名字通道"
- 自动分流的匹配对象是"用户会说的词"，不是技能名：用户说"喇叭爆音"时 `sh-windows-audio-diagnose` 帮不上忙，"声卡无声/爆音"才有用
- 规范现状：`SKILL-AUTHORING-RULES.md` 已规定 description 1–1024 字符；`USER-SKILL-AUTHORING-RULES.md` 只约束子技能，未约束路由器

## 方案

1. description 改为五域分组关键词/症状词（装机与环境／排障／开发与重构／文档与交接／检索与媒资归档）
2. 末尾保留名字兜底子句："用户直接点名 `sh-*` 子技能（含拼写近似）时也由本入口解析"
3. 正文新增 `### 🗣️ 口语说法 → 技能速查`（35 行"口语/症状 → 技能名"对照表）
4. 正文交互协议新增"名字兜底"：点名名字不在表内时用 `ls` / `rg --files` 做目录名模糊匹配，不得放弃
5. `USER-SKILL-AUTHORING-RULES.md` 固化：硬约束表新增一行 + 新增「二·补、顶层分流器 description 规范」+ Step 3/4 补关键词回填与长度校验

## 任务分解

- [x] Task 1: 确认回滚基线（baseline `6d5ce52`，工作区干净）
- [x] Task 2: 重写 frontmatter description（2514 → 713 字符）并补名字兜底子句
- [x] Task 3: 新增口语说法速查表（35 行）与正文名字兜底规则
- [x] Task 4: 固化 `USER-SKILL-AUTHORING-RULES.md`（+26 / -2 行）
- [x] Task 5: 校验与实测（见"实施说明"）
- [x] Task 6: 分范围提交与推送（plan 文件 / sh-user-skills / 根规范 三笔独立 commit）

## 实施说明（2026-10-07）

- **长度**：description 2514 → **713 字符**（PowerShell 正则口径 721，含尾随换行），≤1024 通过，harness 的 `[Skill conflicts]` 消除
- **覆盖核对**：49 个子技能 + 3 个族路由器逐条映射进五域关键词，无遗漏；新 description 内**不含任何 `sh-*` 名字**（名字通道本就不存在，不必占预算）
- **写入保真**：CRLF + 无 BOM 保持不变；frontmatter 其余字段（name/version/created/updated）未改动
- **校验命令**（已实跑并写入规范第二节·补）：

  ```powershell
  $f = "D:\Users\language_projects\.agents\skills\sh-user-skills\SKILL.md"
  $raw = Get-Content -Encoding UTF8 $f -Raw
  ([regex]::Match($raw, '(?ms)^description: \|\r?\n(.*?)^version:').Groups[1].Value).Length   # 必须 <= 1024
  ```

- **未做**：eval 命中率实测（交用户按真实口语验收，命中失败则回补关键词）

## 延后积压

- 口语命中率实测与关键词回补闭环（新建子技能时必须回填新领域关键词）
- 若用户坚持"名字级全量可见"，再评估 `sh-user-skills-*` 兄弟路由器拆分方案（成本：维护翻倍、登记多处，与"单一总入口"定位冲突）
- 三个族路由器（agy / lark / redis）暂无超限风险

---
**最后更新：** 2026-10-07
**作者：** AI & User
**版本：** v1
