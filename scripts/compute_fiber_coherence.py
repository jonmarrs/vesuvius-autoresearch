#!/usr/bin/env python3
"""
Utility to compute Fiber Coherence using Villa Structure Tensor tools.
"""

import math
import sys
from pathlib import Path

import numpy as np
import torch
import zarr

# Villa from this checkout, wherever the caller runs.
VILLA_SRC = str(Path(__file__).resolve().parents[1] / "villa" / "vesuvius" / "src")
if VILLA_SRC not in sys.path:
    sys.path.append(VILLA_SRC)

# An ImportError reaches the caller (predict.py reports it); this exited the
# whole process at import, after predict had written its outputs.
from vesuvius.image_proc.geometry.structure_tensor import (  # noqa: E402
    StructureTensorComputer,
    eigendecompose,
)


def compute_coherence(volume_data, sigma=1.0, device="cuda", integration=3.0):
    """Mean fractional anisotropy of the structure tensor of volume_data: near 1
    where the gradients share one direction (fibres, sheets), lower where they
    have none (noise). A 2-D slice (what predict.py passes) gives two
    eigenvalues, a 3-D block three; FA = sqrt(n / (n - 1)) * |l - mean(l)| / |l|
    covers both, and for three it is the usual formula.

    The tensor is villa's (StructureTensorComputer.compute, eigendecompose),
    with its components smoothed at ``integration`` times the gradient scale.
    Unsmoothed, each pixel's tensor is one gradient's outer product, rank 1, so
    its FA is 1 everywhere, noise included. This used to call compute_st and
    layout, which villa's computer does not have, so it never returned.

    Reflect enough context for all three filters, then retain only the input
    field. Villa's internal zero padding otherwise creates coherent crop edges.
    Both filter scales must be finite and positive.
    """
    data = np.asarray(volume_data, dtype=np.float64)
    if data.ndim not in (2, 3):
        raise ValueError(f"expected a 2-D slice or a 3-D block, not {data.ndim}-D")
    if not data.size or not np.isfinite(data).all():
        raise ValueError("volume must be nonempty and finite")
    sigma, integration = float(sigma), float(integration)
    for name, value in (("sigma", sigma), ("integration", integration)):
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
    component_sigma = integration * sigma
    if not math.isfinite(component_sigma):
        raise ValueError("sigma * integration must be finite")
    # Gaussian radii plus the pinned Villa derivative kernel's radius of four.
    halo = math.ceil(3 * sigma) + 4 + math.ceil(3 * component_sigma)
    # Removing a constant leaves gradients unchanged and avoids DC roundoff
    # when Villa subsequently computes derivatives in float32. Do not mutate data.
    centered = (data - data.mean()).astype(np.float32)
    volume = torch.as_tensor(np.pad(centered, halo, mode="reflect"))
    computer = StructureTensorComputer(
        sigma=sigma,
        component_sigma=component_sigma,
        smooth_components=True,
        device=device,
    )
    # Batch and channel first, so villa reads a 2-D slice as 2-D.
    components = computer.compute(volume[None, None])
    region = (slice(None), slice(None)) + tuple(
        slice(halo, halo + length) for length in data.shape
    )
    components = components[region]
    evals, _ = eigendecompose(components)
    evals = evals.clamp(min=0)  # positive semidefinite, up to rounding
    n = evals.shape[-1]
    spread = (evals - evals.mean(dim=-1, keepdim=True)).norm(dim=-1)
    fa = math.sqrt(n / (n - 1)) * spread / (evals.norm(dim=-1) + 1e-8)
    return float(fa.clamp(0, 1).mean().cpu())


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to Zarr volume")
    parser.add_argument("--sigma", type=float, default=1.0)
    args = parser.parse_args()

    z = zarr.open(args.input, mode="r")
    if hasattr(z, "0"):
        data = np.array(z["0"])
    else:
        data = np.array(z)

    score = compute_coherence(data, sigma=args.sigma)
    print(f"Fiber Coherence Score: {score:.6f}")


if __name__ == "__main__":
    main()
