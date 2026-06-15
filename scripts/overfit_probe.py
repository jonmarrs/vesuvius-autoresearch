"""Overfit / feasibility probe: can a fresh model memorize a tiny fixed batch?
Classifies the detector's ~0.52 pixel-AUC ceiling as capacity / optimization /
signal-absent / pipeline-bug. Standalone diagnostic — does not touch train.py,
best_model.pt, or the loop. See docs/superpowers/specs/2026-06-14-overfit-probe-design.md
"""

import argparse
import os
import sys

import numpy as np
import torch
import torch.nn.functional as F

_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _R)
sys.path.insert(0, os.path.join(_R, "scripts", "training"))


def brightness_control_target(x):
    """Synthetic, definitely-learnable per-pixel target from the CT input itself:
    CT channel (0) averaged over z, thresholded at each patch's own mean. Returns
    [K, 1, H, W] float. Used as the Probe 2 control."""
    ct = x[:, 0]  # [K, nl, H, W]
    zmean = ct.mean(dim=1)  # [K, H, W]
    pmean = zmean.mean(dim=(1, 2), keepdim=True)  # [K, 1, 1]
    return (zmean > pmean).float().unsqueeze(1)  # [K, 1, H, W]


def _dice_loss(logits, target, smooth=1e-5):
    """Minimal soft-Dice (inlined to keep this probe standalone and fast — avoids
    importing the heavy train module just for compute_dice_loss)."""
    p = torch.sigmoid(logits)
    inter = (p * target).sum(dim=(-2, -1))
    union = p.sum(dim=(-2, -1)) + target.sum(dim=(-2, -1))
    return (1.0 - (2.0 * inter + smooth) / (union + smooth)).mean()


def overfit(model, x, target, steps=2000, lr=1e-3, log_every=100):
    """Train `model` on the single fixed batch (x, target) for `steps` Adam steps
    (BCE + Dice on the ink logits). Returns a list of (step, pooled_pixel_auc,
    per_patch_auc) sampled every `log_every` steps. No validation, no augmentation."""
    from sklearn.metrics import roc_auc_score

    from scripts.pixel_auc import pooled_pixel_auc

    model.train()
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    curve = []
    for step in range(steps + 1):
        out = model(x)
        out = out[0] if isinstance(out, tuple) else out
        loss = F.binary_cross_entropy_with_logits(out, target) + _dice_loss(out, target)
        opt.zero_grad()
        loss.backward()
        opt.step()
        if step % log_every == 0:
            with torch.no_grad():
                prob = torch.sigmoid(out).detach().cpu().numpy()
                tgt = (target.detach().cpu().numpy() > 0.5).astype(int)
                probs = [prob[i].ravel() for i in range(prob.shape[0])]
                labels = [tgt[i].ravel() for i in range(tgt.shape[0])]
                pooled = pooled_pixel_auc(probs, labels)
                pp = [
                    roc_auc_score(labels[i], probs[i])
                    for i in range(len(labels))
                    if labels[i].min() != labels[i].max()
                ]
                ppm = float(np.mean(pp)) if pp else 0.5
                curve.append((step, pooled, ppm))
                print(
                    f"  step={step} pooled_auc={pooled:.4f} per_patch_auc={ppm:.4f} loss={loss.item():.4f}"
                )
    return curve


def build_fixed_batch(frag_dir, k, num_layers, patch_size, use_ridges, device, seed=7):
    """Load the first `k` ink-containing patches of `frag_dir` into ONE fixed
    batch (jitter=False, no augmentation). Returns (x [K,C,nl,H,W], ink [K,1,H,W])."""
    from measure_ink_auc import _volume_uri

    from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset

    ds = VesuviusLabeledDataset(
        _volume_uri(frag_dir),
        os.path.join(frag_dir, "inklabels.png"),
        os.path.join(frag_dir, "mask.png"),
        patch_size,
        num_layers + 8,
        seed=seed,
        cache_dir=None,
        use_ridges=use_ridges,
        ridge_sigma=2.0,
        use_lasagna=False,
        require_ink=True,
        jitter=False,
    )
    xs, ys = [], []
    for i in range(min(k, len(ds))):
        x_raw, t, _ = ds[i]
        xs.append(x_raw[:, 4 : 4 + num_layers])
        ys.append(t.unsqueeze(0) if t.dim() == 2 else t)
    x = torch.stack(xs).to(device)
    ink = torch.stack(ys).to(device).float()
    return x, ink


def main():
    from vesuvius_autoresearch.core.model_wrappers import build_inference_model

    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["real", "brightness"], default="real")
    ap.add_argument("--frag", default="local_data/PHercParis2Fr47")
    ap.add_argument("--k", type=int, default=16)
    ap.add_argument("--steps", type=int, default=2000)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--num-layers", type=int, default=16)
    ap.add_argument("--patch-size", type=int, default=64)
    ap.add_argument("--out-csv", default="experiments/overfit_probe/probe.csv")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    device = torch.device(args.device)
    model = build_inference_model(
        architecture="resenc_unet",
        patch_size=args.patch_size,
        num_layers=args.num_layers,
        base_feat=64,
        num_blocks=16,
        num_heads=8,
        dropout=0.0,
        use_ridges=True,
        multi_task_heads=False,
    ).to(device)

    x, ink = build_fixed_batch(
        args.frag, args.k, args.num_layers, args.patch_size, True, device
    )
    target = ink if args.target == "real" else brightness_control_target(x)
    print(
        f"probe target={args.target} batch={tuple(x.shape)} "
        f"target_ink_frac={float((target > 0.5).float().mean()):.3f}"
    )

    curve = overfit(model, x, target, steps=args.steps, lr=args.lr, log_every=100)

    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)
    import csv

    with open(args.out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["step", "pooled_auc", "per_patch_auc"])
        w.writerows(curve)
    final = curve[-1][1]
    verdict = "CAN overfit (>=0.9)" if final >= 0.9 else "STALLS (<0.9)"
    print(f"FINAL pooled_auc={final:.4f} -> {verdict}  (csv: {args.out_csv})")


if __name__ == "__main__":
    main()
