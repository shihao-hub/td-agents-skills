# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""只做全量软链+改名一件事：把 sh-user-skills/<name>/ 内全部内容软链到 ../<name>/（顶层同名真实目录），其中 README.md 改名为 SKILL.md 链出，其余文件和子目录原名链出。

用法：
    uv run expose_user_skill.py <name> [--check] [--force]
    uv run expose_user_skill.py sh-plan-driven-development --check
"""

from __future__ import annotations

import argparse
import ctypes
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parent
ROUTER = SKILLS_ROOT / "sh-user-skills"

FILE_ATTRIBUTE_REPARSE_POINT = 0x400
_KERNEL32 = ctypes.windll.kernel32


def is_link(p: Path) -> bool:
    """junction 与 symlink 共用的 reparse point 判定（Path.is_symlink 不识别 junction）"""
    attrs = _KERNEL32.GetFileAttributesW(str(p))
    return attrs != -1 and bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)


def remove_path(p: Path) -> None:
    """删除文件/真实目录/链接；链接只解除 reparse point 本身，绝不伤及目标内容"""
    if is_link(p):
        os.rmdir(p)
    elif p.is_dir():
        shutil.rmtree(p)
    elif p.is_file():
        p.unlink()


def link_ok(p: Path, target: Path) -> bool:
    if not is_link(p) and not p.is_symlink():
        try:
            return p.is_file() and p.stat().st_size == target.stat().st_size
        except OSError:
            return False
    try:
        return Path(os.path.realpath(p)) == target.resolve()
    except OSError:
        return False


def make_file_link(link: Path, target: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(target, link)
        return
    except OSError:
        pass
    r = subprocess.run(
        ["cmd", "/c", "mklink", "/H", str(link), str(target)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 or not link.exists():
        raise RuntimeError(
            "创建文件链接失败（symlink 无权限，硬链接回退也失败，请开开发者模式或管理员运行）: "
            + (r.stdout + r.stderr).strip()
        )


def make_dir_link(link: Path, target: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        r = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not link.exists():
            raise RuntimeError(f"创建目录链接失败: {(r.stdout + r.stderr).strip()}")


def main() -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("name", help="sh-user-skills 下的子目录名，如 sh-plan-driven-development")
    ap.add_argument("--check", action="store_true", help="dry-run：只打印将执行的动作")
    ap.add_argument("--force", action="store_true", help="先清空目标目录再重建")
    args = ap.parse_args()

    src = ROUTER / args.name
    dst = SKILLS_ROOT / args.name
    if not src.is_dir():
        print(f"错误: 源不存在: {src}")
        return 1
    if (src / "README.md").is_file() is False:
        print(f"错误: 源内没有 README.md: {src}")
        return 1

    actions = 0
    skips = 0

    def do(msg: str, fn=None) -> None:
        nonlocal actions
        print(msg)
        actions += 1
        if not args.check and fn is not None:
            fn()

    def skip(msg: str) -> None:
        nonlocal skips
        print(f"SKIP {msg}")
        skips += 1

    if args.force and dst.exists():
        do(f"FORCE 清空 {dst}", lambda: remove_path(dst))
    dst.mkdir(parents=True, exist_ok=True)

    for entry in sorted(src.iterdir()):
        if entry.name == "README.md":
            link, target = dst / "SKILL.md", entry
            kind = "文件"
        else:
            link, target = dst / entry.name, entry
            kind = "目录" if entry.is_dir() else "文件"
        maker = (lambda l=link, t=target: make_dir_link(l, t)) if entry.is_dir() else (lambda l=link, t=target: make_file_link(l, t))
        if link_ok(link, target):
            skip(f"{link.name} 已指向 {target.name}（{kind}）")
        elif link.exists() or is_link(link):
            do(f"RELINK {link.name} -> {target.name}（{kind}）", lambda l=link, t=target, m=maker: (remove_path(l), m()))
        else:
            do(f"LINK {link.name} -> {target.name}（{kind}）", maker)

    keep = dst / ".gitkeep"
    keep_text = f"本目录为本机软链暴露位，真身在 ./sh-user-skills/{args.name}/（SKILL.md 即其 README.md 的改名链出），链接产物不入库，仅 .gitkeep 占位。\n"
    if keep.is_file() and keep.read_text(encoding="utf-8") == keep_text:
        skip(".gitkeep 已存在")
    else:
        do(".gitkeep 写入占位说明", lambda: keep.write_text(keep_text, encoding="utf-8"))

    ignore = dst / ".gitignore"
    ignore_text = (
        "# 本目录为本机软链暴露位：除本文件与 .gitkeep 外，其余"
        "（SKILL.md、references/、evals/ 等链接产物）一律不入库\n"
        "*\n!.gitkeep\n!/.gitignore\n"
    )
    if ignore.is_file() and ignore.read_text(encoding="utf-8") == ignore_text:
        skip(".gitignore 已存在")
    else:
        do(".gitignore 写入仅留 .gitkeep 规则", lambda: ignore.write_text(ignore_text, encoding="utf-8"))

    for entry in sorted(dst.iterdir()):
        if entry.name in (".gitkeep", ".gitignore", "SKILL.md"):
            continue
        if entry.name != "README.md" and (src / entry.name).exists():
            continue
        if entry.name == "README.md":
            continue
        do(f"REMOVE {entry.name}（源中不存在）", lambda e=entry: remove_path(e))

    print(f"\n完成: {actions} 个动作{'（dry-run）' if args.check else ''}，{skips} 个跳过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
