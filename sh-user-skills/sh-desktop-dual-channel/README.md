---
name: sh-desktop-dual-channel
description: 桌面双通道应用脚手架（Go/Wails 与 Python/pywebview）：GUI 只开窗口、CLI 只跑终端，内嵌 WebUI、托盘常驻、关窗销毁重建、窗口几何记忆、dev/release 五维隔离与图标双通道。点名使用
version: 2.1.0
created: 2026-10-21
updated: 2026-10-25
disable-model-invocation: true
---

# sh-desktop-dual-channel：桌面双通道应用脚手架（Go/Wails + Python/pywebview）

> **定位**：把一个工具做成**两条通道、两份产物**——GUI 只开桌面壳（托盘 + 内嵌 HTTP/WebUI），CLI 只做终端子命令；dev / release 在产物名、版本号、数据目录、单实例、图标五个维度完全隔离。
> **硬约束**：GUI 不解析任何子命令，CLI 不开窗口；**禁止**用「单产物双模」把两者合成。
> **来源**：由 `sh-go-wails-desktop` 升级（2026-10-25 拆分 Go / Python 双模块，Go 正文零改写）。
> **验证锚点**：Go `go_projects/anatomymanager`（2026-10）；Python `python_projects/zedhub`（2026-10）。

---

## 一、模块分流（先读这里）

| 技术栈信号 | 模块 |
|---|---|
| Go / Wails v3 / go-winres / `.syso` / `-H windowsgui` / `-tags cli` | [`references/go-wails.md`](references/go-wails.md) |
| Python / pywebview / WebView2 / pystray / Nuitka / Typer / uv | [`references/python-webview.md`](references/python-webview.md) |
| TypeScript / Electron / Tauri | 暂无模块：按共同不变式自建，勿套用 Go/Python 细节 |

判定顺序：

1. 用户已明确技术栈 → 直接进对应模块；
2. 未明确 → 读项目清单（`go.mod` / `pyproject.toml`）后路由，或先问一句；
3. 两模块细节不可混用（go-winres ≠ Nuitka；Wails UniqueID ≠ OS 文件锁）。

## 二、跨语言共同不变式（两模块都必须满足）

1. **双通道产物**：GUI 与 CLI 各一个可执行文件，统一落 `bin/`；禁止单产物双模——GUI 子系统拿不到终端管道，会顶掉 prompt、`--json > out.json` 为空白。
2. **职责边界**：GUI 只开窗口（不解析子命令），CLI 只跑终端（不开窗口）。
3. **同一 Handler**：CLI `serve` 与 GUI 必须托管同一个 HTTP Handler（`/` 返回完整 WebUI，`/api/*` 返回 REST），禁止只起裸 API 端口。
4. **dev/prod 五维隔离**：产物名、版本号、数据目录（`%APPDATA%\language_projects\<app>\{dev,prod}`）、单实例标识、图标全部分离。
5. **窗口几何记忆**：`<dataDir>/window.json`，移动/缩放防抖保存；最大化只记标记、不覆盖还原尺寸；离屏坐标不写回。
6. **关窗销毁 + 托盘重建**：关闭窗口必须销毁 WebView（释放子进程内存），进程留托盘；托盘「显示窗口」按上次几何重建。
7. **无控制台可观测性**：日志与通道无关地落盘；GUI 无 stdout 也能排障。
8. **本地数据只写自有目录**：只落 `%APPDATA%\language_projects\<app>\`，绝不写入外部数据库 / 编辑器凭据目录。

## 三、模块地图

### Go / Wails v3

- 前置检查、适用范围、Step 1–9、反模式、验收与回滚 → `references/go-wails.md`
- 深度材料：`go-architecture.md`（蓝图 / `gui.go` / 几何）、`go-build-pipeline.md`（`build.py` / go-winres / 图标）、`go-troubleshooting.md`（白框 / 日志 / 门禁）

### Python / pywebview

- 运行时：前置检查、Step 1–12、差异、踩坑、测试与验收 → `references/python-webview.md`
- 打包：Nuitka 双产物、PE 图标/版本、五条实测坑 → `references/python-nuitka.md`
- 验证锚点：`python_projects/zedhub`

## 四、快速验收对照

| 验证项 | Go | Python |
|---|---|---|
| 双产物 | `bin/<app>-{gui,cli}[-dev].exe` | 同左（Nuitka） |
| GUI 子系统 | `-H windowsgui`，Subsystem=2 | `--windows-console-mode=disable` |
| CLI 子系统 | console，Subsystem=3 | `--windows-console-mode=force` |
| PE 版本 / 图标 | go-winres + `.syso` | Nuitka `--file-version` / `--windows-icon-from-ico` |
| 通道判定 | tag + 干净工作区 | 包版本干净号（hatch-vcs） |
| 单实例 | Wails UniqueID（dev 追加 `.dev`） | OS 文件锁（`gui.lock` / `daemon.lock`） |
| 关窗 | 销毁 WebviewWindow | 销毁 pywebview 窗口 + 二次 `start()` 重建 |

## 五、参考索引

| 文件 | 内容 |
|---|---|
| `references/go-wails.md` | Go / Wails 完整 SOP |
| `references/go-architecture.md` | Go 架构与实现细节 |
| `references/go-build-pipeline.md` | Go 构建脚本与图标 |
| `references/go-troubleshooting.md` | Go 排障 |
| `references/python-webview.md` | Python 运行时：壳 / 托盘 / 几何 / 通道 / 日志 / 内存 |
| `references/python-nuitka.md` | Python 打包：Nuitka 双产物 / PE / 实测坑 |
