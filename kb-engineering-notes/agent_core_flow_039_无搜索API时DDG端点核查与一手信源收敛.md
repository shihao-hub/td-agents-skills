---
name: kb-web-factcheck-pipeline
description: 知识库：无第三方搜索 API 时，用单文件脚本抓 DuckDuckGo HTML 端点做公开信息事实核查，并经 site: 收敛到第一方信源的三段式流水线。当需要核实「某公开信息到底有没有/是什么」、手上只有终端、或担心把「我没查到」误当「不存在」时查阅。
---

# 无搜索 API 时抓 DuckDuckGo HTML 端点做事实核查与第一方信源收敛指南

> **实测环境**：Windows + Git Bash + Agent 终端，只用 `bash` 工具（无浏览器内核、无搜索 API key）。
> **真实案例**：核实「滴滴内部 IM 叫什么」——最终由滴滴自有域名 `xiaojukeji.com` 的第一方页面坐实为 **D-Chat**。

---

## 一、业务场景与核查需求

### 1.1 输入、能力与交付

| 项 | 内容 |
|:---|:---|
| 输入 | 一句待核实命题，如「某公司内部 IM 叫什么」「某工具是否支持某特性」 |
| 可用能力 | 只有终端 `bash`（`curl` / `uv run python`），**没有**搜索 API、没有无头浏览器 |
| 目标产出 | 带**信源分级**的结论：第一方证据 / 二手佐证 / 查无实据 |
| 交付格式 | 结论 + 命中链接 + 该链接的原文片段（**不是**"我印象中"） |

### 1.2 真正的风险不是"查不到"，而是把"我没查到"说成"不存在"

本条目诞生于一次真实翻车：

1. 面对「滴滴内部 IM 叫什么」，我**没有检索**，直接下结论：「公开语料里几乎是空白」；
2. 还配了一整套听起来很严谨的解释——信息密度、平台封闭性、脉脉不可爬——**用来解释一个根本没验证过的前提**；
3. 用户一句「难道没有内部员工分享？」就戳穿了；
4. 实际检索 **3 轮**后，拿到了**滴滴自有域名上的第一方页面**（D-Chat 下载页 + 用户手册 + FAQ）。

> **教训**：用精致的理论包装没做的检索，比直接说"我不知道"有害得多。
> `我的记忆里没有` ≠ `世界上没有`，这两件事必须严格分开；否定性结论（"没有"）的举证责任更高。

---

## 二、技术核心难点与底层剖析

### 2.1 主流搜索引擎网页版是 JS 渲染的，抓下来是空壳

`bing.com/search?q=...`、`google.com/search?q=...` 的结果块由前端异步注入；不带浏览器内核直接 GET，HTML 里没有 `li.b_algo` / `div.g` 之类的结构。

### 2.2 反爬降级页会造成**假阴性**（最隐蔽的坑）

实测观测：对 Bing 用**三个完全不同**的查询，返回的结果**逐条完全相同**（全是"滴滴官网 / 百度百科 / 维基百科"这类大站首页）。

服务端识别出非浏览器流量后，吐了一个**与查询无关的通用降级页**。若不做自检直接采信，就会得出「公网上没有这个信息」的**反向错误结论** —— 与 1.2 的翻车是同一风险结构。

**所以：结果的"雷同度"必须作为门禁指标。**

### 2.3 DuckDuckGo 的 `/html/` 端点是无 JS 服务端渲染版

| 入口 | 能否直接抓 |
|:---|:---|
| `duckduckgo.com` | ❌ 重度 JS |
| **`html.duckduckgo.com/html/`** | ✅ **服务端渲染，结果直接在 HTML 里**（本条主用） |
| `lite.duckduckgo.com/lite/` | ✅ 更极简的表格版（备用） |
| `api.duckduckgo.com/?q=&format=json` | ⚠️ 官方 API 只回"即时答案"，**不给网页结果**，不适用 |

页面结构（CSS 选择器即取即用）：

```html
<div class="result">
  <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2F...">标题</a>
  <a class="result__snippet">摘要</a>
</div>
```

### 2.4 出站链接被包了一层跳转，必须解包

DDG 为统计点击，把真实地址塞进 `uddg` 参数：

```text
//duckduckgo.com/l/?uddg=https%3A%2F%2Fzhushou.xiaojukeji.com%2F
```

不解包就去 GET，会一直停在 DDG 的跳转页。解法：取 `uddg` 后 `unquote`。

### 2.5 信源分级：第一方 ≫ 二手 ≫ 无源转述

| 级别 | 定义 | 本次案例 |
|:---|:---|:---|
| **第一方** | 当事主体**自有域名**上的页面 | `zhushou.xiaojukeji.com`（*Download D-Chat*）、`im.xiaojukeji.com/guide`（*D-Chat User Guide*）、`/faq` |
| 二手 | 第三方盘点、媒体、社区帖 | 知乎《扒一扒，互联网大厂内部都用什么软件沟通？》——「滴滴：最早是企微，现在用 D-Chat」 |
| 不可用 | 无来源转述、AI 内容农场模板文 | 逗号里罗列"Teams/Slack/Trello"那种明显套壳生成的页面 |

**只有第一方能定案**；二手用于交叉印证方向，不可单独成结论。

### 2.6 结构性可见性：区分两种"查不到"

| 类型 | 特征 | 例 |
|:---|:---|:---|
| **结构上必然可见** | 需向员工/外包/海外同事**分发产物** → 必须有公网下载页、手册、FAQ | 内部 IM（D-Chat）、内部 IT 工具（`day.xiaojukeji.com` 的 D-Day） |
| **结构上基本不可见** | 纯内部行政/采购政策，无对外分发需求 | "配什么笔记本""几块显示器""是否双屏" |

结论：「办公电脑/双屏」查不到属**预期**；「内部 IM 叫什么」查不到就**只能是我没查**。
下结论前必须先判断自己遇到的是哪一种。

---

## 三、标准核查流水线与代码实现

### 3.1 三步式流程图

```text
步骤0 连通性探测  →  curl -w "%{http_code}"   判断哪些域名能通（418 反爬 / 302 登录墙）
步骤1 DDG 抓搜    →  html.duckduckgo.com/html/   多查询抓取 + uddg 解包
步骤2 降级自检    →  多查询结果是否雷同？关键词是否命中？雷同即整批作废
步骤3 第一方收敛  →  site:<自有域名> <关键词>  → GET 命中页 → 取 <title> + 正文摘要
```

### 3.2 步骤 0：连通性探测（终端一条命令）

```bash
curl -s -o /dev/null -w "bing:%{http_code} " --max-time 8 https://www.bing.com/
curl -s -o /dev/null -w "zhihu:%{http_code} " --max-time 8 https://www.zhihu.com/
curl -s -o /dev/null -w "maimai:%{http_code}\n" --max-time 8 https://maimai.cn/
# 实测输出：bing:200  zhihu:302（跳登录墙）  maimai:418（反爬）
```

### 3.3 完整脚本骨架（PEP 723 + uv 单文件，可直接跑）

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx", "beautifulsoup4", "lxml"]
# ///
"""公开信息事实核查流水线（无搜索 API 版）。

用法:
  uv run factcheck.py "滴滴 内部IM"
  uv run factcheck.py "滴滴 内部IM" --site xiaojukeji.com --first-party-term D-Chat
"""
from __future__ import annotations

import argparse
import re
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
DDG = "https://html.duckduckgo.com/html/"


def clean(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def unwrap(href: str) -> str:
    """解开 DDG 的 //duckduckgo.com/l/?uddg=<encoded> 跳转包装。"""
    if "duckduckgo.com/l/" in href:
        qs = parse_qs(urlparse(href).query)
        if "uddg" in qs:
            return unquote(qs["uddg"][0])
    return href


def ddg_search(client: httpx.Client, query: str, limit: int = 8) -> list[dict]:
    """抓 DDG 无 JS 端点，返回 [{title,url,snippet}]。"""
    r = client.post(DDG, data={"q": query})
    r.raise_for_status()
    rows: list[dict] = []
    for box in BeautifulSoup(r.text, "lxml").select("div.result")[:limit]:
        a = box.select_one("a.result__a")
        if not a:
            continue
        s = box.select_one("a.result__snippet")
        rows.append({
            "title": clean(a.get_text()),
            "url": unwrap(a.get("href", "")),
            "snippet": clean(s.get_text()) if s else "",
        })
    return rows


def is_degenerated(batches: dict[str, list[dict]]) -> bool:
    """门禁：多个不同查询返回同一批 URL -> 判定反爬降级页，整批作废。"""
    sigs = {q: tuple(r["url"] for r in rows) for q, rows in batches.items() if rows}
    return len(sigs) > 1 and len(set(sigs.values())) == 1


def keyword_hit(rows: list[dict], terms: list[str]) -> bool:
    """结果里至少要命中一个查询词，否则可疑。"""
    blob = " ".join(f"{r['title']} {r['snippet']}" for r in rows)
    return any(t in blob for t in terms if t)


def fetch_page(client: httpx.Client, url: str) -> tuple[str, str]:
    """第一方取证：取页面 <title> + 正文前 400 字。"""
    r = client.get(url)
    soup = BeautifulSoup(r.text, "lxml")
    title = clean(soup.title.get_text()) if soup.title else "(no title)"
    return title, clean(soup.get_text())[:400]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--site", default="", help="第一方域名，用于 site: 收敛，如 xiaojukeji.com")
    ap.add_argument("--first-party-term", default="", help="第一方页面应出现的关键词，用于自检")
    args = ap.parse_args()

    queries = [args.query, f"{args.query} 叫什么", f"{args.query} 自研"]
    out: list[str] = []
    terms = [w for w in args.query.split() if len(w) > 1]

    with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": UA}) as c:
        batches = {q: ddg_search(c, q) for q in queries}

        # —— 步骤 2：降级自检（门禁）——
        if is_degenerated(batches):
            out.append("!! 降级告警：多个不同查询返回完全相同的 URL 批次，本批结果整体作废。")
        for q, rows in batches.items():
            out.append(f"\n=== {q} ({len(rows)}) ===")
            for r in rows:
                out.append(f"- {r['title']} | {r['url']} | {r['snippet'][:150]}")
            if rows and not keyword_hit(rows, terms):
                out.append("  ! 关键词未命中，结果与查询可能无关。")

        # —— 步骤 3：第一方域名收敛 ——
        if args.site:
            key = args.first_party_term or args.query
            out.append(f"\n=== site:{args.site} {key} ===")
            for r in ddg_search(c, f"site:{args.site} {key}"):
                title, body = fetch_page(c, r["url"])
                ok = not args.first_party_term or args.first_party_term.lower() in body.lower()
                out.append(f"- HIT {r['url']}")
                out.append(f"  [{'OK' if ok else '?'}] title={title}")
                out.append(f"  body={body}")

    text = "\n".join(out)
    with open("factcheck_report.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print(text if len(text) < 4000 else text[:4000] + "\n...(已截断，完整见 factcheck_report.txt)")


if __name__ == "__main__":
    main()
```

> 按仓库脚本约定：正式化后应落在 `.scripts/`（PEP 723 + uv 单文件）；一次性探针可先临时放置，**用后即删**，不污染 `.scripts/`。

---

## 四、交付验证、信源分级与防复发建议

1. **断言强度必须匹配证据强度**
   - 有第一方页面 → 可用"是 / 为"陈述；
   - 只有二手 → 必须标注"据第三方报道"；
   - 什么都没有 → 只能说「**我暂时查不到，需进一步检索**」，**禁止**说"公开语料里没有 / 不存在"。

2. **否定性结论要额外举证**
   说"没有"比说"有"责任更重：必须跑完三步流水线（含降级自检），并在报告里留下查询词与命中情况，证明**确实搜过**。

3. **降级自检是硬门禁**
   多查询结果雷同、或关键词零命中 → 该批结果整体作废，不得作为"查无此物"的依据。这是本条目最重要的一条：**假阴性比假阳性更危险**，因为它伪装成"有结论"。
   - **实测补充**：同一个 `site:` 查询，前一次跑回 8 条、紧接第二次跑回 **0 条**（限流／瞬时波动）。因此**"0 结果"必须重试确认后才能当作线索缺失**，绝不能直接升级为"没有"。

4. **双源交叉 + 域名归属核实**
   第一方页面要确认**域名确属当事主体**（例：`xiaojukeji.com` → 北京小桔科技有限公司 → 滴滴法人主体，域名与主体能对上）；二手信息只用于印证方向。

5. **临时脚本与产物用后即清**
   探针脚本 + `factcheck_report.txt` 属临时资源，任务收尾立即删除；只有验证有效、值得复用的流程才正式化进 `.scripts/`。

6. **已知局限（别高估这套）**
   - DDG 会限流，量一大就 403 / 验证页；需退避与降频；
   - 抓 SERP 处于各家 ToS 灰区，只适合**一次性核查**，不可作生产方案；
   - 结果依地区/时间浮动，同一查询不同时刻可能不同，结论要带时间戳。

7. **常态化检索就上正规通道**
   搜索 API（Bing Search API / Brave / Serper / Tavily）或自建 SearXNG；JS 重度站点再上 Playwright / chrome-devtools 类无头浏览器。**现写爬虫只应是"没有 API 时的兜底"。**
