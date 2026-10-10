"""The registered verdict logic of scripts/scrollgt_current_annotations_analysis.py, on synthetic rows: a partial sample
or any fidelity mismatch must refuse a verdict, and the predictions must read the rows they claim to."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import scrollgt_current_annotations_analysis as a  # noqa: E402


def _row(erl=50.0, pen=40.0, cov=0.6, prec=0.3, merges=10, splits=20, n=100) -> dict:
    return {"scoring_version": 2, "erl": erl, "erl_merge_penalized": pen, "coverage": cov, "precision": prec,
            "splits": splits, "merges": merges, "merged_instances": merges, "n_gt_fibers": 100,
            "n_pred_instances": n, "gt_length": 1000.0, "pred_length": 5000.0, "tolerance": 2.0}  # fmt: skip


def _rows(cc_erl=200.0, cc_pen=35.0, tb_pen=38.0, prec=0.3, merges=10) -> dict:
    r = {k: _row(prec=prec, merges=merges) for k in a.COMPUTED}
    r[a.CC] = _row(erl=cc_erl, pen=cc_pen, prec=prec, merges=merges)
    r[a.TB] = _row(erl=45.0, pen=tb_pen, prec=prec, merges=merges)
    r[a.TF] = _row(erl=47.0, pen=tb_pen + 2, prec=prec, merges=merges)
    return r


def _all_held() -> dict:
    return {
        c: {
            "old": _rows(prec=0.30, merges=10),
            "current": _rows(prec=0.35, merges=14),
            "mismatches": [],
        }
        for c in a.REVISED
    }


def test_partial_sample_refuses_verdict():
    res = _all_held()
    res.pop("s1_08997_02997_02497_256")
    v = a.verdict(res)
    assert v["status"] == "INCOMPLETE" and "predictions" not in v
    assert v["missing"] == ["s1_08997_02997_02497_256"]


def test_fidelity_failure_refuses_verdict():
    res = _all_held()
    res["s5_14997_01497_01497_256"]["mismatches"] = ["floor_connected_components"]
    v = a.verdict(res)
    assert v["status"] == "FIDELITY_FAILED" and "predictions" not in v


def test_all_predictions_hold_on_constructed_rows():
    v = a.verdict(_all_held())
    assert v["status"] == "OK" and all(v["predictions"].values())


def test_each_prediction_can_fail():
    base = _all_held()
    r = copy.deepcopy(base)
    r["s1_00497_02497_02997_256"]["current"][a.CC]["erl"] = (
        40.0  # below the tracer's 45
    )
    assert not a.verdict(r)["predictions"]["P1_cc_raw_erl_above_tracer_on_all_3"]
    r = copy.deepcopy(base)
    r["s1_08997_02997_02497_256"]["current"][a.TB]["precision"] = (
        0.30  # equal is not a rise
    )
    assert not a.verdict(r)["predictions"]["P2_precision_rises_cc_and_tracer_on_all_3"]
    r = copy.deepcopy(base)
    r["s5_14997_01497_01497_256"]["current"][a.CC]["merges"] = 9
    assert not a.verdict(r)["predictions"]["P3_merges_rise_cc_and_tracer_on_all_3"]
    r = copy.deepcopy(base)
    r["s5_14997_01497_01497_256"]["current"][a.TB]["erl_merge_penalized"] = (
        30.0  # below cc's 35
    )
    assert not a.verdict(r)["predictions"]["P4_s5_14997_tracer_pen_above_cc"]


def test_fidelity_mismatch_detection():
    old = _rows()
    published = {k: dict(old[k]) for k in a.COMPUTED}
    published["tracer_strict_relink"] = {
        k: old[a.TB][k] for k in ("erl", "erl_merge_penalized", "coverage")
    }
    published["tracer_strict_relink"]["scoring_version"] = 2
    frozen = {k: old[a.TF][k] for k in a.FROZEN_KEYS}
    assert a.fidelity_mismatches(old, published, frozen) == []
    published[a.CC]["erl"] = 200.01
    frozen["merges"] += 1
    assert a.fidelity_mismatches(old, published, frozen) == [a.CC, a.TF]
