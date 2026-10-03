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
    assert "the effect is about 1% per window" in _text()
