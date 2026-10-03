#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 Office 文档（docx / pptx / xlsx / docm / pptm / xlsm ...）里取出内嵌原图。

原理：这些 OOXML 文件本质是 ZIP 包，内嵌媒体原封不动地放在 word/media、
ppt/media、xl/media 等目录下——不经过任何压缩或重采样，所以拿到的就是
作者插入时的原始分辨率文件。

本脚本只读取源文档（绝不改写），图片按 输出根目录/<文档名>/ 分目录落地，
并在输出根目录写一份 _manifest.tsv 汇总（文件名、尺寸、体积、哈希、来源条目）。

用法示例：
    # 只列不写盘（先看有多少张、多大、什么格式）
    python extract_media.py report.docx --list

    # 提取单个文档
    python extract_media.py report.docx -o ./out

    # 批量：目录下所有 docx/pptx/xlsx 一起提取，跳过重复内容
    python extract_media.py ./作业 -o ./out --dedupe

    # 顺手把 EMF/WMF 矢量图转成 PNG（需要 Pillow）
    python extract_media.py deck.pptx -o ./out --convert-vector
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import sys
import zipfile
from pathlib import Path, PurePosixPath

# 视为 Office 文档的后缀（都是 ZIP 容器）
OFFICE_EXTS = {".docx", ".pptx", ".xlsx", ".docm", ".pptm", ".xlsm",
               ".dotx", ".potx", ".xltx", ".dotm", ".potm", ".xltm"}

# 非 ZIP 的旧版 Office 二进制格式
LEGACY_EXTS = {".doc", ".ppt", ".xls"}

# 明确属于“图片”的后缀；media 目录里其它后缀（bin、xlsx 内嵌对象等）默认不算图片
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff",
              ".webp", ".emf", ".wmf", ".svg", ".ico", ".heic", ".heif",
              ".avif", ".pcx", ".tga", ".jp2", ".jfif"}

VECTOR_EXTS = {".emf", ".wmf"}

OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"          # 旧版/加密 Office 容器
OLD_PPT_BITMAP = b"\x00\x6e\x1e\xf0"                      # .ppt 里内嵌位图的标识


def _log(msg: str) -> None:
    print(msg, flush=True)


# --------------------------------------------------------------------------- #
# 图片尺寸探测：不依赖 Pillow，直接读文件头
# --------------------------------------------------------------------------- #
def probe_size(data: bytes) -> tuple[int, int] | None:
    """返回 (宽, 高)；识别不了就返回 None。"""
    try:
        if data[:8] == b"\x89PNG\r\n\x1a\n":                       # PNG
            w, h = struct.unpack(">II", data[16:24])
            return int(w), int(h)

        if data[:6] in (b"GIF87a", b"GIF89a"):                     # GIF
            w, h = struct.unpack("<HH", data[6:10])
            return int(w), int(h)

        if data[:2] == b"BM":                                      # BMP
            w, h = struct.unpack("<ii", data[18:26])
            return abs(int(w)), abs(int(h))

        if data[:4] in (b"II*\x00", b"MM\x00*"):                   # TIFF
            endian = "<" if data[:2] == b"II" else ">"
            offset = struct.unpack(endian + "I", data[4:8])[0]
            count = struct.unpack(endian + "H", data[offset:offset + 2])[0]
            entry = data[offset + 2:offset + 2 + count * 12]
            dims: dict[int, int] = {}
            for i in range(count):
                tag, typ, _cnt, val = struct.unpack(endian + "HHII", entry[i * 12:(i + 1) * 12])
                if tag in (256, 257) and typ == 3:                  # ImageWidth / ImageLength
                    dims[tag] = struct.unpack(endian + "H", entry[i * 12 + 8:i * 12 + 10])[0]
                elif tag in (256, 257) and typ == 4:
                    dims[tag] = val
            if 256 in dims and 257 in dims:
                return dims[256], dims[257]
            return None

        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":          # WebP
            fourcc = data[12:16]
            if fourcc == b"VP8X":
                w = int.from_bytes(data[24:27], "little") + 1
                h = int.from_bytes(data[27:30], "little") + 1
                return w, h
            if fourcc == b"VP8 ":
                w = int.from_bytes(data[26:28], "little") & 0x3FFF
                h = int.from_bytes(data[28:30], "little") & 0x3FFF
                return w, h
            if fourcc == b"VP8L":
                bits = int.from_bytes(data[21:25], "little")
                return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
            return None

        if data[:2] == b"\xff\xd8":                                # JPEG：扫 SOF 段
            i, n = 2, len(data)
            while i + 9 < n:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                    i += 2
                    continue
                seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
                if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    return int(w), int(h)
                i += 2 + seg_len
            return None
    except Exception:
        return None
    return None


# --------------------------------------------------------------------------- #
# 文档识别
# --------------------------------------------------------------------------- #
def sniff_container(path: Path) -> str:
    """判断容器类型：ok / legacy / encrypted / notoffice / missing"""
    if not path.exists():
        return "missing"
    try:
        with open(path, "rb") as fh:
            head = fh.read(8)
    except OSError:
        return "missing"
    if head.startswith(b"PK"):
        return "ok"
    if head.startswith(OLE_MAGIC):
        # 旧版二进制格式，或新版格式被加密（加密后外层是 OLE 包）
        return "legacy" if path.suffix.lower() in LEGACY_EXTS else "encrypted"
    return "notoffice"


def find_external_images(zf: zipfile.ZipFile) -> list[str]:
    """包里没有位图时，找 .rels 里指向外部的图片引用——这些图的原件在包外。"""
    import xml.etree.ElementTree as ET

    ns = "{http://schemas.openxmlformats.org/package/2006/relationships}"
    targets: list[str] = []
    for name in zf.namelist():
        if not name.endswith(".rels") or not name.startswith(("word/", "ppt/", "xl/")):
            continue
        try:
            root = ET.fromstring(zf.read(name))
        except ET.ParseError:
            continue
        for rel in root.findall(f"{ns}Relationship"):
            if rel.get("TargetMode") != "External":
                continue
            rtype = (rel.get("Type") or "").lower()
            target = rel.get("Target") or ""
            # 图片关系，或没有类型信息但看着像图片路径
            looks_image = any(target.lower().split("?")[0].endswith(e) for e in IMAGE_EXTS)
            if "image" in rtype or looks_image:
                targets.append(target)
    return targets


def find_media_entries(zf: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    """media 目录下、后缀属于图片的条目。"""
    out = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        parts = PurePosixPath(info.filename).parts
        if any(p.lower() == "media" for p in parts[:-1]) and \
                PurePosixPath(info.filename).suffix.lower() in IMAGE_EXTS:
            out.append(info)
    return out


# --------------------------------------------------------------------------- #
# 提取
# --------------------------------------------------------------------------- #
def safe_name(entry_name: str, used: set[str]) -> str:
    """只用条目基名；重名时补短哈希，绝不写穿输出目录。"""
    base = PurePosixPath(entry_name).name or "unnamed"
    if base not in used:
        used.add(base)
        return base
    stem, dot, ext = base.rpartition(".")
    digest = hashlib.sha1(entry_name.encode("utf-8")).hexdigest()[:6]
    cand = f"{stem or base}_{digest}{dot}{ext}"
    used.add(cand)
    return cand


def dedupe_key(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def convert_vector(src: Path, dst_png: Path) -> bool:
    """EMF/WMF -> PNG。Windows 上用 Pillow 打开矢量图时通常能借系统渲染器成功。"""
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        return False
    try:
        with Image.open(src) as im:
            im.load()
            im.convert("RGBA").save(dst_png)
        return True
    except Exception:
        return False


def process_doc(path: Path, out_root: Path, args, seen_hashes: dict[str, str],
                manifest: list[list[str]], report: dict) -> None:
    container = sniff_container(path)
    if container != "ok":
        reason = {
            "legacy": "旧版二进制格式（.doc/.ppt/.xls），不是 ZIP 容器，需先另存为 docx/pptx/xlsx",
            "encrypted": "疑似加密/受保护的 Office 文件（OLE 容器），需先去掉密码另存",
            "notoffice": "文件头既不是 ZIP 也不是 OLE，可能不是 Office 文档",
            "missing": "文件不存在或无法读取",
        }[container]
        _log(f"[skip] {path.name}：{reason}")
        report["skipped"].append({"document": str(path), "reason": reason})
        return

    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        reason = f"ZIP 打不开（{exc}），文件可能损坏或后缀与内容不符"
        _log(f"[skip] {path.name}：{reason}")
        report["skipped"].append({"document": str(path), "reason": reason})
        return

    with zf:
        entries = find_media_entries(zf)
        if not entries:
            externals = find_external_images(zf)
            if externals:
                _log(f"[ -- ] {path.name}：包里没有位图；发现 {len(externals)} 处**外部链接**图片引用：")
                for tgt in externals[:10]:
                    _log(f"       @ {tgt}")
                if len(externals) > 10:
                    _log(f"       @ ...（其余 {len(externals) - 10} 处省略）")
                _log("       这些图不在文档里，得去上面这些路径（相对路径以文档所在目录为基准）找原件")
            else:
                _log(f"[ -- ] {path.name}：没有内嵌图片"
                     "（文档里的\"图\"可能是形状/SmartArt/图表，它们是 XML 绘制的，包里没有位图）")
            report["documents"].append(
                {"document": str(path), "images": 0, "external_links": externals})
            return

        stem_dir = path.stem
        dest_dir = out_root / stem_dir
        _log(f"[doc ] {path.name}：发现 {len(entries)} 个媒体图片条目")
        if not args.list_only:
            dest_dir.mkdir(parents=True, exist_ok=True)

        used: set[str] = set()
        kept = 0
        for info in entries:
            data = zf.read(info)
            digest = dedupe_key(data)
            size = probe_size(data)
            size_txt = f"{size[0]}x{size[1]}" if size else "-"

            if args.dedupe and digest in seen_hashes:
                _log(f"       · {info.filename}  [{size_txt}] -> 与 {seen_hashes[digest]} 内容重复，跳过")
                report["duplicates"].append(
                    {"document": str(path), "entry": info.filename, "same_as": seen_hashes[digest]})
                continue
            seen_hashes.setdefault(digest, f"{path.name}:{info.filename}")

            if args.list_only:
                _log(f"       · {info.filename}  [{size_txt}, {info.file_size / 1024:.0f} KB]")
                kept += 1
                continue

            name = safe_name(info.filename, used)
            target = dest_dir / name
            existed = target.exists()
            if args.skip_existing and existed:
                _log(f"       = {name}  [已存在，跳过]")
                manifest.append([
                    stem_dir, name, size_txt, str(info.file_size), digest[:12],
                    info.filename, str(target),
                ])
                report["already_present"].append(
                    {"document": str(path), "entry": info.filename, "path": str(target)})
                continue
            target.write_bytes(data)
            kept += 1
            _log(f"       -> {target}  [{size_txt}, {info.file_size / 1024:.0f} KB]")

            if args.convert_vector and PurePosixPath(info.filename).suffix.lower() in VECTOR_EXTS:
                png = target.with_suffix(".png")
                if convert_vector(target, png):
                    _log(f"          ~ 矢量转 PNG：{png.name}")
                else:
                    _log("          ~ 矢量转 PNG 失败（缺 Pillow 或系统渲染器不支持），保留原矢量文件")

            manifest.append([
                stem_dir, name, size_txt, str(info.file_size), digest[:12],
                info.filename, str(target) if not args.list_only else "",
            ])

        report["documents"].append({"document": str(path), "images": kept})


def iter_documents(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    docs = [p for p in sorted(target.rglob("*"))
            if p.is_file() and p.suffix.lower() in (OFFICE_EXTS | LEGACY_EXTS)]
    return docs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="从 docx/pptx/xlsx 里提取内嵌原图（Office 文件本质是 ZIP）")
    ap.add_argument("target", help="Office 文档路径，或包含文档的目录")
    ap.add_argument("-o", "--out", default="./extracted_media",
                    help="输出根目录，默认 ./extracted_media")
    ap.add_argument("--list", dest="list_only", action="store_true",
                    help="只列出内嵌图片，不写盘（看清单用）")
    ap.add_argument("--dedupe", action="store_true",
                    help="内容哈希去重：跨文档/文档内重复的图只留第一份")
    ap.add_argument("--skip-existing", action="store_true",
                    help="输出目录里已存在同名文件就跳过（增量提取）")
    ap.add_argument("--convert-vector", action="store_true",
                    help="把 EMF/WMF 另存一份 PNG（需 Pillow）")
    args = ap.parse_args(argv)

    target = Path(args.target).expanduser()
    if not target.exists():
        _log(f"[error] 找不到：{target}")
        return 2

    docs = iter_documents(target)
    if not docs:
        _log(f"[error] {target} 下没有发现 docx/pptx/xlsx 等 Office 文档")
        return 2

    out_root = Path(args.out).expanduser()
    if not args.list_only:
        out_root.mkdir(parents=True, exist_ok=True)

    _log(f"共 {len(docs)} 个文档待处理；输出根目录：{out_root}"
         + ("（dry-run，不写盘）" if args.list_only else ""))

    manifest: list[list[str]] = []
    report: dict = {"documents": [], "duplicates": [], "already_present": [],
                    "skipped": [], "list_only": args.list_only}
    seen_hashes: dict[str, str] = {}

    for doc in docs:
        process_doc(doc, out_root, args, seen_hashes, manifest, report)

    total = sum(d["images"] for d in report["documents"])
    _log(f"\n完成：{total} 张图片，来自 {len(report['documents'])} 个文档；"
         f"跳过 {len(report['skipped'])} 个文档，去重 {len(report['duplicates'])} 张，"
         f"已存在略过 {len(report['already_present'])} 张")

    if not args.list_only:
        header = ["doc", "file", "dimensions", "bytes", "sha1_12", "zip_entry", "saved_to"]
        mpath = out_root / "_manifest.tsv"
        with open(mpath, "w", encoding="utf-8", newline="") as fh:
            fh.write("\t".join(header) + "\n")
            for row in manifest:
                fh.write("\t".join(row) + "\n")
        rpath = out_root / "_report.json"
        rpath.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        _log(f"清单：{mpath}\n报告：{rpath}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    raise SystemExit(main())
