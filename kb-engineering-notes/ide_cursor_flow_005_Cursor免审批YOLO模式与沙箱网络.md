---
name: kb-cursor-yolo-sandbox
description: Cursor Agent 免审批（YOLO / Run Everything）三档 Run Mode 的差异、`permissions.json` 与 `sandbox.json` 的分工（"跑不跑" vs "能碰什么"）、开了自动仍弹窗的硬保护根因，以及沙箱网络白名单写法。当想减少批准弹窗、限制 YOLO 下的网络访问、或疑惑"为什么开了免审批还弹"时查阅本条目。
---

# 05-Cursor免审批YOLO模式与沙箱网络配置指南

## 一、现象与诉求直击

Cursor Agent 默认每个终端命令都要弹批准框，想开"YOLO 模式"让它全自动跑：

- 入口 `Settings > Agents > Approvals & Execution > Run Mode` 有三档：`Auto-review` / `Allowlist` / `Run Everything`。
- 切到 `Run Everything` 后截图显示：`All commands will run without approval, classification or sandboxing.`——即零弹窗、无分类器、无沙箱。
- 追加诉求：YOLO 状态下"访问网络是否可以修改"？

## 二、底层机制剖析

1. **Run Mode 只管"跑不跑"，不管"能碰什么"**：`permissions.json` 决定自动跑还是送审；`sandbox.json` 决定沙箱内能访问的网络域名与文件路径。两者分工不同（官方原话）。
2. **沙箱是叠加层**：只对 shell 命令生效，控制"在哪里跑"；Run Mode 控制"要不要过分类器"。`Run Everything` 直接 bypass 沙箱，所以此时配 `sandbox.json` 的网络策略**不生效**，网络全开。
3. **硬保护不受 Run Mode 控制**：删文件（含 `rm`）、工作区外创建/改/删文件、Browser 工具调用，任何模式都可能弹窗——这是"开了自动还是弹"最常见的根因。
4. **Auto-review 判定链**：白名单直跑 → 其余 shell 尽量进沙箱 → 进不了沙箱（要完整网络/写区外/提权）转后端分类器（Gemini 3.5 Flash Lite，fallback Claude 4.5 Haiku）→ 分类器 block 但 agent 坚持则弹窗。分类器可在本机做只读 `ReadFile/Grep/Glob/ListDir`。
5. **Windows 特殊性**：沙箱实现官方只写了 macOS（Seatbelt）和 Linux（user namespace，沙箱内 `id -u`=0，用 `CURSOR_ORIG_UID/GID` 取真用户）；Windows/PowerShell 命令多半走不了沙箱，只能走分类器/弹窗，所以更爱弹。

## 三、标准操作 SOP

### A. 纯 YOLO（零弹窗，不管网络）

`Settings > Agents > Approvals & Execution > Run Mode = Run Everything`。无额外文件可配。

### B. YOLO 但限网（推荐折中）

1. Run Mode 退回 `Allowlist`（打开沙箱）或 `Auto-review`；
2. 写 `sandbox.json`（`~/.cursor/sandbox.json` 整机 / `<project>/.cursor/sandbox.json` 单项目优先可提交）；
3. 白名单制示例（只放行包管理器与 GitHub）：

```json
{ "networkPolicy": { "default": "deny", "allow": ["registry.npmjs.org", "pypi.org", "*.githubusercontent.com"] } }
```

4. 全放行示例：`{ "networkPolicy": { "default": "allow" } }`；
5. Settings 网络档选 `sandbox.json Only` 最严，默认 `sandbox.json + Defaults`（内置上百个包管理器域名）。

### C. Auto-review 微调（少弹窗但高风险留一手）

`~/.cursor/permissions.json` 或项目 `.cursor/permissions.json`（并存合并；团队有全局配置时本地被忽略）：

```json
{
  "autoRun": {
    "allow_instructions": [],
    "block_instructions": ["Every AWS CLI command should go through approval first."]
  }
}
```

偷懒写法：直接跟 Cursor agent 说"以后所有 AWS CLI 命令先过审批"，让它帮改。

### D. `networkPolicy` 语法速查

- `allow[]/deny[]` 支持精确域名、`*.example.com` 通配、CIDR；`deny` 永远优先；只匹配域名/IP，URL 路径忽略。
- 内网段（10/172.16/192.168/127、169.254.169.254、`::1/fe80/fc00`）默认防 SSRF blocked。
- 合并规则：allow 取并集（团队有 allowlist 则团队替换本地），deny 恒并集，`default` 取更严的 `deny`。

## 四、验证与防复发

- 验证 YOLO：Run Mode 显示 `Run Everything` 且描述含 `without approval, classification or sandboxing`。
- 验证限网生效：必须在非 `Run Everything` 模式下，进沙箱跑 `curl` 不在白名单的域名应失败。
- 排障清单：模式没切对 / 撞硬保护 / 命令进不了沙箱 / `Read Access=Workspace` 读区外要批 / MCP 需另配 allowlist / 团队策略覆盖个人 / 企业版禁 Claude 4.5 Haiku 会致 Auto-review 置灰（去 Team Settings → Models 放开，重开 Cursor）。
- 版本锚点：3.5 废弃 `Ask Every Time`；3.6 Auto-review 上线为推荐默认；3.23 新增 Read Access Workspace 模式；Cloud Agents 不用 Run Modes。

> 一手来源：`cursor.com/docs/agent/security/run-modes`（Pick a mode / How Auto-review works / Network access / Other protections / Changelog）、`cursor.com/docs/agent/security`（First-party/Third-party tool calls）、`cursor.com/docs/reference/sandbox`（networkPolicy/合并规则）、`cursor.com/docs/agent/terminal`。完整长文见 `docs/plans/49-cursor-yolo-mode-no-approval.md`。
