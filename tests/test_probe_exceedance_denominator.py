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
