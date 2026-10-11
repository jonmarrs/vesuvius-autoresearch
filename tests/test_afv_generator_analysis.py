"""The registered verdict and identity logic of scripts/afv_generator_analysis.py, on synthetic rows."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import afv_generator_analysis as a  # noqa: E402


def _row(erl=90.0, pen=60.0, cov=0.40) -> dict:
    return {"erl": erl, "erl_merge_penalized": pen, "coverage": cov}


def _setup():
    gen = {c: _row() for c in a.IN_SAMPLE + a.S3}
    comp = {c: {"cc": _row(erl=200.0, pen=40.0, cov=0.85), "tracer": _row(erl=45.0, pen=35.0, cov=0.60)}
            for c in a.IN_SAMPLE + a.S3}  # fmt: skip
    for c in a.S3:
        gen[c] = _row(cov=0.30)
    return gen, comp


def test_all_hold_on_constructed_rows():
    gen, comp = _setup()
    v = a.verdict(gen, comp, heldout_ok=True)
    assert (
        v["status"] == "OK"
        and all(v["predictions"].values())
        and v["heldout_evaluated"]
    )


def test_missing_in_sample_run_refuses_verdict():
    gen, comp = _setup()
    gen[a.IN_SAMPLE[4]] = None
    v = a.verdict(gen, comp, heldout_ok=True)
    assert v["status"] == "INCOMPLETE" and "predictions" not in v


def test_heldout_not_ok_or_too_few_s3_leaves_p4_p5_unevaluated():
    gen, comp = _setup()
    v = a.verdict(gen, comp, heldout_ok=False)
    assert v["predictions"]["P4_s3_pen_above_tracer_on_75pct"] is None
    assert v["predictions"]["P5_s3_median_coverage_below_in_sample_512_median"] is None
    for c in a.S3[:3]:
        gen[c] = None
    v = a.verdict(gen, comp, heldout_ok=True)
    assert v["predictions"]["P4_s3_pen_above_tracer_on_75pct"] is None and v[
        "failed_runs"
    ] == sorted(a.S3[:3])


def test_each_prediction_can_fail():
    base = _setup()
    gen, comp = copy.deepcopy(base)
    for c in a.IN_SAMPLE[:3]:
        gen[c]["erl"] = 40.0  # 8 of 11 above the tracer's 45
    assert not a.verdict(gen, comp, True)["predictions"][
        "P1_raw_erl_above_tracer_on_9_of_11"
    ]
    gen, comp = copy.deepcopy(base)
    for c in a.IN_SAMPLE[:3]:
        gen[c]["coverage"] = 0.60  # equal to the tracer is not below it
    assert not a.verdict(gen, comp, True)["predictions"][
        "P2_coverage_below_tracer_on_9_of_11"
    ]
    gen, comp = copy.deepcopy(base)
    gen["s5_07997_02997_05497_256"]["erl"] = 250.0
    assert not a.verdict(gen, comp, True)["predictions"][
        "P3_cc_raw_erl_above_generator_on_all_256"
    ]
    gen, comp = copy.deepcopy(base)
    for c in a.S3[:3]:  # 5 of 8 above
        gen[c]["erl_merge_penalized"] = 30.0
    assert not a.verdict(gen, comp, True)["predictions"][
        "P4_s3_pen_above_tracer_on_75pct"
    ]
    gen, comp = copy.deepcopy(base)
    for c in a.S3:
        gen[c]["coverage"] = 0.40  # equal to the in-sample 512 median is not below it
    assert not a.verdict(gen, comp, True)["predictions"][
        "P5_s3_median_coverage_below_in_sample_512_median"
    ]


def test_identity_check_names_every_difference():
    good = {
        "model": a.MODEL,
        "revision": a.REVISION,
        **a.SETTINGS,
        "size_xyz": [256, 256, 256],
    }
    assert a.identity_problems(good, 256) == []
    bad = dict(good, revision="deadbeef", extend=True, size_xyz=[512, 512, 512])
    probs = a.identity_problems(bad, 256)
    assert len(probs) == 3 and any("extend" in p for p in probs)
