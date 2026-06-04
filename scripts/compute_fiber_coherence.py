#!/usr/bin/env python3
"""
Utility to compute Fiber Coherence using Villa Structure Tensor tools.
"""

import os
import sys
from pathlib import Path

import numpy as np
import torch
import zarr

# Add villa paths
VILLA_SRC = os.path.abspath("villa/vesuvius/src")
if VILLA_SRC not in sys.path:
    sys.path.append(VILLA_SRC)

try:
    from vesuvius.image_proc.geometry.structure_tensor import (
        StructureTensorComputer,
        _ensure_tensor,
    )
except ImportError as e:
    print(f"Error: Could not import Villa structure tensor modules: {e}")
    sys.exit(1)


def compute_coherence(volume_data, sigma=1.0, device="cuda"):
    """
    Computes a coherence score for the given 3D volume data.
    Coherence is based on the fractional anisotropy of the structure tensor.
    """
    computer = StructureTensorComputer(sigma=sigma)
    volume_tensor = _ensure_tensor(
        volume_data, device=torch.device(device), dtype=torch.float32
    )

    # Structure tensor components: [B, 6, Z, H, W]
    if volume_tensor.dim() == 3:
        volume_tensor = volume_tensor.unsqueeze(0).unsqueeze(0)
    elif volume_tensor.dim() == 4:
        volume_tensor = volume_tensor.unsqueeze(0)

    st_components = computer.compute_st(volume_tensor)

    # Derived quantities (eigenvalues)
    # mats: [B, Z, H, W, 3, 3]
    from vesuvius.image_proc.geometry.structure_tensor import (
        _components_to_matrix_structure,
    )

    mats = _components_to_matrix_structure(st_components, computer.layout)

    # Compute eigenvalues
    evals, _ = torch.linalg.eigh(mats)
    # evals: [B, Z, H, W, 3] sorted ascending
    l1 = evals[..., 2]
    l2 = evals[..., 1]
    l3 = evals[..., 0]

    # Fractional Anisotropy (FA)
    # Measures how much the tensor is dominated by one direction (fibers)
    numerator = torch.sqrt((l1 - l2) ** 2 + (l2 - l3) ** 2 + (l3 - l1) ** 2)
    denominator = torch.sqrt(l1**2 + l2**2 + l3**2) + 1e-8
    fa = (1.0 / np.sqrt(2.0)) * (numerator / denominator)

    return float(fa.mean().cpu().item())


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
