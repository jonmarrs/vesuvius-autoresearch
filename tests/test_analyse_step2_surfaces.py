"""Step-2 across-surfaces summary: tested before any step-2 arm rendered."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyse_step2_surfaces import PAIRS, effects  # noqa: E402


def _ink(mult):
    ink = {}
    for s, (a, b) in PAIRS.items():
        ink[a] = 3.0e6
        ink[b] = 3.0e6 * mult[s]
    return ink


def test_partial_sample_is_refused():
    ink = _ink({s: 1.05 for s in PAIRS})
    del ink["step2_s6"]
    with pytest.raises(ValueError, match="partial"):
        effects(ink)


def test_effects_are_ratios_and_summarised():
    r = effects(_ink({"up1": 1.0532, "s4": 1.03, "s5": 1.08, "s6": 1.05}))
    assert r["per_surface"]["up1"] == pytest.approx(0.0532)
    assert r["min"] == pytest.approx(0.03) and r["max"] == pytest.approx(0.08)
    assert r["all_positive"] and r["all_clear_floor"]


def test_a_null_surface_is_reported_not_hidden():
    r = effects(_ink({"up1": 1.05, "s4": 1.0, "s5": 1.04, "s6": 1.06}))
    assert not r["all_positive"] and not r["all_clear_floor"]
