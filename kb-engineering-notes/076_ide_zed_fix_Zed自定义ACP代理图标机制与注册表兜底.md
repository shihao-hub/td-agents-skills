---
name: kb-zed-acp-custom-agent-icon
description: |
  Zed 自定义 ACP 代理（agent_servers 里 type: custom）无法配置图标：设置层无 icon 字段、注册时硬编码为 None，图标唯一来源是 ACP Registry。涵盖五处 UI 的图标解析差异（线程侧栏无兜底、线程头部与新建线程菜单有注册表兜底、工具栏无）、三条绕过路径及其代价，以及升级后按 SHA 自查当前版本行为的方法。
version: 1.0.0
created: 2026-10-19
updated: 2026-10-19
---

# ide_fix_076_Zed自定义ACP代理图标机制与注册表兜底

> **条目定位**：Type A 疑难排障型条目
> **结论版本锚点**：**验证于 Zed 1.24.3 / commit `2a857f5f2ec368745c1af5209d49836968fe75b8`**（2026-10-16）。Zed 迭代快，升级后请按「四、自查」重跑，不要沿用旧结论。
> **关联条目**：Zed 集成 Pi Coding Agent 的管道挂起与内存问题见 `074_agent_pi_fix_Zed集成PiCodingAgent双层管道难用与openma内存直载SOP.md`。

---

## 一、现象与诉求直击

### 典型现象
1. 在 Threads Sidebar 或线程标题处，自定义 ACP 代理显示一个通用的终端图标（`>_` 方框），而 Registry 安装的代理（Claude / Codex / Pi 等）显示各自的品牌 SVG；
2. 想在 `settings.json` 的 agent 配置里加一行 `"icon": "..."` 换掉它——**没有任何效果，也不报错**，图标纹丝不动；
3. 诉求：像 Registry 代理那样显示自己的图标。

### 期望与现实
期望：存在一个配置项或环境变量可以指定本地 SVG 路径。
现实：**该能力在当前版本不存在**，图标由 Zed 的 ACP Registry 缓存独占提供。

---

## 二、底层根因剖析

### 1. 设置层压根没有这个字段
`crates/settings_content/src/agent.rs` 中 `CustomAgentServerSettings::Custom` 的字段全集只有：
`command`、`args`、`env`、`default_mode`、`default_config_options`、`favorite_config_option_values`。
写进去的 `icon` 会被 serde **静默忽略**（不是报错），所以「加了没反应」。

### 2. 注册层硬编码 icon = None
`crates/project/src/agent_server_store.rs:361-374`，`Custom` 分支构造 `ExternalAgentEntry` 时后两个参数直接写死：

```rust
ExternalAgentEntry::new(
    Box::new(LocalCustomAgent { .. }),
    ExternalAgentSource::Custom,
    None,   // icon
    None,   // display_name
)
```

对比 `Registry` 分支（同文件 `:414`、`:437`）传入的是 `agent.metadata.icon_path.clone()`。**这是根因**：custom 代理在数据层就没有图标，UI 再怎么渲染也拿不到。

### 3. 图标唯一来源 = ACP Registry 本地缓存
| 环节 | 位置 |
|:---|:---|
| 索引 URL（**硬编码，无设置项可覆盖**） | `crates/project/src/agent_registry_store.rs:20` → `https://cdn.agentclientprotocol.com/registry/v1/latest/registry.json` |
| 索引中每条含 `icon` 字段 | 如 `"icon": "https://cdn.agentclientprotocol.com/.../pi-acp.svg"` |
| 图标下载与落盘 | 同文件 `:485-538`，落在 `%LOCALAPPDATA%\Zed\external_agents\registry\icons\<id>.svg`（仅当文件不存在才重新下载） |
| 索引缓存 | `%LOCALAPPDATA%\Zed\external_agents\registry\registry.json`（刷新节流 1 小时，`:21`） |

本机实测该目录已存在 42 个 SVG，含 `pi-acp.svg`——这就是 Registry 代理有图标的全部秘密。

### 4. 五处 UI 的解析差异（关键：兜底不一致）

| UI 位置 | 代码位置 | 解析链 | 自定义代理表现 |
|:---|:---|:---|:---|
| 线程侧栏 | `crates/sidebar/src/sidebar.rs:1435-1447` | `Agent::Custom => IconName::Terminal` + 只查 `agent_server_store.agent_icon()` | **永远是终端图标**（无 Registry 兜底） |
| 线程头部 | `crates/agent_ui/src/conversation_view.rs:1598-1609` | `agent_icon()` **`.or_else(按 id 查 AgentRegistryStore.icon_path())`** | **有兜底**，键名撞上 Registry id 就出图标 |
| 新建线程右键菜单 | `crates/agent_ui/src/agent_panel.rs:6022-6028` | 同上的 `.or_else(...)` 兜底 | **有兜底** |
| Agent 面板工具栏 | `crates/agent_ui/src/agent_panel.rs:5890-5902` | 只查 `agent_icon()`，无兜底 | **无图标** |
| 配置层 | `crates/settings_content/src/agent.rs` | 无 `icon` 字段 | 配置无效 |

兜底能生效的原因：`agent_servers` 的 **键名同时充当 Registry 查询 id**（`AgentId`），所以键名撞上 Registry 里已存在的 id 时，兜底分支就能查到对应 `icon_path`。

### 5. 协议层其实能带图标，但 Zed 不读
ACP `initialize` 响应的 `agentInfo` 在 schema 里确实含 `icons`（`Implementation.icons`，支持尺寸与 light/dark 主题）。但 Zed 侧只取 `name` / `version` 用于遥测与版本记录——`crates/agent_servers/src/acp.rs:921-932`，**没有把 `icons` 接到任何 UI**。所以「让 ACP 服务端自报图标」这条路在当前版本也是死的。

---

## 三、标准修复 SOP

### 方案 A：走 Registry 安装（图标全场景生效，但会换进程来源）
```json
{
  "agent_servers": {
    "pi-acp": { "type": "registry" }
  }
}
```
- 效果：侧栏 / 头部 / 菜单 / 工具栏**全部**显示 Registry 图标（`agent_server_store.rs:414-441` 带 `metadata.icon_path`）；
- 代价：Zed 会 `npm install <package>@<version> --save-exact` 到 `%LOCALAPPDATA%\Zed\external_agents\registry\npx\<id>`，**跑的是 Registry 声明的 npm 包**（见 `agent_server_store.rs:1364-1398`）。若你在跑本地 fork，此法会切回官方包，可能不是你想要的。

### 方案 B：保留本地命令，只把键名改成 Registry id（部分场景出图标）
```json
{
  "agent_servers": {
    "pi-acp": {
      "type": "custom",
      "command": "node",
      "args": ["C:/Users/<user>/.bun/install/global/node_modules/@openma/pi-acp/dist/bin.js"],
      "env": {}
    }
  }
}
```
- ✅ 生效：线程头部、新建线程右键菜单（走 Registry 兜底）；
- ❌ 不生效：线程侧栏、Agent 面板工具栏（那两处没有兜底，仍是终端图标）；
- 副作用：菜单里的显示名可能被 Registry 的 `name` 覆盖（如 `pi ACP`）。

### 方案 C：不可行路径归档（别再试）
1. **自建 Registry 源**：`REGISTRY_URL` 硬编码，无设置项、无环境变量可覆盖；
2. **替换 `icons\pi-acp.svg`**：只影响走 Registry 的代理自身，对 custom 的侧栏毫无作用；且索引刷新时因「文件已存在」不会重下，改动会残留（属于跨条目污染，不建议）；
3. **改 Zed 二进制 / 打补丁**：无官方支持，升级即失效，不进入常规方案。

### 想彻底解决
给上游提 FR：在 `CustomAgentServerSettings::Custom` 增加 `icon`（本地 SVG 路径）字段，并在 `agent_server_store.rs:361-374` 传入。这是唯一能既保留自定义命令、又拿到图标的干净路径。

---

## 四、验证与防复发闭环

### 验证
```powershell
# 1. 确认 Registry 图标缓存里有哪些 id（决定了键名能"蹭"到哪些图标）
Get-ChildItem "$env:LOCALAPPDATA\Zed\external_agents\registry\icons" -Name

# 2. 改配置后无需重启 Zed（自动侦测设置变更），新开/切换线程即可观察
#    侧栏图标 → 观察 Threads Sidebar 列表项
#    头部图标 → 观察线程标题左侧
```

### 防复发（版本漂移是最大风险）
1. **结论必须带锚点**：本条目所有行号仅对 Zed 1.24.3 / `2a857f5f` 成立。升级 Zed 后按第 2 条自查。
2. **自查命令**（按 SHA 精确取证的方法论见 `075_dev_core_flow_发行版二进制嵌SHA溯源与上游源码取证.md`）：
   ```powershell
   & "D:\Users\29580\AppData\Local\Programs\Zed\bin\Zed.exe" --version   # 取新 SHA
   # 用 075 的脚本按该 SHA 取回以下文件，确认字段与兜底链是否变化：
   #   crates/settings_content/src/agent.rs          → Custom 变体是否新增 icon
   #   crates/project/src/agent_server_store.rs      → Custom 分支 icon 是否仍为 None
   #   crates/sidebar/src/sidebar.rs                 → 侧栏是否补上 Registry 兜底
   ```
3. **判断标准**：若 `Custom` 变体出现 `icon` 字段、或侧栏 `resolve_agent_icon` 补上 Registry 兜底，则本条目结论失效，应更新而不是继续照抄。
