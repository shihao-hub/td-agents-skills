import os, glob, argparse, sys

try:
    from dst_detect_env import detect_klei_save_dir
except ImportError:
    sys.path.append(os.path.dirname(__file__))
    from dst_detect_env import detect_klei_save_dir

def convert_hex_dumps(save_dir, output_dir, prefix="q_"):
    """
    遍历指定 save_dir 下的所有 {prefix}*.hex 文件，
    剥除 Klei 存档头 'KLEI     1 '，还原为标准 Lua 5.1 x64 .luac 二进制文件。
    """
    os.makedirs(output_dir, exist_ok=True)
    hex_files = glob.glob(os.path.join(save_dir, f"{prefix}*.hex"))
    print(f"[*] Scanning hex files in: {save_dir}")
    print(f"[*] Total matching hex files found: {len(hex_files)}")
    
    success = 0
    for fp in hex_files:
        fn = os.path.basename(fp).replace(".hex", ".luac")
        out_path = os.path.join(output_dir, fn)
        try:
            with open(fp, "rb") as f:
                content = f.read().strip()
            
            if content.startswith(b"KLEI"):
                idx = content.find(b"1b4c7561") # 寻找 \x1bLua 的十六进制编码
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
            print(f"[!] Error converting {fp}: {e}")
            
    print(f"[+] Successfully converted {success} / {len(hex_files)} files into standard .luac bytecode at: {output_dir}")
    return success

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert live-dumped DST Hex files to Lua 5.1 x64 bytecode chunks.")
    parser.add_argument("--save-dir", help="Path to client_save/mod_config_data. Auto-detected if omitted.")
    parser.add_argument("--output-dir", default="./extracted_luac", help="Target output directory for .luac files.")
    parser.add_argument("--prefix", default="q_", help="Hex filename prefix to filter.")
    args = parser.parse_args()

    target_save = args.save_dir
    if not target_save:
        target_save, sid = detect_klei_save_dir()
        if target_save:
            print(f"[*] Auto-detected active Klei save directory for SteamID {sid}: {target_save}")
        else:
            print("[!] Could not auto-detect Klei save directory. Please pass --save-dir explicitly.")
            sys.exit(1)

    convert_hex_dumps(target_save, args.output_dir, args.prefix)
