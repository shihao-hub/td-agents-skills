# 架构参考：双通道产物与桌面壳实现

> 归属：`sh-go-wails-desktop`。本文是深度材料，日常执行以 `README.md` 的 SOP 为准。
> 验证环境：Windows 11 24H2、Go 1.26、Wails v3.0.0-beta.33、Edge WebView2。

---

## 一、双通道蓝图

同一份源码，用 build tag 编译出**两个子系统不同的二进制**（详见 `README.md` Step 2 / Step 3）：

```text
                 ┌─────────────────────── 同一份 internal/ 源码 ───────────────────────┐
                 │                                                                     │
   -H windowsgui │                                                     -tags cli       │
                 ▼                                                                     ▼
  ┌────────────────────────────┐                                   ┌────────────────────────────┐
  │ <app>-gui.exe              │                                   │ <app>-cli.exe              │
  │ PE Subsystem = 2 (GUI)     │                                   │ PE Subsystem = 3 (Console) │
  │ main.go (//go:build !cli)  │                                   │ cli.go (//go:build cli)    │
  └─────────────┬──────────────┘                                   └─────────────┬──────────────┘
                │                                                                 │
                ▼                                                                 ▼
  ┌────────────────────────────┐                                   ┌────────────────────────────┐
  │ 不解析子命令                │                                   │ 子命令派发                 │
  │ 双击/任意参数 → 出窗口       │                                   │ ingest/list/get/...       │
  │ --hidden → 静默托盘        │                                   │ serve → WebUI + REST      │
  └─────────────┬──────────────┘                                   │ --hidden → 无窗服务        │
                │                                                  └─────────────┬──────────────┘
                ▼                                                                │
  ┌────────────────────────────┐                                   ┌────────────────────────────┐
  │ 嵌入 HTTP / WebUI           │                                   │ 打印 WebUI URL + 阻塞      │
  │ (net.Listen + embed)        │                                   │ (同一 Handler，无窗口)     │
  └─────────────┬──────────────┘                                   └────────────────────────────┘
                ▼
  ┌────────────────────────────┐
  │ Wails v3 消息循环            │
  │ 系统托盘 + 菜单守护          │
  └─────────────┬──────────────┘
       ┌─────────┴───────────────────────────┐
       ▼ 点击“打开工作台”/双击托盘            ▼ 点击“X”关闭窗口
┌──────────────────────┐             ┌──────────────────────┐
│ 按需创建/展示主窗口   │             │ 彻底销毁 WebviewWindow│
│ (WebView2 渲染 DOM)  │             │ 6 个 Chromium 进程退出│
│ 内存占用: ~350MB     │             │ GC 释放, 常驻降至~25MB│
└──────────────────────┘             └──────────────────────┘
```

两端共享 `internal/api`（HTTP 层，GUI 与 CLI `serve` 调用同一个 `Handler()`，静态 WebUI + REST）、`internal/storage`（持久层）、`internal/web`（embed 前端资产）与 `internal/app`（托盘、自启、数据目录、日志），因此两条通道看到的是同一个数据库与同一套 REST。**CLI `serve` 必须打开与 GUI 相同的 WebUI 根路径，不得退化成裸 API 端口。**

> **例外（旧项目）**：Wails-only 项目（前端依赖 bindings/Events、没有 HTTP 层）不强制改造成上述形态；保持现状时必须在 README 声明「无浏览器入口」。只有明确需要 CLI + 浏览器/远程入口时，才单独立项做 HTTP 化 + SSE + 单写者锁。新项目不适用此例外。

---

## 二、目录结构

```text
your_app/
├── cmd/
│   └── your_app/
│       ├── main.go                     # GUI 入口 (//go:build !cli)：不解析子命令，只拉桌面壳
│       ├── cli.go                      # CLI 入口 (//go:build cli)：子命令派发与全部 handler
│       └── rsrc_windows_amd64.syso     # 编译生成的 PE 资源段 (必须与入口文件同目录!)
├── internal/
│   ├── api/                            # HTTP 层：静态 WebUI + REST，GUI 与 CLI serve 共用 Handler()
│   ├── app/
│   │   ├── gui.go                      # Wails v3 托盘与窗口生命周期
│   │   ├── autostart.go                # 开机自启封装与 Dev 防呆
│   │   ├── version.go                  # 编译期版本与 Release 状态 (IsRelease 只认 BuildMode)
│   │   ├── datadir.go                  # dev/prod 数据目录解析 + 旧库一次性迁移
│   │   ├── icon_release.go             # //go:build !dev  embed icon.ico
│   │   ├── icon_dev.go                 # //go:build dev   embed icon_dev.ico (地鼠)
│   │   ├── icon.ico                    # release 运行时图标 (render_icon.py 生成)
│   │   ├── icon_dev.ico                # dev 运行时图标 (静态入库，约 43KB)
│   │   └── log.go                      # 滚动双写落盘日志
│   ├── storage/                        # 本地 SQLite 数据层
│   └── web/                            # 嵌入式 WebUI 前端资产 (HTML/JS/CSS)
├── scripts/
│   ├── render_icon.py                  # 专属图标渲染流水线 (Pillow，仅 release 图标)
│   └── build.py                        # 一键构建：通道判定 + 图标 + go-winres 资源段 + 双通道 go build（GUI/Console 各一）
├── winres/
│   ├── gui.json                        # VERSIONINFO + manifest + 图标模板（GUI 产物）
│   └── cli.json                        # 同上，FileDescription/InternalName 换成 CLI 文案
├── icon.png                            # 1024x1024 原图
├── icon.ico                            # 多尺寸 Windows 图标
├── info.json                           # 无 tag 时的版本基线（PE 资源由 winres 模板生成，不读此文件）
└── wails.exe.manifest                  # 4段式 WinSxS 清单文件（由 winres 模板以 RT_MANIFEST 引用）
```

---

## 三、PE 清单与版本元数据

### `wails.exe.manifest`（版本号必须 4 段式）

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly manifestVersion="1.0" xmlns="urn:schemas-microsoft-com:asm.v1" xmlns:asmv3="urn:schemas-microsoft-com:asm.v3">
    <assemblyIdentity type="win32" name="your_team.your_app" version="1.0.0.0" processorArchitecture="*"/>
    <dependency>
        <dependentAssembly>
            <assemblyIdentity type="win32" name="Microsoft.Windows.Common-Controls" version="6.0.0.0" processorArchitecture="*" publicKeyToken="6595b64144ccf1df" language="*"/>
        </dependentAssembly>
    </dependency>
    <asmv3:application>
        <asmv3:windowsSettings>
            <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true/pm</dpiAware>
            <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">permonitorv2,permonitor</dpiAwareness>
        </asmv3:windowsSettings>
    </asmv3:application>
    <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
        <security>
            <requestedPrivileges>
                <requestedExecutionLevel level="asInvoker" uiAccess="false"/>
            </requestedPrivileges>
        </security>
    </trustInfo>
</assembly>
```

### `info.json`（仅作版本基线，不再写入 PE）

**注意：`rsrc` 不读 `info.json`**，所以它现在只承担一件事——无 git tag 时的版本基线回退值（`fixed.file_version`）。真正的 PE VERSIONINFO 由 `winres/{gui,cli}.json` 模板 + `go-winres` 生成（见 `build-pipeline.md` §1.1）；两者版本号必须同步递增，别只改一处。

```json
{
  "fixed": {
    "file_version": "1.0.0",
    "product_version": "1.0.0"
  },
  "info": {
    "0409": {
      "comments": "YourApp CLI and Desktop Application",
      "company_name": "YourTeam",
      "file_description": "YourApp - All-in-One CLI & Desktop",
      "file_version": "1.0.0",
      "internal_name": "your_app",
      "legal_copyright": "Copyright 2026 YourTeam",
      "original_filename": "your_app.exe",
      "product_name": "YourApp",
      "product_version": "1.0.0"
    }
  }
}
```

---

## 四、`gui.go` 完整核心实现

> 覆盖：单实例、托盘、窗口关闭销毁 + 双击重建、HWND 就绪后的任务栏图标绑定、自启菜单门禁。
> 若使用本模板，请把 `your_app` / `your_team` 替换为真实值，并把 `http.Serve` 换成真实 mux。

```go
package app

import (
	"fmt"
	"net"
	"net/http"
	"os/exec"
	"runtime"
	"runtime/debug"
	"sync"
	"sync/atomic"
	"time"

	"github.com/wailsapp/wails/v3/pkg/application"
	"github.com/wailsapp/wails/v3/pkg/events"
	"github.com/wailsapp/wails/v3/pkg/w32"
)

type App struct {
	app       *application.App
	serverURL string
	winMu     sync.Mutex
	win       *application.WebviewWindow
	ensureMu  sync.Mutex
	tray      *application.SystemTray
	exiting   atomic.Bool
}

// LaunchGUI 启动 WebUI + Wails 桌面壳。port 传 0 由内核动态探测可用端口
// （默认行为：dev / release 乃至同机多实例各占不同端口，无需端口约定）。
func LaunchGUI(dbPath string, port int, hidden bool) error {
	// 先绑定再建窗口：窗口 URL 需要真实端口，不能先构造地址后监听。
	listener, err := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", port))
	if err != nil {
		return fmt.Errorf("启动 HTTP 监听失败: %w", err)
	}
	serverURL := "http://" + listener.Addr().String()
	logf("WebUI 已启动: %s", serverURL) // 落日志（实现见 troubleshooting §3）
	go http.Serve(listener, api.NewServer(store).Handler()) // 与 CLI serve 共用同一 handler

	var appInstance *App

	// 单实例 ID 按通道隔离：dev 追加 .dev，避免与常驻正式版互斥
	singleInstanceID := "your_team.your_app.gui"
	if !IsRelease() {
		singleInstanceID += ".dev"
	}

	wailsApp := application.New(application.Options{
		Name: "your_app",
		Icon: iconICO, // 注册内存图标（dev/release 由 build tag 选择）
		Windows: application.WindowsOptions{
			DisableQuitOnLastWindowClosed: true, // 窗口关闭保持托盘常驻
			WebviewUserDataPath:           webviewDataPath(),
			AdditionalBrowserArgs: []string{
				"--disable-gpu",
				"--disable-gpu-compositing",
				"--disable-software-rasterizer",
				"--renderer-process-limit=1",
				"--disable-features=NetworkServiceOutOfProcess",
			},
		},
		SingleInstance: &application.SingleInstanceOptions{
			UniqueID: singleInstanceID,
			ExitCode: 0,
			OnSecondInstanceLaunch: func(data application.SecondInstanceData) {
				if appInstance != nil {
					appInstance.ensureMainWindow()
				}
			},
		},
	})

	appInstance = &App{
		app:       wailsApp,
		serverURL: serverURL,
	}

	appInstance.buildTray()
	if !hidden {
		appInstance.ensureMainWindow()
	}

	return wailsApp.Run()
}

func (a *App) buildWindowLocked(hidden bool) {
	win := a.app.Window.NewWithOptions(application.WebviewWindowOptions{
		Title:            "YourApp - 工作台",
		Width:            1280,
		Height:           850,
		Hidden:           hidden,
		URL:              a.serverURL,
		BackgroundColour: application.NewRGB(22, 22, 28),
	})
	a.win = win

	// 注册窗口就绪与激活钩子，HWND 创建后即刻绑定 Win32 大小图标与类图标
	win.RegisterHook(events.Windows.WindowShow, func(*application.WindowEvent) {
		a.applyWindowIcon(win)
	})
	win.RegisterHook(events.Windows.WindowActive, func(*application.WindowEvent) {
		a.applyWindowIcon(win)
	})

	// 关闭销毁：放行关闭事件，释放底层 WebView2 渲染进程与物理内存
	win.RegisterHook(events.Common.WindowClosing, func(*application.WindowEvent) {
		if a.exiting.Load() {
			return
		}
		a.winMu.Lock()
		if a.win == win {
			a.win = nil
		}
		a.winMu.Unlock()

		go func() {
			time.Sleep(250 * time.Millisecond)
			runtime.GC()
			debug.FreeOSMemory()
		}()
	})
}

func (a *App) applyWindowIcon(win *application.WebviewWindow) {
	if win == nil || len(iconICO) == 0 {
		return
	}
	hwnd := w32.HWND(win.NativeWindow())
	if hwnd == 0 {
		return
	}
	if hBig, err := w32.CreateLargeHIconFromImage(iconICO); err == nil && hBig != 0 {
		w32.SendMessage(hwnd, w32.WM_SETICON, w32.ICON_BIG, uintptr(hBig))
		w32.SetApplicationIcon(uintptr(hwnd), hBig)
	}
	if hSmall, err := w32.CreateSmallHIconFromImage(iconICO); err == nil && hSmall != 0 {
		w32.SetWindowIcon(hwnd, hSmall)
	}
}

func (a *App) ensureMainWindow() {
	go a.showMainWindow()
}

func (a *App) showMainWindow() {
	a.ensureMu.Lock()
	defer a.ensureMu.Unlock()

	if a.exiting.Load() {
		return
	}

	// 存活检查
	a.winMu.Lock()
	win := a.win
	if win != nil {
		if _, exists := a.app.Window.GetByID(win.ID()); !exists {
			a.win = nil
			win = nil
		}
	}
	a.winMu.Unlock()

	if win != nil {
		if win.IsMinimised() {
			win.UnMinimise()
		}
		win.Show()
		win.Focus()
		a.applyWindowIcon(win)
		return
	}

	// 窗口已被销毁，按需瞬时重建
	a.winMu.Lock()
	a.buildWindowLocked(false)
	win = a.win
	a.winMu.Unlock()

	if win != nil {
		win.Show()
		win.Focus()
		a.applyWindowIcon(win)
	}
}

func (a *App) buildTray() {
	a.tray = a.app.SystemTray.New()
	if len(iconICO) > 0 {
		a.tray.SetIcon(iconICO)
	}
	a.tray.SetTooltip("YourApp - 桌面外壳")
	a.tray.OnClick(a.ensureMainWindow)
	a.tray.OnDoubleClick(a.ensureMainWindow)

	menu := a.app.NewMenu()
	menu.Add("打开工作台").OnClick(func(*application.Context) {
		a.ensureMainWindow()
	})
	menu.Add("在默认浏览器中打开").OnClick(func(*application.Context) {
		_ = openURL(a.serverURL)
	})
	menu.AddSeparator()

	// 开机自启动项：Dev 模式置灰禁用，Release 模式正常可选
	if IsRelease() {
		autostartItem := menu.AddCheckbox("开机自启", a.autostartEnabled())
		autostartItem.OnClick(func(*application.Context) {
			enabled := a.autostartEnabled()
			if err := a.setAutostart(!enabled); err != nil {
				logf("设置开机自启失败: %v", err)
			} else {
				autostartItem.SetChecked(!enabled)
			}
		})
	} else {
		disabledItem := menu.AddCheckbox("开机自启 (开发版已禁用)", false)
		disabledItem.SetEnabled(false)
	}

	menu.AddSeparator()
	menu.Add("彻底退出").OnClick(func(*application.Context) {
		go a.quit()
	})

	a.tray.SetMenu(menu)
}

func (a *App) quit() {
	a.exiting.Store(true)
	a.winMu.Lock()
	win := a.win
	a.win = nil
	a.winMu.Unlock()

	if win != nil {
		win.Close()
	}
	a.app.Quit()
}
```

---

## 四·补 窗口几何记忆（`window_state.go` + 接入点）

wails v3 beta.33 未提供窗口状态持久化，需要在 `gui.go` 的建窗路径自己接入。

### 快照与读写（`internal/app/window_state.go` 核心）

```go
const (
	windowStateFileName = "window.json"
	defaultWindowWidth  = 1280
	defaultWindowHeight = 850
	minWindowWidth      = 900   // 读到比这更小的值视为脏数据
	minWindowHeight     = 600
	windowStateSaveDelay = 700  // ms，几何事件防抖窗口
)

type windowState struct {
	Width     int  `json:"width"`
	Height    int  `json:"height"`
	X         int  `json:"x"`
	Y         int  `json:"y"`
	HasPos    bool `json:"hasPosition"`
	Maximised bool `json:"maximised"`
}

func windowStatePath() string { /* appDataDir() + windowStateFileName，目录空则返回 "" */ }
func loadWindowState() windowState {
	/* 无文件 / 解析失败 / 尺寸过小 → defaultWindowState()；HasPos 仅在文件里为真时置位 */
}
func writeWindowState(state windowState) error {
	/* MkdirAll(dir) + json.MarshalIndent + os.WriteFile(…, 0o644) → 无 BOM UTF-8 */
}
```

### `App` 新增字段与建窗接入

```go
type App struct {
	// …原有字段
	stateMu    sync.Mutex
	stateTimer *time.Timer
	winState   windowState // 启动时 loadWindowState()，之后随操作回写
}

func (a *App) buildWindowLocked(hidden bool) {
	state := a.currentWindowState()
	opts := application.WebviewWindowOptions{
		Title:    windowTitle,
		Width:    state.Width,
		Height:   state.Height,
		MinWidth: minWindowWidth,
		MinHeight: minWindowHeight,
		Hidden:   hidden,
		URL:      a.serverURL,
	}
	if state.HasPos {
		opts.InitialPosition = application.WindowXY
		opts.X, opts.Y = state.X, state.Y
	}
	win := a.app.Window.NewWithOptions(opts)

	// 图标 + 屏幕可见性兜底
	win.RegisterHook(events.Windows.WindowShow, func(*application.WindowEvent) {
		a.applyWindowIcon(win)
		a.ensureWindowOnScreen(win)
	})
	// 几何变更防抖落盘
	for _, evt := range []events.WindowEventType{
		events.Common.WindowDidResize, events.Common.WindowDidMove,
		events.Common.WindowMaximise, events.Common.WindowUnMaximise,
	} {
		win.OnWindowEvent(evt, func(*application.WindowEvent) { a.scheduleSaveWindowState(win) })
	}
	// 关闭前同步落盘（窗口销毁后 Size() 归零）
	win.RegisterHook(events.Common.WindowClosing, func(*application.WindowEvent) {
		a.stopWindowStateTimer()
		a.saveWindowState(win)
		// …原有放行逻辑
	})
}
```

### 保存判定（关键分支）

```go
func (a *App) saveWindowState(win *application.WebviewWindow) {
	state := a.currentWindowState()
	switch {
	case win.IsMinimised(), win.IsFullscreen():
		return // 最小化坐标是 -32000 之类，不能入库
	case win.IsMaximised():
		state.Maximised = true // 只翻标记，保留上一次的还原几何
	default:
		w, h := win.Size()
		if w < minWindowWidth || h < minWindowHeight {
			return
		}
		x, y := win.Position()
		state.Width, state.Height = w, h
		state.X, state.Y, state.HasPos = x, y, true
		state.Maximised = false
	}
	// 与 a.winState 比较，有变化才写文件
}
```

### 屏幕外兜底

```go
func (a *App) ensureWindowOnScreen(win *application.WebviewWindow) {
	screens := a.app.Screen.GetAll()
	if len(screens) == 0 {
		return // Run() 之前屏幕缓存可能还是空的，别据此判"不可见"
	}
	x, y := win.Position()
	w, h := win.Size()
	cx, cy := x+w/2, y+h/2
	for _, s := range screens {
		area := s.WorkArea // 已是 DIP
		if cx >= area.X && cx < area.X+area.Width && cy >= area.Y && cy < area.Y+area.Height {
			return
		}
	}
	win.Center() // 拔掉外接屏后旧坐标会让窗口彻底不可见
	a.scheduleSaveWindowState(win)
}
```

---

## 四·补二 单实例互斥探测（让外部工具判断 GUI 是否在跑）

Wails v3 的 Windows 单实例实现（`single_instance_windows.go`）建锁命名是固定的：

```go
id         := "wails-app-" + uniqueID
mutexName  := id + "-sim"   // CreateMutex 创建，进程存活期间一直存在
className  := id + "-sic"   // 隐藏的 event target 窗口
windowName := id + "-siw"
```

因此外部 CLI 可以用 `OpenMutex` 探测某个通道的 GUI 是否在运行，比按进程名匹配可靠（exe 改名、僵死进程都不影响）：

```go
//go:build windows
package app

func guiSingleInstanceID(release bool) string {
	id := "shihao.langproj.<app>.gui"
	if !release {
		id += ".dev"
	}
	return id
}

func GUIRunning(release bool) bool {
	name := "wails-app-" + guiSingleInstanceID(release) + "-sim"
	handle, err := windows.OpenMutex(windows.SYNCHRONIZE, false, windows.StringToUTF16Ptr(name))
	if err != nil {
		return false
	}
	_ = windows.CloseHandle(handle)
	return true
}
```

- **单一真源**：`LaunchGUI` 建锁与外部探测必须共用同一个 `guiSingleInstanceID()`，否则改名后探测静默失效（GUI 在跑却报未运行）；
- **非 Windows 留桩**：另一份 `//go:build !windows` 实现返回 `false`，保持调用方逻辑统一；
- **典型用途**：dev/prod 双通道桌面应用里，CLI 写入前先探测「用户窗口在看哪个通道的库」，避免归档进用户看不见的那一个。

---

## 五、窗口生命周期与图标绑定时序

- **创建时机**：`Window.NewWithOptions` 返回时底层 `HWND` 尚未创建（`NativeWindow() == 0`），此刻调用 Win32 设图标会静默失效。
- **正确时机**：在 `WindowShow` / `WindowActive` 钩子里调用 `applyWindowIcon`，并在 `win.Show()` 之后主动补调一次。
- **大小图标语义**：`WM_SETICON + ICON_BIG` 影响任务栏与 Alt+Tab；`ICON_SMALL` 影响标题栏；`SetApplicationIcon` 把大图标固化到窗口类（`GCLP_HICON`）。
- **关闭行为**：放行 `WindowClosing`（不 `Cancel`）使 Wails 销毁窗口，Chromium 子进程随之退出；250ms 后 GC 把常驻内存从 ~350MB 拉回 25~40MB。
- **重建行为**：`showMainWindow` 用 `ensureMu` 防连击，`win == nil` 时重新 `buildWindowLocked(false)` 并立即补刷图标。
- **几何记忆时序**：`NewWithOptions`（带记忆尺寸/坐标）→ `Show` → 若 `Maximised` 则 `Maximise()` → `Focus`；`WindowShow` 钩子里做屏幕可见性兜底。**切勿**在 `Show()` 前 `Maximise()`：隐藏窗口的 `ShowWindow(SW_MAXIMIZE)` 行为不稳定。
- **关闭时序**：`WindowClosing` 先同步保存几何（此后 `Size()`/`Position()` 归零），再放行销毁；`stateTimer` 必须 `Stop()`，否则定时器会在窗口销毁后回写 0 尺寸。

---

## 六、运行数据与日志路径

- `appDataDir()`：`%APPDATA%\language_projects\<app>\{dev,prod}`，回退 `~/.language_projects/<app>/<通道>`。
- `webviewDataPath()`：`<appDataDir>/webview2`，避免 WebView2 缓存散落到可执行文件目录。
- 日志：`<appDataDir>/<app>.log`，`logf()` 同时写 `os.Stderr` 与追加文件；GUI 产物（`-H windowsgui`）无控制台，日志文件是唯一事后取证入口。
- 旧库迁移：新库不存在且旧库存在时复制主库与 `-wal`/`-shm`，旧文件保留。
- **并发**：同一通道库被 GUI 与多个 CLI 共用，DSN 必须带 `busy_timeout(5000)` + `journal_mode(WAL)`；GUI 退出前 `store.Close()` 触发 checkpoint（详见 README Step 7）。
- **写的唯一入口是 CLI**：GUI 的 HTTP 层保持只读，这是「WAL 足够、无需跨进程写锁」的前提。
