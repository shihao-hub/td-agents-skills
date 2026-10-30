# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "psutil>=7.0.0",
# ]
# ///
"""
========================================================================================
Windows Terminal (wt) 会话恢复守卫引擎：Antigravity CLI (agy) & Pi Coding Agent (pi)
========================================================================================
【架构定位】
面向 Windows Terminal 独立定制版与主流 Coding Agent (agy / pi) 的双保险会话保持与优雅收敛守卫工具。

【核心痛点】
当用户在 Windows Terminal 中运行多个 agy 或 pi 会话时，如果直接点击右上角 [X] 并确认“全部关闭”，
WT 会直接切断 ConPTY 管道并强杀子进程树，导致 Agent 来不及向终端标准输出打印会话恢复命令：
- agy: `Resume with -c: agy --conversation=<uuid>`
- pi:  `To resume this session: pi --session <uuid>`
在 WT 重启还原各标签页时，用户无法从还原历史中直接复制命令恢复会话。

【双保险解决方案】
1. 内存态精准追踪：
   - 实时解析 WindowsTerminal.exe 进程树；
   - 提取各标签页的 WT_SESSION (GUID)；
   - 识别子进程中的 agy.exe 与 pi (node.exe / pi.exe)；
   - 解析命令行参数或反查其工作区持久化历史（~/.pi/agent/sessions/ 与 agy history.jsonl）。
2. 优雅停机信号注入：
   - 支持通过 Win32 AttachConsole + GenerateConsoleCtrlEvent(CTRL_C_EVENT) 向指定或全部 Agent 广播优雅停机信号。
3. 退出后 Buffer 原子补写保底（100% 视觉还原）：
   - 当 WT 窗口关闭/退出落盘后，守卫自动定位 %LOCALAPPDATA%\\Microsoft\\Windows Terminal\\buffer_<GUID>.txt；
   - 校验文件尾部，若未包含恢复提示，以 UTF-16LE 格式自动追加标准化恢复行：
       [agy] Resume with -c (or command below):
             agy --conversation=<uuid>
             PS <cwd>>
       [pi]  To resume this session: pi --session <uuid>
             PS <cwd>>
   - 确保下次 WT 还原会话时，屏幕尾部 100% 呈现与手动 Ctrl+C 完全一致的恢复命令。
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
VERSION = "1.1.0"
LOCALAPPDATA = os.environ.get("LOCALAPPDATA", "")
USERPROFILE = os.environ.get("USERPROFILE", "")

# Windows Terminal 状态目录
WT_STATE_DIR = Path(LOCALAPPDATA) / "Microsoft" / "Windows Terminal" if LOCALAPPDATA else Path.home() / "AppData" / "Local" / "Microsoft" / "Windows Terminal"

# agy CLI 状态目录与文件
AGY_HOME = Path(USERPROFILE) / ".gemini" / "antigravity-cli" if USERPROFILE else Path.home() / ".gemini" / "antigravity-cli"
AGY_HISTORY_FILE = AGY_HOME / "history.jsonl"
AGY_PRESENCE_DIR = AGY_HOME / "presence"

# pi CLI (Pi Coding Agent) 状态目录
PI_HOME = Path(USERPROFILE) / ".pi" / "agent" if USERPROFILE else Path.home() / ".pi" / "agent"
PI_SESSIONS_DIR = PI_HOME / "sessions"

# 正则表达式
UUID_REGEX = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
AGY_CONV_ARG_REGEX = re.compile(r"--conversation=([0-9a-fA-F-]+)")
PI_SESSION_ARG_REGEX = re.compile(r"(?:--session|-s)(?:=|\s+)([0-9a-fA-F-]+)")

# Win32 API 常量
CTRL_C_EVENT = 0
kernel32 = ctypes.windll.kernel32

# 守卫锁文件与日志
GUARD_PID_FILE = WT_STATE_DIR / "session_guard.pid"
GUARD_LOG_FILE = WT_STATE_DIR / "session_guard.log"
AUTOSTART_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_VAL_NAME = "WindowsTerminalSessionGuard"


# -----------------------------------------------------------------------------
# 数据结构定义
# -----------------------------------------------------------------------------
@dataclass
class AgentSession:
    agent_type: str  # "agy" | "pi"
    wt_pid: int
    shell_name: str
    shell_pid: int
    wt_session_guid: str
    proc_pid: int
    cmdline: List[str]
    session_id: str
    cwd: str
    buffer_file: Path

    @property
    def conversation_id(self) -> str:
        """向后兼容属性，等价于 session_id"""
        return self.session_id

    @property
    def agy_pid(self) -> int:
        """向后兼容属性，等价于 proc_pid"""
        return self.proc_pid

    def to_dict(self) -> Dict[str, object]:
        return {
            "agent_type": self.agent_type,
            "wt_pid": self.wt_pid,
            "shell_name": self.shell_name,
            "shell_pid": self.shell_pid,
            "wt_session_guid": self.wt_session_guid,
            "proc_pid": self.proc_pid,
            "session_id": self.session_id,
            "cwd": self.cwd,
            "buffer_file": str(self.buffer_file),
            "buffer_exists": self.buffer_file.exists(),
        }


# 向后兼容别名
AgySession = AgentSession


# -----------------------------------------------------------------------------
# 核心业务逻辑
# -----------------------------------------------------------------------------
def setup_console_encoding() -> None:
    """保障控制台标准输入输出为 UTF-8，并在 pythonw.exe (无控制台) 下安全重定向至 devnull"""
    if sys.platform == "win32":
        if sys.stdout is None:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
        elif hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

        if sys.stderr is None:
            sys.stderr = open(os.devnull, "w", encoding="utf-8")
        elif hasattr(sys.stderr, "buffer"):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# -----------------------------------------------------------------------------
# agy 会话解析逻辑
# -----------------------------------------------------------------------------
def get_latest_conversation_for_workspace(workspace_dir: str) -> Optional[str]:
    """从 agy 的 history.jsonl 反查指定工作区最近活跃的会话 ID"""
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


def resolve_agy_conversation_id(agy_proc: psutil.Process, cmdline: List[str], cwd: str) -> str:
    """综合命令行参数与工作区历史解析出真实 agy conversation_id"""
    # 1. 优先从命令行参数中提取 --conversation=...
    cmd_str = " ".join(cmdline)
    match = AGY_CONV_ARG_REGEX.search(cmd_str)
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


def resolve_conversation_id(agy_proc: psutil.Process, cmdline: List[str], cwd: str) -> str:
    """向后兼容接口"""
    return resolve_agy_conversation_id(agy_proc, cmdline, cwd)


# -----------------------------------------------------------------------------
# pi 会话解析逻辑
# -----------------------------------------------------------------------------
def encode_pi_session_dir(cwd: str, agent_dir: Path = PI_HOME) -> Path:
    """按 pi 官方规范将 cwd 编码为 session 目录路径。
    规则：`--${resolvedCwd.replace(/^[/\\]/, "").replace(/[/\\:]/g, "-")}--`
    """
    resolved = str(Path(cwd).resolve()) if cwd else str(Path.home().resolve())
    clean = re.sub(r"^[/\\]", "", resolved)
    safe = re.sub(r"[/\\:]", "-", clean)
    return agent_dir / "sessions" / f"--{safe}--"


def resolve_pi_session_id(proc: psutil.Process, cmdline: List[str], cwd: str) -> str:
    """综合命令行参数与工作区 sessions 目录反查出真实的 pi 会话 UUID"""
    # 1. 优先从命令行参数匹配 --session <uuid> 或 -s <uuid>
    cmd_str = " ".join(cmdline)
    match = PI_SESSION_ARG_REGEX.search(cmd_str)
    if match:
        return match.group(1)

    # 2. 从 cwd 对应的 sessions 目录中寻找最新修改的 *.jsonl
    if cwd:
        sdir = encode_pi_session_dir(cwd)
        if sdir.exists():
            try:
                jsonls = sorted(sdir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
                if jsonls:
                    m = UUID_REGEX.search(jsonls[0].name)
                    if m:
                        return m.group(0)
            except Exception:
                pass

    # 3. 兜底扫描所有 sessions 子目录中最近修改的 *.jsonl
    if PI_SESSIONS_DIR.exists():
        try:
            recent_files = sorted(
                PI_SESSIONS_DIR.glob("*/*.jsonl"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if recent_files:
                m = UUID_REGEX.search(recent_files[0].name)
                if m:
                    return m.group(0)
        except Exception:
            pass

    return "unknown-session-id"


# -----------------------------------------------------------------------------
# 进程树扫描与会话识别
# -----------------------------------------------------------------------------
def scan_wt_agent_sessions() -> List[AgentSession]:
    """全盘扫描 Windows Terminal 进程树下所有运行中的 agy 与 pi 会话"""
    sessions: List[AgentSession] = []

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

            # 寻找该 Shell 下的子进程（递归检测 agy / pi）
            try:
                children = proc.children(recursive=True)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue

            for child in children:
                try:
                    cname = (child.name() or "").lower()
                    agent_type: Optional[str] = None

                    if cname in ("agy.exe", "agy"):
                        agent_type = "agy"
                    elif cname in ("pi.exe", "pi"):
                        agent_type = "pi"
                    elif cname in ("node.exe", "node"):
                        try:
                            cmdline = child.cmdline()
                        except Exception:
                            cmdline = []
                        cmd_str = " ".join(cmdline).lower()
                        if "pi-coding-agent" in cmd_str or (("dist\\bundle\\cli.js" in cmd_str or "dist/bundle/cli.js" in cmd_str) and "pi" in cmd_str):
                            agent_type = "pi"

                    if not agent_type:
                        continue

                    try:
                        cmdline = child.cmdline()
                    except Exception:
                        cmdline = []

                    try:
                        cwd = child.cwd()
                    except Exception:
                        cwd = ""

                    if agent_type == "agy":
                        sid = resolve_agy_conversation_id(child, cmdline, cwd)
                    else:
                        sid = resolve_pi_session_id(child, cmdline, cwd)

                    buf_file = WT_STATE_DIR / f"buffer_{wt_session.upper()}.txt"

                    sessions.append(
                        AgentSession(
                            agent_type=agent_type,
                            wt_pid=wt_pid or (parent.pid if parent else 0),
                            shell_name=pname,
                            shell_pid=proc.pid,
                            wt_session_guid=wt_session,
                            proc_pid=child.pid,
                            cmdline=cmdline,
                            session_id=sid,
                            cwd=cwd,
                            buffer_file=buf_file,
                        )
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return sessions


def scan_wt_agy_sessions() -> List[AgentSession]:
    """向后兼容接口"""
    return scan_wt_agent_sessions()


# -----------------------------------------------------------------------------
# 信号与缓冲区修补
# -----------------------------------------------------------------------------
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


def build_resume_block(agent_type: str, session_id: str, cwd: str = "") -> str:
    """构造与各 Agent 原生退出输出 100% 吻合的恢复命令文本块"""
    prompt_dir = cwd if cwd else (USERPROFILE or r"C:\Users\29580")
    if agent_type == "pi":
        return (
            f"\nTo resume this session: pi --session {session_id}\n"
            f"PS {prompt_dir}>\n"
        )
    else:  # agy
        return (
            "\nResume with -c (or command below):\n"
            f"agy --conversation={session_id}\n"
            f"PS {prompt_dir}>\n"
        )


def is_patch_needed(content: str, agent_type: str, session_id: str) -> bool:
    """精准判断终端缓冲区末尾是否已存在本会话紧贴光标尾部的有效恢复命令。

    不变式约束：
    1. 还原隔离（Restore Isolation）：若内容中包含 '[已还原' 分隔符，
       则在该标记之前的所有历史文本均属于上一轮生命周期，严禁作为当前轮次的判定依据；
    2. 严格紧贴尾部（Strict Tail Adjacency）：
       一个真正的恢复提示块，在它之后至多只能有一个 Shell 提示符行（如 'PS C:\\Users\\...'），
       绝对不可能跟随任何运行中日志（如 'Model scope:'、'Resumed session'）或命令行输入；
    3. 整句校验（Full Phrase Match）：
       - pi: 某一行必须完整包含 f'To resume this session: pi --session {session_id}'；
       - agy: 必须在尾部紧贴处完整出现 f'agy --conversation={session_id}' 并伴随 'Resume with -c'。
    """
    if not content:
        return True

    # 1. 还原隔离：若存在 '[已还原'，只截取最后一次还原标记之后的内容
    if "[已还原" in content:
        content = content.rsplit("[已还原", 1)[1]

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return True

    # 取最后 4 行有效非空文本
    tail = lines[-4:]

    if agent_type == "pi":
        target_exact = f"To resume this session: pi --session {session_id}"
        found_idx = -1
        for idx, line in enumerate(tail):
            if target_exact in line:
                found_idx = idx
                break

        if found_idx != -1:
            remaining = tail[found_idx + 1 :]
            # 找到恢复提示行后，其后至多允许 1 行且必须是 Shell 提示符
            if len(remaining) == 0:
                return False
            if len(remaining) == 1 and (remaining[0].startswith("PS ") or remaining[0].endswith(">")):
                return False

    else:  # agy
        target_exact = f"agy --conversation={session_id}"
        found_idx = -1
        for idx, line in enumerate(tail):
            if target_exact in line:
                found_idx = idx
                break

        if found_idx != -1:
            has_resume_hint = any("Resume with -c" in l for l in tail[: found_idx + 1])
            if has_resume_hint:
                remaining = tail[found_idx + 1 :]
                if len(remaining) == 0:
                    return False
                if len(remaining) == 1 and (remaining[0].startswith("PS ") or remaining[0].endswith(">")):
                    return False

    return True


def patch_buffer_file(buffer_file: Path, agent_type: str, session_id: str, cwd: str = "", dry_run: bool = False) -> bool:
    """原子校对并以 UTF-16LE 格式追加会话恢复命令"""
    if not buffer_file.exists():
        # 若 buffer 文件尚未生成，暂不强制创建空文件避免影响 WT 内部加载状态
        return False

    try:
        content = buffer_file.read_text(encoding="utf-16le", errors="ignore")
    except Exception as e:
        print(f"[-] 读取 buffer 文件异常 {buffer_file.name}: {e}")
        return False

    # 若尾部已存在恢复提示，说明已经正常写入过，无需重复补写
    if not is_patch_needed(content, agent_type, session_id):
        return False

    resume_block = build_resume_block(agent_type, session_id, cwd)

    if dry_run:
        print(f"[Dry-Run] 拟向 {buffer_file.name} 追加 [{agent_type}] 补丁:\n{resume_block.strip()}")
        return True

    try:
        with open(buffer_file, "a", encoding="utf-16le") as f:
            f.write(resume_block)
        return True
    except Exception as e:
        print(f"[-] 补写 buffer 文件失败 {buffer_file.name}: {e}")
        return False


# -----------------------------------------------------------------------------
# 守卫与自启动底层支撑
# -----------------------------------------------------------------------------
def is_compiled() -> bool:
    """判断当前进程是否已编译为独立二进制 exe"""
    if "__compiled__" in globals() or getattr(sys, "frozen", False):
        return True
    try:
        buf = ctypes.create_unicode_buffer(1024)
        ctypes.windll.kernel32.GetModuleFileNameW(0, buf, 1024)
        name = Path(buf.value).name.lower()
        if name.endswith(".exe") and "python" not in name and "uv" not in name:
            return True
    except Exception:
        pass
    exe_name = Path(sys.executable).name.lower()
    return "python" not in exe_name and "uv" not in exe_name


def get_self_executable() -> str:
    """获取当前真实可执行程序绝对路径（支持 Nuitka 单文件 exe、pythonw 及脚本模式）"""
    if is_compiled():
        # 1. 优先使用 Win32 GetModuleFileNameW（最权威底层 API，避开 Nuitka onefile 虚构的 temp python.exe）
        try:
            buf = ctypes.create_unicode_buffer(1024)
            ctypes.windll.kernel32.GetModuleFileNameW(0, buf, 1024)
            mod_path = Path(buf.value).resolve()
            if mod_path.exists() and mod_path.suffix.lower() == ".exe":
                return str(mod_path)
        except Exception:
            pass

        # 2. 尝试 sys.argv[0]
        try:
            argv_path = Path(sys.argv[0]).resolve()
            if argv_path.exists() and argv_path.suffix.lower() == ".exe":
                return str(argv_path)
        except Exception:
            pass

        # 3. 兜底 sys.executable
        if Path(sys.executable).exists():
            return str(Path(sys.executable).resolve())

    # 脚本模式：优先返回同目录下的 pythonw.exe，避免控制台黑框
    py_exec = Path(sys.executable).resolve()
    pyw_exec = py_exec.parent / "pythonw.exe"
    if pyw_exec.exists():
        return str(pyw_exec)
    return str(py_exec)


def get_windowless_executable() -> str:
    """获取专用于后台静默常驻与自启动的无窗口 PE Subsystem=2 (GUI) 镜像路径"""
    main_exe = Path(get_self_executable()).resolve()
    if is_compiled():
        # 若存在配套的无窗口 GUI 镜像 (wt_session_guardw.exe)，优先使用
        name = main_exe.stem
        if not name.endswith("w"):
            mirror = main_exe.with_name(name + "w.exe")
            if mirror.exists():
                return str(mirror)
        return str(main_exe)

    # 脚本模式：优先使用 pythonw.exe
    py_exec = Path(sys.executable).resolve()
    pyw_exec = py_exec.parent / "pythonw.exe"
    if pyw_exec.exists():
        return str(pyw_exec)
    return str(py_exec)


def get_daemon_pid() -> Optional[int]:
    """检查后台守护进程是否正在运行"""
    if GUARD_PID_FILE.exists():
        try:
            pid = int(GUARD_PID_FILE.read_text(encoding="utf-8").strip())
            if psutil.pid_exists(pid):
                p = psutil.Process(pid)
                pname = (p.name() or "").lower()
                target_name = Path(get_self_executable()).name.lower()
                if "python" in pname or "uv" in pname or "wt_session_guard" in pname or target_name in pname:
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

    target_exe = get_windowless_executable()
    if is_compiled():
        # 已编译为独立 exe：直接拉起无窗口 GUI 镜像自身二进制
        cmd = [target_exe, "guard", "--foreground"]
    else:
        # 单脚本运行：优先使用同虚拟环境下的 pythonw.exe
        script_path = str(Path(__file__).resolve())
        cmd = [target_exe, script_path, "guard", "--foreground", "--headless"]

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
            print(f"[+] 守护进程已成功在后台静默启动 (PID: {daemon_pid})。")
        else:
            print(f"[+] 守护进程已发起启动 (Launcher PID: {proc.pid})。")
        print(f"    可执行程序: {target_exe}")
        print(f"    日志文件:   {GUARD_LOG_FILE}")
        print("    可通过 `status` 查看状态，`stop-guard` 停止。")
    except Exception as e:
        print(f"[-] 启动后台守护进程失败: {e} (调用命令: {cmd})")


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


# -----------------------------------------------------------------------------
# 命令行子命令入口
# -----------------------------------------------------------------------------
def cmd_scan(args: argparse.Namespace) -> None:
    """扫描并展示当前 WT 窗口与各标签页中的 agy 与 pi 会话"""
    sessions = scan_wt_agent_sessions()
    if not sessions:
        print("[*] 当前未检测到在 Windows Terminal 标签页内运行的 agy / pi 会话。")
        return

    print(f"[+] 检测到 {len(sessions)} 个在 Windows Terminal 内运行的 Agent 会话:\n")
    for idx, s in enumerate(sessions, 1):
        print(f"[{idx}] 类型: [{s.agent_type.upper()}]  会话 ID: {s.session_id}")
        print(f"    ├─ Agent PID:        {s.proc_pid}")
        print(f"    ├─ Shell (PID):      {s.shell_name} ({s.shell_pid})")
        print(f"    ├─ WT PID:           {s.wt_pid}")
        print(f"    ├─ WT 标签页 GUID:   {s.wt_session_guid}")
        print(f"    ├─ 工作目录 (Cwd):   {s.cwd}")
        print(f"    └─ WT Buffer 路径:   {s.buffer_file} (存在: {s.buffer_file.exists()})")
        print()


def cmd_stop_all(args: argparse.Namespace) -> None:
    """优雅向所有在 WT 内运行的 Agent 会话发送 Ctrl+C"""
    current_pid = os.getpid()
    sessions = scan_wt_agent_sessions()
    if not sessions:
        print("[*] 当前未检测到需要终止的 Agent 会话。")
        return

    print(f"[*] 准备向 {len(sessions)} 个 Agent 会话广播 Ctrl+C 优雅停机信号...")
    stopped = 0
    for s in sessions:
        if s.proc_pid == current_pid:
            print(f"    [-] 跳过当前正在执行脚本的自身进程 (PID {s.proc_pid})")
            continue

        print(f"    ├─ 向 [{s.agent_type.upper()}] PID {s.proc_pid} (会话: {s.session_id[:8]}...) 发送 Ctrl+C...")
        ok = send_ctrl_c_to_pid(s.proc_pid)
        if ok:
            stopped += 1

    print(f"[+] 信号广播完成 (成功投递: {stopped}/{len(sessions)})。")


def cmd_patch_all(args: argparse.Namespace) -> None:
    """手动扫描并修补对应 WT 标签页的 buffer 文件"""
    sessions = scan_wt_agent_sessions()
    if not sessions:
        print("[*] 当前未检测到活跃会话。")
        return

    patched = 0
    for s in sessions:
        if patch_buffer_file(s.buffer_file, s.agent_type, s.session_id, cwd=s.cwd, dry_run=args.dry_run):
            print(f"[+] 成功修补 {s.buffer_file.name} ➔ [{s.agent_type}] 会话 {s.session_id}")
            patched += 1
        else:
            print(f"[*] {s.buffer_file.name} 无需修补或文件不存在。")

    print(f"\n[+] 处理完成，共补写 {patched} 个 buffer 文件。")


def cmd_status(args: argparse.Namespace) -> None:
    """查询守护状态与当前受保护的会话"""
    daemon_pid = get_daemon_pid()
    if daemon_pid:
        print(f"[+] 守卫状态: 后台运行中 (PID: {daemon_pid})")
    else:
        print("[-] 守卫状态: 未运行 (可通过 `guard --daemon` 启动)")

    sessions = scan_wt_agent_sessions()
    print(f"[*] 当前在线受保护的 Agent 会话数: {len(sessions)}")
    for idx, s in enumerate(sessions, 1):
        print(f"    [{idx}] [{s.agent_type.upper()}] {s.session_id[:8]}... (PID {s.proc_pid}, Tab GUID: {s.wt_session_guid[:8]}...)")


def cmd_guard(args: argparse.Namespace) -> None:
    """常驻后台守护引擎：实时追踪会话，在 WT 关闭/退出瞬间完成双保险补写"""
    if getattr(args, "daemon", False):
        start_daemon()
        return

    is_headless = getattr(args, "headless", False)
    if is_headless:
        hwnd = kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)

    # 前台/工作线程执行
    if not is_headless:
        print("==================================================================")
        print("Windows Terminal (wt) 会话恢复守护引擎已启动 (agy & pi)")
        print("监听模式：双保险协同（WT 退出自动落盘修补 + 活跃追踪）")
        print("按 Ctrl+C 可停止当前守护进程。")
        print("==================================================================")

    current_pid = os.getpid()
    log_guard(f"守护引擎启动 (PID: {current_pid}) [headless={is_headless}]")
    try:
        GUARD_PID_FILE.write_text(str(current_pid), encoding="utf-8")
    except Exception:
        pass

    # 缓存上一次扫描到的活跃会话：wt_session_guid -> AgentSession
    last_known_sessions: Dict[str, AgentSession] = {}
    known_wt_pids: set[int] = set()

    try:
        while True:
            active_sessions = scan_wt_agent_sessions()
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
                        if patch_buffer_file(buf_file, session.agent_type, session.session_id, cwd=session.cwd):
                            if session.agent_type == "pi":
                                info = f"成功补写标签页 {guid} ➔ pi 会话恢复命令: pi --session {session.session_id}"
                            else:
                                info = f"成功补写标签页 {guid} ➔ agy 会话恢复命令: agy --conversation={session.session_id}"
                            print(f"    [+] {info}")
                            log_guard(info)
                            patched_count += 1
                        else:
                            skip_info = f"标签页 {guid} 尾部已具备有效恢复命令，跳过补写"
                            print(f"    [*] {skip_info}")
                            log_guard(skip_info)
                    else:
                        missing_info = f"标签页 {guid} 的 buffer 文件不存在 ({buf_file.name})，跳过"
                        print(f"    [-] {missing_info}")
                        log_guard(missing_info)

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


def cmd_autostart(args: argparse.Namespace) -> None:
    """管理 Windows 开机自启动项 (HKCU Run)"""
    import winreg

    action = (getattr(args, "action", "") or "status").lower()
    target_exe = get_windowless_executable()
    if is_compiled():
        # 若为无窗口镜像，开机自启无需再通过二级 daemon 启动，直接作为静默常驻进程
        cmd_str = f'"{target_exe}" guard --foreground'
    else:
        script_path = str(Path(__file__).resolve())
        cmd_str = f'"{target_exe}" "{script_path}" guard --foreground'

    if action in ("on", "enable", "install", "add"):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, AUTOSTART_VAL_NAME, 0, winreg.REG_SZ, cmd_str)
            print(f"[+] 成功配置 Windows 开机静默自启动！")
            print(f"    注册表项: HKCU\\{AUTOSTART_REG_KEY}\\{AUTOSTART_VAL_NAME}")
            print(f"    自启命令: {cmd_str}")
            print(f"    提示: 下次开机或登录系统时，守卫引擎将自动在后台静默运行。")
        except Exception as e:
            print(f"[-] 配置开机自启动失败: {e}")

    elif action in ("off", "disable", "uninstall", "remove"):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, AUTOSTART_VAL_NAME)
            print(f"[+] 成功移除 Windows 开机自启动项: {AUTOSTART_VAL_NAME}")
        except FileNotFoundError:
            print(f"[*] 开机自启动项当前未配置，无需移除。")
        except Exception as e:
            print(f"[-] 移除开机自启动项失败: {e}")

    elif action in ("status", "check", "info"):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_KEY, 0, winreg.KEY_QUERY_VALUE) as key:
                val, _ = winreg.QueryValueEx(key, AUTOSTART_VAL_NAME)
            print(f"[+] 开机自启动状态: 已启用 (Enabled)")
            print(f"    注册表项: HKCU\\{AUTOSTART_REG_KEY}\\{AUTOSTART_VAL_NAME}")
            print(f"    自启命令: {val}")
        except FileNotFoundError:
            print(f"[-] 开机自启动状态: 未启用 (Disabled)")
            print(f"    可通过 `autostart on` 命令一键开启开机自启。")
        except Exception as e:
            print(f"[-] 查询开机自启动状态失败: {e}")


# -----------------------------------------------------------------------------
# 程序入口
# -----------------------------------------------------------------------------
def main() -> None:
    setup_console_encoding()

    parser = argparse.ArgumentParser(
        description="Windows Terminal (wt) 会话保持与恢复双保险守卫引擎 (agy & pi)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    subparsers = parser.add_subparsers(dest="subcommand", help="子命令")

    # scan
    subparsers.add_parser("scan", help="扫描并列出当前 WT 内运行的所有 agy 与 pi 会话")

    # status
    subparsers.add_parser("status", help="查询守护进程运行状态与受保护会话")

    # stop-all
    subparsers.add_parser("stop-all", help="向当前所有 WT 内的 Agent 广播 Ctrl+C 优雅停机信号")

    # patch-all
    p_patch = subparsers.add_parser("patch-all", help="手动校对并修补当前各标签页的 buffer 文件")
    p_patch.add_argument("--dry-run", action="store_true", help="仅预览拟追加的恢复文本，不实际落盘")

    # guard
    p_guard = subparsers.add_parser("guard", help="启动常驻守护模式（WT 关闭时全自动补写保证 100%% 还原）")
    p_guard.add_argument("--daemon", action="store_true", help="以无窗口后台守护模式运行")
    p_guard.add_argument("--foreground", action="store_true", help="显式前台运行（守护进程内部使用）")
    p_guard.add_argument("--headless", action="store_true", help="无窗口静默运行（自动隐藏控制台窗口）")

    # stop-guard
    subparsers.add_parser("stop-guard", help="停止后台守护进程")

    # autostart
    p_auto = subparsers.add_parser("autostart", help="管理 Windows 用户开机自启动配置 (HKCU Run)")
    p_auto.add_argument(
        "action",
        nargs="?",
        default="status",
        choices=["on", "off", "status", "enable", "disable", "check"],
        help="操作: on(开启), off(关闭), status(查看状态，默认)",
    )

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
    elif args.subcommand == "autostart":
        cmd_autostart(args)
    else:
        cmd_scan(args)


if __name__ == "__main__":
    main()
