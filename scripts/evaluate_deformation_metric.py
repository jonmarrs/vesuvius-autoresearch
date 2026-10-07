#!/usr/bin/env python3
"""Measure fractional anisotropy of stored structure tensors in bounded blocks.

FA describes local anisotropy, not neighborhood alignment or successful
registration. Rotation leaves FA unchanged; this command does not certify
flattening or a deformation correction.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import zarr

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.candidate_artifacts import (
    ARTIFACT_ERRORS,
    integer,
    spatial_blocks,
    write_json,
)

# Packed symmetric matrix order used by villa's StructureTensorComputer.
TENSOR_COMPONENTS = ("zz", "zy", "zx", "yy", "yx", "xx")


def compute_fractional_anisotropy(evals):
    values = np.asarray(evals, dtype=np.float64)
    if values.ndim == 0 or values.shape[-1] != 3:
        raise ValueError("eigenvalues must have a final dimension of three")
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("eigenvalues must be finite and nonnegative")
    scale = values.max(axis=-1, keepdims=True)
    values = np.divide(values, scale, out=np.zeros_like(values), where=scale > 0)
    numerator = (
        (values[..., 0] - values[..., 1]) ** 2
        + (values[..., 1] - values[..., 2]) ** 2
        + (values[..., 2] - values[..., 0]) ** 2
    )
    denominator = (values * values).sum(axis=-1)
    return np.sqrt(
        np.divide(
            0.5 * numerator,
            denominator,
            out=np.zeros_like(denominator),
            where=denominator > 0,
        )
    )


def tensor_fa(packed):
    packed = np.asarray(packed, dtype=np.float64)
    if packed.ndim != 4 or packed.shape[0] != 6 or not np.isfinite(packed).all():
        raise ValueError("tensor block must be finite with shape (6, z, y, x)")
    scale = np.max(np.abs(packed), axis=0)
    normalized = np.divide(
        packed, scale[None], out=np.zeros_like(packed), where=scale[None] > 0
    )
    matrix = np.empty((*packed.shape[1:], 3, 3), dtype=np.float64)
    matrix[..., 0, 0] = normalized[0]
    matrix[..., 0, 1] = matrix[..., 1, 0] = normalized[1]
    matrix[..., 0, 2] = matrix[..., 2, 0] = normalized[2]
    matrix[..., 1, 1] = normalized[3]
    matrix[..., 1, 2] = matrix[..., 2, 1] = normalized[4]
    matrix[..., 2, 2] = normalized[5]
    eigenvalues = np.linalg.eigvalsh(matrix)
    if (eigenvalues < -1e-6).any():
        raise ValueError("structure tensors must be positive semidefinite")
    clipped = int((eigenvalues < 0).sum())
    return compute_fractional_anisotropy(np.maximum(eigenvalues, 0)), scale > 0, clipped


def measure_structure_tensor(path, subsample=1):
    step = integer(subsample, "subsample", 1)
    root = zarr.open(str(path), mode="r")
    if isinstance(root, zarr.Array):
        tensor, dataset = root, "."
    elif "structure_tensor" in root:
        tensor, dataset = root["structure_tensor"], "structure_tensor"
    elif "0" in root:
        tensor, dataset = root["0"], "0"
    else:
        raise ValueError(
            "Zarr group must contain structure_tensor or a 6-channel array at 0"
        )
    if (
        not isinstance(tensor, zarr.Array)
        or len(tensor.shape) != 4
        or tensor.shape[0] != 6
        or min(tensor.shape) <= 0
        or tensor.dtype.kind != "f"
    ):
        raise ValueError(
            "expected a floating structure tensor array of shape (6, z, y, x)"
        )
    count = nonzero = clipped = 0
    total = squared = informative_total = 0.0
    for selection in spatial_blocks(tensor.shape[1:], step=step):
        fa, informative, roundoff = tensor_fa(tensor[(slice(None), *selection)])
        count += fa.size
        nonzero += int(informative.sum())
        total += float(fa.sum())
        squared += float(np.square(fa).sum())
        informative_total += float(fa[informative].sum())
        clipped += roundoff
    mean = total / count
    return {
        "measurement_contract": 1,
        "source_path": str(Path(path).resolve()),
        "dataset": dataset,
        "shape_czyx": list(tensor.shape),
        "tensor_components": list(TENSOR_COMPONENTS),
        "subsample": step,
        "sampled_voxels": count,
        "nonzero_tensor_voxels": nonzero,
        "zero_tensor_voxels": count - nonzero,
        "mean_fa": mean,
        "std_fa": float(np.sqrt(max(0.0, squared / count - mean * mean))),
        "nonzero_mean_fa": informative_total / nonzero if nonzero else None,
        "negative_roundoff_eigenvalues_clipped": clipped,
        "interpretation": "Local tensor anisotropy; does not measure spatial coherence or certify deformation correction.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--st-zarr", required=True)
    parser.add_argument("--subsample", type=int, default=1)
    parser.add_argument("--output", help="Optional JSON report")
    args = parser.parse_args(argv)
    try:
        report = measure_structure_tensor(args.st_zarr, args.subsample)
        if args.output:
            write_json(args.output, report)
    except ARTIFACT_ERRORS as exc:
        parser.exit(1, f"Structure tensor measurement failed: {exc}\n")
    print(f"Mean FA: {report['mean_fa']:.4f} ± {report['std_fa']:.4f}")
    print(
        f"Sampled voxels: {report['sampled_voxels']}; zero tensors: {report['zero_tensor_voxels']}"
    )
    print(report["interpretation"])


if __name__ == "__main__":
    main()
