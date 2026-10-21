---
name: kb-localhost-pwa-standalone
description: 本地 Web/CLI 服务桌面应用化改造流水线：利用 Chromium SSB（--app 模式）与 PWA 规范（manifest.json/icon.svg），实现零 Electron/PyQt 依赖的原生独立窗口面板与启动器 SOP。改造本地服务为桌面应用时查阅。
---

# 本地服务桌面应用化与 PWA 独立窗口改造流水线

> 本条目沉淀自将本地运行的 Web/CLI 服务（如 Python FastAPI / Flask / Streamlit、Go WebUI、Node 等）改造成具备原生桌面体验独立面板的工程方案。

---

## 一、业务场景与架构优势

当开发者为本地工具构建了 Web 界面时，常规用浏览器标签页访问存在三大痛点：
1. 容易混杂在海量网页标签中被误关；
2. 存在顶部地址栏、书签栏干扰，缺乏沉浸式应用质感；
3. 引入 Electron 或 PyQt/PySide 导致打包体积暴增（动辄 100MB+）且资源占用巨大。

**本方案技术组合**：
- **Chromium SSB（Site-Specific Browser / `--app` 模式）**：无地址栏、无书签栏、独立任务栏分组、自动记忆窗口尺寸；
- **Web App Manifest（PWA 规范）**：声明独立主题色、名称与矢量图标，支持浏览器一键“安装到桌面”生成独立快捷方式。

---

## 二、标准落地三步走 SOP

### Step 1: 补齐 PWA 极简双文件（静态资源根目录）

在 WebUI 的静态目录中放置 `manifest.json` 与 `icon.svg`：

#### 1. `manifest.json` 配置模板
```json
{
  "name": "本地管理控制台",
  "short_name": "控制台",
  "description": "本地高性能工程控制面板",
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
*注：`display: "standalone"` 是使浏览器以独立沉浸窗口呈现的核心字段。*

#### 2. `icon.svg` 设计规范
- 采用深色或品牌色圆角背景外框（如 `rx="108"`），内部包含清晰的几何矢量路径（`<path>` / `<circle>`）；
- 避免引用任何外部网络字体，全部使用纯矢量路径；
- Chromium 内核安装应用时会自动将 SVG 光栅化为 Windows 原生 `.ico`。

#### 3. HTML 头部注入（`index.html`）
```html
<link rel="icon" type="image/svg+xml" href="/ui/icon.svg">
<link rel="manifest" href="/ui/manifest.json">
<meta name="theme-color" content="#18181b">
```

---

## 三、原生快捷方式与启动脚本设计

在 CLI 或应用启动完成后，通过终端或桌面快捷方式拉起无头独立窗口：

### 1. 跨平台 Chromium 探测与拉起逻辑（PowerShell / Python）
```powershell
# 寻找本机 Chromium 内核浏览器（Chrome 优先，Edge 兜底）
$browserPath = $null
$candidates = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles(x86)\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles(x86)\Microsoft\Edge\Application\msedge.exe"
)
foreach ($c in $candidates) {
    if (Test-Path $c) { $browserPath = $c; break }
}

if ($browserPath) {
    # 以 --app 模式拉起独立窗口，指定窗口宽高与独立隔离 profile（可选）
    Start-Process -FilePath $browserPath -ArgumentList @(
        "--app=http://localhost:8000/ui",
        "--window-size=1200,800"
    )
} else {
    # 兜底直接用系统默认程序打开 URL
    Start-Process "http://localhost:8000/ui"
}
```

---

## 四、交付验证与收益断言

1. **界面检查**：启动后弹出的窗口**无浏览器地址栏、无前进后退导航按钮、无书签栏**；
2. **任务栏表现**：在 Windows 任务栏中拥有**独立的分组图标**，不与常规浏览器的标签页窗口折叠合并；
3. **资源占用**：复用操作系统已安装的 Chrome/Edge 内核，额外常驻内存极低（仅数十 MB 渲染进程开销），零安装包体积包袱。
