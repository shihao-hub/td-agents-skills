---
name: kb-windows-terminal-cwd-osc99
description: Windows Terminal 拆分窗格与会话恢复在 cd 切换目录后重启记不住路径排障：剖析终端与 Shell 跨进程隔离、ConPTY 目录感知断层与 OSC 9;9 路径上报协议，在 PowerShell Profile 注入原生 prompt 并保障 UTF-8 BOM，实现分屏与重启精准还原当前目录。当 WT 恢复会话目录全部回到初始路径、拆分窗格无法继承 cd 目录时查阅。
version: 1.0.0
created: 2026-10-13
updated: 2026-10-13
id: "053"
domain: ide
scope: terminal
type: fix
slug: "WinTerminal拆分窗格cd目录丢失与OSC99上报"
status: verified
last_verified: "2026-10-20"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: true
---

# Windows Terminal 拆分窗格 cd 目录重启不保留与 OSC 9;9 路径上报排障指南

> **适用场景**：Windows Terminal 开启了“重新打开先前的会话”（`"firstWindowPreference": "persistedWindowLayout"`），拆分出多个窗格（Pane）并在其中各自 `cd` 切换到不同工程目录开发。但关闭并重启终端后，所有恢复出来的窗格全部退回最初始的项目目录，`cd` 过的路径完全无法被记住；且按 `Alt+Shift+D` 拆分新窗格时，新窗格也无法继承当前已 `cd` 的目录。

---

## 一、现象与报错直击

### 1. 真实现场（2026-10-12 实测）

Windows Terminal 内包含多个标签页与多层拆分窗格（左右竖切与多层横切）。重启终端后，界面显示会话还原提示：

```text
[已还原 2026/10/12 14:48:36]
Windows PowerShell
PS D:\Users\language_projects\go_projects\agyquota>

[已还原 2026/10/12 15:41:13]
Windows PowerShell
PS D:\Users\language_projects\go_projects\agyquota>

[已还原 2026/10/12 17:08:36]
Windows PowerShell
PS D:\Users\language_projects\go_projects\agyquota> cd ..
PS D:\Users\language_projects\go_projects>

[已还原 2026/10/12 23:36:50]
Windows PowerShell
PS D:\Users\language_projects\go_projects\agyquota>
```

### 2. 用户核心困惑与认知误区

1. **界面无属性设置**：右键点击窗格或标签页，找不到任何“修改此窗格启动目录”的 UI 设置项；
2. **以为 `cd` 能持久化**：在窗格内执行 `cd ..` 切换了目录，但一旦关闭终端重新启动，还原出来的该窗格依然顽固地回到了旧目录 `...\agyquota`；
3. **怀疑是终端 Bug**：“为什么会话布局和文字能恢复，唯独 `cd` 后的目录记不住？”

---

## 二、底层根因剖析

### 1. 终端与 Shell 的跨进程目录黑盒（ConPTY 隔离）

Windows Terminal 本质是一个 GUI 文本渲染与输入宿主（Terminal Emulator），而你在里面运行的 PowerShell / CMD 是独立的子进程。
- 当你在 Shell 内部调用 `cd` 时，这个工作目录变更（CWD）仅存在于 PowerShell 子进程的内存空间与句柄中；
- 在 Windows 的 ConPTY / PTY 架构下，**操作系统内核不会、也无法主动通知父级 Windows Terminal“子进程改目录了”**；
- 加上 PowerShell 独特的 Provider 抽象（`$PWD` 与底层 Win32 API `GetCurrentDirectory` 可能不一致），外部终端更无法通过暴力读取进程内存获得真实有效的路径。

### 2. Windows Terminal 会话持久化的记忆依赖：`state.json`

在 `%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\state.json` 中，WT 记录会话布局时：

```json
"persistedWindowLayouts": [
    {
        "tabLayout": [
            {
                "action": "newTab",
                "profile": "{61c54bbd-c2c6-5271-96e7-009a87ff44bf}",
                "startingDirectory": "D:\\Users\\language_projects\\go_projects\\agyquota"
            }
        ]
    }
]
```

如果 Shell 从不告诉终端自己的当前目录，WT 在退出落盘 `state.json` 时，就**只能写入最初创建该窗格时记录的旧 `startingDirectory`**。下次还原，自然只能以旧目录拉起。

### 3. 通信桥梁：`OSC 9;9`（ConEmu / WT CWD 上报协议）

微软为 Windows Terminal 设计的目录同步方案是**转义序列协议**：
通过 Shell 的提示符（`prompt`）钩子，在每次用户敲回车刷新提示符时，向标准输出静默打印一段特定的虚拟控制序列：
```text
ESC ] 9 ; 9 ; "<完整路径>" ESC \
```
- 十六进制字节流：`1B 5D 39 3B 39 3B 22 <Path> 22 1B 5C`
- WT 的 VT 字符流解析器截获到此序列后，会静默消费掉它（不展示在屏幕上），并将该 Pane 内存中的 `CurrentWorkingDirectory` 更新为最新路径。
- **断层所在**：PowerShell 5.1 / 7 默认的 `prompt` 函数**没有内置这段上报代码**。

### 4. 衍生大坑：PowerShell 5.1 读取 UTF-8 文件必须带 BOM

在修改 Windows PowerShell 5.1 的配置文件 `$PROFILE` 时，存在极其隐蔽的编码陷阱（印证本库第 28 篇手记）：
- 若使用普通文本工具或无 BOM 形式保存 `$PROFILE`（UTF-8 Without BOM）；
- PS 5.1 启动时会默认以系统代码页（GBK / CP936）解析该文件；
- 文件内的中文注释在被 GBK 强行拼合时，中文字节会吃掉后续字符，导致语法树解析错位，引发离奇报错：
  ```text
  At C:\...\Microsoft.PowerShell_profile.ps1:56 char:1
  + }
  + ~
  Unexpected token '}' in expression or statement.
  ```
- **正解**：文件头部必须显式保留 3 字节 UTF-8 BOM（`EF BB BF`）。

---

## 三、标准抢救与修复 SOP

### Step 1：定位 PowerShell 配置文件

在终端中检查你的 `$PROFILE` 路径：
```powershell
$PROFILE
# 典型路径：C:\Users\<用户名>\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1
```

### Step 2：注入 OSC 9;9 路径上报 prompt 函数

使用文本编辑器打开 `$PROFILE`，在末尾追加微软官方推荐的标准 `prompt` 函数：

```powershell
# 向 Windows Terminal 上报当前工作目录（支持会话恢复持久化与分屏继承 CWD）
function prompt {
    $loc = $executionContext.SessionState.Path.CurrentLocation
    $out = ""
    if ($loc.Provider.Name -eq "FileSystem") {
        $out += "$([char]27)]9;9;`"$($loc.ProviderPath)`"$([char]27)\"
    }
    $out += "PS $loc$('>' * ($nestedPromptLevel + 1)) "
    return $out
}
```

> **原理说明**：
> - `$loc.Provider.Name -eq "FileSystem"`：防御非文件系统（如注册表 `HKCU:\`、证书库等），避免在注册表路径下向 WT 发送无效目录；
> - `$([char]27)`：输出 ASCII `0x1B`（ESC 字符）；
> - 格式保持了原汁原味的 PowerShell 经典提示符外观（`PS C:\path> `），用户无任何视觉异样感。

### Step 3：保障 UTF-8 带 BOM 保存（防 Unexpected token 报错）

若通过脚本或编辑器修改，确保文件以 UTF-8 with BOM 编码落盘。可通过 Python 极简校验与重写：

```python
profile_path = r"C:\Users\<用户名>\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1"
with open(profile_path, "r", encoding="utf-8") as f:
    text = f.read().lstrip("\ufeff")

with open(profile_path, "wb") as f:
    f.write(b"\xef\xbb\xbf" + text.encode("utf-8"))
```

### Step 4：即时载入生效

在当前已打开的窗格中执行：
```powershell
. $PROFILE
```
（或者关闭所有终端，重新打开 Windows Terminal）。

---

## 四、验证与防复发闭环

### 1. 验证 1：拆分窗格自动继承当前目录

1. 在窗格 A 中执行 `cd ..` 或切换到任意新路径；
2. 按快捷键 `Alt + Shift + D` 触发自动拆分；
3. **断言**：新拆分出的窗格 B 应该直接位于刚才 `cd` 后的目录，不再重置为默认 profile 路径。

### 2. 验证 2：重启 Windows Terminal 完美恢复最新目录

1. 在拆分窗格中各执行一次 `cd` 并敲回车触发提示符刷新；
2. 正常关闭 Windows Terminal 窗口（触发 WT 写回 `state.json`）；
3. 重新打开 Windows Terminal；
4. **断言**：所有带 `[已还原 ...]` 标识的窗格均精准还原在各自最后 `cd` 的路径下。

### 3. 验证 3：底层转义序列流单元测试

若想自动化验证 PowerShell 是否切实发出了 `OSC 9;9` 序列，可运行以下检测脚本：

```python
import subprocess

res = subprocess.run(["powershell", "-NoLogo", "-Command", "prompt"], capture_output=True)
if b"\x1b]9;9;" in res.stdout:
    print("SUCCESS: OSC 9;9 escape sequence detected!")
else:
    print("FAIL: OSC 9;9 sequence missing.")
```

输出 `SUCCESS: OSC 9;9 escape sequence detected!` 即代表整条链路彻底打通。
