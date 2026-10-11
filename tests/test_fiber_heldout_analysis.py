"""The registered verdict logic of scripts/fiber_heldout_analysis.py, on synthetic rows: missing chain output refuses a
verdict, a gate failure excludes a cube, too few eligible Scroll-3 cubes leaves P1 and P4 unevaluated, and each
prediction reads the rows it claims to."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fiber_heldout_analysis as a  # noqa: E402


def _entry(cov=0.70, cc_erl=250.0, cc_pen=12.0, t_erl=45.0, t_pen=35.0) -> dict:
    return {
        "semantic_landing": 1.0,
        "mask_enrichment": 12.0,
        "rows": {
            a.CC: {"coverage": cov, "erl": cc_erl, "erl_merge_penalized": cc_pen},
            "tracer": {"coverage": 0.5, "erl": t_erl, "erl_merge_penalized": t_pen},
        },
    }


def _all() -> dict:
    return {c: _entry() for c in a.CUBES}


def test_missing_cube_refuses_verdict():
    r = _all()
    r.pop(a.S3[3])
    v = a.verdict(r)
    assert (
        v["status"] == "INCOMPLETE"
        and "predictions" not in v
        and v["missing"] == [a.S3[3]]
    )


def test_all_hold_on_constructed_rows():
    v = a.verdict(_all())
    assert v["status"] == "OK" and all(v["predictions"].values())


def test_gate_failure_excludes_and_too_few_s3_leaves_p1_p4_unevaluated():
    r = _all()
    for c in a.S3[:3]:
        r[c]["mask_enrichment"] = 4.9
    v = a.verdict(r)
    assert v["status"] == "NO_S3_VERDICT" and v["excluded"] == sorted(a.S3[:3])
    assert v["predictions"]["P1_s3_median_cc_coverage_below_0.8130"] is None
    assert v["predictions"]["P4_tracer_pen_above_cc_on_75pct_of_s3"] is None
    r = _all()
    for c in a.S3[:2]:
        r[c]["semantic_landing"] = 0.998
    v = a.verdict(r)
    assert v["status"] == "OK" and len(v["eligible"]) == 8


def test_each_prediction_can_fail():
    base = _all()
    r = copy.deepcopy(base)
    for c in a.S3[:4]:
        r[c]["rows"][a.CC]["coverage"] = (
            0.8130  # equal to the in-sample minimum is not below it
        )
    for c in a.S3[4:]:
        r[c]["rows"][a.CC]["coverage"] = 0.90
    assert not a.verdict(r)["predictions"]["P1_s3_median_cc_coverage_below_0.8130"]
    r = copy.deepcopy(base)
    r[a.S5[1]]["rows"][a.CC]["coverage"] = 0.87
    assert not a.verdict(r)["predictions"]["P2_both_s5_cc_coverage_below_0.8666"]
    r = copy.deepcopy(base)
    r[a.S5[0]]["rows"]["tracer"]["erl"] = 260.0
    assert not a.verdict(r)["predictions"][
        "P3_cc_raw_erl_above_tracer_on_every_eligible_cube"
    ]
    r = copy.deepcopy(base)
    for c in a.S3[:3]:  # 5 of 8 = 62.5% < 75%
        r[c]["rows"]["tracer"]["erl_merge_penalized"] = 10.0
    assert not a.verdict(r)["predictions"]["P4_tracer_pen_above_cc_on_75pct_of_s3"]
    r = copy.deepcopy(base)
    for c in a.S3[:2]:  # 6 of 8 = 75% holds
        r[c]["rows"]["tracer"]["erl_merge_penalized"] = 10.0
    assert a.verdict(r)["predictions"]["P4_tracer_pen_above_cc_on_75pct_of_s3"]


def test_registered_constants_match_the_preregistration():
    prereg = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "preregistration"
        / "2026-10-11_fiber_heldout_split.md"
    ).read_text()
    assert "0.8882, 0.8130, 0.8223" in prereg and "0.8666, 0.9119, 0.8185" in prereg
    assert list(a.IN_SAMPLE_CC_COVERAGE[512].values()) == [0.8882, 0.8130, 0.8223]
    assert list(a.IN_SAMPLE_CC_COVERAGE[256].values()) == [0.8666, 0.9119, 0.8185]
    for c in a.CUBES:
        assert c in prereg


def test_score_cube_reproduces_a_published_target():
    """The scoring path, run on an in-sample cube whose rows ScrollGT publishes, must reproduce them exactly."""
    import json

    import pytest

    root = Path(__file__).resolve().parents[1]
    c = "s1_00497_01497_03997_256"
    data = root / "local_data" / "fiber_skeletons"
    inst = Path(
        f"/home/jon/openclaw-workspace/Neo-VM/spiral_out/tracer_rescore/{c}_instances.npy"
    )
    meta_p = a.SG / "data" / f"fibers_{c}" / "meta.json"
    if not (
        (data / f"{c}_fiberprob.npy").exists() and inst.exists() and meta_p.exists()
    ):
        pytest.skip("local cube data, finding 80 labellings or ../scrollgt not present")
    e = a.score_cube(c, data, inst)
    meta = json.loads(meta_p.read_text())
    for k in (*(r for r in meta["floors"] if r.startswith("floor_")), "oracle"):
        assert e["rows"][k] == meta["floors"][k], k
    assert e["rows"]["tracer"] == meta["floors"]["tracer_strict_relink"]
    assert (
        round(e["mask_enrichment"], 6)
        == meta["convention_check"]["landing_enrichment_vs_chance"]
    )
