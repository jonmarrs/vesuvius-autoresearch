"""Overfit / feasibility probe: can a fresh model memorize a tiny fixed batch?
Classifies the detector's ~0.52 pixel-AUC ceiling as capacity / optimization /
signal-absent / pipeline-bug. Standalone diagnostic — does not touch train.py,
best_model.pt, or the loop. See docs/superpowers/specs/2026-06-14-overfit-probe-design.md
"""

import argparse  # noqa: F401
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
