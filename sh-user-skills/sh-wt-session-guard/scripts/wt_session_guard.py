# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "psutil>=7.0.0",
# ]
# ///
"""
========================================================================================
Windows Terminal (wt) 与 Antigravity CLI (agy) 会话恢复守卫引擎
========================================================================================
【架构定位】
面向 Windows Terminal 独立定制版与 agy CLI 的双保险会话保持与优雅收敛守卫工具。

【核心痛点】
当用户在 Windows Terminal 中运行多个 agy 会话时，如果直接点击右上角 [X] 并确认“全部关闭”，
WT 会直接切断 ConPTY 管道并强杀子进程树，导致 agy 来不及向终端标准输出打印
`Resume with -c: agy --conversation=<id>`。
在 WT 重启还原各标签页时，用户无法从还原历史中直接复制命令恢复会话。

【双保险解决方案】
1. 内存态精准追踪：
   - 实时解析 WindowsTerminal.exe 进程树；
   - 提取各标签页的 WT_SESSION (GUID)；
   - 识别子进程中的 agy.exe，提取 --conversation=<uuid> 或关联其活跃工作区历史。
2. 优雅停机信号注入：
   - 支持通过 Win32 AttachConsole + GenerateConsoleCtrlEvent(CTRL_C_EVENT) 向指定或全部 agy 广播信号。
3. 退出后 Buffer 原子补写保底（100% 视觉还原）：
   - 当 WT 窗口关闭/退出落盘后，守卫自动定位 %LOCALAPPDATA%\\Microsoft\\Windows Terminal\\buffer_<GUID>.txt；
   - 校验文件尾部，若未包含恢复提示，以 UTF-16LE 格式自动追加标准化恢复行：
       Resume with -c (or command below):
       agy --conversation=<uuid>
       PS C:\\Users\\29580>
   - 确保下次 WT 还原会话时，屏幕上方 100% 呈现与手动 Ctrl+C 完全一致的恢复命令。
========================================================================================
"""

from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass
import io
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Dict, List, Optional

import psutil

# -----------------------------------------------------------------------------
# 模块常量与开关配置
# -----------------------------------------------------------------------------
LOCALAPPDATA = os.environ.get("LOCALAPPDATA", "")
USERPROFILE = os.environ.get("USERPROFILE", "")

WT_STATE_DIR = Path(LOCALAPPDATA) / "Microsoft" / "Windows Terminal" if LOCALAPPDATA else Path.home() / "AppData" / "Local" / "Microsoft" / "Windows Terminal"
AGY_HOME = Path(USERPROFILE) / ".gemini" / "antigravity-cli" if USERPROFILE else Path.home() / ".gemini" / "antigravity-cli"
AGY_HISTORY_FILE = AGY_HOME / "history.jsonl"
AGY_PRESENCE_DIR = AGY_HOME / "presence"

# 正则表达式
UUID_REGEX = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
CONV_ARG_REGEX = re.compile(r"--conversation=([0-9a-fA-F-]+)")

# Win32 API 定义
kernel32 = ctypes.windll.kernel32
CTRL_C_EVENT = 0


# -----------------------------------------------------------------------------
# 数据结构定义
# -----------------------------------------------------------------------------
@dataclass
class AgySession:
    wt_pid: int
    shell_name: str
    shell_pid: int
    wt_session_guid: str
    agy_pid: int
    cmdline: List[str]
    conversation_id: str
    cwd: str
    buffer_file: Path

    def to_dict(self) -> Dict[str, object]:
        return {
            "wt_pid": self.wt_pid,
            "shell_name": self.shell_name,
            "shell_pid": self.shell_pid,
            "wt_session_guid": self.wt_session_guid,
            "agy_pid": self.agy_pid,
            "conversation_id": self.conversation_id,
            "cwd": self.cwd,
            "buffer_file": str(self.buffer_file),
            "buffer_exists": self.buffer_file.exists(),
        }


# -----------------------------------------------------------------------------
# 核心业务逻辑
# -----------------------------------------------------------------------------
def setup_console_encoding() -> None:
    """保障控制台标准输入输出为 UTF-8"""
    if sys.platform == "win32":
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "buffer"):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def get_latest_conversation_for_workspace(workspace_dir: str) -> Optional[str]:
    """从 history.jsonl 反查指定工作区最近活跃的会话 ID"""
    if not AGY_HISTORY_FILE.exists():
        return None

    norm_target = str(Path(workspace_dir).resolve()).lower() if workspace_dir else ""
    try:
        # 逆序读取最后 200 行
        with open(AGY_HISTORY_FILE, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        for line in reversed(lines[-200:]):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                ws = data.get("workspace", "")
                cid = data.get("conversationId", "")
                if cid and ws:
                    norm_ws = str(Path(ws).resolve()).lower()
                    if norm_ws == norm_target:
                        return cid
            except Exception:
                continue
    except Exception:
        pass
    return None


def resolve_conversation_id(agy_proc: psutil.Process, cmdline: List[str], cwd: str) -> str:
    """综合命令行参数与工作区历史解析出真实 conversation_id"""
    # 1. 优先从命令行参数中提取 --conversation=...
    cmd_str = " ".join(cmdline)
    match = CONV_ARG_REGEX.search(cmd_str)
    if match:
        return match.group(1)

    # 2. 从 history.jsonl 查找匹配 cwd 的最新活跃会话
    if cwd:
        found = get_latest_conversation_for_workspace(cwd)
        if found:
            return found

    # 3. 兜底尝试检查 presence 目录最近修改的 lock 文件
    if AGY_PRESENCE_DIR.exists():
        try:
            locks = sorted(
                AGY_PRESENCE_DIR.glob("*.lock"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if locks:
                name = locks[0].stem
                if UUID_REGEX.match(name):
                    return name
        except Exception:
            pass

    return "unknown-conversation-id"


def scan_wt_agy_sessions() -> List[AgySession]:
    """全盘扫描 Windows Terminal 进程树下所有运行中的 agy 会话"""
    sessions: List[AgySession] = []

    # 查找所有 WindowsTerminal.exe 进程
    wt_procs: Dict[int, psutil.Process] = {}
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = (proc.info["name"] or "").lower()
            if name in ("windowsterminal.exe", "wt.exe"):
                wt_procs[proc.pid] = proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not wt_procs:
        return sessions

    # 扫描 Shell 进程（powershell.exe, pwsh.exe, cmd.exe）
    for proc in psutil.process_iter(["pid", "name", "ppid"]):
        try:
            pname = (proc.info["name"] or "").lower()
            if not (pname.startswith("powershell") or pname.startswith("pwsh") or pname == "cmd.exe"):
                continue

            # 检查环境变量中是否有 WT_SESSION
            try:
                env = proc.environ()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue

            wt_session = env.get("WT_SESSION")
            if not wt_session:
                continue

            # 确认父进程祖先链是否通往某个 WindowsTerminal.exe
            parent = proc.parent()
            wt_pid = 0
            curr = proc
            while curr:
                if curr.pid in wt_procs:
                    wt_pid = curr.pid
                    break
                try:
                    curr = curr.parent()
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    break

            # 寻找该 Shell 下的子进程 agy.exe
            try:
                children = proc.children(recursive=True)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue

            for child in children:
                try:
                    cname = (child.name() or "").lower()
                    if cname == "agy.exe" or cname == "agy":
                        cmdline = child.cmdline()
                        try:
                            cwd = child.cwd()
                        except Exception:
                            cwd = ""
                        cid = resolve_conversation_id(child, cmdline, cwd)
                        buf_file = WT_STATE_DIR / f"buffer_{wt_session.upper()}.txt"

                        sessions.append(
                            AgySession(
                                wt_pid=wt_pid or (parent.pid if parent else 0),
                                shell_name=pname,
                                shell_pid=proc.pid,
                                wt_session_guid=wt_session,
                                agy_pid=child.pid,
                                cmdline=cmdline,
                                conversation_id=cid,
                                cwd=cwd,
                                buffer_file=buf_file,
                            )
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return sessions


def send_ctrl_c_to_pid(pid: int) -> bool:
    """向指定控制台进程安全广播 Win32 CTRL_C_EVENT"""
    try:
        kernel32.FreeConsole()
        if kernel32.AttachConsole(pid):
            kernel32.SetConsoleCtrlHandler(None, True)
            kernel32.GenerateConsoleCtrlEvent(CTRL_C_EVENT, 0)
            kernel32.FreeConsole()
            return True
    except Exception:
        pass
    return False


def is_patch_needed(content: str, conversation_id: str) -> bool:
    """精准判断当前会话对应的终端尾部是否已存在恢复提示"""
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return True

    # 寻找最后一个 "[已还原" 标记（若有）
    last_restore_idx = -1
    for idx, line in enumerate(lines):
        if "[已还原" in line:
            last_restore_idx = idx

    # 仅检测最近一个生命周期周期（还原标记之后或最后 25 行）
    active_lines = lines[last_restore_idx + 1 :] if last_restore_idx != -1 else lines[-25:]
    tail_text = "\n".join(active_lines)

    if "Resume with -c" in tail_text or f"agy --conversation={conversation_id}" in tail_text:
        return False
    return True


def patch_buffer_file(buffer_file: Path, conversation_id: str, dry_run: bool = False) -> bool:
    """原子校对并以 UTF-16LE 格式追加会话恢复命令"""
    if not buffer_file.exists():
        # 若 buffer 文件尚未生成，暂不强制创建空文件避免影响 WT 内部加载状态
        return False

    try:
        content = buffer_file.read_text(encoding="utf-16le", errors="ignore")
    except Exception as e:
        print(f"[-] 读取 buffer 文件异常 {buffer_file.name}: {e}")
        return False

    # 若尾部在最近周期中已存在恢复提示，说明已经正常写入过，无需重复补写
    if not is_patch_needed(content, conversation_id):
        return False

    resume_block = (
        "\nResume with -c (or command below):\n"
        f"agy --conversation={conversation_id}\n"
        "PS C:\\Users\\29580>\n"
    )

    if dry_run:
        print(f"[Dry-Run] 拟向 {buffer_file.name} 追加补丁:\n{resume_block.strip()}")
        return True

    try:
        with open(buffer_file, "a", encoding="utf-16le") as f:
            f.write(resume_block)
        return True
    except Exception as e:
        print(f"[-] 补写 buffer 文件失败 {buffer_file.name}: {e}")
        return False


# -----------------------------------------------------------------------------
# 命令行子命令入口
# -----------------------------------------------------------------------------
def cmd_scan(args: argparse.Namespace) -> None:
    """扫描并展示当前 WT 窗口与各标签页中的 agy 会话"""
    sessions = scan_wt_agy_sessions()
    if not sessions:
        print("[*] 当前未检测到在 Windows Terminal 标签页内运行的 agy 会话。")
        return

    print(f"[+] 检测到 {len(sessions)} 个在 Windows Terminal 内运行的 agy 会话:\n")
    for idx, s in enumerate(sessions, 1):
        print(f"[{idx}] 会话 ID (Conversation): {s.conversation_id}")
        print(f"    ├─ agy PID:          {s.agy_pid}")
        print(f"    ├─ Shell (PID):      {s.shell_name} ({s.shell_pid})")
        print(f"    ├─ WT PID:           {s.wt_pid}")
        print(f"    ├─ WT 标签页 GUID:   {s.wt_session_guid}")
        print(f"    ├─ 工作目录 (Cwd):   {s.cwd}")
        print(f"    └─ WT Buffer 路径:   {s.buffer_file} (存在: {s.buffer_file.exists()})")
        print()


def cmd_stop_all(args: argparse.Namespace) -> None:
    """优雅向所有在 WT 内运行的 agy 会话发送 Ctrl+C"""
    current_pid = os.getpid()
    sessions = scan_wt_agy_sessions()
    if not sessions:
        print("[*] 当前未检测到需要终止的 agy 会话。")
        return

    print(f"[*] 准备向 {len(sessions)} 个 agy 会话广播 Ctrl+C 优雅停机信号...")
    stopped = 0
    for s in sessions:
        if s.agy_pid == current_pid:
            print(f"    [-] 跳过当前正在执行脚本的自身进程 (PID {s.agy_pid})")
            continue

        print(f"    ├─ 向 PID {s.agy_pid} (会话: {s.conversation_id[:8]}...) 发送 Ctrl+C...")
        ok = send_ctrl_c_to_pid(s.agy_pid)
        if ok:
            stopped += 1

    print(f"[+] 信号广播完成 (成功投递: {stopped}/{len(sessions)})。")


def cmd_patch_all(args: argparse.Namespace) -> None:
    """手动扫描并修补对应 WT 标签页的 buffer 文件"""
    sessions = scan_wt_agy_sessions()
    if not sessions:
        print("[*] 当前未检测到活跃会话。")
        return

    patched = 0
    for s in sessions:
        if patch_buffer_file(s.buffer_file, s.conversation_id, dry_run=args.dry_run):
            print(f"[+] 成功修补 {s.buffer_file.name} ➔ 会话 {s.conversation_id}")
            patched += 1
        else:
            print(f"[*] {s.buffer_file.name} 无需修补或文件不存在。")

    print(f"\n[+] 处理完成，共补写 {patched} 个 buffer 文件。")


GUARD_PID_FILE = WT_STATE_DIR / "session_guard.pid"
GUARD_LOG_FILE = WT_STATE_DIR / "session_guard.log"


def get_daemon_pid() -> Optional[int]:
    """检查后台守护进程是否正在运行"""
    if GUARD_PID_FILE.exists():
        try:
            pid = int(GUARD_PID_FILE.read_text(encoding="utf-8").strip())
            if psutil.pid_exists(pid):
                p = psutil.Process(pid)
                pname = (p.name() or "").lower()
                if "python" in pname or "uv" in pname:
                    return pid
        except Exception:
            pass
    return None


def log_guard(msg: str) -> None:
    """写入带时间戳的守护日志"""
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now_str}] {msg}\n"
    try:
        with open(GUARD_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def start_daemon() -> None:
    """启动无窗口后台守护进程"""
    running_pid = get_daemon_pid()
    if running_pid:
        print(f"[*] 守护进程已在后台运行中 (PID: {running_pid})。")
        return

    import subprocess

    script_path = str(Path(__file__).resolve())
    cmd = ["uv", "run", script_path, "guard", "--foreground"]
    # DETACHED_PROCESS = 0x00000008, CREATE_NO_WINDOW = 0x08000000
    creationflags = 0x00000008 | 0x08000000
    try:
        proc = subprocess.Popen(
            cmd,
            creationflags=creationflags,
            close_fds=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
        time.sleep(1.5)
        daemon_pid = get_daemon_pid()
        if daemon_pid:
            print(f"[+] 守护进程已成功在后台启动 (PID: {daemon_pid})。")
        else:
            print(f"[+] 守护进程已发起启动 (Launcher PID: {proc.pid})。")
        print(f"    日志文件: {GUARD_LOG_FILE}")
        print("    可通过 `uv run wt_session_guard.py status` 查看状态，`stop-guard` 停止。")
    except Exception as e:
        print(f"[-] 启动后台守护进程失败: {e}")


def stop_daemon() -> None:
    """停止后台守护进程"""
    running_pid = get_daemon_pid()
    if not running_pid:
        print("[*] 后台守护进程未在运行。")
        if GUARD_PID_FILE.exists():
            try:
                GUARD_PID_FILE.unlink()
            except Exception:
                pass
        return

    try:
        p = psutil.Process(running_pid)
        p.terminate()
        p.wait(timeout=3)
        print(f"[+] 后台守护进程 (PID: {running_pid}) 已优雅终止。")
    except Exception as e:
        print(f"[-] 停止守护进程异常: {e}")
    finally:
        if GUARD_PID_FILE.exists():
            try:
                GUARD_PID_FILE.unlink()
            except Exception:
                pass


def cmd_status(args: argparse.Namespace) -> None:
    """查询守护状态与当前受保护的会话"""
    daemon_pid = get_daemon_pid()
    if daemon_pid:
        print(f"[+] 守卫状态: 后台运行中 (PID: {daemon_pid})")
    else:
        print("[-] 守卫状态: 未运行 (可通过 `guard --daemon` 启动)")

    sessions = scan_wt_agy_sessions()
    print(f"[*] 当前在线受保护的 agy 会话数: {len(sessions)}")
    for idx, s in enumerate(sessions, 1):
        print(f"    [{idx}] {s.conversation_id[:8]}... (PID {s.agy_pid}, Tab GUID: {s.wt_session_guid[:8]}...)")


def cmd_guard(args: argparse.Namespace) -> None:
    """常驻后台守护引擎：实时追踪会话，在 WT 关闭/退出瞬间完成双保险补写"""
    if getattr(args, "daemon", False):
        start_daemon()
        return

    # 前台/工作线程执行
    print("==================================================================")
    print("Windows Terminal (wt) agy 会话恢复守护引擎已启动")
    print("监听模式：双保险协同（WT 退出自动落盘修补 + 活跃追踪）")
    print("按 Ctrl+C 可停止当前守护进程。")
    print("==================================================================")

    current_pid = os.getpid()
    log_guard(f"守护引擎启动 (PID: {current_pid})")
    try:
        GUARD_PID_FILE.write_text(str(current_pid), encoding="utf-8")
    except Exception:
        pass

    # 缓存上一次扫描到的活跃会话：wt_session_guid -> AgySession
    last_known_sessions: Dict[str, AgySession] = {}
    known_wt_pids: set[int] = set()

    try:
        while True:
            active_sessions = scan_wt_agy_sessions()
            current_wt_pids = set()

            for s in active_sessions:
                last_known_sessions[s.wt_session_guid] = s
                if s.wt_pid:
                    current_wt_pids.add(s.wt_pid)

            # 检测是否有已跟踪的 WT 进程发生退出
            if known_wt_pids and not current_wt_pids:
                msg_exit = "检测到全部 Windows Terminal 窗口已关闭退出！开始执行会话历史双保险收敛..."
                print(f"\n[!] {msg_exit}")
                log_guard(msg_exit)
                time.sleep(0.3)  # 等待 WT 最后一批 buffer 文件彻底完成磁盘刷入

                patched_count = 0
                for guid, session in list(last_known_sessions.items()):
                    buf_file = session.buffer_file
                    if buf_file.exists():
                        if patch_buffer_file(buf_file, session.conversation_id):
                            info = f"成功补写标签页 {guid} ➔ 会话恢复命令: agy --conversation={session.conversation_id}"
                            print(f"    [+] {info}")
                            log_guard(info)
                            patched_count += 1
                        else:
                            print(f"    [*] 标签页 {guid} 已具备恢复命令，跳过")

                summary = f"会话还原保底完成，共修补 {patched_count} 个标签页。下次打开 WT 即可直接复制恢复。"
                print(f"[+] {summary}\n")
                log_guard(summary)
                last_known_sessions.clear()

            known_wt_pids = current_wt_pids
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[*] 守护引擎已退出。")
        log_guard(f"守护引擎被手动中断 (PID: {current_pid})")
    except Exception as e:
        import traceback

        err_detail = traceback.format_exc()
        print(f"\n[-] 守护引擎发生异常: {e}\n{err_detail}")
        log_guard(f"守护引擎异常崩溃: {e}\n{err_detail}")
    finally:
        if GUARD_PID_FILE.exists():
            try:
                if GUARD_PID_FILE.read_text(encoding="utf-8").strip() == str(current_pid):
                    GUARD_PID_FILE.unlink()
            except Exception:
                pass


# -----------------------------------------------------------------------------
# 程序入口
# -----------------------------------------------------------------------------
def main() -> None:
    setup_console_encoding()

    parser = argparse.ArgumentParser(
        description="Windows Terminal (wt) 与 agy CLI 会话保持与恢复双保险守卫引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="子命令")

    # scan
    subparsers.add_parser("scan", help="扫描并列出当前 WT 内运行的所有 agy 会话")

    # status
    subparsers.add_parser("status", help="查询守护进程运行状态与受保护会话")

    # stop-all
    subparsers.add_parser("stop-all", help="向当前所有 WT 内的 agy 广播 Ctrl+C 优雅停机信号")

    # patch-all
    p_patch = subparsers.add_parser("patch-all", help="手动校对并修补当前各标签页的 buffer 文件")
    p_patch.add_argument("--dry-run", action="store_true", help="仅预览拟追加的恢复文本，不实际落盘")

    # guard
    p_guard = subparsers.add_parser("guard", help="启动常驻守护模式（WT 关闭时全自动补写保证 100% 还原）")
    p_guard.add_argument("--daemon", action="store_true", help="以无窗口后台守护模式运行")
    p_guard.add_argument("--foreground", action="store_true", help="显式前台运行（守护进程内部使用）")

    # stop-guard
    subparsers.add_parser("stop-guard", help="停止后台守护进程")

    args = parser.parse_args()

    if args.subcommand == "scan":
        cmd_scan(args)
    elif args.subcommand == "status":
        cmd_status(args)
    elif args.subcommand == "stop-all":
        cmd_stop_all(args)
    elif args.subcommand == "patch-all":
        cmd_patch_all(args)
    elif args.subcommand == "guard":
        cmd_guard(args)
    elif args.subcommand == "stop-guard":
        stop_daemon()
    else:
        cmd_scan(args)


if __name__ == "__main__":
    main()
