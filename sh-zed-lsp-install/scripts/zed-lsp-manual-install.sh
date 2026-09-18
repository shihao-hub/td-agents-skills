#!/usr/bin/env bash
# Zed 语言服务器手工安装：绕过 rename 杀毒竞态 + 补 metadata 快速通道
# 实证环境：Windows Git Bash + Zed 1.17.2 + rust-analyzer 2026-08-24（2026-08-30 验证）
#
# 用法：
#   bash zed-lsp-manual-install.sh                          # rust-analyzer 最新版全自动
#   bash zed-lsp-manual-install.sh --url U --tag T --digest D [--server S] [--dir B] [--repo O/R] [--asset A]
#     三参数来源：Zed.log 的 rename 报错行（tag/目录名）+ GitHub API releases/latest（digest）
#     digest 允许带 sha256: 前缀，脚本会自动去掉
set -euo pipefail

SERVER="rust-analyzer"
REPO="rust-lang/rust-analyzer"
ASSET="rust-analyzer-x86_64-pc-windows-msvc.zip"
URL=""; TAG=""; DIGEST=""; DIRNAME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)    URL="$2"; shift 2 ;;
    --tag)    TAG="$2"; shift 2 ;;
    --digest) DIGEST="$2"; shift 2 ;;
    --server) SERVER="$2"; shift 2 ;;
    --dir)    DIRNAME="$2"; shift 2 ;;
    --repo)   REPO="$2"; shift 2 ;;
    --asset)  ASSET="$2"; shift 2 ;;
    *) echo "未知参数: $1（支持 --url --tag --digest --server --dir --repo --asset）" >&2; exit 1 ;;
  esac
done

# 前置：Zed 必须完全退出，否则后台重试安装会先 remove_dir_all 目标目录再 rename，
# 把本脚本装的目录删掉（Zed 1.17.2 http_client/github_download.rs:222）
if tasklist 2>/dev/null | grep -qi "zed\.exe"; then
  echo "错误：Zed 正在运行。请先完全退出（taskkill //IM zed.exe）再执行本脚本。" >&2
  exit 1
fi

# 缺任一关键参数则从 GitHub API 取最新 release 补全三个（node 解析 JSON；python 可能是商店 stub，勿用）
if [[ -z "$URL" || -z "$TAG" || -z "$DIGEST" ]]; then
  echo "[1/6] 查询 $REPO 最新 release..."
  META=$(curl -sL "https://api.github.com/repos/$REPO/releases/latest" | REPO="$REPO" ASSET="$ASSET" node -e '
    let s = ""; process.stdin.on("data", d => s += d).on("end", () => {
      const j = JSON.parse(s);
      const a = (j.assets || []).find(x => x.name === process.env.ASSET);
      if (!a) { console.error("release 里找不到 asset: " + process.env.ASSET); process.exit(1); }
      const d = (a.digest || "").replace(/^sha256:/, "");
      if (!d) { console.error("asset 无 digest 字段"); process.exit(1); }
      console.log([a.browser_download_url, j.tag_name, d].join("\t"));
    });')
  URL="${META%%$'\t'*}"
  REST="${META#*$'\t'}"
  TAG="${REST%%$'\t'*}"
  DIGEST="${REST#*$'\t'}"
fi
DIGEST="${DIGEST#sha256:}"; DIGEST="${DIGEST,,}"   # 防御：去前缀 + 小写

[[ -n "$DIRNAME" ]] || DIRNAME="$SERVER-$TAG"
LANG_ROOT="$(cygpath -u "$LOCALAPPDATA")/Zed/languages/$SERVER"
DEST="$LANG_ROOT/$DIRNAME"
# metadata 文件名模拟 Rust Path::with_extension("metadata")：目录名最后一个 "." 之后被替换
BASE="$(basename "$DIRNAME")"
if [[ "$BASE" == *.* ]]; then META_FILE="$LANG_ROOT/${BASE%.*}.metadata"; else META_FILE="$LANG_ROOT/$BASE.metadata"; fi

echo "目标服务器 : $SERVER"
echo "版本目录   : $DEST"
echo "metadata   : $META_FILE"
echo "zip        : $URL"

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
ZIP="$TMP/asset.zip"

echo "[2/6] 下载 zip..."
curl.exe -L --retry 5 -C - -o "$ZIP" "$URL" > /dev/null

echo "[3/6] 校验 SHA-256..."
ACTUAL="$(sha256sum "$ZIP" | awk '{print $1}')"
if [[ "$ACTUAL" != "$DIGEST" ]]; then
  echo "错误：SHA-256 不一致（可能被代理改写或下载损坏）" >&2
  echo "  期望: $DIGEST" >&2
  echo "  实际: $ACTUAL" >&2
  exit 1
fi
unzip -t "$ZIP" > /dev/null || { echo "错误：zip 校验失败" >&2; exit 1; }

echo "[4/6] 解压到最终目录（绕过 rename）..."
mkdir -p "$DEST"
unzip -o "$ZIP" -d "$DEST" > /dev/null

echo "[5/6] 运行一次 --version（杀毒预扫 + 验证可执行）..."
EXE=$(find "$DEST" -maxdepth 1 -iname '*.exe' | head -1)
[[ -n "$EXE" ]] || { echo "错误：解压后找不到 exe" >&2; exit 1; }
timeout 120 "$EXE" --version

echo "[6/6] 写 metadata（digest 裸 hex 无前缀，关键一步）..."
printf '%s' "{\"metadata_version\":1,\"digest\":\"$DIGEST\"}" > "$META_FILE"

echo
echo "完成。可执行: $EXE"
echo "下一步：启动 Zed 打开一个开了 Rust 白名单的项目，确认日志零下载（判据见 SKILL.md「验证」节）。"
