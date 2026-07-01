# repro/sota_data/evaluate.py
"""Evaluate the existing detector on a converted SOTA segment with A's metric contract and
write a report comparing to the old-data Scroll-1 baseline. Operational (loads a checkpoint,
runs GPU inference)."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath("."))
from vesuvius_autoresearch.detector.config import DetectorConfig
from vesuvius_autoresearch.detector.data import read_image_mask
from vesuvius_autoresearch.detector.infer import infer
from vesuvius_autoresearch.detector.metrics import segmentation_metrics

BASELINE = {"val_f1": 0.2218, "average_precision": 0.1445,
            "ap_prevalence_lift": 1.2904, "roc_auc": 0.5848}


def evaluate_segment(seg_id, data_root="local_data/sota_scroll1",
                     checkpoint="models/detector/detector_epoch=7.ckpt"):
    cfg = DetectorConfig(data_root=data_root)
    prob = infer(cfg, checkpoint, seg_id)
    _, label, mask = read_image_mask(cfg, seg_id)
    h, w = label.shape
    m = segmentation_metrics(prob[:h, :w], (label > 0.5).astype(np.uint8),
                             mask[:h, :w].astype(bool))
    m.pop("metrics_by_threshold", None)
    os.makedirs("reports/detector", exist_ok=True)
    cols = ["val_f1", "average_precision", "ap_prevalence_lift", "roc_auc"]
    lines = ["# Detector on SOTA Scroll-1 data vs old data", "",
             f"Segment: `{seg_id}`  |  checkpoint: `{checkpoint}`", "",
             "| source | " + " | ".join(cols) + " |",
             "|---|" + "|".join(["---"] * len(cols)) + "|",
             "| old 8-bit Scroll-1 (20230702185753) | "
             + " | ".join(f"{BASELINE[c]:.4f}" for c in cols) + " |",
             "| SOTA data (" + seg_id + ") | "
             + " | ".join(f"{m.get(c, float('nan')):.4f}" for c in cols) + " |"]
    with open("reports/detector/sota_scroll1_measurement.md", "w") as f:
        f.write("\n".join(lines) + "\n")
    with open("reports/detector/sota_scroll1_measurement.json", "w") as f:
        json.dump({"segment": seg_id, "sota": m, "baseline": BASELINE}, f, indent=2)
    print(f"SOTA {seg_id}: val_f1={m.get('val_f1', float('nan')):.4f} ap={m.get('average_precision', float('nan')):.4f} "
          f"lift={m.get('ap_prevalence_lift', float('nan')):.4f} (old baseline val_f1={BASELINE['val_f1']})",
          flush=True)
    return m


if __name__ == "__main__":
    evaluate_segment(sys.argv[1])
