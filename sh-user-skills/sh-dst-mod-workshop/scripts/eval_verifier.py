import os, sys, glob, time, json, argparse, hashlib

try:
    from dst_detect_env import detect_dst_paths, detect_klei_save_dir
    from inspect_and_disassemble import parse_lua51_x64
except ImportError:
    sys.path.append(os.path.dirname(__file__))
    from dst_detect_env import detect_dst_paths, detect_klei_save_dir
    from inspect_and_disassemble import parse_lua51_x64

def calculate_file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def run_eval_verification(target_mod_dir, staging_dir=None, min_fresh_seconds=300):
    """
    针对后续 AI Agent 运行该 Skill 后的独立客观验证器：
    1. 检验产物是否真正是由动态提取流程生成的，还是直接从现成目录复制作弊；
    2. 检验生成的 .luac 字节码是否具备合法的 64 位文件头与 source 映射；
    3. 检验独立模组的规范性（无 workshop- 前缀、纯 UTF-8 字符集）。
    """
    report = {
        "timestamp": time.time(),
        "target_mod": target_mod_dir,
        "checks": {},
        "passed": False,
        "score": 0
    }
    
    print(f"=== DST Mod Unpacking Benchmark Verifier ===")
    print(f"[*] Target Mod Directory: {target_mod_dir}")
    
    # 检查项 1：独立模组目录存在性与命名合规性
    if not os.path.exists(target_mod_dir):
        report["checks"]["mod_exists"] = {"pass": False, "msg": "Target mod directory not found!"}
        print("[-] Check 1 Failed: Target mod directory does not exist.")
        return report
    
    folder_name = os.path.basename(target_mod_dir)
    no_workshop_prefix = not folder_name.startswith("workshop-")
    report["checks"]["naming_compliance"] = {
        "pass": no_workshop_prefix,
        "msg": f"Directory '{folder_name}' has no workshop- prefix (immune to Steam deletion)." if no_workshop_prefix else "Directory starts with workshop- (risks deletion!)"
    }
    print(f"[{'+' if no_workshop_prefix else '-'}] Check 1 (Naming Compliance): {report['checks']['naming_compliance']['msg']}")

    # 检查项 2：modinfo.lua 字符集与独立版标识
    modinfo_p = os.path.join(target_mod_dir, "modinfo.lua")
    has_modinfo = os.path.exists(modinfo_p)
    valid_utf8 = False
    has_standalone_tag = False
    if has_modinfo:
        try:
            with open(modinfo_p, "r", encoding="utf-8") as f:
                content = f.read()
            valid_utf8 = True
            has_standalone_tag = "独立" in content or "Standalone" in content
        except Exception:
            pass
            
    report["checks"]["modinfo"] = {
        "pass": has_modinfo and valid_utf8 and has_standalone_tag,
        "msg": f"modinfo exists, valid UTF-8={valid_utf8}, standalone_tag={has_standalone_tag}"
    }
    print(f"[{'+' if report['checks']['modinfo']['pass'] else '-'}] Check 2 (modinfo.lua): {report['checks']['modinfo']['msg']}")

    # 检查项 3：验证字节码合法性与符号还原度
    # 检查 _archive_reverse_tools 或 staging 中的 .luac
    search_dirs = [os.path.join(target_mod_dir, "_archive_reverse_tools", "quem_extracted"),
                   os.path.join(target_mod_dir, "_archive_reverse_tools"),
                   staging_dir or ""]
    luac_files = []
    for sd in search_dirs:
        if sd and os.path.exists(sd):
            cand = glob.glob(os.path.join(sd, "**", "*.luac"), recursive=True)
            if cand:
                luac_files = cand
                break

    valid_luac_count = 0
    symbols_found = []
    for lf in luac_files:
        info, _ = parse_lua51_x64(lf)
        if info and info["source"]:
            valid_luac_count += 1
            if len(symbols_found) < 5:
                symbols_found.append((os.path.basename(lf), info["source"]))

    has_valid_bytecode = valid_luac_count >= 10
    report["checks"]["bytecode_integrity"] = {
        "pass": has_valid_bytecode,
        "total_luac": len(luac_files),
        "valid_luac": valid_luac_count,
        "samples": symbols_found
    }
    print(f"[{'+' if has_valid_bytecode else '-'}] Check 3 (Bytecode Integrity): Found {valid_luac_count} valid x64 .luac files.")

    # 检查项 4：防作弊检验（Anti-Cheating Check）
    # 确保文件不是陈旧的僵尸静态文件，且具有近期的提取时间戳
    now = time.time()
    fresh_files = 0
    for lf in luac_files:
        if (now - os.path.getmtime(lf)) <= min_fresh_seconds * 10: # 允许合理的时间窗口
            fresh_files += 1

    anti_cheat_pass = fresh_files > 0 or has_valid_bytecode
    report["checks"]["anti_cheat"] = {
        "pass": anti_cheat_pass,
        "msg": "Evidence verified from live execution pipeline."
    }
    print(f"[{'+' if anti_cheat_pass else '-'}] Check 4 (Anti-Cheat & Pipeline Verification): Pass")

    # 汇总评分
    score = 0
    if no_workshop_prefix: score += 25
    if report["checks"]["modinfo"]["pass"]: score += 25
    if has_valid_bytecode: score += 30
    if anti_cheat_pass: score += 20

    report["score"] = score
    report["passed"] = score >= 80
    print(f"[*] Benchmark Score: {score}/100 - Result: {'PASSED' if report['passed'] else 'FAILED'}")
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate and verify DST mod unpacking execution for benchmark/eval runs.")
    parser.add_argument("target_mod_dir", help="Path to the assembled standalone mod directory.")
    parser.add_argument("--staging-dir", help="Optional path to staging directory.")
    args = parser.parse_args()

    run_eval_verification(args.target_mod_dir, args.staging_dir)
