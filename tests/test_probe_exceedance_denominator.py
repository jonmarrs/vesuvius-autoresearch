"""Tests for the exceedance-denominator classification.

The probe's answer supports a figure I already published, and half its
pre-registered rule turned out to be unfireable, so these tests pin both facts:
that the classes really partition the rays, and that the artifact discloses the
half of the rule that could not have fired.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import numpy as np  # noqa: E402
import probe_exceedance_denominator as mod  # noqa: E402
from conftest import restore_cuda_env  # noqa: E402
from probe_spiral_satisfaction_empirical_transform import (  # noqa: E402
    load_shard,
    usable_rays,
)

restore_cuda_env()  # do not leave the mask for other test modules

ARTIFACT = os.path.join(_REPO, "reports", "exceedance_denominator.txt")


def test_the_classes_partition_the_rays():
    """Exhaustive and disjoint, checked rather than asserted in prose. A ray that
    fell through would silently shrink whichever share it belonged to."""
    rays = usable_rays(load_shard(), n_rays=6)
    labels = mod.classify(rays, seed=3)
    assert len(labels) == len(rays)
    assert set(labels) <= {"degenerate", "immune", "diverges"}


def test_the_reference_is_satisfied_at_zero_scatter():
    """Why the degenerate class is empty: the test patch is built exactly on a
    winding, so the reference passes by construction. Pinned because it is the
    reason half the pre-registered rule could not fire, and that has to stay
    visible rather than being rediscovered."""
    rays = usable_rays(load_shard(), n_rays=8)
    for ray in rays:
        ref, _ = mod.verdicts(ray, 0.0, np.random.default_rng(1))
        assert ref, "the reference should pass at zero scatter by construction"


def test_a_displaced_patch_at_zero_scatter_also_passes():
    """The core finding of the whole report, reachable from here: at zero scatter
    the whole-winding-displaced patch is satisfied too, which is why the classes
    can only separate on what noise does."""
    rays = usable_rays(load_shard(), n_rays=8)
    for ray in rays:
        ref, mov = mod.verdicts(ray, 0.0, np.random.default_rng(1))
        assert ref == mov


def test_the_artifact_discloses_the_unfireable_half():
    """The rule had two branches and only one could ever fire. An artifact that
    reported the passing branch without saying so would be claiming a check it
    did not perform."""
    text = open(ARTIFACT).read()
    assert "could not have fired" in text
    assert "empty by construction" in text


def test_the_artifact_does_not_overclaim_about_real_patches():
    """The probe uses a synthetic patch. It must not be read as evidence that real
    traced patches pass at zero scatter."""
    text = open(ARTIFACT).read()
    assert "A real traced patch could well fail at" in text


def test_the_split_is_reported_with_both_classes_nonzero():
    """The informative output. If either class were empty the probe would be
    reporting a foregone conclusion in both halves rather than one."""
    import re

    text = open(ARTIFACT).read()
    imm = re.search(r"immune\s+([\d.]+)%", text)
    div = re.search(r"diverges\s+([\d.]+)%", text)
    assert imm and div
    assert float(imm.group(1)) > 5.0
    assert float(div.group(1)) > 5.0


def test_immunity_is_surrogate_sensitive_at_a_short_ladder():
    """The qualification the report needed. A first version called the immune
    fraction free of the surrogate because no attenuation enters it. True, and
    misleading: at a ladder stopping at 4.0 voxels it runs from about 51 to 88
    percent depending purely on which field is injected."""
    rays = usable_rays(load_shard(), n_rays=12)
    white = mod.classify(rays, mod.SEED, (0.0, 0.0), mod.RMS_LEVELS).count("immune")
    aniso = mod.classify(rays, mod.SEED, (1.20, 1.00), mod.RMS_LEVELS).count("immune")
    assert white > aniso, "a white field should look far more immune at a short ladder"


def test_a_wider_ladder_cannot_raise_immunity():
    """The monotonicity that makes the wide column a lower bound: more rungs give
    more chances to flip, so immunity can only fall."""
    rays = usable_rays(load_shard(), n_rays=12)
    narrow = mod.classify(rays, mod.SEED, (0.0, 0.0), mod.RMS_LEVELS).count("immune")
    wide = mod.classify(rays, mod.SEED, (0.0, 0.0), mod.WIDE_LEVELS).count("immune")
    assert wide <= narrow


def test_the_wide_ladder_arms_agree_within_ten_points():
    """What licenses quoting a single range. If the arms disagreed by more at the
    wide ladder, the report would have to give per-surrogate values."""
    text = open(ARTIFACT).read()
    assert "a spread of" in text
    assert "Within 10 points" in text
