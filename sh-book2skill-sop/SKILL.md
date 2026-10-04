---
name: sh-book2skill-sop
description: 把书/文档转成 agent skill：book-to-skill 全流程 SOP、扫描版 OCR 兜底与本机坑位速查。点名使用
---

# book-to-skill 使用 SOP（本机版）

把 PDF/EPUB/DOCX/MD/HTML/RTF 转成结构化 agent skill。本 SOP 是官方 skill
`book-to-skill`（同名 SKILL.md 里的 11 步流程）在本机的执行手册：先读本文，
再按官方 skill 的 Step 0–11 走；本文只解决"本机怎么跑"与"哪里有坑"。

## 0. 本机安装现状（勿重装，勿 npx update）

| 项 | 值 |
|---|---|
| 真身 | `~/.agents/skills/book-to-skill`（独立 git clone，master @ c108d25）|
| Python | 内嵌 `.venv`（106MB，base=anaconda 3.12.7）；User 级 `PYTHON_BIN` 已指向它 |
| 已装抽取包 | pypdf / pdfminer.six / ebooklib / bs4 / python-docx / striprtf / trafilatura / pdf-inspector / **pillow / rapidocr-onnxruntime**（OCR 兜底） |
| 未装 | docling（技术书结构抽取，1-2GB）、Calibre（MOBI/AZW） |
| 仓库状态 | 故意不入库：外层 `.git/info/exclude` 排除 `/book-to-skill/`，内层排除 `/.venv/`；且已从 `~/.agents/.skill-lock.json` 摘除 |

**两条铁律**（原因见 `references/why-not-npx.md`）：
1. **永远不对它跑 `npx skills add/update`**——CLI 会先 `rm -rf` 整个目录再重拷，venv 当场蒸发。更新只能 `git pull`。
2. **`PYTHON_BIN` 必须正斜杠**——反斜杠被 Git Bash MSYS 转换改写后会静默退回没装包的 MSYS2 python。

环境自检（6 格式全 ready 即健康）：

```powershell
& $env:PYTHON_BIN "C:\Users\29580\.agents\skills\book-to-skill\scripts\extract.py" --check
```

## 1. 标准流程（文字层完好的文档）

1. `Test-Path` 确认输入文件存在，`& $env:PYTHON_BIN --version` 确认 venv 活着。
2. 跑 `book-to-skill` skill 的 Step 2 抽取（`scripts/extract.py`，text 模式秒级完成）。
3. **立刻验货**：看 `Words`/`Tokens` 是否与页数匹配（健康：中文书每页 ~300-500 字）。字数接近 0 → 走第 2 节 OCR 兜底。
4. 按官方 skill Step 2.6：>50k token 的书**不要整读**，用 grep 定位章节边界 + sed/read offset 分段取。
5. 章节摘要生成可并行委派子代理（每代理 2 章，读自己的行号区间，写 `chapters/chNN-*.md`），主会话汇总写 SKILL.md/glossary/patterns/cheatsheet。
6. 官方 Step 9.5 安全扫描必跑：
   `& $env:PYTHON_BIN ...\book-to-skill\tools\scan_generated_skill.py <输出目录>`
7. 收尾：跑 `& $env:PYTHON_BIN "C:\Users\29580\.agents\skills\sync_skills.py"` 让 codex per-skill junction 同步（claude/opencode/gemini/pi 是整体 junction 或原生读取，自动生效）。
8. 清理抽取 workdir（`Workdir ->` 路径）与临时脚本。

## 2. 扫描版 PDF（无文字层）OCR 兜底

判据：抽取结果只有几百字符、pdf-inspector 报 `classified as scanned`。

1. 采样验证可行性：用 venv python + pypdf 抽一页原图（每页 1 张图），`read_image` 人眼确认清晰度。
2. 装 `rapidocr-onnxruntime`（~100MB，无 torch，中文好）进内嵌 venv——**优先于 docling**（1-2GB 且对中文扫描件提升有限）。
3. 批量脚本模式（参考下面骨架，按页抽图→OCR→utf8 落盘，每 10 页 flush 进度）：

```python
import io, pypdf
from PIL import Image
from rapidocr_onnxruntime import RapidOCR
ocr = RapidOCR()
for i, page in enumerate(pypdf.PdfReader(PDF).pages):
    im = Image.open(io.BytesIO(page.images[0].data))
    result, _ = ocr(im)
    text = "\n".join(x[1] for x in (result or []))
    f.write(f"\n\n===== PAGE {i+1} =====\n{text}")  # 页标记是后续章节定位的锚
```

实测参考：353 页约 20 分钟（~3.5s/页），中文识别质量良好（仅个别错字）。

## 3. 坑位速查（都真实踩过）

| 坑 | 症状 | 处理 |
|---|---|---|
| 扫描版 PDF | 355 页只提出 19 词 | 第 2 节 OCR 兜底，先采样一页再全量 |
| GBK 控制台 | OCR/中文输出满屏乱码 | 一律落盘 utf8 文件再读；`Get-Content -Encoding utf8`；**别在控制台直读**，会误判失败 |
| PYTHON_BIN 反斜杠 | extract 静默用错 python，报 PEP 668 | 环境变量值用正斜杠 |
| npx skills update | 整个 book-to-skill 连 venv 被删 | 见第 0 节铁律；lock 里条目已摘，别再 add 回去 |
| 章节边界误判 | OCR 把"第3章"识别成"第 3章/第3草/第3节"，或 ToC 页命中 | 用"页首页脚 running header（页码+第N章标题）"双信号确认真实起始页；先抽 `第N章` 首现页再人工核一两处 |
| 提示/tip 编号错乱 | "提示62"识别成"提示2"（掉首位数字） | 按出现顺序+内容重排编号，勿信 OCR 原始编号 |
| 大书整读 | 26 万字直接 read 爆上下文 | grep 定位 + read offset/limit 分段；摘要下放子代理 |

## 4. 换机重建（六步）

```bash
# 1. 克隆上游
git clone https://github.com/virgiliojr94/book-to-skill.git ~/.agents/skills/book-to-skill
# 2. 建 venv（任选带 pip 的 Python；anaconda 亦可）
"D:/Users/29580/anaconda3/python.exe" -m venv ~/.agents/skills/book-to-skill/.venv
# 3. 装抽取依赖（+ pillow、rapidocr-onnxruntime 走 OCR 兜底）
& "C:/Users/29580/.agents/skills/book-to-skill/.venv/Scripts/python.exe" -m pip install `
    pypdf "pdfminer.six" ebooklib beautifulsoup4 python-docx striprtf trafilatura `
    "pdf-inspector>=1.15,<2" pillow rapidocr-onnxruntime
# 4. 环境变量（User 级，必须正斜杠）
[Environment]::SetEnvironmentVariable('PYTHON_BIN',
  'C:/Users/29580/.agents/skills/book-to-skill/.venv/Scripts/python.exe', 'User')
# 5. 排除规则（外层防 embedded repo，内层防 venv 入库）
Add-Content ~/.agents/skills/.git/info/exclude '/book-to-skill/'
Add-Content ~/.agents/skills/book-to-skill/.git/info/exclude "/.venv/"
# 6. 确认 skill-lock.json 里没有 book-to-skill（跑过 npx skills add 才需要）
```

可选增强：技术书（表格/公式/代码密集）再装 docling；MOBI/AZW 装 Calibre（`ebook-convert`）。

## 5. 验证

- 抽取健康：`extract.py --check` 6 格式 ready；真 PDF 抽取中文完好。
- 产物健康：`scan_generated_skill.py` 通过；SKILL.md + chapters/ + glossary + patterns + cheatsheet 齐全；目标 agent 能发现（`sync_skills.py --check` 全 SKIP/LINK）。

## 6. 版权门槛

受版权保护书籍的衍生 skill **只能保持 private**，不得公开推送（生成 skill 的 Step 11 发布环节自带此问询，勿选 public）。
