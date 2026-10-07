# 按键编码与终端键盘协议（深挖参考）

> sh-pi-keybindings 的附录，沉淀自 2026-10-06 对 pi-tui 匹配器与 Windows Terminal 的实测。日常改键不需要读本文；只在需要判断「某个组合键到底能不能送达」或手工验证时查阅。

## 目录

1. 传统 VT 编码完整规则
2. 扩展协议格式（Kitty CSI-u / modifyOtherKeys）
3. pi 的协商与匹配实现（源码位置 + 已实测结论）
4. 终端支持与探测方法
5. 手工验证命令
6. Windows Terminal sendInput 序列速查

## 1. 传统 VT 编码完整规则

终端把按键翻译成字节流，修饰键只能靠字符本身或前缀编码：

| 类别 | 编码规则 | 举例 |
| :--- | :--- | :--- |
| 可打印字符 | 原样 | `a` → `0x61` |
| Shift+字母 | 大写字母 | `Shift+A` → `0x41`（Shift 信息只剩大小写） |
| Ctrl+字母 | `code & 0x1f` 控制码 | `Ctrl+V` → `0x16`；`Ctrl+[` → `0x1b`（与 ESC 同码，歧义） |
| Ctrl+符号 | 同掩码规则 | `Ctrl+-` → `0x1f`；`Ctrl+_` → `0x1f`（同物理键） |
| Alt+可打印字符 | `ESC` + 该字符 | `Alt+V` → `ESC v` |
| Ctrl+Alt+字母 | `ESC` + 控制码 | `Ctrl+Alt+V` → `ESC 0x16` |
| 功能键 | CSI 序列 | 方向键 `ESC[A`、PageUp `ESC[5~`、F1 `ESCOP` |
| 带修饰的功能键 | `CSI 1;N 字母`（N: 2=Shift 3=Alt 5=Ctrl 6=Shift+Ctrl…） | `Ctrl+Left` → `ESC[1;5D` |

**无法表达的**：`Shift+Alt+字母`（`ESC`+大写，无标准含义）、`Ctrl+Shift+字母`（Shift 丢失，与 `Ctrl+字母` 同码）、`Shift+Enter`/`Ctrl+Enter`（与 Enter 同码）等。这就是 pi 里 `shift+alt+v` 在 Windows Terminal 1.24 上「按了没反应」的全部原因。

## 2. 扩展协议格式

### Kitty CSI-u

```
CSI <codepoint> ; <modifiers>[:<event>] u
```

- 修饰值 = `1 + bitmask`：shift=1、alt=2、ctrl=4、super=8、hyper=16、meta=32、capslock=64、numlock=128。加 1 是为了 0 表示「无修饰」。
- 事件类型可选（`1`=按下、`2`=重复、`3`=松开），由 pi 请求的 flags 决定是否上报。

| 按键 | 序列 | 说明 |
| :--- | :--- | :--- |
| `Shift+Alt+V` | `ESC[118;4u` | 118='v'，4=1+1+2 |
| `Ctrl+V` | `ESC[118;5u` | 5=1+4 |
| `Alt+V` | `ESC[118;3u` | 3=1+2 |
| `Ctrl+Shift+V` | `ESC[118;6u` | 6=1+1+4 |
| `Shift+Alt+V`（上报大写码） | `ESC[86;4u` | 86='V'，pi 会归一化大小写后同样匹配 |

### xterm modifyOtherKeys

```
CSI 27 ; <modifiers> ; <codepoint> ~
```

修饰值规则同上（含 +1）。例：`Shift+Alt+V` → `ESC[27;4;118~`。pi 在终端没有 Kitty 协议时发送 `CSI > 4 ; 2 m` 开启它。

## 3. pi 的协商与匹配实现

源码位置（以 `npm root -g` 下 `@earendil-works/pi-coding-agent` 为基准）：

| 文件 | 内容 |
| :--- | :--- |
| `dist/terminal.js` | `queryAndEnableKittyProtocol()`：发送 `ESC[>1;2;4u` + `ESC[?u` + `ESC[c`（DA 哨兵）；有 Kitty flags 应答则激活，只有 DA 则 `enableModifyOtherKeys()`（`ESC[>4;2m`） |
| `node_modules/@earendil-works/pi-tui/dist/keys.js` | `parseKeyId` / `matchesKey`；传统回退分支（`ESC+小写`=alt、大写=shift、控制码=ctrl、`ESC+控制码`=ctrl+alt）、`matchesKittySequence`、`matchesModifyOtherKeys`、`decodeKittyPrintable` |
| `dist/core/keybindings.js` | `KEYBINDINGS` 默认表（含平台分支：win32/WSL 与 darwin/linux 默认键不同）与旧名迁移表 |
| `dist/config.js` | `getAgentDir()`（`~/.pi/agent`，可用 `PI_CODING_AGENT_DIR` 覆盖） |

**已实测结论**（pi-tui 当前版本，node 直接调用 `matchesKey`）：

| 字节序列 | `shift+alt+v` | `alt+v` | 备注 |
| :--- | :---: | :---: | :--- |
| `ESC[118;4u`（Kitty） | ✅ | ❌ | 不需要 Kitty 协商处于激活态也能匹配 |
| `ESC[27;4;118~`（modifyOtherKeys） | ✅ | ❌ | |
| `ESC v`（传统 alt+v） | ❌ | ✅ | |
| `ESC V`（传统 shift+alt+v） | ❌ | ❌ | pi 没有任何绑定会匹配它，按键被静默忽略 |
| `ESC 0x16`（传统 ctrl+alt+v） | ❌ | ❌ | 匹配 `ctrl+alt+v` |

## 4. 终端支持与探测方法

| 终端 | 扩展协议 | 采纳版本 | 来源 |
| :--- | :--- | :--- | :--- |
| Windows Terminal | Kitty | 1.25+（首个含它的发布 v1.25.622.0，2026-03；1.25 stable v1.25.2733.0，2026-10-02） | PR microsoft/terminal#19817 重写 TerminalInput；1.24 系列发布说明无 Kitty 条目 |
| VS Code 内置终端 | Kitty | ≥ 1.109.5 默认开启 | pi `docs/terminal-setup.md` |
| Kitty / WezTerm / Ghostty / iTerm2 | Kitty / modifyOtherKeys | — | 免配置 |
| tmux | 透传 | — | 见 pi `docs/tmux.md` |

探测方法（从强到弱）：

1. **看版本**：`powershell Get-AppxPackage Microsoft.WindowsTerminal`，对照上表。
2. **看发布说明**：`microsoft/terminal` 的 release notes 里搜 "Kitty Keyboard Protocol"。
3. **扫二进制字符串**（弱证据交叉验证，Git Bash 示例）：
   ```bash
   strings -a -e l "/c/Program Files/WindowsApps/Microsoft.WindowsTerminal_<版本>_x64__8wekyb3d8bbwe/OpenConsole.exe" | grep -i kitty
   ```
   没有字符串不代表一定不支持（实现可能不带字面量），有则是强信号。
4. **实测**：在目标终端里运行 `kitten show-key -m kitty`（Kitty 自带工具）——Windows Terminal 没有等价物，只能用 sendInput 映射方案实测按下后的行为。

## 5. 手工验证命令

```bash
PI_ROOT="$(npm root -g)/@earendil-works/pi-coding-agent"

# 1) 匹配器：某个字节序列能匹配哪些键 id
node --input-type=module -e "
const { matchesKey, parseKey } = await import('$PI_ROOT/node_modules/@earendil-works/pi-tui/dist/keys.js');
for (const [name, data] of Object.entries({
  'kitty shift+alt+v': '\x1b[118;4u',
  'legacy ESC V': '\x1bV',
  'legacy ESC v': '\x1bv',
})) console.log(name, '| shift+alt+v:', matchesKey(data, 'shift+alt+v'), '| alt+v:', matchesKey(data, 'alt+v'), '| parse:', parseKey(data));
"

# 2) 生效配置：动作 → 实际按键
node --input-type=module -e "
const { KeybindingsManager } = await import('$PI_ROOT/dist/core/keybindings.js');
const { getAgentDir } = await import('$PI_ROOT/dist/config.js');
const kb = KeybindingsManager.create(getAgentDir());
console.log(JSON.stringify(kb.getResolvedBindings()['app.clipboard.pasteImage']));
"
```

更省事的方式：直接用本 skill 的 `scripts/verify-binding.mjs`（封装了上面两件事 + 反向匹配）。

## 6. Windows Terminal sendInput 序列速查

映射入口见 SKILL.md §三。序列生成公式：`ESC[<键码>;<修饰值>u`。

| 目标 pi 键 id | WT keys | sendInput input |
| :--- | :--- | :--- |
| `shift+alt+v` | `alt+shift+v` | `\u001b[118;4u` |
| `alt+v` | `alt+v` | `\u001b[118;3u` |
| `ctrl+shift+v` | `ctrl+shift+v` | `\u001b[118;6u` |
| `ctrl+alt+v` | `ctrl+alt+v` | `\u001b[118;7u` |
| `shift+alt+b` | `alt+shift+b` | `\u001b[98;4u` |

- 键码 = 字母小写 ASCII；修饰值 = 1 + shift(1) + alt(2) + ctrl(4) + super(8)。
- 功能键/方向键的 Kitty 键码是 PUA 码位（与字母不同），需要对照 Kitty 协议规范，不在本表覆盖范围。
- 该方式与终端版本无关，WT 升级到 1.25+ 后仍可用，不冲突。


## 7. 终端备用屏幕与鼠标滚轮协议（Alternate Scroll 与 ConPTY 陷阱）

### 7.1 现象对比
- **Zed / VS Code 1.140+**：在 pi 交互会话中向上滚动鼠标，消息历史顺畅上滚，视口偏离底部时出现 `↓ Jump to latest message · ctrl+end` 悬浮按钮。
- **Cursor / Antigravity IDE**：向上滚动滚轮不仅不翻页，反而不断在输入框填充历史消息（等价于按下向上方向键 `↑`）。

### 7.2 根因链路与源码追踪
1. **备用屏幕与鼠标模式声明**：
   pi agent 的 `TuiAltScreen` 在启动时向终端输出：
   ```text
   \x1b[?1049h   # 进入备用屏幕缓冲区 (Alternate Screen Buffer)
   \x1b[?1000h   # 启用正常鼠标跟踪
   \x1b[?1002h   # 启用按钮移动跟踪
   \x1b[?1003h   # 启用全移动跟踪
   \x1b[?1006h   # 启用 SGR 扩展鼠标模式
   ```
2. **ConPTY 模式隔离缺陷**：
   Cursor / Antigravity IDE 的 `terminal.integrated.windowsUseConptyDll` 默认为 `false`（处于 preview 状态），`node-pty` 调用系统内置 `conhost.exe`。
   旧版系统 ConPTY 实现了 `\x1b[?1049h` 屏幕缓冲切换，但会吞噬 `\x1b[?1000h`~`\x1b[?1006h` 鼠标跟踪请求，导致外部宿主 `xterm.js` 认为当前应用并未请求鼠标事件（`requestedEvents.wheel` 为 `null`）。
3. **xterm.js 的 `_handlePassiveWheel` 兜底行为**：
   在 `@xterm/xterm` 的事件处理代码中：
   ```javascript
   _handlePassiveWheel(e, t) {
     if (!e.requestedEvents.wheel) {
       if (!this._mouseStateService.allowCustomWheelEvent(t)) return false;
       if (!this._bufferService.buffer.hasScrollback) { // 备用屏幕下 hasScrollback === false
         if (0 === t.deltaY) return false;
         // 向上滚动 (t.deltaY < 0) 被转译为 Up Arrow (\x1b[A 或 \x1bOA)
         const e = "\x1b" + (this._coreService.decPrivateModes.applicationCursorKeys ? "O" : "[") + (t.deltaY < 0 ? "A" : "B");
         return this._coreService.triggerDataEvent(e, true);
       }
     }
   }
   ```
   由于当前是备用屏幕且缺少鼠标模式，`xterm.js` 自动将鼠标滚轮转译为 `\x1b[A` 注入到进程输入流。
4. **命令行历史触发**：
   pi 的输入框正处于焦点的交互读取状态，收到 `Up Arrow` 立即回显前一条历史消息。

### 7.3 修复验证
在 Cursor 或 Antigravity IDE 的 `settings.json` 中配置：
```json
{
  "terminal.integrated.windowsUseConptyDll": true
}
```
强制 `node-pty` 加载 IDE 自身绑定的现代 `conpty.dll`（VS Code / Zed 已内置 1.25+），从而完整支持 SGR 鼠标序列透明透传。
