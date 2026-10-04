"""Every number in the October 2026 filing draft must match the artifact it comes from.

Same discipline as test_filing_numbers_match_sources.py for September: a figure in the filing text is a
claim, and the claim is only as good as the file it was read from. Each test recomputes the figure from the
committed JSON and asserts the draft states it.
"""

import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_DRAFT = _REPO / "docs/PRIZE_FILING_2026-10_DRAFT.md"
_F72 = _REPO / "reports/scorer_vs_labels.json"
_F71 = _REPO / "reports/interp_vs_labels.json"
_F70 = _REPO / "reports/interp_windows.json"

pytestmark = pytest.mark.skipif(
    not (_DRAFT.exists() and _F72.exists() and _F71.exists() and _F70.exists()),
    reason="draft or source artifact absent",
)


def _text() -> str:
    # the draft wraps lines; compare on single-spaced text
    return " ".join(_DRAFT.read_text().split())


def _pct(x: float) -> str:
    return f"{x * 100:+.1f}%".replace("-", "−")


def test_segment_count_range_matches_finding_72():
    d = json.loads(_F72.read_text())
    totals = [r["d_total"] for r in d["segments"]]
    assert f"{_pct(min(totals))} to {_pct(max(totals))} per segment" in _text()


def test_faithfulness_claim_matches_finding_72():
    d = json.loads(_F72.read_text())
    s = d["summary"]
    assert len(d["segments"]) == 8 and s["n_included"] == 8
    assert max(abs(v) for v in s["prob_d_ap"].values()) < 0.001
    assert s["prob_resolved_pos"] == 0 and s["prob_resolved_neg"] == 0
    assert "(|ΔAP| < 0.001 in all 8, none resolved)" in _text()


def test_the_eight_labelled_segments_are_named():
    d = json.loads(_F72.read_text())
    txt = _text()
    for r in d["segments"]:
        assert f"`{r['segment']}`" in txt


def test_failed_prediction_fraction_matches_finding_72():
    s = json.loads(_F72.read_text())["summary"]
    assert round(s["frac_windows_abs_d_ge_5pct"] * 100) == 15
    assert "the count was sensitive in 15% of windows, not ≥ 25%" in _text()
    held = json.loads(_F72.read_text())["predictions_held"]
    assert held["p1_count_sensitive_ge_25pct_windows"] is False
    assert held["p2_faithfulness_abs_dAP_lt_0.01_in_6"] is True


def test_finding_70_magnitude_and_its_failed_prediction():
    d = json.loads(_F70.read_text())
    lo, hi = d["summary"]["d_fg_range"]
    assert round(max(abs(lo), abs(hi)) * 100) == 20
    assert d["predictions_held"]["fg_abs_below_1pct_every_window"] is False
    assert "it moved up to ±20%" in _text()


def test_finding_71_prediction_1_failed_on_exclusions():
    d = json.loads(_F71.read_text())
    assert d["predictions_held"]["p1_abs_dAP_lt_0.02_in_6_of_8"] is False
    assert d["summary"]["n_excluded"] == 3
    assert "failed on three exclusions" in _text()


def test_about_one_percent_per_window_in_villas_pipeline():
    d = json.loads(_F72.read_text())
    ws = sorted(abs(w["d"]) for r in d["segments"] for w in r["windows"])
    n = len(ws)
    median = (ws[n // 2] + ws[(n - 1) // 2]) / 2
    assert 0.005 <= median < 0.015  # "about 1%"
    assert "about 1% per window on villa's 20-voxel segment meshes" in _text()


_F73 = _REPO / "reports/scorer_vs_labels_coarse.json"


@pytest.mark.skipif(not _F73.exists(), reason="finding 73 artifact absent")
def test_coarse_grid_numbers_match_finding_73():
    d = json.loads(_F73.read_text())
    txt = _text()
    totals = [r["d_total"] for r in d["segments"]]
    assert f"{_pct(min(totals))} to {_pct(max(totals))} per segment" in txt
    lo, hi = d["summary"]["window_d_range"]
    assert f"({_pct(lo)} to {_pct(hi)} per window)" in txt
    ws = sorted(abs(w["d"]) for r in d["segments"] for w in r["windows"])
    n = len(ws)
    assert f"{100 * (ws[n // 2] + ws[(n - 1) // 2]) / 2:.1f}% median" in txt
    ge = sum(r["prob"]["d_ap"] >= 0 for r in d["segments"])
    assert ge == 2 and "2 of 8, not ≥ 6" in txt
    # the raw-render size (~1% of AP) is bound to the supervised re-analysis:
    # test_band_and_route_numbers_are_the_supervised_ones


_VAL = _REPO / "reports/inkagree_validation.json"


@pytest.mark.skipif(not _VAL.exists(), reason="inkagree validation artifact absent")
def test_inkagree_validation_claim_matches_its_artifact():
    v = json.loads(_VAL.read_text())
    assert v["n_ok"] == v["n"] == 16
    assert "reproduces findings 71 and 72 exactly (16 of 16 segment results" in _text()
    assert "https://github.com/jonmarrs/inkagree" in _DRAFT.read_text()


_SUP = _REPO / "reports/supervised_reanalysis.json"


def _rel_median(rows):
    r = sorted(x["d_ap"] / x["ap_a"] for x in rows if x["status"] == "compared")
    n = len(r)
    return 100 * (r[n // 2] + r[(n - 1) // 2]) / 2


@pytest.mark.skipif(not _SUP.exists(), reason="supervised re-analysis artifact absent")
def test_band_and_route_numbers_are_the_supervised_ones():
    d, txt = json.loads(_SUP.read_text()), _text()
    f74 = d["f74"]
    assert (
        f74["0.25"]["tally"]["resolved_a"] == 8
        and round(-_rel_median(f74["0.25"]["rows"])) == 6
    )
    assert (
        f74["2.0"]["tally"]["resolved_a"] == 8
        and round(-_rel_median(f74["2.0"]["rows"])) == 20
    )
    assert f74["1.0"]["tally"]["resolved_a"] < 6  # no consistent difference vs 1.0
    assert (
        "(0.25: 8 of 8, about −6% of AP)" in txt and "(2.0: 8 of 8, about −20%)" in txt
    )
    assert "Against 1.0 there is no consistent difference" in txt
    f75 = d["f75"]
    assert (
        f75["0.5"]["tally"]["resolved_a"] == 8
        and round(-_rel_median(f75["0.5"]["rows"])) == 5
    )
    assert (
        f75["2.0"]["tally"]["resolved_b"] == 8
        and round(_rel_median(f75["2.0"]["rows"])) == 8
    )
    assert "(8 of 8, about +5% AP)" in txt and "(8 of 8, about +8%)" in txt
    assert (
        d["f73"]["strip"]["tally"]["resolved_b"] == 8
        and round(_rel_median(d["f73"]["strip"]["rows"])) == 1
    )
    assert "1% of AP)" in txt


_F76 = _REPO / "reports/objective_vs_labels.json"


@pytest.mark.skipif(not _F76.exists(), reason="finding 76 artifact absent")
def test_objective_vs_labels_claim_matches_finding_76():
    d = json.loads(_F76.read_text())
    assert d["predictions_held"]["p1_scorer_rho_gt_0.3_ci_excludes_0"] is False
    assert f"ρ = {d['q1']['scorer']['rho']:+.2f}" in _text()
