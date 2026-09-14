"""The consensus gate must be applied to the quantity it was calibrated on.

Calibrating a threshold on one measurement and applying it to another is what
voided `2026-09-13_consensus_forward_prediction.md`. The re-test repeated a
milder version of it: `GATE_INK` was computed from `total_fg_pixels` (s1-s6 mean
3,019,001 exactly) while the module gated `H.sum()` from the volume map, which
runs ~0.2% lower because the histogram's validity mask drops non-finite and
non-positive coordinates. Immaterial against a +/-20% gate, but the class of
error is not, so these tests hold the two apart.
"""

import json
import statistics as st
from pathlib import Path

import pytest

import scripts.analyse_consensus_retest as acr

SPIRAL_OUT = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
CALIB_ARMS = [f"curbase_s{i}" for i in range(1, 7)]


def _fg(tag: str) -> float | None:
    p = SPIRAL_OUT / f"outer_{tag}" / "ink_metric" / "metrics.json"
    if not p.exists():
        return None
    return float(json.loads(p.read_text())["summary"]["total_fg_pixels"])


def test_gate_source_names_the_calibration_quantity():
    """The constant carries its provenance, so the next reader cannot guess."""
    assert acr.GATE_SOURCE == "ink_metric/metrics.json:summary.total_fg_pixels"


def test_gate_is_applied_to_total_fg_pixels_not_the_histogram():
    """Guards the specific regression: gating H.sum() against these constants."""
    src = Path(acr.__file__).read_text()
    gate_line = next(
        ln for ln in src.splitlines() if "GATE_INK[0] <= v <= GATE_INK[1]" in ln
    )
    assert "fg.items()" in gate_line, (
        "the gate must iterate the total_fg_pixels dict, not the H.sum() dict; "
        f"got: {gate_line.strip()}"
    )


def test_registered_constants_reproduce_the_calibration_sample():
    """mean and sd must come back exactly; the bounds carry a rounding slop."""
    raw = [_fg(t) for t in CALIB_ARMS]
    if any(v is None for v in raw):
        pytest.skip("calibration arms not scored on this machine")
    vals = [v for v in raw if v is not None]
    assert round(st.mean(vals)) == 3_019_001
    assert round(st.stdev(vals)) == 223_329

    half = 2.571 * st.stdev(vals) * (1 + 1 / len(vals)) ** 0.5
    lo, hi = st.mean(vals) - half, st.mean(vals) + half
    # The registration rounded sqrt(7/6) to 1.07994; 100 units on a 1.24M gate.
    assert abs(lo - acr.GATE_INK[0]) < 200
    assert abs(hi - acr.GATE_INK[1]) < 200


def test_every_calibration_arm_passes_its_own_gate():
    """A gate that rejects an arm the process really produced is a broken gate."""
    vals = {t: _fg(t) for t in CALIB_ARMS}
    if any(v is None for v in vals.values()):
        pytest.skip("calibration arms not scored on this machine")
    outside = [
        t for t, v in vals.items() if not acr.GATE_INK[0] <= v <= acr.GATE_INK[1]
    ]
    assert not outside, f"gate rejects its own calibration arms: {outside}"


def test_retired_comparison_cannot_be_computed():
    """A-vs-B was seen at 0.876 and must stay out of the forward test."""
    assert frozenset({"A", "B"}) in acr.RETIRED
    assert all(frozenset(c) not in acr.RETIRED for c in acr.COMPARISONS)
