---
id: "081"
domain: "agent"
scope: "dsh"
type: "fix"
slug: "Cursor别名冲突致Grok误唤起与xai弹窗修复"
status: "verified"
created: "2026-10-20"
last_verified: "2026-10-20"
superseded_by: null
deprecation_reason: null
compatibility:
  os: ["windows"]
  tools:
    agent_framework: ["dsh", "grok", "cursor"]
falsification_signals:
  - "若系统中未安装 Grok CLI (agent.exe) 或 PATH 中无 grok/bin，则不是本冲突"
  - "若弹出的不是 accounts.x.ai/oauth2/device 页面，需按具体 URL 反查拉起进程"
invocation:
  auto_trigger: true
  trigger_keywords: ["accounts.x.ai", "user_code", "dsh web", "ds-harness-remote", "Cursor ACP communication failed", "CURSOR_BINARY_UNAVAILABLE", "agent.exe"]
---

# 081-Cursor别名冲突致Grok误唤起与xai弹窗修复

## 一、现象与报错直击

在 Windows PowerShell 下启动 DeepSeek Harness Web 服务时：
```powershell
PS C:\Users\29580\dsh_web_launcher> dsh web --port 11111 --no-open
```
终端输出各 MCP 与子模块正常初始化日志：
```text
[argo-mcp] starting (lazy imports enabled)
[agy-bridge] starting agy-bridge 0.1.0; agy=found
[dsh-remote] host identity ready {"deviceId":"01a0f1f8…ebdd","fingerprint":"E29F C408 C0E1","server":"https://dsh.r2049.cn"}
[dsh-remote] Codex App Server communication failed {"code":"CODEX_BINARY_UNAVAILABLE"}
[dsh-remote] Cursor ACP communication failed {"code":"CURSOR_BINARY_UNAVAILABLE"}
...
dsh web: http://127.0.0.1:11111/?token=...
```

### 诡异异常现象
明明在命令行显式传递了 `--no-open`（禁止打开网页），系统默认浏览器却突兀地弹出了一个 xAI (Grok) 官方的设备授权登录页面：
```text
https://accounts.x.ai/oauth2/device?user_code=TCX7-A3SG
```
而整个过程用户并没有主动使用任何与 xAI 或 Grok 相关的命令。

---

## 二、底层根因剖析（双重撞车机制）

经深入系统排查，该事故由 **“通用命名撞车（Binary Name Shadowing）”** 与 **“CLI 掉登强制弹窗”** 两层独立机制叠加导致：

```text
dsh web 启动
  └─ 加载 ds-harness-remote (0.5.14) 作为 Host 运行
      └─ 初始化 ACP 网关 backends
          └─ 探测 cursor 后端：spawn('agent', ['acp'])
              │
              ▼ (PATH 命中)
          C:\Users\<user>\.grok\bin\agent.exe (xAI Grok CLI，撞名 agent)
              │
              ▼ (自检 auth.json 缺失 / 未登录)
          触发 auth: inline auth flow (向 accounts.x.ai 请求设备授权码)
              │
              ▼
          调用 Win32 ShellExecute 打开浏览器强弹 https://accounts.x.ai/oauth2/device?user_code=...
```

### 1. 第一层：`ds-harness-remote` 远程网关的 ACP 探测与别名撞车
- `ds-harness-remote` 是一个跨设备端到端加密远程中继插件，用于在远端客户端统一调度本地 AI 工作区。
- 它内置了实验性的 ACP（Agent Client Protocol）网关。在 `cordis.patch.yml` 中，默认配置了对 Cursor 的探测：
  ```yaml
  acp:
    enabled: true
    backends:
      - id: cursor
        enabled: true
        command: agent    # Cursor 早期的后台 Agent CLI 裸别名
        args: [acp]
  ```
- 巧合的是，用户系统内通过官方渠道安装了 **xAI Grok CLI**（位于 `C:\Users\<user>\.grok\bin`），该目录被自动添加到了系统环境变量 `PATH` 中。
- Grok CLI 的主执行程序名字正好也是 **`agent.exe`**。
- 当 `ds-harness-remote` 启动并调用 `agent acp` 时，Windows 系统解析裸名 `agent` 优先命中了 `C:\Users\<user>\.grok\bin\agent.exe`。

### 2. 第二层：Grok CLI 掉登触发强制 OAuth2 Device Code Flow
- **为什么以前没弹过？**
  - 在以往正常使用时，如果 Grok 处于登录状态（存在有效的 `~/.grok/auth.json`），`agent.exe` 收到不认识的 `acp` 参数通常会识别为未知子命令并静默退出，`dsh` 捕获到进程退出只会在终端输出一行 `CURSOR_BINARY_UNAVAILABLE`，用户完全无感。
- **为什么这次突然弹窗？**
  - 排查 Grok 运行日志（`~/.grok/logs/unified.jsonl`），时间戳（19:38:39）与 `dsh` 启动时间完全一致：
    ```json
    {"ts":"2026-10-20T11:38:39.481Z","src":"shell","pid":12240,"lvl":"info","msg":"auth started","ctx":{"method":"grok.com"}}
    {"ts":"2026-10-20T11:38:39.481Z","src":"shell","pid":12240,"lvl":"info","msg":"auth: inline auth flow","ctx":{"method":"grok.com"}}
    ```
  - 当本地缺少 `auth.json`（掉登、缓存清理或新装）时，Grok CLI 设定了极高的鉴权拦截优先级：**无论传入什么参数（哪怕传错），一律先启动内联登录流**，直接向 `https://accounts.x.ai` 申请设备码，并通过系统 API 强制唤起默认浏览器打开授权页。
  - `--no-open` 是 `dsh` 自身的参数，完全无法约束外部第三方独立进程通过系统 API 唤起浏览器的行为。

---

## 三、标准抢救与修复 SOP

如果日常并不需要通过 `dsh` 远程调度本地 Cursor，最彻底、干净的修复方式是将 `cursor` ACP 后端禁用，消除空耗与误拉起风险。

### 步骤 1：定位并修改 Profile 配置文件
检查所有加载了 `ds-harness-remote` 的配置文件（通常包含 `web` 与 `desktop` profile）：
- `~/.dsh/profiles/web/cordis.patch.yml`
- `~/.dsh/profiles/desktop/cordis.patch.yml`

将 `acp.backends` 列表中的 `cursor` 项设为 `enabled: false`：

```yaml
      backends:
        - id: codex
          enabled: true
          command: codex
          args:
            - acp
        - id: cursor
          enabled: false # 禁用：避免与 PATH 中的 Grok agent.exe (xAI) 命名冲突导致误拉起与 OAuth 弹窗
          command: agent
          args:
            - acp
        - id: kimi
          enabled: true
          command: kimi
          args:
            - acp
```

### 步骤 2：写后必检（Post-Write Invariant）
在 PowerShell 中对修改后的 YAML 文件执行格式与 BOM 检查：

```powershell
# 1. 验证绝无 UTF-8 BOM（头3字节无 EF BB BF）
$files = @(
    "$env:USERPROFILE\.dsh\profiles\web\cordis.patch.yml",
    "$env:USERPROFILE\.dsh\profiles\desktop\cordis.patch.yml"
)
foreach ($f in $files) {
    $bytes = [System.IO.File]::ReadAllBytes($f)
    $hasBom = ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)
    if ($hasBom) { throw "BOM detected in $f" }
}

# 2. 验证 YAML 语法解析
uv run --with pyyaml python -c "
import yaml
for f in [r'$env:USERPROFILE\.dsh\profiles\web\cordis.patch.yml', r'$env:USERPROFILE\.dsh\profiles\desktop\cordis.patch.yml']:
    with open(f, 'r', encoding='utf-8') as fp:
        yaml.safe_load(fp)
    print(f, 'OK')
"
```

---

## 四、验证与防复发闭环

1. **现场验证**：
   再次在终端执行 `dsh web --port 11111 --no-open`：
   - 不再输出 `Cursor ACP communication failed`。
   - `C:\Users\<user>\.grok\bin\agent.exe` 进程不再被拉起。
   - 默认浏览器不再弹出 `https://accounts.x.ai/...` 设备授权流页面。

2. **架构级防坑警示**：
   - **避免裸调无命名空间的通用 CLI 别名**：在跨 Agent、多客户端共存的环境中，诸如 `agent`、`cli`、`server`、`runner` 这类极度宽泛的名字极易被其他厂商的同类工具劫持；若确需集成 Cursor，应显式指定全路径或专有包装器（如 `cursor-agent.cmd`）。
   - **防范未鉴权 CLI 的主动弹窗副作用**：命令行工具集成至后台服务或自动化工作流时，需警惕未登录状态下可能产生的 GUI/浏览器弹窗阻断行为。
