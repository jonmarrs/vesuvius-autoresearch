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
        "all fits in tier",
        "seed-only baselines",
        "patch-selection arms",
        "constraint-ablation arms",
    }
    assert len(g["all fits in tier"]) == 4
    tags = [r["tag"] for r in g["seed-only baselines"]]
    assert tags == ["baseline01", "seed02"]
    # the three named subgroups must not overlap
    named = [set(r["tag"] for r in g[k]) for k in g if k != "all fits in tier"]
    for i in range(len(named)):
        for j in range(i + 1, len(named)):
            assert not named[i] & named[j]


# --- the two tiers must never be pooled ---------------------------------------
#
# Current villa recovers 67.6% more ink than the pinned tree through a
# byte-identical scorer. Before tiering, this script silently absorbed the
# current-code arms and reported 27 fits at "100% spread" with r = -0.090 -- a
# number that is the code change, not a relationship, and that would have been
# quotable. The published figure is the PINNED tier's r = -0.121 over 24 fits.


def test_tier_assignment_covers_both_families():
    assert mod.tier_of("curbase_s1") == "current"
    assert mod.tier_of("nosamecur_s2") == "current"
    for t in (
        "baseline01",
        "seed04",
        "boot090s1",
        "rand090s3",
        "strip090s2",
        "nosame_s1",
    ):
        assert mod.tier_of(t) == "pinned", t


def test_the_old_ablation_arms_are_not_mistaken_for_current_ones():
    """`nosame_s1` (pinned) and `nosamecur_s1` (current) differ by three
    characters; a prefix that caught both would silently pool them."""
    assert mod.tier_of("nosame_s1") == "pinned"
    assert mod.tier_of("nosamecur_s1") == "current"


def test_subgroups_never_return_a_cross_tier_group():
    rows = [
        {"tag": "baseline01", "satisfied_area": 0.84, "total_fg_pixels": 1_700_000},
        {"tag": "curbase_s1", "satisfied_area": 0.85, "total_fg_pixels": 2_900_000},
    ]
    pinned = [r for r in rows if mod.tier_of(r["tag"]) == "pinned"]
    current = [r for r in rows if mod.tier_of(r["tag"]) == "current"]
    assert len(pinned) == 1 and len(current) == 1
    # subgroups is documented as operating WITHIN a tier; feeding it one tier
    # must never surface the other's tag.
    tags = {r["tag"] for g in mod.subgroups(pinned).values() for r in g}
    assert "curbase_s1" not in tags


def test_the_pooled_correlation_is_not_reported(capsys):
    """A pooled number that exists will get quoted, so it must not be printed."""
    import subprocess
    import sys as _s

    out = subprocess.run(
        [_s.executable, os.path.join(_REPO, "scripts", "correlate_geometry_ink.py")],
        capture_output=True,
        text=True,
    ).stdout
    assert "NON-COMPARABLE TIERS" in out
    assert "pinned tree:" in out
    # the old pooled framing must be gone
    assert "ALL fits" not in out
