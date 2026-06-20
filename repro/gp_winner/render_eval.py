# repro/gp_winner/render_eval.py
"""Downscale a GP-winner inference prediction to an inspectable thumbnail, and
(optionally) compute pixel-AUC against an inklabels.png if one is provided."""

import argparse
import os

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True, help="prediction PNG from inference")
    ap.add_argument("--out", required=True, help="thumbnail PNG path")
    ap.add_argument("--scale", type=int, default=8)
    ap.add_argument("--label", default="", help="optional inklabels.png for AUC")
    args = ap.parse_args()

    p = np.array(Image.open(args.pred).convert("L")).astype(np.float32)
    h, w = p.shape
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    Image.fromarray(p.astype(np.uint8)).resize((w // args.scale, h // args.scale)).save(
        args.out
    )
    print(f"thumbnail {args.out} ({w // args.scale}x{h // args.scale})")

    if args.label and os.path.exists(args.label):
        from sklearn.metrics import roc_auc_score

        y = (np.array(Image.open(args.label).convert("L")) > 127).astype(int)
        if y.shape == p.shape and y.min() != y.max():
            print(f"pixel_auc={roc_auc_score(y.ravel(), (p / 255.0).ravel()):.4f}")
        else:
            print("label/pred shape mismatch or single-class; skipping AUC")


if __name__ == "__main__":
    main()
