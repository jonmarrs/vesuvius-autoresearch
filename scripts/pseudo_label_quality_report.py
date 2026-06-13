"""Score confidence-filtered pseudo-labels against known ground truth within a
region: coverage (fraction of confident pixels) and precision/recall/AUC on the
confident subset. Used to judge pseudo-label quality before self-training."""

import argparse

import numpy as np
from PIL import Image
from sklearn.metrics import roc_auc_score

Image.MAX_IMAGE_PIXELS = None


def score_pseudo(pseudo, true):
    """pseudo: uint8 [H,W] with values {0,128,255}; true: binary [H,W] (0/1 or
    0/255). Returns coverage + precision/recall/auc over confident pixels."""
    true_bin = (true > 127).astype(int) if true.max() > 1 else true.astype(int)
    confident = pseudo != 128
    coverage = float(confident.mean())
    if confident.sum() == 0:
        return {"coverage": 0.0, "precision": 0.0, "recall": 0.0, "auc": 0.5}
    pred = (pseudo[confident] == 255).astype(int)
    gt = true_bin[confident]
    tp = int(((pred == 1) & (gt == 1)).sum())
    fp = int(((pred == 1) & (gt == 0)).sum())
    fn = int(((pred == 0) & (gt == 1)).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    auc = roc_auc_score(gt, pred) if gt.min() != gt.max() else 0.5
    return {
        "coverage": coverage,
        "precision": precision,
        "recall": recall,
        "auc": float(auc),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pseudo", required=True)
    ap.add_argument("--true", required=True, help="true inklabels.png")
    ap.add_argument("--region-mask", required=True)
    args = ap.parse_args()
    pseudo = np.array(Image.open(args.pseudo).convert("L"))
    true = np.array(Image.open(args.true).convert("L"))
    region = np.array(Image.open(args.region_mask).convert("L")) > 127
    pseudo = np.where(region, pseudo, 128).astype(np.uint8)
    r = score_pseudo(pseudo, true)
    print(
        f"coverage={r['coverage']:.3f} precision={r['precision']:.3f} "
        f"recall={r['recall']:.3f} auc={r['auc']:.3f}"
    )


if __name__ == "__main__":
    main()
