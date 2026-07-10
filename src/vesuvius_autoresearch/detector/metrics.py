"""Community-aligned segmentation metrics for ink detection: threshold-swept F1 (primary),
average precision and prevalence-lift (honest, imbalance-robust gates), with ROC-AUC kept
only as a secondary diagnostic. Mask-restricted, pooled over the fragment."""
from typing import Any

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

_DEGENERATE_KEYS = [
    "val_f1", "best_threshold", "f1_at_0.5", "val_f05", "precision", "recall",
    "pred_positive_rate", "average_precision", "ap_prevalence_lift", "roc_auc",
]


def _fbeta(precision, recall, beta):
    b2 = beta * beta
    denom = b2 * precision + recall
    return (1.0 + b2) * precision * recall / denom if denom > 0 else 0.0


def _confusion_at(p, y, t):
    pred = (p >= t).astype(np.uint8)
    tp = int(((pred == 1) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return precision, recall, int(pred.sum())


def segmentation_metrics(prob, label, mask, thresholds=None):
    if thresholds is None:
        thresholds = np.linspace(0.05, 0.95, 19)
    sel = np.asarray(mask).astype(bool)
    p = np.asarray(prob)[sel].astype(np.float64)
    y = (np.asarray(label)[sel] > 0.5).astype(np.uint8)
    n = int(y.size)
    pos = int(y.sum())
    positive_rate = pos / n if n else float("nan")
    card: dict[str, Any] = {"positive_rate": positive_rate, "n_pixels": n}

    if pos == 0 or pos == n or n == 0:
        card.update({k: float("nan") for k in _DEGENERATE_KEYS})
        card["note"] = "degenerate: mask has no positive/negative contrast"
        card["metrics_by_threshold"] = []
        return card

    by_thr = []
    best = {"f1": -1.0, "threshold": 0.5, "precision": 0.0, "recall": 0.0,
            "pred_positive_rate": 0.0}
    best_f05 = -1.0
    for t in thresholds:
        precision, recall, pred_pos = _confusion_at(p, y, float(t))
        f1 = _fbeta(precision, recall, 1.0)
        f05 = _fbeta(precision, recall, 0.5)
        by_thr.append({"threshold": float(t), "precision": precision,
                       "recall": recall, "f1": f1, "f05": f05})
        if f1 > best["f1"]:
            best = {"f1": f1, "threshold": float(t), "precision": precision,
                    "recall": recall, "pred_positive_rate": pred_pos / n}
        best_f05 = max(best_f05, f05)

    pr_half, rc_half, _ = _confusion_at(p, y, 0.5)
    ap = float(average_precision_score(y, p))
    card.update({
        "val_f1": best["f1"],
        "best_threshold": best["threshold"],
        "f1_at_0.5": _fbeta(pr_half, rc_half, 1.0),
        "val_f05": best_f05,
        "precision": best["precision"],
        "recall": best["recall"],
        "pred_positive_rate": best["pred_positive_rate"],
        "average_precision": ap,
        "ap_prevalence_lift": ap / positive_rate if positive_rate > 0 else float("nan"),
        "roc_auc": float(roc_auc_score(y, p)),  # secondary diagnostic ONLY
        "metrics_by_threshold": by_thr,
    })
    return card
