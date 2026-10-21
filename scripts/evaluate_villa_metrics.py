#!/usr/bin/env python3
"""
Evaluate two Zarr/TIFF volumes using official Villa topology-aware metrics.
"""

import argparse
import importlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch
import zarr

# Villa's metrics, found from this checkout rather than the working directory.
VILLA_SRC = str(Path(__file__).resolve().parents[1] / "villa/segmentation/evaluation")
if VILLA_SRC not in sys.path:
    sys.path.append(VILLA_SRC)

# The metrics every run reports. Without them, stop here: carrying on read both
# volumes and then failed on the first metric with a NameError.
try:
    from metrics.centerline_dice import compute as compute_centerline_dice
    from metrics.connected_components import compute as compute_cc
    from metrics.dice import compute as compute_dice
except ImportError as e:
    raise SystemExit(
        f"Error importing Villa metrics: {e}\n"
        f"Ensure the villa submodule is present ({VILLA_SRC}) with its dependencies"
    ) from e


def _optional_metric(module):
    """A metric main() reports when it can, as it does when one fails to compute:
    critical_components_multiclass needs cupy (a GPU), mean_ap sklearn,
    skeleton_distance_length kimimaro."""
    try:
        return importlib.import_module(f"metrics.{module}").compute
    except ImportError as e:
        print(f"Villa metric {module} unavailable: {e}")
        return None


compute_crit_mc = _optional_metric("critical_components_multiclass")
compute_dice_multiclass = _optional_metric("dice_multiclass")
compute_mean_ap = _optional_metric("mean_ap")
compute_skel_dist = _optional_metric("skeleton_distance_length")


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
    parser.add_argument(
        "--num_classes",
        type=int,
        default=2,
        help="Number of classes for multiclass metrics",
    )
    parser.add_argument(
        "--soft_pred",
        action="store_true",
        help="Use soft probability predictions (skip binarization for mean_ap)",
    )
    args = parser.parse_args()

    # villa's skeleton metric calls wandb.log, which raises without an active
    # run. This script never tracks, so start a disabled (no-op) one.
    try:
        import wandb

        if wandb.run is None:
            wandb.init(mode="disabled")
    except ImportError:
        pass  # villa's metric skips logging when wandb is absent

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
    # Villa gives a slice with no ground truth the whole slice as its tolerance region,
    # so every predicted skeleton pixel there counts as a hit (METHOD.md): count them.
    if gt_bin.ndim == 3:
        unlabelled = sum(
            1
            for z in range(gt_bin.shape[0])
            if pred_bin[z].any() and not gt_bin[z].any()
        )
        results["centerline_slices_predicted_without_ground_truth"] = unlabelled
        if unlabelled:
            print(
                f"Warning: {unlabelled} slices have a prediction and no ground truth; "
                "villa's centerline_dice counts their predicted skeleton as matching, "
                "which can raise it above 1"
            )

    print("Computing Connected Components...")
    cc_res = compute_cc(gt_bin, pred_bin, num_classes=2, ignore_index=0)
    results.update(cc_res)

    print("Computing Critical Components (Multiclass)...")
    try:
        if compute_crit_mc is None:
            raise RuntimeError("not imported")
        crit_mc_res = compute_crit_mc(gt_bin, pred_bin, num_classes=args.num_classes)
        results.update(crit_mc_res)
    except Exception as e:
        print(f"Critical components multiclass failed: {e}")

    print("Computing Skeleton Distance...")
    try:
        if compute_skel_dist is None:
            raise RuntimeError("not imported")
        # Every call saves a histogram PNG to output_folder, "." by default.
        skel_res = compute_skel_dist(
            gt_bin,
            pred_bin,
            output_folder=str(
                Path(__file__).resolve().parents[1] / "outputs" / "skeleton_hists"
            ),
        )
        if isinstance(skel_res, dict):
            results.update(skel_res)
        else:
            results["skeleton_distance"] = float(skel_res)
    except Exception as e:
        print(f"Skeleton distance failed: {e}")

    print("Computing Dice Multiclass...")
    try:
        if compute_dice_multiclass is None:
            raise RuntimeError("not imported")
        dice_mc = compute_dice_multiclass(
            gt_bin, pred_bin, num_classes=args.num_classes, ignore_index=0
        )
        results["dice_multiclass"] = dice_mc
    except Exception as e:
        print(f"Dice multiclass failed: {e}")

    print("Computing Mean AP...")
    try:
        if compute_mean_ap is None:
            raise RuntimeError("not imported")
        pred_for_ap = pred.astype(np.float32) if args.soft_pred else pred_bin
        ap_res = compute_mean_ap(gt_bin, pred_for_ap, ignore_index=0)
        results.update(ap_res)
    except Exception as e:
        print(f"Mean AP failed: {e}")

    print("\n--- Evaluation Results ---")
    for k, v in results.items():
        print(f"{k:30}: {v}")

    if args.out:
        with open(args.out, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved results to {args.out}")


if __name__ == "__main__":
    main()
