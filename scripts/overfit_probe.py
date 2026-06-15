"""Overfit / feasibility probe: can a fresh model memorize a tiny fixed batch?
Classifies the detector's ~0.52 pixel-AUC ceiling as capacity / optimization /
signal-absent / pipeline-bug. Standalone diagnostic — does not touch train.py,
best_model.pt, or the loop. See docs/superpowers/specs/2026-06-14-overfit-probe-design.md
"""

import argparse  # noqa: F401
import os
import sys

import numpy as np  # noqa: F401
import torch
import torch.nn.functional as F  # noqa: F401

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
