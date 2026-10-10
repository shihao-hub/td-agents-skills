---
name: kb-antigravity-paste-keybindings
description: Antigravity CLI (agy) 与 Pi 终端中修改「粘贴图片」快捷键的完整 SOP：keybindings.json 配置规范、edit.paste 动作映射、Windows Terminal 扩展协议 (Kitty CSI-u) 映射解决组合键失效、以及 PowerShell 写入 UTF-8 BOM 导致「invalid character '\ufeff'」报错排查。当 Alt+V 冲突被占、按 Alt+Shift+V 无反应、或 keybindings 报 ufeff 时查阅。
---

# Antigravity CLI 粘贴图片改键、Windows 终端 Kitty 协议透传与 BOM 排障指南

## 一、 现象与报错直击

1. **默认 `Alt+V` 粘图在 Windows 下经常无反应或被抢占**：
   - 终端内 `Ctrl+V` 默认被终端模拟器截获为系统剪贴板纯文本粘贴，无法透传图片对象；
   - CLI 官方在 Windows 下添加了 `Alt+V` 作为备选粘图快捷键，但 `Alt+V` 在 Windows 上极易与各类全局工具冲突（如 Voicemeeter 录音快捷键、剪贴板增强工具 Ditto/PowerToys、部分输入法角标切换、微星/NVIDIA 显卡控制台等），导致按下后毫无动静。
2. **改键为 `Alt+Shift+V` 后终端按下无任何反应**：
   - 用户在配置文件中改成了 `alt+shift+v`，按下却无法唤出图片上传。
   - 根因在于传统 VT 键盘编码中，`Shift+Alt+V` 仅被编码为无意义的 `ESC + V`，终端没有将修饰键完整透传给 CLI 进程。
3. **配置 `keybindings.json` 后启动报 UTF-8 BOM 错误**：
   - 终端显眼处出现黄色/蓝色警告提示框：
     ```text
     ⚠ Keybindings Error
       ⎿  error loading keybindings from C:\Users\<用户>\.gemini\antigravity-cli\keybindings.json: invalid character '\ufeff' looking for beginning of value (delete ~\.gemini\antigravity-cli\keybindings.json and run /keybindings to reset)
     ```
   - 根因在于 Windows PowerShell 5.1 使用 `Set-Content -Encoding UTF8` 写入时，强制附带了 3 字节 UTF-8 BOM 头（`\xEF\xBB\xBF`，即 Unicode `\uFEFF`），导致 Go 原生 JSON 解析器在起始位置崩溃拒绝解析。

---

## 二、 底层根因剖析

### 1. 三层按键截获模型

在命令行终端中使用富文本/图片粘贴功能，按键会经历三层流转，任一层失效都会导致功能断裂：

```text
[物理键盘 Alt+Shift+V]
         │
         ▼
[第 1 层：终端模拟器 (Windows Terminal)]
 ├── 是否被终端自身菜单/操作快捷键拦截？
 └── 终端是否将复合按键转译为现代键盘协议 (Kitty CSI-u) 发送给子进程？
         │ （若仅发送传统 VT ESC+V，则复合修饰键丢失）
         ▼
[第 2 层：CLI 终端协议解析层 (Bubble Tea v2)]
 ├── 解析终端输入的字节序列（支持 Kitty CSI-u 协议与 modifyOtherKeys）
 └── 将扩展按键序列标准化为规范按键标识（如 "alt+shift+v"）
         │
         ▼
[第 3 层：应用层配置与动作路由 (keybindings.json)]
 ├── 读取 ~/.gemini/antigravity-cli/keybindings.json（必须为纯 UTF-8，无 BOM）
 └── 命中动作标识 edit.paste，从操作系统剪贴板提取图片并暂存上传
```

### 2. 核心机制解密：为什么改这个键能粘图片？（Key 与 Value 的本质）

开发者最常见的困惑是：*“为什么给配置文件加了个键值对就能粘图片？普通按键不能粘，凭什么这个快捷键能粘？”*

#### (1) Key 与 Value 不是普通标签，而是「函数入口」与「开门钥匙」

在 `keybindings.json` 中：
```json
{
  "edit.paste": ["alt+shift+v", "shift+alt+v", "ctrl+v"]
}
```
- **右边的 Value（`"alt+shift+v"`）**：只是一个**触发信号（钥匙）**，告诉 CLI 捕获到哪个键盘字节序列时去调用相应功能；
- **左边的 Key（`"edit.paste"`）**：是 CLI 源码中**写死的核心功能入口（Action ID）**。随便自定义一个 `"my.paste": "alt+shift+v"` 是完全无效的，因为 CLI 内部根本没有对应的处理函数。

#### (2) `edit.paste` 内部在执行什么（剪贴板探针与位图落盘）

`edit.paste` 背后绑定了一套完整的操作系统底层图形处理函数（内部枚举 `KeyPaste`）：

```text
用户按下 Alt + Shift + V
       │
       ▼
CLI 命中 action: edit.paste
       │
       ▼
调用 Windows Win32 剪贴板 API (OpenClipboard / GetClipboardData)
       │
   ┌───┴─────────────────────────────────────────┐
   │ 探测：当前剪贴板中存在哪种数据格式？        │
   └───┬─────────────────────────────────────┬───┘
       ▼ 存在位图 (CF_DIB / CF_DIBV5 / 图像数据)   ▼ 仅有纯文本 (CF_UNICODETEXT)
1. 从内存中提取原始图像二进制字节流            直接将字符串填入终端输入光标处
2. 在本地持久化落盘为临时 .png 文件
   (.gemini/antigravity-cli/.../.user_uploaded/)
3. 向当前会话上下文自动挂载多模态图片附件！
```

#### (3) 为什么终端自带的 Ctrl+V 或其他键无法粘图片？

1. **终端模拟器（Windows Terminal）的限制**：终端自带的粘贴（`PasteFromClipboard`）设计初衷是向终端输入输出管道（stdin）推送**纯字符流**。当剪贴板里是一张位图截图时，终端根本无法将其“打印”为字符，因此静默丢弃或毫无反应；
2. **普通按键的限制**：普通按键只会向 CLI 发送字符的 ASCII/Unicode 码，不会主动触发操作系统的剪贴板访问接口；
3. **改键的真实本质**：并不是改键“创造”了粘图功能，而是**为 CLI 底层早已实现的「剪贴板探针与图片落盘函数」，重新配了一把没有被系统和终端拦截的新钥匙**（从被抢占的 `Alt+V` 迁移到 `Alt+Shift+V`）。

### 3. Antigravity CLI 的按键系统与动作映射

通过对 `agy.exe`（Jetski 架构）逆向符号与源码可知：
- **核心包**：`google3/third_party/jetski/cli/keybindings`。
- **粘贴动作 ID**：**`edit.paste`**（对应内部底层枚举 `KeyPaste`）。该动作统筹了文本粘贴、富文本转换与剪贴板图片提取上传全流程。
- **延迟创建机制**：`agy` 为了避免污染用户目录，默认启动**不会**自动生成 `keybindings.json`。仅在用户手动运行 `/keybindings` 或自行创建该文件时生效。
- **映射位置**：
  - Windows 主路径：`%USERPROFILE%\.gemini\antigravity-cli\keybindings.json`；
  - 兼容回退路径：`%USERPROFILE%\.gemini\antigravity\keybindings.json` 及 `%USERPROFILE%\.gemini\keybindings.json`。

> [!NOTE]
> 若同时使用同生态的 `pi` Agent（`@earendil-works/pi-coding-agent`），其对应的粘贴图片动作 ID 为 **`app.clipboard.pasteImage`**，配置文件位于 `%USERPROFILE%\.pi\agent\keybindings.json`。

### 4. Kitty CSI-u 协议计算原理

传统 VT 100 编码通过单个控制字节或 `ESC + 字符` 表示修饰键，根本无法区分 `Shift+Alt+字母`。现代终端采用 **Kitty CSI-u** 协议表示复合修饰键：

$$\text{序列格式：}\quad \text{ESC}[<\text{按键码}>;<\text{修饰键位图}>u$$

- **按键码**：小写字母 `v` 的 ASCII 码为 `118`；
- **修饰键位图公式**：$\text{基础值 } 1 + \text{Shift}(1) + \text{Alt}(2) + \text{Ctrl}(4) + \text{Super}(8)$；
  - 当按下 <kbd>Alt</kbd> + <kbd>Shift</kbd> 时：$1 + 1 + 2 = 4$；
- **计算结果**：`\u001b[118;4u`（即 `ESC[118;4u`）。

### 5. PowerShell UTF-8 BOM 陷阱

- Windows PowerShell 5.1（默认 `powershell.exe`）的 `Set-Content` 和 `Out-File` 参数 `-Encoding UTF8` 会自动输出 `0xEF 0xBB 0xBF` 的 UTF-8 BOM 头。
- Go 语言标准库 `encoding/json` 严格遵循 [RFC 8259](https://datatracker.ietf.org/doc/html/rfc8259)，规范规定 JSON 文本“MUST NOT”包含 BOM。遇到前置 `0xEF 0xBB 0xBF` 时，Go 解析器将其解码为 Unicode `\ufeff` 并抛出 `invalid character '\ufeff' looking for beginning of value`。

---

## 三、 标准配置与解决 SOP

### 步骤一：创建纯 UTF-8（无 BOM）的 keybindings.json

必须确保生成的 JSON 首字节为 `{`（`0x7B`），绝不带 BOM。

#### 推荐方案（PowerShell 一键写入，安全无 BOM）：

```powershell
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$json = @'
{
  "edit.paste": ["alt+shift+v", "shift+alt+v", "ctrl+v"]
}
'@

$paths = @(
  "$env:USERPROFILE\.gemini\antigravity-cli\keybindings.json",
  "$env:USERPROFILE\.gemini\antigravity\keybindings.json"
)

foreach ($p in $paths) {
  $dir = Split-Path $p -Parent
  if (!(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
  [System.IO.File]::WriteAllText($p, $json, $utf8NoBom)
  Write-Output "写入成功: $p"
}
```

> [!TIP]
> 同时保留 `"ctrl+v"` 是最佳实践：当剪贴板是文本时，在支持的环境依然可以快速粘贴；而遇到图片或终端文本冲突时，走 `"alt+shift+v"`。

#### （可选）同步配置 `pi` Agent：

若同机也使用 `pi`，将其粘贴配置对齐至相同按键：

```powershell
$piJson = @'
{
  "app.clipboard.pasteImage": ["shift+alt+v", "alt+shift+v"]
}
'@
$piPath = "$env:USERPROFILE\.pi\agent\keybindings.json"
if (Test-Path (Split-Path $piPath -Parent)) {
  [System.IO.File]::WriteAllText($piPath, $piJson, $utf8NoBom)
  Write-Output "同步更新 pi 配置: $piPath"
}
```

---

### 步骤二：Windows Terminal 扩展协议透传配置

确保 Windows Terminal 在接收到 <kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>V</kbd> 时，不会被系统静默吃掉，而是发送 Kitty CSI-u 扩展键码 `\u001b[118;4u`。

1. 打开 Windows Terminal 设置配置文件：
   - 路径：`%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json`
   - 或者在 Windows Terminal 中按下 <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>,</kbd> 打开。
2. 在 `actions` 列表中添加一条 `sendInput` 映射：

```json
{
  "command": {
    "action": "sendInput",
    "input": "\u001b[118;4u"
  },
  "keys": "alt+shift+v"
}
```

3. 保存文件，Windows Terminal 会立即热重载，无需重启终端。

---

### 步骤三：验证与生效检查

#### 1. 验证 BOM 是否彻底清除：

在 PowerShell 中查看首三字节：

```powershell
$bytes = [System.IO.File]::ReadAllBytes("$env:USERPROFILE\.gemini\antigravity-cli\keybindings.json")
$hex = ($bytes[0..2] | ForEach-Object { '{0:X2}' -f $_ }) -join ' '
Write-Output "文件头十六进制: $hex (期望值: 7B 0A 20)"
```

- 若输出 `7B 0A 20`（代表 `{` 开头）：**校验通过**；
- 若输出 `EF BB BF`：存在 BOM 头，需按步骤一重写。

#### 2. 在 CLI 中重载并测试：

1. 在当前 `agy` 会话中输入 `/keybindings`（或直接重启一次 `agy` 进程）；
2. 观察终端是否出现黄蓝色的 `Keybindings Error`。若无报错，说明配置已无缝解析；
3. 使用截图工具（如 Snipping Tool / 微信截图）截取一张屏幕图片；
4. 聚焦到 CLI 输入框，按下 <kbd>Alt</kbd> + <kbd>Shift</kbd> + <kbd>V</kbd>；
5. 输入框成功显示图片附件标记（如 `[Image: uploaded_media_*.png]`），即代表整条改键与协议透传链路完全畅通！

---

## 四、 关键差异与避坑速查表

| 项目 | Antigravity CLI (`agy`) | `pi` Coding Agent |
| :--- | :--- | :--- |
| **配置文件路径** | `~/.gemini/antigravity-cli/keybindings.json` | `~/.pi/agent/keybindings.json` |
| **粘贴动作 ID** | `edit.paste` | `app.clipboard.pasteImage` |
| **键名规范** | 数组列表，如 `["alt+shift+v", "ctrl+v"]` | 字符串或数组，如 `["shift+alt+v", "alt+shift+v"]` |
| **终端协议** | Bubble Tea v2（原生支持 Kitty CSI-u 与 modifyOtherKeys） | pi-tui（启动时自动协商 Kitty / modifyOtherKeys） |
| **重载命令** | `/keybindings` 或重启进程 | `/reload` 或重启进程 |
| **文件编码** | **严格纯 UTF-8，禁止任何 BOM** | **严格纯 UTF-8，禁止任何 BOM** |
