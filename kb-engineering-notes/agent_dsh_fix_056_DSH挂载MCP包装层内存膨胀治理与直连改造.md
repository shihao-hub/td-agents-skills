---
name: kb-dsh-mcp-npx-uvx-wrapper-memory
description: DSH 通过 profile 补丁挂载 stdio MCP 时，npx/uvx 启动包装层带来的进程数与常驻内存膨胀（npx 一层即 cmd+npx-cli+cmd 三进程且因持有子进程 stdio 全程常驻），含 profile patch 的 config 浅替换语义与直连入口改造。当客户端进程树冒出一堆 cmd/node 吃内存、或改了 MCP 配置不确定是否生效时查阅。
version: 1.0.0
created: 2026-10-13
updated: 2026-10-13
---

# DSH 挂载 MCP 服务 npx 与 uvx 启动包装层进程内存膨胀治理与直连入口改造指南

> **适用场景**：Agent 客户端（DeepSeek Harness 等）进程树里，每挂一个 MCP 服务就多出 `cmd.exe → node.exe → cmd.exe → node.exe → conhost.exe` 一长串进程；任务管理器 / Process Explorer 里「启动没多久内存就上一个 G」，单个 MCP 链路子树能占 300 MB+；想改 MCP 启动命令却发现"改了没效果"或"改完字段丢了"。

---

## 一、现象与报错直击

### 1. 现场一：进程树里 MCP 一条链路 6 个进程、327 MB

在 Process Explorer 里按子树看，某个 `cmd.exe (2)` 节点的子树合计 **327 MB**，展开是：

```text
DSH 宿主进程
└─ cmd.exe          (npx.cmd 批处理)          9.1 MB
   └─ node.exe      (npx-cli.js 解析/校验包)  108.7 MB   ← 比服务本体还贵
      └─ cmd.exe    (包自己的 bin .cmd shim)   9.3 MB
         └─ node.exe (MCP 服务本体)           124.1 MB
            └─ node.exe (telemetry watchdog)  63.5 MB
   conhost.exe                                12.6 MB
```

### 2. 现场二：内存比"以前刚启动"多出几百 MB

同一台机器、同一客户端版本，实测（工作集 / 私有）：

| 归属 | 进程数 | 工作集 | 说明 |
| :-- | :-- | :-- | :-- |
| 客户端应用本体（Electron 6 进程） | 6 | 1,439 MB | 正常 |
| `chrome-devtools` MCP（npx） | 6 | **327 MB** | 仅 2 个是"干活"的 |
| `argo` MCP（npx） | 6 | **227 MB** | 服务本体才 64 MB |
| `everything` MCP（uvx） | 6 | **154 MB** | |
| `aoci` MCP（本机 exe） | 2 | 50 MB | 直连形态，正常 |
| 插件辅助进程 | 2 | 113 MB | |
| **合计** | **30** | **2,358 MB**（私有 1,742 MB） | 系统 23.8 GB 仅剩 1,654 MB 空闲 |

### 3. 现场三：改了 MCP 启动命令，字段被悄悄抹掉

把 profile 补丁里的命令从 `npx` 改成直连 `node`，只写了 `command` 和 `args`，以为只是"换条命令"；结果合成后的条目**丢了 `serverName` 与 `transport`**，服务名对不上、挂载异常。

---

## 二、底层根因剖析

### 1. npx / uvx 在 Windows 上不是"一个进程"，而是一条链

**npx** 本身只是 `npx.cmd` 批处理，必须由 `cmd.exe` 解释；真正的逻辑在 `node npx-cli.js`（做版本解析、缓存查找、必要时下载）；解析完再 spawn 包自己的 `bin`——而包的 bin 在 Windows 上又是 `.cmd` shim，于是**再来一个 cmd.exe**，最后才轮到 node 跑真正的 JS。

```text
一层 npx  = cmd.exe + node.exe(npx-cli) + cmd.exe    ← 3 个进程
一层 uvx  = uvx.exe + uv.exe                          ← 2 个进程（+ 工具 shim + python）
```

### 2. 关键：包装进程不是"启动完就退"，而是**全程常驻**

`npx`/`uvx` 会一直持有子进程的 stdio 并等它结束。只要 MCP 服务常驻，这层包装就跟着常驻，**全程占着内存**——这才是真问题，不只是"启动慢"。所以"少 8 个进程"不是少了 8 次瞬时开销，而是少了 8 个**终身住户**。

### 3. 最贵的往往不是服务本体

`npx-cli` 那个 node 进程约 **108 MB**；对比之下 argo 服务本体才 64 MB。也就是说"为了解析一下包"付的代价比"真正干活"还高。

### 4. profile patch 的 `config` 是**整块浅替换**，不是深合并

这是最容易踩的隐式语义：按 `id` 覆盖某个条目时，`config` 整体替换。只写 `command`/`args` 会把 `serverName`、`transport` 一起抹掉，而**覆盖 bundle 自带条目时尤其危险**（包自带的 `cordis.patch.yml` 里往往同时写了这四个字段）。

### 5. 配置变更会热重挂，插件代码变更才需要重启

MCP 条目属于 profile 组合层，改完配置文件后实测**立刻按新命令重挂**（旧包装链路消失、新直连进程出现），无需重启客户端；但插件的宿主半区 JS 只在启动时装载，改插件代码必须重启。

---

## 三、标准抢救与改造 SOP

### 步骤 1：先清点合成后的真实配置

```powershell
dsh --profile <profile> --dump-config
```

注意 `desktop` 这类由 Electron 应用独占管理的 profile 会被 CLI 拒绝：

```text
error: profile "desktop" is managed exclusively by the Electron application
```

**影子 profile 校验法**（离线看合成结果，不碰真身）：

```powershell
$base = "$env:USERPROFILE\.dsh\profiles"
$src  = Join-Path $base 'desktop'; $dst = Join-Path $base 'dsh-memtest'
New-Item -ItemType Directory -Path $dst -Force | Out-Null
foreach ($f in @('cordis.yml','cordis.patch.yml','package.json','pnpm-workspace.yaml')) {
  if (Test-Path (Join-Path $src $f)) { Copy-Item (Join-Path $src $f) (Join-Path $dst $f) }
}
New-Item -ItemType Junction -Path (Join-Path $dst 'node_modules') -Target (Join-Path $src 'node_modules') | Out-Null
dsh --profile dsh-memtest --dump-config
```

dump 结果里会标注层级来源，便于确认"谁覆盖了谁"：

```yaml
# == argo, patched by C:\Users\...\profiles\dsh-memtest\cordis.patch.yml
- id: mcp-argo
  name: '@deepseek-ai/dsh-mcp-client'
  config:
    serverName: argo          # ← 若这里消失，就是覆盖时没写全
    transport: stdio
    command: node
    args:
      - D:\...\node_modules\argo-search\bin\argo.js
```

清理影子 profile 时**必须先拆 Junction 再删目录**：

```powershell
cmd /c rmdir "<影子>\node_modules"   # 只删链接本身，绝不跟随
Remove-Item "<影子>" -Recurse -Force
```

> `Remove-Item -Recurse` 会**跟随** Junction 递归删除，直接删掉真实 profile 的 `node_modules`。删前删后都应核对真实目录条目数一致。

### 步骤 2：三个方向的直连改造

| 原形态 | 改造后 | 前置安装 | 省下 |
| :-- | :-- | :-- | :-- |
| `npx -y <pkg>@latest` | `node <全局>\<pkg>\build\src\bin\<entry>.js` | `npm i -g <pkg>` | ~130 MB（npx-cli + 2×cmd） |
| `npx -y github:<owner>/<repo>` | `node <全局>\<repo-pkg>\bin\<entry>.js` | `npm i -g github:<owner>/<repo>` | ~130 MB |
| `uvx <tool>` | `C:\Users\<u>\.local\bin\<tool>.exe` | `uv tool install <tool>` | ~39 MB（uvx + uv） |

要点：

- **不要指 npx 缓存路径**（`...\npm-cache\_npx\<hash>\node_modules\...`）：hash 目录会被 `npm cache clean` 或重解析清理，写进长期配置迟早挂。优先全局安装。
- **保持版本保真**：`npx -y github:owner/repo` 拉到的可能是 2.9.3，而 profile 内依赖是 2.9.2；改造时用全局安装对齐到**原版本**，不要顺手降级。
- 在配置里写注释记录升级方式（`npm i -g ...` / `uv tool upgrade ...`），免得半年后不知道怎么更新。

### 步骤 3：覆盖 bundle 自带条目必须写全字段

```yaml
# 覆盖 argo 包自带的 mcp-argo：config 是整块浅替换，四个字段一个都不能少
- id: mcp-argo
  config:
    serverName: argo
    transport: stdio
    command: 'D:\nvm4w\nodejs\node.exe'
    args:
      - 'D:\nvm4w\nodejs\node_modules\argo-search\bin\argo.js'
```

### 步骤 4：改造后立刻做协议级握手验证（不要只看进程起没起）

对每个新入口发 MCP `initialize` + `tools/list`，比对工具数量与名字是否与改造前一致：

```js
// 伪代码：stdio NDJSON 帧协议
spawn(cmd, args, { stdio: ['pipe','pipe','pipe'], windowsHide: true })
// → {"jsonrpc":"2.0","id":1,"method":"initialize","params":{...}}
// → {"jsonrpc":"2.0","method":"notifications/initialized"}
// → {"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
```

实测样例：`argo 3 个工具(2.9.3)` / `chrome-devtools 30 个(1.10.1)` / `everything 5 个`——数量与名字与改造前逐一对齐才算"零能力损失"。收尾用 `taskkill /PID <pid> /T /F` 连子孙一起收（python 之类的子进程必须带 `/T`）。

---

## 四、验证与防复发

### 1. 改造前后对比（实测）

| 指标 | 改造前 | 改造后 | 变化 |
| :-- | :-- | :-- | :-- |
| MCP 进程数 | 20 | 12 | **−8** |
| MCP 工作集 | 758 MB | 443 MB | **−315 MB** |
| 客户端进程树进程数 | 30 | 22 | −8 |
| 客户端进程树工作集 | 2,358 MB | 1,871 MB | −487 MB |
| 系统空闲内存 | 1,654 MB | 2,615 MB | +961 MB |

减少的 8 个进程账目对得上：chrome-devtools −3（cmd + npx-cli + cmd）、argo −3、everything −2（uvx + uv）；**conhost 数量不变**（改造前后都是 6，只是宿主换了），所以别把它算进收益。

### 2. 按父链聚合子树的测量方法（比看单个进程准）

```powershell
$all = Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine
$go = @{}; foreach ($p in Get-Process) { $go[[int]$p.Id] = $p }
# 从根进程出发 BFS 收集子孙，再按子树汇总工作集/私有内存
```

Process Explorer 的树列也能直接读：某节点第三列是**子树合计**，用它比逐个进程相加快得多。

### 3. 自伤型坑：按命令行匹配杀进程会**杀掉自己**

```powershell
# 危险：CommandLine 里含关键字的不只是目标，还有"正在执行这条命令的自己"和终端宿主 helper
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*dsh-window-memory-helper.ps1*' }
```

后果是把自己连同宿主一起 `Stop-Process` 掉，表现为执行器报 `Windows Job runner exited with exit code 4294967295`（进程异常退出、后续语句全部没执行）。

修正写法：

```powershell
$me = $PID
$targets = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -eq 'powershell.exe' -and
  $_.CommandLine -like '*-File*dsh-window-memory-helper.ps1*' -and   # 匹配启动形态，不匹配"提到过这个文件"
  $_.ProcessId -ne $me -and
  $_.ParentProcessId -ne $me
}
```

原则：**按"启动形态"匹配（`-File <path>`、可执行路径），并显式排除自身 PID 与父链**；能用绝对路径 + 参数特征就别用裸关键字。

### 4. 防复发

- 新装 MCP 服务时**默认走直连形态**（全局安装 + 绝对路径），除非该服务只以 npx 分发且无全局安装方式；
- 定期用影子 profile dump 一次，确认没有新条目把 `npx`/`uvx` 带回来；
- 记住「MCP 配置热重挂、插件代码要重启」这条区别，能省掉大量"改了没生效？"的误判。

### 5. 相关条目

- `browser_devtools_flow_037_opencode集成chrome-devtools-mcp浏览器控制.md`：chrome-devtools-mcp 在另一套客户端的接入与调试；
- `win_conhost_fix_052_PE控制台委托DefTerm断层与MCP无窗口镜像.md`：MCP 服务自身的无窗口化（PE Subsystem 2 GUI）；
- `win_mem_fix_019_Win内存防死机与Pagefile提交归因优化.md`：内存归因与提交内存分析方法。
