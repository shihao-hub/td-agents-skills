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

3. **绿色单二进制不要声明未注册的 AppUserModelID**
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

## 3. `-H windowsgui` 下 CLI 无输出 / 无法排障

### 3.1 标准流被丢弃 → AttachConsole

`cmd/<app>/console_windows.go`（必须在 main 包 `init()` 最早时机）：

```go
//go:build windows

package main

import (
	"os"

	"golang.org/x/sys/windows"
)

func init() {
	k := windows.NewLazySystemDLL("kernel32.dll")
	// ATTACH_PARENT_PROCESS = (DWORD)-1 = 0xFFFFFFFF
	r, _, _ := k.NewProc("AttachConsole").Call(uintptr(^uint32(0)))
	if r == 0 {
		return
	}
	hOut, err := windows.GetStdHandle(windows.STD_OUTPUT_HANDLE)
	if err == nil && hOut != 0 && hOut != windows.InvalidHandle {
		os.Stdout = os.NewFile(uintptr(hOut), "/dev/stdout")
	}
	hErr, err := windows.GetStdHandle(windows.STD_ERROR_HANDLE)
	if err == nil && hErr != 0 && hErr != windows.InvalidHandle {
		os.Stderr = os.NewFile(uintptr(hErr), "/dev/stderr")
	}
}
```

**验证**：`.\<app>-dev.exe version | Out-String` 能回显；从 Explorer 双击仍无黑框（因为未附着到父控制台）。

### 3.2 无控制台时看日志 → 滚动双写

`internal/app/log.go` 把每条日志同时写 `os.Stderr` 与 `<appDataDir>/<app>.log`：

```go
var (
	logOnce sync.Once
	logFile *os.File
)

func logf(format string, args ...any) {
	line := fmt.Sprintf("%s %s\n", time.Now().Format("2006-01-02 15:04:05"), fmt.Sprintf(format, args...))
	_, _ = fmt.Fprint(os.Stderr, line)

	logOnce.Do(func() {
		base := appDataDir()
		if base == "" {
			return
		}
		if err := os.MkdirAll(base, 0o755); err != nil {
			return
		}
		f, err := os.OpenFile(filepath.Join(base, "your_app.log"), os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o644)
		if err == nil {
			logFile = f
		}
	})
	if logFile != nil {
		_, _ = logFile.WriteString(line)
	}
}
```

排障路径：`%APPDATA%\language_projects\<app>\<dev|prod>\<app>.log`。GUI 启动失败、单实例创建失败、自启被拒都会留下记录。

### 3.3 前端白屏 / 交互异常

- 确认内置 HTTP 服务已监听（`net.Listen` 失败会回退随机端口，日志里有实际 URL）。
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
- **工作区脏**：生成物未进 `.gitignore`（`icon.ico`、`.syso`、`*.exe`）会永远判脏。
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
| `rsrc.exe` 找不到 | `%GOPATH%\bin` 不在 PATH | `go install github.com/akavel/rsrc@latest` 后补 PATH |
