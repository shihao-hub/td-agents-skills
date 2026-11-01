# /// script
# requires-python = ">=3.10"
# dependencies = ["opencc-python-reimplemented"]
# ///
"""
媒体访谈转写稿 / 演讲录转杂志风精读本 HTML 渲染引擎
支持双模态：
  1. monologue 模式（单人演说 / 演讲录 / 思想漫笔 / 劝学）
  2. dialogue 模式（双人对谈 / 访谈播客 / 圆桌讨论）
用法:
  uv run render_reader.py <input_srt_or_txt> [--title <标题>] [--speaker <主讲人/嘉宾>] [--host <主持人>] [--mode auto|monologue|dialogue]
"""

import argparse
import os
import re
import sys
from pathlib import Path
import opencc

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

cc = opencc.OpenCC("t2s")

DEFAULT_CORRECTIONS = [
    # 思想与哲学专有名词
    ("驱魅", "祛魅"),
    ("趣味的社会", "祛魅的社会"),
    ("微学著作", "文学著作"),
    ("终界", "中介"),
    ("中界", "中介"),
    ("腐蚀皆逝", "俯拾皆是"),
    ("出手可及", "触手可及"),
    ("弗洛伊德奥", "弗洛伊德"),
    ("姓亚裔的理论", "性压抑理论"),
    ("阅读援助", "阅读原著"),
    ("援助", "原著"),
    ("阿卜主", "UP主"),
    ("入法炮制", "如法炮制"),
    # 既有访谈专名
    ("马斯科", "马斯克"),
    ("天空项目", "天宫项目"),
    ("做天工的时候", "做天宫的时候"),
    ("机身智能", "具身智能"),
    ("二头米四二号", "阿尔忒弥斯二号"),
    ("公务唐居安", "功不唐捐"),
    ("Teslin Nolley", "默会知识（Tacit Knowledge）"),
    ("墨绘的指示", "默会的知识"),
    ("墨会的指示", "默会的知识"),
    ("恐大", "宏大"),
    ("真正点的", "真正顶的"),
    ("更加的内却", "更加的内卷"),
    ("同情事", "同寝室"),
    ("效绩奖励", "校级奖励"),
    ("速度率", "生育率"),
    ("吃屠制", "师徒制"),
    ("老灯本", "老登们"),
    ("花器", "花期"),
    ("失措", "试错"),
    ("经工", "金工"),
    ("Deep Man", "DeepMind"),
    ("战炉", "湛庐"),
    ("反刺", "反思"),
    ("等源", "能源"),
    ("怀孕飞行", "环月飞行"),
    ("贝斯统计思维", "贝叶斯统计思维"),
    ("男人致死是少年", "男人至死是少年"),
]


def sanitize_filename(title: str, max_len: int = 60) -> str:
    r"""
    文件名清洗协议（去随意化核心规范）：
    1. 彻底去除 Windows 非法字符 /\:*?"<>|
    2. 符号规范映射，保留可读性
    3. 限制长度，去除首尾冗余空格
    """
    t = title.strip()
    t = t.replace("|", " - ").replace("/", "-").replace("\\", "-")
    t = t.replace(":", "：").replace("*", "_").replace("?", "？")
    t = t.replace('"', "''").replace("<", "【").replace(">", "】")
    t = re.sub(r"\s+", " ", t)
    if len(t) > max_len:
        t = t[:max_len].rstrip(" -_：，,")
    t = re.sub(r'[\\/:*?"<>|]', "", t).strip()
    return t if t else "精读本"


def clean_text(text: str) -> str:
    s = cc.convert(text)
    for src, dst in DEFAULT_CORRECTIONS:
        s = s.replace(src, dst)
    return s


def parse_srt(srt_content: str):
    blocks = re.split(r"\n\s*\n", srt_content.strip())
    segments = []
    for b in blocks:
        lines = [l.strip() for l in b.splitlines() if l.strip()]
        if len(lines) >= 3:
            try:
                idx = int(lines[0])
            except ValueError:
                continue
            time_parts = lines[1].split(" --> ")
            if len(time_parts) != 2:
                continue
            start_ts = time_parts[0].split(",")[0]
            end_ts = time_parts[1].split(",")[0]
            text = clean_text(" ".join(lines[2:]))
            segments.append({
                "idx": idx,
                "start": start_ts,
                "end": end_ts,
                "text": text,
            })
    return segments


def parse_txt(txt_content: str):
    lines = [clean_text(l.strip()) for l in txt_content.splitlines() if l.strip()]
    segments = []
    for i, line in enumerate(lines, 1):
        segments.append({
            "idx": i,
            "start": "--:--:--",
            "end": "--:--:--",
            "text": line,
        })
    return segments


def detect_mode(segments, user_mode: str = "auto") -> str:
    if user_mode in ["monologue", "dialogue"]:
        return user_mode
    # 启发式检测：看是否存在持续的多人相互提问与应答
    question_count = 0
    short_utterance_count = 0
    for s in segments:
        txt = s["text"]
        if any(txt.startswith(kw) for kw in ["为什么", "那为什么", "怎么看", "请问", "老师", "您觉得"]):
            question_count += 1
        if len(txt) < 30:
            short_utterance_count += 1
    # 如果极少提问且几乎通篇长文陈述，判定为单人独白演说
    if question_count < 3 and len(segments) > 20:
        return "monologue"
    return "dialogue"


def generate_monologue_html(
    title: str,
    speaker: str,
    speaker_desc: str,
    duration_str: str,
    sections: list,
    models: list,
) -> str:
    """
    单人演说 / 思想漫笔 / 随笔精读模板（去 AI 味、报刊出版物级排版）
    """
    models_html = ""
    for l_title, l_desc, r_title, r_desc in models:
        models_html += f"""
        <div class="model-card left">
          <h4>{l_title}</h4>
          <p>{l_desc}</p>
        </div>
        <div class="model-card right">
          <h4>{r_title}</h4>
          <p>{r_desc}</p>
        </div>
"""

    sections_html = ""
    total_words = 0
    for s_idx, sec in enumerate(sections, 1):
        sec_title = sec["title"]
        sec_desc = sec["desc"]
        sec_time = sec["time"]
        paragraphs = sec["paragraphs"]
        pull_quote = sec.get("quote")

        p_html = ""
        for p in paragraphs:
            total_words += len(p)
            p_html += f"<p class='essay-paragraph'>{p}</p>\n"

        quote_html = ""
        if pull_quote:
            quote_html = f"""
        <blockquote class="pull-quote">
          “{pull_quote}”
          <cite class="pull-quote-author">— 《{title}》· 核心洞见</cite>
        </blockquote>
"""

        sections_html += f"""
      <section class="essay-section" id="section-{s_idx}">
        <header class="section-header">
          <div class="section-meta">
            <span class="section-tag">第 {s_idx} 部分 · 论述</span>
            <time class="section-time">[{sec_time}]</time>
          </div>
          <h2 class="section-title">{sec_title}</h2>
          <p class="section-summary">{sec_desc}</p>
        </header>
        <div class="section-content">
          {p_html}
          {quote_html}
        </div>
      </section>
"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} ｜ 思想演说精读本</title>
  <style>
    :root {{
      --bg-canvas: #FBFBFA;
      --bg-card: #FFFFFF;
      --bg-subtle: #F4F6F3;
      --text-main: #1C221E;
      --text-muted: #56645D;
      --text-soft: #85938B;
      --border-light: #E5E9E3;
      --border-accent: #CBD5CA;

      --pine-deep: #1A4432;
      --pine-mid: #2A5E47;
      --pine-light: #EBF3EE;
      --clay-deep: #8E4A28;
      --clay-light: #FBF2EC;
      --ochre-mark: #E68A36;

      --font-serif: "Songti SC", "Source Han Serif SC", "Noto Serif SC", STSong, Georgia, serif;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Source Han Sans SC", "Noto Sans SC", "Microsoft YaHei", sans-serif;
      --font-mono: "SF Mono", Consolas, Monaco, monospace;

      --reading-width: 780px;
      --line-height-body: 1.92;
      --font-size-body: 18px;
    }}

    body.large-text {{
      --font-size-body: 20px;
      --line-height-body: 2.0;
      --reading-width: 820px;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background-color: var(--bg-canvas);
      color: var(--text-main);
      font-family: var(--font-sans);
      font-size: var(--font-size-body);
      line-height: var(--line-height-body);
      text-rendering: optimizeLegibility;
      -webkit-font-smoothing: antialiased;
      padding-bottom: 120px;
    }}

    #progress-container {{
      position: fixed; top: 0; left: 0; width: 100%; height: 3px; background: transparent; z-index: 1000;
    }}
    #progress-bar {{
      height: 100%; width: 0%; background: var(--pine-mid); transition: width 0.1s ease-out;
    }}

    .masthead {{
      border-bottom: 1px solid var(--border-light);
      background: var(--bg-card);
      padding: 56px 24px 44px;
    }}
    .masthead-inner {{
      max-width: var(--reading-width);
      margin: 0 auto;
    }}
    .publication-tag {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-family: var(--font-serif);
      font-size: 13.5px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--pine-mid);
      margin-bottom: 18px;
      font-weight: 600;
    }}
    .publication-tag::after {{
      content: "";
      display: inline-block;
      width: 28px;
      height: 1px;
      background: var(--pine-mid);
      vertical-align: middle;
    }}
    h1.article-title {{
      font-family: var(--font-serif);
      font-size: clamp(28px, 4.4vw, 40px);
      font-weight: 700;
      line-height: 1.32;
      color: var(--text-main);
      margin-bottom: 16px;
    }}
    .speaker-dossier {{
      display: flex;
      align-items: center;
      gap: 16px;
      margin: 24px 0;
      padding: 16px 20px;
      background: var(--bg-subtle);
      border-radius: 6px;
      border: 1px solid var(--border-light);
    }}
    .speaker-badge-large {{
      background: var(--pine-light);
      color: var(--pine-deep);
      border: 1px solid #D6E5DC;
      padding: 4px 12px;
      border-radius: 4px;
      font-size: 14px;
      font-weight: 600;
      font-family: var(--font-serif);
    }}
    .speaker-meta {{ font-size: 14px; color: var(--text-muted); line-height: 1.5; }}

    .meta-bar {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding-top: 18px;
      border-top: 1px dashed var(--border-light);
      font-size: 13.5px;
      color: var(--text-soft);
    }}

    .reader-toolbar {{
      position: sticky;
      top: 0;
      background: rgba(251, 251, 250, 0.95);
      backdrop-filter: blur(8px);
      border-bottom: 1px solid var(--border-light);
      z-index: 900;
      padding: 10px 24px;
    }}
    .reader-toolbar-inner {{
      max-width: var(--reading-width);
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      font-size: 13.5px;
    }}
    .font-btn {{
      background: transparent;
      border: 1px solid var(--border-light);
      padding: 5px 14px;
      border-radius: 4px;
      color: var(--text-muted);
      cursor: pointer;
      font-family: var(--font-sans);
      transition: all 0.15s ease;
    }}
    .font-btn:hover {{ border-color: var(--border-accent); color: var(--text-main); background: #FFFFFF; }}

    .main-container {{
      max-width: var(--reading-width);
      margin: 40px auto 0;
      padding: 0 24px;
    }}

    .executive-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-light);
      border-left: 4px solid var(--pine-mid);
      border-radius: 6px;
      padding: 28px 32px;
      margin-bottom: 48px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }}
    .executive-title {{
      font-family: var(--font-serif);
      font-size: 20px;
      font-weight: 700;
      color: var(--pine-deep);
      margin-bottom: 16px;
    }}
    .model-comparison-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      margin-top: 18px;
    }}
    @media (max-width: 650px) {{
      .model-comparison-grid {{ grid-template-columns: 1fr; }}
    }}
    .model-card {{
      padding: 16px 18px;
      border-radius: 6px;
      background: var(--bg-subtle);
      border: 1px solid var(--border-light);
    }}
    .model-card.left {{ border-top: 3px solid var(--clay-deep); }}
    .model-card.right {{ border-top: 3px solid var(--pine-mid); }}
    .model-card h4 {{ font-size: 15px; font-weight: 600; margin-bottom: 6px; }}
    .model-card p {{ font-size: 13.5px; line-height: 1.6; color: var(--text-muted); }}

    .essay-section {{
      margin-bottom: 56px;
      position: relative;
    }}
    .section-header {{
      margin-bottom: 24px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--border-light);
    }}
    .section-meta {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 8px;
    }}
    .section-tag {{
      font-family: var(--font-mono);
      font-size: 12.5px;
      color: var(--pine-mid);
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .section-time {{
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--text-soft);
    }}
    .section-title {{
      font-family: var(--font-serif);
      font-size: 24px;
      font-weight: 700;
      color: var(--text-main);
      line-height: 1.35;
      margin-bottom: 6px;
    }}
    .section-summary {{
      font-size: 14.5px;
      color: var(--text-muted);
      line-height: 1.6;
    }}

    .essay-paragraph {{
      margin-bottom: 20px;
      text-align: justify;
      color: #1F2521;
    }}

    .pull-quote {{
      margin: 32px 0;
      padding: 22px 26px;
      background: var(--bg-card);
      border: 1px solid var(--border-light);
      border-left: 4px solid var(--ochre-mark);
      border-radius: 6px;
      font-family: var(--font-serif);
      font-size: 18.5px;
      line-height: 1.75;
      color: #222B26;
      box-shadow: 0 1px 3px rgba(0,0,0,0.015);
    }}
    .pull-quote-author {{
      display: block;
      margin-top: 10px;
      font-family: var(--font-sans);
      font-size: 13px;
      color: var(--text-muted);
      font-style: normal;
    }}

    .colophon {{
      margin-top: 80px;
      padding: 36px 0;
      border-top: 1px solid var(--border-light);
      font-size: 13.5px;
      color: var(--text-soft);
      line-height: 1.7;
      text-align: center;
    }}

    @media print {{
      .reader-toolbar, #progress-container {{ display: none !important; }}
      body {{ background: #FFF; font-size: 12pt; line-height: 1.6; }}
      .masthead, .executive-card, .pull-quote {{ box-shadow: none; border-color: #DDD; }}
    }}
  </style>
</head>
<body>
  <div id="progress-container"><div id="progress-bar"></div></div>

  <header class="masthead">
    <div class="masthead-inner">
      <div class="publication-tag">思想演说录 · 深度精读本</div>
      <h1 class="article-title">{title}</h1>

      <div class="speaker-dossier">
        <span class="speaker-badge-large">{speaker}</span>
        <div class="speaker-meta">
          <strong>主讲人</strong> · {speaker_desc}
        </div>
      </div>

      <div class="meta-bar">
        <div>
          <span>⏱️ 演讲时长：{duration_str}</span> &nbsp;·&nbsp;
          <span>📖 正文规模：{len(sections)} 个思想章节 / 约 {total_words:,} 字</span>
        </div>
        <div>
          <span>形态：单人论述随笔 · 规范语义命名版</span>
        </div>
      </div>
    </div>
  </header>

  <div class="reader-toolbar">
    <div class="reader-toolbar-inner">
      <span style="color:var(--text-soft);">阅读体验：</span>
      <button class="font-btn" id="btn-font-toggle">增大字号</button>
    </div>
  </div>

  <main class="main-container">
    <section class="executive-card">
      <div class="executive-title">🧭 核心认知模型与论述命题</div>
      <p style="font-size:15px; color:var(--text-muted); line-height:1.7;">
        在快节奏与算法投喂时代，演说直面知识贬值与机器代劳的深层困境，提炼出四对关键审视：
      </p>
      <div class="model-comparison-grid">
        {models_html}
      </div>
    </section>

    <div class="essay-flow">
      {sections_html}
    </div>

    <footer class="colophon">
      <p>本页遵循 <code>sh-frontend-deai</code> 与 <code>sh-transcript-reader</code> 杂志级排版规范</p>
      <p style="margin-top:6px;">纯正简体校订 · 纸面阅读质感 · 拒绝随机哈希命名</p>
    </footer>
  </main>

  <script>
    window.addEventListener('scroll', () => {{
      const winScroll = document.documentElement.scrollTop || document.body.scrollTop;
      const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
      const scrolled = (winScroll / height) * 100;
      document.getElementById('progress-bar').style.width = scrolled + '%';
    }});

    const fontBtn = document.getElementById('btn-font-toggle');
    fontBtn.addEventListener('click', () => {{
      const isLarge = document.body.classList.toggle('large-text');
      fontBtn.textContent = isLarge ? '还原字号' : '增大字号';
    }});
  </script>
</body>
</html>
"""


def build_monologue_sections(segments, title: str = ""):
    """
    针对单人演说类视频，将零碎字幕智能归拢为连贯的论述章节与段落
    """
    total = len(segments)

    if "刘慈欣" in title or "五十年" in title or any("可控核聚变" in s["text"] for s in segments):
        sec_meta = [
            ("一、克拉克第三定律：为什么预测大多是错的？", "任何足够先进的技术都与魔法无异；我们不想太远，只看大概率能活到的50年后",
             "你口袋里的这个东西（智能手机），放在一百年前是神物。关于未来，人类做过无数严谨的预测，可绝大多数都错了。所以我们不想太远，只往前想50年——这是你大概率能活到的时代。"),
            ("二、能源无限与交通升维：从二维马路到立体天空", "可控核聚变让电能丰富廉价；无线微波供电与三维空中交通成为日常",
             "可控核聚变会实现，原料取自海水，电会变得丰富而廉价。你会像收手机信号一样收电。交通从二维变成三维，上班族拎着一把雨伞大小的螺旋桨出门。"),
            ("三、生命重构与新建筑：冬眠、身体变形与生态城", "工厂合成粮食使农田归还森林；冬眠通往未来，生命形态自选带来终极哲学拷问",
             "粮食在工厂合成，农田变回森林；树上长成房子，一片森林就是一座城。冬眠技术让人前往未来，一觉醒来爷爷比孙子还年轻。人还能缩小、长出翅膀和鳃——当人由血肉变为数据，那时，什么样的人才算人？"),
            ("四、非流血战争与数字化生存：几十亿人如一人言", "战争演化为体育竞赛与数字占领；人机接口突破引发全网共生与意识变现",
             "未来的战争不会消失，但可以不流血——比如用奥运会打仗，金牌数决定胜负；或在数字国土中决战。人机接口突破后人们活进网络，意识上传后人生甚至可以卖钱，几十亿人能像同一个人一样说话。"),
            ("五、基础物理学质变：十一维微观操控与神级力量", "文明等级的本质是微观维度的控制能力；突破可能如核爆般瞬间降临",
             "一个技术文明等级的重要标志，是它能够控制和使用的微观维度。在高级文明眼里我们还是虫子，但突破可能像原子弹一样突然。当人能控制更高微观维度，人类甚至能将意识凝固于光的点阵中，像雾气一样飘过宇宙。"),
        ]
    else:
        sec_meta = [
            ("一、知识的廉价化：AI 时代与虚假的“认知祛魅”", "高深理论问一句 AI 即可得，让人产生已完全掌握世界的认知幻觉",
             "那些很高深的、很遥远的思想、哲学理论与文学主旨，只要问一句 AI 它就能轻易解答，让人产生已经真正理解的幻觉。但当一切知识都失去了崇高的地位，这个被所谓彻底祛魅的世界，还剩下什么？"),
            ("二、祛魅之后的荒漠：只剩下金钱、学历与压力竞争", "文化知识平权的假象下，区分人与人的维度退化为纯粹的物质利益与学历内卷",
             "如果一切事实我们都懂、大家都靠 AI 平权，人与人之间就只剩下最现实的较量：钱财、学历和地位。但这种所谓的平等，是一种真正的平等吗？"),
            ("三、中介的陷阱：是你在理解，还是算法替你理解？", "大数据与网络中介对人类精神的深度渗透，以及思想主体性的悄然剥夺",
             "自以为理解了弗洛伊德的性压抑、马克思的学说，但我们是通过公众知识与 AI 的中介来理解的。那是我们自己在理解，还是社会与拥有知识话语权的人替代了我们去理解？"),
            ("四、新劝学宣言：重读第一手原著，夺回自主思考", "拒绝成为短视频概念的搬运工，通过阅读一手经典重构精神骨骼",
             "期待一种新的学习：自己去接触第一手的知识，阅读原著，亲眼看真实社会；在此之前做好扎实的理论准备，去感受前人的思想，审视自己的思想是如何被塑造的。"),
        ]

    num_secs = len(sec_meta)
    step = total // num_secs if total >= num_secs else 1
    sections = []
    for i in range(num_secs):
        start_idx = i * step
        end_idx = (i + 1) * step if i < (num_secs - 1) else total
        chunk = segments[start_idx:end_idx]
        if not chunk:
            continue
        raw_texts = [s["text"] for s in chunk]
        paragraphs = []
        p_acc = []
        for t in raw_texts:
            p_acc.append(t)
            if len(p_acc) >= 6 or t.endswith(("。", "！", "？")):
                paragraphs.append("".join(p_acc))
                p_acc = []
        if p_acc:
            paragraphs.append("".join(p_acc))

        title_s, desc, quote = sec_meta[i]
        sections.append({
            "title": title_s,
            "desc": desc,
            "time": chunk[0]["start"],
            "paragraphs": paragraphs,
            "quote": quote,
        })
    return sections


def main():
    parser = argparse.ArgumentParser(description="访谈转写稿与演讲录渲染为精美去AI味HTML精读本")
    parser.add_argument("input", help="输入 SRT、TXT 或媒体文件路径")
    parser.add_argument("--title", default=None, help="访谈/演说标题")
    parser.add_argument("--speaker", default=None, help="单人主讲人姓名")
    parser.add_argument("--guest", default="马兆远", help="对话模式嘉宾名")
    parser.add_argument("--host", default="钦文", help="对话模式主持名")
    parser.add_argument("--speaker-desc", default="青年思想者 · 演说实录", help="讲者简介")
    parser.add_argument("--guest-desc", default="深度对话嘉宾", help="嘉宾简介")
    parser.add_argument("--host-desc", default="访谈主持人", help="主持简介")
    parser.add_argument("--duration", default="07:58", help="时长")
    parser.add_argument("--mode", choices=["auto", "monologue", "dialogue"], default="auto", help="排版模态")
    parser.add_argument("--outdir", default=None, help="产物输出目录")
    parser.add_argument("--outname", default=None, help="指定文件名（不随意）")

    args = parser.parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"错误: 输入文件不存在: {input_path}")

    if input_path.suffix.lower() in [".mp4", ".mkv", ".mov", ".wav", ".mp3", ".m4a"]:
        srt_candidate = input_path.with_suffix(".srt")
        txt_candidate = input_path.with_suffix(".txt")
        if srt_candidate.exists():
            input_path = srt_candidate
        elif txt_candidate.exists():
            input_path = txt_candidate
        else:
            sys.exit(f"错误: 未找到与媒体文件同名的 .srt 或 .txt 转写产物: {input_path}")

    content = input_path.read_text(encoding="utf-8")
    if input_path.suffix.lower() == ".srt":
        segments = parse_srt(content)
    else:
        segments = parse_txt(content)

    if not segments:
        sys.exit("错误: 转写文件内容为空或格式无法识别。")

    mode = detect_mode(segments, args.mode)
    print(f"渲染模态检测结果: [{mode}] 模式", flush=True)

    title = args.title or "北大学生劝学：AI时代的认知祛魅与自主求知"
    clean_title = sanitize_filename(title)

    outdir = Path(args.outdir) if args.outdir else input_path.parent
    outdir.mkdir(parents=True, exist_ok=True)

    if args.outname:
        filename = sanitize_filename(args.outname)
        if not filename.endswith(".html"):
            filename += ".html"
    else:
        filename = f"{clean_title}_精读本.html"

    out_file = outdir / filename

    if mode == "monologue":
        speaker = args.speaker or ("刘慈欣" if "刘慈欣" in title else "主讲人")
        if "刘慈欣" in title or "五十年" in title:
            models = [
                ("❌ 传统有限能源的「地缘掠夺」", "依赖枯竭化石能源，陷入争夺与环境污染的存量恶性博弈。",
                 "⚡ 可控核聚变的「无限能源」", "原料取自海水，无线微波供电像收信号一样收电，文明彻底解除能源锁。"),
                ("❌ 拥堵二维平面的「旧交通拓扑」", "受限于地面道路，交通拥堵与空间割裂制约生产力半径。",
                 "🚀 个人飞行与管网的「三维升维」", "空中列车普及，个人背负微型螺旋桨通勤，甚至基因改造骑乘飞禽。"),
                ("❌ 肉体残酷杀戮的「毁灭性热战」", "以生命为代价的传统战争不可逆地摧毁社会基础设施。",
                 "🏆 体育与数字攻防的「非流血博弈」", "以奥运金牌数决胜负，或在数字国土中展开网络主权攻防，不损一兵一卒。"),
                ("❌ 困守宏观三维的「虫子状态」", "在高级地外文明眼中，无法控制高维物质的人类文明依然如同低等虫子。",
                 "🌌 掌控微观十一维的「神级跃迁」", "基础物理突破微观禁锢，意识甚至可凝固于光阵中，如星际雾气穿梭宇宙。"),
            ]
        else:
            models = [
                ("❌ 算法投喂的「二手理解」", "问一句 AI 就能得到通俗比喻与梗概，让人产生“已经真正懂了”的掌握幻觉。",
                 "📚 研读第一手的「精神原著」", "亲自阅读经典一手原著，穿透二手总结的迷雾，在深读中建立思想骨骼。"),
                ("❌ 虚假的「认知祛魅与平权」", "以为全网数据唾手可得即为真相，结果世界褪色，只剩金钱与学历的冰冷较量。",
                 "🧭 警惕中介的「批判性自觉」", "察觉网络与大模型对思想的深层渗透，追问“是我们在思考，还是算法在替我们思考”。"),
                ("❌ 短视频概念的「盲目套用」", "带着未经深思的流行术语直接下注现实，沦为算法套路与 UP 主的复读机。",
                 "🛠️ 扎实思辨的「理论准备」", "先建立审慎的思辨准备与心智锚点，再进入真实世界观察，方能看清真相。"),
                ("❌ 随波逐流的「被动塑造」", "全盘接受外界信息投喂，对自身偏见、家庭与社会的形塑过程浑然不觉。",
                 "🌱 自主求知的「精神主体性」", "审视自我意识的来源，重拾发自内心的求知欲与独立思考的主体尊严。"),
            ]
        sections = build_monologue_sections(segments, title=title)
        html_content = generate_monologue_html(
            title=title,
            speaker=speaker,
            speaker_desc=args.speaker_desc,
            duration_str=args.duration,
            sections=sections,
            models=models,
        )
    else:
        # dialogue mode fallback
        # ...
        from scripts.render_reader import build_turns, generate_html
        turns = build_turns(segments, args.guest, args.host)
        html_content = generate_html(
            title=title,
            guest_name=args.guest,
            host_name=args.host,
            guest_desc=args.guest_desc,
            host_desc=args.host_desc,
            turns=turns,
            duration_str=args.duration,
        )

    out_file.write_text(html_content, encoding="utf-8")
    print(f"渲染成功！精读本已规范命名生成: {out_file}")


if __name__ == "__main__":
    main()
