"""Eigenvector / fiber-orientation primitive (August fiber-tracer step 1).

`compute_eigenvalues_3x3_batch` gives curvature magnitudes but no direction, so
a tracer cannot use it alone. These tests pin the eigenvector routine against
`numpy.linalg.eigh` and, more importantly, pin the *degenerate* behaviour: the
validity mask must be False rather than the code emitting an arbitrary unit
vector, because a tracer would follow such a vector straight off a fiber.
"""

import numpy as np
import pytest

from vesuvius_autoresearch.fibers import (
    compute_eigenvalues_3x3_batch,
    compute_eigenvectors_3x3_batch,
    fiber_direction,
    hessian,
    symmetrize_upper,
)


def _sym_batch(n, rng):
    A = rng.random((n, 3, 3))
    return (A + A.swapaxes(-1, -2)) / 2


def test_eigenvectors_match_numpy_up_to_sign():
    rng = np.random.default_rng(0)
    A = _sym_batch(200, rng)
    evals = compute_eigenvalues_3x3_batch(A)
    ref_w, ref_v = np.linalg.eigh(A)  # ascending, same order as ours

    for k in range(3):
        ours, valid = compute_eigenvectors_3x3_batch(A, evals, k)
        assert valid.all(), "random symmetric matrices should be non-degenerate"
        ref = ref_v[..., k]
        # Eigenvectors are defined up to sign; compare |cos| to 1.
        cos = np.abs(np.sum(ours * ref, axis=-1))
        np.testing.assert_allclose(cos, np.ones_like(cos), rtol=0, atol=1e-5)


def test_eigenvectors_are_unit_and_orthogonal():
    rng = np.random.default_rng(1)
    A = _sym_batch(100, rng)
    evals = compute_eigenvalues_3x3_batch(A)
    vs = [compute_eigenvectors_3x3_batch(A, evals, k)[0] for k in range(3)]

    for v in vs:
        np.testing.assert_allclose(np.linalg.norm(v, axis=-1), 1.0, atol=1e-6)
    for i, j in [(0, 1), (0, 2), (1, 2)]:
        dot = np.sum(vs[i] * vs[j], axis=-1)
        np.testing.assert_allclose(dot, np.zeros_like(dot), atol=1e-5)


def test_eigenvector_satisfies_defining_equation():
    """A v = lambda v is the property a tracer actually depends on."""
    rng = np.random.default_rng(2)
    A = _sym_batch(64, rng)
    evals = compute_eigenvalues_3x3_batch(A)
    for k in range(3):
        v, _ = compute_eigenvectors_3x3_batch(A, evals, k)
        Av = np.einsum("nij,nj->ni", A, v)
        lv = evals[..., k][:, None] * v
        np.testing.assert_allclose(Av, lv, atol=1e-5)


def test_isotropic_input_is_marked_invalid_not_arbitrary():
    """Identity-like Hessians have no unique eigenvector: mask must be False."""
    A = np.broadcast_to(np.eye(3), (32, 3, 3)).copy()
    evals = compute_eigenvalues_3x3_batch(A)
    for k in range(3):
        v, valid = compute_eigenvectors_3x3_batch(A, evals, k)
        assert not valid.any(), "repeated eigenvalues must not report a direction"
        assert np.all(v == 0.0), "invalid voxels must be zero, not arbitrary"
        assert np.isfinite(v).all(), "must not emit NaN"


def test_zero_matrix_does_not_nan():
    A = np.zeros((16, 3, 3))
    evals = compute_eigenvalues_3x3_batch(A)
    v, valid = compute_eigenvectors_3x3_batch(A, evals, 0)
    assert not valid.any()
    assert np.isfinite(v).all()


def test_upper_triangular_input_matches_full_symmetric():
    """`hessian()` emits only the upper triangle; both forms must agree."""
    rng = np.random.default_rng(3)
    full = _sym_batch(48, rng)
    upper = full.copy()
    upper[..., 1, 0] = 0.0
    upper[..., 2, 0] = 0.0
    upper[..., 2, 1] = 0.0

    np.testing.assert_allclose(symmetrize_upper(upper), full, atol=0)
    e_full = compute_eigenvalues_3x3_batch(full)
    e_up = compute_eigenvalues_3x3_batch(upper)
    np.testing.assert_allclose(e_full, e_up, atol=1e-12)

    for k in range(3):
        vf, _ = compute_eigenvectors_3x3_batch(full, e_full, k)
        vu, _ = compute_eigenvectors_3x3_batch(upper, e_up, k)
        cos = np.abs(np.sum(vf * vu, axis=-1))
        np.testing.assert_allclose(cos, np.ones_like(cos), atol=1e-6)


def test_fiber_direction_returns_zyx_order():
    """`fiber_direction` must return (z, y, x), not `hessian()`'s (x, y, z).

    Regression test for a real bug: the raw eigenvector is in the Hessian's
    matrix order (0<->x, 1<->y, 2<->z), so returning it unreversed made the
    tracer step along z while following a fiber that ran along x. It looked
    plausible and produced zero fibers.
    """
    n = 48
    vol = np.zeros((n, n, n), dtype=float)
    zz, yy = np.mgrid[0:n, 0:n]
    disc = (zz - n // 2) ** 2 + (yy - n // 2) ** 2 <= 3.0**2
    vol[disc, :] = 1.0  # tube along axis 2 (x)

    J, _ = hessian(vol, gauss_sigma=1, sigma=2)
    dirs, valid = fiber_direction(J)

    core = np.zeros((n, n, n), dtype=bool)
    core[disc, :] = True
    core[:, :, : n // 4] = False
    core[:, :, -n // 4 :] = False
    sel = core & valid
    assert sel.sum() > 100

    # In (z, y, x) the tube tangent is the LAST component.
    assert np.median(np.abs(dirs[sel][:, 2])) > 0.95
    assert np.median(np.abs(dirs[sel][:, 0])) < 0.2

    # It is exactly the reverse of the raw eigenvector for the smallest-|lambda|
    # index. Note the index is chosen per voxel, so it is not a fixed 2.
    evals = compute_eigenvalues_3x3_batch(J)
    idx = np.argmin(np.abs(evals), axis=-1)
    raw = np.stack(
        [compute_eigenvectors_3x3_batch(J, evals, k)[0] for k in range(3)], axis=-2
    )
    chosen = np.take_along_axis(raw, idx[..., None, None], axis=-2)[..., 0, :]
    np.testing.assert_allclose(dirs[sel], chosen[sel][:, ::-1], atol=1e-12)


def test_fiber_direction_recovers_a_synthetic_tube_axis():
    """A bright cylinder along x must yield a tangent parallel to x.

    End-to-end contract: raw volume -> hessian -> direction. The returned vector
    is (z, y, x), so the x component is index 2.
    """
    n = 48
    vol = np.zeros((n, n, n), dtype=float)
    zz, yy = np.mgrid[0:n, 0:n]
    r2 = (zz - n // 2) ** 2 + (yy - n // 2) ** 2
    disc = r2 <= 3.0**2
    vol[disc, :] = 1.0  # constant along axis 2 (x)

    J, _ = hessian(vol, gauss_sigma=1, sigma=2)
    dirs, valid = fiber_direction(J)

    # Sample the tube core, away from the volume edges.
    core = np.zeros((n, n, n), dtype=bool)
    core[disc, :] = True
    core[:, :, : n // 4] = False
    core[:, :, -n // 4 :] = False
    sel = core & valid
    assert sel.sum() > 100, "expected a usable number of valid core voxels"

    ax = np.abs(dirs[sel][:, 2])  # x-component, last in (z, y, x)
    assert np.median(ax) > 0.95, (
        f"tangent not along the tube axis (median |x|={np.median(ax):.3f})"
    )


@pytest.mark.parametrize("index", [0, 1, 2])
def test_shapes_and_dtypes(index):
    rng = np.random.default_rng(4)
    A = _sym_batch(10, rng)
    evals = compute_eigenvalues_3x3_batch(A)
    v, valid = compute_eigenvectors_3x3_batch(A, evals, index)
    assert v.shape == (10, 3)
    assert valid.shape == (10,)
    assert valid.dtype == np.bool_
