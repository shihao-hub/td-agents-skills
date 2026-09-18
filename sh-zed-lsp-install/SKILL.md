---
name: sh-zed-lsp-install
description: 修复 Zed 编辑器 GitHub 下载型语言服务器（languages\ 目录：rust-analyzer、gopls 等）的安装失败：rename .tmp-github-download-* 报 os error 5/拒绝访问、反复重新下载、手工装的目录被 Zed 清掉。提供杀毒竞态根因分析、metadata 快速通道绕过、手工安装脚本与零下载验证。当用户提到 Zed 的 rust-analyzer/gopls/语言服务器下载失败、装不上、rename 报错、Access Denied、os error 5 时，务必使用本 skill。
---

# Zed 语言服务器安装失败修复手册（languages\ 目录）

本 skill 沉淀自 2026-08-30 的一次完整排障会话，已在 **rust-analyzer 2026-08-24 + Zed 1.17.2 (stable.349)** 上端到端验证。
与 `sh-zed-opencode-setup` 任务 A（`external_agents\registry\`）是同族杀毒竞态，但 **languages\ 流程多一道 metadata 快速通道，修法不同**——只解压到最终目录会被 Zed 删掉重装，见下文。

## 总原则（每次使用先读）

1. **动手前完全退出 Zed**：运行中的 Zed 会在后台重试安装，流程是"先 `remove_dir_all(目标目录)` 再 rename"——手工放的目录会被它直接删掉。
2. **只解压到最终目录不够，必须补 `.metadata` 文件**：这是与任务 A 的关键差异。`fetch_server_binary` 下载前会读版本目录旁的 `<目录名>.metadata`，摘要一致且 exe 能跑 `--version` 就完全跳过下载。
3. **digest 必须是裸 hex（不带 `sha256:` 前缀）**：GitHub API 返回 `sha256:<hex>`，Zed 内部比较时是去前缀的裸 hex。带前缀写进 metadata 会报 "SHA-256 mismatch" 又触发下载（实测踩过）。
4. **改完必须实证验证**：重启 Zed 后日志零下载才算修好，判据见「验证」节。不要只看目录存在就收工。
5. 本 skill 依赖 Zed 内部实现（1.17.2 锚点），Zed 升级后若行为不符，读 `references/zed-lsp-install-internals.md` 对照新源码。

## 环境路径（按机器解析，不要硬编码）

| 项 | 路径 |
|---|---|
| 语言服务器目录 | `$LOCALAPPDATA/Zed/languages/<server>/<server>-<版本tag>/`（exe 直接在版本目录内）|
| metadata 文件 | 版本目录旁 `<目录名>.metadata`，内容 `{"metadata_version":1,"digest":"<裸hex>"}` |
| metadata 文件名规则 | 模拟 Rust `with_extension("metadata")`：目录名**最后一个 `.` 之后**被替换成 `metadata`（`rust-analyzer-2026-08-24` → `…-2026-08-24.metadata`；若版本带点如 `v1.2.3` 会变成 `v1.2.metadata`，其他服务器要小心）|
| Zed 日志 | `$LOCALAPPDATA/Zed/logs/Zed.log` |

## 诊断（确认属于此问题）

```bash
ls "$LOCALAPPDATA/Zed/languages/rust-analyzer/"    # 空目录或只有 .tmp-* 残留 = 从未成功安装
grep -i "rust-analyzer" "$LOCALAPPDATA/Zed/logs/Zed.log" | tail -5
```

判定特征（三者齐了就是这个病）：
- `ERROR [project::lsp_store] Failed to start language server "rust-analyzer": renaming "…\.tmp-github-download-xxx" to "…\rust-analyzer-<tag>"`，`Caused by: 拒绝访问。 (os error 5)`
- 前一行 `downloading github artifact from https://github.com/…/releases/download/<tag>/…zip`（下载 URL 从这拿）
- 版本目录不存在（失败后 Zed 清理了现场）

根因：Zed 下载 zip → 解压到临时目录 → 杀毒/企业安全软件（如 CorpLink）扫描刚解压的 exe 持有句柄 → rename 报 os error 5 → 清理重试又从头下载，反复输竞态。**注意 `gopls` 等其他 GitHub 下载型服务器目录若也是空的，说明同样从未成功过，同法可修。**

## 修复（绕过 rename，走 metadata 快速通道）

**前置：完全退出 Zed**（`tasklist | grep -i zed` 应为空；有进程则 `taskkill //IM zed.exe` 优雅退出，别加 //F）。

方式一，脚本全自动（rust-analyzer 默认参数，自动查最新版、校验 sha256、写 metadata）：

```bash
bash scripts/zed-lsp-manual-install.sh
```

方式二，带参数（其他服务器或指定版本；三个参数从 Zed.log 的 rename 行和 GitHub API 拿）：

```bash
bash scripts/zed-lsp-manual-install.sh \
  --url https://github.com/rust-lang/rust-analyzer/releases/download/2026-08-24/rust-analyzer-x86_64-pc-windows-msvc.zip \
  --tag 2026-08-24 \
  --digest f6d80045e6f475606f62d294fa3b618304fd24d2ff86160495440f23d5f7fcdb
  # 可选: --server <名> --dir <版本目录名> --repo <owner/name> --asset <asset文件名>
  # digest 从 https://api.github.com/repos/<repo>/releases/latest 拿 asset.digest，去掉 sha256: 前缀
```

手工等效（脚本不可用时）：

```bash
# 1. 下载并校验（sha256 必须等于 GitHub API 的 asset.digest 去前缀值）
curl.exe -L --retry 5 -C - -o "$TEMP/ra.zip" "<zip地址>"
sha256sum "$TEMP/ra.zip"
unzip -t "$TEMP/ra.zip"
# 2. 直接解压到最终目录（不 rename）
mkdir -p "$LOCALAPPDATA/Zed/languages/rust-analyzer/rust-analyzer-<tag>"
unzip -o "$TEMP/ra.zip" -d "$LOCALAPPDATA/Zed/languages/rust-analyzer/rust-analyzer-<tag>"
# 3. 跑一次 --version（让杀毒扫完 + 验证可执行）
"$LOCALAPPDATA/Zed/languages/rust-analyzer/rust-analyzer-<tag>/rust-analyzer.exe" --version
# 4. 写 metadata（关键！digest 裸 hex 无前缀）
printf '%s' '{"metadata_version":1,"digest":"<裸hex>"}' > "$LOCALAPPDATA/Zed/languages/rust-analyzer/rust-analyzer-<tag>.metadata"
```

## 验证（必做）

注意前提：用户全局 `enable_language_server: false`（见 `sh-zed-lsp-config`），Rust 靠项目 `.zed/settings.json` 白名单放开，所以要建带白名单的测试项目才会拉起 rust-analyzer：

```bash
mkdir -p "$TEMP/zed-rust-verify/.zed"
cat > "$TEMP/zed-rust-verify/.zed/settings.json" <<'EOF'
{ "languages": { "Rust": { "enable_language_server": true, "language_servers": ["rust-analyzer"] } } }
EOF
printf '[package]\nname = "zed-rust-verify"\nversion = "0.1.0"\nedition = "2021"\n' > "$TEMP/zed-rust-verify/Cargo.toml
echo 'fn main() { println!("ok"); }' > "$TEMP/zed-rust-verify/main.rs"
cmd //c start "" "C:\Users\<user>\AppData\Local\Programs\Zed\Zed.exe" "$(cygpath -w "$TEMP/zed-rust-verify")"
sleep 30
```

判据（三条全绿才算修好）：
1. `tasklist | grep -i rust` 有 `rust-analyzer.exe`，且 PowerShell `Get-Process rust-analyzer | Select Path` 确认路径是 `languages\rust-analyzer\rust-analyzer-<tag>\rust-analyzer.exe`。
2. 日志出现 `[lsp] starting language server process. binary path: "…\languages\rust-analyzer\…"`。
3. **启动时间点之后日志零** `github_download` / `renaming` / `No cached` 记录（用 `awk '$0 >= "<启动时间>"'` 过滤后 grep）。

验证后清理：关 Zed（`taskkill //IM zed.exe`）→ 删 `$TEMP/zed-rust-verify` 和临时 zip。

## 常见坑速查

| 症状 | 原因/处理 |
|---|---|
| 手工放好目录，重启 Zed 后目录又被清掉 | `download_server_binary` 先 `remove_dir_all(目标)` 再 rename；必须补 `.metadata` 走快速通道让 Zed 根本不进下载流程 |
| 补了 metadata 还是重新下载，日志报 "SHA-256 mismatch" | digest 带了 `sha256:` 前缀；Zed 内部 expected 是裸 hex，去掉前缀重写 |
| 测试时报 "Failed to discover workspace" | 测试项目缺 `Cargo.toml`（裸 .rs 没有 Cargo 工作区），是夹具问题不是安装问题 |
| 下周一又坏了 | rust-analyzer 每周一发版，新 tag digest 不匹配 → 又走下载竞态；重跑脚本即可，或上「治本」方案 |
| 治本（方案 B） | `rustup component add rust-analyzer` 后在 settings 里指定 rustup 的二进制路径，彻底绕开 GitHub 下载。**要改用户 settings，先向用户确认再动** |

## 深入资料

`references/zed-lsp-install-internals.md` —— Zed 源码机制全记录（metadata 快速通道代码、remove_dir_all+rename 竞态、get_cached_server_binary 的 last-entry-wins、digest 格式差异实证、版本锚点）。**Zed 升级后本 skill 行为不符时必读**。
