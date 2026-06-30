# src/vesuvius_autoresearch/detector/eval.py
"""Evaluate a prediction with the community metric contract (F1-swept primary, AP +
prevalence-lift gates, ROC-AUC secondary), writing a scorecard, a per-threshold CSV, and a
thumbnail. Does NOT gate on skel_dist (FINDINGS.md Phase 4b)."""
import csv
import json
import os

import numpy as np
from PIL import Image

from .metrics import segmentation_metrics


def evaluate(prob_map, label, mask, cfg, fragment_id="frag"):
    os.makedirs(cfg.reports_dir, exist_ok=True)
    m = segmentation_metrics(prob_map, label, mask)
    by_thr = m.pop("metrics_by_threshold", [])
    card = {"fragment_id": fragment_id, **m}
    # Backward-compat aliases (cli.assert_auc / reproduce gate / older readers use these).
    card["pixel_auc"] = m.get("roc_auc", float("nan"))
    card["threshold"] = m.get("best_threshold", float("nan"))

    with open(os.path.join(cfg.reports_dir, f"{fragment_id}_metrics_by_threshold.csv"),
              "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["threshold", "precision", "recall", "f1", "f05"])
        writer.writeheader()
        for row in by_thr:
            writer.writerow(row)

    thumb = (np.clip(prob_map, 0, 1) * 255).astype(np.uint8)
    h, w = thumb.shape
    Image.fromarray(thumb).resize((max(1, w // 8), max(1, h // 8))).save(
        os.path.join(cfg.reports_dir, f"{fragment_id}_pred_thumb.png"))
    with open(os.path.join(cfg.reports_dir, f"{fragment_id}_scorecard.json"), "w") as f:
        json.dump(card, f, indent=2)
    return card
