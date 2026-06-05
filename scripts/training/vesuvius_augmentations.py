#!/usr/bin/env python3
"""
Vesuvius Autoresearch: Standardized Villa Augmentations
Wraps the official vesuvius augmentation pipelines for use in Autoresearch.
"""

from typing import Optional

import numpy as np
import torch

try:
    from vesuvius.models.augmentation.pipelines.training_transforms import (
        create_training_transforms,
    )

    VESUVIUS_PKG_AVAILABLE = True
except ImportError:
    VESUVIUS_PKG_AVAILABLE = False


def get_villa_augmentations(patch_size: tuple[int, int, int]):
    """
    Returns the official composed training transforms from the vesuvius package.
    """
    if not VESUVIUS_PKG_AVAILABLE:
        print("Warning: 'vesuvius' package not found. Using identity transforms.")
        return lambda x: x

    return create_training_transforms(patch_size=patch_size)


def apply_villa_aug(data_dict, transforms):
    """
    Applies the composed transforms to a data dictionary.
    Expected dict keys: 'data' (C, D, H, W), 'seg' (C, D, H, W)
    """
    return transforms(data_dict)


if __name__ == "__main__":
    if VESUVIUS_PKG_AVAILABLE:
        print("Vesuvius package augmentations are available.")
        # Test creation
        aug = get_villa_augmentations((16, 64, 64))
        print(f"Created augmentation pipeline: {type(aug).__name__}")

        # Test dummy data
        dummy_data = {
            "data": np.random.rand(1, 16, 64, 64).astype(np.float32),
            "seg": np.random.randint(0, 2, (1, 16, 64, 64)).astype(np.float32),
        }
        res = apply_villa_aug(dummy_data, aug)
        print(f"Augmentation successful. Data shape: {res['data'].shape}")
    else:
        print(
            "Vesuvius package NOT available. Please run 'uv pip install ./villa/vesuvius'."
        )
