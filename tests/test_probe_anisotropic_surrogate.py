"""Tests for the anisotropic surrogate.

Two premises carry this probe, and both were got wrong in a first attempt: that
the measurement pipeline itself induces negative row correlation (so the real
negative target does not imply anti-correlated data), and that the isotropic arm
it is compared against is the PUBLISHED configuration rather than a strawman.
Both are pinned here.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from probe_anisotropic_surrogate import (  # noqa: E402
    ISOTROPIC_SIGMA,
    TARGET_COL_LAG1,
    TARGET_ROW_LAG1,
    anisotropic_field,
    effective_sample_size,
    ess_matched_isotropic,
    fit_surrogate,
    surrogate_lag1s,
    white_noise_baseline,
)
from probe_onset_at_matched_correlation import INJECTION_GRID  # noqa: E402


def test_the_pipeline_induces_negative_row_correlation_on_white_noise():
    """The premise the first attempt lacked. If this were near zero, the real
    -0.076 would indicate genuinely anti-correlated data and a high-pass filter
    would have been the right surrogate after all."""
    col, row = white_noise_baseline(INJECTION_GRID)
    assert row < -0.1, "pipeline does not induce negative row correlation"
    assert col < 0.0


def test_the_real_row_target_is_ABOVE_the_white_noise_baseline():
    """Which is why the fix is positive row smoothing, not a high-pass: the real
    data is LESS anti-correlated than white noise through the same pipeline."""
    _, row_baseline = white_noise_baseline(INJECTION_GRID)
    assert row_baseline < TARGET_ROW_LAG1


def test_the_joint_fit_reaches_both_targets():
    """A large residual would mean the target is unreachable with this surrogate
    family, which must be reported rather than fitted around."""
    sc, sr, residual = fit_surrogate(INJECTION_GRID)
    assert residual < 0.10, f"joint fit did not converge: residual {residual}"
    col, row = surrogate_lag1s(INJECTION_GRID, sc, sr)
    assert col == pytest.approx(TARGET_COL_LAG1, abs=0.06)
    assert row == pytest.approx(TARGET_ROW_LAG1, abs=0.06)


def test_the_axes_are_not_separable():
    """Justifies the joint search over two bisections. Raising row smoothing must
    materially move the COLUMN statistic; if it did not, independent fits would
    have been adequate and the joint search unnecessary."""
    col_a, _ = surrogate_lag1s(INJECTION_GRID, 0.823, 0.0)
    col_b, _ = surrogate_lag1s(INJECTION_GRID, 0.823, 1.0)
    assert abs(col_a - col_b) > 0.2


def test_field_rms_is_preserved_across_both_axes():
    """Otherwise a shape effect and a magnitude effect are confounded, which is
    the confound this whole line of probes exists to avoid."""
    rng = np.random.default_rng(4)
    for sc, sr in ((0.0, 0.0), (1.45, 1.05), (0.561, 0.561)):
        f = anisotropic_field(INJECTION_GRID, 2.5, sc, sr, rng)
        assert float(f.std()) == pytest.approx(2.5, rel=1e-9)


def test_the_isotropic_arm_smooths_both_axes():
    """Guard against the strawman a first draft of this comparison contained: an
    'isotropic' arm that smoothed only one axis is not the published
    configuration, and comparing against it would exaggerate the effect."""
    rng = np.random.default_rng(9)
    both = anisotropic_field(INJECTION_GRID, 1.0, ISOTROPIC_SIGMA, ISOTROPIC_SIGMA, rng)
    one = anisotropic_field(INJECTION_GRID, 1.0, ISOTROPIC_SIGMA, 0.0, rng)

    def lag(f, ax):
        a = np.moveaxis(f, ax, -1)
        return float(np.corrcoef(a[..., :-1].ravel(), a[..., 1:].ravel())[0, 1])

    assert lag(both, 0) > lag(one, 0) + 0.2


def test_ess_matched_control_really_matches():
    """The control arm only isolates anisotropy if its effective sample size
    equals the anisotropic arm's. If it did not, the 'magnitude alone' comparison
    would itself be confounded -- which is exactly the error this control exists
    to correct."""
    sc, sr = 1.45, 1.05
    control = ess_matched_isotropic(INJECTION_GRID, sc, sr)
    target = effective_sample_size(INJECTION_GRID, sc, sr)
    got = effective_sample_size(INJECTION_GRID, control, control)
    assert got == pytest.approx(target, rel=0.10)


def test_the_published_arm_has_far_more_effective_dof():
    """The premise of the whole correction: the published isotropic arm and the
    anisotropic arm are NOT comparable in magnitude, so attributing their gap to
    the axis ratio was invalid."""
    published = effective_sample_size(INJECTION_GRID, ISOTROPIC_SIGMA, ISOTROPIC_SIGMA)
    fitted = effective_sample_size(INJECTION_GRID, 1.45, 1.05)
    assert published > 3 * fitted
