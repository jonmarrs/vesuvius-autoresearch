"""Diagnose whether post-processing (threshold + small-component removal) can
move the real model's skel_dist toward the prize gate (<= 2.0), separately from
training changes.

Loads best_model.pt, runs validation inference (CPU by default to avoid the
GPU the autoresearch loop uses), then sweeps binarization threshold x despeckle
min-component-size and reports the villa topology metrics for each combination.

Usage:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/diagnose_topology_postproc.py
"""

import os
import sys

import numpy as np
import torch
from scipy import ndimage

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts", "training"))

from torch.utils.data import DataLoader
from train import (
    ExperimentConfig,
    compute_cc_diff,
    compute_centerline_dice,
    compute_official_dice,
    compute_skeleton_dist,
    load_shape_compatible_state,
)

from vesuvius_autoresearch.core.model_wrappers import build_inference_model
from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset


def despeckle(mask: np.ndarray, min_size: int) -> np.ndarray:
    if min_size <= 1:
        return mask
    lbl, k = ndimage.label(mask)
    if k == 0:
        return mask
    sizes = ndimage.sum(np.ones_like(lbl), lbl, range(1, k + 1))
    keep = 1 + np.where(sizes >= min_size)[0]
    return np.isin(lbl, keep)


def topo_metrics(probs, targets, threshold, min_size):
    """Average villa topology metrics over the patch list at a given post-proc."""
    skel, cd, cc, dice = [], [], [], []
    for i in range(len(probs)):
        tgt = targets[i]
        prob = probs[i]
        dice.append(compute_official_dice(tgt, prob, threshold=threshold))
        gt = (tgt > 0.5).numpy().astype(bool)
        pred = (prob > threshold).numpy().astype(bool)
        for b in range(gt.shape[0]):
            pb = despeckle(pred[b, 0], min_size)
            cc.append(compute_cc_diff(gt[b, 0], pb))
        if i % 5 == 0:
            gt3 = np.squeeze(gt)
            pred3 = np.squeeze(
                np.stack(
                    [despeckle(pred[b, 0], min_size) for b in range(pred.shape[0])]
                )
            )
            if gt3.ndim == 2:
                gt3 = gt3[None]
            if pred3.ndim == 2:
                pred3 = pred3[None]
            try:
                sd = compute_skeleton_dist(gt3, pred3)
                if not np.isnan(sd):
                    skel.append(sd)
            except Exception:
                pass
            try:
                c = compute_centerline_dice(gt3, pred3, tolerance_radius=3.0).get(
                    "centerline_dice", 0.0
                )
                if not np.isnan(c):
                    cd.append(c)
            except Exception:
                pass
    return {
        "dice": float(np.mean(dice)) if dice else float("nan"),
        "skel_dist": float(np.mean(skel)) if skel else float("nan"),
        "centerline_dice": float(np.mean(cd)) if cd else float("nan"),
        "cc_diff": float(np.mean(cc)) if cc else float("nan"),
        "n_skel": len(skel),
    }


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device: {device}")
    config = ExperimentConfig.load("config.json")
    chk = torch.load("best_model.pt", map_location="cpu", weights_only=False)
    stored = chk.get("config", {})
    stored_arch = stored.get("architecture", "?")
    print(
        f"stored arch={stored_arch} val_bpb={chk.get('val_bpb')} skel={chk.get('avg_skel_dist')}"
    )

    model = build_inference_model(
        architecture=stored_arch,
        patch_size=config.patch_size,
        num_layers=config.num_layers,
        base_feat=config.base_feat,
        num_blocks=config.num_blocks,
        num_heads=config.num_heads,
        dropout=config.dropout,
        use_ridges=config.use_ridges,
        multi_task_heads=stored.get("multi_task_heads", False),
    ).to(device)
    load_shape_compatible_state(model, chk["model_state_dict"], "best_model.pt")

    parent = os.path.dirname(config.val_uri.rstrip("/"))
    labels_path = os.path.join(parent, "inklabels.png")
    mask_path = os.path.join(parent, "mask.png")
    val_ds = VesuviusLabeledDataset(
        config.val_uri,
        labels_path,
        mask_path if os.path.exists(mask_path) else None,
        config.patch_size,
        config.num_layers + 8,
        seed=42,
        cache_dir=config.cache_dir,
        use_ridges=config.use_ridges,
        ridge_sigma=getattr(config, "ridge_sigma", 2.0),
        use_lasagna=False,
        require_ink=True,
    )
    val_loader = DataLoader(val_ds, batch_size=config.batch_size, num_workers=0)
    val_iter = iter(val_loader)

    cache = "/tmp/topo_postproc_preds.pt"
    if os.path.exists(cache):
        blob = torch.load(cache)
        all_probs, all_targets = blob["probs"], blob["targets"]
        print(f"loaded cached predictions: {len(all_probs)} batches")
    else:
        model.eval()
        all_probs, all_targets = [], []
        import time

        t0 = time.time()
        with torch.no_grad():
            for _ in range(120):
                try:
                    x_raw, target, _ = next(val_iter)
                except StopIteration:
                    break
                x = x_raw[:, :, 4 : 4 + config.num_layers].to(device)
                if target is None or target.numel() == 0:
                    continue
                target = target.to(device)
                if target.dim() == 3:
                    target = target.unsqueeze(1)
                if torch.sum(target.float()) < 1.0:
                    continue
                out = model(x)
                if isinstance(out, tuple):
                    out = out[0]
                all_probs.append(torch.sigmoid(out).cpu())
                all_targets.append(target.cpu())
                print(f"  batch {len(all_probs)} ({time.time() - t0:.0f}s)", flush=True)
                if len(all_probs) >= 30:
                    break
        torch.save({"probs": all_probs, "targets": all_targets}, cache)
    print(f"usable validation batches: {len(all_probs)}")
    if not all_probs:
        print("ERROR: no usable validation patches")
        return

    probs_cat = torch.cat(all_probs)
    targets_cat = torch.cat(all_targets)
    best_dice, dice_thr = 0.0, 0.5
    for t in np.linspace(0.05, 0.8, 16):
        d = compute_official_dice(targets_cat, probs_cat, threshold=t)
        if d > best_dice:
            best_dice, dice_thr = d, t
    print(f"Dice-optimal threshold = {dice_thr:.3f} (dice={best_dice:.4f})\n")

    print(
        f"{'thresh':>7} {'minsz':>6} {'dice':>7} {'skel_dist':>10} {'cl_dice':>8} {'cc_diff':>8}"
    )
    print("-" * 52)
    baseline = None
    for thr in [dice_thr, 0.5, 0.65]:
        for ms in [1, 16, 64]:
            m = topo_metrics(all_probs, all_targets, thr, ms)
            tag = "  <- Dice-opt, no postproc" if (thr == dice_thr and ms == 1) else ""
            if thr == dice_thr and ms == 1:
                baseline = m
            print(
                f"{thr:7.3f} {ms:6d} {m['dice']:7.4f} {m['skel_dist']:10.3f} "
                f"{m['centerline_dice']:8.4f} {m['cc_diff']:8.3f}{tag}"
            )
    if baseline:
        print(
            f"\nBaseline (current eval): skel_dist={baseline['skel_dist']:.3f}, gate=2.0"
        )


if __name__ == "__main__":
    main()
