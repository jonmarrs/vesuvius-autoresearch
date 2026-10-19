"""Augmentations that change the CT's intensities leave the ridge channel alone.

With use_ridges, channel 1 is the ridge filter's response to the CT, around
1e-3 (vesuvius_loader.ridge_channel). The Albumentations recipe's brightness
shift (up to 0.2, clipped at 0) zeroed it or lifted it far past its range, its
Gaussian noise (std 0.1-0.17) erased it, and the scroll intensity drift moved it
by up to 0.08: training saw a ridge channel inference never does. The spatial
transforms still move it with the CT. See
docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-19_RIDGE_CHANNEL_AUGMENTATION.md.
"""

import random

import numpy as np
import pytest
import torch

import scroll_augmentations as sa
from scripts.training import train
from scripts.training.config import ExperimentConfig

D, H, W = 16, 64, 64
SCROLL = [k for k in vars(ExperimentConfig()) if k.startswith("aug_scroll_")]


def _config(**changes):
    config = ExperimentConfig(
        aug_mode="albumentations",
        aug_flip_p=0.0,
        aug_brightness_p=0.0,
        aug_affine_p=0.0,
        aug_coarse_dropout_p=0.0,
        aug_elastic_p=0.0,
        aug_grid_p=0.0,
    )
    for name in SCROLL:
        setattr(config, name, 0.0)
    for name, value in changes.items():
        setattr(config, name, value)
    return config


def _batch(seed=0):
    """A (CT, ridge) patch: CT in [0, 1] with high-contrast blocks, and a ridge
    channel of the same pattern at the ridge filter's scale."""
    rng = np.random.RandomState(seed)
    blocks = np.kron(rng.rand(D, H // 8, W // 8) > 0.5, np.ones((1, 8, 8)))
    ct = (0.2 + 0.6 * blocks).astype(np.float32)
    x = torch.from_numpy(np.stack([ct, ct * 1e-3]))[None]
    ink = torch.zeros(1, 1, H, W)
    fiber = torch.zeros(1, 1, 1, H, W)
    return x, ink, fiber


def _seed(i):
    np.random.seed(i)
    random.seed(i)
    torch.manual_seed(i)


needs_albumentations = pytest.mark.skipif(
    not train._HAS_ALBUMENTATIONS, reason="albumentations is not installed"
)


@needs_albumentations
def test_the_recipe_runs_its_pixel_level_transforms_on_the_ct_only():
    config = _config(aug_flip_p=0.5, aug_brightness_p=0.75, aug_affine_p=0.75)
    config.aug_coarse_dropout_p = 0.5
    stages = train._get_villa_aug(W, config)
    names = [type(stage.transforms[0]).__name__ for stage, _ in stages]
    assert names == [
        "HorizontalFlip",
        "VerticalFlip",
        "RandomBrightnessContrast",
        "Affine",
        "OneOf",
        "CoarseDropout",
    ]
    assert [ct_only for _, ct_only in stages] == [
        False,
        False,
        True,
        False,
        True,
        False,
    ]


@needs_albumentations
def test_brightness_noise_and_blur_leave_the_ridge_channel():
    """Every transform that only changes values, at production's probabilities
    or higher; the ridge channel is the original, or its z-flip."""
    x, ink, fiber = _batch()
    ridge = x[0, 1]
    config = _config(aug_brightness_p=1.0)
    changed = 0
    for i in range(40):
        _seed(i)
        out, _, _ = train.apply_augmentations(x.clone(), ink, fiber, 0, 1, config)
        assert torch.equal(out[0, 1], ridge) or torch.equal(out[0, 1], ridge.flip(0)), (
            f"seed {i}"
        )
        changed += not torch.allclose(out[0, 0], x[0, 0]) and not torch.allclose(
            out[0, 0], x[0, 0].flip(0)
        )
    assert changed == 40  # brightness fires on every sample, on the CT


@needs_albumentations
def test_the_spatial_transforms_still_move_the_ridge_channel_with_the_ct():
    x, ink, fiber = _batch()
    config = _config(aug_flip_p=0.5, aug_affine_p=1.0, aug_coarse_dropout_p=0.5)
    for i in range(20):
        _seed(i)
        out, _, _ = train.apply_augmentations(x.clone(), ink, fiber, 0, 1, config)
        ct, ridge = out[0, 0].numpy().ravel(), out[0, 1].numpy().ravel() * 1e3
        # The OneOf's noise or blur changes the CT alone; the geometry is shared.
        assert np.corrcoef(ct, ridge)[0, 1] > 0.8, f"seed {i}"
        assert not np.allclose(ridge, x[0, 1].numpy().ravel() * 1e3)


@pytest.mark.parametrize(
    "probability", ["aug_scroll_intensity_drift_p", "aug_scroll_rician_noise_p"]
)
def test_the_scroll_intensity_augmentations_leave_the_ridge_channel(probability):
    x, ink, fiber = _batch()
    config = _config(**{probability: 1.0})
    torch.manual_seed(0)
    out, _, _ = sa.apply_scroll_specific_3d_augmentations(x.clone(), ink, fiber, config)
    assert torch.equal(out[:, 1], x[:, 1])
    assert not torch.allclose(out[:, 0], x[:, 0])


def test_without_ct_channels_the_library_augments_every_channel():
    """Its public API keeps its behaviour for other callers; a CT-only input is
    augmented as before through the loop's adapter too."""
    x, ink, fiber = _batch()
    probs = sa.ScrollAugProbs(intensity_drift=1.0)
    torch.manual_seed(0)
    out, _, _ = sa.apply_scroll_augmentations(x.clone(), ink, fiber, probs)
    assert not torch.allclose(out[:, 1], x[:, 1])
    ct_only = x[:, :1]
    torch.manual_seed(0)
    out, _, _ = sa.apply_scroll_specific_3d_augmentations(
        ct_only.clone(), ink, fiber, _config(aug_scroll_intensity_drift_p=1.0)
    )
    assert not torch.allclose(out, ct_only)


def test_a_blanked_region_takes_each_sample_and_channels_own_mean():
    """One mean over the batch and every channel filled the CT with a share of
    the ridge channel's values and the ridge channel with the CT's. On an input
    constant in each sample and channel, each region's own mean changes nothing."""
    levels = torch.tensor([[0.4, 4e-4], [0.7, 1e-3]]).view(2, 2, 1, 1, 1)
    x = levels.expand(2, 2, D, H, W).clone()
    for i in range(10):
        torch.manual_seed(i)
        out = sa.scroll_blank_rectangles(x)
        # float32 means of a constant region are within rounding of it.
        assert torch.allclose(out, x, rtol=1e-5, atol=0), f"seed {i}"
