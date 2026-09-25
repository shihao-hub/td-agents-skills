# 本地 Agent 会话审计与接管核查手册

当交接件未打标、状态存疑，或需要核实某份交接件是否已被某个 Agent 真实接管并消费时，**严禁凭空推断或后验猜测**。
通过本手册提供的各 Agent 本地会话存储位置与检索方法，可直接调取确凿日志证据。

---

## 1. 各 Agent 本地会话存储索引

| Agent / 工具 | 存储类型 | 典型路径 | 检索关键字段 |
|---|---|---|---|
| **Zed Agent Panel** | SQLite (WAL 模式) | `%LOCALAPPDATA%\Zed\db\0-stable\db.sqlite` | 表 `sidebar_threads` 中的 `title`、`agent_id`、`session_id`、`updated_at` |
| **Codex CLI / ACP** | JSONL 流式日志 | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` | 搜索 `sh-agent-handoff` 与交接文件名 |
| **Pi Agent** | JSONL 消息流 | `~/.pi/agent/sessions/--<workspace>--/*.jsonl` | 搜索交接文件名、`sh-agent-handoff` |
| **OpenCode** | JSON / 状态库 | `~/.local/share/opencode` 或 `%APPDATA%\opencode` | 搜索 session JSON 中的交接件路径 |

---

## 2. 查证 SOP 与脚本范例

### 2.1 Zed Agent 数据库排查（最高频入口）
用户在 Zed 界面中通过 Agent 面板输入 `sh-agent-handoff: <路径>` 时，Zed 会将第一句作为 `title` 写入 `sidebar_threads`。

> ⚠️ **安全铁律**：SQLite 处于 WAL 模式且 Zed 可能正在运行，必须**将三件套复制到临时目录后只读查询副本**，切勿直接连接原库：

```python
import os, shutil, sqlite3, tempfile

zed_dir = os.path.expandvars(r'%LOCALAPPDATA%\Zed\db\0-stable')
handoff_name = '20260925-120834-typeai-glm-cli-handoff'

with tempfile.TemporaryDirectory() as td:
    for f in ['db.sqlite', 'db.sqlite-wal', 'db.sqlite-shm']:
        src = os.path.join(zed_dir, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(td, f))
    
    conn = sqlite3.connect(os.path.join(td, 'db.sqlite'))
    cur = conn.cursor()
    cur.execute(
        """SELECT agent_id, title, updated_at, session_id 
           FROM sidebar_threads 
           WHERE title LIKE ? OR session_id LIKE ? 
           ORDER BY updated_at DESC""",
        (f'%{handoff_name}%', f'%{handoff_name}%')
    )
    rows = cur.fetchall()
    for agent_id, title, updated_at, session_id in rows:
        print(f'命中: Agent={agent_id}, 时间={updated_at}, Session={session_id}')
    conn.close()
```

### 2.2 Codex 会话日志排查
Codex 会将所有轮次保存在按日期归档的 JSONL 文件中：

```python
import os, json, glob

sessions_dir = os.path.expanduser('~/.codex/sessions')
handoff_name = '20260925-120834-typeai-glm-cli-handoff'

for jsonl_path in glob.glob(f'{sessions_dir}/**/*.jsonl', recursive=True):
    try:
        with open(jsonl_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if handoff_name in content:
                print(f'Codex 会话命中: {jsonl_path}')
    except Exception:
        pass
```

### 2.3 Pi 会话日志排查
Pi 在 `~/.pi/agent/sessions/` 下按工作区路径编码存放 `.jsonl`：

```python
import os, glob

pi_dir = os.path.expanduser('~/.pi/agent/sessions')
handoff_name = '20260923-194029-agent-handoff-skill'

for jsonl_path in glob.glob(f'{pi_dir}/**/*.jsonl', recursive=True):
    try:
        with open(jsonl_path, 'r', encoding='utf-8', errors='ignore') as f:
            if handoff_name in f.read():
                print(f'Pi 会话命中: {jsonl_path}')
    except Exception:
        pass
```

---

## 3. 证据判定准则

1. **已接管证据**：
   - 某 Agent 接收到 `sh-agent-handoff: <path>` 并输出了对简报的复述、读取或后续命令执行；
   - Zed 的 `sidebar_threads` 中记录了以该交接件为 title 的 thread，且 `updated_at` 晚于生成时间。
2. **生成自测完成证据**：
   - 某 Agent 在开发/测试该技能时自行运行 Eval 生成了交接件并在当前会话闭环校验。
3. **未接管证据**：
   - 全盘日志检索该交接文件名，仅在生成它的原始会话中出现过一次，后续没有任何其他 Agent 会话读取过它。
