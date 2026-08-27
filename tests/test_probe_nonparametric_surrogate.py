"""Tests for the non-parametric surrogate probe, whose verdict is WITHDRAWN.

The probe's pre-registered rule fired, and the verdict it produced was wrong
anyway, because the comparison it fired on was between incommensurable
quantities. These tests pin the diagnostic that establishes that, and pin the
withdrawal itself so the artifact cannot quietly regain a verdict it has not
earned.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import numpy as np  # noqa: E402
import probe_nonparametric_surrogate as mod  # noqa: E402
import pytest  # noqa: E402
from conftest import restore_cuda_env  # noqa: E402
from probe_real_patch_scatter import patch_dirs  # noqa: E402

restore_cuda_env()  # do not leave the mask for other test modules

needs_data = pytest.mark.skipif(not patch_dirs(), reason="real patch data absent")
ARTIFACT = os.path.join(_REPO, "reports", "nonparametric_surrogate.txt")


def test_a_short_correlation_field_survives_a_small_window():
    """The control that gives the diagnostic its meaning. A white field keeps most
    of its variance inside a 3x4 window, so a low ratio for another field is a
    statement about that field, not about the measurement."""
    from probe_anisotropic_surrogate import anisotropic_field

    rng = np.random.default_rng(2)
    white = anisotropic_field((120, 160), 1.0, 0.0, 0.0, rng)
    assert mod.windowed_over_global(white, rng) > 0.7


def test_a_long_wavelength_field_does_not():
    """The mechanism itself, on a field of known construction rather than on the
    real data: heavy smoothing moves power to wavelengths a 3x4 plane fit removes,
    and the ratio collapses. This is why the probe's k is not comparable."""
    from probe_anisotropic_surrogate import anisotropic_field

    rng = np.random.default_rng(2)
    smooth = anisotropic_field((120, 160), 1.0, 8.0, 8.0, rng)
    assert mod.windowed_over_global(smooth, rng) < 0.1


@needs_data
def test_the_real_residual_is_the_long_wavelength_case():
    """And the real transplanted residual behaves like the smooth field, not the
    white one, which is the whole reason the verdict was withdrawn."""
    rng = np.random.default_rng(4)
    bank = mod.residual_bank()
    ratios = [
        mod.windowed_over_global(mod.transplant(r, (120, 160), 1.0, rng), rng)
        for _, r, _ in bank[:5]
    ]
    finite = [x for x in ratios if np.isfinite(x)]
    assert finite, "every donor degenerated; the diagnostic would say nothing"
    assert max(finite) < 0.3


def test_the_artifact_carries_no_verdict():
    """The withdrawal, pinned. The rule firing is not the same as the comparison
    being valid, and the artifact must not present one as the other."""
    text = open(ARTIFACT).read()
    assert "THE PRE-REGISTERED VERDICT IS WITHDRAWN" in text
    assert "UNDERESTIMATE" not in text
    assert "carries no verdict either" in text


def test_the_artifact_says_what_would_make_it_valid():
    """A withdrawn probe should leave the next person a route, not just a hole."""
    text = open(ARTIFACT).read()
    assert "What would make it valid" in text
    assert "probe_self_consistent_exceedance" in text


@needs_data
def test_the_donor_is_never_the_recipient():
    """Self-injection is the flattering failure here, and the assertion that
    prevents it must actually be reachable rather than decorative."""
    import inspect

    src = inspect.getsource(mod.refit_nonparametric)
    assert 'assert donor_name != os.path.basename(d), "self-injection"' in src
    assert "names.index(os.path.basename(d))" in src
