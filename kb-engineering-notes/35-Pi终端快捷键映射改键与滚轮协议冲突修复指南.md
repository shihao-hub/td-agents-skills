---
name: kb-pi-terminal-keybindings
description: Pi 终端快捷键改键、按键协议排障与鼠标滚轮误触命令历史冲突修复指南。
---

# Pi终端快捷键映射改键与滚轮协议冲突修复指南

# sh-pi-keybindings — pi 快捷键配置与终端协议排障

沉淀自 2026-10-06 实战：
1. 把 pi 的「粘贴图片」从 `alt+v` 改到 `shift+alt+v`。改完按下毫无反应——根因不在 pi 配置，而在 Windows Terminal 1.24 不支持扩展键盘协议，`Shift+Alt+V` 只被编码成无意义的 `ESC+V`。
2. 在 Cursor / Antigravity IDE 终端中鼠标向上滚，不仅没翻页反而把上次发送的消息填进输入框——根因在于系统 inbox ConPTY 吞掉 SGR 鼠标序列，触发 xterm.js 备用屏幕滚轮转译为上方向键。

本手册覆盖：pi 改键完整流程、按键/鼠标编码原理、终端支持矩阵、Windows Terminal 修复路径，以及 IDE 终端 ConPTY 滚轮修复。

## 三条核心判断（先读这个）

1. **"按了没反应"分三层：配置层 → 终端编码层 → 剪贴板层**。`/hotkeys` 里能看到新键 = 配置层没问题；配置正确但动作不触发，且组合键带 Shift+Alt / Ctrl+Shift = 几乎一定是终端没送出可识别的序列。先分层再动手，别反复改 keybindings.json。
2. **字母键的传统编码只够表达四种组合**：`ctrl+字母`（控制码）、`alt+字母`（ESC+小写）、`shift+字母`（大写）、`ctrl+alt+字母`（ESC+控制码）。`shift+alt+字母`、`ctrl+shift+字母`、`shift+enter` 这些必须靠扩展协议（Kitty CSI-u / xterm modifyOtherKeys）才能区分。
3. **pi 的 `keybindings.json` 是运行时加载的**：改完要 `/reload`（或重启 pi）；而终端键盘/鼠标协议只在 pi 启动时协商一次，升级或更换终端/驱动后要重启终端或 pi。

## 工作流

1. 改键：写 `~/.pi/agent/keybindings.json` → `/reload` → `/hotkeys` 确认
2. 验证：用 `scripts/verify-binding.mjs` 离线确认「这个字节序列会被哪个动作吃掉」
3. 分层判因：配置层（§一）/ 终端层（§二、§三）/ 剪贴板层（§四）/ 滚轮排障（§七）
4. 修终端层：Windows Terminal ≤ 1.24 用 sendInput 映射，或升级到 1.25+；IDE 终端开启 `windowsUseConptyDll`
5. 回归：按键或滚动滚轮，观察输入框与视口行为

## 一、pi 侧改键

配置文件为 `~/.pi/agent/keybindings.json`（Windows：`C:\Users\<用户>\.pi\agent\keybindings.json`；agent 目录可用环境变量 `PI_CODING_AGENT_DIR` 覆盖）：

```json
{
  "app.clipboard.pasteImage": "shift+alt+v",
  "app.session.tree": ["ctrl+shift+t", "alt+shift+t"],
  "tui.altScreen.pageUp": []
}
```

- 值 = 单个键字符串，或键数组（多个键都生效）；`[]` 清空该动作的所有按键（禁用）。
- 键格式 `modifier+key`：修饰键 `ctrl/shift/alt/super` 可叠加、顺序无关；键位支持 a-z、0-9、功能键与常用特殊键（`escape/enter/return/tab/space/backspace/delete/insert/home/end/pageUp/pageDown/up/down/left/right/f1-f12`）及符号。
- 常用动作 id（**完整列表直接读 pi 安装目录的 `docs/keybindings.md`**，比抄表可靠）：

| id | 用途 | Windows/WSL 默认 |
| :--- | :--- | :--- |
| `app.clipboard.pasteImage` | 粘贴图片/文件/文本 | `alt+v` |
| `app.message.followUp` | 排队追加消息 | `ctrl+q` |
| `app.message.dequeue` | 取回排队消息 | `alt+q` |
| `app.model.cycleBackward` | 上一个模型 | `alt+p` |
| `app.interrupt` | 中断 | `escape` |
| `app.editor.external` | 外部编辑器 | `ctrl+g` |
| `tui.input.newLine` | 输入换行 | `shift+enter` / `ctrl+j` |

> 不知道动作 id 时：运行中的 pi 里 `/hotkeys` 有中文面板可对照；或在 pi 安装目录读 `docs/keybindings.md`。

生效与确认：

1. `/reload` 重新加载 keybindings.json（重启 pi 等效）。
2. `/hotkeys` 查看当前实际绑定——这里显示的还是旧键，说明文件没被读到（路径错 / JSON 语法错 / 改完没 reload）。

## 二、终端层：为什么组合键送不达

传统 VT 编码靠「字节本身」猜修饰键，覆盖面很窄：

| 按键 | 传统编码发出的字节 | pi 能匹配的 id |
| :--- | :--- | :--- |
| `v` | `v` | `v` |
| `Shift+V` | `V` | `shift+v` |
| `Ctrl+V` | `0x16` | `ctrl+v` |
| `Alt+V` | `ESC` + `v` | `alt+v` |
| `Ctrl+Alt+V` | `ESC` + `0x16` | `ctrl+alt+v` |
| `Shift+Alt+V` | `ESC` + `V` | ❌ 无定义，无任何绑定能匹配 |
| `Ctrl+Shift+V` | `0x16`（Shift 丢失） | `ctrl+v`（与纯 Ctrl+V 无法区分） |

扩展协议把「键码 + 修饰键位图」分开报告，pi 都支持：

- **Kitty CSI-u**：`ESC[118;4u`（118 = 'v'，修饰值 4 = 1 + shift(1) + alt(2)）
- **xterm modifyOtherKeys**：`ESC[27;4;118~`

pi 启动时协商：请求 Kitty flags（disambiguate + event types + alternate keys）并查询；终端用 DA 应答而无 Kitty 应答时降级开启 modifyOtherKeys；两者都没有则纯传统编码。协商只发生在启动时。

终端支持矩阵：

| 终端 | 扩展协议 | 说明 |
| :--- | :---: | :--- |
| Windows Terminal ≥ 1.25 | ✅ Kitty | 1.25 起支持；≤ 1.24 完全不支持 |
| Kitty / WezTerm / Ghostty / iTerm2 | ✅ | 免配置 |
| VS Code 内置终端 ≥ 1.109.5 | ✅ | 默认开启 |
| tmux | 透传 | tmux 内的问题单看 pi 的 `docs/tmux.md` |
| xfce4-terminal / Terminator / IntelliJ 内置终端 | ❌ | 连 modified Enter 都难区分 |

判断本机 Windows Terminal 版本：

```powershell
Get-AppxPackage Microsoft.WindowsTerminal | Select-Object Name, Version
```

## 三、Windows Terminal ≤ 1.24 的修复：sendInput 映射

思路：不让 WT 猜，直接告诉它「按下这个组合键时，把 pi 认识的 CSI-u 字节原样送进去」。

1. `Ctrl+Shift+,` 打开 WT 的 settings.json，或编辑
   `%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json`
2. 在 `actions` 数组加一条（以 `shift+alt+v` 为例）：

```json
{
  "command": { "action": "sendInput", "input": "\u001b[118;4u" },
  "keys": "alt+shift+v"
}
```

3. 保存即热重载，无需重启 WT。**WT 会重写这份文件**：把动作拆成 `actions`（自动补 id，如 `User.sendInput.3D5D3200`）和旧式 `keybindings`（id ↔ keys 配对）两段，这是正常行为，不要手动合并回去。
4. 序列按目标键替换：`ESC[<键码>;<修饰值>u`，键码 = 字母小写 ASCII（v=118、b=98、f=102…），修饰值 = 1 + shift(1) + alt(2) + ctrl(4) + super(8)。该序列不依赖 Kitty 协商是否激活，pi 同样匹配。
5. 更彻底的替代：`winget upgrade Microsoft.WindowsTerminal` 升到 1.25+，升级后**重启 pi** 让协议重新协商；已有 sendInput 配置保留也不冲突。

## 四、剪贴板层：按键对了但没粘进来

pi 的粘贴顺序是 **文件路径 → 图片 → 文本**：剪贴板里是复制的文件时插入路径；是图片时存临时文件再插入路径；是文字时直接插入文字。所以「没看到图片」很多时候是剪贴板内容不是图片。

```bash
cd "$(npm root -g)/@earendil-works/pi-coding-agent"
node --input-type=module -e "import {readClipboardImage} from './dist/utils/clipboard-image.js'; const i = await readClipboardImage(); console.log(i ? i.mimeType + ' ' + i.bytes.length + 'B' : 'no image')"
```

Windows 上读图依赖 pi-tui 原生模块（`node_modules/@earendil-works/pi-tui/native/win32/prebuilds/win32-x64/win32-platform.node`）；返回 `no image` 说明剪贴板里确实没有图片，截图/复制图片后再试。

## 五、离线验证：这个序列会被谁吃掉

```bash
node <skill目录>/scripts/verify-binding.mjs list app.clipboard.pasteImage
node <skill目录>/scripts/verify-binding.mjs test shift+alt+v kitty:118:4   # 期望 true → app.clipboard.pasteImage
node <skill目录>/scripts/verify-binding.mjs test shift+alt+v alt:V         # 传统 ESC+V，期望 false 且“无任何动作匹配”
```

`test` 会同时给反向结果（该字节序列会被哪些动作匹配），是区分「配置写错」与「终端发错」最快的办法。脚本自动定位 pi 安装目录（可用 `PI_ROOT` 覆盖），读取当前生效的 keybindings.json。

## 六、避坑清单

- 改完不 `/reload`：`/hotkeys` 仍是旧键；重启 pi 可兜底。
- 传统终端里 `ESC+V`（Shift+Alt+V）**不匹配任何键**，这不是 keybindings.json 写错；带 `shift+alt` / `ctrl+shift` 的字母组合都同理。
- `super` 前缀依赖 Kitty 协议（`super+k` 等只在支持的终端有意义）。
- WT 的 `actions` 与旧 `keybindings` 段是同一份数据的两个视图，改完确认两处成对存在即可，不要重复定义同一组合键。
- 升级终端或换终端后要重启 pi，协议协商不会热更新；sendInput 方式则随时生效。
- 各平台默认键不同（如 `pasteImage`：Windows/WSL 是 `alt+v`，macOS/Linux 是 `ctrl+v`），跨机器同步配置时注意。

## 七、滚轮排障：终端鼠标向上滚变成“显示上次发送消息”

### 症状与排查表现
在 Cursor、Antigravity IDE 等 VS Code 衍生 IDE 的内置终端（PowerShell）中：
- 鼠标向上滚不仅没有滚动消息视口，反而输入框里调出了上一次发送的消息。
- 相同的 PowerShell 在 Zed 或新版 VS Code 内置终端中，向上滚可正常滚动视口，并显示 `↓ Jump to latest message · ctrl+end` 悬浮提示。

### 根因全链路解析
1. **备用屏幕激活**：pi 运行在全屏交互模式（`TuiAltScreen`）时进入备用屏幕缓冲区（`DECSET 1049`），并请求 SGR 鼠标捕获协议（`DECSET 1000/1006`）。
2. **ConPTY 拦截与吞噬**：Cursor 和 Antigravity IDE 默认 `"terminal.integrated.windowsUseConptyDll": false`，降级调用 Windows 系统旧版 `System32\conhost.exe`（inbox ConPTY）。系统 ConPTY 吞掉了应用发出的 SGR 鼠标序列，导致外层 `xterm.js` 认为应用程序未申请鼠标事件。
3. **xterm.js 的 `_handlePassiveWheel` 兜底**：`xterm.js` 判定当前在无回滚缓冲的备用屏幕且鼠标未激活时，将向上滚轮（`deltaY < 0`）转译为 `\x1b[A`（Up Arrow 上方向键）发给 stdin。
4. **历史回溯**：输入框接收到 Up Arrow 按键，自然触发命令行历史回溯，显示上一条发送的消息。

### 修复方案
在目标 IDE（Cursor 或 Antigravity IDE）的 `settings.json`（`Ctrl+,` 点击右上角图标）中添加：

```json
{
  "terminal.integrated.windowsUseConptyDll": true
}
```

**生效条件**：
- 不需要重启整个 IDE 软件。
- 但必须**关闭旧终端（点垃圾桶 Kill Terminal）并重新打开一个终端**，再启动 `pi` 即可让自带的现代 ConPTY 生效并透传鼠标滚轮序列。

---

进阶细节（传统编码完整规则、协商报文、源码位置、终端探测方法、sendInput 序列速查、xterm.js 滚轮源码机制）见 `references/key-encoding-and-protocols.md`。
