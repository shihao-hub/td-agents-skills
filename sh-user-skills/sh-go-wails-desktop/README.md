---
name: sh-go-wails-desktop
description: Go 双通道桌面应用脚手架：GUI(-gui) 只开窗口不做 CLI、CLI(-cli) 只跑终端不开窗口，内嵌 WebUI 与 Wails v3 托盘、dev/release 通道隔离、PE 图标双通道与无控制台排障。点名使用
version: 1.5.0
created: 2026-10-21
updated: 2026-10-21
disable-model-invocation: true
---

# sh-go-wails-desktop：Go 双通道桌面应用脚手架与通道隔离

> **定位**：把一个 Go 工具做成**两条通道、四个产物**——`<app>-gui` 只开桌面壳（Wails v3 托盘 + 内嵌 HTTP/WebUI），`<app>-cli` 只做终端 CLI；并让 dev / release 两个通道在产物名、版本号、数据目录、单实例 ID、图标五个维度完全隔离。
> **硬约束**：GUI 产物不解析任何子命令（不管从哪里启动都只出窗口），CLI 产物不开窗口。**禁止**用 `-H windowsgui` + `AttachConsole` 把两者合成单产物（原因见「三、反模式警示」）。
> **来源**：由知识库条目 `kb-engineering-notes/082` 转正（原条目保留为 deprecated 存根，历史排障细节可回溯）。
> **验证锚点**：Windows 11 24H2、Go 1.26、Wails v3.0.0-beta.33、Edge WebView2；实机项目 `go_projects/anatomymanager`（2026-10-21 全链路实测；同日二次实测推翻了本 skill 1.2.0 的「单产物双模」旧范式，产物改名 `-gui` / `-cli`；1.4.0 补齐 Step 4b 窗口几何记忆）。
> **深度材料**：
> - `references/architecture.md`：双通道蓝图、目录树、PE 清单与版本元数据、`gui.go` 全文、窗口几何记忆实现
> - `references/build-pipeline.md`：构建脚本全文、通道隔离五件套、图标双通道
> - `references/troubleshooting.md`：任务栏白框、无控制台日志、窗口不记忆/跑到屏外、门禁拒绝等排障

---

## 一、前置检查与环境准备

```powershell
go version          # ≥ 1.23（Wails v3 要求）
uv --version        # 构建脚本使用 PEP 723 内联依赖（Pillow）
Get-Command rsrc    # 缺则 go install github.com/akavel/rsrc@latest，确认 %GOPATH%\bin 在 PATH
```

- **WebView2 Runtime**：查 `HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}`，不存在则安装 Evergreen Runtime。
- **Git 约定**：monorepo 内项目 tag 必须带项目前缀（`<project>/v1.0.0`），构建脚本据此判定 release；单仓项目可把 `TAG_PREFIX` 置空。
- **资产就位**：`internal/app/icon_dev.ico`（dev 通道静态图标）需入库；`internal/app/icon.ico` 是 `go:embed` 必需资产，确认未被 `.gitignore` 误伤（`git check-ignore -v internal/app/icon.ico` 应无输出）。

---

## 二、分步执行 SOP

### Step 1 建骨架

按 `references/architecture.md` 的目录树创建：

```text
cmd/<app>/          main.go(GUI 入口 //go:build !cli) / cli.go(CLI 入口 //go:build cli) / rsrc_windows_amd64.syso(生成物)
internal/api        HTTP REST
internal/app        gui.go / autostart.go / version.go / datadir.go / icon_*.go / log.go
internal/storage    SQLite（或你的持久层）
internal/web        //go:embed 前端资产
scripts/            render_icon.py / build.py
根目录              icon.png / icon.ico / icon_dev 静态资产 / info.json / wails.exe.manifest
```

**校验**：`go build ./cmd/<app>` 通过（尚无资源段时使用系统默认图标属正常）。

### Step 2 GUI 入口（`main.go`，`//go:build !cli`）

**不解析子命令**：任何启动方式（双击 / 终端 / 快捷方式 / 带任意参数）都只显示桌面壳；唯一语义参数是 `--hidden`（开机自启注册的静默托盘，`--tray` 作同义别名），其余参数一律忽略。

```go
//go:build !cli

package main

func main() {
	hidden := false
	for _, arg := range os.Args[1:] {
		switch arg {
		case "--hidden", "--tray":
			hidden = true
		}
	}
	if err := app.LaunchGUI("", 0, hidden); err != nil { // port=0 → 动态探测可用端口
		fallbackServe(!hidden) // WebView2 运行时缺失时降级为无窗口 HTTP 服务
	}
}
```

**校验**：``.\<app>-gui-dev.exe list --json`` 不给任何 CLI 输出、只出窗口（参数被忽略）。

### Step 3 CLI 入口（`cli.go`，`//go:build cli`）

console 子系统产物，全部子命令集中于此；无参数打印用法，`--hidden` / `--tray` 退化为无窗口 `serve`。两个入口文件用 build tag 各自提供一个 `main()`，handler 只在 `cli` 通道编译。

```go
//go:build cli

package main

func main() {
	if len(os.Args) < 2 {
		printUsage()
		return
	}
	switch command := os.Args[1]; command {
	case "ingest":
		handleIngest(os.Args[2:])
	// ... list / get / export / serve / schema / version
	default:
		fmt.Fprintf(os.Stderr, "未知子命令: %s\n", command)
		os.Exit(1)
	}
}
```

**校验**：``.\<app>-cli-dev.exe version`` 回显通道后秒退，且 prompt 正常返回、末尾无悬空光标。

#### 硬约束：`serve` 必须同时托管 WebUI，不得只起裸 API

`serve` 是 CLI 通道里唯一会阻塞的常驻命令，它必须与 GUI 打开的是**同一个 HTTP handler**：根路径返回内嵌 WebUI（`internal/web/assets`），`/api/*` 返回 REST。正确做法是把 HTTP 层放在独立包（如 `internal/api` 或 `internal/webui`），GUI 与 CLI 都调用同一个 `Handler()`：

```go
// internal/api/server.go —— 不依赖 Wails，GUI 与 CLI serve 共用
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/artworks", s.handleArtworks)
	subFS, _ := fs.Sub(web.Assets, "assets")
	mux.Handle("/", http.FileServer(http.FS(subFS)))
	return mux
}
```

```go
// cli.go :: handleServe
listener, err := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", *port))
if err != nil {
	fmt.Fprintf(os.Stderr, "绑定监听失败: %v\n", err)
	os.Exit(1)
}
url := "http://" + listener.Addr().String()
fmt.Printf("%s WebUI is running at %s\n", appName, url) // console 通道直接打印
log.Fatal(http.Serve(listener, api.NewServer(store).Handler()))
```

- **禁止**把 `serve` 实现成只有 `/v1/*`、`/api/*` 的裸 API 端口：根路径 `404 page not found` 就是典型症状（历史项目 `agyquota` 踩过）。
- 端口语义：`serve --port` 可默认 0（动态探测）或项目约定固定端口；GUI 的窗口 URL 与 CLI 打印的 URL 必须来自**同一次 `net.Listen` 结果**，禁止「以为的端口」。
- 若项目另有后台 daemon 架构（CLI 客户端 + daemon），daemon 的 HTTP 层也必须挂同一个 WebUI handler，让 `serve` 根路径可用；**不要出现 WebUI 只属于 GUI、CLI/daemon 只能 curl JSON 的分裂**。
- 拆包方向：`webui`/`api` 包只依赖 `internal/web`、业务核心与日志注入点，**不得 import `internal/app`**（否则会把 Wails 拖进 console 产物）。
- 验收：`serve` 后浏览器打开打印的地址必须是完整工作台页面，同时 `/v1/ping` 或 `/api/*` 仍正常；`/v1/` 下的未知路径保持 404，不能被静态文件服务吞掉。

### Step 4 桌面壳（`gui.go`）

托盘常驻、单实例、窗口关闭销毁 + 双击重建、任务栏图标在 HWND 就绪后绑定。完整实现见 `references/architecture.md`。关键点：

- `DisableQuitOnLastWindowClosed: true` 保持托盘常驻；
- dev 的 `SingleInstanceOptions.UniqueID` 必须追加 `.dev`，否则与常驻正式版互斥；
- 关闭窗口放行 `WindowClosing`，延时 `runtime.GC()` + `debug.FreeOSMemory()`；
- **端口默认 `port=0` 动态探测**，不要写死固定端口（如 8765）：GUI 必须先 `net.Listen` 拿到真实端口才能构造窗口 `URL:`，CLI `serve` 则绑定后阻塞；两处共用同一个绑定函数与同一个 `Handler()`（见 Step 3 硬约束），杜绝「以为的端口」与「实际端口」两份真相，也杜绝 GUI 有页面、CLI 只有裸 API 的分裂。实际 URL 必须走 `logf`（`-H windowsgui` 下 stdout 不可见）或 console 通道的 `fmt.Printf`，固定端口仅作为可选参数保留。

**校验**：dev 与 release 可同时运行且互不唤醒。

### Step 4b 窗口几何记忆（尺寸 / 位置 / 最大化）

wails v3（beta.33 实测）**没有**任何窗口状态记忆能力：`WebviewWindowOptions` 只有 `Width/Height/X/Y/InitialPosition`，每次 `NewWithOptions` 都按字面值重建。而本架构「关窗 ≠ 退进程」（托盘常驻），用户从托盘或快捷方式再开时走的正是同一条 `buildWindowLocked` —— 于是**永远回到默认尺寸**。这一条是实测反馈的第一号体验缺陷，必须自己补，别指望升级 wails 解决。

新增 `internal/app/window_state.go`（纯函数 + 无副作用，可直接单测）：

```go
const windowStateFileName = "window.json"

type windowState struct {
	Width     int  `json:"width"`
	Height    int  `json:"height"`
	X         int  `json:"x"`
	Y         int  `json:"y"`
	HasPos    bool `json:"hasPosition"`
	Maximised bool `json:"maximised"`
}

func windowStatePath() string { /* appDataDir() + windowStateFileName */ }
func loadWindowState() windowState { /* 缺失/脏 JSON/过小尺寸 → 回落默认值 */ }
func writeWindowState(s windowState) error { /* MkdirAll + os.WriteFile */ }
```

- **落盘位置**：`<appDataDir>/window.json`，dev / prod 自动隔离；`os.WriteFile` 写出无 BOM UTF-8。
- **单位一致**：Windows 下 `Size()` / `Position()` 内部走 `PhysicalToDipRect`，返回的就是 DIP，与 `WebviewWindowOptions.Width/X` 同单位，**原值存取，别再叠加缩放换算**。
- **恢复**：`HasPos` 为真时才设 `InitialPosition: application.WindowXY` + `opts.X/Y`（否则保持 OS 默认居中）；`Maximised` 为真在 `win.Show()` **之后** `win.Maximise()`。
- **采集**：订阅 `events.Common.{WindowDidMove, WindowDidResize, WindowMaximise, WindowUnMaximise}` → **700ms 防抖**落盘（拖拽一次会触发几十个事件）；`WindowClosing` 钩子里先 `timer.Stop()` 再**同步**保存一次（窗口销毁后 `Size()` 归零，晚一步就只能存到 0）。
- **最大化不得污染还原尺寸**：`IsMaximised()` 为真时只翻 `Maximised = true`，绝不覆盖 `Width/Height/X/Y`；`IsMinimised()` / `IsFullscreen()` 直接 `return`（否则会把 -32000 之类最小化坐标写进库）。
- **外接屏兜底**：`WindowShow` 钩子里取 `app.Screen.GetAll()`，用 `WorkArea`（DIP）判断窗口中心是否落在某块屏内，不在则 `win.Center()` 并回写（拔掉外接屏后旧坐标会让窗口彻底不可见，用户以为程序没启动）。
- **保存入口不要做窗口存活校验**：`saveWindowState` 只需判 `win == nil`，别用 `aliveWindow()` 那种 `Window.GetByID` 校验——`WindowClosing` 触发时窗口还没销毁，用存在性校验反而会跳过保存。

**校验**（`go test` 五条断言 + 三项实机操作）：

```powershell
go test ./internal/app/ -run WindowState -v   # 往返 / 无文件 / 脏 JSON / 过小尺寸 / 无坐标不恢复位置
```

1. 移动 + 缩放窗口 → 等 1s → `window.json` 与窗口实际几何一致；
2. 关窗（进程留托盘）→ 再次启动 exe → 新窗口精确恢复上次尺寸与位置；
3. 最大化后关窗重开 → 仍是最大化，且 `window.json` 里保留的还原尺寸没被写成满屏值。

### Step 5 图标资产（release 专属 + dev 地鼠）

`render_icon.py` 生成 1024 PNG 与 256/128/64/48/32/24/16 全尺寸 ICO，并同步 `internal/app/icon.ico`；把 `go-default.ico` 复制为 `internal/app/icon_dev.ico`。脚本全文见 `references/build-pipeline.md`。

**校验**：`gofmt -l internal/app` 无输出（`//go:embed` 前需空 `//` 注释行）。

### Step 6 构建脚本（`build.py`）

按 `references/build-pipeline.md` 落地。**一次构建在同一通道内产出两个二进制**：

| 通道 | 产物 |
|:---|:---|
| dev | `<app>-gui-dev.exe` + `<app>-cli-dev.exe` |
| release | `<app>-gui.exe` + `<app>-cli.exe` |

判定规则：

```text
HEAD 精确命中 <project>/v* tag  且  工作区干净（剔除构建生成物）  → release
其余情况（含无 tag、脏工作区、--release 但条件不足）            → dev / 退出码 2
```

**校验**：无 tag 时 `uv run scripts/build.py --release` 退出码 2，且不产出正式名。

### Step 7 运行数据隔离

`appDataDir()` 返回 `%APPDATA%\language_projects\<app>\{dev,prod}`（取不到则 `~/.language_projects/<app>/<通道>`）；首次启动把旧库及 `-wal`/`-shm` 复制到新目录，**旧文件保留不删**。

**同通道多进程并发（必做，别用单实例/端口去解决）**：同一通道的库会被「GUI 内嵌服务 + 多个 CLI（`serve` / `ingest`）」同时打开。动态端口下多进程共存是常态，因此数据层必须自带守卫：

```go
// 上游默认 busy_timeout=0 + rollback journal，并发写会直接报 database is locked。
const sqliteDSNParams = "?_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)&_pragma=synchronous(NORMAL)"
db, err := sql.Open("sqlite", dbPath+sqliteDSNParams)
```

- **并发模型前提**：GUI 的 HTTP 层保持只读（写只走 CLI），这样 WAL 下「读不阻塞写、写不阻塞读」即可覆盖全部场景；将来给 GUI 加写接口时，才需要引入跨进程写锁（命名 Mutex）。
- **`busy_timeout` 是每连接的 busy handler**，跨进程同样生效；WAL 是持久化到库文件的设置，写一次后对新连接持续有效。
- **驱动注意**：`modernc.org/sqlite` 在 DSN 不以 `file:` 开头时，`?` 之后按 query 解析、路径原样保留，Windows 反斜杠路径可直接拼接。
- **GUI 退出前 `store.Close()`**：让 WAL 及时 checkpoint，避免 `-wal` 膨胀到下次启动。
- **回归测试三断言**（少一条就可能被后人删掉参数）：带守卫的第二个写者必须等持锁方释放后成功；裸 DSN 必须立即失败；`NewStore` 产出的连接必须 `journal_mode=wal` 且 `busy_timeout=5000`。

**校验**：dev 与 release 各执行一次 `list`，两个通道目录各自出现数据库文件；再并行跑两个 `ingest`（含首次建表 DDL 竞争）并其间请求 `/api/artworks`，应全部成功。

### Step 8 开机自启门禁

仅 `IsRelease()` 允许 `Autostart.EnableWithOptions`；dev 菜单项置灰，后端返回 `dev_mode` 错误并拒绝写入。

**校验**：dev 版尝试勾选自启后，`HKCU\Software\Microsoft\Windows\CurrentVersion\Run` 无新增项。

### Step 9 构建与验收

```powershell
cd <project>
uv run scripts/build.py            # dev     → <app>-gui-dev.exe + <app>-cli-dev.exe  vX.Y.Z-dev[-dirty]
git tag <project>/v1.0.0
uv run scripts/build.py --release  # release → <app>-gui.exe     + <app>-cli.exe      vX.Y.Z
git status --porcelain             # 必须为空：构建不得弄脏工作区
```

按下节验收表逐项确认；发布后如需继续开发，新提交自然回到 dev 通道。

---

## 三、反模式警示：禁止单产物双模

**症状族**（出现任意一条就说明踩了这个坑）：

- 执行 exe 后 prompt 被顶掉、输出接在 prompt 后面，屏幕末尾留一个**悬空块状光标**；
- `--json > out.json` 或 `| jq` / `| ConvertFrom-Json` 拿到**空内容**；
- `serve` 这类阻塞命令 shell 根本不等待，立即返回 prompt。

**为什么不可救**：

- PowerShell / cmd 对 GUI 子系统进程**异步启动**，prompt 早已渲染完毕；随后 `AttachConsole(ATTACH_PARENT_PROCESS)` 抢父控制台只能往“当前光标处”追加，**没有任何一方负责重绘 prompt**；
- Shell 不向 GUI 子系统进程传管道句柄，重定向注定丢输出；
- 补前导换行、保存/还原句柄都是治标：shell 依然不会重新给出可交互 prompt。

**业内做法**：`git.exe` / `git-gui.exe`、`docker.exe` / `Docker Desktop.exe`、`python.exe` / `pythonw.exe` 一律拆成两个产物，本 skill 的 `<app>-gui` / `<app>-cli` 同此。

**唯一保留项**：GUI 产物内部仍用 `logf` 双写落盘做无控制台排障（`references/troubleshooting.md` §3.2），但绝不向控制台写业务输出。

---

## 四、常见踩坑与回滚

| 症状 | 根因 | 处置 |
|---|---|---|
| 任务栏 / 资源管理器图标是白框 | `.syso` 未放在 `cmd/<app>/`；manifest 非 4 段；乱设 AppUserModelID | `references/troubleshooting.md` §1 |
| 双击无窗口、托盘也不出现 | WebView2 运行时缺失；启动参数冲突 | 装 Evergreen Runtime；看 `logf` 落盘日志 |
| CLI 在 PowerShell 无输出 / `--json > out.json` 为空 | GUI 子系统进程拿不到父进程管道句柄；`AttachConsole` 只能写进控制台 | 改用 `<app>-cli.exe`，GUI 产物不做 CLI（本节 + `troubleshooting.md` §3） |
| 执行后 prompt 被顶掉、末尾光标悬空 | shell 不等待 GUI 子系统进程，prompt 先渲染，程序又往同一光标处写 | 同上：终端一律用 `-cli` 产物 |
| `--release` 总被拒 | tag 前缀不匹配；工作区脏（生成物未入 ignore） | 查 `git tag --points-at HEAD` 与 `.gitignore` |
| dev 与正式版互相挤掉 | 单实例 ID 未隔离 | dev `UniqueID` 追加 `.dev` |
| `go:embed` 资产被忽略 | `.gitignore` 写成 `icon.ico` | 改为 `/icon.ico`，用 `git check-ignore -v` 复核 |
| `gofmt -l` 一直报图标文件 | doc comment 与 `//go:embed` 间缺空 `//` 行 | 补一行 `//` |
| `serve` 根路径 `404 page not found` | CLI serve 只挂了裸 API，WebUI handler 只被 GUI 使用 | HTTP 层抽独立包，GUI 与 CLI/daemon 共用同一 `Handler()`（Step 3 硬约束） |
| 并发写报 `database is locked (SQLITE_BUSY)` | 裸 DSN：`busy_timeout=0` + rollback journal | 统一 DSN 加 `busy_timeout`/WAL（Step 7、troubleshooting §8） |
| 每次打开窗口都是默认尺寸、位置也不记得 | wails v3 不内置窗口状态记忆；关窗只销毁窗口（进程留托盘），重建走同一份默认 options | 落 `window.json` + 几何事件防抖保存（Step 4b、troubleshooting §9） |
| 最大化后重开，点还原变成满屏或尺寸错乱 | 把最大化尺寸写进了「还原几何」 | 保存时先判 `IsMaximised()`，最大化只翻标记不采集尺寸（Step 4b） |

**回滚**：

```powershell
Remove-Item .\<app>-gui-dev.exe, .\<app>-cli-dev.exe -ErrorAction SilentlyContinue  # 只删产物，不动源码
git tag -d <project>/vX.Y.Z                                                        # 误打 tag（远端已 push 需单独处理）
```

数据目录回滚：删除 `%APPDATA%\language_projects\<app>\{dev,prod}` 不影响旧库（迁移只复制不删除）。

---

## 五、交付验收清单

| 验证项 | 操作 | 预期 |
|---|---|---|
| 双击零黑框 | 资源管理器双击 | 无 CMD 闪窗；托盘就绪 |
| 任务栏图标 | 观察运行图标 | 专属图标，无白框 |
| CLI 回显 | `.\<app>-cli.exe version` | 版本 + 通道正确后秒退，prompt 正常返回、无悬空光标 |
| CLI 管道 | `.\<app>-cli.exe list --json \| ConvertFrom-Json` | 正常拿到 JSON，非空 |
| GUI 忽略参数 | `.\<app>-gui.exe list --json` | 只出窗口，零 CLI 输出 |
| 双通道子系统 | 读 PE 头 Subsystem | gui=2(WINDOWS_GUI)、cli=3(CONSOLE) |
| dev 图标 | 看文件管理器 | Go 地鼠；release 为专属图标 |
| release 门禁 | 无 tag / 脏工作区执行 `--release` | 退出码 2，不产正式名 |
| 通道数据隔离 | dev 与 release 各跑一次 | 分别落 `dev` / `prod` 目录 |
| 并发写不冲突 | 并行两个 `ingest`，其间请求 `/api/artworks` | 两条都 success，API 200 |
| 单实例隔离 | 两者同时运行 | 互不唤醒、可并存 |
| 端口零冲突 | dev 与 release 同时启动看日志 URL | 各自不同动态端口，互不串台 |
| CLI serve WebUI | `.\<app>-cli.exe serve` 后浏览器打开输出地址 | 根路径 200 显示完整工作台；`/api/*` 正常 |
| 自启门禁 | dev 勾选自启 | 菜单置灰 + 注册表无写入 |
| 关窗释放 | 关窗后看任务管理器 | WebView2 子进程退出，内存回落 |
| 窗口记忆 | 移窗 + 缩放 → 关窗 → 从托盘重开 | 恢复上次尺寸与位置 |
| 最大化记忆 | 最大化 → 关窗 → 重开 → 点还原 | 重开即最大化；还原回到记忆的还原尺寸，不是满屏 |
| 构建幂等 | 连续两次 release 后 `git status` | 输出为空 |

---

## 六、参考索引

| 文件 | 内容 |
|---|---|
| `references/architecture.md` | 双通道蓝图、目录树、manifest/info.json、`gui.go` 全文、窗口几何记忆（§四·补）、生命周期 |
| `references/build-pipeline.md` | 通道隔离五件套与铁律、图标双通道、`render_icon.py` / `build.py` 全文 |
| `references/troubleshooting.md` | PE 图标三铁律、HWND 时序、无控制台日志、窗口几何不记忆（§9）、门禁与迁移排障 |
| `kb-engineering-notes/082_...md` | 原知识库条目（deprecated 存根，保留检索入口） |
