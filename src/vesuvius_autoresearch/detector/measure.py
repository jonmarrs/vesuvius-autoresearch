"""No-retrain cross-scroll measurement: score one checkpoint across several fragments
(same-scroll vs cross-scroll) with the community metric contract and write a gap report."""
import json
import os

import numpy as np

from .data import read_image_mask
from .infer import infer
from .metrics import segmentation_metrics

_COLS = ["val_f1", "f1_at_0.5", "average_precision", "ap_prevalence_lift",
         "precision", "recall", "positive_rate", "roc_auc"]


def measure(cfg, checkpoint_path, targets, model=None):
    os.makedirs(cfg.reports_dir, exist_ok=True)
    rows = {}
    for fragment_id, scroll_label in targets:
        try:
            prob = infer(cfg, checkpoint_path, fragment_id, model=model)
            _, label, mask = read_image_mask(cfg, fragment_id)
            h, w = label.shape
            m = segmentation_metrics(prob[:h, :w], (label > 0.5).astype(np.uint8),
                                     mask[:h, :w].astype(bool))
            m.pop("metrics_by_threshold", None)
            m["scroll_label"] = scroll_label
            rows[fragment_id] = m
        except Exception as exc:  # keep going; record the failure
            rows[fragment_id] = {"scroll_label": scroll_label, "error": str(exc)}
    _write_report(cfg, checkpoint_path, rows)
    return rows


def _fmt(v):
    return f"{v:.4f}" if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v)


def _write_report(cfg, checkpoint_path, rows):
    lines = ["# Cross-Scroll Measurement", "",
             f"Checkpoint: `{checkpoint_path}`", "",
             "| fragment | scroll | " + " | ".join(_COLS) + " |",
             "|---|---|" + "|".join(["---"] * len(_COLS)) + "|"]
    for fid, m in rows.items():
        if "error" in m:
            lines.append(f"| {fid} | {m['scroll_label']} | ERROR: {m['error']} |")
            continue
        lines.append(f"| {fid} | {m.get('scroll_label','')} | "
                     + " | ".join(_fmt(m.get(c, float('nan'))) for c in _COLS) + " |")
    with open(os.path.join(cfg.reports_dir, "cross_scroll_measurement.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(cfg.reports_dir, "cross_scroll_measurement.json"), "w") as f:
        json.dump(rows, f, indent=2)
