---
name: sh-nuitka-pack
description: uv单脚本PEP 723+Nuitka打包Windows单文件exe与启动加速缓存SOP。点名使用
version: 1.0.0
created: 2026-10-13
updated: 2026-10-13
disable-model-invocation: true
---

# sh-nuitka-pack — uv 单脚本 Nuitka 单文件打包与启动加速

把"PEP 723 单脚本 Python 工具 → 免安装单一 Windows `.exe`"变成标准确定性交付：确认脚本与依赖 → 运行 `scripts/pack.py`（固化 Nuitka 单文件编译、解压缓存、双蛇图标注入）→ 验证产物（启动耗时、版本、图标）→ 汇报。

产物为 `dist/<app_name>.exe`，目标机器无需安装 Python，单文件拷贝即用。  
深度原理解析与踩坑背景见 `references/pitfalls.md`。

---

## 核心铁律（生产级落地硬核总结）

1. **单脚本首选 Nuitka 单文件，不建议使用 PyStand 或传统 PyInstaller**：
   - 相比 PyInstaller：消除了每次启动重复解压的 500~1500ms 黑框延迟，且机器码编译反编译难度极高；
   - 相比 PyStand：交付物为**真正的单一独立 `.exe`**，无需携带 `runtime/`、`site-packages/` 等数十个散碎目录，分发极致干净。
2. **强制使用 `--onefile-tempdir-spec` 固化解压缓存**：
   - 配置 `{CACHE_DIR}/<app_name>/{VERSION}`（解压到 `%LOCALAPPDATA%`）；
   - 首次启动解压（~700ms），后续启动直接复用二进制，冷启动仅需 **~165ms**（接近原生 C 程序）；升级版本时自动切换新目录，互不冲突。
   - 变量名为 Nuitka 4.x `{VAR}` 格式，只认 `{CACHE_DIR}`，**严禁写成 `{CACHE}`**。
3. **`zstandard` 是体积压缩的生死线**：
   - 编译环境必须包含 `zstandard>=0.22`；
   - 缺失 zstandard 会导致单文件压缩回退，体积从 7MB 膨胀到 27MB+。`scripts/pack.py` 已强制内置。
4. **编译期解释器必须与 PEP 723 依赖保持严格一致**：
   - Nuitka 是真编译，依赖 AST 静态分析和当前环境实际 import；
   - 单脚本中声明的第三方依赖必须全部带入构建环境，漏掉任何一个都会导致运行时抛出 `ModuleNotFoundError`。
5. **图标经 PE 资源段直接注入**：
   - 使用 `--windows-icon-from-ico` 在链接阶段原生写入 PE 资源，不修改已有二进制字节，降低杀软误报；
   - 默认自动关联仓库双蛇吉祥物图标（`docs/assets/projects/python_projects/python-default.ico`）。
6. **排除单元测试与多余包**：
   - 必须配置 `--noinclude-unittest-mode=nofollow` 和 `--nofollow-import-to=unittest`，避免第三方库自带的测试套件污染产物并拖慢编译。
7. **终端控制台模式感知**：
   - CLI 命令行工具默认强制控制台（`--windows-console-mode=force`），确保 stdout/stderr 与退出码在 PowerShell/CMD 中正常透传；
   - GUI 工具则使用 `--gui` 关闭控制台窗口。

---

## 工作流 SOP

### Step 1: 确认输入参数

| 参数 | 默认值 | 说明 |
|---|---|---|
| **目标脚本** | 必填 | 包含 PEP 723 内联元数据（`# /// script ...`）的单文件 Python 脚本 |
| **应用名称** | 脚本文件名（不含 `.py`） | 产物 exe 名称（如 `douyin_dl.exe`） |
| **版本号** | 自动提取 `VERSION` 或 `0.1.0` | 写入 VS_VERSION_INFO 及缓存路径，版本单一事实源 |
| **交付形态** | `onefile`（单文件） | 可传 `--dir` 切换为 standalone 文件夹模式（构建与调试更快） |
| **程序类型** | `CLI`（强制控制台） | 若为图形界面工具可传 `--gui` 消除黑框 |
| **程序图标** | 仓库默认双蛇图标 | 可传 `--icon <path.ico>` 指定，或 `--no-icon` 明确跳过 |
| **输出目录** | `dist` | 编译产物输出位置 |

---

### Step 2: 执行打包构建

统一由 `scripts/pack.py` 驱动，支持 dry-run 预演与实际编译：

```powershell
# 1. 预演命令（仅打印拼装参数，不启动耗时编译）
uv run "<skill目录>/scripts/pack.py" path/to/my_tool.py --dry-run

# 2. 正式打包（默认单文件 + 启动加速缓存 + 双蛇图标）
uv run "<skill目录>/scripts/pack.py" path/to/my_tool.py

# 3. GUI 应用打包（无黑框）
uv run "<skill目录>/scripts/pack.py" path/to/my_gui.py --gui

# 4. 指定自定义图标与输出目录
uv run "<skill目录>/scripts/pack.py" path/to/my_tool.py --icon app.ico --output-dir release
```

---

### Step 3: 验证产物（必检三项）

构建完成后，依次执行以下冒烟验证：

```powershell
# 1. 功能与版本验证
.\dist\my_tool.exe --help
.\dist\my_tool.exe --version

# 2. 启动耗时测速（验证 ~165ms 秒开加速）
# 首次运行（解压落盘，约 500~700ms）
Measure-Command { .\dist\my_tool.exe --version }
# 二次运行（命中 %LOCALAPPDATA%\my_tool\<version> 缓存，直降至 ~165ms）
Measure-Command { .\dist\my_tool.exe --version }

# 3. PE 图标与资源验证
powershell -NoProfile -Command "Add-Type -AssemblyName System.Drawing; [System.Drawing.Icon]::ExtractAssociatedIcon((Resolve-Path 'dist\my_tool.exe')).Size"
# 正常应输出: Width: 32, Height: 32
```

---

### Step 4: 汇报与交付

向用户汇报以下关键指标：
1. **产物路径与体积**：如 `dist/my_tool.exe (7.6 MB)`；
2. **启动加速效果**：首次解压与二次复用启动耗时对比；
3. **缓存维护提示**：缓存位于 `%LOCALAPPDATA%\<app_name>\<version>`，旧版本可安全手动清理；
4. **杀软误报提醒**：单文件打包 exe 偶发被安全软件拦截属常见现象，分发时提前知会。

---

## 常见排障速查

| 现象 / 报错 | 根因剖析 | 快速修复方案 |
|---|---|---|
| `ModuleNotFoundError` | 编译期解释器未安装目标脚本依赖 | 确保目标脚本有完整 PEP 723 `dependencies` 块，`pack.py` 会自动透传 |
| 打包体积达 25MB+ | 缺失 `zstandard` 压缩扩展 | 确保 `pack.py` 内含 `zstandard>=0.22` 依赖，重跑编译 |
| Nuitka 提示缺少 C 编译器 | 未安装 Visual Studio MSVC 工具链 | 安装 VS 2022 Build Tools（勾选 "C++ 桌面开发"） |
| 控制台无回显或退出码异常 | 未开启强制控制台模式 | 检查参数是否包含 `--windows-console-mode=force` |
| 图标未更新 | 资源管理器 Icon 缓存未刷新 | 移动 exe 到新目录或重启 Explorer 进程测试 |
