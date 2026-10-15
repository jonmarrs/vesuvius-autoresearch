"""Frangi vesselness in torch, batched, on whatever device the batch is on.

The same filter as vesuvius_loader.frangi_vesselness_zcollapsed (skimage
0.25's ``frangi(sigmas=(sigma,), black_ridges=False)``, then the mean over z),
for a batch of [Z, H, W] patches at once:

* the Hessian from two first-order Gaussian derivative filters of sigma/sqrt(2)
  each, truncated at 8 standard deviations, with scipy's 'reflect' edges
  (``skimage.feature.hessian_matrix(..., use_gaussian_derivatives=True)``);
* everything in float64: on a GPU, cuDNN runs float32 convolutions in TF32
  (a 10-bit mantissa) by default, and the Hessian's ratios would lose it;
* its eigenvalues in closed form, so no cuSolver call: the villa
  backend's CuPy eigvalsh is what made the original GPU target fail (the
  NumPy/CuPy fibers.detection.compute_eigenvalues_3x3_batch avoids it the same
  way; this is the torch version, for batches already on the training device);
* eigenvalues ordered by magnitude, ties kept in descending order as numpy's
  stable small-array argsort keeps them; gamma is half of each patch's own
  largest Hessian norm.

tests/test_frangi_torch.py checks it against skimage, patch by patch.
"""

import math
from itertools import combinations_with_replacement

import torch
import torch.nn.functional as F

TRUNCATE = 8.0  # skimage's _hessian_matrix_with_gaussian, for sigma > 1


def _gaussian_kernel(sigma: float, order: int, radius: int) -> torch.Tensor:
    """scipy.ndimage's 1D Gaussian (order 0) or its derivative (order 1), as the
    correlation weights gaussian_filter1d applies (the kernel reversed)."""
    x = torch.arange(-radius, radius + 1, dtype=torch.float64)
    phi = torch.exp(-0.5 * x**2 / sigma**2)
    phi = phi / phi.sum()
    kernel = phi if order == 0 else -x / sigma**2 * phi
    return kernel.flip(0)


def _reflect_index(n: int, radius: int, device) -> torch.Tensor:
    """scipy's 'reflect' (d c b a | a b c d | d c b a) indices of an axis of
    length n padded by radius on each side."""
    idx = torch.arange(-radius, n + radius, device=device) % (2 * n)
    return torch.where(idx >= n, 2 * n - 1 - idx, idx)


def _filter_axis(
    volume: torch.Tensor, weights: torch.Tensor, axis: int
) -> torch.Tensor:
    radius = (weights.numel() - 1) // 2
    moved = volume.movedim(axis, -1)
    shape = moved.shape
    padded = moved.index_select(-1, _reflect_index(shape[-1], radius, volume.device))
    out = F.conv1d(
        padded.reshape(-1, 1, padded.shape[-1]),
        weights.to(volume.device, volume.dtype).view(1, 1, -1),
    )
    return out.reshape(shape).movedim(-1, axis)


def _gaussian(volume: torch.Tensor, sigma: float, orders) -> torch.Tensor:
    """scipy.ndimage.gaussian_filter over the last three axes, with per-axis
    derivative orders, applied axis by axis in order."""
    radius = int(TRUNCATE * sigma + 0.5)
    for axis, order in zip((-3, -2, -1), orders, strict=True):
        volume = _filter_axis(volume, _gaussian_kernel(sigma, order, radius), axis)
    return volume


def _eigenvalues_descending(a, b, c, d, e, f):
    """Eigenvalues of [[a, d, e], [d, b, f], [e, f, c]], largest first, in
    closed form (the trigonometric solution of the characteristic cubic)."""
    q = (a + b + c) / 3
    p1 = d**2 + e**2 + f**2
    p2 = (a - q) ** 2 + (b - q) ** 2 + (c - q) ** 2 + 2 * p1
    p = torch.sqrt(p2 / 6)
    safe = torch.where(p > 0, p, torch.ones_like(p))
    ba, bb, bc = (a - q) / safe, (b - q) / safe, (c - q) / safe
    bd, be, bf = d / safe, e / safe, f / safe
    det = ba * (bb * bc - bf * bf) - bd * (bd * bc - bf * be) + be * (bd * bf - bb * be)
    phi = torch.acos(torch.clamp(det / 2, -1.0, 1.0)) / 3
    largest = q + 2 * p * torch.cos(phi)
    smallest = q + 2 * p * torch.cos(phi + 2 * math.pi / 3)
    middle = 3 * q - largest - smallest
    return torch.stack([largest, middle, smallest])


def frangi_vesselness_zcollapsed_torch(
    ct: torch.Tensor, sigma: float = 2.0
) -> torch.Tensor:
    """Frangi vesselness of each [Z, H, W] patch of ct ([B, Z, H, W]) for bright
    ridges, at one scale, averaged over z: [B, H, W], float32. Autocast is off
    inside: in half precision the Hessian's ratios would be noise."""
    with torch.autocast(device_type=ct.device.type, enabled=False):
        return _frangi(ct, sigma)


def _frangi(ct: torch.Tensor, sigma: float) -> torch.Tensor:
    image = -ct.to(torch.float64)  # black_ridges=False: bright ridges
    scaled = sigma / math.sqrt(2)
    unit = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
    gradients = [_gaussian(image, scaled, unit[axis]) for axis in range(3)]
    hessian = {
        (i, j): _gaussian(gradients[i], scaled, unit[j])
        for i, j in combinations_with_replacement(range(3), 2)
    }
    eig = _eigenvalues_descending(
        hessian[0, 0], hessian[1, 1], hessian[2, 2],
        hessian[0, 1], hessian[0, 2], hessian[1, 2],
    )  # fmt: skip
    order = eig.abs().sort(dim=0, stable=True).indices
    eig = eig.gather(0, order)
    lambda1 = eig[0]
    lambda2, lambda3 = eig[1].clamp(min=1e-10), eig[2].clamp(min=1e-10)
    r_a = lambda2 / lambda3
    r_b = lambda1.abs() / torch.sqrt(lambda2 * lambda3)
    s = torch.sqrt((eig**2).sum(0))
    gamma = s.flatten(1).max(dim=1).values / 2  # each patch's own
    gamma = torch.where(gamma == 0, torch.ones_like(gamma), gamma).view(-1, 1, 1, 1)
    alpha = beta = 0.5
    vals = (1 - torch.exp(-(r_a**2) / (2 * alpha**2))) * torch.exp(
        -(r_b**2) / (2 * beta**2)
    )
    vals = vals * (1 - torch.exp(-(s**2) / (2 * gamma**2)))
    return torch.nan_to_num(vals.float()).mean(dim=1)
