# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""sync_mattpocock_skills.py: Matt Pocock 纯正技能与 sh-mattpocock-skills 路由器的资产同步与双向迁移工具。

核心设计哲学：脚本归脚本，AI 归 AI (AI-in-the-Loop)
- 脚本负责：文件原子移动/覆盖、根目录清理、还原(--restore)、探针检测、JSON 诊断报告
- AI 负责：日常意图精准分流、生命周期流转编排、架构演进与深模块重构建议

用法:
    python sync_mattpocock_skills.py                # 执行收割迁移（将根目录散装 Matt Pocock 技能移入 sh-mattpocock-skills/）
    python sync_mattpocock_skills.py --dry-run      # 预览执行计划，不修改文件
    python sync_mattpocock_skills.py --check        # 仅状态检查与探针诊断
    python sync_mattpocock_skills.py --restore      # 【一键复原】将 sh-mattpocock-skills/ 子目录全部移回根目录
    python sync_mattpocock_skills.py --json         # 输出结构化诊断数据，供 AI Agent 直接解析
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

# 目标路由器目录 (~/.agents/skills/sh-mattpocock-skills)
ROUTER_DIR_NAME = "sh-mattpocock-skills"
ROUTER_DIR = ROOT_SKILLS_DIR / ROUTER_DIR_NAME

# 严格限定的 14 个 Matt Pocock 原生工程技能
OFFICIAL_MATT_POCOCK_SKILLS = [
    "wayfinder",
    "research",
    "prototype",
    "grill-me",
    "grilling",
    "grill-with-docs",
    "domain-modeling",
    "to-spec",
    "to-tickets",
    "implement",
    "tdd",
    "code-review",
    "diagnosing-bugs",
    "improve-codebase-architecture",
]


def scan_status():
    """扫描当前状态并生成诊断结果"""
    target_set = set(OFFICIAL_MATT_POCOCK_SKILLS)
    root_loose_dirs = []
    for item in ROOT_SKILLS_DIR.iterdir():
        if item.is_dir() and item.name in target_set:
            if (item / "SKILL.md").exists():
                root_loose_dirs.append(item.name)
    root_loose_dirs.sort()

    routed_subdirs = []
    if ROUTER_DIR.exists() and ROUTER_DIR.is_dir():
        for item in ROUTER_DIR.iterdir():
            if item.is_dir() and item.name in target_set:
                if (item / "SKILL.md").exists():
                    routed_subdirs.append(item.name)
    routed_subdirs.sort()

    return {
        "root_loose_dirs": root_loose_dirs,
        "routed_subdirs": routed_subdirs,
        "router_exists": ROUTER_DIR.exists(),
        "total_official": len(OFFICIAL_MATT_POCOCK_SKILLS),
    }


def sync_to_router(dry_run: bool = False) -> dict:
    """将根目录散装 Matt Pocock 技能收拢至 sh-mattpocock-skills/"""
    status = scan_status()
    loose = status["root_loose_dirs"]
    actions = []

    if not loose:
        return {
            "status": "success",
            "message": "No loose Matt Pocock skills in root directory. Clean state.",
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
    """【一键复原】将 sh-mattpocock-skills/ 子目录全部移回根目录"""
    status = scan_status()
    routed = status["routed_subdirs"]
    actions = []

    if not routed:
        return {
            "status": "noop",
            "message": "No routed skills found in sh-mattpocock-skills/ to restore.",
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
        description="Matt Pocock 技能资产管理与双向迁移同步工具"
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
        help="一键复原：将收拢在 sh-mattpocock-skills/ 下的子技能移回根目录",
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
        print("=== Matt Pocock Skills 收拢状态检查 ===")
        print(f"根目录散装数量: {len(status['root_loose_dirs'])}")
        for item in status["root_loose_dirs"]:
            print(f"  - [散装] {item}")
        print(f"路由器收拢数量: {len(status['routed_subdirs'])}")
        for item in status["routed_subdirs"]:
            print(f"  - [已收拢] {item}")
        print(f"官方规范技能总数: {status['total_official']}")
        return

    if args.restore:
        print(">>> 正在执行一键复原到根目录...")
        res = restore_to_root(dry_run=args.dry_run)
        for act in res["actions_performed"]:
            print(f"  {act}")
        print(f"复原完成: {res['status']}")
        return

    # 默认：迁移收拢到路由器
    print(">>> 正在执行收拢迁移到 sh-mattpocock-skills/ ...")
    res = sync_to_router(dry_run=args.dry_run)
    for act in res["actions_performed"]:
        print(f"  {act}")
    print(f"迁移完成: {res['status']}")


if __name__ == "__main__":
    main()
