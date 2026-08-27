"""Tests for the scatter-onset probe.

The two claims that carry weight are that the onset exists and is bracketed, and
that it is ABSOLUTE (governed by villa's 6.0-voxel scan tolerance) rather than
RELATIVE (governed by its 0.45*dr spiral tolerance). The second is only credible
because dr is isolated by rescaling; the guard here is that the rescale really
does hold irregularity fixed.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""  # CPU-only for the imports below
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from conftest import restore_cuda_env  # noqa: E402
from probe_spiral_satisfaction_empirical_transform import (  # noqa: E402
    load_shard,
    usable_rays,
)
from probe_spiral_satisfaction_onset import (  # noqa: E402
    onset_by_rescaled_dr,
    onsets,
    rescale_to,
    sweep,
)
from probe_spiral_satisfaction_splicing_and_seam import REPORTING  # noqa: E402

restore_cuda_env()  # do not leave the mask for other test modules


def _rays(n=40):
    """40, matching the probe's own N_RAYS. The headline onset is a min over the
    sampled rays, so a smaller sample can miss it entirely -- which an earlier
    version of these tests did, at n=12."""
    return usable_rays(load_shard(), n_rays=n)


def test_rescale_sets_dr_and_preserves_irregularity():
    """The rescale is the whole basis for the absolute-vs-relative claim. It must
    move dr and leave every relative irregularity untouched; if it altered the
    shape, the isolated sweep would be measuring two things again."""
    for _, radii in _rays(6):
        for target in (7.0, 19.0):
            out = rescale_to(radii, target)
            assert float(np.mean(np.diff(out))) == pytest.approx(target, rel=1e-9)
            before = np.diff(np.diff(radii)) / float(np.mean(np.diff(radii)))
            after = np.diff(np.diff(out)) / float(np.mean(np.diff(out)))
            assert np.allclose(before, after, atol=1e-9)


def test_an_onset_exists_and_is_bracketed():
    """Below the onset nothing flips; above it something does. A probe that found
    a flip at every level, or none at any, would not have located anything."""
    rays = _rays()
    o = onsets(sweep(rays, REPORTING))
    assert o["verdict_flips"] is not None
    assert o["fraction_moves"] is not None
    assert o["fraction_moves"] <= o["verdict_flips"]


def test_the_onset_is_absolute_not_a_fixed_fraction_of_dr():
    """The interpretive claim. Across a 2.5x range of dr the onset in VOXELS
    should stay within a narrow band, while the onset expressed as a fraction of
    dr should vary substantially. If both were flat, or the voxel figure moved
    proportionally with dr, the conclusion would be the opposite one."""
    rays = _rays()
    pairs = [(t, o) for t, o in onset_by_rescaled_dr(rays, REPORTING) if o is not None]
    assert len(pairs) >= 4
    voxels = [o for _, o in pairs]
    fractions = [o / t for t, o in pairs]
    assert max(voxels) - min(voxels) <= 0.75
    assert max(fractions) / min(fractions) > 2.0


def test_the_confounds_that_make_the_dr_bins_unusable_are_real():
    """The probe prints the by-dr-bin table labelled confounded. That label has to
    be earned, not asserted: dr must actually covary with knot count in the real
    population."""
    rays = _rays(40)
    dr = np.array([float(np.mean(np.diff(r))) for _, r in rays])
    n_knots = np.array([len(r) for _, r in rays], dtype=float)
    assert np.corrcoef(dr, n_knots)[0, 1] < -0.5
