---
name: kb-dsh-web-update-pipeline
description: DeepSeek Harness Web UI (dsh web) 三层更新体系全景实战：涵盖全局 CLI 升级、Profile 远程插件依赖更新 (pnpm/lockfile 机制)、本地模组软链体系，及常驻后台服务平滑重启与 Cordis 容器层叠校验；并含 ds-harness-remote ACP 后端默认全开致 agy 幽灵常驻的关闭方案与升级后自检门禁。
id: "099"
domain: "agent"
scope: "dsh"
type: "flow"
slug: "DSHWeb三层更新体系与插件升级及容器校验"
status: "verified"
created: "2026-10-25"
last_verified: "2026-11-03"
superseded_by: null
deprecation_reason: null
compatibility:
  os: ["windows"]
falsification_signals:
  - "若当前环境并非通过 dsh CLI (Node.js) 启动，而是纯 Electron 独立二进制且无 profiles/web，本流水线不适用"
invocation:
  auto_trigger: true
  trigger_keywords: ["dsh web 更新", "dsh 更新", "dsh plugin update", "dsh 升级", "dsh web 重启", "agy 自动启动", "agy 莫名常驻", "ds-harness-remote ACP", "ds-harness-remote 拉起 agy", "acp.backends 默认全开", "dsh-remote-agy-images"]
---

# DeepSeek Harness Web UI (dsh web) 三层更新体系与插件升级及容器校验

> **一句话**：升级 `dsh web` 绝非单纯的一句 `npm update`，而是涵盖 **全局 CLI 核心**、**Profile 远端/本地插件依赖**、**Cordis 容器静态层叠校验** 与 **后台常驻服务无窗口平滑重启** 的四维确定性流水线。

---

## 一、业务场景与需求拆解（Type B 输入）

### 1.1 典型业务痛点

在深度定制和日常使用 DeepSeek Harness (DSH) Web UI 时，开发者常陷入以下几类更新困局：

| # | 症状 / 困局 | 底层反面现象 | 真实根因 |
|:---|:---|:---|:---|
| 1 | 执行了 `npm i -g @deepseek-ai/dsh`，浏览器打开依然是旧功能 | 界面无变化，新增的设置项或修复未生效 | 后台常驻服务（如 `Start-DshWeb.ps1` 启动的进程）未终止，仍驻留旧版内存实例 |
| 2 | 更新了全局 CLI，但三方插件（如 `ds-harness-remote`）依然停留在旧版本 | 远程通信特性报错或缺少新协议字段 | DSH 采用 Profile 隔离机制，每个 Profile（`~/.dsh/profiles/web`）有独立的 `package.json` 与 `pnpm-lock.yaml` |
| 3 | 修改了本地插件（`dsh-local-plugins`）代码后盲目重装 | 误删 `link:` 软链，导致 Cordis 找不到模块 | 本地插件走的是符号链接/Junction 直挂，仅需重启或热重载，严禁覆盖安装 |
| 4 | 更新完直接启动，启动失败弹窗崩溃 | 插件与新版核心接口不兼容，端口被占 | 缺乏零启动风险的静态容器配置校验，难以定位到底是哪个 patch 损坏 |

### 1.2 交付目标

沉淀一套确定性、低心智负担的 **DSH Web 端到端全景升级与验证流水线**，达成：
1. **分层分治**：精确区分核心升级、Profile 远端插件升级与本地软链模组；
2. **零启动验证**：在不盲目拉起服务前，通过 `dsh web --dump-config` 验证 Cordis 容器层叠完整性；
3. **平滑重启**：安全仲裁端口占用，无痛重启常驻无窗口后台服务。

---

## 二、技术核心难点与底层剖析

### 2.1 三层更新体系分层拓扑

DSH 的架构基于 Cordis 微内核与 Profile 补丁分层体系，逻辑拓扑如下：

```text
┌────────────────────────────────────────────────────────────────────────┐
│ 第一层：全局 CLI 核心与内置 App Bundles                                │
│   - 位置: D:\nvm4w\nodejs\node_modules\@deepseek-ai\dsh                │
│   - 范围: @deepseek-ai/dsh-base, @deepseek-ai/dsh-web-app 等           │
│   - 更新机制: npm install -g @deepseek-ai/dsh@latest                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ 继承 / 层叠
┌───────────────────────────────────▼────────────────────────────────────┐
│ 第二层：Web Profile 运行时依赖 (隔离沙箱)                               │
│   - 位置: ~/.dsh/profiles/web/ (package.json, pnpm-lock.yaml)          │
│   - 范围: 远端独立插件 (ds-harness-remote, argo, @taxueseek/argo-dsh)   │
│   - 更新机制: dsh plugin --profile web <pnpm-args...>                  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ 软链挂载
┌───────────────────────────────────▼────────────────────────────────────┐
│ 第三层：本地定制模组 (Local Mod Plugins)                               │
│   - 位置: D:\Users\dsh-local-plugins (如 rider-theme, skills-panel 等) │
│   - 依赖形式: "link:D:/Users/dsh-local-plugins/<plugin-name>"           │
│   - 更新机制: 本地源码就地修改，进程重启即生效，严禁 npm 覆写           │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.2 `dsh plugin` 转发机制与 pnpm 锁文件陷阱

DSH CLI 提供了原生的插件管理命令：
```text
dsh plugin --profile <name> <pnpm-args...>
```
其本质是把参数透明转发给 `~/.dsh/profiles/<name>/` 目录下的内置或全局 `pnpm` 执行。

在此过程中有两个关键细节：
1. **`pnpm outdated` 退出码陷阱**：
   当 pnpm 检测到有可更新的包时，其 CLI 设计规范是**返回退出码 1**。DSH 会输出 `dsh: plugin command failed` 并打印日志路径。这**不是执行器崩溃**，而是 pnpm 发现更新项的标准信号；
2. **精确版本升级陷阱**：
   `~/.dsh/profiles/web/package.json` 中的依赖通常为确定性锁定的固定版本号（如 `"ds-harness-remote": "0.5.14"`），若仅执行 `pnpm update`，只会刷新 lockfile 的次版本/补丁范围。若要升级至最新大版本，必须执行：
   ```powershell
   dsh plugin --profile web add <package>@latest
   ```

### 2.3 零启动风险：Cordis 容器静态遍历校验

更新包或修改插件后，直接拉起 Web 服务可能会因语法或依赖丢失导致闪退。DSH 提供了强大的静态解析能力：
```powershell
dsh web --dump-config
```
- **工作机制**：在内存中加载 Profile，按顺序层叠内置 bundle、`cordis.patch.yml`、环境变量与 `--patch`，渲染出最终生效的 YAML 配置树；
- **核心价值**：**完全不绑定网络端口，不拉起监听，不创建外部子进程**。若任何插件路径错误、缺依赖或 YAML 语法破损，将在该命令阶段立即抛出异常并定位到出错 entry，是绝对安全的预检手段。

---

## 三、标准自动化流水线与操作 SOP

### Step 1：环境诊断与运行态探测

检查当前是否有运行中的 `dsh web` 实例，以及监听端口（默认通常配置为 `11111` 或 `8080`）：

```powershell
# 1. 检查端口占用与持有进程 PID
$Port = 11111
$conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    Write-Host "检测到运行中的 DSH Web 实例 (PID: $($conn.OwningProcess))"
} else {
    Write-Host "当前无常驻 Web 服务运行，可安全更新"
}
```

### Step 2：升级全局 CLI 核心

通过 npm 升级全局 `@deepseek-ai/dsh` 包，并校验版本：

```powershell
# 1. 执行全局安装
npm install -g @deepseek-ai/dsh@latest

# 2. 验证版本（确认更新落地）
dsh -V
```

### Step 3：升级 Web Profile 插件与依赖

进入 Web Profile 依赖层更新远端插件：

```powershell
# 1. 安全备份当前配置与锁文件（防意外污染）
Copy-Item "$HOME\.dsh\profiles\web\package.json" "$HOME\.dsh\profiles\web\package.json.bak-update"
Copy-Item "$HOME\.dsh\profiles\web\pnpm-lock.yaml" "$HOME\.dsh\profiles\web\pnpm-lock.yaml.bak-update"

# 2. 检查可更新插件
dsh plugin --profile web outdated

# 3. 将目标插件升级至最新版本（以 ds-harness-remote 为例）
dsh plugin --profile web add ds-harness-remote@latest
```

> **注意（本地模组保护）**：  
> `D:\Users\dsh-local-plugins\` 下的本地插件（如 `@local/skills-panel`）是开发源码真身，只要源码被编辑保存即可，**严禁通过 `dsh plugin add/remove` 去修改它们**，否则会破坏 `package.json` 中的 `link:` 协议映射。

### Step 4：Cordis 容器层叠静态校验（门禁测试）

在不启动服务的前提下，验证配置与依赖树完整性：

```powershell
dsh web --dump-config
```
**通过判据**：输出全量 YAML 配置树，且控制台未打印 `StartupError`、`Cannot find module` 或 `did not activate`。

### Step 5：常驻后台服务重启生效

将旧进程优雅关闭并重新拉起无窗口服务：

```powershell
# 1. 若端口被旧服务占用，强制终止旧进程
$conn = Get-NetTCPConnection -LocalPort 11111 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    Stop-Process -Id $conn.OwningProcess -Force
    Start-Sleep -Seconds 1
}

# 2. 通过标准启动脚本重新拉起（无窗口 PWA 模式）
& "$HOME\.dsh\scripts\Start-DshWeb.ps1"

# 3. 或在前台临时验证排查
# dsh web
```

---

## 四、交付验证与防踩坑指南

### 4.1 交付核验清单（Checklist）

- [x] **CLI 版本一致性**：`dsh -V` 匹配 `npm view @deepseek-ai/dsh version`；
- [x] **Profile 依赖合规**：`~/.dsh/profiles/web/package.json` 中远端插件版本已更新，且本地插件的 `link:` 路径未被冲掉；
- [x] **静态解析无异常**：`dsh web --dump-config` 正常返回，退出码为 0；
- [x] **端口与连接正常**：服务启动后端口处于 `Listen` 状态，浏览器访问无白屏、Console 无 404/500。

### 4.2 高频踩坑与避坑铁律

1. **UTF-8 BOM 导致的启动器崩溃**：
   修改 `~/.dsh/scripts/Start-DshWeb.ps1` 等脚本时，Windows PowerShell 5.1 解析带 BOM 的 UTF-8 可能会破坏语法（误报 Try/Catch 缺失）。一律保持纯 ASCII 或使用无 BOM UTF-8。
2. **`dsh plugin command failed` 假警报**：
   跑 `dsh plugin --profile web outdated` 时若退出码为 1，先看控制台输出的表格。只要能打印出依赖的新旧版本，即表示依赖检查成功，不要误判为环境崩溃。
3. **“更新了但页面没变”的幽灵旧进程**：
   由于 `Start-DshWeb.ps1` 具备**端口幂等防护**（端口有人占着就只开 Chrome 窗口，不重新拉起服务），若更新前未先 `Stop-Process` 杀掉旧 node 进程，无论怎么双击快捷方式，启动的都是运行在旧内存里的老代码。

---

## 五、ds-harness-remote 专项：ACP 后端默认全开与 agy 幽灵常驻（2026-11-03 增补）

> 本质是 `fix` 类故障，但因与“插件升级”强绑定（每次升级都可能复发），按知识库高内聚原则就地并入本 Hub。**升级该插件后先跑 5.4 自检，可完全避免复发。**

### 5.1 现象直击

`dsh web` 运行一段时间后，任务管理器冒出 1~2 个 `agy.exe`（各约 190MB），命令行形如：

```text
agy --input-format stream-json --output-format stream-json --add-dir C:\Users\<u>\AppData\Local\Temp\dsh-remote-agy-images-user
```

- 父进程是 `dsh web` 的 node 进程，并非用户手动启动；
- 每个 `agy` 还会各自拉起一个 `aoci.exe`（agy 自带的 MCP server），合计 400~500MB；
- 手动 `Stop-Process -Name agy -Force` 后**几秒内重生**，像打不死的小强。

### 5.2 根因剖析（不是随机，是被 ACP 预热拉起的）

`ds-harness-remote/dist/config.js` 的 `resolveConfig()` 内置了六个 ACP 后端，且默认值判定如下：

```js
backends: [...new Set(['codex','cursor','antigravity','pi','claude','opencode', ...你的配置])]
enabled: configured?.enabled ?? legacy?.enabled ?? (
    id === 'codex'  ? codexEnabled
  : id === 'cursor' ? cursorEnabled
  : id === 'pi' || id === 'claude' || id === 'opencode' ? true
  : parsed.acp !== undefined        // ← antigravity 落到这一支
)
```

**关键结论：只要 `cordis.patch.yml` 里出现 `acp:` 这一块，`antigravity` 就默认 `enabled: true`**，哪怕你只写了 codex。随后任一客户端请求会话列表（`acp/gateway.js` 的 `dsh/sessionList`）时，会走 `prewarmSession()` 常驻一个 `agy` 准备接活——这就是“莫名其妙”的全部来源。

### 5.3 修复：按需全关 / 只留 codex / 只封 AGY

`~/.dsh/profiles/web/cordis.patch.yml` 的 `ds-harness-remote` 条目（**patch 的 config 是整块浅替换，acp 段必须写全**）：

```yaml
    codex:
      enabled: false
    acp:
      enabled: false
      backends:
        - { id: codex,       enabled: false, command: codex, args: [acp] }
        - { id: cursor,      enabled: false, command: agent, args: [acp] }
        - { id: antigravity, enabled: false }
        - { id: pi,          enabled: false }
        - { id: claude,      enabled: false }
        - { id: opencode,    enabled: false }
```

三档选择：

| 目标 | 配置 | 效果 |
| :--- | :--- | :--- |
| 完全不要 ACP 后端 | `acp.enabled: false` + 各 backend `enabled: false` | 网关不初始化，零子进程 |
| 只保留远程 Codex 工作区 | `acp.enabled: true`，仅 codex 为 true | 只剩 codex app-server |
| 只封 AGY | 其余不动，仅加 `- id: antigravity { enabled: false }` | codex/cursor 保持原样 |

两个坑：
- `kimi` 自 0.6.0 起被 `resolveConfig` 过滤（`item.id !== 'kimi'`），写了无效，直接删；
- `cursor` 的默认命令是裸 `agent`，在装了 xAI Grok CLI 的机器上会被同名解析并弹 `accounts.x.ai`（详见 081 条），建议永远显式 `enabled: false`。

### 5.4 升级后必做自检（防复发核心）

```powershell
# 1) 升级（dsh plugin 会自动改写 lockfile；带 dsh.bundle 声明的依赖也会自动回到 bundles）
dsh plugin --profile web add ds-harness-remote@latest

# 2) 确认 bundles 里仍有它（被 UI 手动停用过会保留 disabled 状态，需要再确认一次）
(Get-Content "$HOME\.dsh\profiles\web\package.json" -Raw | ConvertFrom-Json).dsh.profile.bundles -contains 'ds-harness-remote'

# 3) 静态校验容器层叠（不启动服务、不占端口）
dsh --profile web --dump-config | Select-String 'ds-harness-remote|not found'

# 4) 用插件自己的 resolveConfig 验证后端是否真的全关（关键门禁）
node "$env:TEMP\probe-remote-acp.mjs"

# 5) 重启后观察 10 秒，agy 必须为 0
(Get-Process agy -ErrorAction SilentlyContinue | Measure-Object).Count
```

第 4 步的探针（一次性保存到 `%TEMP%\probe-remote-acp.mjs`，升级后重跑；输出应打印 `acp.enabled=false` 且启用列表为空）：

```js
import { resolveConfig } from 'file:///C:/Users/29580/.dsh/profiles/web/node_modules/ds-harness-remote/dist/config.js';
const cfg = {
  enabled: true, role: 'host', serverUrl: 'https://dsh.r2049.cn',
  codex: { enabled: false, binary: 'codex' }, terminal: { enabled: true },
  loopback: { ports: [] }, forceRelay: false, logLevel: 'info',
  reconnect: { initialDelayMs: 1000, maxDelayMs: 30000, jitter: 0.2 },
  acp: { enabled: false, backends: [
    { id: 'codex', enabled: false, command: 'codex', args: ['acp'] },
    { id: 'cursor', enabled: false, command: 'agent', args: ['acp'] },
    { id: 'antigravity', enabled: false }, { id: 'pi', enabled: false },
    { id: 'claude', enabled: false }, { id: 'opencode', enabled: false },
  ] },
};
const r = resolveConfig(cfg);
console.log('acp.enabled =', r.acp.enabled, '| codex.enabled =', r.codex.enabled);
console.log('enabled backends:', r.acp.backends.filter(b => b.enabled).map(b => b.id));
```

### 5.5 验证与防复发闭环

- `(Get-Process agy).Count -eq 0`，且重启、远程客户端连入、刷新 Remote 面板后仍保持 0；
- `acp.enabled: false` 时 `/ds-harness-remote/status` 仍返回 **401**（插件在线、仅需鉴权），说明“关 ACP”没有误伤远程连接本身；
- Windows 上父进程退出不会连带杀子进程，历史残留需 `Stop-Process -Name agy -Force` 清一次；
- 新版本若又引入新的默认后端，按 5.3 的写法在 `backends` 里补一条 `enabled: false` 即可，无需改代码。
