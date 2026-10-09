"""Measure label agreement on a declared region and confident subset.

AUC uses thresholded hard labels, not teacher probabilities. Undefined metrics
are null; neither missing predictions nor one-class truth establishes chance.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pseudo_label_artifacts import (
    MAX_LABEL_PIXELS,
    binary_array,
    pseudo_array,
    read_png,
)


def score_pseudo(pseudo, true, region=None):
    pseudo = pseudo_array(pseudo)
    true = binary_array(true, "ground truth", pseudo.shape)
    region = (
        np.ones(pseudo.shape, bool)
        if region is None
        else binary_array(region, "region", pseudo.shape)
    )
    requested = int(region.sum())
    if not requested:
        raise ValueError("region must contain requested pixels")
    confident = (pseudo != 128) & region
    count = int(confident.sum())
    pred, gt = pseudo[confident] == 255, true[confident]
    tp = int((pred & gt).sum())
    fp = int((pred & ~gt).sum())
    fn = int((~pred & gt).sum())
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    auc = float(roc_auc_score(gt, pred)) if count and gt.min() != gt.max() else None
    return {
        "status": "MEASURED"
        if all(v is not None for v in (precision, recall, auc))
        else "INDETERMINATE",
        "coverage": count / requested,
        "precision": precision,
        "recall": recall,
        "auc": auc,
        "auc_kind": "hard_label_roc_auc_on_confident_subset",
        "requested_pixels": requested,
        "confident_pixels": count,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "accuracy_verified": False,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pseudo", required=True)
    ap.add_argument("--true", required=True, help="binary ground-truth PNG")
    ap.add_argument("--region-mask", required=True)
    ap.add_argument("--max-pixels", type=int, default=MAX_LABEL_PIXELS)
    args = ap.parse_args(argv)
    try:
        pseudo = read_png(args.pseudo, kind="pseudo", max_pixels=args.max_pixels)
        true = read_png(
            args.true, kind="binary", shape=pseudo.shape, max_pixels=args.max_pixels
        )
        region = read_png(
            args.region_mask,
            kind="binary",
            shape=pseudo.shape,
            max_pixels=args.max_pixels,
        )
        result = score_pseudo(pseudo, true, region)
    except (ValueError, OSError) as exc:
        ap.exit(1, f"pseudo-label quality: {exc}\n")
    print(json.dumps(result, allow_nan=False, sort_keys=True))
    if result["status"] != "MEASURED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
