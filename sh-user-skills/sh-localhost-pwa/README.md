---
name: sh-localhost-pwa
description: 本地 Web/CLI 服务改造为 Chrome/Edge 独立应用窗口（--app 模式）与 PWA 规范面板。点名使用
version: 1.0.0
created: 2026-10-07
updated: 2026-10-07
---

# sh-localhost-pwa：本地服务桌面应用化 SOP

把本地运行的 Web/CLI 服务（如 Python FastAPI / Starlette / Flask、Go、Node 等），以**零重型 GUI 依赖（无需 Electron/PyQt）**的方式改造成具备**原生桌面体验的独立应用面板**。

核心基于两项技术组合：
1. **Chromium SSB（`--app` 模式）**：无地址栏、无书签栏、独立任务栏分组、记忆窗口尺寸。
2. **Web App Manifest（PWA 规范）**：声明应用名称、独立主题色与 SVG 专属图标，浏览器地址栏支持一键安装至桌面。

---

## 落地三步走 SOP

### Step 1: 补齐 PWA 极简双文件（静态资源目录）

在 WebUI 静态根目录下放置 `manifest.json` 与 `icon.svg`：

#### 1. `manifest.json` 模板
```json
{
  "name": "应用完整名称",
  "short_name": "面板简称",
  "description": "应用一句话功能说明",
  "start_url": "/ui",
  "scope": "/ui",
  "display": "standalone",
  "background_color": "#18181b",
  "theme_color": "#18181b",
  "icons": [
    {
      "src": "/ui/icon.svg",
      "sizes": "any",
      "type": "image/svg+xml"
    }
  ]
}
```
*注：`display: "standalone"` 是使浏览器以独立应用呈现的关键配置。*

#### 2. `icon.svg` 规范建议
- 采用深色或品牌色圆角背景外框（如 `rx="108"`），内部结合渐变色几何符号或品牌字；
- 避免使用外部引用的网络字体，全部使用矢量路径（`<path>` / `<circle>` / `<rect>`）；
- 浏览器“安装应用”时会自动将 SVG 转为 Windows 原生 `.ico` 桌面图标。

#### 3. HTML 头部引入（`index.html`）
```html
<link rel="icon" type="image/svg+xml" href="/ui/icon.svg">
<link rel="manifest" href="/ui/manifest.json">
<meta name="theme-color" content="#18181b">
```

---

### Step 2: 服务端静态资源白名单放行

确保后端 HTTP 服务允许读取 `.json` 与 `.svg` 静态后缀：
- **安全检查**：限制在本地回环（`127.0.0.1` / `localhost`）且限制访问目录，防止路径穿越；
- **开发期缓存**：WebUI 静态文件建议返回 `Cache-Control: no-store`，改动即时生效。

---

### Step 3: CLI 增加 `--app` 模式与探针回退

为 CLI 工具的 `ui` 命令增加 `--app` 选项，核心代码逻辑：

```python
def _launch_app_window(url: str) -> bool:
    """自动探测 Chrome / Edge 并以独立应用窗口 (--app) 启动。"""
    import os, shutil, subprocess

    # 1. 优先检查 PATH 中的环境变量
    candidates = ["chrome", "google-chrome", "google-chrome-stable", "chromium", "msedge", "microsoft-edge"]
    for c in candidates:
        found = shutil.which(c)
        if found:
            try:
                subprocess.Popen([found, f"--app={url}"])
                return True
            except OSError:
                continue

    # 2. Windows 常见物理安装路径探测
    win_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for p in win_paths:
        if os.path.isfile(p):
            try:
                subprocess.Popen([p, f"--app={url}"])
                return True
            except OSError:
                continue

    # 3. macOS 路径探测
    mac_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ]
    for p in mac_paths:
        if os.path.isfile(p):
            try:
                subprocess.Popen([p, f"--app={url}"])
                return True
            except OSError:
                continue

    return False
```

---

## 核心体验防线：避免“白屏断层”

> [!IMPORTANT] 生命周期闭环
> - **纯 PWA 桌面图标的缺陷**：用户双击桌面图标时，只启动 Chrome 访问 URL，若后台未启动，会出现 `ERR_CONNECTION_REFUSED`。
> - **CLI `--app` 的闭环优势**：在调起浏览器窗口前，CLI 必须先执行 `ensure_connected()`：
>   1. 检查后台 daemon 是否活着；
>   2. 若未运行，自动在后台静默拉起 daemon（detach 子进程）；
>   3. 服务就绪后再唤出 Chrome/Edge `--app` 窗口。

---

## 桌面一键直达方案（可选）

为用户提供直接双击的 Windows 快捷入口（零黑框静默运行）：
- **通过快捷方式**：创建指向 `wt.exe -w 0 <tool> ui --app` 或后台拉起命令。
- **通过静默 VBS 脚本**：
  ```vbscript
  Set WshShell = CreateObject("WScript.Shell")
  WshShell.Run "cmd /c <tool> ui --app", 0, False
  ```
  该 VBS 可直接设置图标并放置在桌面或固定在任务栏。

---

## 验收检查清单

1. [ ] 访问 `/ui` 时，网络面板确认 `manifest.json` 与 `icon.svg` 响应 200；
2. [ ] Chrome / Edge 访问页面，地址栏右侧正确显示「安装应用」图标；
3. [ ] 终端执行 `<tool> ui --app`，弹出的窗口无 URL 地址栏、无标签页，具备独立任务栏图标；
4. [ ] 关闭 Chrome 后，再次执行 `<tool> ui --app`，能正确记住上次窗口的尺寸与屏幕位置。
