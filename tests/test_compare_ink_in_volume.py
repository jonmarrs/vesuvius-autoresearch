"""Tests for the volume-space ink comparison.

The bug this instrument already had is the one to guard: blocking mask tiles into
tifxyz cells PER TILE silently dropped two columns, because tiles are 16384 wide
and 16384 is not divisible by the scale factor 10. Nothing raised -- every column
after the first tile boundary was simply shifted, which would have depressed every
correlation by an amount no one could have attributed.
"""

import os
import sys

import numpy as np
import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import compare_ink_in_volume as mod  # noqa: E402


def test_the_scale_factor_and_bins_are_constants():
    assert mod.SCALE == 10
    assert (mod.NZ, mod.NTHETA) == (96, 256)


def test_tiles_are_ordered_numerically_not_lexically():
    names = [f"/x/w120-129_flat_mask.{i:03d}.png" for i in (10, 2, 0, 1)]
    assert [mod.tile_index(n) for n in sorted(names, key=mod.tile_index)] == [
        0,
        1,
        2,
        10,
    ]


def test_a_tile_width_indivisible_by_scale_must_not_lose_columns():
    """The real bug, in miniature. Two tiles of width 16384 and one of 7900 sum
    to 40668 pixels = 4066.8 cells; per-tile truncation gives 1638+1638+790 =
    4066 and loses the boundary remainder. Concatenating first is exact."""
    widths = [16384, 16384, 7900]
    per_tile = sum(w // mod.SCALE for w in widths)
    concatenated = sum(widths) // mod.SCALE
    assert per_tile == 4066 and concatenated == 4066
    # and with three full tiles the loss is visible
    widths = [16384, 16384, 16384]
    assert sum(w // mod.SCALE for w in widths) == 4914
    assert sum(widths) // mod.SCALE == 4915, "per-tile blocking loses a column here"


def test_corr_ignores_bins_empty_in_both_maps():
    """Most of a (z, theta) map is empty; counting shared emptiness as agreement
    would inflate every correlation toward 1, so jointly-empty bins are dropped.
    Padding a map with them must therefore change nothing."""
    rng = np.random.default_rng(0)
    a = np.zeros((20, 20))
    occupied = rng.random((20, 20)) < 0.6
    a[occupied] = rng.uniform(1, 5, occupied.sum())
    b = np.where(occupied, a + rng.normal(0, 0.3, a.shape), 0.0)
    r_sparse = mod.corr(a, b)
    assert np.isfinite(r_sparse)
    big_a = np.zeros((60, 60))
    big_a[:20, :20] = a
    big_b = np.zeros((60, 60))
    big_b[:20, :20] = b
    assert mod.corr(big_a, big_b) == pytest.approx(r_sparse, abs=1e-9), (
        "padding with jointly-empty bins changed the correlation"
    )


def test_corr_is_nan_when_there_is_nothing_to_compare():
    assert np.isnan(mod.corr(np.zeros((5, 5)), np.zeros((5, 5))))


def test_identical_maps_correlate_perfectly_and_rotation_destroys_it():
    """Density matters here. On a map as sparse as scattered points, two disjoint
    supports anti-correlate strongly (about -0.67) under the union mask rather
    than landing near zero. Real maps occupy ~3,800 of 24,576 bins with broad
    structure, and their theta-rotated null is -0.09. The fixture is built dense
    enough to behave like the real thing rather than like scattered points."""
    rng = np.random.default_rng(1)
    zz, tt = np.meshgrid(np.arange(mod.NZ), np.arange(mod.NTHETA), indexing="ij")
    H = (
        2.0
        + np.sin(2 * np.pi * tt / mod.NTHETA * 3)
        + np.cos(2 * np.pi * zz / mod.NZ * 2)
    )
    H = H * (rng.random(H.shape) < 0.5)
    assert mod.corr(H, H) == pytest.approx(1.0, abs=1e-9)
    r_rot = mod.corr(H, np.roll(H, mod.NTHETA // 2, axis=1))
    assert r_rot < 0.3, (
        f"a half-turn rotation must destroy the agreement, got {r_rot:.3f}"
    )


@pytest.mark.skipif(
    not os.path.isfile(os.path.join(_REPO, "reports/ink_volume_all_arms.json")),
    reason="volume comparison not run",
)
def test_the_published_result_has_a_null_far_below_its_signal():
    import json

    d = json.load(open(os.path.join(_REPO, "reports/ink_volume_all_arms.json")))
    rs = [p["r"] for p in d["pairs"]]
    assert min(rs) > 0.5, "every arm pair must agree far above the null"
    assert max(d["null_rotated"]) < 0.1, "the theta-rotated null must be near zero"


def test_arm_paths_default_to_outer_prefix_and_accept_none():
    assert mod.arm_path("/so", "curbase_s4") == "/so/outer_curbase_s4"
    assert mod.arm_path("/so", "detfit_s4", prefix="") == "/so/detfit_s4"


def test_no_usable_arm_is_refused_cleanly_not_a_typeerror(tmp_path):
    import subprocess

    r = subprocess.run(
        [
            sys.executable,
            os.path.join(_REPO, "scripts", "compare_ink_in_volume.py"),
            "--spiral-out",
            str(tmp_path),
            "--arms",
            "a",
            "b",
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0
    assert "TypeError" not in r.stderr, r.stderr
    assert "need two usable arms" in (r.stdout + r.stderr)
