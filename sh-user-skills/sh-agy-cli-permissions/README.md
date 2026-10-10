---
name: sh-agy-cli-permissions
description: 配置：Antigravity CLI 模式辨析与免批 YOLO、Tool Permission 及规则表配置。点名使用
version: 1.0.1
created: 2026-10-10
updated: 2026-10-10
---

# Antigravity CLI 模式辨析与权限配置 (YOLO SOP)

> 本技能解决在 Antigravity CLI (`agy`) 中“为什么没有 YOLO 模式”、“为什么模式栏只有 plan 和 accept”、“`/permissions` 为什么全是 0”、“`/config` 面板怎么配置”、“如何实现无人值守全自动执行”等问题。

---

## 一、核心概念：执行模式与权限策略分离

Antigravity CLI 将智能体的运作解耦为两个独立层级：

| 层级 | 控制对象 | 可选值 | 说明 |
| :--- | :--- | :--- | :--- |
| **Agent Mode<br>（执行模式）** | 代码生成与文件修改策略 | • `default` (标准)<br>• `accept-edits` (界面简写为 accept)<br>• `plan` (只读规划) | 通过 `Shift + Tab` 或 `/config`（旧版兼容 `/settings`）切换。<br>`accept-edits` 只代表**自动合入代码 diff**，终端命令等危险工具**依然会弹窗确认**。 |
| **Permission Policy<br>（权限策略）** | 工具调用与系统命令审批 | • `request-review` (默认询问)<br>• `always-proceed` (全部自动放行)<br>• `proceed-in-sandbox` (沙箱自动放行) | 决定执行 Shell 命令、读写非工作区、访问网络时是否暂停等待人工审批。 |

> **关键认知**：社区常说的 **“YOLO 模式”并不是一种 Agent Mode，而是一种 Permission Policy**（全自动免审）。因此在状态栏的模式切换列表里永远找不到名为 `yolo` 的模式。

---

## 二、开启“真·YOLO 模式”的三种途径

### 途径 1：启动参数直接开启（最纯正推荐）

启动 CLI 时加上 `--dangerously-skip-permissions`：

```bash
# 启动即开启全自动免审（搭配 accept-edits 获得纯正 YOLO 体验）
agy --dangerously-skip-permissions --mode accept-edits
```

#### Windows PowerShell 快捷别名（一劳永逸）
在 PowerShell 中运行以下命令，为当前用户配置快捷命令 `agy-yolo`：

```powershell
if (!(Test-Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force }
@'

# Antigravity CLI YOLO Mode
function agy-yolo {
    & "C:\Users\29580\.gemini\bin\agy.exe" --dangerously-skip-permissions --mode accept-edits @args
}
'@ | Add-Content -Path $PROFILE -Encoding utf8
```
配置后新开终端直接输入 `agy-yolo` 即可免确认进入工作。

---

### 途径 2：在运行中的会话内配置（免重启）

如果已经处于 `agy` 交互界面中，可通过配置面板开启（最新版本命令为 `/config`，兼容 `/settings`）：

1. 在输入框输入 `/config`（或 `/settings`）并回车；
2. **解除命令确认（关键）**：
   - 方向键移动到 **`Tool Permission`**（默认显示 `request-review`）；
   - 回车展开，选择 **`always-proceed`** 并确认；
3. **解除代码确认**：
   - 移到顶部的 **`Agent Mode`**；
   - 切换为 **`accept-edits`**；
4. 按 **`Esc`** 保存并返回会话。

---

### 途径 3：会话内遇到弹窗时临时放行

当 CLI 在执行某项敏感工具（如 `run_command`）暂停等待确认时：
- 选择 **`Always allow this tool for this session`**（当前会话全部允许此工具）；
- 选定后当前会话内该类工具将不再反复弹窗。

---

## 三、`/permissions` 规则表管理与配置

在会话中输入 `/permissions` 会打开细粒度规则过滤界面：
```text
Permissions - Global
  allowlist (0)    denylist (0)    asklist (0)    (←/→ to switch)
No allowlist rules.
Keyboard: ↑/↓ Navigate  ←/→ Switch View  a Add rule  e Edit rule  d/Delete rule
```

### 1. 为什么这里初始全是 `(0)`？
`/permissions` 是**细粒度白/黑名单规则表（类似防火墙 ACL）**，而非全局 YOLO 开关：
- **`allowlist`（白名单）**：明确允许某些安全命令免审（例如仅允许 `git status`、`npm test`）；
- **`denylist`（黑名单）**：明确禁止执行的敏感命令；
- **`asklist`（询问表）**：强制要求每次人工确认的危险操作。
默认未配置任何规则时即显示为 `(0)`。

### 2. 常用操作按键
- **`← / →`**：在 `allowlist`、`denylist`、`asklist` 之间切换视图；
- **`a`**：添加一条规则（支持按工具名称、命令前缀或 pattern 过滤）；
- **`e`**：编辑光标所在规则；
- **`d` 或 `Delete`**：删除光标所在规则。

---

## 四、排错与现象速查

| 现象 / 疑问 | 根因分析 | 解决措施 |
| :--- | :--- | :--- |
| **Shift+Tab 只有 plan 和 accept** | 状态栏切的是 Agent Mode（编辑模式），不是权限模式 | 接受编辑选 `accept`，命令免审通过 `--dangerously-skip-permissions` 或 `/config` 的 `Tool Permission` 解决 |
| **选了 accept-edits 依然弹窗** | `accept-edits` 只放行文件修改，不放行 Shell 命令 | 见本文“途径 1”或“途径 2”，将 `Tool Permission` 设为 `always-proceed` |
| **打开 /permissions 全是 0** | 这是精细化 ACL 过滤表，不是全局策略开关 | 如需全局 YOLO 无需在此逐条添加，直接在 `/config` 切换全局策略即可 |
| **命令用 /config 还是 /settings** | 最新版本主推 `/config`，`/settings` 为历史别名 | 推荐在交互输入框直接使用 `/config`，两者呼出相同配置界面 |
| **需要跨工作区读写文件被拦截** | `Non-Workspace Access` 默认处于 `off` | 在 `/config` 中将 `Non-Workspace Access` 设置为 `on` |
