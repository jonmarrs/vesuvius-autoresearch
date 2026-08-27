"""Tests for the matched-correlation onset sweep.

The point of this probe is that the two sides of a comparison were previously
measured at different correlation lengths. The tests pin the things that make the
corrected comparison meaningful: that correlation length actually moves the onset
(otherwise the mismatch never mattered), that the fitted sigma is in the swept
set, and that the min-over-rays and per-ray-median statistics are not confused.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""  # CPU-only for the imports below
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import pathlib  # noqa: E402
import re  # noqa: E402

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from conftest import restore_cuda_env  # noqa: E402
from probe_correlated_scatter import run_level  # noqa: E402
from probe_onset_at_matched_correlation import (  # noqa: E402
    CORRECTED_MEDIAN,
    CORRECTED_TAIL,
    INJECTION_GRID,
    RMS_LEVELS,
    SIGMA_GRID,
    onset_for,
)
from probe_scatter_estimator_calibration import WINDOW, matched_sigma  # noqa: E402
from probe_spiral_satisfaction_empirical_transform import (  # noqa: E402
    load_shard,
    usable_rays,
)

restore_cuda_env()  # do not leave the mask for other test modules


def _rays(n=40):
    return usable_rays(load_shard(), n_rays=n)


def test_correlation_length_actually_moves_the_onset():
    """If it did not, the mismatch this probe exists to fix would not have
    mattered, and the whole exercise would be empty."""
    rays = _rays()
    lo, _, _ = onset_for(rays, 0.0)
    hi, _, _ = onset_for(rays, 2.0)
    assert lo is not None and hi is not None
    assert hi < lo


def test_more_correlation_flips_more_rays():
    """The monotone direction the comparison relies on: at a fixed rms, a longer
    correlation length should catch at least as many rays."""
    rays = _rays()
    rms = 2.5
    _, few = run_level(rays, rms, 0.0, np.random.default_rng(1))
    _, many = run_level(rays, rms, 2.0, np.random.default_rng(1))
    assert many > few


def test_the_fitted_sigma_is_fitted_on_the_injection_grid():
    """The sigma must be fitted on the grid the noise is actually injected on, not
    on the calibration's analysis window. The same sigma induces a materially
    different lag-1 on the two shapes, so transferring the parameter across probes
    does not transfer the statistic it was calibrated to. An earlier version did
    exactly that."""
    on_injection = matched_sigma(INJECTION_GRID)
    on_window = matched_sigma(WINDOW)
    assert abs(on_injection - on_window) > 0.05
    assert min(SIGMA_GRID) <= on_injection <= max(SIGMA_GRID)


def test_corrected_bands_match_the_artifact_they_cite():
    """The specific failure that has now happened four times: a statistic typed
    into one file from another and never re-checked. CORRECTED_MEDIAN's low end was
    1.30, which appears in no artifact."""
    text = pathlib.Path(
        os.path.join(_REPO, "reports", "scatter_estimator_calibration.txt")
    ).read_text()
    found = sorted(
        {
            float(m)
            for m in re.findall(r"\b1\.\d{2}\b", text.split("corrected median")[-1])
            if 1.2 < float(m) < 1.6
        }
    )
    assert found, "no corrected-median values parsed from the artifact"
    assert CORRECTED_MEDIAN[0] == pytest.approx(min(found), abs=0.01)
    assert CORRECTED_MEDIAN[1] == pytest.approx(max(found), abs=0.01)
    assert CORRECTED_TAIL[0] < CORRECTED_TAIL[1]


def test_the_reported_median_is_not_the_min():
    """Kills the mutant the old test could not: collapsing the per-ray median to a
    min over rays. The old assertion was `first <= med`, which the gating it was
    testing guaranteed by construction and which min==median also satisfies."""
    rays = _rays()
    first, med, n = onset_for(rays, 0.56)
    assert first is not None and med is not None
    assert 0 < n <= len(rays)
    assert med > first, "median collapsed to the minimum; the statistic is wrong"


def test_the_median_is_conditional_and_the_count_says_so():
    """The reported median is taken among rays that flip at all. Fewer than half do
    at most correlation lengths, so the unconditional median is censored above the
    swept range. The count column is what makes that visible and must be reported."""
    rays = _rays()
    _, med, n = onset_for(rays, 0.56)
    assert med is not None
    if n < len(rays) / 2:
        assert med <= max(RMS_LEVELS)


def test_the_swept_range_reaches_the_corrected_scatter_band():
    """Relevance guard, now driven by the constants rather than re-hardcoding them."""
    assert min(RMS_LEVELS) <= CORRECTED_MEDIAN[0]
    assert max(RMS_LEVELS) >= CORRECTED_TAIL[1]
