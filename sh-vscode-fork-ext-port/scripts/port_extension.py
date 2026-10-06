# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""把某个扩展从一个 VS Code 系 IDE 搬到另一个：复制目录 + 写注册表 + （可选）应用主题。

背景：VS Code 各分支（VS Code / Cursor / Antigravity IDE / Trae / Kiro / Qoder…）共用扩展机制，
但各有各的扩展目录与市场。目标市场里没有的扩展（如 VS Code Marketplace 独占）只能手工搬运，
手工搬的关键是"目录 + 注册表条目"两件套都到位，缺一个就不生效。

用法：
    uv run port_extension.py --from cursor --to antigravity-ide --id edwinsulaiman.jetbrains-rider-dark-theme
    uv run port_extension.py --from cursor --to antigravity-ide --id <id> --dry-run      # 只看会做什么
    uv run port_extension.py --from cursor --to kiro --id <id> --apply-theme             # 主题类顺带写入 colorTheme
    uv run port_extension.py --to antigravity-ide --list                                 # 目标已装扩展与注册表对照
    uv run port_extension.py --to antigravity-ide --id <id> --uninstall --yes            # 回滚（删目录 + 摘注册表）

分支名可用 dataFolderName（.cursor）、nameShort（Cursor）、安装目录名或安装目录路径。
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from scan_ides import (  # noqa: E402
    find_cli,
    find_in_dir,
    is_running,
    list_profiles,
    load_registry,
    read_manifest,
    registry_entry,
    registry_path,
    resolve,
    save_registry,
)


def pick_source_dir(src: dict, ext_id: str, want_version: str | None) -> Path:
    """在源 IDE 的扩展目录里定位该扩展；多个候选时按 manifest 版本取最高。"""
    cands = [Path(src["extensionsDir"]) / n for n in find_in_dir(Path(src["extensionsDir"]), ext_id)]
    if not cands:
        raise SystemExit(
            f"源分支 {src.get('nameShort')} 的扩展目录里没有 {ext_id}：{src['extensionsDir']}\n"
            f"用 `uv run scan_ides.py --has {ext_id}` 看看哪个分支装了它"
        )
    if want_version:
        cands = [c for c in cands if read_manifest(c).get("version") == want_version] or cands
    cands.sort(key=lambda c: str(read_manifest(c).get("version", "")), reverse=True)
    if len(cands) > 1:
        print(f"  源目录有 {len(cands)} 个候选，取版本最高的：{[c.name for c in cands]}")
    return cands[0]


def semver_tuple(v: str) -> tuple:
    out = []
    for part in str(v).split("."):
        out.append(int(part) if part.isdigit() else 0)
    return tuple(out + [0, 0, 0])[:3]


def check_engines(manifest: dict, dst: dict) -> str | None:
    """粗查 engines.vscode 与目标分支版本是否相容。

    不少分支用自有版本号（Kiro 1.1.14、Cursor 3.x），跟 engines.vscode 不是一个序列，
    比出来的结果只会误导；只对版本号明显沿用上游 VS Code 序列（1.x 且 minor>=50）的分支做比较。
    """
    eng = ((manifest.get("engines") or {}).get("vscode") or "").lstrip("^~>=< ").strip()
    have = dst.get("version") or ""
    if not eng or not have or not have[0].isdigit():
        return None
    target = semver_tuple(have)
    if not (target[0] == 1 and target[1] >= 50):
        return None
    if target < semver_tuple(eng):
        return f"扩展要求 vscode >= {eng}，目标分支是 {have}，可能不兼容"
    return None


def apply_theme(dst: dict, manifest: dict, dry_run: bool) -> str | None:
    """主题类扩展：把第一个主题 label 写进目标分支的 workbench.colorTheme。"""
    themes = (manifest.get("contributes") or {}).get("themes") or []
    if not themes:
        return "该扩展没有 contributes.themes，跳过 --apply-theme"
    label = themes[0].get("label") or themes[0].get("id")
    sfile = Path(dst["userDataDir"]) / "User" / "settings.json"
    if dry_run:
        return f"[dry-run] 会在 {sfile} 写入 workbench.colorTheme = {label!r}"
    sfile.parent.mkdir(parents=True, exist_ok=True)
    settings: dict = {}
    if sfile.is_file():
        try:
            settings = json.loads(sfile.read_text(encoding="utf-8-sig") or "{}")
        except json.JSONDecodeError:
            return f"{sfile} 不是合法 JSON，已跳过主题写入（手工改）"
        if not sfile.with_suffix(".json.bak").exists():
            sfile.with_suffix(".json.bak").write_bytes(sfile.read_bytes())
    settings["workbench.colorTheme"] = label
    sfile.write_text(json.dumps(settings, ensure_ascii=False, indent=4) + "\n", encoding="utf-8", newline="")
    return f"已写入 {sfile}：workbench.colorTheme = {label!r}"


def do_list(dst: dict) -> int:
    """列出目标分支的扩展目录 + 注册表，并标出两者的不一致（排障常用）。"""
    ext_dir = Path(dst["extensionsDir"])
    reg = registry_path(dst)
    entries = load_registry(reg)
    on_disk = sorted(p.name for p in ext_dir.iterdir() if p.is_dir()) if ext_dir.is_dir() else []
    obsolete: dict = {}
    ob_file = ext_dir / ".obsolete"
    if ob_file.is_file():
        try:
            obsolete = json.loads(ob_file.read_text(encoding="utf-8-sig") or "{}")
        except json.JSONDecodeError:
            obsolete = {}
    print(f"目标：{dst.get('nameShort')}  {ext_dir}")
    print(f"注册表：{reg}（{len(entries)} 条）")
    print(f"磁盘目录：{len(on_disk)} 个")
    if list_profiles(dst):
        print(f"注意：该分支还有具名 profile {list_profiles(dst)}，其注册表在 <userData>/User/profiles/<名>/extensions.json")
    reg_dirs = {e.get("relativeLocation") for e in entries}
    for name in on_disk:
        if name in reg_dirs:
            mark = ""
        elif name in obsolete:
            mark = "   ← 已卸载待删（.obsolete），下次启动清目录"
        else:
            mark = "   ← 磁盘有、注册表没有（不会加载）"
        print(f"  {name}{mark}")
    for loc in sorted(x for x in reg_dirs if x and x not in on_disk):
        print(f"  {loc}   ← 注册表有、磁盘没有（加载失败）")
    return 0


def do_uninstall(dst: dict, ext_id: str, dry_run: bool, assume_yes: bool) -> int:
    ext_dir = Path(dst["extensionsDir"])
    reg = registry_path(dst)
    entries = load_registry(reg)
    keep = [e for e in entries if e.get("identifier", {}).get("id") != ext_id]
    dirs = find_in_dir(ext_dir, ext_id)
    print(f"将删除目录：{dirs or '无'}")
    print(f"将从注册表摘掉 {len(entries) - len(keep)} 条条目：{reg}")
    if dry_run:
        print("[dry-run] 未做任何改动")
        return 0
    if not assume_yes:
        raise SystemExit("真要删就加 --yes（本操作不可逆）")
    for name in dirs:
        shutil.rmtree(ext_dir / name)
    if len(keep) != len(entries):
        save_registry(reg, keep)
    print("完成。若 IDE 正在运行，重载窗口后生效")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="VS Code 系 IDE 之间手工搬运扩展")
    ap.add_argument("--from", dest="src", help="源分支（dataFolderName / nameShort / 路径）")
    ap.add_argument("--to", dest="dst", required=True, help="目标分支")
    ap.add_argument("--id", dest="ext_id", help="扩展 id：publisher.name")
    ap.add_argument("--src-dir", help="直接用这个扩展目录当源（省去 --from 探测）")
    ap.add_argument("--version", help="源扩展版本（默认取最高版本）")
    ap.add_argument("--profile", help="目标分支的 profile 名（默认 profile 不用写）")
    ap.add_argument("--apply-theme", action="store_true", help="主题类扩展顺带写入 workbench.colorTheme")
    ap.add_argument("--list", action="store_true", help="列出目标分支已装扩展，不做改动")
    ap.add_argument("--uninstall", action="store_true", help="回滚：删目录 + 摘注册表")
    ap.add_argument("--yes", action="store_true", help="--uninstall 的确认开关")
    ap.add_argument("--dry-run", action="store_true", help="只打印将做的动作")
    args = ap.parse_args()

    dst = resolve(args.dst)

    if args.list:
        return do_list(dst)
    if not args.ext_id:
        raise SystemExit("缺 --id（publisher.name）")
    if args.uninstall:
        return do_uninstall(dst, args.ext_id, args.dry_run, args.yes)

    if args.src_dir:
        src_dir = Path(args.src_dir)
        src = {"nameShort": f"目录 {src_dir}", "extensionsDir": str(src_dir.parent)}
    else:
        if not args.src:
            raise SystemExit("缺 --from（或用 --src-dir 直接给扩展目录）")
        src = resolve(args.src)
        src_dir = pick_source_dir(src, args.ext_id, args.version)

    manifest = read_manifest(src_dir)
    version = str(manifest.get("version", ""))
    if manifest.get("publisher") and manifest.get("name"):
        real_id = f"{manifest['publisher']}.{manifest['name']}"
        if real_id.lower() != args.ext_id.lower():
            print(f"  注意：--id 是 {args.ext_id}，但 package.json 里是 {real_id}，以目录实际内容为准")

    ext_dir = Path(dst["extensionsDir"])
    target_dir = ext_dir / src_dir.name
    reg = registry_path(dst, args.profile)
    entries = load_registry(reg)
    replaced = [e for e in entries if e.get("identifier", {}).get("id") == args.ext_id]

    print(f"源：{src.get('nameShort')}  {src_dir}")
    print(f"目标：{dst.get('nameShort')}  {target_dir}")
    print(f"版本：{version}   注册表：{reg}")
    if target_dir.exists():
        old = read_manifest(target_dir).get("version") if (target_dir / "package.json").is_file() else "?"
        print(f"  目标已存在同版本目录（旧版本 {old}），将覆盖刷新")
    if replaced:
        print(f"  注册表已有 {len(replaced)} 条同 id 条目，将替换")
    warn = check_engines(manifest, dst)
    if warn:
        print(f"  警告：{warn}")
    if "-" in src_dir.name[len(args.ext_id) + 1 :] and any(
        p in src_dir.name for p in ("win32", "darwin", "linux", "arm64", "x64")
    ):
        print("  警告：源目录带平台后缀（含平台二进制），只能搬给同 OS/同架构的分支")
    if list_profiles(dst):
        print(f"  注意：目标分支有具名 profile {list_profiles(dst)}，非默认 profile 要加 --profile")
    running = is_running(dst)
    if running:
        print("  注意：目标 IDE 正在运行——改注册表会即时触发它内部的重扫，建议改完 Reload Window")

    if args.dry_run:
        print("[dry-run] 未做任何改动")
        if args.apply_theme:
            print("  " + (apply_theme(dst, manifest, True) or ""))
        return 0

    ext_dir.mkdir(parents=True, exist_ok=True)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(src_dir, target_dir, symlinks=True)
    entries = [e for e in entries if e.get("identifier", {}).get("id") != args.ext_id]
    entries.append(registry_entry(args.ext_id, version, target_dir))
    save_registry(reg, entries)
    print(f"  已复制 {target_dir.name}，注册表共 {len(entries)} 条")

    if args.apply_theme:
        print("  " + (apply_theme(dst, manifest, False) or ""))

    cli = dst.get("cli") or find_cli(dst)
    print("\n下一步：")
    if running:
        print("  在目标 IDE 里执行「Developer: Reload Window」；主题类扩展重载后即生效")
    else:
        print("  直接启动目标 IDE 即可（启动时扫描扩展目录）")
    if cli:
        print(f"  自检：{cli} --list-extensions --show-versions | findstr /i {args.ext_id}")
    friendly = dst.get("nameShort") or dst["dataFolderName"]
    print("  回滚：" + f'uv run port_extension.py --to "{friendly}" --id {args.ext_id} --uninstall --yes')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
