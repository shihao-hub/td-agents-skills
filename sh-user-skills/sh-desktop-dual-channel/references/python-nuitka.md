# Python 模块：Nuitka 双通道打包

> 归属：`sh-desktop-dual-channel`。运行时壳见 `python-webview.md`，本文只讲打包与 PE。
> 验证锚点：`python_projects/zedhub`（2026-10，Nuitka 4.3 + MSVC 2022）。
> Nuitka 版本差异较大，命令以 4.x 为准；升级后先跑一遍 `--help` 核对参数名。

---

## 一、前置

```powershell
uv --version
uv add --dev "nuitka>=2.5" "zstandard>=0.22"   # zstandard 用于 onefile 压缩
uv run python -m nuitka --version              # 自动通过 vswhere 找 MSVC
```

- **编译器**：VS 2022 Build Tools（MSVC）或 MinGW64；没有编译器时 Nuitka 会在 Scons 阶段失败。
- **入口脚本**：`scripts/gui_entry.py` 与 `scripts/cli_entry.py`，只做 import + 调用，不放业务。

```python
# scripts/gui_entry.py
from myapp.gui import main

if __name__ == "__main__":
    raise SystemExit(main())
```

```python
# scripts/cli_entry.py
from myapp.cli import app

if __name__ == "__main__":
    app(prog_name="myapp-cli")
```

---

## 二、产物与通道判定

| 通道 | 产物 |
|---|---|
| dev | `bin/<app>-gui-dev.exe` + `bin/<app>-cli-dev.exe` |
| release | `bin/<app>-gui.exe` + `bin/<app>-cli.exe` |

判定（与 Go 模块语义一致）：

```text
HEAD 精确命中 <app>-v* tag  且  工作区干净（剔除 bin/dist/build）  → release
其余情况（含 --release 但条件不足）                              → dev / 退出码 2
```

版本来自 `hatch-vcs`（`[tool.hatch.version] source = "vcs"`）：干净 tag = `X.Y.Z`，
tag 后有提交 = `X.Y.devN+g<hash>`。`is_production_build()` 用「无 `.dev`、无 local `+`」判定。

---

## 三、构建脚本骨架

```python
COMMON_PACKAGES = (
    "myapp", "pystray", "PIL", "pythonnet", "clr_loader",
    "uvicorn", "starlette", "typer", "pydantic", "mcp", "websockets",
)  # 注意：不要把 webview 放进来（见坑 3）

def _common_args(output_name, description, version, *, icon, bundle_dev_icon):
    args = [
        "--assume-yes-for-downloads",
        f"--output-dir={OUT_DIR}",
        f"--output-filename={output_name}",
        f"--company-name={COMPANY}",
        f"--product-name={PRODUCT}",
        f"--file-description={description}",
        f"--file-version={_pe_version(version)}",
        f"--product-version={_pe_version(version)}",
        f"--windows-icon-from-ico={icon}",
        f"--include-data-dir={SRC / 'webui'}=myapp/webui",
        f"--include-data-dir={SRC / 'gui' / 'assets'}=myapp/gui/assets",
        "--nofollow-import-to=pytest",
        "--nofollow-import-to=ruff",
    ]
    if bundle_dev_icon:
        args.append(f"--include-data-file={PYTHON_ICON}=myapp/gui/assets/icon-dev.ico")
    for pkg in COMMON_PACKAGES:
        args.append(f"--include-package={pkg}")
    return args

def _build(entry, name, desc, version, *, gui, onefile, channel):
    icon, bundle = _icon_for(channel)
    cmd = [sys.executable, "-m", "nuitka", str(entry),
           *_common_args(name, desc, version, icon=icon, bundle_dev_icon=bundle)]
    cmd.append("--windows-console-mode=" + ("disable" if gui else "force"))
    if onefile:
        base = Path(name).stem
        cmd += ["--onefile",
                f"--onefile-tempdir-spec={{CACHE_DIR}}/{COMPANY}/onefile/{base}/{{VERSION}}"]
    else:
        cmd.append("--standalone")
    subprocess.run(cmd, cwd=PROJECT_DIR, check=True)
```

- GUI 用 `--windows-console-mode=disable`（Subsystem=2），CLI 用 `force`（Subsystem=3）；
- **一个包只能有一个子系统**：必须构建两次，禁止合成单 exe；
- 数据资产必须显式 `--include-data-dir`：Nuitka 只跟踪 `.py` import，不会自动收 `.html/.js/.css`；
- 打包后 `__file__` 指向解压目录，代码里用 `Path(__file__).parent / "webui"` 即可命中映射后的目录。

---

## 四、五条实测坑（按踩到顺序）

### 坑 1：`uv run --with nuitka` 用错解释器

```text
uv run --with nuitka scripts/build_exe.py
# → sys.executable 指向 uv 的临时隔离环境，Nuitka 找不到项目包
# → No module named 'nuitka' 或 ModuleNotFoundError: myapp
```

**处置**：把 `nuitka`/`zstandard` 写进 `[dependency-groups] dev`，直接 `uv run scripts/build_exe.py`。
带 PEP 723 头的脚本会被 uv 视为独立脚本环境，构建脚本不要加该头。

### 坑 2：`--output-dir` / `--output-filename` 必须 `=`

```text
__main__.py: error: The '--output-dir' option requires an argument with '--output-dir='.
```

**处置**：全部写成 `--opt=value`，不要用空格分隔。

### 坑 3：`--include-package=webview` 与 pywebview 插件冲突

```text
FATAL: pywebview: Conflict between user and plugin decision for module 'webview.platforms.android'.
```

**处置**：**不要**显式 include `webview`。pywebview 自带 Nuitka 插件，会按平台挑模块；
显式 include 会与插件的排除决策冲突。

### 坑 4：onefile 每次启动重新解压

默认 onefile 会把 150 MB payload 解压到临时目录，冷启动 5–10 s。

**处置**：

```text
--onefile-tempdir-spec={CACHE_DIR}/<company>/onefile/<name>/{VERSION}
```

固定解压目录后，同一版本二次启动直接复用；版本升级自动换目录。若仍嫌慢，改用
`--standalone`（文件夹版，启动快、分发麻烦）。

### 坑 5：构建中间产物巨大

一次双通道构建会留下 `bin/*.build`、`bin/*.dist`、`bin/*.onefile-build`，合计约 2.3 GB。

**处置**：`.gitignore` 加 `bin/`；构建后清理 `bin/*.build bin/*.dist bin/*.onefile-build`，
只保留 exe。不要为了省事把 `bin/` 提交入库。

---

## 五、图标双通道（构建侧）

| 通道 | PE 图标 | 运行期图标 |
|---|---|---|
| dev | 语言默认图标（Python：`docs/assets/projects/python_projects/python-default.ico`） | 打包为 `myapp/gui/assets/icon-dev.ico`，运行时优先读它 |
| release | `myapp/gui/assets/icon.ico`（`render_icon.py` 生成） | 同一文件 |

```python
def _icon_for(channel):
    if channel != "release" and PYTHON_ICON.is_file():
        return PYTHON_ICON, True     # 同时 include 为 icon-dev.ico
    return ICON, False
```

- 语言图标以**绝对路径**引用，不复制进项目目录（构建期写入 PE；运行期由 include 兜底）；
- `--windows-icon-from-ico` 只影响 exe 文件图标；窗口/托盘图标由运行时 `app_icon()` 决定（`python-webview.md` Step 10）；
- 验证：`[System.Drawing.Icon]::ExtractAssociatedIcon(exe)` 分别提取两个产物，像素必须不同。

---

## 六、PE 版本与描述

```python
def _pe_version(version: str) -> str:
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
    return ".".join(m.groups()) + ".0" if m else "0.0.0.0"
```

- `--file-version` / `--product-version` 只接受 4 段数字，`0.0.0.dev0` 会被拒绝；
- `--file-description` 不要用中文：命令行参数在 Windows 下可能被按 ANSI 解析，PE 属性面板会乱码；
  GUI 用 `"MyApp Desktop Shell"`、CLI 用 `"MyApp Command Line"`，两者必须不同；
- `--company-name` / `--copyright` 一并写入，属性面板才完整。

**校验**：

```powershell
(Get-Item .\bin\myapp-gui-dev.exe).VersionInfo |
  Select-Object FileDescription, FileVersion, ProductName, CompanyName
```

---

## 七、清理与验收

```powershell
uv run scripts/build_exe.py            # dev
uv run scripts/build_exe.py --release  # 无干净 tag → 退出码 2，不产正式名
git status --porcelain                 # 必须为空（bin/ 已 ignore）
```

| 验证项 | 操作 | 预期 |
|---|---|---|
| 子系统 | 读 PE 头 Subsystem | gui=2、cli=3 |
| 版本资源 | 右键属性 | 描述/版本/公司齐全，GUI 与 CLI 描述不同 |
| dev 图标 | 提取 exe 图标 | Python 双蛇（或语言默认图标） |
| release 图标 | 提取 exe 图标 | 专属图标 |
| 启动 | 双击 GUI | 窗口出现、无控制台闪窗 |
| CLI | `.\bin\myapp-cli-dev.exe --version` | 输出后秒退、prompt 正常 |
| 门禁 | 无 tag 执行 `--release` | 退出码 2 |
| 中间产物 | `bin/` | 只有 exe，无 `.build/.dist/.onefile-build` |

---

## 八、回滚

```powershell
Remove-Item .\bin\myapp-gui-dev.exe, .\bin\myapp-cli-dev.exe -ErrorAction SilentlyContinue
Remove-Item .\bin\*.build, .\bin\*.dist, .\bin\*.onefile-build -Recurse -Force
```
