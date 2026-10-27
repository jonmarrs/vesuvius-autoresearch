"""The replicate rule in the live loop, beside train.py's single-cycle margin (adopted by the owner on 2026-10-27).

As registered (docs/preregistration/2026-10-26_loop_replicate_rule_window.md) and tested on the batchgeneratorsv2
window (reports/loop_confirmation_readout_2026-10-27.md): at the end of each scored cycle of tweak T, each of T's
cycles so far is set against the mean of the other tweaks' cycles so far in its code epoch (kept when that epoch has
at least 10 of them), and Student's t of those differences is taken for val_f1 and for ROC AUC. With at least 6 of T's
cycles, the score is the smaller t; above c = 4.5 the rule fires. The scoring is scripts/loop_replicate_rule.scores at
its REGISTERED values, imported, not copied.

The cycles are cycles.jsonl's: those that faced this checkpoint's bytes at this budget, validation protocol and input
fingerprint, with complete matching patch counts (not crashed or blocked), in order, with this cycle last. Older
records without a checkpoint identity cannot support the rule. A code epoch is a commit and its uncommitted
changes to what a cycle runs (the record's commit and code_changes). A firing promotes this cycle's own candidate,
last_model.pt, only if it passes every other gate of train.py's promotion_decision and beats the incumbent (eligible).

Importing this module loads neither torch nor the trainer; scoring imports SciPy only when needed.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict
from pathlib import Path

from scripts.training.promotion import (  # noqa: F401
    HISTORY_COLUMNS,
    LIFT_MARGIN,
    VALIDATION_SAMPLE_PATCHES,
)

SCORED = ("REVERTED", "SUCCESS")


def epoch(record: dict) -> str:
    return json.dumps([record.get("commit"), record.get("code_changes")])


def _validation_key(result: dict) -> tuple | None:
    diag = result.get("validation_diag")
    if not isinstance(diag, dict):
        return None
    protocol, inputs = result.get("val_protocol"), diag.get("inputs_sha256")
    requested = diag.get("requested_patches")
    if (
        not isinstance(protocol, str)
        or not protocol
        or diag.get("protocol") != protocol
        or not isinstance(inputs, str)
        or not inputs
        or diag.get("complete") is not True
        or diag.get("batch_errors") != 0
        or not isinstance(requested, int)
        or isinstance(requested, bool)
        or not 0 < requested <= VALIDATION_SAMPLE_PATCHES
        or diag.get("scored_patches") != requested
    ):
        return None
    return protocol, inputs, requested


def _scored(record: dict) -> bool:
    result = record.get("result")
    if record.get("status") not in SCORED or not isinstance(result, dict):
        return False
    if result.get("promotion_blocked"):
        return False
    if _validation_key(result) is None or not record.get("incumbent_sha256"):
        return False
    return all(
        isinstance(result.get(k), (int, float)) and math.isfinite(result[k])
        for k in ("val_f1", "roc_auc", "incumbent_val_f1")
    )


def rows(records: list[dict], current: dict) -> list[dict]:
    """The cycles the rule reads at the end of current: those that faced its incumbent at its budget, it last."""
    inc, budget = current["result"]["incumbent_val_f1"], current.get("budget_s")
    same = [
        r
        for r in records
        if _scored(r)
        and r["result"]["incumbent_val_f1"] == inc
        and r.get("incumbent_sha256") == current.get("incumbent_sha256")
        and _validation_key(r["result"]) == _validation_key(current["result"])
        and r.get("budget_s") == budget
    ]
    return [
        {
            "start": r.get("started"),
            "tweak": r["tweak"],
            "epoch": epoch(r),
            "val_f1": r["result"]["val_f1"],
            "roc_auc": r["result"]["roc_auc"],
        }
        for r in [*same, current]
    ]


def decide(records: list[dict], current: dict) -> dict:
    """The rule's score for current's tweak at current's end, and whether it fires."""
    from scripts.loop_replicate_rule import MEASURES, REGISTERED, scores

    if not _scored(current):
        return {"tweak": current.get("tweak"), "score": None, "fires": False, "reason": "not scored"}  # fmt: skip
    read = rows(records, current)
    measures = MEASURES[REGISTERED["measures"]]
    labels = [r["tweak"] for r in read]
    s = float(scores(read, labels, measures, REGISTERED["min_cycles"], REGISTERED["min_others"])[-1])  # fmt: skip
    return {
        "tweak": current["tweak"],
        "score": round(s, 4) if math.isfinite(s) else (None if s < 0 else "inf"),
        "fires": s > REGISTERED["c"],
        "c": REGISTERED["c"],
        "tweak_cycles": labels.count(current["tweak"]),
        "cycles": len(read),
    }


def eligible(result: dict, enforce_prize_gates: bool) -> str | None:
    """Why this cycle's candidate cannot be promoted, or None: every gate of train.py's promotion_decision but the
    margin, and it must beat the incumbent."""
    if result.get("promotion_blocked"):
        return f"its comparison was blocked ({result['promotion_blocked']})"
    if (result.get("validation_diag") or {}).get("complete") is not True:
        return "its validation sample is incomplete"
    if enforce_prize_gates and result.get("submittable") is not True:
        return "it fails the prize gates"
    lift = result.get("ap_prevalence_lift")
    if not (isinstance(lift, (int, float)) and math.isfinite(lift) and lift > 1 + LIFT_MARGIN):  # fmt: skip
        return f"its AP lift {lift} is not above {1 + LIFT_MARGIN}"
    f1, inc = result.get("val_f1"), result.get("incumbent_val_f1")
    if not (isinstance(f1, (int, float)) and isinstance(inc, (int, float)) and f1 > inc):  # fmt: skip
        return f"its val_f1 {f1} does not beat the incumbent's {inc}"
    return None


def promote(loop: Path, result: dict, stamp: str, incumbent_sha256: str) -> Path:
    """Promote this cycle's candidate (last_model.pt) as train.py would have; returns where the old files were kept.
    The loop then does the rest of a promotion: config.json, the family's weight, the commit."""
    from scripts import promote_loop_candidate as P

    path = loop / "last_model.pt"
    raw = path.read_bytes()
    candidate = P.checkpoint(raw)
    if any(
        candidate.get(k) != result.get(k)
        for k in (
            "val_f1",
            "val_protocol",
            "roc_auc",
            "ap_prevalence_lift",
            "validation_diag",
            "submittable",
        )
    ):
        raise RuntimeError("last_model.pt is not this cycle's candidate")
    config = asdict(P.ExperimentConfig.load(str(loop / "config_temp.json")))
    if candidate.get("config") != config:
        raise RuntimeError("last_model.pt is not this cycle's candidate config")
    incumbent_raw = (loop / P.INCUMBENT).read_bytes()
    if hashlib.sha256(incumbent_raw).hexdigest() != incumbent_sha256:
        raise RuntimeError("the incumbent changed during this cycle")
    incumbent = P.checkpoint(incumbent_raw)
    if incumbent.get("val_f1") != result.get("incumbent_val_f1"):
        raise RuntimeError("the incumbent score does not match this cycle")
    inputs = P.validation_inputs_fingerprint(
        config["val_uri"], config.get("depth_band")
    )
    failed = [
        name
        for name, ok, _ in P.comparison_checks(candidate, incumbent, config, inputs)
        if not ok
    ]
    if failed:
        raise RuntimeError(f"candidate comparison failed: {', '.join(failed)}")
    new_rows = P.rows(P.history_row(loop, candidate), candidate, stamp)
    if (loop / P.INCUMBENT).read_bytes() != incumbent_raw:
        raise RuntimeError("the incumbent changed before promotion")
    if (
        P.validation_inputs_fingerprint(config["val_uri"], config.get("depth_band"))
        != inputs
    ):
        raise RuntimeError("validation inputs changed before promotion")
    return P.promote_files(loop, raw, new_rows, stamp)
