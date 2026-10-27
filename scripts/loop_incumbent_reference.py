"""Compare the published pre-window cycles with metrics already saved in their incumbent.

This reads checkpoint metadata on CPU, without constructing a model or loading
validation data. It is a historical reference comparison, not a new evaluation
or an unchanged-training control. The confirmation window is refused.

python3 scripts/loop_incumbent_reference.py --checkpoint best_model.pt \
    --record reports/loop_tweak_replication_2026-10-25.json --out reports/reference.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loop_tweak_replication import REGISTERED


MEASURES = {
    "val_f1": ("val_f1", 0.0),
    "roc_auc": ("roc_auc", 0.00005),
    "ap_lift": ("ap_prevalence_lift", 0.00005),
}


def checkpoint_metadata(raw: bytes) -> dict:
    # NumPy scalar metadata occurs in the published checkpoint. Keep the
    # allowlist scoped; weights-only deserialization does not construct a model.
    try:
        from numpy._core.multiarray import scalar
    except ImportError:
        from numpy.core.multiarray import scalar
    allowed = [scalar, np.dtype, type(np.dtype("float64")), type(np.dtype("float32"))]
    with torch.serialization.safe_globals(allowed):
        saved = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)
    config, diag = saved.get("config", {}), saved.get("validation_diag", {})
    protocol = saved.get("val_protocol")
    if protocol != "seeded-sample-400-v3+z1-27" or diag.get("protocol") != protocol:
        raise ValueError(
            "the saved reference must use the loop's recorded v3 depth-band protocol"
        )
    if (
        diag.get("complete") is not True
        or diag.get("requested_patches") != 400
        or diag.get("scored_patches") != 400
        or diag.get("batch_errors") != 0
    ):
        raise ValueError("the saved reference has incomplete validation")
    metrics = {name: float(saved[name]) for name, _ in MEASURES.values()}
    if not all(math.isfinite(v) for v in metrics.values()):
        raise ValueError("saved reference metrics must be finite")
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1": hashlib.sha1(
            b"blob " + str(len(raw)).encode() + b"\0" + raw
        ).hexdigest(),
        "metrics": metrics,
        "validation_diag": diag,
        "val_protocol": protocol,
        "config": {
            k: config.get(k)
            for k in (
                "architecture", "num_layers", "patch_size", "val_uri", "depth_band", "use_lasagna"
            )
        },
    }


def compare(record: dict, reference: dict) -> dict:
    rows = record["rows"]
    boundary = dt.datetime.fromisoformat(REGISTERED["since"])
    if not rows or any(dt.datetime.fromisoformat(r["start"]) >= boundary for r in rows):
        raise ValueError("only the published cycles before the confirmation window are allowed")
    incumbent = reference["metrics"]["val_f1"]
    if not math.isclose(record["incumbent"], incumbent, abs_tol=0.0000005, rel_tol=0):
        raise ValueError("the record and saved reference name different incumbents")
    if any(
        not math.isclose(r["incumbent"], incumbent, abs_tol=0.0000005, rel_tol=0)
        for r in rows
    ):
        raise ValueError("a cycle names another incumbent")
    groups = {
        "all_cycles": rows,
        "batchgeneratorsv2": [r for r in rows if r["tweak"] == REGISTERED["standing"]],
        "other_tweaks": [r for r in rows if r["tweak"] != REGISTERED["standing"]],
    }
    results = {}
    for name, members in groups.items():
        if not members:
            raise ValueError(f"no cycles for {name}")
        measured = {}
        for metric, (stored, rounding) in MEASURES.items():
            values = [float(r[metric]) for r in members]
            if not all(math.isfinite(v) for v in values):
                raise ValueError("cycle metrics must be finite")
            baseline = reference["metrics"][stored]
            above = sum(v - rounding > baseline for v in values)
            below = sum(v + rounding < baseline for v in values)
            mean = statistics.mean(values)
            measured[metric] = {
                "saved_reference": baseline,
                "recorded_mean": mean,
                "mean_minus_saved": mean - baseline,
                "log_rounding_half_width": rounding,
                "definitely_above": above,
                "definitely_below": below,
                "rounding_overlap": len(values) - above - below,
            }
        results[name] = {"cycles": len(members), "metrics": measured}
    return {
        "measurement": "saved checkpoint metadata; no new inference",
        "cycles": len(rows),
        "last_start": max(r["start"] for r in rows),
        "reference": reference,
        "groups": results,
        "limits": [
            "Descriptive comparison with one saved measurement; no significance test.",
            "Cycle rows omit per-cycle validation input fingerprints; exact input equality is not independently verified.",
            "Historical checkpoint metrics, not a fresh evaluation under today's runtime.",
            "A zero-step saved model is not a same-budget unchanged-training control.",
            "One selected incumbent and one reused Fr143 validation sample; no cross-scroll claim.",
            "Does not change the registered confirmation, promotion rule or live loop.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    for source in (args.checkpoint, args.record):
        if args.out.resolve() == source.resolve() or (
            args.out.exists() and args.out.samefile(source)
        ):
            raise ValueError("the output must not replace either input")
    # Hash and deserialize the same captured bytes, even if a source is replaced.
    checkpoint_raw, record_raw = args.checkpoint.read_bytes(), args.record.read_bytes()
    result = compare(json.loads(record_raw), checkpoint_metadata(checkpoint_raw))
    result["sources"] = {
        "checkpoint": str(args.checkpoint),
        "record": str(args.record),
        "record_sha256": hashlib.sha256(record_raw).hexdigest(),
    }
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"cycles": result["cycles"], "groups": result["groups"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
