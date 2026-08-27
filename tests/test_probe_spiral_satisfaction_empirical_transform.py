"""Tests for the empirical-transform probe.

The claim is that the winding-blindness survives a radial warp built from real
measured winding positions, which is the locally-irregular shape the smooth
power-law sweep structurally could not represent. The two things that would make
that claim vacuous are a transform that is secretly an identity, and a ray filter
that silently admits skipped windings. Both are guarded here.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""  # CPU-only for the imports below
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import numpy as np  # noqa: E402
import pytest  # noqa: E402
import torch  # noqa: E402
from conftest import restore_cuda_env  # noqa: E402
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

restore_cuda_env()  # do not leave the mask for other test modules


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
    into one, corrupting the measured spacing sequence.

    The earlier version of this test used ray index 0, which has 8 crossings and
    is rejected by the >=10 crossing check BEFORE the consecutiveness guard is
    ever reached -- so it passed with the guard deleted entirely. It is pinned
    here to a ray that actually reaches the guard.
    """
    shard = load_shard()
    idx = next(
        i
        for i in range(len(shard["crossing_offsets"]) - 1)
        if ray_winding_radii(shard, i) is not None
    )
    assert ray_winding_radii(shard, idx) is not None

    mutated = {k: v.copy() for k, v in shard.items()}
    lo = int(mutated["crossing_offsets"][idx])
    mutated["crossing_level"][lo + 2] += 5
    assert ray_winding_radii(mutated, idx) is None


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


def test_zero_scatter_is_degenerate_and_is_labelled_as_such():
    """At zero scatter the delta is zero for ANY invertible transform by the
    section-1 algebra, so this row carries no information about the empirical
    warp. Pinned so nobody reads it as evidence again."""
    shard = load_shard()
    rays = usable_rays(shard, n_rays=8)
    for _, radii in rays:
        assert run_ray(radii, REPORTING, scatter_voxels=0.0)["delta"] == pytest.approx(
            0.0, abs=1e-9
        )


def test_the_invariance_breaks_under_real_warps_once_scatter_is_present():
    """The actual finding of this probe, and the opposite of what its first
    version reported. Under the reporting configuration at 6 voxels of scatter,
    villa's entire scan tolerance, the empirical warps produce a delta far above
    the pinned smooth-sweep worst case of 0.042424, and the verdict differs on
    several rays."""
    shard = load_shard()
    rays = usable_rays(shard, n_rays=40)
    rows = [run_ray(radii, REPORTING, scatter_voxels=6.0) for _, radii in rays]
    assert max(abs(r["delta"]) for r in rows) > 0.2
    assert sum(1 for r in rows if r["ref_verdict"] != r["disp_verdict"]) >= 5


def test_the_break_is_monotone_in_scatter():
    """Guard against a one-off: the departure should grow with scatter, not
    appear at a single cherry-picked level."""
    shard = load_shard()
    rays = usable_rays(shard, n_rays=15)
    worst = [
        max(
            abs(run_ray(radii, REPORTING, scatter_voxels=vox)["delta"])
            for _, radii in rays
        )
        for vox in (0.0, 3.0, 6.0)
    ]
    assert worst[0] <= worst[1] <= worst[2]
    assert worst[2] > worst[0]
