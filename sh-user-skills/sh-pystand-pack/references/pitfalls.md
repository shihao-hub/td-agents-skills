# PyStand 踩坑手册（2026-08-24 全流程实测；10~12 节为 2026-08-26 服务器型实战补充）

打包失败、产物行为异常时读本文件。全部条目来自真实实验（Windows 11 x64、无系统级 Python、无编译器环境），验证矩阵见文末。

## 目录
1. [URL 与下载清单](#1-url-与下载清单)
2. [._pth 隔离模式与 sys.path 规则](#2-_pth-隔离模式与-syspath-规则)
3. [启动脚本查找顺序（_pystand_static.int 优先级）](#3-启动脚本查找顺序)
4. [GUI 变体的隐藏行为](#4-gui-变体的隐藏行为)
5. [tkinter 四件套](#5-tkinter-四件套)
6. [Git Bash / Windows 工具链坑](#6-git-bash--windows-工具链坑)
7. [版本边界与兼容性](#7-版本边界与兼容性)
8. [手动复刻流程](#8-手动复刻流程)
9. [验证矩阵](#9-验证矩阵)
10. [服务器型应用交付（--server 预设）](#10-服务器型应用交付server-预设)
11. [无控制台环境的 bat 三坑](#11-无控制台环境的-bat-三坑)
12. [uv 项目 / src 布局适配](#12-uv-项目--src-布局适配)

## 1. URL 与下载清单

| 资源 | URL 模板 | 坑 |
|---|---|---|
| 嵌入式 Python | `https://www.python.org/ftp/python/{v}/python-{v}-embed-amd64.zip`（32 位 `embed-win32.zip`） | 3.5+ 每个版本都有，3.12.5 = 10.5MB |
| PyStand exe 包 | `https://github.com/skywind3000/PyStand/releases/download/1.1.5/PyStand-v1.1.5-exe.zip` | **tag 无 `v` 前缀**！错 URL 返回 9 字节 "Not Found" |
| get-pip | `https://bootstrap.pypa.io/get-pip.py` | EOL 版本要用 `https://bootstrap.pypa.io/pip/{v}/get-pip.py` |
| rcedit | `https://github.com/electron/rcedit/releases/download/v2.0.0/rcedit-x64.exe` | 最新就是 v2.0.0（v2.1.0 不存在） |

- zip 内含 8 个 exe 变体：`PyStand-{x64|Win32|mingw32|mingw64}-{GUI|CLI}/PyStand.exe`。MSVC 的 `x64`/`Win32` 为首选。
- 拿准确资产名：GitHub API `https://api.github.com/repos/skywind3000/PyStand/releases/latest`。

## 2. ._pth 隔离模式与 sys.path 规则

embed 包的 `python312._pth`（文件名带版本号）使解释器**完全隔离**：忽略 PYTHONPATH 等环境变量，sys.path 固定为文件内容（默认 `python312.zip` + `.`）。

- **pip 默认装进 `runtime\Lib\site-packages`，PyStand 看不见**。PyStand 初始化只把 **HOME（exe 同级）** 下的 `. / lib / site-packages / runtime` 加入 sys.path。
- 修正（pack.py 已内置）：pip 用 `--target <HOME>\site-packages`；`._pth` 追加一行 `../site-packages` 并把 `#import site` 取消注释——后者让 `runtime\python.exe` 也能 import 用户依赖（调试入口）。
- 发布目录不要放多余路径进 `._pth`；隔离模式同时是优点（不受系统环境变量污染）。

## 3. 启动脚本查找顺序

`DetectScript()` 顺序（源码实证）：

1. **`<HOME>\_pystand_static.int`——存在即用，拦截一切**（任何名字的 PyStand exe）
2. `<exe去扩展名>.int`（如 `PyStand-CLI.exe` → `PyStand-CLI.int`）
3. `<exe去扩展名>.py` / `.pyw`
4. 都没有 → 弹错误 MessageBox（无头环境 = 挂死）

- 实验事故复盘：目录里有 `_pystand_static.int` 后，`PyStand-CLI.exe`（console 变体）也执行它跑起 GUI mainloop——表现为"stdout 空、debug 日志不出现、进程 45MB 挂死"，被误判为 exe 损坏/杀软拦截排查近一小时。
- 规则：**发布目录只放一个启动脚本**；临时调试同名 `.int` 机制时先挪走 `_pystand_static.int`。
- `.int` 有 32KB 大小限制（PyStand 用命令行 `-c` 传入）；`runpy.run_path` 方式不受影响。

## 4. GUI 变体的隐藏行为

- GUI 变体（无 `PYSTAND_CONSOLE` 宏编译）启动时若无 attached console：**stdout/stderr 重定向到 devnull**——print 全部消失，不是 bug。
- `.int` 抛异常时弹 **MessageBox**（无头/自动化环境表现为进程挂死不死）。pack.py 生成的启动脚本已内置异常落盘 `pystand-error.log` + `raise`。
- CLI 变体在无控制台的后台环境（任务计划器、服务、某些 CI 通道）可能挂起；有真终端时一切正常。**交付一律 GUI 变体**。
- **控制台检测语义（2026-08-26 实测）**：`ctypes.windll.kernel32.GetConsoleWindow()` 是入口脚本判断"有没有控制台"的可靠手段——双击 `*-cli.exe` 或真终端里跑 = 有（值非 0）；GUI 变体、重定向管道、无头调度器 = 没有（值为 0）。隐藏窗口启动（`-WindowStyle Hidden`）仍算有控制台。server 入口按此分流：有控制台 → tee（控制台+文件双写）；无 → 纯落盘。**在无头宿主里测 CLI 变体捕获不到 stdout 属预期行为，不是 bug**——此刻它走的就是落盘分支。
- `sys.argv[0]` 是 `.int` 文件路径；用户命令行参数从 `argv[1:]`。`sys.executable` = PyStand exe；注入属性：`sys.PYSTAND_HOME / PYSTAND_SCRIPT / PYSTAND_SEP`。

## 5. tkinter 四件套

embed 包从不包含 tkinter（cpython#99566），且 pip 装不了（不在 PyPI）。必须从**同 minor 版本、同位数完整安装**复制：

| 源位置 | 目标位置 | 内容 |
|---|---|---|
| `Lib/tkinter` | `<HOME>\site-packages\tkinter` | 纯 py 包（site-packages 在 sys.path 上） |
| `DLLs/_tkinter.pyd` | `<HOME>\runtime\` | 扩展（runtime 在 sys.path 上且是 DLL 搜索目录） |
| `DLLs/tcl86t.dll tk86t.dll` | `<HOME>\runtime\` | tcl/tk 本体 |
| `tcl/{tcl8, tcl8.6, tk8.6}` | `<HOME>\runtime\tcl\` | tcl 数据目录 |

- 3.12.x 内 ABI 兼容：uv managed 的 cpython-3.12（3.12.11 构建）配官方 3.12.5 embed 实测可用。
- `TCL_LIBRARY/TK_LIBRARY` 实测可不设（tcl 自动发现 `runtime\tcl\tcl8.6`），但启动脚本里 `setdefault` 更稳。
- 复制源探测顺序（pack.py 内置）：`--tkinter-source` 显式指定 → `%APPDATA%\uv\python\cpython-{mj}.*-windows-x86_64-none` → `py -0p` 解析 → 下载同版本安装器静默装临时目录（`python-3.12.5-amd64.exe /quiet TargetDir=...`）。
- 3.13 的 embed 包曾意外附带 tcl/tk DLL（cpython#126074），但仍缺数据文件与纯 py 部分——四件套逻辑照旧。

## 6. Git Bash / Windows 工具链坑

- Git Bash 的 `tar` 是 GNU tar，**不认 zip** → 用 `/c/Windows/System32/tar.exe`（bsdtar）或 Python `zipfile`。
- **中文路径 mojibake**：bash（UTF-8）→ Windows API（GBK）转码错乱，曾出现 `rm -rf` 报 Device or resource busy 且目录名显示乱码；**PowerShell `Remove-Item` 可正常删**。skill 自动化操作中文路径统一走 PowerShell。
- bash 后台陷阱：`cd X && ./app.exe & sleep N` 中 `&` 把整个 `cd && app.exe` 划为后台 job，后续命令仍在旧 cwd 执行（曾导致"exe 报不存在"假象）。
- 大目录复制是异步缓慢操作，不要和后续启动命令拼在同一条 `&&` 链里。

## 7. 版本边界与兼容性

- PyStand exe **不绑 Python 版本**：它 `LoadLibrary("runtime\\python3.dll")`（稳定 ABI 转发库，任何 embed 包都带）→ 换版本 = 换 runtime 目录，exe 永不重编译。
- 但其内部调用 `Py_Main()`：3.13 起 deprecated，**3.15 移除** → 官方预编译 exe 预计用到 3.14；3.12.x 最稳。
- Win7 目标：Python 3.8（PyStand release 另附 py38 运行时包；或 NulAsh 的 3.10 Win7 移植版）。
- 含 C 扩展依赖（numpy/pydantic-core 等）要求 embed 位数与 wheel 一致（x64 默认）。
- PyQt/PySide：可 pip 装；中文路径下需代码里手动设 Qt 插件目录（PyStand issue #6），未实测。

## 8. 手动复刻流程

pack.py 不可用时的手动等价流程（Git Bash）：

```bash
PY=3.12.5; APP=MyApp; D=dist/$APP
mkdir -p $D/runtime $D/site-packages
curl -L -o /tmp/embed.zip "https://www.python.org/ftp/python/$PY/python-$PY-embed-amd64.zip"
/c/Windows/System32/tar.exe -xf /tmp/embed.zip -C $D/runtime
# ._pth: 追加 ../site-packages，#import site 取消注释
curl -L -o $D/runtime/get-pip.py https://bootstrap.pypa.io/get-pip.py
(cd $D/runtime && ./python.exe get-pip.py --no-warn-script-location)
$D/runtime/python.exe -m pip install -r requirements.txt --target $D/site-packages --no-warn-script-location
# tkinter: 见第 5 节复制四件套（源: %APPDATA%\uv\python\cpython-3.12-*-none）
cp main.py $D/app/  # + 写 _pystand_static.int（模板见 pack.py 的 INT_TEMPLATE）
cp PyStand-x64-GUI/PyStand.exe $D/$APP.exe
rcedit-x64.exe $D/$APP.exe --set-icon app.ico   # 可选
rm -rf $D/site-packages/bin                     # pip --target 的杂物
```

## 9. 验证矩阵（实验实测数据）

| 验证项 | 方法 | 结果 |
|---|---|---|
| GUI 最小闭环 | 进程存活 + `MainWindowTitle` 断言 | ✅ |
| 嵌入式解释器 | `sys.version`=3.12.5、`sys.executable`=exe 自身 | ✅ |
| 第三方依赖 | requests 2.34.2 + 5 个传递依赖 | ✅ |
| tkinter | TkVersion 8.6、`Tk()` init、tcl library 定位 | ✅ |
| 图标 | rcedit `--set-icon`，exe 增 ~5KB | ✅ |
| 改名机制 | `<App>.exe` + `_pystand_static.int` | ✅ |
| CLI 变体 | 前台管道 stdout、exit=0、`argv[1:]` 参数转发 | ✅ |
| 中文路径 | GUI 窗口标题 + CLI 全断言（路径含"中文应用"） | ✅ |
| standalone | 本机无系统级 Python 全程可用 | ✅ |
| 服务器型闭环（2026-08-26） | `/health` 1s 即响应；stop.bat 优雅停机 ~3s，run.log 见 `app_stopped`/`shutdown complete` | ✅ |
| 控制台双分支（2026-08-26） | `console=True` tee 双写逐行 flush；`console=False` 纯落盘；两分支停机均正常 | ✅ |
| --server 一条命令复刻 | pack.py --server 产物与手工适配产物行为一致（仅注释差异） | ✅ |

产物体积参考：requests + tkinter 场景 ≈ 51MB（embed 10.5MB + pip 依赖 + tcl 数据）；FastAPI/uvicorn 全家桶 ≈ 88MB。

## 10. 服务器型应用交付（--server 预设，2026-08-26 FastAPI/uvicorn 实战）

服务器型 = 常驻无窗口进程。与 GUI 型的差异全部固化在 pack.py `--server`：

- **验证方法论反转**：没有窗口标题可看 → 用 `/health` 轮询（`Invoke-RestMethod`，1s 间隔 30s 上限；DB 不通返回 degraded 也算进程活着）+ `logs/run.log` 判定。铁律 3 的"进程活着≠正常"在此处对应为"端口通了≠健康"（health 应带 DB 探活）。
- **入口模板三件事**（SERVER_MAIN_TEMPLATE，缺一不可）：
  1. 日志落盘：GUI 变体 stdout 进 devnull，不重定向 = 日志黑洞。chdir 到产物根后开 `logs/run.log`（append + 行缓冲）。
  2. 控制台检测分流：`GetConsoleWindow()` 有 → Tee 双写（**每行 flush**，见第 11 节③）；无 → 纯落盘。launcher 首行打印 `console=True/False` 便于排查输出分支。
  3. 停机：无窗口没有 Ctrl+C → 看门狗线程每 0.5s 查产物根 `stop.flag`，发现即 `server.should_exit = True`，uvicorn 走完 lifespan 干净退出（日志有 `app_stopped`）。用 `uvicorn.Server(config)` + `server.run()` 而非 `uvicorn.run()`，才能拿到 server 对象置 should_exit。
- **交付物必须带停机脚本** `stop-<App>.bat`（见第 11 节）；任务管理器强杀是最后手段（跳过 lifespan，DB 连接/进行中请求被腰斩）。
- **uvicorn 注意**：`log_config=None` 保留 structlog 配置；`uvloop` 在 win32 自动排除（uv export 的环境标记已处理）；`--reload` 绝不带进产物。
- 已实测：FastAPI + SQLAlchemy + psycopg 连内网 RDS，health 返回真实 DB 状态。未实测：gunicorn/多 worker、websocket 长连接下的优雅停机耗时。

## 11. 无控制台环境的 bat 三坑（2026-08-26 实测，模板已固化 STOP_BAT_TEMPLATE）

1. **`timeout` 命令在无控制台环境直接失败**（"输入重定向不受支持"级错误，GNU 中文代码页下显示乱码）→ 睡眠直接跳过 → 脚本瞬间走到强杀分支。解法：`ping -n 2 127.0.0.1 >nul` 当 ~1s 睡眠——不碰 stdin，任何宿主都可用，且轮询 `tasklist` 进程一退立刻返回，不等满超时。
2. **中文注释 = 定时炸弹**：bat 按 OEM 代码页（如 GBK 936）解析，UTF-8 中文注释轻则 echo 乱码，重则整行解析报错（实测"不是内部或外部命令"）。**bat 全 ASCII**，说明放 rem 里也别用中文。
3. **Python Tee 往管道写必须逐行 flush**：重定向/管道场景 sys.stdout 是块缓冲（~8KB），不 flush 表现为"控制台明明有分支却看不到日志"。`print(flush=True)` 或在 Tee.write 里对每个 stream flush。行缓冲只在 tty/`buffering=1` 文件上生效。

进程检测用 `tasklist /FI "IMAGENAME eq xxx.exe" | find /I "xxx.exe" >nul` + errorlevel 判断；bat 里 `%~dp0` 定位自身目录保证双击可用。

## 12. uv 项目 / src 布局适配（2026-08-26 demo-api 实战，pack.py --server 已自动化）

- **无 requirements.txt 但有 uv.lock** → `uv export --project <dir> --no-hashes --no-emit-project -o <cache>/requirements-<App>.txt`：版本与 uv.lock 完全一致（含 win32 环境标记裁剪，uvloop 自动排除），比手抄 pyproject dependencies 更可靠。
- **src 布局**：pack.py 常规只拷根目录 `*.py`；`--server` 额外把 `src/*` 拷进 `app/`（过滤 `__pycache__`）。`app/` 在 PyStand 注入的 sys.path 上，包内 import 零改动。
- **BASE_DIR 巧合**：`Path(__file__).resolve().parents[2]` 这类"从包内 config.py 往上跳到项目根"的写法，在 `app/<pkg>/config.py` 布局下恰好解析到产物根 → `.env` 放 exe 同级即被 pydantic-settings 自动读到，代码零改动。但 `parents[3]` 及更深跳数会跳过头——打包前扫一眼包内所有 `parents[N]` 用法。
- **.env 凭据**：默认拷贝 `.env` + `.env.example` + README 到产物根并打印提醒；要外发产物时先确认 `.env` 是否该删。
- 常驻服务器应用建议 `--debug-cli` 一起出：调试期真控制台直看日志，交付只发主 exe。
