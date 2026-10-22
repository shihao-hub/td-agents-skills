# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""sync_standby_skills.py: 备用低频技能与 sh-standby-skills 路由器的资产双向管理与自动化同步工具。

核心设计哲学：脚本归脚本，AI 归 AI (AI-in-the-Loop)
- 脚本负责：任意技能的收拢/移动、一键还原(--restore)、磁盘真实目录全景扫描、自动重新渲染 SKILL.md 路由表。
- AI 负责：日常意图按需单点调入执行，保证全局上下文零常驻污染。

用法示例:
    python sync_standby_skills.py move <skill1> [skill2 ...] # 将指定根级技能移入备用库，并自动刷新路由表
    python sync_standby_skills.py restore <skill1> [skill2] # 将指定备用技能移回根目录，并自动刷新路由表
    python sync_standby_skills.py --restore-all             # 一键将所有备用技能全部还原回根目录
    python sync_standby_skills.py --check                   # 状态检查与诊断
    python sync_standby_skills.py --json                    # 输出 JSON 格式诊断数据
    python sync_standby_skills.py                           # 默认：根据真实目录重新生成 SKILL.md 路由表
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

# 根技能仓库目录 (~/.agents/skills)
ROOT_SKILLS_DIR = Path(__file__).resolve().parent

# 目标路由器目录 (~/.agents/skills/sh-standby-skills)
ROUTER_DIR_NAME = "sh-standby-skills"
ROUTER_DIR = ROOT_SKILLS_DIR / ROUTER_DIR_NAME
ROUTER_SKILL_MD = ROUTER_DIR / "SKILL.md"


def get_skill_description(skill_dir: Path) -> str:
    """提取技能的一句话描述"""
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        skill_file = skill_dir / "README.md"
    if not skill_file.exists():
        return "通用备用技能"

    try:
        raw = skill_file.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"(?ms)^description:\s*([^\r\n]+)", raw)
        if m:
            clean = m.group(1).strip().strip("\"'|")
            return clean[:65]
        # 尝试多行
        m2 = re.search(r"(?ms)^description:\s*\|?\s*\n\s*([^\r\n]+)", raw)
        if m2:
            clean = m2.group(1).strip().strip("\"'|")
            return clean[:65]
    except Exception:
        pass
    return "通用备用技能"


def refresh_router_skill_md():
    """根据真实存在的子目录，全自动重新渲染 sh-standby-skills/SKILL.md"""
    if not ROUTER_DIR.exists():
        ROUTER_DIR.mkdir(parents=True, exist_ok=True)

    subdirs = sorted(
        [d for d in ROUTER_DIR.iterdir() if d.is_dir() and not d.name.startswith((".", "__"))]
    )

    table_rows = []
    for d in subdirs:
        desc = get_skill_description(d)
        entry_file = "SKILL.md" if (d / "SKILL.md").exists() else ("README.md" if (d / "README.md").exists() else "SKILL.md")
        table_rows.append(f"| `{d.name}` | {desc} | `{ROUTER_DIR_NAME}/{d.name}/{entry_file}` |")

    table_str = "\n".join(table_rows) if table_rows else "| (当前无收拢技能) | - | - |"

    # 生成紧凑的 SKILL.md
    names_summary = ", ".join(d.name for d in subdirs)
    content = f"""---
name: sh-standby-skills
description: |
  备用与低频技能收拢库：集中存放暂不使用但保留备查的各类通用技能（{names_summary}）。点名使用。
disable-model-invocation: true
version: 1.0.0
created: 2026-10-22
updated: 2026-10-23
---

# sh-standby-skills: 备用与低频技能收拢库

> **核心定位**：非永久废弃（Non-Archived），而是**“按需唤醒的备用抽屉”**。  
> 核心目标是**极大减少日常 AI 会话的上下文占用**。平常零常驻加载、零提示词污染；仅在用户明确需要参考对应设计模式、架构理论或代码库提取时按需单点调入。

---

## 调取与执行协议

当用户明确点名或提及调取本库内的某项技能时：
1. AI 使用专用读文件工具（`read_file`）单点加载对应子目录下的入口文档；
2. 严格按其 SOP 步骤执行，执行完成后释放，绝不污染全局常驻上下文；
3. 执行时提示用户该技能已处于备用库模式。

---

## 备用技能清单（不作多余分类，扁平收拢，共 {len(subdirs)} 项）

| 技能名称 | 原始核心职责与领域 | 物理寻址路径 |
| :--- | :--- | :--- |
{table_str}

---

## 资产运维与双向迁移

本仓库配有双向自动化同步工具 `sync_standby_skills.py`：
- **将技能移入备用库**：`uv run sync_standby_skills.py move <skill1> [skill2 ...]`
- **将技能还原至根目录**：`uv run sync_standby_skills.py restore <skill1> [skill2 ...]`
- **一键全量还原**：`uv run sync_standby_skills.py --restore-all`
- **状态检查**：`uv run sync_standby_skills.py --check`
- **自动对齐刷新路由表**：`uv run sync_standby_skills.py`
"""
    ROUTER_SKILL_MD.write_text(content, encoding="utf-8")


def scan_status() -> dict:
    """扫描当前状态并生成诊断结果"""
    routed_subdirs = []
    if ROUTER_DIR.exists() and ROUTER_DIR.is_dir():
        for item in ROUTER_DIR.iterdir():
            if item.is_dir() and not item.name.startswith((".", "__")):
                routed_subdirs.append(item.name)
    routed_subdirs.sort()

    return {
        "routed_subdirs": routed_subdirs,
        "router_exists": ROUTER_DIR.exists(),
        "total_routed": len(routed_subdirs),
    }


def move_skills(skill_names: list[str], dry_run: bool = False) -> dict:
    """将指定根级技能移入 sh-standby-skills/"""
    actions = []
    errors = []

    if not ROUTER_DIR.exists() and not dry_run:
        ROUTER_DIR.mkdir(parents=True, exist_ok=True)

    for name in skill_names:
        src = ROOT_SKILLS_DIR / name
        if not src.exists() or not src.is_dir():
            errors.append(f"Source not found in root: {name}")
            continue

        dest = ROUTER_DIR / name
        act = f"Move root/{name} -> {ROUTER_DIR_NAME}/{name}"
        if not dry_run:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.move(str(src), str(dest))
        actions.append(act)

    if not dry_run:
        refresh_router_skill_md()

    return {
        "status": "success" if not dry_run else "dry-run",
        "actions_performed": actions,
        "errors": errors,
        "total_standby_now": len(scan_status()["routed_subdirs"]),
    }


def restore_skills(skill_names: list[str] | None = None, dry_run: bool = False) -> dict:
    """将备用库中的技能移回根目录（指定或全部）"""
    actions = []
    errors = []

    status = scan_status()
    all_routed = status["routed_subdirs"]

    targets = skill_names if skill_names else all_routed

    for name in targets:
        src = ROUTER_DIR / name
        if not src.exists() or not src.is_dir():
            errors.append(f"Standby skill not found: {name}")
            continue

        dest = ROOT_SKILLS_DIR / name
        act = f"Restore {ROUTER_DIR_NAME}/{name} -> root/{name}"
        if not dry_run:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.move(str(src), str(dest))
        actions.append(act)

    if not dry_run:
        refresh_router_skill_md()

    return {
        "status": "success" if not dry_run else "dry-run",
        "actions_performed": actions,
        "errors": errors,
        "total_standby_now": len(scan_status()["routed_subdirs"]),
    }


def main():
    parser = argparse.ArgumentParser(
        description="备用低频技能资产管理与双向迁移同步工具（sh-standby-skills）"
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # move
    move_parser = subparsers.add_parser("move", help="将指定根目录技能收拢至备用库")
    move_parser.add_argument("skills", nargs="+", help="技能目录名（空格分隔）")
    move_parser.add_argument("--dry-run", action="store_true", help="演练模式")

    # restore
    restore_parser = subparsers.add_parser("restore", help="将指定备用技能恢复至根目录")
    restore_parser.add_argument("skills", nargs="+", help="技能目录名（空格分隔）")
    restore_parser.add_argument("--dry-run", action="store_true", help="演练模式")

    # flags for root
    parser.add_argument("--restore-all", action="store_true", help="一键将所有备用技能恢复至根目录")
    parser.add_argument("--check", action="store_true", help="检查当前备用库收纳状态")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式诊断数据")
    parser.add_argument("--refresh", action="store_true", help="强制根据真实目录重新生成 SKILL.md 路由表")
    parser.add_argument("--dry-run", action="store_true", help="演练模式")

    args = parser.parse_args()

    if args.json:
        status = scan_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return

    if args.check:
        status = scan_status()
        print("=== sh-standby-skills 备用库收纳状态 ===")
        print(f"备用库目录是否存在: {status['router_exists']}")
        print(f"当前收拢在备用库的技能总数: {status['total_routed']}")
        for s in status["routed_subdirs"]:
            print(f"  [STANDBY] {s} (已隔离，不占用全局上下文)")
        return

    if args.command == "move":
        res = move_skills(args.skills, dry_run=args.dry_run)
        print(f"[{res['status'].upper()}]")
        for act in res["actions_performed"]:
            print(f"  -> {act}")
        for err in res["errors"]:
            print(f"  [ERROR] {err}")
        print(f"当前备用库技能总数: {res['total_standby_now']}")
        return

    if args.command == "restore":
        res = restore_skills(args.skills, dry_run=args.dry_run)
        print(f"[{res['status'].upper()}]")
        for act in res["actions_performed"]:
            print(f"  -> {act}")
        for err in res["errors"]:
            print(f"  [ERROR] {err}")
        print(f"当前备用库技能总数: {res['total_standby_now']}")
        return

    if args.restore_all:
        res = restore_skills(None, dry_run=args.dry_run)
        print(f"[{res['status'].upper()}] 全部备用技能恢复完成")
        for act in res["actions_performed"]:
            print(f"  -> {act}")
        return

    # 默认：刷新路由表
    refresh_router_skill_md()
    print("[SUCCESS] 已对齐并刷新 sh-standby-skills/SKILL.md 路由表。")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
