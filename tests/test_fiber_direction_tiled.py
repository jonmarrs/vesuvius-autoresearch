"""fiber_direction_tiled must equal the dense fiber_direction(hessian(...)) exactly, not approximately.

The tracer walks these directions step by step, so a last-bit difference can move a walk and change a score. The 512^3
ScrollGT cubes can only be traced in blocks (the dense path needs ~30 GB), and their scores are only comparable with the
256^3 cubes' if blocking changes nothing.
"""

from __future__ import annotations

import numpy as np
import pytest

from vesuvius_autoresearch.fibers.detection import (
    detect_ridges,
    detect_ridges_tiled,
    detect_vesselness,
    detect_vesselness_tiled,
    fiber_direction,
    fiber_direction_tiled,
    hessian,
)


def _volume(shape, seed=0):
    rng = np.random.default_rng(seed)
    v = rng.random(shape).astype(np.float32)
    v[shape[0] // 3, :, :] += 2.0  # a bright sheet, so the field has structure
    return v


@pytest.mark.parametrize(
    "shape, block", [((40, 40, 40), 16), ((37, 50, 29), 16), ((48, 48, 48), 48)]
)
def test_tiled_directions_equal_dense_exactly(shape, block):
    v = _volume(shape)
    J, _ = hessian(v.copy(), gauss_sigma=2, sigma=3)
    d_dense, ok_dense = fiber_direction(J)
    d_tiled, ok_tiled = fiber_direction_tiled(
        v, gauss_sigma=2, sigma=3, block_size=block, halo=16
    )
    assert d_tiled.shape == d_dense.shape and d_tiled.dtype == d_dense.dtype
    assert np.array_equal(ok_tiled, ok_dense)
    assert np.array_equal(d_tiled, d_dense, equal_nan=True)


def test_the_trace_paths_vesselness_settings_tile_exactly_too():
    v = _volume((40, 44, 36), seed=1)
    dense = np.asarray(detect_vesselness(v.copy(), gauss_sigma=1, sigma=2), dtype=float)
    tiled = np.asarray(
        detect_vesselness_tiled(
            v.copy(), block_size=16, halo=16, gauss_sigma=1, sigma=2
        ),
        dtype=float,
    )
    assert np.array_equal(tiled, dense, equal_nan=True)


def test_too_small_a_halo_is_refused():
    with pytest.raises(ValueError, match="halo must be"):
        fiber_direction_tiled(
            _volume((20, 20, 20)), gauss_sigma=2, sigma=3, block_size=8, halo=4
        )


@pytest.mark.parametrize(
    "shape", [(17, 16, 18), (16, 17, 18), (16, 18, 17), (17, 17, 17)]
)
@pytest.mark.parametrize("gauss_sigma", [0, 1, 2])
@pytest.mark.parametrize("dtype", [np.float32, np.float64])
def test_minimum_halo_matches_dense_at_singleton_boundary_tiles(
    shape, gauss_sigma, dtype
):
    volume = np.random.default_rng(2026).random(shape).astype(dtype)
    halo = int(4 * gauss_sigma + 0.5) + 2
    for dense_fn, tiled_fn in (
        (detect_ridges, detect_ridges_tiled),
        (detect_vesselness, detect_vesselness_tiled),
    ):
        dense = dense_fn(volume.copy(), gauss_sigma=gauss_sigma)
        tiled = tiled_fn(
            volume.copy(), block_size=8, halo=halo, gauss_sigma=gauss_sigma
        )
        np.testing.assert_array_equal(tiled, dense)

    dense_directions, dense_valid = fiber_direction(
        hessian(volume.copy(), gauss_sigma=gauss_sigma)[0]
    )
    tiled_directions, tiled_valid = fiber_direction_tiled(
        volume, block_size=8, halo=halo, gauss_sigma=gauss_sigma
    )
    np.testing.assert_array_equal(tiled_valid, dense_valid)
    np.testing.assert_array_equal(tiled_directions, dense_directions)


def test_one_voxel_blocks_match_dense_at_both_physical_faces():
    volume = np.random.default_rng(2026).random((5, 6, 7))
    dense = detect_vesselness(volume.copy(), gauss_sigma=0)
    tiled = detect_vesselness_tiled(volume.copy(), block_size=1, halo=2, gauss_sigma=0)
    np.testing.assert_array_equal(tiled, dense)
    dense_directions, dense_valid = fiber_direction(
        hessian(volume.copy(), gauss_sigma=0)[0]
    )
    tiled_directions, tiled_valid = fiber_direction_tiled(
        volume, gauss_sigma=0, block_size=1, halo=2
    )
    np.testing.assert_array_equal(tiled_valid, dense_valid)
    np.testing.assert_array_equal(tiled_directions, dense_directions)
