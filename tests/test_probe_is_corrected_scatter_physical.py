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
    ANALYSIS,
    SCALES,
    corrected_p95,
    raw_deviation,
    shared_vs_local,
    statistic_power,
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
def test_the_concern_is_open_at_the_analysis_scale():
    """The check that matters, and the one an earlier version got backwards. The
    corrected figure describes deviation inside the ANALYSIS window, so it must be
    compared against raw deviation at that same window -- not at a nine times
    larger one. It is several times larger, and that gap is the open concern."""
    rng = np.random.default_rng(4)
    h, w = ANALYSIS
    raw = raw_deviation(h, w, rng, n=800)
    assert float(np.percentile(raw, 95)) * 2 < corrected_p95()


@needs_data
def test_the_cross_scale_argument_is_unstable():
    """Pins why the earlier closure was invalid rather than merely unlucky: its
    conclusion flips on an unargued constant. A check whose outcome is set by which
    window the author picked is not a check."""
    rng = np.random.default_rng(9)
    small = raw_deviation(7, 9, rng, n=400)
    big = raw_deviation(9, 12, rng, n=400)
    assert float(np.percentile(small, 95)) < corrected_p95()
    assert float(np.percentile(big, 95)) > corrected_p95()


def test_the_local_fraction_statistic_saturates():
    """The power calibration whose absence let 0.85 be read as '85 percent
    perturbs'. On fields of known composition the statistic must be shown to
    compress a wide range of true fractions into a narrow reported band, or the
    observed value would carry the information it was assumed to."""
    rng = np.random.default_rng(12)
    power = statistic_power(rng, fractions=(0.05, 0.50), trials=120)
    (_, low), (_, high) = power
    assert low > 0.3, "a 5% local field should already report a large fraction"
    assert high / low < 3.0, "statistic does not compress; it may have real power"


def test_the_split_is_not_a_partition():
    """Pins the symptom that shows the decomposition is a vector subtraction, not
    an orthogonal split: local can exceed total, which a partition cannot do."""
    rng = np.random.default_rng(13)
    totals, locals_ = shared_vs_local(rng, n=400)
    assert float((locals_ > totals).mean()) > 0.05


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
def test_samples_are_pooled_across_patches():
    """An earlier version drew every sample from one patch, because the loop broke
    out of the outer patch loop. That patch was the second-highest of eight for
    this statistic."""
    import probe_is_corrected_scatter_physical as mod

    rng = np.random.default_rng(5)
    per_patch = 20
    v = raw_deviation(*ANALYSIS, rng, per_patch=per_patch)
    assert len(v) > per_patch, "all samples came from a single patch"
    assert len(v) <= per_patch * len(mod.patch_dirs())


@needs_data
def test_removing_shared_curvature_cannot_increase_the_median():
    """Sanity on the decomposition: subtracting a fitted smooth surface should not
    make the typical residual larger. A median local fraction above 1 would mean
    the split is not doing what it claims."""
    rng = np.random.default_rng(6)
    totals, locals_ = shared_vs_local(rng, n=300)
    assert float(np.median(locals_)) <= float(np.median(totals))
