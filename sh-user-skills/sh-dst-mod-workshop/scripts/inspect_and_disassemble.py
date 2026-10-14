import struct, os, glob, json, argparse

def parse_lua51_x64(path):
    """
    解析 Lua 5.1 64-bit 预编译块头部及核心常量/操作码
    DST 引擎格式：sizeof(size_t) = 8, sizeof(int) = 4, sizeof(Instruction) = 4, sizeof(lua_Number) = 8
    """
    try:
        with open(path, "rb") as f:
            hdr = f.read(12)
            if not hdr.startswith(b"\x1bLuaQ"):
                return None, "Not a valid Lua 5.1 bytecode chunk"
            
            slen = struct.unpack("<Q", f.read(8))[0]
            source = f.read(slen)[:-1].decode("latin1", errors="ignore") if slen > 0 else ""
            line_def, last_line_def = struct.unpack("<II", f.read(8))
            num_upvals = ord(f.read(1))
            num_params = ord(f.read(1))
            is_vararg = ord(f.read(1))
            max_stack = ord(f.read(1))
            num_inst = struct.unpack("<I", f.read(4))[0]
            insts = [struct.unpack("<I", f.read(4))[0] for _ in range(num_inst)]
            num_consts = struct.unpack("<I", f.read(4))[0]
            consts = []
            for _ in range(num_consts):
                t = ord(f.read(1))
                if t == 0: consts.append(None)
                elif t == 1: consts.append(ord(f.read(1)) != 0)
                elif t == 3: consts.append(struct.unpack("<d", f.read(8))[0])
                elif t == 4:
                    sz = struct.unpack("<Q", f.read(8))[0]
                    consts.append(f.read(sz)[:-1].decode("latin1", errors="ignore") if sz else "")
                else: consts.append(f"<type {t}>")
                    
            return {
                "source": source,
                "line_def": line_def,
                "last_line_def": last_line_def,
                "num_upvals": num_upvals,
                "num_params": num_params,
                "instructions_count": num_inst,
                "constants_count": num_consts,
                "sample_constants": [c for c in consts if isinstance(c, str)][:15]
            }, None
    except Exception as e:
        return None, str(e)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse and map Lua 5.1 x64 bytecode symbols and source paths.")
    parser.add_argument("target", help="Path to a single .luac file or a directory containing .luac files.")
    parser.add_argument("--export-map", help="Optional output JSON path for the source mapping manifest.")
    args = parser.parse_args()

    if os.path.isfile(args.target):
        info, err = parse_lua51_x64(args.target)
        if info:
            print(f"[*] File: {args.target}")
            print(f"    Source Path: {info['source']}")
            print(f"    Instructions: {info['instructions_count']}, Constants: {info['constants_count']}")
            print(f"    Sample Constants: {info['sample_constants']}")
        else:
            print(f"[!] Error: {err}")
    elif os.path.isdir(args.target):
        files = glob.glob(os.path.join(args.target, "*.luac"))
        print(f"[*] Scanning {len(files)} bytecode chunks in: {args.target}")
        manifest = {}
        for fp in files:
            info, _ = parse_lua51_x64(fp)
            if info:
                manifest[os.path.basename(fp)] = info
        print(f"[+] Successfully extracted {len(manifest)} valid bytecode descriptors.")
        if args.export_map:
            with open(args.export_map, "w", encoding="utf-8") as out_f:
                json.dump(manifest, out_f, indent=2, ensure_ascii=False)
            print(f"[+] Exported source mapping manifest to: {args.export_map}")
