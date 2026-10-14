import os, sys, glob, winreg

def detect_steam_path():
    """通过 Windows 注册表与常见盘符，自动探测 Steam 安装路径。"""
    paths_to_check = []
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            val, _ = winreg.QueryValueEx(key, "SteamPath")
            if val and os.path.exists(val):
                paths_to_check.append(os.path.normpath(val))
    except Exception:
        pass

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam") as key:
            val, _ = winreg.QueryValueEx(key, "InstallPath")
            if val and os.path.exists(val):
                paths_to_check.append(os.path.normpath(val))
    except Exception:
        pass

    drives = ["C", "D", "E", "F", "G"]
    for d in drives:
        paths_to_check.append(f"{d}:\\Program Files (x86)\\Steam")
        paths_to_check.append(f"{d}:\\Steam")

    for p in paths_to_check:
        if os.path.isdir(p) and os.path.exists(os.path.join(p, "steam.exe")):
            return p
    return None

def detect_dst_paths(steam_dir=None):
    """
    通过解析 libraryfolders.vdf，在所有 Steam 库目录中自动查找 Don't Starve Together。
    返回: (dst_game_dir, dst_mods_dir, workshop_content_dir)
    """
    if not steam_dir:
        steam_dir = detect_steam_path()
        
    library_dirs = []
    if steam_dir:
        library_dirs.append(steam_dir)
        vdf_path = os.path.join(steam_dir, "steamapps", "libraryfolders.vdf")
        if os.path.exists(vdf_path):
            try:
                with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if '"path"' in line.lower():
                            parts = line.split('"')
                            if len(parts) >= 4:
                                p = parts[3].replace(r"\\", "\\")
                                if os.path.exists(p) and p not in library_dirs:
                                    library_dirs.append(os.path.normpath(p))
            except Exception:
                pass

    for lib in library_dirs:
        cand_game = os.path.join(lib, "steamapps", "common", "Don't Starve Together")
        if os.path.exists(cand_game):
            mods_dir = os.path.join(cand_game, "mods")
            ws_dir = os.path.join(lib, "steamapps", "workshop", "content", "322330")
            return os.path.normpath(cand_game), os.path.normpath(mods_dir), os.path.normpath(ws_dir)

    return None, None, None

def detect_klei_save_dir():
    """自动查找当前用户的 Klei 存档目录，并返回最近活跃的 <SteamID>/client_save/mod_config_data 路径。"""
    user_home = os.path.expanduser("~")
    base_save = os.path.join(user_home, "Documents", "Klei", "DoNotStarveTogether")
    if not os.path.exists(base_save):
        return None, None

    active_candidates = []
    for sub in os.listdir(base_save):
        sub_path = os.path.join(base_save, sub)
        if os.path.isdir(sub_path) and sub.isdigit():
            client_save = os.path.join(sub_path, "client_save", "mod_config_data")
            if os.path.exists(client_save):
                mtime = os.path.getmtime(client_save)
                active_candidates.append((mtime, client_save, sub))

    if active_candidates:
        active_candidates.sort(key=lambda x: x[0], reverse=True)
        return active_candidates[0][1], active_candidates[0][2]

    return None, None

if __name__ == "__main__":
    print("=== DST Reverse Toolchain Environment Auto-Discovery ===")
    steam_p = detect_steam_path()
    print(f"[*] Steam Path: {steam_p or 'Not Found'}")
    game_d, mods_d, ws_d = detect_dst_paths(steam_p)
    print(f"[*] DST Game Dir: {game_d or 'Not Found'}")
    print(f"[*] DST Mods Dir: {mods_d or 'Not Found'}")
    print(f"[*] DST Workshop Dir: {ws_d or 'Not Found'}")
    save_d, sid = detect_klei_save_dir()
    print(f"[*] Active SteamID: {sid or 'Not Found'}")
    print(f"[*] Save Dir: {save_d or 'Not Found'}")
