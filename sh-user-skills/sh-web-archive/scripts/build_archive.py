# /// script
# requires-python = ">=3.11"
# dependencies = ["beautifulsoup4"]
# ///
"""网页文章 → 目录形态静态存档（sh-web-archive 确定性管线）。

fetch：匿名抓取无需鉴权的公开网页，正文三级提取 + 资源本地化，
产出 {存档目录}/article.json + assets/。
render：由 article.json（与可选 summary.json）渲染三主 tab 静态页面
index.html + history/ + manifest.json。

职责分离：语义（AI 总结）由模型撰写 summary.json 注入，本脚本只做
确定性渲染。鉴权页（登录墙 / 403 / 站点环境异常）一律拒绝，不做绕过。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, date
from pathlib import Path

from bs4 import BeautifulSoup, Tag

# ---------------- 常量 ----------------

MAX_ASSETS = 300          # 资源下载保护上限，超出保留远程 URL 并警告
GET_TIMEOUT = 30          # 单次请求超时（秒）
RETRY_WAIT = 2            # 失败重试间隔（秒）
MAX_TITLE_LEN = 60        # 目录名标题截断长度
MAX_URL_LEN = 2000        # 输入 URL 长度上限
MIN_TEXT_LEN = 200        # 正文最少字符数，低于则 extract_failed

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

EXT_BY_CT = {
    "image/jpeg": "jpg", "image/png": "png", "image/gif": "gif",
    "image/webp": "webp", "image/svg+xml": "svg", "image/bmp": "bmp",
    "image/avif": "avif", "image/tiff": "tiff", "image/x-icon": "ico",
    "audio/mpeg": "mp3", "audio/mp4": "m4a", "audio/aac": "aac",
    "audio/wav": "wav", "audio/x-wav": "wav", "audio/ogg": "ogg",
    "video/mp4": "mp4", "video/webm": "webm", "video/quicktime": "mov",
}

ATTR_WHITELIST = {
    "img": {"src", "alt"},
    "a": {"href", "target", "rel"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
    "audio": {"src", "controls"},
    "video": {"src", "controls", "poster"},
    "iframe": {"src", "width", "height", "allowfullscreen", "allow"},
}


class ArchiveError(Exception):
    """带分类码的业务失败；code 决定 stderr 提示与退出码。"""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


# ---------------- 基础设施 ----------------

def app_root() -> Path:
    """存档产物根目录：~\\agents-skills\\sh-web-archive\\（用户主目录下）。

    位置变更记录：最初用 %APPDATA%\\agents-skills\\，但 Chrome 的
    showDirectoryPicker 拒绝选择带隐藏属性目录链（AppData 默认 Hidden，
    报"包含系统文件"），无法完成编辑授权，故移到用户主目录。
    """
    return Path.home() / "agents-skills" / "sh-web-archive"


def log(msg: str) -> None:
    print(msg, flush=True)


def http_get(url: str, timeout: int = GET_TIMEOUT) -> tuple[int, bytes]:
    """匿名 GET（浏览器 UA、无 Cookie、无 Referer）。

    返回 (status, body)；HTTP 错误码原样返回给调用方分类，
    网络层失败抛 ArchiveError("network")。
    """
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,image/*,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() or b""
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
        raise ArchiveError("network", f"网络请求失败：{url}（{e}）") from e


def get_with_retry(url: str) -> tuple[int, bytes]:
    """网络错误/5xx 重试 1 次；4xx 鉴权类不重试。"""
    for attempt in range(2):
        try:
            status, body = http_get(url)
            if status < 500:
                return status, body
            last = (status, body)
        except ArchiveError as e:
            last = (0, str(e).encode())
        if attempt == 0:
            time.sleep(RETRY_WAIT)
    return last


def decode_html(body: bytes, resp_ct: str = "") -> str:
    """按 Content-Type > meta charset > utf-8 解码。"""
    m = re.search(r"charset=([\w-]+)", resp_ct or "", re.I)
    candidates = [m.group(1)] if m else []
    head = body[:2048].decode("ascii", errors="ignore")
    m2 = re.search(r'charset=["\']?([\w-]+)', head, re.I)
    if m2:
        candidates.append(m2.group(1))
    candidates.append("utf-8")
    for enc in candidates:
        try:
            return body.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", errors="replace")


def sanitize_title(raw: str) -> str:
    """目录名标题清洗：非法字符 → _，去结尾点/空格，截 60 字符。"""
    t = re.sub(r'[\\/:*?"<>|]', "_", raw.strip())
    t = re.sub(r"\s+", " ", t)
    t = t.rstrip(" .")
    return t[:MAX_TITLE_LEN].rstrip(" .")


# ---------------- Cloudflare 邮箱保护还原 ----------------

def _cfemail_decode(hexdata: str) -> str:
    """Cloudflare 邮箱保护解码：首字节为异或密钥，其余逐字节异或得明文。"""
    try:
        raw = bytes.fromhex(hexdata)
    except ValueError:
        return ""
    if not raw:
        return ""
    key = raw[0]
    return "".join(chr(b ^ key) for b in raw[1:])


def decode_cfemail(soup: BeautifulSoup) -> int:
    """把 Cloudflare 邮箱保护锚点还原为明文文本节点。

    覆盖两种形态：data-cfemail 属性（现行）、
    href="/cdn-cgi/l/email-protection#hex" 片段（旧式）。
    无编码数据的锚点不动（无法还原，留给后续 localize/清理）。
    返回还原数量。
    """
    n = 0
    for a in list(soup.find_all("a")):
        hexdata = a.get("data-cfemail") or ""
        href = a.get("href") or ""
        if not hexdata and "/cdn-cgi/l/email-protection#" in href:
            hexdata = href.split("#", 1)[1]
        if not hexdata:
            continue
        plain = _cfemail_decode(hexdata)
        if plain:
            a.replace_with(plain)
            n += 1
    return n


# ---------------- 正文提取（三级） ----------------

def extract_content(soup: BeautifulSoup, page_url: str) -> Tag:
    """三级提取：微信特化 → article/main/[role=main] → 文本密度最大 div。"""
    node = soup.select_one("#js_content")
    if node:
        return node
    for sel in ("article", "main", "[role=main]"):
        node = soup.select_one(sel)
        if node:
            return node
    best, best_score = None, 0.0
    for div in soup.find_all(["div", "section", "td"]):
        text_len = len(div.get_text(" ", strip=True))
        if text_len < MIN_TEXT_LEN:
            continue
        n_elems = max(1, len(div.find_all(True)))
        score = text_len / n_elems
        if score > best_score:
            best, best_score = div, score
    if best:
        return best
    raise ArchiveError("extract_failed",
                       "正文提取失败（文本量过少）：页面可能由 JS 渲染（SPA），"
                       "本工具不做无头浏览器。")


def looks_like_login_wall(soup: BeautifulSoup, page_url: str) -> bool:
    if soup.find("input", attrs={"type": "password"}):
        return True
    host_path = (urllib.parse.urlparse(page_url).netloc +
                 urllib.parse.urlparse(page_url).path).lower()
    return ("login" in host_path) or ("passport" in host_path)


def looks_like_blocked(soup: BeautifulSoup) -> bool:
    text = soup.get_text(" ", strip=True)
    for kw in ("环境异常", "操作频繁", "去验证", "完成验证后", "访问过于频繁"):
        if kw in text:
            return True
    return False


# ---------------- 资源下载与正文改写 ----------------

def guess_ext(url: str, data: bytes | None = None) -> str:
    m = re.search(r"wx_fmt=(\w+)", url)
    if m:
        return m.group(1).lower()[:5]
    path = urllib.parse.urlparse(url).path
    m = re.search(r"\.([A-Za-z0-9]{2,5})$", path)
    if m:
        return m.group(1).lower()
    if data:
        if data[:3] == b"\xff\xd8\xff":
            return "jpg"
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return "png"
        if data[:4] in (b"GIF8",):
            return "gif"
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "webp"
        if data[:2] == b"BM":
            return "bmp"
        if data[:3] == b"ID3" or (len(data) > 2 and data[0] == 0xFF and data[1] & 0xE0):
            return "mp3"
        if len(data) > 12 and data[4:8] == b"ftyp":
            return "mp4"
        if data[:5] == b"<?xml" or data[:4] == b"<svg":
            return "svg"
    return "bin"


def download_asset(url: str, dest: Path) -> bool:
    """下载单个资源：失败重试 1 次，仍失败返回 False（不中断）。"""
    for attempt in range(2):
        try:
            status, data = http_get(url)
            if status == 200 and data:
                dest.write_bytes(data)
                return True
        except ArchiveError:
            pass
        if attempt == 0:
            time.sleep(RETRY_WAIT)
    return False


def abs_url(raw: str, page_url: str) -> str:
    raw = (raw or "").strip()
    if raw.startswith("//"):
        return "https:" + raw
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    return urllib.parse.urljoin(page_url, raw)


class AssetLocalizer:
    """资源统一本地化：img / audio / video / 微信 mpvoice / iframe 提示。"""

    def __init__(self, soup: BeautifulSoup, assets_dir: Path, page_url: str):
        self.soup = soup
        self.assets_dir = assets_dir
        self.page_url = page_url
        self.assets: list[dict] = []
        self.counters = {"img": 0, "aud": 0, "vid": 0}
        self.warnings: list[str] = []

    def _next_name(self, kind: str, ext: str) -> str:
        self.counters[kind] += 1
        return f"{kind}-{self.counters[kind]:03d}.{ext}"

    def _record(self, file: str | None, kind: str, ok: bool, url: str,
                note: str = "") -> None:
        item = {"file": file, "kind": kind, "ok": ok, "url": url}
        if note:
            item["note"] = note
        self.assets.append(item)

    def _download(self, url: str, kind: str) -> tuple[str, bool]:
        """下载并落盘；返回 (相对引用, ok)。受 MAX_ASSETS 保护。"""
        if sum(self.counters.values()) >= MAX_ASSETS:
            self.warnings.append(f"资源数达到上限 {MAX_ASSETS}，保留远程 URL：{url[:90]}")
            self._record(None, kind, False, url, note="over_limit")
            return url, False
        status, data = (200, b"")
        try:
            status, data = http_get(url)
        except ArchiveError:
            pass
        ext = guess_ext(url, data if data else None)
        name = self._next_name(kind, ext)
        if status == 200 and data:
            (self.assets_dir / name).write_bytes(data)
            self._record(f"assets/{name}", kind, True, url)
            return f"assets/{name}", True
        time.sleep(RETRY_WAIT)
        try:
            status, data = http_get(url)
        except ArchiveError:
            data = b""
        if status == 200 and data:
            if guess_ext(url) != ext:
                ext = guess_ext(url, data)
                name = self._next_name(kind, ext)  # 重下重命名场景极少见
            (self.assets_dir / name).write_bytes(data)
            self._record(f"assets/{name}", kind, True, url)
            return f"assets/{name}", True
        ext2 = guess_ext(url, data if data else None)
        if ext2 != ext:
            name = self._next_name(kind, ext2)
        self.warnings.append(f"资源下载失败（保留远程 URL）：{url[:90]}")
        self._record(f"assets/{name}", kind, False, url, note="download_failed")
        return url, False

    def localize(self, node: Tag) -> None:
        # 噪声标签剔除（iframe 除外，后续单独处理）
        for t in node.find_all(["script", "style", "noscript", "svg", "button",
                                "input", "form", "link", "meta", "textarea",
                                "select", "canvas", "map", "object", "embed"]):
            t.decompose()
        # 隐藏元素剔除（微信正文含大量 display:none 的排序占位）
        for t in node.find_all(style=re.compile(
                r"display\s*:\s*none|visibility\s*:\s*hidden", re.I)):
            t.decompose()
        # 图片：data-src / data-original 优先（全站统一懒加载规则）
        for img in node.find_all("img"):
            raw = (img.get("data-src") or img.get("data-original")
                   or img.get("src") or "")
            src = abs_url(raw, self.page_url)
            alt = (img.get("alt") or "").strip()
            if not src or src.startswith("data:") or src.startswith("blob:"):
                img.decompose()
                continue
            local, ok = self._download(src, "img")
            attrs = {"src": local}
            if alt:
                attrs["alt"] = alt
            if not ok:
                attrs["class"] = "arch-miss"
                attrs["data-arch-url"] = src
            img.attrs = attrs
        # 微信语音 mpvoice → getvoice 端点 → <audio controls>
        for mv in node.find_all("mpvoice"):
            digest = (mv.get("voice_encode_file_digest")
                      or mv.get("voice_id") or "").strip()
            if not digest:
                mv.decompose()
                continue
            url = f"https://res.wx.qq.com/voice/getvoice?mediaid={digest}"
            local, ok = self._download(url, "aud")
            aud = self.soup.new_tag("audio")
            aud.attrs = {"src": local, "controls": ""}
            if not ok:
                aud.attrs["class"] = "arch-miss"
                aud.attrs["data-arch-url"] = url
            mv.replace_with(aud)
        # audio / video：取自身或子 source 的 src
        for av in node.find_all(["audio", "video"]):
            src_tag = av.find("source")
            raw = av.get("src") or (src_tag.get("src") if src_tag else "") or ""
            if src_tag:
                src_tag.decompose()
            if not raw:
                av.decompose()
                continue
            src = abs_url(raw, self.page_url)
            kind = "vid" if av.name == "video" else "aud"
            local, ok = self._download(src, kind)
            attrs = {k: av.get(k) for k in ("width", "height", "poster")
                     if av.get(k)}
            attrs["src"] = local
            attrs["controls"] = ""
            if not ok:
                attrs["class"] = "arch-miss"
                attrs["data-arch-url"] = src
            av.attrs = attrs
        # iframe：不下载，补全 https: 原样保留 + 在线提示；
        # 微信嵌套文章卡片（src 指向公众号文章页，file:// 下必被
        # X-Frame-Options 拦成空白框）替换为明确的引用链接卡片
        video_hosts = ("v.qq.com", "youtube.com", "youtu.be", "bilibili.com",
                       "b23.tv", "ixigua.com", "player.", "video.")
        for fr in node.find_all("iframe"):
            src = abs_url(fr.get("src") or "", self.page_url)
            box = self.soup.new_tag("div")
            note = self.soup.new_tag("span")
            if src and "mp.weixin.qq.com" in (urllib.parse.urlparse(src).netloc) \
                    and re.search(r"/s(/|\?|$)", src):
                a = self.soup.new_tag("a")
                a.attrs = {"href": src, "target": "_blank",
                           "rel": "noreferrer"}
                a.string = "嵌入引用的微信文章（点击打开原文）"
                box["class"] = "arch-refcard"
                box.append(a)
            elif src:
                box["class"] = "online-embed"
                nf = self.soup.new_tag("iframe")
                nf.attrs = {"src": src, "allowfullscreen": ""}
                box.append(nf)
                host = urllib.parse.urlparse(src).netloc
                note["class"] = "embed-note"
                note.string = ("在线视频，需联网播放"
                               if any(v in host for v in video_hosts)
                               else "在线嵌入内容，需联网加载")
                box.append(note)
            fr.replace_with(box)
        # 链接：javascript:/空 href 解包成纯文本，外链新窗口打开
        for a in list(node.find_all("a")):
            href = (a.get("href") or "").strip()
            if not href or href.startswith(("javascript:", "#")):
                a.unwrap()
            else:
                a.attrs = {"href": href, "target": "_blank",
                           "rel": "noreferrer"}
        # 属性白名单清理（保结构，丢内联样式与追踪类名）
        for tag in node.find_all(True):
            keep = ATTR_WHITELIST.get(tag.name)
            tag.attrs = ({k: v for k, v in tag.attrs.items() if k in keep}
                         if keep else {})


# ---------------- fetch 子命令 ----------------

def fetch_meta(soup: BeautifulSoup, page_url: str) -> dict:
    def meta_content(prop: str) -> str:
        tag = soup.find("meta", attrs={"property": prop}) or \
            soup.find("meta", attrs={"name": prop})
        return (tag.get("content") or "").strip() if tag else ""

    title = (meta_content("og:title")
             or (soup.select_one("#activity-name").get_text(strip=True)
                 if soup.select_one("#activity-name") else "")
             or (soup.title.get_text(strip=True) if soup.title else ""))
    title = re.sub(r"\s+", " ", title).strip()
    author = (meta_content("og:article:author")
              or (soup.select_one("#js_name").get_text(strip=True)
                  if soup.select_one("#js_name") else ""))
    publish_time = (meta_content("og:article:published_time")
                    or (soup.select_one("em#publish_time").get_text(strip=True)
                        if soup.select_one("em#publish_time") else ""))
    if not publish_time:
        # 微信正文模板把时间藏在 JS 变量里：createTime='...' 或 var ct=Unix 秒
        m = re.search(r"createTime\s*=\s*['\"]([^'\"]+)['\"]", str(soup))
        if m:
            publish_time = m.group(1).strip()
        else:
            m = re.search(r'var\s+ct\s*=\s*["\'](\d{9,13})["\']', str(soup))
            if m:
                ts = int(m.group(1))
                if ts > 10**12:
                    ts //= 1000
                publish_time = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    host = urllib.parse.urlparse(page_url).netloc
    site = "微信公众号" if host == "mp.weixin.qq.com" else host
    return {
        "title": title,
        "author": author,
        "publish_time": publish_time,
        "url": page_url,
        "site": site,
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def cmd_fetch(args: argparse.Namespace) -> None:
    url = (args.url or "").strip()
    scheme = urllib.parse.urlparse(url).scheme
    if scheme not in ("http", "https") or len(url) >= MAX_URL_LEN:
        raise ArchiveError("bad_url",
                           f"URL 不合法（需 http/https 且长度 < {MAX_URL_LEN}）：{url[:80]}")

    log(f"匿名 GET {url}")
    status, body = get_with_retry(url)
    if status in (401, 403):
        raise ArchiveError("auth_required",
                           f"HTTP {status}：该页面需要鉴权，按约定拒绝存档（不做绕过）。")
    if status != 200:
        raise ArchiveError("fetch_failed", f"HTTP {status}：页面获取失败：{url}")

    ct = ""
    html = decode_html(body, ct)
    soup = BeautifulSoup(html, "html.parser")
    n_cf = decode_cfemail(soup)
    if n_cf:
        log(f"Cloudflare 邮箱保护：已还原 {n_cf} 处明文")

    content = extract_content(soup, url)
    text = re.sub(r"\n{3,}", "\n\n", content.get_text("\n", strip=True))
    if len(text) < MIN_TEXT_LEN:
        if looks_like_login_wall(soup, url):
            raise ArchiveError("login_wall",
                               "检测到登录墙（密码输入框或登录 URL 特征），拒绝存档。")
        if looks_like_blocked(soup):
            raise ArchiveError("blocked_by_site",
                               "站点返回环境异常/验证提示页，拒绝存档。")
        raise ArchiveError("extract_failed",
                           f"正文不足 {MIN_TEXT_LEN} 字：页面可能由 JS 渲染（SPA），"
                           "或需要鉴权。本工具不做无头浏览器。")

    meta = fetch_meta(soup, url)
    dir_name = args.dir or f"{date.today().isoformat()} {sanitize_title(args.title or meta['title'])}"
    if not dir_name:
        raise ArchiveError("bad_url", "无法确定目录名：标题为空，请用 --title/--dir 指定。")
    target = app_root() / dir_name
    if target.exists():
        raise ArchiveError("dir_exists",
                           f"目录已存在，防覆盖编辑产物拒绝写入：{target}\n"
                           "换用 --dir 指定其他名字。")
    assets_dir = target / "assets"
    assets_dir.mkdir(parents=True)
    log(f"存档目录：{target}")

    loc = AssetLocalizer(soup, assets_dir, url)
    loc.localize(content)
    # 正文根节点自身的属性一并清理（如微信 #js_content 的
    # style="visibility:hidden; opacity:0" 淡入初始态会让全文在存档里不可见）
    content.attrs = {}
    for w in loc.warnings:
        log(f"警告：{w}")

    content_html = content.decode()
    article = {
        "meta": meta,
        "content_html": content_html,
        "assets": loc.assets,
        "text": text,
    }
    (target / "article.json").write_text(
        json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8")

    ok_n = sum(1 for a in loc.assets if a["ok"])
    fail_n = len(loc.assets) - ok_n
    log(f"抓取完成：标题《{meta['title']}》 作者 {meta['author'] or '未知'} "
        f"时间 {meta['publish_time'] or '未知'}")
    log(f"资源：成功 {ok_n} / 失败 {fail_n} / 共 {len(loc.assets)}")
    log(f"正文：{len(text)} 字")


# ---------------- render：summary 校验与渲染 ----------------

CN_NUM = "一二三四五六七八九十"
CN_TAB = {"original": "原文", "summary": "AI 总结", "scratch": "可编辑页面"}
CN_OBJECT = {"original": "原文转录", "summary": "AI 总结", "scratch": "自由页"}
SUMMARY_PLACEHOLDER = ('<p class="sum-placeholder">总结待生成：由模型通读原文撰写 '
                       'summary.json 后重跑 render 注入本栏。</p>')
SCRATCH_GUIDE = ('<p>此页可自由编辑：记录你的批注、补充与想法。</p>'
                 '<p>在下方选择编辑对象（原文转录 / AI 总结 / 自由页），每次保存'
                 '生成一个不可变历史版本；左侧「可编辑页面」的子 tab 是全部编辑'
                 '动作的时间线。</p>')


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def validate_summary(data, src: str) -> dict:
    """校验 summary.json；违规报出具体 JSON 路径（$.sections[i].x）。"""

    def fail(path: str, why: str):
        raise ArchiveError("bad_summary", f"{src} {path}: {why}")

    if not isinstance(data, dict):
        fail("$", "必须是 JSON 对象")
    one = data.get("one_liner")
    if not isinstance(one, str) or not one.strip():
        fail("$.one_liner", "必填且为非空字符串")
    if len(one.strip()) > 60:
        fail("$.one_liner", f"超长（{len(one.strip())} 字 > 60）")
    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        fail("$.sections", "必须是非空数组")
    for i, sec in enumerate(sections):
        base = f"$.sections[{i}]"
        if not isinstance(sec, dict):
            fail(base, "必须是对象")
        t = sec.get("title")
        if not isinstance(t, str) or not t.strip():
            fail(f"{base}.title", "必填且为非空字符串")
        paras = sec.get("paragraphs")
        if (not isinstance(paras, list) or not paras
                or not all(isinstance(p, str) and p.strip() for p in paras)):
            fail(f"{base}.paragraphs", "必须是非空字符串数组")
        for opt in ("quote", "quote_ref"):
            v = sec.get(opt)
            if v is not None and not isinstance(v, str):
                fail(f"{base}.{opt}", "必须是字符串")
    return data


def render_summary_html(s: dict) -> str:
    parts = [f'<p class="sum-oneliner">{esc(s["one_liner"].strip())}</p>']
    for i, sec in enumerate(s["sections"]):
        num = CN_NUM[i] if i < len(CN_NUM) else str(i + 1)
        parts.append('<section class="sum-sec">')
        parts.append(f'<h3><span class="sec-num">{num}、</span>'
                     f'{esc(sec["title"].strip())}</h3>')
        for p in sec["paragraphs"]:
            parts.append(f"<p>{esc(p.strip())}</p>")
        if (sec.get("quote") or "").strip():
            parts.append("<blockquote><p>"
                         + esc(sec["quote"].strip()) + "</p>")
            if (sec.get("quote_ref") or "").strip():
                parts.append(f'<cite>—— {esc(sec["quote_ref"].strip())}</cite>')
            parts.append("</blockquote>")
        parts.append("</section>")
    return "".join(parts)


# ---------------- render：index.html 模板 ----------------

INDEX_TEMPLATE = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ · 网页存档</title>
<style>
:root{
  --paper:#f6f3ec; --ink:#2f2a24; --vermilion:#a23c2a; --hairline:#d9d2c0;
  --meta:#8b8474; --wash:#efe9db;
  --serif:"Source Han Serif SC","Noto Serif CJK SC","Songti SC","SimSun",serif;
  --mono:"Cascadia Mono",Consolas,"Courier New",monospace;
}
*{box-sizing:border-box}
html{background:var(--paper)}
body{
  margin:0; color:var(--ink); font-family:var(--serif); font-size:16px;
  line-height:1.85;
  background-image:url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20width='160'%20height='160'%3E%3Cfilter%20id='n'%3E%3CfeTurbulence%20type='fractalNoise'%20baseFrequency='0.8'%20numOctaves='2'/%3E%3CfeColorMatrix%20type='saturate'%20values='0'/%3E%3C/filter%3E%3Crect%20width='160'%20height='160'%20filter='url(%23n)'%20opacity='0.05'/%3E%3C/svg%3E");
}
a{color:var(--vermilion)}
h1,h2,h3,h4{line-height:1.4}
blockquote{margin:1em 0;padding:.2em 1em;border-left:3px solid var(--vermilion);color:#5a5348}
blockquote p{margin:.4em 0}
pre{background:var(--wash);padding:.9em 1em;overflow-x:auto;font-family:var(--mono);font-size:.85em;line-height:1.6}
code{font-family:var(--mono);font-size:.9em;background:var(--wash);padding:0 .3em}
pre code{background:none;padding:0}
table{border-collapse:collapse;margin:1em 0;max-width:100%}
th,td{border:1px solid var(--hairline);padding:.4em .7em;font-size:.92em}
th{background:var(--wash)}
img{max-width:100%;height:auto}
/* ---- 布局：左侧 rail + 右侧主文（非对称） ---- */
#rail{position:fixed;top:0;bottom:0;left:0;width:300px;padding:30px 24px;
  border-right:1px solid var(--hairline);overflow-y:auto}
#rail h1{font-size:19px;margin:0 0 .4em}
#rail .rail-sub{color:var(--meta);font-size:13px;margin:.2em 0}
#rail .rail-link{font-size:13px;margin:.6em 0 0}
#rail .rail-link a{font-family:var(--mono);font-size:12px}
#tabs{margin-top:26px;display:flex;flex-direction:column;gap:2px}
.tabbtn{all:unset;cursor:pointer;font-family:var(--serif);font-size:15px;
  padding:7px 12px;border-left:3px solid transparent;color:#5a5348}
.tabbtn:hover{color:var(--vermilion)}
.tabbtn.active{border-left-color:var(--vermilion);color:var(--vermilion);font-weight:700}
#subtabs{margin-top:16px;display:flex;flex-wrap:wrap;gap:6px}
.subtab{all:unset;cursor:pointer;font-family:var(--mono);font-size:11px;
  padding:3px 8px;border:1px solid var(--hairline);color:#5a5348;background:rgba(255,255,255,.35)}
.subtab:hover{border-color:var(--vermilion);color:var(--vermilion)}
.subtab.active{border-color:var(--vermilion);color:var(--vermilion);font-weight:700}
.sub-empty{color:var(--meta);font-size:12px;font-family:var(--mono)}
#perm-status{margin-top:22px;font-size:12px;color:var(--meta);line-height:1.7}
#perm-status button{all:unset;cursor:pointer;font-family:var(--mono);font-size:12px;
  border:1px solid var(--vermilion);color:var(--vermilion);padding:4px 10px;margin-top:6px}
#main{margin-left:340px;max-width:800px;padding:44px 36px 90px}
section[data-tab]{display:none}
.js-on section[data-tab].active{display:block}
.viewing-bar{font-family:var(--mono);font-size:12px;color:var(--vermilion);
  border:1px dashed var(--vermilion);padding:6px 12px;margin-bottom:18px;
  display:flex;gap:14px;align-items:center}
.viewing-bar button{all:unset;cursor:pointer;text-decoration:underline}
.noscript-note{margin:14px 340px 0 24px;font-size:13px;color:var(--vermilion);border:1px dashed var(--vermilion);padding:6px 12px}
/* ---- 原文 ---- */
#sec-original{font-size:16.5px}
#sec-original h1{font-size:24px}#sec-original h2{font-size:21px}
.arch-refcard{border-left:3px solid var(--vermilion);background:var(--wash);
  padding:10px 14px;margin:1em 0;font-size:14px}
.miss-box{border:1px dashed var(--meta);color:var(--meta);padding:14px;
  margin:1em 0;font-size:13px;font-family:var(--mono);text-align:center}
.online-embed{margin:1em 0}
.online-embed iframe{width:100%;aspect-ratio:16/9;border:0}
.embed-note{display:block;font-family:var(--mono);font-size:11px;color:var(--meta);margin-top:4px}
audio{width:100%;margin:.6em 0}
/* ---- AI 总结 ---- */
#sec-summary .sum-oneliner{font-size:18px;border-bottom:1px solid var(--hairline);
  padding-bottom:1em;color:#5a5348}
#sec-summary .sum-sec{margin-top:1.6em}
#sec-summary h3{font-size:17px;margin:0 0 .5em}
#sec-summary .sec-num{color:var(--vermilion);font-weight:700}
#sec-summary cite{display:block;margin-top:.5em;font-size:13px;color:var(--meta);font-style:normal}
.sum-placeholder{color:var(--meta);border:1px dashed var(--hairline);padding:18px;font-size:14px}
/* ---- 可编辑页面 ---- */
.editor{margin-top:1em}
.ed-toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;
  border:1px solid var(--hairline);background:var(--wash);padding:8px 12px}
.ed-toolbar select{font-family:var(--serif);font-size:14px;padding:3px 6px}
.ed-toolbar button{all:unset;cursor:pointer;font-size:13px;padding:4px 12px;border:1px solid var(--ink)}
.ed-toolbar button.primary{border-color:var(--vermilion);color:var(--vermilion)}
.ed-toolbar button:disabled{opacity:.4;cursor:not-allowed}
#ed-note{font-size:12px;color:var(--meta);font-family:var(--mono)}
#editor{min-height:220px;border:1px solid var(--hairline);border-top:0;
  padding:20px 24px;background:rgba(255,255,255,.45);outline:none}
#editor:focus{border-color:var(--vermilion)}
.scratch-guide{color:#5a5348}
/* ---- 其他 ---- */
#foot{margin-top:70px;border-top:1px solid var(--hairline);padding-top:14px;
  font-size:12px;color:var(--meta);font-family:var(--mono)}
#lb{display:none;position:fixed;inset:0;background:rgba(20,16,12,.86);
  z-index:50;cursor:zoom-out;align-items:center;justify-content:center}
#lb.on{display:flex}
#lb img{max-width:94vw;max-height:94vh}
#toast{position:fixed;left:340px;bottom:26px;background:#2f2a24;color:#f6f3ec;
  font-size:13px;font-family:var(--mono);padding:9px 16px;display:none;z-index:60}
@media (max-width:900px){
  #rail{position:static;width:auto;border-right:0;border-bottom:1px solid var(--hairline)}
  #main{margin-left:0;padding:28px 18px 70px}
  #toast{left:16px}
  .noscript-note{margin:14px 18px 0}
}
</style>
</head>
<body>
<noscript><p class="noscript-note">JavaScript 已禁用：以下为三栏纵向全展的静态内容，编辑与历史功能不可用。</p></noscript>
<aside id="rail">
  <h1>__TITLE__</h1>
  <p class="rail-sub" id="rail-author">__AUTHOR__</p>
  <p class="rail-sub" id="rail-time">__PUBLISH__</p>
  <p class="rail-sub" id="rail-site">__SITE__</p>
  <p class="rail-link"><a href="__URL__" target="_blank" rel="noreferrer">原文链接</a></p>
  <p class="rail-sub" id="rail-assets">__ASSET_STAT__</p>
  <nav id="tabs">
    <button class="tabbtn active" data-tab="original">原文</button>
    <button class="tabbtn" data-tab="summary">AI 总结</button>
    <button class="tabbtn" data-tab="scratch">可编辑页面</button>
  </nav>
  <div id="subtabs"></div>
  <div id="perm-status"></div>
</aside>
<main id="main">
  <section data-tab="original" class="active content" id="sec-original">__ORIGINAL_HTML__</section>
  <section data-tab="summary" id="sec-summary">__SUMMARY_HTML__</section>
  <section data-tab="scratch" id="sec-scratch">
    <div class="scratch-guide" id="scratch-content">__SCRATCH_HTML__</div>
    <div class="editor">
      <div class="ed-toolbar">
        <label for="edit-target">编辑对象</label>
        <select id="edit-target">
          <option value="scratch">自由页</option>
          <option value="original">原文转录</option>
          <option value="summary">AI 总结</option>
        </select>
        <button id="ed-save" class="primary">保存新版本</button>
        <button id="ed-cancel">放弃修改</button>
        <span id="ed-note"></span>
      </div>
      <div id="editor" contenteditable="true"></div>
    </div>
  </section>
  <footer id="foot">__FOOT__</footer>
</main>
<div id="lb"><img alt=""></div>
<div id="toast"></div>
<script type="application/json" id="arch-meta">__META_JSON__</script>
<script type="application/json" id="arch-manifest">__MANIFEST_JSON__</script>
<script>
(function(){
"use strict";
function jget(id){try{return JSON.parse(document.getElementById(id).textContent);}catch(e){return {};}}
var META = jget("arch-meta");
var manifest = jget("arch-manifest");
manifest.tabs = manifest.tabs || {}; manifest.actions = manifest.actions || [];
var TABS = ["original","summary","scratch"];
var CN = {original:"原文",summary:"AI 总结",scratch:"自由页"};
var canFSA = !!(window.showDirectoryPicker && window.indexedDB);
var state = {tab:"original", dir:null, permHandle:null, viewing:{tab:null,file:null},
  content:{original:null,summary:null,scratch:null}};
TABS.forEach(function(t){
  if (t === "scratch"){
    /* 自由页内容与其编辑器分离，避免编辑器把自身嵌套进内容 */
    state.content[t] = $("#scratch-content") ? $("#scratch-content").innerHTML : "";
  } else {
    var sec = document.getElementById("sec-"+t);
    state.content[t] = sec ? sec.innerHTML : "";
  }
});
document.body.classList.add("js-on");

function $(s,r){return (r||document).querySelector(s);}
function sectionEl(t){return document.getElementById("sec-"+t);}
function toast(msg){var t=$("#toast");t.textContent=msg;t.style.display="block";
  clearTimeout(t._h);t._h=setTimeout(function(){t.style.display="none";},3200);}

/* ---------- tab 切换 ---------- */
function setTab(tab){
  if (state.viewing.tab && state.viewing.tab !== tab) backToLatest(state.viewing.tab);
  state.tab = tab;
  document.querySelectorAll(".tabbtn").forEach(function(b){
    b.classList.toggle("active", b.dataset.tab === tab);});
  TABS.forEach(function(t){sectionEl(t).classList.toggle("active", t === tab);});
  renderSubtabs(tab);
}
document.querySelectorAll(".tabbtn").forEach(function(b){
  b.addEventListener("click", function(){setTab(b.dataset.tab);});});

/* ---------- 子 tab 行（原文/总结=版本列表；可编辑页=动作时间线） ---------- */
function hhmm(ts){var d=(ts||"").replace(/\D/g,"");
  return d.length >= 12 ? d.slice(8,10)+":"+d.slice(10,12) : ts;}
function versionNo(tab,file){
  var lst = manifest.tabs[tab]||[];
  for (var i=0;i<lst.length;i++) if (lst[i].file===file) return lst.length-i;
  return null;
}
function renderSubtabs(tab){
  var box = $("#subtabs"); if(!box) return;
  if (tab === "scratch"){
    var acts = manifest.actions||[];
    if (!acts.length){box.innerHTML='<span class="sub-empty">暂无编辑动作</span>';return;}
    box.innerHTML = acts.map(function(a){
      return '<button class="subtab" data-act="1" data-tab="'+a.tab+'" data-ts="'+a.ts+'" data-file="'+a.file+
        '" title="'+a.tab+' '+a.ts+'">'+hhmm(a.ts)+' 编辑了 '+CN[a.tab]+'</button>';}).join("");
    box.querySelectorAll(".subtab").forEach(function(b){
      b.addEventListener("click", function(){jumpAction(b.dataset);});});
    return;
  }
  var lst = manifest.tabs[tab]||[];
  if (!lst.length){box.innerHTML='<span class="sub-empty">暂无版本</span>';return;}
  box.innerHTML = lst.map(function(e,i){
    var vn = lst.length-i;
    var on = (state.viewing.tab===tab) ? (state.viewing.file===e.file) : (i===0);
    return '<button class="subtab'+(on?" active":"")+'" data-file="'+e.file+
      '" title="'+tab+' '+e.ts+'">v'+vn+" · "+hhmm(e.ts)+'</button>';}).join("");
  box.querySelectorAll(".subtab").forEach(function(b){
    b.addEventListener("click", function(){
      viewVersion(tab, b.dataset.file);});});
}
function jumpAction(ds){
  var tab = ds.tab;
  if (tab === "scratch"){
    setTab("scratch");
    loadIntoEditor("scratch", ds.file);
    toast("已把自由页历史版本载入编辑器（不会自动保存）");
  } else {
    setTab(tab);
    viewVersion(tab, ds.file);
  }
}

/* ---------- 历史版本只读查看 ---------- */
function showViewingBar(tab, vn){
  hideViewingBar();
  var bar = document.createElement("div");
  bar.className = "viewing-bar"; bar.id = "viewing-bar";
  bar.innerHTML = "<span>正在查看历史版本 v"+vn+"（只读）</span>";
  var btn = document.createElement("button"); btn.textContent = "回到最新";
  btn.addEventListener("click", function(){backToLatest(tab);});
  bar.appendChild(btn);
  sectionEl(tab).insertBefore(bar, sectionEl(tab).firstChild);
}
function hideViewingBar(){var b=$("#viewing-bar"); if(b) b.remove();}
function backToLatest(tab){
  state.viewing = {tab:null,file:null};
  hideViewingBar();
  if (tab === "scratch"){
    $("#scratch-content").innerHTML = state.content[tab];
  } else {
    sectionEl(tab).innerHTML = state.content[tab];
    processMisses(sectionEl(tab));
  }
  renderSubtabs(tab);
}
function readArchText(path){
  if (!state.dir) return Promise.reject(new Error("尚未连接存档目录"));
  var parts = path.split("/");
  var root = Promise.resolve(state.dir);
  for (var i=0;i<parts.length-1;i++){(function(name){
    root = root.then(function(d){return d.getDirectoryHandle(name);});})(parts[i]);}
  return root.then(function(d){
    return d.getFileHandle(parts[parts.length-1]);
  }).then(function(f){return f.getFile();}).then(function(f){return f.text();});
}
function viewVersion(tab, file){
  var vn = versionNo(tab, file);
  readArchText("history/"+file).then(function(txt){
    state.viewing = {tab:tab,file:file};
    sectionEl(tab).innerHTML = txt;
    processMisses(sectionEl(tab));
    showViewingBar(tab, vn);
    renderSubtabs(tab);
  }).catch(function(e){toast("读取历史版本失败："+e.message);});
}

/* ---------- 失败媒体占位 / lightbox ---------- */
function processMisses(root){
  (root||document).querySelectorAll(".arch-miss").forEach(function(el){
    if (el.closest(".miss-box")) return;
    var url = el.getAttribute("data-arch-url")||"";
    var box = document.createElement("div"); box.className = "miss-box";
    box.textContent = "此资源未能本地化";
    if (url){
      var a = document.createElement("a");
      a.href = url.replace(/"/g,"%22"); a.target="_blank"; a.rel="noreferrer";
      a.textContent = "查看原文资源"; box.appendChild(document.createTextNode(" · ")); box.appendChild(a);
    }
    el.replaceWith(box);
  });
}
$("#lb").addEventListener("click", function(){$("#lb").classList.remove("on");});
document.addEventListener("click", function(ev){
  var img = ev.target;
  if (img.tagName !== "IMG" || img.closest("#lb") || img.closest("#editor")) return;
  if (img.closest(".miss-box")) return;
  if (!img.src || img.src.indexOf("file:") !== 0) return;
  $("#lb img").src = img.src; $("#lb").classList.add("on");
});

/* ---------- IndexedDB：directory handle 持久化 ---------- */
function idb(){return new Promise(function(res,rej){
  var r = indexedDB.open("sh-web-archive", 1);
  r.onupgradeneeded = function(){r.result.createObjectStore("handles");};
  r.onsuccess = function(){res(r.result);}; r.onerror = function(){rej(r.error);};});}
function idbGet(key){return idb().then(function(db){return new Promise(function(res,rej){
  var tx = db.transaction("handles","readonly"); var rq = tx.objectStore("handles").get(key);
  rq.onsuccess = function(){res(rq.result);}; rq.onerror = function(){rej(rq.error);};});});}
function idbPut(key,val){return idb().then(function(db){return new Promise(function(res,rej){
  var tx = db.transaction("handles","readwrite");
  tx.objectStore("handles").put(val,key);
  tx.oncomplete = function(){res();}; tx.onerror = function(){rej(tx.error);};});});}

/* ---------- 编辑授权与最新历史载入 ---------- */
function setStatus(html){$("#perm-status").innerHTML = html;}
function bindEnable(label){
  var box = $("#perm-status");
  box.innerHTML = '<span>'+label+'</span><br>';
  var b = document.createElement("button"); b.textContent = "启用编辑";
  b.addEventListener("click", enableEdit); box.appendChild(b);
  box.appendChild(document.createElement("br"));
  var tip = document.createElement("span");
  tip.textContent = "弹出窗口地址栏粘贴此路径后点「选择文件夹」："+META.dir_full;
  tip.style.cssText = "word-break:break-all";
  box.appendChild(tip);
}
function updateEditorUI(){
  var note = $("#ed-note"), dis = !state.dir;
  $("#ed-save").disabled = dis;
  if (state.dir){note.textContent = "已连接："+state.dir.name;}
}
function connect(dir){
  state.dir = dir;
  var chain = readArchText("manifest.json").then(function(txt){
    var m = JSON.parse(txt);
    m.tabs = m.tabs||{}; m.actions = m.actions||[];
    manifest = m;
    return Promise.all(TABS.map(function(tab){
      var lst = m.tabs[tab]||[];
      if (!lst.length) return;
      return readArchText("history/"+lst[0].file).then(function(t){
        state.content[tab] = t;
      }).catch(function(){});
    }));
  }).then(function(){
    TABS.forEach(function(tab){
      if (tab === "scratch"){
        $("#scratch-content").innerHTML = state.content[tab];
      } else {
        sectionEl(tab).innerHTML = state.content[tab];
        processMisses(sectionEl(tab));
      }
    });
    if (editorTarget) editor.innerHTML = state.content[editorTarget];
    renderSubtabs(state.tab);
    updateEditorUI();
    setStatus('<span>已连接存档目录：'+dir.name+'<br>内容与历史已同步为最新。</span>');
  }).catch(function(e){
    /* 目录失效（已删除/移动）或不是有效存档：丢弃旧句柄，回到重新选择状态 */
    state.dir = null; state.permHandle = null;
    $("#ed-save").disabled = true;
    bindEnable("读取存档失败："+e.message+"。存档目录可能已被移动或删除，请重新选择。");
  });
}
function enableEdit(){
  if (state.permHandle){
    state.permHandle.requestPermission({mode:"readwrite"}).then(function(p){
      if (p === "granted") connect(state.permHandle);
      else toast("未授予读写权限，编辑不可用");
    });
    return;
  }
  window.showDirectoryPicker({mode:"readwrite"}).then(function(d){
    if (d.name !== META.dir){toast("所选目录与存档不符：期望「"+META.dir+"」，收到「"+d.name+"」");return;}
    idbPut(META.dir, d).then(function(){connect(d);});
  }).catch(function(e){ if (e.name !== "AbortError") toast("打开目录失败："+e.message); });
}
function tryRestore(){
  idbGet(META.dir).then(function(h){
    if (!h){bindEnable("尚未连接存档目录（编辑与最新历史需要授权）");return;}
    h.queryPermission({mode:"readwrite"}).then(function(p){
      if (p === "granted") connect(h);
      else {state.permHandle = h; bindEnable("需要重新授权后才能同步最新历史");}
    });
  }).catch(function(e){bindEnable("本地授权数据读取失败："+e.message);});
}

/* ---------- 编辑工作台 ---------- */
var editor = $("#editor"), editorTarget = "scratch";
function loadIntoEditor(target, histFile){
  editorTarget = target;
  $("#edit-target").value = target;
  var p = histFile ? readArchText("history/"+histFile)
                   : Promise.resolve(state.content[target]);
  p.then(function(txt){editor.innerHTML = txt;})
   .catch(function(e){toast("载入编辑器失败："+e.message);});
}
$("#edit-target").addEventListener("change", function(){
  editorTarget = this.value; editor.innerHTML = state.content[editorTarget];
});
$("#ed-cancel").addEventListener("click", function(){
  editor.innerHTML = state.content[editorTarget];
  toast("已放弃未保存的修改");
});
function stamp(){var d=new Date(),p=function(n){return (n<10?"0":"")+n;};
  return ""+d.getFullYear()+p(d.getMonth()+1)+p(d.getDate())+"-"+p(d.getHours())+p(d.getMinutes())+p(d.getSeconds())+p(d.getMilliseconds());}
$("#ed-save").addEventListener("click", function(){
  if (!state.dir){toast("尚未启用编辑：请先在左侧授权连接存档目录");return;}
  var tab = editorTarget, html = editor.innerHTML, ts = stamp();
  var file = tab + "-" + ts + ".html";
  var hist = state.dir.getDirectoryHandle("history").then(null,function(){
    return state.dir.getDirectoryHandle("history",{create:true});});
  hist.then(function(hd){return hd.getFileHandle(file,{create:true});})
  .then(function(fh){return fh.createWritable();})
  .then(function(w){return w.write(html).then(function(){return w.close();});})
  .then(function(){return readArchText("manifest.json");})
  .then(function(txt){
    var m = JSON.parse(txt); m.tabs = m.tabs||{}; m.actions = m.actions||[];
    m.tabs[tab] = m.tabs[tab]||[];
    m.tabs[tab].unshift({ts:ts,file:file});
    m.actions.unshift({ts:ts,tab:tab,file:file});
    var vn = m.tabs[tab].length;
    return state.dir.getFileHandle("manifest.json").then(function(mf){
      return mf.createWritable();
    }).then(function(w){return w.write(JSON.stringify(m,null,2))
      .then(function(){return w.close();});}).then(function(){return vn;});
  })
  .then(function(vn){
    return readArchText("manifest.json").then(function(t2){
      var m2 = JSON.parse(t2); m2.tabs=m2.tabs||{}; m2.actions=m2.actions||[];
      manifest = m2;
      state.content[tab] = html;
      if (tab === "scratch") $("#scratch-content").innerHTML = html;
      if (state.viewing.tab === tab) backToLatest(tab);
      renderSubtabs(state.tab);
      updateEditorUI();
      toast("已保存 v"+vn+"（history/"+file+"）");
    });
  })
  .catch(function(e){toast("保存失败："+e.message+"（如为权限问题请点左侧「启用编辑」重新授权）");});
});

/* ---------- 启动 ---------- */
TABS.forEach(processMisses.bind(null,null));
renderSubtabs("original");
editor.innerHTML = state.content.scratch;
if (!canFSA){
  var readNote = "当前浏览器只读：编辑与完整历史需要 Chrome/Edge。" +
    "本页内容为最后一次 render 的快照，Chrome 编辑出的新版本本浏览器也读不到。";
  setStatus('<span>'+readNote+'</span>');
  $("#ed-save").disabled = true;
  $("#ed-note").textContent = "编辑需 Chrome/Edge";
  editor.removeAttribute("contenteditable");
} else {
  tryRestore();
  updateEditorUI();
}
})();
</script>
</body>
</html>
"""


def build_index_html(article: dict, manifest: dict, dir_name: str,
                     dir_full: str, ok_n: int, fail_n: int) -> str:
    meta = article["meta"]
    meta_view = {
        "title": meta.get("title", ""),
        "dir": dir_name,
        "dir_full": dir_full,
    }
    asset_stat = f"资源 {ok_n} 张本地化" + (f" · {fail_n} 张在线兜底" if fail_n else "")
    foot = (f"原文：{meta.get('url', '')} · 抓取 {meta.get('fetched_at', '')}"
            f" · sh-web-archive 生成 · 纯静态离线存档")
    html_doc = INDEX_TEMPLATE
    for key, val in {
        "__TITLE__": esc(meta.get("title", "未命名")),
        "__AUTHOR__": meta.get("author") or "佚名",
        "__PUBLISH__": meta.get("publish_time") or "时间未知",
        "__SITE__": meta.get("site", ""),
        "__URL__": esc(meta.get("url", "")),
        "__ASSET_STAT__": asset_stat,
        "__ORIGINAL_HTML__": article["content_html"],
        "__SUMMARY_HTML__": render_summary_html_cached(article),
        "__SCRATCH_HTML__": SCRATCH_GUIDE,
        "__FOOT__": esc(foot),
        "__META_JSON__": json.dumps(meta_view, ensure_ascii=False).replace("</", "<\\/"),
        "__MANIFEST_JSON__": json.dumps(manifest, ensure_ascii=False).replace("</", "<\\/"),
    }.items():
        html_doc = html_doc.replace(key, val)
    return html_doc


_SUMMARY_STATE: dict | None = None


def render_summary_html_cached(article: dict) -> str:
    """render 主流程把已校验 summary 预渲染后挂到模块级，模板替换时取用。"""
    if _SUMMARY_STATE is not None:
        return _SUMMARY_STATE
    return SUMMARY_PLACEHOLDER


# ---------------- render 子命令 ----------------

def cmd_render(args: argparse.Namespace) -> None:
    global _SUMMARY_STATE
    dir_path = Path(args.dir).expanduser()
    aj = dir_path / "article.json"
    if not aj.exists():
        raise ArchiveError("render_failed",
                           f"缺少 article.json：{aj}（请先对目标 URL 运行 fetch）")
    article = json.loads(aj.read_text(encoding="utf-8"))

    if args.summary:
        sp = Path(args.summary).expanduser()
        if not sp.exists():
            raise ArchiveError("bad_summary", f"summary 文件不存在：{sp}")
        summary = validate_summary(
            json.loads(sp.read_text(encoding="utf-8")), str(sp))
        _SUMMARY_STATE = render_summary_html(summary)
    else:
        _SUMMARY_STATE = None

    hist_dir = dir_path / "history"
    hist_dir.mkdir(exist_ok=True)
    manifest_path = dir_path / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.setdefault("tabs", {})
        manifest.setdefault("actions", [])
    else:
        manifest = {"tabs": {}, "actions": []}

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    # 快照内容 = 各 tab 的 section 初始 HTML（与 index.html 内嵌一致）
    original_html = article["content_html"]
    summary_html = _SUMMARY_STATE if _SUMMARY_STATE is not None else SUMMARY_PLACEHOLDER
    scratch_html = SCRATCH_GUIDE
    new_state = {"original": original_html, "summary": summary_html,
                 "scratch": scratch_html}
    for tab, html_content in new_state.items():
        lst = manifest["tabs"].get(tab, [])
        latest = None
        if lst:
            f = hist_dir / lst[0]["file"]
            if f.exists():
                latest = f.read_text(encoding="utf-8")
        if latest != html_content:
            fname = f"{tab}-{ts}.html"
            (hist_dir / fname).write_text(html_content, encoding="utf-8")
            lst.insert(0, {"ts": ts, "file": fname})
            manifest["tabs"][tab] = lst
            log(f"{CN_TAB[tab]} tab 追加新版本：history/{fname}")
        else:
            log(f"{CN_TAB[tab]} tab 内容未变，不追加")

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    assets = article.get("assets", [])
    ok_n = sum(1 for a in assets if a.get("ok"))
    fail_n = len(assets) - ok_n
    out = dir_path / "index.html"
    out.write_text(
        build_index_html(article, manifest, dir_path.name,
                         str(dir_path.resolve()), ok_n, fail_n),
        encoding="utf-8")

    vers = " · ".join(
        f"{CN_TAB[t]} v{len(v)}" for t, v in manifest["tabs"].items())
    log(f"渲染完成：{out}")
    log(f"资源：成功 {ok_n} / 失败 {fail_n} / 共 {len(assets)}")
    log(f"版本：{vers}")


def main() -> None:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        prog="build_archive.py",
        description="网页文章 → 目录形态静态存档（fetch 抓取 / render 渲染）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_fetch = sub.add_parser("fetch", help="匿名抓取网页 → article.json + assets/")
    p_fetch.add_argument("--url", required=True, help="无需鉴权的公开网页 URL")
    p_fetch.add_argument("--title", help="覆盖目录名中的标题部分")
    p_fetch.add_argument("--dir", help="覆盖存档子目录名（默认 'YYYY-MM-DD 标题'）")

    p_render = sub.add_parser("render",
                              help="渲染三 tab 静态页面 index.html + history/")
    p_render.add_argument("--dir", required=True, help="存档子目录路径")
    p_render.add_argument("--summary", help="模型撰写的 summary.json（可选）")

    args = parser.parse_args()
    try:
        if args.cmd == "fetch":
            cmd_fetch(args)
        elif args.cmd == "render":
            cmd_render(args)
    except ArchiveError as e:
        print(f"error: {e.code}: {e}", file=sys.stderr, flush=True)
        sys.exit(2 if e.code == "bad_url" else 1)


if __name__ == "__main__":
    main()
