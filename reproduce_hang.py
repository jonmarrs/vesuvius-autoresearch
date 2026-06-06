import json
import os
import sys

import torch

# Add project root to path
sys.path.insert(0, os.getcwd())

from scripts.training.train import ExperimentConfig, apply_augmentations


def test_thick_slice_hang():
    print("Testing SimulateThickSliceTransform hang...")
    config = ExperimentConfig(
        aug_mode="batchgeneratorsv2",
        aug_scroll_thick_slice_p=1.0,  # Force it
        num_layers=16,
    )

    # Create dummy data
    B, C, D, H, W = 2, 1, 16, 64, 64
    x = torch.randn(B, C, D, H, W)
    target_ink = torch.randn(B, 1, H, W)
    target_fiber = torch.randn(B, 1, 1, H, W)

    for i in range(100):
        print(f"Iteration {i}...")
        x_aug, ink_aug, fiber_aug = apply_augmentations(
            x, target_ink, target_fiber, i, 1000, config
        )
        print(f"Iteration {i} done.")


if __name__ == "__main__":
    test_thick_slice_hang()
