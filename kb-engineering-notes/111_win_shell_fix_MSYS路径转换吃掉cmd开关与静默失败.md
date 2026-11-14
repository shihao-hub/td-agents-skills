---
name: kb-msys-cmd-flag-pathconv-fix
description: |
  Git Bash / MSYS2 环境下执行 `cmd /c "..."` 被路径自动转换吃掉 `/c` 开关，cmd 退化为交互模式只打印 banner、无任何业务输出却返回 exit code 0，导致把"命令根本没执行"误判成"执行成功且无匹配项"；并伴生 `FINDSTR: 无法打开 xxx`（参数错位把过滤词当文件名）。深度剖析 MSYS2 runtime 的 POSIX→Windows 路径转换规则（`/x` 单字母且盘符真实存在时转成 `X:\`，故 `/c`、`/d` 中招而 `/i`、`/query` 不受影响）、cmd 交互态 EOF 退出码为 0 的静默失败链路，以及它如何让自启项排查漏掉计划任务并导致错误归因。提供 `cmd //c`、`MSYS_NO_PATHCONV=1`、`MSYS2_ARG_CONV_EXCL`、直调 exe、改用 PowerShell 五条规避路径，并固化"看业务输出不看退出码"的命令成功判据。第五节追加 Agent 宿主 Shell 选型实战：把 Git Bash 配为 Agent 主 Shell 后，任意带 `/flag` 的原生 CLI 调用都被整批改写（表现为挂死或空输出），Agent 会据此把环境问题误判为代码语法错误。
version: 1.1.0
created: 2026-11-08
updated: 2026-11-14
id: "111"
domain: win
scope: shell
type: fix
slug: "MSYS路径转换吃掉cmd开关与静默失败"
status: verified
last_verified: "2026-11-14"
compatibility:
  os: ["windows"]
falsification_signals:
  - "若命令输出了真实业务数据（任务列表、注册表项、进程信息），说明本次未触发路径转换，不适用本条目"
  - "若在 PowerShell（非 MSYS/Git Bash）中执行同一命令正常，说明问题只出在 MSYS 参数转换层，按第三节规避即可"
  - "若退出码非 0 且 stderr 有明确报错，属于普通命令失败，不是本条目描述的静默吞参数"
invocation:
  auto_trigger: true
  trigger_keywords: ["cmd /c 没输出", "cmd 只打印 banner", "cmd 进入交互模式", "MSYS_NO_PATHCONV", "MSYS2_ARG_CONV_EXCL", "cmd //c", "路径转换", "POSIX to Windows path conversion", "Git Bash cmd 参数丢失", "FINDSTR 无法打开", "exit code 0 但没结果", "命令没执行却返回成功", "schtasks 查不到", "cmd /c 被转成 C:/", "Agent shell 配成 Git Bash", "opencode shell 改回 pwsh", "原生 CLI 斜杠开关失效", "/Validate 挂死", "AHK 参数被吃", "命令超时却无报错"]
---

# win_shell_fix_111_MSYS路径转换吃掉cmd开关与静默失败

> **条目定位**：**Type A 疑难排障条目（MSYS2 runtime 参数路径转换 × Windows 命令行工具斜杠开关冲突 × 静默失败判据）**
> **危险评级**：★★★★☆（不报错、不抛异常、退出码 0，失败被伪装成"成功且无结果"，直接污染排查结论）
> **验证环境**：Windows 11 25H2、Git Bash（MSYS2 runtime）、OpenCode / Claude Code 等 Agent 的 bash 执行层。
> **关联条目**：Windows 原生命令行工具调用规范见 `GLOBAL.md`（优先 PowerShell / 直调 exe）；计划任务与自启项排查见 `046_win_everything_fix_Win进程启动来源取证与Everything闲置保护.md`。

---

## 一、现象与报错直击

### 1. 核心现场：`cmd /c` 只打印 banner，一行业务输出都没有

在 Git Bash 中执行一条本该查询计划任务的命令：

```bash
cmd /c "schtasks /query /fo LIST /v | findstr /i deepseek"
```

实际输出：

```text
Microsoft Windows [版本 10.0.26200.9711]
(c) Microsoft Corporation。保留所有权利。

D:\Users\language_projects>
```

随后命令结束，`echo $?` 得到 `0`。

关键特征：

- 只有 cmd 的 banner 与交互提示符 `D:\Users\language_projects>`，**没有任何任务名、状态、时间等业务数据**
- 没有报错，没有非零退出码
- 紧接着若再串一条 `| findstr /i deepseek`，会出现 `FINDSTR: 无法打开 deepseek`（参数错位，过滤词被当成文件名）

### 2. 伴生陷阱：退出码 0 让人误判为"查过了，没有结果"

真实踩坑链路：

1. 排查某程序开机自启弹窗，需要确认它是否注册了计划任务
2. 用 `cmd /c "schtasks /query ... | findstr /i deepseek"` 查询
3. 看到 `===status:0`（`$?` 的值为 0），判定"命令成功执行，没有匹配项"
4. 转而用运行事件日志推断"Run 键被执行两遍"，给出错误根因
5. 后续用 `Get-ScheduledTask` 重查，一条命令就命中 `DeepSeekSearchStudio` 计划任务——**真正的双注册来源一直存在，只是第一次没查成**

结论被污染的代价：基于错误根因设计的修复方案全部落空。

---

## 二、底层根因剖析

### 1. MSYS2 runtime 的 POSIX → Windows 路径转换

Git Bash 打包的是 MSYS2 运行时。它在 `exec` 一个**非 MSYS 程序**（`cmd.exe`、`findstr.exe`、`reg.exe` 等 Windows 原生 exe）之前，会扫描 `argv`，把形似 POSIX 路径的参数翻译成 Windows 路径。

否则 `ls /usr/bin`、`cd /c/Users` 这类写法对原生程序毫无意义。

### 2. 为什么偏偏是 `/c`

转换规则中有一条：**`/x`（单个字母）视为盘符根，转成 `X:\`**。因为 POSIX 风格里 `/c/Users/foo` 就等于 `C:\Users\foo`。

于是：

```text
用户输入： cmd /c "schtasks /query ..."
exec 前：  cmd C:\ "schtasks /query ..."
```

`cmd.exe` 收到的第一个参数变成了 `C:\`，找不到 `/c` 开关，就**退化成交互模式**：打印 banner、等待 stdin、读到 EOF 后退出。

### 3. 为什么 `/i`、`/query` 反而没事

转换不是无差别触发，它还会检查**该盘符在本机是否真实存在**：

| 参数 | 是否转换 | 原因 |
| :--- | :--- | :--- |
| `/c` | ✅ 转成 `C:\` | 单字母 + C 盘存在 |
| `/d` | ✅ 转成 `D:\` | 单字母 + D 盘存在 |
| `/i` | ❌ 保留 | I 盘不存在 |
| `/query`、`/fo`、`/v` | ❌ 保留 | 多字母，不构成盘符 |

这也解释了同一条命令里为什么 `findstr /i` 没事、而 `cmd /c` 中招。

### 4. 为什么失败是静默的

| 环节 | 表现 |
| :--- | :--- |
| 参数被改写 | 无任何提示 |
| cmd 进入交互模式 | 只打印 banner，看起来像"程序启动了" |
| stdin 为 EOF | cmd 正常退出 |
| 退出码 | `0` |

**三个"正常"叠加，唯一的异常信号只有 banner**。如果只看最后一行 `status:0`，就会得到完全相反的结论。

### 5. 与 PowerShell / 直接调 exe 的差异

- PowerShell 是原生 Windows 程序，斜杠开关（`-Command`、`-NoProfile`）走自己的解析器，不经过 MSYS 转换
- 直接调用 `schtasks.exe /query`：`/query` 是多字母，不触发盘符转换，安全
- 只有 `cmd /c "..."` 这种"用 cmd 包一层"的写法，才把单字母开关暴露在转换规则下

---

## 三、标准抢救与修复 SOP

### 1. 立即判定：这条命令到底执行了没有

出现以下任一特征，一律判定失败，不要看退出码：

- 输出了 cmd 的 banner 或交互提示符 `C:\...>` / `D:\...>`
- 有业务预期但输出为空
- 出现 `FINDSTR: 无法打开 xxx` 这类参数错位报错

### 2. 五条规避路径（按推荐顺序）

```bash
# ① 首选：直接调 exe，不用 cmd 包裹（/query、/fo 等多字母开关不会被转）
schtasks.exe /query /fo LIST /v

# ② 次选：改用 PowerShell（原生 Windows 解析器，引号与编码都可控）
powershell -NoProfile -Command "Get-ScheduledTask | Where-Object { \$_.TaskName -like '*deepseek*' }"

# ③ 一次性关闭全部路径转换（Git Bash 专用）
MSYS_NO_PATHCONV=1 cmd /c "schtasks /query /fo LIST /v"

# ④ MSYS2 通用：只排除指定参数
MSYS2_ARG_CONV_EXCL='/c' cmd /c "schtasks /query /fo LIST /v"

# ⑤ 双斜杠让转换跳过，cmd 自己会归一化成 /c
cmd //c "schtasks /query /fo LIST /v"
```

验证记录（本机实测）：

```text
cmd //c "echo ok"                    -> ok
MSYS_NO_PATHCONV=1 cmd /c "echo ok"  -> ok
MSYS2_ARG_CONV_EXCL='/c' cmd /c ...  -> ok
cmd /c "echo ok"                     -> 打印 banner，进入交互模式
```

### 3. 命令成功判据（防同类静默失败）

| 判据 | 用法 |
| :--- | :--- |
| 业务输出 | **首要判据**：有结构化数据才算成功 |
| 退出码 | **辅助判据**：0 不代表业务成功，只代表进程没崩 |
| 空输出 | 在"预期有数据"的场景下，空输出 = 失败，必须换法重查 |
| stderr | 有输出就要读，不要只扫最后一行 |

### 4. 排查类任务的硬规则

- `schtasks`、`reg`、`sc`、`netsh` 等原生工具**直接调 exe**，禁止用 `cmd /c` 包一层
- 需要管道 / 复杂过滤时，优先 `powershell -NoProfile -Command`，或写单文件 Python 脚本用 `uv run` 驱动
- 一条命令失败后，**必须换路径重查并在结论里标注**，不能静默跳过

---

## 四、验证与防复发闭环

### 1. 自检脚本（判断当前 shell 是否会发生转换）

```bash
# 若输出 banner 而不是 ok，说明本环境会转换 /c
cmd /c "echo ok" 2>&1 | head -3
```

### 2. 回归断言

- 任何查询类命令执行后，先看是否出现 banner / 提示符
- 任何"没有结果"的结论，必须至少用第二种写法复核一次
- 结论写入文档时，附带实际命令与关键输出行，便于他人复核

### 3. 防复发建议

- 在 Agent 规则层固化：Windows 下优先 PowerShell 与直调 exe，`cmd /c` 仅作为最后手段
- 看到 `===status:0` 不要直接采信，先确认命令产生了预期业务输出
- 知识库条目描述排查结论时，明确区分「直接证据」与「间接推断」，间接推断必须标注

### 4. 可证伪信号

- 命令输出了真实任务 / 注册表 / 进程数据 → 本次未触发转换
- 在 PowerShell 中执行同一命令正常 → 问题仅限 MSYS 参数转换层
- 退出码非 0 且有明确报错 → 属于普通命令失败，不是本条目描述的静默吞参数

---

## 五、Agent 宿主 Shell 选型：严禁把 Git Bash 配成 Agent 主 Shell

> **实战来源**：2026-11-14，OpenCode `opencode.json` 的 `shell` 字段被设为 `D:/Program Files/Git/bin/bash.exe`，在为 AutoHotkey 启动脚本做语法校验时爆雷。
> **验证环境**：Windows 11 25H2、OpenCode（shell 配 Git Bash）、Git Bash（MINGW64_NT-10.0-26200）、pwsh 7.6.9、AutoHotkey 2.0.29。

### 1. 现场：一条完全正常的原生 CLI 命令把 Agent 骗了

```bash
# Agent 执行层是 Git Bash 时
AutoHotkey64.exe /ErrorStdOut /Validate "app_switcher.ahk"
```

实际表现：

- 命令**永不返回**（Agent 侧看到的是超时）
- 进程列表里出现一个窗口标题恰为 `ErrorStdOut` 的错误对话框——MSYS 把 `/ErrorStdOut` 转成 `C:\Program Files\Git\ErrorStdOut`，AHK 把它当脚本路径去找，弹出"文件未找到"并阻塞
- Agent 只能看到「超时 + 零输出」，于是把结论误判为「**脚本有语法错误**」或「**该开关版本不支持**」

同机同命令的对照实验（唯一变量是 Shell）：

| Shell | 调用方式 | 结果 |
| :--- | :--- | :--- |
| Git Bash | `AutoHotkey64.exe /ErrorStdOut /Validate x.ahk` | 挂死 → 超时，伴随 `ErrorStdOut` 弹窗 |
| pwsh 7.6.9 | `Start-Process -ArgumentList '/ErrorStdOut /Validate "x.ahk"'` | `ExitCode=0`，秒回 |

第二组对照（同机验证 111 原条目场景是否复现）：

```text
Git Bash: cmd /c "echo ok"  ->  打印 banner + 提示符，exit 0（命令没执行）
pwsh 7  : cmd /c "echo ok"  ->  cmd_switch_ok，exit 0（命令执行了）
```

### 2. 为什么它比第三节的 `cmd /c` 更危险

| 维度 | 单次 `cmd /c` 踩坑 | Agent 主 Shell 是 Git Bash |
| :--- | :--- | :--- |
| 影响面 | 一条命令 | **每一次工具调用** |
| 失败形态 | 静默空输出 | 空输出 / 挂死 / 弹窗阻塞，三种变体 |
| 误判方向 | 漏查 | **把环境问题归因为代码缺陷**，并据此"修"不存在的 bug |
| 可发现性 | 低 | 极低：Agent 的唯一判据就是退出码与输出，两者同时被污染 |

Agent 的决策闭环是「下发命令 → 读退出码与输出 → 下结论」。MSYS 转换恰好能在**全程不报警**的前提下把这三环一起污染。

### 3. Agent 主 Shell 选型判据

| 候选 | 判定 | 理由 |
| :--- | :--- | :--- |
| pwsh 7（绝对路径） | ✅ **首选** | 原生解析器：斜杠开关 / 引号 / 编码都不被改写，且支持 `&&` |
| Windows PowerShell 5.1 | ⚠️ 次选 | 无 `&&`、默认编码坑、终端落盘易带 BOM |
| cmd.exe | ⚠️ 兜底 | 无管道链、转义能力弱 |
| Git Bash / MSYS2 | ❌ **禁止作主 Shell** | 参数路径转换系统性失真且静默 |

一句话判据：**Agent 主 Shell 必须是「不会改写参数」的原生 Windows 解析器**；Git Bash 只作为按需显式调用的 POSIX 兜底，且一律走探测到的绝对路径（裸写 `bash` 可能命中 WSL stub）。

### 4. 落地 SOP（以 OpenCode 为例）

1. 编辑 `~/.config/opencode/opencode.json` 根级字段：

   ```json
   "shell": "C:/Users/<User>/AppData/Local/Programs/PowerShell/7/pwsh.exe"
   ```

   不填该字段时 OpenCode 自动回退 pwsh/powershell；**填 `bash` 相对名或 Git Bash 绝对路径属于踩坑配置**。

2. 复核解析结果：

   ```powershell
   opencode debug config | Select-String '"shell"'
   ```

3. 现场确认当前解释器：

   ```powershell
   $PSVersionTable.PSVersion   # 有版本号 = pwsh
   uname -s                    # MINGW64* = Git Bash
   ```

4. 回归断言（切换后必须全部通过，缺一即配置未生效）：

   ```powershell
   cmd /c "echo cmd_switch_ok"                        # 必须打印 cmd_switch_ok
   & $ahk /ErrorStdOut /Validate "<任意 ahk 脚本>"    # 必须 exit 0 且秒回
   ```

5. 需要 POSIX 工具链时按 `GLOBAL.md` §2 兜底探测后显式调用：

   ```powershell
   $bash = (Get-Command git).Source -replace '\\cmd\\git\.exe$','\bin\bash.exe'
   if (-not (Test-Path $bash)) { $bash = "$env:ProgramFiles\Git\bin\bash.exe" }
   & $bash -c 'uname -s'
   ```

### 5. 误判识别信号（写结论前强制自查）

| 症状 | 正确动作 |
| :--- | :--- |
| 命令超时/挂死但零报错 | 先 `Get-Process` 查是否有弹窗（窗口标题常暴露被改写后的参数名） |
| "脚本没改却报语法错" | 换 pwsh 复测同一条命令，再谈代码 |
| 同一命令换 Shell 结果不同 | 结论只能写「执行层差异」，严禁写「代码缺陷」 |
| `$?`/`$LASTEXITCODE` 为空或异常 | GUI 子系统程序（如 AHK）改用 `Start-Process -Wait -PassThru` 取 `ExitCode` |

### 6. 可证伪信号

- 在 pwsh 下执行同一条命令，秒回且 `ExitCode=0` → 问题出在 Shell 层，与本条描述一致
- 在 Git Bash 下命令产出了真实业务输出 → 本次未触发转换（多字母开关如 `/query`、`/fo` 安全）
- 弹窗标题不是被改写后的参数名 → 属其它类型的程序错误，不要套用本节结论
