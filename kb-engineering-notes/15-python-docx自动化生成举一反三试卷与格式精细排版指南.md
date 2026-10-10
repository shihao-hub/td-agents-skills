---
name: kb-docx-practice-generator
description: 基于 python-docx 的试卷与教辅「举一反三」变式题自动化生成与精细排版指南：涵盖考点拆解映射、中西文字体分离(w:eastAsia)、页边距与行距控制、化学式与方程式排版、及批量自动化生成流水线。需批量生成试卷、Word 教辅或自动化排版时查阅。
---

# python-docx 自动化生成举一反三试卷与格式精细排版指南

## 一、 业务场景与生成需求

在教研教学与教辅内容生产场景中，经常需要针对学生的阶段诊断试卷（如月考卷、课后诊断卷）开展**精准个性化变式训练（举一反三）**。

### 1. 核心业务输入与产出
- **输入源**：原始诊断卷（通常为 PDF 或图片，包含固定讲次的若干道核心题，如第 6 讲化学式计算 5 题、第 12 讲金属活动性 7 题）；
- **生成诉求**：为原卷中每一道题目衍生 **2 道同考点、同梯度难度、同题型的变式题**（即 1:2 衍生）；
- **最终交付物**：排版严整、格式统一的 Word 文档（`.docx`），包含：
  - 试卷大标题、副标题与学生姓名留白下划线；
  - 相对原子质量等前置参数声明；
  - 按原题考点分组，题号全局连续编号（如 1~10、1~14）；
  - 选择题选项（A/B/C/D）对齐与填空题下划线留白；
  - 计算题解答区域与步骤留白；
  - 卷末附带结构对齐、步骤规范的**参考答案与标准解析**。

---

## 二、 排版引擎核心技术难点与剖析

在纯 Python 命令行或自动化流水线中，直接使用 `python-docx` 生成中文正规试卷时，常见以下底层格式与排版断层：

### 1. 中西文字体分离与 `w:eastAsia` 缺失导致字体回退
`python-docx` 的 `run.font.name = "宋体"` 仅修改西文字体标签（`<w:rFonts w:ascii="宋体" w:hAnsi="宋体"/>`）。在 Microsoft Word 或 WPS 中打开时，中文文字因未指定东亚字体（`w:eastAsia`），会退化为系统的默认字体（如苹方、等线或 Calibri），导致版面混乱、字符间距失控。

**解决方案（底层 XML 注入）**：
```python
from docx.oxml.ns import qn

def set_run_font(run, font_name="宋体", font_size_pt=10.5, bold=False):
    run.font.name = "Times New Roman"  # 西文与数字使用经典衬线体
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)  # 中文强制使用指定东亚字体
    run.font.size = Pt(font_size_pt)
    run.bold = bold
```

### 2. 标准试卷版心、页边距与行间距精确换算
正规中小学试卷通常采用 A4 竖版标准版心，页边距往往略紧凑于标准商务公文，以承载更多题目。
- **页面大小**：A4（$210\,\text{mm} \times 297\,\text{mm}$，换算为磅值为 $595.3\,\text{pt} \times 841.9\,\text{pt}$）；
- **页边距**：上/下 $25\,\text{mm}$（$70.9\,\text{pt}$），左/右 $20\,\text{mm}$（$56.7\,\text{pt}$）；
- **行间距与段间距**：题干行距通常为 1.25~1.35 倍，题干与小题之间段前 $2\,\text{pt}$、段后 $2\,\text{pt}$，考点大标题段前 $6\,\text{pt}$、段后 $4\,\text{pt}$，避免题目之间过密粘连。

### 3. 化学式、方程式与上下标的无格式降级处理
在化学、物理试卷中，化学式涉及大量下标（如 $\text{H}_2\text{O}$、$\text{Fe}_2\text{O}_3$）与离子上标（如 $\text{Mg}^{2+}$、$\text{Cl}^-$），以及反应条件（$\Delta$、催化剂、点燃、高温）。
- **方案 A（Unicode 原生上下标）**：直接在文本中使用 Unicode 标准上下标字符（如 `C₄H₈O₂`、`Fe₂O₃`、`Mg²⁺`、`Cl⁻`、`SO₄²⁻`），排版稳定性最高，拷贝时不会丢失格式，跨平台渲染极其稳定；
- **方案 B（run 级别 superscript/subscript）**：对极其复杂的长分子式，可使用 `run.font.superscript = True` 动态拼接。

---

## 三、 标准自动化生成流水线与代码实现

以下为生成教学试卷的标准化 Python 脚本骨架与核心实现。

### 1. 核心封装模块（`generate_lianxi.py`）

```python
# -*- coding: utf-8 -*-
"""
自动化试卷与举一反三练习题生成引擎
"""

import os
import docx
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn


def set_run_font(run, font_name="宋体", font_size_pt=10.5, bold=False, italic=False, color=None):
    """精确设置 Run 的东亚中文字体、西文字体与字号样式"""
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)
    run.font.size = Pt(font_size_pt)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = color


def add_paragraph_with_runs(doc, text_runs, align=WD_ALIGN_PARAGRAPH.LEFT, space_before=0, space_after=3, line_spacing=1.25):
    """
    添加段落，支持在一个段落中按 Run 拆分渲染多种字号与字重
    text_runs: list of tuple (text, font_name, font_size_pt, bold, italic)
    """
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line_spacing

    for item in text_runs:
        text = item[0]
        font_name = item[1] if len(item) > 1 and item[1] else "宋体"
        size = item[2] if len(item) > 2 and item[2] else 10.5
        bold = item[3] if len(item) > 3 else False
        italic = item[4] if len(item) > 4 else False
        run = p.add_run(text)
        set_run_font(run, font_name=font_name, font_size_pt=size, bold=bold, italic=italic)
    return p


def init_exam_document():
    """初始化并配置 A4 标准试卷版心"""
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Pt(595.3)
    sec.page_height = Pt(841.9)
    sec.top_margin = Pt(70.9)
    sec.bottom_margin = Pt(70.9)
    sec.left_margin = Pt(56.7)
    sec.right_margin = Pt(56.7)
    return doc
```

### 2. 试卷生成模板装配流

```python
def generate_lesson_paper(paper_title, exam_data, out_filepath):
    doc = init_exam_document()

    # 1. 大标题 (二号/小二号 黑体或加粗宋体)
    add_paragraph_with_runs(
        doc,
        [(paper_title, "宋体", 15, True, False)],
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_before=6,
        space_after=6,
        line_spacing=1.5
    )

    # 2. 学生信息栏
    add_paragraph_with_runs(
        doc,
        [("学生姓名：               　。", "宋体", 12, False, False)],
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_before=0,
        space_after=8,
        line_spacing=1.5
    )

    # 3. 参数声明 (如相对原子质量)
    if "header_meta" in exam_data:
        add_paragraph_with_runs(
            doc,
            [(exam_data["header_meta"], "宋体", 9.5, False, False)],
            space_before=0,
            space_after=8,
            line_spacing=1.2
        )

    # 4. 按考点组装变式题
    for group in exam_data["groups"]:
        # 考点小标题 (四号/小四加粗)
        add_paragraph_with_runs(
            doc,
            [(group["topic_title"], "宋体", 11, True, False)],
            space_before=6,
            space_after=4
        )
        for problem in group["problems"]:
            # 题干
            add_paragraph_with_runs(
                doc,
                [(problem["stem"], "宋体", 10.5, False, False)],
                space_before=2,
                space_after=2
            )
            # 选项或解答留白
            if "content" in problem and problem["content"]:
                add_paragraph_with_runs(
                    doc,
                    [(problem["content"], "宋体", 10.5, False, False)],
                    space_before=0,
                    space_after=6,
                    line_spacing=1.35
                )

    # 5. 卷末答案区 (分页或显著分隔)
    add_paragraph_with_runs(
        doc,
        [(f"{paper_title}参考答案", "宋体", 14, True, False)],
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_before=14,
        space_after=8
    )

    for group_ans in exam_data["answers"]:
        add_paragraph_with_runs(
            doc,
            [(group_ans["topic_title"], "宋体", 10.5, True, False)],
            space_before=4,
            space_after=2
        )
        add_paragraph_with_runs(
            doc,
            [(group_ans["answer_text"], "宋体", 10.5, False, False)],
            space_before=0,
            space_after=4
        )

    doc.save(out_filepath)
```

---

## 四、 交付验证与工程扩展建议

### 1. 质量检验与断言 SOP
1. **进程与文件可读性**：生成完成后，使用 `docx.Document(filepath)` 重新加载，校验段落总数与关键大标题是否完整，确保无损坏的 XML 标签；
2. **多终端兼容性**：
   - 在 Microsoft Word 与 WPS Office 中分别打开抽检，检查中文字体是否准确匹配为宋体，西文是否为 Times New Roman；
   - 验证化学式（如下标数字）是否自然平整，无上下错位；
3. **试卷逻辑闭环**：检查各考点变式题数量是否与原题数呈 $1:2$ 完整对应，题号是否连续单调递增，答案区是否覆盖全部题号。

### 2. 多学科与新讲次扩展指南
当需要为物理、生物、数学等其他学科或新的讲次生成练习卷时：
1. **考点拆解模型保持独立**：保持 Python 脚本中“数据结构定义（字典/JSON）”与“文档装配（Document Builder）”解耦；
2. **公式与特殊字符优先 Unicode**：优先采用标准 Unicode 上下标集合（`⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻` 与 `₀₁₂₃₄₅₆₇₈₉`），避免使用复杂的公式编辑器对象，保障跨平台轻量高质。

---

**最后更新：** 2026-10-10
