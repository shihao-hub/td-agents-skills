import os, shutil, glob

def build_standalone_mod(workshop_content_dir, dst_mods_dir, local_mod_name="quem", staging_dir=None, clean_client_save=True):
    """
    全自动完成：
    1. 组装 100% 独立可运行的本地模组目录 (mods/<local_mod_name>)；
    2. 目录命名强制为纯本地模组（严禁 workshop-* 前缀），彻底免疫 Steam 创意工坊退订自动删除机制；
    3. 清理并修正 modinfo.lua，写入纯正 UTF-8（无 BOM）标识；
    4. 规范化归档：将逆向过程中的中间产物 (staging 字节码、提取脚本、环境配置) 自动打包移入
       mods/<local_mod_name>/_archive_reverse_tools/，并生成详尽的 README.md 说明文档；
    5. 自动化环境整洁：清理 staging 临时目录、清理 client_save/mod_config_data/ 中的 hex 碎片，
       确保游戏目录与用户项目绝对纯净，零残留污染。
    """
    dest_path = os.path.join(dst_mods_dir, local_mod_name)
    archive_path = os.path.join(dest_path, "_archive_reverse_tools")
    print(f"[*] Assembling standalone mod at: {dest_path}")
    
    # 保留原有的归档内容（如果存在）
    backup_archive = None
    if os.path.exists(archive_path):
        backup_archive = os.path.join(dst_mods_dir, f"_temp_archive_{local_mod_name}")
        shutil.move(archive_path, backup_archive)
        
    if os.path.exists(dest_path):
        shutil.rmtree(dest_path)
    shutil.copytree(workshop_content_dir, dest_path)
    
    # 修正 modinfo.lua 为独立免订阅版
    modinfo_file = os.path.join(dest_path, "modinfo.lua")
    if os.path.exists(modinfo_file):
        with open(modinfo_file, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            
        content = content.replace('name = "奎姆"', f'name = "奎姆 (独立免订阅版)"')
        content = content.replace('description = ""', 'description = "奎姆独立运行版 (免Steam创意工坊订阅，可离线独立运行)"')
        content = content.replace('version = "7.8"', 'version = "7.8.0_Standalone"')
        
        with open(modinfo_file, "w", encoding="utf-8") as f:
            f.write(content)
            
    # 创建规范化过程归档目录
    os.makedirs(archive_path, exist_ok=True)
    if backup_archive and os.path.exists(backup_archive):
        for item in os.listdir(backup_archive):
            shutil.move(os.path.join(backup_archive, item), os.path.join(archive_path, item))
        shutil.rmtree(backup_archive)
        
    # 将 staging 中的中间逆向产物归档进去
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
        print(f"[+] Cleaned staging directory: {staging_dir}")
        
    # 生成归档文档
    readme_path = os.path.join(archive_path, "README.md")
    if not os.path.exists(readme_path):
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"""# {local_mod_name} 模组逆向工程与活体脱壳归档资产说明

本目录 `_archive_reverse_tools/` 是在对本模组进行脱壳、解密和逆向分析过程中，产生的全套**提取脚本、中间解码数据与辅助工程文件**的专用归档区。

---

## 一、归档资产清单
* `dump_memory.lua`：活体内存导出工具，在游戏完全加载后抓取 Prefabs、Brains、Components 函数。
* `quem_extracted/`：从 Hex 文本还原的 Lua 5.1 x64 .luac 二进制字节码块。
* `zzz_quem_exporter/`：低优先级挂载辅助模组。

---

## 二、中间环节作用与原理
1. **解决静态反调试与自校验**：DaxSg 外壳含有文件大小自校验与反调试逻辑炸弹，静态修改触发死锁，故改走内存活体导出。
2. **解决 Klei 引擎空字节截断**：内存导出的二进制包含大量 `\\0`，Klei 引擎内部作为 C 字符串处理会截断，故在 Lua 层转为十六进制文本再由 Python 反解。
3. **隔离防删**：本独立模组采用纯英文名 `{local_mod_name}`，脱离 Steam 创意工坊退订自动删除机制。
""")

    # 清理客户端存档中的临时 Hex 文件
    if clean_client_save:
        user_home = os.path.expanduser("~")
        save_base = os.path.join(user_home, "Documents", "Klei", "DoNotStarveTogether")
        if os.path.exists(save_base):
            for sub in os.listdir(save_base):
                hex_dir = os.path.join(save_base, sub, "client_save", "mod_config_data")
                if os.path.exists(hex_dir):
                    hex_files = glob.glob(os.path.join(hex_dir, "q_*.hex"))
                    for hf in hex_files:
                        try: os.remove(hf)
                        except: pass
                    if hex_files:
                        print(f"[+] Cleaned {len(hex_files)} temporary hex dump files from {hex_dir}")

    total_files = len([os.path.join(r, f) for r, d, fs in os.walk(dest_path) for f in fs])
    print(f"[+] Done! Standalone mod assembled with {total_files} files ready to play in DST.")

if __name__ == "__main__":
    import sys
    ws_dir = sys.argv[1] if len(sys.argv) > 1 else r"D:\Program Files (x86)\Steam\steamapps\workshop\content\322330\3152990521"
    mods_dir = sys.argv[2] if len(sys.argv) > 2 else r"D:\Program Files (x86)\Steam\steamapps\common\Don't Starve Together\mods"
    build_standalone_mod(ws_dir, mods_dir, "quem")
