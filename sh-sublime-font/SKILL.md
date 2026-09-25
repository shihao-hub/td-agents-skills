---
name: sh-sublime-font
description: 装机/配置：YaHei Consolas Hybrid 字体下载安装，Sublime Text/Merge 字体配置及 UI 补丁。点名使用
---

# sh-sublime-font — Sublime Text / Merge 字体管理与 UI 字体补丁

自动化完成 **YaHei Consolas Hybrid**（微软雅黑 + Consolas 合成等宽字体）在 Windows 上的下载安装，以及 **Sublime Text** 和 **Sublime Merge**（含 Diff 区域、提交历史 Commits、变更文件 Files 及全部界面控件）的字体与字号统一配置。

---

## 核心原则与铁律

1. **字号硬性推荐 13 磅（`"font_size": 13`）**：
   - Sublime Text 与 Sublime Merge **必须统一配置为 13**。
   - YaHei Consolas Hybrid 是点阵与矢量融合字体，**字号低于 13（如 10、11、12）在 100%、125% 或 150% 等 Windows DPI 缩放比例下，汉字笔画交叉处容易发虚发糊**；13 磅是中英字符笔画渲染最结实清晰、既不拥挤也不模糊的最佳黄金字号。
2. **严禁使用注册表 FontLink + GDI 模式**：
   - 开启 `"font_options": ["gdi"]` 会失去 DirectWrite GPU 硬件加速，变成纯 CPU 渲染，导致长文件和大项目列表严重掉帧卡顿；且未注销前中文会回退为 90 年代点阵宋体（SimSun）。
3. **改动内置主题包前必须创建 `.original` 备份**：
   - Sublime Merge 的左侧 Commits、Files、Branches 列表等 UI 控件字体由主题包内的 `Merge.sublime-theme` 控制，不受用户 Preferences 的 `font_size` 影响。
   - 必须通过外科手术式精准文本补丁更新 `Theme - Merge.sublime-package`。脚本会自动创建 `*.original` 备份，支持随时 `restore` 一键无损还原。
4. **全动态跨机器兼容，绝无硬编码路径**：
   - 脚本自动通过进程、注册表（Uninstall/App Paths）、环境变量（`%APPDATA%`、`%WINDIR%`、`%LOCALAPPDATA%`、`PATH`）及全机所有驱动器盘符动态发现路径，新电脑直接开箱可用。
5. **绝对禁止全量重写/混淆主题 AST 规则与颜色**：
   - 内置主题包包含 520+ 条精密级联规则与数十个高精度控件切图。必须采用只替换 `font_face`/`font_size` 变量与补齐 `commit_file_name_label` 的外科手术式纯文本替换，绝不破坏任何容器 layer、texture 或背景颜色变量，杜绝白边、白条与渲染异常。
6. **严禁在终端后台启动 GUI 进程**：
   - 绝不可在 CLI 后台通过 `start` 或 `Start-Process` 静默拉起 `sublime_merge.exe`，否则 Windows 会创建无界面的孤儿僵尸进程（`MainWindowHandle: 0`），导致后续用户从桌面点击时单实例互斥死锁。配置完成后应提示用户从系统菜单手动启动。

---

## 快速命令

管理脚本位于 `scripts/patch_merge_theme.py`：

```bash
python "<skill目录>/scripts/patch_merge_theme.py" <action> [options]
```

| Action | 作用 | 备注 |
|---|---|---|
| `status` | 跨机器自动探测字体、ST/SM 配置文件、主题包补丁状态 | 默认命令，只读安全，先跑它确认环境 |
| `patch` | 自动备份并打外科手术式无损字体补丁（font_face 与 font_size） | 默认 `--font "YaHei Consolas Hybrid" --font-size 13` |
| `restore` | 从 `.original` 备份彻底还原内置主题包 | 恢复官方系统默认字体与原始字号 |
| `config` | 自动往 ST 和 SM 的 User Preferences 写入 13 号字体配置 | 自动处理带注释和尾部逗号的 JSON 文件 |

---

## 完整执行 SOP

### 第一步：检查并下载字体
从 GitHub 官方源下载最新免安装 TTF 文件至当前用户下载目录：
```powershell
# 1. 从 GitHub 下载 YaHei Consolas Hybrid 1.12.ttf (约 13.8MB)
curl.exe -fLo "$HOME\Downloads\YaHei Consolas Hybrid 1.12.ttf" "https://raw.githubusercontent.com/yakumioto/YaHei-Consolas-Hybrid-1.12/master/YaHei%20Consolas%20Hybrid%201.12.ttf"

# 2. 验证下载完整性
Get-Item "$HOME\Downloads\YaHei Consolas Hybrid 1.12.ttf" | Select-Object FullName, Length, LastWriteTime
```

### 第二步：安装字体至 Windows 系统
- **手动方式**：打开 `$HOME\Downloads`，右键 `YaHei Consolas Hybrid 1.12.ttf` $\rightarrow$ 点击 **「为所有用户安装」**（或「安装」）。
- **验证安装**：无论是系统级（`%WINDIR%\Fonts`）还是用户私有级（`%LOCALAPPDATA%\Microsoft\Windows\Fonts`），脚本跑 `status` 均能通过注册表与文件系统双重确认。

### 第三步：配置 Sublime Text
- **配置文件路径**：`%APPDATA%\Sublime Text\Packages\User\Preferences.sublime-settings`（ST3 则为 `Sublime Text 3`）
- **写入配置**：
```json
{
	"font_face": "YaHei Consolas Hybrid",
	"font_size": 13
}
```

### 第四步：配置 Sublime Merge 用户基础配置
运行脚本写入 13 号字体：
```bash
python scripts/patch_merge_theme.py config --font "YaHei Consolas Hybrid" --font-size 13
```
脚本会自动更新当前用户的 `Preferences.sublime-settings`，确保右侧 Diff 代码视图与提交输入框生效 13 号字体。

### 第五步：解决 Sublime Merge 左侧 Commits / Files 字体未生效问题
#### 现象与根因
在 `Preferences.sublime-settings` 改了 `font_face` 和 `font_size`，右侧 Diff 变了，但左侧侧边栏、中间 `Commits` 列表与 `Files` 列表完全不变。这是因为：
1. 界面列表属于 UI 控件，受 `Merge.sublime-theme` 控制，不受用户 Preferences 的编辑器字体设置影响；
2. 原版 `Merge.sublime-theme` 中 `commit_file_name_label` 规则遗漏了 `"font.face": "var(font_face)"`。

#### 解决方案：打外科手术式字体补丁
```bash
python scripts/patch_merge_theme.py patch --font-size 13
```
- 自动备份 `Theme - Merge.sublime-package` 为 `.original`；
- 在 `Merge.sublime-theme` 中精准将 `font_face` 设为 `YaHei Consolas Hybrid`，`font_size` 设为 13，`font_size_sm` 设为 12，`font_size_lg` 设为 14；
- 精准为 `commit_file_name_label` 补齐 `"font.face": "var(font_face)"`；
- **不触动任何控件颜色、贴图或层级规则，彻底杜绝白条白块与渲染异常**；
- 退出后手动重启 Sublime Merge 即可完美生效。

---

## 常见排障与答疑

### Q: 为什么字号一定要设为 13，不能用 11 或 12 吗？
- YaHei Consolas Hybrid 属于点阵与矢量融合的中英文合成字体。在 100%、125% 或 150% 等常见 Windows DPI 缩放比例下，**字号设为 10~12 时中文字符由于抗锯齿边缘对齐特性，极易发虚模糊**，影响阅读。
- 13 磅是中英字符笔画渲染最结实清晰的甜点字号，既不臃肿，又完全不发糊。

### Q: 为什么之前改动会导致 Untracked 区域上面有一条白线，或者提交按钮区域变白？
- Sublime Merge 的主题引擎非常严谨，`details_panel` 和 `commit_message_container` 的背景依赖动态计算变量 `var(--background)` 与 `detail_panel_bg`。
- 如果尝试使用 JSON 全量重写 `Merge.sublime-theme` 或混入第三方配色规则，会导致主题引擎解析异常或回退到浅色默认的 `#fcfdfd`（Breakers 浅色背景），从而产生白线和白块。
- 正确做法是：**仅使用纯文本外科手术式替换修改字号与字体声明，绝不引入任何配色改动**，确保 UI 100% 保持官方原版质感。

### Q: 新电脑上非标准路径安装（如装在 E 盘或免安装绿色版），脚本能认出来吗？
- 脚本内置 4 级探测机制：
  1. 当前系统 `PATH` 环境变量与 `smerge` 命令行；
  2. Windows 注册表 `Uninstall` 与 `App Paths` 登记项；
  3. 全机所有实际存在的驱动器盘符（`C:`, `D:`, `E:`, ...）常见路径扫描；
  4. 支持显式追加 `--merge-dir "D:\CustomPath\Sublime Merge"` 参数强行指定。

### Q: Sublime Merge 升级后字体失效了怎么办？
- 软件大版本覆盖安装会还原官方的 `Theme - Merge.sublime-package`。
- 直接在新电脑/新版本上重跑一次 `python patch_merge_theme.py patch` 即可瞬间恢复。
