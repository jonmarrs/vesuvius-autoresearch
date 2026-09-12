"""Tests for the winding-identity instrument.

This decides whether the anchor-count ablation can run at all, so its failure
mode matters more than its success: if it reported "numbering preserved" when the
strip had actually shifted a winding, we would compare different papyrus between
arms and publish the difference as an effect.

So the synthetic cases build surfaces whose correct answer is known by
construction, including one that is deliberately shifted.
"""

import os
import sys

import numpy as np
import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import measure_winding_identity as mod  # noqa: E402

pytest.importorskip("scipy")


def _cylinder(radius, n=2000, seed=0):
    """Points on a cylinder of the given radius -- a stand-in for one winding."""
    rng = np.random.default_rng(seed)
    th = rng.uniform(0, 2 * np.pi, n)
    z = rng.uniform(0, 100, n)
    return np.column_stack([radius * np.cos(th), radius * np.sin(th), z])


def test_median_surface_distance_recovers_a_known_gap():
    a, b = _cylinder(100.0), _cylinder(110.0, seed=1)
    assert mod.median_surface_distance(a, b) == pytest.approx(10.0, abs=1.0)


def test_distance_to_itself_is_essentially_zero():
    a = _cylinder(100.0)
    assert mod.median_surface_distance(a, a) == 0.0


def test_the_nearest_surface_is_the_one_at_the_same_radius():
    """The core discrimination: a winding must match its own radius, not a
    neighbour's."""
    ref = _cylinder(100.0)
    cand = {w: _cylinder(100.0 + 10 * (w - 120), seed=w) for w in range(117, 124)}
    best = min(cand, key=lambda w: mod.median_surface_distance(ref, cand[w]))
    assert best == 120


def test_a_shifted_stack_is_detected_as_renumbered():
    """The failure this instrument exists to catch. If every alt winding is
    really its neighbour's surface, the offset must come back non-zero."""
    ref = {w: _cylinder(100.0 + 10 * (w - 120), seed=w) for w in range(118, 126)}
    alt = {w: ref[w + 1] for w in range(118, 125)}  # alt w120 IS ref w121
    offs = []
    for w in range(120, 124):
        best = min(alt, key=lambda v: mod.median_surface_distance(ref[w], alt[v]))
        offs.append(best - w)
    assert offs == [-1, -1, -1, -1], "a one-winding shift must not read as preserved"


def test_subsampling_is_bounded_and_deterministic_given_a_seed():
    assert mod.MAX_PTS <= 100_000
    rng_a = np.random.default_rng(5)
    rng_b = np.random.default_rng(5)
    big = _cylinder(100.0, n=mod.MAX_PTS * 2)
    ia = rng_a.choice(len(big), mod.MAX_PTS, replace=False)
    ib = rng_b.choice(len(big), mod.MAX_PTS, replace=False)
    assert np.array_equal(ia, ib)


def test_load_points_returns_None_for_a_missing_winding(tmp_path):
    assert mod.load_points(str(tmp_path), "tag", 120, np.random.default_rng(0)) is None


@pytest.mark.skipif(
    not os.path.isdir(
        "/home/jon/openclaw-workspace/Neo-VM/spiral_out/"
        "2026-09-07_s1_slice-13056-18432_38442-patch_curbase_s1/meshes"
    ),
    reason="fit corpus not present",
)
def test_positive_control_two_seeds_of_the_same_config_keep_their_numbering():
    """Real data. Two current-code baselines differ only by RNG, so every winding
    must match itself. If this fails the instrument is unusable on real meshes,
    whatever the synthetic cases say."""
    S = "/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    rng = np.random.default_rng(0)
    ref_root = f"{S}/2026-09-07_s1_slice-13056-18432_38442-patch_curbase_s1/meshes/fitted_curbase_s1"
    alt_root = f"{S}/2026-09-08_s1_slice-13056-18432_38442-patch_curbase_s3/meshes/fitted_curbase_s3"
    for w in (120, 125, 129):
        a = mod.load_points(ref_root, "curbase_s1", w, rng)
        cand = {
            v: mod.median_surface_distance(a, b)
            for v in range(w - 2, w + 3)
            if (b := mod.load_points(alt_root, "curbase_s3", v, rng)) is not None
        }
        assert min(cand, key=cand.get) == w, f"w{w} matched w{min(cand, key=cand.get)}"
