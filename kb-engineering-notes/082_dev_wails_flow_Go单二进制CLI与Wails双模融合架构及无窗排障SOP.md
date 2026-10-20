---
name: kb-go-cli-wails-dual-mode
description: |
  Go 单二进制 CLI + HTTP API + WebUI + Wails v3 托盘桌面全栈融合架构、Windows PE 资源段图标与任务栏绑定、dev/release 构建通道隔离（产物命名/版本号/数据目录/单实例/图标双通道）、开机自启门禁、关闭销毁双击重建内存优化及 -H windowsgui 零黑框排障 SOP。
version: 1.3.0
created: 2026-10-20
updated: 2026-10-21
id: "082"
domain: dev
scope: wails
type: flow
slug: "Go单二进制CLI与Wails双模融合架构及无窗排障SOP"
status: verified
last_verified: "2026-10-21"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: true
---

# dev_flow_082_Go单二进制CLI与Wails双模融合架构及无窗排障SOP

> **条目定位**：Type B 方案与流水线型条目（兼含 Windows PE 图标与 WinSxS 疑难排障）
> **结论版本锚点**：**实机验证通过于 Windows 11 24H2、Go 1.23+、Wails v3 (v3.0.0-beta.33+)、Edge WebView2 运行时**（2026-10-21）。
> **关联条目**：Wails 托盘常驻与内存释放见 `071_dev_wails_fix_WailsV3WebView2高内存治理与关窗生命周期重构.md`；Windows 开机自启治理见 `winstartupmanager` 与 `glmquotawatch-gui`；PE 资源注入见 `rsrc` 与 `075`。

---

## 一、 架构目标与全栈蓝图

现代工具与业务软件常面临严重开发与分发割裂：
1. **工具链与分发割裂**：后台由 Go 构建为高效 CLI，但可视化需求又逼迫用户打开浏览器，或额外打包数百 MB 的 Electron 外壳，导致无法在 CI/CD 或终端直接作为单文件独立调用。
2. **黑框与静默矛盾**：Subsystem Console 程序双击运行会弹出丑陋的黑色 CMD 窗口；强制加 `-H windowsgui` 静态消除黑框后，在 PowerShell/CMD 中执行 CLI 子命令时标准输出（Stdout/Stderr）又会被操作系统静默丢弃。
3. **资源泄漏与常驻开销**：带 WebView2 的桌面外壳若只是简单隐藏窗口，Chromium 的 6 个底层渲染与工具进程持续占用 300MB+ 内存；关窗时若彻底退出又失去托盘守护能力。
4. **任务栏图标丢失（白框蓝方块）**：托盘可以动态用内存图片设置图标，但 Windows 任务栏和文件资源管理器只认 `.exe` PE 静态资源段与窗口消息，Go 开发者常因 `.syso` 放置目录错误或误设 `AppUserModelID` 导致任务栏图标退化为系统默认图标。
5. **开机自启污染开发环境**：开发期间（`go run` 或临时构建产物）若随意注册开机自启动，会向系统注册表写入临时的 `go-build*` 路径，重启后沦为死链，并污染日常生产环境。
6. **dev 与 release 通道混淆**：两者产物同名（dev 直接覆盖正式版）、版本号看不出通道、共用同一份 SQLite 与单实例互斥锁、exe 图标完全一致——用户与 Agent 都无从判断手里的是不是正式版，出问题也难定位是哪个通道写入的数据。

### 全栈融合架构蓝图（四位一体）
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

## 二、 核心机制与避坑铁律

### 1. 任务栏图标与 Windows PE `.syso` 链接机制（致命避坑）
- **现象**：托盘有自定义图标，但任务栏和 `.exe` 属性里显示为系统默认的“白窗蓝方块”。
- **底层原因与三大铁律**：
  1. **`.syso` 放置目录铁律**：
     - 托盘图标是运行时通过 Go 代码 `a.tray.SetIcon(iconBytes)` 从内存加载并传给 Win32 Shell API 的；
     - 任务栏和 Windows Explorer 读取的是 **PE 可执行文件头部的静态资源区（`RT_GROUP_ICON` / `RT_ICON`）**。
     - Go 编译器规定：**`.syso` 文件必须放在与 `package main` 相同的目录下（即 `cmd/your_app/rsrc_windows_amd64.syso`）！**
     - **致命错误**：将 `rsrc_windows_amd64.syso` 放到项目根目录，而 `main.go` 位于 `cmd/your_app/`。执行 `go build ./cmd/your_app` 时，Go 编译器完全不会查找根目录的 `.syso`，导致产物中 PE 资源为空！
  2. **Manifest 版本 4 段式铁律**：
     - Windows PE 清单文件 `wails.exe.manifest` 中，`<assemblyIdentity version="1.0.0.0" .../>` 的 `version` 属性**必须为严格的 4 段式（major.minor.build.revision）**。
     - 若写成 3 段式（如 `0.1.0`），Windows 会直接报 `Side-by-side configuration is incorrect` 进程无法启动崩溃。
  3. **AppUserModelID 陷阱（绿色单二进制绝不可随意声明）**：
     - 若在 `init()` 中调用 `SetCurrentProcessExplicitAppUserModelID("YourCompany.App")`，Windows Taskbar 会强制解除该进程与 `.exe` 路径的默认关联，转而在开始菜单中通过快捷方式（`.lnk`）查找匹配的 AppID。
     - 免安装绿色工具若没有安装器在开始菜单注册带 AppID 的快捷方式，**Windows Shell 将直接找不到图标，任务栏退化为系统空白文档方块**！
     - 正确做法：绿色单二进制**不要声明未注册的 AppUserModelID**，让 Windows Explorer 自然绑定可执行文件自身 PE 头部的矢量图标。
  4. **Wails v3 窗口生命周期与 HWND 异步绑定时机**：
     - `win := a.app.Window.NewWithOptions(...)` 调用时，底层的 Windows `HWND` 尚未创建（`win.NativeWindow() == 0`）。
     - 若在此处直接调用 Win32 API 设图标，全部静默失效！
     - 正确做法：必须在 `win.RegisterHook(events.Windows.WindowShow, ...)` 与 `win.RegisterHook(events.Windows.WindowActive, ...)` 中挂载 `applyWindowIcon(win)`，并在 `showMainWindow()` 的 `win.Show()` 后主动补调，同时写入：
       - `SendMessage(hwnd, WM_SETICON, ICON_BIG, hBig)`（任务栏与 Alt+Tab）
       - `SendMessage(hwnd, WM_SETICON, ICON_SMALL, hSmall)`（标题栏小图标）
       - `w32.SetApplicationIcon(uintptr(hwnd), hBig)`（向窗口类固化 `GCLP_HICON`）

### 2. 图标自主渲染流水线（拒绝复制借用）
每个独立桌面项目必须拥有专属图标生成脚本（基于 Python Pillow），由脚本自动生成 Windows 所需的全套规范尺寸：
- 导出 `icon.png`（1024×1024 原图）；
- 导出 Windows 多尺寸 `icon.ico`：包含 `256, 128, 64, 48, 32, 24, 16` 完整尺寸链；
- 自动同步至内部 `internal/app/icon.ico` 供 `//go:embed` 使用，并由 `rsrc` 编译为 `.syso`。

### 3. 开机自启治理：Dev 置灰防踩踏与 Release 门禁
- **注册表路径**：`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`（无需管理员权限，无 UAC 弹窗）。
- **Release 识别标准**：仅限经过 Git Tag 标记的构建版本（如 `v1.0.0`，无 dirty 后缀）或构建期显式注入 `BuildMode=release`。
- **托盘菜单表现**：
  - **开发版（Dev）**：`menuItem := menu.AddCheckbox("开机自启 (开发版已禁用)", false)` 并显式调用 `menuItem.SetEnabled(false)`，使其置灰不可点击，且后端防呆拒绝注册；
  - **正式版（Release）**：提供实时可交互的复选框，勾选后注册 `"your_app.exe" --hidden`。
- **`--hidden` 启动支持**：开机自启拉起应用时携带 `--hidden` 参数，进程静默常驻托盘，不自动弹出主窗口。

### 4. 窗口关闭销毁与双击瞬时重建（内存极致优化）
- **关闭（X）**：放行 `events.Common.WindowClosing`（不调用 `event.Cancel()`），让 Wails v3 彻底销毁 `WebviewWindow`。
  - 底层 Chromium (WebView2) 相关的 6 个子进程全部退出；
  - 启动轻量 goroutine 延时 250ms 触发 `runtime.GC()` 与 `debug.FreeOSMemory()`；
  - 进程内存瞬间从 350MB+ 回落到 25MB~40MB 的纯 Go 守护态。
- **双击唤起 / "打开工作台"**：
  - `showMainWindow()` 加互斥锁（`ensureMu`）防连击并发建窗；
  - 若窗口尚存且最小化：`UnMinimise()`, `Show()`, `Focus()`；
  - 若窗口已被销毁（`a.win == nil`）：调用 `buildWindowLocked(false)` 重新构建 `WebviewWindow`，URL 指向本地内嵌 HTTP 服务地址，毫秒级重新加载并补刷窗口大小图标。
- **"在默认浏览器中打开"**：调用系统默认浏览器协议唤起，解决大屏、调试或特定浏览器扩展需求。

### 5. CLI 控制台动态附着（`AttachConsole`）
- 在 `-H windowsgui` 静默构建下，必须在 `cmd/your_app/console_windows.go` 的 `init()` 函数最早时机调用：
  `procAttachConsole.Call(uintptr(^uint32(0)))`（`(DWORD)-1` 表示父进程）。
- 附着成功后，重新将父控制台句柄绑定到 `os.Stdout` 与 `os.Stderr`，确保 CLI 子命令在 PowerShell 和 CMD 中回显正常。

### 6. 构建通道隔离五件套（dev / release 硬隔离）
通道混淆比“没有 release”更危险：dev 产物覆盖正式名、共用同一份数据库、共用单实例锁、图标一模一样，用户与 Agent 都无从判断手里的是哪个版本。五个维度必须同步隔离：

| 维度 | dev | release |
|:---|:---|:---|
| 产物名 | `your_app-dev.exe` | `your_app.exe` |
| 版本号 | `vX.Y.Z-dev[-dirty]` | `vX.Y.Z` |
| 数据目录 | `%APPDATA%\language_projects\<app>\dev` | `...\prod` |
| 单实例 ID | `team.app.gui.dev` | `team.app.gui` |
| exe/窗口图标 | Go 地鼠（一眼可辨） | 项目专属图标 |

铁律：
1. **判定单一入口**：仅当 HEAD 精确命中项目 tag（monorepo 形如 `anatomymanager/v1.0.0`）**且**工作区干净才产 release，其余一律 dev；`--release` 只能做断言（条件不足即 `exit 2`），绝不允许它改写判定结果。
2. **严禁 dev 覆盖正式名**：早期脚本喜欢在 dev 构建后 `shutil.copy2(dev_exe, app_exe)` “方便双击调试”，这会让正式名长期躺着一个 dev 二进制，发布时真假难辨——必须删除此逻辑。
3. **版本号必须自解释**：dev 基线取最近项目 tag，无 tag 回退 `info.json` 的 `fixed.file_version`；工作区脏追加 `-dirty`。版本由 `-ldflags -X ...Version=...` 注入。
4. **IsRelease 单一真源**：`IsRelease()` 只认编译期注入的 `BuildMode`，禁止再用 `strings.HasPrefix(Version, "v")` 猜测——否则 `--version v1.0.0` 会造出 `BuildMode=dev` + `Version=v1.0.0` 的混合体，直接绕过开机自启门禁。
5. **数据目录与单例同步隔离**：`appDataDir()` 按 `IsRelease()` 追加 `dev` / `prod` 子目录；Wails `SingleInstanceOptions.UniqueID` 在 dev 追加 `.dev`，避免调试实例被后台常驻的正式版挤掉。
6. **旧库一次性迁移**：切换数据目录时，若新库不存在且旧库（如 `~/.anatomy/anatomy.db`）存在，复制主库与 `-wal` / `-shm`，**旧文件保留不删**，写日志留痕。
7. **dirty 判定要过滤构建生成物**：`git -c status.relativePaths=false status --porcelain` 输出中剔除 `*.exe`、`icon.ico`、`rsrc_*.syso` 后为空才算干净；`git` 不可用（返回非 0）时保守按脏处理，宁可产 dev。
8. **`.gitignore` 的根路径限定**：`icon.ico` / `icon.png` 必须写成 `/icon.ico`（前导斜杠），否则会连带忽略 `internal/app/icon.ico`——那正是 `//go:embed` 的必需资产，忽略后干净检出直接编译失败。

### 7. 图标双通道：PE 资源与 go:embed 同步切换
exe 文件图标与窗口/托盘图标走的是两条完全不同的通道，dev 通道必须同时改，否则会出现“任务栏是地鼠、文件管理器是专属图标”的割裂：

1. **PE 静态资源（文件管理器/任务栏）**：`rsrc -ico` 参数按通道选择——release 用 `icon.ico`（自动化渲染），dev 用静态入库的 `icon_dev.ico`（Go 地鼠）。
2. **窗口/托盘（内存图标）**：`//go:embed` 在编译期固化，无法用 ldflags 替换，必须用 build tag 拆两个同名变量：
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
   dev 构建命令追加 `-tags dev`；单实例 ID、自启门禁等逻辑照旧只认 `BuildMode`。
3. **地鼠资产入库**：把 `go-default.ico` 复制进 `internal/app/icon_dev.ico`（约 43KB），不要 go:embed 跨仓引用 `docs/assets/...`（embed 不允许项目外路径）。
4. **gofmt 指令注释规则**：`//go:embed` 前的文档注释与指令之间必须有一个空的 `//` 行，否则 `gofmt -l` 会一直报该文件，CI 里容易被当成格式未跑。
5. **验证手段**：PowerShell `[System.Drawing.Icon]::ExtractAssociatedIcon($exe)` 取 32×32 图标存 PNG 算哈希，两个通道哈希必须不同；再用 Pillow 取 `icon_dev.ico` 的 32×32 帧做像素比对，可确认 dev 图标确实是地鼠（本次实测 1024/1024 像素一致）。

---

## 三、 标准代码骨架与流水线实现

### 1. 目录结构推荐
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

### 2. PE 清单与版本元数据

#### `wails.exe.manifest`（版本号必须 4 段式）
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

#### `info.json`
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

### 3. `gui.go` 完整核心实现（双击重建、内存释放、任务栏绑定）
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

	wailsApp := application.New(application.Options{
		Name: "your_app",
		Icon: iconICO, // 注册内存图标
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
			UniqueID: "your_team.your_app.gui",
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

### 4. 专属图标渲染流水线（`scripts/render_icon.py`）
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

### 5. 一键构建流水线（`scripts/build.py`）
```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow>=11.0"]
# ///
import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TAG_PREFIX = "your_app/"          # monorepo 项目 tag 前缀；单仓项目置空，tag 直接写 vX.Y.Z
ICON_RELEASE = PROJECT_ROOT / "icon.ico"
ICON_DEV = PROJECT_ROOT / "internal" / "app" / "icon_dev.ico"
GENERATED_SUFFIXES = (
    "/your_app.exe",
    "/your_app-dev.exe",
    "/icon.ico",
    "/icon.png",
    "/cmd/your_app/rsrc_windows_amd64.syso",
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
    """最近的项 tag，用于推导 dev 版本基线。"""
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

def main() -> int:
    parser = argparse.ArgumentParser(description="构建单二进制工具（dev / release 严格隔离）")
    parser.add_argument("--release", action="store_true", help="声明发布构建；tag 或干净条件不满足即报错")
    parser.add_argument("--version", default="", help="仅覆盖版本基线，不改变通道判定")
    args = parser.parse_args()

    # 1. 先判定通道（图标与产物名都依赖它）；--release 只做断言
    release = exact_project_tag() is not None and not worktree_dirty()
    if args.release and not release:
        print("❌ 拒绝发布构建：需同时满足 精确 tag + 工作区干净", file=sys.stderr)
        return 2

    # 2. 图标：release 重绘专属图标；dev 直接用地鼠静态资产
    render_script = PROJECT_ROOT / "scripts" / "render_icon.py"
    if release and render_script.exists():
        subprocess.run(["uv", "run", str(render_script)], cwd=str(PROJECT_ROOT), check=True)
    icon = ICON_RELEASE if release else ICON_DEV

    # 3. PE 资源段必须落在 main 包目录，且 -ico 按通道选择
    subprocess.run([
        r"C:\Users\29580\go\bin\rsrc.exe",
        "-manifest", str(PROJECT_ROOT / "wails.exe.manifest"),
        "-ico", str(icon),
        "-arch", "amd64",
        "-o", str(PROJECT_ROOT / "cmd" / "your_app" / "rsrc_windows_amd64.syso"),
    ], cwd=str(PROJECT_ROOT), check=True)

    # 4. 版本与产物名
    dirty = worktree_dirty()
    base = args.version.lstrip("v") or base_version()
    version = f"v{base}" if release else f"v{base}-dev" + ("-dirty" if dirty else "")
    out_exe = PROJECT_ROOT / ("your_app.exe" if release else "your_app-dev.exe")

    # 5. 编译（dev 额外注入 -tags dev，切换窗口/托盘图标）
    build_mode = "release" if release else "dev"
    cmd = ["go", "build", "-trimpath"]
    if not release:
        cmd += ["-tags", "dev"]
    cmd += [
        f"-ldflags=-w -s -H windowsgui "
        f"-X your_app/internal/app.Version={version} "
        f"-X your_app/internal/app.BuildMode={build_mode}",
        "-o", str(out_exe),
        "./cmd/your_app",
    ]
    subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=True)
    print(f"🎉 {out_exe.name} ({out_exe.stat().st_size / 1048576:.2f} MB, {version}, {build_mode})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

---

## 四、 交付验收与测试断言

| 验证项 | 测试操作 | 预期断言 |
|:---|:---|:---|
| **双击启动零黑框** | 资源管理器双击 `your_app.exe` | 100% 不闪烁任何 CMD 窗口；托盘就绪；主窗口正常展示 |
| **任务栏图标正常** | 观察任务栏运行图标 | 100% 显示专属矢量图标，绝无默认“白窗蓝方块”通用图标 |
| **CLI 回显与秒退** | 终端执行 `.\your_app.exe version \| Out-String` | 正确回显 `YourApp vX.Y.Z[-dev] (mode: ..., build: ...)` 并立即退出 |
| **开机自启隔离 (Dev)** | 本地 Dev 构建运行，右键托盘菜单 | 菜单显示 `开机自启 (开发版已禁用)` 且**置灰无法勾选**；注册表无写入 |
| **开机自启支持 (Release)** | 精确 tag + 干净工作区构建 release，右键托盘 | 菜单显示 `开机自启`，勾选后注册表写入 `"exe" --hidden` |
| **静默托盘启动** | 终端执行 `.\your_app.exe --hidden` | 不弹出主窗口，仅托盘图标出现，后台守护正常就绪 |
| **关窗释放内存** | 任务管理器观察，点击右上角叉号（X） | WebView2 子进程全部退出，进程常驻内存从 ~350MB 回落至 ≤ 40MB |
| **双击瞬时重建** | 关窗后双击托盘图标或点击“打开工作台” | 毫秒级重新拉起 WebView2 窗口并聚焦，业务页面正常展现 |
| **默认浏览器跳转** | 托盘菜单点击“在默认浏览器中打开” | 系统唤起 Chrome/Edge 打开 `http://127.0.0.1:<port>` |
| **release 门禁** | 未打 tag 或工作区脏时执行 `uv run scripts/build.py --release` | 退出码 2，不产出 `your_app.exe`，也不覆盖既有 dev 产物 |
| **dev 图标可辨** | dev 与 release 分别构建后看文件管理器/任务栏 | dev 为 Go 地鼠、release 为专属图标；两者 `ExtractAssociatedIcon` 哈希不同 |
| **通道数据隔离** | dev 与 release 各运行一次 | 分别写入 `%APPDATA%\language_projects\<app>\dev` 与 `\prod`，互不可见；两通道可同时运行 |
| **构建幂等** | 连续两次 release 构建后执行 `git status --porcelain` | 输出为空（图标重绘字节稳定，不产生脏文件，不会自锁 release 门禁） |
