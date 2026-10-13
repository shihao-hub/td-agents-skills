"""
DST 模组加密特征分析与解密校验脚本
"""
import os
import sys

def analyze_mod_dir(mod_dir):
    print(f"[*] 正在分析模组目录: {mod_dir}")
    if not os.path.exists(mod_dir):
        print(f"[-] 目录不存在: {mod_dir}")
        return

    files = os.listdir(mod_dir)
    print(f"[+] 根目录文件数: {len(files)}")

    has_modinfo = "modinfo.lua" in files
    has_modmain = "modmain.lua" in files
    has_daxsg_path = "daxsg_mod_path.txt" in files
    has_modmain0 = "modmain0.lua" in files
    has_modmain1 = "modmain1.lua" in files

    print(f"    - modinfo.lua: {has_modinfo}")
    print(f"    - modmain.lua: {has_modmain}")
    print(f"    - daxsg_mod_path.txt: {has_daxsg_path}")
    print(f"    - modmain0/1.lua: {has_modmain0} / {has_modmain1}")

    if has_daxsg_path and has_modmain0:
        print("[!] 确认为 DaxSg（大仙）Lua 混淆壳！")
        path_txt = os.path.join(mod_dir, "daxsg_mod_path.txt")
        with open(path_txt, "r", encoding="utf-8", errors="ignore") as f:
            targets = [l.strip() for l in f if l.strip()]
        print(f"[+] DaxSg 加密脚本清单总计: {len(targets)} 个文件")
        print("    样例列表:")
        for t in targets[:10]:
            print(f"      - scripts/{t}.lua")
    else:
        print("[*] 未检测到 DaxSg 专有标记，按通用模组结构处理。")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    analyze_mod_dir(target)
