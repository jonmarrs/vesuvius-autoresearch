"""Finding 85's report states what its registered analysis and post-hoc script wrote."""

import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_RES = _REPO / "reports/afv_generator_entrant.json"
_POST = _REPO / "reports/erl_coverage_conditioning.json"
_MD = _REPO / "reports/afv_generator_entrant.md"
pytestmark = pytest.mark.skipif(
    not (_RES.exists() and _POST.exists() and _MD.exists()),
    reason="finding 85 artifacts absent",
)
NEW = ("s5_13497_01497_02497_256", "s5_16997_03997_04497_256")


def _t() -> str:
    return " ".join(_MD.read_text().split())


def test_registered_verdict():
    r = json.loads(_RES.read_text())
    assert r["status"] == "OK" and r["failed_runs"] == []
    assert r["predictions"] == {
        "P1_raw_erl_above_tracer_on_9_of_11": False,
        "P2_coverage_below_tracer_on_9_of_11": True,
        "P3_cc_raw_erl_above_generator_on_all_256": True,
        "P4_s3_pen_above_tracer_on_75pct": True,
        "P5_s3_median_coverage_below_in_sample_512_median": True,
    }
    g, comp = r["generator_rows"], r["comparators"]
    ins = [c for c in g if not c.startswith("s3_") and c not in NEW]
    assert len(ins) == 11 and len(g) == 21
    above = sum(g[c]["erl"] > comp[c]["tracer"]["erl"] for c in ins)
    t = _t()
    assert f"above our tracer's on {above} of the 11 in-sample targets" in t
    lo, hi = min(g[c]["coverage"] for c in ins), max(g[c]["coverage"] for c in ins)
    assert f"({lo:.3f}–{hi:.3f}," in t


def test_post_hoc_counts_and_control():
    p, t = json.loads(_POST.read_text()), _t()
    n = p["entrant_gt_normalized"]
    raw_below = sum(n[c]["generator"]["erl_gt"] < n[c]["tracer"]["erl_gt"] for c in n)
    pen_below = sum(
        n[c]["generator"]["erl_pen_gt"] < n[c]["tracer"]["erl_pen_gt"] for c in n
    )
    assert (raw_below, pen_below) == (21, 20)
    assert "below the tracer on 21 of 21 cubes" in t and "below on 20 of 21" in t
    ctrl = {r["min_voxels"]: r for r in p["deletion_control"]}
    assert (
        ctrl[400]["erl"] > ctrl[0]["erl"]
        and ctrl[400]["coverage"] < ctrl[0]["coverage"]
    )
    assert ctrl[400]["erl_gt"] < ctrl[0]["erl_gt"]
    assert (
        f"| 400 | {ctrl[400]['instances']} | {ctrl[400]['erl']:.2f} | {ctrl[400]['erl_merge_penalized']:.2f} |"
        in _MD.read_text()
    )
    held = [c for c in n if c.startswith("s3_") or c in NEW]
    assert (
        sum(n[c]["tracer"]["erl_pen_gt"] > n[c]["cc"]["erl_pen_gt"] for c in held) == 9
    )
    assert "On the ten held-out cubes it survives on 9" in t
