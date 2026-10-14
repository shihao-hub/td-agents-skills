import struct, os, glob

def parse_lua51_x64(path):
    """
    解析 Lua 5.1 64-bit 预编译块头部及核心常量/操作码
    DST 引擎规格：sizeof(size_t) = 8, sizeof(int) = 4, sizeof(Instruction) = 4, sizeof(lua_Number) = 8
    """
    with open(path, "rb") as f:
        hdr = f.read(12)
        if not hdr.startswith(b"\x1bLuaQ"):
            return None, "Not a valid Lua 5.1 bytecode chunk"
        
        # 1. 原始源码路径 (size_t + string)
        slen = struct.unpack("<Q", f.read(8))[0]
        source = f.read(slen)[:-1].decode("latin1", errors="ignore") if slen > 0 else ""
        
        # 2. 行定义
        line_def, last_line_def = struct.unpack("<II", f.read(8))
        
        # 3. 参数与上值
        num_upvals = ord(f.read(1))
        num_params = ord(f.read(1))
        is_vararg = ord(f.read(1))
        max_stack = ord(f.read(1))
        
        # 4. 指令数
        num_inst = struct.unpack("<I", f.read(4))[0]
        insts = [struct.unpack("<I", f.read(4))[0] for _ in range(num_inst)]
        
        # 5. 常量池 (Constants)
        num_consts = struct.unpack("<I", f.read(4))[0]
        consts = []
        for _ in range(num_consts):
            t = ord(f.read(1))
            if t == 0: # LUA_TNIL
                consts.append(None)
            elif t == 1: # LUA_TBOOLEAN
                consts.append(ord(f.read(1)) != 0)
            elif t == 3: # LUA_TNUMBER
                consts.append(struct.unpack("<d", f.read(8))[0])
            elif t == 4: # LUA_TSTRING
                sz = struct.unpack("<Q", f.read(8))[0]
                consts.append(f.read(sz)[:-1].decode("latin1", errors="ignore") if sz else "")
            else:
                consts.append(f"<type {t}>")
                
        return {
            "source": source,
            "line_def": line_def,
            "last_line_def": last_line_def,
            "num_upvals": num_upvals,
            "num_params": num_params,
            "instructions_count": num_inst,
            "constants": consts
        }, None

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "./extracted_luac"
    if os.path.isfile(target):
        info, err = parse_lua51_x64(target)
        if info:
            print(f"Source: {info['source']}")
            print(f"Constants ({len(info['constants'])}): {info['constants'][:20]}")
    elif os.path.isdir(target):
        files = glob.glob(os.path.join(target, "*.luac"))
        print(f"Scanning {len(files)} files in {target}...")
        sources = {}
        for fp in files:
            info, _ = parse_lua51_x64(fp)
            if info and info["source"]:
                sources[os.path.basename(fp)] = info["source"]
        print(f"Extracted {len(sources)} source path mappings:")
        for k, v in list(sources.items())[:15]:
            print(f"  {k} -> {v}")
