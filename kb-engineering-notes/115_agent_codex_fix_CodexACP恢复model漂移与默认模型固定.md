---
name: kb-codex-acp-resume-model-drift
description: |
  Zed Codex ACP 恢复旧线程弹 "This session was recorded with model X but is resuming with Y" 警告、状态栏 model 变成新默认的排障；根因是 codex 包更新后内置默认模型漂移，且 resume 路径不吃 Zed default_config_options，用 ~/.codex/config.toml 顶层 model 锚定修复。适用于 model 与配置不一致、Codex 默认模型被静默切换、恢复会话必弹警告等场景。
version: 1.0.0
created: 2026-11-19
updated: 2026-11-19
id: "115"
domain: agent
scope: codex
type: fix
slug: "CodexACP恢复model漂移与默认模型固定"
status: draft
last_verified: "2026-11-19"
compatibility:
  os: ["windows"]
falsification_signals:
  - "若警告不是 'recorded with model ... but is resuming with ...' 模式（如报上下文超限/登录/鉴权），不是本根因，立即退出本 SOP"
  - "若 ~/.codex/config.toml 顶层已有 model 字段且值恰为警告里的 resuming model，说明 Codex 侧默认与漂移无关，另查 Zed 显式传值路径，退出本 SOP"
  - "若警告出现在新建会话而非恢复旧线程，不是 resume 恢复路径问题，退出本 SOP"
invocation:
  auto_trigger: true
  trigger_keywords: ["recorded with model", "but is resuming with", "gpt-6.2-sol", "6.2 Sol", "Codex ACP model 漂移", "Codex 恢复会话 警告", "default_config_options model 不生效", "Codex 默认模型变了"]
---

# agent_codex_fix_115_CodexACP恢复model漂移与默认模型固定

> **条目定位**：**Type A 疑难排障（Zed codex-acp 恢复会话 × Codex 内置默认模型漂移 × config.toml 锚定）**  
> **修复动作**：`~/.codex/config.toml` 顶层加一行 `model = "..."`（可逆、零工具依赖）。  
> **复发预期**：OpenAI 每次切换内置默认模型会复发（vendor codex 随 Zed 自动升级、无感），锚点行是常驻防线。

---

## 一、现象与报错直击

Zed Agent Panel 中 Codex（codex-acp）**恢复旧线程**时顶部横幅：

```text
⚠ This session was recorded with model `gpt-6.1-sol` but is resuming with `gpt-6.2-sol`.
  Consider switching back to `gpt-6.1-sol` as it may affect Codex performance.
```

同时底部输入框旁的 model selector 显示 `6.2 Sol`，而 Zed settings.json 里明确写的是旧模型：

```json
"agent_servers": {
  "codex-acp": {
    "default_config_options": { "model": "gpt-6.1-sol", "reasoning_effort": "high", ... },
    "type": "registry"
  }
}
```

特征：**每次恢复旧线程必现**；新建会话不弹；配置文件无人改动过。现场还出现 `gpt-6.1-terra` 等手动选择过的模型残留。

## 二、底层根因剖析

1. **警告由 Codex CLI 在 resume 时发出**：恢复 rollout 时，Codex 用「当前生效的默认模型」打开旧会话文件；发现 rollout 内记录的 model 与当前默认不一致即提示（rollout 本身不改写，只警告）。
2. **Zed 的 codex-acp 是 registry agent**（settings 中 `"type": "registry"`，不在 `extensions/installed/`），底层 vendor codex 二进制（WMI 取证）：

   ```text
   <Zed数据目录>\external_agents\registry\npx\codex-acp\node_modules\@openai\codex-win32-x64\vendor\x86_64-pc-windows-msvc\bin\codex.exe app-server
   ```

   启动命令行**不带任何 model 覆盖参数**。
3. **`~/.codex/config.toml` 无顶层 `model` 字段** → Codex 当前默认 = codex 包内置默认。2026-11 中旬随 Zed 更新的 codex 运行时（codex-cli 0.164.x）内置默认已从 `gpt-6.1-sol` 切到 `gpt-6.2-sol`。
4. **`default_config_options` 只在新建会话时作为初始 configOptions 发给 agent**；恢复旧线程走 Codex 自身 rollout 恢复路径，不吃这份默认 → 落到新版内置默认 6.2 → 与旧 rollout 记录的 6.1 冲突 → 每次恢复必弹。状态栏 `6.2 Sol` 即恢复后 agent 上报的当前值。
5. **rollout 时间线取证互证**（`~/.codex/sessions/**/rollout-*.jsonl` 中 `"model":"gpt-..."` 按文件修改日汇总）：

   ```text
   2026-11-14: gpt-6.1-sol
   2026-11-18: gpt-6.1-sol, gpt-6.1-terra, gpt-6.2-sol   ← 分水岭
   2026-11-19: gpt-6.1-sol, gpt-6.2-sol
   ```

   11-18 前后 codex 包/桌面端更新换默认，与「配置没改却突然变 6.2」完全吻合。

## 三、标准抢救与修复 SOP

### 步骤 1：只读定位三件套（取证，不改盘）

- **config.toml 顶层有无 model**：读 `C:\Users\<user>\.codex\config.toml` 第一个 `[table]` 之前的部分；
- **Zed 实际拉起的 codex 及参数**（uv run + pywin32 探针，放 %TEMP% 就地迭代）：

  ```python
  # probe_codex.py：WMI 取证 codex.exe 命令行
  import sys, win32com.client
  wmi = win32com.client.GetObject("winmgmts:{impersonationLevel=impersonate}!\\\\.\\root\\cimv2")
  for p in wmi.ExecQuery("SELECT ProcessId, CommandLine FROM Win32_Process WHERE Name='codex.exe'"):
      print(f"[{p.ProcessId}] {p.CommandLine}")
  ```

  ```bash
  uv run --with pywin32 probe_codex.py
  ```

- **rollout model 时间线**：python 单文件正则扫 `"model"\s*:\s*"(gpt-[^"]+)"`，按文件 mtime 分日汇总（同脚本就地迭代）。

### 步骤 2：锚定修复（治本）

在 `~/.codex/config.toml` **顶层（第一个 `[table]` 之前）**追加一行，与 Zed default_config_options 对齐：

```toml
model = "gpt-6.1-sol"
```

> TOML 顶层键必须在首个 `[table]` 之前，写在文件中部会被吞进最近的 table 而静默失效。

效果：Codex 自身默认被钉死 → resume 时当前默认 = rollout 记录值，警告消失；Zed 新会话两侧一致无漂移。副作用：Codex 桌面端/CLI 全局新会话默认同步变为该值（GUI 手动切模型是会话级覆盖，不受影响）。

### 步骤 3（反向，不推荐）：整体升到新默认

Zed settings 与 config.toml 同改 `gpt-6.2-sol`。但旧 rollout 记录 6.1 的会话恢复时仍会警告（resume model ≠ rollout model 就弹），治标不治本。

### 步骤 4：生效

重启 Zed（或关闭重开 codex 会话）——`codex.exe app-server` 常驻，需重启才重读 config.toml。

## 四、验证与防复发闭环

**验证**：
1. 恢复一个旧线程 → 横幅警告消失；
2. 新建会话发一条消息 → 对应 rollout 首行/turn_context 的 model = 配置值；
3. `codex --version` 对照版本，确认漂移起点版本。

**防复发**：
- OpenAI 每次切换内置默认模型即复发：vendor codex 随 Zed registry 自动升级、用户无感；config.toml 顶层 model 是**常驻锚点**，无需再动 Zed；
- Codex 桌面端会自行重写 config.toml（外观、plugins 等），大版本更新后复查锚点行是否仍在；
- 复验通过后 `kbman touch 115` 刷新时序；若被现场证伪则 `kbman report 115 --status suspect --reason "..." --append "现场证据"`。

---
