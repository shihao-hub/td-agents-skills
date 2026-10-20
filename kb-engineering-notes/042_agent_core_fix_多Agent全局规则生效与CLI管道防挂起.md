---
name: kb-multi-agent-global-sync-probe-verification
description: 多 Agent（Codex、Claude Code、OpenCode、Pi、DSH、AGY）全局指令分发、Windows 子进程标准输入管道挂起（readPipedStdin / 600s 超时）排障、以及基于独立目录隔离探针（Print Mode / < NUL）的端到端生效性验证指南。当遇到命令行调用 Agent CLI 卡死、探针问答参数不兼容、或需验证跨端全局规则是否真实生效时查阅。
version: 1.0.0
created: 2026-10-11
updated: 2026-10-11
id: "042"
domain: agent
scope: core
type: fix
slug: "多Agent全局规则生效与CLI管道防挂起"
status: verified
last_verified: "2026-10-20"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: true
---

# 42-多Agent全局规则跨端分发与CLI管道防挂起及隔离探针验证指南

> **适用场景**：  
> 当维护多个 AI 编程智能体（Claude Code、OpenCode、Pi Coding Agent、Antigravity CLI、Codex 等）时，需要将单一大模型基线规范（如 `GLOBAL.md`）分发到各工具的全局注入点，并通过命令行自动化发起非交互式（Print Mode）探针，实测全局规范是否已真实成为模型的原生系统提示词认知。特别适用于遭遇 CLI 子进程挂起超时（600s）、标准输入未闭合、终端编码乱码、以及探针误判本地仓库规则等技术痛点。

---

## 一、现象与报错直击

在使用外部自动化脚本、Subprocess 或 PowerShell 命令链调用各类 Agent CLI 进行探针验证时，常见以下四类典型故障：

### 1. 子进程调用 `pi -p` 无限等待并超时（600s Command timed out）
```text
Encountered error in step execution: Command timed out, needed to complete in 600s. 
This timeout applies to all commands. You won't be able to run this command with these arguments: command timed out
```
- **表面现象**：在后台子进程或 PowerShell 管道中调用 `pi -p "query"`，终端没有任何输出，进程持续占用内存与 CPU 句柄，直至触发系统硬超时。

### 2. `agy -p` 参数解析失败（unexpected argument / flag needs an argument）
```text
Error: unexpected argument "Answer".
Prompts are read only from -p/--print, -i/--prompt-interactive, or stdin, so this argument would have been ignored.
```
或：
```text
flag needs an argument: -p
Usage of agy.exe:
  -p, --print    Run a single prompt non-interactively and print the response
```
- **表面现象**：不同 Agent CLI 对 `-p` / `--print` 的定义各异，部分将 `-p` 视为接收 prompt 字符串的参数项，部分将其视为布尔开关，若参数传递格式或外层引号嵌套不当，直接导致命令行解析中断。

### 3. 跨进程管道流中文乱码（`?????????`）
```text
收到的消息内容显示为乱码（全是不明问号 ????????????），只能隐约看出包含两条编号内容（1. ... 2. AI ...），无法判断您的实际需求。
```
- **表面现象**：通过 PowerShell 管道 `| claude -p` 时，Windows 默认控制台代码页（CP936/GBK）导致管道流数据被破坏，下游 LLM 接收到一连串问号，导致探针无法得到预期答复。

### 4. 探针验证中的“虚假阳性（False Positive）”
- **表面现象**：在 Monorepo 仓库根目录下执行探针测试时，Agent 成功回答了规则问题。但实际上模型加载的是当前仓库下的局部 `AGENTS.md`，而非系统全局的 `GLOBAL.md`；一旦在其他空目录运行该 Agent，规则完全失效。

---

## 二、底层根因剖析

### 1. 各 Agent Harness 全局指令发现机制源码对照

各主流 Agent 对全局指令文件的检索位置与加载策略存在本质差异：

| Agent 工具 | 源码级检索实现路径 | 宿主全局注入文件路径 | 仓库级局部继承方式 |
| :--- | :--- | :--- | :--- |
| **Pi Coding Agent** | `@earendil-works/pi-coding-agent`<br>[`dist/core/resource-loader.js`](file:///D:/nvm4w/nodejs/node_modules/@earendil-works/pi-coding-agent/dist/core/resource-loader.js) | `~/.pi/agent/AGENTS.md` | 先装载 agentDir 下全局文件，再逐级向上检索 cwd 及其父目录的 `AGENTS.md` |
| **Claude Code** | `@anthropic-ai/claude-code` | `~/.claude/CLAUDE.md` | 启动时自动注入用户主目录下全局 `CLAUDE.md`，并叠加当前项目的 `CLAUDE.md` |
| **OpenCode** | `opencode-ai`<br>二进制内嵌规则查找机制 | `~/.config/opencode/AGENTS.md`<br>*(兼读 `~/.claude/CLAUDE.md`)* | 自动读取 `config/AGENTS.md`，同时向上检索 `worktree` 根目录 `AGENTS.md` |
| **Antigravity CLI** | `agy.exe` (Go/Rust 编译) | `~/.gemini/AGENTS.md`<br>`~/.gemini/config/AGENTS.md` | 自动合并全局 `AGENTS.md` 与工作区 `AGENTS.md` |
| **Codex** | `@openai/codex` | `~/.codex/AGENTS.md` | 自动合并全局指令与项目局部配置 |
| **DeepSeek Harness** | `dsh` | `~/.dsh/AGENTS.md` | 自动读取主目录下的全局约束基线 |

> **架构启示**：由于各 Harness 均原生支持全局指令合并，因此通用规范（语言规范、PowerShell 安全、Token 经济、不变式架构）只需由 `GLOBAL.md` 作为单一真理来源（SSOT）软链接至上述注入点，即可达成 100% 覆盖。

### 2. 子进程管道挂起机理：`readPipedStdin()` 与未决的 EOF

以 `pi` 的 CLI 启动引导逻辑为例（[`dist/bundle/chunks/chunk-OIM2DMFI.js`](file:///D:/nvm4w/nodejs/node_modules/@earendil-works/pi-coding-agent/dist/bundle/chunks/chunk-OIM2DMFI.js)）：
```javascript
let stdinContent;
if (appMode !== "rpc") {
    stdinContent = await readPipedStdin();
    if (stdinContent !== undefined && appMode === "interactive") {
        appMode = "print";
    }
}
```
- **阻塞机制**：Node.js 检测到标准输入不是交互式 TTY（如运行在自动化 Subprocess 中）时，会调用 `readPipedStdin()` 尝试读取管道内容。
- **未决原因**：在 Windows PowerShell 下以非交互模式唤起子进程时，PowerShell 赋予子进程的标准输入流句柄处于“开启且无数据”状态，并未发送 EOF（End-Of-File）。`readPipedStdin()` 的 Promise 会永远处于 `pending` 状态，最终导致死锁挂起。

### 3. 本地配置项对探针延迟的倍增效应
- **Thinking / Reasoning 档位**：若 `settings.json` 中配置了高思考档位（如 `defaultThinkingLevel: high`），模型在输出最终答案前需要生成大量推理 Token，可能耗费数十秒；
- **MCP / 插件扩展探测**：部分 Agent 在 Print Mode 下仍默认启动配置的 MCP 客户端（如 `aoci`、`feishu-bridge`），会额外增加启动握手耗时。

---

## 三、标准抢救与验证 SOP

### 步骤 1：闭环管道防挂起与编码统一标准模板
在通过命令行、Subprocess 或测试脚本自动化调起 Agent CLI 时，**必须使用 `< NUL` 主动发送 EOF**，并显式指定 UTF-8 编码流：

```powershell
# PowerShell 环境下安全执行范式：
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 借助 cmd /c 与 < NUL 强制闭合标准输入流
cmd /c "<Agent_CLI_Command> < NUL"
```

### 步骤 2：建立 100% 独立的隔离探针环境
为确保测试命中且仅命中 `GLOBAL.md`，**必须脱离当前仓库目录**，在无任何本地 `AGENTS.md` / `CLAUDE.md` 的独立临时目录下运行：

```powershell
# 切换至系统临时目录
Set-Location -Path $env:TEMP
```

### 步骤 3：多端 Agent CLI 隔离探针单行执行命令

以下命令均经过 Windows 实机真机验证，可直接复制执行，验证全局规则内化情况：

#### 1. Pi Coding Agent (`pi`)
```powershell
cmd /c "node D:\nvm4w\nodejs\node_modules\@earendil-works\pi-coding-agent\dist\bundle\cli.js --no-mcp --no-extensions --thinking off -p \"根据你的全局规则，文件名内部严禁包含什么字符？应使用什么代替？\" < NUL"
```
* **参数要点**：`--no-mcp --no-extensions` 禁用冗余插件，`--thinking off` 开启秒级响应，`< NUL` 彻底防止管道挂起。

#### 2. Claude Code (`claude`)
```powershell
cmd /c "claude -p \"根据你的全局规范（CLAUDE.md），文件名内部严禁包含什么字符？应使用什么代替？\" < NUL"
```
* **参数要点**：`-p` 原生进入 Print Mode，`< NUL` 避免 3 秒 stdin 等待告警。

#### 3. OpenCode (`opencode`)
```powershell
cmd /c "opencode run -m deepseek/deepseek-flash \"根据你的全局 AGENTS.md 规范，文件名内部严禁包含什么字符？应使用什么代替？\" < NUL"
```
* **参数要点**：`run` 子命令进入非交互模式，显式指定 `-m` 快速模型跳过供应商交互提示。

#### 4. Antigravity CLI (`agy`)
```powershell
agy -p "根据你的全局 AGENTS.md 规范回答：文件名内部严禁包含什么字符？应使用什么代替？" --model gemini-3.8-flash-low
```
* **参数要点**：`-p` 必须紧跟单引号提示词，显式指定 `--model` 轻量模型。

---

## 四、验证断言与防复发建议

### 1. 探针有效性验证基线（必须全部满足）
- [x] **目录隔离性**：执行探针的工作目录（cwd）不存在任何名为 `AGENTS.md` 或 `CLAUDE.md` 的文件；
- [x] **准确溯源性**：Agent 能准确指出其约束来源于其宿主全局目录（如 `~/.pi/agent/AGENTS.md`、`~/.claude/CLAUDE.md` 等）；
- [x] **条款专属性**：Agent 能准确说出 `GLOBAL.md` 中的独特规定（例如“文件名禁止 `/` 和 `\`，只能用 `-` 或 `_`”、“PowerShell 无 BOM UTF-8 落盘”、“禁止复述事实”等）；
- [x] **秒级响应性**：配合 `< NUL` 与轻量思考档位，单次探针应在 5~15 秒内完成，无任何卡顿。

### 2. 跨端规则一致性防复发建议
1. **单一真理来源（SSOT）**：永远在 `D:\Users\language_projects\GLOBAL.md` 单一文件维护通用规则；
2. **符号链接直连**：在 Windows 开启开发者模式后，使用软链接（Symlink）直连各全局路径，修改源文件即全端即时生效：
   ```powershell
   uv run D:\Users\language_projects\.scripts\sync-agent-rules.py --status
   ```
3. **消除仓库级重复**：仓库级 `AGENTS.md` 仅声明本 Monorepo 专属的技术栈规范与上下文指针，严禁复制粘贴全局条款，彻底规避 Double Context Tax。
