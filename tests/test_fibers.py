import numpy as np
import pytest
from conftest import gpu_is_available

from vesuvius_autoresearch.fibers import (
    compute_eigenvalues_3x3_batch,
    detect_ridges,
    detect_ridges_tiled,
    detect_vesselness,
    detect_vesselness_tiled,
)

# Guarding on the cupy import alone was not enough: cupy imports fine with no
# visible device, so the parity test FAILED rather than skipped whenever the
# GPU was masked -- a long-standing caveat that read as "not a regression".
HAS_CUPY = gpu_is_available()


def test_eigensolver_matches_numpy():
    rng = np.random.default_rng(0)
    A = rng.random((50, 3, 3)).astype(np.float64)
    A = (A + A.swapaxes(-1, -2)) / 2  # symmetric
    ours = np.asarray(compute_eigenvalues_3x3_batch(A))
    ref = np.linalg.eigvalsh(A)
    np.testing.assert_allclose(
        np.sort(ours, -1), np.sort(ref, -1), rtol=1e-4, atol=1e-6
    )


def test_vesselness_nonzero_and_finite():
    rng = np.random.default_rng(0)
    vol = rng.random((24, 32, 32)).astype(np.float32)
    out = detect_vesselness(vol)
    assert out.shape == vol.shape
    assert np.isfinite(out).all()
    assert float(np.abs(out).sum()) > 0.0


def test_tiled_matches_dense_vesselness():
    rng = np.random.default_rng(42)
    vol = rng.random((64, 64, 64)).astype(np.float32)
    dense = detect_vesselness(vol.copy())
    tiled = detect_vesselness_tiled(vol.copy(), block_size=32, halo=16)
    np.testing.assert_allclose(dense, tiled, rtol=1e-3, atol=1e-4)


def test_constant_volume_is_finite():
    # Blank CT regions (constant/all-zero patches) must not produce NaN ridges:
    # normalize() would otherwise divide by (max - min) == 0.
    zeros = np.zeros((16, 32, 32), dtype=np.float32)
    rid = detect_ridges(zeros.copy())
    ves = detect_vesselness(zeros.copy())
    assert np.isfinite(rid).all() and np.isfinite(ves).all()
    const = np.full((16, 32, 32), 0.5, dtype=np.float32)
    assert np.isfinite(detect_ridges(const.copy())).all()


def test_tiled_matches_dense_ridges():
    rng = np.random.default_rng(7)
    vol = rng.random((64, 64, 64)).astype(np.float32)
    dense = detect_ridges(vol.copy())
    tiled = detect_ridges_tiled(vol.copy(), block_size=32, halo=16)
    np.testing.assert_allclose(dense, tiled, rtol=1e-3, atol=1e-4)


@pytest.mark.skipif(not HAS_CUPY, reason="no visible CUDA device")
def test_cpu_gpu_vesselness_parity():
    import cupy as cp  # imported here: at module scope it runs with no device

    rng = np.random.default_rng(42)
    vol = rng.random((32, 32, 32)).astype(np.float32)
    res_np = detect_vesselness(vol)
    res_cp = detect_vesselness(cp.asarray(vol))
    np.testing.assert_allclose(res_np, cp.asnumpy(res_cp), rtol=1e-3, atol=1e-4)
