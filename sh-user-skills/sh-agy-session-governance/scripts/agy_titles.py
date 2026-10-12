# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""agy_titles: Google Antigravity CLI (agy) 会话标题批量治理与中文化工具。

支持查看、导出待治理英文会话列表，提供安全事务双写（SQLite 与 annotations 描述文件）
以及自动快照备份与还原，供人类用户与 AI Agent 协同批量翻译与治理会话标题。
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ----------------------------------------------------------------------
# 模块常量与配置
# ----------------------------------------------------------------------
VERSION = "1.0.0"
CHINESE_PATTERN = re.compile(r"[\u4e00-\u9fa5]")

DEFAULT_CLI_DIR = Path.home() / ".gemini" / "antigravity-cli"
DEFAULT_DB_PATH = DEFAULT_CLI_DIR / "conversation_summaries.db"
DEFAULT_ANNOTATIONS_DIR = DEFAULT_CLI_DIR / "annotations"
DEFAULT_BACKUP_ROOT = DEFAULT_CLI_DIR / "backups" / "titles"


# ----------------------------------------------------------------------
# 辅助函数与基础设施
# ----------------------------------------------------------------------
def init_console_encoding() -> None:
    """保障 Windows 控制台输出 UTF-8 编码安全。"""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def get_db_connection(db_path: Path) -> sqlite3.Connection:
    """获取 SQLite 连接，配置超时与行字典模式。"""
    if not db_path.is_file():
        raise FileNotFoundError(f"未找到 agy 会话数据库: {db_path}")
    conn = sqlite3.connect(str(db_path), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000;")
    return conn


def create_backup(db_path: Path, annotations_dir: Path, target_ids: Optional[List[str]] = None) -> Path:
    """创建时间戳快照备份（含 sqlite db 及相关 annotations 文件）。"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
    backup_dir = DEFAULT_BACKUP_ROOT / f"backup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # 1. 备份数据库
    if db_path.is_file():
        shutil.copy2(db_path, backup_dir / db_path.name)

    # 2. 备份 annotations
    anno_backup_dir = backup_dir / "annotations"
    anno_backup_dir.mkdir(exist_ok=True)

    if annotations_dir.is_dir():
        if target_ids is None:
            # 全量备份 annotations
            for pbtxt in annotations_dir.glob("*.pbtxt"):
                shutil.copy2(pbtxt, anno_backup_dir / pbtxt.name)
        else:
            for conv_id in target_ids:
                pbtxt = annotations_dir / f"{conv_id}.pbtxt"
                if pbtxt.is_file():
                    shutil.copy2(pbtxt, anno_backup_dir / pbtxt.name)

    # 3. 记录元数据
    meta = {
        "timestamp": timestamp,
        "db_source": str(db_path),
        "annotations_source": str(annotations_dir),
        "target_ids": target_ids or "all",
    }
    (backup_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return backup_dir


def update_annotation_file(annotations_dir: Path, conv_id: str, new_title: str) -> None:
    """安全更新或创建 annotations/<id>.pbtxt 文件。"""
    annotations_dir.mkdir(parents=True, exist_ok=True)
    pbtxt_path = annotations_dir / f"{conv_id}.pbtxt"

    # 转义标题字符串
    escaped_title = new_title.replace("\\", "\\\\").replace('"', '\\"')

    if pbtxt_path.is_file():
        content = pbtxt_path.read_text(encoding="utf-8", errors="replace")
        if re.search(r'title\s*:\s*".*?"', content):
            new_content = re.sub(r'title\s*:\s*".*?"', f'title:"{escaped_title}"', content, count=1)
        else:
            new_content = f'title:"{escaped_title}"\n' + content
    else:
        new_content = f'title:"{escaped_title}"\n'

    pbtxt_path.write_text(new_content, encoding="utf-8")


def is_chinese_title(title: str) -> bool:
    """检测标题中是否已包含中文字符。"""
    return bool(CHINESE_PATTERN.search(title))


# ----------------------------------------------------------------------
# 命令处理函数
# ----------------------------------------------------------------------
def cmd_list(args: argparse.Namespace) -> int:
    """列出会话信息，支持语言过滤及 JSON 格式输出。"""
    db_path = Path(args.db) if args.db else DEFAULT_DB_PATH
    conn = get_db_connection(db_path)

    query = (
        "SELECT conversation_id, title, preview, last_modified_time, workspace_uris, step_count "
        "FROM conversation_summaries "
        "ORDER BY last_modified_time DESC"
    )

    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    results: List[Dict[str, Any]] = []
    for r in rows:
        cid = r["conversation_id"]
        title = r["title"] or ""
        preview = (r["preview"] or "").replace("\r", " ").replace("\n", " ").strip()
        mod_time = str(r["last_modified_time"] or "")
        workspaces = r["workspace_uris"] or ""
        step_count = r["step_count"] or 0

        has_cn = is_chinese_title(title)
        if args.english_only and has_cn:
            continue
        if args.chinese_only and not has_cn:
            continue

        results.append({
            "id": cid,
            "title": title,
            "preview": preview[:60] + "..." if len(preview) > 60 else preview,
            "last_modified": mod_time,
            "workspaces": workspaces,
            "step_count": step_count,
            "is_chinese": has_cn,
        })

    if not args.all and args.limit and args.limit > 0:
        results = results[: args.limit]

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    if not results:
        print("未匹配到任何符合条件的会话。")
        return 0

    print(f"\n共找到 {len(results)} 条会话记录：")
    print(f"{'ID (前8位)':<10} | {'标题':<35} | {'步数':<5} | {'修改时间':<22} | {'预览'}")
    print("-" * 105)
    for item in results:
        cid_short = item["id"][:8]
        t = item["title"][:33]
        steps = str(item["step_count"])
        mtime = item["last_modified"][:19]
        prev = item["preview"][:30]
        print(f"{cid_short:<10} | {t:<35} | {steps:<5} | {mtime:<22} | {prev}")
    print()
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    """查询单条会话详情。"""
    db_path = Path(args.db) if args.db else DEFAULT_DB_PATH
    conn = get_db_connection(db_path)

    cursor = conn.cursor()
    cursor.execute(
        "SELECT conversation_id, title, preview, last_modified_time, workspace_uris, step_count, status "
        "FROM conversation_summaries WHERE conversation_id LIKE ?",
        (f"{args.id}%",),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print(f"未找到 ID 匹配 '{args.id}' 的会话。")
        return 1

    r = rows[0]
    cid = r["conversation_id"]
    pbtxt_path = (Path(args.annotations_dir) if args.annotations_dir else DEFAULT_ANNOTATIONS_DIR) / f"{cid}.pbtxt"
    pbtxt_content = pbtxt_path.read_text(encoding="utf-8", errors="replace").strip() if pbtxt_path.is_file() else "（不存在）"

    detail = {
        "id": cid,
        "title": r["title"],
        "preview": r["preview"],
        "step_count": r["step_count"],
        "status": r["status"],
        "last_modified": str(r["last_modified_time"]),
        "workspace_uris": r["workspace_uris"],
        "annotation_pbtxt": pbtxt_content,
    }

    if args.json:
        print(json.dumps(detail, ensure_ascii=False, indent=2))
    else:
        print("\n会话详细信息：")
        print(f"  ID:           {detail['id']}")
        print(f"  当前标题:     {detail['title']}")
        print(f"  执行步数:     {detail['step_count']}")
        print(f"  状态:         {detail['status']}")
        print(f"  最后修改:     {detail['last_modified']}")
        print(f"  工作区:       {detail['workspace_uris']}")
        print(f"  提示词预览:   {detail['preview']}")
        print(f"  .pbtxt 内容:  {detail['annotation_pbtxt']}\n")
    return 0


def cmd_rename(args: argparse.Namespace) -> int:
    """重命名单个会话。"""
    db_path = Path(args.db) if args.db else DEFAULT_DB_PATH
    anno_dir = Path(args.annotations_dir) if args.annotations_dir else DEFAULT_ANNOTATIONS_DIR

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT conversation_id, title FROM conversation_summaries WHERE conversation_id LIKE ?",
        (f"{args.id}%",),
    )
    rows = cursor.fetchall()

    if not rows:
        conn.close()
        print(f"错误: 未找到匹配 ID '{args.id}' 的会话。")
        return 1

    cid = rows[0]["conversation_id"]
    old_title = rows[0]["title"] or ""
    new_title = args.new_title.strip()

    if not new_title:
        conn.close()
        print("错误: 新标题不能为空。")
        return 1

    print(f"\n[会话重命名]")
    print(f"  会话 ID:  {cid}")
    print(f"  原标题:   {old_title}")
    print(f"  新标题:   {new_title}")

    if args.dry_run:
        conn.close()
        print("  -> 模式: [Dry-Run] 预览模式，未做任何实际写入。\n")
        return 0

    # 1. 自动备份
    backup_path = create_backup(db_path, anno_dir, [cid])
    print(f"  -> 已创建前置快照: {backup_path}")

    # 2. 事务更新 SQLite
    try:
        cursor.execute(
            "UPDATE conversation_summaries SET title = ? WHERE conversation_id = ?",
            (new_title, cid),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"错误: SQLite 更新失败: {e}")
        return 1
    finally:
        conn.close()

    # 3. 更新 annotations/<id>.pbtxt
    try:
        update_annotation_file(anno_dir, cid, new_title)
    except Exception as e:
        print(f"警告: 更新 .pbtxt 文件失败: {e}")

    print("  -> [成功] 会话标题已更新！可在 agy 中按 /resume 查看效果。\n")
    return 0


def cmd_batch_rename(args: argparse.Namespace) -> int:
    """批量重命名多个会话。"""
    db_path = Path(args.db) if args.db else DEFAULT_DB_PATH
    anno_dir = Path(args.annotations_dir) if args.annotations_dir else DEFAULT_ANNOTATIONS_DIR

    # 1. 解析输入的 JSON 数据
    raw_payload: str = ""
    if args.file:
        file_path = Path(args.file)
        if not file_path.is_file():
            print(f"错误: 找不到指定的 JSON 文件: {file_path}")
            return 1
        raw_payload = file_path.read_text(encoding="utf-8")
    elif args.payload == "-":
        raw_payload = sys.stdin.read()
    elif args.payload:
        raw_payload = args.payload
    else:
        print("错误: 请提供 JSON 重命名数据（通过参数、--file 或标准输入管道）。")
        return 1

    try:
        data = json.loads(raw_payload)
    except Exception as e:
        print(f"错误: JSON 解析失败: {e}")
        return 1

    # 归一化为 List[Tuple[id, new_title]]
    rename_pairs: List[Tuple[str, str]] = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "id" in item and "title" in item:
                rename_pairs.append((str(item["id"]).strip(), str(item["title"]).strip()))
    elif isinstance(data, dict):
        for k, v in data.items():
            rename_pairs.append((str(k).strip(), str(v).strip()))
    else:
        print("错误: JSON 格式不受支持。支持 [{'id': '...', 'title': '...'}, ...] 或 {'id': 'title', ...}。")
        return 1

    if not rename_pairs:
        print("未发现任何待处理的重命名条目。")
        return 0

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 2. 校验与查找原标题
    validated_tasks: List[Tuple[str, str, str]] = []  # (full_id, old_title, new_title)
    for cid_input, new_title in rename_pairs:
        if not new_title:
            continue
        cursor.execute(
            "SELECT conversation_id, title FROM conversation_summaries WHERE conversation_id LIKE ?",
            (f"{cid_input}%",),
        )
        found = cursor.fetchall()
        if not found:
            print(f"跳过: 未找到 ID '{cid_input}' 对应的会话。")
            continue
        full_id = found[0]["conversation_id"]
        old_title = found[0]["title"] or ""
        validated_tasks.append((full_id, old_title, new_title))

    if not validated_tasks:
        conn.close()
        print("没有可执行的有效重命名条目。")
        return 0

    print(f"\n[批量会话重命名任务] 共 {len(validated_tasks)} 项：")
    print(f"{'ID (前8位)':<10} | {'原标题':<35} -> {'新标题'}")
    print("-" * 80)
    for cid, old_t, new_t in validated_tasks:
        print(f"{cid[:8]:<10} | {old_t[:33]:<35} -> {new_t}")
    print()

    if args.dry_run:
        conn.close()
        print("-> 模式: [Dry-Run] 预览模式，未做任何实际写入。\n")
        return 0

    # 3. 自动备份
    target_ids = [cid for cid, _, _ in validated_tasks]
    backup_path = create_backup(db_path, anno_dir, target_ids)
    print(f"-> 已创建前置快照: {backup_path}")

    # 4. 事务批量更新
    updated_count = 0
    try:
        for cid, _, new_t in validated_tasks:
            cursor.execute(
                "UPDATE conversation_summaries SET title = ? WHERE conversation_id = ?",
                (new_t, cid),
            )
            update_annotation_file(anno_dir, cid, new_t)
            updated_count += 1
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"错误: 批量写入失败，已触发事务回滚: {e}")
        return 1
    finally:
        conn.close()

    print(f"-> [成功] 成功完成 {updated_count} 条会话的重命名！可在 agy 中按 /resume 查验。\n")
    return 0


def cmd_backup(args: argparse.Namespace) -> int:
    """手动创建数据库与注解完整快照。"""
    db_path = Path(args.db) if args.db else DEFAULT_DB_PATH
    anno_dir = Path(args.annotations_dir) if args.annotations_dir else DEFAULT_ANNOTATIONS_DIR

    backup_path = create_backup(db_path, anno_dir)
    print(f"\n[快照备份成功]")
    print(f"  保存路径: {backup_path}\n")
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    """列出快照或从指定快照恢复。"""
    if args.list:
        if not DEFAULT_BACKUP_ROOT.is_dir():
            print("目前没有任何快照备份。")
            return 0
        backups = sorted(DEFAULT_BACKUP_ROOT.glob("backup_*"), reverse=True)
        if not backups:
            print("目前没有任何快照备份。")
            return 0
        print("\n可用快照列表：")
        for b in backups:
            meta_file = b / "meta.json"
            meta_str = ""
            if meta_file.is_file():
                try:
                    m = json.loads(meta_file.read_text(encoding="utf-8"))
                    meta_str = f" (目标: {len(m.get('target_ids', [])) if isinstance(m.get('target_ids'), list) else '全量'})"
                except Exception:
                    pass
            print(f"  - {b.name}{meta_str} -> {b}")
        print()
        return 0

    if not args.snapshot:
        print("错误: 请指定要恢复的快照目录路径或快照名称，或使用 --list 查看可用快照。")
        return 1

    snap_path = Path(args.snapshot)
    if not snap_path.is_dir() and (DEFAULT_BACKUP_ROOT / args.snapshot).is_dir():
        snap_path = DEFAULT_BACKUP_ROOT / args.snapshot

    if not snap_path.is_dir():
        print(f"错误: 快照路径不存在: {snap_path}")
        return 1

    db_path = Path(args.db) if args.db else DEFAULT_DB_PATH
    anno_dir = Path(args.annotations_dir) if args.annotations_dir else DEFAULT_ANNOTATIONS_DIR

    backup_db = snap_path / db_path.name
    if backup_db.is_file():
        shutil.copy2(backup_db, db_path)
        print(f"已恢复数据库: {db_path}")

    backup_annos = snap_path / "annotations"
    if backup_annos.is_dir():
        for pbtxt in backup_annos.glob("*.pbtxt"):
            shutil.copy2(pbtxt, anno_dir / pbtxt.name)
        print(f"已恢复 annotations 目录下的注解文件。")

    print("\n[还原成功] 已从快照恢复完成。\n")
    return 0


# ----------------------------------------------------------------------
# CLI 入口与解析
# ----------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="agy_titles",
        description="Google Antigravity CLI (agy) 会话标题批量治理与中文化工具",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument("--db", type=str, help=f"自定义 SQLite 数据库路径 (默认: {DEFAULT_DB_PATH})")
    parser.add_argument("--annotations-dir", type=str, help=f"自定义 annotations 目录路径 (默认: {DEFAULT_ANNOTATIONS_DIR})")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 1. list
    p_list = subparsers.add_parser("list", help="列出会话并支持中英文筛选")
    p_list.add_argument("--limit", type=int, default=50, help="限制输出条数 (默认 50)")
    p_list.add_argument("--all", action="store_true", help="显示全部记录")
    p_list.add_argument("--english-only", action="store_true", help="仅显示英文标题的会话（待治理项）")
    p_list.add_argument("--chinese-only", action="store_true", help="仅显示已有中文标题的会话")
    p_list.add_argument("--json", action="store_true", help="以 JSON 格式输出，便于 AI Agent 解析")

    # 2. get
    p_get = subparsers.add_parser("get", help="查看单个会话详细信息")
    p_get.add_argument("id", type=str, help="会话 ID (支持前缀匹配)")
    p_get.add_argument("--json", action="store_true", help="以 JSON 格式输出")

    # 3. rename
    p_rename = subparsers.add_parser("rename", help="重命名单个会话")
    p_rename.add_argument("id", type=str, help="会话 ID (支持前缀匹配)")
    p_rename.add_argument("new_title", type=str, help="新标题")
    p_rename.add_argument("--dry-run", action="store_true", help="预览变更，不实际修改")

    # 4. batch-rename
    p_batch = subparsers.add_parser("batch-rename", help="批量重命名多个会话")
    p_batch.add_argument("payload", nargs="?", type=str, help="JSON 字符串或 '-' (从标准输入读取)")
    p_batch.add_argument("--file", type=str, help="包含重命名映射的 JSON 文件路径")
    p_batch.add_argument("--dry-run", action="store_true", help="预览变更，不实际修改")

    # 5. backup
    subparsers.add_parser("backup", help="创建数据库与注解快照备份")

    # 6. restore
    p_restore = subparsers.add_parser("restore", help="从快照恢复数据")
    p_restore.add_argument("snapshot", nargs="?", type=str, help="快照目录路径或快照名称")
    p_restore.add_argument("--list", action="store_true", help="列出可用快照")

    return parser


def main() -> int:
    """主程序入口。"""
    init_console_encoding()
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "list":
        return cmd_list(args)
    elif args.command == "get":
        return cmd_get(args)
    elif args.command == "rename":
        return cmd_rename(args)
    elif args.command == "batch-rename":
        return cmd_batch_rename(args)
    elif args.command == "backup":
        return cmd_backup(args)
    elif args.command == "restore":
        return cmd_restore(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
