# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""agy_titles: Google Antigravity (App & CLI) 会话标题批量治理与中文化工具。

支持 Antigravity Desktop App (~/.gemini/antigravity) 与 agy CLI (~/.gemini/antigravity-cli)，
提供 SQLite 字段与 Protobuf raw_summary / agyhub_summaries_proto.pb / annotations 三重原子同步更新，
以及自动快照备份与还原。
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ----------------------------------------------------------------------
# 模块常量与配置
# ----------------------------------------------------------------------
VERSION = "1.1.0"
CHINESE_PATTERN = re.compile(r"[\u4e00-\u9fa5]")

KNOWN_ENVIRONMENTS: Dict[str, Path] = {
    "app": Path.home() / ".gemini" / "antigravity",
    "cli": Path.home() / ".gemini" / "antigravity-cli",
    "ide": Path.home() / ".gemini" / "antigravity-ide",
}


# ----------------------------------------------------------------------
# Protobuf 底层编解码（零外部依赖，纯标准库字节流处理）
# ----------------------------------------------------------------------
def parse_proto_fields(data: bytes) -> List[Tuple[int, int, Any]]:
    """解析 Protobuf 字节流为 (field_num, wire_type, value) 列表。"""
    idx = 0
    fields: List[Tuple[int, int, Any]] = []
    while idx < len(data):
        key = 0
        shift = 0
        while idx < len(data):
            b = data[idx]
            idx += 1
            key |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
        if key == 0:
            break
        field_num = key >> 3
        wire_type = key & 0x7
        if wire_type == 0:
            val = 0
            shift = 0
            while idx < len(data):
                b = data[idx]
                idx += 1
                val |= (b & 0x7F) << shift
                if not (b & 0x80):
                    break
                shift += 7
            fields.append((field_num, wire_type, val))
        elif wire_type == 1:
            val = data[idx:idx + 8]
            idx += 8
            fields.append((field_num, wire_type, val))
        elif wire_type == 2:
            length = 0
            shift = 0
            while idx < len(data):
                b = data[idx]
                idx += 1
                length |= (b & 0x7F) << shift
                if not (b & 0x80):
                    break
                shift += 7
            val = data[idx:idx + length]
            idx += length
            fields.append((field_num, wire_type, val))
        elif wire_type == 5:
            val = data[idx:idx + 4]
            idx += 4
            fields.append((field_num, wire_type, val))
        else:
            break
    return fields


def encode_varint(val: int) -> bytes:
    """编码无符号 Varint。"""
    res = bytearray()
    while val >= 0x80:
        res.append((val & 0x7F) | 0x80)
        val >>= 7
    res.append(val & 0x7F)
    return bytes(res)


def encode_fields(fields: List[Tuple[int, int, Any]]) -> bytes:
    """将 (field_num, wire_type, value) 列表重构为 Protobuf 二进制字节。"""
    res = bytearray()
    for field_num, wire_type, val in fields:
        key = (field_num << 3) | wire_type
        res.extend(encode_varint(key))
        if wire_type == 0:
            res.extend(encode_varint(val))
        elif wire_type == 1:
            res.extend(val)
        elif wire_type == 2:
            res.extend(encode_varint(len(val)))
            res.extend(val)
        elif wire_type == 5:
            res.extend(val)
    return bytes(res)


def update_summary_title(raw_bytes: bytes, new_title: str) -> bytes:
    """更新 CascadeTrajectorySummary 二进制中的 Field 1 (title) 与 Field 15 (annotations.title)。"""
    try:
        fields = parse_proto_fields(raw_bytes)
        new_fields: List[Tuple[int, int, Any]] = []
        title_bytes = new_title.encode("utf-8")
        has_f1 = False
        for fn, wt, val in fields:
            if fn == 1:
                new_fields.append((fn, wt, title_bytes))
                has_f1 = True
            elif fn == 15 and wt == 2:
                # Field 15: annotations sub-message
                try:
                    sub_fields = parse_proto_fields(val)
                    new_sub: List[Tuple[int, int, Any]] = []
                    has_sub1 = False
                    for sfn, swt, sval in sub_fields:
                        if sfn == 1:
                            new_sub.append((sfn, swt, title_bytes))
                            has_sub1 = True
                        else:
                            new_sub.append((sfn, swt, sval))
                    if not has_sub1:
                        new_sub.insert(0, (1, 2, title_bytes))
                    new_fields.append((fn, wt, encode_fields(new_sub)))
                except Exception:
                    new_fields.append((fn, wt, val))
            else:
                new_fields.append((fn, wt, val))
        if not has_f1:
            new_fields.insert(0, (1, 2, title_bytes))
        return encode_fields(new_fields)
    except Exception:
        return raw_bytes


def update_pb_store(pb_path: Path, rename_map: Dict[str, str]) -> int:
    """安全更新 agyhub_summaries_proto.pb 文件中的指定会话标题。"""
    if not pb_path.is_file():
        return 0
    try:
        data = pb_path.read_bytes()
        root = parse_proto_fields(data)
        updated_count = 0
        new_root: List[Tuple[int, int, Any]] = []
        for fn, wt, val in root:
            if fn == 1 and wt == 2:
                map_entry = parse_proto_fields(val)
                cid = None
                for sfn, swt, sval in map_entry:
                    if sfn == 1 and swt == 2:
                        try:
                            cid = sval.decode("utf-8")
                        except Exception:
                            pass
                if cid and cid in rename_map:
                    new_title = rename_map[cid]
                    new_map_entry: List[Tuple[int, int, Any]] = []
                    for sfn, swt, sval in map_entry:
                        if sfn == 2 and swt == 2:
                            new_map_entry.append((sfn, swt, update_summary_title(sval, new_title)))
                        else:
                            new_map_entry.append((sfn, swt, sval))
                    new_root.append((fn, wt, encode_fields(new_map_entry)))
                    updated_count += 1
                else:
                    new_root.append((fn, wt, val))
            else:
                new_root.append((fn, wt, val))

        if updated_count > 0:
            pb_path.write_bytes(encode_fields(new_root))
        return updated_count
    except Exception as e:
        print(f"  [警告] 更新 {pb_path.name} 异常: {e}")
        return 0


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


def get_active_environments(target_name: str = "all") -> List[Tuple[str, Path]]:
    """获取存在有效 conversation_summaries.db 的目标环境列表。"""
    target_name = (target_name or "all").lower()
    envs: List[Tuple[str, Path]] = []
    if target_name in KNOWN_ENVIRONMENTS:
        p = KNOWN_ENVIRONMENTS[target_name]
        if p.is_dir() and (p / "conversation_summaries.db").is_file():
            envs.append((target_name, p))
    else:
        for name, p in KNOWN_ENVIRONMENTS.items():
            if p.is_dir() and (p / "conversation_summaries.db").is_file():
                envs.append((name, p))
    return envs


def get_db_connection(db_path: Path) -> sqlite3.Connection:
    """获取 SQLite 连接，配置超时与行字典模式。"""
    if not db_path.is_file():
        raise FileNotFoundError(f"未找到会话数据库: {db_path}")
    conn = sqlite3.connect(str(db_path), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000;")
    return conn


def db_has_raw_summary(conn: sqlite3.Connection) -> bool:
    """检查 conversation_summaries 表是否具备 raw_summary 字段。"""
    try:
        cols = [c["name"] for c in conn.execute("PRAGMA table_info(conversation_summaries)").fetchall()]
        return "raw_summary" in cols
    except Exception:
        return False


def create_backup(env_dir: Path, target_ids: Optional[List[str]] = None) -> Path:
    """创建时间戳快照备份（含 SQLite db、.pb 文件及 annotations 注释）。"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
    backup_root = env_dir / "backups" / "titles"
    backup_dir = backup_root / f"backup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    db_path = env_dir / "conversation_summaries.db"
    pb_path = env_dir / "agyhub_summaries_proto.pb"
    anno_dir = env_dir / "annotations"

    if db_path.is_file():
        shutil.copy2(db_path, backup_dir / db_path.name)
    if pb_path.is_file():
        shutil.copy2(pb_path, backup_dir / pb_path.name)

    anno_backup_dir = backup_dir / "annotations"
    anno_backup_dir.mkdir(exist_ok=True)
    if anno_dir.is_dir():
        if target_ids is None:
            for pbtxt in anno_dir.glob("*.pbtxt"):
                shutil.copy2(pbtxt, anno_backup_dir / pbtxt.name)
        else:
            for cid in target_ids:
                pbtxt = anno_dir / f"{cid}.pbtxt"
                if pbtxt.is_file():
                    shutil.copy2(pbtxt, anno_backup_dir / pbtxt.name)

    meta = {
        "timestamp": timestamp,
        "env_dir": str(env_dir),
        "db_source": str(db_path),
        "target_ids": target_ids or "all",
    }
    (backup_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return backup_dir


def update_annotation_file(annotations_dir: Path, conv_id: str, new_title: str) -> None:
    """安全更新或创建 annotations/<id>.pbtxt 文件。"""
    annotations_dir.mkdir(parents=True, exist_ok=True)
    pbtxt_path = annotations_dir / f"{conv_id}.pbtxt"
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


def try_call_app_rpc(tasks: List[Tuple[str, str, str]]) -> Dict[str, bool]:
    """尝试通过 Antigravity 正在运行的 language_server.exe 官方 RPC 实时推送改名并更新内存与 UI。"""
    results: Dict[str, bool] = {}
    try:
        cmd = 'powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name=\'language_server.exe\'\" | Select-Object ProcessId, CommandLine | ConvertTo-Json"'
        res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if not res.stdout.strip():
            return results
        proc_info = json.loads(res.stdout)
        if isinstance(proc_info, list):
            proc_info = proc_info[0]
        pid = proc_info.get("ProcessId")
        cmdline = proc_info.get("CommandLine", "")
        token_m = re.search(r'--csrf_token\s+([a-zA-Z0-9\-]+)', cmdline)
        if not pid or not token_m:
            return results
        csrf_token = token_m.group(1)

        cmd2 = f'powershell -NoProfile -Command "Get-NetTCPConnection -OwningProcess {pid} -State Listen | Select-Object -ExpandProperty LocalPort"'
        res2 = subprocess.run(cmd2, capture_output=True, text=True, shell=True)
        ports = [int(p.strip()) for p in res2.stdout.split() if p.strip().isdigit()]

        http_port = None
        for p in ports:
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{p}/", headers={"User-Agent": "antigravity"})
                with urllib.request.urlopen(req, timeout=0.8) as resp:
                    if resp.status == 200:
                        http_port = p
                        break
            except Exception:
                pass

        if not http_port:
            return results

        rpc_url = f"http://127.0.0.1:{http_port}/exa.language_server_pb.LanguageServerService/UpdateConversationAnnotations"
        for cid, _, new_title in tasks:
            payload = json.dumps({
                "cascadeIds": [cid],
                "annotations": {"title": new_title},
                "mergeAnnotations": True
            }).encode("utf-8")
            req = urllib.request.Request(
                rpc_url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-codeium-csrf-token": csrf_token,
                    "User-Agent": "antigravity"
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=3) as resp:
                    results[cid] = (resp.status == 200)
            except Exception:
                results[cid] = False
    except Exception:
        pass
    return results


def is_chinese_title(title: str) -> bool:
    """检测标题中是否已包含中文字符。"""
    return bool(CHINESE_PATTERN.search(title))


# ----------------------------------------------------------------------
# 命令处理函数
# ----------------------------------------------------------------------
def cmd_list(args: argparse.Namespace) -> int:
    """列出会话信息，支持环境、语言过滤及 JSON 格式输出。"""
    envs = get_active_environments(args.target)
    if not envs:
        print(f"未找到可用的会话环境 (目标: {args.target})。")
        return 1

    all_results: List[Dict[str, Any]] = []
    seen_ids = set()

    for env_name, env_dir in envs:
        db_path = env_dir / "conversation_summaries.db"
        try:
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
        except Exception as e:
            print(f"读取 [{env_name}] 会话数据库异常: {e}")
            continue

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

            dedup_key = f"{cid}_{env_name}"
            if dedup_key in seen_ids:
                continue
            seen_ids.add(dedup_key)

            all_results.append({
                "id": cid,
                "env": env_name,
                "title": title,
                "preview": preview[:60] + "..." if len(preview) > 60 else preview,
                "last_modified": mod_time,
                "workspaces": workspaces,
                "step_count": step_count,
                "is_chinese": has_cn,
            })

    # 按修改时间逆序排序
    all_results.sort(key=lambda x: x["last_modified"], reverse=True)

    if not args.all and args.limit and args.limit > 0:
        all_results = all_results[: args.limit]

    if args.json:
        print(json.dumps(all_results, ensure_ascii=False, indent=2))
        return 0

    if not all_results:
        print("未匹配到任何符合条件的会话。")
        return 0

    print(f"\n共找到 {len(all_results)} 条会话记录：")
    print(f"{'ID (前8位)':<10} | {'环境':<6} | {'标题':<35} | {'步数':<5} | {'修改时间':<22} | {'预览'}")
    print("-" * 115)
    for item in all_results:
        cid_short = item["id"][:8]
        env_tag = item["env"]
        t = item["title"][:33]
        steps = str(item["step_count"])
        mtime = item["last_modified"][:19]
        prev = item["preview"][:30]
        print(f"{cid_short:<10} | {env_tag:<6} | {t:<35} | {steps:<5} | {mtime:<22} | {prev}")
    print()
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    """查询单条会话详情。"""
    envs = get_active_environments(args.target)
    for env_name, env_dir in envs:
        db_path = env_dir / "conversation_summaries.db"
        try:
            conn = get_db_connection(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT conversation_id, title, preview, last_modified_time, workspace_uris, step_count, status "
                "FROM conversation_summaries WHERE conversation_id LIKE ?",
                (f"{args.id}%",),
            )
            rows = cursor.fetchall()
            conn.close()
            if rows:
                r = rows[0]
                cid = r["conversation_id"]
                pbtxt_path = env_dir / "annotations" / f"{cid}.pbtxt"
                pbtxt_content = pbtxt_path.read_text(encoding="utf-8", errors="replace").strip() if pbtxt_path.is_file() else "（不存在）"

                detail = {
                    "id": cid,
                    "env": env_name,
                    "env_path": str(env_dir),
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
                    print(f"\n会话详细信息 [{env_name}]：")
                    print(f"  ID:           {detail['id']}")
                    print(f"  所属环境:     {detail['env']} ({detail['env_path']})")
                    print(f"  当前标题:     {detail['title']}")
                    print(f"  执行步数:     {detail['step_count']}")
                    print(f"  状态:         {detail['status']}")
                    print(f"  最后修改:     {detail['last_modified']}")
                    print(f"  工作区:       {detail['workspace_uris']}")
                    print(f"  提示词预览:   {detail['preview']}")
                    print(f"  .pbtxt 内容:  {detail['annotation_pbtxt']}\n")
                return 0
        except Exception:
            continue

    print(f"未找到 ID 匹配 '{args.id}' 的会话。")
    return 1


def cmd_rename(args: argparse.Namespace) -> int:
    """重命名单个会话（支持 App 与 CLI）。"""
    new_title = args.new_title.strip()
    if not new_title:
        print("错误: 新标题不能为空。")
        return 1

    envs = get_active_environments(args.target)
    matched_envs: List[Tuple[str, Path, str, str]] = []  # (env_name, env_dir, full_id, old_title)

    for env_name, env_dir in envs:
        db_path = env_dir / "conversation_summaries.db"
        try:
            conn = get_db_connection(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT conversation_id, title FROM conversation_summaries WHERE conversation_id LIKE ?",
                (f"{args.id}%",),
            )
            rows = cursor.fetchall()
            conn.close()
            if rows:
                matched_envs.append((env_name, env_dir, rows[0]["conversation_id"], rows[0]["title"] or ""))
        except Exception:
            continue

    if not matched_envs:
        print(f"错误: 未找到匹配 ID '{args.id}' 的会话。")
        return 1

    print(f"\n[会话重命名任务]")
    for env_name, env_dir, cid, old_title in matched_envs:
        print(f"  环境:   [{env_name}] ({env_dir})")
        print(f"  会话:   {cid}")
        print(f"  原标题: {old_title}")
        print(f"  新标题: {new_title}")

    if args.dry_run:
        print("  -> 模式: [Dry-Run] 预览模式，未做任何实际写入。\n")
        return 0

    success_count = 0
    for env_name, env_dir, cid, old_title in matched_envs:
        db_path = env_dir / "conversation_summaries.db"
        pb_path = env_dir / "agyhub_summaries_proto.pb"
        anno_dir = env_dir / "annotations"

        # 0. 尝试通过 Live RPC 实时推送给正在运行的 Antigravity App
        if env_name == "app":
            rpc_res = try_call_app_rpc([(cid, old_title, new_title)])
            if rpc_res.get(cid):
                print(f"  -> [{env_name}] 实时 RPC 推送成功（语言服务器内存与前端 UI 已同步）")

        # 1. 自动前置备份
        backup_path = create_backup(env_dir, [cid])
        print(f"  -> [{env_name}] 已创建前置快照: {backup_path}")

        # 2. 事务更新 SQLite (title + raw_summary)
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        has_raw = db_has_raw_summary(conn)
        try:
            if has_raw:
                cursor.execute("SELECT raw_summary FROM conversation_summaries WHERE conversation_id = ?", (cid,))
                r = cursor.fetchone()
                if r and r["raw_summary"]:
                    new_raw = update_summary_title(r["raw_summary"], new_title)
                    cursor.execute("UPDATE conversation_summaries SET title = ?, raw_summary = ? WHERE conversation_id = ?", (new_title, new_raw, cid))
                else:
                    cursor.execute("UPDATE conversation_summaries SET title = ? WHERE conversation_id = ?", (new_title, cid))
            else:
                cursor.execute("UPDATE conversation_summaries SET title = ? WHERE conversation_id = ?", (new_title, cid))
            conn.commit()
            success_count += 1
        except Exception as e:
            conn.rollback()
            print(f"  [{env_name}] SQLite 更新失败: {e}")
        finally:
            conn.close()

        # 3. 更新 agyhub_summaries_proto.pb
        if pb_path.is_file():
            update_pb_store(pb_path, {cid: new_title})

        # 4. 更新 annotations
        try:
            update_annotation_file(anno_dir, cid, new_title)
        except Exception as e:
            print(f"  [{env_name}] 警告: 更新 .pbtxt 文件失败: {e}")

    print(f"  -> [成功] 会话标题已在 {success_count} 个环境中成功更新！\n")
    return 0


def cmd_batch_rename(args: argparse.Namespace) -> int:
    """批量重命名多个会话（跨 App 与 CLI 双端原子支持）。"""
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

    envs = get_active_environments(args.target)
    # 按环境组织任务: env_name -> (env_dir, List[(full_id, old_title, new_title)])
    env_tasks: Dict[str, Tuple[Path, List[Tuple[str, str, str]]]] = {}

    for env_name, env_dir in envs:
        db_path = env_dir / "conversation_summaries.db"
        try:
            conn = get_db_connection(db_path)
            cursor = conn.cursor()
            tasks: List[Tuple[str, str, str]] = []
            for cid_input, new_title in rename_pairs:
                if not new_title:
                    continue
                cursor.execute(
                    "SELECT conversation_id, title FROM conversation_summaries WHERE conversation_id LIKE ?",
                    (f"{cid_input}%",),
                )
                found = cursor.fetchall()
                if found:
                    full_id = found[0]["conversation_id"]
                    old_t = found[0]["title"] or ""
                    tasks.append((full_id, old_t, new_title))
            conn.close()
            if tasks:
                env_tasks[env_name] = (env_dir, tasks)
        except Exception:
            continue

    if not env_tasks:
        print("没有可执行的有效重命名条目。")
        return 0

    print(f"\n[批量会话重命名任务] 涉及环境: {list(env_tasks.keys())}")
    for env_name, (env_dir, tasks) in env_tasks.items():
        print(f"\n--- 环境: [{env_name}] ({len(tasks)} 项) ---")
        print(f"{'ID (前8位)':<10} | {'原标题':<35} -> {'新标题'}")
        print("-" * 80)
        for cid, old_t, new_t in tasks:
            print(f"{cid[:8]:<10} | {old_t[:33]:<35} -> {new_t}")

    if args.dry_run:
        print("\n-> 模式: [Dry-Run] 预览模式，未做任何实际写入。\n")
        return 0

    total_updated = 0
    for env_name, (env_dir, tasks) in env_tasks.items():
        db_path = env_dir / "conversation_summaries.db"
        pb_path = env_dir / "agyhub_summaries_proto.pb"
        anno_dir = env_dir / "annotations"

        # 0. 尝试通过 Live RPC 批量实时推送给正在运行的 Antigravity App
        if env_name == "app":
            rpc_res = try_call_app_rpc(tasks)
            rpc_ok = sum(1 for v in rpc_res.values() if v)
            if rpc_ok > 0:
                print(f"\n-> [{env_name}] 实时 RPC 推送成功 ({rpc_ok}/{len(tasks)} 条，语言服务器内存与前端 UI 已实时同步)")

        # 1. 自动前置备份
        target_ids = [cid for cid, _, _ in tasks]
        backup_path = create_backup(env_dir, target_ids)
        print(f"\n-> [{env_name}] 已创建前置快照: {backup_path}")

        # 2. 事务批量更新 SQLite
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        has_raw = db_has_raw_summary(conn)
        rename_dict = {cid: new_t for cid, _, new_t in tasks}
        try:
            for cid, _, new_t in tasks:
                if has_raw:
                    cursor.execute("SELECT raw_summary FROM conversation_summaries WHERE conversation_id = ?", (cid,))
                    r = cursor.fetchone()
                    if r and r["raw_summary"]:
                        new_raw = update_summary_title(r["raw_summary"], new_t)
                        cursor.execute("UPDATE conversation_summaries SET title = ?, raw_summary = ? WHERE conversation_id = ?", (new_t, new_raw, cid))
                    else:
                        cursor.execute("UPDATE conversation_summaries SET title = ? WHERE conversation_id = ?", (new_t, cid))
                else:
                    cursor.execute("UPDATE conversation_summaries SET title = ? WHERE conversation_id = ?", (new_t, cid))
                update_annotation_file(anno_dir, cid, new_t)
                total_updated += 1
            conn.commit()
            print(f"-> [{env_name}] SQLite 数据库与 annotations 已成功更新 ({len(tasks)} 条)")
        except Exception as e:
            conn.rollback()
            print(f"-> [{env_name}] 错误: 写入失败已回滚: {e}")
        finally:
            conn.close()

        # 3. 批量更新 agyhub_summaries_proto.pb
        if pb_path.is_file():
            pb_updated = update_pb_store(pb_path, rename_dict)
            if pb_updated > 0:
                print(f"-> [{env_name}] agyhub_summaries_proto.pb 同步更新成功 ({pb_updated} 条)")

    print(f"\n-> [成功] 全部任务执行完毕！共完成 {total_updated} 处写入。\n")
    return 0


def cmd_backup(args: argparse.Namespace) -> int:
    """手动创建指定或全部环境的快照备份。"""
    envs = get_active_environments(args.target)
    if not envs:
        print(f"未找到环境 (目标: {args.target})。")
        return 1

    for env_name, env_dir in envs:
        backup_path = create_backup(env_dir)
        print(f"[{env_name}] 快照备份成功: {backup_path}")
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    """列出快照或从指定快照恢复。"""
    envs = get_active_environments(args.target)
    if not envs:
        print("未找到有效环境。")
        return 1

    if args.list:
        print("\n可用快照列表：")
        found_any = False
        for env_name, env_dir in envs:
            b_root = env_dir / "backups" / "titles"
            if not b_root.is_dir():
                continue
            backups = sorted(b_root.glob("backup_*"), reverse=True)
            for b in backups:
                found_any = True
                meta_file = b / "meta.json"
                meta_str = ""
                if meta_file.is_file():
                    try:
                        m = json.loads(meta_file.read_text(encoding="utf-8"))
                        tids = m.get("target_ids", [])
                        meta_str = f" (目标: {len(tids) if isinstance(tids, list) else '全量'})"
                    except Exception:
                        pass
                print(f"  [{env_name}] {b.name}{meta_str} -> {b}")
        if not found_any:
            print("  （目前没有任何快照备份）")
        print()
        return 0

    if not args.snapshot:
        print("错误: 请指定要恢复的快照目录路径或快照名称，或使用 --list 查看可用快照。")
        return 1

    snap_path = Path(args.snapshot)
    matched_env_dir: Optional[Path] = None

    if snap_path.is_dir():
        # 从 meta.json 推导所属环境
        meta_file = snap_path / "meta.json"
        if meta_file.is_file():
            try:
                m = json.loads(meta_file.read_text(encoding="utf-8"))
                if "env_dir" in m:
                    matched_env_dir = Path(m["env_dir"])
            except Exception:
                pass
    else:
        # 在各环境备份目录下查找
        for _, env_dir in envs:
            cand = env_dir / "backups" / "titles" / args.snapshot
            if cand.is_dir():
                snap_path = cand
                matched_env_dir = env_dir
                break

    if not snap_path.is_dir():
        print(f"错误: 快照路径不存在: {args.snapshot}")
        return 1

    if not matched_env_dir:
        matched_env_dir = envs[0][1]

    # 执行恢复
    db_backup = snap_path / "conversation_summaries.db"
    if db_backup.is_file():
        shutil.copy2(db_backup, matched_env_dir / "conversation_summaries.db")
        print(f"已恢复数据库: {matched_env_dir / 'conversation_summaries.db'}")

    pb_backup = snap_path / "agyhub_summaries_proto.pb"
    if pb_backup.is_file():
        shutil.copy2(pb_backup, matched_env_dir / "agyhub_summaries_proto.pb")
        print(f"已恢复 protobuf 文件: {matched_env_dir / 'agyhub_summaries_proto.pb'}")

    anno_backup = snap_path / "annotations"
    if anno_backup.is_dir():
        target_annos = matched_env_dir / "annotations"
        target_annos.mkdir(parents=True, exist_ok=True)
        for pbtxt in anno_backup.glob("*.pbtxt"):
            shutil.copy2(pbtxt, target_annos / pbtxt.name)
        print(f"已恢复 annotations 注解文件。")

    print("\n[还原成功] 已从快照恢复完成。\n")
    return 0


# ----------------------------------------------------------------------
# CLI 入口与解析
# ----------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    common_parent = argparse.ArgumentParser(add_help=False)
    common_parent.add_argument(
        "--target",
        type=str,
        default="all",
        choices=["all", "app", "cli", "ide"],
        help="目标治理环境: all (全部), app (Antigravity桌面端), cli (agy命令行), ide (默认: all)",
    )

    parser = argparse.ArgumentParser(
        prog="agy_titles",
        description="Google Antigravity (App & CLI) 会话标题批量治理与中文化工具",
        parents=[common_parent],
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 1. list
    p_list = subparsers.add_parser("list", parents=[common_parent], help="列出会话并支持环境与中英文筛选")
    p_list.add_argument("--limit", type=int, default=50, help="限制输出条数 (默认 50)")
    p_list.add_argument("--all", action="store_true", help="显示全部记录")
    p_list.add_argument("--english-only", action="store_true", help="仅显示英文标题的会话（待治理项）")
    p_list.add_argument("--chinese-only", action="store_true", help="仅显示已有中文标题的会话")
    p_list.add_argument("--json", action="store_true", help="以 JSON 格式输出，便于 AI Agent 解析")

    # 2. get
    p_get = subparsers.add_parser("get", parents=[common_parent], help="查看单个会话详细信息")
    p_get.add_argument("id", type=str, help="会话 ID (支持前缀匹配)")
    p_get.add_argument("--json", action="store_true", help="以 JSON 格式输出")

    # 3. rename
    p_rename = subparsers.add_parser("rename", parents=[common_parent], help="重命名单个会话")
    p_rename.add_argument("id", type=str, help="会话 ID (支持前缀匹配)")
    p_rename.add_argument("new_title", type=str, help="新标题")
    p_rename.add_argument("--dry-run", action="store_true", help="预览变更，不实际修改")

    # 4. batch-rename
    p_batch = subparsers.add_parser("batch-rename", parents=[common_parent], help="批量重命名多个会话")
    p_batch.add_argument("payload", nargs="?", type=str, help="JSON 字符串或 '-' (从标准输入读取)")
    p_batch.add_argument("--file", type=str, help="包含重命名映射的 JSON 文件路径")
    p_batch.add_argument("--dry-run", action="store_true", help="预览变更，不实际修改")

    # 5. backup
    subparsers.add_parser("backup", parents=[common_parent], help="创建数据库、pb 与注解快照备份")

    # 6. restore
    p_restore = subparsers.add_parser("restore", parents=[common_parent], help="从快照恢复数据")
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