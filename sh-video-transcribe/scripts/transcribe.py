# /// script
# requires-python = ">=3.10"
# dependencies = ["faster-whisper"]
# ///
# 媒体文件语音转文字：faster-whisper 本地转写，输出 SRT 与纯文本
# 用法: uv run transcribe.py <媒体文件> [--model small] [--lang auto] [--outdir 输出目录]
import argparse
import os
import sys
from pathlib import Path

# Windows 控制台默认 GBK，中文输出会乱码；统一强制 UTF-8
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 国内网络直连 huggingface.co 常超时，默认走 hf-mirror 镜像；
# 已设置 HF_ENDPOINT 时尊重现有值（设为 https://huggingface.co 可回官方）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from faster_whisper import WhisperModel  # noqa: E402


def pick_device() -> tuple[str, str]:
    # 有 NVIDIA GPU 用 float16（快数倍），否则 CPU int8（兼容性最好）
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


def fmt_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_model(name: str, device: str, compute_type: str) -> WhisperModel:
    # GPU 探测通过不代表运行库齐全（如缺 cublas64_12.dll），构造失败时回退 CPU
    try:
        return WhisperModel(name, device=device, compute_type=compute_type)
    except Exception as exc:
        if device == "cuda":
            print(f"GPU 初始化失败({exc})，回退 CPU", flush=True)
            return WhisperModel(name, device="cpu", compute_type="int8")
        raise


def main() -> None:
    ap = argparse.ArgumentParser(description="媒体文件语音转文字（SRT + TXT）")
    ap.add_argument("input", help="视频或音频文件路径")
    ap.add_argument(
        "--model",
        default="small",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        help="whisper 模型档位（默认 small）",
    )
    ap.add_argument(
        "--lang", default="auto", help="语言代码，auto 为自动检测（默认 auto）"
    )
    ap.add_argument("--outdir", default=None, help="输出目录（默认与输入文件同目录）")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.is_file():
        sys.exit(f"文件不存在: {src}")
    outdir = Path(args.outdir) if args.outdir else src.parent
    outdir.mkdir(parents=True, exist_ok=True)

    device, compute_type = pick_device()
    print(f"模型: {args.model} | 设备: {device} ({compute_type})", flush=True)
    model = build_model(args.model, device, compute_type)

    segments, info = model.transcribe(
        str(src),
        language=None if args.lang == "auto" else args.lang,
        vad_filter=True,
        beam_size=5,
    )
    print(
        f"检测语言: {info.language} (置信度 {info.language_probability:.2f})",
        flush=True,
    )

    srt_path = outdir / f"{src.stem}.srt"
    txt_path = outdir / f"{src.stem}.txt"
    lines_srt: list[str] = []
    lines_txt: list[str] = []
    for i, seg in enumerate(segments, start=1):
        text = seg.text.strip()
        if not text:
            continue
        lines_srt.append(f"{i}\n{fmt_ts(seg.start)} --> {fmt_ts(seg.end)}\n{text}\n")
        lines_txt.append(text)
        print(f"[{fmt_ts(seg.start)}] {text}", flush=True)

    srt_path.write_text("\n".join(lines_srt), encoding="utf-8")
    txt_path.write_text("\n".join(lines_txt), encoding="utf-8")
    print(f"完成: {len(lines_txt)} 段\n  {srt_path}\n  {txt_path}", flush=True)


if __name__ == "__main__":
    main()
