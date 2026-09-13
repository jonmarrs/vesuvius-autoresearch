"""Tests for the ink-placement comparison.

The instrument's whole credibility rests on one control: that a difference in
strip LENGTH does not by itself look like the ink having moved. Each fit makes
its own flattening and the strips differ by up to 3.6%, so if relative-position
resampling did not absorb that, every number the script prints would be an
artefact.
"""

import os
import sys

import numpy as np
import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import compare_ink_placement as mod  # noqa: E402


def _bumpy(n=90_000, seed=0):
    """A BROADBAND stand-in for an ink profile.

    An earlier version summed three sinusoids, which made two independent draws
    correlate at r=0.62 under the lag search -- indistinguishable from the real
    between-arm figure -- and made local warping nearly free. Near-periodic
    signals are alignable in ways real ink profiles are not, so a fixture built
    from a few tones tests the opposite of what it should. Real null controls on
    the actual profiles land at r~0.05; this fixture reproduces that.
    """
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 1, n)
    sig = 0.4 * np.sin(2 * np.pi * 3 * x + rng.uniform(0, 6))
    # Band-limited, not white: a real profile is a sum over ~4,500 rows, so it
    # has no per-column independent component. White noise here would decorrelate
    # under interpolation and make the uniform-stretch control fail for a reason
    # the real data does not have.
    noise = rng.normal(0, 1.0, n)
    k = np.ones(64) / 64
    sig += np.convolve(noise, k, mode="same") * 3.0
    for _ in range(60):  # sparse strong features
        c = int(rng.integers(0, n))
        w = int(rng.integers(200, 900))
        sig[max(0, c - w) : c + w] += rng.uniform(2, 6)
    return np.clip(sig + 3.0, 0, None)


def test_identical_profiles_correlate_perfectly():
    p = mod.resample(_bumpy())
    assert mod.best_correlation(p, p)[0] == pytest.approx(1.0, abs=1e-9)


@pytest.mark.parametrize("stretch", [0.005, 0.01, 0.02, 0.036, 0.05])
def test_a_uniform_stretch_is_fully_absorbed(stretch):
    """THE load-bearing control. Strips differ by up to 3.6% in length; if that
    read as disagreement, the whole comparison would be measuring flattening
    length rather than ink."""
    p = _bumpy()
    x = np.linspace(0, 1, len(p))
    stretched = np.interp(np.linspace(0, 1, int(len(p) * (1 + stretch))), x, p)
    r, _ = mod.best_correlation(mod.resample(p), mod.resample(stretched))
    assert r > 0.999, f"a {stretch:.1%} uniform stretch cost {1 - r:.4f} of correlation"


def test_a_pure_shift_is_absorbed_by_the_lag_search():
    p = mod.resample(_bumpy())
    shifted = np.roll(p, 40)
    r, lag = mod.best_correlation(p, shifted)
    assert r > 0.99 and abs(lag) == 40


def test_unrelated_profiles_do_not_correlate():
    a, b = mod.resample(_bumpy(seed=1)), mod.resample(_bumpy(seed=2))
    assert mod.best_correlation(a, b)[0] < 0.25, (
        "independent profiles must not align; real null controls give r~0.05"
    )


def test_local_warping_DOES_reduce_correlation():
    """The limitation the report discloses. If this ever stopped holding, the
    report's central caveat would be wrong."""
    p = mod.resample(_bumpy())
    x = np.linspace(0, 1, len(p))
    warped = np.interp(np.clip(x + 0.002 * np.sin(2 * np.pi * 3 * x), 0, 1), x, p)
    assert mod.best_correlation(p, warped)[0] < 0.95


def test_tiles_are_concatenated_in_numeric_order():
    """Masks tile the strip horizontally; out-of-order concatenation would
    scramble the profile while still summing to the right total."""
    names = [f"/x/w120-129_flat_mask.{i:03d}.png" for i in (10, 2, 0, 1)]
    assert [mod.tile_index(n) for n in sorted(names, key=mod.tile_index)] == [
        0,
        1,
        2,
        10,
    ]


def test_resample_preserves_relative_position_not_absolute_width():
    short, long = _bumpy(1000), _bumpy(4000)
    assert len(mod.resample(short)) == len(mod.resample(long)) == mod.COMMON
