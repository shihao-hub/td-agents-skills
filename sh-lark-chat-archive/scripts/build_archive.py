# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""飞书聊天区间/话题 → 单文件 HTML 存档（泛化生成器）。

区间模式：lark-cli +chat-messages-list 按 position/时间起点翻页拉取；
话题模式：+messages-mget --message-ids <话题根> 自动展开全部回复。
图片优先批量取（mget --download-resources 落到 ./lark-im-resources/），
失败退回逐张 +messages-resources-download；按 position 缓存复用。
输出：单文件 HTML（图 base64 内嵌、lightbox、页内编辑器）+ messages.json 快照。

语义（编后记/图注/标题文案）由模型生成后经 --afterword/--captions/--dek 注入，
本脚本只做确定性渲染。
"""

from __future__ import annotations

import argparse
import base64
import html
import io
import json
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

MAX_SIDE = 1600       # 超过则等比缩到该边长
KEEP_RAW_BYTES = 400_000  # 小图直接嵌原字节，不重压
PAGE_SIZE = 50        # 翻页每页条数
MAX_PAGES = 40        # 翻页保护上限
MGET_BATCH = 50       # mget 单批 message id 上限（平台限制）

WEEKDAYS = "星期一 星期二 星期三 星期四 星期五 星期六 星期日".split()


# ---------------- lark-cli 调用 ----------------

def cli_json(args: str, cwd: str | None = None, timeout: int = 180) -> dict:
    """跑 lark-cli 并解析 JSON；stdout 可能带 warning 前缀，从第一个 { 开始截。"""
    p = subprocess.run(
        "lark-cli " + args,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        cwd=cwd,
    )
    out = p.stdout or ""
    i = out.find("{")
    if i < 0:
        raise RuntimeError(
            f"lark-cli 无 JSON 输出：{out[:200]} | stderr: {(p.stderr or '')[:200]}"
        )
    return json.loads(out[i:])


def walk_messages(obj) -> list[dict]:
    """从任意 JSON 包络里递归收集含 message_id 的消息对象（兼容 data.messages/items 等形态）。

    mget 展开话题时同一条消息会出现多次（列表 stub + 展开详情），
    按 message_id 去重并保留字段更全的那份。
    """
    found: dict[str, dict] = {}

    def richness(m: dict) -> int:
        return sum(1 for k in ("msg_type", "create_time", "content", "message_position")
                   if m.get(k) not in (None, ""))

    def rec(node):
        if isinstance(node, dict):
            mid = node.get("message_id")
            if isinstance(mid, str):
                old = found.get(mid)
                if old is None or richness(node) > richness(old):
                    found[mid] = node
            for v in node.values():
                rec(v)
        elif isinstance(node, list):
            for v in node:
                rec(v)

    rec(obj)
    return list(found.values())


# ---------------- 消息拉取 ----------------

def collect_range_messages(chat_id: str, start_position: int | None,
                           start_time: str | None) -> list[dict]:
    """翻页拉取，直到覆盖起点（position 或时间）或没有更多。"""
    got: dict[str, dict] = {}
    token = ""
    for _ in range(MAX_PAGES):
        args = (f"im +chat-messages-list --chat-id {chat_id} --as user "
                f"--json --page-size {PAGE_SIZE}")
        if token:
            args += f" --page-token {token}"
        obj = cli_json(args)
        data = obj.get("data") or {}
        for m in walk_messages(obj):
            got[m["message_id"]] = m
        token = data.get("page_token") or ""
        if not (data.get("has_more") and token):
            break
        msgs = list(got.values())
        positions = [int(m.get("message_position") or 0) for m in msgs]
        times = [str(m.get("create_time") or "") for m in msgs]
        if start_position is not None and positions and min(positions) <= start_position:
            break
        if start_time is not None and times and min(times) <= start_time:
            break

    def keep(m: dict) -> bool:
        if start_position is not None and int(m.get("message_position") or 0) < start_position:
            return False
        if start_time is not None and str(m.get("create_time") or "") < start_time:
            return False
        return True

    msgs = [m for m in got.values() if keep(m)]
    msgs.sort(key=lambda m: (int(m.get("message_position") or 0),
                             str(m.get("create_time") or "")))
    return msgs


def collect_thread_messages(root_id: str, workdir: Path,
                            download: bool = True) -> tuple[list[dict], dict]:
    """话题模式：mget 根消息自动展开全部回复；download=True 时顺带批量下图。

    mget 会把 thread_replies 嵌套在消息对象里（walk_messages 负责展平去重）。
    排序：根消息最前，回复按 thread_message_position（真实楼层号，根为 -1），
    缺楼层号的按 create_time 兜底。
    """
    args = f"im +messages-mget --message-ids {root_id} --as user --json"
    if download:
        args += " --download-resources"
    obj = cli_json(args, cwd=str(workdir))
    msgs = walk_messages(obj)

    def order(m: dict):
        if m.get("message_id") == root_id:
            return (0, -1)
        try:
            t = int(m.get("thread_message_position"))
        except (TypeError, ValueError):
            t = None
        if t is not None and t >= 0:
            return (0, t)
        return (1, str(m.get("create_time") or ""))

    ordered = sorted(msgs, key=order)
    return ordered, obj


# ---------------- 图片获取 ----------------

IMG_KEY_RE = re.compile(r"\[Image:\s*([^\]]+)\]")
POST_IMG_RE = re.compile(r"!\[Image\]\(([^)]+)\)")  # post 富文本内嵌图标记


def extract_image_key(msg: dict) -> str:
    content = str(msg.get("content") or "")
    m = IMG_KEY_RE.search(content)
    if m:
        return m.group(1).strip()
    try:  # 兼容纯 JSON 形态 {"image_key": "..."}
        obj = json.loads(content)
        if isinstance(obj, dict) and isinstance(obj.get("image_key"), str):
            return obj["image_key"]
    except (ValueError, TypeError):
        pass
    return ""


def find_resource_file(res_dir: Path, file_key: str,
                       claimed: set[Path]) -> Path | None:
    """在 mget 批量下图的目录里找属于本消息的文件：优先文件名含 file_key。"""
    if not res_dir.is_dir():
        return None
    files = sorted(f for f in res_dir.iterdir() if f.is_file() and f not in claimed)
    if file_key:
        for f in files:
            if file_key in f.name:
                claimed.add(f)
                return f
    return None


def download_image(message_id: str, file_key: str, name: str,
                   img_dir: Path) -> bytes | None:
    """逐张下载（批量路径失败后的兜底）；name 为缓存/输出基名。成功返回字节。"""
    cached = list(img_dir.glob(f"{name}.*"))
    if cached:
        return cached[0].read_bytes()
    img_dir.mkdir(parents=True, exist_ok=True)
    before = set(img_dir.iterdir())
    for _ in range(2):  # 失败重试一次
        p = subprocess.run(
            f"lark-cli im +messages-resources-download --message-id {message_id} "
            f"--file-key {file_key} --type image --as user --output {name}",
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            cwd=str(img_dir),
        )
        new = [f for f in img_dir.iterdir() if f not in before and f.is_file()]
        if p.returncode == 0 and new:
            return new[0].read_bytes()
    return None


def batch_download(msgs: list[dict], workdir: Path) -> None:
    """区间模式：把图片消息分批交给 mget --download-resources 批量下图。"""
    ids = [m["message_id"] for m in msgs if m.get("msg_type") == "image"]
    for i in range(0, len(ids), MGET_BATCH):
        chunk = ",".join(ids[i:i + MGET_BATCH])
        try:
            cli_json(f"im +messages-mget --message-ids {chunk} --as user "
                     f"--json --download-resources", cwd=str(workdir))
        except Exception as e:  # noqa: BLE001 批量失败不致命，逐张兜底
            print(f"  批量下图失败（将由逐张兜底）：{e}")


def shrink_image(raw: bytes) -> tuple[bytes, str]:
    """按需压缩：大图等比缩到 MAX_SIDE 转 JPEG；小图保留原样。"""
    try:
        from PIL import Image
    except ImportError:
        return raw, "image/png"
    try:
        im = Image.open(io.BytesIO(raw))
        fmt = (im.format or "").upper()
        small = max(im.size) <= MAX_SIDE and len(raw) <= KEEP_RAW_BYTES
        if small and fmt in ("PNG", "JPEG", "GIF", "WEBP"):
            return raw, ("image/png" if fmt == "PNG" else "image/jpeg")
        if max(im.size) > MAX_SIDE:
            ratio = MAX_SIDE / max(im.size)
            im = im.resize((round(im.width * ratio), round(im.height * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        im.convert("RGB").save(buf, "JPEG", quality=84, optimize=True)
        return buf.getvalue(), "image/jpeg"
    except Exception:  # noqa: BLE001 损坏图按原样嵌入
        return raw, "image/png"


def build_data_uri(raw: bytes) -> str:
    data, mime = shrink_image(raw)
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


# ---------------- 渲染 ----------------

def linkify(escaped: str) -> str:
    """把明文 URL 变成可点的链接（在转义后的文本上做，避免破坏 HTML）。"""
    return re.sub(
        r"(https?://[^\s<>\u201c\u201d\"']+|ftp://[^\s<>\u201c\u201d\"']+)",
        r'<a href="\1">\1</a>',
        escaped,
    )


def render_text(msg: dict) -> str:
    content = str(msg.get("content") or "")
    # post 内嵌图标记不进正文文本（图在消息循环里单独渲染）
    content = POST_IMG_RE.sub("", content)
    return "<p class='txt'>" + linkify(html.escape(content)).replace("\n", "<br>") + "</p>"


def render_placeholder(msg: dict) -> str:
    """图片以外的富消息（文件/卡片/音视频等）统一占位，不参与下载。"""
    t = str(msg.get("msg_type") or "?")
    content = str(msg.get("content") or "")
    brief = html.escape(content[:120])
    return f"<div class='missing'>[{t} 消息] {brief}</div>"


NOISE_SVG = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E"
    "%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E"
    "%3CfeColorMatrix values='0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.03 0'/%3E%3C/filter%3E"
    "%3Crect width='140' height='140' filter='url(%23n)'/%3E%3C/svg%3E"
)

CSS = """\
:root{--paper:#f6f3ec;--ink:#26231d;--meta:#8b8474;--line:#d9d2c0;--cinnabar:#a23c2a}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);
  font:15.5px/1.85 "Source Han Serif SC","Noto Serif CJK SC","Source Han Serif CN","STSong","SimSun",serif;
  background-image:url("__NOISE__")}
::selection{background:#e8d8c8}
a{color:var(--cinnabar);text-decoration:none}
a:hover{border-bottom:1px dotted var(--cinnabar)}
.rail{position:fixed;top:0;bottom:0;left:0;width:236px;padding:52px 30px;
  border-right:1px solid var(--line);font-size:13px;line-height:1.7;color:#5d564a}
.rail h1{font-size:15px;margin:0 0 18px;letter-spacing:.35em;color:var(--ink);font-weight:600}
.rail dl{margin:0 0 22px}
.rail dt{font-size:11.5px;letter-spacing:.2em;color:var(--meta);margin-top:12px}
.rail dd{margin:2px 0 0}
.rail nav a{display:block;color:#5d564a;padding:1px 0}
.rail nav a:hover{color:var(--cinnabar);border-bottom:none}
.rail .fine{position:absolute;bottom:40px;font-size:11px;color:var(--meta);line-height:1.7;margin:0}
main{margin-left:236px;padding:70px 56px 90px;max-width:940px}
.head .kicker{font:12px/1 "Cascadia Mono",Consolas,monospace;color:var(--meta);letter-spacing:.18em;margin:0}
.head h2{font-size:30px;font-weight:600;margin:14px 0 10px;letter-spacing:.02em}
.head .dek{color:#5d564a;margin:0 0 8px;max-width:560px}
.rule{border:none;border-top:1px solid var(--line);margin:36px 0 10px}
.sec-label{font:11.5px/1 "Cascadia Mono",Consolas,monospace;letter-spacing:.3em;color:var(--meta);margin:28px 0 30px}
.msg{display:grid;grid-template-columns:58px 1fr;gap:18px;padding:8px 0}
.msg time{font:12px/2.2 "Cascadia Mono",Consolas,monospace;color:var(--meta)}
.msg .body{min-width:0}
.msg .txt{margin:0;overflow-wrap:break-word}
.msg .who{display:block;font-size:12.5px;color:var(--meta);margin-bottom:1px}
.msg.cont{padding-top:3px;margin-top:-5px}
.msg.reply .body{border-left:2px solid var(--cinnabar);padding-left:14px}
.reply-ref{font-size:12.5px;color:var(--cinnabar);display:block;margin-bottom:2px}
.body img{max-width:460px;width:100%;height:auto;display:block;background:#fff;
  border:1px solid var(--line);padding:5px;cursor:zoom-in}
.body img.chain{margin-top:10px}
.lb{position:fixed;inset:0;background:rgba(26,23,18,.93);display:none;z-index:50;cursor:grab}
.lb.on{display:flex;align-items:center;justify-content:center}
.lb img{max-width:94vw;max-height:92vh;width:auto;height:auto;background:#fff;
  border:1px solid #3a352c;padding:10px;cursor:grab;transform-origin:center center}
.lb .hint{position:fixed;left:20px;bottom:16px;font:12px/1 Consolas,monospace;
  color:#b9b0a0;letter-spacing:.14em}
.imgrow{margin:2px 0}
.imgcap{margin:6px 0 0;font-size:12px;line-height:1.7;color:var(--meta)}
.imgcap b{color:var(--cinnabar);font-weight:400;margin-right:.5em;font-family:"Cascadia Mono",Consolas,monospace}
.missing{border:1px dashed var(--line);color:var(--meta);font-size:12.5px;
  padding:14px 16px;font-family:Consolas,monospace;max-width:460px}
.afterword{max-width:660px}
.afterword h3{font-size:17.5px;font-weight:600;margin:34px 0 8px}
.afterword h3 .no{color:var(--cinnabar);font-weight:400;margin-right:.6em}
.afterword p{margin:8px 0}
.afterword blockquote{margin:14px 0;padding:2px 16px;border-left:2px solid var(--cinnabar);color:#57503f}
footer{margin-top:70px;padding-top:18px;border-top:1px solid var(--line);
  font:11.5px/1.8 "Cascadia Mono",Consolas,monospace;color:var(--meta)}
/* 页内编辑 */
.editbar{position:fixed;right:18px;bottom:16px;z-index:60;background:#fffdf7;border:1px solid var(--line);
  box-shadow:0 2px 10px rgba(31,29,26,.18);padding:10px 14px;display:flex;gap:10px;align-items:center;font-size:13px}
.editbar .cnt{color:var(--cinnabar);font-family:"Cascadia Mono",Consolas,monospace;font-size:12px}
.editbar button{font:13px/1 "Source Han Serif SC","Noto Serif CJK SC","SimSun",serif;padding:7px 12px;cursor:pointer;
  border:1px solid var(--line);background:#fff;color:var(--ink)}
.editbar button.primary{background:var(--cinnabar);border-color:var(--cinnabar);color:#fff}
.ebtn{border:1px solid var(--cinnabar);color:var(--cinnabar);background:rgba(255,253,247,.92);
  font:12px/1 "Source Han Serif SC","Noto Serif CJK SC","SimSun",serif;padding:4px 10px;cursor:pointer;z-index:3}
.ebtn:hover{background:var(--cinnabar);color:#fff}
body.editing .msg{position:relative}
.msgdel{position:absolute;top:2px;right:2px}
body.editing .afterword h3{position:relative}
.secdel{margin-left:14px;vertical-align:middle}
body.editing .msg .txt,body.editing p.imgcap{outline:1px dashed #b9b09b;outline-offset:3px;min-height:1em}
@media (max-width:960px){
  .rail{position:static;width:auto;border-right:none;border-bottom:1px solid var(--line);padding:36px 30px}
  .rail .fine{position:static;margin-top:24px}
  main{margin-left:0;padding:44px 24px 70px}
}
"""

LIGHTBOX_JS = """\
<script>
(function () {
  var lb = document.getElementById('lb');
  var big = lb.querySelector('img');
  var scale = 1, tx = 0, ty = 0;
  var dragging = false, sx = 0, sy = 0, moved = false;
  function apply() { big.style.transform = 'translate(' + tx + 'px,' + ty + 'px) scale(' + scale + ')'; }
  function open(src) {
    big.src = src; scale = 1; tx = 0; ty = 0; apply();
    lb.classList.add('on');
    var gap = window.innerWidth - document.documentElement.clientWidth;
    document.documentElement.style.overflow = 'hidden';
    document.body.style.paddingRight = gap > 0 ? gap + 'px' : '';
  }
  function close() {
    lb.classList.remove('on');
    document.documentElement.style.overflow = '';
    document.body.style.paddingRight = '';
  }
  lb.addEventListener('click', function () {
    if (moved) { moved = false; return; }  // 拖拽结束的那次 click 不当作关闭
    close();
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
  document.querySelectorAll('.body img').forEach(function (im) {
    im.addEventListener('click', function () { open(im.src); });
  });
  lb.addEventListener('wheel', function (e) {
    e.preventDefault();  // 锁掉滚动链，Ctrl+滚轮只做缩放
    if (!e.ctrlKey) return;
    scale *= e.deltaY < 0 ? 1.12 : 1 / 1.12;
    scale = Math.min(8, Math.max(0.2, scale));
    apply();
  }, { passive: false });
  lb.addEventListener('mousedown', function (e) {
    if (e.button !== 0) return;
    dragging = true; moved = false; sx = e.clientX - tx; sy = e.clientY - ty;
    lb.style.cursor = 'grabbing';
    e.preventDefault();
  });
  window.addEventListener('mousemove', function (e) {
    if (!dragging) return;
    var nx = e.clientX - sx, ny = e.clientY - sy;
    if (Math.abs(nx - tx) + Math.abs(ny - ty) > 3) moved = true;
    tx = nx; ty = ny; apply();
  });
  window.addEventListener('mouseup', function () {
    dragging = false; lb.style.cursor = '';
  });
  big.addEventListener('dblclick', function () { scale = 1; tx = 0; ty = 0; apply(); });
})();
</script>
"""

EDITOR_JS = """\
<script>
/* 页内编辑：删除消息/编后记小节、改正文与图注、序列化保存。无外部依赖。 */
(function () {
  var FILENAME = '__FILENAME__';
  var undoStack = [];
  var bar = null;

  function mkBtn(label, primary) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = primary ? 'primary' : '';
    b.textContent = label;
    return b;
  }

  function delNodeWithUndo(nodes) {
    var refs = nodes.map(function (n) { return { parent: n.parentNode, node: n, next: n.nextSibling }; });
    undoStack.push(refs);
    nodes.forEach(function (n) { n.remove(); });
    refreshBar();
  }

  function enterEdit() {
    document.body.classList.add('editing');
    document.querySelectorAll('.msg').forEach(function (m) {
      if (m._hasDel) return;
      m._hasDel = true;
      var b = mkBtn('删除本条', true);
      b.className = 'ebtn msgdel';
      b.title = '删除本条（可撤销）';
      b.addEventListener('click', function (e) { e.stopPropagation(); delNodeWithUndo([m]); });
      m.appendChild(b);
    });
    var aw = document.querySelector('.afterword');
    if (aw) {
      Array.prototype.forEach.call(aw.children, function (c) {
        if (c.tagName !== 'H3' || c._hasDel) return;
        c._hasDel = true;
        var b = mkBtn('删除本节', true);
        b.className = 'ebtn secdel';
        b.title = '删除本节（含其下段落，可撤销）';
        b.addEventListener('click', function (e) {
          e.stopPropagation();
          var group = [c], cur = c.nextElementSibling;
          while (cur && cur.tagName !== 'H3') { group.push(cur); cur = cur.nextElementSibling; }
          delNodeWithUndo(group);
        });
        c.appendChild(b);
      });
    }
    document.querySelectorAll('.msg .txt, p.imgcap').forEach(function (p) {
      p.contentEditable = 'true';
      p.spellcheck = false;
    });
    makeBar();
  }

  function makeBar() {
    bar = document.createElement('div');
    bar.className = 'editbar';
    var cnt = document.createElement('span');
    cnt.className = 'cnt';
    bar.appendChild(cnt);
    var ub = mkBtn('撤销删除');
    ub.addEventListener('click', function () {
      var refs = undoStack.pop();
      if (!refs) return;
      refs.forEach(function (r) {
        r.parent.insertBefore(r.node, (r.next && r.next.parentNode === r.parent) ? r.next : null);
      });
      refreshBar();
    });
    var db = mkBtn('放弃修改');
    db.addEventListener('click', function () {
      if (window.confirm('放弃全部未保存的修改并重新加载？')) location.reload();
    });
    var sb = mkBtn('保存修改', true);
    sb.addEventListener('click', save);
    bar.appendChild(ub); bar.appendChild(db); bar.appendChild(sb);
    document.body.appendChild(bar);
    refreshBar();
  }

  function refreshBar() {
    if (!bar) return;
    bar.querySelector('.cnt').textContent = '已删 ' + undoStack.length + ' 处 · 未保存';
  }

  function exitEditUI() {
    document.body.classList.remove('editing');
    document.querySelectorAll('.ebtn').forEach(function (n) { n.remove(); });
    document.querySelectorAll('.msg, .afterword h3').forEach(function (n) { n._hasDel = false; });
    document.querySelectorAll('[contenteditable]').forEach(function (n) {
      n.removeAttribute('contenteditable');
      n.removeAttribute('spellcheck');
    });
    if (bar) { bar.remove(); bar = null; }
  }

  function updateStats() {
    var msgs = document.querySelectorAll('.msg').length;
    var imgCount = document.querySelectorAll('.msg .imgrow img').length;
    var dds = document.querySelectorAll('.rail dl dd');
    if (dds[2]) dds[2].textContent = msgs + ' 条 · 文本 ' + (msgs - imgCount) + ' · 图 ' + imgCount;
    var f = document.querySelector('main > footer');
    if (f) f.textContent = 'lark-cli 导出 · ' + msgs + ' 条 · 图片 ' + imgCount + ' 张内嵌 · 页内编辑版';
  }

  function save() {
    exitEditUI();
    updateStats();
    var big = document.querySelector('#lb img');
    if (big) big.removeAttribute('src');
    var lbEl = document.getElementById('lb');
    if (lbEl) lbEl.classList.remove('on');
    var html = '<!doctype html>\n' + document.documentElement.outerHTML;
    var blob = new Blob([html], { type: 'text/html' });
    function finish(how) {
      var note = document.createElement('div');
      note.className = 'editbar';
      note.appendChild(document.createTextNode(
        how === 'picker' ? '已写入所选文件，建议重载核对。' : '已导出，请用它替换原文件后再打开。'));
      var rb = mkBtn('重载页面', true);
      rb.addEventListener('click', function () { location.reload(); });
      note.appendChild(rb);
      document.body.appendChild(note);
    }
    function fallbackDownload() {
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = FILENAME;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 5000);
      finish('download');
    }
    if (window.showSaveFilePicker) {
      window.showSaveFilePicker({
        suggestedName: FILENAME,
        types: [{ description: 'HTML 存档', accept: { 'text/html': ['.html'] } }]
      }).then(function (h) {
        return h.createWritable().then(function (w) {
          return w.write(blob).then(function () { return w.close(); });
        });
      }).then(function () { finish('picker'); }).catch(fallbackDownload);
    } else {
      fallbackDownload();
    }
  }

  var t = document.getElementById('editToggle');
  if (t) t.addEventListener('click', function (e) {
    e.preventDefault();
    enterEdit();
  });
})();
</script>
"""

PAGE_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>__CSS__</style>
</head>
<body>
<aside class="rail">
  <h1>私 人 存 档</h1>
  <dl>
    <dt>会话</dt><dd>__CHAT_LINE__</dd>
    <dt>时间</dt><dd>__DATE_CN__<br>__SPAN__</dd>
    <dt>规模</dt><dd>__STATS__</dd>
    <dt>目录</dt>
  </dl>
  <nav>
    <a href="#transcript">原文转录</a>
    <a href="#afterword">编后记</a>
    <a href="#" id="editToggle">编辑此页</a>
  </nav>
  <p class="fine">导出自 lark-cli<br>图片已内嵌，仅本机查看<br>__RANGE_NOTE__</p>
</aside>
<main>
  <header class="head">
    <p class="kicker">__KICKER__</p>
    <h2>__TITLE__</h2>
    <p class="dek">__DEK__</p>
  </header>
  <hr class="rule">
  <p class="sec-label" id="transcript">原 文 转 录</p>
  __BODY__
  <hr class="rule">
  <p class="sec-label" id="afterword">编 后 记</p>
  <section class="afterword">
__AFTERWORD__
  </section>
  <footer>__FOOTER__</footer>
</main>
<div class="lb" id="lb"><img alt=""><span class="hint">Ctrl+滚轮缩放 · 拖拽平移 · 双击复位 · Esc 或点空白关闭</span></div>
__LIGHTBOX__
__EDITOR__
</body>
</html>
"""


def render_afterword(sections: list[dict]) -> str:
    nums = "一二三四五六七八九十"
    out = []
    for i, sec in enumerate(sections):
        title = html.escape(str(sec.get("title") or f"小节 {i + 1}"))
        parts = [f"<h3><span class='no'>{nums[i] if i < len(nums) else i + 1}</span>{title}</h3>"]
        for p in sec.get("before") or []:
            parts.append(f"<p>{linkify(html.escape(str(p)))}</p>")
        quote = sec.get("quote")
        if quote:
            parts.append(f"<blockquote>{html.escape(str(quote))}</blockquote>")
        for p in sec.get("after") or []:
            parts.append(f"<p>{linkify(html.escape(str(p)))}</p>")
        out.append("".join(parts))
    return "\n".join(out)


def pos_key(msg: dict, idx: int) -> int:
    """消息的展示/缓存键：优先真实 position；话题回复的 position 恒为 -3（不在主时间线），
    非正数一律回退序号兜底（避开真实区间），保证锚点/缓存/图注键唯一。"""
    try:
        p = int(msg.get("message_position"))
        if p > 0:
            return p
    except (TypeError, ValueError):
        pass
    return 10_000 + idx


def main() -> None:
    ap = argparse.ArgumentParser(
        description="飞书聊天区间/话题 → 单文件 HTML 存档（泛化生成器）")
    ap.add_argument("--chat-id", help="会话 id（oc_xxx）；区间模式必填")
    ap.add_argument("--start-position", type=int,
                    help="区间起点 position（取 >= 该值的消息）")
    ap.add_argument("--start-time",
                    help='区间起点时间，如 "2026-09-20 09:13"（取首个 >= 该时间的消息）')
    ap.add_argument("--thread-root", help="话题根消息 id（om_xxx），话题模式")
    ap.add_argument("--out-dir", help="工作/输出目录（默认 %%TEMP%%\\opencode\\lark_archive\\<id尾8位>）")
    ap.add_argument("--title", default="聊天存档", help="存档标题（默认：聊天存档）")
    ap.add_argument("--dek", help="页首导语（默认自动生成一句话统计）")
    ap.add_argument("--chat-name", help="侧栏会话名（默认用 chat id / 话题根 id）")
    ap.add_argument("--afterword", help="编后记 JSON：[{title,before[],quote?,after[]}]")
    ap.add_argument("--captions", help="图注 JSON：{\"position\": \"图注文字\"}")
    args = ap.parse_args()

    thread_mode = bool(args.thread_root)
    if thread_mode:
        if args.start_position is not None or args.start_time:
            ap.error("--thread-root 与 --start-position/--start-time 互斥")
    elif not args.chat_id:
        ap.error("区间模式需要 --chat-id（或改用 --thread-root 话题模式）")
    if not thread_mode and args.start_position is None and not args.start_time:
        ap.error("区间模式需要 --start-position 或 --start-time 之一作为起点")

    key_id = args.thread_root if thread_mode else args.chat_id
    tail8 = re.sub(r"[^0-9a-zA-Z_]", "", str(key_id)[-8:]) or "default"
    workdir = Path(args.out_dir) if args.out_dir else (
        Path(tempfile.gettempdir()) / "opencode" / "lark_archive" / tail8)
    workdir.mkdir(parents=True, exist_ok=True)
    img_dir = workdir / "img"
    img_dir.mkdir(parents=True, exist_ok=True)
    res_dir = workdir / "lark-im-resources"  # mget --download-resources 的落点

    # ---- 拉取 ----
    if thread_mode:
        print(f"话题模式：mget 展开根消息 {args.thread_root} …")
        msgs, _raw = collect_thread_messages(args.thread_root, workdir, download=True)
    else:
        start_desc = (f"position >= {args.start_position}" if args.start_position is not None
                      else f"time >= {args.start_time}")
        print(f"区间模式：{args.chat_id}，{start_desc} …")
        msgs = collect_range_messages(args.chat_id, args.start_position, args.start_time)
        if any(m.get("msg_type") == "image" for m in msgs):
            print("批量下图（mget --download-resources）…")
            batch_download(msgs, workdir)
    if not msgs:
        raise SystemExit("没有取到任何消息（检查 chat-id / 起点 / 话题根 id）")

    for i, m in enumerate(msgs):
        m["_pos"] = pos_key(m, i)
    n_img = sum(1 for m in msgs if m.get("msg_type") == "image")
    t_first = str(msgs[0].get("create_time") or "")
    t_last = str(msgs[-1].get("create_time") or "")
    print(f"共 {len(msgs)} 条（图片 {n_img}），{t_first} → {t_last}")

    # 快照落盘：撤回阶段取 message_id 用；重跑时可对照
    snapshot = [{
        "message_id": m.get("message_id"),
        "pos_key": m["_pos"],
        "position": m.get("message_position"),
        "msg_type": m.get("msg_type"),
        "create_time": m.get("create_time"),
        "sender": (m.get("sender") or {}).get("sender_name")
        if isinstance(m.get("sender"), dict) else m.get("sender_name"),
        "file_key": extract_image_key(m) if m.get("msg_type") == "image" else None,
        "content_brief": str(m.get("content") or "")[:120],
    } for m in msgs]
    (workdir / "messages.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"消息快照：{workdir / 'messages.json'}")

    # ---- 发送者展示：多人会话才显示名字 ----
    def sender_id(m: dict) -> str:
        s = m.get("sender")
        if isinstance(s, dict):
            return str(s.get("id") or s.get("open_id") or s.get("sender_id") or "")
        return str(s or m.get("sender_name") or "")

    def sender_name(m: dict) -> str:
        s = m.get("sender")
        if isinstance(s, dict):
            return str(s.get("sender_name") or s.get("name") or "")
        return str(s or "")

    multi_sender = len({sender_id(m) for m in msgs if sender_id(m)}) > 1

    # ---- 图注 ----
    captions: dict[str, str] = {}
    if args.captions:
        captions = json.loads(Path(args.captions).read_text(encoding="utf-8"))

    # ---- 正文渲染 ----
    by_id = {m.get("message_id"): m for m in msgs}
    claimed: set[Path] = set()
    body_parts: list[str] = []
    prev_time: str | None = None
    prev_img = False
    ok_img = 0
    cap_no = 0
    for m in msgs:
        pos = m["_pos"]
        t = str(m.get("create_time") or "")[-5:]  # HH:MM
        mtype = m.get("msg_type")
        is_img = mtype == "image"
        cont = is_img and prev_img  # 连发图片：紧凑堆叠
        show_time = t if t != prev_time else ""

        classes = ["msg"]
        if cont:
            classes.append("cont")
        reply_ref = ""
        rid = m.get("reply_to")
        root_id = m.get("root") or m.get("root_id") or m.get("parent_id")
        if rid and rid in by_id:
            classes.append("reply")
            target = by_id[rid]
            tt = str(target.get("create_time") or "")[-5:]
            what = "的图" if target.get("msg_type") == "image" else "那条"
            reply_ref = f"<a class='reply-ref' href='#m{target['_pos']}'>↩ 回复 {tt} {what}</a>"
        elif rid:
            classes.append("reply")
            reply_ref = "<span class='reply-ref'>↩ 回复上一条</span>"
        elif root_id:
            classes.append("reply")
            reply_ref = "<span class='reply-ref'>↩ 话题内</span>"

        who = f"<span class='who'>{html.escape(sender_name(m))}</span>" \
            if multi_sender and sender_name(m) else ""

        if is_img:
            key = extract_image_key(m)
            raw = None
            cached = list(img_dir.glob(f"m{pos}.*"))
            if cached:
                raw = cached[0].read_bytes()
            elif key:
                f = find_resource_file(res_dir, key, claimed)
                if f is not None:
                    raw = f.read_bytes()
                    (img_dir / f"m{pos}{f.suffix}").write_bytes(raw)  # 转存缓存
            if raw is None and key:
                raw = download_image(m["message_id"], key, f"m{pos}", img_dir)
            if raw:
                ok_img += 1
                uri = build_data_uri(raw)
                cls = " class='chain'" if cont else ""
                inner = f"<div class='imgrow'><img{cls} src='{uri}' alt='图片 {t}'></div>"
            else:
                inner = f"<div class='missing'>图片未能下载：{html.escape(key)}</div>"
            cap = captions.get(str(pos)) or captions.get(str(m.get("message_position")))
            if cap:
                cap_no += 1
                inner += f"<p class='imgcap'><b>图{cap_no}</b>{html.escape(cap)}</p>"
        elif mtype in ("text", "post"):
            inner = render_text(m)
            # post 富文本内嵌图：content 里的 ![Image](key) 标记逐张挂接（键 m{pos}e{n} 缓存）
            for n, ekey in enumerate(POST_IMG_RE.findall(str(m.get("content") or "")), 1):
                ename = f"m{pos}e{n}"
                eraw = None
                ecached = list(img_dir.glob(f"{ename}.*"))
                if ecached:
                    eraw = ecached[0].read_bytes()
                else:
                    ef = find_resource_file(res_dir, ekey, claimed)
                    if ef is not None:
                        eraw = ef.read_bytes()
                        (img_dir / f"{ename}{ef.suffix}").write_bytes(eraw)
                if eraw is None:
                    eraw = download_image(m["message_id"], ekey, ename, img_dir)
                if eraw:
                    ok_img += 1
                    n_img += 1
                    inner += (f"<div class='imgrow'><img class='chain' "
                              f"src='{build_data_uri(eraw)}' alt='内嵌图 {t}'></div>")
                    ecap = captions.get(f"{pos}e{n}")
                    if ecap:
                        cap_no += 1
                        inner += f"<p class='imgcap'><b>图{cap_no}</b>{html.escape(ecap)}</p>"
                else:
                    inner += f"<div class='missing'>内嵌图未能获取：{html.escape(ekey)}</div>"
        else:
            inner = render_placeholder(m)

        time_cell = f"<time>{show_time}</time>" if show_time else "<time></time>"
        body_parts.append(
            f"<div class=\"{' '.join(classes)}\" id='m{pos}'>{time_cell}"
            f"<div class='body'>{who}{reply_ref}{inner}</div></div>\n"
        )
        prev_time = t
        prev_img = is_img

    print(f"图片成功下载并内嵌 {ok_img}/{n_img}")

    # ---- 页面组装 ----
    date = t_first[:10] or datetime.now().strftime("%Y-%m-%d")
    try:
        wd = WEEKDAYS[datetime.strptime(date, "%Y-%m-%d").weekday()]
    except ValueError:
        wd = ""
    date_cn = f"{date[:4]} 年 {int(date[5:7])} 月 {int(date[8:10])} 日" + (f" · {wd}" if wd else "")
    span = f"{t_first[-5:]} – {t_last[-5:]}"
    n_text = len(msgs) - n_img
    mode_label = "话题" if thread_mode else ("群聊" if multi_sender else "私聊")
    safe_title = re.sub(r'[\\/:*?"<>|]', "", args.title).strip() or "聊天存档"
    out_html = workdir / f"{date} {safe_title}.html"

    chat_line = html.escape(args.chat_name or (
        f"话题 {args.thread_root}" if thread_mode else str(args.chat_id)))
    range_note = (f"话题 · 根消息 {args.thread_root}" if thread_mode
                  else f"范围：第 {msgs[0]['_pos']} 条起")
    dek = args.dek or f"从 {t_first[-5:]} 到 {t_last[-5:]}，共 {len(msgs)} 条（图 {ok_img} 张）。"
    afterword_html = render_afterword(
        json.loads(Path(args.afterword).read_text(encoding="utf-8"))
        if args.afterword else [])
    if not afterword_html:
        afterword_html = "<p>（未提供编后记。）</p>"

    page = (PAGE_TEMPLATE
            .replace("__TITLE__", html.escape(f"{safe_title}，{span} · 存档"))
            .replace("__CHAT_LINE__", chat_line)
            .replace("__DATE_CN__", date_cn)
            .replace("__SPAN__", span)
            .replace("__STATS__", f"{len(msgs)} 条 · 文本 {n_text} · 图 {ok_img}")
            .replace("__RANGE_NOTE__", html.escape(range_note))
            .replace("__KICKER__", html.escape(f"{date_cn} · 飞书 · {mode_label}"))
            .replace("__DEK__", html.escape(dek))
            .replace("__BODY__", "".join(body_parts))
            .replace("__AFTERWORD__", afterword_html)
            .replace("__FOOTER__",
                     f"lark-cli 导出 · {len(msgs)} 条 · 图片 {ok_img} 张内嵌 · {date}")
            .replace("__LIGHTBOX__", LIGHTBOX_JS)
            .replace("__EDITOR__", EDITOR_JS.replace("__FILENAME__", out_html.name))
            )
    page = page.replace("__CSS__", CSS.replace("__NOISE__", NOISE_SVG))
    out_html.write_text(page, encoding="utf-8")
    print(f"已写出：{out_html}（{out_html.stat().st_size / 1024 / 1024:.1f} MB）")


if __name__ == "__main__":
    main()
