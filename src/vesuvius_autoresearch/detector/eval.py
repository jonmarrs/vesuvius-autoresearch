"""Evaluate a prediction: mask-restricted pixel-AUC + a calibrated binarization threshold,
plus a thumbnail and JSON scorecard. Does NOT gate on skel_dist (FINDINGS.md Phase 4b)."""
import json
import os
import sys

import numpy as np
from PIL import Image

_REPO = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir)
if os.path.abspath(os.path.join(_REPO, "scripts")) not in sys.path:
    sys.path.append(os.path.abspath(os.path.join(_REPO, "scripts")))


def _pixel_auc(prob, label, mask):
    from pixel_auc import pooled_pixel_auc
    sel = mask.astype(bool)
    return float(pooled_pixel_auc([prob[sel]], [label[sel].astype(np.uint8)]))


def _youden_threshold(prob, label, mask):
    sel = mask.astype(bool)
    p, y = prob[sel], label[sel].astype(np.uint8)
    best_t, best_j = 0.5, -1.0
    for t in np.linspace(0.1, 0.9, 17):
        pred = (p >= t).astype(np.uint8)
        tp = int(((pred == 1) & (y == 1)).sum())
        fp = int(((pred == 1) & (y == 0)).sum())
        fn = int(((pred == 0) & (y == 1)).sum())
        tn = int(((pred == 0) & (y == 0)).sum())
        tpr = tp / (tp + fn) if (tp + fn) else 0.0
        fpr = fp / (fp + tn) if (fp + tn) else 0.0
        j = tpr - fpr
        if j > best_j:
            best_j, best_t = j, float(t)
    return best_t


def evaluate(prob_map, label, mask, cfg, fragment_id="frag"):
    os.makedirs(cfg.reports_dir, exist_ok=True)
    auc = _pixel_auc(prob_map, label, mask)
    threshold = _youden_threshold(prob_map, label, mask)
    card = {"fragment_id": fragment_id, "pixel_auc": auc, "threshold": threshold,
            "centerline_dice": float("nan")}
    thumb = (np.clip(prob_map, 0, 1) * 255).astype(np.uint8)
    h, w = thumb.shape
    Image.fromarray(thumb).resize((max(1, w // 8), max(1, h // 8))).save(
        os.path.join(cfg.reports_dir, f"{fragment_id}_pred_thumb.png"))
    with open(os.path.join(cfg.reports_dir, f"{fragment_id}_scorecard.json"), "w") as f:
        json.dump(card, f, indent=2)
    return card
