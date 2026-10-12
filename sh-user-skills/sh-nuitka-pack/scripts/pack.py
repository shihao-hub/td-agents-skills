# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "nuitka>=2.5",
#     "zstandard>=0.22",
# ]
# ///
"""sh-nuitka-pack: 通用 Python 单脚本 (PEP 723) Nuitka 单文件打包与启动加速构建器。

所有打包机制与优化（onefile-tempdir-spec 缓存加速、zstandard 体积压缩、
PEP 723 依赖自动对齐、PE 图标注入、unittest 警告排除）均已固化在本脚本。

用法:
    uv run scripts/pack.py <path/to/script.py> [选项]

常见示例:
    # 基础打包（默认 onefile 单文件、自动注入默认双蛇图标、自动缓存加速）:
    uv run scripts/pack.py my_tool.py

    # 文件夹模式（standalone 目录，构建更快，无解压开销）:
    uv run scripts/pack.py my_tool.py --dir

    # GUI 应用（隐藏命令行黑框）:
    uv run scripts/pack.py my_gui.py --gui

    # 仅预演打印构建命令，不执行实际编译:
    uv run scripts/pack.py my_tool.py --dry-run

    # 指定自定义图标与输出目录:
    uv run scripts/pack.py my_tool.py --icon app.ico --output-dir release
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ----------------------------------------------------------------------
# 模块常量与配置
# ----------------------------------------------------------------------
DEFAULT_VERSION = "0.1.0"
NUITKA_MIN_VERSION = "2.5"
ZSTD_MIN_VERSION = "0.22"


def resolve_default_icon(start_path: Path) -> Optional[Path]:
    """定位全局统一的 Python 默认双蛇图标。"""
    curr = start_path.resolve()
    for _ in range(8):
        candidate = (
            curr
            / "docs"
            / "assets"
            / "projects"
            / "python_projects"
            / "python-default.ico"
        )
        if candidate.is_file():
            return candidate.resolve()
        if curr.parent == curr:
            break
        curr = curr.parent
    return None


def parse_pep723_dependencies(script_path: Path) -> Tuple[List[str], Optional[str]]:
    """解析 PEP 723 内联元数据块中的 dependencies 和 requires-python。"""
    text = script_path.read_text(encoding="utf-8")
    block_match = re.search(r"(?ms)^# /// script\s*\n(.*?)\n# ///", text)
    if not block_match:
        return [], None

    content = block_match.group(1)
    deps: List[str] = []
    python_req: Optional[str] = None

    # 解析 requires-python
    req_match = re.search(r'requires-python\s*=\s*"([^"]+)"', content)
    if req_match:
        python_req = req_match.group(1)

    # 解析 dependencies 列表
    deps_match = re.search(r"(?ms)dependencies\s*=\s*\[(.*?)\]", content)
    if deps_match:
        raw_items = deps_match.group(1)
        for line in raw_items.splitlines():
            line = line.strip()
            # 匹配带引号的依赖包名称
            m = re.search(r'["\']([^"\']+)["\']', line)
            if m:
                deps.append(m.group(1))

    return deps, python_req


def parse_script_version(script_path: Path) -> str:
    """从源码中提取 VERSION 或 __version__，未提供时回退到默认版本。"""
    text = script_path.read_text(encoding="utf-8")
    # 优先匹配全大写 VERSION = "..."
    m = re.search(r'^(?:VERSION|__version__)\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    if m:
        return m.group(1)
    return DEFAULT_VERSION


def build_nuitka_args(
    entry_script: Path,
    app_name: str,
    version: str,
    out_dir: Path,
    is_standalone_dir: bool,
    is_gui: bool,
    icon_path: Optional[Path],
    extra_packages: List[str],
) -> List[str]:
    """拼装规范的 Nuitka 编译参数。"""
    exe_filename = f"{app_name}.exe"
    args = [
        "-m", "nuitka",
        "--assume-yes-for-downloads",
        "--standalone",
        "--noinclude-unittest-mode=nofollow",
        f"--output-dir={out_dir}",
        f"--output-filename={exe_filename}",
        f"--product-name={app_name}",
        f"--product-version={version}",
        f"--file-version={version}",
        f"--file-description={app_name} Windows Standalone Utility",
    ]

    # 控制台模式
    if is_gui:
        args.append("--windows-console-mode=disable")
    else:
        args.append("--windows-console-mode=force")

    # 单文件模式与启动缓存目录加速
    if not is_standalone_dir:
        args.append("--onefile")
        # 核心加速参数：固定解压至 %LOCALAPPDATA%/<app_name>/<version>
        # 命中缓存后实现 ~165ms 原生级冷启动
        args.append(f"--onefile-tempdir-spec={{CACHE_DIR}}/{app_name}/{version}")

    # PE 图标注入
    if icon_path and icon_path.is_file():
        args.append(f"--windows-icon-from-ico={icon_path}")
    else:
        print(f"[!] 未指定或未找到有效图标，跳过图标注入", file=sys.stderr)

    # 常见测试包排除防御
    args.extend([
        "--nofollow-import-to=unittest",
        "--nofollow-import-to=test",
        "--nofollow-import-to=tests",
    ])

    # 包含显式声明的包名
    for pkg in extra_packages:
        # 去掉版本限定符 (如 requests>=2.0 -> requests)
        pkg_clean = re.split(r"[<>=!~ ]", pkg)[0].strip()
        if pkg_clean:
            args.append(f"--include-package={pkg_clean}")

    args.append(str(entry_script))
    return args


def run_build(
    entry_script: Path,
    app_name: str,
    version: str,
    out_dir: Path,
    is_standalone_dir: bool,
    is_gui: bool,
    icon_path: Optional[Path],
    dependencies: List[str],
    dry_run: bool,
) -> int:
    """驱动 uv 环境调起 Nuitka 进行编译构建。"""
    nuitka_args = build_nuitka_args(
        entry_script=entry_script,
        app_name=app_name,
        version=version,
        out_dir=out_dir,
        is_standalone_dir=is_standalone_dir,
        is_gui=is_gui,
        icon_path=icon_path,
        extra_packages=dependencies,
    )

    # 组装完整运行命令：使用 uv run --with 动态注入环境依赖，保证编译期解释器完全对齐
    uv_cmd = ["uv", "run", "--no-project"]
    uv_cmd.extend(["--with", f"nuitka>={NUITKA_MIN_VERSION}"])
    uv_cmd.extend(["--with", f"zstandard>={ZSTD_MIN_VERSION}"])
    for dep in dependencies:
        uv_cmd.extend(["--with", dep])
    uv_cmd.extend(["python"])
    uv_cmd.extend(nuitka_args)

    print("\n" + "=" * 70)
    print(f"[*] 构建配置摘要:")
    print(f"  - 目标脚本:    {entry_script}")
    print(f"  - 目标程序名:  {app_name}.exe")
    print(f"  - 程序版本:    v{version}")
    print(f"  - 打包模式:    {'Standalone 文件夹' if is_standalone_dir else 'Onefile 单文件（含缓存加速）'}")
    print(f"  - 界面模式:    {'GUI (无控制台黑框)' if is_gui else 'CLI (强制终端控制台)'}")
    print(f"  - 资源图标:    {icon_path if icon_path else '无'}")
    print(f"  - 关联依赖:    {dependencies if dependencies else '纯标准库'}")
    print(f"  - 输出目录:    {out_dir}")
    print("=" * 70)

    if dry_run:
        print("\n[dry-run] 组装的完整构建命令行:")
        print(" ".join(uv_cmd))
        print("\n[dry-run] 预演完毕，未执行实际编译。")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    print("\n[*] 开始调用 Nuitka 编译（首次编译需检测 MSVC 并生成 C 代码，耗时数分钟）...")
    completed = subprocess.run(uv_cmd, cwd=entry_script.parent)
    if completed.returncode != 0:
        print(f"\n[!] Nuitka 编译失败，退出码: {completed.returncode}", file=sys.stderr)
        print("    提示：请确保已安装 Visual Studio Build Tools (MSVC C++ 编译环境)。", file=sys.stderr)
        return completed.returncode

    exe_file = (out_dir / f"{app_name}.exe") if not is_standalone_dir else (out_dir / f"{app_name}.dist" / f"{app_name}.exe")
    if not exe_file.is_file():
        print(f"\n[!] 未能找到预期产物文件: {exe_file}", file=sys.stderr)
        return 1

    size_mb = exe_file.stat().st_size / (1024 * 1024)
    print("\n" + "=" * 70)
    print(f"[OK] 构建成功！")
    print(f"  - 可执行文件:  {exe_file}")
    print(f"  - 产物体积:    {size_mb:.2f} MB")
    print(f"\n[+] 验证与测速建议:")
    print(f"  1. 运行验证:   & '{exe_file}' --help")
    if not is_standalone_dir:
        print(f"  2. 缓存解压目录: %LOCALAPPDATA%\\{app_name}\\{version}")
        print(f"  3. 测速命令:   powershell -NoProfile -Command \"Measure-Command {{ & '{exe_file}' --help }}\"")
    print("=" * 70 + "\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="sh-nuitka-pack: PEP 723 Python 单脚本 Nuitka 单文件打包与启动加速构建器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("script", help="要打包的目标 Python 脚本文件路径 (如: my_tool.py)")
    parser.add_argument("--app-name", help="产物 exe 名称（默认取脚本文件名不含后缀）")
    parser.add_argument("--version", help="指定程序版本（默认从脚本解析 VERSION 或默认为 0.1.0）")
    parser.add_argument("--dir", action="store_true", help="构建 standalone 文件夹版（默认 onefile 单文件）")
    parser.add_argument("--gui", action="store_true", help="构建 GUI 程序（无黑框控制台，默认保留控制台）")
    parser.add_argument("--icon", help="指定 PE 图标 (.ico 路径)；默认自动定位仓库默认双蛇图标")
    parser.add_argument("--no-icon", action="store_true", help="明确不注入任何图标")
    parser.add_argument("--output-dir", default="dist", help="产物输出目录（默认 dist）")
    parser.add_argument("--dry-run", action="store_true", help="仅打印生成的编译命令，不实际调用编译")

    args = parser.parse_args()

    entry_path = Path(args.script).resolve()
    if not entry_path.is_file():
        print(f"[FATAL] 目标脚本文件不存在: {entry_path}", file=sys.stderr)
        return 1

    # 提取应用名称与版本
    app_name = args.app_name or entry_path.stem
    version = args.version or parse_script_version(entry_path)

    # 提取 PEP 723 依赖
    dependencies, _ = parse_pep723_dependencies(entry_path)

    # 解析图标
    icon_target: Optional[Path] = None
    if not args.no_icon:
        if args.icon:
            icon_target = Path(args.icon).resolve()
        else:
            icon_target = resolve_default_icon(entry_path.parent)

    out_dir = Path(args.output_dir)
    if not out_dir.is_absolute():
        out_dir = (entry_path.parent / out_dir).resolve()

    return run_build(
        entry_script=entry_path,
        app_name=app_name,
        version=version,
        out_dir=out_dir,
        is_standalone_dir=args.dir,
        is_gui=args.gui,
        icon_path=icon_target,
        dependencies=dependencies,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
