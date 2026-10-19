# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""把 sh-user-skills/<name>/ 以「相对软链」暴露为根级 <name>/：README.md 改名链出为 SKILL.md，其余内容原名链出。

链接本身随仓入库（git 以 mode 120000 记录链接文本），因此必须是**相对路径**链接：
仓库换盘/换机/换工作副本（如 ~/.agents/skills 与本仓 .agents/skills 双入口）都不用重建。

用法：
    uv run expose_user_skill.py <name> [--check] [--force]
    uv run expose_user_skill.py sh-plan-driven-development --check
"""

from __future__ import annotations

import argparse
import ctypes
import os
import subprocess
import sys
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parent
ROUTER = SKILLS_ROOT / "sh-user-skills"

FILE_ATTRIBUTE_REPARSE_POINT = 0x400
_IS_WINDOWS = sys.platform == "win32"
_KERNEL32 = ctypes.windll.kernel32 if _IS_WINDOWS else None

# 历史遗留占位文件：链接入库后不再需要，脚本遇到即清理
LEGACY_FILES = (".gitkeep", ".gitignore")


def is_link(p: Path) -> bool:
    """junction 与 symlink 共用的 reparse point 判定（Path.is_symlink 不识别 junction）"""
    if not _IS_WINDOWS:
        return p.is_symlink()
    attrs = _KERNEL32.GetFileAttributesW(str(p))
    return attrs != -1 and bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)


def remove_path(p: Path) -> None:
    """删除文件/真实目录/链接；链接只解除 reparse point 本身，绝不伤及目标内容"""
    if is_link(p):
        try:
            os.rmdir(p)  # junction 与目录软链
        except OSError:
            p.unlink()  # 文件软链（含断链）
        return
    if p.is_dir():
        for child in p.iterdir():
            remove_path(child)
        os.rmdir(p)
    elif p.is_file():
        p.unlink()


def link_ok(p: Path, target: Path) -> bool:
    """链接存在、文本与预期的相对形式一致、且能解析到真身才算合格。

    非链接（历史硬链接/拷贝）或遗留绝对路径链接（换机即断）一律判不合格，触发重建。
    """
    if not is_link(p) and not p.is_symlink():
        return False
    try:
        if os.readlink(p) != link_text(p, target):
            return False
        return Path(os.path.realpath(p)) == target.resolve()
    except OSError:
        return False


def link_text(link: Path, target: Path) -> str:
    """构造写入 reparse point 的相对链接文本。

    Windows 限制：相对软链的目标若含正斜杠 `/`，原生 API（Node/PowerShell/.NET）解析失败，
    必须用反斜杠；POSIX 下则沿用 `/`。链接文本会随 git 入库，故此处差异需明示保留。
    """
    rel = os.path.relpath(target, link.parent)
    return rel.replace(os.sep, "\\") if _IS_WINDOWS else rel


def make_symlink(link: Path, target: Path) -> None:
    """建软链。不做硬链接/junction 兜底：那两种形态 git 无法以链接模式入库（会被当成真实文件/目录递归收录）。"""
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(
            link_text(link, target),
            link,
            target_is_directory=target.is_dir(),
        )
    except OSError as exc:
        raise RuntimeError(
            f"创建软链失败: {link} -> {target}\n"
            f"  原因: {exc}\n"
            "  修复: Windows 需开启「设置 → 系统 → 开发者选项 → 开发人员模式」（或管理员执行本脚本），"
            "POSIX 需允许 symlink。本脚本刻意不做硬链接/junction 兜底——它们无法以链接模式随 git 入库。"
        ) from exc


def check_core_symlinks() -> None:
    """core.symlinks=false 的仓库会把入库链接检出成普通文本文件，届时技能发现会静默失败，故提示。"""
    try:
        r = subprocess.run(
            ["git", "-C", str(SKILLS_ROOT), "config", "--get", "core.symlinks"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return
    if r.stdout.strip().lower() == "false":
        print(
            "警告: 本仓 core.symlinks=false，检出时会把手动链接/入库链接落成普通文件；"
            "请执行 `git config core.symlinks true` 后重建链接。"
        )


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
    if not (src / "README.md").is_file():
        print(f"错误: 源内没有 README.md: {src}")
        return 1

    check_core_symlinks()

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
            link, target, kind = dst / "SKILL.md", entry, "文件"
        else:
            link, target = dst / entry.name, entry
            kind = "目录" if entry.is_dir() else "文件"
        if link_ok(link, target):
            skip(f"{link.name} 已指向 {target.name}（{kind}）")
        elif link.exists() or is_link(link):
            do(f"RELINK {link.name} -> {target.name}（{kind}）", lambda l=link, t=target: (remove_path(l), make_symlink(l, t)))
        else:
            do(f"LINK {link.name} -> {target.name}（{kind}）", lambda l=link, t=target: make_symlink(l, t))

    for legacy in LEGACY_FILES:
        p = dst / legacy
        if p.exists() or is_link(p):
            do(f"REMOVE 遗留占位 {legacy}（链接已入库，占位文件不再需要）", lambda p=p: remove_path(p))

    for entry in sorted(dst.iterdir()):
        if entry.name in LEGACY_FILES or entry.name == "SKILL.md":
            continue
        if (src / entry.name).exists():
            continue
        do(f"REMOVE {entry.name}（源中不存在）", lambda e=entry: remove_path(e))

    print(f"\n完成: {actions} 个动作{'（dry-run）' if args.check else ''}，{skips} 个跳过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
