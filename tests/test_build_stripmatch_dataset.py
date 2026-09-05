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
