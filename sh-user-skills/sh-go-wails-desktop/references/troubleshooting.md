# 排障参考：PE 图标、无控制台日志与构建门禁

> 归属：`sh-go-wails-desktop`。症状 → 根因 → 处置，按现场报错顺序排列。

---

## 1. 任务栏 / 资源管理器图标是白框或系统默认图标

### 三条铁律

1. **`.syso` 必须与 `package main` 同目录**
   - 任务栏与 Explorer 读的是 PE 头部静态资源（`RT_GROUP_ICON` / `RT_ICON`），不是运行时内存图标。
   - Go 编译器只收集与 main 包同目录的 `.syso`。放到项目根而 main 在 `cmd/<app>/` 时，`go build ./cmd/<app>` **完全不会**读取它，产物 PE 资源为空。
   - 正确输出：`cmd/<app>/rsrc_windows_amd64.syso`。

2. **manifest 版本必须 4 段式**
   - `<assemblyIdentity version="1.0.0.0">`；写成 3 段（`0.1.0`）会导致进程启动即报 `Side-by-side configuration is incorrect`。

3. **绿色便携版（免安装 exe）不要声明未注册的 AppUserModelID**
   - `SetCurrentProcessExplicitAppUserModelID` 会让任务栏改从开始菜单快捷方式匹配 AppID；无安装器注册快捷方式时图标直接退化为空白方块。
   - 让 Explorer 自然绑定 exe 自身 PE 头部图标即可。

### 窗口/托盘图标正常但任务栏不对

内存图标（`tray.SetIcon` / `app.Icon`）与 PE 资源是两套通道，见 `build-pipeline.md` 的图标双通道。

---

## 2. 任务栏图标时而正常时而丢失（HWND 时序）

- `Window.NewWithOptions` 返回时 `win.NativeWindow()` 仍为 0，此时 `WM_SETICON` 全部静默失效。
- 必须在 `events.Windows.WindowShow` 与 `WindowActive` 钩子里调用 `applyWindowIcon`，并在 `win.Show()` 之后补调一次。
- 大图标走 `WM_SETICON + ICON_BIG`（任务栏 / Alt+Tab），小图标走 `ICON_SMALL`（标题栏），`SetApplicationIcon` 固化窗口类图标。

---

## 3. GUI 产物跑 CLI：prompt 错位 / 光标悬空 / 管道为空

### 3.1 症状族 → 根因 → 正解

**症状**（任意一条都指向同一个根因）：

- 在 PowerShell / cmd 执行 exe 后，prompt 被顶掉，输出接在 prompt 行后面；
- 屏幕末尾留一个**悬空块状光标**，按任意键画面才跳一下；
- `--json > out.json`、`| jq`、`| ConvertFrom-Json` 拿到**空内容**；
- `serve` 这类阻塞命令 shell 立刻返回 prompt（压根没等）。

**根因**：GUI 子系统（`-H windowsgui`）进程被 shell **异步启动**——prompt 在程序开始输出之前就已渲染完毕，且没有任何一方负责重绘；同时 shell 不向 GUI 子系统进程传管道句柄。

**正解**：拆双通道产物，终端一律用 console 那一个。

| 产物 | 子系统 | 请求 | 结果 |
|:---|:---|:---|:---|
| `<app>-gui.exe` | GUI(2) | 双击 / 任意参数 | 只出窗口（无 CLI 输出） |
| `<app>-cli.exe` | Console(3) | 子命令 / JSON / 管道 | shell 正常等待，输出与重定向全合规 |

**校验子系统**（两条通道必须分别是 2 和 3）：

```powershell
uv run python -c "import struct,sys;d=open(sys.argv[1],'rb').read(0x400);pe=struct.unpack_from('<I',d,0x3c)[0];print(sys.argv[1], struct.unpack_from('<H',d,pe+0x5c)[0])" .\bin\<app>-gui.exe
# 期望输出 2（IMAGE_SUBSYSTEM_WINDOWS_GUI）
uv run python -c "import struct,sys;d=open(sys.argv[1],'rb').read(0x400);pe=struct.unpack_from('<I',d,0x3c)[0];print(sys.argv[1], struct.unpack_from('<H',d,pe+0x5c)[0])" .\bin\<app>-cli.exe
# 期望输出 3（IMAGE_SUBSYSTEM_WINDOWS_CUI）
```

**验证 shell 是否真的等待**（关键反证）：把 `serve` 放到后台跑，若父 shell 仍在阻塞，说明等待关系正常：

```powershell
$p = Start-Process -PassThru .\bin\<app>-cli.exe -ArgumentList 'serve','--port','0'
Start-Sleep 3
if (-not $p.HasExited) { "shell 已交出控制权但进程仍在跑（serve 语义正确）" }
$p | Stop-Process
```

### 3.2 反模式：`AttachConsole` 抢救单产物

历史做法是给 GUI 产物加 `console_windows.go`，在 `init()` 里 `AttachConsole(ATTACH_PARENT_PROCESS)` 并重绑 `os.Stdout` / `os.Stderr`，企图让一个 exe 兼做 CLI。**这条路已被实测否决**：

- 抢来的控制台只能往"当前光标处"追加，prompt 已被 shell 画完，没人重绘 → 悬空光标与错位 prompt 是必然而非偶发；
- GUI 进程拿不到 shell 的管道句柄，重定向永远是空文件；
- 即便再加"保存/还原有效句柄 + 补前导换行"，也只能缓解视觉，shell 仍不会重新交回可交互 prompt。

因此 skill 的产物契约是：**GUI 不做 CLI，CLI 不开窗口**，不要为了"少一个 exe"把两者合并。

### 3.3 无控制台时看日志 → slog 双写

`internal/logx/logx.go` 把每条日志同时写 `os.Stderr` 与 `<appDataDir>/<app>.log`：

```go
type teeWriter struct{ stderr, file io.Writer }

func (w teeWriter) Write(p []byte) (int, error) {
	_, _ = w.stderr.Write(p) // GUI 子系统下必然失败，必须忽略
	return w.file.Write(p)
}

func Init(dataDir string) *slog.Logger {
	// …OpenFile(append) → teeWriter{os.Stderr, f}
}
```

**四个必须点**：

1. `io.MultiWriter` 不行：stderr 写失败会短路，文件一条也写不进去（release 下日志永远为空）；
2. `logx` 不 import `store`（由调用方传 `dataDir`），否则 `store → logx → store` 依赖成环；
3. Wails 内部日志用过滤后的 `SystemLogger()`，去掉 `[AssetFileServerFS] Handling request` 噪音，否则错误会被逐请求日志淹没；
4. 2 MB + 1 份轮转，避免无限增长；启动横幅记录 `version / commit / mode`。

排障路径：`%APPDATA%\language_projects\<app>\<dev|prod>\<app>.log`。启动失败、单实例冲突、备份失败、前端 JS 异常（`[FE]` 前缀）都在这一个文件里。release 无控制台时靠 panic 弹窗提示日志位置。

### 3.4 前端白屏 / 交互异常

- 确认内置 HTTP 服务已监听：默认 `port=0` 由内核探测端口，日志里有实际 URL（`WebUI 已启动: http://127.0.0.1:<port>`）。显式传入固定端口却被占用时，GUI 直接启动失败并落 `logf`、CLI 直接报错退出——不再提供「失败后偷偷换端口」的兜底，否则外部无法确定到底连到了哪个实例。
- 需要看 WebView2 控制台时，用 Wails v3 的 Debug 选项开启 DevTools（不同 beta 版本字段名有差异，以 `go doc` 为准），不要为此改动 release 构建。

---

## 4. `--release` 一直返回 2（拒绝发布构建）

按顺序自查：

```powershell
git tag --points-at HEAD          # 是否精确命中 <project>/v* tag
git status --porcelain            # 是否仍有未提交/未忽略文件
git check-ignore -v icon.ico internal/app/icon.ico
```

- **tag 前缀不匹配**：monorepo tag 必须是 `<project>/vX.Y.Z`；`TAG_PREFIX` 为空时只认 `vX.Y.Z`。
- **工作区脏**：生成物未进 `.gitignore`（`icon.ico`、`.syso`、`bin/`）会永远判脏；`.gitignore` 必须写 `/bin/` 而不是逐个根目录 exe。
- **`.gitignore` 误伤**：写成 `icon.ico` 会忽略 `internal/app/icon.ico`，干净检出后 `go:embed` 直接编译失败；必须 `/icon.ico`。
- **`--version` 误用**：它只覆盖版本基线，不改变通道判定；想发版只能靠 tag + 干净工作区。

---

## 5. dev 与正式版互相挤掉 / 数据串台

- **单实例**：`SingleInstanceOptions.UniqueID` dev 必须追加 `.dev`。
- **数据目录**：`appDataDir()` 按 `IsRelease()` 追加 `dev` / `prod` 子目录。
- **旧库迁移**：新库不存在且旧库存在时复制主库与 `-wal`/`-shm`，旧文件保留；若迁移失败会在日志留痕并继续使用旧库。
- **验证**：`%APPDATA%\language_projects\<app>\` 下应同时出现 `dev` 与 `prod` 目录，各自独立数据库与日志。

---

## 6. dev 版勾选开机自启无效

预期行为，不是 bug：

- 托盘菜单在 `!IsRelease()` 时渲染为置灰的 `开机自启 (开发版已禁用)`；
- 即使绕过 UI，`setAutostart` 也返回 `dev_mode: 开发版禁止注册开机自启`；
- 验证注册表：`HKCU\Software\Microsoft\Windows\CurrentVersion\Run` 不应出现你的应用项。

要测试自启，直接构建 release 并运行。

---

## 7. 其他高频小坑

| 现象 | 原因 | 处置 |
|---|---|---|
| `gofmt -l` 一直报 `icon_dev.go` | 文档注释与 `//go:embed` 之间缺空 `//` 行 | 补一行 `//` |
| Python 构建脚本首行报 `invalid non-printable character U+FEFF` | 文件被写入 BOM | 去 BOM（`UTF8Encoding($false)` 或写后自检） |
| `uv run scripts/build.py` 报无 Pillow | 直接用 `python` 而非 `uv run` | 用 `uv run`（PEP 723 自动装依赖） |
| 构建后 `git status` 变脏 | 图标渲染非确定性 | 固定渲染参数，确保同源码同字节 |
| `rsrc.exe` / `go-winres.exe` 找不到 | `%GOPATH%\bin` 不在 PATH | 用 `go install github.com/tc-hib/go-winres@latest` 后补 PATH |
| exe 属性面板版本/描述全空 | rsrc 不支持 VERSIONINFO，或 syso 未按产物重建 | 改用 go-winres，并在每个产物 go build 前重建 syso（见 build-pipeline.md） |

---

## 8. 并发写入报 `database is locked (SQLITE_BUSY)`

**症状**：GUI 桌面壳运行中，另一个终端跑 `ingest`（或两个 `ingest` 并行）偶尔直接报 `database is locked (5) (SQLITE_BUSY)`，而不是等待。

**根因**：`sql.Open("sqlite", dbPath)` 用裸 DSN 时，上游 `busy_timeout` 默认为 **0**，且默认 rollback journal 下写者互斥，第二个写者拿不到锁就立即失败。这跟端口、单实例都无关——动态端口下多进程共存是常态。

**处置**：

1. 统一 DSN（存储层一处改完，所有入口共享）：
   ```go
   const sqliteDSNParams = "?_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)&_pragma=synchronous(NORMAL)"
   db, err := sql.Open("sqlite", dbPath+sqliteDSNParams)
   ```
2. 保持 GUI 的 HTTP 层只读（写只走 CLI），这样 WAL 足以覆盖全部场景；给 GUI 加写接口后才需要跨进程写锁。
3. GUI 退出路径补 `store.Close()`，让 WAL checkpoint 及时落盘。
4. 补回归测试（三条）：带守卫的第二个写者需等待成功；裸 DSN 必须立即失败；`NewStore` 必须 `journal_mode=wal`、`busy_timeout=5000`。

**验证**：并行两个 `ingest`（各含数 MB 产物，含首次建表 DDL 竞争）+ 同时请求 `/api/artworks`，三者均成功。

---

## 9. 窗口尺寸/位置/最大化不记忆，或恢复后窗口跑到屏幕外

**症状**：每次从托盘或快捷方式重新打开，窗口都回到 1280×850 居中；或者搬动/缩放后关窗再开全丢。反过来还可能出现：重开后窗口压根看不见（任务栏有图标、屏幕没有窗口）。

**根因**：

1. wails v3 的 `WebviewWindowOptions` 只有 `Width/Height/X/Y/InitialPosition`，**没有任何状态持久化能力**，每次 `NewWithOptions` 都按字面值重建；
2. 本架构「关窗只是销毁窗口、进程留托盘」，重建走的还是同一条 `buildWindowLocked`，于是永远默认尺寸；
3. 若把「窗口几何」存到错误时机，还会污染数据：最大化时 `Size()` 是满屏值、最小化时 `Position()` 是 `-32000` 之类，直接落盘会导致下次还原尺寸/位置错乱；
4. 恢复的老坐标可能属于已拔掉的外接屏，`InitialPosition: WindowXY` 会把窗口放到不存在的显示器上。

**处置**（完整实现见 `architecture.md` §四·补）：

1. 落 `<appDataDir>/window.json`（dev/prod 自动隔离），字段 `width/height/x/y/hasPosition/maximised`；
2. 采集：`events.Common.{WindowDidResize,WindowDidMove,WindowMaximise,WindowUnMaximise}` → 700ms 防抖写盘；`WindowClosing` 里先停定时器再**同步**保存一次（销毁后 `Size()` 归零）；
3. 判定：`IsMinimised() || IsFullscreen()` 直接跳过；`IsMaximised()` 只翻 `maximised=true`，**不覆盖还原几何**；其余情况采集 `Size()`/`Position()`，小于 `MinWidth/MinHeight` 视为脏数据丢弃；
4. 恢复：`hasPosition` 才设 `InitialPosition: WindowXY`；最大化在 `win.Show()` **之后**调 `win.Maximise()`；
5. 兜底：`WindowShow` 钩子里用 `app.Screen.GetAll()` 的 `WorkArea`（DIP）判断窗口中心是否落在某块屏内，不在则 `win.Center()` 回写。

**验证**：

```powershell
go test ./internal/app/ -run WindowState -v   # 往返/无文件/脏 JSON/过小尺寸/无坐标
```

实机三步：移动+缩放 → 关窗 → 重启（尺寸位置一致）；最大化 → 关窗 → 重启（仍最大化，`window.json` 里还原尺寸未被写满屏）；还原（尺寸位置正确、`maximised` 翻回 false）。

**排障提示**：`window.json` 是纯人读 JSON，可直接看内容定位是「没写入」还是「写错值」；日志里出现「解析窗口状态失败」「保存窗口状态失败」「不在任何屏幕工作区内」即对应上述分支。
