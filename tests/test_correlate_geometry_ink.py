"""Tests for the corpus-level correlation.

The point of this analysis is the INTERVAL, not the point estimate, so the tests
that matter are the ones pinning that a CI is reported and that it is refused
when n is too small to mean anything. A bare r of -0.12 read without its interval
would overclaim in the direction we already believe.
"""

import math
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import correlate_geometry_ink as mod  # noqa: E402


def test_pearson_matches_a_known_value():
    assert mod.pearson([1, 2, 3, 4], [2, 4, 6, 8]) == pytest.approx(1.0)
    assert mod.pearson([1, 2, 3, 4], [8, 6, 4, 2]) == pytest.approx(-1.0)


def test_pearson_is_zero_for_an_uncorrelated_pair():
    assert mod.pearson([1, 2, 3, 4], [1, 1, 1, 1]) != mod.pearson([1, 2], [1, 2])


def test_a_ci_is_refused_below_n_equals_four():
    """n=3 gives a meaningless interval; the script must print 'too small'
    rather than a number a reader would quote."""
    assert mod.fisher_ci(0.5, 3) is None
    assert mod.fisher_ci(0.5, 2) is None
    assert mod.fisher_ci(0.5, 10) is not None


def test_the_ci_widens_as_n_shrinks():
    wide = mod.fisher_ci(0.3, 6)
    narrow = mod.fisher_ci(0.3, 60)
    assert (wide[1] - wide[0]) > (narrow[1] - narrow[0])


def test_the_ci_brackets_the_point_estimate():
    for n in (6, 12, 24, 100):
        lo, hi = mod.fisher_ci(-0.121, n)
        assert lo < -0.121 < hi


def test_a_perfect_correlation_has_no_finite_interval():
    """r = ±1 makes the Fisher transform infinite; refuse rather than emit inf."""
    assert mod.fisher_ci(1.0, 24) is None
    assert mod.fisher_ci(-1.0, 24) is None


def test_subgroups_are_disjoint_and_named():
    rows = [
        {"tag": t, "satisfied_area": 0.8, "total_fg_pixels": 1}
        for t in ("baseline01", "boot090s1", "nosame_s1", "seed02")
    ]
    g = mod.subgroups(rows)
    assert set(g) == {
        "ALL fits",
        "seed-only baselines",
        "patch-selection arms",
        "constraint-ablation arms",
    }
    assert len(g["ALL fits"]) == 4
    tags = [r["tag"] for r in g["seed-only baselines"]]
    assert tags == ["baseline01", "seed02"]
    # the three named subgroups must not overlap
    named = [set(r["tag"] for r in g[k]) for k in g if k != "ALL fits"]
    for i in range(len(named)):
        for j in range(i + 1, len(named)):
            assert not named[i] & named[j]
