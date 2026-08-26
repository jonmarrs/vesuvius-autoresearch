"""Tests for the self-consistent exceedance.

The finding is negative and unfavourable: computing both sides of the comparison
under one surrogate does NOT stabilise the exceedance, it spans more than an order
of magnitude across plausible surrogates. Two things would make that finding
spurious -- an attenuation refit that does not actually respond to the surrogate,
and a sweep too narrow to show the spread. Both are pinned.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from probe_real_patch_scatter import patch_dirs  # noqa: E402
from probe_self_consistent_exceedance import (  # noqa: E402
    SURROGATES,
    admissibility,
    real_reported_scatter,
    refit_attenuation,
)

needs_data = pytest.mark.skipif(not patch_dirs(), reason="real patch data absent")


@needs_data
def test_the_attenuation_responds_to_the_surrogate():
    """The premise. If k were the same under every field, there would be no
    inconsistency to fix and no spread to report."""
    _, k_published = refit_attenuation(0.561, 0.561)
    _, k_corrected = refit_attenuation(1.45, 1.05)
    assert k_published > 2 * k_corrected


@needs_data
def test_a_more_correlated_field_gives_a_smaller_k():
    """Direction check: more correlation means the estimator absorbs more of the
    injected signal, so k falls. A k that rose would invert the whole argument."""
    _, k_low = refit_attenuation(0.561, 0.561)
    _, k_mid = refit_attenuation(0.90, 0.90)
    _, k_high = refit_attenuation(1.236, 1.236)
    assert k_low > k_mid > k_high


@needs_data
def test_the_floor_is_surrogate_independent():
    """The floor is measured with nothing injected, so it must not depend on which
    field WOULD have been injected. If it did, the refit would be leaking."""
    f_a, _ = refit_attenuation(0.561, 0.561)
    f_b, _ = refit_attenuation(1.45, 1.05)
    assert f_a == pytest.approx(f_b, abs=0.02)


@needs_data
def test_reported_scatter_is_stable_across_seeds():
    """Named for what it actually pins. Surrogate independence is STRUCTURAL --
    `real_reported_scatter` takes no surrogate argument -- so this can only test
    sampling stability. An earlier docstring claimed it ruled out circularity,
    which is a stronger claim than the assertion supports."""
    a = real_reported_scatter(seed=1)
    b = real_reported_scatter(seed=2)
    assert float(np.median(a)) == pytest.approx(float(np.median(b)), rel=0.10)


def test_only_one_swept_surrogate_reproduces_the_real_statistics():
    """The criterion that decides which arms are candidate fields. Without it the
    probe reported a 15.6x spread across four arms as uncertainty, when three of
    them are fields the data rejects. If more than one were admissible, the
    published band would have to widen accordingly."""
    scored = [(label, admissibility(sc, sr)) for label, sc, sr in SURROGATES]
    admissible = [label for label, (_, _, cost) in scored if cost < 0.10]
    assert len(admissible) == 1
    assert "anisotropic" in admissible[0]


def test_the_published_surrogate_has_the_wrong_sign():
    """The sharpest single fact against treating the four arms as peers: the
    published field's column statistic points the opposite way from the real
    residual it is supposed to reproduce."""
    published = next(s for s in SURROGATES if "published" in s[0])
    col, _, _ = admissibility(published[1], published[2])
    assert col < 0


def test_the_sweep_spans_a_meaningful_surrogate_range():
    """Relevance guard: a sweep over near-identical fields could not detect the
    sensitivity this probe exists to measure."""
    sigmas = [max(sc, sr) for _, sc, sr in SURROGATES]
    assert max(sigmas) > 2 * min(sigmas)
    assert len(SURROGATES) >= 3
