---
name: sh-vscode-gitlg-panel
description: 配置：VS Code 底部面板 Git 提交图（GitLG/IDEA体验）与分支颜色调优。点名使用
---

# VS Code 底部面板 Git 提交图配置手册（GitLG）

用于在 VS Code 中配置类似 IntelliJ IDEA 的 Git Log 底部工具窗体验：图形化提交树常驻底栏、随时按 `Ctrl + J` 一键展开/隐藏、点击文件改动直接在上方编辑区对比 Diff 且不跳走覆盖。

## 一、方案选型与避坑背景

| 方案 | 限制 / 缺陷 | 是否推荐 |
|---|---|---|
| **原版 Git Graph** (`mhutchie.git-graph`) | 停更于 2021 年；底层写死为 `WebviewPanel`（普通标签页），无法拖入底栏 Panel；查看 Diff 会跳走覆盖标签页。 | ❌ |
| **GitLens Commit Graph** | 商业化严重，提示登录/Pro 付费；体积庞大臃肿，搜索 Commit 隐蔽不直观。 | ❌ |
| **VS Code 原生提交图** | 仅为简陋折叠树，无彩色分支拓扑线，无独立作者/时间列，改动文件塞在节点下。 | ❌ |
| **GitLG (`phil294.git-log--graph`)** | 支持通过 `"git-log--graph.position": "view"` 转为原生面板视图；支持拖入底部 Panel；无广告、带搜索。 | ✅ **首选方案** |

> **注意**：GitLG 原作者默认将 `main`/`master` 分支硬编码为刺眼的警示红（`#ff3333`），需配置覆盖为经典蓝色。

## 二、落地 SOP（一键配置）

### 1. 安装扩展
在 VS Code 扩展市场搜索并安装：
* `GitLG`（ID: `phil294.git-log--graph`）

或通过终端安装：
```powershell
code --install-extension phil294.git-log--graph
```

### 2. 写入用户配置（`settings.json`）
修改全局设置文件 `C:\Users\<User>\AppData\Roaming\Code\User\settings.json`（或按 `Ctrl + ,` 搜索配置）：

```json
{
  // 1. 将 GitLG 从默认全屏 Editor 切换为独立视图，允许拖入底部面板/侧边栏
  "git-log--graph.position": "view",

  // 2. 覆盖默认的刺眼红色主分支，改成舒适的海蓝色/VS Code 蓝
  "git-log--graph.branch-color-custom-mapping": {
    "main": "#007acc",
    "master": "#007acc",
    "develop": "#388e3c",
    "dev": "#388e3c"
  },

  // 3. 详情面板位置（可选：right 或 bottom，右侧更贴合 IDEA 体验）
  "git-log--graph.details-panel-position": "right"
}
```

### 3. 重载并拖拽到底部面板（关键操作）
1. 修改 `"git-log--graph.position": "view"` 后**必须重载窗口**：
   * 快捷键 `Ctrl + Shift + P` -> 运行 `Developer: Reload Window`（开发人员: 重载窗口）。
2. 打开左侧活动栏的 **「源代码管理」(`Ctrl + Shift + G`)**。
3. 找到出现的 **「GitLG」** 面板。
4. **按住「GitLG」标题栏，直接拖拽到底部的面板栏（与“终端”、“输出”并排）松开**。

## 三、日常工作流体验（对比 IDEA）

* **随叫随到**：按 **`Ctrl + J`**（或点击面板最小化按钮）即可一键隐藏/唤出 Git 提交树，不需要时完全不占屏幕。
* **Diff 联动**：在底部的 GitLG 中点击任意提交或右侧变更文件，对比 Diff 自动在**上方主代码区**打开，底部提交树常驻不跳切。
* **分支搜索**：顶部自带分支切换框与检索框（可直接搜 Commit Message、Author 或 Hash），回车即定位。
* **布局记忆**：只要不点击标签页上的 `X` 关闭它，VS Code 会永久记住底栏停靠位置，重启 IDE 无需重新排版。

## 四、排障速查

* **改了 `position: view` 后找不到面板**：检查是否执行了 `Reload Window`；未重载前 VS Code 尚未注册新 View。
* **分支依然显示红色**：在 GitLG 面板右上角点击刷新按钮 🔄，或检查 `settings.json` 中的 `branch-color-custom-mapping` 拼写与合法颜色值。
* **底栏高度过窄**：鼠标悬停在底栏面板上边框处，拖动向上扩宽高度即可。