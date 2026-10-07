"""Corner/object watermark removal via light-only diffusion inpainting.

Pipeline: segment (keep dark strokes / clean warm bg / rest) -> harmonic fill
sourced ONLY from clean bg pixels -> background-grain noise -> two-ring
anti-alias rebuild toward kept dark strokes -> verification (probes + garish
scan vs original + before/after zoom previews).

Incorporates three hard-won fixes (see SKILL.md):
  1. neighbor counting on bool arrays must cast to int first
  2. every np.pad needs explicit mode (default zeros poison diffusion)
  3. AA blend averages DARK neighbors only (numerator and denominator same set)

Usage:
  python clean_corner.py --src in.png --dst out.png --roi x0,y0,x1,y1
      [--keep-below 135] [--warm-diff 3] [--src-above 230] [--seed 7]
      [--margin 40] [--zoom 3] [--preview-dir DIR]
"""
import argparse
import os

import numpy as np
from PIL import Image


def nsum(field2d):
    """Sum of 8 neighbors, edge-padded (never zero-padded!)."""
    p = np.pad(field2d, 1, mode="edge").astype(np.float64)
    return (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:] +
            p[:-2, :-2] + p[:-2, 2:] + p[2:, :-2] + p[2:, 2:])


def parse_roi(s, w, h):
    x0, y0, x1, y1 = (int(v) for v in s.split(","))
    return max(0, x0), max(0, y0), min(w, x1), min(h, y1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--roi", required=True, help="x0,y0,x1,y1 in source pixels")
    ap.add_argument("--keep-below", type=float, default=135,
                    help="value(v) below this = protected dark stroke core")
    ap.add_argument("--warm-diff", type=float, default=3,
                    help="min r-b for a pixel to count as clean warm background")
    ap.add_argument("--src-above", type=float, default=230,
                    help="value(v) above this (and warm) = fill source")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--margin", type=int, default=40)
    ap.add_argument("--zoom", type=int, default=3)
    ap.add_argument("--preview-dir", default=None)
    args = ap.parse_args()

    orig = np.asarray(Image.open(args.src).convert("RGB")).astype(np.float64)
    H, W = orig.shape[:2]
    x0, y0, x1, y1 = parse_roi(args.roi, W, H)
    roi = orig[y0:y1, x0:x1]
    r, g, b = roi[..., 0], roi[..., 1], roi[..., 2]
    v = roi.mean(2)

    keep = v < args.keep_below                                    # protected strokes
    srcmask = ((r - b) >= args.warm_diff) & (v > args.src_above)  # clean warm bg
    if srcmask.sum() == 0:
        srcmask = v > args.src_above  # fallback: neutral background
        print(f"[warn] no warm bg found, relaxed source test to v > {args.src_above}")
    mask = ~(keep | srcmask)
    print(f"ROI {x1 - x0}x{y1 - y0}  keep(strokes)={int(keep.sum())}  "
          f"src(bg)={int(srcmask.sum())}  fill={int(mask.sum())}")
    if mask.sum() == 0:
        print("[warn] nothing to fill; check --roi and thresholds")
        return

    # --- light-only harmonic diffusion (sources: clean bg pixels only) ---
    F = roi.copy()
    F[~srcmask] = 0.0
    wgt = srcmask.astype(np.float64)
    for _ in range(600):
        sF = np.stack([nsum(F[..., c]) for c in range(3)], axis=-1)
        sw = nsum(wgt)
        upd = (sw > 0) & (wgt == 0)
        F[upd] = sF[upd] / sw[upd, None]
        wgt[upd] = 1.0
    for _ in range(200):  # smooth the filled field
        pF = np.pad(F, ((1, 1), (1, 1), (0, 0)), mode="edge")
        avg = (pF[:-2, 1:-1] + pF[2:, 1:-1] + pF[1:-1, :-2] + pF[1:-1, 2:] +
               pF[:-2, :-2] + pF[:-2, 2:] + pF[2:, :-2] + pF[2:, 2:]) / 8.0
        F[mask] = avg[mask]

    ys, xs = np.where(mask)
    probe = (int(ys[len(ys) // 2]), int(xs[len(xs) // 2]))
    print("fill probe (y,x)->RGB:", (probe[0], probe[1], F[probe].round(0).tolist()))

    # --- background-grain noise ---
    bg_std = roi[srcmask].std(0).mean()
    rng = np.random.default_rng(args.seed)
    F[mask] += rng.normal(0, min(bg_std, 1.0), (int(mask.sum()), 3))
    F = np.clip(F, 0, 255)

    out = roi.copy()
    out[mask] = F[mask]

    # --- AA rebuild: blend toward mean color of DARK kept neighbors only ---
    pk = np.pad(keep, 1)  # constant False outside -> correct neighbor set
    colsum = np.zeros_like(out)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            colsum += roi * pk[1 + dy:1 + dy + keep.shape[0],
                               1 + dx:1 + dx + keep.shape[1], None]
    dn = nsum(keep.astype(np.float64))
    darkavg = colsum / np.maximum(dn, 1)[..., None]
    touch = mask & (dn > 0)
    out[touch] = 0.55 * out[touch] + 0.45 * darkavg[touch]
    dn2 = nsum(touch.astype(np.float64))
    t2 = mask & ~touch & (dn2 > 0)
    out[t2] = 0.8 * out[t2] + 0.2 * darkavg[t2]
    out = np.clip(out, 0, 255)
    print("blend probe:", (probe[0], probe[1], out[probe].round(0).tolist()))

    res = orig.copy()
    res[y0:y1, x0:x1] = out
    res8 = res.round().astype(np.uint8)
    Image.fromarray(res8).save(args.dst)
    print("saved:", args.dst)

    # --- verify 1: garish-pixel scan vs original (same count => artwork, not bug) ---
    def garish_count(arr):
        rr, gg, bb = arr[..., 0].astype(int), arr[..., 1].astype(int), arr[..., 2].astype(int)
        return int(((np.abs(rr - gg) > 40) | (np.abs(bb - gg) > 40)).sum())
    go, gn = garish_count(orig[y0:y1, x0:x1]), garish_count(res8[y0:y1, x0:x1])
    print(f"garish px in roi: original={go}  result={gn}  (result <= original is OK)")

    # --- verify 2: before/after zoom previews ---
    pdir = args.preview_dir or os.path.dirname(os.path.abspath(args.dst))
    px0, py0 = max(0, x0 - args.margin), max(0, y0 - args.margin)
    px1, py1 = min(W, x1 + args.margin), min(H, y1 + args.margin)
    cw, ch = px1 - px0, py1 - py0
    Image.fromarray(orig.round().astype(np.uint8)[py0:py1, px0:px1]).resize(
        (cw * args.zoom, ch * args.zoom)).save(os.path.join(pdir, "corner_before.png"))
    Image.fromarray(res8[py0:py1, px0:px1]).resize(
        (cw * args.zoom, ch * args.zoom)).save(os.path.join(pdir, "corner_after.png"))
    print("previews:", os.path.join(pdir, "corner_before.png"), "and",
          os.path.join(pdir, "corner_after.png"))


if __name__ == "__main__":
    main()
