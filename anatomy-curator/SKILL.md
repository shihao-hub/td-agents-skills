---
name: anatomy-curator
description: 精密机械图谱策展人与生命周期管理包装器：端到端统筹 isometric 交互式机械原理图谱（anatomy）的生成与自动化入库归档。当用户需要绘制技术原理的拟物机械仪态图（如仪表、阀门、限流器、排队机、储能腔等）、或需要检索、导出、展示和管理已收录的 anatomy 机械图谱资产时使用。自动委托原生 anatomy 技能完成高质量制图与原理解析文档编写，并在完成后立即调用 anatomymanager CLI 将全套代码与多媒体资产持久化至本地 SQLite 单文件数据库，实现生命周期闭环与一键 WebUI 预览。
version: 1.1.0
created: 2026-10-20
updated: 2026-10-21
---

# anatomy-curator：精密机械图谱策展与资产归档包装器

本技能是原生 `anatomy` 机械制图技能的**资产全生命周期管理包装器（Wrapper & Lifecycle Curator）**。
在保持原生 `anatomy` 纯洁性（不侵入修改其代码与提示词、随时平滑跟进上游更新）的前提下，为用户提供**“制图 ➔ 归档 ➔ 检索 ➔ 展示”**的一站式自动化闭环。

---

## 🛠️ 底座工具链位置契约

本包装器默认依赖已编译就绪的 Go 二进制管理工具与单文件数据库：
- **管理器执行程序**：`D:\Users\language_projects\go_projects\anatomymanager\anatomymanager-cli.exe`（release / prod 通道，Console 子系统，shell 正常等待、管道 / `--json` 可捕获）。同目录下 `anatomymanager-gui.exe` 是 GUI 通道，**只负责桌面工作台，不接受任何子命令**（传参也会被忽略、直接出窗口）。dev 通道对应 `anatomymanager-cli-dev.exe`（数据库落 `dev` 子目录）。
- **数据库落盘路径**：**由你调哪个 exe 决定**，不是可配项：
  - `anatomymanager-cli.exe` → `%APPDATA%\language_projects\anatomymanager\prod\anatomy.db`
  - `anatomymanager-cli-dev.exe` → `%APPDATA%\language_projects\anatomymanager\dev\anatomy.db`
  - 不传 `--db` 时按二进制所属通道自动落库；**严禁**手拼 `--db`（会造出用户 GUI 看不到的孤儿库）。

### 🧭 通道判定（归档前必做，一条命令自证）

```powershell
D:\Users\language_projects\go_projects\anatomymanager\anatomymanager-cli.exe where --json
```

解读回执并按下列口径选 CLI（与 `anatomymanager` README 的「Agent 接入与通道判定」一致）：

| 回执 | 动作 |
| :--- | :--- |
| `runningGuis` 里与本 CLI 同通道为 `true` | 继续用本 CLI（`recommendation` 会写 OK） |
| 另一个通道的 GUI 在跑 | **改用 `anatomymanager-cli-dev.exe`**（或 prod 对应版本），保持与用户窗口一致 |
| 两个通道都没 GUI 在跑 | **默认用 release 版 `anatomymanager-cli.exe` 写 prod**（用户日常双击的正式版）；用户明确说在开发 anatomymanager 时才切 dev |

> `where` 无副作用：库不存在时只报 `dbExists: false`，不会凭空建空库。

---

## 🚀 核心工作流（制图与归档全自动管道）

当用户提出任何精密机械可视化需求（例如：“用 anatomy 帮我画一个高并发连接池阀门图谱”、“画一个令牌桶测绘台”）时，必须严格执行以下三阶段流水线：

```
[ 阶段一：意图解析与制图 ]
       │ 委托原生 anatomy 规范，在独立临时目录产出 HTML/SVG/MJS/PNG 与 Markdown 原理文档
       ▼
[ 阶段二：自动化持久化归档 ]
       │ 先 `where --json` 判定通道，再调用 <CLI> ingest --json 将全部产物整块归档进 SQLite BLOB
       ▼
[ 阶段三：交付验证与一键启动 ]
       │ 输出归档回执 JSON，提供 WebUI 启动命令与离线导出命令
```

### 阶段一：委托制图（遵循原生 anatomy 标准）

1. **确定工作目录**：
   在任务临时工作目录（例如项目临时输出目录或当前会话临时路径）中构建图谱。
2. **构思物理实体**（*The object is the explanation*）：
   - 将抽象概念拟物化为真实物理设备（如基座、导轨、精密旋钮、弹簧测力计、指针刻度盘、指示灯、连杆机构）。
   - 编写原理说明文档 `doc.md`（清晰阐述该物理机械如何映射计算机底层原理）。
3. **产出规范产物**：
   - 核心主页面：`index.html` 或 `<name>.html`
   - 绘图脚本：`<name>.mjs` / `model.mjs`
   - 静态/缩略图：`<name>.png`（可选但建议）
   - 原理文档：`<name>-anatomy.md`

### 阶段二：自动化归档（Ingest Pipeline）

图谱测试渲染无误后，**Agent 必须立即主动调用底座 CLI 将全部产物持久化**，切忌让产物散落在临时目录。

先跑上面的「通道判定」选定 CLI 路径（记为 `<CLI>`），再执行：

```powershell
<CLI> ingest `
  --name "<唯一短标识，如 connection-pool>" `
  --title "<人类可读完整标题，如 高并发连接池流道定压阀测控台>" `
  --dir "<产物所在的完整绝对路径>" `
  --doc "<原理说明 md 文件的完整绝对路径>" `
  --session-id "<当前Agent会话ID，若无法获取可留空>" `
  --category "figure" `
  --tags "database,pool,concurrency,valves,isometric" `
  --json
```

**确认回执**：
命令将输出标准 JSON。Agent 解析并校验 `status == "success"`，确认归档文件数（`filesCount`）、主渲染文件（`primaryHtml`），以及**实际写入的通道与库路径**（`channel` / `dbPath`）。

### 阶段三：对用户交付成果

归档成功后，Agent 需在最终回复中向用户汇报：
1. **作品基本信息**：标题、唯一标识（ID）、分类、涵盖的物理组件；
2. **归档去向**：直接报出回执里的 `channel` 与 `dbPath`（例：`prod 通道 → …\prod\anatomy.db`），并提醒用户「看哪个窗口：prod 对应 `anatomymanager-gui.exe`，dev 对应 `anatomymanager-gui-dev.exe`」；
3. **查阅方式**：
   - 启动本地可视化服务：`<CLI> serve --open`（端口默认动态探测，`--open` 自动开浏览器；若需在回复中给出地址，从终端输出或 `%APPDATA%\language_projects\anatomymanager\<dev|prod>\anatomymanager.log` 读取，不要写死 8765），或在 `D:\Users\language_projects\go_projects\anatomymanager` 下双击对应通道的 GUI；
   - 或单独离线导出：`<CLI> export <name> --out ./dist/<name>`。

---

## 🔍 管理与运维子意图（Query & Maintenance）

当用户不仅是制图，而是希望管理历史作品时，Agent 直接调用对应的 CLI 命令（<CLI> = 按通道判定选定的二进制，不确定时先 `where --json`）：

### 0. 自省当前通道与库（排障第一步）
```powershell
<CLI> where --json
```

### 1. 列出已有图谱库
```powershell
<CLI> list --json
```

### 2. 查询特定图谱详情与包含文件
```powershell
<CLI> get <name> --json
```

### 3. 导出数据库中的图谱到本地文件夹
```powershell
<CLI> export <name> --out "<目标导出目录>"
```

### 4. 调取 Agent 协同参数 Schema
```powershell
<CLI> schema ingest
```
