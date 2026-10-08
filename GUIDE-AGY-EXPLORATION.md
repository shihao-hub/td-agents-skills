# SKILL-AGY-EXPLORATION：Antigravity 斜杠命令逆向探索记录

> 版本 v1.0.0 ｜ 2026-09-25 ｜ 探索产物：`D:\Users\zeddefault\agy-extracted-prompts.md`（约 19KB 原始提示词）｜ 衍生：8 个 sh-agy-* skill

## 一、任务背景

用户提供 Antigravity 斜杠命令菜单截图的中文介绍（/goal、/schedule、/browser、/plan、/grill-me、/teamwork-preview、/learn、/boost 共 8 个），要求：探索这些功能的实现方式，提取提示词，并评估/制作成 skill。

## 二、探索路径（含碰壁）

1. **定位安装**：`C:\Users\29580\AppData\Local\Programs\antigravity`（Electron 应用，VS Code fork）；用户数据在 `AppData\Roaming\Antigravity`。
2. **碰壁一**：先搜 `resources\app.asar` 里的 "grill" —— 零命中。结论：AI 逻辑不在前端壳里。
3. **转折**：`Roaming\Antigravity\bin\agy-node.cmd` 只是 `ELECTRON_RUN_AS_NODE` 包装；真正的线索是 `resources\bin\language_server.exe`（**162MB Go 二进制**）。
4. **碰壁二**：`rg` 不存在（报错被 2>/dev/null 吞了，一度误判无命中）；`grep -a -o -E ".{60}grill.{400}"` 因二进制 null 字节/巨行匹配失败。
5. **方法定型**：Python 读全文件 + 正则定位关键词偏移 + 把不可打印字符替换成换行后按行过滤，成功提取全部提示词。命中证据：grill=3、teamwork=733、slashCommand=83。
6. **确认血统**：二进制内大量 `com.exafunction.codeium`、`third_party/jetski` 包名 —— Windsurf/Codeium 团队产物（Google 收购），agent 核心沿用 Windsurf 语言服务器架构。

## 三、总体架构结论

- Antigravity = Electron 壳（UI/编辑器）+ `language_server.exe`（Go，承载全部 agent 逻辑、提示词、工具、会话存储 sqlite FTS5）。
- **斜杠命令不是独立程序**：本质是"提示词注入 + 原生工具 + 宿主循环"三种机制的组合。
- 提示词以明文内嵌，用 `<GRILL_ME>`、`<PLAN>`、`<LEARN>`、`<TEAMWORK>` 标签包裹；另有 Go embed 的技能资产 `assets/external/skills/`（antigravity_guide、agy-customizations 等，即 SKILL.md/app.md/ide.md/cli.md 那套）。
- 主系统提示词开头："You are Antigravity, a powerful agentic AI coding assistant designed by the Google Deepmind team working on Advanced Agentic Coding."

## 四、8 个命令的实现机制与提取偏移

| 命令 | 机制 | 关键字符串/偏移（2026-09-23 构建） |
|---|---|---|
| /grill-me | 注入 `<GRILL_ME>`：访谈用户、一次一题、能查代码就不问、用 ask_question 工具 | 0x30CC5F8 附近（51115480） |
| /goal | 注入目标声明 + 哨兵 `<!-- GOAL_COMPLETE -->` / `<!-- GOAL_CANCELLED -->` + 系统强制续跑审计提示词（重读需求→交付物→证据 checklist→"付出努力≠完成"） | 初始 51115983；续跑 51232500 区；哨兵 49770576/49828211 |
| /plan | 注入 `<PLAN>`：研究同步→plan artifact（request_feedback）→批准→执行→验证→walkthrough | 51766134 |
| /schedule | 原生工具：DurationSeconds 单次 / CronExpression 周期 / TimerCondition 早取消 / IsDaemon 常驻；调完立即 end turn 等通知；禁 shell sleep | 工具描述 51126000 区（原文 "Schedule a one-shot timer…"） |
| /browser | 独立 browser agent（"You are a browser agent."），底层 **chrome-devtools-mcp**（app.asar.unpacked\node_modules 里可见） | 49882771 |
| /teamwork-preview | `<TEAMWORK>`：9 步交互打磨任务书（prompt_draft.md artifact，4 核心原则）+ 委派 teamwork 多 agent 系统；git worktree 隔离（refs/battle/base） | 52672360 |
| /boost | 服务端 "battle" 编排系统（winner conversation、battle child、END_BATTLE_MODE），**本地无提示词**；admin proto 有 boost_command_disabled / teamwork_preview_command_disabled 开关 | 描述 50713274；admin 字段 52040802 区 |
| /learn | 注入 `<LEARN>`：分析纠正→定位关键修复→根因/范围→Rule/Skill 分类→更新优先→learning_proposal.md 提案→批准后才写 | 51389164 |

## 五、其它值得记录的发现

- **内嵌技能资产**（Go embed）：antigravity_guide（SKILL.md + references/app|cli|ide|sdk.md，含官方文档 sitemap 与 LINT.IfChange 标记）、agy-customizations（docs/hooks|rules|skills|plugins|mcp_servers|json_configs.md）、shared/skills/permissioned-github、migrate-workflows。
- 内嵌 proto 里有 Google 内部服务依赖（businessaicode v1beta AdminControls、Cloud Speech、internal/assistant 等），佐证服务端编排（boost/teamwork）走 Google 云。
- 彩蛋提示词：git worktree 命名生成器（"senior developer… 4 words max, underscore separated"）、终端 stdin 等待分类器（"Enter password:" → YES）、hook 沙箱执行器（"You are a sandboxed background helper executing a prompt-based hook"）、lint 错误注入（"As IDE feedback, the following lint errors may be related…"）。

## 六、提取方法复现（下次升级版直接用）

```python
import re
data = open(r'C:\Users\29580\AppData\Local\Programs\antigravity\resources\bin\language_server.exe','rb').read()
i = data.find(b'<GRILL_ME>')   # 换成任意关键词/标签
txt = re.sub(rb'[^\x20-\x7e\n\r\t]', b'\n', data[i-100:i+1500]).decode('ascii')
print('\n'.join(l for l in txt.split('\n') if len(l.strip()) > 25))
```

注意：bash 里路径必须加引号（反斜杠会被吃掉）；grep 对该二进制的 -o 上下文提取不可靠，直接上 Python。

## 七、移植映射（本次产出）

| 命令 | skill | 移植方式 |
|---|---|---|
| /goal | sh-agy-goal | 提示词全量移植；系统强制续跑降级为自审计协议，哨兵保留 |
| /schedule | sh-agy-schedule | 原生工具降级为 schtasks + 落盘结果，无法唤醒对话 |
| /browser | sh-agy-browser | 同源 chrome-devtools 工具直接编排，零降级 |
| /plan | sh-agy-plan | 提示词+文档格式全量移植，artifact 改为 plans/ 落盘 |
| /grill-me | sh-agy-grill-me | 全量移植，ask_question 改为回复内提问 |
| /teamwork-preview | sh-agy-teamwork | 9 步打磨全量移植，委派降级为 task 子代理+文件分区 |
| /learn | sh-agy-learn | 全量移植，写入目标改为 ~/.agents/skills 与 AGENTS.md |
| /boost | sh-agy-boost | 原版在服务端无法提取，本地复刻为多遍强化流水线 |
