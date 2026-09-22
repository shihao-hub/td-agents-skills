# sh-* Skill 创作规范（AUTHORING RULES）

> 本文件是后续新建/大改个人沉淀类 skill 时的强制规范，源自 2026-09-22 的 23 个 sh-* skill description 整改（plans-01）。使用模式前提：**用户点名调用，AI 不需要自主触发**。

## 一、硬约束（opencode 机制，违反即加载失败或失效）

| 约束 | 内容 |
|---|---|
| 目录结构 | `~/.agents/skills/<name>/SKILL.md`，只扫这一层，嵌套不发现 |
| 命名 | 目录名 == frontmatter `name`，正则 `^[a-z0-9]+(-[a-z0-9]+)*$`（小写字母数字+单连字符） |
| description | 1–1024 字符，单行 YAML；**常驻每个会话的 system prompt——长度即每会话成本** |
| 同步 | 只改 `~/.agents/skills` 一处；`~/.config/opencode/skills` 与 `~/.claude/skills` 是指向它的 Junction，自动跟随 |

## 二、description 规范（核心）

1. **一句话功能语义**，目标 ≤70 字符（本次 23 条实测平均 ~55）
2. **性质前缀**：装机类 `装机：`、配置类 `配置：`、排障类 `排障：`；任务类不加前缀，直接动词短语开头
3. **保留核心关键词**：任务类保留任务语义词（如"去水印/提字幕"），排障类保留症状词（如"401/登录失败/不生效"）——点名与偶尔描述任务双保险
4. **结尾固定**：`点名使用`
5. **禁止**：触发词穷举、"必须使用本 skill"、"即使只说 X 也要触发"等军备竞赛语言

**示例**（好坏对比，取自 sh-pwsh7-install）：

```
❌ 在 Windows 上零影响安装 PowerShell 7.x（跨平台 pwsh）：ZIP 绿色版安装到用户目录……当用户提到安装/升级 PowerShell 7、pwsh、PS7……即使只说"装个新版 powershell"也应触发。
✅ 装机：PowerShell 7 绿色版 ZIP 安装，零影响可卸干净。点名使用
```

**例外——主动触发类（auto）**：真正需要 AI 自主触发、影响功能开发流程的方法论/流程 skill（现有：sh-backend-design、sh-tech-doc-writing）不写"点名使用"，改为保留触发语义但**划清边界**："用户要 X 时使用；Y 场景不用"，同样禁止军备竞赛语言。新建此类需在 description 中明确正反边界各一句。

## 三、正文结构惯例

- 正文精炼（≤250 行），每个 skill 保持"可从头到尾执行"的 SOP 体或"可查阅"的手册体，二选一为主
- 深度知识下沉 `references/`（按需加载不占目录），可执行脚本放 `scripts/`
- 评测放 `evals/evals.json`：**任务式用例**（prompt=用户视角的任务描述，expected_output=正确执行结果），不写触发断言

## 四、创作流程（强制）

**新建或大改这类 skill 时，必须调用 `skill-creator` skill 来编写、优化与评测**（含 description 按上述规范生成、evals 产出），不要手写 SKILL.md 后直接入库。本文件仅是规格约束，执行交给 skill-creator。

---
**最后更新：** 2026-09-22
**来源：** plans-01-sh-skill-description-rewrite 整改实践
