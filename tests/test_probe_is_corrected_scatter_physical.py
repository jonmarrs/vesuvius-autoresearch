"""Tests for the physicality check on corrected real scatter.

This probe closes a loose end in favour of the figure it checks, which is the
direction that deserves the most scepticism. Its two claims are that the raw
geometry independently supports the corrected magnitude, and that most of the
deviation is local rather than shared curvature. Both are pinned, along with the
premise that makes the first check meaningful at all: that it uses no correction
model, so it is not the model checking itself.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from probe_is_corrected_scatter_physical import (  # noqa: E402
    CORRECTED_P95,
    SCALES,
    raw_deviation,
    shared_vs_local,
)
from probe_real_patch_scatter import patch_dirs  # noqa: E402

needs_data = pytest.mark.skipif(not patch_dirs(), reason="real patch data absent")


@needs_data
def test_deviation_grows_with_window_extent():
    """The premise behind reading the growth as curvature. If deviation were flat
    across scales it would be local roughness throughout and the second half of
    this probe would be asking a question that does not arise."""
    rng = np.random.default_rng(3)
    meds = [float(np.median(raw_deviation(h, w, rng, n=200))) for h, w in SCALES]
    assert meds == sorted(meds)
    assert meds[-1] > 3 * meds[0]


@needs_data
def test_the_corrected_magnitude_is_reachable_in_raw_geometry():
    """The physicality check. The corrected p95 must sit inside what the raw
    geometry does at some observable scale; if it exceeded everything measurable,
    it would be an artifact of dividing by a small attenuation."""
    rng = np.random.default_rng(4)
    h, w = SCALES[-1]
    biggest = raw_deviation(h, w, rng, n=300)
    assert float(np.percentile(biggest, 95)) > CORRECTED_P95


@needs_data
def test_the_raw_check_uses_no_correction_model():
    """Guard on independence. `raw_deviation` must not import or apply the
    attenuation being checked, or the check is the model validating itself."""
    import inspect

    import probe_is_corrected_scatter_physical as mod

    src = inspect.getsource(mod.raw_deviation)
    for forbidden in ("CAL_K", "CAL_FLOOR", "anisotropic_field", "refit_attenuation"):
        assert forbidden not in src


@needs_data
def test_most_deviation_is_local_not_shared_curvature():
    """The second claim, and the one that decides whether the exceedance model is
    treating the right quantity. If the local fraction were small, most of the
    corrected scatter would be curvature the spiral follows and the exceedance
    would be an overestimate."""
    rng = np.random.default_rng(5)
    totals, locals_ = shared_vs_local(rng, n=300)
    frac = float(np.median(locals_ / np.maximum(totals, 1e-12)))
    assert 0.0 < frac <= 1.05
    assert frac > 0.6


@needs_data
def test_removing_shared_curvature_cannot_increase_the_median():
    """Sanity on the decomposition: subtracting a fitted smooth surface should not
    make the typical residual larger. A median local fraction above 1 would mean
    the split is not doing what it claims."""
    rng = np.random.default_rng(6)
    totals, locals_ = shared_vs_local(rng, n=300)
    assert float(np.median(locals_)) <= float(np.median(totals))
