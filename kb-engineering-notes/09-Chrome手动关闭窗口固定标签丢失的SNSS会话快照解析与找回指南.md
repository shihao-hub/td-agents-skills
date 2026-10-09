---
name: kb-chrome-snss-session-recovery
description: Chrome 手动关闭的窗口（含固定标签页）重启后整体丢失的完整找回 SOP：Sessions 目录 SNSS v3 明文快照的帧格式与两套命令字典（Session_* 与 Tabs_*）、独占文件锁与启动轮换的规避、从 TabRestoreService「最近关闭」数据精确提取窗口与固定标签清单。当「继续浏览上次打开的网页」只恢复一个窗口、固定标签丢失、Sessions 文件报 Device or resource busy 时查阅。
---

# Chrome 手动关闭窗口与固定标签丢失：SNSS 会话快照解析与找回指南

## 一、 现象与报错直击

1. **双窗口手动关闭后，重启只回来一个窗口**：
   用户开着两个窗口：A（含一排固定标签）与 B（普通）。先手动关闭 A、再关闭 B，重开 Chrome 后只有 B 被恢复，A 及其固定标签"整体丢失"，看起来像被 Chrome 吞了。
2. **关键数据文件被系统独占拒绝**：
   ```text
   cp: cannot open '...\Google\Chrome\User Data\Default\Sessions\Tabs_13435990886378556' for reading: Device or resource busy
   ```
   对应 Python 侧为 `PermissionError: [Errno 13] Permission denied`。**文件还在，只是 Chrome 没退干净**。
3. **"我已经退出了"是最大误判源**：
   关闭可见窗口 ≠ Chrome 退出。实测残留 17 个 `chrome.exe`（后台驻留/未发现窗口），主进程 `MainWindowTitle` 非空即说明还有窗口没关。
4. **排查期间快照被"吃掉"**：
   反复重启 Chrome 排查的过程中，每启动一次都会轮换并删除旧快照文件，真正的"案发现场"可能被覆盖。

---

## 二、 底层根因剖析

### 1. 会话恢复的真实语义（为什么会"丢"）

- "继续浏览上次打开的网页"（Continue where you left off）只恢复**退出那一刻仍打开**的窗口；
- **用户手动关闭的窗口**会被记入 `TabRestoreService`（即界面上的"最近关闭"列表）：一个整窗条目 = 窗口元数据 + 全部标签 + **每个标签的固定（pinned）状态**；
- 因此固定窗口并不是"损坏丢失"，而是躺在"最近关闭"通道里——按设计如此，完全可找回。

### 2. 数据文件体系（Windows）

- 位置：`%LOCALAPPDATA%\Google\Chrome\User Data\<Profile>\Sessions\`
- 文件三类：`Session_<ts>`（会话主服务）、`Tabs_<ts>`（TabRestoreService = "最近关闭"）、`Apps_<ts>`（应用会话）；
- `<ts>` 是 **Windows epoch（1601-01-01 起）微秒数**（即文件创建时刻），可直接换算成本地时间排序定位案发时间线。

### 3. SNSS 文件格式（version 3 = 明文）

- 文件头 8 字节：ASCII `"SNSS"` + `int32 version`；**version 3 = 明文**（默认）；version 5 = OSCrypt 加密（罕见）；
- 记录帧（明文）：`[u16 size_field][u8 command_id][content(size_field-1 字节)]`，整条记录 = `2 + size_field` 字节；`command_id = 255` 为初始状态标记（内容 0 字节）；
- 帧格式自检示例：`19 00 0e ...` → `size=0x19=25`、`id=0x0e=14`（SetWindowBounds3），内容 24 字节 = 6×int32，可据此确认对齐无误；
- 载荷两类：**定长 C 结构**（如 `{int32, int32}`）与 **Pickle**（首 4 字节 payload_size；字段 4 字节对齐；字符串 = `[u32 长度][字节][补齐到 4 字节]`；string16 为 UTF-16LE 同理）。Pickle 数据起点可用 `payload_size == len-content-偏移` 自校验定位（4 或 8 字节头两种历史布局）。

### 4. 两套命令字典（最容易踩的坑！）

**Session_\*（会话服务）——注意与 Tabs 完全不同**：

| id | 含义 | 载荷布局 |
|----|------|----------|
| 0 | SetTabWindow | `int32 window, int32 tab`（每个标签一条） |
| 6 | UpdateTabNavigation | Pickle：`int32 tab_id, int32 index, string URL, string16 标题…` |
| 12 | **SetPinnedState** | `int32 tab_id, bool pinned`（+3 字节 padding，共 8 字节） |
| 16 / 17 | 标签 / 窗口关闭事件 | `int32 id, int64 close_time(µs)` |
| 20 / 21 | 活动窗口 / 最后活跃时间 | `int32` / `int32 tab + int64 ts` |

**Tabs_\*（TabRestoreService）**：

| id | 含义 | 载荷布局 |
|----|------|----------|
| 4 | SelectedNavigationInTab（开启一个"被关闭标签"） | `int32 id, int32 index, int64 timestamp`（共 16 字节） |
| 5 | **PinnedState** | **1 字节 bool，且仅固定标签才会写**（紧随其标签的 cmd4 之后） |
| 1 | UpdateTabNavigation | 同 Session 的 Pickle 布局 |
| 9 | Window（开启一个"被关闭窗口"） | Pickle：`id, sel, num_tabs, int64 ts, x, y, w, h, show, workspace(str), type` |
| 13 / 15 | 组 / 分屏容器 | 同样带 num_tabs（挂靠逻辑同窗口） |
| 2 | RestoredEntry | 删除一个尚未恢复的条目 |

关键推论：**统计 Tabs 文件的 `cmd5` 条数 = 该快照里固定标签的数量**——不开 Chrome 就能判断"哪个快照含固定标签"；若误用 Session 字典（cmd12）去解 Tabs 文件，会得到"固定=0"的假象。

### 5. 独占锁与轮换删除（现场保护机制）

- 当前正在写的文件以**独占读写**方式打开（`FLAG_WIN_EXCLUSIVE_WRITE | FLAG_WIN_EXCLUSIVE_READ`），其它进程完全打不开——必须确认 **0 个 `chrome.exe`** 后才能读取；
- **轮换**：Chrome 启动时 `FindLastSessionFile`（取最新有效快照）、`DeleteLastSessionFiles`（删除其余）、`MoveCurrentSessionToLastSession`（每次截断生成新文件）——**每次重启都在蚕食案发现场**。

---

## 三、 标准解决与抢救 SOP

### 0. 铁律

**事故后第一动作：不要重启 Chrome、不要清历史；能复制就先复制。**

### 1. 先在 UI 里试"最近关闭"（成本最低，通常一步解决）

- ⋮ → 历史记录 → **最近关闭**：找形如「**N 个标签页**」的整窗条目（N 应与丢失窗口标签数一致）→ 点击整窗恢复；
- 不要连按 `Ctrl+Shift+T`（逐个恢复、易乱且会消耗条目）；
- 固定状态会一并恢复（pinned 标记持久化于条目中）。

### 2. 彻底退出并确认锁已释放

```powershell
Get-Process -Name chrome -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count   # 期望 0
```

- 有残留时：托盘图标 → 右键退出；检查"关闭 Chrome 后继续运行后台应用"设置；`MainWindowTitle` 非空的进程说明还有窗口未关；
- 锁测试（能复制即已释放）：
```powershell
Copy-Item "…\Default\Sessions\Tabs_*" "D:\backup\ChromeSessions\" -Force
```

### 3. 全量备份（所有 Profile）

用脚本把 `Default`、`Profile 1..N` 下 `Sessions\*` 全部复制到独立目录（保留 mtime）——**任何分析之前先做备份**。

### 4. Python 解析与定位（最小骨架）

```python
# PEP 723 单文件；仅标准库
import re, struct
from pathlib import Path

def walk(path):
    data = Path(path).read_bytes()
    assert data[:4] == b"SNSS", "非 SNSS 文件"
    ver = struct.unpack_from("<i", data, 4)[0]
    off, recs = 8, []
    while off + 3 <= len(data):
        size = struct.unpack_from("<H", data, off)[0]
        if size < 1 or off + 2 + size > len(data):
            break
        recs.append((data[off + 2], data[off + 3:off + 2 + size]))
        off += 2 + size
    return ver, recs

URL = re.compile(rb"https?://[\x21-\x7e]{4,300}")

def dump_pinned(tabs_file):
    """重放 Tabs_*：cmd4 开标签、cmd5=固定（仅固定才写）、cmd1=导航；cmd9 重置窗口容器。"""
    ver, recs = walk(tabs_file)
    cur, out = None, []
    def settle():
        if cur and cur["pinned"] and cur["urls"]:
            out.append(dict(cur))
    for cmd, c in recs:
        if cmd in (9, 255):                    # 窗口/标记：结算并重置
            settle(); cur = None
        elif cmd == 4:                         # 开启一个被关闭标签
            settle()
            cur = {"id": struct.unpack_from("<i", c, 0)[0], "pinned": False, "urls": []}
        elif cmd == 5 and cur is not None:     # 仅固定标签会写
            cur["pinned"] = True
        elif cmd == 1 and cur is not None:     # 导航 Pickle：正则直接捞 URL
            cur["urls"] += [m.decode("utf-8", "replace") for m in URL.findall(c)]
    settle()
    return out

for f in Path(r"…\User Data\Default\Sessions").glob("Tabs_*"):
    pinned = dump_pinned(f)
    print(f.name, "固定标签数:", len(pinned))
```

- 窗口挂靠要点：**窗口命令（cmd9）后的 num_tabs 条 cmd4 依序归属该窗口**；组/分屏同理，不能把全部标签都挂到第一个容器；
- 输出窗口条目（标签数/固定数/时间）后，用"标签数 + 固定数 + 关键词"与当事人记忆交叉比对锁定目标窗口；
- 本案例命中锚点：窗口 id=15309472，103 标签（18 固定），固定清单含 千问 / Gemini / 元宝 / opencode / DeepSeek / JSON Schema。

### 5. 恢复手段（按优先级）

1. **UI 整窗恢复**：打开 Chrome →「最近关闭」→ 点「N 个标签页」条目（固定保持）——本案例即此路径成功；
2. 若 UI 列表已被挤出/消耗：用备份文件做**文件级恢复**（构造/掉换快照后让 Chrome 启动加载）；
3. 兜底：导出「标题 + 原始 URL」清单，手动逐个打开并重新固定。

### 6. 历史数据库辅助（无快照时的备选）

- `Default\History`（SQLite，Chrome 运行中也可复制）：`urls / visits` 表提供 URL + 标题 + 访问时间；
- 标签被挂起扩展包裹时，可解码还原真实 URL：
  - `…suspended.html#ttl=标题&…&uri=<URL编码>` → 取 `uri=` 参数并 URL 解码；
  - `https://s.tabxpert.com/#!…&url=<URL编码>` → 取 `url=` 参数并 URL 解码。

---

## 四、 验证与防复发建议

1. **恢复验证**：恢复后核对固定标签数量与位置（最左侧、小图标、无关闭按钮），与解析清单逐一比对；数量、顺序、内容一致即为命中。
2. **挂起页说明**：恢复后很多标签会显示为灰色"挂起"页（The Marvellous Suspender / tabXpert 等扩展的包裹页），点开或刷新即还原原网页——**先不要卸载/禁用这些扩展**，等确认全部回来后再处理。
3. **防复发**：
   - 关键固定页同时加入"启动时 → 打开特定网页"，不依赖会话恢复；
   - 事故现场保护优先：**先备份 `Sessions\` 目录再折腾**，频繁重启是最大的数据杀手；
   - 用会话管理扩展（OneTab / Session Buddy 等）主动整窗存档。
4. **通用踩坑附录**：
   - 从 Git Bash 调 `powershell.exe -Command "…$var…"` 时 `$` 会被 bash 先展开导致命令损坏——把 PS 脚本写成 `.ps1` 文件执行，或改用单引号包裹；
   - 中文输出经 PowerShell 5.1 回显可能乱码，优先"脚本写 UTF-8 报告文件 + 读取文件"，而不是终端回显。
