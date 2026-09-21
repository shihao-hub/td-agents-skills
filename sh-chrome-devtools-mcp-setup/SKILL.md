---
name: sh-chrome-devtools-mcp-setup
description: 装机：opencode 配置 chrome-devtools-mcp 浏览器控制。点名使用
---

# Chrome DevTools MCP 配置（opencode）

给 opencode 接入 Google 官方的 `chrome-devtools-mcp`，让 AI 原生拥有浏览器控制工具。核心认知：**不需要手写 puppeteer/CDP 脚本**——MCP 服务器已经把 Chrome DevTools Protocol 封装成了现成工具，配置只是往 opencode.json 里加一段。

## 新电脑四步流程

1. **Node.js**（含 npx）：装 LTS 版即可，验证 `node -v`。npx 是运行 MCP 服务器的载体
2. **Chrome**：普通安装即可（stable/beta/canary 都行）。MCP 会自动定位系统里的 Chrome，不会下载浏览器、不碰用户日常使用的 profile
3. **写配置**：编辑全局配置 `~/.config/opencode/opencode.json`（Windows 即 `%USERPROFILE%\.config\opencode\opencode.json`），在 `mcp` 对象里加入：

```json
"chrome-devtools": {
  "type": "local",
  "command": ["npx", "-y", "chrome-devtools-mcp@latest"],
  "enabled": true
}
```

   也可以直接运行本技能自带的脚本（幂等，可重复执行）：
   `powershell -File <skill目录>/scripts/setup-chrome-devtools-mcp.ps1`
   脚本会检查 node/Chrome、自动写入或跳过已存在的配置、写前备份、写后校验 JSON。
4. **重启 opencode**：配置只在启动时加载，不热更新。重启后首次使用浏览器工具时，npx 会自动下载 chrome-devtools-mcp（几秒到几十秒，仅一次），然后拉起一个专属 Chrome 窗口

## 常用启动选项（写进 command 数组即可）

| 需求 | 追加参数 |
|---|---|
| 无头模式（不弹窗口） | `--headless` |
| 一次性临时 profile（用完即删） | `--isolated` |
| 附加到已运行的 Chrome | `--browserUrl http://127.0.0.1:9222`（该 Chrome 需带 `--remote-debugging-port=9222` 启动） |
| 换 Chrome 通道 | `--channel canary`（或 beta/dev/stable） |
| 指定初始窗口大小 | `--viewport 1280x720` |

默认行为：有界面窗口、独立 profile（位于 `~/.cache/chrome-devtools-mcp/chrome-profile`）。日常给用户演示自动化，默认即可；跑批量任务可加 `--headless`。

## 排障速查

- **重启后没有浏览器工具**：先在终端跑 `npx -y chrome-devtools-mcp@latest --help` 能打印帮助就说明包和网络没问题，再看 opencode.json 的 JSON 是否合法（opencode 对配置严格校验，非法直接拒绝启动）
- **JSON 写坏了导致 opencode 起不来**：临时用环境变量 `OPENCODE_DISABLE_PROJECT_CONFIG=1` 启动后修复文件
- **npx 下载慢/失败**：是首次下载包，检查网络代理即可，与 Chrome 无关
- **命令数组**：`command` 必须是字符串数组（`["npx", "-y", "chrome-devtools-mcp@latest"]`），`type` 必填——这是 opencode 的硬性格式要求

## 为什么不手写脚本

CDP 是 WebSocket 协议，终端里没法直接发命令；手搓 puppeteer 驱动脚本（launch.js/drive.js 那套）是一次性胶水，功能、稳定性、维护成本全面劣于官方 MCP（后者还带 DOM 快照、网络监听、性能追踪、设备模拟）。遇到"AI 操作浏览器"需求，正确姿势永远是配 MCP，不是写脚本。
