import sys; sys.stdout.reconfigure(line_buffering=True)
print("STARTING TRAINING")
"""
Vesuvius Training Script: Scroll Foundation Model.
Optimized for direct S3 loading and DINO-style Self-Supervised Pretraining.
Usage: uv run train.py
"""

import os
import sys
import time
import math
import json
from dataclasses import dataclass, asdict

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import pandas as pd
from torch.utils.data import DataLoader
from torch.amp import GradScaler, autocast

# Add villa official metrics
sys.path.append(os.path.abspath('villa/segmentation/evaluation'))
try:
    from metrics.dice import compute as compute_official_dice
    from metrics.skeleton_distance_length import compute as compute_skeleton_dist
except ImportError:
    # Fallback if module is missing during test environments
    def compute_official_dice(label, prediction, threshold=0.5):
        prediction_bin = (prediction >= threshold).float()
        intersection = torch.sum(label.float() * prediction_bin)
        return ((2.0 * intersection) / (torch.sum(label.float()) + torch.sum(prediction_bin) + 1e-12)).item()

    def compute_skeleton_dist(label, prediction, **kwargs):
        return 1.0 # Constant fallback

try:
    from metrics.centerline_dice import compute as compute_centerline_dice
except ImportError:
    def compute_centerline_dice(label, prediction, **kwargs):
        return {"centerline_dice": 0.0}

try:
    from scipy.ndimage import label as _scipy_cc_label
    def compute_cc_diff(gt_bin: np.ndarray, pred_bin: np.ndarray) -> int:
        _, n_gt = _scipy_cc_label(gt_bin)
        _, n_pred = _scipy_cc_label(pred_bin)
        return abs(int(n_pred) - int(n_gt))
except ImportError:
    def compute_cc_diff(gt_bin, pred_bin):
        return 0

# Add villa to path for ridge detection and structure tensors
VILLA_SRC = os.path.abspath("villa/vesuvius/src")
VILLA_INK_SRC = os.path.abspath("villa/ink-detection")
if VILLA_SRC not in sys.path:
    sys.path.append(VILLA_SRC)
if VILLA_INK_SRC not in sys.path:
    sys.path.append(VILLA_INK_SRC)

try:
    from vesuvius.image_proc.geometry.structure_tensor import StructureTensorComputer
except ImportError:
    StructureTensorComputer = None
try:
    from models.resnetall import generate_model as generate_resnet3d
    from models.i3dallnl import InceptionI3d
except ImportError:
    generate_resnet3d = None
    InceptionI3d = None

try:
    from dynamic_network_architectures.architectures.unet import ResidualEncoderUNet
    from dynamic_network_architectures.building_blocks.helper import convert_dim_to_conv_op, get_matching_instancenorm
except ImportError:
    ResidualEncoderUNet = None

class ResEncUNetWrapper(nn.Module):
    def __init__(self, model, features_per_stage):
        super().__init__()
        self.model = model
        self.features_per_stage = features_per_stage
        # Add basic multi-task heads if needed for consistency loss or projector
        self.projector = nn.Sequential(
            nn.AdaptiveAvgPool3d(1),
            nn.Flatten(),
            nn.Linear(1, 128) # Projecting from the pooled final logit channel
        )
        
    def forward(self, x, return_fiber=False, return_qc=False, return_proj=False, return_st=False, **kwargs):
        # x: [B, C, Z, H, W]
        # ResidualEncoderUNet returns logits (single 3D tensor if deep_supervision=False)
        out = self.model(x)
        
        # ResEncUNet returns full 3D segmentation [B, 1, Z, H, W]
        # We need to project to 2D for our ink loss
        ink_2d = torch.mean(out, dim=2)
        
        results = [ink_2d]
        if return_fiber:
            # Fake fiber head using mean pooling for compatibility
            results.append(out)
        if return_qc:
            # Fake QC head
            results.append(torch.zeros((x.shape[0], 1), device=x.device))
        if return_proj:
            # Actually use a projector for DINO consistency
            # Need to get bottleneck features. Model returns logits, so we use pool on those
            results.append(self.projector(out))
        if return_st:
            # Fake ST head
            results.append(torch.zeros((x.shape[0], 6, *x.shape[2:]), device=x.device))
            
        if len(results) == 1:
            return results[0]
        return tuple(results)

try:
    from vesuvius.models.augmentation.pipelines.training_transforms import create_training_transforms
except ImportError:
    create_training_transforms = None

_villa_aug_cache = {}
_bg2_aug_cache = {}

# Villa Albumentations recipe (Grand Prize team, tuned for Scroll 2 noise profile).
# See villa/ink-detection/train_timesformer_og.py.
try:
    import albumentations as A
    _HAS_ALBUMENTATIONS = True
except ImportError:
    _HAS_ALBUMENTATIONS = False

_villa_aug_cache = {}

def _get_villa_aug(size: int, config: ExperimentConfig):
    if not _HAS_ALBUMENTATIONS:
        return None
        
    cache_key = (
        size, config.aug_flip_p, config.aug_brightness_p, config.aug_affine_p,
        config.aug_coarse_dropout_p, config.aug_elastic_p, config.aug_grid_p,
        config.aug_rotate_limit, config.aug_scale_limit
    )
    
    if cache_key in _villa_aug_cache:
        return _villa_aug_cache[cache_key]

    transforms = []
    
    if config.aug_flip_p > 0:
        transforms.extend([
            A.HorizontalFlip(p=config.aug_flip_p),
            A.VerticalFlip(p=config.aug_flip_p)
        ])
        
    if config.aug_brightness_p > 0:
        transforms.append(A.RandomBrightnessContrast(p=config.aug_brightness_p))
        
    if config.aug_affine_p > 0:
        transforms.append(
            A.Affine(
                rotate=(-config.aug_rotate_limit, config.aug_rotate_limit),
                scale=(1.0 - config.aug_scale_limit, 1.0 + config.aug_scale_limit),
                translate_percent=(-0.15, 0.15),
                border_mode=0,
                p=config.aug_affine_p
            )
        )
        
    transforms.append(
        A.OneOf([
            A.GaussNoise(std_range=(0.01, 0.03)),
            A.GaussianBlur(),
            A.MotionBlur(),
        ], p=0.4)
    )
        
    if config.aug_coarse_dropout_p > 0:
        transforms.append(
            A.CoarseDropout(
                num_holes_range=(1, 2),
                hole_height_range=(0.1, 0.2),
                hole_width_range=(0.1, 0.2),
                fill=0,
                fill_mask=0,
                p=config.aug_coarse_dropout_p
            )
        )
        
    if getattr(config, 'aug_elastic_p', 0.0) > 0:
        transforms.append(A.ElasticTransform(alpha=1, sigma=50, alpha_affine=50, p=config.aug_elastic_p))
        
    if getattr(config, 'aug_grid_p', 0.0) > 0:
        transforms.append(A.GridDistortion(num_steps=5, distort_limit=0.3, p=config.aug_grid_p))

    pipeline = A.Compose(transforms, additional_targets={'fiber': 'mask'})
    _villa_aug_cache[cache_key] = pipeline
    return pipeline

# Import our breakthrough components
from vesuvius_model import InkDetectorOptimized, VesuviusTimeSformer, VesuviusConfig
from vesuvius_loader import VesuviusS3Dataset, VesuviusLabeledDataset

# ---------------------------------------------------------------------------
# Training Configuration
# ---------------------------------------------------------------------------

@dataclass
