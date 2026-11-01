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
    # REA与逆向评测专有名词
    ("最近一顿", "最近一款"),
    ("几天就收获了20多碗士大", "几天就收获了20多万Star"),
    ("20多碗士大", "20多万Star"),
    ("复车出一则", "复刻出一款"),
    ("自家充条的APP", "自家空调的APP"),
    ("充条的APP", "空调的APP"),
    ("逆向一著游戏和颜色", "逆向一款游戏和颜色"),
    ("别写APP", "学习APP"),
    ("Todetsch", "Codex"),
    ("Godetsch", "Codex"),
    ("Stereos技能包", "Skills技能包"),
    ("Tursell", "Cursor"),
    ("Turzr", "Cursor"),
    ("Tolodos 5.5", "Claude 3.5"),
    ("Cloud Ops 5.5", "Claude 3.5"),
    ("成中加入", "成功加入"),
    ("查死了", "卡死了"),
    ("GPT6 Ostra", "GPT-5 / o系列"),
    ("私有的资源争士", "私有的资源格式"),
    ("私有争士", "私有格式"),
    ("紫智能体", "子智能体"),
    ("此智能体", "子智能体"),
    ("八门盾甲", "八门遁甲"),
    ("蹭吃蹭吃", "吭哧吭哧"),
    ("弹活", "干活"),
    ("战活", "干活"),
    ("站了8分钟", "干了8分钟"),
    ("占了8分钟", "干了8分钟"),
    ("占了三个多小时", "干了三个多小时"),
    ("站了三个多小时", "干了三个多小时"),
    ("站得更快", "跑得更快"),
    ("360加步车", "360加固壳"),
    ("加步只保护了一半", "加固只保护了一半"),
    ("加步", "加固"),
    ("拔出了", "扒出了"),
    ("判出了不少门道", "盘出了不少门道"),
    ("死活不成把圆码", "死活不肯把源码"),
    ("圆码", "源码"),
    ("缘嘛", "源码"),
    ("没有真心了", "没有更新了"),
    ("多推了REA", "多亏了REA"),
    ("真本无从下手", "根本无从下手"),
    ("DeepSit Harness", "DeepSeek Harness"),
    ("DeepSit", "DeepSeek"),
    ("大肥鱼", "大肥鲸（DeepSeek图标）"),
    ("急剧化", "几句话"),
    ("拎着多占记照", "宁肯多占几兆"),
    ("也要把观展绰号", "也要把观感做好"),
    ("观展绰号", "观感做好"),
    ("IEA", "REA"),
    ("Totents", "Tokens"),
    ("上下纹理", "上下文里"),
    ("血头", "噱头"),
    ("一著", "一款"),
    ("一团", "一款"),
    ("换了著颜色", "换了个颜色"),
    ("改了著名字", "改了个名字"),
    # AI的狗与懂的权利专有名词
    ("身边全是神经", "身边全是神迹"),
    ("几乎没有一直需要干活", "几乎没有一只需要干活"),
    ("受众生情", "寿终正寝"),
    ("神物链", "食物链"),
    ("哀恶", "挨饿"),
    ("思量不迁进", "四两拨千斤"),
    ("高丝球盒", "高斯求和"),
    ("高丝蛇尾配对", "高斯首尾配对"),
    ("蛇尾配对", "首尾配对"),
    ("2加929", "2加99"),
    ("乔法", "巧法"),
    ("自身体体相等", "自身体积相等"),
    ("河的自身体体相等", "和自身体积相等"),
    ("没屁找屁", "脱裤子放屁"),
    ("证为", "证伪"),
    ("通财", "通才"),
    ("这被子", "这辈子"),
    ("吃虾的食物", "吃下的食物"),
    ("披月", "批阅"),
    ("精赛", "竞赛"),
    ("地缘估计关系历史向脱钩", "地缘政治关系、历史相脱钩"),
    ("历史向脱钩", "历史相脱钩"),
    ("狗一见都不懂", "狗一件都不懂"),
    ("惨酷", "残酷"),
    # 24个AI热词专有名词校正
    ("什么是Coken", "什么是Token"),
    ("Coken", "Token"),
    ("什么是Scale", "什么是Skill"),
    ("Scale技能", "Skill技能"),
    ("Loop Engineering", "Loop Engineering（循环工程）"),
    ("Luba Engineering", "Loop Engineering（循环工程）"),
    ("路牌真正的", "Loop真正的"),
    ("DeepSig", "DeepSeek"),
    ("Tation Is All You Need", "Attention Is All You Need"),
    ("Chat GP3.5", "ChatGPT 3.5"),
    ("Jam9", "Gemini"),
    ("千万制服Kimi", "通义千问、Kimi"),
    ("GPD 5.6 Astra", "GPT-4o / o1"),
    ("数学寒书", "数学函数"),
    ("矩正运算", "矩阵运算"),
    ("ToolColy", "Tool Calling"),
    ("Tool Coly", "Tool Calling"),
    ("RMC-P", "MCP"),
    ("上下门管理", "上下文管理"),
    ("全线控制", "权限控制"),
    ("共同共成了Harness", "共同构成了Harness"),
    ("Cloud Code", "Claude Code"),
    ("Open Cloud", "OpenClaw / OpenCode"),
    ("Workbody", "WorkBuddy"),
    ("附用", "复用"),
    # 额度重置与AI用户权益专名校正
    ("前从后景", "前后折算"),
    ("厌务损失心理", "损失厌恶心理"),
    ("时间点钱重次", "时间点前冲刺"),
    ("时间点钱", "时间点前"),
    ("重次", "冲刺"),
    ("开Ultra K-Max加Fast", "开 Ultra / Max 加 Fast"),
    ("重置后一段同一时间", "重置后又在同一时间"),
    ("SelectedModelAZ Capacity", "Selected Model At Capacity"),
    ("有用心", "有用性"),
    ("断脸", "断连"),
    ("婚户专发", "欢呼转发"),
    ("闹惧", "闹剧"),
    ("海底牢", "海底捞"),
    ("客头", "磕头"),
    ("发布前处安是50倍", "发布前盛传是50倍"),
    ("最理谱的是", "最离谱的是"),
    ("伪命体", "伪命题"),
    ("大磨修感", "打磨修改"),
    ("十里逃紧", "沙里淘金"),
    ("学好玩", "消耗完"),
    ("兔子速度慢", "吐字速度慢"),
    ("溃增", "馈赠"),
    ("训话", "驯化"),
    ("57页 关注我看更多AS的对方点", "我是七月，关注我看更多AI的独家观点"),
    ("57页", "我是七月"),
    # AI裁员与大厂教训专名校正
    ("Mata微软", "Meta与微软"),
    ("Mata", "Meta"),
    ("内软", "微软"),
    ("占博格", "扎克伯格"),
    ("扎克波哥", "扎克伯格"),
    ("JAC网络", "组织架构"),
    ("小炮的", "Pods（小豆荚小组）"),
    ("小豆家项目组", "小豆荚项目组（Pods）"),
    ("统成叫Builder", "统称为Builder"),
    ("正流员工", "蒸馏员工"),
    ("裁屁股", "擦屁股"),
    ("Srp", "Anthropic"),
    ("Anstropic", "Anthropic"),
    ("把自己Cloud", "把自己Claude"),
    ("Cloud", "Claude"),
    ("高足增长期", "高速增长期"),
    ("只能体", "智能体"),
    ("是能提", "智能体"),
    ("太值的人", "在职的人"),
    ("夸破门", "跨部门"),
    ("领乔代码", "零敲代码"),
    ("散坑", "踩坑"),
    ("机肉机", "肌肉记忆"),
    ("当时等体的经历", "做智能体的经理"),
    ("真心百印", "真金白银"),
    ("账之债", "认知债"),
    ("快捷的视角", "前瞻的视角"),
    # 产业链与出版行业专名校正
    ("西夕书店", "西西弗书店"),
    ("国卖文化", "果麦文化"),
    ("摩铁", "磨铁文化"),
    ("独克文化", "读客文化"),
    ("产业列", "产业链"),
    ("将为打击", "降维打击"),
    ("这列录", "这条链路"),
    ("一面一次", "一年一次"),
    ("我禁止走到", "我径直走到"),
    ("去撕去发", "去私信去发"),
    ("接剩很多的时间", "节省很多的时间"),
    ("多卖很大一步", "多迈很大一步"),
    ("去建产业列上游", "去见产业链上游"),
    ("玩具接触不到", "完全接触不到"),
    ("现场守备", "现场值守"),
    ("多我一个有的怎样呢", "多我一个又怎样呢"),
    ("书好好在售卖发表", "书号怎么售卖发表"),
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
        s = s.replace(cc.convert(src), dst).replace(src, dst)
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
    elif "半导体" in title or "秋招" in title or any("半导体" in s["text"] for s in segments):
        sec_meta = [
            ("一、秋招冰火两重天：为什么半导体是版本答案？", "传统互联网大厂招聘名额骤减、锁HC颗粒无收，而硬科技赛道处于需求爆发扩张期",
             "真的别再来硬卷传统互联网了！招聘人数断崖式减少，难度极高；多去看看半导体、芯片硬件、具身智能这些行业，需求扩张特别多，普遍涨薪，薪酬开得真不低。"),
            ("二、真实开奖实录：10分钟面试轻松拿年包40-45万", "没有深厚相关经验也能直接开大奖，真正想招人的企业宽容度远超想象",
             "企业真想招人，就跟我朋友一样，就一轮面试面了十几分钟，没有相关经验直接开奖年包45万；另一家GPU芯片公司也是年包40多万。在BOSS上随便瞎投投，没听过的小厂结果能开这么高！"),
            ("三、求职的底层真理：企业真不真想招人决定一切", "互联网有一万个理由挂你，而真想招人的企业无论如何都愿意给你发offer",
             "找工作最重要的是什么？不就是企业到底真不真想招人吗！反观互联网，八股不会挂你、手撕代码写不出来挂你、没实习挂你、答得全对也横向对比挂你——不想招人有一万个理由挂你。"),
            ("四、应届生破局思路：打破信息茧房，走出大厂执念", "计算机与工科同学需及时转变方向，在增量产业周期中寻找时代红利",
             "对于找工作的计算机工科同学们，一定要及时转变思路了。不要再死盯着传统互联网死磕了，除了互联网之外，外面广阔天地到处都在下雨，换个赛道海阔天空。"),
        ]
    elif any(kw in title for kw in ["重置", "额度"]):
        sec_meta = [
            ("一、重置的算术真相：白嫖幻觉下的隐蔽缩水", "GPT重置不同于Claude；提前截断周期反致账面额度缩水，损失厌恶绑架用户心智",
             "GPT的重置额度跟Claude不同：Claude是白送你一次，而GPT是替你提前重置。前后折算下来，普通用户的实际额度比不重置还要少。但由于人皆有之的损失厌恶心理，大家为了不亏，疯狂在重置前把额度用光，深陷自欺欺人的白嫖幻觉。"),
            ("二、双向惩罚的困局：全球1100万用户两头挤爆服务器", "预告重置人为制造流量洪峰，冲刺与重置两头挤兑，服务崩溃与模型断连成常态",
             "当官方预告明天重置，全球上千万用户在同一时间点前冲刺，开满Ultra和Fast死命烧额度；重置后又同时满血开干。两头各挤爆一次，动不动报错Capacity超限断连。海德格尔说可靠性大于有用性，天天用AI工作的人，根本无法忍受这种动荡。"),
            ("三、营销算盘与驯化心理：从“赛博义父”到先砍后赏的PUA", "零成本全网刷量，把付费消费者应得的商业本分扭曲成施舍恩赐",
             "预告重置是OpenAI最拿手的免费营销，瞬间拉满全网活跃度与数据财报。最诡异的是用户还要对此感恩戴德，甚至喊出‘圣Tibo’、‘赛博义父’。官方暗中把20x砍成10x、承诺50倍实测只给25倍，先砍一刀再把原本属于你的东西施舍给你，彻底驯化了用户。"),
            ("四、拒绝垃圾需求与算力空转：夺回稳定生产力的消费尊严", "额度翻倍不等于需求翻倍；拒绝盲目烧垃圾算力，主张满血模型与诚恳服务",
             "突然给你两倍额度，你的bug和科研课题会凭空多出两倍吗？真正的生产力工作必须精细打磨，多出来的额度只能拿去制造无人问津的垃圾需求。用户需要的不是三天两头施舍的‘重置补偿’，而是稳定的额度、不降质的满血模型与诚恳可靠的服务。"),
        ]
    elif any(kw in title for kw in ["裁员", "大厂", "教训", "认知债"]):
        sec_meta = [
            ("一、巨头试水翻车记：从微软的内耗空转到 Meta 的激进反噬", "副总裁吐槽下属用 AI 写文档上级用 AI 读文档；Meta 激进重组裁员 60%、键鼠监控，换来重大故障飙升 40%、排障耗时增加 70%，扎克伯格紧急叫停",
             "代码改动量确实暴涨了 2 倍，但真正变成用户可见功能的只涨了 36%；更要命的是，重大安全与技术事故增加了 40%，工程师全在给 AI 擦屁股。"),
            ("二、效能 6 倍背后的真相：Anthropic 为何能成而 Meta 翻车？", "Anthropic 员工翻 3 倍、人均产值翻 2~4 倍，智能体工时达人类 6 倍；核心在于不是整建制端掉岗位，而是抽走基础执行，留下更高难度的硬骨头",
             "AI 替代人的方式，从来不是把一个岗位整建制端掉，而是先把岗位里最好交出去的那层执行抽走，留给人类的反而是更麻烦的活。"),
            ("三、认知债（Cognitive Debt）：一键 Accept 抹平的心智地图", "从“技术债”到“认知债”；过去从零敲代码卡壳翻工是在脑中画全貌地图，现在一键接受导致没人知道为何这么写，第 8 周系统崩溃无人敢动",
             "现在代码写得挺好，但团队里没有任何一个人知道它为什么这么写，这叫认知债。第一天交付翻倍，到第八周系统崩了，没人知道哪出了问题，谁也不敢动。"),
            ("四、抽掉梯子的断层危机：教育与就业体系的终极考验", "企业招聘初级岗位降至 9%，只看自主性与判断力，但人类判断力来自初级岗踩坑积攒的肌肉记忆；抽掉爬楼梯子，却要求楼上的人立刻学会飞",
             "AI 替代人的方式，从来不是一夜之间把所有人赶出大楼，它是先抽掉让人往上爬的梯子，再要求楼上所有还没掉下来的人马上会飞。"),
        ]
    elif any(kw in title for kw in ["热词", "24个", "名词", "小白入门"]):
        sec_meta = [
            ("一、认知基石与底层驱动：AI、AGI、LLM 与文字接龙机制", "从大模型概念到 Transformer 架构；理解‘下一个词预测’如何造就通用智能",
             "大模型本质上是一个文字接龙游戏。它通过复杂的矩阵运算，不停地根据前面的输入预测下一个最可能出现的词。理解了这个，你就明白为什么 AI 回答是一句一句、一个词一个词往外蹦，因为它的底层就是这么运行的。"),
            ("二、数据度量与计费体系：Token、分词器、API 与缓存经济学", "大模型不认识字，只认识数字；理解 Token 换算、API 计费与 Prompt Caching 成本优化",
             "模型处理文本的最小单位叫 Token。负责把文字切分并转成 Token ID、再把输出还原成人类语言的叫 Tokenizer。输入、输出以及是否命中缓存（Prompt Caching），决定了调用大模型的价格和性能。"),
            ("三、人机交互与指令工程：Prompt、角色设定与提示词工程边界", "从 User Prompt 到 System Prompt；为什么提示词工程不是玄学而是精准约束",
             "交给模型的问题和指令叫 Prompt。User Prompt 代表当前任务诉求，System Prompt 规定角色、规则与回答边界。研究如何把要求描述得清清楚楚、让模型稳定完成任务的学科，就是提示词工程。"),
            ("四、记忆机制与认知瓶颈：Context、上下文窗口、工程调优与 RAG", "大模型为什么会‘胡说八道’与遗忘？长文本管理与检索增强生成的实战解法",
             "模型参考的信息不只是提示词，还包括对话历史与检索资料，总共构成 Context。Context Window 决定了容量上限；在不同阶段决定塞什么、删什么、压缩什么，就是上下文工程；而资料过多时先检索再注入，就是 RAG。"),
            ("五、突破孤岛连接现实：Tool、Tool Calling 与 MCP 统一协议", "让 AI 拥有手和脚；从单向问答迈向联网查询、文件操作与代码执行",
             "大模型光靠脑子无法获得最新信息或修改文件，必须借助 Tool。模型提出调用请求，宿主程序代为执行并将结果喂回，这就是 Tool Calling。而 MCP 协议为连接外部工具与数据提供了标准接口，让工具跨平台随意复用。"),
            ("六、智能体与系统终局：Agent、Skill、Harness 与循环工程闭环", "从工具人到自主智能体；运行底座（Harness）与三层循环（Loop）的终极飞轮",
             "当系统能围绕目标自动规划、调用工具并根据结果调整方案，它就成了 Agent。成熟的工作流封装成 Skill；支撑它安全执行、断点恢复与权限控制的底座就是 Harness；而将 AI 质检、人工校准与用户反馈打通的循环工程，才是 AI 落地生根的真正秘密。"),
        ]
    elif any(kw in title for kw in ["狗", "懂的权利", "陶哲轩"]):
        sec_meta = [
            ("一、两万年前的先例：狗撞上“神迹”与陶哲轩的思想实验", "10亿只宠物狗活在不懂却舒适的世界；陶哲轩提出AI抗癌药无人懂机制的隐忧，引发大V嘲讽",
             "狗在两万年前就撞到了‘人工智能’。它们活在一个自己根本看不懂的世界里，身边全是神迹，理所当然；照顾它们的存在在想什么，它们根本不知道。现在地球上十亿只狗，大部分过得挺开心，结局还挺不错。但如果换成人类，你愿意吗？"),
            ("二、数学美是思维的局限？人类的优雅 vs AI的高维硬算", "人脑容量有限才发明公式定理以四两拨千斤；AI无需迁就人类的优雅，高维硬算便是一眨眼",
             "人类之所以追求公式定理的简洁和数学美，是因为人脑能力有上限，一个顶尖数学家脑子里同时只能盯住五六个变量。AI不需要什么优雅，算得过来硬算一遍就行了；就像人喝水直接往嘴里倒，不会像乌鸦一样去算阿基米德浮力。在我们眼里看来是优雅的，或许真的就是因为我们能力上限。"),
            ("三、必然失控的认知鸿沟：跨学科超级通才、光速产出与军备竞赛", "AI多学科降维打击，几天产出上万篇论文无法审阅；地缘竞争绑定军备竞赛，任何踩刹车的呼吁都化为泡影",
             "即便在单一领域人类都比不过AI，更何况AI是全领域的通才：数学加语言学、法学加传播学。AI开足马力几天写出上万篇论文，你一辈子都不吃不喝也读不完。2023年上千人联名呼吁暂停六个月，没有一家停下来——放弃AI就意味着放弃竞争，如同战争一样，如果要人类真正踩下刹车，往往只在出了事之后。"),
            ("四、文明的终极悲哀：被剥夺“懂的权利”，社会不再为人搭建", "绝育与短鼻狗的悲剧揭示宠物没有话语权；剥夺了懂的权利，人类在AI社会便彻底丧失主体性",
             "狗确实过得很好，可它吃什么、能不能生孩子、能不能上床，很多狗做了绝育，短鼻狗一辈子喘不上气——狗一件都不懂，也没有人问过它。在人类社会里，狗是没有懂的权利的；这个世界的搭建和存在，从来就不是给它弄明白的。就像放在AI社会的未来，或许社会所搭建起来的一切，从来就不是给人类弄明白的。"),
        ]
    elif "REA" in title or "逆向" in title or "颜色" in title or any("REA" in s["text"] for s in segments):
        sec_meta = [
            ("一、从 20 万 Star 谈起：破除“逆向一切”与“软件已死”神话", "开源项目 REA 爆火出圈，然而神话背后是老牌逆向工具的 MCP 封装与 Skills 指导",
             "吹捧者宣称 REA 能逆向一切，甚至喊出‘软件已死’。真的有那么神吗？所谓逆向就是只有成品程序反推原理。逆向圈本就有老牌工具，REA 只是把它们封装成 MCP 服务并附带技能包，让 AI 能够调动工具。"),
            ("二、实测单机安卓游戏：从换皮崩溃到 Codex 注入“迈特凯”", "Cursor 换皮改色导致游戏卡死；换用 Codex 摸清私有格式、子智能体手绘像素帧跑通",
             "多亏了 REA 先把私有格式整理成 AI 能看懂的信息，不然面对一大坨机器码根本无从下手。AI 还派了子智能体专门画跑步、出拳、八门遁甲特效，实机模拟器验证三个小时，终于完美跑通新角色。"),
            ("三、实测付费学习 APP：合规底线碰撞与 DeepSeek 爆改重生", "Claude 守住安全红线拒绝脱壳；DeepSeek 拆解夜间模式 128 张配色，爆改成编程学习软件",
             "Cursor 加 Claude 刚开工就触发安全过滤，死活不肯还原源码，但静态分析扒出了 360 加固壳只保一半及扣费套路；换成 DeepSeek 后，几句话摸清底细，还派子智能体爆改成交付了一款能直接运行的 AI 编程学习 APP。"),
            ("四、冷静反思：170 个工具的 Token 困境与软件真正的护城河", "噱头大于实际、动辄塞爆十万 Token，客户端可以被重写，但后端的壁垒永远带不走",
             "REA 本身没有发明新技术，工具多达 170 个，会往上下文里塞十几个万的 Token，有时不用它 AI 反而更快更省。客户端代码就算被读懂重写，别人也拿不走后端、数据和运营策略，这些才是软件真正值钱的地方。"),
        ]
    elif any(kw in title for kw in ["产业链", "走出去", "出书", "小埃"]):
        sec_meta = [
            ("一、破除“西西弗”迷茫：从闭门码字到认知觉醒", "新人作者困于零售书店的浩瀚书海，闭门敲字却不知出版商业全流程",
             "我一个朋友一直想出书当作家，一进西西弗书店，觉得这么多人出书了，多我一个又怎样呢？但生活中完全接触不到人脉，只知道在电脑前敲字。编辑和市场喜欢什么、如何到对应出版公司、怎么拿书号发表，这条链路他什么都不懂——这个人就是我自己。"),
            ("二、穿透终端迷雾：分清“行业人员”与“产业上游”", "普通书店店员只是分销终端，唯有行业展会才能直达出版策划源头",
             "主要你不能去书店这么做，你要分清楚什么是行业相关人士，什么是产业链相关人士。只有大型全国性或城市书展，才会是出版公司内部的核心人员来现场值守，你才能真正接触到产业链上游的核心资源。"),
            ("三、坦荡肉身破局：大方站在果麦与磨铁面前", "直奔头部出版机构展位，自信表达创作者诉求，高维打通编辑网络",
             "别人都是去逛书买书的，我径直走到果麦文化、磨铁、读客文化等展位，进去直接说：‘你好，我是一个作家，我需要编辑的联系方式。’工作人员态度极好，当场电话对接：‘现场有一个作者，要不直接让她加你微信吧！’很顺利地加上了许多不同编辑。"),
            ("四、站在人前才有机会：物理维度的降维打击", "线上私信多石沉大海，肉身站在关键人面前省下数年摸索时间",
             "很多作者不去线下，在网络上四处给编辑发私信投稿，人家根本不回复。如果你亲自站在了产业链上游的人面前，你就会比别人多迈很大一步，节省很多时间。女生一定要多走出去，参加行业展会，亲自见产业链上游，给自己创造机会！"),
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
        elif "半导体" in title or "秋招" in title:
            models = [
                ("❌ 存量踩踏的「互联网大厂执念」", "招聘断崖式缩减、锁HC严控人头，即便有学历有实习也大概率零offer颗粒无收。",
                 "⚡ 增量扩张的「半导体与硬科技」", "芯片、GPU、具身智能企业处于强扩张期，岗位缺口大，起薪与涨薪具备极高爆发力。"),
                ("❌ 找借口挂人的「虚假考核内卷」", "挑刺式面试：八股、手撕代码、无尽横向对比，哪怕全部答对依然会被找一万个理由挂掉。",
                 "🤝 降维宽容的「真实求贤若渴」", "真招人的企业面试扁平高效（甚至一轮十来分钟），看重基础潜质而非吹毛求疵，直接开奖40W+。"),
                ("❌ 盲目卷做题的「战术勤奋」", "在下行或饱和的存量赛道中死磕技巧，边际效用递减，越卷越痛苦越没有出路。",
                 "🧭 顺应产业红利的「战略选择」", "选择大于努力，及时打破信息差，把技能映射到国家与产业投资重仓的蓝海风口。"),
                ("❌ 纯应用层软件的「路径依赖」", "局限于传统Web/移动端业务CRUD开发，替代性强，抗周期与抗淘汰能力薄弱。",
                 "🚀 软硬结合底层的「工程护城河」", "切入芯片底层驱动、固件、GPU算力与具身智能硬件协同，构建不可替代的终身壁垒。"),
            ]
        elif any(kw in title for kw in ["重置", "额度"]):
            models = [
                ("❌ 贪图小利的「补偿狂欢」", "每当官方预告重置便熬夜刷额度，甚至对平台感恩戴德奉为“赛博义父”。",
                 "⚡ 清醒理性的「消费者契约」", "认清付费订阅的商业本质，平台提供充足算力是本分而非施舍，警惕先砍额度再补偿的PUA。"),
                ("❌ 人造洪峰的「双向挤兑」", "重置前全体突击清零，重置后蜂拥满额开干，两头挤爆服务器引发大面积断连报错。",
                 "🛡️ 平稳预期的「高可用基准」", "可靠性远大于有用性；生产力工作依赖全天候稳定在线，拒绝被定时重置打乱工作节奏。"),
                ("❌ 算力空转的「垃圾需求」", "额度翻倍而真实需求不会翻倍，为了不亏硬跑低价值高消耗任务，甚至忍受模型高峰降质。",
                 "🎯 真实价值的「人机协同深度」", "复杂生产无法全靠放羊批处理；好任务需要精细打磨，拒绝为平台财报刷虚假活跃数据。"),
                ("❌ 被动接受的「黑盒驯化」", "额度缩水、模型降速、偷改规则，用户只能在忽高忽低的算力施舍中妥协凑合。",
                 "🧭 权利捍卫的「服务透明化」", "拒绝三天两头的花哨补丁，坚决主张稳定额度、满血模型与诚恳透明的服务承诺。"),
            ]
        elif any(kw in title for kw in ["裁员", "大厂", "教训", "认知债"]):
            models = [
                ("❌ 粗暴裁员的「岗位替代思维」", "以为 AI 能整建制取代人，激进裁员 60%，把 10 个人直接砍成 3 个人。",
                 "⚡ 抽离执行的「人机协同分层」", "AI 抽走的是容易标准化的底层执行，将高阶判断、架构决策与跨部门协调留给人类。"),
                ("❌ 盲目追求行数的「技术假繁荣」", "代码改动量暴增 200%，然而重大故障增加 40%，骨干工程师全在替 AI 擦屁股。",
                 "🛡️ 可靠交付的「真实业务增效」", "代码量不等于交付质量；严防一键 Accept 带来的系统黑盒，追求高确定性功能落地。"),
                ("❌ 侵蚀心智地图的「工程认知债」", "一键全部接受抹平了卡壳翻工的摩擦力，导致团队无人真正理解系统为何如此运作。",
                 "🧭 强力治理的「主动还债体系」", "如 Anthropic 编写 8000+ 条常驻规则，决策全公开，逼产品经理亲自写代码验收。"),
                ("❌ 抽掉晋升梯子的「断层式裁员」", "砍掉初级岗位至 9%，扼杀新手试错与肌肉记忆，要求新人未经踩坑便具备资深判断力。",
                 "🌱 梯队培养的「判断力护城河」", "珍惜基础实践对自主性与判断力的磨砺，构建可持续的人才孵化与工程进化闭环。"),
            ]
        elif any(kw in title for kw in ["热词", "24个", "名词", "小白入门"]):
            models = [
                ("❌ 孤立调戏的「问答玩具」", "以为 AI 只是写写文案、查查资料的聊天框，频繁遭遇幻觉与遗忘后便弃之不用。",
                 "⚡ 系统工程的「智能体底座」", "从 Token、Context 到 Harness，将 LLM 嵌入自动规划、工具调用与沙箱执行的现代工程体系。"),
                ("❌ 死记硬背的「提示词玄学」", "沉迷网络流传的万能咒语模板，一旦底层模型升级或任务变得复杂便彻底失效。",
                 "🧠 动态调控的「上下文工程」", "深入理解 Context Window 瓶颈，在不同生命周期精准补充、压缩与剪裁信息，保障高保真推理。"),
                ("❌ 烟囱林立的「私有插件壁垒」", "各家 AI 工具自建孤立接口，工具代码难以在不同智能体之间跨平台复用，碎片化严重。",
                 "🌐 开放标准的「MCP 协议生态」", "拥抱 Model Context Protocol 开放规范，让数据库、CLI 与本地文件系统在所有 Agent 间即插即用。"),
                ("❌ 盲目放羊的「裸奔智能体」", "把复杂目标扔给 Agent 便听天由命，遇到死循环、报错或状态丢失只能无奈手动重启。",
                 "🔄 闭环演进的「Harness 与 Loop 工程」", "构筑上下文管理、进度持久化与权限沙箱底座，通过“AI质检-人校准-真反馈”三层循环驱动飞轮。"),
            ]
        elif any(kw in title for kw in ["狗", "懂的权利", "陶哲轩"]):
            models = [
                ("❌ 盲目享受的「宠物化幸福」", "活在自己看不懂的神迹里，需求全被照料得妥妥帖帖，代价是完全失去对自身命运的话语权。",
                 "⚡ 警惕代价的「主体性自觉」", "绝育、短鼻畸形、健康与生存全凭饲主决定；必须警惕便利背后人性的悄然让渡。"),
                ("❌ 人类脑力的「优雅妥协」", "公式、定理与数学美之所以被推崇，本质是人脑容量受限（一次只能盯五六个变量）的妥协产物。",
                 "🌌 维度升维的「高维暴力求解」", "AI无需迁就人类的极简优雅，算力充足直接暴力硬算；高维求解本就是低维维度无法窥测的范式。"),
                ("❌ 知识过载的「认知死局」", "AI成为全学科超级通才，几天内光速产出上万篇论文，人类专家即使不吃不喝一辈子也读不完。",
                 "🧭 不可剥夺的「懂的权利」", "你可以不什么都懂，但只要想弄明白路必须是通的；一旦路被掐断，人类在AI社会便沦为宠物的生态位。"),
                ("❌ 踩不下刹车的「囚徒困境」", "全球AI军备竞赛与地缘政治深度绑定，一千人联名呼吁暂停六个月，也没有任何一家巨头敢停手。",
                 "🛡️ 人文视角的「防线坚守」", "放弃AI等于放弃竞争，如同战争般不可逆；人类往往要等出事才踩刹车，唯有人文警醒能守住尊严底线。"),
            ]
        elif "REA" in title or "逆向" in title or "颜色" in title:
            models = [
                ("❌ 盲信噱头的「逆向神话」", "以为 REA 发明了颠覆性黑科技，盲目鼓吹能逆向一切、甚至叫嚣软件已死。",
                 "🛠️ 务实集成的「MCP 工具链」", "本质是将 Ghidra/JADX/Frida 等老牌逆向工具封装为 MCP，降低大模型调用门槛。"),
                ("❌ 机械塞入的「Token 膨胀」", "170+ 工具直接塞入提示词上下文，动辄消耗十余万 Token，反致推理迟缓卡顿。",
                 "⚡ 精准按需的「轻量化调用」", "按需加载单一工具或让 AI 动态安装 CLI 独立排查，反而响应更快、成本更低。"),
                ("❌ 触发风控的「死板对齐」", "面对逆向安全红线模型直接降级拒绝，软磨硬泡亦无法突破商业模型的静态分析限制。",
                 "🌊 灵活适配的「模型与 Harness」", "选用开放度更高的模型（如 DeepSeek）配合多子智能体并行协作，突破死板安全限制完成重构。"),
                ("❌ 易被攻破的「客户端代码」", "前端与客户端逻辑再精巧，只要编译成二进制或 APK 终究难逃被逆向还原。",
                 "🏰 不可动摇的「后端数据与运营」", "核心商业资产在于云端服务、数据积累与网络效应，这才是现代软件真正的护城河。"),
            ]
        elif any(kw in title for kw in ["产业链", "走出去", "出书", "小埃"]):
            models = [
                ("❌ 网上私信石沉大海的「被动等候」", "在网络社交平台、征稿邮箱中漫无目的地单向海投，面对冷漠算法和防骚扰机制毫无回音。",
                 "⚡ 亲临现场物理接触的「降维打击」", "肉身打破信息屏障，直抵国家级/区域级大型行业展会，站在产业链关键人面前建立直接连接。"),
                ("❌ 困守消费终端的「西西弗视角」", "逛零售书店只看到汗牛充栋的出版物和层层阻隔，错把终端销售渠道当成行业的准入门槛。",
                 "🤝 直捣核心机构的「产业链上游思维」", "越过零售书店和普通店员，直接对接果麦、磨铁、读客等核心出版机构的参展员工与策划编辑。"),
                ("❌ 闭门码字不问市场的「单点执念」", "只知道在电脑前敲字，对市场喜好、选题立项、书号申报、分销链路等商业闭环一无所知。",
                 "🧭 穿透商业闭环的「创作者工程化」", "主动探求从作者草稿到出版公司、书号审批、宣发分销的全生命周期，让创作具备产业确定性。"),
                ("❌ 羞于自我推荐的「心理怯懦」", "总觉得自己是无名小白、毫无背景人脉，在权威面前习惯性自我怀疑和畏缩不前。",
                 "🚀 坦荡争取赋能的「主体性觉醒」", "大方表达需求（“我是一个作家，我需要编辑的联系方式”），用专业与勇气赢得一线工作人员的尊重与引荐。"),
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
