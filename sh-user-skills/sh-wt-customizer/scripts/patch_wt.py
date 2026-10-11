# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
========================================================================================
Windows Terminal (wt) 独立版定制、图标注入、任务栏与右键菜单全链路接管与无损复原引擎
========================================================================================
"""

import argparse
import ctypes
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import winreg
import zipfile
from pathlib import Path

# 控制台 UTF-8 输出
if sys.platform == "win32":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
ICONS_DIR = SCRIPT_DIR.parent / "icons"

RCEDIT_DEFAULT_PATH = Path(r"D:\Users\language_projects_bin\rcedit.exe")
DEFAULT_TARGET_DIRS = [
    Path(r"D:\Users\Softwares\WindowsTerminal"),
    Path(r"D:\Users\tools\WindowsTerminal"),
]

STATE_FILE = Path(os.path.expandvars(r"%APPDATA%\language_projects\wt_customizer\state.json"))
APP_PATHS_KEY = r"Software\Microsoft\Windows\CurrentVersion\App Paths\wt.exe"

# Nilesoft Shell 典型安装目录候选
NILESOFT_CANDIDATE_DIRS = [
    Path(r"D:\Program Files\Nilesoft Shell\imports"),
    Path(r"C:\Program Files\Nilesoft Shell\imports"),
]


def load_state() -> dict:
    if STATE_FILE.is_file():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def get_available_styles() -> dict[str, Path]:
    if not ICONS_DIR.is_dir():
        return {}
    return {ico.stem: ico for ico in ICONS_DIR.glob("*.ico")}


def add_to_user_path(directory: Path) -> bool:
    dir_str = str(directory)
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            try:
                current_path, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                current_path = ""
            paths = [p.strip() for p in current_path.split(";") if p.strip()]
            if dir_str not in paths:
                new_path = dir_str + (";" + current_path if current_path else "")
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                try:
                    HWND_BROADCAST = 0xFFFF
                    WM_SETTINGCHANGE = 0x001A
                    SMTO_ABORTIFHUNG = 0x0002
                    result = ctypes.c_ulong()
                    ctypes.windll.user32.SendMessageTimeoutW(
                        HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment", SMTO_ABORTIFHUNG, 3000, ctypes.byref(result)
                    )
                except Exception:
                    pass
                print(f"[+] 已将 {dir_str} 添加至用户环境变量 Path 最顶端")
                return True
            else:
                print(f"[*] 用户 PATH 中已存在: {dir_str}")
                return True
    except Exception as e:
        print(f"[-] 写入环境变量 PATH 失败: {e}")
        return False


def remove_from_user_path(directory: Path) -> bool:
    dir_str = str(directory)
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            try:
                current_path, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                return True
            paths = [p.strip() for p in current_path.split(";") if p.strip()]
            if dir_str in paths:
                new_paths = [p for p in paths if p != dir_str]
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, ";".join(new_paths))
                try:
                    HWND_BROADCAST = 0xFFFF
                    WM_SETTINGCHANGE = 0x001A
                    SMTO_ABORTIFHUNG = 0x0002
                    result = ctypes.c_ulong()
                    ctypes.windll.user32.SendMessageTimeoutW(
                        HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment", SMTO_ABORTIFHUNG, 3000, ctypes.byref(result)
                    )
                except Exception:
                    pass
                print(f"[+] 已从用户环境变量 Path 中移除: {dir_str}")
                return True
    except Exception as e:
        print(f"[-] 移除环境变量 PATH 失败: {e}")
        return False


def download_file(url: str, dest_path: Path, desc: str = "文件") -> bool:
    print(f"[*] 正在自动下载 {desc}...")
    print(f"    来源: {url}")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    urls = [url]
    if "github.com" in url:
        urls.append(f"https://ghproxy.net/{url}")

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    for u in urls:
        try:
            req = urllib.request.Request(u, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp, open(dest_path, "wb") as f:
                total_len = resp.headers.get("Content-Length")
                total = int(total_len) if total_len else 0
                downloaded = 0
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = downloaded / total * 100
                        print(f"\r    进度: {pct:.1f}% ({downloaded // 1024}/{total // 1024} KB)", end="", flush=True)
                print()
            print(f"[+] 下载完成: {dest_path}")
            return True
        except Exception as e:
            print(f"\n[-] 从 {u} 下载失败: {e}，尝试备用线路...")
    return False


def auto_setup_rcedit() -> Path | None:
    dest = SCRIPT_DIR / "rcedit.exe"
    url = "https://github.com/electron/rcedit/releases/download/v2.0.0/rcedit-x64.exe"
    if download_file(url, dest, "rcedit.exe"):
        return dest
    return None


def auto_setup_windows_terminal(custom_dir: str | None = None) -> Path | None:
    if custom_dir:
        target_dir = Path(custom_dir).resolve()
    elif Path(r"D:\Users\Softwares").is_dir() or Path("D:/").is_dir():
        target_dir = Path(r"D:\Users\Softwares\WindowsTerminal")
    else:
        target_dir = Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\WindowsTerminal"))

    print(f"[*] 准备安装 Windows Terminal 独立版至: {target_dir}")

    api_url = "https://api.github.com/repos/microsoft/terminal/releases/latest"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    download_url = None
    asset_name = None

    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.startswith("Microsoft.WindowsTerminal_") and name.endswith("_x64.zip") and "msixbundle" not in name:
                    download_url = asset.get("browser_download_url")
                    asset_name = name
                    break
    except Exception as e:
        print(f"[-] 查询 GitHub API 异常: {e}，使用固定推荐稳定版下载源...")

    if not download_url:
        download_url = "https://github.com/microsoft/terminal/releases/download/v1.25.2733.0/Microsoft.WindowsTerminal_1.25.2733.0_x64.zip"
        asset_name = "Microsoft.WindowsTerminal_1.25.2733.0_x64.zip"

    temp_zip = target_dir.parent / (asset_name or "WindowsTerminal_x64.zip")
    if not download_file(download_url, temp_zip, "Windows Terminal 官方免安装包"):
        return None

    print(f"[*] 正在解压缩至 {target_dir}...")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(temp_zip, "r") as zf:
            zf.extractall(target_dir)
        print(f"[+] 解压完成！")
    except Exception as e:
        print(f"[-] 解压失败: {e}")
        return None
    finally:
        try:
            temp_zip.unlink(missing_ok=True)
        except Exception:
            pass

    add_to_user_path(target_dir)
    return target_dir


def ensure_rcedit(custom_path: str | None = None, auto_download: bool = False) -> Path:
    if custom_path:
        p = Path(custom_path).resolve()
        if p.is_file():
            return p
        raise FileNotFoundError(f"指定的 rcedit 不存在: {p}")

    # 候选路径：脚本同级、当前工作目录、项目默认路径
    candidates = [
        SCRIPT_DIR / "rcedit.exe",
        SCRIPT_DIR / "rcedit-x64.exe",
        Path.cwd() / "rcedit.exe",
        Path.cwd() / "rcedit-x64.exe",
        RCEDIT_DEFAULT_PATH,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    path_which = shutil.which("rcedit") or shutil.which("rcedit-x64")
    if path_which:
        return Path(path_which)

    if auto_download:
        downloaded = auto_setup_rcedit()
        if downloaded and downloaded.is_file():
            return downloaded

    raise RuntimeError("未找到 rcedit.exe！在新电脑上可直接传入 --auto-setup 参数，脚本将全自动下载并配置。\n下载地址: https://github.com/electron/rcedit/releases")


def resolve_icon_path(style: str | None, custom_icon: str | None) -> Path:
    if custom_icon:
        p = Path(custom_icon).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"未找到指定的自定义 ICO 文件: {p}")
        return p

    style_map = get_available_styles()
    target_style = style or "pure_dark"
    if target_style in style_map:
        return style_map[target_style]

    if "pure_dark" in style_map:
        return style_map["pure_dark"]
    if "titanium" in style_map:
        return style_map["titanium"]

    if style_map:
        return list(style_map.values())[0]

    raise ValueError(f"未知图标款式: {target_style}。可用款式: {list(style_map.keys())}")


def find_target_exes(custom_dir: str | None = None) -> list[Path]:
    dirs = [Path(custom_dir).resolve()] if custom_dir else DEFAULT_TARGET_DIRS
    exes: list[Path] = []
    for base_dir in dirs:
        if base_dir.is_dir():
            wt_exe = base_dir / "wt.exe"
            main_exe = base_dir / "WindowsTerminal.exe"
            if main_exe.is_file():
                exes.append(main_exe)
            if wt_exe.is_file():
                exes.append(wt_exe)
            if exes:
                return exes

    which_wt = shutil.which("wt.exe") or shutil.which("wt")
    if which_wt:
        p = Path(which_wt).resolve()
        if "WindowsApps" not in str(p) and p.is_file():
            exes.append(p)
            companion = p.parent / "WindowsTerminal.exe"
            if companion.is_file():
                exes.append(companion)
    return exes


def is_process_running(exe_name: str) -> bool:
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Get-Process -Name '{exe_name}' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return bool(res.stdout.strip())
    except Exception:
        return False


def patch_pe_exe(exe_path: Path, ico_path: Path, rcedit_bin: Path) -> bool:
    cmd = [str(rcedit_bin), str(exe_path), "--set-icon", str(ico_path)]
    for _ in range(3):
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if res.returncode == 0:
                print(f"[+] 成功烧录 PE 图标资源: {exe_path.name}")
                return True
            time.sleep(0.3)
        except Exception:
            time.sleep(0.3)

    print(f"[-] 烧录 PE 图标失败: {exe_path}")
    if is_process_running("WindowsTerminal"):
        print("    ⚠️ 检测到 Windows Terminal 正在运行中！Windows 对正在运行的 exe 加了独占执行锁。")
        print("    💡 请彻底关闭屏幕上正在运行的所有 Windows Terminal 窗口后再次运行即可写入！")
    return False


def apply_app_paths(wt_exe_path: str) -> None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APP_PATHS_KEY, 0, winreg.KEY_READ) as k:
            cur_val, _ = winreg.QueryValueEx(k, "")
    except Exception:
        cur_val = ""

    state = load_state()
    if "original_app_paths" not in state:
        state["original_app_paths"] = cur_val or r"C:\Program Files\WindowsApps\Microsoft.WindowsTerminal_1.24.12741.0_x64__8wekyb3d8bbwe\wt.exe"
        save_state(state)

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, APP_PATHS_KEY) as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, wt_exe_path)
        print(f"[+] 已劫持注册表 App Paths wt.exe -> {wt_exe_path} (保证 Win+R 立即生效)")
    except Exception as e:
        print(f"[-] 配置 App Paths 失败: {e}")


def revert_app_paths() -> None:
    state = load_state()
    orig = state.get("original_app_paths")
    if orig:
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, APP_PATHS_KEY) as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, orig)
            print(f"[+] 已恢复注册表 App Paths wt.exe -> {orig}")
        except Exception as e:
            print(f"[-] 恢复 App Paths 失败: {e}")


def update_shortcut(lnk_path: Path, ico_target: str, exe_target: str, desc: str = "") -> bool:
    user_home = str(Path.home())
    ps_cmd = f"""
$wsh = New-Object -ComObject WScript.Shell
$sc = $wsh.CreateShortcut('{str(lnk_path)}')
$sc.TargetPath = '{exe_target}'
$sc.WorkingDirectory = '{user_home}'
$sc.Description = '{desc}'
$sc.IconLocation = '{ico_target}, 0'
$sc.Save()
"""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return res.returncode == 0
    except Exception:
        return False


def get_nilesoft_dir() -> Path | None:
    for d in NILESOFT_CANDIDATE_DIRS:
        if d.is_dir():
            return d
    return None


def apply_nilesoft(exe_target: str) -> None:
    nilesoft_dir = get_nilesoft_dir()
    if not nilesoft_dir:
        return

    term_nss = nilesoft_dir / "terminal.nss"
    mod_nss = nilesoft_dir / "modify.nss"

    # 1. 备份
    for f in [term_nss, mod_nss]:
        if f.is_file():
            bak = f.with_suffix(".nss.bak")
            if not bak.is_file():
                try:
                    shutil.copy2(f, bak)
                    print(f"[+] 已安全备份 Nilesoft Shell 配置: {bak.name}")
                except Exception as e:
                    print(f"[-] 备份 {f.name} 失败: {e}")

    safe_target = exe_target.replace("\\", "\\\\")

    # 2. 补丁 terminal.nss
    if term_nss.is_file():
        try:
            content = term_nss.read_text(encoding="utf-8")
            pat = r"(item\(where=package\.exists\(\"WindowsTerminal\"\) title=title\.Windows_Terminal tip=tip_run_admin admin=has_admin image=')(.*?)(' cmd=')(.*?)(' arg=)"
            if re.search(pat, content):
                content = re.sub(pat, rf"\g<1>{safe_target}\g<3>{safe_target}\g<5>", content)
                term_nss.write_text(content, encoding="utf-8", newline="\n")
                print("[+] 已更新 Nilesoft Shell terminal.nss 二级终端菜单命令与图标")
        except Exception as e:
            print(f"[-] 更新 terminal.nss 失败: {e}")

    # 3. 补丁 modify.nss (隐藏系统 Store 版并用独立版接管启动命令与图标)
    if mod_nss.is_file():
        try:
            content = mod_nss.read_text(encoding="utf-8")
            patch_snippet = f"""
// Hide default Store WT item and replace with custom WT launcher
modify(mode=mode.multiple find='在终端中打开|open in terminal' vis=vis.remove)
item(type='dir|drive|back' title='在终端中打开(T)' pos=4 image='{safe_target}' cmd='{safe_target}' arg='-d "@sel.path\\."')
"""
            old_rule_pat = r"// (?:Custom Windows Terminal Icon|Hide default Store WT item)[^\n]*\n(?:(?:modify|item)\([^\n]+\)\n?)+"
            if re.search(old_rule_pat, content):
                content = re.sub(old_rule_pat, "", content).rstrip() + "\n" + patch_snippet
            elif "在终端中打开" not in content and "open in terminal" not in content:
                content += patch_snippet
            else:
                content = content.rstrip() + "\n" + patch_snippet

            mod_nss.write_text(content, encoding="utf-8", newline="\n")
            print("[+] 已更新 Nilesoft Shell modify.nss 顶层右键菜单独立版接管指令")
        except Exception as e:
            print(f"[-] 更新 modify.nss 失败: {e}")


def revert_nilesoft() -> None:
    nilesoft_dir = get_nilesoft_dir()
    if not nilesoft_dir:
        return

    for name in ["terminal.nss", "modify.nss"]:
        target = nilesoft_dir / name
        bak = nilesoft_dir / f"{name}.bak"
        if bak.is_file():
            try:
                shutil.copy2(bak, target)
                bak.unlink()
                print(f"[+] 已无损还原 Nilesoft Shell 配置文件: {name}")
            except Exception as e:
                print(f"[-] 还原 {name} 失败: {e}")


def refresh_shell(shortcuts: list[Path]) -> None:
    now = time.time()
    for s in shortcuts:
        try:
            if s.is_file():
                os.utime(s, (now, now))
        except Exception:
            pass

    try:
        subprocess.run(
            ["ie4uinit.exe", "-show"],
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except Exception:
        pass

    try:
        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_FLUSH = 0x1000
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_FLUSH, None, None)
    except Exception:
        pass


def restart_explorer() -> None:
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Stop-Process -Name explorer -Force; Start-Sleep -Milliseconds 800; if (-not (Get-Process explorer -ErrorAction SilentlyContinue)) { Start-Process explorer.exe }"],
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        print("[+] 已平稳重启 Windows Explorer 刷新图标与外壳缓存")
    except Exception as e:
        print(f"[-] 重启 Explorer 异常: {e}")


def apply(style: str | None, custom_icon: str | None, target_dir: str | None, restart_exp: bool, custom_rcedit: str | None = None, auto_setup: bool = False) -> int:
    ico_path = resolve_icon_path(style, custom_icon)
    print(f"[*] 选定定制图标: {ico_path.name} (路径: {ico_path})")

    target_exes = find_target_exes(target_dir)
    if not target_exes:
        if auto_setup:
            print("[*] 正在全自动下载部署 Windows Terminal 独立版...")
            installed_dir = auto_setup_windows_terminal(target_dir)
            if installed_dir:
                target_exes = find_target_exes(str(installed_dir))

        if not target_exes:
            print("[-] 未定位到免安装独立版 WindowsTerminal，请确认解压目录。")
            print("💡 提示：在新电脑上可直接传入 --auto-setup 参数，脚本将全自动从 GitHub 下载最新独立版并完成全链路部署。")
            return 1

    rcedit_bin = ensure_rcedit(custom_rcedit, auto_download=auto_setup)
    for exe in target_exes:
        patch_pe_exe(exe, ico_path, rcedit_bin)

    main_wt = str(target_exes[0])
    wt_bin = str(target_exes[1]) if len(target_exes) > 1 else main_wt

    # 1. 注册表 App Paths
    apply_app_paths(wt_bin)

    # 2. 快捷方式
    updated_shortcuts: list[Path] = []
    taskbar_dir = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar"))
    taskbar_dir.mkdir(parents=True, exist_ok=True)
    taskbar_lnk = taskbar_dir / "Windows Terminal.lnk"
    if update_shortcut(taskbar_lnk, str(ico_path), main_wt, "Windows Terminal (Customized)"):
        updated_shortcuts.append(taskbar_lnk)
        print(f"[+] 已同步任务栏快捷方式: {taskbar_lnk}")

    start_menu_lnk = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Windows Terminal.lnk"))
    if update_shortcut(start_menu_lnk, str(ico_path), main_wt, "Windows Terminal"):
        updated_shortcuts.append(start_menu_lnk)
        print(f"[+] 已同步开始菜单快捷方式: {start_menu_lnk}")

    # 3. Nilesoft Shell
    apply_nilesoft(main_wt)

    # 记录安装状态
    state = load_state()
    state["installed_dir"] = str(Path(main_wt).parent)
    state["style"] = ico_path.stem
    save_state(state)

    # 4. 外壳刷新
    refresh_shell(updated_shortcuts)
    print("[+] 已广播 Windows 外壳与图标缓存刷新通知 (SHChangeNotify FLUSH)")

    if restart_exp:
        restart_explorer()

    print("\n" + "=" * 70)
    print("✅ Windows Terminal 定制与全链路守护已成功应用！")
    print(f"   生效图标: {ico_path.name}")
    print(f"   程序目标: {main_wt}")
    print("=" * 70)
    return 0


def revert(restart_exp: bool, remove_path: bool = False) -> int:
    print("[*] 正在执行 Windows Terminal 定制回退与 100% 官方原生复原...")

    # 1. 还原 App Paths
    revert_app_paths()

    # 2. 还原 Nilesoft Shell
    revert_nilesoft()

    # 3. 移除快捷方式
    taskbar_lnk = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\Windows Terminal.lnk"))
    start_menu_lnk = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Windows Terminal.lnk"))
    touched: list[Path] = []
    for lnk in [taskbar_lnk, start_menu_lnk]:
        if lnk.is_file():
            try:
                lnk.unlink()
                print(f"[+] 已移除快捷方式: {lnk.name}")
            except Exception as e:
                print(f"[-] 移除快捷方式失败 {lnk.name}: {e}")

    # 4. 可选移除 PATH
    state = load_state()
    installed_dir = state.get("installed_dir")
    if remove_path and installed_dir:
        remove_from_user_path(Path(installed_dir))

    refresh_shell(touched)
    print("[+] 已广播 Windows 外壳刷新通知 (SHChangeNotify FLUSH)")

    if restart_exp:
        restart_explorer()

    print("\n" + "=" * 70)
    print("✅ 已彻底还原为官方原生状态！")
    print("💡 提示：如需彻底移除独立版，从用户环境变量 Path 移除该目录并删除解压文件夹即可。")
    print("=" * 70)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Windows Terminal (wt) 独立版定制、图标注入与全链路接管引擎")
    parser.add_argument("--auto-setup", action="store_true", help="新电脑全自动部署模式：自动从 GitHub 下载最新免安装终端与 rcedit，并自动配置 PATH")
    parser.add_argument("--style", type=str, default="pure_dark", help="图标风格 (pure_dark, titanium, underlit_chrome, dark_blue, cyan_matrix)")
    parser.add_argument("--custom-icon", type=str, default=None, help="自定义 .ico 文件绝对路径")
    parser.add_argument("--target-dir", type=str, default=None, help="Windows Terminal 免安装独立版解压目录")
    parser.add_argument("--rcedit", type=str, default=None, help="自定义 rcedit.exe 路径")
    parser.add_argument("--restart-explorer", action="store_true", help="修改完成后自动重启资源管理器以立即刷新缓存")
    parser.add_argument("--revert", action="store_true", help="一键彻底撤销修改并还原为系统官方原生状态")
    parser.add_argument("--remove-path", action="store_true", help="复原时一并从用户环境变量 Path 中移除独立版目录")
    parser.add_argument("--list-styles", action="store_true", help="列出全部可用图标风格")

    args = parser.parse_args()

    if args.list_styles:
        styles = get_available_styles()
        print("可用图标风格列表:")
        for name, p in styles.items():
            print(f"  - {name:<16} ({p.name})")
        return

    if args.revert:
        sys.exit(revert(args.restart_explorer, args.remove_path))

    sys.exit(apply(args.style, args.custom_icon, args.target_dir, args.restart_explorer, args.rcedit, args.auto_setup))


if __name__ == "__main__":
    main()
