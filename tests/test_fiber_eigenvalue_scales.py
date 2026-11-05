"""Curvature eigenvalues must scale with the Hessian, without a fixed floor."""

import numpy as np
import pytest

from vesuvius_autoresearch.fibers import detection


@pytest.mark.parametrize("dtype", [np.float32, np.float64])
@pytest.mark.parametrize("scale", [0, 1e-12, 1e-7, 1e-5, 1, 1e12])
def test_diagonal_spectra_are_exact(dtype, scale):
    diagonal = np.array(
        [[0, 0, 0], [1, 1, 1], [-1, -1, 0.01], [-1, 0.01, 0.01]], dtype=dtype
    ) * dtype(scale)
    matrices = diagonal[..., None] * np.eye(3, dtype=dtype)
    before = matrices.copy()
    with np.errstate(all="raise"):
        actual = detection.compute_eigenvalues_3x3_batch(matrices)
    np.testing.assert_array_equal(actual, np.sort(diagonal, axis=-1))
    np.testing.assert_array_equal(matrices, before)


@pytest.mark.parametrize("dtype", [np.float32, np.float64])
@pytest.mark.parametrize("scale", [1e-12, 1e-7, 1e-5, 1e-3, 1, 1e12])
def test_distinct_spectra_match_numpy_at_each_scale(dtype, scale):
    a = np.random.default_rng(4090).normal(size=(256, 3, 3)).astype(dtype)
    a = (a + a.swapaxes(-1, -2)) / dtype(2)
    a *= dtype(scale)
    reference = np.linalg.eigvalsh(a)
    actual = detection.compute_eigenvalues_3x3_batch(a)
    radius = np.max(np.abs(reference), axis=-1)
    error = np.max(np.abs(actual - reference), axis=-1) / radius
    assert np.max(error) < (8e-6 if dtype == np.float32 else 2e-13)
    margin = 128 * np.finfo(dtype).eps * radius[..., None]
    robust = np.abs(reference) > margin
    np.testing.assert_array_equal(actual[robust] > 0, reference[robust] > 0)


# Without the max-component scaling, centering and the cubic still stay finite at 1e±150; the squares of
# 1e±200 entries overflow or underflow, so only those scales reach the normalization this test is named for.
@pytest.mark.parametrize("scale", [1e-200, 1e-150, 1e150, 1e200])
def test_normalization_avoids_intermediate_underflow_and_overflow(scale):
    a = np.array([[1, 0.2, -0.3], [0.2, -2, 0.4], [-0.3, 0.4, 0.5]])
    with np.errstate(all="raise"):
        actual = detection.compute_eigenvalues_3x3_batch(a * scale)
    np.testing.assert_allclose(actual / scale, np.linalg.eigvalsh(a), rtol=1e-13)


@pytest.mark.parametrize("dtype", [np.float32, np.float64])
@pytest.mark.parametrize("gap", [0, 1e-4])
def test_rotated_repeated_or_nearly_repeated_spectra(dtype, gap):
    q, _ = np.linalg.qr(np.random.default_rng(4090).normal(size=(128, 3, 3)))
    a = ((q * np.array([1, 1 + gap, 2])) @ q.swapaxes(-1, -2)).astype(dtype)
    actual = detection.compute_eigenvalues_3x3_batch(a)
    reference = np.linalg.eigvalsh(a)
    error = np.max(np.abs(actual - reference), axis=-1)
    radius = np.max(np.abs(reference), axis=-1)
    # Trigonometric roots lose accuracy near a double root; use a norm-scaled
    # bound rather than claiming the distinct-root tolerance applies there.
    assert np.max(error / radius) < 4 * np.sqrt(np.finfo(dtype).eps)


def test_small_departure_from_isotropy_is_not_lost_to_trace_cancellation():
    a = np.full((3, 3), 1e-5)
    np.fill_diagonal(a, 1.0)
    actual = detection.compute_eigenvalues_3x3_batch(a)
    np.testing.assert_allclose(actual, [0.99999, 0.99999, 1.00002], atol=2e-12, rtol=0)


def test_weak_saddle_does_not_pass_the_tube_curvature_gate():
    q, _ = np.linalg.qr(np.random.default_rng(4090).normal(size=(3, 3)))
    a = q @ np.diag([-1e-5, 1e-7, 1e-7]) @ q.T
    z, y, x = np.mgrid[-8:9, -8:9, -8:9]
    xyz = np.stack([x, y, z], axis=-1)
    volume = 0.5 + 0.5 * np.einsum("...i,ij,...j->...", xyz, a, xyz)
    # Pin the normalization range independently of the weak local curvatures.
    volume[0, 0, 0], volume[-1, -1, -1] = 0, 1
    hessian, _ = detection.hessian(volume, gauss_sigma=0, sigma=1)
    reference = np.linalg.eigvalsh(detection.symmetrize_upper(hessian[8, 8, 8]))
    assert reference[0] < 0 and np.all(reference[1:] > 0)
    # There is only one negative curvature; Frangi's tube gate must suppress it.
    actual = detection.detect_vesselness(volume, gauss_sigma=0, sigma=1)
    assert actual[8, 8, 8] == 0


def test_only_the_upper_triangle_defines_the_symmetric_problem():
    a = np.array([[2e-7, 3e-8, -1e-8], [3e-8, -1e-7, 2e-8], [-1e-8, 2e-8, 4e-7]])
    reference = np.linalg.eigvalsh(a)
    a[np.tril_indices(3, -1)] = np.nan
    actual = detection.compute_eigenvalues_3x3_batch(a)
    np.testing.assert_allclose(actual, reference, atol=1e-20, rtol=1e-13)
