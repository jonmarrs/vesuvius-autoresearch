"""
Re-evaluate best_model.pt under TODAY's validation methodology.

Why this exists: the val_bpb stored inside best_model.pt is from the cycle that
promoted it. Validation methodology can drift over time (sampling, threshold
sweep, metric implementations). Cycles compare their fresh val_bpb against the
STORED value, so any drift between then and now makes the comparison apples-to-
oranges and can permanently freeze best_model.pt.

This script runs validation only (no training) on best_model.pt and reports
the metrics as measured by today's code. Compare to chk['val_bpb'] etc.

Usage:
    uv run python scripts/reevaluate_best_model.py
    uv run python scripts/reevaluate_best_model.py --update-stored  # rewrites best_model.pt's stored val_bpb fields
"""

import argparse
import os
import sys

import numpy as np
import torch

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
# train.py lives in scripts/training/ (moved); keep it importable as `train`.
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts", "training"))

from torch.utils.data import DataLoader

from train import (
    ExperimentConfig,
    compute_cc_diff,
    compute_centerline_dice,
    compute_official_dice,
    compute_skeleton_dist,
    load_shape_compatible_state,
    select_topology_threshold,
)
from vesuvius_autoresearch.core.model_wrappers import build_inference_model
from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset


def reevaluate(update_stored: bool = False) -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    config = ExperimentConfig.load("config.json")

    print("Loading best_model.pt...")
    chk = torch.load("best_model.pt", map_location="cpu", weights_only=False)
    stored = chk.get("config", {})
    stored_arch = stored.get("architecture", "?")

    print(f"  stored architecture: {stored_arch!r}")
    print(f"  stored val_bpb:      {chk.get('val_bpb')}")
    print(f"  stored skel_dist:    {chk.get('avg_skel_dist')}")
    print(f"  stored cd_dice:     {chk.get('avg_centerline_dice')}")
    print(f"  stored cc_diff:     {chk.get('avg_cc_diff')}")
    print()

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
    skipped = load_shape_compatible_state(
        model, chk["model_state_dict"], "best_model.pt"
    )
    print(
        f"  load_shape_compatible_state: skipped {len(skipped) if hasattr(skipped, '__len__') else 0} tensors"
    )

    parent_dir = os.path.dirname(config.val_uri.rstrip("/"))
    labels_path = os.path.join(parent_dir, "inklabels_filled.png")
    if not os.path.exists(labels_path):
        labels_path = os.path.join(parent_dir, "inklabels.png")
    mask_path = os.path.join(parent_dir, "mask.png")

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
    val_loader = DataLoader(
        val_ds, batch_size=config.batch_size, num_workers=0, pin_memory=True
    )
    val_iter = iter(val_loader)

    model.eval()
    torch.manual_seed(42)

    all_probs, all_targets = [], []
    requested = 100
    empty = 0
    with torch.no_grad():
        for _ in range(requested):
            try:
                x_raw, target, _fiber = next(val_iter)
            except StopIteration:
                val_iter = iter(val_loader)
                continue
            x = x_raw[:, :, 4 : 4 + config.num_layers].to(device)
            if target is None or target.numel() == 0:
                continue
            target = target.to(device)
            if target.dim() == 3:
                target = target.unsqueeze(1)
            if torch.sum(target.float()) < 1.0:
                empty += 1
                continue
            with torch.autocast(device_type=device.type, enabled=device.type == "cuda"):
                out = model(x)
                if isinstance(out, tuple):
                    out = out[0]
            all_probs.append(torch.sigmoid(out).cpu())
            all_targets.append(target.cpu())

    if not all_probs:
        print("ERROR: zero usable validation patches.")
        return

    probs_cat = torch.cat(all_probs)
    targets_cat = torch.cat(all_targets)

    best_dice, best_threshold = 0.0, 0.5
    for t in np.linspace(0.01, 0.8, 40):
        d = compute_official_dice(targets_cat, probs_cat, threshold=t)
        if d > best_dice:
            best_dice, best_threshold = d, t
    print(f"  best dice: {best_dice:.6f} at threshold {best_threshold:.3f}")

    # Topology gates are evaluated at the centerline_dice-optimal threshold (see
    # train.select_topology_threshold), matching the loop's validation.
    topo_threshold, topo_cd = select_topology_threshold(all_probs, all_targets)
    print(f"  topology threshold: {topo_threshold:.3f} (centerline_dice {topo_cd:.6f})")

    val_losses, val_skel, val_cd, val_cc = [], [], [], []
    for i in range(len(all_probs)):
        prob_2d = all_probs[i]
        tgt = all_targets[i]
        val_losses.append(
            1.0 - compute_official_dice(tgt, prob_2d, threshold=best_threshold)
        )
        try:
            gt = (tgt > 0.5).numpy().astype(bool)
            pred = (prob_2d > topo_threshold).numpy().astype(bool)
            for b in range(gt.shape[0]):
                val_cc.append(compute_cc_diff(gt[b, 0], pred[b, 0]))
        except Exception:
            pass
        if i % 10 == 0:
            gt3 = np.squeeze((tgt > 0.5).numpy().astype(bool))
            pred3 = np.squeeze((prob_2d > topo_threshold).numpy().astype(bool))
            if gt3.ndim == 2:
                gt3 = gt3[np.newaxis, ...]
            if pred3.ndim == 2:
                pred3 = pred3[np.newaxis, ...]
            try:
                sd = compute_skeleton_dist(gt3, pred3)
                if not np.isnan(sd):
                    val_skel.append(sd)
            except Exception:
                pass
            try:
                cd = compute_centerline_dice(gt3, pred3, tolerance_radius=3.0).get(
                    "centerline_dice", 0.0
                )
                if not np.isnan(cd):
                    val_cd.append(cd)
            except Exception:
                pass

    val_bpb = float(np.mean(val_losses))
    skel = float(np.mean(val_skel)) if val_skel else float("nan")
    cd = float(np.mean(val_cd)) if val_cd else 0.0
    cc = float(np.mean(val_cc)) if val_cc else 0.0

    print()
    print("=== TODAY'S MEASUREMENT (eval only, no training) ===")
    print(f"  val_bpb:             {val_bpb:.16f}")
    print(f"  avg_skel_dist:       {skel:.6f}")
    print(f"  avg_centerline_dice: {cd:.6f}")
    print(f"  avg_cc_diff:         {cc:.3f}")
    print(f"  usable / requested:  {len(all_probs)}/{requested} (empty={empty})")

    print()
    print("=== DIFF: today vs stored ===")
    for name, today_val, stored_val in [
        ("val_bpb", val_bpb, chk.get("val_bpb")),
        ("avg_skel_dist", skel, chk.get("avg_skel_dist")),
        ("avg_centerline_dice", cd, chk.get("avg_centerline_dice")),
        ("avg_cc_diff", cc, chk.get("avg_cc_diff")),
    ]:
        if stored_val is None:
            print(f"  {name}: today={today_val} stored=<MISSING>")
        else:
            delta = today_val - stored_val
            print(
                f"  {name}: today={today_val:.6f} stored={stored_val:.6f} delta={delta:+.6f}"
            )

    if update_stored:
        print()
        print("Updating best_model.pt's stored metrics to today's values...")
        chk["val_bpb"] = val_bpb
        chk["avg_skel_dist"] = skel
        chk["avg_centerline_dice"] = cd
        chk["avg_cc_diff"] = cc
        torch.save(chk, "best_model.pt")
        print("Done.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument(
        "--update-stored",
        action="store_true",
        help="rewrite best_model.pt's stored val_bpb/skel/cd/cc to today's values",
    )
    args = p.parse_args()
    reevaluate(update_stored=args.update_stored)
