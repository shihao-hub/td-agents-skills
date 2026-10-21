---
name: sh-go-wails-desktop
description: Go 单二进制桌面应用脚手架：CLI+WebUI+Wails v3 托盘、dev/release 通道隔离、PE 图标双通道与无控制台排障。点名使用
version: 1.2.0
created: 2026-10-21
updated: 2026-10-21
disable-model-invocation: true
---

# sh-go-wails-desktop：Go 单二进制桌面应用脚手架与通道隔离

> **定位**：把一个 Go 工具同时做成「终端 CLI + 内嵌 HTTP/WebUI + Wails v3 托盘桌面」，并让 dev / release 两个通道在产物名、版本号、数据目录、单实例 ID、图标五个维度完全隔离。
> **来源**：由知识库条目 `kb-engineering-notes/082` 转正（原条目保留为 deprecated 存根，历史排障细节可回溯）。
> **验证锚点**：Windows 11 24H2、Go 1.26、Wails v3.0.0-beta.33、Edge WebView2；实机项目 `go_projects/anatomymanager`（2026-10-21 全链路实测）。
> **深度材料**：
> - `references/architecture.md`：四位一体蓝图、目录树、PE 清单与版本元数据、`gui.go` 全文
> - `references/build-pipeline.md`：构建脚本全文、通道隔离五件套、图标双通道
> - `references/troubleshooting.md`：任务栏白框、无控制台日志、门禁拒绝等排障

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
cmd/<app>/          main.go / console_windows.go / rsrc_windows_amd64.syso(生成物)
internal/api        HTTP REST
internal/app        gui.go / autostart.go / version.go / datadir.go / icon_*.go / log.go
internal/storage    SQLite（或你的持久层）
internal/web        //go:embed 前端资产
scripts/            render_icon.py / build.py
根目录              icon.png / icon.ico / icon_dev 静态资产 / info.json / wails.exe.manifest
```

**校验**：`go build ./cmd/<app>` 通过（尚无资源段时使用系统默认图标属正常）。

### Step 2 入口分流（`main.go`）

```go
if len(os.Args) < 2 {                       // 双击：GUI（port=0 → 动态探测可用端口）
    _ = app.LaunchGUI("", 0, false)
    return
}
if os.Args[1] == "--hidden" {               // 开机自启：静默托盘
    _ = app.LaunchGUI("", 0, true)
    return
}
switch os.Args[1] { /* ingest / list / get / export / serve / schema / version */ }
```

**校验**：`.\<app>-dev.exe version` 回显 `vX.Y.Z-dev (mode: development, build: dev)` 后立即退出。

### Step 3 控制台附着（`console_windows.go`）

`-H windowsgui` 构建下标准流被丢弃，必须在 `init()` 里 `AttachConsole(ATTACH_PARENT_PROCESS)` 并重新绑定 `os.Stdout` / `os.Stderr`。全文见 `references/troubleshooting.md` §3。

**校验**：`.\<app>-dev.exe version | Out-String` 在 PowerShell 中能看到输出。

### Step 4 桌面壳（`gui.go`）

托盘常驻、单实例、窗口关闭销毁 + 双击重建、任务栏图标在 HWND 就绪后绑定。完整实现见 `references/architecture.md`。关键点：

- `DisableQuitOnLastWindowClosed: true` 保持托盘常驻；
- dev 的 `SingleInstanceOptions.UniqueID` 必须追加 `.dev`，否则与常驻正式版互斥；
- 关闭窗口放行 `WindowClosing`，延时 `runtime.GC()` + `debug.FreeOSMemory()`；
- **端口默认 `port=0` 动态探测**，不要写死固定端口（如 8765）：GUI 必须先 `net.Listen` 拿到真实端口才能构造窗口 `URL:`，CLI `serve` 则绑定后阻塞；两处共用同一个绑定函数，杜绝「以为的端口」与「实际端口」两份真相。实际 URL 必须走 `logf`（`-H windowsgui` 下 stdout 不可见），固定端口仅作为可选参数保留。

**校验**：dev 与 release 可同时运行且互不唤醒。

### Step 5 图标资产（release 专属 + dev 地鼠）

`render_icon.py` 生成 1024 PNG 与 256/128/64/48/32/24/16 全尺寸 ICO，并同步 `internal/app/icon.ico`；把 `go-default.ico` 复制为 `internal/app/icon_dev.ico`。脚本全文见 `references/build-pipeline.md`。

**校验**：`gofmt -l internal/app` 无输出（`//go:embed` 前需空 `//` 注释行）。

### Step 6 构建脚本（`build.py`）

按 `references/build-pipeline.md` 落地。判定规则：

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
uv run scripts/build.py            # dev     → <app>-dev.exe  vX.Y.Z-dev[-dirty]
git tag <project>/v1.0.0
uv run scripts/build.py --release  # release → <app>.exe      vX.Y.Z
git status --porcelain             # 必须为空：构建不得弄脏工作区
```

按下节验收表逐项确认；发布后如需继续开发，新提交自然回到 dev 通道。

---

## 三、常见踩坑与回滚

| 症状 | 根因 | 处置 |
|---|---|---|
| 任务栏 / 资源管理器图标是白框 | `.syso` 未放在 `cmd/<app>/`；manifest 非 4 段；乱设 AppUserModelID | `references/troubleshooting.md` §1 |
| 双击无窗口、托盘也不出现 | WebView2 运行时缺失；启动参数冲突 | 装 Evergreen Runtime；看 `logf` 落盘日志 |
| CLI 在 PowerShell 无输出 | `-H windowsgui` 丢弃标准流 | 补 `AttachConsole`（§3） |
| `--release` 总被拒 | tag 前缀不匹配；工作区脏（生成物未入 ignore） | 查 `git tag --points-at HEAD` 与 `.gitignore` |
| dev 与正式版互相挤掉 | 单实例 ID 未隔离 | dev `UniqueID` 追加 `.dev` |
| `go:embed` 资产被忽略 | `.gitignore` 写成 `icon.ico` | 改为 `/icon.ico`，用 `git check-ignore -v` 复核 |
| `gofmt -l` 一直报图标文件 | doc comment 与 `//go:embed` 间缺空 `//` 行 | 补一行 `//` |
| 并发写报 `database is locked (SQLITE_BUSY)` | 裸 DSN：`busy_timeout=0` + rollback journal | 统一 DSN 加 `busy_timeout`/WAL（Step 7、troubleshooting §8） |

**回滚**：

```powershell
Remove-Item .\<app>-dev.exe -ErrorAction SilentlyContinue   # 只删产物，不动源码
git tag -d <project>/vX.Y.Z                                # 误打 tag（远端已 push 需单独处理）
```

数据目录回滚：删除 `%APPDATA%\language_projects\<app>\{dev,prod}` 不影响旧库（迁移只复制不删除）。

---

## 四、交付验收清单

| 验证项 | 操作 | 预期 |
|---|---|---|
| 双击零黑框 | 资源管理器双击 | 无 CMD 闪窗；托盘就绪 |
| 任务栏图标 | 观察运行图标 | 专属图标，无白框 |
| CLI 回显 | `.\<app>.exe version \| Out-String` | 版本 + 通道正确后秒退 |
| dev 图标 | 看文件管理器 | Go 地鼠；release 为专属图标 |
| release 门禁 | 无 tag / 脏工作区执行 `--release` | 退出码 2，不产正式名 |
| 通道数据隔离 | dev 与 release 各跑一次 | 分别落 `dev` / `prod` 目录 |
| 并发写不冲突 | 并行两个 `ingest`，其间请求 `/api/artworks` | 两条都 success，API 200 |
| 单实例隔离 | 两者同时运行 | 互不唤醒、可并存 |
| 端口零冲突 | dev 与 release 同时启动看日志 URL | 各自不同动态端口，互不串台 |
| 自启门禁 | dev 勾选自启 | 菜单置灰 + 注册表无写入 |
| 关窗释放 | 关窗后看任务管理器 | WebView2 子进程退出，内存回落 |
| 构建幂等 | 连续两次 release 后 `git status` | 输出为空 |

---

## 五、参考索引

| 文件 | 内容 |
|---|---|
| `references/architecture.md` | 四位一体蓝图、目录树、manifest/info.json、`gui.go` 全文、生命周期 |
| `references/build-pipeline.md` | 通道隔离五件套与铁律、图标双通道、`render_icon.py` / `build.py` 全文 |
| `references/troubleshooting.md` | PE 图标三铁律、HWND 时序、无控制台日志、门禁与迁移排障 |
| `kb-engineering-notes/082_...md` | 原知识库条目（deprecated 存根，保留检索入口） |
