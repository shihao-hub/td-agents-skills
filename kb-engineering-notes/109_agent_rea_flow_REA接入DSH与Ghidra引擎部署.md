---
name: kb-rea-dsh-ghidra-deployment
description: REA 逆向 MCP 工具在 Windows 上的源码部署与 DSH 接入（Cordis patch），含 Ghidra 12.1.x 引擎配置，覆盖 Node 版本闸、原生插件、tag 字节不等、unblob 非法名等 8 个静默坑。何时查阅：provider_unavailable、unsupported_version、EBADENGINE，或要给 DSH 挂 stdio MCP。
version: 1.0.0
status: verified
created: 2026-11-01
last_verified: 2026-11-01
superseded_by: null
deprecation_reason: null
compatibility:
  os: ["windows"]
  tools: ["rea-agents", "dsh", "ghidra", "node"]
falsification_signals:
  - "若 rea doctor 报 provider_unavailable 但 candidate_ids 里没有 ghidra/hopper/ida 三者，说明不是引擎缺失而是目标格式根本不走深度引擎，立即退出本 SOP，改用不需要引擎的静态能力"
  - "若 Hopper 检查报 unsupported_host 且平台是 win32，这是设计事实不是配置缺失，不要再尝试装 Hopper 或设 HOPPER_LAUNCHER_PATH"
  - "若 Ghidra 报 unsupported_version 且实测版本号是 12.2 及以上，说明该 REA 版本只认 12.1.x 行，降级到 12.1.4 而不是改环境变量硬绕"
  - "若 dsh --dump-config 输出里搜不到 mcp-rea，先确认改的是 $DSH_HOME/cordis.patch.yml 而非某个 profile 目录下的同名文件"
invocation:
  auto_trigger: true
  trigger_keywords: ["REA 安装", "rea-agents", "MCP 逆向工具", "DSH 挂 MCP", "cordis.patch.yml", "Ghidra 配置", "GHIDRA_INSTALL_DIR", "provider_unavailable", "unsupported_version", "EBADENGINE", "engine-strict", "rea-windows-x64.node", "reverse-engineer-anything"]
---

# REA 源码部署并只接入 DeepSeek Harness + Ghidra 引擎全流水线

## 一、业务场景与交付目标

**输入源**：Windows 10/11 x64 机器，已有 Node（可能多版本共存于 nvm-windows）、已有 JDK 21+、只有 DSH 作为 agent 宿主。

**交付目标**：

1. REA 源码落在指定目录（本例 `D:\Users\Softwares\rea`），可跑 CLI 与 MCP server；
2. **只**注册到 DSH，不污染 Claude Code / Codex / Cursor 等「每会话拉起 MCP 进程」的客户端；
3. 装好深度分析引擎，使反编译/伪代码/交叉引用可用；
4. 全部配完**只需重启一次** DSH 即生效。

**为什么只挂 DSH**：stdio MCP server 是会话级拉起的，每开一个新会话就 spawn 一个 node 进程；DSH 是常驻进程、MCP client 只起一次。REA 的 MCP server 有 170 个工具定义，多客户端注册的边际成本是每次会话重复付。

## 二、八个坑的根因剖析

### 坑 1：Node 版本是硬闸，不是建议

REA `package.json` 的 engines 为 `^22.19.0 || ^24.11.0 || >=26.0.0`，且仓库自带 `.npmrc` 里是 `engine-strict=true`。**全局 Node 若为 24.10.0 会直接 EBADENGINE 拒装**。注意 `24.18.0`（仓库 `.nvmrc`）与 `22.20.0` 都合规，但 `24.10.0` 不合规——25.x/23.x 也不支持。

### 坑 2：不要用 `nvm use` 切全局（DSH 会消失）

nvm-windows 的 `nvm use` 改写的是 `~\AppData\Local\nvm` 下 `nodejs` 软链（形如 `D:\nvm4w\nodejs` → `...\nvm\vX.Y.Z`）。而 **DSH 自身的全局包只装在某个具体版本目录下**（如 `...\nvm\v24.10.0\node_modules\@deepseek-ai\dsh`）。切走软链 = `dsh` 命令与其依赖一起失联。

**正确做法**：不切全局，用**绝对路径**钉住 Node，两条路径都钉：

- CLI 手敲：PATH 前缀或包装脚本；
- MCP 拉起：在注册配置的 `command` 里直接写 node 绝对路径。

### 坑 3：源码检出不含预编译原生插件，且 Windows 无法本地编译

`native/windows/build/` 被 `.gitignore` 覆盖，clone 拿不到 `rea-windows-x64.node`；而 `npm run build:windows-native` 会直接抛错「requires Linux and MinGW-w64」——这是该构建 lane 的硬性平台约束。

**解法**：从 npm 发布包里取预编译产物。发布包 `files` 字段明确包含 `native/windows/build/manifest.json` 与 `rea-windows-x64.node`。

### 坑 4（最隐蔽）：tag 与 npm tarball 字节不等，版本号却相同

**现象**：`npm run verify:windows-native` 在 main HEAD 上失败，报错为断言某个 `PrivateRuntimeRootUnavailableError` 未命中；但同一份 `.node` 在切到 release tag 后立刻 `ok:true`。

**根因**：main HEAD 比 release tag 超前数百个提交，其中多个提交改动了 `native/windows`（典型如把 `FILE_SHARE_DELETE` 加入共享语义），导致 **JS 侧期望的行为**与**发布时刻编译的原生插件行为**漂移。而两边的 `package.json` 版本号都是同一个（release-please 只在发版时 bump），所以 `WindowsNativeLoader` 的版本闸门（比对 `manifest.packageVersion` 与 `PACKAGE_METADATA.version`）**完全拦不住**——这是一次静默不一致。

REA 官方文档自己就警告过：*"The same package version string in a development checkout does not establish that its bytes match the npm tarball."*

**解法**：源码路线必须**锁定到 release tag**，让源码与预编译原生插件同源同版；切 tag 后重跑 `npm ci` + 构建 + `verify:windows-native` 验证。

### 坑 5：`unblob` 子模块在 Windows 上必然检出失败

`third_party/unblob` 的测试夹具有 `?`、`"` 等 **NTFS 非法字符**。git 在**写入 index 阶段**就报 `error: invalid path`，所以：

- `git submodule update --init` 失败；
- `sparse-checkout` 也救不了——它只跳过**工作树写入**，index 仍要记录全部路径，`git reset` 同样报错。

**结论**：这是平台硬限制，不要反复尝试。且 REA 的 Binwalk/Unblob 集成本身只在 Linux 生效，Windows 上不影响任何功能。要清理 `git status` 可 `git submodule deinit third_party/unblob`。

### 坑 6：DSH 不在 `setup --client` 白名单，必须手写 Cordis patch

REA 的 `setup --client` 只认 17 个客户端 ID（`claude_code`/`codex`/`cursor`/`gemini_cli`/`opencode`/`antigravity`/`vscode`/`pi`/`hermes`…），**不含 DSH**。官方文档明确写：*"DeepSeek Harness uses a Cordis YAML patch sequence rather than a `mcpServers` object. REA's `setup --client` does not edit this format."*

所以 `doctor` 会**检查** DSH 注册（`registration:dsh`）但 `setup` **不会写**它；而 `doctor --client dsh` 会直接报 `Unsupported agent integration`（白名单校验）。

**落位选择**：写 **home 层** `$DSH_HOME/cordis.patch.yml`（未设 `DSH_HOME` 时为 `~/.dsh/cordis.patch.yml`）。DSH 源码注释写明该层 *"applied over every profile's own layer"*，即对 `acp`/`desktop`/`web` 全部生效，且不动用户已有的 profile 定制。该文件是 `loadOptionalPatches` **可选加载**，不存在也不报错，可安全新建。

### 坑 7：Ghidra 只认 12.1.x 行，装最新版会被拒

REA 源码里 `SUPPORTED_GHIDRA_VERSION = "12.1.4"`，并明确「other **12.1.x** builds are accepted」——同属 12.1.x 的小版本（12.1.2/12.1.3/12.1.4）都收，但 **12.2 属于下一个 release line，会判 `unsupported_version`**。

判定依据是安装目录的 `Ghidra\application.properties` 里的 `application.version`，同时读 `application.java.min` / `application.java.max` 校验 JDK 边界（12.1.4 为 `min=21`、`max` 空即无上限）。

### 坑 8：`GHIDRA_INSTALL_DIR` 的时序与环境污染

`[Environment]::SetEnvironmentVariable(..., "User")` 写的用户级变量**只有在宿主进程重启后**才会进入其环境；而 `dsh-mcp-client` 对 stdio 子进程还有环境清理逻辑。若只靠用户级变量，重启后 MCP 子进程仍可能拿不到。

**解法**：双保险——既写用户级持久变量（`doctor` 等 CLI 场景用），又在 patch 的 `config.env` 里显式下发（MCP 子进程用）。

## 三、标准自动化流水线

### 步骤 1：锁定 release tag 检出

```powershell
git clone https://github.com/morluto/rea.git "D:\Users\Softwares\rea"
cd "D:\Users\Softwares\rea"
# 关键：不要停在 main HEAD，切到与预编译原生插件同源的发布 tag
git tag --list | Select-String "rea-agents-"
git checkout "rea-agents-6.4.0"
```

### 步骤 2：用合规 Node 做确定性安装与构建

```powershell
$env:PATH = "D:\Users\29580\AppData\Local\nvm\v22.20.0;" + $env:PATH
node --version   # 必须满足 ^22.19 || ^24.11 || >=26
npm ci --no-audit --no-fund
npm run build:cached     # turbo: metadata:check -> compile -> artifacts:skills
# 产物布局随版本而异：tag 版为 dist\cli.js / dist\main.js（tsc 直出）
```

### 步骤 3：从 npm 包提取预编译原生插件

```powershell
$tmp = "D:\Users\Softwares\rea\.pack-tmp"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
cd $tmp
npm pack rea-agents@6.4.0 --silent
tar -xzf rea-agents-6.4.0.tgz
Copy-Item "$tmp\package\native\windows\build\*" "D:\Users\Softwares\rea\native\windows\build\" -Force
cd "D:\Users\Softwares\rea"
npm run verify:windows-native:artifact   # 静态：SHA-256 / PE32+ / NAPI
npm run verify:windows-native            # 运行时：应为 {"ok":true,...}
Remove-Item $tmp -Recurse -Force
```

### 步骤 4：装 agent skill（不装则模型不懂方法论）

```powershell
node scripts\rea.mjs setup --skill --dry-run --json   # 先看计划，仅 install_skill
node scripts\rea.mjs setup --skill --yes
# 落到 ~/.agents/skills/reverse-engineer-anything（SKILL.md + 6 个 references）
node scripts\rea.mjs doctor --skill --json           # 期望 state: aligned
```

### 步骤 5：装 Ghidra 12.1.x 并校验

```powershell
$url = "https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_12.1.4_build/ghidra_12.1.4_PUBLIC_20260921.zip"
curl.exe -L --retry 3 -sS -o "D:\Users\Softwares\ghidra_12.1.4.zip" $url
(Get-FileHash "D:\Users\Softwares\ghidra_12.1.4.zip" -Algorithm SHA256).Hash.ToLower()
# 必须与官方 release digest 一致（12.1.4 为 ddac49f9...d2d4db）
Expand-Archive -LiteralPath "D:\Users\Softwares\ghidra_12.1.4.zip" -DestinationPath "D:\Users\Softwares" -Force
# 确认版本行与 Java 边界
Get-Content "D:\Users\Softwares\ghidra_12.1.4_PUBLIC\Ghidra\application.properties" |
  Select-String '^application\.(version|java\.)'
```

### 步骤 6：写 DSH home 层 patch

```yaml
# $DSH_HOME/cordis.patch.yml（~/.dsh/cordis.patch.yml）
- insert:
    - id: mcp-rea
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: rea                     # 须匹配 ^[A-Za-z0-9_-]{1,32}$，工具名将是 mcp__rea__*
        transport: stdio
        command: 'D:\...\nvm\v22.20.0\node.exe'   # 绝对路径，绕开 engine-strict 与 PATH
        args:
          - 'D:\Users\Softwares\rea\scripts\rea.mjs'
          - mcp                            # 必须恰好是 ["<rea.mjs>", "mcp"]，脚本内按 argv.slice(2).length===1 判定
        cwd: 'D:\Users\Softwares\rea'
        env:
          GHIDRA_INSTALL_DIR: 'D:\Users\Softwares\ghidra_12.1.4_PUBLIC'
        failOnStartupError: false          # REA 起不来只让工具不可用，不拖垮 DSH 启动
        toolCallTimeoutMs: 600000          # Ghidra 首次全量分析远超默认 60s
```

同时写持久环境变量（供 CLI 侧 doctor 使用）：

```powershell
[Environment]::SetEnvironmentVariable("GHIDRA_INSTALL_DIR","D:\Users\Softwares\ghidra_12.1.4_PUBLIC","User")
```

## 四、交付验证与扩展建议

### 四层验证（逐层加深，全部可复现）

| 层 | 命令 | 期望 |
|---|---|---|
| 1 语法 | 用 `yaml` 解析 patch + 查前 3 字节 | 解析 OK 且**不含 BOM**（`EF BB BF`），严格 YAML 配置带 BOM 会导致加载失败 |
| 2 合成 | `dsh --profile web --dump-config` | 输出里出现 `mcp-rea` 且 config 完整 |
| 3 握手 | 临时探针 spawn `node rea.mjs mcp`，发 `initialize` + `tools/list` | `serverInfo.name=rea`，工具数 170 |
| 4 端到端 | `node scripts\rea.mjs analyze "C:\Windows\System32\notepad.exe" --format json` | `provider=rea-workflow`，`procedure_count≈853`、`string_count≈638` |

**第 3 层做法**：写临时 `.mjs` 到 `%TEMP%`（不要落仓），`child_process.spawn` 子进程；`initialize` 后补发 `notifications/initialized` 再 `tools/list`；收集 stdout 按行 JSON 解析；超时即 `child.kill()`；用完删除。

**注意 `doctor` 的输出陷阱**：`doctor --provider` / `--client` 会展开完整工具效果表（十万字符级）。**必须加 `--json` 并在脚本里只取 `scope_checks` / `providerInspections` 字段**，否则会把大量无用内容灌进模型上下文。

### 扩展建议

- **上下文成本**：170 个工具定义每轮都进上下文。若嫌重，在 patch 的 `env` 里加 `REA_MCP_INPUT_SCHEMA_PROFILE: compact`——只精简工具广告中的嵌套 schema 约束，REA 仍完整校验输入，功能不减。此项会改变模型可见的参数约束，建议实测后再决定。
- **按目标补外部工具**（都不影响 MCP 通道本身）：Android → JADX + JDK / adb / Apktool；pcap → tshark（仅 Linux 验证）；WASM → WABT 1.0.42；固件 → Binwalk/Unblob（仅 Linux）。
- **Windows 上永远不可用的能力**，不要浪费时间配置：Hopper（`unsupported_host`）、pwntools/pwndbg/GDB、sigrok-cli、Binwalk/Unblob、macOS 原生（Mach-O/plist/codesign/Swift demangle）、PTY 进程捕获。
- **不需要引擎就能用的能力**：JS/Electron 静态分析、.NET 元数据、PE 结构/资源、Go 二进制、网页与抓包、证据管理——这类工具在没装任何引擎时也可正常返回。实测基线：`inspect-pe-resources notepad.exe` → 31 资源 / 4 icon group / coverage complete。

### 卸载与回滚

```powershell
# 只摘掉 DSH 注册：删除 $DSH_HOME/cordis.patch.yml 中的 mcp-rea 条目（或整文件）
# 卸载 skill
node scripts\rea.mjs uninstall --skill
# 撤环境变量
[Environment]::SetEnvironmentVariable("GHIDRA_INSTALL_DIR", $null, "User")
```
