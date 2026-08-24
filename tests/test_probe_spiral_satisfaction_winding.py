"""The probe's own harness must be correct before its null means anything."""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import numpy as np
import pytest
import torch
from probe_spiral_satisfaction_winding import (
    DR,
    build_synthetic_patch,
    displace,
    score,
)


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
