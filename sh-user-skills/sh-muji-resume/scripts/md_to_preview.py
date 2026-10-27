"""把木及简历格式的 Markdown 转成本地墨线预览 HTML（兜底渲染/打印用）。

用法：
  uv run python md_to_preview.py --md <内容.md> --out <预览.html> [--css <ink-rule.css>]

--css 缺省时自动使用本脚本同目录 ../assets/ink-rule.css。
md 约定：`::: left ... ::: right ... :::` 为左右栏组；`1、`/`1.` 有序列表；`- ` 无序列表。
"""
import argparse
import re
from pathlib import Path

DEFAULT_CSS = Path(__file__).resolve().parent.parent / "assets" / "ink-rule.css"


def esc(s: str) -> str:
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)


def paras(lines):
    for ln in lines:
        yield f'<div class="block"><p>{esc(ln)}</p></div>'


def parse(md_lines):
    body, i, n = [], 0, len(md_lines)
    while i < n:
        s = md_lines[i].strip()
        if not s:
            i += 1
            continue
        if s.startswith("# "):
            body.append(f'<div class="h1_block block"><h1>{esc(s[2:].strip())}</h1></div>')
            i += 1
            continue
        if s.startswith("## "):
            body.append(f'<div class="h2_block block"><h2>{esc(s[3:].strip())}</h2></div>')
            i += 1
            continue
        if s.startswith("### "):
            body.append(f'<div class="h3_block block"><h3>{esc(s[4:].strip())}</h3></div>')
            i += 1
            continue
        if s == "::: left":
            i += 1
            left = []
            while i < n and md_lines[i].strip() != "::: right":
                if md_lines[i].strip() and md_lines[i].strip() != ":::":
                    left.append(md_lines[i].strip())
                i += 1
            i += 1
            right = []
            while i < n and md_lines[i].strip() != ":::":
                if md_lines[i].strip():
                    right.append(md_lines[i].strip())
                i += 1
            i += 1
            L, R = "".join(paras(left)), "".join(paras(right))
            body.append(f'<div class="block lr-container"><div class="left">{L}</div><div class="right">{R}</div></div>')
            continue
        if s == ":::":
            i += 1
            continue
        m, mo = re.match(r"^- (.*)$", s), re.match(r"^(\d+)\. (.*)$", s)
        if m or mo:
            kind = "-" if m else "ol"
            items = []
            while i < n:
                s2 = md_lines[i].strip()
                if not s2:
                    j = i + 1
                    while j < n and not md_lines[j].strip():
                        j += 1
                    if j < n and re.match(r"^(- |\d+\. )", md_lines[j].strip()):
                        i = j
                        continue
                    break
                mm, mo2 = re.match(r"^- (.*)$", s2), re.match(r"^\d+\. (.*)$", s2)
                if kind == "-" and mm:
                    items.append(mm.group(1))
                elif kind == "ol" and mo2:
                    items.append(mo2.group(1))
                else:
                    break
                i += 1
            tag = "ul" if kind == "-" else "ol"
            lis = "".join(f"<li>{esc(t)}</li>" for t in items)
            body.append(f'<div class="block"><{tag}>{lis}</{tag}></div>')
            continue
        body.append(f'<div class="block"><p>{esc(s)}</p></div>')
        i += 1
    return body


TEMPLATE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{title}</title>
<style>
@page {{ size: A4; margin: 0; }}
@media print {{ body {{ background: #fff; }} .rs-page-item {{ margin: 0; box-shadow: none; }} }}
body {{ margin: 0; background: #F2F0EC; font-family: "Noto Sans SC", "Microsoft YaHei", sans-serif; }}
.rs-page-item {{ width: 794px; min-height: 1123px; background: #fff; margin: 24px auto; box-shadow: 0 2px 14px rgba(0,0,0,.08); }}
.rs-view {{ padding: 48px 56px; }}
.rs-view .lr-container {{ display: flex; justify-content: space-between; align-items: flex-start; }}
.rs-view .lr-container .left {{ flex: 1; }}
.rs-view .lr-container .right {{ text-align: right; white-space: nowrap; }}
.rs-view ul, .rs-view ol {{ margin: 4px 0 6px; padding-left: 22px; }}
{css}
</style></head>
<body><div class="rs-page-item"><div class="rs-view">
{body}
</div></div></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--css", default=str(DEFAULT_CSS))
    ap.add_argument("--title", default="简历预览")
    a = ap.parse_args()
    css = Path(a.css).read_text(encoding="utf-8")
    md_lines = Path(a.md).read_text(encoding="utf-8").splitlines()
    title = next((ln[2:].strip() for ln in md_lines if ln.startswith("# ")), a.title)
    html = TEMPLATE.format(title=title, css=css, body="\n".join(parse(md_lines)))
    Path(a.out).write_text(html, encoding="utf-8", newline="\n")
    print("written:", a.out)


if __name__ == "__main__":
    main()
