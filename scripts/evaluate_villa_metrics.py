#!/usr/bin/env python3
"""
Evaluate two Zarr/TIFF volumes using official Villa topology-aware metrics.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch
import zarr

# Add villa paths
VILLA_SRC = os.path.abspath("villa/segmentation/evaluation")
if VILLA_SRC not in sys.path:
    sys.path.append(VILLA_SRC)

try:
    from metrics.centerline_dice import compute as compute_centerline_dice
    from metrics.connected_components import compute as compute_cc
    from metrics.critical_components import compute as compute_crit
    from metrics.dice import compute as compute_dice
    from metrics.skeleton_distance_length import compute as compute_skel_dist
except ImportError as e:
    print(f"Error importing Villa metrics: {e}")
    print(
        "Ensure villa submodule is present and PYTHONPATH includes villa/segmentation/evaluation"
    )


def load_volume(path):
    path = str(path)
    if path.endswith(".zarr") or os.path.isdir(path):
        z = zarr.open(path, mode="r")
        if hasattr(z, "0"):
            return np.array(z["0"])
        return np.array(z)
    elif path.endswith((".tif", ".tiff")):
        import tifffile

        return tifffile.imread(path)
    else:
        raise ValueError(f"Unsupported file format: {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate Villa metrics on two volumes."
    )
    parser.add_argument(
        "--gt", required=True, help="Path to ground truth volume (Zarr or TIFF)"
    )
    parser.add_argument(
        "--pred", required=True, help="Path to prediction volume (Zarr or TIFF)"
    )
    parser.add_argument(
        "--threshold", type=float, default=0.5, help="Threshold for hard labels"
    )
    parser.add_argument("--out", help="Path to save results as JSON")
    args = parser.parse_args()

    print(f"Loading Ground Truth: {args.gt}")
    gt = load_volume(args.gt)
    print(f"Loading Prediction: {args.pred}")
    pred = load_volume(args.pred)

    if gt.shape != pred.shape:
        print(f"Warning: Shape mismatch! GT {gt.shape} vs Pred {pred.shape}")
        # Attempt to crop to smallest common shape
        min_shape = tuple(
            min(s1, s2) for s1, s2 in zip(gt.shape, pred.shape, strict=False)
        )
        gt = gt[: min_shape[0], : min_shape[1], : min_shape[2]]
        pred = pred[: min_shape[0], : min_shape[1], : min_shape[2]]
        print(f"Reshaped to: {gt.shape}")

    # Ensure binary for some metrics
    gt_bin = (gt > 0.5).astype(np.uint8)
    # If pred is float, it might be probs
    is_probs = np.issubdtype(pred.dtype, np.floating)
    pred_bin = (pred > args.threshold).astype(np.uint8)

    results = {}

    print("Computing Dice...")
    results["dice"] = compute_dice(torch.from_numpy(gt_bin), torch.from_numpy(pred))

    print("Computing Centerline Dice...")
    cd_res = compute_centerline_dice(gt_bin, pred_bin, tolerance_radius=3.0)
    results.update(cd_res)

    print("Computing Connected Components...")
    cc_res = compute_cc(gt_bin, pred_bin, num_classes=2, ignore_index=0)
    results.update(cc_res)

    print("Computing Critical Components...")
    try:
        crit_res = compute_crit(gt_bin, pred_bin)
        results.update(crit_res)
    except Exception as e:
        print(f"Critical components failed: {e}")

    print("Computing Skeleton Distance...")
    try:
        skel_res = compute_skel_dist(gt_bin, pred_bin)
        if isinstance(skel_res, dict):
            results.update(skel_res)
        else:
            results["skeleton_distance"] = float(skel_res)
    except Exception as e:
        print(f"Skeleton distance failed: {e}")

    print("\n--- Evaluation Results ---")
    for k, v in results.items():
        print(f"{k:30}: {v}")

    if args.out:
        with open(args.out, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved results to {args.out}")


if __name__ == "__main__":
    main()
