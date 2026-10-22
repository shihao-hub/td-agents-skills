# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""sync_standby_skills.py: 低频备用技能与 sh-standby-skills 路由器的资产同步与双向迁移工具。

核心设计哲学：脚本归脚本，AI 归 AI (AI-in-the-Loop)
- 脚本负责：文件原子移动/覆盖、根目录清理、还原(--restore)、探针检测、JSON 诊断报告
- AI 负责：日常意图按需调取、单点文件读取加载，实现全局上下文零常驻污染

用法:
    python sync_standby_skills.py                # 执行收拢迁移（将根目录散装低频技能移入 sh-standby-skills/）
    python sync_standby_skills.py --dry-run      # 预览执行计划，不修改文件
    python sync_standby_skills.py --check        # 仅状态检查与探针诊断
    python sync_standby_skills.py --restore      # 【一键复原】将 sh-standby-skills/ 子目录全部移回根目录
    python sync_standby_skills.py --json         # 输出结构化诊断数据，供 AI Agent 直接解析
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

# 根技能仓库目录 (~/.agents/skills)
ROOT_SKILLS_DIR = Path(__file__).resolve().parent

# 目标路由器目录 (~/.agents/skills/sh-standby-skills)
ROUTER_DIR_NAME = "sh-standby-skills"
ROUTER_DIR = ROOT_SKILLS_DIR / ROUTER_DIR_NAME

# 指定收拢入备用库的 6 个低频技能（不按技能分类，统一存放）
STANDBY_SKILLS = [
    "architecture-patterns",
    "clean-code",
    "frontend-design",
    "git-advanced-workflows",
    "python-design-patterns",
    "zread",
]


def scan_status() -> dict:
    """扫描当前状态并生成诊断结果"""
    target_set = set(STANDBY_SKILLS)
    root_loose_dirs = []
    for item in ROOT_SKILLS_DIR.iterdir():
        if item.is_dir() and item.name in target_set:
            if (item / "SKILL.md").exists() or (item / "README.md").exists():
                root_loose_dirs.append(item.name)
    root_loose_dirs.sort()

    routed_subdirs = []
    if ROUTER_DIR.exists() and ROUTER_DIR.is_dir():
        for item in ROUTER_DIR.iterdir():
            if item.is_dir() and item.name in target_set:
                if (item / "SKILL.md").exists() or (item / "README.md").exists():
                    routed_subdirs.append(item.name)
    routed_subdirs.sort()

    return {
        "root_loose_dirs": root_loose_dirs,
        "routed_subdirs": routed_subdirs,
        "router_exists": ROUTER_DIR.exists(),
        "total_targets": len(STANDBY_SKILLS),
    }


def sync_to_router(dry_run: bool = False) -> dict:
    """将根目录散装低频技能收拢至 sh-standby-skills/"""
    status = scan_status()
    loose = status["root_loose_dirs"]
    actions = []

    if not loose:
        return {
            "status": "success",
            "message": "No loose standby skills in root directory. Clean state.",
            "actions_performed": [],
            "details": status,
        }

    if not ROUTER_DIR.exists():
        if not dry_run:
            ROUTER_DIR.mkdir(parents=True, exist_ok=True)
        actions.append(f"Create directory: {ROUTER_DIR_NAME}")

    for skill_name in loose:
        src = ROOT_SKILLS_DIR / skill_name
        dest = ROUTER_DIR / skill_name
        act = f"Move {src.name} -> {ROUTER_DIR_NAME}/{dest.name}"
        if not dry_run:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.move(str(src), str(dest))
        actions.append(act)

    return {
        "status": "success" if not dry_run else "dry-run",
        "actions_performed": actions,
        "details": scan_status(),
    }


def restore_to_root(dry_run: bool = False) -> dict:
    """【一键复原】将 sh-standby-skills/ 子目录全部移回根目录"""
    status = scan_status()
    routed = status["routed_subdirs"]
    actions = []

    if not routed:
        return {
            "status": "noop",
            "message": "No routed skills found in sh-standby-skills/ to restore.",
            "actions_performed": [],
        }

    for skill_name in routed:
        src = ROUTER_DIR / skill_name
        dest = ROOT_SKILLS_DIR / skill_name
        act = f"Restore {ROUTER_DIR_NAME}/{src.name} -> {dest.name}"
        if not dry_run:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.move(str(src), str(dest))
        actions.append(act)

    return {
        "status": "success" if not dry_run else "dry-run",
        "actions_performed": actions,
        "details": scan_status(),
    }


def main():
    parser = argparse.ArgumentParser(
        description="备用低频技能资产管理与双向迁移同步工具"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览将执行的操作，不实际修改磁盘",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="仅检查当前收拢状态与诊断信息，不做变更",
    )
    parser.add_argument(
        "--restore",
        action="store_true",
        help="一键复原：将收拢在 sh-standby-skills/ 下的子技能移回根目录",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出 JSON 格式诊断数据",
    )

    args = parser.parse_args()

    if args.json:
        status = scan_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return

    if args.check:
        status = scan_status()
        print("=== Standby Skills 收拢状态检查 ===")
        print(f"路由器目录是否存在: {status['router_exists']}")
        print(f"根目录散装待收拢技能 ({len(status['root_loose_dirs'])}):")
        for s in status["root_loose_dirs"]:
            print(f"  [!] {s} (在根目录，仍会占用全局上下文)")
        print(f"已收拢在路由器的备用技能 ({len(status['routed_subdirs'])}):")
        for s in status["routed_subdirs"]:
            print(f"  [OK] {s} (已隔离，不占用全局上下文)")
        return

    if args.restore:
        res = restore_to_root(dry_run=args.dry_run)
        print(f"[{res['status'].upper()}] {res.get('message', '')}")
        for act in res.get("actions_performed", []):
            print(f"  -> {act}")
        return

    # 默认：收拢迁移
    res = sync_to_router(dry_run=args.dry_run)
    print(f"[{res['status'].upper()}] {res.get('message', 'Sync completed')}")
    for act in res.get("actions_performed", []):
        print(f"  -> {act}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
