#!/usr/bin/env python3
"""PyStand 打包器：Python 项目 → 免安装独立文件夹（dist/<AppName>/）。

所有流程坑位（._pth 隔离、_pystand_static.int 优先级、pip --target、
tkinter 四件套、下载 URL tag 陷阱）的修正都已固化在本脚本。
仅用标准库；本机无系统 Python 时用 `uv run --no-project python pack.py ...` 调起。

用法示例:
    uv run --no-project python pack.py --project-dir myproj --entry main.py \
        --app-name MyApp --icon app.ico
    # 服务器型应用（FastAPI/uvicorn 等，无窗口交付）:
    uv run --no-project python pack.py --project-dir myapi --app-name myapi \
        --server --debug-cli        # 自动: uv export 锁版本 / src 布局 / 生成入口与停机脚本
"""
import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ---------------------------------------------------------------- 常量（URL 坑位已修正）
PYSTAND_TAG = "1.1.5"  # 注意: tag 无 v 前缀
URLS = {
    "embed": "https://www.python.org/ftp/python/{v}/python-{v}-embed-{arch}.zip",
    "pystand": f"https://github.com/skywind3000/PyStand/releases/download/{PYSTAND_TAG}/PyStand-v{PYSTAND_TAG}-exe.zip",
    "getpip": "https://bootstrap.pypa.io/get-pip.py",
    "rcedit": "https://github.com/electron/rcedit/releases/download/v2.0.0/rcedit-x64.exe",  # 最新就是 v2.0.0
}
EMBED_ARCH = {"x64": "amd64", "x86": "win32"}
PYSTAND_VARIANT = {("x64", "gui"): "PyStand-x64-GUI", ("x64", "cli"): "PyStand-x64-CLI",
                   ("x86", "gui"): "PyStand-Win32-GUI", ("x86", "cli"): "PyStand-Win32-CLI"}


def step(msg):
    print(f"\n=== {msg}")


def die(msg):
    print(f"\n[FATAL] {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------- 下载（带缓存）
def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1024:  # 9 字节的 "Not Found" 视为失败残留
        print(f"  [cache] {dest.name}")
        return dest
    print(f"  [download] {url}")
    try:
        with urllib.request.urlopen(url, timeout=120) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
    except Exception as e:
        die(f"下载失败 {url}: {e}\n  手动下载放到 {dest} 后重跑本脚本即可续传。")
    if dest.stat().st_size < 1024:
        dest.unlink()
        die(f"下载内容异常（<1KB，可能是 404）: {url}")
    return dest


# ---------------------------------------------------------------- tkinter 复制源探测
def find_tkinter_source(major_minor: str, arch: str, explicit: str) -> Path:
    if explicit:
        p = Path(explicit)
        if (p / "DLLs" / "_tkinter.pyd").exists():
            return p
        die(f"--tkinter-source 指定的目录缺少 DLLs/_tkinter.pyd: {p}")
    if arch != "x64":
        die("32 位打包需要 32 位完整 Python 作为 tkinter 复制源，请用 --tkinter-source 显式指定。")
    # 1) uv managed python（本机实测布局）
    uvdir = Path(os.environ.get("APPDATA", "")) / "uv" / "python"
    if uvdir.is_dir():
        cands = sorted(g for g in uvdir.glob(f"cpython-{major_minor}.*-windows-x86_64-none")
                       if (g / "DLLs" / "_tkinter.pyd").exists())
        if cands:
            return cands[-1]
    # 2) py launcher 安装的正式版
    try:
        out = subprocess.run(["py", "-0p"], capture_output=True, text=True, timeout=15).stdout
        for line in out.splitlines():
            m = re.search(r"([A-Z]:\\[^\s]+)", line)
            if m and f"Python{major_minor.replace('.', '')}" in line:
                p = Path(m.group(1))
                if (p / "DLLs" / "_tkinter.pyd").exists():
                    return p
    except Exception:
        pass
    die("找不到含 tkinter 的完整 Python（同 3.%s 版本）。备选：装一个同版本 Python，"
        "或 uv python install，或 --tkinter-source 指定路径。详见 skill references/pitfalls.md 坑 5。" % major_minor)


def copy_tkinter(src: Path, app: Path):
    print(f"  tkinter 源: {src}")
    rt = app / "runtime"
    # 纯 py 包 → site-packages（在 PyStand 注入的 sys.path 上）
    shutil.copytree(src / "Lib" / "tkinter", app / "site-packages" / "tkinter",
                    dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    # 扩展与 DLL → runtime（既是 sys.path 项，也是 DLL 搜索目录）
    for pat in ("_tkinter.pyd", "tcl8*t.dll", "tk8*t.dll"):
        for f in (src / "DLLs").glob(pat):
            shutil.copy2(f, rt / f.name)
    # tcl/tk 数据目录 → runtime/tcl
    (rt / "tcl").mkdir(exist_ok=True)
    for name in ("tcl8", "tcl8.6", "tcl8.5", "tk8.6", "tk8.5"):
        d = src / "tcl" / name
        if d.is_dir():
            shutil.copytree(d, rt / "tcl" / name, dirs_exist_ok=True)


# ---------------------------------------------------------------- 启动脚本模板（GUI 异常坑的兜底）
INT_TEMPLATE = '''import sys, os, runpy

home = sys.PYSTAND_HOME

# tkinter 运行库定位（无 tcl 目录时无害）
os.environ.setdefault('TCL_LIBRARY', os.path.join(home, 'runtime', 'tcl', '{tcl_dir}'))
os.environ.setdefault('TK_LIBRARY', os.path.join(home, 'runtime', 'tcl', '{tk_dir}'))

sys.path.insert(0, os.path.join(home, 'app'))

try:
    runpy.run_path(os.path.join(home, 'app', '{entry}'), run_name='__main__')
except Exception:
    import traceback
    text = traceback.format_exc()
    print(text)  # CLI 变体可见；GUI 变体进 devnull 无害
    try:
        with open(os.path.join(home, 'pystand-error.log'), 'w', encoding='utf-8') as f:
            f.write(text)
    except OSError:
        pass
    raise  # 交给 PyStand 的错误提示
'''


# ---------------------------------------------------------------- 服务器型应用模板（2026-08-26 实测）
# 用 .replace() 注入 token，不用 .format（模板里有 f-string 花括号）。
# 三件事（缺一不可，详见 pitfalls.md 坑 10/11/12）:
#   1. 日志落盘: GUI 变体 stdout 进 devnull，不重定向 = 日志黑洞
#   2. 控制台检测 + Tee: demo-api-cli.exe/终端下同打控制台+文件（每行 flush，管道块缓冲 8KB 才吐）
#   3. stop.flag 停机: 无窗口环境没有 Ctrl+C，靠看门狗线程置 server.should_exit 优雅收尾
SERVER_MAIN_TEMPLATE = '''"""server launcher (generated by pack.py --server)."""
import ctypes
import os
import sys
import threading
import time
from pathlib import Path


def _resolve_root() -> Path:
    home = getattr(sys, "PYSTAND_HOME", None)
    if home:
        return Path(home)
    return Path(__file__).resolve().parent.parent


ROOT = _resolve_root()
os.chdir(ROOT)

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = open(LOG_DIR / "run.log", "a", buffering=1, encoding="utf-8")

STOP_FLAG = ROOT / "stop.flag"


class _Tee:
    def __init__(self, *streams):
        self._streams = streams

    def write(self, s):
        for st in self._streams:
            try:
                st.write(s)
                st.flush()
            except Exception:
                pass
        return len(s)

    def flush(self):
        for st in self._streams:
            try:
                st.flush()
            except Exception:
                pass

    def isatty(self):
        return False


def _has_console() -> bool:
    try:
        return bool(ctypes.windll.kernel32.GetConsoleWindow())
    except Exception:
        return False


if _has_console():
    stdout = sys.stdout if sys.stdout is not None else LOG_FILE
    stderr = sys.stderr if sys.stderr is not None else LOG_FILE
    sys.stdout = _Tee(stdout, LOG_FILE)
    sys.stderr = _Tee(stderr, LOG_FILE)
else:
    sys.stdout = LOG_FILE
    sys.stderr = LOG_FILE

import uvicorn


def main():
    print(f"=== launcher start, root={ROOT}, console={_has_console()}")

    config = uvicorn.Config(
        "@@APP_TARGET@@",
        host="@@HOST@@",
        port=@@PORT@@,
        log_config=None,
    )
    server = uvicorn.Server(config)

    def watch_stop_flag():
        while True:
            if STOP_FLAG.exists():
                print("=== stop.flag detected, requesting graceful shutdown")
                server.should_exit = True
                return
            time.sleep(0.5)

    STOP_FLAG.unlink(missing_ok=True)
    threading.Thread(target=watch_stop_flag, daemon=True).start()

    try:
        server.run()
    finally:
        print("=== server stopped")


if __name__ == "__main__":
    main()
'''

# bat 三坑已规避: 全 ASCII（中文注释在非 UTF-8 代码页乱码甚至解析报错）；
# ping 轮询代替 timeout（无控制台环境 timeout 直接失败导致提前强杀）；
# tasklist|find 检测进程，退出立即返回不等满 30s。
STOP_BAT_TEMPLATE = '''@echo off
rem Graceful shutdown for @@EXE@@: creates stop.flag, waits for graceful exit, force-kills only as last resort.
cd /d "%~dp0"
type nul > stop.flag
echo Stop signal sent. Waiting up to 30s for graceful shutdown...
set /a tries=0
:waitloop
tasklist /FI "IMAGENAME eq @@EXE@@" 2>nul | find /I "@@EXE@@" >nul
if errorlevel 1 goto :graceful_done
set /a tries+=1
if %tries% GEQ 30 goto :kill_now
ping -n 2 127.0.0.1 >nul
goto :waitloop
:graceful_done
echo @@EXE@@ stopped gracefully.
del stop.flag 2>nul
exit /b 0
:kill_now
echo Graceful shutdown timed out, force killing...
taskkill /IM @@EXE@@ /F >nul 2>&1
del stop.flag 2>nul
exit /b 1
'''


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser(description="PyStand 独立打包器")
    ap.add_argument("--project-dir", default=".", help="项目目录（默认当前目录）")
    ap.add_argument("--entry", default=None, help="入口文件（默认 main.py，需可直接 python 运行；--server 时自动生成）")
    ap.add_argument("--server", action="store_true",
                    help="服务器型应用预设（FastAPI/uvicorn 等）: 生成带日志落盘+stop.flag 停机的入口、"
                         "stop-<App>.bat、自动 uv export 锁版本、src 布局与 .env 拷贝；验证走 /health 而非窗口标题")
    ap.add_argument("--host", default="127.0.0.1", help="--server 监听地址（默认 127.0.0.1）")
    ap.add_argument("--port", type=int, default=8000, help="--server 监听端口（默认 8000）")
    ap.add_argument("--app-target", default=None, help="--server 的 ASGI app（如 mypkg.main:app，默认取 src 下第一个含 main.py 的包）")
    ap.add_argument("--app-name", default=None, help="产物名（默认项目目录名）")
    ap.add_argument("--requirements", default=None, help="requirements 文件（默认 <project>/requirements.txt，无则跳过依赖）")
    ap.add_argument("--python-version", default="3.12.5", help="嵌入式 Python 版本（默认 3.12.5；3.15+ 不可用）")
    ap.add_argument("--variant", choices=["gui", "cli"], default="gui", help="默认 gui（交付用 gui，cli 仅调试）")
    ap.add_argument("--arch", choices=["x64", "x86"], default="x64")
    ap.add_argument("--icon", default=None, help=".ico 文件路径（可选）")
    ap.add_argument("--dist-dir", default=None, help="默认 <project-dir>/dist")
    ap.add_argument("--cache-dir", default=None, help="默认 ~/.cache/pystand-pack")
    ap.add_argument("--with-tkinter", action="store_true", help="强制复制 tkinter（默认扫描源码自动判定）")
    ap.add_argument("--skip-tkinter", action="store_true", help="跳过 tkinter（覆盖自动判定）")
    ap.add_argument("--tkinter-source", default=None, help="完整 Python 安装路径（tkinter 复制源，默认自动探测）")
    ap.add_argument("--debug-cli", action="store_true", help="额外产出 <AppName>-cli.exe（带控制台的调试变体）")
    ap.add_argument("--slim", action="store_true", help="发布瘦身：删 pip 本体等（牺牲 runtime\\python.exe 的调试能力）")
    args = ap.parse_args()

    project = Path(args.project_dir).resolve()
    entry = args.entry or "main.py"
    gen_entry = args.server and args.entry is None  # --server 且未显式指定入口 → 由模板生成
    app_name = args.app_name or project.name
    pyver = args.python_version
    major_minor = ".".join(pyver.split(".")[:2])
    dist = Path(args.dist_dir).resolve() if args.dist_dir else project / "dist"
    cache = Path(args.cache_dir).resolve() if args.cache_dir else Path.home() / ".cache" / "pystand-pack"

    if not gen_entry and not (project / entry).exists():
        die(f"入口文件不存在: {project / entry}")
    reqs = Path(args.requirements).resolve() if args.requirements else project / "requirements.txt"
    if args.server and not reqs.exists() and (project / "uv.lock").exists():
        step("uv export（无 requirements.txt，从 uv.lock 锁版本导出）")
        reqs = cache / f"requirements-{app_name}.txt"
        r = subprocess.run(["uv", "export", "--project", str(project), "--no-hashes",
                            "--no-emit-project", "-o", str(reqs)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            die(f"uv export 失败（需要 uv 在 PATH）:\n{r.stderr[-2000:]}")
        print(f"  {reqs}")
    if args.icon and not Path(args.icon).exists():
        die(f"--icon 文件不存在: {args.icon}")

    app = dist / app_name
    rt = app / "runtime"
    step(f"参数确认: app={app_name} python={pyver}({args.arch}) variant={args.variant} entry={entry}"
         + (f" server={args.app_target or '(auto)'}@{args.host}:{args.port}" if args.server else ""))

    # 1. 下载
    step("下载（有缓存，二次打包直接跳过）")
    embed_zip = download(URLS["embed"].format(v=pyver, arch=EMBED_ARCH[args.arch]), cache / f"python-{pyver}-embed-{EMBED_ARCH[args.arch]}.zip")
    pystand_zip = download(URLS["pystand"], cache / f"PyStand-v{PYSTAND_TAG}-exe.zip")
    getpip_py = download(URLS["getpip"], cache / "get-pip.py")

    # 2. 清场 + 解压 runtime
    step("搭建目录")
    if rt.exists():
        shutil.rmtree(rt)  # 幂等重打包
    rt.mkdir(parents=True)
    with zipfile.ZipFile(embed_zip) as z:
        z.extractall(rt)
    print(f"  runtime: {len(list(rt.iterdir()))} 个文件")

    # 3. ._pth（坑: 隔离模式。加 ../site-packages + 启用 import site 便于 runtime\python.exe 调试）
    pths = list(rt.glob("python*._pth"))
    if not pths:
        die("runtime 里找不到 python*._pth（embed 包结构异常）")
    pth = pths[0]
    lines = pth.read_text().splitlines()
    lines = ["import site" if l.strip() == "#import site" else l for l in lines]
    if "../site-packages" not in lines:
        lines.append("../site-packages")
    pth.write_text("\n".join(lines) + "\n")
    print(f"  ._pth 已改: {pth.name} (+../site-packages, +import site)")

    # 4. get-pip 引导 + 依赖安装（坑: 必须 --target 到 HOME 的 site-packages）
    sp = app / "site-packages"
    sp.mkdir(exist_ok=True)
    pyexe = str(rt / "python.exe")
    if reqs.exists():
        step("pip 引导")
        r = subprocess.run([pyexe, str(getpip_py), "--no-warn-script-location"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            die(f"get-pip 失败:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
        step(f"安装依赖 → {sp}")
        r = subprocess.run([pyexe, "-m", "pip", "install", "-r", str(reqs), "--target", str(sp),
                            "--no-warn-script-location", "-q"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            die(f"pip install 失败:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
        print(r.stdout.strip()[-500:] or "  ok")
    else:
        print("\n=== 跳过依赖（无 requirements.txt）")

    # 5. tkinter（坑: embed 从不带，pip 装不了；自动扫描）
    need_tk = args.with_tkinter
    if not args.skip_tkinter and not need_tk:
        pat = re.compile(r"^\s*(import|from)\s+(tkinter|turtle)\b", re.M)
        for f in project.rglob("*.py"):
            if "__pycache__" in f.parts or "dist" in f.parts:
                continue
            if pat.search(f.read_text(encoding="utf-8", errors="ignore")):
                need_tk = True
                print(f"\n=== 检测到 tkinter 使用: {f.relative_to(project)}")
                break
    tcl_dir, tk_dir = "tcl8.6", "tk8.6"
    if need_tk and not args.skip_tkinter:
        step("复制 tkinter 四件套")
        src = find_tkinter_source(major_minor, args.arch, args.tkinter_source)
        copy_tkinter(src, app)
        got = sorted((rt / "tcl").glob("tcl8.*")) + sorted((rt / "tcl").glob("tk8.*"))
        tcls = [d.name for d in got if d.name.startswith("tcl8") and "." in d.name]
        tks = [d.name for d in got if d.name.startswith("tk8") and "." in d.name]
        tcl_dir, tk_dir = (tcls[-1] if tcls else "tcl8.6"), (tks[-1] if tks else "tk8.6")

    # 6. 源码 + 启动脚本（坑: _pystand_static.int 优先级最高、GUI 异常需落日志）
    step("复制源码与启动脚本")
    app_src = app / "app"
    if app_src.exists():
        shutil.rmtree(app_src)
    (app / "app").mkdir()
    for f in project.glob("*.py"):
        shutil.copy2(f, app_src / f.name)
    for f in project.glob("*.txt"):
        if f.name == "requirements.txt":
            shutil.copy2(f, app_src / f.name)
    if args.server and (project / "src").is_dir():
        # src 布局: src/<pkg> → app/<pkg>（app/ 在 sys.path 上，包内代码零改动）
        for child in (project / "src").iterdir():
            if child.name == "__pycache__":
                continue
            dest = app_src / child.name
            if child.is_dir():
                shutil.copytree(child, dest, ignore=shutil.ignore_patterns("__pycache__"))
            else:
                shutil.copy2(child, dest)
        print("  src 布局: src/* → app/")
    for name in (".env", ".env.example", "README.md"):
        if (project / name).exists():
            shutil.copy2(project / name, app / name)
    if (app / ".env").exists():
        print("  已复制 .env（若含真实凭据，注意产物分发范围）")
    if gen_entry:
        target = args.app_target
        if not target:
            pkgs = [d.name for d in app_src.iterdir()
                    if d.is_dir() and (d / "main.py").exists() and not d.name.startswith(("_", "."))]
            if not pkgs:
                die('--server 未在 app/ 下找到含 main.py 的包目录；请用 --app-target 显式指定，如 mypkg.main:app')
            target = f"{pkgs[0]}.main:app"
        (app_src / "main.py").write_text(
            SERVER_MAIN_TEMPLATE.replace("@@APP_TARGET@@", target)
                                .replace("@@HOST@@", args.host)
                                .replace("@@PORT@@", str(args.port)),
            encoding="utf-8")
        print(f"  server 入口: app/main.py（{target} @ {args.host}:{args.port}，日志→logs/run.log，stop.flag 停机）")
    (app / "_pystand_static.int").write_text(
        INT_TEMPLATE.format(tcl_dir=tcl_dir, tk_dir=tk_dir, entry=entry), encoding="utf-8")
    print(f"  app/*.py + _pystand_static.int (entry={entry})")

    # 7. exe（改名机制 + 可选图标）
    step("PyStand exe")
    with zipfile.ZipFile(pystand_zip) as z:
        member = f"{PYSTAND_VARIANT[(args.arch, args.variant)]}/PyStand.exe"
        exe_path = app / f"{app_name}.exe"
        exe_path.write_bytes(z.read(member))
    if args.icon:
        rcedit = download(URLS["rcedit"], cache / "rcedit-x64.exe")
        r = subprocess.run([str(rcedit), str(exe_path), "--set-icon", str(Path(args.icon).resolve())],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            die(f"rcedit 改图标失败: {r.stderr[-1000:]}")
        print(f"  图标已写入: {args.icon}")
    if args.debug_cli:
        with zipfile.ZipFile(pystand_zip) as z:
            member = f"{PYSTAND_VARIANT[(args.arch, 'cli')]}/PyStand.exe"
            # CLI 变体与主 exe 共用 _pystand_static.int（同级优先级：static 拦截所有 exe，
            # 正好让 CLI 变体以带控制台方式跑同一入口，stdout/traceback 直接可见）
            (app / f"{app_name}-cli.exe").write_bytes(z.read(member))
        print(f"  调试变体: {app_name}-cli.exe（复用 _pystand_static.int，有 stdout）")
    if args.server:
        bat = app / f"stop-{app_name}.bat"
        bat.write_text(STOP_BAT_TEMPLATE.replace("@@EXE@@", f"{app_name}.exe"), encoding="ascii")
        print(f"  停机脚本: {bat.name}（双击优雅停机；无控制台 bat 三坑已规避，见 pitfalls.md 坑 11）")

    # 8. 清理（坑: pip --target 的 bin/；slim 删 pip 本体）
    step("清理")
    shutil.rmtree(app / "site-packages" / "bin", ignore_errors=True)
    for junk in (rt / "get-pip.py",):
        junk.unlink(missing_ok=True)
    if args.slim:
        shutil.rmtree(rt / "Lib" / "site-packages", ignore_errors=True)
        shutil.rmtree(rt / "Scripts", ignore_errors=True)
        for cat in rt.glob("*.cat"):
            cat.unlink()
        print("  slim: 已删 pip 本体（runtime\\python.exe 失去 -m pip，主 exe 不受影响）")

    # 9. 完成
    total = sum(f.stat().st_size for f in app.rglob("*") if f.is_file())
    step(f"完成: {app}  ({total / 1024 / 1024:.1f} MB)")
    for p in sorted(app.iterdir()):
        kind = "/" if p.is_dir() else ""
        print(f"  {p.name}{kind}")
    if args.server:
        print(f"""验证提示（服务器型无窗口，不要用窗口标题判定）:
  PowerShell: Start-Process <app>\\{app_name}.exe; 轮询 http://{args.host}:{args.port}/health 应返回 JSON（DB 不通时 degraded 也算进程正常）
  停机: 双击 stop-{app_name}.bat → "stopped gracefully" + 进程退出 = 优雅停机通过
  日志: <app>\\logs\\run.log（console= 行说明当前走的输出分支）；异常: pystand-error.log""")
    else:
        print(f"""验证提示（GUI 变体不要用"进程活着"判定，异常会弹隐藏 MessageBox）:
  cd "{app}"
  ./{app_name}.exe &
  sleep 6 && powershell -NoProfile -Command "Get-Process {app_name} -ErrorAction SilentlyContinue | Select -ExpandProperty MainWindowTitle"
  # 窗口标题出现 = 通过；为空 = 查看 pystand-error.log
  taskkill //IM {app_name}.exe //F""")


if __name__ == "__main__":
    main()
