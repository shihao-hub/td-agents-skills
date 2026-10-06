# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""sync_redis_skills.py: Redis 与 Iris 官方散装技能与 sh-redis-skills 路由器的资产同步与双向迁移工具。

核心设计哲学：脚本归脚本，AI 归 AI (AI-in-the-Loop)
- 脚本负责：文件原子移动/覆盖、根目录清理、还原(--restore)、探针检测、JSON 诊断报告
- AI 负责：日常感知意图精准分流、解读新 domain 文档并刷新路由消歧规则、评估官方原生 suite 就绪度

用法:
    python sync_redis_skills.py                # 执行收割迁移（将根目录散装 redis/iris 技能移入 sh-redis-skills/）
    python sync_redis_skills.py --dry-run      # 预览执行计划，不修改文件
    python sync_redis_skills.py --check        # 仅状态检查与探针诊断
    python sync_redis_skills.py --restore      # 【一键复原】将 sh-redis-skills/ 子目录全部移回根目录
    python sync_redis_skills.py --json         # 输出结构化诊断数据，供 AI Agent 直接解析
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

# 目标路由器目录 (~/.agents/skills/sh-redis-skills)
ROUTER_DIR_NAME = "sh-redis-skills"
ROUTER_DIR = ROOT_SKILLS_DIR / ROUTER_DIR_NAME

# 默认 8 域官方组件清单
OFFICIAL_REDIS_SKILLS = [
    "iris-development",
    "redis-clustering",
    "redis-connections",
    "redis-core",
    "redis-observability",
    "redis-search",
    "redis-security",
    "redis-semantic-cache",
]

def probe_official_suite() -> dict:
    """探针：检查官方是否已经提供了原生一体化 suite (非散装模式)"""
    reasons = []
    ready = False
    suite_dir = ROOT_SKILLS_DIR / "redis-suite"
    if suite_dir.exists() and (suite_dir / "SKILL.md").exists():
        ready = True
        reasons.append("Found official 'redis-suite' directory with SKILL.md in root")
    return {
        "ready": ready,
        "reasons": reasons,
    }

def find_known_routed_domains() -> set[str]:
    """从 sh-redis-skills/SKILL.md 中解析出已经被路由表收录的 domain 名称"""
    router_skill_md = ROUTER_DIR / "SKILL.md"
    routed = set()
    if router_skill_md.exists():
        try:
            content = router_skill_md.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("- `redis-") or line.startswith("| `redis-") or line.startswith("- `iris-") or line.startswith("| `iris-"):
                    parts = line.split("`")
                    for p in parts:
                        if (p.startswith("redis-") or p.startswith("iris-")) and " " not in p:
                            routed.add(p)
        except Exception:
            pass
    return routed

def scan_status():
    """扫描当前状态并生成诊断结果"""
    target_set = set(OFFICIAL_REDIS_SKILLS)
    root_loose_dirs = []
    for item in ROOT_SKILLS_DIR.iterdir():
        if item.is_dir() and not item.name.startswith("sh-"):
            if item.name in target_set or ((item.name.startswith("redis-") or item.name.startswith("iris-")) and (item / "SKILL.md").exists()):
                root_loose_dirs.append(item.name)
    root_loose_dirs.sort()

    routed_subdirs = []
    if ROUTER_DIR.exists() and ROUTER_DIR.is_dir():
        for item in ROUTER_DIR.iterdir():
            if item.is_dir() and (item.name.startswith("redis-") or item.name.startswith("iris-")) and (item / "SKILL.md").exists():
                routed_subdirs.append(item.name)
    routed_subdirs.sort()

    routed_in_md = find_known_routed_domains()
    all_known_domains = set(routed_subdirs) | set(root_loose_dirs)
    new_domains = [d for d in all_known_domains if d not in routed_in_md and d not in OFFICIAL_REDIS_SKILLS]

    suite_probe = probe_official_suite()
    return {
        "root_loose_dirs": root_loose_dirs,
        "routed_subdirs": routed_subdirs,
        "new_domains": new_domains,
        "suite_probe": suite_probe,
        "router_exists": ROUTER_DIR.exists(),
    }

def sync_to_router(dry_run: bool = False) -> dict:
    """将根目录散装官方技能收拢至 sh-redis-skills/"""
    status = scan_status()
    loose = status["root_loose_dirs"]
    actions = []

    if not loose:
        return {
            "status": "success",
            "message": "No loose redis/iris skills in root directory. Clean state.",
            "actions_performed": [],
            "details": status,
        }

    if not dry_run:
        ROUTER_DIR.mkdir(parents=True, exist_ok=True)

    for name in loose:
        src = ROOT_SKILLS_DIR / name
        dst = ROUTER_DIR / name
        if dst.exists():
            action_desc = f"UPDATE: {name} (overwrite {dst.relative_to(ROOT_SKILLS_DIR)})"
            actions.append(action_desc)
            if not dry_run:
                shutil.rmtree(dst)
                shutil.move(str(src), str(dst))
        else:
            action_desc = f"MOVE: {name} -> {dst.relative_to(ROOT_SKILLS_DIR)}"
            actions.append(action_desc)
            if not dry_run:
                shutil.move(str(src), str(dst))

    post_status = scan_status() if not dry_run else status
    return {
        "status": "success",
        "dry_run": dry_run,
        "actions_performed": actions,
        "details": post_status,
    }

def restore_to_root(dry_run: bool = False) -> dict:
    """【一键复原】将 sh-redis-skills/ 下的子技能全部还原移回根目录"""
    if not ROUTER_DIR.exists():
        return {
            "status": "noop",
            "message": f"{ROUTER_DIR_NAME} does not exist. Nothing to restore.",
            "actions_performed": [],
        }

    subdirs = [p for p in ROUTER_DIR.iterdir() if p.is_dir() and (p.name.startswith("redis-") or p.name.startswith("iris-"))]
    if not subdirs:
        return {
            "status": "noop",
            "message": f"No sub-skills found inside {ROUTER_DIR_NAME}.",
            "actions_performed": [],
        }

    actions = []
    for sub in subdirs:
        dst = ROOT_SKILLS_DIR / sub.name
        action_desc = f"RESTORE: {sub.name} -> {dst.relative_to(ROOT_SKILLS_DIR)}"
        actions.append(action_desc)
        if not dry_run:
            if dst.exists():
                shutil.rmtree(dst)
            shutil.move(str(sub), str(dst))

    return {
        "status": "success",
        "dry_run": dry_run,
        "actions_performed": actions,
        "message": f"Successfully restored {len(actions)} skills to root directory.",
    }

def print_human_report(status_data: dict, action_result: dict | None = None):
    print("=" * 65)
    print("      sh-redis-skills Redis 资产同步与 AI 协同诊断报告")
    print("=" * 65)

    if action_result:
        dry = " [DRY-RUN 预览模式]" if action_result.get("dry_run") else ""
        print(f"\n[操作执行结果{dry}]")
        print(f"  状态: {action_result.get('status')}")
        if action_result.get("message"):
            print(f"  说明: {action_result.get('message')}")
        actions = action_result.get("actions_performed", [])
        if actions:
            print("  动作列表:")
            for a in actions:
                print(f"    * {a}")

    print("\n[当前目录状态]")
    loose = status_data.get("root_loose_dirs", [])
    routed = status_data.get("routed_subdirs", [])
    print(f"  根目录散装 redis/iris 数量 : {len(loose)} 个")
    if loose:
        print(f"    -> 散装清单: {', '.join(loose)}")
    print(f"  sh-redis-skills 已收拢    : {len(routed)} 个")
    print(f"  sh-redis-skills 目录状态  : {'已就绪' if status_data.get('router_exists') else '尚未创建'}")

    print("\n[AI 感知中枢与探针诊断 (AI-in-the-Loop)]")
    new_domains = status_data.get("new_domains", [])
    if new_domains:
        print(f"  [NEW DOMAIN 发现官方新增域]: {', '.join(new_domains)}")
        print("      提示 AI: 发现新 Redis 业务域！请 AI 读取该域的 SKILL.md，更新顶层路由表并补充消歧规则。")
    else:
        print("  - 业务域状态: 当前无未收录的官方新增域。")

    suite_probe = status_data.get("suite_probe", {})
    if suite_probe.get("ready"):
        print("  [OFFICIAL SUITE READY 官方原生套件就绪!]")
        for r in suite_probe.get("reasons", []):
            print(f"      - {r}")
        print("      提示 AI: 官方原生一体化套件已就绪！请 AI 向用户发起评估，研判是否切回官方原生。")
    else:
        print("  - 官方套件探针: 官方仍为 separate 散装模式，自建 sh-redis-skills 路由器保持生效。")

    print("=" * 65)

def main():
    parser = argparse.ArgumentParser(description="sh-redis-skills Redis 资产同步与 AI 协同迁移工具")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--restore", "-r", action="store_true", help="【一键复原】将 sh-redis-skills 中的所有子技能还原回根目录")
    group.add_argument("--check", "-c", action="store_true", help="仅状态检查与探针诊断，不修改任何文件")
    parser.add_argument("--dry-run", "-n", action="store_true", help="演练模式，预览将要执行的操作")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出诊断信息，供 AI 机器解析")

    args = parser.parse_args()

    if args.restore:
        result = restore_to_root(dry_run=args.dry_run)
        curr_status = scan_status()
        if args.json:
            print(json.dumps({"action": "restore", "result": result, "status": curr_status}, ensure_ascii=False, indent=2))
        else:
            print_human_report(curr_status, result)
        return

    if args.check:
        curr_status = scan_status()
        if args.json:
            print(json.dumps({"action": "check", "status": curr_status}, ensure_ascii=False, indent=2))
        else:
            print_human_report(curr_status)
        return

    result = sync_to_router(dry_run=args.dry_run)
    curr_status = scan_status()
    if args.json:
        print(json.dumps({"action": "sync", "result": result, "status": curr_status}, ensure_ascii=False, indent=2))
    else:
        print_human_report(curr_status, result)

if __name__ == "__main__":
    main()
