---
name: kb-antigravity-manager-switch-conflict
description: Antigravity Manager 切换客户端报错“操作失败，请查看诊断详情后重试”、target-conflict 进程冲突归因排障与 App/CLI 凭证体系深度解析指南。
id: "068"
domain: agent
scope: agyman
type: fix
slug: "AGYManager切换失败target-conflict与汉化进程冲突"
status: verified
created: "2026-09-22"
last_verified: "2026-10-20"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: true
---

# Antigravity Manager 切换客户端失败 target-conflict 根因排障与汉化工具进程冲突解决指南

## 一、现象与报错直击

在使用第三方账号管理工具 **Antigravity Manager**（基于 Electron + React / Vite 构建）进行多账号或多环境切换时，点击卡片菜单中的 `SWITCH ENVIRONMENT -> 切换到 Antigravity`，界面右下角立即弹出红色错误 Toast：

```text
切换账号失败
操作失败，请查看诊断详情后重试。
[上报到 GitHub]  [详情]
```

### 1. 真实运行日志提取
在 `%USERPROFILE%\.antigravity-agent\app-YYYY-MM-DD.log`（例如 `app-2026-10-17.log`）中记录了切换失败时的精确诊断信息：

```json
[2026-10-16T20:00:56.430Z] [INFO] Operation step v1 {"schemaVersion":1,"diagnosticId":"ba44ae9d-1ee7-49bc-845c-812f5b702a03","operation":"cloud-account-switch","stage":"account-load","outcome":"started"}
[2026-10-16T20:00:56.433Z] [INFO] Switching to cloud account: user@example.com (01bfbf8b-f53c-4b7c-a4b8-9b6132a38604)
[2026-10-16T20:00:56.433Z] [INFO] Operation step v1 {"schemaVersion":1,"diagnosticId":"ba44ae9d-1ee7-49bc-845c-812f5b702a03","operation":"cloud-account-switch","stage":"client-selection","outcome":"started"}
[2026-10-16T20:00:56.521Z] [INFO] Operation step v1 {"schemaVersion":1,"diagnosticId":"ba44ae9d-1ee7-49bc-845c-812f5b702a03","operation":"cloud-account-switch","stage":"client-selection","outcome":"failed"}
[2026-10-16T20:00:56.522Z] [INFO] Operation diagnostic v1 {
  "schemaVersion": 1,
  "diagnosticId": "ba44ae9d-1ee7-49bc-845c-812f5b702a03",
  "operation": "cloud-account-switch",
  "stage": "client-selection",
  "reason": "unknown",
  "nativeCode": "ANTIGRAVITY_PROCESS_FAILED",
  "target": "classic",
  "rollback": "not-attempted",
  "causes": [{"reason":"unknown","nativeCode":"ANTIGRAVITY_PROCESS_FAILED"}]
}
[2026-10-16T20:00:56.524Z] [ERROR] [ORPC] Error in handler for ["cloud","switchCloudAccount"]: {"name":"Error","message":"Cloud account switch failed"}
```

---

## 二、底层根因剖析

### 1. 切换目标环境辨析（Target 区分）
Antigravity Manager 代码内将客户端划分为三个目标（`appTarget`）：
- `"classic"`（UI 显示为 **切换到 Antigravity**）：Google Antigravity 独立桌面端，可执行文件为 `Antigravity.exe`；
- `"ide"`（UI 显示为 **切换到 Antigravity IDE**）：基于 VS Code 内核包装的 IDE 桌面端，可执行文件为 `Antigravity IDE.exe`；
- `"agy"`（UI 显示为 **Switch to Antigravity CLI**）：终端命令行工具 `agy.exe`。

### 2. 源码调用链路与预检机制
在主进程 `main-*.js` 的 `switchCloudAccount` 处理链中：
```javascript
// 1. 进入切换流程并标记 launch-preflight（映射为 client-selection 阶段）
te.info(`Switching to cloud account: ${l.email} (${l.id})`),
u("launch-preflight");
const d = t === "agy" ? void 0 : await B_(t === "ide" ? "ide" : "classic");

// 2. B_ 函数负责启动前进程与路径探测
async function B_(e) {
  return await CHt(e), kHt(e, await ec(e));
}
```

其中 `ec(e)` 会调用 `IHt(e)`，借助原生模块 `@draculabo/sysinfo-process-enhanced` 枚举系统正在运行的所有进程，并通过 `Jfe` / `MHe` 过滤匹配目标客户端。

### 3. 正则误判与路径冲突（Target Conflict）
看核心过滤函数 `MHe` 对经典版客户端的识别逻辑：
```javascript
function MHe(e, t, n) {
  const i = e.name.toLowerCase();
  const a = e.commandLine.toLowerCase();
  ...
  return (i.includes("antigravity") || a.includes("antigravity"))
    && !m
    && !i.includes("manager")
    && !a.includes("manager")
    && !i.includes("tools")
    && !a.includes("tools");
}
```

* **误识别点**：若系统后台正运行着中文汉化辅助程序（如 `antigravity-hans-gui.exe`），其进程名中包含 `antigravity`，且不包含 `ide`、`manager`、`tools`。
* `MHe` 将 `antigravity-hans-gui.exe` 误判定为“正在运行的 Antigravity 客户端实例”，并将其放入当前进程列表 `t` 中。
* 接着执行 `kHt` 进行环境一致性校验：
  ```javascript
  function kHt(e, t) {
    const r = fre(n || z9(e, { ignoreRunningProcessCache: !0 })); // 配置的实际客户端路径，如 C:\...\Antigravity.exe
    if (t.some(m => !UVe(r, m.executablePath))) throw Gt("target-conflict");
  ```
* 此时 `r` 为配置的 `Antigravity.exe`，而检测到的进程 `m.executablePath` 是 `antigravity-hans-gui.exe`。
* `UVe(r, m.executablePath)` 校验失败，抛出 `Gt("target-conflict")`，内部包装为 `nativeCode: "ANTIGRAVITY_PROCESS_FAILED"`。
* 前端捕获后找不到定制的错误码文案，回退到兜底状态 `switchFailureCodes.retry`，显示“操作失败，请查看诊断详情后重试”。

---

## 三、标准抢救与修复 SOP

### 1. 临时抢救步骤（立竿见影）
若当前需要立即在 Antigravity Manager 中完成切换：

1. 打开任务管理器（`Ctrl + Shift + Esc`）或使用 PowerShell 查找冲突进程：
   ```powershell
   Get-Process | Where-Object { $_.ProcessName -match "antigravity" } | Select-Object Id, ProcessName, Path
   ```
2. 找到 `antigravity-hans-gui` 进程并退出：
   ```powershell
   Stop-Process -Name "antigravity-hans-gui" -Force
   ```
3. 返回 Antigravity Manager，再次点击 `切换到 Antigravity`，此时预检通过，正常写入凭据。
4. 切换完成后，可重新启动汉化工具。

### 2. 区分实际使用的客户端类型
* 若你安装并使用的是 **Antigravity IDE**（基于 VS Code 外壳），在卡片下拉菜单中应选择：
  👉 **`切换到 Antigravity IDE`**
* IDE 模式的预检过滤条件强制要求进程包含 `ide`，不会被 `antigravity-hans-gui.exe` 误伤。

---

## 四、延伸机制：Antigravity App 与 CLI 是否共享账号？

### 结论
**默认不共享。二者拥有完全隔离的本地凭据存储体系。**

| 客户端形态 | 凭证存储载体 / 路径 | 认证机制 | 相互影响 |
|---|---|---|---|
| **Antigravity CLI (`agy`)** | `~/.gemini/antigravity-cli/antigravity-oauth-token`<br>`~/.gemini/oauth_creds.json`<br>`~/.gemini/google_accounts.json` | 纯文本 / JSON 文件 | 在终端 `agy auth login` 切换账号，**不影响**桌面 App / IDE |
| **Antigravity App (独立版)** | Windows 凭据管理器（Credential Manager）：<br>Target: `gemini:antigravity`<br>User: `antigravity` | 操作系统安全凭据环 | 在 App 内注销或重新登录，**不影响** CLI 终端会话 |
| **Antigravity IDE (VS Code 版)** | `%APPDATA%\Antigravity IDE\User\globalStorage\state.vscdb` | SQLite 数据库键值表 | 独立会话库，与独立 App 及 CLI 均隔离 |

在 Antigravity Manager 中，右侧卡片显示 `• Antigravity CLI`，左侧卡片显示 `• Antigravity IDE`，也正印证了 Manager 在底层是对这三套凭证环境分别进行独立调度与针对性注入的。

---

## 五、验证与防复发建议

1. **检查 Manager 配置文件路径**：
   查看 `%USERPROFILE%\.antigravity-agent\gui_config.json`，确保其中的可执行文件路径与实际磁盘安装位置一致：
   ```json
   {
     "antigravity_executable": "C:\\Users\\<User>\\AppData\\Local\\Programs\\antigravity\\Antigravity.exe",
     "antigravity_ide_executable": "D:\\...\\Antigravity IDE\\Antigravity IDE.exe",
     "antigravity_cli_executable": "C:\\Users\\<User>\\AppData\\Local\\agy\\bin\\agy.exe"
   }
   ```
2. **多设备/多环境协同注意**：
   同一个 Google 账号在 Mac 与 Windows 上同时登录是完全被官方允许的，但两台设备共用同一个 5 小时滚动配额池（Five Hour Limit）。进行高并发 Coding Agent 任务时注意额度合理分配。