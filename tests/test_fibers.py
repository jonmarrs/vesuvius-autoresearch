import numpy as np
import pytest
from conftest import (
    ambient_cuda_is_masked,
    gpu_available_ambiently,
    process_cuda_is_masked,
)

from vesuvius_autoresearch.fibers import (
    compute_eigenvalues_3x3_batch,
    detect_ridges,
    detect_ridges_tiled,
    detect_vesselness,
    detect_vesselness_tiled,
)


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


@pytest.mark.skipif(
    not gpu_available_ambiently(),
    reason="no CUDA device (absent, or masked by the shell)",
)
def test_cpu_gpu_vesselness_parity():
    """Real GPU/CPU parity. The guard is deliberately three-way.

    Guarding on `import cupy` succeeding was wrong: it succeeds with no device,
    so this FAILED instead of skipping under masking. Guarding on an in-process
    device count was wrong in the other direction -- evaluated at collection
    time, so importing a probe module first would skip this test on a perfectly
    good GPU, deleting the coverage with no signal. So: skip if the machine has
    no GPU, skip if the SHELL asked for CPU-only, and FAIL if the machine has a
    GPU and the shell did not mask it but something in-process did. That is
    contamination, not a reason to go quiet.
    """
    if ambient_cuda_is_masked():
        pytest.skip("shell set CUDA_VISIBLE_DEVICES=''")
    if process_cuda_is_masked():
        pytest.fail(
            "CUDA was masked in-process by an unrelated test module; this test "
            "must not silently skip on a machine that has a GPU"
        )

    import cupy as cp  # imported here: at module scope it runs with no device

    rng = np.random.default_rng(42)
    vol = rng.random((32, 32, 32)).astype(np.float32)
    res_np = detect_vesselness(vol)
    res_cp = detect_vesselness(cp.asarray(vol))
    np.testing.assert_allclose(res_np, cp.asnumpy(res_cp), rtol=1e-3, atol=1e-4)
