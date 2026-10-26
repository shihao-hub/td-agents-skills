# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""sync_mattpocock_repo.py: mattpocock/skills 官方仓库资产同步与更新工具。

职责：
- 从 GitHub 官方仓库 (https://github.com/mattpocock/skills.git) 探测并拉取最新技能
- 镜像同步至本地 sh-mattpocock-skills/skills/ 目录
- 提供状态检查、已下载技能盘点与结构化 JSON 报告

用法:
    python sync_mattpocock_repo.py --list      # 列出本地已下载的全部技能及其分类
    python sync_mattpocock_repo.py --check     # 探测远程仓库最新 Commit，比对是否有更新
    python sync_mattpocock_repo.py --update    # 拉取最新代码并同步更新本地 skills/ 目录
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent
LOCAL_SKILLS_DIR = SKILL_ROOT / "skills"
REPO_URL = "https://github.com/mattpocock/skills.git"
VERSION_FILE = SKILL_ROOT / ".upstream-version.json"


def list_local_skills() -> dict[str, list[dict[str, str]]]:
    """扫描本地已下载的官方技能"""
    if not LOCAL_SKILLS_DIR.exists():
        return {}

    inventory: dict[str, list[dict[str, str]]] = {}
    for cat in sorted(LOCAL_SKILLS_DIR.iterdir()):
        if not cat.is_dir():
            continue
        skills_in_cat = []
        for sk in sorted(cat.iterdir()):
            if not sk.is_dir():
                continue
            skill_md = sk / "SKILL.md"
            desc = ""
            if skill_md.exists():
                try:
                    text = skill_md.read_text(encoding="utf-8")
                    for line in text.splitlines():
                        if line.startswith("description:"):
                            desc = line.split("description:", 1)[1].strip()
                            break
                except Exception:
                    desc = "(读取失败)"
            skills_in_cat.append({
                "name": sk.name,
                "category": cat.name,
                "path": str(sk.relative_to(SKILL_ROOT)).replace("\\", "/"),
                "description": desc,
            })
        if skills_in_cat:
            inventory[cat.name] = skills_in_cat
    return inventory


def check_remote_head() -> str | None:
    """获取 GitHub 远程 HEAD commit hash"""
    try:
        r = subprocess.run(
            ["git", "ls-remote", REPO_URL, "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        output = r.stdout.strip()
        if output:
            return output.split()[0]
    except Exception as e:
        print(f"[警告] 无法连接到 GitHub 探测远程版本: {e}", file=sys.stderr)
    return None


def get_current_version() -> dict:
    """获取当前记录的版本信息"""
    if VERSION_FILE.exists():
        try:
            return json.loads(VERSION_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"commit": None, "updated_at": None}


def update_skills(force: bool = False) -> bool:
    """从上游拉取最新技能并覆盖本地 skills 目录"""
    temp_clone = Path(os.environ.get("TEMP", "/tmp")) / "mattpocock-skills-clone"
    print(f">>> 正在同步上游仓库: {REPO_URL} ...")

    if temp_clone.exists():
        try:
            shutil.rmtree(temp_clone)
        except Exception:
            pass

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", REPO_URL, str(temp_clone)],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception as e:
        print(f"[错误] git clone 失败: {e}", file=sys.stderr)
        return False

    src_skills = temp_clone / "skills"
    if not src_skills.exists():
        print("[错误] 克隆的仓库中未找到 skills 目录", file=sys.stderr)
        return False

    # 覆盖同步到本地 skills
    if LOCAL_SKILLS_DIR.exists():
        shutil.rmtree(LOCAL_SKILLS_DIR)
    shutil.copytree(src_skills, LOCAL_SKILLS_DIR)

    # 记录最新 commit
    head_commit = None
    try:
        r = subprocess.run(
            ["git", "-C", str(temp_clone), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        head_commit = r.stdout.strip()
    except Exception:
        pass

    import datetime
    version_info = {
        "commit": head_commit,
        "updated_at": datetime.datetime.now().isoformat(),
        "total_skills": sum(len(v) for v in list_local_skills().values()),
    }
    VERSION_FILE.write_text(json.dumps(version_info, ensure_ascii=False, indent=2), encoding="utf-8")

    # 清理临时克隆目录
    try:
        shutil.rmtree(temp_clone)
    except Exception:
        pass

    print(f">>> 同步成功！当前 Commit: {head_commit}，共下载 {version_info['total_skills']} 个官方技能。")
    return True


def configure_console():
    """Windows 控制台输出流编码保障"""
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except AttributeError:
            pass


def main():
    configure_console()
    parser = argparse.ArgumentParser(description="mattpocock/skills 官方技能同步管理工具")
    parser.add_argument("--list", action="store_true", help="列出本地已下载的官方技能")
    parser.add_argument("--check", action="store_true", help="检查远程更新状态")
    parser.add_argument("--update", action="store_true", help="执行全量拉取更新")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")

    args = parser.parse_args()

    if args.json:
        data = {
            "version": get_current_version(),
            "skills": list_local_skills(),
        }
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if args.check:
        cur = get_current_version()
        print(f"本地记录版本: {cur.get('commit') or '未知'} (上次更新: {cur.get('updated_at') or '无'})")
        print("正在探测远程 HEAD ...")
        remote_head = check_remote_head()
        if remote_head:
            print(f"远程最新版本: {remote_head}")
            if remote_head == cur.get("commit"):
                print("✅ 当前已是最新版本！")
            else:
                print("⚡ 检测到新版本，可执行 python sync_mattpocock_repo.py --update 进行更新。")
        return

    if args.update:
        success = update_skills()
        sys.exit(0 if success else 1)

    # 默认或 --list
    inventory = list_local_skills()
    total = sum(len(v) for v in inventory.values())
    cur = get_current_version()
    print(f"=== Matt Pocock 官方已下载技能清单 (共 {total} 个) ===")
    print(f"上游 Commit: {cur.get('commit', '本地初始化')} | 更新时间: {cur.get('updated_at', '未记录')}\n")
    for cat, skills in inventory.items():
        print(f"【{cat}】({len(skills)} 个):")
        for sk in skills:
            desc = sk['description']
            if len(desc) > 55:
                desc = desc[:52] + "..."
            print(f"  - {sk['name']:<30} {desc}")
        print()


if __name__ == "__main__":
    main()
