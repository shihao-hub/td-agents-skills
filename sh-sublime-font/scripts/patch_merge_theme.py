# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Sublime Merge 内置主题包字体补丁与跨机器环境检查脚本

跨机器无硬编码设计：
- 自动探测 Sublime Merge 安装路径（进程、注册表 Uninstall/App Paths、PATH、多盘符遍历）
- 自动探测字体安装状态（系统全局 Fonts、用户私有 Fonts、注册表）
- 自动定位 Sublime Text 3/4 与 Sublime Merge 的 %APPDATA% 用户配置文件
- 支持通过 --merge-dir 手动指定非标准安装路径
- 默认字体：YaHei Consolas Hybrid，推荐字号：13（低于 13 在部分高分屏下容易发虚模糊）
- 外科手术式无损字体补丁：仅替换主题包内的 font_face/font_size 变量与补齐 commit_file_name_label
- 绝不改动任何官方布局规则、贴图材质与颜色定义，杜绝任何白边、白条或 UI 渲染异常
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import string
import sys
import winreg
import zipfile
from pathlib import Path

# Windows 终端强制 utf-8 输出
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEFAULT_FONT = "YaHei Consolas Hybrid"
DEFAULT_SIZE = 13


def find_sublime_merge_dir(override: str | None = None) -> Path | None:
    """跨机器动态探测 Sublime Merge 安装根目录（绝无硬编码单一盘符或用户名）"""
    if override:
        p = Path(override)
        if (p / "sublime_merge.exe").is_file():
            return p
        if (p / "Packages" / "Theme - Merge.sublime-package").is_file():
            return p
        print(f"[警告] 用户指定的 --merge-dir 无效: {override}")

    # 1. 尝试从 PATH 或 smerge 别名查找
    for cmd in ["sublime_merge", "smerge"]:
        which_path = shutil.which(cmd)
        if which_path:
            p = Path(which_path).resolve().parent
            if (p / "sublime_merge.exe").is_file() and (p / "Packages" / "Theme - Merge.sublime-package").is_file():
                return p

    # 2. 尝试从 Windows 注册表 Uninstall 条目查找 (官方安装包必写)
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for sub in (
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ):
            try:
                with winreg.OpenKey(root, sub) as k:
                    for i in range(winreg.QueryInfoKey(k)[0]):
                        try:
                            subkey_name = winreg.EnumKey(k, i)
                            with winreg.OpenKey(k, subkey_name) as sk:
                                disp, _ = winreg.QueryValueEx(sk, "DisplayName")
                                if "sublime merge" in str(disp).lower():
                                    loc, _ = winreg.QueryValueEx(sk, "InstallLocation")
                                    p = Path(str(loc))
                                    if (p / "sublime_merge.exe").is_file() and (p / "Packages" / "Theme - Merge.sublime-package").is_file():
                                        return p
                        except Exception:
                            pass
            except Exception:
                pass

    # 3. 尝试从注册表 App Paths 查找
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for app_name in ["sublime_merge.exe", "smerge.exe"]:
            try:
                with winreg.OpenKey(root, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{app_name}") as k:
                    val, _ = winreg.QueryValueEx(k, "")
                    p = Path(str(val)).resolve().parent
                    if (p / "sublime_merge.exe").is_file() and (p / "Packages" / "Theme - Merge.sublime-package").is_file():
                        return p
            except Exception:
                pass

    # 4. 遍历所有存在的本地盘符的常见安装目录（兼容 C:, D:, E: 等盘符与各种安装器）
    drive_candidates = []
    for letter in string.ascii_uppercase:
        drive_root = Path(f"{letter}:\\")
        if drive_root.exists():
            drive_candidates.extend([
                drive_root / "Program Files" / "Sublime Merge",
                drive_root / "Program Files (x86)" / "Sublime Merge",
                drive_root / "Sublime Merge",
                drive_root / "Tools" / "Sublime Merge",
                drive_root / "Software" / "Sublime Merge",
            ])

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        drive_candidates.extend([
            Path(local_app_data) / "Programs" / "Sublime Merge",
            Path(local_app_data) / "Sublime Merge",
        ])

    for c in drive_candidates:
        try:
            if (c / "sublime_merge.exe").is_file() and (c / "Packages" / "Theme - Merge.sublime-package").is_file():
                return c
        except Exception:
            pass

    return None


def get_merge_pkg_paths(merge_dir: Path) -> tuple[Path, Path]:
    pkg = merge_dir / "Packages" / "Theme - Merge.sublime-package"
    orig = merge_dir / "Packages" / "Theme - Merge.sublime-package.original"
    return pkg, orig


def check_font_installed(font_name: str) -> bool:
    """检查字体是否已在 Windows 中安装（支持全局 Fonts、用户私有 Fonts、注册表三种方式）"""
    keywords = font_name.lower().split()

    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(root, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts") as k:
                num_values = winreg.QueryInfoKey(k)[1]
                for i in range(num_values):
                    val_name, _, _ = winreg.EnumValue(k, i)
                    v_lower = val_name.lower()
                    if all(kw in v_lower for kw in keywords):
                        return True
        except Exception:
            pass

    font_dirs = []
    windir = os.environ.get("WINDIR") or os.environ.get("SystemRoot")
    if windir:
        font_dirs.append(Path(windir) / "Fonts")
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        font_dirs.append(Path(local_app_data) / "Microsoft" / "Windows" / "Fonts")

    for fdir in font_dirs:
        if fdir.is_dir():
            try:
                for f in fdir.iterdir():
                    fname = f.name.lower()
                    if all(kw in fname for kw in keywords):
                        return True
            except Exception:
                pass

    return False


def get_st_settings_path() -> Path | None:
    """动态获取当前用户的 Sublime Text 3 或 4 配置文件路径"""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    for name in ["Sublime Text", "Sublime Text 3"]:
        p = Path(appdata) / name / "Packages" / "User" / "Preferences.sublime-settings"
        if p.parent.is_dir():
            return p
    return None


def get_sm_user_dir() -> Path | None:
    """动态获取当前用户的 Sublime Merge User 目录"""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    p = Path(appdata) / "Sublime Merge" / "Packages" / "User"
    if p.is_dir():
        return p
    return None


def get_sm_settings_path() -> Path | None:
    """动态获取当前用户的 Sublime Merge 配置文件路径"""
    u = get_sm_user_dir()
    if u:
        return u / "Preferences.sublime-settings"
    return None


def extract_setting_value(path: Path, key: str) -> str:
    """从包含注释或尾部逗号的 sublime-settings 中提取配置值"""
    if not path.is_file():
        return "(文件不存在)"
    try:
        txt = path.read_text(encoding="utf-8")
        m = re.search(rf'"{key}"\s*:\s*([^,\r\n}}]+)', txt)
        if m:
            val = m.group(1).strip()
            val = val.strip('"\'')
            return val
    except Exception as e:
        return f"(读取失败: {e})"
    return "(未配置)"


def cmd_status(args: argparse.Namespace) -> int:
    font = args.font or DEFAULT_FONT
    font_ok = check_font_installed(font)
    print(f"[系统字体] {font}: {'已安装' if font_ok else '未检测到（请安装字体）'}")

    st_file = get_st_settings_path()
    if st_file and st_file.is_file():
        ff = extract_setting_value(st_file, "font_face")
        fs = extract_setting_value(st_file, "font_size")
        print(f"[Sublime Text] 配置文件: {st_file}")
        print(f"               font_face: {ff}, font_size: {fs}")
    else:
        print("[Sublime Text] 未检测到用户配置文件")

    sm_file = get_sm_settings_path()
    if sm_file and sm_file.is_file():
        ff = extract_setting_value(sm_file, "font_face")
        fs = extract_setting_value(sm_file, "font_size")
        print(f"[Sublime Merge] 配置文件: {sm_file}")
        print(f"                font_face: {ff}, font_size: {fs}")
    else:
        print("[Sublime Merge] 未检测到用户配置文件")

    merge_dir = find_sublime_merge_dir(args.merge_dir)
    if not merge_dir:
        print("[Sublime Merge] 未自动探测到安装目录（若装在特殊路径，可使用 --merge-dir 指定）")
        return 0

    pkg, orig = get_merge_pkg_paths(merge_dir)
    print(f"[Sublime Merge] 安装目录: {merge_dir}")
    print(f"                主题包: {pkg.name} ({'存在' if pkg.is_file() else '不存在'})")
    print(f"                原版备份: {orig.name} ({'已备份，可随时 restore' if orig.is_file() else '未备份'})")

    if pkg.is_file():
        try:
            with zipfile.ZipFile(pkg, "r") as z:
                theme_txt = z.read("Merge.sublime-theme").decode("utf-8")
                m_face = re.search(r'"font_face":\s*"([^"]+)"', theme_txt)
                m_size = re.search(r'"font_size":\s*(\d+)', theme_txt)
                current_font = m_face.group(1) if m_face else "未知"
                current_size = m_size.group(1) if m_size else "未知"
                print(f"                主题包内 font_face: {current_font}, font_size: {current_size}")
        except Exception as e:
            print(f"                主题包读取失败: {e}")

    return 0


def cmd_patch(args: argparse.Namespace) -> int:
    font = args.font or DEFAULT_FONT
    size = int(args.font_size or DEFAULT_SIZE)

    merge_dir = find_sublime_merge_dir(args.merge_dir)
    if not merge_dir:
        print("[错误] 未能自动定位 Sublime Merge 安装目录，请通过 --merge-dir 指定路径。")
        return 1

    pkg, orig = get_merge_pkg_paths(merge_dir)
    if not pkg.is_file() and not orig.is_file():
        print(f"[错误] 未找到主题包文件：{pkg}")
        return 1

    # 1. 确保存在原版备份
    if not orig.is_file():
        print(f"正在创建原版备份：{orig.name}...")
        try:
            shutil.copy2(pkg, orig)
        except PermissionError:
            print(f"[权限不足] 无法写入 {orig}，请以管理员身份运行终端。")
            return 1
    else:
        print(f"已存在原版备份：{orig.name}，从原版读取基础文件。")

    # 2. 从原版读取基准数据（绝不重新解析/序列化整套 520+ 规则与贴图，避免破坏 UI）
    print("正在解压原版并执行外科手术式无损字体替换...")
    with zipfile.ZipFile(orig, "r") as zin:
        file_data = {name: zin.read(name) for name in zin.namelist()}

    base_txt = file_data["Merge.sublime-theme"].decode("utf-8")

    # 外科手术 1：精准替换 Merge.sublime-theme 变量区的 font_face 与 font_size
    vars_pattern = re.compile(
        r'("font_face":\s*)"[^"]+",\s*'
        r'("font_size":\s*)\d+,\s*'
        r'("font_size_sm":\s*)\d+,\s*'
        r'("font_size_lg":\s*)\d+,',
    )
    new_vars_block = (
        f'\\1"{font}",\n'
        f'\\2{size},\n'
        f'\\3{max(10, size - 1)},\n'
        f'\\4{size + 1},'
    )
    patched_txt, n_vars = vars_pattern.subn(new_vars_block, base_txt, count=1)
    if n_vars == 0:
        print("[警告] 未匹配到标准变量块，尝试逐行替换...")
        patched_txt = re.sub(r'("font_face":\s*)"[^"]+"', rf'\1"{font}"', base_txt, count=1)
        patched_txt = re.sub(r'("font_size":\s*)\d+', rf'\g<1>{size}', patched_txt, count=1)
        patched_txt = re.sub(r'("font_size_sm":\s*)\d+', rf'\g<1>{max(10, size - 1)}', patched_txt, count=1)
        patched_txt = re.sub(r'("font_size_lg":\s*)\d+', rf'\g<1>{size + 1}', patched_txt, count=1)

    # 外科手术 2：在 commit_file_name_label 规则中精准补齐 "font.face": "var(font_face)"
    label_pattern = re.compile(
        r'("class":\s*"commit_file_name_label",\s*'
        r'"parents":\s*\[\{"class":\s*"commit_summary_control"\}\],\s*)'
        r'(?!"font\.face")',
    )
    patched_txt = label_pattern.sub(r'\1"font.face": "var(font_face)",\n\t\t\t', patched_txt)

    file_data["Merge.sublime-theme"] = patched_txt.encode("utf-8")

    # 3. 写入临时包并原子替换
    tmp_pkg = pkg.with_suffix(".tmp")
    with zipfile.ZipFile(tmp_pkg, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for name, data in file_data.items():
            zout.writestr(name, data)

    shutil.move(tmp_pkg, pkg)
    print(f"[成功] 已成功将 Theme - Merge.sublime-package 的 font_face 打补丁为: {font}, font_size 为: {size}")
    print("提示：仅修改字体与字号，100% 保持官方原版样式与贴图无瑕！")
    print("请彻底退出并重启 Sublime Merge 即可生效！")
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    merge_dir = find_sublime_merge_dir(args.merge_dir)
    if not merge_dir:
        print("[错误] 未能自动定位 Sublime Merge 安装目录，可通过 --merge-dir 指定。")
        return 1

    pkg, orig = get_merge_pkg_paths(merge_dir)
    if not orig.is_file():
        print(f"[错误] 未找到备份文件 {orig}，无法还原。")
        return 1

    print(f"正在从备份 {orig.name} 恢复原版主题包...")
    try:
        shutil.copy2(orig, pkg)
    except PermissionError:
        print(f"[权限不足] 无法写入 {pkg}，请以管理员身份运行终端。")
        return 1
    print("[成功] 已成功恢复原版内置主题包！重启 Sublime Merge 即可恢复系统默认字体与原始样式。")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    font = args.font or DEFAULT_FONT
    size = int(args.font_size or DEFAULT_SIZE)

    # 1. 配置 Sublime Text
    st_file = get_st_settings_path()
    if st_file:
        try:
            content = st_file.read_text(encoding="utf-8") if st_file.is_file() else "{\n}\n"
            if '"font_face"' in content:
                content = re.sub(r'("font_face":\s*)"[^"]+"', rf'\1"{font}"', content)
            else:
                content = re.sub(r'\{', f'{{\n\t"font_face": "{font}",', content, count=1)
            if '"font_size"' in content:
                content = re.sub(r'("font_size":\s*)\d+', rf'\g<1>{size}', content)
            else:
                content = re.sub(r'\{', f'{{\n\t"font_size": {size},', content, count=1)
            st_file.write_text(content, encoding="utf-8")
            print(f"[成功] 已更新 Sublime Text 配置: {st_file}")
        except Exception as e:
            print(f"[失败] 更新 Sublime Text 配置失败: {e}")

    # 2. 配置 Sublime Merge
    sm_user = get_sm_user_dir()
    if sm_user:
        try:
            sm_file = sm_user / "Preferences.sublime-settings"
            content = sm_file.read_text(encoding="utf-8") if sm_file.is_file() else "{\n}\n"
            if '"font_face"' in content:
                content = re.sub(r'("font_face":\s*)"[^"]+"', rf'\1"{font}"', content)
            else:
                content = re.sub(r'\{', f'{{\n\t"font_face": "{font}",', content, count=1)
            if '"font_size"' in content:
                content = re.sub(r'("font_size":\s*)\d+', rf'\g<1>{size}', content)
            else:
                content = re.sub(r'\{', f'{{\n\t"font_size": {size},', content, count=1)
            sm_file.write_text(content, encoding="utf-8")
            print(f"[成功] 已更新 Sublime Merge 配置: {sm_file}")
        except Exception as e:
            print(f"[失败] 更新 Sublime Merge 配置失败: {e}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Sublime Merge 内置主题包字体补丁及检查")
    parser.add_argument("--merge-dir", default=None, help="手动指定 Sublime Merge 安装目录（默认全自动探测）")
    subparsers = parser.add_subparsers(dest="action")

    p_status = subparsers.add_parser("status", help="检查字体与配置状态")
    p_status.add_argument("--font", default=DEFAULT_FONT, help="字体名称")

    p_patch = subparsers.add_parser("patch", help="应用内置主题包外科手术式无损字体补丁")
    p_patch.add_argument("--font", default=DEFAULT_FONT, help="字体名称")
    p_patch.add_argument("--font-size", type=int, default=DEFAULT_SIZE, help="字体大小 (默认 13)")

    p_restore = subparsers.add_parser("restore", help="恢复原版主题包")

    p_config = subparsers.add_parser("config", help="更新用户 Preferences.sublime-settings")
    p_config.add_argument("--font", default=DEFAULT_FONT, help="字体名称")
    p_config.add_argument("--font-size", type=int, default=DEFAULT_SIZE, help="字体大小 (默认 13)")

    args = parser.parse_args()
    action = args.action or "status"

    if action == "status":
        return cmd_status(args)
    elif action == "patch":
        return cmd_patch(args)
    elif action == "restore":
        return cmd_restore(args)
    elif action == "config":
        return cmd_config(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
