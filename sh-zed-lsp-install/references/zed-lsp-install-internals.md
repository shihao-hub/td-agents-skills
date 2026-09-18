# Zed 语言服务器安装机制源码解析（版本锚点：Zed 1.17.2 / stable.349.c8e44cfa7bda9b2e）

排障会话：2026-08-30，rust-analyzer 2026-08-24，Windows + 企业杀毒环境。
本文记录源码级机制与实证日志，**Zed 升级后本 skill 行为不符时，按此思路对照新源码重验**。

涉及文件（v1.17.2 tag）：
- `crates/languages/src/rust.rs`（RustLspAdapter，~L800-935、L1402-1443）
- `crates/http_client/src/github_download.rs`（下载与 rename，~L18-41、L221-223）

## 1. 安装/启动决策链（为什么手工放目录会被删）

`fetch_server_binary`（rust.rs）每次启动语言服务器都会走：

```rust
let destination_path = container_dir.join(format!("rust-analyzer-{name}")); // name = release.tag_name
let server_path = ... AssetKind::Zip => destination_path.join("rust-analyzer.exe");

// ① metadata 快速通道：命中则直接返回，完全不下载
let metadata_path = destination_path.with_extension("metadata");
let metadata = GithubBinaryMetadata::read_from_file(&metadata_path).await.ok();
if let Some(metadata) = metadata {
    if let (Some(actual_digest), Some(expected_digest)) = (&metadata.digest, &expected_digest) {
        if actual_digest == expected_digest {
            if validity_check().await.is_ok() {   // try_exec(--version)
                return Ok(binary);                // ← 修复目标：让流程走到这里
            }
        } else {
            log::info!("SHA-256 mismatch for {destination_path:?} asset, downloading new asset. ...");
        }
    } else if validity_check().await.is_ok() { return Ok(binary); }
}

// ② 否则走下载：download_server_binary(...) → remove_matching 清旧版本目录 → 写 metadata
```

`download_server_binary`（github_download.rs L221-223）尾部：

```rust
_ = async_fs::remove_dir_all(destination_path).await;  // 先无条件删目标目录！
async_fs::rename(staging_path, destination_path)        // 再 rename；杀毒持有 staging 内 exe 句柄 → os error 5
```

**推论**：
- 只手工解压到最终目录（不写 metadata）→ 快速通道不命中 → 走下载 → `remove_dir_all` 把手工目录删掉 → rename 又输杀毒竞态 → 无限循环。实测验证（2026-08-30 02:42 手工目录被删）。
- rename 失败后 staging 被清理，重试从下载从头来（无断点续传意义上的复用）。

## 2. digest 格式差异（最大的坑）

- GitHub API `releases/latest` 的 asset 字段：`"digest": "sha256:f6d80045…"`（带前缀）。
- Zed 内部 `expected_digest` 是**去前缀的裸 hex**。实证日志（metadata 写了带前缀的值）：

```
INFO [languages::rust] SHA-256 mismatch for "…\rust-analyzer-2026-08-24" asset, downloading new asset.
Expected: f6d80045e6f475606f62d294fa3b618304fd24d2ff86160495440f23d5f7fcdb,
Got: sha256:f6d80045e6f475606f62d294fa3b618304fd24d2ff86160495440f23d5f7fcdb
```

- Zed 自己成功安装后写回的 metadata（98 字节）：`{"metadata_version":1,"digest":"f6d80045…"}` —— 裸 hex，`metadata_version` 为数字 1。
- `sha256_matches`（大小写不敏感比较）只用于下载流式校验，metadata 快速通道用的是严格字符串 `==`，所以前缀和大小写都不能错（小写最稳）。

## 3. GithubBinaryMetadata 结构（github_download.rs L18-41）

```rust
#[derive(serde::Deserialize, serde::Serialize, Debug)]
pub struct GithubBinaryMetadata {
    pub metadata_version: u64,
    pub digest: Option<String>,
}
// read_from_file = async_fs::read_to_string + serde_json::from_str（无 rename_all，字段名原样）
// write_to_file  = serde_json::to_string + async_fs::write
```

无 `#[serde(rename_all)]` → JSON 字段名就是 `metadata_version` / `digest`。

## 4. get_cached_server_binary（rust.rs L1402+，次要路径）

```rust
let mut last = None;
let mut entries = fs::read_dir(&container_dir)...;
while let Some(entry) = entries.next().await {
    let path = entry?.path();
    if path.extension().is_some_and(|ext| ext == "metadata") { continue; }  // 跳过 *.metadata
    last = Some(path);                                                       // readdir 顺序最后一个赢
}
// Zip ⇒ 返回 last.join("rust-analyzer.exe")；不校验文件是否存在
```

要点：只列容器目录、跳过 `*.metadata`、**最后一个条目胜出**、不校验存在性、不跑 `--version`。启动主路径走的是 `fetch_server_binary`（含快速通道），此函数用于别的路径（如实测中 rename 失败后的重试会打 "No cached rust-analyzer binary found"）。

## 5. with_extension 陷阱（跨服务器泛化时注意）

`destination_path.with_extension("metadata")` 把目录名**最后一个 `.` 之后**替换为 `metadata`：
- `rust-analyzer-2026-08-24`（日期 tag 无点）→ `rust-analyzer-2026-08-24.metadata` ✓
- 假如某服务器版本目录是 `gopls-v1.2.3` → metadata 文件名是 `gopls-v1.2.metadata`（不是 `gopls-v1.2.3.metadata`）！

其他 GitHub 下载型服务器（gopls 等）大概率共用 `http_client::github_download` 这套机制，但**仅在 rust-analyzer 上实证过**；gopls 目录为空说明它在本机同样从未安装成功。泛化使用时：目录名/tag 从 Zed.log 的 rename 报错行拿（权威），metadata 文件名按 with_extension 规则推。

## 6. 2026-08-30 会话时间线（worked example）

| 时间 | 事件 |
|---|---|
| 01:30 | 用户环境首次失败：下载→rename os error 5，目录空 |
| 02:41 | 手工解压到 `rust-analyzer-2026-08-24/`（未写 metadata），exe `--version` 正常 |
| 02:42 | 启动 Zed 验证：仍走下载，`remove_dir_all` 删掉手工目录，rename 又输竞态 → 同款报错 |
| 02:47 | 读源码定位 metadata 快速通道；写**带 `sha256:` 前缀**的 metadata → "SHA-256 mismatch" 又触发下载；该轮竞态 Zed 赢了：下载 4s 完成、rename 成功、Zed 自己写回**裸 hex** metadata，服务器正常启动 |
| 02:50 | 重启验证：`[lsp] starting language server process`，路径正确，**零** github_download/renaming/No cached → 修复确认 |

（skill 脚本即把 02:41-02:47 的弯路拉直：校验 sha256 → 解压 → 跑 `--version` → 写裸 hex metadata，一次性完成。）
