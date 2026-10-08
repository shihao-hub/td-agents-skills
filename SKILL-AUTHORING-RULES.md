---
name: skill-authoring-rules
description: |
  公共根级技能与族路由器的创作规范：目录结构与命名正则、description 的 1–1024 字符常驻预算、点名触发写法与反军备竞赛红线、正文渐进披露与 evals 产出要求，并说明本 harness 实际把哪些文件注册为技能。当你新建或改造根级技能、sh-* 族路由器，或需要判断某个能力该走公共规范还是个人沉淀类规范时使用。个人沉淀类技能（sh-user-skills/ 下的 sh-* 子技能）走 skill-user-authoring-rules，不要套用本规范。
version: 1.0.0
created: 2026-10-07
updated: 2026-10-09
---

# SKILL-AUTHORING-RULES：公共根级技能创作规范

> 本文件约束**公共根级技能**与**族路由器本身**；个人沉淀类技能请改看 [SKILL-USER-AUTHORING-RULES.md](file:///D:/Users/language_projects/.agents/skills/SKILL-USER-AUTHORING-RULES.md)。
> 使用模式前提：这类技能的 description 常驻每个会话的 system prompt，**用户点名调用即可，AI 不必自主触发**——写清"是什么"比写满"什么时候必须用"更划算。

## 〇、先认清机制：这个 harness 把什么注册成技能

动手前先确认落点，放错地方要么技能不生效，要么把 prompt 预算烧掉：

| 形态 | 是否注册 | 说明 |
|---|---|---|
| `<skills-root>/<name>/SKILL.md` | ✅ | 只扫这一层，嵌套子目录不发现 |
| `<skills-root>/SKILL-<NAME>.md`（根目录散装单文件）+ 合规 frontmatter | ✅ | 实测（2026-10-09）：补上 `name`/`description` 后立即以 `skill-<name>` 出现在技能目录里 |
| 同目录但不带 frontmatter 的 `.md`（`GUIDE-*.md`、`plans-*.md`、未改造的 `SKILL-*.md`） | ❌ | 实测均未注册：没有 `name`/`description` 就不会进技能目录 |
| 子目录里命名为 `SKILL-DRAFT.md` 等非 `SKILL.md` 的文件 | ❌ | 子目录扫描只认 `SKILL.md`；这是"内容合规但暂不注册"的写法（见 `kb-engineering-notes/`） |

由此得到两条实操结论：

- **想只沉淀文档、不占 prompt 预算**：别给根目录散装 `.md` 加 frontmatter，或者按 `SKILL-DRAFT.md` 的写法放进子目录；
- **想知道某个技能有没有真正生效**：看它是否出现在会话的 available skills 列表里——文件写了不等于注册成功，frontmatter 缺字段会被静默跳过。

## 一、硬约束（违反即加载失败或失效）

| 约束 | 内容 | 为什么 |
|---|---|---|
| 目录结构 | `~/.agents/skills/<name>/SKILL.md`，只扫这一层，嵌套不发现 | 把多个子技能塞进一个目录不会逐个注册，只会剩族路由器一个入口 |
| 命名 | 目录名 / `name` 字段 == 小写字母数字 + 单连字符，正则 `^[a-z0-9]+(-[a-z0-9]+)*$` | 引擎按此校验，非法名会被跳过 |
| description | 1–1024 字符，单行或块状 YAML；**常驻每个会话的 system prompt——长度即每会话成本** | 超限会被截断（实测报 `[Skill conflicts] ... description exceeds 1024 characters`），尾部内容失联 |
| 同步 | 只改 `~/.agents/skills` 一处；`~/.config/opencode/skills` 与 `~/.claude/skills` 是指向它的 Junction，自动跟随 | 三处各改一遍必然漂移 |

## 二、description 规范（核心）

description 是点名匹配与"用户说得不精确时能否被想起"的唯一依据，按下面五条写：

1. **一句话功能语义**，目标 ≤70 字符（本次 23 条实测平均 ~55）
2. **性质前缀**：装机类 `装机：`、配置类 `配置：`、排障类 `排障：`；任务类不加前缀，直接动词短语开头
3. **保留核心关键词**：任务类保留任务语义（如"去水印/提字幕"），排障类保留症状词（如"401/登录失败/不生效"）——用户口语里冒出来的正是这些词
4. **结尾固定**：`点名使用`
5. **禁止**：触发词穷举、"必须使用本 skill"、"即使只说 X 也要触发"等军备竞赛语言——这类措辞既挤占预算，又会让模型对真实边界失去判断

**示例**（好坏对比，取自 sh-pwsh7-install）：

```
❌ 在 Windows 上零影响安装 PowerShell 7.x（跨平台 pwsh）：ZIP 绿色版安装到用户目录……当用户提到安装/升级 PowerShell 7、pwsh、PS7……即使只说"装个新版 powershell"也应触发。
✅ 装机：PowerShell 7 绿色版 ZIP 安装，零影响可卸干净。点名使用
```

**例外——主动触发类（auto）**：真正需要 AI 自主触发、影响功能开发流程的方法论/流程 skill（现有：sh-backend-design、sh-tech-doc-writing）不写"点名使用"，改为保留触发语义但**划清边界**："用户要 X 时使用；Y 场景不用"，同样禁止军备竞赛语言。新建此类需在 description 中明确正反边界各一句。

## 三、正文结构惯例

- 正文精炼（≤250 行），每个 skill 保持"可从头到尾执行"的 SOP 体或"可查阅"的手册体，二选一为主。
  正文是每次触发都要读进上下文的，所以只留会被反复用到的内容。
- 深度知识下沉 `references/`（按需加载，不占正文），可执行脚本放 `scripts/`。
- 评测放 `evals/evals.json`：**任务式用例**（prompt = 用户视角的任务描述，expected_output = 正确执行结果），不写触发断言。
  这类断言测的是"技能有没有被调用"，属 description 优化的范畴，放进用例只会让评测失真。

## 四、创作流程（强制）

**新建或大改这类 skill 时，必须调用 `skill-creator` skill 来编写、优化与评测**（含 description 按上述规范生成、evals 产出），不要手写 SKILL.md 后直接入库。本文档仅是规格约束，执行交给 skill-creator。

---

**最后更新：** 2026-10-09
**来源：** plans-01 与 sh-user-skills 收敛演进实践
