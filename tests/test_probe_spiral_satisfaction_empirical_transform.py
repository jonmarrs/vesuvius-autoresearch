"""Tests for the empirical-transform probe.

The claim is that the winding-blindness survives a radial warp built from real
measured winding positions, which is the locally-irregular shape the smooth
power-law sweep structurally could not represent. The two things that would make
that claim vacuous are a transform that is secretly an identity, and a ray filter
that silently admits skipped windings. Both are guarded here.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import numpy as np  # noqa: E402
import pytest  # noqa: E402
import torch  # noqa: E402
from probe_spiral_satisfaction_empirical_transform import (  # noqa: E402
    EmpiricalRadialTransform,
    load_shard,
    ray_winding_radii,
    run_ray,
    usable_rays,
)
from probe_spiral_satisfaction_splicing_and_seam import (  # noqa: E402
    REPORTING,
    SPLICING,
)
from probe_spiral_satisfaction_winding import build_synthetic_patch  # noqa: E402


def _knots():
    measured = np.array([0.0, 12.0, 25.0, 34.0, 49.0, 58.0, 74.0], dtype=np.float64)
    ideal = np.arange(len(measured), dtype=np.float64) * float(
        np.mean(np.diff(measured))
    )
    return ideal, measured


def test_transform_round_trips():
    """inv then forward must return the original geometry, or the warp is not an
    invertible change of coordinates and nothing measured through it means much."""
    ideal, measured = _knots()
    t = EmpiricalRadialTransform(ideal, measured)
    p = build_synthetic_patch(dr=float(np.mean(np.diff(measured))), winding=3)
    back = t(t.inv(p.zyxs))
    assert torch.allclose(back, p.zyxs, atol=1e-4)


def test_transform_is_materially_not_an_identity():
    """The whole point is testing a NON-identity, locally irregular warp. If the
    warp moved points only negligibly the result would be a restatement of the
    identity-transform case."""
    ideal, measured = _knots()
    t = EmpiricalRadialTransform(ideal, measured)
    p = build_synthetic_patch(dr=float(np.mean(np.diff(measured))), winding=3)
    moved = t.inv(p.zyxs)
    shift = (moved[..., 1:] - p.zyxs[..., 1:]).abs().max().item()
    assert shift > 1.0


def test_transform_rejects_non_monotonic_knots():
    """A non-increasing knot sequence is not invertible and must be refused
    rather than silently producing a folded map."""
    with pytest.raises(ValueError):
        EmpiricalRadialTransform([0.0, 1.0, 2.0], [0.0, 5.0, 3.0])


def test_ray_filter_rejects_skipped_winding_levels():
    """A ray whose crossings skip a winding would fold two inter-winding gaps
    into one, corrupting the measured radial map. The filter must refuse it."""
    shard = load_shard()
    shard = {k: v.copy() for k, v in shard.items()}
    lo = int(shard["crossing_offsets"][0])
    good = ray_winding_radii(shard, 0)
    shard["crossing_level"][lo + 2] += 5  # break consecutiveness
    assert ray_winding_radii(shard, 0) is None
    if good is not None:
        assert len(good) >= 2


def test_real_rays_are_actually_irregular():
    """Guard on the premise: if the measured gap sequences were nearly uniform,
    this probe would not be testing local irregularity at all."""
    shard = load_shard()
    rays = usable_rays(shard, n_rays=10)
    assert rays
    worst = 0.0
    for _, radii in rays:
        dr = float(np.mean(np.diff(radii)))
        worst = max(worst, float(np.max(np.abs(np.diff(np.diff(radii)) / dr))))
    assert worst > 0.1


def test_blindness_survives_real_measured_geometry():
    """The finding, under real locally-irregular winding geometry, in both of
    villa's configurations."""
    shard = load_shard()
    rays = usable_rays(shard, n_rays=10)
    for cfg in (REPORTING, SPLICING):
        for _, radii in rays:
            row = run_ray(radii, cfg)
            assert row["delta"] == pytest.approx(0.0, abs=1e-9)
            assert row["ref_verdict"] is True
            assert row["disp_verdict"] is True
