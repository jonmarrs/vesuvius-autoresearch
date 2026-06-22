# repro/gp_winner/prize_gate_eval.py
"""Score a prediction PNG through the villa prize topology gates over a threshold sweep,
reporting the topology-optimal centerline_dice + its skel_dist + pixel-AUC. Reuses the
villa metric functions (not reimplemented)."""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

# --- villa metrics (loop .venv); wandb must be init'd disabled before skel_dist ---
_VILLA = os.path.join(
    os.path.dirname(__file__), "..", "..", "villa", "segmentation", "evaluation"
)
if os.path.isdir(_VILLA) and os.path.abspath(_VILLA) not in sys.path:
    sys.path.append(os.path.abspath(_VILLA))


def _ensure_wandb_disabled():
    os.environ.setdefault("WANDB_MODE", "disabled")
    import wandb

    if wandb.run is None:
        wandb.init(mode="disabled")


def _centerline_dice(label, pred, **k):
    from metrics.centerline_dice import compute

    return compute(label, pred, **k)


def _skel_dist(label, pred, **k):
    from metrics.skeleton_distance_length import compute

    return compute(label, pred, **k)


def load_pred_label_mask(pred_png, label_png, mask_png=None):
    """Load a probability prediction PNG (0..255 -> [0,1]), an inklabels PNG (>127 -> {0,1}),
    and an optional papyrus mask; crop all to the common H x W."""
    prob = np.array(Image.open(pred_png).convert("L")).astype(np.float32) / 255.0
    label = (np.array(Image.open(label_png).convert("L")) > 127).astype(np.uint8)
    if mask_png and os.path.exists(mask_png):
        mask = np.array(Image.open(mask_png).convert("L")) > 127
    else:
        mask = np.ones(label.shape, bool)
    h = min(prob.shape[0], label.shape[0], mask.shape[0])
    w = min(prob.shape[1], label.shape[1], mask.shape[1])
    return prob[:h, :w], label[:h, :w], mask[:h, :w]


def sweep_topology(prob, label, mask, thresholds):
    """For each threshold, binarize prob*mask and compute villa centerline_dice + skel_dist
    on (1,H,W) arrays; return the topology-optimal (max centerline_dice) result + pixel-AUC."""
    from sklearn.metrics import roc_auc_score

    m = mask.astype(bool)
    y = label * m
    sel = m.ravel()
    auc = (
        float(roc_auc_score(label.ravel()[sel], prob.ravel()[sel]))
        if label[m].min() != label[m].max()
        else 0.5
    )
    lab3 = y[None].astype(np.uint8)
    per = []
    best = None
    for t in thresholds:
        pred_bin = ((prob >= t) & m).astype(np.uint8)[None]
        cd = _centerline_dice(lab3, pred_bin)
        cdv = float(cd["centerline_dice"]) if isinstance(cd, dict) else float(cd)
        sk = float(_skel_dist(lab3, pred_bin))
        row = {"threshold": float(t), "centerline_dice": cdv, "skel_dist": sk}
        per.append(row)
        if best is None or cdv > best["centerline_dice"]:
            best = row
    return {
        "best_threshold": best["threshold"],
        "centerline_dice": best["centerline_dice"],
        "skel_dist": best["skel_dist"],
        "pixel_auc": auc,
        "per_threshold": per,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--mask", default="")
    ap.add_argument("--out", required=True, help="JSON scorecard path")
    ap.add_argument("--thresholds", default="0.2,0.3,0.4,0.5,0.6,0.7")
    args = ap.parse_args()
    _ensure_wandb_disabled()
    prob, label, mask = load_pred_label_mask(args.pred, args.label, args.mask or None)
    ths = [float(x) for x in args.thresholds.split(",")]
    res = sweep_topology(prob, label, mask, ths)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(res, f, indent=2)
    print(
        f"pixel_auc={res['pixel_auc']:.4f} centerline_dice={res['centerline_dice']:.4f} "
        f"skel_dist={res['skel_dist']:.3f} @thr={res['best_threshold']}"
    )


if __name__ == "__main__":
    main()
