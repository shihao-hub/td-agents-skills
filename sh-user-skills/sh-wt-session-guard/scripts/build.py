# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "nuitka>=4.0.0",
#     "psutil>=7.0.0",
# ]
# ///
"""
========================================================================================
wt-session-guard 自动化双镜像编译与 PE Subsystem 校验流水线
========================================================================================
【架构目标】
1. 编译生成标准 CLI 控制台二进制: dist/wt_session_guard.exe (PE Subsystem 3, CUI)
2. 自动派生无窗口静默守护与自启镜像: dist/wt_session_guardw.exe (PE Subsystem 2, GUI)
3. 严格执行 PE 文件头校验，彻底杜绝手动敲编译命令导致的“漏转 GUI 弹黑框”退化。
========================================================================================
"""

from __future__ import annotations

from pathlib import Path
import shutil
import struct
import subprocess
import sys


def get_pe_subsystem(exe_path: Path) -> int:
    """读取 PE 二进制文件的 OptionalHeader.Subsystem 字段 (2=GUI, 3=CUI)"""
    with open(exe_path, "rb") as f:
        dos_header = f.read(64)
        pe_offset = struct.unpack_from("<I", dos_header, 0x3C)[0]
        # PE Signature (4) + COFF Header (20) + OptionalHeader.Subsystem (offset 68 in OptionalHeader)
        subsystem_pos = pe_offset + 4 + 20 + 68
        f.seek(subsystem_pos)
        return struct.unpack("<H", f.read(2))[0]


def patch_pe_subsystem_to_gui(src_exe: Path, target_exe: Path) -> None:
    """复制并修改 PE 文件头，将 Subsystem 改为 2 (IMAGE_SUBSYSTEM_WINDOWS_GUI)"""
    shutil.copyfile(src_exe, target_exe)
    with open(target_exe, "r+b") as f:
        dos_header = f.read(64)
        pe_offset = struct.unpack_from("<I", dos_header, 0x3C)[0]
        subsystem_pos = pe_offset + 4 + 20 + 68
        f.seek(subsystem_pos)
        f.write(struct.pack("<H", 2))


def main() -> None:
    root_dir = Path(__file__).resolve().parent.parent
    scripts_dir = root_dir / "scripts"
    dist_dir = root_dir / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    target_script = scripts_dir / "wt_session_guard.py"
    cli_exe = dist_dir / "wt_session_guard.exe"
    gui_exe = dist_dir / "wt_session_guardw.exe"

    print("==================================================================")
    print("wt-session-guard 自动化构建开始...")
    print(f"源码路径: {target_script}")
    print(f"产物目录: {dist_dir}")
    print("==================================================================")

    # 1. 执行 Nuitka 单文件编译生成 CLI 二进制
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--onefile",
        f"--output-dir={dist_dir}",
        "--remove-output",
        str(target_script),
    ]

    print("[*] 正在执行 Nuitka 单文件编译 (含 psutil 依赖)...")
    res = subprocess.run(cmd, cwd=root_dir)
    if res.returncode != 0:
        print(f"[-] Nuitka 编译失败 (Exit Code: {res.returncode})")
        sys.exit(res.returncode)

    if not cli_exe.exists():
        print(f"[-] 未找到产物: {cli_exe}")
        sys.exit(1)

    print(f"[+] 成功生成 CLI 控制台二进制: {cli_exe.name}")

    # 2. 派生无窗口 GUI 二进制镜像
    print(f"[*] 正在派生无窗口静默守护镜像: {gui_exe.name}...")
    patch_pe_subsystem_to_gui(cli_exe, gui_exe)
    print(f"[+] 成功生成无窗口静默镜像: {gui_exe.name}")

    # 3. 严格执行 PE Subsystem 自检断言（防退化不变式）
    sub_cli = get_pe_subsystem(cli_exe)
    sub_gui = get_pe_subsystem(gui_exe)

    print(f"[*] 执行 PE Subsystem 自检断言:")
    print(f"    ├─ {cli_exe.name}: Subsystem = {sub_cli} (预期: 3 CUI 控制台)")
    print(f"    └─ {gui_exe.name}: Subsystem = {sub_gui} (预期: 2 GUI 无窗口)")

    assert sub_cli == 3, f"断言失败: {cli_exe.name} Subsystem 不是 3 (当前: {sub_cli})"
    assert sub_gui == 2, f"断言失败: {gui_exe.name} Subsystem 不是 2 (当前: {sub_gui})"

    print("\n[+] 全套构建自检验收 100% 通过！双镜像已就绪。")
    print("    - 终端日常维护使用: dist/wt_session_guard.exe (有控制台回显)")
    print("    - 后台守护与开机自启: dist/wt_session_guardw.exe (物理级 0 闪烁 0 黑框)")


if __name__ == "__main__":
    main()
