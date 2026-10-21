---
name: kb-feishu-bridge-keeper-conhost-popup
description: |
  Pi 飞书桥接（ax-feishu-bridge）的隐藏保活器 pi-feishu-keeper.mjs 因 CLI 入口解析失败 + PI_CLI_ENTRY 指向包装层，导致 child.pid 与网关锁 owner pid 不一致，把自家 daemon 误判成“别人的 owner”而每 10 秒杀掉重生，且 spawn 缺 windowsHide 在定制版 WT（DefTerm 断层）下每轮弹出一个标题为 pi 的裸 conhost 黑窗的全链路根因与修复 SOP。
version: 1.0.0
created: 2026-10-20
updated: 2026-10-20
id: "084"
domain: agent
scope: pi
type: fix
slug: "飞书桥接keeper空转重生pi弹conhost黑窗"
status: verified
last_verified: "2026-10-20"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: true
  trigger_keywords: ["pi 弹窗", "重启弹黑窗", "标题 pi 窗口", "feishu keeper", "pi-feishu-keeper", "ax-feishu-bridge", "another live owner", "windowsHide", "PI_CLI_ENTRY"]
---

# agent_pi_fix_084_飞书桥接keeper空转重生pi弹conhost黑窗

> **条目定位**：**Type A 疑难排障条目（Windows 后台守护进程 pid 语义 × conhost 窗口归属）**
> **危险评级**：★★★☆☆（无数据损失，但每 10 秒重拉一次 pi daemon，持续吃 CPU/内存并反复弹窗，极易被误判为终端或编辑器问题）
> **验证环境**：Windows 11、Pi 1.3.0 托管安装（`~/.pi/agent/install/releases/1.3.0`）、`ax-feishu-bridge`（npm 扩展）、定制版独立 Windows Terminal（`D:\Users\Softwares\WindowsTerminal`，PE 便携版，未注册为系统默认终端）。
> **关联条目**：定制版 WT 控制台委托断层与 PE 无窗口镜像见 `052_win_conhost_fix_PE控制台委托DefTerm断层与MCP无窗口镜像.md`；计划任务触发 WT 闪标签页见 `011_win_conhost_fix_计划任务控制台委托闪窗与conhost注册.md`；无窗口服务与自启治理见 `063_win_sys_flow_Win无窗口服务快捷方式与自重启及PS5.1排障.md`。

---

## 一、现象与报错直击

### 1. 用户可见症状

- **每次重启电脑都会弹出一个标题为 `pi` 的独立窗口**：黑色内容区、无标签栏、带系统标题栏（最小化/最大化/关闭），与 Windows Terminal 窗口外观高度相似，非常容易被误判为"WT 恢复上次会话"或"pi 自己弹窗"。
- 该窗口内容为空（或只有零星残影字符），关掉后过一会儿可能再次出现。
- `Get-Process | Where MainWindowTitle -eq 'pi'` 能稳定命中一个 `node.exe`。

### 2. 关键取证（`~/.pi/agent/feishu/daemon.log`）

```text
[keeper 08:11:12] spawned daemon pid=37004
[keeper 08:11:22] killing my daemon pid=37004 (another live owner)
[keeper 08:11:32] spawned daemon pid=38296
[keeper 08:11:42] killing my daemon pid=38296 (another live owner)
[keeper 08:11:52] spawned daemon pid=38948
```

严格 20 秒一轮（spawn → 10s 后自杀 → 10s 后再 spawn）的**无限重生循环**，且每次重生都伴随一个新窗口。

### 3. 进程取证

```powershell
Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
  Where-Object { $_.CommandLine -like '*--mode rpc*' } |
  Select ProcessId,ParentProcessId,CommandLine
```

```text
33560 <- 34296  node ...\bin\pi-launcher.js --mode rpc ... -e ...ax-feishu-bridge...\feishu\index.ts
34296 <- 33560  node ...\install\releases\1.3.0\...\dist\bundle\cli.js --mode rpc ... -e ...feishu\index.ts
```

`locks.json` 里的网关 owner pid 是 `34296`（真实 cli），而 keeper 记录的 `child.pid` 是 `33560`（launcher 包装层）——**两者不是同一个进程**，这就是全部问题的起点。

```powershell
# 该窗口挂在裸 conhost 下，而不是 WT 的 OpenConsole 会话里
Get-CimInstance Win32_Process -Filter "Name='conhost.exe'"   # parent = node.exe
```

---

## 二、底层根因剖析（三层叠加）

### 根因 1：托管安装入口路径写死在旧位置

```js
// 错误写法：1.3.x 起入口已迁至 dist/bundle/cli.js
const cli = join(AGENT_DIR, "install", "releases", version, "node_modules",
                 "@earendil-works", "pi-coding-agent", "dist", "cli.js");
if (existsSync(cli)) return cli;
return join(AGENT_DIR, "bin", "pi-launcher.js");   // 静默回落
```

`dist/cli.js` 在新版仍作为兼容垫片存在但并非 keeper 需要的**直连入口**语义；一旦解析走到 `pi-launcher.js`，`spawn` 出来的就是包装层 node，再由它 `spawnSync` 真正的 cli.js。

### 根因 2：`PI_CLI_ENTRY` 环境变量把包装层钉死了

```powershell
Get-ItemProperty 'HKCU:\Environment' | Select PI_CLI_ENTRY
# PI_CLI_ENTRY : C:\Users\29580\.pi\agent\bin\pi-launcher.js
```

keeper 早期实现是 `process.env.PI_CLI_ENTRY || FALLBACK_CLI`，即**环境变量优先级最高**。用户环境里这条变量一旦指向 launcher，根因 1 的修复就完全无效——必须在 keeper 侧改成"托管直连入口优先"。

### 根因 3：pid 语义不自洽 → keeper 自杀式空转

keeper 用 `child.pid` 与 `locks.json` 的 `owner.pid` 比较来判断"这个 owner 是不是我自己"：

```js
if (fresh) {
  if (mine && owner.pid !== child.pid) killChild("another live owner");
  return;
}
```

- 走 launcher 时 `child.pid`（包装层）恒不等于 `owner.pid`（内层 cli），**自己永远被判定成"别人的 daemon"**；
- 杀掉包装层后，`locks.json` 里仍残留刚写的心跳（`heartbeatAt` 未过期但 pid 已死）→ 下一轮 `fresh=false` → 走 stale 分支再 `spawnDaemon()`；
- 于是形成 20 秒一轮的 **spawn → 误杀 → 残留锁 → 再 spawn** 死循环。

> 该缺陷的隐蔽性在于：功能"看起来是好的"（飞书消息能收发），日志里只有 `another live owner` 这种"合理"文案，若不去数时间戳间隔，很难察觉是自残。

### 根因 4：`spawn` 缺 `windowsHide` + 定制版 WT 委托断层 → 黑窗直接落在桌面

```js
spawn("node", [cli, ...args], { detached: true, stdio: [...] });   // 无 windowsHide
```

- keeper 自身由 `wscript.exe ... 0, False`（隐藏窗口）启动，**没有任何控制台**；
- 无控制台的父进程 `spawn` 子进程且 `detached: true` 时，Windows 会为子进程**新建一个可见控制台**（conhost）；
- 定制版 WT 是便携版 PE，未注册为系统默认终端（`HKCU\Console\%%Startup` 的 `DelegationConsole/DelegationTerminal` 仍指向系统 conhost 或指向便携版但 CLSID 未注册）→ 控制台委托（DefTerm handoff）断层，该会话**无法被并入 WT 标签**；
- 结果就是桌面上凭空出现一个标题为 `pi` 的裸 conhost 黑窗，每重生一次就再弹一个。

---

## 三、标准修复 SOP

> 目标：让 keeper 的 `child.pid` 恒等于网关锁 owner pid，且永不创建可见控制台。

### 步骤 1：修正入口解析，兼容 `dist/bundle/cli.js`

```js
function resolveManagedCli() {
  try {
    const version = readFileSync(join(AGENT_DIR, "install", "current-version"), "utf8").trim();
    const pkgDir = join(AGENT_DIR, "install", "releases", version,
                        "node_modules", "@earendil-works", "pi-coding-agent");
    for (const rel of [join("dist", "bundle", "cli.js"), join("dist", "cli.js")]) {
      const cli = join(pkgDir, rel);
      if (existsSync(cli)) return cli;
    }
  } catch {}
  return join(AGENT_DIR, "bin", "pi-launcher.js");
}
```

### 步骤 2：托管直连入口优先，环境变量只作兜底

```js
const managedCli = resolveManagedCli();
const cli = !managedCli.endsWith("pi-launcher.js")
  ? managedCli                                   // 能直连就直连，无视 PI_CLI_ENTRY
  : (process.env.PI_CLI_ENTRY && existsSync(process.env.PI_CLI_ENTRY)
      ? process.env.PI_CLI_ENTRY : managedCli);
```

### 步骤 3：`spawn` 补 `windowsHide: true`

```js
child = spawn("node", [cli, ...args], {
  detached: true,
  windowsHide: true,   // 无控制台父进程 + detached：不加这行必弹 conhost 黑窗
  cwd: WORKSPACE,
  env: { ...process.env, PI_FEISHU_DAEMON: "1" },
  stdio: ["pipe", logFd, logFd],
});
```

### 步骤 4：为"包装层"场景加防误杀兜底

```js
if (fresh) {
  // 经 launcher 兜底启动时，child.pid 是包装层 pid，与 owner pid 天然不同，不得误杀
  if (mine && owner.pid !== child.pid && !cli.endsWith("pi-launcher.js")) {
    killChild("another live owner");
  }
  return;
}
```

### 步骤 5：清场并重启 keeper 验证

```powershell
$env:PI_CLI_ENTRY   # 仅诊断用，不必删除该变量
Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
  Where-Object { $_.CommandLine -like '*pi-feishu-keeper*' -or $_.CommandLine -like '*--mode rpc*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep 2
Start-Process wscript.exe -ArgumentList 'C:\Users\29580\.pi\agent\feishu\pi-feishu-keeper.vbs'
```

---

## 四、验证与防复发

### 1. 三条硬指标（全部满足才算修好）

```powershell
# ① keeper 日志里 keeper started 的 cli 必须是 dist\bundle\cli.js
Select-String -Path "$env:USERPROFILE\.pi\agent\feishu\daemon.log" -Pattern "keeper started" | Select -Last 1

# ② 观察 ≥3 分钟，不得再出现 killing my daemon（正常应 0 条）
Select-String -Path "$env:USERPROFILE\.pi\agent\feishu\daemon.log" -Pattern "killing my daemon" | Select -Last 5

# ③ owner pid 必须等于 keeper 的子进程 pid，且不残留可见 pi 窗口
Get-Process | Where-Object { $_.MainWindowTitle -eq 'pi' }   # 期望：无输出
Select-String -Path "$env:USERPROFILE\.pi\agent\locks.json" -Pattern '"pid"'
```

### 2. 防复发建议

- **升级 pi 后回归一次**：pi 每次大版本可能再次搬移 CLI 入口（`dist/cli.js` → `dist/bundle/cli.js` → 未来 `dist/rpc-entry.js`），keeper 的入口解析应始终优先识别"能直连的 cli"，而不是依赖某个固定相对路径。
- **凡"隐藏守护 + detached spawn"的组合，一律显式 `windowsHide: true`**；这是 Windows 上无控制台父进程凭空造出黑窗的唯一常见来源。
- **不要把 pi 的包装层（`bin\pi-launcher.js`）写进 `PI_CLI_ENTRY`**：包装层会让所有基于 pid 的身份判定（锁文件、单实例保护、保活器）全部失准。
- **误诊排除记录**：本次曾被误判为「定制版 WT 的 `firstWindowPreference: persistedLayoutAndContent` 回放了 pi 的全屏 TUI 快照」。判别方法很简单——**WT 回放的画面必然活在 WT 窗口内（标题栏是 WT 的、有标签栏），而裸 conhost 黑窗是独立顶层窗口，且 `Get-CimInstance Win32_Process -Filter "Name='conhost.exe'"` 能看到 parent 是 `node.exe`**。改 WT 设置对该问题完全无效。
