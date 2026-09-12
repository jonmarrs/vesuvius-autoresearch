"""Tests for the tier-aware noise-floor measurement.

The instrument being replaced is a hardcoded `OUTER_CV = 0.0421` carrying df=3.
Two things must hold for the replacement to be trustworthy, and both are pinned
here rather than left to the report:

1. it reproduces the published figure from the published fits (a positive
   control -- an instrument that cannot recover a known answer measures nothing);
2. it cannot pool the two code tiers, which are different instruments.
"""

import json
import os
import statistics as st
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import measure_noise_floor as mod  # noqa: E402


def test_pooled_cv_recovers_a_known_spread():
    """Positive control: one group whose CV is known by construction."""
    v = [100.0, 110.0, 90.0]
    cv, df = mod.pooled_cv({"g": v})
    assert df == 2
    assert cv == pytest.approx(st.stdev(v) / st.mean(v), rel=1e-9)


def test_pooling_uses_RELATIVE_deviations_so_tiers_at_different_means_are_comparable():
    """The current tier sits ~68% above the pinned one. Absolute pooling would
    let the higher-mean group dominate purely through scale."""
    lo = [100.0, 110.0, 90.0]
    hi = [x * 10 for x in lo]  # same CV, ten times the mean
    cv_lo, _ = mod.pooled_cv({"a": lo})
    cv_both, _ = mod.pooled_cv({"a": lo, "b": hi})
    assert cv_both == pytest.approx(cv_lo, rel=1e-9)


def test_degrees_of_freedom_add_across_groups_not_fits():
    cv, df = mod.pooled_cv({"a": [1.0, 2.0], "b": [3.0, 4.0, 5.0]})
    assert df == 1 + 2  # five fits, three df


def test_a_singleton_group_contributes_nothing():
    cv_a, df_a = mod.pooled_cv({"a": [100.0, 110.0, 90.0]})
    cv_b, df_b = mod.pooled_cv({"a": [100.0, 110.0, 90.0], "solo": [5000.0]})
    assert (cv_a, df_a) == (cv_b, df_b)


def test_no_groups_with_replication_is_an_error_not_a_zero():
    with pytest.raises(ValueError):
        mod.pooled_cv({"solo": [1.0]})


def test_the_two_tiers_are_disjoint_and_there_is_no_pooled_tier():
    pinned = {t for ts in mod.PINNED_GROUPS.values() for t in ts}
    current = {t for ts in mod.CURRENT_GROUPS.values() for t in ts}
    assert not (pinned & current)
    assert set(mod.TIERS) == {"pinned", "current"}


def test_cv_ci_brackets_the_estimate_and_widens_as_df_shrinks():
    lo3, hi3 = mod.cv_ci(0.05, 3)
    lo18, hi18 = mod.cv_ci(0.05, 18)
    assert lo3 < 0.05 < hi3 and lo18 < 0.05 < hi18
    assert (hi3 / lo3) > (hi18 / lo18), "a df=3 CV must be the less certain one"


def test_mde_matches_the_formula_the_registrations_used():
    assert mod.mde(0.0421, 3, 3) == pytest.approx(0.096, abs=0.004)


@pytest.mark.skipif(
    not os.path.isdir("/home/jon/openclaw-workspace/Neo-VM/spiral_out"),
    reason="fit corpus not present",
)
def test_positive_control_reproduces_the_published_0421_from_its_own_four_fits():
    """`outer_winding_noise_floor.md` reports 0.0421 from baseline01 and seeds
    02-04. If this instrument cannot recover that, it is not measuring the same
    thing and no other number it prints can be trusted."""
    D = mod.load("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
    four = [D[t] for t in ("baseline01", "seed02", "seed03", "seed04")]
    assert st.stdev(four) / st.mean(four) == pytest.approx(
        mod.PUBLISHED_PINNED_CV, abs=5e-4
    )


@pytest.mark.skipif(
    not os.path.isfile(os.path.join(_REPO, "reports/noise_floor_by_tier.json")),
    reason="measurement not run",
)
def test_the_published_json_keeps_the_tiers_separate_and_records_df():
    r = json.load(open(os.path.join(_REPO, "reports/noise_floor_by_tier.json")))
    assert "pinned" in r and "current" in r
    assert r["pinned"]["df"] > r["current"]["df"], "pinned has far more replication"
    # The correction that goes against us: the hardcoded constant is optimistic.
    assert r["pinned"]["cv"] > mod.PUBLISHED_PINNED_CV
