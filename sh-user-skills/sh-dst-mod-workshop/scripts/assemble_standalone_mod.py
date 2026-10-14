import os, shutil, glob, re, argparse, sys

try:
    from dst_detect_env import detect_dst_paths, detect_klei_save_dir
except ImportError:
    sys.path.append(os.path.dirname(__file__))
    from dst_detect_env import detect_dst_paths, detect_klei_save_dir

def parse_modinfo(modinfo_path):
    """自适应解析原版 modinfo.lua 中的 name, version, author。"""
    meta = {"name": "Mod_Standalone", "version": "1.0.0", "author": "Unknown"}
    if not os.path.exists(modinfo_path):
        return meta
    with open(modinfo_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    m_name = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
    m_ver = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
    m_auth = re.search(r'author\s*=\s*["\']([^"\']+)["\']', content)
    if m_name: meta["name"] = m_name.group(1)
    if m_ver: meta["version"] = m_ver.group(1)
    if m_auth: meta["author"] = m_auth.group(1)
    return meta

def build_standalone_mod(src_mod_dir, dst_mods_dir, local_mod_name=None, staging_dir=None, clean_client_save=True):
    """
    通用自适应组装：
    1. 动态生成纯本地命名（脱离 workshop-* 标识，防止 Steam 启动删除）；
    2. 复制全部原始静态资源；
    3. 自适应修改 modinfo.lua（纯 UTF-8，增加免订阅标识）；
    4. 自动归档 staging 中的逆向工程资产到 _archive_reverse_tools/ 并生成说明文档；
    5. 自动清理 staging 临时目录与 client_save 中的 Hex 碎片。
    """
    src_mod_dir = os.path.normpath(src_mod_dir)
    dst_mods_dir = os.path.normpath(dst_mods_dir)
    
    modinfo_src = os.path.join(src_mod_dir, "modinfo.lua")
    meta = parse_modinfo(modinfo_src)
    
    if not local_mod_name:
        # 基于原文件夹名或名称自动生成无 workshop- 前缀的本地目录名
        base_folder = os.path.basename(src_mod_dir).replace("workshop-", "")
        local_mod_name = f"local_{base_folder}" if base_folder.isdigit() else base_folder
        
    dest_path = os.path.join(dst_mods_dir, local_mod_name)
    archive_path = os.path.join(dest_path, "_archive_reverse_tools")
    print(f"[*] Assembling standalone mod: '{meta['name']}' -> '{dest_path}'")
    
    # 临时备份已有归档
    backup_archive = None
    if os.path.exists(archive_path):
        backup_archive = os.path.join(dst_mods_dir, f"_temp_archive_{local_mod_name}")
        shutil.move(archive_path, backup_archive)
        
    if os.path.exists(dest_path):
        shutil.rmtree(dest_path)
    shutil.copytree(src_mod_dir, dest_path)
    
    # 自适应修正 modinfo.lua
    dest_modinfo = os.path.join(dest_path, "modinfo.lua")
    if os.path.exists(dest_modinfo):
        with open(dest_modinfo, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        old_name = meta["name"]
        new_name = f"{old_name} (独立免订阅版)"
        new_ver = f"{meta['version']}_Standalone"
        
        content = re.sub(r'name\s*=\s*["\'][^"\']+["\']', f'name = "{new_name}"', content)
        content = re.sub(r'version\s*=\s*["\'][^"\']+["\']', f'version = "{new_ver}"', content)
        
        with open(dest_modinfo, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[+] Updated modinfo.lua: '{new_name}' (v{new_ver})")
        
    os.makedirs(archive_path, exist_ok=True)
    if backup_archive and os.path.exists(backup_archive):
        for item in os.listdir(backup_archive):
            shutil.move(os.path.join(backup_archive, item), os.path.join(archive_path, item))
        shutil.rmtree(backup_archive)
        
    # 归档 staging 中的逆向数据
    if staging_dir and os.path.exists(staging_dir):
        print(f"[*] Archiving staging artifacts from {staging_dir} to {archive_path}...")
        for item in os.listdir(staging_dir):
            s_item = os.path.join(staging_dir, item)
            d_item = os.path.join(archive_path, item)
            if os.path.exists(d_item):
                if os.path.isdir(d_item): shutil.rmtree(d_item)
                else: os.remove(d_item)
            shutil.move(s_item, d_item)
        shutil.rmtree(staging_dir, ignore_errors=True)
        print(f"[+] Staging directory cleaned.")
        
    # 生成归档自说明文档
    readme_path = os.path.join(archive_path, "README.md")
    if not os.path.exists(readme_path):
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"""# {meta['name']} 模组逆向工程与活体脱壳资产归档

本目录 `_archive_reverse_tools/` 归档了对原模组进行脱壳解密时使用的全套**提取脚本、中间解码数据与辅助工程文件**。

---

## 一、资产说明
* 提取脚本与预编译字节码保存在本目录下；
* 独立主模组运行不依赖本目录（游戏引擎仅读取 `modmain.lua` 与 `scripts/`）；
* 独立模组采用本地无 `workshop-` 前缀命名，彻底杜绝 Steam 退订静默删除。
""")

    # 清理客户端存档中的 hex 碎片
    if clean_client_save:
        save_base, _ = detect_klei_save_dir()
        if save_base and os.path.exists(save_base):
            hex_files = glob.glob(os.path.join(save_base, "q_*.hex"))
            for hf in hex_files:
                try: os.remove(hf)
                except: pass
            if hex_files:
                print(f"[+] Cleaned {len(hex_files)} temporary hex dump files from client_save.")

    total_files = len([os.path.join(r, f) for r, d, fs in os.walk(dest_path) for f in fs])
    print(f"[+] Standalone mod assembly complete with {total_files} files at: {dest_path}")
    return dest_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assemble a clean, independent standalone DST mod with zero workshop dependencies.")
    parser.add_argument("src_mod_dir", help="Path to original workshop mod directory.")
    parser.add_argument("--mods-dir", help="Destination DST mods directory. Auto-detected if omitted.")
    parser.add_argument("--name", help="Local mod directory name (without workshop- prefix).")
    parser.add_argument("--staging-dir", help="Staging directory to archive and clean up.")
    args = parser.parse_args()

    dst_mods = args.mods_dir
    if not dst_mods:
        _, dst_mods, _ = detect_dst_paths()
        if not dst_mods:
            print("[!] Could not auto-detect DST mods directory. Please specify --mods-dir.")
            sys.exit(1)

    build_standalone_mod(args.src_mod_dir, dst_mods, args.name, args.staging_dir)
