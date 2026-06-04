#!/usr/bin/env python3
"""
Dynamic Z-Shift Optimizer for inference.
Automatically searches for the most legible Z-layer within a stack.
"""

import numpy as np
import torch
import torch.nn.functional as F


def optimize_z_shift(logits_3d, window_size=5):
    """
    Given a 3D logit volume [Z, H, W], find the optimal Z-offset
    that maximizes local ink confidence.
    """
    # Softmax across layers to see where ink 'peaks'
    probs = torch.sigmoid(logits_3d)

    # Calculate a legibility score per layer (e.g., max confidence)
    # or mean of top-k pixels
    z_scores = probs.amax(dim=(-2, -1))

    # Smooth scores to avoid jitter
    kernel = torch.ones(window_size, device=logits_3d.device) / window_size
    z_scores_smooth = F.conv1d(
        z_scores.view(1, 1, -1), kernel.view(1, 1, -1), padding=window_size // 2
    ).view(-1)

    best_z = torch.argmax(z_scores_smooth).item()
    return best_z, z_scores_smooth.cpu().numpy()


if __name__ == "__main__":
    # Test with dummy data
    logits = torch.randn(24, 64, 64)
    # Add a fake 'ink' signal at layer 12
    logits[12, 30:34, 30:34] += 10

    best_z, scores = optimize_z_shift(logits)
    print(f"Optimal Z-Shift found at index: {best_z}")
    print(f"Layer Scores: {scores}")
