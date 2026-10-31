"""Score detector predictions and publish a verified report generation."""

import csv
import io

import numpy as np
from PIL import Image

from vesuvius_autoresearch.core.prediction_artifacts import prediction_stem
from vesuvius_autoresearch.core.report_artifacts import publish_report, report_output

from .scoring import score_prediction


def evaluate(prob_map, label, mask, cfg, fragment_id="frag", checkpoint=None):
    """Keep legacy filenames/metric aliases; publish the scorecard last.

    All files are staged and read back before replacing previous reports. Caught
    publication errors restore the previous generation. Readers/writers must be
    serialized; use check_detector_report.py before trusting report files.
    """
    prediction_stem(fragment_id)
    report_output(
        cfg.reports_dir,
        f"{fragment_id}_scorecard.json",
        "detector_evaluation",
        inputs=() if checkpoint is None else (checkpoint,),
    )
    m = score_prediction(prob_map, label, mask)
    by_thr = m.pop("metrics_by_threshold", [])
    card = {"fragment_id": fragment_id, **m, "report_status": "COMPLETE"}
    if checkpoint is not None:
        card["checkpoint"] = str(checkpoint)
    card["pixel_auc"] = m.get("roc_auc", float("nan"))
    card["threshold"] = m.get("best_threshold", float("nan"))
    table = io.StringIO(newline="")
    writer = csv.DictWriter(
        table, fieldnames=["threshold", "precision", "recall", "f1", "f05"]
    )
    writer.writeheader()
    writer.writerows(by_thr)

    thumb = (np.clip(prob_map, 0, 1) * 255).astype(np.uint8)
    h, w = thumb.shape
    thumbnail = Image.fromarray(thumb).resize((max(1, w // 8), max(1, h // 8)))
    buffer = io.BytesIO()
    thumbnail.save(buffer, format="PNG")
    with Image.open(io.BytesIO(buffer.getvalue())) as back:
        if not np.array_equal(np.asarray(back), np.asarray(thumbnail)):
            raise OSError("thumbnail readback failed")
    payloads = {
        f"{fragment_id}_metrics_by_threshold.csv": table.getvalue().encode("utf-8"),
        f"{fragment_id}_pred_thumb.png": buffer.getvalue(),
    }
    return publish_report(
        cfg.reports_dir,
        payloads,
        f"{fragment_id}_scorecard.json",
        card,
        "detector_evaluation",
        inputs=() if checkpoint is None else (checkpoint,),
    )
