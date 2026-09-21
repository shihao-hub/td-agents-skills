#!/usr/bin/env python3
"""ACP agent 认证探针（Zed registry 外部 agent，stdio JSON-RPC）。

不进 Zed UI，用 settings.json 里 agent_servers.<agent>.env 的环境直接启动官方
agent exe，走 initialize → authenticate(oauth-personal) → session/new，
拿到登录链路的真实结果（含被 Zed 界面隐藏的底层异常）。

用法:
  python acp-auth-probe.py [agent名] [--cached] [--cwd 路径] [--timeout 秒]

模式:
  默认     initialize → authenticate（自动开浏览器，需人工完成授权）→ session/new
  --cached initialize → session/new（不登录，验证已存凭据跨进程可用）

判读:
  POST /token 200 + AUTHENTICATE_OK / SESSION_CREATED_OK + AVAILABLE_MODEL_COUNT>0
  = 链路通；AUTH_FAILED / SESSION_FAILED 会打印 code/message/data。
"""
import argparse
import json
import os
import pathlib
import queue
import re
import subprocess
import sys
import threading
import time

ZED_SETTINGS = pathlib.Path(os.environ.get('APPDATA', '')) / 'Zed' / 'settings.json'
REGISTRY = pathlib.Path(os.environ.get('LOCALAPPDATA', '')) / 'Zed' / 'external_agents' / 'registry'

INTERESTING = re.compile(
    r'Starting|Shutting down|SSL|CERTIFICATE|Traceback|ConnectionError|onboard'
    r'|Resolving Google|Running CCPA|loadCodeAssist|Failed to run onboarding'
    r'|Failed to connect|The authentication flow|Open the following link'
    r'|Cleared credential|Logged out'
)
HTTP_LINE = re.compile(r'connectionpool\.py.*"(?:POST|GET) (\S+) HTTP/[^"]+" (\d+)')
SECRETISH = re.compile(r'(?i)bearer|refresh_token|access_token|client_secret|code_verifier|\bcode=')
ENV_KEYS = ('HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY', 'REQUESTS_CA_BUNDLE',
            'SSL_CERT_FILE', 'GEMINI_API_KEY')


def _strip_jsonc(text):
    out = []
    i, n = 0, len(text)
    in_str = esc = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                in_str = False
            i += 1
        elif c == '"':
            in_str = True
            out.append(c)
            i += 1
        elif text[i:i + 2] == '//':
            while i < n and text[i] != '\n':
                i += 1
        elif text[i:i + 2] == '/*':
            i = text.find('*/', i + 2)
            i = n if i < 0 else i + 2
        else:
            out.append(c)
            i += 1
    return re.sub(r',(\s*[}\]])', r'\1', ''.join(out))


def _agent_object_text(text, agent):
    m = re.search(rf'"{re.escape(agent)}"\s*:\s*\{{', text)
    if not m:
        return None
    start = m.end() - 1
    depth = 0
    in_str = esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def load_env(agent):
    try:
        text = ZED_SETTINGS.read_text(encoding='utf-8')
    except Exception as e:
        print(f'WARN: 无法读取 {ZED_SETTINGS}: {e}', flush=True)
        return {}
    cfg = None
    try:
        settings = json.loads(_strip_jsonc(text))
        cfg = settings.get('agent_servers', {}).get(agent, {})
    except Exception:
        obj = _agent_object_text(text, agent)
        if obj:
            try:
                cfg = json.loads(_strip_jsonc(obj))
            except Exception:
                cfg = None
    if not isinstance(cfg, dict):
        print(f'WARN: 无法从 {ZED_SETTINGS} 解析 agent_servers.{agent}（JSONC 兜底也失败）', flush=True)
        return {}
    env = dict(cfg.get('env', {}))
    if not env:
        print(f'NOTE: agent_servers.{agent}.env 为空/缺失，agent 将走 urllib 注册表回落代理'
              f'（Windows 系统代理）；若需显式注入代理/CA，按 SKILL.md 任务 B 配置。', flush=True)
    return env


def find_exe(agent):
    root = REGISTRY / agent
    if not root.is_dir():
        sys.exit(f'未找到 registry agent 目录: {root}')
    exe = None
    try:
        reg = json.loads((REGISTRY / 'registry.json').read_text(encoding='utf-8'))
        agents = reg.get('agents', reg if isinstance(reg, list) else [])
        info = next((a for a in agents
                     if a.get('name') == agent or a.get('id') == agent), None)
        if info:
            cmd = info.get('command') or info.get('cmd') or ''
            if isinstance(cmd, list):
                cmd = cmd[0] if cmd else ''
            ver = str(info.get('version') or '')
            dirs = (sorted(root.glob(f'v_{ver}_*')) if ver
                    else sorted(d for d in root.glob('v_*') if d.is_dir()))
            if dirs and cmd:
                cand = dirs[-1] / pathlib.Path(cmd).name
                if cand.is_file():
                    exe = cand
    except Exception:
        pass
    if exe is None:
        cands = [p for p in root.glob('v_*/*.exe')
                 if 'localharness' not in p.name.lower()
                 and 'crash' not in p.name.lower()]
        if not cands:
            sys.exit(f'{root} 下没找到可执行文件')
        exe = max(cands, key=lambda p: p.stat().st_size)
    return exe


def sanitize(line):
    return re.sub(r'https?://\S+', '<URL>', line)[:600]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('agent', nargs='?', default='antigravity-acp')
    ap.add_argument('--cached', action='store_true', help='跳过 authenticate，验证已存凭据')
    ap.add_argument('--cwd', default=os.getcwd())
    ap.add_argument('--timeout', type=float, default=240)
    args = ap.parse_args()

    exe = find_exe(args.agent)
    env = os.environ.copy()
    env.update(load_env(args.agent))
    extra = ['--debug'] if 'agy' in exe.name.lower() else []

    print(f'Agent exe: {exe}', flush=True)
    injected = sorted(k for k in env if k.upper() in ENV_KEYS)
    print(f'Injected env keys: {injected}', flush=True)

    p = subprocess.Popen(
        [str(exe), *extra], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace',
        env=env, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    events = queue.Queue()

    def reader(stream, kind):
        for line in stream:
            events.put((kind, line.rstrip('\n')))

    threading.Thread(target=reader, args=(p.stdout, 'rpc'), daemon=True).start()
    threading.Thread(target=reader, args=(p.stderr, 'log'), daemon=True).start()

    def send(i, method, params):
        p.stdin.write(json.dumps(
            {'jsonrpc': '2.0', 'id': i, 'method': method, 'params': params}) + '\n')
        p.stdin.flush()

    send(1, 'initialize', {'protocolVersion': 1, 'clientCapabilities': {},
                           'clientInfo': {'name': 'acp-auth-probe', 'version': '1'}})

    success = False
    auth_sent = session_sent = False
    deadline = time.monotonic() + args.timeout
    try:
        while time.monotonic() < deadline:
            try:
                kind, line = events.get(timeout=1)
            except queue.Empty:
                if p.poll() is not None:
                    print(f'PROCESS_EXIT code={p.returncode}', flush=True)
                    break
                continue
            if kind == 'log':
                if 'stringValue' in line or SECRETISH.search(line):
                    continue
                if 'Open the following link' in line:
                    print('BROWSER_LOGIN_OPENED: 请在弹出的浏览器里完成 Google 授权。', flush=True)
                elif INTERESTING.search(line):
                    print('LOG:', sanitize(line), flush=True)
                elif HTTP_LINE.search(line):
                    m = HTTP_LINE.search(line)
                    path = re.sub(r'\?[^ ]+', '', m.group(1))
                    print(f'HTTP: {path} -> {m.group(2)}', flush=True)
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get('id') == 1 and not auth_sent and not session_sent:
                if 'error' in msg:
                    print(f'INITIALIZE_FAILED: {msg["error"].get("message")}', flush=True)
                    break
                print('INITIALIZE_OK', flush=True)
                if args.cached:
                    send(3, 'session/new', {'cwd': args.cwd, 'mcpServers': []})
                    session_sent = True
                else:
                    send(2, 'authenticate', {'methodId': 'oauth-personal'})
                    auth_sent = True
            elif msg.get('id') == 2 and auth_sent:
                if 'error' in msg:
                    e = msg['error']
                    print('AUTH_FAILED:', json.dumps(
                        {k: e.get(k) for k in ('code', 'message', 'data')},
                        ensure_ascii=False), flush=True)
                    break
                print('AUTHENTICATE_OK', flush=True)
                send(3, 'session/new', {'cwd': args.cwd, 'mcpServers': []})
                session_sent = True
            elif msg.get('id') == 3 and session_sent:
                if 'error' in msg:
                    e = msg['error']
                    print('SESSION_FAILED:', json.dumps(
                        {k: e.get(k) for k in ('code', 'message', 'data')},
                        ensure_ascii=False), flush=True)
                else:
                    models = [o for c in msg['result'].get('configOptions', [])
                              if c.get('category') == 'model'
                              for o in c.get('options', [])]
                    print(f'SESSION_CREATED_OK AVAILABLE_MODEL_COUNT={len(models)}', flush=True)
                    success = True
                break
        else:
            print('LOGIN_WAIT_TIMED_OUT', flush=True)
    finally:
        try:
            p.stdin.close()
        except Exception:
            pass
        try:
            p.wait(timeout=15)
        except subprocess.TimeoutExpired:
            subprocess.run(['taskkill', '/PID', str(p.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        print(f'PROBE_DONE success={success}', flush=True)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
