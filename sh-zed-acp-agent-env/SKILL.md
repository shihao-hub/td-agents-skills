---
name: sh-zed-acp-agent-env
description: Zed 编辑器 ACP 外部 agent（antigravity-acp / Google Antigravity / codex-acp / claude-acp / opencode registry agent）的 Windows 排障手册：环境变量注入（agent_servers.*.env）、系统代理（Clash）与 CA 证书、Google OAuth 登录失败（浏览器显示认证成功但 Zed 仍要求登录、反复 onboarding_failed、凭据被清）、改 env 不生效（Zed 复用旧 agent 进程）、以及不经 Zed UI 直接对 agent 做 stdio JSON-RPC 认证探针。当用户说 Zed 里 Antigravity/Google agent 登录不了、登录成功了却没登录态、ACP agent 不走代理或不信任证书、怀疑 agent 进程是旧的、要杀 agy_acp_server 进程、或要验证 ACP agent 认证链路时，必须使用本 skill。
---

# Zed ACP 外部 agent 环境注入与登录排障手册（Windows）

沉淀自 2026-09-21 的 antigravity-acp 登录排障实战（Zed 1.20.2 + antigravity-acp v_1.1.1 + Clash Verge/mihomo `127.0.0.1:7897`，修复全程实证：token 兑换 200 → 会话创建 → 11 个模型 → 凭据跨进程持久）。核心是三条反直觉事实，漏掉任何一条都会走弯路：

1. **浏览器显示 "Authentication successful" ≠ 登录成功。** Antigravity 的 OAuth 成功页由本地回环服务器在 code→token 兑换**之前**展示；之后还有 token 兑换 + CCPA onboarding，任一步失败都会清凭据并登出（Zed 界面回到登录按钮）。源码链路见 `references/antigravity-internals.md`。
2. **代理对 agent 的生效形态要实测，别想当然。** Windows 上 agent 内的 Python 没有代理环境变量时会**回落读注册表系统代理**（实测 `getproxies()` 返回 Clash 的 `127.0.0.1:7897`，并按 ProxyOverride 豁免回环）；显式 `agent_servers.<id>.env` 注入的价值是代理/NO_PROXY/CA 三者确定、不随注册表状态漂移。首案对照：无 env 的旧进程登录必败，带 env 的新进程一次通过。
3. **改 env 配置不影响已在运行的 agent 进程。** Zed 复用后台 agent 进程，新建线程、开关 agent 面板都不触发重启；改完必须杀进程（或完全退出 Zed）。

## 总原则（每次使用先读）

1. **改 settings.json 前先备份**（`Copy-Item` 一份 `.bak`）。
2. **诊断从 Zed.log 的 agent stderr 开始**，不要凭界面现象猜（任务 A 第一步）。
3. **不要让用户反复点登录来验证修复**——每轮都要人工过浏览器，还拿不到被 agent 吞掉的底层异常；用任务 C 的 stdio 探针一次拿确切结果。
4. **不要把 `%TEMP%\_MEI*` 下的任何路径写进持久配置**——PyInstaller 每次启动随机解包、退出即清；CA 证书要拷到固定目录。
5. **归因要诚实**：本 skill 首案未捕获 agent 吞掉的底层异常，代理与 CA 是组合修复、无法归因单项。遇到新案例先用探针 `--debug` 输出抓底层异常，再下结论。

## 环境路径（按机器解析，不要硬编码）

| 项 | 路径 |
|---|---|
| Zed 用户配置 | `%APPDATA%\Zed\settings.json`（`agent_servers` 段） |
| registry agent | `%LOCALAPPDATA%\Zed\external_agents\registry\<agent>\v_*\` |
| Zed 日志 | `%LOCALAPPDATA%\Zed\logs\Zed.log`（agent stderr 全在 `agent_servers::acp` 行里） |
| Antigravity 凭据 | `~\.gemini\antigravity-acp\acp_token.json`（登录成功才存在） |
| Antigravity 解包源码 | `%TEMP%\_MEI*\google3\cloud\developer_experience\antigravity_extensions\acp_server\` |

---

## 任务 A：诊断登录失败（浏览器成功但 Zed 没登录态）

第一步永远是看日志：

```powershell
rg -n "agent_servers::acp" "$env:LOCALAPPDATA\Zed\logs\Zed.log" | Select-Object -Last 30
```

**本问题的指纹**（四行连环出现即坐实）：

```
Authenticate called with method_id='oauth-personal'
Credentials missing or invalid. Launching browser login flow...
Signing out after onboarding_failed: stored credentials are unusable.
Cleared credential file at ...acp_token.json
```

**按日志分流**：

| 日志特征 | 根因方向 | 走向 |
|---|---|---|
| `onboarding_failed`，无更多细节（最常见） | 代理/CA 没注入 agent 进程 | 任务 B |
| 明确 `SSL: CERTIFICATE_VERIFY_FAILED` | CA bundle 缺失或代理 MITM | 任务 B（MITM 时 CA 用代理自己的根证书） |
| `Timed out waiting for the authentication flow` | OAuth 回环被代理劫持（NO_PROXY 缺 localhost）或用户没完成授权 | 任务 B 的 NO_PROXY 要点 |
| 探针/日志见 403 `SUBSCRIPTION_REQUIRED` / `#3501` | 账号无资格（非网络问题） | 换账号或改用 `gemini-api-key`（env `GEMINI_API_KEY`） |
| `ProxyError: Unable to connect to proxy, SSLError(SSLEOFError)` | Clash 节点级瞬时抖动（负载均衡组里的坏节点；2026-09-21 实测 3 分钟自愈） | curl 经同一代理对照（healthy 为 400）、复跑探针、换节点 |

**查当前系统代理**（修复时沿用这个端口）：

```powershell
Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' | Select-Object ProxyEnable,ProxyServer
Get-NetTCPConnection -LocalPort 7897 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { (Get-Process -Id $_.OwningProcess).ProcessName }
# verge-mihomo = Clash Verge；7897 是其混合代理端口
```

**确认 agent 进程是否吃到新 env**（改配置后必查）：

```powershell
Get-Process agy_acp_server -ErrorAction SilentlyContinue | Select-Object Id,StartTime
(Get-Item "$env:APPDATA\Zed\settings.json").LastWriteTime
# 任何 StartTime 早于配置修改时间 ⇒ 旧进程，env 必然没生效，走任务 B 第 4 步
```

确需看进程真实环境块（比 StartTime 更直接的证据）：ctypes 读 PEB 的代码在 `references/antigravity-internals.md`。

---

## 任务 B：注入代理 + CA（修复）

1. **备份** settings.json。
2. **CA bundle 持久化**到 `%APPDATA%\Zed\certs\antigravity-ca.pem`（不要引用 _MEI 临时路径）：
   ```powershell
   $mei = Get-ChildItem $env:TEMP -Directory -Filter '_MEI*' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
   New-Item -ItemType Directory -Force "$env:APPDATA\Zed\certs" | Out-Null
   Copy-Item "$($mei.FullName)\google3\third_party\py\certifi\cacert.pem" "$env:APPDATA\Zed\certs\antigravity-ca.pem"
   ```
   来源二选一：agent 自带 certifi（上面命令，需 agent 至少跑过一次）；或系统 Python 的 `python -c "import certifi;print(certifi.where())"`。**若代理做 TLS MITM，改用代理自己的根证书。**
3. **settings.json 的 `agent_servers."antigravity-acp"` 加 env**（保留原有字段如 `type`；路径用正斜杠；端口换成任务 A 查到的实际代理）：
   ```json
   "antigravity-acp": {
     "type": "registry",
     "env": {
       "HTTP_PROXY": "http://127.0.0.1:7897",
       "HTTPS_PROXY": "http://127.0.0.1:7897",
       "NO_PROXY": "localhost,127.0.0.1,::1",
       "REQUESTS_CA_BUNDLE": "C:/Users/<user>/AppData/Roaming/Zed/certs/antigravity-ca.pem",
       "SSL_CERT_FILE": "C:/Users/<user>/AppData/Roaming/Zed/certs/antigravity-ca.pem"
     }
   }
   ```
   要点：**NO_PROXY 必须含 localhost/127.0.0.1**——OAuth 回调落在本机回环端口，被代理吃掉就是登录转圈到 timeout。
4. **杀旧 agent 进程**（Zed 不会自己重启它们；只杀 registry 路径下的，防误杀）：
   ```powershell
   $root = [IO.Path]::GetFullPath("$env:LOCALAPPDATA\Zed\external_agents\registry\antigravity-acp") + '\'
   Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'agy_acp_server.exe' -and $_.ExecutablePath -and ([IO.Path]::GetFullPath($_.ExecutablePath)).StartsWith($root, [StringComparison]::OrdinalIgnoreCase) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
   ```
5. 走任务 C 验证，通过后让用户**新建 Antigravity 线程**（Zed 会自动带新 env 重生 agent 进程）。

---

## 任务 C：stdio 探针验证（不进 Zed UI，一次拿确切结果）

`scripts/acp-auth-probe.py`：用 settings.json 里 `agent_servers.<agent>.env` 的环境直接启动官方 agent exe，走 ACP JSON-RPC 完整登录链，日志脱敏后实时打印：

```powershell
python scripts/acp-auth-probe.py antigravity-acp            # 完整链：initialize → authenticate（自动开浏览器）→ session/new
python scripts/acp-auth-probe.py antigravity-acp --cached   # 验证已存凭据跨进程可用（不开浏览器）
```

**判读**：

- `POST /token ... 200` + `AUTHENTICATE_OK` + `SESSION_CREATED_OK` + `AVAILABLE_MODEL_COUNT>0` ⇒ 登录链路通（首案实测 11 个模型）。
- 再跑 `--cached` 也 OK ⇒ 凭据已持久，Zed 里直接可用，无需再登录。
- `AUTH_FAILED` / `SESSION_FAILED` 会打印 agent 返回的 code/message/data；`LOG:` 行里的 SSL/Traceback 就是 Zed 界面一直隐藏的底层异常。
- 探针通用：换 agent 名可探任何 registry ACP agent（env 从对应 `agent_servers.<名>.env` 读）。

---

## 通用机制（适用所有 Zed ACP agent）

- **`agent_servers.<id>.env` 是给 ACP agent 配代理/证书/密钥的唯一正规入口**（antigravity-acp、codex-acp、claude-acp、opencode registry 同理）。Zed 启动 agent 进程时注入这些环境变量。
- **进程复用**：Zed 复用已运行的 agent 进程；改 env、新建线程、开关 agent 面板都不触发重启。改完必须杀进程或完全退出 Zed。
- **ACP JSON-RPC over stdio**：所有 ACP agent 都能用 initialize / authenticate / session/new 探针模式调试。认证方法 id 从 initialize 应答的 `authMethods` 里拿（如 `oauth-personal` / `oauth-business` / `gemini-api-key` / `agent-platform`）。
- **系统代理的注册表回落**：agent 内 Python 无代理环境变量时，urllib 会读 WinINET 注册表拿系统代理（含 ProxyOverride 回环豁免）。但回落形态不可控（无显式 CA、随注册表漂移），推荐仍用 env 显式注入。

## 常见坑速查

| 症状 | 原因/处理 |
|---|---|
| 浏览器显示认证成功，Zed 还是登录按钮 | 成功页先于 token 兑换；日志找 `onboarding_failed`，按任务 A 分流 |
| 改了 `agent_servers.*.env` 没生效 | 旧 agent 进程复用；对比 StartTime 与配置 mtime，杀进程（任务 B 第 4 步） |
| 登录一直转圈直到 timeout | NO_PROXY 没排除 127.0.0.1，OAuth 回环被代理吃掉 |
| Clash 开着，agent/探针却报 ProxyError（SSLEOF 等） | 节点级瞬时抖动（负载均衡组坏节点）；curl 经同代理对照、复跑探针、换节点或直连 |
| `CERTIFICATE_VERIFY_FAILED` | REQUESTS_CA_BUNDLE/SSL_CERT_FILE 指向有效 bundle；MITM 代理用代理根证书 |
| 网络/证书都正常仍 `onboarding_failed` | 账号资格问题（403 `#3501` SUBSCRIPTION_REQUIRED）；换账号或 gemini-api-key |
| 昨天配好的 CA 今天又失效 | 引用了 `_MEI*` 临时路径；CA 拷到 `%APPDATA%\Zed\certs` 持久化 |
| 杀了进程 Zed 里还是老行为 | Zed 自身状态也可能陈旧；完全退出 Zed 重开 |

## 深入资料

- `references/antigravity-internals.md` —— Antigravity ACP server 源码级机制：OAuth/onboarding 完整链路、失败即清凭据的策略、PyInstaller 打包与 _MEI 布局、bundled requests 的 CA/代理行为、进程环境块检查代码、外部同类案例链接。
