# Python 模块：pywebview 双通道桌面壳

> 归属：`sh-desktop-dual-channel`。本文是 Python 分支的运行时 SOP；打包见 `python-nuitka.md`。
> 验证锚点：`python_projects/zedhub`（2026-10 全链路实测）。
> 环境：Windows 11 24H2、Python 3.12、pywebview 6.2、pystray 0.19、WebView2 155、Nuitka 4.3、MSVC 2022。

---

## 一、前置检查

```powershell
uv --version
python -c "import webview, pystray, PIL; print(webview.__version__)"
# WebView2 Runtime：HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}
uv run scripts/render_icon.py     # 生成 icon.png / icon.ico / icon-256.png / PWA SVG
```

- **依赖**：`pywebview>=5`、`pystray>=0.19`、`pillow>=10`；打包期 `nuitka>=2.5`、`zstandard>=0.22`（见 `python-nuitka.md`）。
- **数据目录**：只落 `%APPDATA%\language_projects\<app>\<channel>\`，取不到 APPDATA 回退 `~/.language_projects/<app>/<channel>/`。
- **入口**：`pyproject.toml` 保留两个 script——`<app>`（CLI）与 `<app>-gui`（桌面壳）。

---

## 二、适用范围

| 旧项目现状 | 建议 | 代价 |
|---|---|---|
| 已有 HTTP 层 / 静态前端，只缺桌面宿主 | 补壳（本文），推荐 | 低 |
| 已有 `ui --app`（Chrome `--app` 借壳） | 升级为自有壳：托盘、图标、几何、单实例 | 低 |
| 纯 CLI、无 HTTP 层 | 先抽 HTTP Handler + `/ui`，再加壳 | 中 |
| 纯 Web/PWA、无本地服务 | 评估是否需要本地能力；不需要则保持 PWA | 零 |
| 前端与后端同进程强耦合 | 先解耦成 daemon + 薄壳，再套本文 | 中高 |

判断锚点：**有没有独立 HTTP 层**。没有就先别加壳，否则窗口只是另一个 WebView 套壳。

---

## 三、目录结构

```text
<project>/
├── pyproject.toml                 # [project.scripts] <app> 与 <app>-gui
├── src/<pkg>/
│   ├── cli.py                     # CLI 薄客户端（Typer）
│   ├── api.py / http_api.py       # HTTP Handler（GUI 与 CLI serve 共用）
│   ├── channel.py                 # dev/prod 通道判定 + 数据目录
│   ├── buildid.py                 # 源码指纹 / 版本 → 握手 buildID
│   ├── logx.py                    # 双写落盘日志
│   ├── webui/                     # index.html / app.js / style.css / icon.svg
│   └── gui/
│       ├── app.py                 # 壳：窗口 / 托盘 / 重建 / 单实例 / 内存治理
│       ├── window_state.py        # 几何记忆（纯函数，可单测）
│       └── assets/icon.ico|png     # release 图标（render_icon.py 生成）
├── scripts/
│   ├── render_icon.py             # PNG/ICO/SVG 同源生成
│   ├── gui_entry.py               # Nuitka GUI 入口（无控制台）
│   ├── cli_entry.py               # Nuitka CLI 入口（控制台）
│   └── build_exe.py               # 双通道构建（见 python-nuitka.md）
└── bin/                           # 产物（gitignore）
```

---

## 四、分步 SOP

### Step 1 双入口（CLI / GUI）

```toml
[project.scripts]
myapp = "myapp.cli:app"
myapp-gui = "myapp.gui:main"
```

- GUI 入口只做壳，**不 import `core`**、不直连数据库；
- CLI 入口保持纯终端语义；
- 打包时两个入口分别编成 console / GUI 子系统（`python-nuitka.md`）。

**校验**：`uv run myapp --help` 有输出；`uv run myapp-gui` 只出窗口。

### Step 2 HTTP 层与 WebUI 共用同一 Handler

```python
def build_app():
    routes = [Route(ep.path, dispatch, methods=[ep.method]) for ep in HTTP_ENDPOINTS]
    routes.extend(static_routes())      # /ui + 静态资源
    return Starlette(routes=routes)
```

- `serve` 与 GUI 都调 `build_app()`；
- 根路径必须是完整 WebUI，不能 404；
- 静态资源白名单后缀，禁止目录遍历；
- `Host` 必须回环（防 DNS rebinding）。

**校验**：`myapp serve --port 0` 打印的地址打开是完整页面，`/api/*` 正常。

### Step 3 桌面壳（pywebview）

```python
webview_data = data_dir() / "webview"
webview_data.mkdir(parents=True, exist_ok=True)

window = webview.create_window(
    "MyApp", url,
    width=state.width, height=state.height,
    x=state.x, y=state.y, maximized=state.maximized,
    min_size=(480, 360),
    background_color="#121316",   # 与页面暗色底一致，避免首帧闪白
    text_select=True,
    js_api=bridge,                # 页面 → Python 的桥（可选）
)
webview.start(
    func=boot_tray,
    icon=str(ICON_ICO),
    private_mode=False,           # 否则 cookie/localStorage 每次清空
    storage_path=str(webview_data),
)
```

- 窗口 URL 来自 daemon 实际监听地址（动态端口时从地址文件取）；
- **`icon=` 必须传 `.ico`**：传 PNG 会触发 .NET `ArgumentException: 参数 picture 不是可用于 Icon 的图片`；
- **站点数据必须落自有目录**：`private_mode=False` + `storage_path=<dataDir>/webview`，主题/偏好才持久，且不污染外部目录；
- 壳内嵌 daemon 时用后台线程跑同一 `serve_with_lifecycle`；已有 CLI `serve` 在跑则复用地址（Step 8）；
- `js_api` 用于页面驱动宿主能力（主题、快捷键），不要在壳里塞业务。

**可选：Windows 深色标题栏**（页面主题跟随，非所有项目必需）：

```python
class TitleBarTheme:
    def _hwnd(self):
        user32 = ctypes.windll.user32
        user32.FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
        user32.FindWindowW.restype = ctypes.c_void_p
        return int(user32.FindWindowW(None, "MyApp") or 0)

    def apply(self, theme: str) -> bool:
        hwnd = self._hwnd()
        value = ctypes.c_int(1 if theme != "light" else 0)
        for attr in (20, 19):   # DWMWA_USE_IMMERSIVE_DARK_MODE 新版/旧版
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd), attr, ctypes.byref(value), ctypes.sizeof(value)
            )
            if result == 0:
                return True
        return False

# 绑定：js_api=titlebar；每次窗口 shown 后 apply("dark")
# 关窗销毁 + 重建后 HWND 会变，必须按标题重新查找，不能缓存句柄
```

**校验**：窗口标题栏与任务栏图标正确；WebUI 完整加载；切换主题后重开仍保持。

### Step 4 托盘（pystray）

```python
def _start_tray(show_cb, quit_cb, url):
    import pystray
    from PIL import Image

    image = Image.open(app_icon())      # ICO/PNG 均可被 Pillow 打开
    tray = pystray.Icon("myapp", image, "MyApp", pystray.Menu(
        pystray.MenuItem("显示窗口", lambda *_: show_cb(), default=True),
        pystray.MenuItem("在浏览器打开", lambda *_: webbrowser.open(url)),
        pystray.MenuItem("退出", lambda icon, _: quit_cb(icon)),
    ))
    tray.run_detached()
    return tray
```

- 托盘必须**在 `webview.start(func=...)` 的线程里创建**，不要在 `start` 前抢主线程消息循环；
- 托盘失败（RDP/无通知区域）返回 `None`，关窗即退出，避免主线程永久等待。

### Step 5 关窗销毁 + 托盘重建（核心，别用 hide）

```python
holder = {}
show_requested = threading.Event()
quitting = threading.Event()

def _build_window():
    window = webview.create_window(...)
    holder["window"] = window
    window.events.closed += lambda *args: _on_closed()
    return window

def _on_closed():
    holder["window"] = None
    gc.collect()                          # 对齐 go-wails 的 runtime.GC
    if sys.platform == "win32":
        ctypes.windll.psapi.EmptyWorkingSet(
            ctypes.windll.kernel32.GetCurrentProcess()
        )                                 # FreeOSMemory：把工作集还给系统

def _show_window():
    window = holder.get("window")
    if window is not None:
        window.show(); window.restore(); return
    show_requested.set()

while not quitting.is_set():
    _build_window()
    webview.start(func=boot_tray, icon=str(ICON_ICO), ...)
    if quitting.is_set() or holder.get("tray") is None:
        break
    show_requested.wait(); show_requested.clear()
```

- **不要用 `closing` 返回 False + `window.hide()`**：那是隐藏，WebView2 子进程与内存全部驻留；
- 放行关闭 → 窗口销毁 → 子进程退出（实测 6 → 0）→ `gc.collect()` + `EmptyWorkingSet`；
- pywebview 允许**二次 `webview.start()`**（窗口列表清空后重新创建即可），这是托盘重建的基础；
- 托盘「退出」：`quitting.set()` + `show_requested.set()` + `window.destroy()` → 主循环退出。

**控制台 Ctrl+C 兜底**（pywebview 把主线程交给 WinForms，SIGINT 不派发）：

```python
class ConsoleQuitHook:
    def __init__(self, on_quit):
        self._on_quit = on_quit
        self._cb = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)(self._handle)

    def _handle(self, event: int) -> bool:   # 回调跑在独立线程，禁止抛异常
        try:
            self._on_quit()
        except Exception:
            return False
        return True

    def install(self):
        return bool(ctypes.windll.kernel32.SetConsoleCtrlHandler(self._cb, True))

    def uninstall(self):
        ctypes.windll.kernel32.SetConsoleCtrlHandler(self._cb, False)
```

**校验**：关窗后任务管理器里该进程的 `msedgewebview2.exe` 子进程归零；托盘右键「显示窗口」按上次几何重建；控制台 Ctrl+C 能退出。

### Step 6 窗口几何记忆

```python
@dataclass
class WindowState:
    width: int = 1280
    height: int = 840
    x: int | None = None
    y: int | None = None
    maximized: bool = False
```

- 落 `<dataDir>/window.json`（dev/prod 隔离，无 BOM UTF-8，`os.replace` 原子写）；
- Windows 下 `window.x/y/width/height` 已是 DIP，原值存取，不要再叠加缩放；
- `events.moved` / `events.resized` → **700ms 防抖**保存；
- 最大化：`events.maximized` 只置标记，`resized` 回调在最大化期间直接 return；
- 最小化坐标是 `-25600/-32000`：保存前用 `MonitorFromPoint` 校验可见性；
- 尺寸 < 480×360 或 > 16384 视为脏数据，回落默认。

```python
def visible_on_screen(x, y, width, height) -> bool:
    class _Point(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    user32 = ctypes.windll.user32
    user32.MonitorFromPoint.argtypes = [_Point, ctypes.c_ulong]
    user32.MonitorFromPoint.restype = ctypes.c_void_p
    point = _Point(x + width // 2, y + min(40, height // 2))
    return bool(user32.MonitorFromPoint(point, 0))   # MONITOR_DEFAULTTONULL
```

**校验**：移动缩放 → 等 1s → `window.json` 与窗口一致；最大化后关窗重开仍是最大化，且还原尺寸未被写坏。

### Step 7 单实例（OS 文件锁）

```python
class InstanceLock:
    def __init__(self, path): ...
    def acquire(self):
        fh = open(self.path, "a+b")
        fh.seek(0)
        if sys.platform == "win32":
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
```

- **动态端口下不能靠端口占用判互斥**：两个进程会各自拿到不同随机端口；
- 文件锁由内核在进程退出时自动释放，无陈旧锁；
- 壳与 daemon 各一把锁（`gui.lock` / `daemon.lock`），不要共用一个文件；
- 锁文件可以保留（0 字节也无妨），不要为了「干净」在退出时删除——删除会引入竞态。

**校验**：并发启动第二个实例被拒绝；硬杀进程后再次启动正常。

### Step 8 dev/prod 通道隔离

```python
def channel() -> str:
    override = os.environ.get("APP_CHANNEL")
    if override in ("dev", "prod"):
        return override
    return "prod" if is_production_build() else "dev"
```

| 维度 | dev | prod |
|---|---|---|
| 数据根 | `%APPDATA%\...\<app>\dev` | `...\<app>\prod` |
| HTTP 端口 | 动态（0，写地址文件） | 固定 |
| 日志 | `<通道>/runtime/app.log` | 同左 |
| buildID | 源码指纹 / `frozen` | 版本号 |
| 图标 | 语言默认图标（如 Python 双蛇） | 专属图标 |

**动态端口**：uvicorn 在 lifespan startup 之后才 bind，此时拿不到端口。先自行 bind，再把同一 socket 交给 uvicorn：

```python
sock = socket.socket(family, socktype, proto)
sock.bind(addr)                      # addr 来自 getaddrinfo(host, 0)
actual_port = sock.getsockname()[1]
server.run(sockets=[sock])           # uvicorn.Server
```

**地址文件**（所有壳的共同入口）：

```python
tmp = path.with_suffix(".json.tmp")
tmp.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
os.replace(tmp, path)                # 原子替换，避免壳读到半截 JSON
```

记录 `host / port / ws_port / pid / build_id / version / channel / data_dir / auto_spawned`；存活判定用「端口可连 + `/health` 通过」，pid 仅作诊断。

**GUI 与 daemon 的协作**：

- 壳启动先探测地址文件 + `/health`：已有 CLI `serve` 就复用，不重复起进程；
- 自己起 daemon 时用后台线程跑 `serve_with_lifecycle`，通过 `on_ready(server, http_port, ws_port)` 回传 uvicorn `server` 引用；
- 退出时 `server.should_exit = True` + `thread.join(timeout)`，等 WAL checkpoint；复用的外部 daemon 不要停。

**自动拉起**（仅 prod）：

- 连接失败且**未显式指定地址**才 detach 拉起（`DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`）；
- dev 一律报错并提示先 `serve`；显式 `--host` / 环境变量指向的实例不存在时绝不本地拉起；
- 拉起期 stderr 落 `runtime/daemon.boot.log`（解释器/import 崩溃兜底），daemon 起来后由 `logx` 接管 `daemon.log`。

**buildID 握手**：

- dev = `dev-{源码指纹}`（相对路径 + size + mtime_ns 聚合哈希；打包后无 `.py` → `frozen`）；
- prod = `v{version}`；
- 壳请求带 `X-Build`，不等返回 409，提示「daemon 是旧构建，请重启」——改代码只重启一边会被当场检出。

**一次性迁移**：首次进入通道目录时把旧扁平目录的 `index`/`operations` **复制**过来，旧文件保留；写 `.migrated-v1` 标记，全局只迁一次；`backups`/`snapshots` 体积大且可回溯，留在旧根目录；`runtime` 含陈旧地址/日志，不迁。

### Step 9 落盘日志（无控制台可排障）

```python
class _Tee(io.TextIOBase):
    def write(self, text):
        try: self._file.write(text); self._file.flush()
        except OSError: pass
        try: self._original.write(text)
        except (OSError, AttributeError): pass
```

- 文件优先、stderr 容错；stderr 失败绝不能阻断文件落盘；
- 单文件 2 MB × 1 份轮转（启动时检查，`os.replace` 原子换名）；
- 启动横幅：version / build / channel / 端口 / 数据目录 / 日志路径；
- 接管 uvicorn 日志：**`uvicorn.Config(..., log_config=None)`**——Nuitka 打包后 `dictConfig` 解析
  `uvicorn.logging.DefaultFormatter` 会抛 `ValueError: Unable to configure formatter 'default'`；
- panic：`sys.excepthook` 写完整栈并提示日志路径；
- **幂等细节**：分别记录 `original`（tee 目标）与 `restore`（初始化前的 `sys.stderr`），
  重复 `init_logging` 只替换文件句柄，不叠加 tee；`fileno()` 转发给原 stderr，兼容调用方探测。

### Step 10 图标双通道（运行时）

- `scripts/render_icon.py` 用 Pillow 超采样生成 1024 PNG + 16–256 七帧 ICO + 512 PWA PNG + 同几何 SVG；
- dev 用语言默认图标（Python 用 `docs/assets/projects/python_projects/python-default.ico`）；
- release 用专属图标；
- 运行时 `app_icon()` 按 `is_production_build()` 返回 ICO；托盘用 `PIL.Image.open()` 读同一 ICO；
- **dev 回退链**：打包内 `icon-dev.ico`（构建时 include）→ 源码态父仓绝对路径 → 专属图标；
- PE 写入与 `--include-data-file` 见 `python-nuitka.md`。

### Step 11 内存治理（WebView2）

**开窗峰值**：WebView2 默认会拉起 GPU / 多个 renderer / 独立网络进程。可在创建窗口前裁剪：

```python
os.environ.setdefault(
    "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS",
    "--disable-gpu --disable-gpu-compositing --disable-software-rasterizer "
    "--renderer-process-limit=1 --disable-features=NetworkServiceOutOfProcess",
)
```

- 实测开窗峰值约降 100 MB；
- **副作用**：禁用 GPU 可能影响动画/视频/复杂 CSS 渲染。面向重媒体应用时只保留
  `--renderer-process-limit=1` 与 `--disable-features=NetworkServiceOutOfProcess`，不要盲目关 GPU；
- 参数必须在 `webview.start()` 之前写入环境变量。

**关窗回收**：`gc.collect()` + `EmptyWorkingSet(GetCurrentProcess())`（Step 5）。

**验收**：关窗后该进程的 `msedgewebview2.exe` 子进程数归零、工作集明显回落；重开窗口功能正常。

### Step 12 SQLite 并发守卫

```python
con = sqlite3.connect(db_path, timeout=5.0)
con.execute("PRAGMA busy_timeout=5000")
con.execute("PRAGMA journal_mode=WAL")
```

- GUI 内嵌 daemon + 多个 CLI 可能同时打开同一索引库；
- `timeout` 是 Python 的 busy timeout，跨进程生效；
- WAL 持久化到库文件，写一次后对新连接持续有效。

**校验**：两个写者并发执行，期间读请求正常；无 `database is locked`。

---

## 五、与 Go 模块差异

| 维度 | Go / Wails | Python / pywebview |
|---|---|---|
| 双产物手段 | build tag + `-H windowsgui` | 两个 Nuitka 入口 + console mode |
| PE 资源 | go-winres + `.syso` + manifest | Nuitka `--windows-icon-from-ico` / `--file-version` |
| 单实例 | Wails `UniqueID` | OS 文件锁（`msvcrt` / `fcntl`） |
| 窗口重建 | Wails 原生支持 | 二次 `webview.start()` |
| 托盘 | Wails 内置 | pystray `run_detached` |
| 窗口几何 | `win.Size()/Position()`（DIP） | `window.x/y/width/height`（DIP） |
| 日志 | `logf` 双写 | `logx` tee + `log_config=None` |
| 版本判定 | tag + 工作区 | 包版本干净号（hatch-vcs） |
| 内存回收 | `runtime.GC()` + `FreeOSMemory()` | `gc.collect()` + `EmptyWorkingSet` |

---

## 六、已实测踩坑

| 症状 | 根因 | 处置 |
|---|---|---|
| 启动即退，退出码 `0xE0434352` | `webview.start(icon=*.png)`，.NET `Icon` 只收 ICO | `icon=` 传 `.ico` |
| Nuitka 打包后 daemon 起不来，`Unable to configure formatter 'default'` | uvicorn dictConfig 解析 `uvicorn.logging.DefaultFormatter` 失败 | `uvicorn.Config(..., log_config=None)` |
| 关窗后内存不降、WebView2 进程常驻 | 用 `hide()` 代替销毁 | 放行 `closing`，销毁窗口 + `gc.collect()` + `EmptyWorkingSet` |
| 关窗后工作集仍占着 | 只做 GC，没有把页归还系统 | `psapi.EmptyWorkingSet`（Step 5） |
| 开窗峰值内存高 | WebView2 默认多进程 + GPU | `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS`（Step 11，注意副作用） |
| 控制台 Ctrl+C 没反应 | pywebview 主线程被 WinForms 占用，SIGINT 不派发 | `SetConsoleCtrlHandler` 独立线程回调（Step 5） |
| 主题/偏好每次重开都重置 | `private_mode` 默认 True | `private_mode=False` + `storage_path=<dataDir>/webview` |
| 标题栏与页面主题不一致 | 未接 DWM immersive dark mode | `DwmSetWindowAttribute` + `js_api`（Step 3，可选） |
| 托盘「显示」无反应 | 窗口销毁后主循环已退出 | 主线程循环 + `show_requested` + 二次 `start()` |
| 每次打开都是默认尺寸 | 未做几何持久化 | Step 6 |
| `window.json` 出现 `-25600` | 最小化坐标被写回 | 保存前 `MonitorFromPoint` 过滤 |
| 动态端口下两个 daemon 并存 | 只靠端口占用判互斥 | OS 文件锁（Step 7） |
| 打包后 buildID 为空 hash | 源码指纹扫不到 `.py` | 无源码时返回 `frozen` |
| `--json` 输出为空 / prompt 被顶掉 | 合成单 exe 的 GUI 子系统 | 拆 GUI / CLI 两个产物 |

---

## 七、测试建议

| 对象 | 用例 |
|---|---|
| `channel` | 通道覆盖、目录分离、迁移只复制一次、端口默认值 |
| `logx` | 往返、轮转、stderr 故障不阻断、重复 init 不嵌套 |
| `window_state` | 往返、脏 JSON、过小尺寸、无坐标、离屏坐标回落 |
| 壳（实机） | 关窗子进程归零、托盘重建、几何恢复、Ctrl+C 退出 |

纯函数优先：`channel` / `window_state` 不碰 GUI，可直接单测；壳只做一次实机冒烟。

---

## 八、验收清单

| 验证项 | 操作 | 预期 |
|---|---|---|
| 双产物 | `bin/` 下两个 exe | GUI 无控制台、CLI 有控制台 |
| GUI 忽略参数 | `.\bin\<app>-gui-dev.exe list --json` | 只出窗口，零 CLI 输出 |
| CLI 管道 | `... --json \| ConvertFrom-Json` | 正常 JSON，非空 |
| 托盘常驻 | 关窗 | 进程存活、WebView2 子进程归零 |
| 托盘重建 | 托盘「显示窗口」 | 按上次尺寸/位置重建 |
| 几何记忆 | 移窗缩放 → 关窗 → 重开 | 恢复上次几何 |
| 最大化 | 最大化 → 关窗 → 重开 → 还原 | 仍最大化；还原尺寸未坏 |
| 通道隔离 | dev/prod 各跑一次 | 数据落各自目录、端口不冲突 |
| 单实例 | 并发启动两次 | 第二次被拒 |
| 日志 | release `--hidden` 跑 5s | 日志有横幅，无逐请求噪音 |
| CLI serve WebUI | `serve` 后打开打印地址 | 完整页面 + `/api/*` 正常 |
| 图标双通道 | 提取 dev/release exe 图标 | dev 语言图标，release 专属 |
| 主题持久 | 切主题 → 重开 | 仍保持 |
| 标题栏 | 暗色主题 | 标题栏同步变暗（若启用） |
| Ctrl+C | 控制台按 Ctrl+C | 优雅退出、无残留进程 |

---

## 九、回滚

```powershell
Remove-Item .\bin\<app>-gui-dev.exe, .\bin\<app>-cli-dev.exe -ErrorAction SilentlyContinue
git tag -d <app>/vX.Y.Z     # 误打 tag；远端已 push 需单独处理
```

数据回滚：删除 `%APPDATA%\language_projects\<app>\{dev,prod}` 不影响旧库（迁移只复制不删除）。
