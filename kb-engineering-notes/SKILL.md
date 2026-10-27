---
name: kb-engineering-notes
description: |
  开发者通用工程实战手记、疑难排障与自动化流水线知识库（两级渐进式检索总入口）：遇到系统/IDE/终端异常、底层报错或落地工程自动化时优先查阅。
   【排障救火】Win文件锁Permission denied、Restart Manager句柄占用原子替换静默丢失；Git变基rescheduled队列挂起、SublimeMerge非相邻Squash、Worktree依赖复用、多Git账号SSH；Win11输入法图标删不掉与Windhawk注入、高频Alt+Tab卡键粘滞、单按Alt抢Chrome焦点与语音输入透传；Win声卡爆音无声、代理下UWP回环、C盘清理与软链Junction、内存防死机与Pagefile；DefTerm控制台委托断层与MCP黑框闪窗；划词工具Ctrl+C误杀终端、WT选中复制Ctrl+C假死与剪贴板锁争用；Chrome固定标签丢失SNSS快照抢救；Zed/VSCode崩溃、LSP下载独占锁、ACP进程池堆积、Zed信任表污染致全盘监听10G内存与Defender死锁、外部 ACP 线程不自动命名、SQLite会话恢复、终端丢失agy历史ID恢复；Terminal分屏治理与BOM报错；Antigravity Manager切换target-conflict、桌面端ConnectRPC热推送；Wails v3 WebView2内存暴涨释放；DarkReader暗黑插件冲突；dsh误唤起Grok与x.ai弹窗；Claude Code升级400与OpenCode协议分立路由代理；父目录Low完整性闪退；Chrome扩展MatchPattern端口报错等。
  【简历排版】木及简历mujicv、简历导入导出、PDF行首裁字、简历CSS不生效、简历制作SOP。
  【实战流水线】uv全机环境统一；Worktree跨语言依赖复用；Word试卷排版；GUI自动化UIA阶梯；无窗口自启服务与WMI脱离；离线向量检索；无API事实核查；开源上游Issue高穿透提交与证据链设计；AGY外观Rider配色；AHK非侵入启动外挂与WMI脱离。
  检索协议：先读本路由表命中条目，再读具体手记SOP；条目持续生长，全量索引以本路由表为准；报错或点名查阅时使用。命中后先看status：deprecated弃用改读superseded_by，suspect先只读探测再执行。
version: 2.3.0
created: 2026-10-07
updated: 2026-10-27
---

# 工程实战手记与疑难排障知识库 (Engineering Notes Playbook)

> **注意（转正状态说明）**：
> 本知识库已转正为**根级活跃技能**（文件名 `SKILL.md`），可被 harness 自动注册，并支持以 `/kb-engineering-notes` 点名调用。
> 本文件架构完全遵循 `/skill-creator` 规范；若要退回草稿隔离态（不被自动注册），只需执行：
> `git mv SKILL.md _SKILL.md`

---

## 知识库文件命名规范与元数据契约（AI 与开发者速查）

> 💡 **两级感知协议**：外部 Agent 载入本文件后，首屏即刻掌握命名规范，通过槽位与正则零 I/O 成本建立结构化感知。

```text
语法结构：<id>_<domain>_<scope>_<type>_<slug>.md
正则解析：^(?<id>\d{3})_(?<domain>[a-z]{2,8})_(?<scope>[a-z0-9]{2,8})_(?<type>fix|flow)_(?<slug>[^_\/\\:\*\?"<>\|]+)\.md$
```

- **槽位 1 `<id>`（逻辑时钟置顶与唯一 UID，使侧边栏与文件列表天然顺序对齐）**：
  `001` ~ `999` 定长 3 位，全局单调递增，永不回收复用。**ID 越大表示创建时间越新，列表尾部即最新条目**。
- **槽位 2 `<domain>`（受控领域，严格 7 枚举，对齐未来一级子目录）**：
  `win`（Windows底层/软链接/注册表）、`git`（版本控制/变基/Worktree/提交）、`ide`（编辑器/终端/Sublime/Zed/Cursor/WT）、`agent`（AI客户端/CLI/模型供应商/密钥）、`browser`（浏览器/扩展/DevTools）、`dev`（语言/构建/uv/OOP/排版流水线/daemon）、`media`（音视频/下载/声学）。
- **槽位 3 `<scope>`（受控软件实体/技术范围，使同款软件自动聚类，严禁留空）**：
  - **受控兜底词**：`sys`（Windows系统功能）、`core`（跨软件基础模式/设计哲学）、`fs`（文件系统/Junction软链接/C盘空间/文件锁）、`cli`（通用命令行管道/守护进程）。
  - **常见软件实体**：`zed`、`cursor`、`vscode`、`sublime`、`smerge`、`terminal`、`terminus`、`atuin`、`pi`、`ahk`、`windhawk`、`everything`、`conhost`、`ps`、`uwp`、`mem`、`audio`、`uv`、`docx`、`wails`、`web`、`rebase`、`worktree`、`ssh`、`chrome`、`firefox`、`devtools`、`opencode`、`agy`、`agyman`、`dsh`、`ccswitch`、`yolo`、`alist` 等。
- **槽位 4 `<type>`（极简双轨，绝对收敛）**：
  `fix`（Type A 疑难排障，含报错直击/根因/抢救 SOP/验证）、`flow`（Type B 方案流水线，含场景/难点/自动化脚本/交付验收）。
- **槽位 5 `<slug>`（自解释主题短语）**：
  `[核心问题/技术词] + [解决动作/交付物]`，剔除“指南/实战”等空洞后缀，中文 ≤25 字。
- **虚拟路径与平滑分层契约**：
  平铺文件名 `<id>_<domain>_<scope>_<type>_<slug>.md` 实质为序列化的虚拟路径，映射未来分层路径 `<domain>/<scope>_<type>_<id>_<slug>.md`。当单域条目 ≥30 或总量 ≥150 篇时无损平移。

---

## 1. 知识库架构与设计哲学

本知识库采用**两级渐进式感知架构（Two-stage Progressive Disclosure）**，涵盖**疑难排障（Type A）**与**工程方案/自动化生成流水线（Type B）**两翼：

```text
kb-engineering-notes/
├── SKILL.md                                          # [Stage 1: 元数据与路由总纲] 本文件，负责总览与场景分流
├── 001_git_smerge_fix_SublimeMerge非相邻提交Squash合并重排.md # [Stage 2: 专项实战] 针对 GUI 提交合并
├── 002_git_rebase_fix_变基PermissionDenied文件锁排障与安全恢复.md # [Stage 2: 专项排障] 针对权限锁与抢救
├── 003_git_rebase_fix_变基Rescheduled队列挂起与冲突解析.md # [Stage 2: 专项机制] 针对队列重调度与避坑
├── 004_ide_cursor_flow_Cursor预览独立标签页切换.md # [Stage 2: 专项技巧] 针对编辑器 Markdown 预览模式
├── 005_ide_cursor_flow_Cursor免审批YOLO模式与沙箱网络.md # [Stage 2: 专项配置] 针对 Agent 免审批自动运行与网络管控
├── 006_git_worktree_flow_Worktree跨语言依赖复用与环境隔离权衡.md # [Stage 2: 专项权衡] 针对 Worktree 依赖共享与跨语言环境隔离
├── 007_dev_uv_flow_uv统一全机Python与新机引导复现.md # [Stage 2: 专项环境] 针对多 Python 来源统一与新机一键复现
├── 008_dev_zed_flow_Win下Java与Maven便携配置及Zed集成.md # [Stage 2: 专项配置] 针对 Java/Maven 便携隔离、C 盘防膨胀与 Zed 任务调试
├── 009_browser_chrome_fix_Chrome关闭标签丢失SNSS快照找回.md # [Stage 2: 专项抢救] 针对 SNSS 快照解析、独占锁规避与丢失窗口/固定标签找回
├── 010_ide_terminal_fix_CLI粘贴图片Kitty透传与BOM排障.md # [Stage 2: 专项配置] 针对 CLI 粘贴图片改键、Windows Terminal 扩展协议与 UTF-8 BOM 报错
├── 011_win_conhost_fix_计划任务控制台委托闪窗与conhost注册.md # [Stage 2: 专项排障] 针对计划任务触发 WT 标签页闪窗（控制台委托 handoff）与无窗口任务手动注册
├── 012_agent_yolo_flow_CLI执行模式辨析与免批YOLO配置.md # [Stage 2: 专项配置] 针对 CLI 执行模式、YOLO 权限免审批与配置面板
├── 013_media_audio_flow_降噪耳机人声泄露声学掩蔽与公有音频.md # [Stage 2: 专项实战] 针对降噪耳机人声泄露掩蔽、Commons API 下载与纯 Python 音频合成
├── 014_win_ahk_flow_Win单手盲切与抽屉式Toggle窗口AHK配置.md # [Stage 2: 专项效率] 针对 Windows 多常驻窗口盲切、左手单手 Toggle、PWA物理隔离与双模降级及 AutoHotkey v2 自动化
├── 015_dev_docx_flow_docx自动化生成试卷与排版流水线.md # [Stage 2: 专项实现] 针对教辅试卷生成、东亚字体分离(w:eastAsia)与 python-docx 精细排版流水线
├── 016_ide_terminus_fix_SublimeTerminus退格失效与原生终端集成.md # [Stage 2: 专项排障] 针对 Sublime 内置终端退格失效/中文吞字根因与原生侧边栏 PowerShell 扩展
├── 017_win_audio_fix_Win声卡爆音无声与虚拟音频抢占排查.md # [Stage 2: 专项排障] 针对设备占用、默认输出抢占与修复
├── 018_win_uwp_fix_Win代理下微软商店与UWP回环豁免.md # [Stage 2: 专项排障] 针对 CheckNetIsolation 回环豁免
├── 019_win_mem_fix_Win内存防死机与Pagefile提交归因优化.md # [Stage 2: 专项排障] 针对 Pagefile 调优与 Commit 归因
├── 020_win_fs_fix_Win系统C盘空间不足排查与软链接重定向.md # [Stage 2: 专项排障] 针对 C 盘清理与环境变量重定向
├── 021_agent_opencode_fix_opencode连接GLM鉴权401与端点排障.md # [Stage 2: 专项排障] 针对 GLM 401 报错与 key 映射
├── 022_ide_zed_fix_Zed语言服务器重命名与杀毒竞态.md # [Stage 2: 专项排障] 针对 LSP 下载失败与文件独占锁
├── 023_ide_zed_fix_Zed与IDEA外接ACP代理失效与进程堆积.md # [Stage 2: 专项排障] 针对 ACP 子进程池膨胀与代理失效
├── 024_ide_zed_fix_Zed面板InternalError会话中断与锁竞态.md # [Stage 2: 专项排障] 针对 Panel 报错与锁竞态归因
├── 025_ide_zed_fix_Zed会话丢失提取与SQLite解析抢救.md # [Stage 2: 专项抢救] 针对 SQLite 历史会话恢复
├── 026_ide_zed_flow_Zed项目级LSP白名单与内存优化.md # [Stage 2: 专项配置] 针对 LSP 项目白名单与内存优化
├── 027_git_ssh_flow_多Git账号SSH与IncludeIf配置.md # [Stage 2: 专项配置] 针对多账号 SSH 与 includeIf 切换
├── 028_ide_atuin_fix_Win终端Atuin历史同步与Profile修复.md # [Stage 2: 专项排障] 针对 Atuin 历史丢失与 profile 修复
├── 029_agent_ccswitch_flow_cc-switch数据库机制模型迁移与避坑指南.md # [Stage 2: 综合避坑] 针对 cc-switch 数据库机制、跨应用迁移与各端排障避坑
├── 030_ide_vscode_flow_VSCode扩展跨分支IDE手动搬运.md # [Stage 2: 专项配置] 针对扩展跨 IDE 搬运生效
├── 031_git_vscode_flow_VSCode底部面板GitLG配色调优.md # [Stage 2: 专项配置] 针对 GitLG 面板与分支配色
├── 032_win_ps_flow_Win便携PowerShell7绿色部署.md # [Stage 2: 专项配置] 针对 Pwsh7 绿色部署与环境变量
├── 033_ide_sublime_flow_YaHeiConsolasHybrid字体渲染与Sublime配置.md # [Stage 2: 专项配置] 针对字体安装与渲染调优
├── 034_ide_sublime_flow_Win11右键菜单注册Sublime与注册表快捷管理.md # [Stage 2: 专项配置] 针对 Win11 右键菜单注册表项
├── 035_ide_pi_fix_Pi终端改键与滚轮协议冲突修复.md # [Stage 2: 专项排障] 针对按键映射与滚轮误触修复
├── 036_agent_core_flow_各Agent客户端终端机制与GitBash切换.md # [Stage 2: 专项配置] 针对各 Agent 终端机制与 Git Bash
├── 037_browser_devtools_flow_opencode集成chrome-devtools-mcp浏览器控制.md # [Stage 2: 专项配置] 针对浏览器控制与 MCP 调试
├── 038_agent_zed_flow_Zed集成opencodeAgent思考档位与供应商迁移.md # [Stage 2: 专项配置] 针对 opencode 思考档位与供应商迁移
├── 039_agent_core_flow_无搜索API时DDG端点核查与一手信源收敛.md # [Stage 2: 专项流水线] 针对无 API 事实核查与 DDG 逆向
├── 040_dev_core_flow_AI辅助面向对象OOP重构与模式演进.md # [Stage 2: 专项流水线] 针对面向对象 OOP 重构与设计模式演进落地
├── 041_win_fs_fix_Win跨盘单文件软链接权限与Junction排障.md # [Stage 2: 专项排障] 针对 Windows 跨盘单文件链接、Junction 与开发者模式符号链接
├── 042_agent_core_fix_多Agent全局规则生效与CLI管道防挂起.md # [Stage 2: 专项排障] 针对多 Agent 全局规则生效验证、子进程标准输入管道挂起与目录隔离探针测试
├── 043_agent_opencode_fix_OpenCodeGo模型提速与关闭思考reasoningEffort.md # [Stage 2: 专项排障] 针对 OpenCode Go 模型访问提速、TTFT 归因与 reasoningEffort 调优
├── 044_ide_sublime_fix_SublimeMarkdown预览抢焦点与静默改键.md # [Stage 2: 专项排障] 针对 Sublime Markdown 预览切窗口自动跳浏览器抢焦点、MPE 源码 Fallback 缺陷与静默快捷键配置
├── 045_agent_core_flow_全机AI密钥清点与供应商指纹脱敏.md # [Stage 2: 专项流水线] 针对全机密钥清点、密钥指纹分组脱敏、SQLite 只读核查与残留识别
├── 046_win_everything_fix_Win进程启动来源取证与Everything闲置保护.md # [Stage 2: 专项排障] 针对 Windows 进程启动来源取证、UserAssist 与 Everything 闲置退出保护
├── 047_ide_sublime_fix_Sublime全局搜索穿透Gitignore慢查排障.md # [Stage 2: 专项排障] 针对全局搜索穿透 .gitignore、非Git数据目录穿透慢查、项目级 folder_exclude_patterns 隔离与 Whole Word 符号边界假阴性排障
├── 048_ide_terminal_fix_WinTerminal分屏窗格判定与关闭误触.md # [Stage 2: 专项排障] 针对 WT 分屏窗格识别、closePane 焦点语义与分屏键误触治理
├── 049_browser_chrome_fix_Chrome与Firefox静默安装迅雷与BT替代.md # [Stage 2: 专项排障] 针对浏览器静默注入扩展、注册表外源安装机制与免迅雷 BT 纯净下载
├── 050_win_sys_flow_平铺知识库文件名元数据规范与迁移SOP.md # [Stage 2: 专项流水线] 针对单目录平铺知识库文件名元数据缺失、Explorer排序割裂与批量迁移SOP
├── 051_dev_core_fix_离线Markdown向量检索混合漏检排障.md # [Stage 2: 专项排障] 针对FastEmbed+LanceDB离线向量检索搭建、语义稀释漏检与混合重排加权
├── 052_win_conhost_fix_PE控制台委托DefTerm断层与MCP无窗口镜像.md # [Stage 2: 专项排障] 针对独立版WT委托断层、aoci黑框弹窗与PE Subsystem 2 GUI无窗口镜像
├── 053_ide_terminal_fix_WinTerminal拆分窗格cd目录丢失与OSC99上报.md # [Stage 2: 专项排障] 针对 WT 拆分窗格与会话恢复 cd 目录丢失、ConPTY 隔离与 OSC 9;9 路径上报
├── 054_win_windhawk_fix_Win11任务栏输入指示图标隐藏与Windhawk代码注入.md # [Stage 2: 专项排障] 针对 25H2 输入指示图标无法原生隐藏、TSF 语言栏项在 explorer 内绘制与 Windhawk 注入隐藏
├── 055_win_sys_fix_划词工具CtrlC误杀终端与AltShift切语言排障.md # [Stage 2: 专项排障] 针对划词工具全局快捷键盲发 Ctrl+C 杀终端会话、黑名单作用域与进程别名陷阱、Windows 默认 Alt+Shift 切换语言注册表禁用
├── 056_agent_dsh_fix_DSH挂载MCP包装层内存膨胀治理与直连改造.md # [Stage 2: 专项排障] 针对 MCP 服务的 npx/uvx 包装层常驻进程与内存膨胀、profile patch 浅替换语义与直连入口改造
├── 057_win_ps_flow_常驻Pwsh替换为csc现场编译原生Win32与零conhost.md # [Stage 2: 专项流水线] 针对常驻 PowerShell 地板价与每 tick 开销、csc 现场编译原生 Win32 小程序与零 conhost 集成
├── 058_git_core_fix_Git批量提交高思考档分析瘫痪排障与灰色资产判决.md # [Stage 2: 专项排障] 针对 Git 批量提交 Agent 高思考档长考、灰色资产微观考古与提交流水线分析瘫痪
├── 059_media_alist_flow_百度网盘在线秒播与Alist聚合挂载提速.md # [Stage 2: 专项流水线] 针对百度网盘免客户端原画秒播、Alist 本地部署与 OAuth 挂载、公开分享外链转存与后台 P2P 防驻留
├── 060_ide_zed_fix_Zed终端无会话恢复agy历史ID丢失与选号恢复.md # [Stage 2: 专项排障] 针对 Zed 终端无会话恢复机制、agy 历史会话 ID 丢失、PowerShell 传参展开陷阱与交互式选号恢复器
├── 061_ide_terminal_fix_WinTerminal定制版PE图标损坏Defender误杀排障.md # [Stage 2: 专项排障] 针对 WT 定制版 PE 图标注入签名破损、触发 Defender 启发式木马 Bearfoos.A!ml 误杀与白名单排除
├── 062_win_sys_flow_WinGUI自动化能力阶梯与UIA元素点击验证.md # [Stage 2: 专项流水线] 针对 GUI 自动化能力阶梯（UIA/键盘/鼠标/OCR）、各技术栈无障碍树对照、最小化启动与 DPI 虚拟化及首次点击被吃三大坑
├── 063_win_sys_flow_Win无窗口服务快捷方式与自重启及PS5.1排障.md # [Stage 2: 专项流水线] 针对快捷方式无窗口启动常驻服务、端口反查幂等仲裁、WMI 脱离进程树自重启与页面自动重载，及 PS 5.1 六类静默失败链路
├── 064_win_chrome_fix_Win单按Alt抢焦点与豆包输入法右Alt语音透传.md # [Stage 2: 专项排障] 针对 Windows 单按 Alt 激活 Chrome 三点菜单抢焦点、豆包输入法长按右 Alt 语音识别上屏中断与 AutoHotkey vkE8 无害掩码静默拆弹
├── 065_win_fs_fix_Win文件外部句柄持有原子替换失败写入静默丢失.md # [Stage 2: 专项排障] 针对原子替换被句柄/映射拒绝、EMPER/Win32 5、上层设置静默丢失与 Restart Manager 反查持有者
├── 066_ide_fs_fix_同步publish重入前端覆盖层擦不掉与视图分叉.md # [Stage 2: 专项排障] 针对宿主 API 同步 publish 重入、旧 disposer no-op、覆盖层残留擦不掉、presenter 晚一拍撤回 inline 变量与三方对照取证
├── 067_dev_web_flow_本机Web应用自签cookie真机取证与浏览器进入.md # [Stage 2: 专项取证] 针对只认签名 cookie/启动令牌的本机 Web GUI、独立 profile 浏览器进不去时，只读存档密钥自签 cookie 取证与回收
├── 068_agent_agyman_fix_AGYManager切换失败target-conflict与汉化进程冲突.md # [Stage 2: 专项排障] 针对 Antigravity Manager 切换环境失败弹窗、target-conflict 进程误判冲突、汉化工具排查与 App/CLI 独立凭据体系
├── 069_agent_agy_fix_AGY桌面端会话覆写逆向与ConnectRPC热推送.md # [Stage 2: 专项排障] 针对 Antigravity 桌面端后台常驻 language_server.exe 内存缓存定时刷盘覆写离线修改、raw_summary Protobuf BLOB 优先级与官方 ConnectRPC 端口及 CSRF 鉴权热推送
├── 070_ide_amwhtml_fix_AnswerMeWithHTML架构与DarkReader暗黑冲突排障.md # [Stage 2: 专项架构与排障] 针对 Answer me with HTML 可视化技能全景架构、Dark Reader 等暗黑插件导致 SVG 矢量节点纯白刺眼与白底白字反色断层排障，及跨设备 Dark/Auto 模式决策与新机环境配置 SOP
├── 071_dev_wails_fix_WailsV3WebView2高内存治理与关窗生命周期重构.md # [Stage 2: 专项排障与架构重构] 针对 Go + Wails v3 (WebView2) 桌面小工具托盘常驻闲置内存高达 350MB 根因剖析、Chromium 参数剪枝、关窗销毁释放 WebView2 堆内存归还与按需毫秒级重建，闲置常驻内存暴降 88.5% (至 40MB 级)
├── 072_win_ahk_fix_Win11高频AltTab卡键停留在切换界面与AHK钩子修复.md # [Stage 2: 专项排障] 针对 Windows 11 高频 Alt+Tab 卡键停留在切换界面、Win32k 消息流时序破坏、A_MenuMaskKey 默认 Left Ctrl 碰撞触发 Sticky 粘滞模式与 AutoHotkey 低级钩子竞态彻底修复
├── 073_dev_cli_flow_CLI临时daemon按需拉起与零残留优雅关停.md # [Stage 2: 专项流水线] 针对 CLI 工具临时 daemon 按需拉起、空闲超时兜底与零残留优雅关停
├── 074_agent_pi_fix_Zed集成PiCodingAgent双层管道难用与openma内存直载SOP.md # [Stage 2: 专项排障] 针对 Zed 集成 Pi Coding Agent 双层管道难用排障与 openma-pi-acp SDK 内存直载 SOP
├── 075_dev_core_flow_发行版二进制嵌SHA溯源与上游源码取证.md # [Stage 2: 专项流水线] 针对发行版二进制嵌 SHA 溯源与上游对应版本源码取证流水线
├── 076_ide_zed_fix_Zed自定义ACP代理图标机制与注册表兜底.md # [Stage 2: 专项排障] 针对 Zed 自定义 ACP 代理图标来源机制与注册表兜底修复
├── 077_ide_zed_fix_Zed外部ACP线程不自动命名与首消息标题链路.md # [Stage 2: 专项排障] 针对 Zed 外部 ACP 线程不自动命名与首消息标题链路（横幅抢占 entry + agent 侧命名插件）
├── 078_ide_zed_fix_Zed信任表家目录污染致全盘监听与Defender死锁.md # [Stage 2: 专项排障·特大高危] 针对 Zed 信任表污染或ACP外部目录读取致C/D盘符滑坡挂载、File Watcher扫爆23万文件、内存暴涨与Defender死锁及--no-delegation源头绝缘SOP
├── 079_dev_core_flow_开源上游Issue高穿透提交与证据链设计SOP.md # [Stage 2: 专项流水线] 针对向头部开源项目(如Zed)提交高穿透力Bug Report的标准流程、置顶前言破局、内核级取证与三重对照实验设计
├── 080_agent_skills_fix_过度disable致Agent规范失盲与时序元数据防腐治理.md # [Stage 2: 专项排障·架构设计] 针对提级暴露技能过度加disable导致Kiro Spec/Plan规范失盲故障、时序软失效与知识库自愈元数据标准契约
├── 081_agent_dsh_fix_Cursor别名冲突致Grok误唤起与xai弹窗修复.md # [Stage 2: 专项排障] 针对 dsh 启动 Cursor ACP 裸命令 agent 与 xAI Grok CLI 命名冲突致强制弹窗 accounts.x.ai 排障
├── 082_dev_wails_flow_Go单二进制CLI与Wails双模融合架构及无窗排障SOP.md # [已转正 → sh-desktop-dual-channel，本文件仅存根] 原 Go 单二进制四位一体架构、任务栏PE图标、dev/release 通道隔离、图标双通道、开机自启门禁与无控制台排障
├── 083_ide_zed_fix_Zed外接ACP长会话生成完毕转圈卡死与PromptResponse丢失排障.md # [Stage 2: 专项排障] 针对 Zed 外接 ACP Agent（如 antigravity-acp）在经历 600+ 步长会话或 502 网络重试后，模型文本已全部输出但界面永久转圈、正文末尾挂三点脉冲、输入框死锁无法发送下一条及 $/cancel_request 缺失排障
├── 084_agent_pi_fix_飞书桥接keeper空转重生pi弹conhost黑窗.md # [Stage 2: 专项排障] 针对 Pi 飞书桥接保活器 CLI 入口解析失败 + PI_CLI_ENTRY 指向包装层致 child.pid ≠ owner pid、每 10 秒误杀重生 daemon，且 spawn 缺 windowsHide 在定制版 WT 委托断层下弹标题 pi 的裸 conhost 黑窗排障；并覆盖 pi 自更新迁移后旧全局入口失效与 settings.json 丢失 packages 致扩展静默不加载
├── 085_dev_bruno_flow_api_test_collection.md # [Stage 2: 专项流水线] 针对后端接口提取、Bruno OpenCollection YAML 测试集生成、认证隔离与语法校验
├── 086_dev_cmake_flow_trilang_lua_cpp_toolchain.md # [Stage 2: 专项流水线] 针对 C/C++/Lua 多语言工具链配置、FetchContent 集成 Lua 5.1、CMake Presets 模板与 MSVC /utf-8 排障
├── 087_git_gh_flow_repo_cleanup_audit.md # [Stage 2: 专项流水线] 针对 GitHub 账号仓库大扫除、fork 识别与超前提交比对、mirror 本地备份与 gh 批量清理
├── 088_browser_pwa_flow_localhost_standalone_window.md # [Stage 2: 专项流水线] 针对本地 Web 服务 Chromium SSB (--app 模式) 桌面独立窗口与 PWA 规范面板改造
├── 089_media_docx_flow_office_extract_media.md # [Stage 2: 专项流水线] 针对 Word/PPT/Excel 等 Office 文档内嵌原图与媒体资源 ZIP 拆包及无损提取流水线
├── 090_dev_sa_flow_sql_query_builder_extract.md # [Stage 2: 专项流水线] 针对复杂 SQLAlchemy Core 查询抽取为文本 SQL 模板与 Query Builder 层重构流水线
├── 091_ide_terminal_fix_WT选中文本CtrlC卡死与剪贴板锁争用排障.md # [Stage 2: 专项排障] 针对 WT 选中文本按 Ctrl+C 偶尔卡死数秒且未复制成功与剪贴板锁争用排障
├── 092_agent_ccswitch_fix_ClaudeCode升级参数冲突与OpenCode路由翻译.md # [Stage 2: 专项排障] 针对 Claude Code 升级参数冲突、OpenCode 协议分立与 CC Switch 路由代理翻译
├── 093_win_ql_flow_QuickLook便携部署与Markdown空格秒览.md # [Stage 2: 专项流水线] 针对 Typora 高内存替代、QuickLook 绿色便携部署与 Markdown 空格即时预览流水线
├── 094_agent_agy_flow_AGY外观RiderDark深色调色板映射与配置.md # [Stage 2: 专项配置] 针对 Antigravity 桌面端外观与 Rider Dark 调色板三元色映射及落盘
├── 095_win_ahk_flow_Win非侵入式AHK启动外挂与极客桌面自动化全景.md # [Stage 2: 专项流水线] 针对非侵入式窗口启动自动最大化外挂、WMI脱离无感热重载与AHK极客能力全景
├── 096_win_conhost_fix_Windhawk置底Hook与Groupy外壳穿透.md # [Stage 2: 专项排障] 针对 Windhawk 控制台置底 Hook 与 Stardock Groupy 外部多标签外壳穿透排障
├── 097_win_tinta_flow_Tinta原生极轻Markdown阅读与双栏编辑.md # [Stage 2: 专项流水线] 针对 Typora 终极替代、Tinta 纯 C++/Direct2D 极轻持久阅读与双栏编辑流水线
├── 098_win_fs_fix_父目录Low完整性继承致GUI闪退与安全警告排障.md # [Stage 2: 专项排障] 针对 Windows 父目录带 Low Mandatory Level 沙箱标签致新建 worktree/子目录继承低完整性、GUI 双击弹安全警告或点击运行闪退 ERROR_DLL_INIT_FAILED (0xC0000142) 排障与 icacls /setintegritylevel Medium 抢救及构建脚本防腐
├── 099_agent_dsh_flow_DSHWeb三层更新体系与插件升级及容器校验.md # [Stage 2: 专项流水线] 针对 DeepSeek Harness Web UI 三层更新（全局CLI/Profile远端依赖/本地模组软链）、Cordis 容器静态校验与后台常驻服务平滑重启
├── 100_win_sys_fix_Win11DWM显存泄漏AltTab失效与Winlogon平滑自愈.md # [Stage 2: 专项排障] 针对 Windows 11 DWM 显存泄漏逼近 1GB、Alt+Tab XAML 宿主 DirectComposition 表面创建失败完全失效与 Winlogon AutoRestartShell 0.5 秒平滑自愈
├── 101_win_sys_fix_Win11开始菜单固定区幽灵回填与强杀StartMenu自愈排障.md # [Stage 2: 专项排障] 针对 Windows 11 开始菜单固定区偶尔莫名其妙追加一整排官方默认应用（画图/计算器/OEM工具/纸牌）、强杀 StartMenuExperienceHost 破坏 start2.bin 触发崩溃自愈与 ContentDeliveryManager 静默推送通道加固
├── 102_browser_chrome_fix_扩展MatchPattern端口限制与tabs查询排障.md # [Stage 2: 专项排障] 针对 Chrome 扩展 Match Pattern 不支持在 host 中指定端口号致 tabs.query 抛 Invalid url pattern 语法错误排障与 JS 运行时精准前缀过滤
├── 103_browser_mujicv_fix_木及简历自定义CSS行首裁字与导出无样式修复.md # [Stage 2: 专项排障] 针对木及简历 JS 动态 margin-left 内联样式致预览/导出 PDF 行首裁字与自定义 CSS 导出不生效
└── 104_agent_dsh_fix_MCP浏览器自动化antd表单与文件上传踩坑.md # [Stage 2: 专项排障] 针对 chrome-devtools MCP 操作 React/AntD 站点的 el.click 无响应、菜单自动收起、受控组件写入、upload_file 沙箱路径与页面卡死处置
└── ...（后续顺次扩充）
```

- **文件名自解释（Self-describing Filename）**：每个知识文件均以`【编号 + 目标工具 + 核心问题场景 + 解决目标】`命名，AI 或开发者仅需浏览文件名列表，即可 100% 判断该文件是否适用于当前上下文，无需逐个打开探查。
- **排障与工程实现双翼**：
  - **Type A（疑难排障型）**：解决踩坑、文件锁、底层冲突，包含精准排查命令、界面现象对照和确定性操作 SOP；
  - **Type B（方案与生成流水线型）**：解决端到端工程实现、内容/试卷/文档自动化生成、样式排版引擎落地，包含业务输入输出、底层技术剖析、代码实现与交付验证模板。
- **条目即技能（隐形技能约定）**：每个 `<id>_<domain>_<scope>_<type>_<slug>.md` 条目在元数据上都视为一个独立 skill，必须带 skill-creator 规范的 frontmatter（`name` + `description`），正文保持单文件 ≤500 行、以 SOP 体为主。

### 条目即技能：为什么条目本身不被注册

靠的是两条命名约束，别去动它们：

- harness 只把名为 `SKILL.md` 的文件注册为技能；本目录条目一律用五段式 `<id>_<domain>_<scope>_<type>_<slug>.md`（如 `001_git_smerge_fix_...md`），因此条目永不单独注册；
- 注册入口只有总控文件 `SKILL.md` 一个（即当前可用 `/kb-engineering-notes` 点名的本技能），条目始终藏在它背后，由路由表按需索引。

### 条目元数据规范

- `name` 取 `kb-<英文主题短横线>`（如 `kb-docx-practice-generator`），**不带编号**：编号只是排序外壳，`name` 才是将来独立成 skill 时沿用的稳定标识，定了就别改，免得引用失效；
- `description` 按 skill-creator 写法：一句话功能语义 + “何时查阅”的触发场景，控制在 200 字符内，关键词尽量用用户真会说的症状词、技术词或目标交付词；
- 本目录的 description 面向**路由与检索**（根级技能与族路由器的预算为 1–1024 字符，故本文件采用长描述）。若某条目将来真要转正为全局技能，除改名建目录外，还必须按 `sh-skill-authoring-rules` 把 description 重写成点名触发式（≤70 字符、结尾 `点名使用`）。

### 条目状态门禁（status 语义与回写纪律）

条目 frontmatter 携带 `status` / `created` / `last_verified` 时序字段。**读取条目时先按 `status` 决定动作，再决定是否照做**——字段就在文件头，零额外调用即可判定：

| status | 含义 | 执行动作 |
|:---|:---|:---|
| `verified` | 已实测通过 | 直接照做 |
| `draft` | 暂行草案，未经多场景验证 | 可参考，须标注“未实测” |
| `suspect` | 近期结论或环境存疑 | 本会话先跑只读探测命令验证，再执行 |
| `deprecated` | 已废弃 | **禁止执行**，改用 `superseded_by` 指向的条目 |

回写纪律（借 `go_projects/kbman` 单文件 CLI，仅在**写入侧**调用，不在检索时调用）：

```bash
# 被证伪 / 环境变化导致方案失效：降级并追加现场证据
kbman report <id> --status suspect --reason "现象描述" --append "实际报错与环境变化"

# 本次实测通过：仅刷新验证时间，不改结论
kbman touch <id>
```

- `kbman` 由 `cd go_projects/kbman && go build -o kbman.exe ./cmd/kbman` 自建，默认目录已指向本知识库（经 `~/.gemini/config/skills` 链接链），无需传 `--dir`；
- `last_verified` 超过约 180 天未刷新时，默认按 `suspect` 对待（人工纪律，`kbman audit` 的时间衰减尚未实现）。

### 核心检索与防盲目新建硬约束（AI 检索铁律）

> ⚠️ **【查实体必查路由表，严禁裸扫文件名断定有无】**
> - **结构性背景**：随着核心技术实体（如 `ccswitch`、`zed`、`uv`、`worktree`、`opencode` 等）的手记在工程实践中不断生长，它们已天然演化为“**复合专题手记（Topic Hub）**”。条目内部高度集成了环境配置机制与多轮硬核排障（典型如 `029` 虽基础归类为 `_flow_`，但内部完整收敛了外键、上下文指示器、Codex 翻译丢 effort、密钥反噬及 OpenCode npm 校验死锁等多项重度 `fix`）；
> - **反盲区操作铁律**：
>   1. **检索严禁凭文件名盲猜**：凡遇到具体软件报错、环境疑难或用户询问“有没有相关知识库”时，**严禁仅凭文件名列表里的 `fix`/`flow` 单字或狭义 slug 盲目断定“没有”**；必须强制在总控 `SKILL.md` 的《场景路由表》中按具体技术实体关键词（如 `ccswitch`、`opencode`、`zed` 等）进行全文检索匹配；
>   2. **沉淀就地演进优于碎片新建**：在准备沉淀新条目前，必须先核查既有专题 Hub 是否存在。若既有条目可容纳该实战场景，一律以“日期增补”方式就地演进，坚决防止知识库因盲目新建单点条目而陷入碎片化与编号膨胀。

---

## 2. 场景路由表（快速匹配）

| 当前遇到的问题或诉求 | 建议读取的条目文档 | 典型现象 / 报错关键词 |
|:---|:---|:---|
| 想在 Sublime Merge 里把两个不相邻的提交合并为一个 | [`001_git_smerge_fix_SublimeMerge非相邻提交Squash合并重排.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/001_git_smerge_fix_SublimeMerge非相邻提交Squash合并重排.md) | 非相邻 commit, 拖拽没反应, Ctrl 多选, Move Commit Down, Squash / Fixup |
| 做了合并操作，界面没报错也没弹窗，怀疑没生效 | [`001_git_smerge_fix_SublimeMerge非相邻提交Squash合并重排.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/001_git_smerge_fix_SublimeMerge非相邻提交Squash合并重排.md) | 误以为没反应, 提交数量少, Stats 文件变化, HEAD 平移 |
| Windows 下变基失败，提示 `Permission denied` 无法写日志 | [`002_git_rebase_fix_变基PermissionDenied文件锁排障与安全恢复.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/002_git_rebase_fix_变基PermissionDenied文件锁排障与安全恢复.md) | `unable to append to logs/HEAD`, Permission denied, 文件锁占用, abort 回滚 |
| 变基失败后停留在 `(onto <hash>)` 状态，暂存区有残留文件 | [`002_git_rebase_fix_变基PermissionDenied文件锁排障与安全恢复.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/002_git_rebase_fix_变基PermissionDenied文件锁排障与安全恢复.md) | rebase in progress, Staged Files, git rebase --abort, 抢救工作区 |
| 变基提示 `It has been rescheduled`，todo 列表混乱 | [`003_git_rebase_fix_变基Rescheduled队列挂起与冲突解析.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/003_git_rebase_fix_变基Rescheduled队列挂起与冲突解析.md) | rescheduled, git-rebase-todo 重复 pick, 交互变基挂起 |
| Cursor / VS Code 预览 Markdown 默认在侧边栏，想用独立标签页全屏查看 | [`004_ide_cursor_flow_Cursor预览独立标签页切换.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/004_ide_cursor_flow_Cursor预览独立标签页切换.md) | Markdown 预览, Ctrl+Shift+V, 侧边栏, 独立标签页, Open Preview |
| Cursor Agent 总弹批准框，想开 YOLO 免审批 / 限制沙箱网络访问 | [`005_ide_cursor_flow_Cursor免审批YOLO模式与沙箱网络.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/005_ide_cursor_flow_Cursor免审批YOLO模式与沙箱网络.md) | Run Everything, YOLO, Auto-review, sandbox.json, networkPolicy, 批准 |
| 需开 Git Worktree 隔离开发，纠结依赖是否该软链接、担心环境与端口冲突 | [`006_git_worktree_flow_Worktree跨语言依赖复用与环境隔离权衡.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/006_git_worktree_flow_Worktree跨语言依赖复用与环境隔离权衡.md) | git worktree, 软链接, .venv, node_modules, target, editable 倒挂, WinError 32, sccache, pnpm, GOMODCACHE |
| 新电脑只装了 uv，要把全局 `python`/`pip` 与 `uv run` 项目工作流统一成同一套配置 | [`007_dev_uv_flow_uv统一全机Python与新机引导复现.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/007_dev_uv_flow_uv统一全机Python与新机引导复现.md) | uv_shim, .uv-global, UV_PYTHON, 一键引导, 新机复现, anaconda 卸载 |
| 全局 `pip install` 报 `externally-managed-environment`，或 venv 里 `python -m pip` 报 `No module named pip` | [`007_dev_uv_flow_uv统一全机Python与新机引导复现.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/007_dev_uv_flow_uv统一全机Python与新机引导复现.md) | PEP 668, externally-managed, No module named pip, seed pip |
| Windows 下安装 Java/Maven 导致 C 盘膨胀、Zed 编辑器硬编码 JDK 路径或缺乏调试能力 | [`008_dev_zed_flow_Win下Java与Maven便携配置及Zed集成.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/008_dev_zed_flow_Win下Java与Maven便携配置及Zed集成.md) | Java, Maven, C 盘空间, settings.xml, localRepository, Corretto, jdtls, tasks.json, JDWP, 远程调试 |
| Chrome「继续浏览上次打开的网页」只恢复了一个窗口，手动关闭的窗口（含固定标签页）整体找不回 | [`009_browser_chrome_fix_Chrome关闭标签丢失SNSS快照找回.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/009_browser_chrome_fix_Chrome关闭标签丢失SNSS快照找回.md) | 固定标签丢失, 只恢复一个窗口, 最近关闭, 继续浏览上次打开的网页 |
| Chrome 的 Sessions 快照文件被锁无法读取（Device or resource busy / Permission denied），想不重启就解析会话数据、提取固定标签清单 | [`009_browser_chrome_fix_Chrome关闭标签丢失SNSS快照找回.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/009_browser_chrome_fix_Chrome关闭标签丢失SNSS快照找回.md) | Device or resource busy, Sessions, Session_, Tabs_, SNSS, cmd5, 固定标签清单 |
| Antigravity CLI 或 Pi 终端中，粘贴图片快捷键 Alt+V 被占想改 Alt+Shift+V，改完终端没反应，或 keybindings.json 报 `invalid character '\ufeff'` | [`010_ide_terminal_fix_CLI粘贴图片Kitty透传与BOM排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/010_ide_terminal_fix_CLI粘贴图片Kitty透传与BOM排障.md) | 粘贴图片快捷键, edit.paste, app.clipboard.pasteImage, Alt+Shift+V, sendInput, 118;4u, Kitty CSI-u, ufeff, UTF-8 BOM, keybindings.json |
| Windows 计划任务/定时脚本每次触发时，已运行的 Windows Terminal 里闪出一个空白 PowerShell 标签页（“弹终端”），任务“隐藏”属性与 `-WindowStyle Hidden` 都无效 | [`011_win_conhost_fix_计划任务控制台委托闪窗与conhost注册.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/011_win_conhost_fix_计划任务控制台委托闪窗与conhost注册.md) | 弹终端, 闪窗, WT 标签页闪现, 控制台委托, handoff, conhost --headless, PseudoConsoleWindow, -WindowStyle Hidden 无效 |
| 需要一条命令手动注册/重配置“无窗口”计划任务（防止终端闪标签页），或任务目录搬移后动作路径失效 | [`011_win_conhost_fix_计划任务控制台委托闪窗与conhost注册.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/011_win_conhost_fix_计划任务控制台委托闪窗与conhost注册.md) | register_task.ps1, conhost --headless, New-ScheduledTaskAction, 手动配置, 幂等注册, $PSScriptRoot |
| Antigravity CLI 执行模式（plan/accept-edits）与免批 YOLO 权限混淆、状态栏无 yolo、/permissions 规则为空、/config 面板与免审启动参数配置 | [`012_agent_yolo_flow_CLI执行模式辨析与免批YOLO配置.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/012_agent_yolo_flow_CLI执行模式辨析与免批YOLO配置.md) | Antigravity CLI, YOLO, accept-edits, plan, /permissions, /config, Tool Permission, --dangerously-skip-permissions |
| 佩戴降噪耳机仍能听到人声谈话、轻音乐休止符间隙漏音打断心流，需要构建抗干扰声床、免鉴权下载公有领域名曲或合成立体声褐噪音/自然雨声 | [`013_media_audio_flow_降噪耳机人声泄露声学掩蔽与公有音频.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/013_media_audio_flow_降噪耳机人声泄露声学掩蔽与公有音频.md) | 降噪耳机, 隔绝人声, 听觉掩蔽, 褐噪音, Brown Noise, 白噪音, 雨声, Wikimedia Commons, 公有领域轻音乐, 萨蒂, 肖邦, 卡农, 巴赫 |
| Windows 常驻应用多（IDE/终端/浏览器/IM）、鼠标跨屏甩动疲劳、Alt+Tab 轮转顺序不稳定、PowerToys 快捷键误触冷启动、Chrome PWA独立应用与浏览器底层串台冲突、桌面端与Web版双模降级调度、AHK终端重载退出 | [`014_win_ahk_flow_Win单手盲切与抽屉式Toggle窗口AHK配置.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/014_win_ahk_flow_Win单手盲切与抽屉式Toggle窗口AHK配置.md) | AutoHotkey, AHK v2, 窗口切换, 盲切, 单手快捷键, Toggle, 前台置顶, 任务栏, PowerToys 缺陷, Chrome PWA 独立应用, 双模优先级降级, - Google Chrome 标题特征, PWA 串台, WMI 进程脱离 |
| 需要基于 python-docx 批量生成 Word 试卷或教辅练习题，处理东亚中文字体分离(w:eastAsia)、页边距、行间距微调、化学式上下标排版或自动化装配流水线 | [`015_dev_docx_flow_docx自动化生成试卷与排版流水线.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/015_dev_docx_flow_docx自动化生成试卷与排版流水线.md) | python-docx, 试卷生成, 举一反三, eastAsia, 宋体回退, 行距, 上下标, 批量生成流水线, Word 排版 |
| Sublime Text 终端插件 Terminus 中文吞字、按 Backspace 无法删除字符、侧边栏右键打开终端看似 PowerShell 实际是 CMD | [`016_ide_terminus_fix_SublimeTerminus退格失效与原生终端集成.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/016_ide_terminus_fix_SublimeTerminus退格失效与原生终端集成.md) | Sublime Text, Terminus, Backspace删不掉, 中文输入法, PSReadLine, Open Terminus here, Open PowerShell here, wt.exe |
| Windows 扬声器/耳机无声、高频或周期性噼啪爆音、默认音频输出设备被虚拟声卡（如 Voicemeeter）静默抢占 | [`017_win_audio_fix_Win声卡爆音无声与虚拟音频抢占排查.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/017_win_audio_fix_Win声卡爆音无声与虚拟音频抢占排查.md) | 声卡爆音, 无声, 默认设备抢占, 虚拟声卡, Voicemeeter, 音频端点, 独占模式 |
| 开启系统/梯子代理时，微软应用商店无法打开、UWP 应用无网络连接或无法初始化 | [`018_win_uwp_fix_Win代理下微软商店与UWP回环豁免.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/018_win_uwp_fix_Win代理下微软商店与UWP回环豁免.md) | 微软商店打不开, UWP 代理, 回环豁免, CheckNetIsolation, AppContainer, LoopbackExempt |
| 电脑频繁卡死或假死、没开大软件但物理内存使用率居高不下、不确定该不该加物理内存条 | [`019_win_mem_fix_Win内存防死机与Pagefile提交归因优化.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/019_win_mem_fix_Win内存防死机与Pagefile提交归因优化.md) | 内存防死机, 内存爆满, Commit Charge, 提交大小, Pagefile, 虚拟内存扩容, 内存条判断 |
| C 盘空间告急、红色预警、Temp/缓存/WSL 虚拟硬盘膨胀，需要无损安全腾挪空间 | [`020_win_fs_fix_Win系统C盘空间不足排查与软链接重定向.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/020_win_fs_fix_Win系统C盘空间不足排查与软链接重定向.md) | C 盘清理, 空间不足, 软链接重定向, mklink, 环境变量重定向, WSL 迁移, 清理缓存 |
| opencode 等工具调用智谱 GLM 模型接口报 401 身份验证失败、API Key 怎么配都不生效 | [`021_agent_opencode_fix_opencode连接GLM鉴权401与端点排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/021_agent_opencode_fix_opencode连接GLM鉴权401与端点排障.md) | GLM 401, opencode 鉴权失败, bigmodel, API Key 优先级, 编码端点冲突 |
| Zed 下载或更新语言服务器时报 `rename os error 5`、下载解压中断或由于杀毒软件占用卡死 | [`022_ide_zed_fix_Zed语言服务器重命名与杀毒竞态.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/022_ide_zed_fix_Zed语言服务器重命名与杀毒竞态.md) | Zed LSP 下载失败, rename os error 5, 杀毒竞态, 手工安装 LSP, 文件独占锁 |
| Zed 或 IntelliJ IDEA 外接 ACP agent（如 codex/antigravity）登录失败、代理/CA 证书失效或子进程池堆积吃满内存 | [`023_ide_zed_fix_Zed与IDEA外接ACP代理失效与进程堆积.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/023_ide_zed_fix_Zed与IDEA外接ACP代理失效与进程堆积.md) | ACP agent 登录失败, 代理不生效, 子进程池膨胀, 孤儿进程堆积, stdio 认证 |
| Zed Agent Panel 界面报 `Internal error`、`Invalid request` 或 `Session is closing`，不知从何定位 | [`024_ide_zed_fix_Zed面板InternalError会话中断与锁竞态.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/024_ide_zed_fix_Zed面板InternalError会话中断与锁竞态.md) | Agent Panel Internal error, Session is closing, telemetry.log, Zed.log 对齐, thread-writer-lock |
| Zed 崩溃或误操作导致历史对话列表空白、重要上下文找不回，需要底层数据恢复 | [`025_ide_zed_fix_Zed会话丢失提取与SQLite解析抢救.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/025_ide_zed_fix_Zed会话丢失提取与SQLite解析抢救.md) | Zed 会话丢失, sidebar_threads, SQLite 对话恢复, 会话归档抢救 |
| Zed 同时打开多个项目导致各个语言服务器全量拉起吃满内存，需要针对特定项目精细管控 LSP | [`026_ide_zed_flow_Zed项目级LSP白名单与内存优化.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/026_ide_zed_flow_Zed项目级LSP白名单与内存优化.md) | Zed LSP 白名单, .zed/settings.json, 按项目开 LSP, 内存优化 |
| 既有个人 GitHub 账号又有公司 GitLab 账号，SSH 密钥冲突或提交邮箱身份串号 | [`027_git_ssh_flow_多Git账号SSH与IncludeIf配置.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/027_git_ssh_flow_多Git账号SSH与IncludeIf配置.md) | GitHub GitLab 共存, 多 SSH Key, includeIf, 身份自动切换, .gitconfig 隔离 |
| Windows 下 Atuin 历史命令不同步、前导空格静默丢失、Ctrl+R 无法呼出或 PowerShell Profile 报错打架 | [`028_ide_atuin_fix_Win终端Atuin历史同步与Profile修复.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/028_ide_atuin_fix_Win终端Atuin历史同步与Profile修复.md) | Atuin 历史丢失, 前导空格, ignorespace, 静默丢弃, Ctrl+R 搜索历史, PSReadLine 冲突, profile.ps1 修复 |
| cc-switch 界面操作卡顿或需要直接通过脚本批量迁移/读写应用模型配置；**换 API Key / 换 token 后不生效或被回滚**；**添加 OpenCode 官方直连供应商（如 DeepSeek）报错「需要填写 npm 包和至少一个模型」无法添加** | [`029_agent_ccswitch_flow_cc-switch数据库机制模型迁移与避坑指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/029_agent_ccswitch_flow_cc-switch数据库机制模型迁移与避坑指南.md) | cc-switch SQLite, 直接修改供应商, 跨应用模型迁移, 绕过 UI 配置, 换密钥, 密钥轮换, 换 key, token 不生效, settings.json 被回写, npm 校验死锁, 只有配置中已有的同名供应商可以沿用默认定义, disabled_providers, live config 二元判定 |
| 在 Cursor、Antigravity IDE 或 Trae 中需要用到某个只有 VS Code 插件市场才有的扩展 | [`030_ide_vscode_flow_VSCode扩展跨分支IDE手动搬运.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/030_ide_vscode_flow_VSCode扩展跨分支IDE手动搬运.md) | VS Code 插件搬运, Cursor 安装离线扩展, Trae 扩展移植, extensions.json 注册 |
| VS Code 缺乏像 IntelliJ IDEA 那样直观清晰的 Git 提交树图谱，希望在底部面板集成 | [`031_git_vscode_flow_VSCode底部面板GitLG配色调优.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/031_git_vscode_flow_VSCode底部面板GitLG配色调优.md) | VS Code 提交图, GitLG, 分支配色, 底部面板终端, IDEA 视图复刻 |
| 新电脑没有管理员权限或不想污染系统，需要免安装绿色便携部署 PowerShell 7 | [`032_win_ps_flow_Win便携PowerShell7绿色部署.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/032_win_ps_flow_Win便携PowerShell7绿色部署.md) | PowerShell 7 绿色安装, Pwsh 便携部署, 零系统残留, 用户级环境变量 |
| Sublime Text 或 Sublime Merge 代码中文乱码、字体发虚或想使用清晰的等宽混合字体 | [`033_ide_sublime_flow_YaHeiConsolasHybrid字体渲染与Sublime配置.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/033_ide_sublime_flow_YaHeiConsolasHybrid字体渲染与Sublime配置.md) | YaHei Consolas Hybrid, Sublime 字体设置, 字体发虚, UI 字体补丁 |
| Windows 11 下希望为文件和文件夹添加“Open with Sublime Text”经典与新型右键菜单 | [`034_ide_sublime_flow_Win11右键菜单注册Sublime与注册表快捷管理.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/034_ide_sublime_flow_Win11右键菜单注册Sublime与注册表快捷管理.md) | Sublime 右键菜单, Win11 注册表右键, 经典右键菜单, Open with Sublime |
| 使用 Pi 终端时快捷键冲突、滚轮误触发历史命令或需要自定义按键动作 | [`035_ide_pi_fix_Pi终端改键与滚轮协议冲突修复.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/035_ide_pi_fix_Pi终端改键与滚轮协议冲突修复.md) | Pi 终端改键, 按键映射, 滚轮翻历史, 终端按键协议, keybindings |
| Windows 各 AI Agent 终端默认是 CMD 或 PowerShell，经常乱码或脚本语法报错，希望统一走 Git Bash | [`036_agent_core_flow_各Agent客户端终端机制与GitBash切换.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/036_agent_core_flow_各Agent客户端终端机制与GitBash切换.md) | Agent 终端乱码, 切换 Git Bash, Codex 终端设置, OpenCode 终端 |
| opencode 需要通过 chrome-devtools-mcp 控制本机浏览器，遇到远程端口连不上或握手失败 | [`037_browser_devtools_flow_opencode集成chrome-devtools-mcp浏览器控制.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/037_browser_devtools_flow_opencode集成chrome-devtools-mcp浏览器控制.md) | chrome-devtools-mcp, 浏览器自动化控制, opencode 浏览器插件, 调试端口 |
| Zed 的 opencode 插件思考档位失灵、服务进程断连或无法成功读取自定义 API 配置 | [`038_agent_zed_flow_Zed集成opencodeAgent思考档位与供应商迁移.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/038_agent_zed_flow_Zed集成opencodeAgent思考档位与供应商迁移.md) | Zed opencode, 思考档位, 供应商配置迁移, opencode 启动脚本 |
| 需要核实「某个公开信息到底有没有/是什么」（如某公司内部工具名），手上只有终端、没有搜索 API，且担心把「我没查到」误当「不存在」 | [`039_agent_core_flow_无搜索API时DDG端点核查与一手信源收敛.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/039_agent_core_flow_无搜索API时DDG端点核查与一手信源收敛.md) | 公开信息核查, 到底有没有, 第一方信源, DuckDuckGo HTML, html.duckduckgo.com, uddg 解包, SERP 降级页, 假阴性, site: 收敛, 是不是不存在 |
| 遗留系统代码腐化、大类长函数、嵌套分支过多，需进行面向对象 (OOP) 重构、消除条件分支、引入设计模式或提升工程内聚度 | [`040_dev_core_flow_AI辅助面向对象OOP重构与模式演进.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/040_dev_core_flow_AI辅助面向对象OOP重构与模式演进.md) | OOP 重构, 遗留代码, 代码坏味道, 接缝测试, 字符化测试, 策略模式, 工厂模式, 组合优于继承, 依赖倒置, 架构分层 |
| Windows 下跨盘单文件软链接失败、Junction 报目录名称无效、硬链接禁止跨卷、或符号链接权限不足 (WinError 1314) | [`041_win_fs_fix_Win跨盘单文件软链接权限与Junction排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/041_win_fs_fix_Win跨盘单文件软链接权限与Junction排障.md) | Windows 软链接, Symlink, Junction 目录联接, mklink /H 硬链接, WinError 1314, 开发者模式, SeCreateSymbolicLinkPrivilege, 单文件跨盘链接 |
| 多 Agent (Pi/Claude/OpenCode/AGY) 全局规则验证、CLI 命令行调用卡死 600s 超时、管道 stdin 未闭合或需隔离测试 | [`042_agent_core_fix_多Agent全局规则生效与CLI管道防挂起.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/042_agent_core_fix_多Agent全局规则生效与CLI管道防挂起.md) | 多 Agent 全局规则, CLI 管道挂起, readPipedStdin, 600s 超时, < NUL, Print Mode, 隔离探针测试, GLOBAL.md 生效验证 |
| OpenCode Go 模型（deepseek-v4.1-flash 等）响应慢、首字延迟高，纠结要不要改代理/Console 配置，或想关掉思考提速 | [`043_agent_opencode_fix_OpenCodeGo模型提速与关闭思考reasoningEffort.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/043_agent_opencode_fix_OpenCodeGo模型提速与关闭思考reasoningEffort.md) | opencode-go, OpenCode Go, deepseek-v4.1-flash, TTFT, 首字延迟, reasoningEffort none, x-opencode-session, MissingSessionID, prompt cache, 前缀缓存, variant |
| Sublime Text 打开 Markdown 后切窗口频繁跳浏览器抢焦点、或寻找更舒适的 Markdown 阅读与预览方案（排版美化/双栏分屏/免弹窗静默预览/终端阅读） | [`044_ide_sublime_fix_SublimeMarkdown预览抢焦点与静默改键.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/044_ide_sublime_fix_SublimeMarkdown预览抢焦点与静默改键.md) | Sublime Text, MarkdownPreviewEnhanced, 抢焦点, 自动跳转浏览器, MarkdownPreview, Shift+Alt+M, MarkdownEditing, MarkdownLivePreview, Terminus glow, minihtml, 预览插件选型 |
| 想把某厂商 API Key 收敛到只留一个工具、或盘点全机有哪些地方配了同一个 key、怀疑「清干净了」其实还有残留 | [`045_agent_core_flow_全机AI密钥清点与供应商指纹脱敏.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/045_agent_core_flow_全机AI密钥清点与供应商指纹脱敏.md) | 密钥清点, key 收敛, 只保留一个工具, API Key 残留, LegacyApiKeys 迁移槽, 密钥指纹分组, sha256 分组, SQLite 只读核查, immutable=1, os.walk 跑飞, UnicodeEncodeError gbk, 环境变量没清, 泄露面盘点 |
| 想查明 Windows 后台某个常驻程序（如 Everything）是谁在什么时间拉起的、排查后台驻留与闲置退出保护漏洞 | [`046_win_everything_fix_Win进程启动来源取证与Everything闲置保护.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/046_win_everything_fix_Win进程启动来源取证与Everything闲置保护.md) | 进程启动来源取证, 谁拉起的, UserAssist, Everything 驻留, idle_exit, 永生实例, 登录会话 |
| Sublime Text 全局搜索速度暴跌扫描数十万文件、穿透 `.gitignore` / 非 Git 数据目录（如 AppData），或搜索 `--flag` 等符号参数遭遇 Whole Word 假阴性 0 匹配 | [`047_ide_sublime_fix_Sublime全局搜索穿透Gitignore慢查排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/047_ide_sublime_fix_Sublime全局搜索穿透Gitignore慢查排障.md) | Sublime Text, Find in Files, Use Gitignore, node_modules 慢查, Unable to open file, binary_file_patterns, project filters, folder_exclude_patterns, Whole Word, 单词边界, \b, 符号前缀, 假阴性 |
| 一个 Windows Terminal 窗口里文字被竖/横线切成几块，不知道哪块能关、怕关掉连 agent 会话一起杀，或误触分屏键后想收场 | [`048_ide_terminal_fix_WinTerminal分屏窗格判定与关闭误触.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/048_ide_terminal_fix_WinTerminal分屏窗格判定与关闭误触.md) | Windows Terminal 分屏, 窗格 pane, 右侧窗格关不掉, Ctrl+Shift+W, ClosePane, 焦点窗格, alt+shift+plus 误触, SwitchToTab3, ctrl+alt+4, defaults.json, Move pane to new window, Toggle pane zoom |
| Chrome 或 Firefox 自动静默安装迅雷下载插件、扩展删除了又死灰复燃，或需免迅雷客户端纯净下载种子/磁力链 | [049_browser_chrome_fix_Chrome与Firefox静默安装迅雷与BT替代.md](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/049_browser_chrome_fix_Chrome与Firefox静默安装迅雷与BT替代.md) | 迅雷插件, 自动安装, ChromeExtensionCache, xl_ext_chrome, NativeMessagingHosts, 注册表残留, 裸磁力链, qBittorrent, Tracker加速, 免迅雷下载 |
| 知识库平铺文件越来越多（50+）、Windows Explorer 排序割裂无聚合、文件名太长被截断、机器无法直接提取分类元数据 | [050_win_sys_flow_平铺知识库文件名元数据规范与迁移SOP.md](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/050_win_sys_flow_平铺知识库文件名元数据规范与迁移SOP.md) | 平铺目录, 文件命名规范, 元数据嵌入, Explorer排序, 正则提取, 受控词典, 批量重命名, DryRun, 回滚SOP |
| 本地文档/技能库离线语义检索搭建（FastEmbed+LanceDB+Watchdog）、专有技术词检索遭遇语义稀释漏检、切块挤占或前端 SyntaxError 假死 | [051_dev_core_fix_离线Markdown向量检索混合漏检排障.md](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/051_dev_core_fix_离线Markdown向量检索混合漏检排障.md) | 本地语义检索, FastEmbed, LanceDB, bge-small-zh, 混合检索, Hybrid Search, 语义稀释, Lexical Boost, 关键词加权, Watchdog 防抖, Group-by-File, 默认折叠, WinError 10048, 离线 RAG |
| 使用独立定制版 Windows Terminal 时启动 Agent 强弹微软原版 WT、绕过后弹黑框 conhost 窗口、或原生 PE 二进制 MCP 服务无窗口运行架构 | [052_win_conhost_fix_PE控制台委托DefTerm断层与MCP无窗口镜像.md](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/052_win_conhost_fix_PE控制台委托DefTerm断层与MCP无窗口镜像.md) | 控制台委托, DefTerm 断层, 原版 WT 弹窗, conhost 黑框, aoci.exe 弹窗, aociw.exe, PE Subsystem 2 GUI, 便携版终端断层, MSIX COM CLSID, 孤儿控制台 |
| Windows Terminal 拆分窗格或会话恢复在 cd 切换目录后，重启依然记不住新目录（退回初始路径），或拆分新窗格无法继承当前目录 | [`053_ide_terminal_fix_WinTerminal拆分窗格cd目录丢失与OSC99上报.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/053_ide_terminal_fix_WinTerminal拆分窗格cd目录丢失与OSC99上报.md) | Windows Terminal 拆分选项卡, 记不住目录, cd 重启还原, persistedWindowLayout, state.json, OSC 9;9, OSC 99, prompt, startingDirectory, CWD 上报, 拆分继承目录 |
| Windows 11 任务栏常驻「输入指示」图标（豆包输入法头像、`英` 语言栏）删不掉：设置里没有「输入指示器」、改 CTF\LangBar 注册表无效、杀输入法进程无效，按 Win+Space 后还会自己长回来 | [`054_win_windhawk_fix_Win11任务栏输入指示图标隐藏与Windhawk代码注入.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/054_win_windhawk_fix_Win11任务栏输入指示图标隐藏与Windhawk代码注入.md) | 任务栏输入指示, 豆包头像图标, 英 图标删不掉, 输入指示器 找不到, 25H2 语言栏, CTF\LangBar, ShowStatus 被改回, tsf-oime.dll, TSF 语言栏项, explorer 内绘制, Win+Space 出现, Windhawk, taskbar-tray-system-icon-tweaks, hideLanguageBar, hideLanguageSupplementaryIcons |
| 终端按快捷键被当成 Ctrl+C 杀会话或清行、划词工具（Manggo等）黑名单失效、或按完快捷键系统静默切为纯英文美式键盘打不出中文 | [`055_win_sys_fix_划词工具CtrlC误杀终端与AltShift切语言排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/055_win_sys_fix_划词工具CtrlC误杀终端与AltShift切语言排障.md) | Manggo, 划词翻译, 盲发 Ctrl+C, SendInput, 终端中断, SIGINT, Resume with -c, 黑名单失效, wt.exe 别名陷阱, WindowsTerminal.exe, Alt+Shift, 切语言, 纯英文键盘, HKL 0x4090409, 语言热键禁用, Keyboard Layout Toggle, 00000070 |
| Agent 客户端进程树里每挂一个 MCP 服务就多出一串 `cmd → node → cmd → node → conhost`，内存比"刚启动"多出几百 MB、单条链路子树能占 300MB+ | [`056_agent_dsh_fix_DSH挂载MCP包装层内存膨胀治理与直连改造.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/056_agent_dsh_fix_DSH挂载MCP包装层内存膨胀治理与直连改造.md) | MCP 进程数, npx 包装层, npx-cli 108MB, uvx, uv 两层, conhost, 常驻内存, 子树 327MB, 内存降不下来, 包装进程不退出, tools/list 比对 |
| 想改 MCP 服务启动命令或覆盖包自带的 MCP 条目，改完 `serverName` 丢了 / 不知道是否生效 / 纠结要不要重启 | [`056_agent_dsh_fix_DSH挂载MCP包装层内存膨胀治理与直连改造.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/056_agent_dsh_fix_DSH挂载MCP包装层内存膨胀治理与直连改造.md) | profile patch, cordis.patch.yml, config 浅替换, serverName 丢失, dsh --dump-config, 影子 profile, Junction 删除陷阱, MCP 热重挂, 插件要重启 |
| 想按命令行关键字批量杀进程，结果把自己或宿主终端一起杀了（执行器报 Job runner 异常退出） | [`056_agent_dsh_fix_DSH挂载MCP包装层内存膨胀治理与直连改造.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/056_agent_dsh_fix_DSH挂载MCP包装层内存膨胀治理与直连改造.md) | CommandLine 匹配, Stop-Process 自杀, Windows Job runner exited 4294967295, -File 形态匹配, 排除自身 PID |
| 某个常驻 PowerShell 看护/轮询脚本吃 100MB+ 内存和几个点 CPU（窗口记忆、看门狗、状态监视），想换成原生小工具 | [`057_win_ps_flow_常驻Pwsh替换为csc现场编译原生Win32与零conhost.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/057_win_ps_flow_常驻Pwsh替换为csc现场编译原生Win32与零conhost.md) | 常驻 PowerShell, 内存 106MB, 每 tick 10ms, 4% 单核, Add-Type, cmdlet 反射开销, 换原生, 原生小程序 |
| 想给 Windows 写个不装 SDK 的常驻小工具，或用 csc 现场编译 C# 却报语法错误 | [`057_win_ps_flow_常驻Pwsh替换为csc现场编译原生Win32与零conhost.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/057_win_ps_flow_常驻Pwsh替换为csc现场编译原生Win32与零conhost.md) | csc.exe, Framework64 v4.0.30319, C# 5 语法限制, 字符串插值报错, target:winexe, platform:x64, 编译缓存, sha256 指纹, OpenProcess, WaitForSingleObject |
| 明明设了 `windowsHide` 还是多出 `conhost.exe`；或窗口几何恢复在缩放屏上位置错位 | [`057_win_ps_flow_常驻Pwsh替换为csc现场编译原生Win32与零conhost.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/057_win_ps_flow_常驻Pwsh替换为csc现场编译原生Win32与零conhost.md) | conhost 仍在, windowsHide 无效, SW_HIDE 不等于不分配控制台, GUI 子系统, DPI 虚拟化, dpiAware 错位, SetWindowPos, GetSystemMetrics 虚拟屏, EnumWindows GC.KeepAlive |
| 用户下达批量提交/交付指令（如"提交全部代码"），Agent 在高思考档下陷入长达数分钟的长考停滞、反复反查非代码文件尺寸或把提交流水线当成全库重构审计 | [`058_git_core_fix_Git批量提交高思考档分析瘫痪排障与灰色资产判决.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/058_git_core_fix_Git批量提交高思考档分析瘫痪排障与灰色资产判决.md) | Git 批量提交, 分析瘫痪, Analysis Paralysis, 高思考档, 思考超时, 灰色资产, test_*.png, 运行时产物误判, 提交流水线, 深度审计混淆, 10秒收敛 |
| 想查看或下载百度网盘视频/大文件，不想装官方客户端被偷跑 P2P 上行，或需用 PotPlayer/VLC 原画免下载秒播公开分享外链 | [`059_media_alist_flow_百度网盘在线秒播与Alist聚合挂载提速.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/059_media_alist_flow_百度网盘在线秒播与Alist聚合挂载提速.md) | 百度网盘, 百度云, 免客户端秒播, Alist, Alist 挂载, 百度网盘 OpenAPI, refresh_token, PotPlayer 秒播, HTTP Range, 偷跑上行, P2P 提速清理, 分享外链转存, errno -7 |
| Zed 重启后终端空白丢失上一轮 agy 会话 ID，或在 PowerShell 脚本传参时报 `conversation "@{Id=...}.Id" not found`，想按项目查看带业务标题的会话清单并交互式选号秒恢复 | [`060_ide_zed_fix_Zed终端无会话恢复agy历史ID丢失与选号恢复.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/060_ide_zed_fix_Zed终端无会话恢复agy历史ID丢失与选号恢复.md) | Zed终端, 会话恢复, Session Restoration, 屏幕清空, agy, agy -c, conversationId, 传参展开陷阱, agy-list, agl, history.jsonl, conversation_summaries.db, AI标题提取, 交互选号 |
| 定制版 Windows Terminal 突然消失、桌面/任务栏快捷方式提示“WindowsTerminal.exe 已经更改或移动”、Defender 报毒 Trojan:Win32/Bearfoos.A!ml | [`061_ide_terminal_fix_WinTerminal定制版PE图标损坏Defender误杀排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/061_ide_terminal_fix_WinTerminal定制版PE图标损坏Defender误杀排障.md) | WindowsTerminal.exe 已经更改或移动, 是否删除该快捷方式, Trojan:Win32/Bearfoos.A!ml, Defender误杀, 隔离区还原, ExclusionPath, PE图标签名损坏 |
| 想用脚本或 Agent 自动操作/验证 Windows 桌面软件（点按钮、切页签、截图取证），或想搞清楚 WebView2 与原生控件分别怎么被自动化、“是不是只能模拟鼠标” | [`062_win_sys_flow_WinGUI自动化能力阶梯与UIA元素点击验证.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/062_win_sys_flow_WinGUI自动化能力阶梯与UIA元素点击验证.md) | UIA, UI Automation, InvokePattern, 无障碍树, AXTree, 自动化能力阶梯, 模拟鼠标, mouse_event, SendInput, 坐标点击, Agent 自验证 GUI, EnumWindows |
| 自动化点击没反应/点不准、截图缺一块、窗口尺寸诡异（199x34）、窗口莫名最小化启动、坐标整体偏移 | [`062_win_sys_flow_WinGUI自动化能力阶梯与UIA元素点击验证.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/062_win_sys_flow_WinGUI自动化能力阶梯与UIA元素点击验证.md) | DPI 虚拟化, SetProcessDPIAware, 首次点击被吃, 前台激活, SetForegroundWindow, PrintWindow, PW_RENDERFULLCONTENT, ShowWindow SW_RESTORE, MainWindowHandle 不对 |
| 想做个桌面快捷方式：双击就启动本地常驻 Web 服务，且全程不弹黑框、不占终端窗口 | [`063_win_sys_flow_Win无窗口服务快捷方式与自重启及PS5.1排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/063_win_sys_flow_Win无窗口服务快捷方式与自重启及PS5.1排障.md) | 一键启动, 快捷方式, 不弹黑框, 无窗口启动, conhost, wscript Run 0, CreateNoWindow, WindowStyle Hidden, 双击启动服务 |
| 直连 `.lnk` 到 powershell 仍闪窗；服务已在运行时再点一次会撞端口 `EADDRINUSE`；想做到"在跑就只开界面" | [`063_win_sys_flow_Win无窗口服务快捷方式与自重启及PS5.1排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/063_win_sys_flow_Win无窗口服务快捷方式与自重启及PS5.1排障.md) | 闪窗, EADDRINUSE, 端口已占用, 幂等启动, 端口反查, Get-NetTCPConnection OwningProcess, 已经在跑, reuse |
| 给本地 Web 服务做"重启自己"按钮：点完页面卡在重启中不刷新、服务带上了黑框窗口、或重启后起不来 | [`063_win_sys_flow_Win无窗口服务快捷方式与自重启及PS5.1排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/063_win_sys_flow_Win无窗口服务快捷方式与自重启及PS5.1排障.md) | 自重启, 重启按钮, 卡在等待重启, 需要手动刷新, 重启后黑框, 无窗口性质丢失, listener is back, WMI Win32_Process Create, 脱离进程树, taskkill /T 不向上 |
| PowerShell 脚本报 `The Try statement is missing its Catch or Finally block` 但 try/catch 明明是对的；或 5.1 下中文注释导致解析崩溃 | [`063_win_sys_flow_Win无窗口服务快捷方式与自重启及PS5.1排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/063_win_sys_flow_Win无窗口服务快捷方式与自重启及PS5.1排障.md) | The Try statement is missing, Unexpected token, UTF-8 无 BOM, 中文注释, 编码误读, GBK 解码, 纯 ASCII 脚本, ParseFile 校验 |
| `Start-Process` 报 `Item has already been added. Key in dictionary: 'NO_PROXY'`；或 `EnvironmentVariables` 操作报 null-valued / null array | [`063_win_sys_flow_Win无窗口服务快捷方式与自重启及PS5.1排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/063_win_sys_flow_Win无窗口服务快捷方式与自重启及PS5.1排障.md) | NO_PROXY no_proxy 重复键, Item has already been added, Start-Process 不可用, ProcessStartInfo EnvironmentVariables null, cannot index into a null array, Process.Start 替代 |
| 生成的 `.bat`/`.cmd` 内容看起来对但执行毫无反应；或 `Set-Content` 写数组被分号连成一行、`rem` 注释吞掉命令 | [`063_win_sys_flow_Win无窗口服务快捷方式与自重启及PS5.1排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/063_win_sys_flow_Win无窗口服务快捷方式与自重启及PS5.1排障.md) | Set-Content 数组分号连接, rem 吞命令, bat 不执行, 退出码 1 无输出, WriteAllText CRLF, 反引号续行误判 |
| 脚本"完全没执行"、连第一行日志都没有，但调用方看到进程创建成功；或日志文件被占用导致新服务起不来 | [`063_win_sys_flow_Win无窗口服务快捷方式与自重启及PS5.1排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/063_win_sys_flow_Win无窗口服务快捷方式与自重启及PS5.1排障.md) | NamedParameterNotFound, 参数名不匹配, 参数绑定阶段终止, 无任何日志, WMI 返回 0 不代表成功, 重定向到文件抓错, 日志文件被占用, being used by another process, 日志按端口隔离 |
| 单按或松开 Alt / 右 Alt 键导致 Chrome 右上角三点菜单被高亮选中、打字光标丢失、或豆包输入法长按右 Alt 语音识别松手后无法正常上屏 | [`064_win_chrome_fix_Win单按Alt抢焦点与豆包输入法右Alt语音透传.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/064_win_chrome_fix_Win单按Alt抢焦点与豆包输入法右Alt语音透传.md) | Chrome 三点菜单, 自定义及控制 Google Chrome, 按 Alt 选中, 抢焦点, 光标丢失, 豆包输入法, 右 Alt, RAlt, 语音输入上屏失败, AutoHotkey, AHK vkE8, SC_KEYMENU, 菜单激活屏蔽 |
| 应用设置点了没反应/自动跳回原值、刷新后不生效，日志里是 `EPERM ... rename *.tmp -> <配置文件>`，而文件"明明能写" | [`065_win_fs_fix_Win文件外部句柄持有原子替换失败写入静默丢失.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/065_win_fs_fix_Win文件外部句柄持有原子替换失败写入静默丢失.md) | EPERM operation not permitted, rename tmp, win32 5 Access is denied, 原子替换失败, MoveFileEx REPLACE_EXISTING, 设置静默丢失, revision 不变, HTTP 200 但没落盘, 临时文件+rename |
| 文件被谁占着完全看不出来（编辑器无标签、任务管理器无句柄），关标签页与重启程序都没用，想按文件反查持有进程 | [`065_win_fs_fix_Win文件外部句柄持有原子替换失败写入静默丢失.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/065_win_fs_fix_Win文件外部句柄持有原子替换失败写入静默丢失.md) | 谁占着文件, 文件锁, 句柄反查, Restart Manager, RmGetList, handle.exe 替代, 看不到占用, 关标签页无效, 重启又回来, last_session |
| Agent/编辑器会话把配置目录（`~/.dsh`、`~/.config`）当上下文长期持有，导致该目录下配置文件的写入持续失败 | [`065_win_fs_fix_Win文件外部句柄持有原子替换失败写入静默丢失.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/065_win_fs_fix_Win文件外部句柄持有原子替换失败写入静默丢失.md) | ACP agent 会话, acp_thread opening file, 上下文占用文件, 删除会话, Zed db.sqlite editors 表, 孤儿 editor 行, opencode 会话, 配置目录别交给 agent |
| 主题/皮肤/覆盖层切回浅色后页面仍是旧样式，行内提示却说"当前基座是浅色"，刷新偶尔好、一旦触发就再点也不回来 | [`066_ide_fs_fix_同步publish重入前端覆盖层擦不掉与视图分叉.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/066_ide_fs_fix_同步publish重入前端覆盖层擦不掉与视图分叉.md) | 切主题不生效, 覆盖层擦不掉, overrideTokens, 旧 disposer no-op, 同步 publish 重入, 视图与渲染分叉, inline CSS 变量残留, presenter 晚一拍, 受限擦除, 在途守卫 |
| 页面配色半套：面板是深色、个别卡片仍是浅灰，属性标记与计算变量互相矛盾，控制台无任何报错 | [`066_ide_fs_fix_同步publish重入前端覆盖层擦不掉与视图分叉.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/066_ide_fs_fix_同步publish重入前端覆盖层擦不掉与视图分叉.md) | 半套主题, dark token 叠浅色结构, data-ds-dark-theme 缺失, 静态色与别名色分叉, getComputedStyle 取证, Maximum call stack size exceeded, 死循环自激 |
| 本机 Web GUI 只回 `authentication required; reopen the URL printed by …`，自动化浏览器（独立 profile）没有登录态，进不去看真实 DOM | [`067_dev_web_flow_本机Web应用自签cookie真机取证与浏览器进入.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/067_dev_web_flow_本机Web应用自签cookie真机取证与浏览器进入.md) | 401, dsh web authentication required, launch token, ?token=, 签名 cookie, HMAC, 凭据库 secret, base64url, authority, 真机取证 |
| 想把自动化浏览器的会话搬进目标站点：只有磁盘上的存档密钥，横幅里的令牌已经滚没了 | [`067_dev_web_flow_本机Web应用自签cookie真机取证与浏览器进入.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/067_dev_web_flow_本机Web应用自签cookie真机取证与浏览器进入.md) | document.cookie 自签, HttpOnly 只挡读取, cookie 按 host 不按端口, 跨源脚本注入, CORS, 密钥不回显, 取证后回收 cookie |
| Antigravity Manager 切换环境报错“切换账号失败：操作失败，请查看诊断详情后重试”；日志报 `target-conflict`、`ANTIGRAVITY_PROCESS_FAILED`、`stage: client-selection` | [`068_agent_agyman_fix_AGYManager切换失败target-conflict与汉化进程冲突.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/068_agent_agyman_fix_AGYManager切换失败target-conflict与汉化进程冲突.md) | Antigravity Manager, 切换账号失败, 操作失败请查看诊断详情后重试, target-conflict, ANTIGRAVITY_PROCESS_FAILED, client-selection, launch-preflight, antigravity-hans-gui, 汉化工具, 切换到 Antigravity, 共享账号, agy cli 凭据, gemini:antigravity |
| 疑问 Antigravity App 桌面版与 Antigravity CLI 是否共享登录账号；想了解 Manager 中 classic/ide/agy 三端凭据存储机制与多设备登录风控 | [`068_agent_agyman_fix_AGYManager切换失败target-conflict与汉化进程冲突.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/068_agent_agyman_fix_AGYManager切换失败target-conflict与汉化进程冲突.md) | antigravity app 共享账号, agy cli 账号, Windows 凭据管理器, state.vscdb, 多设备登录, 多网络登录, 五小时限额, Five Hour Limit, 账号风控 |
| Antigravity 桌面端会话改名不生效、离线改写 SQLite 数据库后被后台定时覆写回滚英文；或侧边栏标题看着依然是旧英文 | [`069_agent_agy_fix_AGY桌面端会话覆写逆向与ConnectRPC热推送.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/069_agent_agy_fix_AGY桌面端会话覆写逆向与ConnectRPC热推送.md) | Antigravity 桌面端改名, 会话标题汉化, language_server.exe, background reconciliation, 幽灵覆写, raw_summary BLOB, Protobuf Wire, ConnectRPC, UpdateConversationAnnotations, csrf_token, 侧边栏没刷新, Ctrl+R 重载 |
| 逆向 Antigravity 核心服务与动态端口通信：如何从运行中常驻进程提取 CSRF Token 并调用官方 RPC 实时热推送数据 | [`069_agent_agy_fix_AGY桌面端会话覆写逆向与ConnectRPC热推送.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/069_agent_agy_fix_AGY桌面端会话覆写逆向与ConnectRPC热推送.md) | Antigravity 逆向, language_server 端口, WMI 提取 csrf_token, Exa LanguageServerService, UpdateConversationAnnotations, StreamCascadeSummariesReactiveUpdates, 动态端口探测 |
| Answer me with HTML 可视化技能生成的页面与 Dark Reader 等暗黑插件冲突，流程图方块/时序图角色出现纯白刺眼大方块、白底白字看不清；或想了解该技能架构与跨电脑新环境如何配置 | [`070_ide_amwhtml_fix_AnswerMeWithHTML架构与DarkReader暗黑冲突排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/070_ide_amwhtml_fix_AnswerMeWithHTML架构与DarkReader暗黑冲突排障.md) | Answer me with HTML, am.mjs, Dark Reader, 暗黑插件冲突, SVG 反色失败, 白底白字, 刺眼白块, flow 节点发白, am config set mode dark, config.json, 新电脑配环境, 跨环境配置决策, mode dark, mode auto, 离线单文件 HTML, Dagre 布局 |
| Go + Wails v3 (WebView2) 桌面小工具托盘常驻闲置内存高达 350MB+；关闭窗口（点 X）仅 Hide 导致 6 个 Chromium 子进程全量驻留；想进行 Chromium 启动参数剪枝并重构关窗销毁与按需重建生命周期实现闲置内存降至 40MB 级 | [`071_dev_wails_fix_WailsV3WebView2高内存治理与关窗生命周期重构.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/071_dev_wails_fix_WailsV3WebView2高内存治理与关窗生命周期重构.md) | Wails v3, WebView2, msedgewebview2, 常驻内存高, 托盘小工具, 关窗 Hide, 销毁 WebView2, DisableQuitOnLastWindowClosed, AdditionalBrowserArgs, --disable-gpu, 内存暴降, 按需重建, isWindowAlive, FreeOSMemory, --hidden 静默自启冷启动, 纯 Go 40MB |
| Windows 11 环境下快速连续按 Alt+Tab 切换窗口，任务切换器卡在屏幕中央不消失（像卡键一样，松手不退出） | [`072_win_ahk_fix_Win11高频AltTab卡键停留在切换界面与AHK钩子修复.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/072_win_ahk_fix_Win11高频AltTab卡键停留在切换界面与AHK钩子修复.md) | Alt+Tab 卡键, Alt Tab 卡住, 任务切换界面不消失, 松开不退, Sticky Alt Tab, Ctrl+Alt+Tab, A_MenuMaskKey, AutoHotkey vkE8, LowLevelHooksTimeout, XamlExplorerHostIslandWindow, 逻辑卡键 |
| CLI 工具依赖本地守护进程但常驻后台吃内存或端口冲突，希望单次查询时零感知自动拉起临时实例并在完成后立即优雅关停，或异常退出时有空闲超时自毁保底 | [`073_dev_cli_flow_CLI临时daemon按需拉起与零残留优雅关停.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/073_dev_cli_flow_CLI临时daemon按需拉起与零残留优雅关停.md) | CLI 工具, 后台常驻, daemon, --once, spawnDaemonWithIdle, --idle-timeout 10s, spawnedEphemeral, /v1/stop, 优雅关停, 零残留, 空闲超时自毁, 孤儿进程保底 |
| Zed 集成 Pi Coding Agent（官方 Registry 版 `svkozak/pi-acp`）难用卡顿、Windows 下 `pi.cmd` 双层管道挂起断开、取消中断信号丢失，或想在 Zed 中零心智负担使用原版 Pi | [`074_agent_pi_fix_Zed集成PiCodingAgent双层管道难用与openma内存直载SOP.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/074_agent_pi_fix_Zed集成PiCodingAgent双层管道难用与openma内存直载SOP.md) | Zed pi-acp 难用, svkozak/pi-acp, openma-ai/pi-acp, @openma/pi-acp, In-Process SDK 直载, createAgentSessionRuntime, 双层 stdio 管道挂起, pi.cmd 管道断开, PI_ACP_PI_COMMAND, 原版 Pi 零心智负担, session/cancel 信号丢失 |
| 想确认某软件「我装的**这版**」到底支不支持某功能，但本地只有发行版产物（无源码、无 `.git`）；或需要给某个结论补上可回查的源码级证据 | [`075_dev_core_flow_发行版二进制嵌SHA溯源与上游源码取证.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/075_dev_core_flow_发行版二进制嵌SHA溯源与上游源码取证.md) | 发行版没有 git 历史, --version 嵌 SHA, Zed 1.24.3 2a857f5f, raw.githubusercontent 按 SHA 取文件, commits API 校验, main 与本地版本差异, 别 dump 巨型二进制字符串, 二进制字符串粘连, 源码级取证, path:line 回查 |
| Zed 里自定义 ACP 代理（`type: custom`）图标是通用终端图标想换掉、settings 里加 `icon` 无效也不报错，或想让自定义代理显示品牌图标 | [`076_ide_zed_fix_Zed自定义ACP代理图标机制与注册表兜底.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/076_ide_zed_fix_Zed自定义ACP代理图标机制与注册表兜底.md) | Zed 自定义代理图标, agent_servers custom icon 无效, ACP Registry 图标, pi-acp.svg, external_agents\registry\icons, 线程侧栏终端图标, CustomAgentServerSettings, REGISTRY_URL 硬编码, agentInfo.icons 不生效, 键名蹭 Registry 图标 |
| Zed 外部 ACP 线程（openma-pi / pi-acp 等）标题永远是占位「New Agent Thread」、不再按首条消息自动命名，而 `/rename` 手动改名却立刻生效；或想搞清启动横幅与自动命名的关系、想改本地命名插件 | [`077_ide_zed_fix_Zed外部ACP线程不自动命名与首消息标题链路.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/077_ide_zed_fix_Zed外部ACP线程不自动命名与首消息标题链路.md) | New Agent Thread, 外部 ACP 线程不自动命名, 第一次正常之后失效, openma-pi 线程标题, pi-acp 标题, startup banner 抢占 entry, is_first_message, provisional title, set_provisional_title, is_draft_thread, session_info_update title, pi 无自动命名, auto-session-title, pi-local-plugins, quietStartup, PI_ACP_QUIET_STARTUP |
| 【特大高危】Zed 内存暴涨至 10GB+（提交 11.5GB）、整机卡死；同时 Windows Defender (MsMpEng) 占用 40%~75%+ CPU 狂飙死锁；Zed.log 狂刷 Temp/ntuser.dat `os error 5 / 32`，或诊断显示 `largest D:\ (231962 entries)` 扫爆 C/D 盘符根 | [`078_ide_zed_fix_Zed信任表家目录污染致全盘监听与Defender死锁.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/078_ide_zed_fix_Zed信任表家目录污染致全盘监听与Defender死锁.md) | 【特大高危】, Zed 10G 内存暴涨, Zed 内存泄漏, Defender 64%, Defender 75%, MsMpEng 占满 CPU, trusted_worktrees, C:\Users, D:\ 扫爆, largest D:\, ACP 读目录滑坡, no-delegation, Temp 临时文件死循环, os error 5, os error 32, live 16 visible 2, WdFilter 死锁, 信任父级目录陷阱 |
| 想给头部开源项目（如 Zed / VS Code / Rust）提交高质量 Bug Report，希望避免被当成杀毒/环境问题误杀、让官方核心维护者几分钟内迅速接单立项 | [`079_dev_core_flow_开源上游Issue高穿透提交与证据链设计SOP.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/079_dev_core_flow_开源上游Issue高穿透提交与证据链设计SOP.md) | 开源提 issue, GitHub Issue, bug report, 官方秒接单, 置顶前言, 对照实验, Restart Manager 内核取证, 标题工程学, 隐私脱敏, Zed issue 实战 |
| 提级暴露技能配置了 disable-model-invocation 导致自然语言交互中 Kiro Spec / Plan 等规范失盲、AI 自由发挥破坏三件套交付基线 | [`080_agent_skills_fix_过度disable致Agent规范失盲与时序元数据防腐治理.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/080_agent_skills_fix_过度disable致Agent规范失盲与时序元数据防腐治理.md) | disable-model-invocation, 规范失盲, 知识库过时, 元数据防腐, Kiro Spec, SPEC.md 自由发挥, 时序软失效 |
| dsh 启动时明明加了 `--no-open` 却弹出 accounts.x.ai 设备登录网页，或报错 Cursor ACP communication failed / CURSOR_BINARY_UNAVAILABLE | [`081_agent_dsh_fix_Cursor别名冲突致Grok误唤起与xai弹窗修复.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/081_agent_dsh_fix_Cursor别名冲突致Grok误唤起与xai弹窗修复.md) | accounts.x.ai, dsh web, --no-open 弹窗, Cursor ACP communication failed, CURSOR_BINARY_UNAVAILABLE, agent.exe, Grok CLI 命名冲突 |
| Zed 外接 ACP Agent（如 antigravity-acp）生成完文本后界面持续转圈、正文末尾挂三点脉冲 `⋮`、输入框锁定无法发下一条，点击停止报错 `method=$/cancel_request Method not found`，重启后发消息又卡死 | [`083_ide_zed_fix_Zed外接ACP长会话生成完毕转圈卡死与PromptResponse丢失排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/083_ide_zed_fix_Zed外接ACP长会话生成完毕转圈卡死与PromptResponse丢失排障.md) | Zed外接ACP卡死, 永久转圈, 三点脉冲, 输入框锁定, PromptResponse丢失, receive_steps, STATE_FULLY_IDLE, cancel_request Method not found, 长会话失步, 502网络重试, antigravity-acp, 新Thread恢复 |
| pi TUI 底部 `Feishu: 已连接` 状态消失、`/feishu` 命令与 `feishu_config_*` 工具没了，但飞书消息仍能收发；或 `pi list` 报 `No packages installed`、`settings.json` 里 `packages` 不见（旁边可能还躺着一份 `config.yml`）；或重启电脑总弹一个标题为 `pi` 的黑窗（外观像 WT 但无标签栏，关掉还会再冒）、`daemon.log` 里每 20 秒一轮 `spawned daemon` / `killing my daemon (another live owner)` | [`084_agent_pi_fix_飞书桥接keeper空转重生pi弹conhost黑窗.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/084_agent_pi_fix_飞书桥接keeper空转重生pi弹conhost黑窗.md) | pi 弹窗, 重启弹黑窗, 标题 pi 窗口, another live owner, pi-feishu-keeper, ax-feishu-bridge, PI_CLI_ENTRY, pi-launcher 包装层, dist/bundle/cli.js, windowsHide, Detached 弹 conhost, DefTerm 断层, Feishu 状态消失, /feishu 命令消失, pi list No packages installed, settings.json packages 丢失, config.yml 无效, pi 自更新 migrated install, 旧全局安装 已删除 |
| 需要为后端 API 接口批量生成 Bruno 测试脚本集合（.bru / OpenCollection YAML），或遇到 Bruno YAML 格式/schema 报错 | [`085_dev_bruno_flow_api_test_collection.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/085_dev_bruno_flow_api_test_collection.md) | Bruno API, .bru, OpenCollection, opencollection.yml, 接口测试, after-response, 变量提取, YAML 语法校验 |
| C/C++/Lua 多语言项目编译构建报错，需要配置 CMake Presets、通过 FetchContent 源码集成 Lua 5.1，或解决 MSVC /utf-8 中文乱码与 clangd 寻址 | [`086_dev_cmake_flow_trilang_lua_cpp_toolchain.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/086_dev_cmake_flow_trilang_lua_cpp_toolchain.md) | CMake, FetchContent, Lua 5.1.5, trilang, MSVC, /utf-8, clangd, Ninja, NeoCMake, LUA_OK, doctest |
| GitHub 账号下仓库堆积，需要安全清点审计、纯收藏 fork 判定转 Star、核心仓库本地 mirror 备份与 gh CLI 批量删除 | [`087_git_gh_flow_repo_cleanup_audit.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/087_git_gh_flow_repo_cleanup_audit.md) | GitHub 仓库清理, gh auth login, delete_repo, fork 判定, ahead_by, mirror 备份, 批量删除仓库, PS 5.1 编码 |
| 本地运行的 Web 或 CLI 服务希望以独立桌面应用窗口（无地址栏/书签栏）运行，或改造为标准 PWA 面板 | [`088_browser_pwa_flow_localhost_standalone_window.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/088_browser_pwa_flow_localhost_standalone_window.md) | localhost PWA, Chromium SSB, --app 模式, 独立窗口应用, manifest.json, Web App Manifest, 独立任务栏图标 |
| 需要从 Word (.docx)、PPT (.pptx)、Excel (.xlsx) 中无损提取内嵌原图、矢量图或媒体资源，避免截图失真 | [`089_media_docx_flow_office_extract_media.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/089_media_docx_flow_office_extract_media.md) | Office 取图, docx 改 zip, pptx 提取原图, media 目录, 无损原图, extract_media.py, OOXML 解包 |
| Repository 层 SQLAlchemy Core 查询过于冗长复杂，需要重构为纯文本 SQL 模板 + Query Builder 参数装配层 | [`090_dev_sa_flow_sql_query_builder_extract.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/090_dev_sa_flow_sql_query_builder_extract.md) | SQLAlchemy Core 重构, Query Builder, 文本 SQL 模板, CTE 抽取, text() 占位符, rows count 共享 params, SQL 注入防御 |
| Windows Terminal (WT) 选中文本按 Ctrl+C 偶尔卡死数秒且未复制成功，或开 copyOnSelect 拖选文字卡顿掉帧 | [`091_ide_terminal_fix_WT选中文本CtrlC卡死与剪贴板锁争用排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/091_ide_terminal_fix_WT选中文本CtrlC卡死与剪贴板锁争用排障.md) | WT Ctrl+C 卡死, 终端复制卡死, 复制不上, OpenClipboard, PR 17006, Sleep 指数退避, UI 线程假死, cbdhsvc 锁争用, copyOnSelect 卡顿, Enter 回车复制 |
| Claude Code 升级后直连 OpenCode/第三方网关报 400 inference_failed、ModelProtocolUnsupported、双鉴权头冲突、Cloudflare 1010 拦截、Zed 弹窗 auto-mode-classifier-billing 警告、底部卡死 Authenticating to Claude Agent... 孤儿进程或包名迁移误判停更 | [`092_agent_ccswitch_fix_ClaudeCode升级参数冲突与OpenCode路由翻译.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/092_agent_ccswitch_fix_ClaudeCode升级参数冲突与OpenCode路由翻译.md) | Claude Code 400, OpenCode GLM 400, ModelProtocolUnsupported, Go requires a credential, Both ANTHROPIC_AUTH_TOKEN and ANTHROPIC_API_KEY set, Header is managed by the local proxy and cannot be overridden, openai_chat 翻译, 1M 上下文, Fable 档位, auto-mode-classifier-billing, Claude reported a warning, 127.0.0.1:15721, Authenticating to Claude Agent..., session account carries no identity signal, Authentication required, auth login --console, claude acp 转圈, @agentclientprotocol/claude-agent-acp, claude-code-acp 弃用 |
| Markdown 纯阅读渲染场景下 Typora/Obsidian 打开多窗口吞噬 1GB 内存，或需要免双击、阅后即焚、常驻仅 15MB 的空格即时预览工作流 | [`093_win_ql_flow_QuickLook便携部署与Markdown空格秒览.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/093_win_ql_flow_QuickLook便携部署与Markdown空格秒览.md) | QuickLook, Typora 替代, Markdown 预览, 空格预览, MarkdownViewer, 内存暴涨, WebView2 白屏, ql |
| Antigravity (agy app) 桌面端默认纯黑主题生硬刺眼，想配置为 JetBrains Rider Dark / Darcula 经典质感与三元基石色彩映射 | [`094_agent_agy_flow_AGY外观RiderDark深色调色板映射与配置.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/094_agent_agy_flow_AGY外观RiderDark深色调色板映射与配置.md) | Antigravity 外观, agy app 主题, Appearance, Dark Theme, Rider Dark, JetBrains 调色板, Background 262626, Foreground DFDFDF, Accent 3574F0, 纯黑刺眼 |
| Antigravity 等 Electron 软件启动写死尺寸记不住最大化，或需要非侵入式桌面自动化、WMI 脱离热重启与 AHK 极客工作流 | [`095_win_ahk_flow_Win非侵入式AHK启动外挂与极客桌面自动化全景.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/095_win_ahk_flow_Win非侵入式AHK启动外挂与极客桌面自动化全景.md) | Antigravity 最大化, AHK 外挂, AutoHotkey, 启动最大化, 窗口记忆, WMI 脱离, 非侵入式, 桌面自动化, 热重启, 抽屉式 Toggle |
| 后台工具拉起纯黑控制台窗口遮挡前台、Windhawk 模组置底 Hook 被 Stardock Groupy 外部多标签管理器穿透置顶（草案存档） | [`096_win_conhost_fix_Windhawk置底Hook与Groupy外壳穿透.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/096_win_conhost_fix_Windhawk置底Hook与Groupy外壳穿透.md) | conhost 黑框置底, Windhawk Hook, Stardock Groupy, 外部外壳穿透, HWND_BOTTOM, SW_SHOWMINNOACTIVE, 抢焦点, 排除名单 |
| Typora 打开多窗口吃 1GB 内存，或需要原生独立桌面窗口长久阅读、多标签管理、内存小于 90MB、Mermaid 矢量图与双栏编辑/贴图落盘 | [`097_win_tinta_flow_Tinta原生极轻Markdown阅读与双栏编辑.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/097_win_tinta_flow_Tinta原生极轻Markdown阅读与双栏编辑.md) | Tinta, Typora 替代, 轻量 Markdown 阅读器, Direct2D, 低内存 Markdown, Markdown 双栏编辑, 截图贴图, tinta |
| Windows 下双击 exe 弹“打开文件-安全警告：无法验证发布者”，点击运行后毫无动静瞬间闪退，排查发现是父目录带 Mandatory Label\Low Mandatory Level 沙箱标签被新建 worktree 继承，导致进程在 Low 级别无法连接 WinSta0 窗口站并死在 DLL 初始化 (0xC0000142) | [`098_win_fs_fix_父目录Low完整性继承致GUI闪退与安全警告排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/098_win_fs_fix_父目录Low完整性继承致GUI闪退与安全警告排障.md) | Mandatory Label, Low Mandatory Level, icacls, /setintegritylevel Medium, Unblock-File, ERROR_DLL_INIT_FAILED, 0xC0000142, WinSta0, 安全警告, 无法验证发布者, 点击运行没反应, 静默闪退, worktree 权限继承, 沙箱完整性级别 |
| DeepSeek Harness Web UI (dsh web) 需要全量升级，更新后界面没变、或三方插件缺少新特性、或想在不启动服务前静态验证 Cordis 插件树与配置完整性 | [`099_agent_dsh_flow_DSHWeb三层更新体系与插件升级及容器校验.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/099_agent_dsh_flow_DSHWeb三层更新体系与插件升级及容器校验.md) | dsh web 更新, dsh 升级, dsh plugin update, ds-harness-remote, --dump-config, 静态容器校验, Cordis 层叠, 幽灵旧进程, 端口幂等, Start-DshWeb, 三层更新体系 |
| Windows 11 下按 Alt+Tab 完全失效无反应（弹不出切换器），此前只能靠重启电脑解决，排查 DWM 显存句柄泄漏破 1GB 与 Explorer 崩溃后 XAML 宿主失步，需免重启秒级自愈 | [`100_win_sys_fix_Win11DWM显存泄漏AltTab失效与Winlogon平滑自愈.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/100_win_sys_fix_Win11DWM显存泄漏AltTab失效与Winlogon平滑自愈.md) | Alt+Tab失效, 弹不出切换器, 重启解决, DWM内存泄漏, dwm.exe, 7500句柄, ForegroundStaging, XamlExplorerHostIslandWindow, AutoRestartShell, Winlogon, 平滑重启, Stop-Process explorer, AltTabSettings |
| Windows 11 开始菜单固定区偶尔莫名其妙多出一整排官方应用（画图/计算器/记事本/OEM工具/纸牌游戏），取消固定后又再次冒出，排查 StartMenuExperienceHost 强杀致 start2.bin 崩溃自愈与 ContentDeliveryManager 静默回填 | [`101_win_sys_fix_Win11开始菜单固定区幽灵回填与强杀StartMenu自愈排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/101_win_sys_fix_Win11开始菜单固定区幽灵回填与强杀StartMenu自愈排障.md) | 开始菜单固定项变多, 莫名其妙再次显示, 被重置了的感觉, 画图计算器记事本又冒出来了, 机械革命, 幽灵回填, StartMenuExperienceHost, ContentDeliveryManager, OemPreInstalledAppsEnabled, SilentInstalledAppsEnabled, start2.bin |
| Chrome 扩展通过 chrome.tabs.query 匹配本地特定端口服务（如 127.0.0.1:11111、localhost:8080）报错 Error: Invalid url pattern，需要绕开 Chromium Match Pattern 端口限制并实现毫秒级精准切页 | [`102_browser_chrome_fix_扩展MatchPattern端口限制与tabs查询排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/102_browser_chrome_fix_扩展MatchPattern端口限制与tabs查询排障.md) | Invalid url pattern, chrome.tabs.query 端口, Match Pattern 端口, Chrome 扩展 url pattern, 端口限制, 127.0.0.1, 11111, tabs.query 报错, 扩展切标签页 |
| 木及简历(mujicv.com)编辑器预览和导出 PDF 每行行首/行尾字被裁掉半个字（"东南大学"缺"东"、"AI"变"AL"），或导出 PDF 不带自定义 CSS 仍是默认模板 | [`103_browser_mujicv_fix_木及简历自定义CSS行首裁字与导出无样式修复.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/103_browser_mujicv_fix_木及简历自定义CSS行首裁字与导出无样式修复.md) | 木及简历, mujicv, 简历导出裁字, 行首被裁, 缺半个字, AI变AL, 导出PDF没有样式, 自定义CSS不生效, 设置CSS保存, margin-left 内联 |
| chrome-devtools MCP 操作 React/AntD 网站：el.click()/dispatchEvent 点击"成功"但页面无反应、AntD 下拉菜单几秒自动收起、受控 textarea 写入被冲掉、upload_file 报 not within workspace roots、截图/脚本连续超时 | [`104_agent_dsh_fix_MCP浏览器自动化antd表单与文件上传踩坑.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/104_agent_dsh_fix_MCP浏览器自动化antd表单与文件上传踩坑.md) | mcp 点击没反应, el.click 无效, 合成事件, CDP click, 下拉菜单收起, dropdown 自动关闭, React 受控组件, value setter, upload_file 拒绝, workspace roots, 截图超时, 页面卡死, clipboard, base64 中转 |

---

## 3. 知识扩充规范（追加新知识时遵循）

当你开发中遇到新的典型踩坑或沉淀出高价值工程实现流水线需要归档时：
1. **确定文件名与 `name`**：文件名遵循五段式受控分面规范 `<id>_<domain>_<scope>_<type>_<slug>.md`（如 `074_win_docker_fix_DockerDesktop卷挂载符号链接失效排障.md` 或 `073_dev_cli_flow_CLI临时daemon按需拉起与零残留优雅关停.md`），序号三位定长顺延；同时 frontmatter 必须齐备 `name`、`description` 与 `status`/`created`/`last_verified` 时序字段——新条目用 `kbman migrate` 生成默认可信态，勿手写漏字段；
2. **文档结构标准（双轨结构）**：
   - **通用 YAML frontmatter**：`name` + `description`（skill-creator 规范，见第 1 节「条目即技能」），缺了它这条目就不算合规；
   - **Type A：疑难排障型条目**：
     - 一、现象与报错直击：贴出真实终端输出或 UI 截图文字；
     - 二、底层根因剖析：讲透为什么会发生（操作系统机制、并发锁、协议冲突等）；
     - 三、标准解决与抢救 SOP：提供原子化、可直接复制执行的命令与操作步骤；
     - 四、验证与防复发建议：如何确认已彻底解决；
   - **Type B：方案与生成流水线型条目**：
     - 一、业务场景与生成需求：输入源、生成目标与最终交付格式；
     - 二、排版/技术核心难点与底层剖析：格式规范、底层引擎机制（如 XML 命名空间、编码标准）；
     - 三、标准自动化生成流水线与代码实现：可直接复用的完整脚本骨架与核心装配函数；
     - 四、交付验证与工程扩展建议：产物校验断言与新场景复用 SOP；
3. **更新本路由表**：在上面的路由表格中添加新条目的索引行；
4. **外部解耦原则**：知识库条目由本路由表完全自洽索引。外部路由器（如 `kb-engineering-notes` 及顶层 `sh-user-skills`）统一采用领域定性描述，严禁绑定条目总数或区间，新增条目无需修改外部技能描述。
---

## 4. 条目时序演进检索表（按 ID 逻辑时钟升序）

> 💡 **四维时间序感知**：按 `<id>` 逻辑时钟单调递增顺序索引全量条目，外部 Agent 与人类可一屏通览知识库生命周期演进全貌。

| ID | 当前文件名 | 规范化映射目标 (平铺/虚拟路径) | 领域 | 形态 | 核心主题场景速查 |
|:---:|:---|:---|:---:|:---:|:---|
| 001 | [`001_git_smerge_fix_SublimeMerge非相邻提交Squash合并重排.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/001_git_smerge_fix_SublimeMerge非相邻提交Squash合并重排.md) | `001_git_smerge_fix_SublimeMerge非相邻提交Squash合并重排.md` | `git` | `fix` | Sublime Merge 非相邻提交跨项重排与 Squash 合并 |
| 002 | [`002_git_rebase_fix_变基PermissionDenied文件锁排障与安全恢复.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/002_git_rebase_fix_变基PermissionDenied文件锁排障与安全恢复.md) | `002_git_rebase_fix_变基PermissionDenied文件锁排障与安全恢复.md` | `git` | `fix` | Git 变基 Permission Denied 文件锁与 Abort 抢救 |
| 003 | [`003_git_rebase_fix_变基Rescheduled队列挂起与冲突解析.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/003_git_rebase_fix_变基Rescheduled队列挂起与冲突解析.md) | `003_git_rebase_fix_变基Rescheduled队列挂起与冲突解析.md` | `git` | `fix` | Git 变基 Rescheduled 队列挂起与暂存区冲突深度解析 |
| 004 | [`004_ide_cursor_flow_Cursor预览独立标签页切换.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/004_ide_cursor_flow_Cursor预览独立标签页切换.md) | `004_ide_cursor_flow_Cursor预览独立标签页切换.md` | `ide` | `flow` | Cursor / VS Code Markdown 独立全屏标签页配置 |
| 005 | [`005_ide_cursor_flow_Cursor免审批YOLO模式与沙箱网络.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/005_ide_cursor_flow_Cursor免审批YOLO模式与沙箱网络.md) | `005_ide_cursor_flow_Cursor免审批YOLO模式与沙箱网络.md` | `ide` | `flow` | Cursor Agent YOLO 免审批运行与沙箱网络策略配置 |
| 006 | [`006_git_worktree_flow_Worktree跨语言依赖复用与环境隔离权衡.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/006_git_worktree_flow_Worktree跨语言依赖复用与环境隔离权衡.md) | `006_git_worktree_flow_Worktree跨语言依赖复用与环境隔离权衡.md` | `git` | `flow` | Worktree 跨语言依赖复用与环境隔离权衡 |
| 007 | [`007_dev_uv_flow_uv统一全机Python与新机引导复现.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/007_dev_uv_flow_uv统一全机Python与新机引导复现.md) | `007_dev_uv_flow_uv统一全机Python与新机引导复现.md` | `dev` | `flow` | uv 统一全机 Python 环境与新机一键引导复现 |
| 008 | [`008_dev_zed_flow_Win下Java与Maven便携配置及Zed集成.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/008_dev_zed_flow_Win下Java与Maven便携配置及Zed集成.md) | `008_dev_zed_flow_Win下Java与Maven便携配置及Zed集成.md` | `dev` | `flow` | Java/Maven 便携子目录隔离与 Zed 任务调试集成 |
| 009 | [`009_browser_chrome_fix_Chrome关闭标签丢失SNSS快照找回.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/009_browser_chrome_fix_Chrome关闭标签丢失SNSS快照找回.md) | `009_browser_chrome_fix_Chrome关闭标签丢失SNSS快照找回.md` | `browser` | `fix` | Chrome 关闭标签丢失 SNSS 快照解析与抢救找回 |
| 010 | [`010_ide_terminal_fix_CLI粘贴图片Kitty透传与BOM排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/010_ide_terminal_fix_CLI粘贴图片Kitty透传与BOM排障.md) | `010_ide_terminal_fix_CLI粘贴图片Kitty透传与BOM排障.md` | `ide` | `fix` | CLI 粘贴图片改键与 Windows Terminal Kitty 透传及 BOM 排障 |
| 011 | [`011_win_conhost_fix_计划任务控制台委托闪窗与conhost注册.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/011_win_conhost_fix_计划任务控制台委托闪窗与conhost注册.md) | `011_win_conhost_fix_计划任务控制台委托闪窗与conhost注册.md` | `win` | `fix` | 计划任务控制台委托闪窗排障与 conhost 无窗口注册 |
| 012 | [`012_agent_yolo_flow_CLI执行模式辨析与免批YOLO配置.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/012_agent_yolo_flow_CLI执行模式辨析与免批YOLO配置.md) | `012_agent_yolo_flow_CLI执行模式辨析与免批YOLO配置.md` | `agent` | `flow` | CLI 执行模式辨析与免批 YOLO 权限及配置面板治理 |
| 013 | [`013_media_audio_flow_降噪耳机人声泄露声学掩蔽与公有音频.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/013_media_audio_flow_降噪耳机人声泄露声学掩蔽与公有音频.md) | `013_media_audio_flow_降噪耳机人声泄露声学掩蔽与公有音频.md` | `media` | `flow` | 降噪耳机人声泄露声学掩蔽与公有领域音频流水线 |
| 014 | [`014_win_ahk_flow_Win单手盲切与抽屉式Toggle窗口AHK配置.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/014_win_ahk_flow_Win单手盲切与抽屉式Toggle窗口AHK配置.md) | `014_win_ahk_flow_Win单手盲切与抽屉式Toggle窗口AHK配置.md` | `win` | `flow` | Windows 单手盲切与抽屉式 Toggle 窗口 AutoHotkey 配置 |
| 015 | [`015_dev_docx_flow_docx自动化生成试卷与排版流水线.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/015_dev_docx_flow_docx自动化生成试卷与排版流水线.md) | `015_dev_docx_flow_docx自动化生成试卷与排版流水线.md` | `dev` | `flow` | python-docx 自动化试卷生成与格式精细排版流水线 |
| 016 | [`016_ide_terminus_fix_SublimeTerminus退格失效与原生终端集成.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/016_ide_terminus_fix_SublimeTerminus退格失效与原生终端集成.md) | `016_ide_terminus_fix_SublimeTerminus退格失效与原生终端集成.md` | `ide` | `fix` | Sublime Terminus 中文退格失效与原生终端侧边栏集成 |
| 017 | [`017_win_audio_fix_Win声卡爆音无声与虚拟音频抢占排查.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/017_win_audio_fix_Win声卡爆音无声与虚拟音频抢占排查.md) | `017_win_audio_fix_Win声卡爆音无声与虚拟音频抢占排查.md` | `win` | `fix` | Windows 声卡爆音无声与虚拟音频抢占排障 |
| 018 | [`018_win_uwp_fix_Win代理下微软商店与UWP回环豁免.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/018_win_uwp_fix_Win代理下微软商店与UWP回环豁免.md) | `018_win_uwp_fix_Win代理下微软商店与UWP回环豁免.md` | `win` | `fix` | 代理下微软应用商店与 UWP 回环网络豁免排障 |
| 019 | [`019_win_mem_fix_Win内存防死机与Pagefile提交归因优化.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/019_win_mem_fix_Win内存防死机与Pagefile提交归因优化.md) | `019_win_mem_fix_Win内存防死机与Pagefile提交归因优化.md` | `win` | `fix` | Windows 内存防死机与 Pagefile 提交内存归因优化 |
| 020 | [`020_win_fs_fix_Win系统C盘空间不足排查与软链接重定向.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/020_win_fs_fix_Win系统C盘空间不足排查与软链接重定向.md) | `020_win_fs_fix_Win系统C盘空间不足排查与软链接重定向.md` | `win` | `fix` | C 盘空间不足安全清理与软链接重定向方案 |
| 021 | [`021_agent_opencode_fix_opencode连接GLM鉴权401与端点排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/021_agent_opencode_fix_opencode连接GLM鉴权401与端点排障.md) | `021_agent_opencode_fix_opencode连接GLM鉴权401与端点排障.md` | `agent` | `fix` | opencode 连接智谱 GLM 401 鉴权失败与端点排障 |
| 022 | [`022_ide_zed_fix_Zed语言服务器重命名与杀毒竞态.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/022_ide_zed_fix_Zed语言服务器重命名与杀毒竞态.md) | `022_ide_zed_fix_Zed语言服务器重命名与杀毒竞态.md` | `ide` | `fix` | Zed 语言服务器下载重命名占用与杀毒竞态排障 |
| 023 | [`023_ide_zed_fix_Zed与IDEA外接ACP代理失效与进程堆积.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/023_ide_zed_fix_Zed与IDEA外接ACP代理失效与进程堆积.md) | `023_ide_zed_fix_Zed与IDEA外接ACP代理失效与进程堆积.md` | `ide` | `fix` | Zed/IDEA 外接 ACP 代理失效与子进程池累积排查 |
| 024 | [`024_ide_zed_fix_Zed面板InternalError会话中断与锁竞态.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/024_ide_zed_fix_Zed面板InternalError会话中断与锁竞态.md) | `024_ide_zed_fix_Zed面板InternalError会话中断与锁竞态.md` | `ide` | `fix` | Zed Agent 面板 InternalError 会话中断与锁竞态归因 |
| 025 | [`025_ide_zed_fix_Zed会话丢失提取与SQLite解析抢救.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/025_ide_zed_fix_Zed会话丢失提取与SQLite解析抢救.md) | `025_ide_zed_fix_Zed会话丢失提取与SQLite解析抢救.md` | `ide` | `fix` | Zed 历史会话丢失提取与 SQLite 数据库表解析抢救 |
| 026 | [`026_ide_zed_flow_Zed项目级LSP白名单与内存优化.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/026_ide_zed_flow_Zed项目级LSP白名单与内存优化.md) | `026_ide_zed_flow_Zed项目级LSP白名单与内存优化.md` | `ide` | `flow` | Zed 项目级 LSP 白名单配置与多项目内存优化 |
| 027 | [`027_git_ssh_flow_多Git账号SSH与IncludeIf配置.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/027_git_ssh_flow_多Git账号SSH与IncludeIf配置.md) | `027_git_ssh_flow_多Git账号SSH与IncludeIf配置.md` | `git` | `flow` | 多 Git 账号 GitHub/GitLab 共存与 SSH IncludeIf 配置 |
| 028 | [`028_ide_atuin_fix_Win终端Atuin历史同步与Profile修复.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/028_ide_atuin_fix_Win终端Atuin历史同步与Profile修复.md) | `028_ide_atuin_fix_Win终端Atuin历史同步与Profile修复.md` | `ide` | `fix` | Windows 终端 Atuin 命令历史同步与 Profile 修复 |
| 029 | [`029_agent_ccswitch_flow_cc-switch数据库机制模型迁移与避坑指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/029_agent_ccswitch_flow_cc-switch数据库机制模型迁移与避坑指南.md) | `029_agent_ccswitch_flow_cc-switch数据库机制模型迁移与避坑指南.md` | `agent` | `flow` | cc-switch 数据库机制、跨应用模型迁移与避坑全指南 |
| 030 | [`030_ide_vscode_flow_VSCode扩展跨分支IDE手动搬运.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/030_ide_vscode_flow_VSCode扩展跨分支IDE手动搬运.md) | `030_ide_vscode_flow_VSCode扩展跨分支IDE手动搬运.md` | `ide` | `flow` | VS Code 扩展跨分支 IDE 手动搬运与注册生效 |
| 031 | [`031_git_vscode_flow_VSCode底部面板GitLG配色调优.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/031_git_vscode_flow_VSCode底部面板GitLG配色调优.md) | `031_git_vscode_flow_VSCode底部面板GitLG配色调优.md` | `git` | `flow` | VS Code 底部终端面板 GitLG 提交树与分支配色调优 |
| 032 | [`032_win_ps_flow_Win便携PowerShell7绿色部署.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/032_win_ps_flow_Win便携PowerShell7绿色部署.md) | `032_win_ps_flow_Win便携PowerShell7绿色部署.md` | `win` | `flow` | Windows 便携免安装 PowerShell 7 绿色部署与初始化 |
| 033 | [`033_ide_sublime_flow_YaHeiConsolasHybrid字体渲染与Sublime配置.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/033_ide_sublime_flow_YaHeiConsolasHybrid字体渲染与Sublime配置.md) | `033_ide_sublime_flow_YaHeiConsolasHybrid字体渲染与Sublime配置.md` | `ide` | `flow` | YaHeiConsolasHybrid 字体渲染与 Sublime 界面高清配置 |
| 034 | [`034_ide_sublime_flow_Win11右键菜单注册Sublime与注册表快捷管理.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/034_ide_sublime_flow_Win11右键菜单注册Sublime与注册表快捷管理.md) | `034_ide_sublime_flow_Win11右键菜单注册Sublime与注册表快捷管理.md` | `ide` | `flow` | Windows 11 右键菜单注册 Sublime 与注册表管理 |
| 035 | [`035_ide_pi_fix_Pi终端改键与滚轮协议冲突修复.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/035_ide_pi_fix_Pi终端改键与滚轮协议冲突修复.md) | `035_ide_pi_fix_Pi终端改键与滚轮协议冲突修复.md` | `ide` | `fix` | Pi 终端按键映射改键与滚轮协议冲突修复 |
| 036 | [`036_agent_core_flow_各Agent客户端终端机制与GitBash切换.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/036_agent_core_flow_各Agent客户端终端机制与GitBash切换.md) | `036_agent_core_flow_各Agent客户端终端机制与GitBash切换.md` | `agent` | `flow` | Windows 各 Agent 客户端终端机制与 Git Bash 切换 |
| 037 | [`037_browser_devtools_flow_opencode集成chrome-devtools-mcp浏览器控制.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/037_browser_devtools_flow_opencode集成chrome-devtools-mcp浏览器控制.md) | `037_browser_devtools_flow_opencode集成chrome-devtools-mcp浏览器控制.md` | `browser` | `flow` | opencode 集成 chrome-devtools-mcp 浏览器控制调试 |
| 038 | [`038_agent_zed_flow_Zed集成opencodeAgent思考档位与供应商迁移.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/038_agent_zed_flow_Zed集成opencodeAgent思考档位与供应商迁移.md) | `038_agent_zed_flow_Zed集成opencodeAgent思考档位与供应商迁移.md` | `agent` | `flow` | Zed 集成 opencode Agent 思考档位与供应商迁移 |
| 039 | [`039_agent_core_flow_无搜索API时DDG端点核查与一手信源收敛.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/039_agent_core_flow_无搜索API时DDG端点核查与一手信源收敛.md) | `039_agent_core_flow_无搜索API时DDG端点核查与一手信源收敛.md` | `agent` | `flow` | 无搜索 API 时 DuckDuckGo HTML 端点事实核查流水线 |
| 040 | [`040_dev_core_flow_AI辅助面向对象OOP重构与模式演进.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/040_dev_core_flow_AI辅助面向对象OOP重构与模式演进.md) | `040_dev_core_flow_AI辅助面向对象OOP重构与模式演进.md` | `dev` | `flow` | AI 辅助面向对象 OOP 重构与设计模式落地演进 |
| 041 | [`041_win_fs_fix_Win跨盘单文件软链接权限与Junction排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/041_win_fs_fix_Win跨盘单文件软链接权限与Junction排障.md) | `041_win_fs_fix_Win跨盘单文件软链接权限与Junction排障.md` | `win` | `fix` | Windows 跨盘单文件软链接权限与 Junction 底层排障 |
| 042 | [`042_agent_core_fix_多Agent全局规则生效与CLI管道防挂起.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/042_agent_core_fix_多Agent全局规则生效与CLI管道防挂起.md) | `042_agent_core_fix_多Agent全局规则生效与CLI管道防挂起.md` | `agent` | `fix` | 多 Agent 全局规则分发生效与 CLI 管道防挂起 |
| 043 | [`043_agent_opencode_fix_OpenCodeGo模型提速与关闭思考reasoningEffort.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/043_agent_opencode_fix_OpenCodeGo模型提速与关闭思考reasoningEffort.md) | `043_agent_opencode_fix_OpenCodeGo模型提速与关闭思考reasoningEffort.md` | `agent` | `fix` | OpenCodeGo 访问提速与关闭思考 reasoningEffort 调优 |
| 044 | [`044_ide_sublime_fix_SublimeMarkdown预览抢焦点与静默改键.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/044_ide_sublime_fix_SublimeMarkdown预览抢焦点与静默改键.md) | `044_ide_sublime_fix_SublimeMarkdown预览抢焦点与静默改键.md` | `ide` | `fix` | Sublime Markdown 预览抢焦点跳浏览器排障与静默改键 |
| 045 | [`045_agent_core_flow_全机AI密钥清点与供应商指纹脱敏.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/045_agent_core_flow_全机AI密钥清点与供应商指纹脱敏.md) | `045_agent_core_flow_全机AI密钥清点与供应商指纹脱敏.md` | `agent` | `flow` | 全机 AI 密钥清点收敛与模型供应商指纹脱敏 |
| 046 | [`046_win_everything_fix_Win进程启动来源取证与Everything闲置保护.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/046_win_everything_fix_Win进程启动来源取证与Everything闲置保护.md) | `046_win_everything_fix_Win进程启动来源取证与Everything闲置保护.md` | `win` | `fix` | Windows 进程启动来源取证与 Everything 闲置退出保护排障 |
| 047 | [`047_ide_sublime_fix_Sublime全局搜索穿透Gitignore慢查排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/047_ide_sublime_fix_Sublime全局搜索穿透Gitignore慢查排障.md) | `047_ide_sublime_fix_Sublime全局搜索穿透Gitignore慢查排障.md` | `ide` | `fix` | Sublime 全局搜索穿透 Gitignore、非Git目录隔离与 Whole Word 符号边界排障 |
| 048 | [`048_ide_terminal_fix_WinTerminal分屏窗格判定与关闭误触.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/048_ide_terminal_fix_WinTerminal分屏窗格判定与关闭误触.md) | `048_ide_terminal_fix_WinTerminal分屏窗格判定与关闭误触.md` | `ide` | `fix` | Windows Terminal 分屏窗格布局判定与关闭误触治理 |
| 049 | [`049_browser_chrome_fix_Chrome与Firefox静默安装迅雷与BT替代.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/049_browser_chrome_fix_Chrome与Firefox静默安装迅雷与BT替代.md) | `049_browser_chrome_fix_Chrome与Firefox静默安装迅雷与BT替代.md` | `browser` | `fix` | 浏览器静默安装迅雷排障与注册表清理及纯净 BT 方案 |
| 050 | [`050_win_sys_flow_平铺知识库文件名元数据规范与迁移SOP.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/050_win_sys_flow_平铺知识库文件名元数据规范与迁移SOP.md) | `050_win_sys_flow_平铺知识库文件名元数据规范与迁移SOP.md` | `win` | `flow` | 平铺知识库文件名元数据架构、双轨规范与时序感知体系 |
| 051 | [`051_dev_core_fix_离线Markdown向量检索混合漏检排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/051_dev_core_fix_离线Markdown向量检索混合漏检排障.md) | `051_dev_core_fix_离线Markdown向量检索混合漏检排障.md` | `dev` | `fix` | 本地 Markdown 向量检索搭建与混合检索专有词漏检排障 |
| 052 | [`052_win_conhost_fix_PE控制台委托DefTerm断层与MCP无窗口镜像.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/052_win_conhost_fix_PE控制台委托DefTerm断层与MCP无窗口镜像.md) | `052_win_conhost_fix_PE控制台委托DefTerm断层与MCP无窗口镜像.md` | `win` | `fix` | PE 控制台委托 DefTerm 断层排查与 MCP 服务无窗口镜像 |
| 053 | [`053_ide_terminal_fix_WinTerminal拆分窗格cd目录丢失与OSC99上报.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/053_ide_terminal_fix_WinTerminal拆分窗格cd目录丢失与OSC99上报.md) | `053_ide_terminal_fix_WinTerminal拆分窗格cd目录丢失与OSC99上报.md` | `ide` | `fix` | WT 拆分窗格 cd 目录重启不保留与 OSC 9;9 路径上报排障 |
| 054 | [`054_win_windhawk_fix_Win11任务栏输入指示图标隐藏与Windhawk代码注入.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/054_win_windhawk_fix_Win11任务栏输入指示图标隐藏与Windhawk代码注入.md) | `054_win_windhawk_fix_Win11任务栏输入指示图标隐藏与Windhawk代码注入.md` | `win` | `fix` | Win11 任务栏输入指示图标隐藏与 Windhawk 运行时代码注入 |
| 055 | [`055_win_sys_fix_划词工具CtrlC误杀终端与AltShift切语言排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/055_win_sys_fix_划词工具CtrlC误杀终端与AltShift切语言排障.md) | `055_win_sys_fix_划词工具CtrlC误杀终端与AltShift切语言排障.md` | `win` | `fix` | 划词工具盲发 Ctrl+C 误杀终端与 Windows 默认 Alt+Shift 切语言排障 |
| 056 | [`056_agent_dsh_fix_DSH挂载MCP包装层内存膨胀治理与直连改造.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/056_agent_dsh_fix_DSH挂载MCP包装层内存膨胀治理与直连改造.md) | `056_agent_dsh_fix_DSH挂载MCP包装层内存膨胀治理与直连改造.md` | `agent` | `fix` | DSH 挂载 MCP 包装层进程内存膨胀治理与直连入口改造 |
| 057 | [`057_win_ps_flow_常驻Pwsh替换为csc现场编译原生Win32与零conhost.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/057_win_ps_flow_常驻Pwsh替换为csc现场编译原生Win32与零conhost.md) | `057_win_ps_flow_常驻Pwsh替换为csc现场编译原生Win32与零conhost.md` | `win` | `flow` | 常驻 PowerShell 替换为 csc 现场编译原生 Win32 与零 conhost |
| 058 | [`058_git_core_fix_Git批量提交高思考档分析瘫痪排障与灰色资产判决.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/058_git_core_fix_Git批量提交高思考档分析瘫痪排障与灰色资产判决.md) | `058_git_core_fix_Git批量提交高思考档分析瘫痪排障与灰色资产判决.md` | `git` | `fix` | Git 批量提交 Agent 高思考档分析瘫痪排障与灰色资产判决 |
| 059 | [`059_media_alist_flow_百度网盘在线秒播与Alist聚合挂载提速.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/059_media_alist_flow_百度网盘在线秒播与Alist聚合挂载提速.md) | `059_media_alist_flow_百度网盘在线秒播与Alist聚合挂载提速.md` | `media` | `flow` | 百度网盘免客户端在线秒播与 Alist 聚合挂载提速方案 |
| 060 | [`060_ide_zed_fix_Zed终端无会话恢复agy历史ID丢失与选号恢复.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/060_ide_zed_fix_Zed终端无会话恢复agy历史ID丢失与选号恢复.md) | `060_ide_zed_fix_Zed终端无会话恢复agy历史ID丢失与选号恢复.md` | `ide` | `fix` | Zed 终端无会话恢复 agy 历史 ID 丢失排障与交互选号恢复 |
| 061 | [`061_ide_terminal_fix_WinTerminal定制版PE图标损坏Defender误杀排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/061_ide_terminal_fix_WinTerminal定制版PE图标损坏Defender误杀排障.md) | `061_ide_terminal_fix_WinTerminal定制版PE图标损坏Defender误杀排障.md` | `ide` | `fix` | WT 定制版 PE 图标注入签名破损致 Defender 误杀排障 |
| 062 | [`062_win_sys_flow_WinGUI自动化能力阶梯与UIA元素点击验证.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/062_win_sys_flow_WinGUI自动化能力阶梯与UIA元素点击验证.md) | `062_win_sys_flow_WinGUI自动化能力阶梯与UIA元素点击验证.md` | `win` | `flow` | Windows GUI 自动化能力阶梯与 UIA 元素点击及截图验证 |
| 063 | [`063_win_sys_flow_Win无窗口服务快捷方式与自重启及PS5.1排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/063_win_sys_flow_Win无窗口服务快捷方式与自重启及PS5.1排障.md) | `063_win_sys_flow_Win无窗口服务快捷方式与自重启及PS5.1排障.md` | `win` | `flow` | 无窗口服务一键启动快捷方式、Web 自重启与 PS 5.1 排障 |
| 064 | [`064_win_chrome_fix_Win单按Alt抢焦点与豆包输入法右Alt语音透传.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/064_win_chrome_fix_Win单按Alt抢焦点与豆包输入法右Alt语音透传.md) | `064_win_chrome_fix_Win单按Alt抢焦点与豆包输入法右Alt语音透传.md` | `win` | `fix` | 单按 Alt 激活 Chrome 抢焦点与豆包输入法语音透传 AHK 排障 |
| 065 | [`065_win_fs_fix_Win文件外部句柄持有原子替换失败写入静默丢失.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/065_win_fs_fix_Win文件外部句柄持有原子替换失败写入静默丢失.md) | `065_win_fs_fix_Win文件外部句柄持有原子替换失败写入静默丢失.md` | `win` | `fix` | 文件被外部持有导致原子替换失败与上层写入静默丢失排障 |
| 066 | [`066_ide_fs_fix_同步publish重入前端覆盖层擦不掉与视图分叉.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/066_ide_fs_fix_同步publish重入前端覆盖层擦不掉与视图分叉.md) | `066_ide_fs_fix_同步publish重入前端覆盖层擦不掉与视图分叉.md` | `ide` | `fix` | 同步 publish 重入与陈旧句柄导致覆盖层擦不掉与视图分叉排障 |
| 067 | [`067_dev_web_flow_本机Web应用自签cookie真机取证与浏览器进入.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/067_dev_web_flow_本机Web应用自签cookie真机取证与浏览器进入.md) | `067_dev_web_flow_本机Web应用自签cookie真机取证与浏览器进入.md` | `dev` | `flow` | 本机 Web 应用自签会话 cookie 真机取证与独立浏览器进入 |
| 068 | [`068_agent_agyman_fix_AGYManager切换失败target-conflict与汉化进程冲突.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/068_agent_agyman_fix_AGYManager切换失败target-conflict与汉化进程冲突.md) | `068_agent_agyman_fix_AGYManager切换失败target-conflict与汉化进程冲突.md` | `agent` | `fix` | Antigravity Manager 切换失败 target-conflict 根因排障 |
| 069 | [`069_agent_agy_fix_AGY桌面端会话覆写逆向与ConnectRPC热推送.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/069_agent_agy_fix_AGY桌面端会话覆写逆向与ConnectRPC热推送.md) | `069_agent_agy_fix_AGY桌面端会话覆写逆向与ConnectRPC热推送.md` | `agent` | `fix` | Antigravity 桌面端会话持久化覆写机制逆向与 ConnectRPC 热推送 |
| 070 | [`070_ide_amwhtml_fix_AnswerMeWithHTML架构与DarkReader暗黑冲突排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/070_ide_amwhtml_fix_AnswerMeWithHTML架构与DarkReader暗黑冲突排障.md) | `070_ide_amwhtml_fix_AnswerMeWithHTML架构与DarkReader暗黑冲突排障.md` | `ide` | `fix` | AnswerMeWithHTML 全景架构与 DarkReader 暗黑冲突排障 |
| 071 | [`071_dev_wails_fix_WailsV3WebView2高内存治理与关窗生命周期重构.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/071_dev_wails_fix_WailsV3WebView2高内存治理与关窗生命周期重构.md) | `071_dev_wails_fix_WailsV3WebView2高内存治理与关窗生命周期重构.md` | `dev` | `fix` | WailsV3 与 WebView2 桌面小工具常驻高内存治理与关窗重构 |
| 072 | [`072_win_ahk_fix_Win11高频AltTab卡键停留在切换界面与AHK钩子修复.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/072_win_ahk_fix_Win11高频AltTab卡键停留在切换界面与AHK钩子修复.md) | `072_win_ahk_fix_Win11高频AltTab卡键停留在切换界面与AHK钩子修复.md` | `win` | `fix` | Win11 高频 Alt+Tab 卡键停留在切换界面与 AHK 钩子竞态修复 |
| 073 | [`073_dev_cli_flow_CLI临时daemon按需拉起与零残留优雅关停.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/073_dev_cli_flow_CLI临时daemon按需拉起与零残留优雅关停.md) | `073_dev_cli_flow_CLI临时daemon按需拉起与零残留优雅关停.md` | `dev` | `flow` | CLI 工具临时 daemon 按需拉起、空闲超时兜底与零残留优雅关停 |
| 074 | [`074_agent_pi_fix_Zed集成PiCodingAgent双层管道难用与openma内存直载SOP.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/074_agent_pi_fix_Zed集成PiCodingAgent双层管道难用与openma内存直载SOP.md) | `074_agent_pi_fix_Zed集成PiCodingAgent双层管道难用与openma内存直载SOP.md` | `agent` | `fix` | Zed 集成 Pi Coding Agent 双层管道难用排障与 openma-pi-acp SDK 内存直载 SOP |
| 075 | [`075_dev_core_flow_发行版二进制嵌SHA溯源与上游源码取证.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/075_dev_core_flow_发行版二进制嵌SHA溯源与上游源码取证.md) | `075_dev_core_flow_发行版二进制嵌SHA溯源与上游源码取证.md` | `dev` | `flow` | 发行版二进制嵌 SHA 溯源与上游对应版本源码取证流水线 |
| 076 | [`076_ide_zed_fix_Zed自定义ACP代理图标机制与注册表兜底.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/076_ide_zed_fix_Zed自定义ACP代理图标机制与注册表兜底.md) | `076_ide_zed_fix_Zed自定义ACP代理图标机制与注册表兜底.md` | `ide` | `fix` | Zed 自定义 ACP 代理图标机制与注册表兜底方案 |
| 077 | [`077_ide_zed_fix_Zed外部ACP线程不自动命名与首消息标题链路.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/077_ide_zed_fix_Zed外部ACP线程不自动命名与首消息标题链路.md) | `077_ide_zed_fix_Zed外部ACP线程不自动命名与首消息标题链路.md` | `ide` | `fix` | Zed 外部 ACP 线程不自动命名与首消息标题链路（横幅抢占 entry + agent 侧命名插件） |
| 078 | [`078_ide_zed_fix_Zed信任表家目录污染致全盘监听与Defender死锁.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/078_ide_zed_fix_Zed信任表家目录污染致全盘监听与Defender死锁.md) | `078_ide_zed_fix_Zed信任表家目录污染致全盘监听与Defender死锁.md` | `ide` | `fix` | 【特大高危】Zed 信任表家目录污染致全盘监听、10G 内存暴涨与 Defender 死锁终极排障 |
| 079 | [`079_dev_core_flow_开源上游Issue高穿透提交与证据链设计SOP.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/079_dev_core_flow_开源上游Issue高穿透提交与证据链设计SOP.md) | `079_dev_core_flow_开源上游Issue高穿透提交与证据链设计SOP.md` | `dev` | `flow` | 开源上游 Issue 高穿透提交、置顶前言破局与证据链设计流水线 |
| 080 | [`080_agent_skills_fix_过度disable致Agent规范失盲与时序元数据防腐治理.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/080_agent_skills_fix_过度disable致Agent规范失盲与时序元数据防腐治理.md) | `080_agent_skills_fix_过度disable致Agent规范失盲与时序元数据防腐治理.md` | `agent` | `fix` | 提级暴露过度 disable 致规范失盲故障与知识库时序元数据防腐治理 |
| 081 | [`081_agent_dsh_fix_Cursor别名冲突致Grok误唤起与xai弹窗修复.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/081_agent_dsh_fix_Cursor别名冲突致Grok误唤起与xai弹窗修复.md) | `081_agent_dsh_fix_Cursor别名冲突致Grok误唤起与xai弹窗修复.md` | `agent` | `fix` | dsh 启动 Cursor ACP 裸命令 agent 与 Grok CLI 冲突致 accounts.x.ai 弹窗修复 |
| 082 | [`082_dev_wails_flow_Go单二进制CLI与Wails双模融合架构及无窗排障SOP.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/082_dev_wails_flow_Go单二进制CLI与Wails双模融合架构及无窗排障SOP.md) | `082_dev_wails_flow_Go单二进制CLI与Wails双模融合架构及无窗排障SOP.md` | `dev` | `flow` | [已转正 → `sh-desktop-dual-channel`] Go 单二进制 CLI 与 Wails v3 双模融合架构、通道隔离与图标双通道（正文已迁移，本条目为存根） |
| 083 | [`083_ide_zed_fix_Zed外接ACP长会话生成完毕转圈卡死与PromptResponse丢失排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/083_ide_zed_fix_Zed外接ACP长会话生成完毕转圈卡死与PromptResponse丢失排障.md) | `083_ide_zed_fix_Zed外接ACP长会话生成完毕转圈卡死与PromptResponse丢失排障.md` | `ide` | `fix` | Zed 外接 ACP 长会话生成完毕转圈卡死与 PromptResponse 丢失排障 |
| 084 | [`084_agent_pi_fix_飞书桥接keeper空转重生pi弹conhost黑窗.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/084_agent_pi_fix_飞书桥接keeper空转重生pi弹conhost黑窗.md) | `084_agent_pi_fix_飞书桥接keeper空转重生pi弹conhost黑窗.md` | `agent` | `fix` | 飞书桥接 keeper 空转重生 pi、conhost 黑窗与自更新后扩展静默掉线排障 |
| 085 | [`085_dev_bruno_flow_api_test_collection.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/085_dev_bruno_flow_api_test_collection.md) | `085_dev_bruno_flow_api_test_collection.md` | `dev` | `flow` | 后端接口提取与 Bruno OpenCollection YAML 脚本生成流水线 |
| 086 | [`086_dev_cmake_flow_trilang_lua_cpp_toolchain.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/086_dev_cmake_flow_trilang_lua_cpp_toolchain.md) | `086_dev_cmake_flow_trilang_lua_cpp_toolchain.md` | `dev` | `flow` | C/C++/Lua 多语言工具链配置、FetchContent 集成与 CMake 构建排障 |
| 087 | [`087_git_gh_flow_repo_cleanup_audit.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/087_git_gh_flow_repo_cleanup_audit.md) | `087_git_gh_flow_repo_cleanup_audit.md` | `git` | `flow` | GitHub 账号仓库大扫除、fork 识别比对、mirror 备份与批量删除 |
| 088 | [`088_browser_pwa_flow_localhost_standalone_window.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/088_browser_pwa_flow_localhost_standalone_window.md) | `088_browser_pwa_flow_localhost_standalone_window.md` | `browser` | `flow` | 本地服务 Chromium SSB (--app 模式) 桌面独立窗口与 PWA 规范面板改造 |
| 089 | [`089_media_docx_flow_office_extract_media.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/089_media_docx_flow_office_extract_media.md) | `089_media_docx_flow_office_extract_media.md` | `media` | `flow` | Office (Word/PPT/Excel) 内嵌原图与媒体资源 ZIP 拆包提取流水线 |
| 090 | [`090_dev_sa_flow_sql_query_builder_extract.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/090_dev_sa_flow_sql_query_builder_extract.md) | `090_dev_sa_flow_sql_query_builder_extract.md` | `dev` | `flow` | 复杂 SQLAlchemy Core 查询抽取为纯文本 SQL 模板与 Query Builder 层重构 |
| 091 | [`091_ide_terminal_fix_WT选中文本CtrlC卡死与剪贴板锁争用排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/091_ide_terminal_fix_WT选中文本CtrlC卡死与剪贴板锁争用排障.md) | `091_ide_terminal_fix_WT选中文本CtrlC卡死与剪贴板锁争用排障.md` | `ide` | `fix` | Windows Terminal 选中文本 Ctrl+C 假死与剪贴板锁争用排障 |
| 092 | [`092_agent_ccswitch_fix_ClaudeCode升级参数冲突与OpenCode路由翻译.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/092_agent_ccswitch_fix_ClaudeCode升级参数冲突与OpenCode路由翻译.md) | `092_agent_ccswitch_fix_ClaudeCode升级参数冲突与OpenCode路由翻译.md` | `agent` | `fix` | Claude Code 升级参数冲突、OpenCode 协议分立与 CC Switch 路由代理翻译 |
| 093 | [`093_win_ql_flow_QuickLook便携部署与Markdown空格秒览.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/093_win_ql_flow_QuickLook便携部署与Markdown空格秒览.md) | `093_win_ql_flow_QuickLook便携部署与Markdown空格秒览.md` | `win` | `flow` | Typora 高内存替代、QuickLook 绿色便携部署与 Markdown 空格即时预览流水线 |
| 094 | [`094_agent_agy_flow_AGY外观RiderDark深色调色板映射与配置.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/094_agent_agy_flow_AGY外观RiderDark深色调色板映射与配置.md) | `094_agent_agy_flow_AGY外观RiderDark深色调色板映射与配置.md` | `agent` | `flow` | Antigravity 桌面端外观与 Rider Dark 调色板映射及配置流水线 |
| 095 | [`095_win_ahk_flow_Win非侵入式AHK启动外挂与极客桌面自动化全景.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/095_win_ahk_flow_Win非侵入式AHK启动外挂与极客桌面自动化全景.md) | `095_win_ahk_flow_Win非侵入式AHK启动外挂与极客桌面自动化全景.md` | `win` | `flow` | Windows 非侵入式 AHK 启动外挂、WMI 脱离热重载与桌面极客自动化全景 |
| 096 | [`096_win_conhost_fix_Windhawk置底Hook与Groupy外壳穿透.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/096_win_conhost_fix_Windhawk置底Hook与Groupy外壳穿透.md) | `096_win_conhost_fix_Windhawk置底Hook与Groupy外壳穿透.md` | `win` | `fix` | [草案/未经验证] Windhawk 控制台置底 Hook 与 Stardock Groupy 外部多标签外壳穿透排障 |
| 097 | [`097_win_tinta_flow_Tinta原生极轻Markdown阅读与双栏编辑.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/097_win_tinta_flow_Tinta原生极轻Markdown阅读与双栏编辑.md) | `097_win_tinta_flow_Tinta原生极轻Markdown阅读与双栏编辑.md` | `win` | `flow` | Typora 终极替代、Tinta 纯 C++/Direct2D 极轻持久阅读与双栏编辑流水线 |
| 098 | [`098_win_fs_fix_父目录Low完整性继承致GUI闪退与安全警告排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/098_win_fs_fix_父目录Low完整性继承致GUI闪退与安全警告排障.md) | `098_win_fs_fix_父目录Low完整性继承致GUI闪退与安全警告排障.md` | `win` | `fix` | 父目录 Low 完整性级别继承致 GUI 无法连接 WinSta0 闪退与安全警告排障 |
| 099 | [`099_agent_dsh_flow_DSHWeb三层更新体系与插件升级及容器校验.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/099_agent_dsh_flow_DSHWeb三层更新体系与插件升级及容器校验.md) | `099_agent_dsh_flow_DSHWeb三层更新体系与插件升级及容器校验.md` | `agent` | `flow` | DSH Web 三层更新体系、Profile 插件升级与 Cordis 容器层叠校验 |
| 100 | [`100_win_sys_fix_Win11DWM显存泄漏AltTab失效与Winlogon平滑自愈.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/100_win_sys_fix_Win11DWM显存泄漏AltTab失效与Winlogon平滑自愈.md) | `100_win_sys_fix_Win11DWM显存泄漏AltTab失效与Winlogon平滑自愈.md` | `win` | `fix` | Win11 DWM 显存泄漏致 Alt+Tab 失效根因与 Winlogon 平滑自愈 |
| 101 | [`101_win_sys_fix_Win11开始菜单固定区幽灵回填与强杀StartMenu自愈排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/101_win_sys_fix_Win11开始菜单固定区幽灵回填与强杀StartMenu自愈排障.md) | `101_win_sys_fix_Win11开始菜单固定区幽灵回填与强杀StartMenu自愈排障.md` | `win` | `fix` | Win11 开始菜单固定区幽灵回填与强杀 StartMenu 自愈排障 |
| 102 | [`102_browser_chrome_fix_扩展MatchPattern端口限制与tabs查询排障.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/102_browser_chrome_fix_扩展MatchPattern端口限制与tabs查询排障.md) | `102_browser_chrome_fix_扩展MatchPattern端口限制与tabs查询排障.md` | `browser` | `fix` | Chrome 扩展 Match Pattern 端口限制致 tabs.query 报错排障 |
| 103 | [`103_browser_mujicv_fix_木及简历自定义CSS行首裁字与导出无样式修复.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/103_browser_mujicv_fix_木及简历自定义CSS行首裁字与导出无样式修复.md) | `103_browser_mujicv_fix_木及简历自定义CSS行首裁字与导出无样式修复.md` | `browser` | `fix` | 木及简历 JS 动态 margin 裁字与自定义 CSS 导出链路修复 |
| 104 | [`104_agent_dsh_fix_MCP浏览器自动化antd表单与文件上传踩坑.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/104_agent_dsh_fix_MCP浏览器自动化antd表单与文件上传踩坑.md) | `104_agent_dsh_fix_MCP浏览器自动化antd表单与文件上传踩坑.md` | `agent` | `fix` | MCP 浏览器自动化 React/AntD 点击、受控组件、上传与卡死踩坑 |


