---
name: sh-uv-python-env
description: uv 统一管理 Python 环境——全局 python/pip 走专用 venv，uv 默认锁 3.12.5，卸载 anaconda/多 python。点名使用
---

# sh-uv-python-env — uv 统一 Python 环境

在一台只配了 uv 的机器上，把「全局 `python` / `pip` 命令」与「`uv run` / `uv add` 项目工作流」统一起来：全局命令经 shim 转发到 uv 创建的**专用全局 venv**，uv 托管解释器本体保持纯净。适合全新机器引导，也适合清理 anaconda / 手动 Python 多版本混存的老机器。

由来：2026-10-07 在 `D:\Users\language_projects` 落地（docs/plans/46）。本 skill 是其可复现提炼 + 全部踩坑。

## 目标架构（先建立心智模型）

```text
全局 python / pip（只认这俩的 AI / 工具用）
   └─> ~/uv_shim/{python.bat,pip.bat,python3.bat,pip3.bat}
          └─> ~/uv_shim/.uv-global/Scripts/python.exe   （uv venv --python 3.12.5 建）
                ├─ python xxx      -> .uv-global 解释器（3.12.5）
                └─ pip install X   -> .uv-global 的 pip（装进同一环境，python 立即可 import）

uv run / uv add（懂 uv 的工具、你自己写项目）
   └─> 各项目独立 .venv（隔离，互不干扰，默认 3.12.5）

uv 托管解释器本体（~/.local/share/uv/python/cpython-3.12.5-...）
   -> 只读，PEP 668 保护，纯净不污染
```

要点：**`python` 与 `pip` 指向同一个 `.uv-global`** → pip 装的包 python 直接能 use（复刻传统全局 pip 体验）；uv 托管解释器本体保持纯净。两套互不干扰。

## 铁律（全部真实踩坑，2026-10-07）

1. **设 `UV_PYTHON=3.12.5` 即锁定 uv 默认版本**。实测：设后 `uv venv` 与 `uv run --no-project python` 都默认 3.12.5，无需每次 `--python`。
2. **`uv venv` 默认不带 pip**。直接 `python -m pip` 报 `No module named pip`。必须先 seed：
   `uv pip install --python <venv>\Scripts\python.exe pip`。
3. **pip.bat 走 `python -m pip`，不要用 `uv pip install`**。`uv pip install --python X install certifi` 会把 `install` 当包名（`No package registry: install`）；且 `uv pip` 的 `--python` 是**子命令级**参数（`uv pip install` 才有），放错层级会报 `Unrecognized arguments`。`python -m pip %*` 语义与传统一致，最稳。
4. **用 `.bat` 转发（PowerShell 侧用 `%~dp0`）**。python.bat 与 pip.bat 都以 `%~dp0` 相对定位 `.uv-global`，目录可整体搬走而不断链。
5. **PATH 改动必须新开终端才生效**。旧终端仍用旧 PATH，验证要开新终端。
6. **`uv python find`（无参数）返回最高版本（如 3.13）是"探测解释器"，不代表默认**。真正默认由 `UV_PYTHON` 控制，别被它误导以为没锁定成功。
7. **uv 托管解释器本体 PEP 668 只读**。`pip install` 会报 `externally-managed-environment`。所有全局装包都落 `.uv-global`，绝不触碰解释器本体 → 保持 uv 纯净。
8. **卸载旧 Python 走官方卸载器，不要直接删目录**。python312（MSI 安装）有 7 个注册表组件 + 卸载器；anaconda3 自带 `Uninstall-Anaconda3.exe /S`。直接删会留注册表残留、MSI 台账、文件关联。

## 一键引导（全新机器，仅装了 uv）

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

# 3. 在 $shim 写 4 个 .bat（内容见下方）：
#    python.bat / python3.bat:
@echo off
"%~dp0.uv-global\Scripts\python.exe" %*
#    pip.bat / pip3.bat:
@echo off
"%~dp0.uv-global\Scripts\python.exe" -m pip %*

# 4. uv_shim 放到 USER PATH 最前
$old = [System.Environment]::GetEnvironmentVariable('Path','User')
[System.Environment]::SetEnvironmentVariable('Path', ($shim + ';' + $old), 'User')

# 5.（可选，清理旧 python）卸载 anaconda/python312：
#    python312:  "C:\...\python-3.12.5-amd64.exe" /uninstall /quiet
#    anaconda3:  Uninstall-Anaconda3.exe /S
#    二者都要抽查注册表 Uninstall 项确认清干净（Get-ChildItem HKLM\...\Uninstall\* 查 DisplayName）

# 6. 新开终端验证
python --version; pip --version
pip install six; python -c "import six; print('ok')"   # -> ok
```

## 验证模板

| 检查 | 期望 |
| --- | --- |
| `python --version` | Python 3.12.5 |
| `pip --version` | pip 26.x（`...\.uv-global\...`）|
| `pip install six` → `python -c "import six"` | ok（同一环境可 import）|
| anaconda3 / python312 目录 | 不存在（若执行了卸载）|
| `(Get-Command python).Source` | `...\uv_shim\python.bat` |

> PATH 改动须新开终端验证。

## torch / 深度学习大依赖（同 uv 项目隔离）

深度学习的 torch 等大依赖**不在全局 python** 里装，放**项目的 uv 隔离环境**（`.venv`），避免污染全局、便于按项目锁版本与 CUDA。

一个重要事实：RTX 50 系（Blackwell / sm_120）**只有 cu128+ 的 torch wheel 支持**。在 `pyproject.toml` 配 pytorch 的 cu128 索引：

```toml
[[tool.uv.index]]
name = "pytorch-cu128"
url = "https://download.pytorch.org/whl/cu128"
explicit = true
[tool.uv.sources]
torch = { index = "pytorch-cu128" }

# torch 2.x 版本要求（示例）：
torch = ">=2.7"
```

- `download.pytorch.org` 的 2.6GB CUDA wheel 在部分网络（尤其国内）**拉不动**（索引页 200、wheel 中断）。可用：国内镜像源（阿里云等）、或从本机已装 torch 的其它环境（如 ComfyUI 的 `.venv`）借实体 wheel 离线安装。
- 检查环境：`python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"`。

## uv 下载物落位速查

| 内容 | 位置 |
| --- | --- |
| uv 托管解释器 | `%LOCALAPPDATA%\uv\python\...` 或 `~/.local/share/uv/python`（每版一目录，只读）|
| 第三方 wheel 缓存 | `UV_CACHE_DIR`（默认 `%LOCALAPPDATA%\uv\cache`；本机设到 `D:\Users\29580\.cache\uv`）|
| 全局 shim 装的包 | `~/uv_shim/.uv-global/Lib/site-packages/` |
| 每项目装包 | `<项目>/.venv/Lib/site-packages/` |

## 回滚

```powershell
[System.Environment]::SetEnvironmentVariable('UV_PYTHON', $null, 'User')
# 从 USER PATH 移除 $HOME\uv_shim 前缀（余项复位）
# 删除 $HOME\uv_shim（含 .uv-global）
# 如需删解释器：uv python uninstall 3.12.5
```

## 已知边界

- **shim 让全局 `python`/`pip` 都指向全局 venv**：如果你想让某个命令走"项目隔离"，应主动用 `uv run`/`uv add`，不要靠全局 python。
- **`D:\Users\tools\python` 之类目录名像 python 但不是解释器**（实际是你放脚本的目录）——不抢 `python` 命令，别误删。
- 卸载旧 python 前，先排查是否有脚本/快捷方式/工具硬编码了绝对路径（`Get-Command python`、扫 `.ps1/.bat/.py` 里 `python312|anaconda3`）——本 skill 落地时扫描过，干净。