---
name: sh-zed-acp-agent-env
description: 排障：IDE（Zed/IntelliJ IDEA）ACP 外部 agent（antigravity/codex/claude）登录失败、代理/CA 不生效、旧进程复用；附 stdio 认证探针。点名使用
---

# IDE（Zed / IntelliJ IDEA）ACP 外部 agent 环境注入与登录排障手册（Windows）

沉淀自 2026-09-21（Zed 1.20.2 + Clash Verge `127.0.0.1:7897`）与 2026-10-07（IntelliJ IDEA 2026.2 + Antigravity ACP v1.3.0）的登录排障实战。修复全程实证：token 兑换 200 → 会话创建 → 11 个模型 → 凭据跨进程持久。

## 核心反直觉事实（不踩坑前提）

1. **浏览器显示 "Authentication successful" ≠ 登录成功。**  
   Antigravity 的 OAuth 成功页由本地回环服务器在 code→token 兑换**之前**展示；之后还有 token 兑换（POST `oauth2.googleapis.com/token`）+ CCPA onboarding，任一步失败都会清凭据并登出（IDE 界面退回登录按钮或报 Internal error）。
2. **代理对 agent 的生效形态分宿主，不能想当然：**
   - **Zed 模式**：通过 `%APPDATA%\Zed\settings.json` 的 `agent_servers.<id>.env` 显式注入代理与 CA 证书。
   - **IntelliJ IDEA / JetBrains 模式**：IDEA 目前**未暴露** agent 的局部 env 配置项，直接继承宿主系统的全局/用户环境变量。当缺少变量时，agent 内部 Python 会回落读取 WinINET 注册表系统代理；而在遇到 Clash/Mihomo 的 HTTP 代理端口时，注册表回退会误将 HTTP 代理当成 SSL 代理发起 TLS 握手，触发 `ProxyError: SSLEOFError(8, 'EOF occurred in violation of protocol')`。**必须写入 Windows 用户级环境变量**（`HTTP_PROXY`、`HTTPS_PROXY` 协议头必须是 `http://`，且设置 `NO_PROXY` 与 CA bundle）。
3. **改配置不影响已在运行的 agent 进程。**  
   无论是 Zed 还是 IDEA，均会复用后台 agent 进程；改完配置必须彻底杀掉后台 agent 进程或退出重启 IDE。

## 总原则（每次使用先读）

1. **改 settings.json 前先备份**（`Copy-Item` 一份 `.bak`）。
2. **诊断从 IDE 日志的 agent stderr 开始**：
   - Zed: `%LOCALAPPDATA%\Zed\logs\Zed.log`（搜 `agent_servers::acp`）。
   - IDEA: `%LOCALAPPDATA%\JetBrains\IntelliJIdea<ver>\log\idea.log`（搜 `AcpServerProcessHandlerImpl` 或 `Max retries exceeded`）。
3. **不要让用户反复点登录来验证修复**——用本 skill 的 `scripts/acp-auth-probe.py` stdio 探针一次拿确切结果。
4. **不要把 `%TEMP%\_MEI*` 下的临时路径写进持久配置**——CA 证书必须拷到固定持久目录（如 `%APPDATA%\Zed\certs\antigravity-ca.pem`）。

## 环境路径（按机器解析）

| 项 | 路径 |
|---|---|
| Zed 用户配置 | `%APPDATA%\Zed\settings.json`（`agent_servers` 段） |
| Zed agent 目录 | `%LOCALAPPDATA%\Zed\external_agents\registry\<agent>\v_*\` |
| IDEA agent 目录 | `%LOCALAPPDATA%\JetBrains\IntelliJIdea<ver>\acp-agents\<agent>\<ver>\` |
| IDEA 运行日志 | `%LOCALAPPDATA%\JetBrains\IntelliJIdea<ver>\log\idea.log` |
| Antigravity 凭据 | `~\\.gemini\antigravity-acp\acp_token.json`（成功后各 IDE 共享） |

---

## 任务 A：诊断登录失败

1. **查日志特征**：
   - 若出现 `ProxyError: ('Unable to connect to proxy', SSLError(SSLEOFError(...)))`：典型 Windows 注册表回落或代理头错误，走任务 B。
   - 若出现 `onboarding_failed`：代理/CA 未注入或未排除 localhost，走任务 B。
   - 若出现 `CERTIFICATE_VERIFY_FAILED`：缺失有效 CA 证书 bundle，走任务 B 第 2 步。
2. **查系统代理**：
   ```powershell
   Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' | Select-Object ProxyEnable,ProxyServer
   # 确认监听端口（如 Clash 7897）
   ```

---

## 任务 B：注入代理 + CA（修复）

### 分支 1：针对 Zed
在 `%APPDATA%\Zed\settings.json` 中配置：
```json
"agent_servers": {
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
}
```

### 分支 2：针对 IntelliJ IDEA（JetBrains 全系列）
IDEA 不支持直接在配置里传 agent env，需配置系统用户级环境变量并重启 IDE：
```powershell
[System.Environment]::SetEnvironmentVariable('HTTP_PROXY', 'http://127.0.0.1:7897', 'User')
[System.Environment]::SetEnvironmentVariable('HTTPS_PROXY', 'http://127.0.0.1:7897', 'User')
[System.Environment]::SetEnvironmentVariable('NO_PROXY', 'localhost,127.0.0.1,::1', 'User')
[System.Environment]::SetEnvironmentVariable('REQUESTS_CA_BUNDLE', 'C:/Users/<user>/AppData/Roaming/Zed/certs/antigravity-ca.pem', 'User')
[System.Environment]::SetEnvironmentVariable('SSL_CERT_FILE', 'C:/Users/<user>/AppData/Roaming/Zed/certs/antigravity-ca.pem', 'User')
```
*要点：`HTTPS_PROXY` 的 scheme 必须为 `http://`，避免 Python 发起代理端自身 SSL 握手。*

### 清理旧进程
```powershell
Get-Process agy_acp_server, localharness_external -ErrorAction SilentlyContinue | Stop-Process -Force
```

---

## 任务 C：stdio 探针验证（免开 IDE）

使用 `scripts/acp-auth-probe.py` 直接对 binary 发送 ACP JSON-RPC 请求验证：

```powershell
# 验证 Zed 实例
python scripts/acp-auth-probe.py antigravity-acp --cached --ide zed

# 验证 IDEA 实例
python scripts/acp-auth-probe.py antigravity-acp --cached --ide idea
```

**判读**：  
看到 `HTTP: /token -> 200` + `SESSION_CREATED_OK AVAILABLE_MODEL_COUNT=11` + `PROBE_DONE success=True` 即证明链路完全恢复，进 IDE 可直接使用。
