# 构建流水线参考：dev / release 通道隔离与图标双通道

> 归属：`sh-go-wails-desktop`。脚本以 Windows + uv + go-winres 为准，其他平台自行替换资源编译环节。
>
> **工具选型（踩过坑）**：不要用 `rsrc` 做版本资源——`rsrc v0.10.2` 只支持 `-manifest` / `-ico`，**不读 `info.json`、不支持 VERSIONINFO**，exe 属性面板的版本/描述会全空。改 `go-winres`：`go install github.com/tc-hib/go-winres@latest`；它能同时产出 VERSIONINFO + manifest + 图标，并支持按产物给不同 FileDescription。

---

## 一、通道隔离五件套

dev 与 release 必须在以下五个维度同时隔离，缺一项就会出现"分不清哪个是正式版"的事故：

| 维度 | dev | release |
|:---|:---|:---|
| 产物名 | `<app>-gui-dev.exe` + `<app>-cli-dev.exe` | `<app>-gui.exe` + `<app>-cli.exe` |
| 版本号 | `vX.Y.Z-dev[-dirty]` | `vX.Y.Z` |
| 数据目录 | `%APPDATA%\language_projects\<app>\dev` | `...\prod` |
| 单实例 ID | `<team>.<app>.gui.dev` | `<team>.<app>.gui` |
| exe / 窗口图标 | Go 地鼠（一眼可辨） | 项目专属图标 |

### 九条铁律

1. **判定单一入口**：仅当 HEAD 精确命中项目 tag 且工作区干净才产 release，其余一律 dev；`--release` 只做断言（条件不足 `exit 2`），不得改写判定。
2. **严禁 dev 覆盖正式名**：不要为了"方便双击"把 dev 产物 `copy` 成正式名——正式名必须只由 release 构建产生。
3. **版本号自解释**：dev 基线取最近项目 tag，无 tag 回退 `info.json` 的 `fixed.file_version`；脏工作区追加 `-dirty`；版本由 `-ldflags -X` 注入。
4. **`IsRelease` 单一真源**：只认编译期注入的 `BuildMode`，禁止用 `Version` 前缀猜测（否则 `--version v1.0.0` 会造出混合体并绕过自启门禁）。
5. **数据目录与单例同步隔离**：`appDataDir()` 按 `IsRelease()` 追加 `dev`/`prod`；Wails `UniqueID` 在 dev 追加 `.dev`。
6. **旧库一次性迁移**：复制主库与 `-wal`/`-shm`，旧文件保留并写日志。
7. **dirty 判定过滤构建生成物**：`git -c status.relativePaths=false status --porcelain` 剔除 `*.exe`、图标、`rsrc_*.syso` 后为空才算干净；git 异常时保守按脏处理。
8. **`.gitignore` 根路径限定**：`/icon.ico`、`/icon.png` 必须带前导斜杠，否则会误忽略 `internal/app/icon.ico`（`go:embed` 必需资产）。
9. **双通道契约**：GUI 产物（`-H windowsgui`）只开窗口、不解析任何子命令；Console 产物（`-tags cli`，console 子系统）只跑终端、不开窗口。一条通道必须出两个二进制，严禁用 `AttachConsole` 合成单产物（原因见 `README.md` 反模式警示与 `references/troubleshooting.md` §3）。


---

## 二、图标双通道

exe 文件图标（PE 资源）与窗口/托盘图标（内存）是两条独立通道，dev 必须同时切换：

### 1. PE 静态资源

图标按通道选择（写进 `winres/{gui,cli}.json` 的 `__ICON__` 占位）：release 用根 `icon.ico`，dev 用 `internal/app/icon_dev.ico`（Go 地鼠，静态入库）。

### 1.1 PE 版本资源（VERSIONINFO）与 winres 模板

exe 属性面板里的「文件说明 / 文件版本 / 产品名称 / 公司 / 版权」来自 VERSIONINFO 资源，必须由 `go-winres` 生成（rsrc 没有这个能力）。模板放 `winres/`，**GUI 与 CLI 各一份**（FileDescription 必须不同）：

```json
{
  "RT_GROUP_ICON": { "APP": { "0000": "__ICON__" } },
  "RT_MANIFEST":   { "#1":  { "0409": "__MANIFEST__" } },
  "RT_VERSION": {
    "#1": { "0000": {
      "fixed": { "file_version": "__FIXED_VERSION__", "product_version": "__FIXED_VERSION__" },
      "info": { "0409": {
        "CompanyName": "Your Company",
        "FileDescription": "AppName - 桌面工作台",
        "FileVersion": "__VERSION__",
        "InternalName": "app-gui",
        "LegalCopyright": "© 2026 Your Company",
        "OriginalFilename": "__ORIGINAL_NAME__",
        "ProductName": "app",
        "ProductVersion": "__VERSION__"
      } }
    } }
  }
}
```

- `cli.json` 只需改 `FileDescription`（如「AppName CLI - 命令行」）与 `InternalName`；
- `RT_MANIFEST` 指向现成的 `wails.exe.manifest` 文件（**路径相对 JSON 所在目录**，即 `"../wails.exe.manifest"`），manifest 内容原样嵌入，DPI/Common-Controls 设置不受影响；
- `__FIXED_VERSION__` 必须是 4 段纯数字（`1.2.1.0`），`__VERSION__` 可带后缀（`1.2.1-dev-dirty`），便于在属性面板区分 dev；
- `__ICON__` / `__MANIFEST__` 用正斜杠相对路径（`../icon.ico`、`../internal/app/icon_dev.ico`）。

**校验**（构建后立刻跑）：

```powershell
Get-Item .\<app>-gui.exe | ForEach-Object {
  $v = $_.VersionInfo
  "{0} | {1} | {2} | {3}" -f $v.FileDescription, $v.FileVersion, $v.ProductName, $v.OriginalFilename
}
# 期望：GUI 与 CLI 的 FileDescription 不同，版本与 tag 一致，OriginalFilename 等于实际文件名
```

### 2. 窗口/托盘（build tag 切换 embed）

`//go:embed` 编译期固化，无法用 ldflags 替换，用 build tag 拆两个同名变量：

```go
// icon_release.go
//go:build !dev
//
//go:embed icon.ico
var iconICO []byte
```

```go
// icon_dev.go
//go:build dev
//
//go:embed icon_dev.ico
var iconICO []byte
```

dev 构建追加 `-tags dev`；`gofmt` 要求文档注释与 `//go:embed` 之间有一个空的 `//` 行。

### 3. 验证图标确实切换（PowerShell + Pillow）

```powershell
Add-Type -AssemblyName System.Drawing
function Get-IconHash($path) {
  $ico = [System.Drawing.Icon]::ExtractAssociatedIcon($path)
  $ms = New-Object System.IO.MemoryStream
  $ico.ToBitmap().Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
  $sha = [System.Security.Cryptography.SHA256]::Create().ComputeHash($ms.ToArray())
  [BitConverter]::ToString($sha).Replace('-','').Substring(0,16)
}
Get-IconHash ".\<app>-gui.exe"        # 与下面必须不同（GUI 通道）
Get-IconHash ".\<app>-gui-dev.exe"
```

再用 Pillow 取 `icon_dev.ico` 的 32×32 帧与 dev exe 图标做像素比对（`uv run --with pillow python`），可确认 dev 图标确实是地鼠。

---

## 三、`scripts/render_icon.py`

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow>=11.0"]
# ///
import math
from pathlib import Path
from PIL import Image, ImageDraw

def render_gear_icon(size: int = 1024) -> Image.Image:
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # 绘制高精底图与主题专属图案 (机械齿轮/晶体等)
    d.ellipse((32, 32, size - 32, size - 32), fill=(24, 27, 36, 255), outline=(0, 229, 255, 230), width=16)
    return im

def main():
    root = Path(__file__).resolve().parent.parent
    im = render_gear_icon(1024)
    im.save(root / "icon.png")

    # 导出完整 Windows ICO 尺寸链
    sizes = [256, 128, 64, 48, 32, 24, 16]
    im.save(root / "icon.ico", format="ICO", sizes=[(s, s) for s in sizes])
    im.save(root / "internal" / "app" / "icon.ico", format="ICO", sizes=[(s, s) for s in sizes])
    print("[OK] 图标生成并同步完成")

if __name__ == "__main__":
    main()
```

渲染必须确定性：同一源码重复执行产生相同字节，否则每次构建都会弄脏工作区，让 release 门禁自锁。

---

## 四、`scripts/build.py`（完整实现）

> 通用模板：把 `your_app` 换成项目名、`TAG_PREFIX` 换成 monorepo 前缀即可直接用。
> 关键点：同一通道内循环构建两次，只有 GUI 目标追加 `-H windowsgui`，只有 CLI 目标追加 `-tags cli`。

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow>=11.0"]
# ///
"""双通道构建：每条通道各出 GUI（-H windowsgui）与 Console（-tags cli）两个二进制。

用法：
  uv run scripts/build.py              # dev     → <app>-gui-dev.exe + <app>-cli-dev.exe
  uv run scripts/build.py --release    # release → <app>-gui.exe     + <app>-cli.exe（条件不足 exit 2）
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TAG_PREFIX = "your_app/"          # monorepo 项目 tag 前缀；单仓项目置空，tag 直接写 vX.Y.Z

# PE 资源工具与模板（go-winres 才能写 VERSIONINFO）
WINRES_EXE = shutil.which("go-winres") or str(Path(os.environ.get("GOPATH", "")) / "bin" / "go-winres.exe")
WINRES_DIR = PROJECT_ROOT / "winres"        # gui.json / cli.json：占位 __ICON__ / __MANIFEST__ / __VERSION__ / __ORIGINAL_NAME__
ICON_RELEASE = PROJECT_ROOT / "icon.ico"
ICON_DEV = PROJECT_ROOT / "internal" / "app" / "icon_dev.ico"
RENDER_ICON = PROJECT_ROOT / "scripts" / "render_icon.py"
MANIFEST = PROJECT_ROOT / "wails.exe.manifest"
SYSO_OUT = PROJECT_ROOT / "cmd" / "your_app" / "rsrc_windows_amd64.syso"

EXE_GUI_RELEASE = PROJECT_ROOT / "your_app-gui.exe"
EXE_GUI_DEV = PROJECT_ROOT / "your_app-gui-dev.exe"
EXE_CLI_RELEASE = PROJECT_ROOT / "your_app-cli.exe"
EXE_CLI_DEV = PROJECT_ROOT / "your_app-cli-dev.exe"

GENERATED_SUFFIXES = (
    "/your_app-gui.exe",
    "/your_app-gui-dev.exe",
    "/your_app-cli.exe",
    "/your_app-cli-dev.exe",
    "/icon.ico",
    "/icon.png",
    "/cmd/your_app/rsrc_windows_amd64.syso",
    "/winres/.tmp-winres.json",
)


def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=str(PROJECT_ROOT), capture_output=True, text=True, check=False)


def exact_project_tag() -> str | None:
    """HEAD 上精确命中的项目 tag（形如 your_app/v1.0.0）。"""
    r = run_git("tag", "--points-at", "HEAD")
    if r.returncode != 0:
        return None
    return next((t.strip() for t in r.stdout.splitlines() if t.strip().startswith(f"{TAG_PREFIX}v")), None)


def latest_project_tag() -> str | None:
    """最近的项目 tag，用于推导 dev 版本基线。"""
    r = run_git("describe", "--tags", "--abbrev=0", "--match", f"{TAG_PREFIX}v*")
    if r.returncode != 0:
        return None
    return r.stdout.strip() or None


def base_version() -> str:
    tag = latest_project_tag()
    if tag:
        return tag[len(TAG_PREFIX):].lstrip("v")
    info = json.loads((PROJECT_ROOT / "info.json").read_text(encoding="utf-8"))
    return str(info["fixed"]["file_version"]).strip()


def worktree_dirty() -> bool:
    """工作区是否含构建产物之外的改动；git 不可用时保守按脏处理。"""
    r = run_git("-c", "status.relativePaths=false", "status", "--porcelain", "--untracked-files=normal")
    if r.returncode != 0:
        return True
    for line in r.stdout.splitlines():
        path = line[3:].strip().strip('"').split(" -> ")[-1]
        normalized = "/" + path.replace("\\", "/").lstrip("/")
        if not any(normalized.endswith(suffix) for suffix in GENERATED_SUFFIXES):
            return True
    return False


def four_part_version(version: str) -> str:
    """v1.2.1 / 1.2.1-dev → VERSIONINFO 要求的 4 段数字。"""
    core = version.lstrip("v").split("-")[0]
    return ".".join((core.split(".") + ["0", "0", "0"])[:4])


def build_resources(release: bool, gui: bool, out_exe: Path, version: str) -> int:
    """PE 资源段：VERSIONINFO + manifest + 图标，落在 main 包目录。

    关键坑：GUI 与 CLI 在同一个 Go 包里，而一个包只能链接一份 syso，
    所以必须在**每个产物 go build 之前**重新生成一次，两者才能有各自的
    FileDescription / OriginalFilename。
    """
    icon = ICON_RELEASE if release else ICON_DEV
    template = WINRES_DIR / ("gui.json" if gui else "cli.json")
    if not (icon.exists() and template.exists()):
        print(f"❌ 缺少图标或资源模板: {icon} / {template}", file=sys.stderr)
        return 4

    # go-winres 按「相对 JSON 所在目录」解析资源路径，故临时 JSON 必须放 winres/
    rel_icon = Path(os.path.relpath(icon, WINRES_DIR)).as_posix()
    rel_manifest = Path(os.path.relpath(MANIFEST, WINRES_DIR)).as_posix()
    rendered = (
        template.read_text(encoding="utf-8")
        .replace("__ICON__", rel_icon)
        .replace("__MANIFEST__", rel_manifest)
        .replace("__FIXED_VERSION__", four_part_version(version))
        .replace("__VERSION__", version.lstrip("v"))
        .replace("__ORIGINAL_NAME__", out_exe.name)
    )
    tmp_json = WINRES_DIR / ".tmp-winres.json"
    try:
        tmp_json.write_text(rendered, encoding="utf-8", newline="
")
        r = subprocess.run(
            [WINRES_EXE, "make", "--in", str(tmp_json), "--arch", "amd64",
             "--out", str(SYSO_OUT.parent / "rsrc")],
            cwd=str(PROJECT_ROOT),
        )
    finally:
        tmp_json.unlink(missing_ok=True)
    if r.returncode != 0:
        print(f"❌ go-winres 生成失败（exit {r.returncode}）", file=sys.stderr)
    return r.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="双通道构建（dev / release 严格隔离）")
    parser.add_argument("--release", action="store_true", help="声明发布构建；tag 或干净条件不满足即报错")
    parser.add_argument("--version", default="", help="仅覆盖版本基线，不改变通道判定")
    args = parser.parse_args()

    # 1. 先判定通道（图标与产物名都依赖它）；--release 只做断言
    dirty = worktree_dirty()
    release = exact_project_tag() is not None and not dirty
    if args.release and not release:
        print("❌ 拒绝发布构建：需同时满足 精确 tag + 工作区干净", file=sys.stderr)
        return 2

    # 2. 版本与通道（PE VERSIONINFO 要用版本号，必须先算）
    base = args.version.lstrip("v") or base_version()
    version = f"v{base}" if release else f"v{base}-dev" + ("-dirty" if dirty else "")
    build_mode = "release" if release else "dev"

    # 3. 逐通道 go build：同一通道内 GUI 与 Console 各一个产物
    targets = (
        (EXE_GUI_RELEASE if release else EXE_GUI_DEV, True),
        (EXE_CLI_RELEASE if release else EXE_CLI_DEV, False),
    )
    for out_exe, gui in targets:
        # 每个产物前重建 syso（GUI/CLI 的 FileDescription 不同）
        rc = build_resources(release, gui, out_exe, version)
        if rc != 0:
            return rc

        flags = ["-w", "-s"]
        if gui:
            flags.append("-H windowsgui")                      # GUI 通道：双击零黑框
        flags.append(f"-X your_app/internal/app.Version={version}")
        flags.append(f"-X your_app/internal/app.BuildMode={build_mode}")

        tags = [] if release else ["dev"]
        if not gui:
            tags.append("cli")                                 # Console 通道：走 cli.go 入口

        cmd = ["go", "build", "-trimpath"]
        if tags:
            cmd += ["-tags", ",".join(tags)]
        cmd += [f"-ldflags={' '.join(flags)}", "-o", str(out_exe), "./cmd/your_app"]

        channel = "GUI" if gui else "Console"
        print(f"🔨 [{channel}] {out_exe.name}")
        r = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
        if r.returncode != 0:
            print(f"❌ go build 失败（exit {r.returncode}）: {out_exe.name}", file=sys.stderr)
            return r.returncode

    # 5. 产物名守卫：dev 必须以 -dev 结尾，release 不得含 dev
    for out_exe, _gui in targets:
        if release and "dev" in out_exe.stem:
            print(f"❌ 产物命名违规: {out_exe}", file=sys.stderr)
            return 3
        if not release and not out_exe.stem.endswith("-dev"):
            print(f"❌ 产物命名违规: {out_exe}", file=sys.stderr)
            return 3

    for out_exe, gui in targets:
        size_mb = out_exe.stat().st_size / 1048576
        print(f"🎉 {out_exe.name} ({size_mb:.2f} MB, {version}, {build_mode}, {'GUI' if gui else 'Console'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

---

## 五、`.gitignore` 片段

```gitignore
# 构建生成物（脚本自动重建，不入库）
/your_app-gui.exe
/your_app-gui-dev.exe
/your_app-cli.exe
/your_app-cli-dev.exe
/icon.ico
/icon.png
/cmd/your_app/rsrc_windows_amd64.syso

# Python 运行缓存
__pycache__/
*.pyc
```

`internal/app/icon_dev.ico` 与 `internal/app/icon.ico` 必须入库：前者是 dev 通道资产，后者是 release 的 `go:embed` 输入。

---

## 六、版本注入与自启判定

```go
// internal/app/version.go
var (
	Version   = "dev"   // -X your_app/internal/app.Version=v1.0.0[-dev[-dirty]]
	BuildMode = "dev"   // -X your_app/internal/app.BuildMode=release
)

func IsRelease() bool { return BuildMode == "release" }
```

自启封装（`autostart.go`）在 `!IsRelease()` 时直接返回错误并拒绝写注册表；托盘菜单同时置灰，形成"UI 置灰 + 后端防呆"双保险。
