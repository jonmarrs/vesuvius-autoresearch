"""Tests for the STRIPMATCH builder.

Two things must hold or the control is worthless: the draw must actually converge
on BOTH constraints, and it must never select on satisfaction -- selecting the
control for quality would destroy the contrast it exists to isolate.
"""

import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import build_stripmatch_dataset as mod  # noqa: E402


def test_strip_weight_is_one_inside_and_zero_outside():
    assert mod.strip_weight((2000.0, 2500.0)) == 1.0
    assert mod.strip_weight((100.0, 200.0)) == 0.0
    assert mod.strip_weight((5000.0, 6000.0)) == 0.0


def test_strip_weight_apportions_a_straddling_patch():
    """The correction that matters: a patch half inside the strip counts half,
    not all-or-nothing on where its midpoint falls."""
    lo, hi = mod.STRIP_LO, mod.STRIP_HI
    w = mod.strip_weight((lo - 100.0, lo + 100.0))
    assert w == pytest.approx(0.5)


def test_a_zero_width_patch_is_handled():
    assert mod.strip_weight((2000.0, 2000.0)) == 1.0
    assert mod.strip_weight((10.0, 10.0)) == 0.0


def test_select_converges_on_area_and_share():
    area = {str(i): 100.0 for i in range(400)}
    # half the pool sits fully in the strip, half fully outside
    weight = {str(i): (1.0 if i % 2 == 0 else 0.0) for i in range(400)}
    keep = mod.select(set(area), area, weight, 10000.0, 0.40, seed=1)
    a, s = mod.profile(set(keep), area, weight)
    assert a == pytest.approx(10000.0, rel=0.01)
    assert s == pytest.approx(0.40, abs=0.005)


def test_select_hits_a_share_the_population_does_not_have():
    """The whole point: the population sits at 0.50 and the draw must reach 0.20."""
    area = {str(i): 10.0 for i in range(1000)}
    weight = {str(i): (1.0 if i % 2 == 0 else 0.0) for i in range(1000)}
    keep = mod.select(set(area), area, weight, 4000.0, 0.20, seed=2)
    _, s = mod.profile(set(keep), area, weight)
    assert s == pytest.approx(0.20, abs=0.01)


def test_select_ignores_satisfaction_entirely():
    """`select` takes no satisfaction argument. If a future edit adds one, this
    fails and forces the author to justify destroying the control."""
    import inspect

    params = set(inspect.signature(mod.select).parameters)
    assert params == {"pool", "area", "weight", "target_area", "target_share", "seed"}


def test_select_is_deterministic_under_a_seed():
    area = {str(i): 5.0 for i in range(200)}
    weight = {str(i): (i % 3) / 2.0 for i in range(200)}
    a = mod.select(set(area), area, weight, 400.0, 0.5, seed=7)
    b = mod.select(set(area), area, weight, 400.0, 0.5, seed=7)
    assert a == b


# --- the single-draw limitation ------------------------------------------------


def test_draw_stability_reports_one_row_per_seed():
    area = {str(i): 10.0 for i in range(400)}
    weight = {str(i): (1.0 if i % 2 == 0 else 0.0) for i in range(400)}
    rows = mod.draw_stability(set(area), area, weight, 2000.0, 0.40, range(3))
    assert [r["seed"] for r in rows] == [0, 1, 2]
    assert rows[0]["overlap_with_first"] == 1.0


def test_every_draw_meets_the_constraints():
    """The point of the check: different subsets, same pinned properties."""
    area = {str(i): 10.0 for i in range(600)}
    weight = {str(i): (1.0 if i % 2 == 0 else 0.0) for i in range(600)}
    rows = mod.draw_stability(set(area), area, weight, 3000.0, 0.40, range(4))
    for r in rows:
        assert r["area_frac_of_target"] == pytest.approx(1.0, rel=0.02)
        assert r["in_strip"] == pytest.approx(0.40, abs=0.01)


def test_different_seeds_give_genuinely_different_subsets():
    """If every draw were the same set, agreement would prove nothing."""
    area = {str(i): 10.0 for i in range(600)}
    weight = {str(i): (1.0 if i % 2 == 0 else 0.0) for i in range(600)}
    rows = mod.draw_stability(set(area), area, weight, 3000.0, 0.40, range(3))
    assert all(r["overlap_with_first"] < 0.99 for r in rows[1:])


def test_mean_satisfaction_is_only_reported_when_asked_for():
    area = {str(i): 10.0 for i in range(200)}
    weight = {str(i): (i % 2) * 1.0 for i in range(200)}
    rows = mod.draw_stability(set(area), area, weight, 1000.0, 0.5, range(2))
    assert "mean_satisfaction" not in rows[0]
    frac = {str(i): 0.5 for i in range(200)}
    rows = mod.draw_stability(set(area), area, weight, 1000.0, 0.5, range(2), frac=frac)
    assert rows[0]["mean_satisfaction"] == pytest.approx(0.5)
