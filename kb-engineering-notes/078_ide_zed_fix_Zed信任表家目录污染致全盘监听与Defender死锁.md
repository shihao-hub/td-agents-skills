---
name: kb-zed-trusted-worktree-leak
description: |
  Zed 编辑器工作区信任表（trusted_worktrees）被父级家目录污染或 ACP 外部目录读取触发根盘符滑坡（Fallback to C:\ / D:\），导致后台动态拉起 23 万全量文件活动监听（live worktrees）、单体内存暴涨至 10GB+、与 Windows Defender (MsMpEng) 内核微筛选器死锁狂吃 75%+ CPU 的完整机理归因、ACP 委托引信拆弹（--no-delegation）、免重启就地脱困与全盘断路器加固 SOP。
version: 2.1.0
created: 2026-10-20
updated: 2026-10-22
id: "078"
domain: ide
scope: zed
type: fix
slug: "Zed信任表家目录污染致全盘监听与Defender死锁"
status: verified
last_verified: "2026-10-22"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: true
---

# ide_fix_078_Zed信任表家目录污染致全盘监听与Defender死锁

> **条目定位**：**【顶级高危事故】Type A 终极排障与架构机理深度复盘条目**  
> **危险评级**：★★★★★（单体吞噬 11.5GB 提交内存，拉爆 Windows Defender 占用 64% CPU，造成磁盘满载与整机假死）  
> **验证环境**：Zed 1.24.3 (Windows x64)、Windows 11 (Defender)、Claude ACP / OpenMA-Pi ACP / Antigravity ACP。  
> **关联条目**：会话提取与 SQLite 抢救见 `025_ide_zed_fix_Zed会话丢失提取与SQLite解析抢救.md`；ACP 进程池累积与内存治理见 `023_ide_zed_fix_Zed与IDEA外接ACP代理失效与进程堆积.md`；文件锁与原子替换排障见 `065_win_fs_fix_Win文件外部句柄持有原子替换失败写入静默丢失.md`。  
> **上游 Issue 追踪**：已向 Zed 官方上游提交两份深度 Bug 报告并建档追踪：  
> 1. 全盘监听与杀毒死锁：[zed-industries/zed#65842](https://github.com/zed-industries/zed/issues/65842)（官方维护者 `@yeskunall` 已接单 Triage）；  
> 2. ACP 隐式 Buffer 句柄泄漏致外部写入 EPERM：[zed-industries/zed#65845](https://github.com/zed-industries/zed/issues/65845)。

---

## 一、灾难现象与典型症状

1. **Zed 主程序吃空内存**：
   任务管理器中 `Zed.exe` 单体物理内存（WorkingSet）暴涨至 **7.7 GB ~ 8.0 GB**，私有提交内存（Commit）突破 **11.5 GB**（且杀掉重启打开任意小工程，一两分钟内依然重新飙满）；
2. **Windows Defender 被拉爆（双进程死锁）**：
   系统杀毒进程 `Antimalware Service Executable`（`MsMpEng.exe`）CPU 狂飙至 **42% ~ 64%**，磁盘读取达 **38 MB/s**；Zed CPU 占用 **31%**，两进程合力吃满整机 CPU；
3. **日志满屏高频报错死循环**：
   `%LOCALAPPDATA%\Zed\logs\Zed.log` 以每秒数十条的速度狂刷系统临时文件与注册表锁冲突：
   ```text
   ERROR [worktree] error processing "C:\\Users\\<user>/AppData/Local/Temp\\~nsu1.tmp": 拒绝访问。 (os error 5)
   ERROR [worktree] error reading file "C:\\Users\\<user>/ntuser.dat.LOG1": 另一个程序正在使用此文件，进程无法访问。 (os error 32)
   INFO  [zed::reliability] worktree diagnostics: projects 2, stores 2, slots 85, live 16, visible 2, strong 14
   ```
   *诊断数据揭露真相：界面上只有 2 个可见项目，后台竟被动态拉起了 **14 个隐藏的活动工作区（live worktrees）**！*

---

## 二、重大误区纠偏与侦破复盘

排查初期极易产生两个“假阳性”判断，必须在此彻底纠偏：

| 初始误区 | 为什么是错的？（确凿反证） |
| :--- | :--- |
| **误区 1：以为是某个特定 Agent（如 openma-pi）的 I/O 漏洞** | **反证**：当为 openma-pi 加上 `--no-delegation` 切断全部文件委托后，用户在另一窗口仅使用纯官方 registry 的 **Claude ACP** 读取跨项目配置时，**内存再次飙到 4GB，Defender 再次狂飙至 63.6%**！这铁证说明 Agent 只是普通读取文件的无辜“引信”，问题在宿主。 |
| **误区 2：以为是 Zed 昨天版本更新引入的新 Bug** | **反证**：用户日常保持持续自动更新，同一版本以前读取外部配置从未出事。这说明代码层早就具备这套逻辑，是**运行期某个数据状态发生了质变**。 |

---

## 三、底层深层机理：架构缺陷与引爆链

### 1. 深度架构追问：为什么 Agent 读外部文件会触发挂载 Worktree？

正常工程常识下，读取一个外部文件不过是一行 `std::fs::read_to_string()` 的毫秒级 I/O，为什么 Zed 偏偏要兴师动众地去挂载一棵庞大的 Worktree？这源于 Zed 内部的两大**过度工程（Over-engineering）与架构耦合硬伤**：

1. **ACP 协议的委托机制与 Zed 的“偷懒复用”**：
   - 在 ACP（Agent Client Protocol）中，Agent 不直接调用 OS 文件系统，而是向宿主（Zed）发送 `fs/read_file` 委托请求；
   - Zed 的工程师在实现该接口时，为了所谓的“高级特性”——*“如果用户正在编辑器某个标签页修改该外部文件但尚未保存（Dirty Buffer），Agent 能读到最新的内存数据而非磁盘旧数据”*，**没有直接调用底层的轻量文件读取，而是直接套用了编辑器的重型核心入口 `Project::open_buffer_by_path()`**！
2. **Zed“不存在孤立文件”的基石契约（Buffer 必须绑定 Worktree）**：
   - Zed 核心基于 **CRDT（协同编辑）** 构建。在它的对象模型中，**任何一个 Buffer 绝不允许悬空存在**，必须绑定到一个 `WorktreeId`，通过工作区相对路径进行全网唯一标识，并以此关联 Language Server（LSP）与 Git Diff 状态；
   - 因此，一旦把读取请求扔给 `open_buffer`，Zed 就强制要求：**必须为该文件找到它所属的工程根目录（Worktree）**！
3. **“轻量只读查询”与“长效工程挂载”的重量级严重失配**：
   - Agent 仅仅需要只读 100 字节的配置内容；
   - 但 Zed 却将其当成：*“用户要在编辑器里把这个文件当作长期工程代码来打开、高亮、索引和编辑！”*
   - 于是 Zed 顺着路径向上递归寻找项目根，一旦在 `trusted_worktrees` 中匹配到被污染的 `C:\Users\<user>`，便自作聪明地在后台将整个人家目录冷启动为活动工作区（为了不破坏前端侧边栏视图，标记为 `visible: false, live: true`），最终点燃了灾难。

---

### 2. 灾难因果链图解：火药桶与引爆链

整个灾难是**底层数据库白名单被污染（火药桶）**与**外部文件读取（引信）**共振引发的系统级雪崩：

```
[历史操作] 曾打开家目录下的单文件 (如 ~/.bashrc、~/.dsh/config)
    │
    ▼ (安全横幅误选)
用户在 Zed 信任横幅中点击了 "Trust parent folder: C:\Users\<user>"
    │
    ▼ (致命埋雷：火药桶成型)
Zed 数据库 trusted_worktrees 表被写入整个家目录：
  (5, 'C:\Users\<user>')
  (6, 'D:\Users')
平时相安无事：因为用户从具体项目启动，该项在内存中处于休眠态。
    │
    ▼ (日常触发：引信点燃)
任何 Agent (Pi / Claude / 外部工具) 跨目录请求读取家目录文件 (如 Temp\scan.py 或 ~/.dsh/config)
    │
    ▼ (致命激活：唤醒后台 Live Worktree)
Zed 收到请求，检查全局信任库，发现 "C:\Users\<user>" 是受信任项目！
Zed 判定："该文件属于合法工程 C:\Users\<user>，立即在后台激活该工程！"
后台强行挂载整个 C 盘家目录 (live 16 worktrees)！
    │
    ▼ (灾难雪崩：全盘监听 + Defender 死锁)
1. File Watcher 递归监听整个人家目录数十万文件 (AppData、Temp、微信、浏览器缓存)；
2. Windows Temp 目录每秒高频产生/删除 .tmp 文件，引发 Zed 疯狂更新文件树；
3. Defender 内核驱动 (WdFilter.sys) 拦截到第三方进程高速触碰系统文件，全面介入实时查杀；
4. Defender 独占扫描与 Zed 并发读取产生文件锁冲突 (os error 5 / 32)；
5. 两者在 CPU 与磁盘上死锁互咬，堆内存飙升至 11.5 GB，界面彻底假死。
---

### 3. 次生灾害深水区：清空信任表后的“盘符根无脑滑坡”（Fallback to C:\）

在实测排障深水区，我们揭露了比“家目录污染”更隐蔽、破坏力更大的系统级架构缺陷：
- **直觉误区**：开发者以为只要把 `C:\Users\<user>` 从 `trusted_worktrees` 表中彻底清除，Zed 找不到受信任工程就会放弃挂载；
- **惊险反转**：当 Agent 恢复历史会话、再次向 Zed 请求读取外部路径（例如 `C:\Users\<user>\.dsh`）时，Zed 向上逐级回溯寻找项目根：
  - `.dsh`：无 `.git`，不受信任；
  - `<user>`：无 `.git`，不受信任；
  - `Users`：无 `.git`，不受信任；
- **致命的兜底逻辑（Fallback to Root）**：
  Zed 代码缺乏根目录边界熔断，**竟然一路无脑回退到了驱动器根路径 `C:\`，直接把整个 C 盘当作了这棵后台 Worktree 的根目录（Root）！**
- **现场日志铁证**：
  ```text
  INFO  [worktree] deferred indexing of 6413 directories in "C:\\" that are outside of git repositories
  ERROR [worktree] error reading file "C:\\Windows/System32/sru": 拒绝访问。 (os error 5)
  ERROR [worktree] error reading file "C:\\Windows/System32/winevt/Logs/Application.evtx": 拒绝访问。 (os error 5)
  ```
- **破坏力倍增**：
  取消信任若无配套规则，挂载范围反而从“家目录”**升级为“整个 Windows 系统盘”**！`C:\Windows\System32`、`winevt`（系统事件日志）、`ProgramData` 等成千上万个带内核排他锁的文件直接把 File Watcher 与 Defender 拖入新一轮死锁！

---

### 4. 深水区第二弹：非系统盘滑坡（D:\ 裸奔）与 ACP 文件委托引燃机制（2026-10-22 追踪）

在 2026-10-22 实战中，我们进一步捕获并侦破了该缺陷在**多驱动器开发环境（非 C 盘主力仓库）**下的全新形态与完整引爆链：

1. **盲区暴露：D 盘“裸奔”被扫爆（231,962 个 entries）**：
   - 开发者主力代码通常位于 `D:\Users` 或非系统盘；前序防御在 `file_scan_exclusions` 中配置了 `**/Windows`、`**/AppData`，**但这全部是 C 盘系统路径，D 盘完全处于防御裸奔状态**；
   - 当 Agent（如 Pi Agent）在排查过程中向 Zed 请求读取 `D:\Users\language_projects\go_projects\glmquota` 时，由于该路径实为**文件夹**而非普通文件，Zed 的 `acp_thread.rs:1716` 打开失败：
     ```text
     2026-10-22T00:25:52 ERROR [crates/acp_thread/src/acp_thread.rs:1716] opening file "D:\\Users\\language_projects"
     ```
   - Zed 向上寻找所属工程，由于父级 `D:\Users` 未被信任且无边界熔断，**再次一路无脑滑坡至驱动器根 `D:\`**！
   - 现场抓包日志铁证：
     ```text
     INFO [zed::reliability] worktree diagnostics: live 10, visible 1, strong 1, entries 236188, visible entries 236089, largest D:\ (231962 entries, 231962 visible)
     INFO [worktree] deferred indexing of 3227 directories in "D:\\" that are outside of git repositories ...
     ```
   - 整个 `D:\` 盘的 Steam 游戏库（`steamapps`）、依赖库与非代码大资产共 **23 万个文件被瞬间挂载扫描**，Windows Defender 内核驱动（`MsMpEng.exe`）CPU 再次暴冲至 **75% ~ 100%**！

2. **引信本质：ACP 的文件系统委托（Delegation）机制**：
   - `@openma/pi-acp` 等 In-Process 适配器默认将 `readTextFile`、`writeTextFile` 委托给客户端宿主 Zed 处理（`fs/read_file`）；
   - 一旦 Agent 试图探测目录或临时路径，Zed 的 `Project::open_buffer_by_path()` 立即套用重型编辑器流程，成为点燃全盘滑坡的引信；
   - **核心领悟**：只要彻底切断 ACP 的文件委托（让 Agent 在自己的 Node.js 内存直接调用原生 `fs`），Zed 就永远不会收到跨盘路径打开请求，从物理源头拔除引信！

---

## 四、确定性排查与终极双层防御 SOP

治理目标：**第一层（就地止血）：无需重启 IDE 释放占用；第二层（源头绝缘）：切断 ACP 委托引信；第三层（物理兜底）：全盘断路器加固。**

### 步骤 0：免重启就地脱困 SOP（当前已被挂死时）

若 Zed 正在全盘狂扫、Defender 处于死锁中，**无需强杀重启 Zed**，可按以下三步就地化解：

1. **销毁死锁 Agent 会话（释放句柄源头）**：
   - 触发全盘扫描的唯一强引用是当前 Agent 面板持有的上下文 Buffer。
   - 打开 Zed 的 Agent 面板顶部会话列表（Threads），找到刚才引发报错的 Thread（如排查外部目录的会话）；
   - **直接点击删除（Delete Thread）或归档**，并新建一个空白会话。`acp_thread` 句柄引用归零，后台 Worktree 立即卸载。
2. **检查 Project 面板并移除滑坡盘符**：
   - 检查左侧项目树根部是否意外多出 `D:\` 或 `C:\` 节点；若有，右键选择 **`Remove from Project`** 即可。
3. **数据库无残留验证（安心保障）**：
   - 实测证明：滑坡的盘符树属于会话级影子工作区（Shadow Worktree），Zed 的 `workspaces` 和 `trusted_worktrees` 表**绝不会持久化写入盘符根**，退出后数据库完全干净，重启绝不会复发。
4. **等待 60 秒**：
   - 句柄释放后，Defender 消化完内核积压队列，CPU 会在 1 分钟左右自动平息回落至 0%。

### 步骤 1：排查当前受信任工作区（安全只读）
```powershell
# 复制副本到临时目录探查，绝不直接读生产库
Copy-Item "$env:LOCALAPPDATA\Zed\db\0-stable\db.sqlite*" "$env:TEMP\" -Force
uv run python -c "
import sqlite3, os
conn = sqlite3.connect(os.path.join(os.environ['TEMP'], 'db.sqlite'))
for r in conn.cursor().execute('SELECT * FROM trusted_worktrees'):
    print(r)
conn.close()
"
```
*判读：若出现 `C:\Users\<user>`、`D:\Users` 或盘符根目录，即确认中招。*

### 步骤 2：安全红线与带时间戳备份
**铁律：必须先确认 Zed 零进程运行，并在修改前备份三件套！**

```powershell
# 1. 确认无 Zed 进程
Get-Process *zed* -ErrorAction SilentlyContinue

# 2. 备份 db.sqlite、db.sqlite-shm、db.sqlite-wal 三件套
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$bakDir = "$env:LOCALAPPDATA\Zed\db\0-stable\backup_$ts"
New-Item -ItemType Directory -Path $bakDir -Force
Copy-Item "$env:LOCALAPPDATA\Zed\db\0-stable\db.sqlite*" "$bakDir" -Force
```

### 步骤 3：单文件 Python 脚本参数化清洗与 WAL 刷盘
编写临时脚本并执行清理（绝不在命令行裸拼接 SQL）：

```python
# clean_zed_trust.py
import sqlite3, os

db_path = os.path.expandvars(r"%LOCALAPPDATA%\Zed\db\0-stable\db.sqlite")
conn = sqlite3.connect(db_path)
c = conn.cursor()

# 目标：仅删除被错误扩大的父级家目录，保留用户真实添加的项目
targets = [
    os.path.expandvars(r"C:\Users\%USERNAME%"),
    r"D:\Users",
    os.path.expandvars("C:/Users/%USERNAME%"),
    "D:/Users"
]

print(f"正在清理被污染的顶级信任项: {targets}")
c.execute("DELETE FROM trusted_worktrees WHERE absolute_path IN (?, ?, ?, ?)", targets)
print(f"清理行数: {c.rowcount}")

conn.commit()

# 核心关键：必须 checkpoint TRUNCATE 强制将修改合并进主库文件
c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
conn.close()
print("WAL checkpoint 完成，数据库已安全对齐。")
```

```powershell
# 执行清理
uv run python clean_zed_trust.py
# 随手清理临时脚本
Remove-Item clean_zed_trust.py -Force
```

### 步骤 4：构建终极双层立体防御（源头绝缘 + 物理断路器）

为了彻底根治滑坡死锁，必须在配置层建立“主动绝缘”与“被动剪枝”双保险：

#### 防线 1（主动源头绝缘）：为 ACP 适配器开启 `--no-delegation`
在 `%APPDATA%\Zed\settings.json` 中，为自定义 In-Process ACP Agent（如 Pi Agent）加上 `--no-delegation` 参数（或环境变量 `PI_ACP_DELEGATION=0`）：

```jsonc
    "Pi Agent": {
      "type": "custom",
      "command": "node",
      "args": [
        "C:/Users/29580/.bun/install/global/node_modules/@openma/pi-acp/dist/bin.js",
        "--no-delegation"  // <-- 核心：切断向 Zed 宿主的文件委托
      ],
      "env": {
        "PI_ACP_DELEGATION": "0"
      }
    }
```
> **原理**：Agent 读取文件/目录将完全在自身的 Node.js 内存进程直接走系统 I/O，遇到目录原生返回 EISDIR，**绝对不会调用 Zed 的 `Project::open_buffer_by_path()`，从物理源头拔除引信**！

#### 防线 2（被动物理断路器）：全驱动器级 `file_scan_exclusions`
不仅排除 C 盘系统目录，还必须覆盖 D 盘等非系统盘上的巨型非代码资产（Steam 游戏库、临时缓存等）：

```jsonc
  "file_scan_exclusions": [
    "**/.git",
    "**/.svn",
    "**/.hg",
    "**/CVS",
    "**/.DS_Store",
    "**/Thumbs.db",
    "**/.classpath",
    "**/.settings",
    "**/node_modules",
    "**/.dsh",
    "**/AppData",
    "**/Windows",
    "**/ProgramData",
    "**/$Recycle.Bin",
    "**/*.evtx",
    "**/*.LOG*",
    "**/System Volume Information",
    // ⬇️ 261022-defense-drive-root：驱动器级断路器，防止退化至 D:\ 时扫爆
    "**/Steam",
    "**/steamapps",
    "**/Program Files*",
    "**/Users/*/AppData",
    "**/Users/*/Downloads",
    "**/*.tmp"
  ]
```

> **机制保障释疑**：
> 1. **为什么有效？** 后台 File Watcher 与 Symbol Indexer 在扫描 `C:\` 时，一旦触碰规则会立刻被底层剪枝，绝不会再去碰 `C:\Windows`、`AppData` 等系统排他锁文件，直接拔除了死锁根基；
> 2. **Agent 还能读写这些文件吗？** **100% 正常读取**。`file_scan_exclusions` 仅作用于后台被动遍历监视，绝不阻断 Agent 或用户对具体单文件的显式主动读取；而且排除了句柄常驻后，外部程序与 Agent 保存文件时再也不会遭遇 `EPERM` 写入丢失。

---

## 五、Defender 现象解释与避坑铁律

### 1. 为什么 Zed 关了之后 Defender 还会狂扫 1~2 分钟？
- **Defender 的异步消化队列**：Zed 在关闭前已向内核驱动提交了成千上万个文件的深度分析请求；
- Zed 退出后，Defender 不会丢弃已入队的未决任务，而是需要花 60 ~ 90 秒将内存中积压的特征比对、解包分析执行完毕；
- 一旦积压任务消化完、且无新进程读写磁盘，Defender 会**自动彻底平息（CPU 归 0%）**，无需手动干预或重启。

### 2. 今后日常操作的防范铁律
1. **绝不勾选“信任父级目录”**：
   在 Zed 中打开 `~/.bashrc`、`~/.dsh/...` 等家目录下的单个配置文件时，如果顶部弹出信任横幅，**只能点击针对当前文件的单次信任，严禁点击“Trust parent folder: C:\Users\<user>”**；
2. **严禁在用户家目录裸跑 `zed .`**：
   在终端处于 `C:\Users\<user>` 时，切勿执行 `zed .` 将整个家目录作为项目打开；
3. **Agent I/O 隔离建议**：
   虽然后台 Worktree 才是真凶，但将本地 Agent（如 Pi Agent）保持本地直接 I/O，不滥用宿主文件系统委托，依然是保障 IDE 稳定轻量的一道坚实防线。
