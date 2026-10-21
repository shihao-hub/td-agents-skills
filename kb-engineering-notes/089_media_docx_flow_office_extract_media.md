---
name: kb-office-extract-embedded-media
description: Word/PPT/Excel 等 Office 文档内嵌原图与音视频无损提取流水线：剖析 OOXML ZIP 容器机制、外部链接媒体判定与 scripts/extract_media.py 批量提取 SOP。提取 Office 文档原图与媒体资源时查阅。
---

# Office 文档内嵌原图与媒体资源无损提取流水线

> 本条目沉淀自批量提取 Office 文档中原始分辨率插图、矢量图及媒体资源的工程实践。

---

## 一、业务场景与底层机制

### 为什么必须“拆包”而不是“另存为”或“截图”？
1. **OOXML 标准容器机制**：`.docx` / `.pptx` / `.xlsx`（以及带宏的 `docm`/`pptm`/`xlsm`）本质上全都是基于 ZIP 格式打包的标准容器包；
2. **零重采样保真**：作者插入文档中的位图（PNG/JPEG/WebP）原封不动存放在压缩包内，**未经过任何有损压缩或像素插值**。而在 Word/WPS 中“右键图片另存为”拿到的是编辑器渲染缩放后的位图，屏幕截图更会将分辨率钉死在当前屏幕像素；
3. **格式与元数据保真**：可一次性完整提取包内的 EMF/WMF 原生矢量图、GIF 动图乃至音频文件（如 `media/audio1.mp3`），且条目编号严格对应作者插入的顺序。

---

## 二、容器内部路径与格式对照表

| 文档类型 | 媒体存放目录 | 补充说明 |
|---|---|---|
| `.docx` / `.docm` | `word/media/` | `word/embeddings/` 包含嵌入的 Visio/Excel 对象；`word/_rels` 存放外部链接关系 |
| `.pptx` / `.pptm` | `ppt/media/` | `ppt/slides/slideN.xml` 对应每张幻灯片的图片引用 |
| `.xlsx` / `.xlsm` | `xl/media/` | `xl/drawings/` 记录单元格内绘图挂载信息 |
| `.doc` / `.ppt` / `.xls`（旧版） | **无**（OLE 复合二进制） | 不是 ZIP 容器，必须先通过 Office/WPS “另存为”转成现代 OOXML 格式 |

### ⚠️ 两类特殊情况辨析
1. **外部链接图片**：文档中看起来有图，但包内 `media/` 为空。原因是在插入时勾选了“链接到文件”，在 `word/_rels/*.xml.rels` 中会存在 `TargetMode="External"` 属性，指向原机外部路径；
2. **矢量形状 / SmartArt / 复杂图表**：这些元素是由 Office DrawingML 动态用 XML 标签渲染绘制的，并不存在位图文件实体。

---

## 三、标准提取执行方式

### 方式 1：手工四步（快速单次操作，无需 Python）
1. **备份原件**：先复制一份副本，严禁直接在原稿上操作（防止改不回来导致 Word 报“文件已损坏”）；
2. **修改后缀**：将副本后缀由 `.docx`/`.pptx`/`.xlsx` 直接重命名为 `.zip`；
3. **解压容器**：使用操作系统自带解压功能或 7-Zip / Bandizip 解压该 zip 包；
4. **定位媒体**：进入解压后的 `word/media/`（或 `ppt/media/`、`xl/media/`）目录，所有原图全在其中（如 `image1.png`、`image2.jpeg`）。

---

### 方式 2：使用自动化脚本批量提取（方案 A 推荐）

知识库内置了纯标准库驱动的专用提取脚本：`scripts/extract_media.py`。
脚本具备容器嗅探、图片尺寸头探测（不依赖 Pillow）、内容哈希去重、生成 `_manifest.tsv` 汇总清单以及外部链接警告等功能。

```powershell
# 1. 快速查看文档中包含多少图片、多大尺寸（dry-run，不写盘）
python "scripts/extract_media.py" "D:\Docs\report.docx" --list

# 2. 提取单个文档全部媒体至指定输出目录
python "scripts/extract_media.py" "D:\Docs\report.docx" -o "D:\MediaOutput"

# 3. 批量处理目录下全部 Office 文档，并按内容哈希自动去重
python "scripts/extract_media.py" "D:\Docs\年度资料" -o "D:\MediaOutput" --dedupe

# 4. 遇到已存在的文件跳过（增量提取），并将 EMF/WMF 矢量图转为 PNG（需 Pillow）
python "scripts/extract_media.py" "D:\Docs\deck.pptx" -o "D:\MediaOutput" --skip-existing --convert-vector
```

---

## 四、交付验证与输出清单

执行完成后，在输出目录下会生成：
- 各文档的媒体子文件夹（如 `report/image1.png`、`report/image2.jpeg`）；
- `_manifest.tsv`：记录文档来源、文件尺寸、字节大小、SHA1 哈希及对应 ZIP 内路径；
- `_report.json`：汇总提取结果统计与跳过原因。
