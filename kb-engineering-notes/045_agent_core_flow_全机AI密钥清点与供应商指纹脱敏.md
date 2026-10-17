---
name: kb-secret-inventory-scan
description: 知识库：在单机范围内清点某厂商 API Key 与模型供应商配置的全流程流水线——rg 粗筛 + Python 密钥指纹分组脱敏 + SQLite 只读核查，识别「表面已清空、key 却藏在迁移槽/应用数据库/历史会话」的残留。当需要确认「某个 key 是否只配在指定工具里」、做密钥收敛或泄露面盘点时查阅。
---

# 全机 AI 密钥与模型供应商配置清点排查指南

> **实测环境**：Windows 11 + Git Bash + Agent 终端（`bash` 工具 + `rg` 15.x + `uv`/系统 Python + sqlite3 标准库）。
> **真实案例**：把 DeepSeek 官方 key 收敛到「只保留在 DeepSeek Harness（DSH）」，对全机 agent/应用/项目做一次彻底清点。最终在 7 类位置查出 **7 把不同的官方 key**，其中 3 把是"人以为已经清掉了"的隐藏残留。

---

## 一、业务场景与清点需求

### 1.1 输入、目标与交付

| 项 | 内容 |
|:---|:---|
| 输入 | 一句约束：「某厂商的官方 key，我只想留在 X 工具里，其他一律不要」 |
| 可用能力 | 只有终端（`rg` / Python / `reg query`），没有密钥管理系统、没有集中配置中心 |
| 目标产出 | **分类清单**：活配置 / 备份文件 / 项目 `.env` / 历史会话 / 误报，逐条给出位置 + 脱敏指纹 + 处置建议 |
| 交付格式 | 表格（位置 / key 指纹 / 生效方式）+ 勾选式清理清单，**全程不回显明文 key** |

### 1.2 为什么这件事不能靠"翻几个配置文件"完成

AI 工具的 key 分布在一个极不均匀的空间里，只查"我知道的那几个配置文件"必然漏：

```text
活配置层：~/.dsh/.credentials.yaml、~/.hanako/*.yaml、%APPDATA%/<app>/settings.json
数据库层：cc-switch.db(providers) / cherrystudio.sqlite(user_provider.api_keys) / Cursor conversation-search.db
项目层  ：D:\...\*.env（含 dist 打包产物、archived 备份）
备份层  ：opencode.json.bak-*、cc-switch/backups/*.json、auth.json.bak-*
历史层  ：.pi/agent/sessions/*.jsonl、.claude/projects/**、.codex/sessions/**、antigravity brain/**、*.db 会话库
环境变量：HKCU/HKLM Environment（配置清了、变量还在激活，等于没清）
```

**关键判据不是"文件里有没有出现厂商名"，而是"这把 key 到底被谁读"** —— 于是必须引入 **密钥指纹** 维度（见 2.3）。

---

## 二、技术核心难点与底层剖析

### 2.1 无界 `os.walk` + 无上限 `read()` = 扫描进程直接跑飞

第一版脚本（纯 `os.walk` 全盘 + 关键字匹配）的实际结局：

```text
现象：Agent 侧命令超时中止，但进程并未退出 —— python.exe PID 41948 仍在跑；
      输出文件 0 字节（因为脚本是"扫完再打印"），看起来像死锁；
根因：① 遍历 AppData\Local（浏览器/Electron 缓存动辄十万级文件）时 skip 名单太窄；
      ② DB 分支没有 size cap，直接 open(p,'rb').read() 撞上 GB 级 .sqlite；
      ③ 结果只在结尾统一 print，中间无进度、无 flush。
```

**纠正后的三条硬规则**：

1. **先判大小再读**：`os.path.getsize(p) > CAP` 直接跳过（文本 4MB / DB 30MB 是够用的阈值）；
2. **不自己造轮子遍历**：用 `rg --max-filesize 1M -g '!缓存目录/**'` 拿"候选文件清单"，Python 只做精筛 —— rg 的文件遍历与并行能力远强于手写 walk；
3. **Agent 超时 ≠ 进程结束**：命令被中止后必须核实并清理孤儿进程，否则它会继续吃 IO：

```bash
tasklist //FI "IMAGENAME eq python.exe"
taskkill //PID <PID> //F
```

### 2.2 控制台编码：Python 在 Windows 上默认 GBK，打印到一半直接崩

```text
UnicodeEncodeError: 'gbk' codec can't encode character '\u2283' in position 12
```

中文报告 + 特殊符号（`⊃`、`≥`、emoji）必然触发。**两种正确姿势**：

- 环境变量法：`PYTHONIOENCODING=utf-8 python scan.py`（终端仍可能乱码，但不再崩）；
- **推荐**：脚本把报告写进 UTF-8 文件（`open(..., "w", encoding="utf-8")`），再用 Agent 的文件读取工具查看 —— 中文完全正常，也避免把大段原始输出灌进模型上下文（Token 经济）。

### 2.3 核心洞察：用「密钥指纹分组」把噪音收敛成结论

只按厂商名（`deepseek`）匹配，一台普通开发机会命中 **700+ 文件**：技能库文档、第三方插件说明、vendored 包（litellm/transformers/onnxruntime）、词典 JS —— 全是噪音。

**改为密钥维度收口**：

```python
KEY_RE = re.compile(r"sk-[A-Za-z0-9_\-]{16,}")     # 厂商 key 形态（按需替换前缀）
h = hashlib.sha256(key.encode()).hexdigest()[:6]   # 指纹：同 key 跨文件自动归并
```

好处有三：

- 同一把 key 散落在 16 个文件里，会自动归并成**一条记录 + 位置清单**（本例 `sk-6f6a…` 出现在 16 处，其中 10 处是备份）；
- 报告只出现 `sk-6f6a…8aea` 这类掩码，**不会把明文 key 二次写进会话记录**；
- 指纹分组天然给出"这把 key 影响面多大"，直接支撑"是否需要轮换"的判断。

### 2.4 假阳性与"假空"：两类必须分开处理

| 类型 | 实例 | 处理 |
|:---|:---|:---|
| 假阳性 | `sk-your-key`、`sk-no-key-required` 占位符；`sk-is_u…late`（压缩 JS 里的巧合串）；statsig 缓存 | 白名单排除 |
| **假空（真残留）** | 字段看着是空的，key 在别处：<br>· Everywhere：`ApiKey` 已是占位 GUID `00000000-…`，真 key 在 `LegacyApiKeys` 里<br>· CherryStudio：key 在 sqlite `user_provider.api_keys` JSON 里，配置文件里根本看不到<br>· 历史会话：key 只是被当时对话写进了 `.jsonl` / `*.db` | 必须靠"指纹维度 + 数据库层 + 历史层"三轮才查得出来 |

### 2.5 已卸载应用 ≠ 无残留：`%APPDATA%` 数据目录会留下来

Everywhere 案例的完整取证链（值得作为范式）：

```text
① 找安装：Program Files / AppData\Local\Programs / 开始菜单 / 注册表 Uninstall / winget list → 全部查无
② 查数据：%APPDATA%\Everywhere\ 仍在（settings.json + db\chat.db + logs\）
③ 读日志：logs\20251127.jsonl 有 POST https://api.deepseek.com/chat/completions → 确实用过官方 key
④ 看迁移：logs\20260222.jsonl 连续 Applying migration 0.5.6 → 0.5.9 → 0.6.6
          → 迁移把 Model.CustomAssistants[0].ApiKey 搬进 LegacyApiKeys，新字段写成占位 GUID
结论：应用已卸载、进程未运行 → 该 key 不会再生效，属"卸载后的磁盘残留"，风险等级低于活配置
```

**判据**：先定"是否仍在生效"（进程 / 安装 / 最近日志），再决定清理优先级 —— 残留 ≠ 泄露中。

### 2.6 SQLite 必须只读打开（活库会被写坏 / 被应用回写）

```python
con = sqlite3.connect(f"file:{dbp}?mode=ro&immutable=1", uri=True)   # 只读 + 不落锁
tabs = [r[0] for r in cur.execute("select name from sqlite_master where type='table'")]
for t in tabs:
    cols = [r[1] for r in cur.execute(f'pragma table_info("{t}")')]
    for row in cur.execute(f'select * from "{t}"'):
        ...  # 命中含厂商名/key 的行，逐列脱敏输出
```

- `mode=ro`：绝不写库；`immutable=1`：避开应用正在写入时的锁争用（参照本库 `029_agent_ccswitch_flow_cc-switch直接读写SQLite模型迁移.md`）；
- 表名/列名先 `sqlite_master` + `pragma table_info` 探测，**不要猜 schema**；
- 命中后要区分"配置行"（`user_provider.api_keys`）与"日志行"（`ai_usage_record`、`proxy_request_logs`）——后者是统计噪音。

---

## 三、标准自动化清点流水线（三段式）

### 3.1 总览

```text
① rg 粗筛  →  候选文件清单（隐藏文件 + 大小上限 + 排除缓存目录）
② Python 精筛  →  提取 key → sha256 指纹分组 → 按路径分类打标 → 脱敏写入 UTF-8 报告
③ SQLite 只读核查  →  providers / user_provider 等配置表逐表扫厂商名
④ 环境变量核查  →  HKCU/HKLM Environment + 当前会话 env
```

### 3.2 ① rg 粗筛（先拿清单，不打印正文）

```bash
rg -i -l --hidden --no-messages --max-filesize 1M \
  -g '!.cache/**' -g '!AppData/Local/Temp/**' \
  -g '!**/node_modules/**' -g '!**/.git/**' -g '!**/Cache/**' -g '!**/Code Cache/**' \
  -g '!**/GPUCache/**' -g '!**/IndexedDB/**' -g '!**/blob_storage/**' -g '!**/logs/**' \
  -g '!**/*.log' -g '!**/*.db*' \
  deepseek . > /tmp/ds-home.txt          # 输出到文件，别直接灌上下文

# 其他盘：项目/工具目录同样跑一遍
rg -i -l --hidden --no-messages --max-filesize 1M \
  -g '*.env' -g '.env*' -g '*.json' -g '*.toml' -g '*.yaml' -g '*.yml' -g '*.py' \
  -g '!**/node_modules/**' -g '!**/.venv/**' -g '!**/site-packages/**' \
  deepseek D:/Users D:/Programmer D:/tmp > /tmp/ds-d.txt
```

### 3.3 ② Python 精筛：指纹分组 + 分类 + 脱敏

```python
import os, re, hashlib, collections
KEY_RE = re.compile(r"sk-[A-Za-z0-9_\-]{16,}")
PLACEHOLDER = {"sk-your-key", "sk-no-key-required"}

def mask(s):
    return KEY_RE.sub(lambda m: m.group(1)[:7] + "…" + m.group(1)[-4:], str(s))[:200]

def category(rel):                      # 分类决定处置优先级
    if re.search(r"(/sessions?/|/projects/|/brain/|/logs?/|telemetry|\.jsonl$|/archived_sessions/|conversations?/)", rel, re.I):
        return "历史/会话/缓存"
    if re.search(r"(/backups?/|\.bak|bak-)", rel, re.I):
        return "备份文件"
    if re.search(r"(\.env$|\.env\.)", rel, re.I):
        return "项目 .env"
    return "活配置"                      # 兜底：Agent/应用配置

groups = collections.defaultdict(list)
for f in candidates:
    if os.path.getsize(f) > 4 * 1024 * 1024:      # 硬规则：先判大小
        continue
    t = open(f, "rb").read().decode("utf-8", "ignore")
    for k in set(KEY_RE.findall(t)) - PLACEHOLDER:
        groups[hashlib.sha256(k.encode()).hexdigest()[:6]].append((category(rel(f)), rel(f), k))

with open("report.txt", "w", encoding="utf-8") as out:   # UTF-8 落盘，规避 GBK 崩溃
    for h, items in sorted(groups.items(), key=lambda x: -len(x[1])):
        print(f"--- key {mask(items[0][2])} 出现于 {len(items)} 处", file=out)
        for c, p, _ in items:
            print(f"    [{c}] {p}", file=out)
```

### 3.4 ④ 环境变量核查（最容易被忽略的一层）

```powershell
reg query "HKCU\Environment" /reg:64 | Select-String -Pattern "DEEPSEEK|API_KEY"
reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" | Select-String -Pattern "DEEPSEEK"
```

```bash
env | grep -i deepseek        # 当前会话（Git Bash 可见 Windows 环境变量）
```

> 配置清了但环境变量还在 → 工具照样能调通，属于"清了个寂寞"。

### 3.5 处置必须分层（不要一刀切删除）

| 层 | 处置 | 理由 |
|:---|:---|:---|
| 本次操作产生的备份 | 直接删（如刚生成的 `auth.json.bak-*`） | 无历史价值，只承载刚摘掉的 key |
| 历史备份 / 计划文档 | 擦除或删除，需确认 | 属于用户资产，**删前必核**（`git status` / `git log` 核实身世） |
| 第三方应用配置（Chatbox/Everywhere/…） | **先关应用再改**，否则被回写覆盖 | 活进程持有内存配置，落盘会盖掉你的修改 |
| 应用 SQLite 配置 | 优先在应用 UI 内删；脚本改库需关应用 | 见 2.6 |
| 项目 `.env` | 单独确认（删了项目就调不通） | 属于业务可用性取舍 |
| 历史会话 / 缓存 | 可选擦除；更彻底的做法是**轮换 key** | 痕迹清理≠消除泄露面 |

---

## 四、交付验证与工程扩展建议

### 4.1 验证闭环（改完必须回读）

```bash
opencode auth list                 # 凭据是否只剩目标项
opencode models | grep -i <厂商>   # 模型列表是否已摘除（注意中继通道会保留同名模型）
```

- 配置层：JSON 解析校验（`json.load`）+ 关键字段回读（`disabled_providers` / `provider` 键集合）；
- 数据库层：重新只读查询一次，确认配置行已消失；
- 语义层：明确区分 **官方直连 key** 与 **中继通道（如 opencode-go）** —— 后者同名模型保留属正常，别误报。

### 4.2 工程扩展

- **换厂商**：只改 `KEY_RE` 前缀与粗筛关键词，流水线不动；
- **换机器**：把三段式封装成单文件脚本（`uv run`），新机一键复现；
- **跨层收口**：把"备份层 + 历史层"也纳入常规巡检，可提前发现 key 扩散；
- **轮换优先**：一旦 key 已进入 `.jsonl` 会话记录 / 云端同步目录，清配置只是止损，**真正止血是去平台吊销并轮换**，只保留目标工具那一把。

### 4.3 红线复述

1. **写前必读、删前必核**：任何疑似"多余"的文件，先 `git status` / `git log` 核身世，已入库文件绝不擅自清理；
2. **只读打开数据库**，绝不为了让扫描"跑通"去改活库；
3. **全程脱敏**：报告、日志、会话里只出现掩码与指纹，明文 key 不落第二份；
4. **先分类后处置**：先回答"这处是否仍在生效"，再谈删不删。

---

## 附：与相邻条目的关系

- `029_agent_ccswitch_flow_cc-switch直接读写SQLite模型迁移.md` —— 数据库层读写规范与锁规避；
- `021_agent_opencode_fix_opencode连接GLM鉴权401与端点排障.md` —— key 优先级与端点映射；
- `043_agent_opencode_fix_OpenCodeGo模型提速与关闭思考reasoningEffort.md` —— 官方直连与中继通道的区别；
- `042_agent_core_fix_多Agent全局规则生效与CLI管道防挂起.md` —— 多 Agent 配置生效性验证方法论。
