---
name: kb-binary-embedded-sha-source-forensics
description: |
  从已安装发行版二进制中提取编译期嵌入的 git commit SHA，据此取回上游一一对应的那一版源码做取证。涵盖 SHA 的常见入口（--version / PE 版本资源 / 崩溃报告 / about 页）、GitHub raw 与 commits API 的按 SHA 取用、与 main 分支的差异实测，以及「别 dump 巨型二进制字符串、别拿 main 猜」的取证纪律与降级路径。
version: 1.0.0
created: 2026-10-19
updated: 2026-10-19
---

# dev_flow_075_发行版二进制嵌SHA溯源与上游源码取证

> **条目定位**：Type B 方案与流水线型条目
> **适用场景**：本地只装了发行版产物（无源码、无 `.git`），却需要确认「**这个版本**」的行为是否支持某功能、某字段是否存在、某 UI 图标/协议能力从哪来；或需要给某个结论补上可回查的源码级证据。
> **反面对照**：若上游闭源或无法出网，请直接跳到「四、降级路径」，不要硬套本流水线。

---

## 一、业务场景与取证需求

### 典型触发场景
1. 想确认「我装的这版到底支不支持 X」——官方文档只讲最新版，论坛答案各说各话，没人给出处；
2. 要给某 UI 行为、协议字段、配置项下结论，需要**可复核的源码级证据**，而不是「我记得是这样」；
3. 本地只有 `Zed.exe` / `Code.exe` 这类发行产物，**没有源码、没有 `.git`、也没有对应 tag 的源码包**。

### 两个必须先想清的痛点
- **发行版不含 git 历史**：实测 Zed 安装目录只有 `Zed.exe`、若干 dll、`unins000.*`、`bin/`、`tools/`、`x64/`、`arm64/`，不存在 `.git`。任何「本地翻 commit 历史」的思路在这里都是死路。
- **直觉做法代价高且证据弱**：把几百 MB 的 exe dump 成可打印字符串再 grep，既慢又不可靠——Rust/Go 等编译后字段名会**粘连成一大坨**（`commandignore_system_versiondefault_model...`），只能靠猜边界。

### 交付目标
一条确定性链路：**本地二进制 → 唯一版本指纹（SHA）→ 与本地二进制一一对应的那一版源码 → 带 `path:line` 行号的结论**。

---

## 二、核心机制与证据链剖析

### 1. SHA 从哪来：编译期写死进产物

| 入口 | 示例 | 可靠性 |
|:---|:---|:---:|
| CLI `--version` | `Zed 1.24.3 2a857f5f2ec368745c1af5209d49836968fe75b8` | 高（首选） |
| Windows PE 版本资源 / 文件属性 | 部分应用把 SHA 写进 `ProductVersion` | 中 |
| 应用内「关于」/ `chrome://version`（Chromium 系） | 显示完整 commit | 高 |
| 崩溃报告 / 遥测上报头 | 需抓包或看日志 | 中 |

构建流水线通常在编译期把 `git rev-parse HEAD` 注入二进制（供崩溃归因、遥测、版本溯源），因此**任何一台装了该软件的机器都能拿到精确 SHA**，与本地是否保留 git 历史无关。

### 2. 为什么 SHA 比版本号 / tag 可靠
同一个版本号可能对应**多次构建**（热修、CI 重发、不同打包渠道）。SHA 唯一定位一次提交，是唯一不会退化的指纹。

### 3. 上游取文件的两种接口（以 GitHub 为例）
```text
raw：    https://raw.githubusercontent.com/<owner>/<repo>/<SHA>/<path>
元信息： https://api.github.com/repos/<owner>/<repo>/commits/<SHA>   → JSON（committer.date / commit.message）
```
- raw 支持**任意 commit**，不要求是 tag；
- 用 commits API 先校验 SHA 真实存在，并顺手拿到提交日期与提交信息（常含 `Bump to X.Y.Z`，可反向印证版本号与 SHA 对应）。

### 4. 「按 SHA 取」不是洁癖，是必须
实测同一文件在本地 SHA 与 `main` 的差异：
```text
crates/settings_content/src/agent.rs   本地 SHA = 55,507 字节   main = 55,613 字节   （差 106 字节）
```
这 106 字节恰好落在配置项字段定义处——**拿 main 下的结论回答「你这版支不支持」就会翻车**。

---

## 三、标准取证流水线

### 步骤 1：取版本指纹
```powershell
& "D:\Users\29580\AppData\Local\Programs\Zed\bin\Zed.exe" --version
# Zed 1.24.3 2a857f5f2ec368745c1af5209d49836968fe75b8  – \\?\D:\Users\29580\AppData\Local\Programs\Zed\Zed.exe
```
若输出不规整，用正则抠 40 位十六进制：`\b[0-9a-f]{40}\b`（短 SHA 则放宽到 7~40 位，但要注意别误抓版本号或构建号）。

### 步骤 2：校验 SHA 并留档提交元信息
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
curl.exe -s "https://api.github.com/repos/zed-industries/zed/commits/2a857f5f2ec368745c1af5209d49836968fe75b8"
# date: 2026-10-16T19:42:04Z   msg: Bump to 1.24.3 for @JosephTLyons
```

### 步骤 3：按 SHA 批量取回文件（uv 单文件脚本）
落盘到系统临时目录（严禁散落项目根），字段齐备后可直接 grep：

```python
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""按 commit SHA 从 GitHub 取回指定源码文件（与本地发行版一一对应的取证用）。"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

SHA_RE = re.compile(r"\b([0-9a-f]{40})\b")
HEADERS = {"User-Agent": "kb-source-forensics/1.0", "Accept": "application/vnd.github+json"}


def http_get(url: str, timeout: int = 30) -> bytes:
    """带 UA 的 GET（GitHub API 拒收无 UA 请求）。"""
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def resolve_sha_from_exe(exe: str) -> str:
    """调用 <exe> --version 并从输出中解析 40 位 SHA。"""
    result = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30)
    text = f"{result.stdout}\n{result.stderr}"
    match = SHA_RE.search(text)
    if not match:
        raise SystemExit(f"未能从 --version 输出解析 40 位 SHA：{text.strip()!r}")
    return match.group(1)


def verify_commit(repo: str, sha: str) -> dict:
    """校验 SHA 存在并返回提交元信息。"""
    return json.loads(http_get(f"https://api.github.com/repos/{repo}/commits/{sha}"))


def fetch_one(repo: str, sha: str, repo_path: str, out_dir: Path) -> tuple[Path, int]:
    """取回单个文件；扁平化落盘（目录分隔符换成 __ 防覆盖）。"""
    body = http_get(f"https://raw.githubusercontent.com/{repo}/{sha}/{repo_path}")
    dest = out_dir / repo_path.replace("/", "__")
    dest.write_bytes(body)
    return dest, len(body)


def read_listing(list_path: str) -> list[str]:
    """读取文件清单（每行一个仓库内路径，# 开头与空行忽略）。"""
    lines = Path(list_path).read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def main() -> int:
    parser = argparse.ArgumentParser(description="按 SHA 取回上游源码文件")
    parser.add_argument("--repo", required=True, help="owner/repo，如 zed-industries/zed")
    parser.add_argument("--sha", help="显式指定 commit SHA")
    parser.add_argument("--exe", help="从该可执行文件的 --version 解析 SHA")
    parser.add_argument("--out", required=True, help="落盘目录（建议 %%TEMP%% 下专用子目录）")
    parser.add_argument("--list", help="文件清单文件，每行一个仓库内相对路径")
    parser.add_argument("paths", nargs="*", help="仓库内相对路径，可多个")
    args = parser.parse_args()

    sha = args.sha or (resolve_sha_from_exe(args.exe) if args.exe else None)
    if not sha:
        raise SystemExit("必须提供 --sha 或 --exe 之一")

    info = verify_commit(args.repo, sha)
    commit = info.get("commit", {})
    print(f"repo    : {args.repo}")
    print(f"sha     : {info.get('sha')}")
    print(f"date    : {commit.get('committer', {}).get('date')}")
    print(f"message : {(commit.get('message') or '').splitlines()[0][:110]}")

    targets = list(args.paths) + (read_listing(args.list) if args.list else [])
    if not targets:
        raise SystemExit("未提供要取回的文件路径（位置参数或 --list）")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for repo_path in targets:
        try:
            dest, size = fetch_one(args.repo, sha, repo_path, out_dir)
            print(f"{size:>10,d}  {dest.name}  <-  {repo_path}")
        except urllib.error.HTTPError as error:
            print(f"{'FAILED':>10}  HTTP {error.code}  <-  {repo_path}")
    print(f"\n落盘目录：{out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

调用示例：
```powershell
uv run fetch_source_at_sha.py --exe "D:\Users\29580\AppData\Local\Programs\Zed\bin\Zed.exe" `
    --repo zed-industries/zed --out "$env:TEMP\zed-src" `
    crates/settings_content/src/agent.rs `
    crates/project/src/agent_server_store.rs `
    crates/sidebar/src/sidebar.rs
```

### 步骤 4：本地检索（限定范围、脚本化）
在已落盘的少量文件里 grep 即可，**不要**在仓库根裸跑全递归：
```powershell
Select-String -Path "$env:TEMP\zed-src\*.rs" -Pattern "CustomAgentServerSettings" -Context 0,12
```

### 步骤 5：交叉验证三件套
| 验证项 | 做法 |
|:---|:---|
| 版本锚点自洽 | commits API 的提交信息含 `Bump to <版本号>`，与 `--version` 输出的版本号一致 |
| 行为自洽 | 源码断言与 UI 实际观察 / 日志 / 抓包一致（不一致说明取错了版本或漏了分支） |
| 可回查 | 结论中每条断言都写 `path:line`，他人可一键复核 |

---

## 四、交付验证与取证纪律

### 交付前 checklist
- [ ] SHA 已通过 commits API 校验，提交日期与信息已留档
- [ ] 已把「本地 SHA 版」与 `main` 版做过大小/diff 对比，确认差异存在（证明按 SHA 取的必要性）
- [ ] 每条结论都有 `path:line`，并标注「验证于 <软件> <版本> / <SHA>」
- [ ] 结论附**复现命令**（`--version` 拿 SHA + 本脚本取文件），使版本漂移后可自证
- [ ] 临时文件全部落 `%TEMP%`，交付前清理干净

### 反模式（真实踩过）
1. **先 dump 巨型二进制再 grep**：360MB 的 exe → 180 万条字符串 / 26MB 中间产物，字段名粘连、证据模糊，耗时最长且结论还不如源码直接。
   **正确顺序**：先测网络能否直达上游仓库（`curl` 一下 raw 地址即可），能取源码就别 dump 二进制。
2. **拿 `main` 猜本地版本**：106 字节的字段差异就足以把「不支持」说成「支持」。
3. **把版本相关结论说成永久结论**：必须带版本锚点，并在升级后重跑自查。
4. **临时脚本散落项目根**：统一落 `%TEMP%`，单文件就地复用，收尾即清（`git status` 必须干净）。

### 降级路径（上游闭源或无网时）
- **闭源**：只能行为取证——UI 观察、日志、抓包、PE 版本资源、对二进制做**局部** `strings`（限定区段，别全量 dump），并且必须在结论中显式标注不确定性等级。
- **其它托管**：GitLab 用 `https://gitlab.com/<group>/<proj>/-/raw/<SHA>/<path>`；Gitea/自建同理，commits API 换成对应 REST 端点。
- **纯离线**：若有官方源码 tarball（`<repo>/archive/<SHA>.tar.gz`），下载后本地解压检索，效果等价。
