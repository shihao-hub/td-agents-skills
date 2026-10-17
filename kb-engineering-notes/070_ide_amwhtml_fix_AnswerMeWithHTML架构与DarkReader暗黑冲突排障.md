---
name: kb-answer-me-with-html-guide
description: 针对 Answer me with HTML 可视化技能的全景架构剖析、组件生态与零依赖 CLI 工作流，深度复盘 Dark Reader 等浏览器暗黑插件与 SVG 矢量图反色冲突导致的“白块刺眼/白底白字”排障 SOP，并给出原生 Dark Mode 原理、多设备迁移权衡及新电脑环境初始化配置指南。
version: 1.0.0
created: 2026-10-17
updated: 2026-10-17
---

# 70-AnswerMeWithHTML单页可视化技能全景架构与DarkReader暗黑冲突排障及新环境配置指南

> **核心摘要**：  
> `answer-me-with-html` 是一个通过“模型写结构化 Markdown 草稿 + 本地 CLI 自动化排版”将复杂技术解释转化为单文件交互式 HTML 卡片的 Agent 技能。  
> 本指南系统剖析该技能的组件生态、排版机制与零依赖运行时架构；深度复盘在启用了 Dark Reader 等浏览器强制暗黑插件时，SVG 矢量节点出现“纯白高亮方块刺眼、白底白字看不清”的底层反色断层根因；解答“本机为何配 `mode: dark` 最优、新电脑默认 `dark` 好不好”的跨环境权衡问题，并为未来开发者和 AI 提供完整的新机初始化与配置 SOP。

---

## 一、技能功能全景与工作流架构

### 1. 技能定位与核心价值
在传统 AI 对话中，长篇纯文字的架构讲解、调用流程或多维对比往往阅读负担极大。`answer-me-with-html` 改变了交互范式：
- **模型职责单一**：AI 不需要手写脆弱繁琐的 HTML、CSS 或 SVG 标签，仅需输出约几百字的扩展 Markdown 结构草稿（包含 YAML frontmatter 与代码围栏）；
- **CLI 接管全部排版**：捆绑的本地 CLI 工具（`scripts/am.mjs`）接管布局网格、Dagre 流程图坐标计算、字体嵌入、暗黑主题与对比度计算；
- **交付物纯粹且安全**：产出**单文件离线 HTML**，所有 CSS、SVG 图标与字体完全内联，**零外部 CDN 联网请求，断网即开即看**；同时自带极严格的 CSP（Content Security Policy）安全防护，严禁任何未授权脚本与外链外泄。

```
┌────────────────────────┐      ┌─────────────────────────┐      ┌─────────────────────────┐
│   Agent / 思考模型     │      │   本地 CLI (am.mjs)     │      │     浏览器 (用户端)     │
│                        │      │                         │      │                         │
│  输出扩展 Markdown 草稿 │ ───> │  • Dagre 计算流程图坐标  │ ───> │  单文件离线交互 HTML     │
│  (包含组件围栏与元数据)│      │  • 主题渲染与字体注入   │      │  • 零外链、断网秒开     │
│                        │      │  • STE 严格可读性检查   │      │  • 内置明暗切换/源码复制│
└────────────────────────┘      └─────────────────────────┘      └─────────────────────────┘
```

### 2. 支持的可视化组件生态
该技能内置了丰富的声明式图表组件，通过简单的代码块标记即可被编译为矢量图形：

| 组件名称 | 声明标识符 | 适用业务场景 | 底层渲染形态 |
| :--- | :--- | :--- | :--- |
| **流程图 (Flow)** | ````flow` | 架构全景、协议调用链路、分支判断、状态迁移 | 基于 Dagre 算法布局的纯 SVG 流程图，支持矩形、菱形分支、数据库圆柱等 |
| **时序图 (Sequence)** | ````sequence` | 多角色交互、客户端与服务端网络握手、往返 RPC 时序 | 自动按标签宽度排列生命线与激活框的 SVG 时序图 |
| **分类树 (Tree)** | ````tree` | 目录结构、组织架构、知识层级体系 | 自动对齐的节点树形拓扑 |
| **数据图表 (Chart)** | ````chart` | 耗时对比、Token 消耗对比、性能压测基准柱状/条形图 | SVG 响应式柱状/条形图，支持主色高亮与参考灰条比对 |
| **文章批注 (Annot)** | ````annot` | 逐句审阅、代码评审、法规与条约批注分析 | 左右分栏行级对齐的批注视图 |
| **决策卡片 (Ask)** | ````ask` | 方案比选、架构选型、用户确认操作 | 页面内嵌的高交互单选/多选卡片 |
| **基础排版面板** | `callout` / `kv` / `table` | 关键结论、键值对参数概览、规格明细对比 | 纯 CSS Grid 弹性卡片与精致表格 |

### 3. 极简运行时契约
- **语言与版本**：仅需 **Node.js 20+** 环境；
- **零依赖安装**：整个 CLI 编译为单个独立脚本 `scripts/am.mjs`（约 900KB），**不需要执行 `npm install`**，杜绝 `node_modules` 膨胀；
- **标准调用命令**：
  ```bash
  # 基础渲染
  node "<skill_dir>/scripts/am.mjs" render "<draft.md>"
  # 不自动弹窗（静默生成，供 Agent 后台流水线调用）
  node "<skill_dir>/scripts/am.mjs" render "<draft.md>" --no-open
  # 查看与修改全局配置
  node "<skill_dir>/scripts/am.mjs" config
  ```

---

## 二、Dark Reader 暗黑插件冲突现象与排障实录

### 1. 现象直击：白块刺眼与白底白字
当用户在 Chrome / Edge 中安装了主流暗黑扩展 **Dark Reader**（处于开启暗色滤镜状态），并打开 `answer-me-with-html` 生成的页面时，会出现严重的视觉灾难：
1. **普通文本面板正常变黑**：结论面板（A）、组件表格（D）的背景被插件成功置为深黑底色，文字变白；
2. **流程图与时序图节点出现“高亮白块”**：中间流程图（C）中的“草稿”、“解析”、“布局”等方块，以及时序图中的“Browser”角色框，依然呈现为刺眼的亮白色（`#ffffff`）；
3. **字迹完全隐形（白底白字）**：白色方框内部的文字，被 Dark Reader 强行反转成了浅白色，导致在纯白背景上看纯白文字，**核心信息完全不可读**；
4. **置灰对比柱状图变成纯白条柱**：柱状图对比项（如基准 `612`）使用了浅灰填充，在插件下同样沦为大白块，数字无法阅读。

---

### 2. 底层机制与反色断层剖析

为什么页面的普通 HTML 正常变黑，而图表节点却会呈现亮白？

```
【HTML 盒模型元素】 (div, section, p)
  浏览器 DOM 样式 ──> Dark Reader 识别为网页背景 ──> 强行注入反色 CSS ──> 正常变暗黑背景 ✓

【SVG 矢量图形元素】 (<rect class="am-node-shape">)
  SVG 矢量图形 ──> Dark Reader 为防破坏插画/Logo ──> 保护策略：不强制覆盖 fill ──> 保持 Light 纯白 ✗
  SVG 文本标签 ──> Dark Reader 识别为文本 (<text>) ──> 依然强制反白文字 ──> 灾难：纯白底 + 纯白字 ✗
```

1. **Light 模式下的变量解析**：
   该技能默认配置为 `mode: auto`。若宿主 Windows 系统的颜色外观偏好为“浅色”，页面在初始化时触发 Light 规则：
   - 背景 `--bg: #f6f6f3;`
   - 卡片与节点填充 `--paper: #ffffff;`
   - 边框 `--line: #1d2026;`
2. **SVG fill 属性与 Dark Reader 的保守反色策略**：
   `am.mjs` 对节点的 CSS 定义为：
   ```css
   .am-node-shape {
     fill: var(--node-fill, var(--paper, #ffffff));
     stroke: var(--node-stroke, var(--line, #1d2026));
   }
   ```
   Dark Reader 在处理网页时，会严格区分“普通 DOM 盒模型”与“SVG 矢量图”：
   - 对普通 `div` / `section`，插件会强力重写 `background-color`；
   - 对 `<svg>` 内部的 `<rect>`、`<path>`、`<polygon>`，插件为了避免破坏网页矢量插画、公司 Logo、复杂图标的色彩准确性，**默认不重写 `fill` 属性**；
   - 此时，节点 rect 的 `fill` 仍然解析为 Light 模式下的 `--paper` 即 `#ffffff` 纯白；
3. **文本强制反色引发“白底白字”**：
   与此同时，插件却对所有的 `<text>` 标签执行了全局文本规则，强行将字体颜色反色为 `#e8e6e3`（亮白）。**结果就是明晃晃的纯白方块叠上纯白字，如同暗室里的刺眼聚光灯**。

---

### 3. 为什么原生 Dark 模式（方案 1）远优于 CSS 补丁（方案 2）？

面对这一冲突，技术上存在两种解法：

| 维度 | 方案 1：开启 Skill 原生 Dark 模式（推荐并采用） | 方案 2：在打包代码 `am.mjs` 中打 CSS 补丁 |
| :--- | :--- | :--- |
| **实施方式** | `am config set mode dark`（修改全局配置） | 在 900KB 单文件 `am.mjs` 模板中硬编码覆盖样式 |
| **升级与维护** | **零维护**：配置存放在 `~/.answer-me-with-html/config.json`，技能后续 `git pull` 升级完全不丢配置 | **脆弱**：属于猴子补丁（Monkey Patch），一旦技能更新就会被完全冲掉覆盖 |
| **色彩质感** | **顶级原生调配**：深蓝图纸底色 `#0d1c31` + 浅蓝白文字 `#e6edf7` + 柔和浅蓝线框 `#c9d6e8`，色彩体系浑然天成 | **被动缝补**：强制通过 `!important` 压暗颜色，图表层次感与渐变容易发闷、不协调 |
| **插件协同** | **完美放行**：Dark Reader 检测到网页背景本来就是深色，**自动跳过反色干预**，呈现 100% 原汁原味 | **仍有竞态**：若插件滤镜策略变更，可能再次发生样式特异性争抢 |

**结论**：方案 1 是架构上最纯净、工程上最安全、视觉上最优雅的终极解法。

---

## 三、深色模式权衡与跨电脑配置决策树

### 1. 本机环境复盘：为什么设为 `mode: dark` 最优？
在本机上，用户的 Chrome 浏览器长期安装并启用了 Dark Reader 扩展，代表用户的**核心阅读习惯是全局暗黑**。
在此环境下，将 `mode` 设为 `dark`：
- 完美迎合用户的暗黑阅读偏好；
- 让页面在底层就输出原生深色变量，使 Dark Reader 自动放行，彻底从根源抹除了 SVG 白块反色 Bug。

---

### 2. 核心疑问解答：在新电脑或他人电脑上，默认 `dark` 好不好？

> **用户的疑虑**：  
> “默认 dark 是因为本机的 chrome 默认全暗色，所以在本机是很匹配的。假如新电脑不这样，是不是默认 dark 不好？”

这是一个极具工程洞察力的好问题。答案需要分场景权衡：

#### 场景 A：新电脑也是暗黑主题用户（或安装了 Dark Reader）
- **结论**：**设为 `mode: dark` 依然是最优解**。
- **原因**：不仅规避了 Dark Reader 的反色冲突，还能享受到极具科技感的蓝图（blueprint）或 shadcn 深色卡片质感。

#### 场景 B：新电脑是纯净浅色环境（未装暗黑插件，Chrome 是默认纯白）
- **结论**：**此时若强制 `mode: dark`，体验可能不是最舒适的**；
- **原因**：
  1. 在四周全白、屏幕高亮的纯浅色办公场景下，突然弹出一个深蓝/纯黑的网页，会产生较强的“视觉撕裂感”；
  2. 纯净浅色环境下，该技能的浅色主题（如 `blueprint` 浅灰蓝工程图纸、`paper` 纯白纸面打印风）其实非常精致清晰，并没有任何白块遮挡字迹的问题；
  3. 纯净浅色浏览器原本能完美支持 `mode: auto`（跟随 Windows 系统的昼夜节律自动切换）。

---

### 3. 跨环境黄金配置决策树与速查表

在不同设备上配环境时，遵循以下决策逻辑：

```
                ┌──────────────────────────────────────┐
                │        新电脑环境初始化配置          │
                └──────────────────────────────────────┘
                                   │
                  浏览器是否安装了 Dark Reader 等强制暗黑插件？
                                   │
                 ┌─────────────────┴─────────────────┐
                 │ 是                                │ 否
                 ▼                                   ▼
    ┌───────────────────────────┐       操作系统是否开启了全局深色模式？
    │ 必须执行：                │                    │
    │ am config set mode dark   │          ┌─────────┴─────────┐
    │ (避免 SVG 矢量白块冲突)   │          │ 是                │ 否
    └───────────────────────────┘          ▼                   ▼
                                   ┌───────────────┐   ┌───────────────────────────┐
                                   │ 推荐执行：    │   │ 推荐保持默认：            │
                                   │ mode dark     │   │ am config set mode auto   │
                                   │ (享受原生质感)│   │ (随系统自适应浅色纸面风)  │
                                   └───────────────┘   └───────────────────────────┘
```

#### 配置对照速查表

| 设备场景 | 推荐 `mode` 配置 | 推荐 `theme` 配置 | 理由与预期效果 |
| :--- | :--- | :--- | :--- |
| **本机（安装了 Dark Reader）** | **`dark`**（必须） | `blueprint` 或 `shadcn` | 彻底杜绝插件反色导致的 SVG 白块与白底白字 Bug |
| **新电脑（纯净办公机，浅色 Chrome）** | **`auto`** | `auto`（长文用 paper，图表用 blueprint） | 保持与办公环境一致的清爽白底黑字纸面风，跟随系统日落自适应 |
| **新电脑（全暗黑开发者工作站）** | **`dark`** | `blueprint`（工程风）或 `shadcn`（极简风） | 原生暗黑高对比度，长时间编程护眼 |
| **投影仪/大屏演示机** | **`light`** | `paper` | 浅色高明度白底黑字，投影对比度最高 |

---

## 四、AI 与未来开发者新电脑环境搭建 SOP

未来的你或任何 AI 在新电脑上配置、迁移该环境时，只需按以下步骤执行：

### Step 1：前置运行时检查
该技能要求 Node.js 20 及以上版本：
```powershell
# 1. 检查 Node.js 版本
node -v

# 2. 若未安装或低于 v20，在 Windows 终端下一键安装 LTS
winget install OpenJS.NodeJS.LTS
```

### Step 2：定位技能目录与配置持久化
该技能无需安装任何 npm 包。进入技能所在目录即可使用：
```powershell
# 技能根目录示例：
$SkillDir = "D:\Users\language_projects\.agents\skills\answer-me-with-html"

# 查看当前配置
node "$SkillDir\scripts\am.mjs" config
```

### Step 3：按宿主环境一键应用最佳配置
根据上一节的决策法则，执行对应配置：

```powershell
# 【若新电脑也开了 Dark Reader 插件】—— 必须锁定深色
node "$SkillDir\scripts\am.mjs" config set mode dark

# 【若新电脑是标准浅色办公环境】—— 恢复随系统自适应
node "$SkillDir\scripts\am.mjs" config set mode auto

# 【可选】关闭渲染后自动弹浏览器打扰（适合纯后台任务）
node "$SkillDir\scripts\am.mjs" config set open off

# 【可选】设置默认主题（auto / blueprint / shadcn / paper）
node "$SkillDir\scripts\am.mjs" config set theme blueprint
```

> **配置文件底层路径**：  
> - Windows：`C:\Users\<用户名>\.answer-me-with-html\config.json`  
> - Linux/macOS：`~/.answer-me-with-html/config.json`  
> 纯 JSON 结构，直接写入 `{"mode": "dark"}` 等价于 CLI 命令。

### Step 4：排障抢救速查表
未来在新机器上使用时，若遇到异常，查阅下表秒级修复：

| 异常现象 | 核心根因 | 抢救 SOP（直接执行） |
| :--- | :--- | :--- |
| **流程图出现白色大方块、字看不清** | 浏览器开了暗黑插件（如 Dark Reader），与浅色 SVG fill 冲突 | `node "$SkillDir\scripts\am.mjs" config set mode dark` |
| **执行 `am render` 报 `node: command not found`** | 新机器未安装 Node.js 或未加入 PATH | `winget install OpenJS.NodeJS.LTS`，重启终端 |
| **生成页面后不想每次弹浏览器打断思路** | `open` 配置项处于开启状态 | `node "$SkillDir\scripts\am.mjs" config set open off` |
| **磁盘缓存页面太多，需要清理** | 历史渲染页面累积在 `~/.answer-me-with-html/pages/` | `node "$SkillDir\scripts\am.mjs" clean --all` |
| **想把所有配置重置为出厂初始状态** | 配置项被改乱 | `node "$SkillDir\scripts\am.mjs" config reset` |
