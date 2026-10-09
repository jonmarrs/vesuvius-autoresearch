"""fiber_direction_tiled must equal the dense fiber_direction(hessian(...)) exactly, not approximately.

The tracer walks these directions step by step, so a last-bit difference can move a walk and change a score. The 512^3
ScrollGT cubes can only be traced in blocks (the dense path needs ~30 GB), and their scores are only comparable with the
256^3 cubes' if blocking changes nothing.
"""

from __future__ import annotations

import numpy as np
import pytest

from vesuvius_autoresearch.fibers.detection import (
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
