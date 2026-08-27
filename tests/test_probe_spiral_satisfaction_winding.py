"""The probe's own harness must be correct before its null means anything."""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""  # CPU-only for the imports below
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import numpy as np
import pytest
import torch
from conftest import restore_cuda_env  # noqa: E402
from probe_spiral_satisfaction_winding import (
    DR,
    build_synthetic_patch,
    displace,
    score,
    score_conditions,
)

restore_cuda_env()  # do not leave the mask for other test modules


def test_reference_patch_is_fully_satisfied():
    """A patch built exactly on winding 5 must score 1.0, or the harness is wrong."""
    patch = build_synthetic_patch(dr=DR, winding=5)
    assert score(patch, DR) == pytest.approx(1.0, abs=1e-9)


def test_displacement_is_exactly_one_winding():
    """displace() must move every point's shifted radius by exactly dr."""
    patch = build_synthetic_patch(dr=DR, winding=5)
    moved = displace(patch, DR, n_windings=1)
    sys.path.insert(
        0, os.path.join(_REPO, "villa", "volume-cartographer", "scripts", "spiral")
    )
    from sample_spiral import get_theta_and_radii

    dr_t = torch.tensor(DR)
    _, _, before = get_theta_and_radii(patch.zyxs[..., 1:], dr_t)
    _, _, after = get_theta_and_radii(moved.zyxs[..., 1:], dr_t)
    assert torch.allclose(after - before, torch.full_like(before, DR), atol=1e-4)


def test_metric_does_detect_a_half_winding_displacement():
    """The control. A half-winding offset sits outside the 0.45*dr tolerance,
    so the metric MUST reject it. If this passes as satisfied, the probe is not
    exercising the metric and the one-winding null means nothing."""
    patch = build_synthetic_patch(dr=DR, winding=5)
    half = displace(patch, DR, n_windings=0.5)
    assert score(half, DR) < 0.5


def test_metric_does_not_detect_a_whole_winding_displacement():
    """The finding itself, pinned as a regression test."""
    patch = build_synthetic_patch(dr=DR, winding=5)
    whole = displace(patch, DR, n_windings=1.0)
    assert abs(score(whole, DR) - score(patch, DR)) <= 1e-6


def test_both_conditions_independently_satisfied_at_one_winding():
    """The actual finding, broken out by condition. get_patch_satisfied_areas
    ANDs a spiral-space shifted-radius tolerance (0.45*dr = 45 units, which a
    one-winding/100-unit offset would fail) with an absolute scan-space
    tolerance (6.0 voxels, which a one-winding offset trivially passes because
    every point lands on the identical geometry one winding over). The blind
    spot is real only if BOTH conditions pass independently, not just their
    AND -- otherwise the combined 1.0 could be hiding a saturated scan-space
    check riding on a spiral-space check that actually fired."""
    patch = build_synthetic_patch(dr=DR, winding=5)
    whole = displace(patch, DR, n_windings=1.0)
    spiral_fraction, scan_fraction, combined_fraction = score_conditions(whole, DR)
    assert spiral_fraction == pytest.approx(1.0, abs=1e-9)
    assert scan_fraction == pytest.approx(1.0, abs=1e-9)
    assert combined_fraction == pytest.approx(score(whole, DR), abs=1e-9)
