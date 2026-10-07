---
name: sh-pystand-pack
description: PyStand+嵌入式 Python 把 Python 项目打包成免安装绿色文件夹。点名使用
---

# sh-pystand-pack — PyStand 独立打包

把"Python 项目 → 免安装可分发文件夹"变成一次可靠的执行：确认参数 → 跑 `scripts/pack.py`（全流程已固化，含全部踩坑修正）→ 验证产物 → 汇报。产物是 `dist/<AppName>/`，目标机器**无需安装 Python**，整体拷走即可运行。

排障、坑的背景与手动复刻流程见 `references/pitfalls.md`（打包失败或产物行为异常时必读）。

## 铁律（2026-08-24 首轮全流程 + 2026-08-26 服务器型实战，全部真实踩坑）

1. **用 `scripts/pack.py` 打包，不要现场手敲流程**。`._pth` 隔离模式、`_pystand_static.int` 优先级、pip `--target`、tkinter 四件套这些坑的修正已全部固化在脚本里，手敲必然漏。
2. **发布目录只允许一个启动脚本**。`_pystand_static.int` 在 PyStand 的查找顺序里优先级最高，会拦截**所有** PyStand exe（包括调试用的 CLI 变体）——曾因此把"exe 在跑 GUI mainloop"误判成"神秘挂起"排查了一小时。要临时调试 CLI 变体，必须先挪走 `_pystand_static.int`。
3. **"进程活着" ≠ "程序正常"**。GUI 变体无控制台：stdout 进 devnull，`.int` 抛异常时弹隐藏 MessageBox，在无头环境表现为进程挂死。验证必须用窗口标题（`Get-Process <AppName> | Select MainWindowTitle`）或产物日志 `pystand-error.log`（pack.py 生成的启动脚本自带异常落盘）。
4. **本机没有系统级 Python 是常态而非故障**。一切 Python 操作走 uv（`uv run --no-project python ...`），用户依赖装进嵌入式 runtime（`runtime\python.exe`），不要试图找/装系统 Python。
5. **解压 zip 不要用 Git Bash 的 `tar`**（GNU tar 不认 zip），Python 的 `zipfile` / `/c/Windows/System32/tar.exe`（bsdtar）才行。涉及中文路径的文件操作（删除/移动目录）走 PowerShell，Git Bash 会 mojibake。
6. **下载 URL 的坑**：PyStand release 的 tag **没有 `v` 前缀**（`1.1.5` 不是 `v1.1.5`，错 URL 返回 9 字节 "Not Found"）；rcedit 最新就是 `v2.0.0`（v2.1.0 不存在）。URL 已固化在 pack.py，不需要记忆，但手动下载时要照 `references/pitfalls.md` 里的清单抄。
7. **tkinter 靠复制，不靠 pip**。嵌入式包从不带 tkinter 且 pip 装不了；pack.py 会从本机同 minor 版本的完整 Python（uv managed 目录优先）复制四件套。源缺失时脚本会报清晰错误，此时按 pitfalls.md 的备选链处理，不要跳过（用户程序 import tkinter 会炸）。
8. **换图标 = 改 exe 字节 = 杀软误报风险升高**。这是无签名小众 exe 的固有问题，无法根治，只能在汇报时提醒用户（尤其要发给客户时）。
9. **Python 版本边界**：PyStand exe 本身不绑版本（加载 `runtime\python3.dll` 稳定 ABI 转发库），换版本 = 换 runtime；但它内部调用的 `Py_Main()` 在 3.15 被移除，**默认用 3.12.x**（打包脚本默认 3.12.5），3.13/3.14 可用需实测，3.15+ 不可用。Win7 目标才用 3.8。
10. **服务器型应用（FastAPI/uvicorn 等无窗口程序）一律 `--server` 打包**。脚本自动生成"日志落盘 + stop.flag 优雅停机"入口和 `stop-<App>.bat`（无窗口环境没有 Ctrl+C，交付物必须带停机脚本）；验证走 `/health` 轮询 + `logs/run.log`，**不要用窗口标题判定**（服务器没有窗口）。GUI 的 stdout 进 devnull，不落盘 = 日志黑洞。
11. **无控制台环境的 bat 三坑**：① `timeout` 在无控制台宿主直接失败 → 提前走强杀分支，用 `ping -n 2 127.0.0.1` 轮询代替；② 中文注释在非 UTF-8 代码页乱码甚至解析报错，bat 全 ASCII；③ Python 侧 Tee 往管道写日志必须逐行 flush（块缓冲攒 8KB 才吐，表现为"控制台看不到日志"）。模板已固化在 pack.py，别手写。

## 工作流

### Step 1: 确认参数（信息缺口才问，用户说了的直接用）

| 参数 | 默认 | 说明 |
|---|---|---|
| 项目目录 | cwd | 至少含入口 py 文件 |
| 入口文件 | `main.py` | 需支持 `python main.py` 直接跑（`if __name__ == "__main__"` 生效，pack.py 用 `runpy.run_path(run_name="__main__")` 调起）；`--server` 且未显式指定时自动生成 |
| App 名称 | 项目目录名 | 产物 exe 与文件夹名 |
| requirements | 目录下 `requirements.txt` | 无则跳过依赖安装 |
| Python 版本 | `3.12.5` | 见铁律 9 |
| 图标 | 无 | 用户给了 .ico 就传 `--icon`；没给可以提议用 Pillow 生成（`uv run --with pillow`），用户拒绝就不加图标 |
| GUI/CLI | GUI | 交付默认 GUI（无黑窗）；CLI 变体仅调试用（无控制台环境下会挂，见铁律 3/4） |
| tkinter | 自动探测 | 扫描源码 `import tkinter/turtle` 自动启用，也可 `--with-tkinter` 强制 |
| 服务器型 | 否 | FastAPI/uvicorn 等常驻服务传 `--server`：自动 uv export 锁版本、src 布局拷贝、.env 拷贝、生成入口与 `stop-<App>.bat`；`--host/--port/--app-target` 可调（app-target 默认取 src 下第一个含 main.py 的包） |

### Step 2: 执行打包

```bash
uv run --no-project python "<skill目录>/scripts/pack.py" \
    --project-dir <项目目录> \
    --entry main.py \
    --app-name MyApp \
    --icon app.ico          # 可选
# 全部参数: --python-version --variant gui|cli --arch x64|x86
#           --dist-dir --cache-dir --with-tkinter --skip-tkinter --slim --debug-cli
#           --server --host --port --app-target

# 服务器型项目（FastAPI/uvicorn，src 布局 + uv.lock 也照吃）一条命令:
uv run --no-project python "<skill目录>/scripts/pack.py" \
    --project-dir <项目目录> --app-name <AppName> --server --debug-cli
```

脚本内部顺序：下载（带缓存，二次打包秒过）→ 解压 runtime → 改 `._pth` → get-pip 引导 → pip `--target` 装依赖 → 复制源码与 tkinter 四件套 → 生成 `_pystand_static.int`（含 TCL_LIBRARY 与异常日志兜底）→ 复制并改名 PyStand exe → rcedit 换图标（可选）→ 清理杂物。

`--server` 额外做：无 requirements.txt 但有 `uv.lock` 时自动 `uv export` 锁版本；`src/*` 拷进 `app/`（app/ 在 sys.path 上，包内 BASE_DIR 类 `parents[2]` 恰好解析到产物根，`.env` 放 exe 同级即生效）；拷 `.env`/`.env.example`/README（有 .env 会提醒凭据风险）；生成 server 入口 `app/main.py`（chdir 到产物根、控制台检测分流日志——有控制台 tee 双写且逐行 flush、无控制台纯落盘 `logs/run.log`；uvicorn 挂 stop.flag 看门狗线程优雅停机）；生成 `stop-<App>.bat`（全 ASCII + ping 轮询，规避铁律 11 三坑）。

- `--debug-cli`：额外放一个 `<AppName>-cli.exe`（CLI 变体，复用 `_pystand_static.int` 同一入口但带控制台，stdout/traceback 直接可见），用户要"看 print 输出"时给这个。
- `--slim`：发布版瘦身（删 pip 本体等 ~10MB），删后 `runtime\python.exe` 调试能力受限。

### Step 3: 验证产物（不要省略，方式见铁律 3）

```bash
# GUI 冒烟: 启动 → 查窗口标题 → 关闭
cd dist/MyApp && ./MyApp.exe & sleep 6
powershell -NoProfile -Command "Get-Process MyApp -ErrorAction SilentlyContinue | Select -ExpandProperty MainWindowTitle"
taskkill //IM MyApp.exe //F
# 判定: 窗口标题 = 程序设定的标题 → 通过；空 → 查 pystand-error.log

# CLI 冒烟（--debug-cli 时）: 注意 Bash 里 & 会把 cd 一并划入后台 job，cd 与执行放同一前台段
cd dist/MyApp && ./MyApp-cli.exe

# 服务器冒烟（--server 时）: /health 轮询 + 优雅停机，没有窗口标题可看
Start-Process -FilePath "dist\MyApp\MyApp.exe" -WorkingDirectory "dist\MyApp"
# PowerShell 轮询 http://127.0.0.1:8000/health（1s 间隔，~30s 上限）；DB 不通返回 degraded 也算进程正常
cmd /c "dist\MyApp\stop-MyApp.bat"
# 判定: "stopped gracefully" + 进程退出 + run.log 出现 app_stopped/shutdown complete = 通过
# 日志: dist\MyApp\logs\run.log（launcher 的 console= 行说明走了哪个输出分支）；异常: pystand-error.log
```

注意 bash 陷阱：`cd X && ./app.exe & sleep N` 的 `&` 会把整个 `cd && app.exe` 划为后台 job，后续命令仍在旧 cwd——cd 与启动放同一条命令、验证命令另起一条。

### Step 4: 汇报

向用户报告：产物路径与大小、目录结构简图、验证结果（GUI=窗口标题 / CLI=输出 / server=health+优雅停机+run.log）、可选后续（`--slim` 发布、`--debug-cli` 调试变体、杀软误报提醒——见铁律 8；server 型提醒 `.env` 凭据别随产物外发）。

## 已知边界（提前告知用户，不要等翻车）

- **PyQt/PySide**：可以装（pip 装进 site-packages 即可），但中文路径下 Qt 插件目录需在代码里手动 `QApplication.setLibraryPaths`（PyStand issue #6）；本 skill 未实测 PyQt 场景。
- **CLI 变体**在计划任务/服务等无控制台环境可能挂起——交付一律 GUI 变体。
- **CLI 变体"没日志"可能不是 bug**：无控制台宿主下 `GetConsoleWindow()=False`，server 入口正确地走纯落盘分支（`console=False`），日志在 `logs/run.log`。双击 `*-cli.exe`（有真控制台）才会 tee 到控制台。验证输出分支看 launcher 首行。
- 含 C 扩展的依赖（numpy 等）会显著增大体积且要求位数匹配（x64/x86 与 embed 包一致）。
