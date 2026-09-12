"""The two-seed false-positive rate is exact, and must not drift back to being
described as noise-dependent.

`two_seed_check_lets_through_one_in_six.md` originally paired this with a power
table computed at a CV from the wrong tier, which made the whole finding look
like a consequence of noisy fits. It is not. Under exchangeability the chance
that all k change runs beat all k baseline runs is 1/C(2k,k) -- free of the CV,
the metric, and the code version.

Pinned here because the noise-dependent misreading is the natural one.
"""

from math import comb

import numpy as np
import pytest


def _rule_a_false_positive(k: int, cv: float, n: int = 200_000, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    b = rng.normal(1.0, cv, (n, k))
    c = rng.normal(1.0, cv, (n, k))
    return float((c.min(1) > b.max(1)).mean())


@pytest.mark.parametrize("k,expected", [(2, 1 / 6), (3, 1 / 20), (4, 1 / 70)])
def test_false_positive_rate_is_one_over_central_binomial(k, expected):
    assert 1 / comb(2 * k, k) == pytest.approx(expected)
    assert _rule_a_false_positive(k, 0.03) == pytest.approx(expected, abs=0.006)


@pytest.mark.parametrize("cv", [0.0125, 0.0421, 0.1086, 0.5])
def test_the_rate_does_not_depend_on_the_noise_level(cv):
    """The claim that survives: villa's fits got 4x quieter and this did not move."""
    assert _rule_a_false_positive(2, cv) == pytest.approx(1 / 6, abs=0.006)


def test_three_seeds_reaches_a_conventional_five_percent():
    assert 1 / comb(6, 3) == pytest.approx(0.05)
    assert 1 / comb(4, 2) > 3 * (1 / comb(6, 3)), "the extra seed must be worth it"


def test_power_however_DOES_depend_on_noise_which_is_why_the_old_table_expired():
    """Guards the other half: the power claim was tier-specific and had to be
    withdrawn. If this ever stops holding, the report's correction is wrong."""
    rng = np.random.default_rng(7)
    n = 100_000

    def power(cv, d):
        b = rng.normal(1.0, cv, (n, 2))
        c = rng.normal(1.0 + d, cv, (n, 2))
        return float((c.min(1) > b.max(1)).mean())

    assert power(0.0125, 0.05) > 0.9
    assert power(0.1086, 0.05) < 0.4
