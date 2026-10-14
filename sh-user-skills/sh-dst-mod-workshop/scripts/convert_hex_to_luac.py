import os, glob

def convert_hex_dumps(save_dir, output_dir):
    """
    遍历 client_save/mod_config_data/ 下的所有 q_*.hex 文件，
    剥除 Klei 存档头 'KLEI     1 '，还原为标准 Lua 5.1 x64 .luac 二进制文件。
    """
    os.makedirs(output_dir, exist_ok=True)
    hex_files = glob.glob(os.path.join(save_dir, "q_*.hex"))
    print(f"Total hex files found: {len(hex_files)}")
    
    success = 0
    for fp in hex_files:
        fn = os.path.basename(fp).replace(".hex", ".luac")
        out_path = os.path.join(output_dir, fn)
        try:
            with open(fp, "rb") as f:
                content = f.read().strip()
            
            # Klei SavePersistentString 会在头部加上 'KLEI     1 ' (9 字节或更多)
            if content.startswith(b"KLEI"):
                idx = content.find(b"1b4c7561") # 查找 \x1bLua 的 hex 编码
                if idx != -1:
                    hex_str = content[idx:].decode("ascii")
                else:
                    parts = content.split(b" ")
                    hex_str = parts[-1].decode("ascii")
            else:
                hex_str = content.decode("ascii")
            
            binary_data = bytes.fromhex(hex_str.strip())
            with open(out_path, "wb") as out_f:
                out_f.write(binary_data)
            success += 1
        except Exception as e:
            print(f"Failed to convert {fp}: {e}")
            
    print(f"Successfully converted {success} / {len(hex_files)} files into standard .luac bytecode!")

if __name__ == "__main__":
    user_home = os.path.expanduser("~")
    save_base = os.path.join(user_home, "Documents", "Klei", "DoNotStarveTogether")
    
    # 自动定位用户的存档目录
    target_save_dir = None
    if os.path.exists(save_base):
        for sub in os.listdir(save_base):
            cand = os.path.join(save_base, sub, "client_save", "mod_config_data")
            if os.path.exists(cand):
                target_save_dir = cand
                break
                
    if target_save_dir:
        output_dir = "./extracted_luac"
        print(f"Processing dumps from: {target_save_dir}")
        convert_hex_dumps(target_save_dir, output_dir)
    else:
        print("Could not find client_save/mod_config_data directory!")
