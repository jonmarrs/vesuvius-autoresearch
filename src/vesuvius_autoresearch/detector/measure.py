"""No-retrain cross-scroll measurement: score one checkpoint across several fragments
(same-scroll vs cross-scroll) with the community metric contract and write a gap report."""

import json
import os

import numpy as np

from vesuvius_autoresearch.core.prediction_artifacts import prediction_stem
from vesuvius_autoresearch.core.report_artifacts import publish_report, report_output

from .data import read_image_mask
from .infer import infer
from .scoring import score_prediction

_COLS = [
    "val_f1",
    "f1_at_0.5",
    "average_precision",
    "ap_prevalence_lift",
    "precision",
    "recall",
    "positive_rate",
    "roc_auc",
]


def measure(cfg, checkpoint_path, targets, model=None):
    targets = list(targets)
    seen = set()
    if not targets:
        raise ValueError("measurement requires at least one target")
    for target in targets:
        if not isinstance(target, (tuple, list)) or len(target) != 2:
            raise ValueError("each target must be (fragment_id, scroll_label)")
        fid, scroll_label = target
        prediction_stem(fid)
        if fid in seen:
            raise ValueError(f"duplicate measurement fragment: {fid}")
        if not isinstance(scroll_label, str) or not scroll_label.strip():
            raise ValueError("scroll_label must be a nonempty string")
        seen.add(fid)
    report_output(
        cfg.reports_dir,
        "cross_scroll_measurement_manifest.json",
        "cross_scroll_measurement",
        inputs=() if checkpoint_path is None else (checkpoint_path,),
    )
    rows = {}
    for fragment_id, scroll_label in targets:
        try:
            prob = infer(cfg, checkpoint_path, fragment_id, model=model)
            _, label, mask = read_image_mask(cfg, fragment_id)
            h, w = label.shape
            m = score_prediction(prob[:h, :w], label, mask[:h, :w])
            m.pop("metrics_by_threshold", None)
            m["scroll_label"] = scroll_label
            rows[fragment_id] = m
        except Exception as exc:  # keep going; record the failure
            rows[fragment_id] = {"scroll_label": scroll_label, "error": str(exc)}
    _write_report(cfg, checkpoint_path, rows)
    return rows


def _cell(text):
    """Text as one Markdown table cell: whitespace runs, newlines among them,
    collapsed to a space, and pipes escaped. A checkpoint that fails to load
    raises a multi-line error, which would otherwise end the table."""
    return " ".join(str(text).split()).replace("|", "\\|")


def _fmt(v):
    return (
        f"{v:.4f}"
        if isinstance(v, (int, float)) and not isinstance(v, bool)
        else str(v)
    )


def _write_report(cfg, checkpoint_path, rows):
    lines = [
        "# Cross-Scroll Measurement",
        "",
        f"Checkpoint: `{checkpoint_path}`",
        "",
        "| fragment | scroll | " + " | ".join(_COLS) + " |",
        "|---|---|" + "|".join(["---"] * len(_COLS)) + "|",
    ]
    for fid, m in rows.items():
        if "error" in m:
            lines.append(
                f"| {_cell(fid)} | {_cell(m['scroll_label'])} | "
                f"ERROR: {_cell(m['error'])} |"
            )
            continue
        lines.append(
            f"| {_cell(fid)} | {_cell(m.get('scroll_label', ''))} | "
            + " | ".join(_fmt(m.get(c, float("nan"))) for c in _COLS)
            + " |"
        )
    failed = sum("error" in row for row in rows.values())
    metadata = {
        "checkpoint": str(checkpoint_path) if checkpoint_path is not None else None,
        "target_count": len(rows),
        "success_count": len(rows) - failed,
        "failure_count": failed,
        "report_status": "COMPLETE"
        if failed == 0
        else "FAILED"
        if failed == len(rows)
        else "PARTIAL",
    }
    publish_report(
        cfg.reports_dir,
        {
            "cross_scroll_measurement.md": ("\n".join(lines) + "\n").encode("utf-8"),
            "cross_scroll_measurement.json": (
                json.dumps(rows, indent=2, allow_nan=False) + "\n"
            ).encode("utf-8"),
        },
        "cross_scroll_measurement_manifest.json",
        metadata,
        "cross_scroll_measurement",
        inputs=() if checkpoint_path is None else (checkpoint_path,),
    )
