---
name: kb-zed-trusted-worktree-leak
description: |
  Zed 编辑器工作区信任表（trusted_worktrees）被父级用户家目录污染，导致后台被动态拉起全量活动监听（16 live worktrees）、单体内存暴涨至 10GB+、与 Windows Defender 内核微筛选器（WdFilter）死锁狂吃 60%+ CPU 的完整机理归因、假阳性误区纠偏与 SQLite 数据库无损清洗 SOP。
version: 2.0.0
created: 2026-10-20
updated: 2026-10-20
---

# ide_fix_078_Zed信任表家目录污染致全盘监听与Defender死锁

> **条目定位**：**【顶级高危事故】Type A 终极排障与架构机理深度复盘条目**  
> **危险评级**：★★★★★（单体吞噬 11.5GB 提交内存，拉爆 Windows Defender 占用 64% CPU，造成磁盘满载与整机假死）  
> **验证环境**：Zed 1.24.3 (Windows x64)、Windows 11 (Defender)、Claude ACP / OpenMA-Pi ACP / Antigravity ACP。  
> **关联条目**：会话提取与 SQLite 抢救见 `025_ide_zed_fix_Zed会话丢失提取与SQLite解析抢救.md`；ACP 进程池累积与内存治理见 `023_ide_zed_fix_Zed与IDEA外接ACP代理失效与进程堆积.md`。

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
```

---

## 四、确定性排查与数据库无损清洗 SOP

清洗目标：**将潜伏在数据库里、被错误提升为受信任项目的父级根目录从 `trusted_worktrees` 表中彻底剔除**。

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
