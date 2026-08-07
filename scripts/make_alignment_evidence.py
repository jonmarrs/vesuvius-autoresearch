#!/usr/bin/env python3
"""Render alignment evidence that can actually be judged by eye.

The old `overlay_vs_canon.png` painted the GT *opaquely on top of* a thresholded model
prediction. That hides the one thing a reader needs to see -- whether the two agree -- and
on a segment where the prediction is weak it shows nothing at all. villa PR #1280 was
closed partly on exactly this ("the provided ink registration example doesn't show the
alignment working"), and the reviewer was right.

This renders three panels at letterform scale:
    prediction alone | GT outline over prediction | agreement map
where the agreement map is colour-coded TP / GT-only / prediction-only, so a systematic
displacement shows up immediately as separated colour fringes rather than as a vague blur.

    uv run python scripts/make_alignment_evidence.py \
        --gt   ../scrollgt/data/scroll1_20231210121321/gt_ink.png \
        --pred local_data/sota_distill/20231210121321_y4000_x2500/20231210121321_y4000_x2500_inklabels.png \
        --out  ../scrollgt/data/scroll1_20231210121321/alignment_evidence.png
"""

import argparse

import numpy as np
from PIL import Image
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument(
        "--crop",
        type=int,
        default=1800,
        help="side length of the detail crop, in target px (default 1800)",
    )
    ap.add_argument("--panel", type=int, default=620, help="rendered panel size")
    args = ap.parse_args()

    gt = np.array(Image.open(args.gt)) > 127
    pred = np.array(Image.open(args.pred)) > 127
    if gt.shape != pred.shape:
        raise SystemExit(f"shape mismatch: {gt.shape} vs {pred.shape}")

    # densest GT crop, so the comparison is made where there is text to judge
    S, H = args.crop, gt.shape[0]
    step = max((H - S) // 8, 1)
    _, y, x = max(
        (gt[j : j + S, i : i + S].mean(), j, i)
        for j in range(0, H - S + 1, step)
        for i in range(0, H - S + 1, step)
    )
    g, p = gt[y : y + S, x : x + S], pred[y : y + S, x : x + S]

    P = args.panel

    def rs(m):
        img = Image.fromarray(m.astype(np.uint8) * 255).resize((P, P), Image.NEAREST)
        return np.array(img) > 127

    g, p = rs(g), rs(p)

    pred_panel = np.where(
        p[..., None], np.uint8([245, 245, 245]), np.uint8([18, 18, 18])
    )

    outline = pred_panel.copy()
    edge = g ^ ndimage.binary_erosion(g, iterations=2)
    outline[edge] = [255, 45, 45]

    agree = np.full((P, P, 3), 18, np.uint8)
    agree[g & p] = [70, 200, 120]  # both  -> green
    agree[g & ~p] = [255, 60, 60]  # GT only -> red
    agree[~g & p] = [70, 130, 255]  # prediction only -> blue

    gap = np.full((P, 14, 3), 90, np.uint8)
    Image.fromarray(np.concatenate([pred_panel, gap, outline, gap, agree], 1)).save(
        args.out
    )

    inter = int((g & p).sum())
    print(f"crop at y={y} x={x} (size {S})")
    print(
        f"  Dice {2 * inter / max(int(g.sum()) + int(p.sum()), 1):.4f}   "
        f"IoU {inter / max(int((g | p).sum()), 1):.4f}"
    )
    print(f"  wrote {args.out}")
    print(
        "  panels: prediction | GT outline over prediction | "
        "green=agree, red=GT-only, blue=prediction-only"
    )


if __name__ == "__main__":
    main()
