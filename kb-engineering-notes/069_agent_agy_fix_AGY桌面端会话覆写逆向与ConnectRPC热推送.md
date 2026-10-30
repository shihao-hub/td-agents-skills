---
name: kb-antigravity-app-session-rpc
description: 针对 Google Antigravity 桌面端应用（Antigravity App）离线修改 SQLite / Protobuf 会话标题被常驻 language_server.exe 内存缓存定时覆盖回滚、raw_summary Protobuf BLOB 字段反序列化优先级以及官方 ConnectRPC (UpdateConversationAnnotations) 动态端口探测与 CSRF 鉴权实时热推送的逆向排障与实战指南。
version: 1.0.0
created: 2026-10-17
updated: 2026-10-30
id: "069"
domain: agent
scope: agy
type: fix
slug: "AGY桌面端会话覆写逆向与ConnectRPC热推送"
status: verified
last_verified: "2026-10-20"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: true
---

# 69-Antigravity 桌面端会话持久化覆写机制逆向与官方 ConnectRPC 热推送实战指南

> **核心摘要**：  
> 在对 Google Antigravity 桌面客户端（Antigravity Desktop App）进行会话标题批量治理与汉化时，若仅在磁盘层离线修改 SQLite 数据库或 Protobuf 序列化文件，会遭遇“修改后界面依然显示旧英文”、“过几分钟或重启后数据库被强制覆盖回滚”的诡异现象。  
> 本手记记录了针对 Antigravity 核心服务 `language_server.exe` 的深度逆向过程，揭示其**内存缓存常驻 + 定时后台对齐刷盘（Background Reconciliation）**机制、`raw_summary` Protobuf BLOB 优先反序列化机制，并给出通过**官方 ConnectRPC 协议动态探测端口与 CSRF Token 进行实时热推送**的标准解决方案。

---

## 一、现象与报错直击

### 1. 现象直击：数据库离线修改被“幽灵覆写”
在尝试对 Antigravity 桌面端会话数据库（`~/.gemini/antigravity/conversation_summaries.db`）执行 SQL 批量更新后：
```sql
UPDATE conversation_summaries SET title = '中文新标题' WHERE conversation_id = 'b4adfb22-...';
```
在 SQLite 查看确实已变成了中文。但在打开或运行中的 Antigravity 桌面端中：
1. **界面完全无动于衷**：左侧 Projects 栏中的会话名称依然顽固地显示为英文原名（如 `Cursor Update Access...`）；
2. **过几分钟后数据库被反向覆盖**：重新查询 SQLite，原本已被改写为中文的 `title` 字段，竟然被悄悄重置回了旧的英文原名！
3. **语言服务器日志暴露线索**：在语言服务器的日志输出中，周期性地出现以下诊断文本：
   ```text
   summary store: starting background reconciliation
   ```

### 2. 现象直击：用户视觉端“看着没有汉化”
即使离线时关闭应用修改了 `conversation_summaries.db`，重新打开应用后，由于 Antigravity 前端是基于 Electron/Webview 的单页应用（SPA），侧边栏渲染完成后 DOM 树保持静态，不会由于底层数据库的文件变更而自动重绘，用户直观感受依然是“没有汉化”。

---

## 二、底层根因剖析

### 1. 多环境数据源目录隔离
与命令行工具 `agy` CLI 不同，Antigravity 生态在本地存在严格的多环境隔离：
- **`agy` CLI 目录**：`~/.gemini/antigravity-cli/`
  - 使用标准的 `conversation_summaries.db` 与 `annotations/<id>.pbtxt`；
- **Antigravity Desktop App 目录**：`~/.gemini/antigravity/`
  - 拥有独立的 `conversation_summaries.db`、`agyhub_summaries_proto.pb` 以及 `annotations/`；
  - 若脚本仅更新了 CLI 目录，桌面端应用完全感知不到。

### 2. `raw_summary` Protobuf BLOB 优先级压制文本列
通过反编译 `language_server.exe` 中的数据读取逻辑（定位到 `jetbox_summaries_store.RecordToSummary` 函数）：
```go
// 伪代码还原语言服务器反序列化逻辑
func (s *SummaryStore) RecordToSummary(record *DbRecord) *CascadeTrajectorySummary {
    if len(record.RawSummary) > 0 {
        var summary CascadeTrajectorySummary
        if err := proto.Unmarshal(record.RawSummary, &summary); err == nil {
            return &summary // 优先直接返回反序列化后的 Protobuf 对象！
        }
    }
    // 仅当 RawSummary 为空时，才回退构造基于 title 文本列的对象
    return &CascadeTrajectorySummary{ Title: record.Title }
}
```
- `conversation_summaries.db` 表中存在名为 `raw_summary` 的 `BLOB` 字段，存储的是 `CascadeTrajectorySummary` Protobuf 二进制流；
- 该二进制流中，`Field 1` 代表根级 `title`，`Field 15` 代表嵌套子消息 `annotations.title`；
- **致命机制**：桌面端加载会话时，**优先从 `raw_summary` BLOB 反序列化标题**！若仅通过 SQL 改写了 `title` 文本列，而未更新 `raw_summary` 二进制中的 Field 1/15，桌面端依然会把反序列化出来的旧英文标题作为主标题展示！

### 3. 常驻进程 `language_server.exe` 内存缓存与定时对齐覆写（核心根因）
- Antigravity 启动后，会在后台拉起一个由 Go 编写的常驻语言服务器进程：
  ```powershell
  Get-Process language_server
  # 路径: C:\Users\<User>\AppData\Local\Programs\antigravity\resources\bin\language_server.exe
  ```
- 该进程在启动初期执行 `GetAllCascadeTrajectories`，将全量会话摘要读入内存维护字典；
- 该进程启动了一个后台 Goroutine 定时器，定时执行 `summary store: starting background reconciliation`；
- **覆写逻辑**：定时器对齐时，以**内存中的状态为真理源**，强行把内存中的会话数据重新序列化并写回 SQLite 数据库与 `.pb` 快照！
- 这就解释了为什么离线写 SQLite 会被“幽灵覆写”：外部修改只写了磁盘，而没有通知内存；语言服务器一旦触发后台对齐，就用旧内存把磁盘上的修改全盘覆盖！

### 4. 官方 ConnectRPC 协议机制突破
为了能在不重启、不杀进程、不丢失正在进行的会话状态下让修改永久生效，必须直接穿透到 `language_server.exe` 的内存层。
逆向扫描二进制提取出所有 ConnectRPC（基于 HTTP POST 的 gRPC-Web 规范）端点，共发现 343 个 RPC 方法，其中关键服务为：
`exa.language_server_pb.LanguageServerService`

通过逆向分析确定了会话注释更新的官方端点：
- **RPC 端点**：`/exa.language_server_pb.LanguageServerService/UpdateConversationAnnotations`
- **动态寻址**：
  - 端口非固定，启动时由操作系统分配随机高位端口（如 14068 等）；
  - `language_server.exe` 只监听 `127.0.0.1`；
- **安全鉴权（CSRF Defense）**：
  - 启动命令中包含参数 `--csrf_token <UUID>`（如 `--csrf_token 58ba079d-15a7-41b7-af24-b4f02203973b`）；
  - 所有的 HTTP POST 请求必须附带 Header：
    `x-codeium-csrf-token: <csrf_token>`
    `Content-Type: application/json`
- **Payload 数据结构**：
  ```json
  {
    "cascadeIds": ["b4adfb22-556c-4291-812e-ffd0a173be20"],
    "annotations": {
      "title": "Cursor 更新权限拒绝排障"
    },
    "mergeAnnotations": true
  }
  ```
- **调用效果**：调用该接口成功返回 `200 OK` 后，语言服务器会：
  1. 立即更新内存字典中该会话的 `summary` 与 `annotations.title`；
  2. 向长连接流 `StreamCascadeSummariesReactiveUpdates` 推送增量更新包；
  3. 主动将新标题同步序列化并刷新写入 SQLite 与磁盘，**使内存与磁盘达成官方一致**。

---

## 三、标准抢救与修复 SOP

### Step 1: 动态探测运行中的语言服务器并提取凭证
编写原子探测脚本（或调用封装好的 CLI），通过 WMI 提取常驻进程信息并定位 HTTP 端口：

```powershell
# 1. 获取 language_server.exe 的 PID 与命令行
$proc = Get-CimInstance Win32_Process -Filter "Name='language_server.exe'" | Select-Object -First 1 ProcessId, CommandLine
if (-not $proc) {
    Write-Host "未发现运行中的 language_server.exe，将回退为纯离线多源原子双写"
}

# 2. 从命令行提取 CSRF Token
$token = [regex]::Match($proc.CommandLine, '--csrf_token\s+([a-zA-Z0-9\-]+)').Groups[1].Value

# 3. 枚举该 PID 监听的所有端口并测试 HTTP 存活
$ports = Get-NetTCPConnection -OwningProcess $proc.ProcessId -State Listen | Select-Object -ExpandProperty LocalPort
```

### Step 2: 通过 ConnectRPC 实时热推送会话标题
使用 Python 发起标准 HTTP POST 请求（兼容 Windows 原生环境，零第三方依赖）：

```python
import json
import urllib.request

def live_push_title(http_port: int, csrf_token: str, conv_id: str, new_title: str) -> bool:
    url = f"http://127.0.0.1:{http_port}/exa.language_server_pb.LanguageServerService/UpdateConversationAnnotations"
    payload = json.dumps({
        "cascadeIds": [conv_id],
        "annotations": {"title": new_title},
        "mergeAnnotations": True
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-codeium-csrf-token": csrf_token,
            "User-Agent": "antigravity"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"RPC 调用失败: {e}")
        return False
```

### Step 3: 四重一致性原子双写兜底（离线与持久化双重保障）
为保证在应用关闭、冷启动或重启后依然完全持久化，必须配套完成四重双写：
1. **自动前置快照**：在 `~/.gemini/antigravity/backups/titles/` 下创建时间戳快照目录，备份 `conversation_summaries.db`、`agyhub_summaries_proto.pb` 与 `annotations/*.pbtxt`；
2. **更新 SQLite `title` 列**：标准 SQL 更新文本索引；
3. **Protobuf Wire 编解码更新 `raw_summary` BLOB**：
   - 提取 `raw_summary` 字节流；
   - 遍历 Protobuf 键值对，将 `Field 1`（根级 `title`）与 `Field 15`（嵌套 `annotations.title`）的字节值重打包；
   - 写回 SQLite `raw_summary` 字段；
4. **更新 `annotations/<id>.pbtxt`**：写入标准 Protocol Buffer 文本格式：
   ```protobuf
   title:"中文新标题"
   ```

### Step 4: 桌面端界面一键刷新（前端 DOM 重绘）
由于 Antigravity Desktop App 前端不会自动重构整个侧边栏 DOM 树，在 RPC 推送成功后：
- 在 Antigravity 界面按下快捷键：**`Ctrl + R`**（或按 `F1` 输入 `Developer: Reload Window`）；
- 前端重新向 `language_server.exe` 发起 `GetAllCascadeTrajectories` 请求；
- 侧边栏所有工作区和会话树将立即以最新中文标题重新渲染展示！

---

## 四、验证与防复发闭环

### 1. 验证命令：RPC 级别全量状态核查
运行以下 Python 单文件脚本，验证语言服务器内存中的所有会话状态：

```python
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
import json, re, subprocess, urllib.request

# 自动获取端口与 token 并调用 GetAllCascadeTrajectories
# 检验返回的 trajectorySummaries 字典中每个会话的 summary 与 annotations.title
```
**判定标准**：
- `Total summaries` 统计总数中，`已汉化条数` 达到 100%，`未汉化条数` 为 0；
- 验证用户关注的重点会话标题是否为标准中文。

### 2. 工具链沉淀
本实战结论已完整固化至自动化运维工具体系中：
- 核心脚本：[`sh-user-skills/sh-agy-session-governance/scripts/agy_titles.py`](file:///d:/Users/language_projects/.agents/skills/sh-user-skills/sh-agy-session-governance/scripts/agy_titles.py)
- 单文件 exe：[`sh-user-skills/sh-agy-session-governance/dist/agy_titles.exe`](file:///d:/Users/language_projects/.agents/skills/sh-user-skills/sh-agy-session-governance/dist/agy_titles.exe)
- 参数支持：`agy_titles.exe batch-rename --target app --file <payload.json>`

### 3. 架构防复发避坑经验
1. **警惕“常驻守护进程 + 内存主本”架构**：
   现代 AI 辅助 IDE（如 VS Code、Cursor、Antigravity、Windsurf）普遍采用“前端 UI + 后台 Language Server”的双进程解耦架构。核心数据往往由后台长驻服务持有内存缓存并单向刷盘。
2. **切忌外部裸改 SQLite**：
   凡遇到后台有长常驻进程对同一文件进行管理的场景，外部离线写文件极易被其后台定时 reconciliation 线程冲掉。最佳实践永远是：**探测 RPC 接口 -> 动态提取鉴权凭证 -> 经由官方通道热推送 -> 辅以底层多源落盘兜底**。

---

## 五、进阶避坑与迭代沉淀（v1.2.0 实战增补）

### 1. “中文分类标签 + 英文主体”的伪中文识别盲区
- **现象**：部分会话标题以业务标签开头（如 `【知识】Douyin Video Summary And Insights` 或 `【待办】Vibe Coding Skill Recommendations`）。
- **根因**：基础中文正则 `re.search(r"[\u4e00-\u9fa5]", title)` 只要匹配到全串任意一个汉字（如“知”、“识”）就会返回 `True`，导致这批“带中文前缀但主体全是英文”的混血标题被彻底漏检。
- **解法**：在判定前通过正则 `TAG_PATTERN = re.compile(r"^[\[【](.*?)[\]】]\s*")` 先行剔除方括号标签，基于主体内容的汉字数与多字符英文单词占比进行严格研判，彻底杜绝伪中文。

### 2. SQLite WAL 事务截断检查点（`PRAGMA wal_checkpoint(TRUNCATE)`）
- **现象**：离线更新了 `conversation_summaries.db` 后，短时间内正常，但语言服务器触发后台内存对齐或重启时，数据库再度被旧数据冲掉。
- **根因**：SQLite 处于 WAL 模式时，更新数据仅追加在 `-wal` 文件中，尚未合并到主数据库文件。当 `language_server.exe` 触发后台 reconciliation 时，易因内存版本较新直接把旧主本覆写主库并截断 WAL，导致离线修改静默丢失。
- **解法**：在所有单条或批量 SQLite UPDATE 事务提交后，显式执行 `PRAGMA wal_checkpoint(TRUNCATE);`，强制将 WAL 日志完整合并并空出主库，确保落盘数据具备最高权威。

