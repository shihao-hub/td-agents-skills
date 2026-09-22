# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""skills 同步器：以 .agents/skills 为唯一源，同步到 Claude Code / Codex / opencode / Gemini。

默认 link 模式（junction，无需管理员权限）：
- claude / opencode / gemini：整个 skills 目录建成指向源的 junction，源即真身，改源即时生效
- codex：skills 本体保持真实目录（保留内置 .system），其下每个 skill 建 per-skill junction
copy 模式（--mode copy）：镜像复制实体文件，并淘汰目标中源没有的内容（codex 的 .system 保留）。

pi 例外：pi 原生就把 ~/.agents/skills（即本源目录）当全局 skills 加载，并按其真实路径去重，
因此无需任何链接或复制；本脚本仅登记其路径，--agent pi / --agent all 时给出说明而不做改动。

用法：
    uv run sync_skills.py [--mode link|copy] [--agent claude|codex|opencode|gemini|pi|all] [--check]
    sync_skills.bat            # 等价于 uv run sync_skills.py（默认 link + all）
"""

from __future__ import annotations

import argparse
import ctypes
import os
import shutil
import subprocess
import sys
from pathlib import Path

# 源 = 本脚本所在目录（.agents/skills），目录整体搬移也不用改代码
SRC = Path(__file__).resolve().parent

# 需要同步（链接/复制）的 agent 的 skills 根目录
AGENTS = {
    "claude": Path.home() / ".claude" / "skills",
    "codex": Path.home() / ".codex" / "skills",
    "opencode": Path.home() / ".config" / "opencode" / "skills",
    "gemini": Path.home() / ".gemini" / "config" / "skills",
}

# 原生读取源目录、无需同步的 agent；仅登记其 skills 路径用于说明
NATIVE_AGENTS = {
    "pi": Path.home() / ".pi" / "agent" / "skills",
}

# 同步时必须保留、绝不删除的目标内条目（按 agent -> 名称集合）
RESERVED: dict[str, set[str]] = {"codex": {".system"}}

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


def make_junction(link: Path, target: Path) -> None:
    """mklink /J 创建目录联接（cmd 内建命令，需经 cmd 调用）"""
    link.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 or not link.exists():
        raise RuntimeError(f"创建 junction 失败: {(r.stdout + r.stderr).strip()}")


def link_ok(p: Path, target: Path) -> bool:
    """p 是否为已正确指向 target 的链接"""
    if not is_link(p):
        return False
    try:
        return Path(os.path.realpath(p)) == target.resolve()
    except OSError:
        return False


class Sync:
    def __init__(self, mode: str, dry: bool) -> None:
        self.mode = mode
        self.dry = dry
        self.actions = 0
        self.skips = 0

    def log(self, agent: str, action: str, *rest: object) -> None:
        print(f"[{agent:8}] {action:<10} " + " ".join(str(x) for x in rest))

    def do(self, agent: str, action: str, *rest: object, fn=None) -> None:
        self.log(agent, action, *rest)
        self.actions += 1
        if not self.dry and fn is not None:
            fn()

    def skip(self, agent: str, *rest: object) -> None:
        self.log(agent, "SKIP", *rest)
        self.skips += 1

    # ---------- link 模式 ----------

    def sync_link_whole(self, agent: str) -> None:
        """claude / opencode / antigravity：整个 skills 目录替换为指向 SRC 的 junction"""
        dst = AGENTS[agent]
        if not dst.exists():
            self.do(agent, "LINK", dst, "->", SRC,
                    fn=lambda d=dst: make_junction(d, SRC))
        elif link_ok(dst, SRC):
            self.skip(agent, dst, "已指向", SRC)
        elif is_link(dst):
            self.do(agent, "RELINK", dst, "->", SRC,
                    fn=lambda d=dst: (remove_path(d), make_junction(d, SRC)))
        else:
            # 真实目录：整体删除后重建链接（完全覆盖语义）
            self.do(agent, "REPLACE", dst, "->", SRC,
                    fn=lambda d=dst: (remove_path(d), make_junction(d, SRC)))

    def sync_link_per_skill(self, agent: str) -> None:
        """codex：skills 本体保留真实目录，每个 skill 一个 junction；保留 .system"""
        dst_root = AGENTS[agent]
        reserved = RESERVED.get(agent, set())
        if dst_root.exists() and is_link(dst_root):
            self.do(agent, "UNLINK", dst_root, "还原为真实目录",
                    fn=lambda d=dst_root: (remove_path(d), d.mkdir(parents=True)))
        else:
            dst_root.mkdir(parents=True, exist_ok=True)

        src_names = sorted(p.name for p in SRC.iterdir() if p.is_dir())
        for name in src_names:
            dst = dst_root / name
            target = SRC / name
            if link_ok(dst, target):
                self.skip(agent, dst)
            elif is_link(dst):
                self.do(agent, "RELINK", dst, "->", target,
                        fn=lambda d=dst, t=target: (remove_path(d), make_junction(d, t)))
            elif dst.exists():
                self.do(agent, "REPLACE", dst, "->", target,
                        fn=lambda d=dst, t=target: (remove_path(d), make_junction(d, t)))
            else:
                self.do(agent, "LINK", dst, "->", target,
                        fn=lambda d=dst, t=target: make_junction(d, t))

        # 镜像淘汰：目标里源没有的（保留项除外）
        for entry in sorted(dst_root.iterdir()):
            if entry.name in reserved:
                self.skip(agent, entry, "(保留)")
            elif entry.name not in src_names:
                self.do(agent, "REMOVE", entry, "(源中不存在)",
                        fn=lambda e=entry: remove_path(e))

    # ---------- copy 模式 ----------

    def sync_copy_whole(self, agent: str) -> None:
        """claude / opencode / antigravity：删除整个目标目录后镜像复制"""
        dst = AGENTS[agent]

        def copy() -> None:
            if dst.exists():
                remove_path(dst)
            shutil.copytree(SRC, dst)

        if dst.exists() and not is_link(dst):
            self.do(agent, "MIRROR", SRC, "->", dst, fn=copy)
        else:
            self.do(agent, "COPY", SRC, "->", dst, fn=copy)

    def sync_copy_per_skill(self, agent: str) -> None:
        """codex：镜像复制，保留 .system"""
        dst_root = AGENTS[agent]
        reserved = RESERVED.get(agent, set())
        dst_root.mkdir(parents=True, exist_ok=True)

        src_names = {p.name for p in SRC.iterdir() if p.is_dir()}
        for entry in sorted(dst_root.iterdir()):
            if entry.name in reserved:
                self.skip(agent, entry, "(保留)")
            elif entry.name not in src_names or is_link(entry):
                self.do(agent, "REMOVE", entry, fn=lambda e=entry: remove_path(e))

        def copy() -> None:
            shutil.copytree(SRC, dst_root, dirs_exist_ok=True)

        self.do(agent, "MIRROR", SRC, "->", dst_root, fn=copy)

    # ---------- 原生读取源目录的 agent ----------

    def sync_native(self, agent: str) -> None:
        """pi：原生读取源目录，不做任何链接/复制，只给出说明"""
        self.log(agent, "NATIVE", f"{NATIVE_AGENTS[agent]}（原生读取 {SRC}，无需同步）")
        self.skips += 1

    # ---------- 入口 ----------

    def sync(self, agent: str) -> None:
        if agent in NATIVE_AGENTS:
            self.sync_native(agent)
        elif self.mode == "link":
            if agent == "codex":
                self.sync_link_per_skill(agent)
            else:
                self.sync_link_whole(agent)
        else:
            if agent == "codex":
                self.sync_copy_per_skill(agent)
            else:
                self.sync_copy_whole(agent)


def main() -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(
        description="以 .agents/skills 为源同步 skills 到各 agent（pi 原生读取源目录，无需同步）")
    ap.add_argument("--mode", choices=["link", "copy"], default="link",
                    help="link=junction 链接（默认）；copy=镜像复制实体文件")
    ap.add_argument("--agent", choices=[*AGENTS, *NATIVE_AGENTS, "all"], default="all",
                    help="目标 agent（默认 all；pi 为原生读取，仅提示不同步）")
    ap.add_argument("--check", action="store_true",
                    help="dry-run：只打印将执行的动作，不做任何修改")
    args = ap.parse_args()

    targets = [*AGENTS, *NATIVE_AGENTS] if args.agent == "all" else [args.agent]
    s = Sync(args.mode, args.check)

    src_count = len([p for p in SRC.iterdir() if p.is_dir()])
    print(f"源: {SRC} ({src_count} skills)  模式: {args.mode}"
          f"{'  [dry-run]' if args.check else ''}\n")

    for agent in targets:
        if not SRC.exists():
            print(f"错误: 源目录不存在: {SRC}")
            return 1
        try:
            s.sync(agent)
        except Exception as exc:  # noqa: BLE001
            print(f"[{agent:8}] ERROR    {exc}")
            return 1

    print(f"\n完成: {s.actions} 个动作"
          f"{'（dry-run，未实际执行）' if args.check else ''}，{s.skips} 个跳过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
