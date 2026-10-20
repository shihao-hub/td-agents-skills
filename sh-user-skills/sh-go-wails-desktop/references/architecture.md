# 架构参考：四位一体单二进制与桌面壳实现

> 归属：`sh-go-wails-desktop`。本文是深度材料，日常执行以 `README.md` 的 SOP 为准。
> 验证环境：Windows 11 24H2、Go 1.26、Wails v3.0.0-beta.33、Edge WebView2。

---

## 一、四位一体蓝图

```text
                     ┌───────────────────────────────────────────────┐
                     │          单一可执行文件 (Single Binary)        │
                     │                 your_app.exe                  │
                     └───────────────────────┬───────────────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼ 启动参数判断 (os.Args)                    ▼
            ┌──────────────────────┐                     ┌──────────────────────┐
            │ 带有业务子命令 / 传参  │                     │   无参数 (双击) 或   │
            │ 如: ingest / list    │                     │   --hidden (开机自启)│
            └──────────┬───────────┘                     └──────────┬───────────┘
                       │                                            │
                       ▼                                            ▼
            ┌──────────────────────┐                     ┌──────────────────────┐
            │    CLI 子命令解析    │                     │  嵌入 HTTP / WebUI   │
            │ (AttachConsole 附着) │                     │ (net.Listen + embed) │
            │ 执行完毕秒级退出     │                     └──────────┬───────────┘
            └──────────────────────┘                                │
                                                                    ▼
                                                         ┌──────────────────────┐
                                                         │   Wails v3 消息循环  │
                                                         │  系统托盘 + 菜单守护 │
                                                         └──────────┬───────────┘
                                        ┌───────────────────────────┴───────────────────────────┐
                                        ▼ 点击 "打开工作台" / 双击托盘                           ▼ 点击 "X" 关闭窗口
                             ┌──────────────────────┐                                ┌──────────────────────┐
                             │ 按需创建/展示主窗口   │                                │ 彻底销毁 WebviewWindow│
                             │ (WebView2 渲染 DOM)  │                                │ 6个 Chromium 进程退出│
                             │ 内存占用: ~350MB     │                                │ GC释放, 常驻降至~25MB│
                             └──────────────────────┘                                └──────────────────────┘
```

---

## 二、目录结构

```text
your_app/
├── cmd/
│   └── your_app/
│       ├── main.go                     # CLI 分流与启动入口
│       ├── console_windows.go          # AttachConsole 标准流绑定 (必须在 main 包的 init 中)
│       └── rsrc_windows_amd64.syso     # 编译生成的 PE 资源段 (必须与 main.go 同目录!)
├── internal/
│   ├── api/                            # HTTP REST API 服务
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
│   └── build.py                        # 一键构建：通道判定 + 图标选择 + rsrc + go build
├── icon.png                            # 1024x1024 原图
├── icon.ico                            # 多尺寸 Windows 图标
├── info.json                           # PE 版本与版权元数据
└── wails.exe.manifest                  # 4段式 WinSxS 清单文件
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

### `info.json`

`fixed.file_version` 同时是 dev 版本基线（无 tag 时的回退值）。

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

func LaunchGUI(dbPath string, defaultPort int, hidden bool) error {
	// 启动内置 HTTP 服务
	listener, _ := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", defaultPort))
	port := listener.Addr().(*net.TCPAddr).Port
	serverURL := fmt.Sprintf("http://127.0.0.1:%d", port)
	go http.Serve(listener, nil) // 挂载你的 mux

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

## 五、窗口生命周期与图标绑定时序

- **创建时机**：`Window.NewWithOptions` 返回时底层 `HWND` 尚未创建（`NativeWindow() == 0`），此刻调用 Win32 设图标会静默失效。
- **正确时机**：在 `WindowShow` / `WindowActive` 钩子里调用 `applyWindowIcon`，并在 `win.Show()` 之后主动补调一次。
- **大小图标语义**：`WM_SETICON + ICON_BIG` 影响任务栏与 Alt+Tab；`ICON_SMALL` 影响标题栏；`SetApplicationIcon` 把大图标固化到窗口类（`GCLP_HICON`）。
- **关闭行为**：放行 `WindowClosing`（不 `Cancel`）使 Wails 销毁窗口，Chromium 子进程随之退出；250ms 后 GC 把常驻内存从 ~350MB 拉回 25~40MB。
- **重建行为**：`showMainWindow` 用 `ensureMu` 防连击，`win == nil` 时重新 `buildWindowLocked(false)` 并立即补刷图标。

---

## 六、运行数据与日志路径

- `appDataDir()`：`%APPDATA%\language_projects\<app>\{dev,prod}`，回退 `~/.language_projects/<app>/<通道>`。
- `webviewDataPath()`：`<appDataDir>/webview2`，避免 WebView2 缓存散落到可执行文件目录。
- 日志：`<appDataDir>/<app>.log`，`logf()` 同时写 `os.Stderr` 与追加文件，供 `-H windowsgui` 无控制台场景排障。
- 旧库迁移：新库不存在且旧库存在时复制主库与 `-wal`/`-shm`，旧文件保留。
