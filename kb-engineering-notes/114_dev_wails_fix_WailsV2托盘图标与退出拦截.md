---
name: kb-wails-v2-tray-icon-and-quit
description: 仅用于既有 Go + Wails v2 托盘应用的图标、退出拦截与左右键故障排查；不作为新项目选型依据。新 Go GUI 使用统一结构入口中的 Wails v3 双通道方案。
version: 1.0.1
created: 2026-11-18
updated: 2026-11-18
id: "114"
domain: dev
scope: wails
type: fix
slug: "WailsV2托盘图标与退出拦截三坑"
status: verified
last_verified: "2026-11-18"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: true
---

# 114-Wails v2 托盘应用三坑：图标空白、退出失效、左键弹菜单

> 适用：Go + Wails v2 自建窗口/托盘应用，且**不用 `wails build`**（自己 `go build` + go-winres）。
> **存量排障边界**：先确认目标项目已使用 Wails v2，再应用本文；新 Go GUI 先读父仓《[Go 项目统一结构](../../../docs/projects/go_projects/Go 项目统一结构.md)》及 [Go SOP](../sh-user-skills/sh-desktop-dual-channel/references/go-wails.md)，默认 Wails v3。本文的 verified 仅表示 v2 故障结论，不表示推荐 v2 新选型；本次只补充资料边界，未重新实测运行时。
> 三个坑互不相关，但会在同一次交付里同时出现，且都能被"看着像正常"掩盖。

## 一、标题栏图标是空白方块

### 现象

exe 右键属性里有正确图标、任务栏也正常，但**窗口标题栏左上角是空白方块**（或系统默认的"窗口框"图标）。

### 根因

窗口图标不会自动继承 exe 资源。Wails v2 的流程是：

1. 注册窗口类时先兜底：`internal/platform/win32/window.go:39` 用 `LoadIconWithResourceID(instance, IDI_APPLICATION)`——`IDI_APPLICATION` 就是那个空白窗口图标；
2. 创建窗口后再换掉：`internal/frontend/desktop/windows/window.go:96`

```go
if ico, err := winc.NewIconFromResource(winc.GetAppInstance(), uint16(winc.AppIconID)); err == nil {
    result.SetIcon(0, ico)
}
```

3. `AppIconID` 在 `internal/frontend/desktop/windows/winc/app.go` 里写死：

```go
// resource compilation tool assigns app.ico ID of 3
AppIconID = 3
```

**所以 Wails 只找资源 ID = 3 的 `RT_GROUP_ICON`。** 若资源名是字符串（go-winres 模板里常见的 `"APP"`），`LoadIconWithResourceID(3)` 必然失败，错误被 `err == nil` 吞掉，窗口保持 `IDI_APPLICATION` → 白块。

`wails build` 构建的项目不会遇到，因为它的资源编译流程天然产出 ID 3。

### 修法

go-winres 的 JSON 模板里，**数字资源 ID 必须写成 `"#n"`**（与 `RT_VERSION` 的 `"#1"` 同一语法）：

```json
"RT_GROUP_ICON": {
  "#3": { "0000": "__ICON__" }
}
```

写成 `"3"` 无效（会被当成字符串名），写成 `"APP"` 也无效。

### 验证

```powershell
# 返回非零即已设置（0 = 仍是空白图标）
Add-Type @"
using System; using System.Runtime.InteropServices;
public class WI { [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, IntPtr l); }
"@
$h = (Get-Process <exe名> | ? { $_.MainWindowHandle -ne 0 }).MainWindowHandle
[WI]::SendMessage($h, 0x007F, [IntPtr]0, [IntPtr]0)   # WM_GETICON / ICON_SMALL
```

## 二、图标背景是白色方块

### 现象

图标显示了，但外面一圈白底，在深色标题栏/托盘上像贴了张白纸。

### 根因

图标文件本身是**白底不透明**（如仓库里 `go-default.ico` 的 16×16 角落像素为 `(255,255,255,255)`）。Windows 不会替你抠背景。

### 修法

GUI 项目应使用专属的**透明底**多尺寸 ico，用脚本生成而非借用默认图标：

```python
# 关键：RGBA 透明画布 + 多尺寸
im = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
im.save("icon.ico", format="ICO", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
```

验收：`Image.open("icon.ico").convert("RGBA").getpixel((0,0))[3] == 0`。

## 三、托盘「退出」点了没反应

### 现象

托盘菜单点「退出」，菜单消失但进程还在，窗口也没关。

### 根因

`internal/frontend/desktop/windows/frontend.go:459`：

```go
func (f *Frontend) Quit() {
    if f.frontendOptions.OnBeforeClose != nil && f.frontendOptions.OnBeforeClose(f.ctx) {
        return              // 返回 true = 取消退出
    }
    f.mainWindow.Invoke(winc.Exit)
}
```

而「关窗收进托盘」的常见写法是：

```go
OnBeforeClose: func(ctx context.Context) bool {
    runtime.WindowHide(ctx)
    return true             // 无条件拦截
}
```

于是 `runtime.Quit(ctx)` 也走同一个回调 → 被拦 → 什么都不会发生。

### 修法

用原子标志区分「关窗」与「退出」：

```go
type guiApp struct {
    ctx      context.Context
    quitting atomic.Bool
}

func (a *guiApp) beforeClose(ctx context.Context) bool {
    if a.quitting.Load() {
        return false        // 放行，Quit 才能继续 winc.Exit
    }
    runtime.WindowHide(ctx) // 普通关窗 = 收进托盘
    return true
}

func (a *guiApp) quitApp() {
    a.quitting.Store(true)
    runtime.Quit(a.ctx)
}
```

> 同款缺陷在归档项目 `file-sync-native`（Wails v2 + systray）中也存在，属照抄先例时的常见继承坑。

### 验证

临时加自检钩子（验证后删除）：启动 4 秒后调用 `quitApp()`，观察进程是否退出。或直接人工点托盘退出。

## 四、左键单击弹菜单而不是开窗

### 现象

Windows 惯例是「左键单击开窗口、右键弹菜单」，实际左右键都弹菜单，双击也不行。

### 根因

`getlantern/systray` 把两个键合并处理（`systray_windows.go:280`）：

```go
case WM_RBUTTONUP, WM_LBUTTONUP:
    t.showMenu()
```

库本身不提供区分回调，配置改不了。

### 修法

换用 `fyne.io/systray`（同一 fork 线的继任者），它区分左右键（`systray.go:162`）：

```go
import "fyne.io/systray"

systray.SetOnTapped(func() { a.showWindow() })   // 左键：开窗
// 不注册 SetOnSecondaryTapped → 右键保留默认菜单
```

### 验证（无需人工点击）

向托盘隐藏窗口发送消息即可模拟左键：

```powershell
$tray = [WinFind]::FindWindow("SystrayClass", $null)
[WinFind]::SendMessage($tray, 0x0401, [IntPtr]0, [IntPtr]0x0202)  # WM_USER+1, lParam=WM_LBUTTONUP
```

先发 `WM_CLOSE(0x0010)` 把窗口收进托盘（`IsWindowVisible=False`），再发上面这条，应变回 `True`。**不要模拟右键**：`TrackPopupMenu` 会阻塞消息循环直到菜单关闭。

## 五、给这类项目的交付清单

- [ ] `winres/*.json` 的图标键是 `"#3"`，`WM_GETICON` 非零；
- [ ] 图标为透明底专属图标，非 `go-default.ico`；
- [ ] `OnBeforeClose` 有 `quitting` 标志，托盘退出能真正结束进程；
- [ ] 托盘左键开窗、右键菜单（用 `fyne.io/systray` 的 `SetOnTapped`）；
- [ ] 单实例锁的 `UniqueId` 区分 dev/prod，避免两版互相顶掉；
- [ ] 关窗行为（隐藏 vs 退出）与用户预期一致，并在 README 写明。

## 六、方法论教训

- **归档项目只能当线索，不能当正确性背书**：`file-sync-native` 的结构可抄，但它自身带着「退出失效」缺陷；`clictl` 的 winres 模板是 Wails **v3** 的，v3 靠 `SetWindowIcon` 手工设图标，`"APP"` 键对 v2 就是错的。跨版本/跨状态照搬先例前，先用框架源码核对关键常量。
- **框架行为必须读源码确认**：`AppIconID = 3`、`Quit` 先问 `OnBeforeClose`、`WM_LBUTTONUP` 与 `WM_RBUTTONUP` 合并——这三处都在依赖源码里一目了然，但只看现象会得出错误结论（如"go build 不继承图标"）。
