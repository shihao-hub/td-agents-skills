---
name: sh-uwp-proxy-loopback
description: 排障：Windows 代理下微软商店与 UWP 初始化失败/无法联网，CheckNetIsolation 回环豁免。点名使用
---

# Skill: sh-uwp-proxy-loopback（Windows 代理环境下 UWP / 微软商店网络排障）

沉淀自实操（Windows 11 / Windows 10，开启代理如 Clash 7897/7890 端口，Microsoft Store 启动报“出现错误，Microsoft Store初始化失败”）。核心原因：**Windows UWP 沙箱隔离机制默认拦截对 127.0.0.1 的本地回环访问**。

## 核心机制与结论

1. **UWP 回环隔离（AppContainer Loopback Restriction）**：
   - 普通 Win32 浏览器应用能直接走 `127.0.0.1:<port>` 代理。
   - UWP 应用（微软商店、Xbox、便签、邮件等）运行于独立沙箱，Windows 内核默认阻断其向本机回环（127.0.0.1）发送网络请求。
   - 开启系统代理后，UWP 应用网络请求全被拦截，表现为“无法联网”、“初始化失败”或“错误代码 0x800704cf / 0x80131500”。
2. **PowerShell 参数避坑（高频踩坑）**：
   - 直接在 PowerShell 中执行 `CheckNetIsolation.exe LoopbackExempt -a -n=xxx` 会报 `错误: 参数无效`。
   - **原因**：PowerShell 的参数解析器会将 `-n=value` 拆解破坏，导致 exe 无法识别参数。
   - **解法**：必须使用 `--%`（Stop-Parsing Token）或者通过 `cmd /c` 调用。

## 排查与修复 SOP

### 第一步：诊断当前代理与回环豁免状态

在终端（非管理员也可）快速排查：

```powershell
# 1. 检查是否启用了系统代理及端口
Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' | Select-Object ProxyEnable, ProxyServer

# 2. 查询当前已豁免的 AppContainer
CheckNetIsolation.exe LoopbackExempt -s
```

如果 `ProxyEnable = 1`，且豁免列表中没有目标 UWP 应用，即可确认为回环隔离问题。

### 第二步：精准解除隔离（需管理员权限）

打开 **管理员身份的 PowerShell / Windows 终端**：

#### 场景 A：仅修复 Microsoft Store（微软应用商店）
```powershell
# 必须带 --% 避免 PowerShell 破坏等号参数
CheckNetIsolation.exe LoopbackExempt -a --% -n=Microsoft.WindowsStore_8wekyb3d8bbwe
```
*(或者通过 cmd 调用：`cmd /c "CheckNetIsolation.exe LoopbackExempt -a -n=Microsoft.WindowsStore_8wekyb3d8bbwe"`)*

#### 场景 B：一键解除本机所有 UWP 应用回环限制（推荐，一劳永逸）
```powershell
foreach ($p in (Get-AppxPackage).PackageFamilyName) { CheckNetIsolation.exe LoopbackExempt -a --% -n=$p }
```

### 第三步：验证修复

1. 终端提示 `完成。` 即表示规则已写入注册表生效。
2. 重新验证豁免列表：
   ```powershell
   CheckNetIsolation.exe LoopbackExempt -s
   ```
3. 返回 Microsoft Store，点击界面中的 **“刷新页面”**，页面正常渲染即排障完成。

## 客户端原生方案（免命令行）

如果不想使用命令行，可在代理软件内配置：

| 方案 | 操作路径 | 原理 |
|---|---|---|
| **TUN 虚拟网卡模式** | Clash Verge / Mihomo: 开启 **TUN Mode** | 流量由虚拟网卡接管，底层绕过回环代理限制 |
| **UWP 回环工具 (Loopback)** | 客户端设置 -> 工具 -> **UWP Loopback** -> 勾选 Store -> Save | 客户端图形化批量调用 Windows 回环 API |
| **临时关闭代理** | 关闭系统代理 (System Proxy)，直连访问应用商店 | 临时应急方案 |

## 常用 UWP 应用 PackageFamilyName 速查

| 应用名称 | PackageFamilyName |
|---|---|
| Microsoft Store (应用商店) | `Microsoft.WindowsStore_8wekyb3d8bbwe` |
| Xbox App | `Microsoft.GamingApp_8wekyb3d8bbwe` |
| Windows Terminal | `Microsoft.WindowsTerminal_8wekyb3d8bbwe` |
| Sticky Notes (便签) | `Microsoft.MicrosoftStickyNotes_8wekyb3d8bbwe` |
| 邮件与日历 | `microsoft.windowscommunicationsapps_8wekyb3d8bbwe` |

> 任意已安装 UWP 应用的包名可通过命令查询：`Get-AppxPackage *关键词* | Select-Object Name, PackageFamilyName`
