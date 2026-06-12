"""GPU-native fiber / ridge / vesselness detection for scroll CT.

Vendored from the validated `sprint033-fibers-gpu` branch (proposed as
ScrollPrize/villa PR #1033). The closed-form symmetric-3x3 eigensolver
(`compute_eigenvalues_3x3_batch`) avoids the cuSolver `eigvalsh` failure on
large Hessian batches; `get_backend` dispatches per-array so the same functions
run on NumPy (CPU) or CuPy (GPU). Tiled variants process volumes larger than
VRAM with a halo, normalizing each block against the global smoothed range.
"""

import math

import numpy as np
from scipy import ndimage

try:
    import cupy as cp
    from cupyx.scipy import ndimage as cupy_ndimage

    HAS_CUPY = True
except ImportError:
    HAS_CUPY = False


def get_backend(volume):
    if HAS_CUPY and isinstance(volume, cp.ndarray):
        return cp, cupy_ndimage
    return np, ndimage


def divide_nonzero(array1, array2, eps=1e-10):
    """
    Divides two arrays. Returns zero when dividing by zero.
    """
    xp, _ = get_backend(array1)
    denominator = xp.copy(array2)
    denominator[denominator == 0] = eps
    return xp.divide(array1, denominator)


def normalize(volume, norm_range=None):
    """
    Min-max normalize in place. If norm_range is given as (min, max), use it
    instead of the volume's own extrema (needed for tiled execution, where each
    block must be normalized against the global range to match dense results).
    """
    xp, _ = get_backend(volume)
    if norm_range is None:
        minim = xp.min(volume)
        maxim = xp.max(volume)
    else:
        minim, maxim = norm_range
    volume -= minim
    volume /= maxim - minim
    return volume


def hessian(volume, gauss_sigma=2, sigma=6, norm_range=None):
    xp, xndimage = get_backend(volume)
    # N.B. this only returns the upper triangular matrix to save time
    volume = xndimage.gaussian_filter(volume, sigma=gauss_sigma)
    volume = normalize(volume, norm_range=norm_range)

    joint_hessian = xp.zeros(
        (volume.shape[0], volume.shape[1], volume.shape[2], 3, 3), dtype=float
    )

    Dz = xp.gradient(volume, axis=0, edge_order=2)
    joint_hessian[:, :, :, 2, 2] = xp.gradient(Dz, axis=0, edge_order=2)
    del Dz

    Dy = xp.gradient(volume, axis=1, edge_order=2)
    joint_hessian[:, :, :, 1, 1] = xp.gradient(Dy, axis=1, edge_order=2)
    joint_hessian[:, :, :, 1, 2] = xp.gradient(Dy, axis=0, edge_order=2)
    # joint_hessian[:, :, :, 2, 1] = joint_hessian[:, :, :, 1, 2]
    del Dy

    Dx = xp.gradient(volume, axis=2, edge_order=2)
    joint_hessian[:, :, :, 0, 0] = xp.gradient(Dx, axis=2, edge_order=2)
    joint_hessian[:, :, :, 0, 1] = xp.gradient(Dx, axis=1, edge_order=2)
    # joint_hessian[:, :, :, 1, 0] = joint_hessian[:, :, :, 0, 1]
    joint_hessian[:, :, :, 0, 2] = xp.gradient(Dx, axis=0, edge_order=2)
    # joint_hessian[:, :, :, 2, 0] = joint_hessian[:, :, :, 0, 2]
    del Dx

    joint_hessian = xp.multiply(sigma**2, joint_hessian)

    # zero_mask = (Dxx + Dyy + Dzz) == 0
    zero_mask = xp.trace(joint_hessian, axis1=3, axis2=4) == 0

    return joint_hessian, zero_mask


def compute_eigenvalues_3x3_batch(J):
    """
    Compute eigenvalues for batched 3x3 symmetric matrices using Cardano's analytical formula.
    Avoids CuPy's batched eigvalsh failure on large arrays (cuSolver errors).
    Works interchangeably with NumPy and CuPy via xp.
    Input: J of shape (..., 3, 3)
    Output: eigenvalues of shape (..., 3) in ascending order
    """
    xp, _ = get_backend(J)
    a11 = J[..., 0, 0]
    a22 = J[..., 1, 1]
    a33 = J[..., 2, 2]
    a12 = J[..., 0, 1]
    a13 = J[..., 0, 2]
    a23 = J[..., 1, 2]

    p1 = a11 + a22 + a33
    p2 = a11 * a22 + a11 * a33 + a22 * a33 - a12 * a12 - a13 * a13 - a23 * a23
    p3 = (
        a11 * (a22 * a33 - a23 * a23)
        - a12 * (a12 * a33 - a13 * a23)
        + a13 * (a12 * a23 - a13 * a22)
    )

    q = p1 * p1 / 9.0 - p2 / 3.0
    r = p1 * p1 * p1 / 27.0 - p1 * p2 / 6.0 + p3 / 2.0

    eps = 1e-12
    sqrt_q = xp.sqrt(xp.clip(q, a_min=eps, a_max=None))
    theta = xp.arccos(xp.clip(r / (sqrt_q**3 + eps), a_min=-1.0, a_max=1.0))

    sqrt_q_2 = 2.0 * sqrt_q
    p1_3 = p1 / 3.0

    lambda1 = p1_3 + sqrt_q_2 * xp.cos(theta / 3.0)
    lambda2 = p1_3 + sqrt_q_2 * xp.cos((theta - 2.0 * math.pi) / 3.0)
    lambda3 = p1_3 + sqrt_q_2 * xp.cos((theta - 4.0 * math.pi) / 3.0)

    eigenvalues = xp.stack([lambda1, lambda2, lambda3], axis=-1)
    eigenvalues = xp.sort(eigenvalues, axis=-1)
    return eigenvalues


def detect_ridges(
    volume, gamma=1.5, beta1=0.5, beta2=0.5, gauss_sigma=2, sigma=6, norm_range=None
):
    xp, _ = get_backend(volume)
    joint_hessian, zero_mask = hessian(
        volume, gauss_sigma, sigma, norm_range=norm_range
    )
    eigvals = compute_eigenvalues_3x3_batch(joint_hessian)
    # Sort in increasing size of the absolute value of the eigenvalues
    idxs = xp.argsort(xp.abs(eigvals), axis=-1)
    eigvals = xp.take_along_axis(eigvals, idxs, axis=-1)
    eigvals[zero_mask, :] = 0

    L1 = xp.abs(eigvals[:, :, :, 0])
    L2 = xp.abs(eigvals[:, :, :, 1])
    L3 = eigvals[:, :, :, 2]
    L3abs = xp.abs(L3)

    S = xp.sqrt(xp.square(eigvals).sum(axis=-1))
    background_term = 1 - xp.exp(-(0.5 * xp.square(S / gamma)))

    Ra = divide_nonzero(L2, L3abs)
    planar_term = xp.exp(-(0.5 * xp.square(Ra / beta1)))

    Rb = divide_nonzero(L1, xp.sqrt(xp.multiply(L2, L3abs)))
    blob_term = xp.exp(-(0.5 * xp.square(Rb / beta2)))

    ridges = background_term * planar_term * blob_term
    ridges[L3 > 0] = 0

    return ridges


def detect_vesselness(
    volume, gamma=1.5, beta1=0.5, beta2=0.5, gauss_sigma=2, sigma=6, norm_range=None
):
    """
    Detect vesselness using the Frangi filter.

    Parameters:
    - volume: 3D array representing the input volume.
    - gamma: Sensitivity to overall structure strength (controls suppression of background).
    - beta1: Controls sensitivity to tubular structures.
    - beta2: Controls sensitivity to blob-like structures.
    - gauss_sigma: Gaussian smoothing applied to the Hessian matrix.
    - sigma: Scale of differentiation for computing the Hessian.

    Returns:
    - vesselness: 3D array representing vesselness probability at each voxel.
    """
    xp, _ = get_backend(volume)
    joint_hessian, zero_mask = hessian(
        volume, gauss_sigma, sigma, norm_range=norm_range
    )
    eigvals = compute_eigenvalues_3x3_batch(joint_hessian)
    # Sort eigenvalues by magnitude (ascending order)
    idxs = xp.argsort(xp.abs(eigvals), axis=-1)
    eigvals = xp.take_along_axis(eigvals, idxs, axis=-1)
    eigvals[zero_mask, :] = 0  # Ignore zero regions

    # Extract eigenvalues
    L1 = eigvals[:, :, :, 0]
    L2 = eigvals[:, :, :, 1]
    L3 = eigvals[:, :, :, 2]

    # Compute terms for Frangi filter
    Ra = divide_nonzero(xp.abs(L2), xp.abs(L3))  # Tubularity ratio
    Rb = divide_nonzero(xp.abs(L1), xp.sqrt(xp.abs(L2 * L3)))  # Blobness ratio
    S = xp.sqrt(xp.square(eigvals).sum(axis=-1))  # Frobenius norm

    # Frangi vesselness components
    planar_term = 1 - xp.exp(-0.5 * xp.square(Ra / beta1))
    blob_term = xp.exp(-0.5 * xp.square(Rb / beta2))
    background_term = 1 - xp.exp(-0.5 * xp.square(S / gamma))

    # Combine terms
    vesselness = background_term * planar_term * blob_term

    # Suppress areas where L2 or L3 are positive (non-tubular regions)
    vesselness[L2 > 0] = 0
    vesselness[L3 > 0] = 0

    return vesselness


def _smoothed_global_range(volume, gauss_sigma, block_size, halo):
    """
    Min/max of the Gaussian-smoothed volume, computed tile-by-tile.
    Matches the dense path exactly when halo covers the filter support
    (truncate * gauss_sigma, i.e. 8 voxels for the default gauss_sigma=2).
    """
    xp, xndimage = get_backend(volume)
    Z, Y, X = volume.shape
    gmin, gmax = xp.inf, -xp.inf
    for z in range(0, Z, block_size):
        for y in range(0, Y, block_size):
            for x in range(0, X, block_size):
                z0, z1 = max(0, z - halo), min(Z, z + block_size + halo)
                y0, y1 = max(0, y - halo), min(Y, y + block_size + halo)
                x0, x1 = max(0, x - halo), min(X, x + block_size + halo)
                smoothed = xndimage.gaussian_filter(
                    volume[z0:z1, y0:y1, x0:x1], sigma=gauss_sigma
                )
                interior = smoothed[
                    z - z0 : z - z0 + min(block_size, Z - z),
                    y - y0 : y - y0 + min(block_size, Y - y),
                    x - x0 : x - x0 + min(block_size, X - x),
                ]
                gmin = min(gmin, float(interior.min()))
                gmax = max(gmax, float(interior.max()))
                if HAS_CUPY and isinstance(volume, cp.ndarray):
                    del smoothed
                    cp.get_default_memory_pool().free_all_blocks()
    return gmin, gmax


def _detect_tiled(volume, filter_fn, block_size=128, halo=16, **kwargs):
    """
    Run a volumetric filter in blocks with a halo to fit in GPU memory.
    Each block is processed with `halo` voxels of context on every side,
    then cropped back to the interior before write-back. A first pass
    computes the global normalization range of the smoothed volume so
    per-block normalization matches the dense path.
    """
    xp, _ = get_backend(volume)
    Z, Y, X = volume.shape
    result = xp.zeros((Z, Y, X), dtype=volume.dtype)

    if kwargs.get("norm_range") is None:
        gauss_sigma = kwargs.get("gauss_sigma", 2)
        kwargs["norm_range"] = _smoothed_global_range(
            volume, gauss_sigma, block_size, halo
        )

    for z in range(0, Z, block_size):
        for y in range(0, Y, block_size):
            for x in range(0, X, block_size):
                # Block coordinates with halo
                z0, z1 = max(0, z - halo), min(Z, z + block_size + halo)
                y0, y1 = max(0, y - halo), min(Y, y + block_size + halo)
                x0, x1 = max(0, x - halo), min(X, x + block_size + halo)

                block = volume[z0:z1, y0:y1, x0:x1]
                block_res = filter_fn(block, **kwargs)

                # Crop the halo off and write back the interior
                bz0 = z - z0
                bz1 = bz0 + min(block_size, Z - z)
                by0 = y - y0
                by1 = by0 + min(block_size, Y - y)
                bx0 = x - x0
                bx1 = bx0 + min(block_size, X - x)
                result[z : z + bz1 - bz0, y : y + by1 - by0, x : x + bx1 - bx0] = (
                    block_res[bz0:bz1, by0:by1, bx0:bx1]
                )

                # Free memory aggressively inside loop if using CuPy
                if HAS_CUPY and isinstance(volume, cp.ndarray):
                    del block
                    del block_res
                    cp.get_default_memory_pool().free_all_blocks()

    return result


def detect_ridges_tiled(volume, block_size=128, halo=16, **kwargs):
    """
    Run detect_ridges in blocks to fit in GPU memory.
    """
    return _detect_tiled(volume, detect_ridges, block_size, halo, **kwargs)


def detect_vesselness_tiled(volume, block_size=128, halo=16, **kwargs):
    """
    Run detect_vesselness in blocks to fit in GPU memory.
    """
    return _detect_tiled(volume, detect_vesselness, block_size, halo, **kwargs)
