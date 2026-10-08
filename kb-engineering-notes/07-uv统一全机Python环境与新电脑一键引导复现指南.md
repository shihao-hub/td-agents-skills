---
name: kb-uv-python-unified-env
description: 把全机 Python 统一到 uv：多来源并存治理、`uv_shim` 全局 `python`/`pip` 转发架构、`UV_PYTHON` 锁版语义、PEP 668 与 venv 无 pip 排坑，以及在只装了 uv 的新电脑上一键复现整套配置。当出现 `externally-managed-environment`、`No module named pip`、`python` 命令被 stub 抢占，或要做新机环境复现时查阅本条目。
---

# 07-uv统一全机Python环境与新电脑一键引导复现指南

> **归档位置**：`kb-engineering-notes/07-uv统一全机Python环境与新电脑一键引导复现指南.md`  
> **实战源起**：全机 Python 环境统一迁移（2026-10-07 卸载 anaconda3 与 python312，统一 uv 3.12.5；完整过程见 `docs/plans/46-python-env-uv-unified.md`）  
> **核心议题**：多 Python 来源并存的治理架构、全局 `python`/`pip` 经 shim 转发到 uv 专用全局环境、新电脑一键复现同一配置  
> **姊妹条目**：面向装机的可执行操作卡见 `sh-user-skills/sh-uv-python-env/`（skill 形态，含 torch/CUDA 大依赖方案）

---

## 一、现象与核心痛点直击

老机器典型混乱状态：多个 Python 来源并存，版本与包互不一致，彼此看不见对方的 site-packages：

| 来源 | 路径 | 问题 |
|:---|:---|:---|
| anaconda3 base | `D:\Users\29580\anaconda3` | 379 个科学包的独立王国，与其它环境零互通（4.67GB） |
| python312（手动 pip） | `D:\Users\python312` | 独立 site-packages（4.95GB），还被 uv 误"借用"为 3.12.5 来源 |
| msys64/mingw64 | `D:\msys64\mingw64\bin` | mingw 版 python 干扰 uv 探测定版（warning） |
| uv 托管 | `C:\Users\<user>\AppData\Roaming\uv\python\...` | PEP 668 只读，期望收敛到的"唯一来源" |
| WindowsApps stub | `...\WindowsApps\python.exe` | 商店占位 stub，抢 `python` 命令名 |

两类真实需求必须**同时**满足：

1. `python xxx` / `pip install X` —— 只认传统命令的 AI Agent、旧脚本、教程；
2. `uv run` / `uv add` —— 现代项目工作流（每项目独立 `.venv`，互不干扰）。

目标：统一到 uv（3.12.5），全局命令经 shim 转发到 uv 创建的**专用全局环境**，两条通道互不污染；且整套配置要能在一台**只装了 uv 的新电脑**上一键复现。

## 二、底层根因与机制剖析（为什么必须这样设计）

### 1. PEP 668：uv 托管解释器不能直接当"全局 python"用
uv 托管解释器带 `EXTERNALLY-MANAGED` 标记，裸 `pip install` 直接报 `externally-managed-environment`。这是刻意设计（防止多包管理器互相踩踏），不是故障。解法：用 `uv venv` 造一个**无 PEP 668 标记**的专用环境（`.uv-global`）承接全局装包——它就是"可自由 pip 的全局环境"替身。

### 2. `uv venv` 默认不 seed pip
新建 venv 里 `python -m pip` 报 `No module named pip`。必须先 `uv pip install --python <venv>\Scripts\python.exe pip` 把 pip 装进去，传统 pip 工作流才可用。

### 3. 默认版本的语义陷阱：`UV_PYTHON` 才是真默认
`uv python find`（无参数）返回**最高**已装版本（如 3.13），那只是"探测解释器"，不代表默认。真正默认由用户级环境变量 `UV_PYTHON=3.12.5` 控制（`uv venv` / `uv run` 均认）。别被 find 的输出误导以为没锁成功。

### 4. `pip.bat` 必须走 `python -m pip`，禁用 `uv pip install` 转发
`uv pip install --python X install certifi` 会把 `install` 当包名（报 `No package registry: install`，受 registry 干扰）；且 `--python` 是**子命令级**参数，放错层级报 `Unrecognized arguments`。`"<python.exe>" -m pip %*` 语义与传统 pip 完全一致，最稳。

### 5. PATH 优先级是最终裁决
`uv_shim` 目录前置 USER PATH，压过 mingw64 的 python 与 WindowsApps stub，接管全局 `python`/`pip`。PATH 改动**必须新开终端**才生效。

### 最终架构

```text
全局 python / pip（只认这俩的 AI / 工具用）
   └─> ~/uv_shim/{python.bat, pip.bat, python3.bat, pip3.bat}
         └─> ~/uv_shim/.uv-global/Scripts/python.exe   （uv venv --python 3.12.5 建）
               ├─ python xxx      -> .uv-global 解释器（3.12.5）
               └─ pip install X   -> .uv-global 的 pip（装进同一环境，python 立即可 import）

uv run / uv add（懂 uv 的工具与自己写项目）
   └─> 各项目独立 .venv（隔离，互不干扰，默认 3.12.5）

uv 托管解释器本体（cpython-3.12.5）-> 只读、PEP 668 保护，纯净不污染
```

要点：`python` 与 `pip` 指向**同一个** `.uv-global` → pip 装的包 python 直接能 import（复刻传统全局 pip 体验）；uv 托管解释器本体保持纯净。

## 三、标准解决 SOP：新电脑一键引导（可直接复制执行）

> 假定 Windows + PowerShell；uv 已装（`winget install astral-sh.uv` 或官方脚本）。先新开终端使 uv 进 PATH。

```powershell
# 1. 下载并锁定 3.12.5
uv python install 3.12.5
[System.Environment]::SetEnvironmentVariable('UV_PYTHON','3.12.5','User')

# 2. 建专用全局环境 + seed pip
$shim = "$HOME\uv_shim"
New-Item -ItemType Directory -Force -Path $shim | Out-Null
uv venv --python 3.12.5 "$shim\.uv-global"
uv pip install --python "$shim\.uv-global\Scripts\python.exe" pip

# 3. 在 $shim 写 4 个转发 .bat（数组行写入自动 CRLF；-Encoding Ascii 确保 .bat 无 BOM）
$pyBat  = '@echo off', '"%~dp0.uv-global\Scripts\python.exe" %*'
$pipBat = '@echo off', '"%~dp0.uv-global\Scripts\python.exe" -m pip %*'
'python','python3' | ForEach-Object { Set-Content "$shim\$_.bat" -Value $pyBat  -Encoding Ascii }
'pip','pip3'       | ForEach-Object { Set-Content "$shim\$_.bat" -Value $pipBat -Encoding Ascii }

# 4. uv_shim 放到 USER PATH 最前（压过 mingw64 / WindowsApps）
$old = [System.Environment]::GetEnvironmentVariable('Path','User')
[System.Environment]::SetEnvironmentVariable('Path', ($shim + ';' + $old), 'User')

# 5.（可选，仅老机器清理）卸载旧 python，走官方卸载器、禁直删目录：
#    python312:  "C:\...\python-3.12.5-amd64.exe" /uninstall /quiet
#    anaconda3:  Uninstall-Anaconda3.exe /S
#    卸后抽查注册表 Uninstall 项（Get-ChildItem HKLM:\...\Uninstall\* 查 DisplayName）确认清干净

# 6. 新开终端验证
python --version; pip --version
pip install six; python -c "import six; print('ok')"   # -> ok
```

`.bat` 以 `%~dp0` 相对定位 `.uv-global`，整个 `uv_shim` 目录可搬走而不断链。

## 四、验证与防复发

### 验证模板（须新开终端）

| 检查 | 期望 |
|:---|:---|
| `python --version` | Python 3.12.5 |
| `pip --version` | pip 26.x（路径含 `...\.uv-global\...`） |
| `(Get-Command python).Source` | `...\uv_shim\python.bat` |
| `pip install six` → `python -c "import six"` | ok（同一环境可 import） |
| `uv venv`（项目内） | 默认建出 3.12.5（`UV_PYTHON` 生效） |

### 易踩坑清单

1. `uv venv` 默认不带 pip → 须 `uv pip install ... pip` seed，否则 `No module named pip`；
2. `pip.bat` 用 `python -m pip`（非 `uv pip install`，其会把 `install` 当包名/受 registry 干扰）；
3. PATH 改动须新开终端生效，旧终端仍用旧 PATH；
4. `uv python find`（无参数）返回最高版本 ≠ 默认；默认由 `UV_PYTHON=3.12.5` 控制；
5. 解释器本体 PEP 668 只读；所有 `pip install` 落 `.uv-global`，不触碰本体 → uv 纯净。

### 防复发纪律

- 深度学习大依赖（torch/CUDA）**不进全局**，放项目 uv 隔离环境（RTX 50 系/sm_120 只有 cu128+ wheel 支持，索引配置见 `sh-user-skills/sh-uv-python-env/`）；
- 卸载旧 python 前先扫硬编码绝对路径（`Get-Command python`、扫 `.ps1/.bat/.py` 里 `python312|anaconda3`）；
- 目录名像 python 但不是解释器的目录（如放脚本的 `tools\python`）不抢命令名，别误删。

### 回滚

```powershell
[System.Environment]::SetEnvironmentVariable('UV_PYTHON', $null, 'User')
# 从 USER PATH 移除 $HOME\uv_shim 前缀（余项复位）
# 删除 $HOME\uv_shim（含 .uv-global）；如需删解释器：uv python uninstall 3.12.5
```

## 附：uv / python 下载物落位速查

| 内容 | 位置 | 说明 |
|:---|:---|:---|
| python 解释器（uv 托管） | `%APPDATA%\uv\python\cpython-<ver>-...`（或 `~/.local/share/uv/python`） | 每版一目录，只读 |
| 第三方 wheel 缓存 | `UV_CACHE_DIR`（默认 `%LOCALAPPDATA%\uv\cache`，本机重定向 `D:\Users\<user>\.cache\uv`） | 全局缓存跨项目复用 |
| 全局 shim 装的包 | `~/uv_shim/.uv-global/Lib/site-packages/` | `python`/`pip` 落此 |
| 每个项目实际安装 | `<项目>\.venv\Lib\site-packages\` | 项目隔离 |
