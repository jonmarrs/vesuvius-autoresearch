"""Tests for the radial-span diagnostic.

This one explains a result rather than testing a hypothesis, so the tests guard
the two ways an explanation can be hollow: a measurement that does not measure
what it claims, and a caveat that quietly disappears.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import numpy as np  # noqa: E402
import probe_radial_span_mismatch as mod  # noqa: E402
import pytest  # noqa: E402
from conftest import restore_cuda_env  # noqa: E402
from probe_real_patch_scatter import patch_dirs  # noqa: E402

restore_cuda_env()  # do not leave the mask for other test modules

needs_data = pytest.mark.skipif(not patch_dirs(), reason="real patch data absent")
ARTIFACT = os.path.join(_REPO, "reports", "radial_span_mismatch.txt")


def test_radial_span_measures_radius_not_extent():
    """The distinction the whole diagnostic turns on. A patch translated in z has
    the same radial span; one moved outward in radius does not."""
    import torch
    from probe_spiral_satisfaction_winding import SyntheticPatch, displace

    zyxs = torch.zeros(3, 3, 3)
    zyxs[..., 2] = torch.tensor([[100.0, 101.0, 102.0]] * 3)
    patch = SyntheticPatch(
        zyxs=zyxs, valid_quad_mask=torch.ones([2, 2], dtype=torch.bool), area=1.0
    )
    span = mod.radial_span(patch)
    assert span == pytest.approx(2.0, abs=1e-3)

    shifted = SyntheticPatch(
        zyxs=zyxs.clone(), valid_quad_mask=patch.valid_quad_mask, area=1.0
    )
    shifted.zyxs[..., 0] += 500.0  # pure z translation
    assert mod.radial_span(shifted) == pytest.approx(span, abs=1e-3)

    moved = displace(patch, 12.81, n_windings=1.0)
    assert mod.radial_span(moved) == pytest.approx(span, abs=1e-2)


@needs_data
def test_the_synthetic_patch_is_sub_winding_and_real_windows_are_not():
    """The finding. The test patch sits inside a fraction of a winding; the
    smallest window the published data can form does not."""
    from probe_correlated_scatter import WINDING
    from probe_real_patch_satisfaction import REAL_DR, real_windows
    from probe_spiral_satisfaction_winding import build_synthetic_patch

    synth = mod.radial_span(build_synthetic_patch(dr=REAL_DR, winding=WINDING))
    assert synth / REAL_DR < 0.25

    windows = real_windows((2, 2), n_windows=20)
    spans = np.array([mod.radial_span(p) for _, p in windows]) / REAL_DR
    assert float(np.median(spans)) > 0.5


@needs_data
def test_span_grows_with_window_size():
    """Sanity on the table: a bigger window cannot span less radius."""
    from probe_real_patch_satisfaction import real_windows

    med = []
    for shape in ((2, 2), (4, 6), (12, 16)):
        windows = real_windows(shape, n_windows=20)
        med.append(float(np.median([mod.radial_span(p) for _, p in windows])))
    assert med == sorted(med)


def test_the_artifact_keeps_the_category_caveat():
    """These are traced surfaces, not villa spiral-fit patches. If that caveat is
    ever dropped the diagnostic overclaims badly."""
    text = open(ARTIFACT).read()
    assert "not villa spiral-fit patches" in text
    assert "no fitted spiral checkpoint is published" in text


def test_the_artifact_names_the_corrected_claim():
    """The report's 'comparable window' phrase has now been wrong on two axes, and
    the artifact has to say which one it is correcting."""
    text = open(ARTIFACT).read()
    assert "comparable to the" in text
    assert "wrong on this axis by a factor of" in text
