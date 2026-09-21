# Antigravity ACP Server 内部机制（源码级）

版本锚点：antigravity-acp **v_1.1.1**（`agy_acp_server_20260818` 一代），Zed 1.20.2，2026-09-21 实测。升级后以 `%TEMP%\_MEI*` 解包源码为准重新核对。

## 目录

1. [打包与解包布局](#1-打包与解包布局)
2. [OAuth 登录链路（成功页为什么先出现）](#2-oauth-登录链路)
3. [onboarding 与"失败即清凭据"策略](#3-onboarding-与失败即清凭据策略)
4. [凭据与配置文件](#4-凭据与配置文件)
5. [认证方法](#5-认证方法)
6. [bundled requests/urllib3 的 CA 与代理行为](#6-bundled-requestsurllib3-的-ca-与代理行为)
7. [检查任意进程的环境变量（ctypes 读 PEB）](#7-检查任意进程的环境变量)
8. [外部同类案例](#8-外部同类案例)
9. [首案时间线与诚实边界](#9-首案时间线与诚实边界)

---

## 1. 打包与解包布局

- `agy_acp_server.exe`（约 430MB）+ `localharness_external.exe`（约 130MB），PyInstaller **onefile**、内嵌 Python 3.10。
- 每次启动解包到 `%TEMP%\_MEI<随机>\`，退出即清——**Python 源码可直接读**，这是排障的最大信息源：
  - 服务主体：`google3\cloud\developer_experience\antigravity_extensions\acp_server\server.py`
  - OAuth：同目录 `oauth\credential_manager.py`、`oauth\credential_store.py`
  - onboarding：`ccpa_connection\onboard.py`、`ccpa_connection\oauth_manager.py`
  - 本地代理注入：`ccpa_connection\proxy_server.py`（运行时还会起一个 127.0.0.1 随机端口的 credentials-injection 反代，session 流量走它）
- 运行中的每个实例对应一个 `_MEI*` 目录（多实例并存时按 LastWriteTime 区分）。
- Zed 侧安装位置：`%LOCALAPPDATA%\Zed\external_agents\registry\antigravity-acp\v_1.1.1_<h>_<h>\`（目录名推算见 sh-zed-opencode-setup 任务 A）。

## 2. OAuth 登录链路

`credential_manager.py` 关键事实（按执行顺序）：

1. 构造 `InstalledAppFlow`（PKCE S256），scopes = `cloud-platform` + `userinfo.email` + `aicode`，`access_type=offline` + `prompt=consent`（强制每次返回 refresh_token）。
2. 在 `127.0.0.1:<随机端口>` 起一次性 WSGI 回环服务器（`allow_reuse_address=False`），redirect_uri 即该地址。
3. 打开浏览器；**回环收到 Google 302 回调、URL 带.code 且无 error 时，立即渲染本地 "Authentication successful" 成功页**——此刻 token 还没兑换！
4. 之后才 `flow.fetch_token()`（POST `oauth2.googleapis.com/token`）。
5. `get_access_token()` → `_resolve_backend(access_token)` → 进入 onboarding（见下节）。

推论：浏览器成功页只证明"用户同意了授权"，兑换与 onboarding 失败时 Zed 界面永远只看到回到登录按钮。登录 URL 也会打到 agent stderr（`Open the following link ...`），Zed.log 里可见。

## 3. onboarding 与"失败即清凭据"策略

`ccpa_connection\onboard.py` + `oauth_manager.py` + `server.py`：

- onboarding = 调 CCPA（`cloudcode-pa.googleapis.com`）`loadCodeAssist` 查用户 tier；无 tier 则自动 `onboardUser` 到 free-tier 并轮询 operation；最终解析出 Google Cloud project ID 与 endpoint，连同凭据写入 token 文件。
- 失败策略集中在 `server.py::_sign_out_after_identity_failure`：token 兑换后任何 `ValueError`（onboarding 失败/解析不到 project）→ 清 `acp_token.json` + `acp_business_token.json` → 登出。日志即指纹 `Signing out after onboarding_failed`。
- `IneligibleUserError`（终端失败）同样清凭据；对应服务端 403 `SUBSCRIPTION_REQUIRED` / `#3501`。
- 设计意图（源码注释）：缓存 token 还有效时会一直复用，不清凭据用户就永远换不了账号——所以"身份不可用"一律登出。副作用：网络层失败也被当成身份失败，凭据反复被清。

## 4. 凭据与配置文件

| 文件 | 说明 |
|---|---|
| `~\.gemini\antigravity-acp\acp_token.json` | 个人 OAuth 凭据（client_id/secret/refresh_token/token_uri/scopes/project_id）；登录成功才存在 |
| `~\.gemini\antigravity-acp\acp_business_token.json` | Gemini Enterprise（oauth-business）凭据 |
| `~\.gemini\antigravity-acp\settings.json` | agent 设置（如 `auth.type`）；首案登录成功后同时出现 |

`credential_store.py` 是"keychain 优先、安全文件兜底"的混合存储；Windows 上落上面的 JSON 文件。`$GEMINI_HOME` 可整体搬迁这些路径（默认 `~\.gemini`，启动日志会打印解析结果）。

## 5. 认证方法

initialize 应答的 `authMethods`（id → 要求）：

| id | 说明 | 前置条件 |
|---|---|---|
| `oauth-personal` | Google 个人账号 OAuth | 本文链路 |
| `oauth-business` | Gemini Enterprise | project/location 配置（settings.json gcp 段），license 解析 |
| `gemini-api-key` | Gemini Developer API key | 环境变量 **`GEMINI_API_KEY`**（必须在 agent 进程环境里，可用 `agent_servers.*.env` 注入） |
| `agent-platform` | Vertex/Agent Platform ADC 或 key | `GOOGLE_API_KEY`/project+location 等 |

排障时 oauth-personal 网络问题排除后，`gemini-api-key` 是最快的旁路验证（论坛同类案例也用它绕过 onboarding 资格问题）。

## 6. bundled requests/urllib3 的 CA 与代理行为

Antigravity 打包的是 **Google 内部 fork 的 requests/urllib3**（`google3\third_party\py\` 下），与 PyPI 版行为有差异：

- `adapters.py::cert_verify`：`verify=True` 时走 `conn.ca_cert_data = DEFAULT_CA_BUNDLE`（即 bundled certifi 的 PEM 文本，`certifi.core.where()` 指向 `google3/third_party/py/certifi/cacert.pem`）；**显式传 CA 路径**（`REQUESTS_CA_BUNDLE` 会让 session 层把 verify 解析成路径）时走 `ca_certs=<路径>`——两条路都有效，但语义不同。
- 代理：requests 优先读**环境变量**（`HTTP_PROXY/HTTPS_PROXY/NO_PROXY`）；**Windows 上无 env 时 urllib 会回落读 WinINET 注册表**（`getproxies()` → `getproxies_registry()`，含 ProxyOverride 的回环豁免；2026-09-21 23:14 实测：清空 env 后仍返回 `127.0.0.1:7897`）。回落形态无显式 CA、随注册表漂移，所以 env 显式注入仍是推荐形态。`NO_PROXY` 决定回环 `127.0.0.1` 是否被代理劫持。
- 实测（本机）：用 bundled 库 + 显式 CA 路径 + 代理 env，POST `oauth2.googleapis.com/token` 返回 400（缺 code，预期）；说明连通与校验链路完好。

## 7. 检查任意进程的环境变量

判断"改的 env 到底有没有进 agent 进程"的最直接证据（PowerShell + Python，读目标进程 PEB→ProcessParameters→Environment，UTF-16LE）：

```python
import ctypes, ctypes.wintypes as w
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
nt = ctypes.WinDLL('ntdll')

class Basic(ctypes.Structure):
    _fields_ = [('Reserved1', w.LPVOID), ('Peb', w.LPVOID),
                ('Reserved2', w.LPVOID * 2), ('Pid', ctypes.c_size_t),
                ('Reserved3', w.LPVOID)]

def read_proc(h, addr, n):
    b = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
    if not kernel.ReadProcessMemory(h, addr, b, n, ctypes.byref(got)):
        raise ctypes.WinError(ctypes.get_last_error())
    return b.raw[:got.value]

pid = <目标PID>
h = kernel.OpenProcess(0x410, False, pid)  # PROCESS_QUERY_INFORMATION|VM_READ
b = Basic(); size = w.ULONG()
nt.NtQueryInformationProcess(h, 0, ctypes.byref(b), ctypes.sizeof(b), ctypes.byref(size))
params = int.from_bytes(read_proc(h, b.Peb + 0x20, 8), 'little')   # x64 ProcessParameters
env = int.from_bytes(read_proc(h, params + 0x80, 8), 'little')     # Environment 指针
raw = bytearray()
for pos in range(0, 131072, 2):
    raw.extend(read_proc(h, env + pos, 2))
    if raw[-4:] == b'\0\0\0\0':
        break
entries = raw.decode('utf-16-le').split('\0')
print([e for e in entries if any(k in e.upper() for k in
      ('HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY', 'REQUESTS_CA_BUNDLE', 'SSL_CERT_FILE'))])
```

日常用轻量替代：`Get-Process <exe> | Select Id,StartTime` 对比 settings.json 的 LastWriteTime——进程比配置早就说明 env 没吃到。首案即靠它发现 Zed 复用了 22:12 的旧进程、新 env 从未生效。

## 8. 外部同类案例

- Google AI 开发者论坛 topic **179763**（antigravity-acp 502 Bad Gateway）：Zed/Linux 用户 `oauth-personal` 全挂，`gemini-api-key` 正常；根因含 `SSL: CERTIFICATE_VERIFY_FAILED`，**Linux workaround 是 `export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt`**；另见 403 `#3501 SUBSCRIPTION_REQUIRED`（账号无 license）。
- JetBrains YouTrack **LLM-30919**：同插件在 JetBrains 侧的证书/登录同类问题。
- 共性：这不是 Zed 独有 bug，是"打包 Python + 本地代理/CA"环境类问题；Windows 上多了"系统代理不进 env"和"进程复用"两层。

## 9. 首案时间线与诚实边界

- 症状：浏览器反复显示认证成功，Zed 始终回到登录按钮；Zed.log 每次登录后 `onboarding_failed` + 清凭据，共 5+ 轮。
- 排查：读 `_MEI` 源码确认成功页先于兑换；网络探测（默认 CA / 显式 CA / 代理组合）都通；据此注入代理+CA env 并杀旧进程后，官方 exe 探针一次通过（token 200、11 模型、`--cached` 持久）。
- **诚实边界：agent 把底层异常吞成了统一文案，首案未能抓到原始异常，因此"代理"与"CA"是组合修复、无法归因单项**（最可能是代理缺失导致直连 Google 失败）。新案例应先用 `scripts/acp-auth-probe.py`（自动加 `--debug`）抓 `LOG:` 行里的原始异常再定论。
- 后记（2026-09-21 23:11–23:14，探针脚本首跑）：恰好撞上 `ProxyError: Unable to connect to proxy, SSLError(SSLEOFError)`（token 刷新失败，完整栈被探针完整打出）——3 分钟后同机 curl 经同一代理与探针复跑全部正常。两点结论：① Clash 负载均衡组存在**坏节点级瞬时抖动**，此类失败重试即恢复，不要误判为配置回归；② **urllib 注册表回落实锤**（当次探针 env 未注入仍走了代理）。另：Zed settings.json 是 JSONC，脚本解析必须剥注释和尾逗号。
