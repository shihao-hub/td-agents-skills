---
name: sh-zed-acp-agent-env
description: 排障：IDE（Zed/IntelliJ IDEA）ACP 外部 agent（antigravity/codex/claude）登录失败、代理/CA 不生效、旧进程复用、子进程池累积吃内存；附 stdio 认证探针。点名使用
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
4. **agent 服务会自己攒出一堆子进程，且不会主动回收。**  
   `agy_acp_server.exe` 会按需 spawn `localharness_external.exe` 工作子进程，用完**不销毁**；实测单个 Zed 会话下累积到 **14 个**（合计 ~0.96GB 物理 / 1.81GB 私有，每个 300+ 线程、启动时间横跨 8 小时、20 秒 CPU 采样增量全为 0）。**这与“多开会话”无关**——Zed 侧只有一条 ACP 链。累积机制与回收纪律见「任务 D」。

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
# 【按树】一起结束：只杀 agy_acp_server 会把 N 个子进程留成孤儿（Windows 不级联杀子）
# 子进程池的累积机制与回收纪律见：任务 D
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

---

## 任务 D：agent 子进程池累积与回收（内存治理）

### 进程树真相（判据是父子关系，不是进程数量）

```
Zed.exe / IDEA
 └─ powershell.exe            ← IDE 借它拉起 ACP agent
     └─ agy_acp_server.exe    ← Antigravity ACP 服务本体（~200MB）
          └─ localharness_external.exe × N   ← 真正干活的工作子进程池
```

**关键认知**：`localharness_external.exe` 的多个实例**不是“多开了几个 agent”**，而是 **agent 服务自身按需 spawn 的常驻工作进程**。它们的命令行**完全相同**（无参数区分角色），启动时间分散在多次操作中，**用完不回收**。

### 实测规模（2026-10-10，Zed 单会话，8 小时内累积）

| 指标 | 实测值 |
|---|---|
| 进程数 | 14 |
| 单进程 | ~65 MB 物理 / ~130 MB 私有 / **300+ 线程** |
| 合计 | ~0.96 GB 物理 / 1.81 GB 私有 |
| 活跃度 | 20 秒 CPU 采样增量**全为 0**（全闲置，占着内存不干活） |
| 本体 exe | 145 MB 单体二进制（Go 风格，自带运行时与线程池） |

### 诊断命令

```powershell
# 1) 看池子规模与累计占用
Get-Process localharness_external -ErrorAction SilentlyContinue |
  Measure-Object WorkingSet64, PrivateMemorySize64 -Sum |
  Select-Object Count, @{n='WS_MB';e={[math]::Round($_.Sum/1MB,1)}}

# 2) 看父子链归属（确认它挂在谁下面，防误杀其他 agent）
Get-CimInstance Win32_Process -Filter "Name='localharness_external.exe' OR Name='agy_acp_server.exe'" |
  Select-Object ProcessId, ParentProcessId, Name, CreationDate,
    @{n='WS_MB';e={[math]::Round($_.WorkingSetSize/1MB,1)}} | Sort-Object CreationDate

# 3) 区分“活跃工作池”与“闲置累积”：隔 20 秒采两次 CPU
Get-Process localharness_external | Select-Object Id, CPU
# 20 秒后再采一次；增量基本为 0 ⇒ 闲置累积，可回收
```

### 回收纪律（Windows 杀父不级联杀子）

```powershell
# 必须【按树】一起结束：只杀 agy_acp_server 会把 N 个子进程留成孤儿继续占内存
Get-CimInstance Win32_Process -Filter "Name='agy_acp_server.exe' OR Name='localharness_external.exe'" |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

# 收尾复查：确认无残留
Get-Process localharness_external, agy_acp_server -ErrorAction SilentlyContinue | Select-Object Id, Name
```

> ⚠️ 会中止该 agent 当前正在跑的任务；只在空闲时执行，或直接重启 IDE 清零。

### 何时该回收

- 池子规模 **> 10 个**或合计 **> 0.5GB 物理**，且 20 秒 CPU 采样基本为 0；
- 机器物理内存吃紧时（配合 `sh-windows-memory-guard` 的提交内存归因一起看）；
- 它是**累积型**而非**泄漏型**——不必频繁处理，重启 IDE 即可清零。
