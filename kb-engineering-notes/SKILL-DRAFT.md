---
name: kb-engineering-notes
description: 开发者通用工程实战手记、自动化流水线与硬核排障知识库。兼具「疑难排障（Windows 文件锁、进程池堆积、闪窗、网络代理、前端覆层残留与视图分叉、本机 Web GUI 真机取证）」与「工程实现/生成流水线（文档与试卷自动化排版、脚手架、复杂脚本设计）」两翼实战 SOP。当遇到疑难报错或需要落地工程自动化流水线时查阅本指南。
---

# 工程实战手记与疑难排障知识库 (Engineering Notes Playbook)

> **注意（隔离与转正说明）**：
> 本文件当前命名为 `SKILL-DRAFT.md`，用于确保在草稿与沉淀阶段**不被外部 Agent 自动注册为活跃技能**。
> 本文件架构完全遵循 `/skill-creator` 规范，未来转正只需执行：
> `git mv SKILL-DRAFT.md SKILL.md`

---

## 1. 知识库架构与设计哲学

本知识库采用**两级渐进式感知架构（Two-stage Progressive Disclosure）**，涵盖**疑难排障（Type A）**与**工程方案/自动化生成流水线（Type B）**两翼：

```text
kb-engineering-notes/
├── SKILL-DRAFT.md                                    # [Stage 1: 元数据与路由总纲] 本文件，负责总览与场景分流
├── 01-SublimeMerge非相邻提交Squash合并与移动重排操作指南.md # [Stage 2: 专项实战] 针对 GUI 提交合并
├── 02-Windows下Git变基PermissionDenied文件锁排障与Abort安全恢复.md # [Stage 2: 专项排障] 针对权限锁与抢救
├── 03-Git变基Rescheduled队列挂起与暂存区冲突深度解析.md # [Stage 2: 专项机制] 针对队列重调度与避坑
├── 04-CursorMarkdown预览独立标签页与侧边栏切换指南.md # [Stage 2: 专项技巧] 针对编辑器 Markdown 预览模式
├── 05-Cursor免审批YOLO模式与沙箱网络配置指南.md # [Stage 2: 专项配置] 针对 Agent 免审批自动运行与网络管控
├── 06-GitWorktree依赖复用与跨语言环境隔离权衡指南.md # [Stage 2: 专项权衡] 针对 Worktree 依赖共享与跨语言环境隔离
├── 07-uv统一全机Python环境与新电脑一键引导复现指南.md # [Stage 2: 专项环境] 针对多 Python 来源统一与新机一键复现
├── 08-Windows下Java与Maven便携子目录配置及Zed任务调试集成指南.md # [Stage 2: 专项配置] 针对 Java/Maven 便携隔离、C 盘防膨胀与 Zed 任务调试
├── 09-Chrome手动关闭窗口固定标签丢失的SNSS会话快照解析与找回指南.md # [Stage 2: 专项抢救] 针对 SNSS 快照解析、独占锁规避与丢失窗口/固定标签找回
├── 10-AntigravityCLI粘贴图片改键Windows终端Kitty协议透传与BOM排障指南.md # [Stage 2: 专项配置] 针对 CLI 粘贴图片改键、Windows Terminal 扩展协议与 UTF-8 BOM 报错
├── 11-Windows计划任务控制台委托闪窗排障与conhost无窗口注册指南.md # [Stage 2: 专项排障] 针对计划任务触发 WT 标签页闪窗（控制台委托 handoff）与无窗口任务手动注册
├── 12-AntigravityCLI执行模式辨析与免批YOLO及配置面板排障指南.md # [Stage 2: 专项配置] 针对 CLI 执行模式、YOLO 权限免审批与配置面板
├── 13-降噪耳机人声泄露声学掩蔽与公有领域高音质音频下载实战指南.md # [Stage 2: 专项实战] 针对降噪耳机人声泄露掩蔽、Commons API 下载与纯 Python 音频合成
├── 14-Windows单手盲切与抽屉式Toggle应用窗口AutoHotkey配置指南.md # [Stage 2: 专项效率] 针对 Windows 多常驻窗口盲切、左手单手 Toggle 与 AutoHotkey v2 自动化
├── 15-python-docx自动化生成举一反三试卷与格式精细排版指南.md # [Stage 2: 专项实现] 针对教辅试卷生成、东亚字体分离(w:eastAsia)与 python-docx 精细排版流水线
├── 16-SublimeTextTerminus中文退格失效与原生PowerShell侧边栏集成指南.md # [Stage 2: 专项排障] 针对 Sublime 内置终端退格失效/中文吞字根因与原生侧边栏 PowerShell 扩展
├── 17-Windows声卡爆音无声与虚拟音频抢占排查指南.md # [Stage 2: 专项排障] 针对设备占用、默认输出抢占与修复
├── 18-Windows代理下微软商店与UWP回环网络豁免排障指南.md # [Stage 2: 专项排障] 针对 CheckNetIsolation 回环豁免
├── 19-Windows内存防死机与Pagefile提交内存归因优化指南.md # [Stage 2: 专项排障] 针对 Pagefile 调优与 Commit 归因
├── 20-Windows系统C盘空间不足排查与安全清理软链接重定向指南.md # [Stage 2: 专项排障] 针对 C 盘清理与环境变量重定向
├── 21-opencode连接GLM模型401鉴权失败与端点排障指南.md # [Stage 2: 专项排障] 针对 GLM 401 报错与 key 映射
├── 22-Zed语言服务器下载失败文件重命名占用与杀毒竞态排障指南.md # [Stage 2: 专项排障] 针对 LSP 下载失败与文件独占锁
├── 23-Zed与IDEA外接ACP代理环境失效与子进程池累积排查指南.md # [Stage 2: 专项排障] 针对 ACP 子进程池膨胀与代理失效
├── 24-Zed面板InternalError会话中断与ACP线程锁竞态归因指南.md # [Stage 2: 专项排障] 针对 Panel 报错与锁竞态归因
├── 25-Zed会话丢失提取与SQLite数据库表解析抢救指南.md # [Stage 2: 专项抢救] 针对 SQLite 历史会话恢复
├── 26-Zed项目级LSP白名单配置与内存占用规避指南.md # [Stage 2: 专项配置] 针对 LSP 项目白名单与内存优化
├── 27-多Git账号GitHub与GitLab共存及SSHIncludeIf配置指南.md # [Stage 2: 专项配置] 针对多账号 SSH 与 includeIf 切换
├── 28-Windows终端Atuin命令历史同步与PwshProfile排障指南.md # [Stage 2: 专项排障] 针对 Atuin 历史丢失与 profile 修复
├── 29-cc-switch配置SQLite直接读写与跨应用模型迁移指南.md # [Stage 2: 专项配置] 针对 cc-switch 数据库直接读写
├── 30-VSCode扩展跨分支IDE手动搬运与注册生效指南.md # [Stage 2: 专项配置] 针对扩展跨 IDE 搬运生效
├── 31-VSCode底部面板Git提交图与分支配色调优配置指南.md # [Stage 2: 专项配置] 针对 GitLG 面板与分支配色
├── 32-Windows便携免安装PowerShell7绿色部署与环境初始化指南.md # [Stage 2: 专项配置] 针对 Pwsh7 绿色部署与环境变量
├── 33-YaHeiConsolasHybrid字体安装与Sublime界面高清字体渲染配置指南.md # [Stage 2: 专项配置] 针对字体安装与渲染调优
├── 34-Windows11右键菜单注册Sublime与注册表快捷管理指南.md # [Stage 2: 专项配置] 针对 Win11 右键菜单注册表项
├── 35-Pi终端快捷键映射改键与滚轮协议冲突修复指南.md # [Stage 2: 专项排障] 针对按键映射与滚轮误触修复
├── 36-Windows各Agent客户端终端机制与GitBash环境切换指南.md # [Stage 2: 专项配置] 针对各 Agent 终端机制与 Git Bash
├── 37-opencode集成chrome-devtools-mcp浏览器控制调试配置指南.md # [Stage 2: 专项配置] 针对浏览器控制与 MCP 调试
├── 38-Zed集成opencodeAgent环境思考档位与供应商迁移指南.md # [Stage 2: 专项配置] 针对 opencode 思考档位与供应商迁移
├── 39-无搜索API时DuckDuckGoHTML端点事实核查与第一方信源收敛流水线指南.md # [Stage 2: 专项流水线] 针对无 API 事实核查与 DDG 逆向
├── 40-AI辅助面向对象OOP重构与设计模式落地演进实战指南.md # [Stage 2: 专项流水线] 针对面向对象 OOP 重构与设计模式演进落地
├── 41-Windows跨盘单文件软链接权限与Junction及硬链接底层机制排障指南.md # [Stage 2: 专项排障] 针对 Windows 跨盘单文件链接、Junction 与开发者模式符号链接
├── 42-多Agent全局规则跨端分发与CLI管道防挂起及隔离探针验证指南.md # [Stage 2: 专项排障] 针对多 Agent 全局规则生效验证、子进程标准输入管道挂起与目录隔离探针测试
├── 43-OpenCodeGo访问DeepSeekV4.1Flash提速实测与关闭思考reasoningEffort指南.md # [Stage 2: 专项排障] 针对 OpenCode Go 模型访问提速、TTFT 归因与 reasoningEffort 调优
├── 44-SublimeTextMarkdown预览切窗口自动跳转浏览器排障与静默快捷键配置指南.md # [Stage 2: 专项排障] 针对 Sublime Markdown 预览切窗口自动跳浏览器抢焦点、MPE 源码 Fallback 缺陷与静默快捷键配置
├── 45-全机AI密钥与模型供应商配置清点排查指南.md # [Stage 2: 专项流水线] 针对全机密钥清点、密钥指纹分组脱敏、SQLite 只读核查与残留识别
├── 46-Windows进程启动来源取证与Everything闲置退出保护永生实例漏洞排障指南.md # [Stage 2: 专项排障] 针对 Windows 进程启动来源取证、UserAssist 与 Everything 闲置退出保护
├── 47-SublimeText全局搜索FindInFiles穿透Gitignore慢查排障与配置防线指南.md # [Stage 2: 专项排障] 针对全局搜索穿透 .gitignore、node_modules 慢查排障与 binary_file_patterns 防线
├── 48-WindowsTerminal分屏窗格布局判定与关闭误触治理指南.md # [Stage 2: 专项排障] 针对 WT 分屏窗格识别、closePane 焦点语义与分屏键误触治理
├── 49-Chrome与Firefox静默安装迅雷插件根因排障与注册表清理及免迅雷BT方案指南.md # [Stage 2: 专项排障] 针对浏览器静默注入扩展、注册表外源安装机制与免迅雷 BT 纯净下载
├── 50-Windows平铺知识库文件名元数据嵌入架构与双端自解释命名规范.md # [Stage 2: 专项流水线] 针对单目录平铺知识库文件名元数据缺失、Explorer排序割裂与批量迁移SOP
├── 51-本地离线Markdown向量检索系统搭建与混合检索专有词漏检排障指南.md # [Stage 2: 专项排障] 针对FastEmbed+LanceDB离线向量检索搭建、语义稀释漏检与混合重排加权
├── 52-Windows原生PE控制台委托DefTerm断层与MCP服务无窗口镜像机制指南.md # [Stage 2: 专项排障] 针对独立版WT委托断层、aoci黑框弹窗与PE Subsystem 2 GUI无窗口镜像
├── 53-WindowsTerminal拆分窗格cd目录重启不保留与OSC99路径上报排障指南.md # [Stage 2: 专项排障] 针对 WT 拆分窗格与会话恢复 cd 目录丢失、ConPTY 隔离与 OSC 9;9 路径上报
├── 54-Windows11豆包输入法任务栏输入指示图标隐藏与Windhawk运行时代码注入指南.md # [Stage 2: 专项排障] 针对 25H2 输入指示图标无法原生隐藏、TSF 语言栏项在 explorer 内绘制与 Windhawk 注入隐藏
├── 55-Manggo划词工具快捷键盲发CtrlC误杀终端会话与Windows默认AltShift切语言排障指南.md # [Stage 2: 专项排障] 针对划词工具全局快捷键盲发 Ctrl+C 杀终端会话、黑名单作用域与进程别名陷阱、Windows 默认 Alt+Shift 切换语言注册表禁用
├── 56-DSH挂载MCP服务npx与uvx启动包装层进程内存膨胀治理与直连入口改造指南.md # [Stage 2: 专项排障] 针对 MCP 服务的 npx/uvx 包装层常驻进程与内存膨胀、profile patch 浅替换语义与直连入口改造
├── 57-常驻PowerShell轮询助手替换为csc现场编译原生Win32小程序与零conhost集成指南.md # [Stage 2: 专项流水线] 针对常驻 PowerShell 地板价与每 tick 开销、csc 现场编译原生 Win32 小程序与零 conhost 集成
├── 58-Git批量提交代码Agent高思考档分析瘫痪根因排障与灰色资产判决指南.md # [Stage 2: 专项排障] 针对 Git 批量提交 Agent 高思考档长考、灰色资产微观考古与提交流水线分析瘫痪
├── 59-百度网盘分享链接免客户端在线秒播与Alist聚合挂载及提速方案指南.md # [Stage 2: 专项流水线] 针对百度网盘免客户端原画秒播、Alist 本地部署与 OAuth 挂载、公开分享外链转存与后台 P2P 防驻留
├── 60-Zed终端无会话恢复agy历史ID丢失排障与PowerShell交互选号恢复指南.md # [Stage 2: 专项排障] 针对 Zed 终端无会话恢复机制、agy 历史会话 ID 丢失、PowerShell 传参展开陷阱与交互式选号恢复器
├── 61-WindowsTerminal定制版PE图标注入签名破损触发Defender启发式木马Bearfoos误杀排障指南.md # [Stage 2: 专项排障] 针对 WT 定制版 PE 图标注入签名破损、触发 Defender 启发式木马 Bearfoos.A!ml 误杀与白名单排除
├── 62-WindowsGUI自动化能力阶梯与UIA元素点击及窗口截图验证指南.md # [Stage 2: 专项流水线] 针对 GUI 自动化能力阶梯（UIA/键盘/鼠标/OCR）、各技术栈无障碍树对照、最小化启动与 DPI 虚拟化及首次点击被吃三大坑
├── 63-Windows无窗口服务一键启动快捷方式与Web服务自重启机制及PowerShell5.1静默失败链路排障指南.md # [Stage 2: 专项流水线] 针对快捷方式无窗口启动常驻服务、端口反查幂等仲裁、WMI 脱离进程树自重启与页面自动重载，及 PS 5.1 六类静默失败链路
├── 64-Windows单按Alt激活Chrome三点菜单抢焦点与豆包输入法右Alt语音透传AutoHotkey排障指南.md # [Stage 2: 专项排障] 针对 Windows 单按 Alt 激活 Chrome 三点菜单抢焦点、豆包输入法长按右 Alt 语音识别上屏中断与 AutoHotkey vkE8 无害掩码静默拆弹
├── 65-Windows文件被外部程序持有导致原子替换失败与上层写入静默丢失排障指南.md # [Stage 2: 专项排障] 针对原子替换被句柄/映射拒绝、EMPER/Win32 5、上层设置静默丢失与 Restart Manager 反查持有者
├── 66-同步publish重入与陈旧句柄导致前端覆盖层擦不掉与视图分叉排障指南.md # [Stage 2: 专项排障] 针对宿主 API 同步 publish 重入、旧 disposer no-op、覆盖层残留擦不掉、presenter 晚一拍撤回 inline 变量与三方对照取证
├── 67-本机Web应用无凭证真机取证与自签会话cookie进入独立浏览器指南.md # [Stage 2: 专项取证] 针对只认签名 cookie/启动令牌的本机 Web GUI、独立 profile 浏览器进不去时，只读存档密钥自签 cookie 取证与回收
├── 68-AntigravityManager切换客户端失败target-conflict根因排障与汉化工具进程冲突解决指南.md # [Stage 2: 专项排障] 针对 Antigravity Manager 切换环境失败弹窗、target-conflict 进程误判冲突、汉化工具排查与 App/CLI 独立凭据体系
├── 69-Antigravity桌面端会话持久化覆写机制逆向与官方ConnectRPC热推送实战指南.md # [Stage 2: 专项排障] 针对 Antigravity 桌面端后台常驻 language_server.exe 内存缓存定时刷盘覆写离线修改、raw_summary Protobuf BLOB 优先级与官方 ConnectRPC 端口及 CSRF 鉴权热推送
└── ...（后续顺次扩充）
```

- **文件名自解释（Self-describing Filename）**：每个知识文件均以`【编号 + 目标工具 + 核心问题场景 + 解决目标】`命名，AI 或开发者仅需浏览文件名列表，即可 100% 判断该文件是否适用于当前上下文，无需逐个打开探查。
- **排障与工程实现双翼**：
  - **Type A（疑难排障型）**：解决踩坑、文件锁、底层冲突，包含精准排查命令、界面现象对照和确定性操作 SOP；
  - **Type B（方案与生成流水线型）**：解决端到端工程实现、内容/试卷/文档自动化生成、样式排版引擎落地，包含业务输入输出、底层技术剖析、代码实现与交付验证模板。
- **条目即技能（隐形技能约定）**：每个 `0N-*.md` 条目在元数据上都视为一个独立 skill，必须带 skill-creator 规范的 frontmatter（`name` + `description`），正文保持单文件 ≤500 行、以 SOP 体为主。

### 条目即技能：为什么“是技能”却检测不到

靠的是两条命名约束，别去动它们：

- harness 在子目录里只认名为 `SKILL.md` 的文件；本目录条目一律用 `0N-主题.md`，因此永不注册（实测：同层的 `SKILL-DRAFT.md` 带完备 frontmatter，也从未出现在技能目录里）；
- 总控文件用 `SKILL-DRAFT.md` 而非 `SKILL.md`，将来转正只需改这一个文件名。

### 条目元数据规范

- `name` 取 `kb-<英文主题短横线>`（如 `kb-docx-practice-generator`），**不带编号**：编号只是排序外壳，`name` 才是将来独立成 skill 时沿用的稳定标识，定了就别改，免得引用失效；
- `description` 按 skill-creator 写法：一句话功能语义 + \"何时查阅\"的触发场景，控制在 200 字符内，关键词尽量用用户真会说的症状词、技术词或目标交付词；
- 本目录的 description 面向**路由与检索**。若某条目将来真要转正为全局技能，除改名建目录外，还必须按 `SKILL-AUTHORING-RULES.md` 把 description 重写成点名触发式（≤70 字符、结尾 `点名使用`）。

---

## 2. 场景路由表（快速匹配）

| 当前遇到的问题或诉求 | 建议读取的条目文档 | 典型现象 / 报错关键词 |
|:---|:---|:---|
| 想在 Sublime Merge 里把两个不相邻的提交合并为一个 | [`01-SublimeMerge非相邻提交Squash合并与移动重排操作指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/01-SublimeMerge非相邻提交Squash合并与移动重排操作指南.md) | 非相邻 commit, 拖拽没反应, Ctrl 多选, Move Commit Down, Squash / Fixup |
| 做了合并操作，界面没报错也没弹窗，怀疑没生效 | [`01-SublimeMerge非相邻提交Squash合并与移动重排操作指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/01-SublimeMerge非相邻提交Squash合并与移动重排操作指南.md) | 误以为没反应, 提交数量少, Stats 文件变化, HEAD 平移 |
| Windows 下变基失败，提示 `Permission denied` 无法写日志 | [`02-Windows下Git变基PermissionDenied文件锁排障与Abort安全恢复.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/02-Windows下Git变基PermissionDenied文件锁排障与Abort安全恢复.md) | `unable to append to logs/HEAD`, Permission denied, 文件锁占用, abort 回滚 |
| 变基失败后停留在 `(onto <hash>)` 状态，暂存区有残留文件 | [`02-Windows下Git变基PermissionDenied文件锁排障与Abort安全恢复.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/02-Windows下Git变基PermissionDenied文件锁排障与Abort安全恢复.md) | rebase in progress, Staged Files, git rebase --abort, 抢救工作区 |
| 变基提示 `It has been rescheduled`，todo 列表混乱 | [`03-Git变基Rescheduled队列挂起与暂存区冲突深度解析.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/03-Git变基Rescheduled队列挂起与暂存区冲突深度解析.md) | rescheduled, git-rebase-todo 重复 pick, 交互变基挂起 |
| Cursor / VS Code 预览 Markdown 默认在侧边栏，想用独立标签页全屏查看 | [`04-CursorMarkdown预览独立标签页与侧边栏切换指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/04-CursorMarkdown预览独立标签页与侧边栏切换指南.md) | Markdown 预览, Ctrl+Shift+V, 侧边栏, 独立标签页, Open Preview |
| Cursor Agent 总弹批准框，想开 YOLO 免审批 / 限制沙箱网络访问 | [`05-Cursor免审批YOLO模式与沙箱网络配置指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/05-Cursor免审批YOLO模式与沙箱网络配置指南.md) | Run Everything, YOLO, Auto-review, sandbox.json, networkPolicy, 批准 |
| 需开 Git Worktree 隔离开发，纠结依赖是否该软链接、担心环境与端口冲突 | [`06-GitWorktree依赖复用与跨语言环境隔离权衡指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/06-GitWorktree依赖复用与跨语言环境隔离权衡指南.md) | git worktree, 软链接, .venv, node_modules, target, editable 倒挂, WinError 32, sccache, pnpm, GOMODCACHE |
| 新电脑只装了 uv，要把全局 `python`/`pip` 与 `uv run` 项目工作流统一成同一套配置 | [`07-uv统一全机Python环境与新电脑一键引导复现指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/07-uv统一全机Python环境与新电脑一键引导复现指南.md) | uv_shim, .uv-global, UV_PYTHON, 一键引导, 新机复现, anaconda 卸载 |
| 全局 `pip install` 报 `externally-managed-environment`，或 venv 里 `python -m pip` 报 `No module named pip` | [`07-uv统一全机Python环境与新电脑一键引导复现指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/07-uv统一全机Python环境与新电脑一键引导复现指南.md) | PEP 668, externally-managed, No module named pip, seed pip |
| Windows 下安装 Java/Maven 导致 C 盘膨胀、Zed 编辑器硬编码 JDK 路径或缺乏调试能力 | [`08-Windows下Java与Maven便携子目录配置及Zed任务调试集成指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/08-Windows下Java与Maven便携子目录配置及Zed任务调试集成指南.md) | Java, Maven, C 盘空间, settings.xml, localRepository, Corretto, jdtls, tasks.json, JDWP, 远程调试 |
| Chrome「继续浏览上次打开的网页」只恢复了一个窗口，手动关闭的窗口（含固定标签页）整体找不回 | [`09-Chrome手动关闭窗口固定标签丢失的SNSS会话快照解析与找回指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/09-Chrome手动关闭窗口固定标签丢失的SNSS会话快照解析与找回指南.md) | 固定标签丢失, 只恢复一个窗口, 最近关闭, 继续浏览上次打开的网页 |
| Chrome 的 Sessions 快照文件被锁无法读取（Device or resource busy / Permission denied），想不重启就解析会话数据、提取固定标签清单 | [`09-Chrome手动关闭窗口固定标签丢失的SNSS会话快照解析与找回指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/09-Chrome手动关闭窗口固定标签丢失的SNSS会话快照解析与找回指南.md) | Device or resource busy, Sessions, Session_, Tabs_, SNSS, cmd5, 固定标签清单 |
| Antigravity CLI 或 Pi 终端中，粘贴图片快捷键 Alt+V 被占想改 Alt+Shift+V，改完终端没反应，或 keybindings.json 报 `invalid character '\ufeff'` | [`10-AntigravityCLI粘贴图片改键Windows终端Kitty协议透传与BOM排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/10-AntigravityCLI粘贴图片改键Windows终端Kitty协议透传与BOM排障指南.md) | 粘贴图片快捷键, edit.paste, app.clipboard.pasteImage, Alt+Shift+V, sendInput, 118;4u, Kitty CSI-u, ufeff, UTF-8 BOM, keybindings.json |
| Windows 计划任务/定时脚本每次触发时，已运行的 Windows Terminal 里闪出一个空白 PowerShell 标签页（“弹终端”），任务“隐藏”属性与 `-WindowStyle Hidden` 都无效 | [`11-Windows计划任务控制台委托闪窗排障与conhost无窗口注册指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/11-Windows计划任务控制台委托闪窗排障与conhost无窗口注册指南.md) | 弹终端, 闪窗, WT 标签页闪现, 控制台委托, handoff, conhost --headless, PseudoConsoleWindow, -WindowStyle Hidden 无效 |
| 需要一条命令手动注册/重配置“无窗口”计划任务（防止终端闪标签页），或任务目录搬移后动作路径失效 | [`11-Windows计划任务控制台委托闪窗排障与conhost无窗口注册指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/11-Windows计划任务控制台委托闪窗排障与conhost无窗口注册指南.md) | register_task.ps1, conhost --headless, New-ScheduledTaskAction, 手动配置, 幂等注册, $PSScriptRoot |
| Antigravity CLI 执行模式（plan/accept-edits）与免批 YOLO 权限混淆、状态栏无 yolo、/permissions 规则为空、/config 面板与免审启动参数配置 | [`12-AntigravityCLI执行模式辨析与免批YOLO及配置面板排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/12-AntigravityCLI执行模式辨析与免批YOLO及配置面板排障指南.md) | Antigravity CLI, YOLO, accept-edits, plan, /permissions, /config, Tool Permission, --dangerously-skip-permissions |
| 佩戴降噪耳机仍能听到人声谈话、轻音乐休止符间隙漏音打断心流，需要构建抗干扰声床、免鉴权下载公有领域名曲或合成立体声褐噪音/自然雨声 | [`13-降噪耳机人声泄露声学掩蔽与公有领域高音质音频下载实战指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/13-降噪耳机人声泄露声学掩蔽与公有领域高音质音频下载实战指南.md) | 降噪耳机, 隔绝人声, 听觉掩蔽, 褐噪音, Brown Noise, 白噪音, 雨声, Wikimedia Commons, 公有领域轻音乐, 萨蒂, 肖邦, 卡农, 巴赫 |
| Windows 常驻应用多（IDE/终端/浏览器/IM）、鼠标跨屏甩动疲劳、Alt+Tab 轮转顺序不稳定、PowerToys 快捷键误触冷启动 | [`14-Windows单手盲切与抽屉式Toggle应用窗口AutoHotkey配置指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/14-Windows单手盲切与抽屉式Toggle应用窗口AutoHotkey配置指南.md) | AutoHotkey, AHK v2, 窗口切换, 盲切, 单手快捷键, Toggle, 前台置顶, 任务栏, PowerToys 缺陷 |
| 需要基于 python-docx 批量生成 Word 试卷或教辅练习题，处理东亚中文字体分离(w:eastAsia)、页边距、行间距微调、化学式上下标排版或自动化装配流水线 | [`15-python-docx自动化生成举一反三试卷与格式精细排版指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/15-python-docx自动化生成举一反三试卷与格式精细排版指南.md) | python-docx, 试卷生成, 举一反三, eastAsia, 宋体回退, 行距, 上下标, 批量生成流水线, Word 排版 |
| Sublime Text 终端插件 Terminus 中文吞字、按 Backspace 无法删除字符、侧边栏右键打开终端看似 PowerShell 实际是 CMD | [`16-SublimeTextTerminus中文退格失效与原生PowerShell侧边栏集成指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/16-SublimeTextTerminus中文退格失效与原生PowerShell侧边栏集成指南.md) | Sublime Text, Terminus, Backspace删不掉, 中文输入法, PSReadLine, Open Terminus here, Open PowerShell here, wt.exe |
| Windows 扬声器/耳机无声、高频或周期性噼啪爆音、默认音频输出设备被虚拟声卡（如 Voicemeeter）静默抢占 | [`17-Windows声卡爆音无声与虚拟音频抢占排查指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/17-Windows声卡爆音无声与虚拟音频抢占排查指南.md) | 声卡爆音, 无声, 默认设备抢占, 虚拟声卡, Voicemeeter, 音频端点, 独占模式 |
| 开启系统/梯子代理时，微软应用商店无法打开、UWP 应用无网络连接或无法初始化 | [`18-Windows代理下微软商店与UWP回环网络豁免排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/18-Windows代理下微软商店与UWP回环网络豁免排障指南.md) | 微软商店打不开, UWP 代理, 回环豁免, CheckNetIsolation, AppContainer, LoopbackExempt |
| 电脑频繁卡死或假死、没开大软件但物理内存使用率居高不下、不确定该不该加物理内存条 | [`19-Windows内存防死机与Pagefile提交内存归因优化指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/19-Windows内存防死机与Pagefile提交内存归因优化指南.md) | 内存防死机, 内存爆满, Commit Charge, 提交大小, Pagefile, 虚拟内存扩容, 内存条判断 |
| C 盘空间告急、红色预警、Temp/缓存/WSL 虚拟硬盘膨胀，需要无损安全腾挪空间 | [`20-Windows系统C盘空间不足排查与安全清理软链接重定向指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/20-Windows系统C盘空间不足排查与安全清理软链接重定向指南.md) | C 盘清理, 空间不足, 软链接重定向, mklink, 环境变量重定向, WSL 迁移, 清理缓存 |
| opencode 等工具调用智谱 GLM 模型接口报 401 身份验证失败、API Key 怎么配都不生效 | [`21-opencode连接GLM模型401鉴权失败与端点排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/21-opencode连接GLM模型401鉴权失败与端点排障指南.md) | GLM 401, opencode 鉴权失败, bigmodel, API Key 优先级, 编码端点冲突 |
| Zed 下载或更新语言服务器时报 `rename os error 5`、下载解压中断或由于杀毒软件占用卡死 | [`22-Zed语言服务器下载失败文件重命名占用与杀毒竞态排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/22-Zed语言服务器下载失败文件重命名占用与杀毒竞态排障指南.md) | Zed LSP 下载失败, rename os error 5, 杀毒竞态, 手工安装 LSP, 文件独占锁 |
| Zed 或 IntelliJ IDEA 外接 ACP agent（如 codex/antigravity）登录失败、代理/CA 证书失效或子进程池堆积吃满内存 | [`23-Zed与IDEA外接ACP代理环境失效与子进程池累积排查指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/23-Zed与IDEA外接ACP代理环境失效与子进程池累积排查指南.md) | ACP agent 登录失败, 代理不生效, 子进程池膨胀, 孤儿进程堆积, stdio 认证 |
| Zed Agent Panel 界面报 `Internal error`、`Invalid request` 或 `Session is closing`，不知从何定位 | [`24-Zed面板InternalError会话中断与ACP线程锁竞态归因指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/24-Zed面板InternalError会话中断与ACP线程锁竞态归因指南.md) | Agent Panel Internal error, Session is closing, telemetry.log, Zed.log 对齐, thread-writer-lock |
| Zed 崩溃或误操作导致历史对话列表空白、重要上下文找不回，需要底层数据恢复 | [`25-Zed会话丢失提取与SQLite数据库表解析抢救指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/25-Zed会话丢失提取与SQLite数据库表解析抢救指南.md) | Zed 会话丢失, sidebar_threads, SQLite 对话恢复, 会话归档抢救 |
| Zed 同时打开多个项目导致各个语言服务器全量拉起吃满内存，需要针对特定项目精细管控 LSP | [`26-Zed项目级LSP白名单配置与内存占用规避指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/26-Zed项目级LSP白名单配置与内存占用规避指南.md) | Zed LSP 白名单, .zed/settings.json, 按项目开 LSP, 内存优化 |
| 既有个人 GitHub 账号又有公司 GitLab 账号，SSH 密钥冲突或提交邮箱身份串号 | [`27-多Git账号GitHub与GitLab共存及SSHIncludeIf配置指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/27-多Git账号GitHub与GitLab共存及SSHIncludeIf配置指南.md) | GitHub GitLab 共存, 多 SSH Key, includeIf, 身份自动切换, .gitconfig 隔离 |
| Windows 下 Atuin 历史命令不同步、前导空格静默丢失、Ctrl+R 无法呼出或 PowerShell Profile 报错打架 | [`28-Windows终端Atuin命令历史同步与PwshProfile排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/28-Windows终端Atuin命令历史同步与PwshProfile排障指南.md) | Atuin 历史丢失, 前导空格, ignorespace, 静默丢弃, Ctrl+R 搜索历史, PSReadLine 冲突, profile.ps1 修复 |
| cc-switch 界面操作卡顿或需要直接通过脚本批量迁移/读写应用模型配置 | [`29-cc-switch配置SQLite直接读写与跨应用模型迁移指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/29-cc-switch配置SQLite直接读写与跨应用模型迁移指南.md) | cc-switch SQLite, 直接修改供应商, 跨应用模型迁移, 绕过 UI 配置 |
| 在 Cursor、Antigravity IDE 或 Trae 中需要用到某个只有 VS Code 插件市场才有的扩展 | [`30-VSCode扩展跨分支IDE手动搬运与注册生效指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/30-VSCode扩展跨分支IDE手动搬运与注册生效指南.md) | VS Code 插件搬运, Cursor 安装离线扩展, Trae 扩展移植, extensions.json 注册 |
| VS Code 缺乏像 IntelliJ IDEA 那样直观清晰的 Git 提交树图谱，希望在底部面板集成 | [`31-VSCode底部面板Git提交图与分支配色调优配置指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/31-VSCode底部面板Git提交图与分支配色调优配置指南.md) | VS Code 提交图, GitLG, 分支配色, 底部面板终端, IDEA 视图复刻 |
| 新电脑没有管理员权限或不想污染系统，需要免安装绿色便携部署 PowerShell 7 | [`32-Windows便携免安装PowerShell7绿色部署与环境初始化指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/32-Windows便携免安装PowerShell7绿色部署与环境初始化指南.md) | PowerShell 7 绿色安装, Pwsh 便携部署, 零系统残留, 用户级环境变量 |
| Sublime Text 或 Sublime Merge 代码中文乱码、字体发虚或想使用清晰的等宽混合字体 | [`33-YaHeiConsolasHybrid字体安装与Sublime界面高清字体渲染配置指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/33-YaHeiConsolasHybrid字体安装与Sublime界面高清字体渲染配置指南.md) | YaHei Consolas Hybrid, Sublime 字体设置, 字体发虚, UI 字体补丁 |
| Windows 11 下希望为文件和文件夹添加“Open with Sublime Text”经典与新型右键菜单 | [`34-Windows11右键菜单注册Sublime与注册表快捷管理指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/34-Windows11右键菜单注册Sublime与注册表快捷管理指南.md) | Sublime 右键菜单, Win11 注册表右键, 经典右键菜单, Open with Sublime |
| 使用 Pi 终端时快捷键冲突、滚轮误触发历史命令或需要自定义按键动作 | [`35-Pi终端快捷键映射改键与滚轮协议冲突修复指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/35-Pi终端快捷键映射改键与滚轮协议冲突修复指南.md) | Pi 终端改键, 按键映射, 滚轮翻历史, 终端按键协议, keybindings |
| Windows 各 AI Agent 终端默认是 CMD 或 PowerShell，经常乱码或脚本语法报错，希望统一走 Git Bash | [`36-Windows各Agent客户端终端机制与GitBash环境切换指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/36-Windows各Agent客户端终端机制与GitBash环境切换指南.md) | Agent 终端乱码, 切换 Git Bash, Codex 终端设置, OpenCode 终端 |
| opencode 需要通过 chrome-devtools-mcp 控制本机浏览器，遇到远程端口连不上或握手失败 | [`37-opencode集成chrome-devtools-mcp浏览器控制调试配置指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/37-opencode集成chrome-devtools-mcp浏览器控制调试配置指南.md) | chrome-devtools-mcp, 浏览器自动化控制, opencode 浏览器插件, 调试端口 |
| Zed 的 opencode 插件思考档位失灵、服务进程断连或无法成功读取自定义 API 配置 | [`38-Zed集成opencodeAgent环境思考档位与供应商迁移指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/38-Zed集成opencodeAgent环境思考档位与供应商迁移指南.md) | Zed opencode, 思考档位, 供应商配置迁移, opencode 启动脚本 |
| 需要核实「某个公开信息到底有没有/是什么」（如某公司内部工具名），手上只有终端、没有搜索 API，且担心把「我没查到」误当「不存在」 | [`39-无搜索API时DuckDuckGoHTML端点事实核查与第一方信源收敛流水线指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/39-无搜索API时DuckDuckGoHTML端点事实核查与第一方信源收敛流水线指南.md) | 公开信息核查, 到底有没有, 第一方信源, DuckDuckGo HTML, html.duckduckgo.com, uddg 解包, SERP 降级页, 假阴性, site: 收敛, 是不是不存在 |
| 遗留系统代码腐化、大类长函数、嵌套分支过多，需进行面向对象 (OOP) 重构、消除条件分支、引入设计模式或提升工程内聚度 | [`40-AI辅助面向对象OOP重构与设计模式落地演进实战指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/40-AI辅助面向对象OOP重构与设计模式落地演进实战指南.md) | OOP 重构, 遗留代码, 代码坏味道, 接缝测试, 字符化测试, 策略模式, 工厂模式, 组合优于继承, 依赖倒置, 架构分层 |
| Windows 下跨盘单文件软链接失败、Junction 报目录名称无效、硬链接禁止跨卷、或符号链接权限不足 (WinError 1314) | [`41-Windows跨盘单文件软链接权限与Junction及硬链接底层机制排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/41-Windows跨盘单文件软链接权限与Junction及硬链接底层机制排障指南.md) | Windows 软链接, Symlink, Junction 目录联接, mklink /H 硬链接, WinError 1314, 开发者模式, SeCreateSymbolicLinkPrivilege, 单文件跨盘链接 |
| 多 Agent (Pi/Claude/OpenCode/AGY) 全局规则验证、CLI 命令行调用卡死 600s 超时、管道 stdin 未闭合或需隔离测试 | [`42-多Agent全局规则跨端分发与CLI管道防挂起及隔离探针验证指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/42-多Agent全局规则跨端分发与CLI管道防挂起及隔离探针验证指南.md) | 多 Agent 全局规则, CLI 管道挂起, readPipedStdin, 600s 超时, < NUL, Print Mode, 隔离探针测试, GLOBAL.md 生效验证 |
| OpenCode Go 模型（deepseek-v4.1-flash 等）响应慢、首字延迟高，纠结要不要改代理/Console 配置，或想关掉思考提速 | [`43-OpenCodeGo访问DeepSeekV4.1Flash提速实测与关闭思考reasoningEffort指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/43-OpenCodeGo访问DeepSeekV4.1Flash提速实测与关闭思考reasoningEffort指南.md) | opencode-go, OpenCode Go, deepseek-v4.1-flash, TTFT, 首字延迟, reasoningEffort none, x-opencode-session, MissingSessionID, prompt cache, 前缀缓存, variant |
| Sublime Text 打开 Markdown 后切窗口频繁跳浏览器抢焦点、或寻找更舒适的 Markdown 阅读与预览方案（排版美化/双栏分屏/免弹窗静默预览/终端阅读） | [`44-SublimeTextMarkdown预览切窗口自动跳转浏览器排障与静默快捷键配置指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/44-SublimeTextMarkdown预览切窗口自动跳转浏览器排障与静默快捷键配置指南.md) | Sublime Text, MarkdownPreviewEnhanced, 抢焦点, 自动跳转浏览器, MarkdownPreview, Shift+Alt+M, MarkdownEditing, MarkdownLivePreview, Terminus glow, minihtml, 预览插件选型 |
| 想把某厂商 API Key 收敛到只留一个工具、或盘点全机有哪些地方配了同一个 key、怀疑「清干净了」其实还有残留 | [`45-全机AI密钥与模型供应商配置清点排查指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/45-全机AI密钥与模型供应商配置清点排查指南.md) | 密钥清点, key 收敛, 只保留一个工具, API Key 残留, LegacyApiKeys 迁移槽, 密钥指纹分组, sha256 分组, SQLite 只读核查, immutable=1, os.walk 跑飞, UnicodeEncodeError gbk, 环境变量没清, 泄露面盘点 |
| 想查明 Windows 后台某个常驻程序（如 Everything）是谁在什么时间拉起的、排查后台驻留与闲置退出保护漏洞 | [`46-Windows进程启动来源取证与Everything闲置退出保护永生实例漏洞排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/46-Windows进程启动来源取证与Everything闲置退出保护永生实例漏洞排障指南.md) | 进程启动来源取证, 谁拉起的, UserAssist, Everything 驻留, idle_exit, 永生实例, 登录会话 |
| Sublime Text 全局搜索速度暴跌扫描数十万文件、穿透 `.gitignore` 搜入 `node_modules` / `.thirdparty` 并报 `Unable to open file` | [`47-SublimeText全局搜索FindInFiles穿透Gitignore慢查排障与配置防线指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/47-SublimeText全局搜索FindInFiles穿透Gitignore慢查排障与配置防线指南.md) | Sublime Text, Find in Files, Use Gitignore, node_modules 慢查, Unable to open file, binary_file_patterns, project filters, F4 遍历, 搜索穿透 |
| 一个 Windows Terminal 窗口里文字被竖/横线切成几块，不知道哪块能关、怕关掉连 agent 会话一起杀，或误触分屏键后想收场 | [`48-WindowsTerminal分屏窗格布局判定与关闭误触治理指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/48-WindowsTerminal分屏窗格布局判定与关闭误触治理指南.md) | Windows Terminal 分屏, 窗格 pane, 右侧窗格关不掉, Ctrl+Shift+W, ClosePane, 焦点窗格, alt+shift+plus 误触, SwitchToTab3, ctrl+alt+4, defaults.json, Move pane to new window, Toggle pane zoom |
| Chrome 或 Firefox 自动静默安装迅雷下载插件、扩展删除了又死灰复燃，或需免迅雷客户端纯净下载种子/磁力链 | [49-Chrome与Firefox静默安装迅雷插件根因排障与注册表清理及免迅雷BT方案指南.md](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/49-Chrome与Firefox静默安装迅雷插件根因排障与注册表清理及免迅雷BT方案指南.md) | 迅雷插件, 自动安装, ChromeExtensionCache, xl_ext_chrome, NativeMessagingHosts, 注册表残留, 裸磁力链, qBittorrent, Tracker加速, 免迅雷下载 |
| 知识库平铺文件越来越多（50+）、Windows Explorer 排序割裂无聚合、文件名太长被截断、机器无法直接提取分类元数据 | [50-Windows平铺知识库文件名元数据嵌入架构与双端自解释命名规范.md](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/50-Windows平铺知识库文件名元数据嵌入架构与双端自解释命名规范.md) | 平铺目录, 文件命名规范, 元数据嵌入, Explorer排序, 正则提取, 受控词典, 批量重命名, DryRun, 回滚SOP |
| 本地文档/技能库离线语义检索搭建（FastEmbed+LanceDB+Watchdog）、专有技术词检索遭遇语义稀释漏检、切块挤占或前端 SyntaxError 假死 | [51-本地离线Markdown向量检索系统搭建与混合检索专有词漏检排障指南.md](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/51-本地离线Markdown向量检索系统搭建与混合检索专有词漏检排障指南.md) | 本地语义检索, FastEmbed, LanceDB, bge-small-zh, 混合检索, Hybrid Search, 语义稀释, Lexical Boost, 关键词加权, Watchdog 防抖, Group-by-File, 默认折叠, WinError 10048, 离线 RAG |
| 使用独立定制版 Windows Terminal 时启动 Agent 强弹微软原版 WT、绕过后弹黑框 conhost 窗口、或原生 PE 二进制 MCP 服务无窗口运行架构 | [52-Windows原生PE控制台委托DefTerm断层与MCP服务无窗口镜像机制指南.md](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/52-Windows原生PE控制台委托DefTerm断层与MCP服务无窗口镜像机制指南.md) | 控制台委托, DefTerm 断层, 原版 WT 弹窗, conhost 黑框, aoci.exe 弹窗, aociw.exe, PE Subsystem 2 GUI, 便携版终端断层, MSIX COM CLSID, 孤儿控制台 |
| Windows Terminal 拆分窗格或会话恢复在 cd 切换目录后，重启依然记不住新目录（退回初始路径），或拆分新窗格无法继承当前目录 | [`53-WindowsTerminal拆分窗格cd目录重启不保留与OSC99路径上报排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/53-WindowsTerminal拆分窗格cd目录重启不保留与OSC99路径上报排障指南.md) | Windows Terminal 拆分选项卡, 记不住目录, cd 重启还原, persistedWindowLayout, state.json, OSC 9;9, OSC 99, prompt, startingDirectory, CWD 上报, 拆分继承目录 |
| Windows 11 任务栏常驻「输入指示」图标（豆包输入法头像、`英` 语言栏）删不掉：设置里没有「输入指示器」、改 CTF\LangBar 注册表无效、杀输入法进程无效，按 Win+Space 后还会自己长回来 | [`54-Windows11豆包输入法任务栏输入指示图标隐藏与Windhawk运行时代码注入指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/54-Windows11豆包输入法任务栏输入指示图标隐藏与Windhawk运行时代码注入指南.md) | 任务栏输入指示, 豆包头像图标, 英 图标删不掉, 输入指示器 找不到, 25H2 语言栏, CTF\LangBar, ShowStatus 被改回, tsf-oime.dll, TSF 语言栏项, explorer 内绘制, Win+Space 出现, Windhawk, taskbar-tray-system-icon-tweaks, hideLanguageBar, hideLanguageSupplementaryIcons |
| 终端按快捷键被当成 Ctrl+C 杀会话或清行、划词工具（Manggo等）黑名单失效、或按完快捷键系统静默切为纯英文美式键盘打不出中文 | [`55-Manggo划词工具快捷键盲发CtrlC误杀终端会话与Windows默认AltShift切语言排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/55-Manggo划词工具快捷键盲发CtrlC误杀终端会话与Windows默认AltShift切语言排障指南.md) | Manggo, 划词翻译, 盲发 Ctrl+C, SendInput, 终端中断, SIGINT, Resume with -c, 黑名单失效, wt.exe 别名陷阱, WindowsTerminal.exe, Alt+Shift, 切语言, 纯英文键盘, HKL 0x4090409, 语言热键禁用, Keyboard Layout Toggle, 00000070 |
| Agent 客户端进程树里每挂一个 MCP 服务就多出一串 `cmd → node → cmd → node → conhost`，内存比"刚启动"多出几百 MB、单条链路子树能占 300MB+ | [`56-DSH挂载MCP服务npx与uvx启动包装层进程内存膨胀治理与直连入口改造指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/56-DSH挂载MCP服务npx与uvx启动包装层进程内存膨胀治理与直连入口改造指南.md) | MCP 进程数, npx 包装层, npx-cli 108MB, uvx, uv 两层, conhost, 常驻内存, 子树 327MB, 内存降不下来, 包装进程不退出, tools/list 比对 |
| 想改 MCP 服务启动命令或覆盖包自带的 MCP 条目，改完 `serverName` 丢了 / 不知道是否生效 / 纠结要不要重启 | [`56-DSH挂载MCP服务npx与uvx启动包装层进程内存膨胀治理与直连入口改造指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/56-DSH挂载MCP服务npx与uvx启动包装层进程内存膨胀治理与直连入口改造指南.md) | profile patch, cordis.patch.yml, config 浅替换, serverName 丢失, dsh --dump-config, 影子 profile, Junction 删除陷阱, MCP 热重挂, 插件要重启 |
| 想按命令行关键字批量杀进程，结果把自己或宿主终端一起杀了（执行器报 Job runner 异常退出） | [`56-DSH挂载MCP服务npx与uvx启动包装层进程内存膨胀治理与直连入口改造指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/56-DSH挂载MCP服务npx与uvx启动包装层进程内存膨胀治理与直连入口改造指南.md) | CommandLine 匹配, Stop-Process 自杀, Windows Job runner exited 4294967295, -File 形态匹配, 排除自身 PID |
| 某个常驻 PowerShell 看护/轮询脚本吃 100MB+ 内存和几个点 CPU（窗口记忆、看门狗、状态监视），想换成原生小工具 | [`57-常驻PowerShell轮询助手替换为csc现场编译原生Win32小程序与零conhost集成指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/57-常驻PowerShell轮询助手替换为csc现场编译原生Win32小程序与零conhost集成指南.md) | 常驻 PowerShell, 内存 106MB, 每 tick 10ms, 4% 单核, Add-Type, cmdlet 反射开销, 换原生, 原生小程序 |
| 想给 Windows 写个不装 SDK 的常驻小工具，或用 csc 现场编译 C# 却报语法错误 | [`57-常驻PowerShell轮询助手替换为csc现场编译原生Win32小程序与零conhost集成指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/57-常驻PowerShell轮询助手替换为csc现场编译原生Win32小程序与零conhost集成指南.md) | csc.exe, Framework64 v4.0.30319, C# 5 语法限制, 字符串插值报错, target:winexe, platform:x64, 编译缓存, sha256 指纹, OpenProcess, WaitForSingleObject |
| 明明设了 `windowsHide` 还是多出 `conhost.exe`；或窗口几何恢复在缩放屏上位置错位 | [`57-常驻PowerShell轮询助手替换为csc现场编译原生Win32小程序与零conhost集成指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/57-常驻PowerShell轮询助手替换为csc现场编译原生Win32小程序与零conhost集成指南.md) | conhost 仍在, windowsHide 无效, SW_HIDE 不等于不分配控制台, GUI 子系统, DPI 虚拟化, dpiAware 错位, SetWindowPos, GetSystemMetrics 虚拟屏, EnumWindows GC.KeepAlive |
| 用户下达批量提交/交付指令（如"提交全部代码"），Agent 在高思考档下陷入长达数分钟的长考停滞、反复反查非代码文件尺寸或把提交流水线当成全库重构审计 | [`58-Git批量提交代码Agent高思考档分析瘫痪根因排障与灰色资产判决指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/58-Git批量提交代码Agent高思考档分析瘫痪根因排障与灰色资产判决指南.md) | Git 批量提交, 分析瘫痪, Analysis Paralysis, 高思考档, 思考超时, 灰色资产, test_*.png, 运行时产物误判, 提交流水线, 深度审计混淆, 10秒收敛 |
| 想查看或下载百度网盘视频/大文件，不想装官方客户端被偷跑 P2P 上行，或需用 PotPlayer/VLC 原画免下载秒播公开分享外链 | [`59-百度网盘分享链接免客户端在线秒播与Alist聚合挂载及提速方案指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/59-百度网盘分享链接免客户端在线秒播与Alist聚合挂载及提速方案指南.md) | 百度网盘, 百度云, 免客户端秒播, Alist, Alist 挂载, 百度网盘 OpenAPI, refresh_token, PotPlayer 秒播, HTTP Range, 偷跑上行, P2P 提速清理, 分享外链转存, errno -7 |
| Zed 重启后终端空白丢失上一轮 agy 会话 ID，或在 PowerShell 脚本传参时报 `conversation "@{Id=...}.Id" not found`，想按项目查看带业务标题的会话清单并交互式选号秒恢复 | [`60-Zed终端无会话恢复agy历史ID丢失排障与PowerShell交互选号恢复指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/60-Zed终端无会话恢复agy历史ID丢失排障与PowerShell交互选号恢复指南.md) | Zed终端, 会话恢复, Session Restoration, 屏幕清空, agy, agy -c, conversationId, 传参展开陷阱, agy-list, agl, history.jsonl, conversation_summaries.db, AI标题提取, 交互选号 |
| 定制版 Windows Terminal 突然消失、桌面/任务栏快捷方式提示“WindowsTerminal.exe 已经更改或移动”、Defender 报毒 Trojan:Win32/Bearfoos.A!ml | [`61-WindowsTerminal定制版PE图标注入签名破损触发Defender启发式木马Bearfoos误杀排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/61-WindowsTerminal定制版PE图标注入签名破损触发Defender启发式木马Bearfoos误杀排障指南.md) | WindowsTerminal.exe 已经更改或移动, 是否删除该快捷方式, Trojan:Win32/Bearfoos.A!ml, Defender误杀, 隔离区还原, ExclusionPath, PE图标签名损坏 |
| 想用脚本或 Agent 自动操作/验证 Windows 桌面软件（点按钮、切页签、截图取证），或想搞清楚 WebView2 与原生控件分别怎么被自动化、“是不是只能模拟鼠标” | [`62-WindowsGUI自动化能力阶梯与UIA元素点击及窗口截图验证指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/62-WindowsGUI自动化能力阶梯与UIA元素点击及窗口截图验证指南.md) | UIA, UI Automation, InvokePattern, 无障碍树, AXTree, 自动化能力阶梯, 模拟鼠标, mouse_event, SendInput, 坐标点击, Agent 自验证 GUI, EnumWindows |
| 自动化点击没反应/点不准、截图缺一块、窗口尺寸诡异（199x34）、窗口莫名最小化启动、坐标整体偏移 | [`62-WindowsGUI自动化能力阶梯与UIA元素点击及窗口截图验证指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/62-WindowsGUI自动化能力阶梯与UIA元素点击及窗口截图验证指南.md) | DPI 虚拟化, SetProcessDPIAware, 首次点击被吃, 前台激活, SetForegroundWindow, PrintWindow, PW_RENDERFULLCONTENT, ShowWindow SW_RESTORE, MainWindowHandle 不对 |
| 想做个桌面快捷方式：双击就启动本地常驻 Web 服务，且全程不弹黑框、不占终端窗口 | [`63-Windows无窗口服务一键启动快捷方式与Web服务自重启机制及PowerShell5.1静默失败链路排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/63-Windows无窗口服务一键启动快捷方式与Web服务自重启机制及PowerShell5.1静默失败链路排障指南.md) | 一键启动, 快捷方式, 不弹黑框, 无窗口启动, conhost, wscript Run 0, CreateNoWindow, WindowStyle Hidden, 双击启动服务 |
| 直连 `.lnk` 到 powershell 仍闪窗；服务已在运行时再点一次会撞端口 `EADDRINUSE`；想做到"在跑就只开界面" | [`63-Windows无窗口服务一键启动快捷方式与Web服务自重启机制及PowerShell5.1静默失败链路排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/63-Windows无窗口服务一键启动快捷方式与Web服务自重启机制及PowerShell5.1静默失败链路排障指南.md) | 闪窗, EADDRINUSE, 端口已占用, 幂等启动, 端口反查, Get-NetTCPConnection OwningProcess, 已经在跑, reuse |
| 给本地 Web 服务做"重启自己"按钮：点完页面卡在重启中不刷新、服务带上了黑框窗口、或重启后起不来 | [`63-Windows无窗口服务一键启动快捷方式与Web服务自重启机制及PowerShell5.1静默失败链路排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/63-Windows无窗口服务一键启动快捷方式与Web服务自重启机制及PowerShell5.1静默失败链路排障指南.md) | 自重启, 重启按钮, 卡在等待重启, 需要手动刷新, 重启后黑框, 无窗口性质丢失, listener is back, WMI Win32_Process Create, 脱离进程树, taskkill /T 不向上 |
| PowerShell 脚本报 `The Try statement is missing its Catch or Finally block` 但 try/catch 明明是对的；或 5.1 下中文注释导致解析崩溃 | [`63-Windows无窗口服务一键启动快捷方式与Web服务自重启机制及PowerShell5.1静默失败链路排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/63-Windows无窗口服务一键启动快捷方式与Web服务自重启机制及PowerShell5.1静默失败链路排障指南.md) | The Try statement is missing, Unexpected token, UTF-8 无 BOM, 中文注释, 编码误读, GBK 解码, 纯 ASCII 脚本, ParseFile 校验 |
| `Start-Process` 报 `Item has already been added. Key in dictionary: 'NO_PROXY'`；或 `EnvironmentVariables` 操作报 null-valued / null array | [`63-Windows无窗口服务一键启动快捷方式与Web服务自重启机制及PowerShell5.1静默失败链路排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/63-Windows无窗口服务一键启动快捷方式与Web服务自重启机制及PowerShell5.1静默失败链路排障指南.md) | NO_PROXY no_proxy 重复键, Item has already been added, Start-Process 不可用, ProcessStartInfo EnvironmentVariables null, cannot index into a null array, Process.Start 替代 |
| 生成的 `.bat`/`.cmd` 内容看起来对但执行毫无反应；或 `Set-Content` 写数组被分号连成一行、`rem` 注释吞掉命令 | [`63-Windows无窗口服务一键启动快捷方式与Web服务自重启机制及PowerShell5.1静默失败链路排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/63-Windows无窗口服务一键启动快捷方式与Web服务自重启机制及PowerShell5.1静默失败链路排障指南.md) | Set-Content 数组分号连接, rem 吞命令, bat 不执行, 退出码 1 无输出, WriteAllText CRLF, 反引号续行误判 |
| 脚本"完全没执行"、连第一行日志都没有，但调用方看到进程创建成功；或日志文件被占用导致新服务起不来 | [`63-Windows无窗口服务一键启动快捷方式与Web服务自重启机制及PowerShell5.1静默失败链路排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/63-Windows无窗口服务一键启动快捷方式与Web服务自重启机制及PowerShell5.1静默失败链路排障指南.md) | NamedParameterNotFound, 参数名不匹配, 参数绑定阶段终止, 无任何日志, WMI 返回 0 不代表成功, 重定向到文件抓错, 日志文件被占用, being used by another process, 日志按端口隔离 |
| 单按或松开 Alt / 右 Alt 键导致 Chrome 右上角三点菜单被高亮选中、打字光标丢失、或豆包输入法长按右 Alt 语音识别松手后无法正常上屏 | [`64-Windows单按Alt激活Chrome三点菜单抢焦点与豆包输入法右Alt语音透传AutoHotkey排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/64-Windows单按Alt激活Chrome三点菜单抢焦点与豆包输入法右Alt语音透传AutoHotkey排障指南.md) | Chrome 三点菜单, 自定义及控制 Google Chrome, 按 Alt 选中, 抢焦点, 光标丢失, 豆包输入法, 右 Alt, RAlt, 语音输入上屏失败, AutoHotkey, AHK vkE8, SC_KEYMENU, 菜单激活屏蔽 |
| 应用设置点了没反应/自动跳回原值、刷新后不生效，日志里是 `EPERM ... rename *.tmp -> <配置文件>`，而文件"明明能写" | [`65-Windows文件被外部程序持有导致原子替换失败与上层写入静默丢失排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/65-Windows文件被外部程序持有导致原子替换失败与上层写入静默丢失排障指南.md) | EPERM operation not permitted, rename tmp, win32 5 Access is denied, 原子替换失败, MoveFileEx REPLACE_EXISTING, 设置静默丢失, revision 不变, HTTP 200 但没落盘, 临时文件+rename |
| 文件被谁占着完全看不出来（编辑器无标签、任务管理器无句柄），关标签页与重启程序都没用，想按文件反查持有进程 | [`65-Windows文件被外部程序持有导致原子替换失败与上层写入静默丢失排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/65-Windows文件被外部程序持有导致原子替换失败与上层写入静默丢失排障指南.md) | 谁占着文件, 文件锁, 句柄反查, Restart Manager, RmGetList, handle.exe 替代, 看不到占用, 关标签页无效, 重启又回来, last_session |
| Agent/编辑器会话把配置目录（`~/.dsh`、`~/.config`）当上下文长期持有，导致该目录下配置文件的写入持续失败 | [`65-Windows文件被外部程序持有导致原子替换失败与上层写入静默丢失排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/65-Windows文件被外部程序持有导致原子替换失败与上层写入静默丢失排障指南.md) | ACP agent 会话, acp_thread opening file, 上下文占用文件, 删除会话, Zed db.sqlite editors 表, 孤儿 editor 行, opencode 会话, 配置目录别交给 agent |
| 主题/皮肤/覆盖层切回浅色后页面仍是旧样式，行内提示却说"当前基座是浅色"，刷新偶尔好、一旦触发就再点也不回来 | [`66-同步publish重入与陈旧句柄导致前端覆盖层擦不掉与视图分叉排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/66-同步publish重入与陈旧句柄导致前端覆盖层擦不掉与视图分叉排障指南.md) | 切主题不生效, 覆盖层擦不掉, overrideTokens, 旧 disposer no-op, 同步 publish 重入, 视图与渲染分叉, inline CSS 变量残留, presenter 晚一拍, 受限擦除, 在途守卫 |
| 页面配色半套：面板是深色、个别卡片仍是浅灰，属性标记与计算变量互相矛盾，控制台无任何报错 | [`66-同步publish重入与陈旧句柄导致前端覆盖层擦不掉与视图分叉排障指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/66-同步publish重入与陈旧句柄导致前端覆盖层擦不掉与视图分叉排障指南.md) | 半套主题, dark token 叠浅色结构, data-ds-dark-theme 缺失, 静态色与别名色分叉, getComputedStyle 取证, Maximum call stack size exceeded, 死循环自激 |
| 本机 Web GUI 只回 `authentication required; reopen the URL printed by …`，自动化浏览器（独立 profile）没有登录态，进不去看真实 DOM | [`67-本机Web应用无凭证真机取证与自签会话cookie进入独立浏览器指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/67-本机Web应用无凭证真机取证与自签会话cookie进入独立浏览器指南.md) | 401, dsh web authentication required, launch token, ?token=, 签名 cookie, HMAC, 凭据库 secret, base64url, authority, 真机取证 |
| 想把自动化浏览器的会话搬进目标站点：只有磁盘上的存档密钥，横幅里的令牌已经滚没了 | [`67-本机Web应用无凭证真机取证与自签会话cookie进入独立浏览器指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/67-本机Web应用无凭证真机取证与自签会话cookie进入独立浏览器指南.md) | document.cookie 自签, HttpOnly 只挡读取, cookie 按 host 不按端口, 跨源脚本注入, CORS, 密钥不回显, 取证后回收 cookie |
| Antigravity Manager 切换环境报错“切换账号失败：操作失败，请查看诊断详情后重试”；日志报 `target-conflict`、`ANTIGRAVITY_PROCESS_FAILED`、`stage: client-selection` | [`68-AntigravityManager切换客户端失败target-conflict根因排障与汉化工具进程冲突解决指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/68-AntigravityManager切换客户端失败target-conflict根因排障与汉化工具进程冲突解决指南.md) | Antigravity Manager, 切换账号失败, 操作失败请查看诊断详情后重试, target-conflict, ANTIGRAVITY_PROCESS_FAILED, client-selection, launch-preflight, antigravity-hans-gui, 汉化工具, 切换到 Antigravity, 共享账号, agy cli 凭据, gemini:antigravity |
| 疑问 Antigravity App 桌面版与 Antigravity CLI 是否共享登录账号；想了解 Manager 中 classic/ide/agy 三端凭据存储机制与多设备登录风控 | [`68-AntigravityManager切换客户端失败target-conflict根因排障与汉化工具进程冲突解决指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/68-AntigravityManager切换客户端失败target-conflict根因排障与汉化工具进程冲突解决指南.md) | antigravity app 共享账号, agy cli 账号, Windows 凭据管理器, state.vscdb, 多设备登录, 多网络登录, 五小时限额, Five Hour Limit, 账号风控 |
| Antigravity 桌面端会话改名不生效、离线改写 SQLite 数据库后被后台定时覆写回滚英文；或侧边栏标题看着依然是旧英文 | [`69-Antigravity桌面端会话持久化覆写机制逆向与官方ConnectRPC热推送实战指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/69-Antigravity桌面端会话持久化覆写机制逆向与官方ConnectRPC热推送实战指南.md) | Antigravity 桌面端改名, 会话标题汉化, language_server.exe, background reconciliation, 幽灵覆写, raw_summary BLOB, Protobuf Wire, ConnectRPC, UpdateConversationAnnotations, csrf_token, 侧边栏没刷新, Ctrl+R 重载 |
| 逆向 Antigravity 核心服务与动态端口通信：如何从运行中常驻进程提取 CSRF Token 并调用官方 RPC 实时热推送数据 | [`69-Antigravity桌面端会话持久化覆写机制逆向与官方ConnectRPC热推送实战指南.md`](file:///d:/Users/language_projects/.agents/skills/kb-engineering-notes/69-Antigravity桌面端会话持久化覆写机制逆向与官方ConnectRPC热推送实战指南.md) | Antigravity 逆向, language_server 端口, WMI 提取 csrf_token, Exa LanguageServerService, UpdateConversationAnnotations, StreamCascadeSummariesReactiveUpdates, 动态端口探测 |



---

## 3. 知识扩充规范（追加新知识时遵循）

当你开发中遇到新的典型踩坑或沉淀出高价值工程实现流水线需要归档时：
1. **确定文件名与 `name`**：文件名遵循 `编号-目标技术核心问题场景与解决目标.md`，序号顺延（如 `0N-DockerDesktop卷挂载Windows符号链接失效排障.md`）；同时在 frontmatter 里定一个 `kb-<英文短横线>` 的 `name`；
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
4. **外部解耦原则**：知识库条目由本路由表完全自洽索引。外部路由器（如 `sh-engineering-notes` 及顶层 `sh-user-skills`）统一采用领域定性描述，严禁绑定条目总数或区间，新增条目无需修改外部技能描述。
