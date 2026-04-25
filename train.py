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

def _get_villa_aug(size: int):
    if not _HAS_ALBUMENTATIONS:
        return None
    if size in _villa_aug_cache:
        return _villa_aug_cache[size]
    # Albumentations 2.x API. Villa used rotate_limit=360 / shift_limit=0.15 /
    # scale_limit=0.15 via the (now deprecated) ShiftScaleRotate; A.Affine is the
    # direct replacement. CoarseDropout switched to *_range tuples + fill/fill_mask.
    pipeline = A.Compose([
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.5),
        A.RandomBrightnessContrast(p=0.75),
        A.Affine(
            rotate=(-180, 180),
            translate_percent=(-0.15, 0.15),
            scale=(0.85, 1.15),
            border_mode=0,
            p=0.75,
        ),
        A.OneOf([
            A.GaussNoise(std_range=(0.01, 0.03)),
            A.GaussianBlur(),
            A.MotionBlur(),
        ], p=0.4),
        A.CoarseDropout(
            num_holes_range=(1, 2),
            hole_height_range=(0.1, 0.2),
            hole_width_range=(0.1, 0.2),
            fill=0,
            fill_mask=0,
            p=0.5,
        ),
    ], additional_targets={'fiber': 'mask'})
    _villa_aug_cache[size] = pipeline
    return pipeline

# Import our breakthrough components
from vesuvius_model import InkDetectorOptimized, VesuviusTimeSformer, VesuviusConfig
from vesuvius_loader import VesuviusS3Dataset, VesuviusLabeledDataset

# ---------------------------------------------------------------------------
# Training Configuration
# ---------------------------------------------------------------------------

@dataclass
class ExperimentConfig:
    # Data
    uri: str = 'local_data/PHercParis2Fr47/surface_volume/'
    val_uri: str = 'local_data/PHercParis2Fr143/surface_volume/'
    cache_dir: str = None  # If None, caches are stored next to volume_uri
    use_ridges: bool = False # 3D Ridge/Frangi feature channel
    ridge_sigma: float = 2.0 # Ridge filter parameter
    
    # Training Loop
    batch_size: int = 16 
    patch_size: int = 64
    num_layers: int = 24 
    lr: float = 1e-3
    weight_decay: float = 0.01
    time_budget: int = 900 
    pinned: bool = False # If True, autoresearch loop should not evolve this config
    
    # Loss Weights
    loss_ink_bce: float = 0.4
    loss_ink_dice: float = 0.4
    loss_fiber_bce: float = 0.2
    loss_st: float = 0.1
    label_smoothing: float = 0.0 # Standard for GP winner is 0.25
    aug_mode: str = 'albumentations' # 'albumentations' or 'batchgeneratorsv2'

    # Model Architecture
    architecture: str = "gated_unet"
    base_feat: int = 64
    num_blocks: int = 16
    num_heads: int = 8
    dropout: float = 0.0

    def save(self, path):
        with open(path, 'w') as f:
            json.dump(asdict(self), f, indent=4)

    @classmethod
    def load(cls, path):
        with open(path, 'r') as f:
            data = json.load(f)
        return cls(**data)

def mixup_data(x, y, z, alpha=0.2):
    if alpha > 0: lam = np.random.beta(alpha, alpha)
    else: lam = 1
    batch_size = x.size()[0]
    index = torch.randperm(batch_size).to(x.device)
    mixed_x = lam * x + (1 - lam) * x[index, :]
    mixed_y = lam * y + (1 - lam) * y[index, :]
    mixed_z = lam * z + (1 - lam) * z[index, :]
    return mixed_x, mixed_y, mixed_z, lam

def cutmix_data(x, y, z, alpha=1.0):
    if alpha > 0: lam = np.random.beta(alpha, alpha)
    else: lam = 1
    batch_size = x.size()[0]
    index = torch.randperm(batch_size).to(x.device)

    W, H = x.size(-1), x.size(-2)
    cut_rat = np.sqrt(1. - lam)
    cut_w, cut_h = int(W * cut_rat), int(H * cut_rat)
    cx, cy = np.random.randint(W), np.random.randint(H)

    bbx1 = np.clip(cx - cut_w // 2, 0, W)
    bby1 = np.clip(cy - cut_h // 2, 0, H)
    bbx2 = np.clip(cx + cut_w // 2, 0, W)
    bby2 = np.clip(cy + cut_h // 2, 0, H)

    x[..., bby1:bby2, bbx1:bbx2] = x[index, ..., bby1:bby2, bbx1:bbx2]
    y[..., bby1:bby2, bbx1:bbx2] = y[index, ..., bby1:bby2, bbx1:bbx2]
    z[..., bby1:bby2, bbx1:bbx2] = z[index, ..., bby1:bby2, bbx1:bbx2]
    
    return x, y, z, lam

def compute_dice_loss(pred_2d, target, smooth=1e-5):
    """
    Standard Dice Loss for 2D ink detection.
    """
    pred_2d = torch.sigmoid(pred_2d)
    
    # target: [B, 1, H, W]
    # Ensure target is 4D
    if target.dim() == 3: target = target.unsqueeze(1)
    
    intersection = (pred_2d * target).sum(dim=(-2, -1))
    union = pred_2d.sum(dim=(-2, -1)) + target.sum(dim=(-2, -1))
    
    dice = (2. * intersection + smooth) / (union + smooth)
    return 1.0 - dice.mean()

def compute_hard_dice(pred_2d, target, smooth=1e-5):
    """
    Hard Dice Score (thresholded at 0.5) for evaluation.
    """
    pred_2d = (torch.sigmoid(pred_2d) > 0.5).float()
    
    if target.dim() == 3: target = target.unsqueeze(1)
    
    intersection = (pred_2d * target).sum(dim=(-2, -1))
    union = pred_2d.sum(dim=(-2, -1)) + target.sum(dim=(-2, -1))
    
    dice = (2. * intersection + smooth) / (union + smooth)
    return dice.mean()

def apply_augmentations(x, target_ink, target_fiber, step, max_steps, config=None):
    """Villa Augmentation recipes.
    
    Supports:
    - 'albumentations': Per-item 2D recipe, synchronized across depth.
    - 'batchgeneratorsv2': Official 3D-native MIC-DKFZ pipeline from villa.

    x: (B, 1, D, H, W); target_ink: (B, 1, H, W); target_fiber: (B, 1, 1, H, W).
    """
    aug_mode = getattr(config, 'aug_mode', 'albumentations')
    
    if aug_mode == 'batchgeneratorsv2' and create_training_transforms is not None:
        B, C, D, H, W = x.shape
        patch_size_3d = (D, H, W)
        if patch_size_3d not in _bg2_aug_cache:
            _bg2_aug_cache[patch_size_3d] = create_training_transforms(patch_size_3d)
        
        bg_aug = _bg2_aug_cache[patch_size_3d]
        
        # Batchgenerators expects: (C, Z, H, W) for per-sample call
        # but our wrapper handles (B, C, Z, H, W) if it's the official villa one.
        # Actually, let's process sample by sample to be safe, like Albumentations path.
        
        out_x, out_ink, out_fiber = [], [], []
        try:
            for b in range(B):
                # Prepare inputs for this sample
                img_3d = x[b] # [C, D, H, W]
                
                # Ensure ink is [1, D, H, W]
                ink_samp = target_ink[b]
                if ink_samp.ndim == 2: # [H, W]
                    ink_3d = ink_samp[None, None].repeat(1, D, 1, 1)
                elif ink_samp.ndim == 3: # [1, H, W]
                    ink_3d = ink_samp[:, None].repeat(1, D, 1, 1)
                else:
                    ink_3d = ink_samp
                
                # Ensure fiber is [1, D, H, W]
                f_samp = target_fiber[b]
                if f_samp.ndim == 2: # [H, W]
                    fiber_3d = f_samp[None, None].repeat(1, D, 1, 1)
                elif f_samp.ndim == 3: # [1, H, W]
                    fiber_3d = f_samp[:, None].repeat(1, D, 1, 1)
                elif f_samp.ndim == 4 and f_samp.shape[1] == 1: # [1, 1, H, W]
                    fiber_3d = f_samp.repeat(1, D, 1, 1)
                else:
                    fiber_3d = f_samp

                # Compose the data dict
                data_dict = {
                    'image': img_3d,
                    'ink': ink_3d,
                    'fiber': fiber_3d,
                    'regression_keys': ['ink', 'fiber'] # Hint for bilinear interpolation
                }
                
                # Call transform with kwargs
                res = bg_aug(**data_dict)
                
                out_x.append(res['image'])
                # Extract 2D ink from the center slice of the augmented 3D label
                # res['ink'] is [1, D, H, W]
                out_ink.append(res['ink'][:, D//2]) 
                # Fiber is used as a 2D pseudo-label (collapsed mean in loss)
                out_fiber.append(res['fiber'][:, D//2:D//2+1])

            x_aug = torch.stack(out_x)
            ink_aug = torch.stack(out_ink)
            fiber_aug = torch.stack(out_fiber)
            
            return x_aug, ink_aug, fiber_aug
        except Exception as e:
            if step % 100 == 0:
                print(f"Warning: batchgeneratorsv2 failed ({e}). Falling back to Albumentations.")
            aug_mode = 'albumentations'

    # Fallback/Default: Albumentations
    aug = _get_villa_aug(x.shape[-1]) if _HAS_ALBUMENTATIONS else None
    if aug is None:
        # Bare-bones fallback so the training loop still runs without albumentations.
        k_rot = np.random.randint(0, 4)
        x_aug = torch.rot90(x, k=k_rot, dims=(-2, -1))
        ink_aug = torch.rot90(target_ink, k=k_rot, dims=(-2, -1)).clamp(0, 1)
        fiber_aug = torch.rot90(target_fiber, k=k_rot, dims=(-2, -1)).clamp(0, 1)
        if np.random.rand() > 0.5:
            x_aug = torch.flip(x_aug, dims=[2])
        return x_aug, ink_aug, fiber_aug

    B, _, D, H, W = x.shape
    device = x.device
    x_dtype = x.dtype
    ink_dtype = target_ink.dtype
    fiber_dtype = target_fiber.dtype

    x_np = x.detach().float().cpu().numpy()
    ink_np = target_ink.detach().float().cpu().numpy()
    fiber_np = target_fiber.detach().float().cpu().numpy()

    # Collapse fiber's singleton depth dim if present.
    fiber_has_d = (fiber_np.ndim == 5)
    if fiber_has_d:
        fiber_np = fiber_np[:, :, 0]  # (B, 1, H, W)

    out_x, out_ink, out_fiber = [], [], []
    for b in range(B):
        img_hwd = np.transpose(x_np[b, 0], (1, 2, 0)).astype(np.float32, copy=False)  # (H, W, D)
        mask_ink = ink_np[b, 0].astype(np.float32, copy=False)
        mask_fiber = fiber_np[b, 0].astype(np.float32, copy=False)
        res = aug(image=img_hwd, mask=mask_ink, fiber=mask_fiber)
        out_x.append(np.transpose(res['image'], (2, 0, 1)))
        out_ink.append(res['mask'])
        out_fiber.append(res['fiber'])

    x_aug = torch.from_numpy(np.ascontiguousarray(np.stack(out_x))).unsqueeze(1).to(device=device, dtype=x_dtype)
    ink_aug = torch.from_numpy(np.ascontiguousarray(np.stack(out_ink))).unsqueeze(1).to(device=device, dtype=ink_dtype).clamp(0, 1)
    fiber_aug = torch.from_numpy(np.ascontiguousarray(np.stack(out_fiber))).unsqueeze(1).to(device=device, dtype=fiber_dtype).clamp(0, 1)
    if fiber_has_d:
        fiber_aug = fiber_aug.unsqueeze(2)  # restore (B, 1, 1, H, W)

    # Cheap 3D-specific aug the villa 2D recipe can't express: random z-flip.
    if np.random.rand() > 0.5:
        x_aug = torch.flip(x_aug, dims=[2])
        if fiber_has_d:
            fiber_aug = torch.flip(fiber_aug, dims=[2])

    return x_aug, ink_aug, fiber_aug

def train(config: ExperimentConfig):
    torch.set_float32_matmul_precision('high')
    device = torch.device("cuda")
    
    v_config = VesuviusConfig(
        patch_size=config.patch_size, 
        num_layers=config.num_layers,
        batch_size=config.batch_size,
        base_feat=config.base_feat,
        num_blocks=config.num_blocks,
        num_heads=config.num_heads,
        dropout=config.dropout,
        in_channels=2 if config.use_ridges else 1,
        architecture=getattr(config, 'architecture', 'gated_unet')
    )

    print(f"Initializing LOCAL TRANSFORMER Training on {config.uri}...")
    sys.stdout.flush()

    def get_dataloader(uri, seed=None):
        parent_dir = os.path.dirname(uri.rstrip('/'))
        labels_path = os.path.join(parent_dir, 'inklabels_filled.png')
        if not os.path.exists(labels_path):
            labels_path = os.path.join(parent_dir, 'inklabels.png')
            
        if os.path.exists(labels_path):
            mask_path = os.path.join(parent_dir, 'mask.png')
            ds = VesuviusLabeledDataset(uri, labels_path, mask_path if os.path.exists(mask_path) else None, config.patch_size, config.num_layers + 8, seed=seed, cache_dir=config.cache_dir, use_ridges=config.use_ridges, ridge_sigma=getattr(config, 'ridge_sigma', 2.0))
        else:
            ds = VesuviusS3Dataset(uri, config.patch_size, config.num_layers + 8, seed=seed, cache_dir=config.cache_dir, use_ridges=config.use_ridges, ridge_sigma=getattr(config, 'ridge_sigma', 2.0))
        return DataLoader(ds, batch_size=config.batch_size, num_workers=min(4, os.cpu_count() or 1), pin_memory=True)

    data_loader = get_dataloader(config.uri)
    data_iter = iter(data_loader)
    # Use fixed seed and num_workers=0 for validation to ensure absolute determinism
    def get_val_dataloader(uri):
        parent_dir = os.path.dirname(uri.rstrip('/'))
        labels_path = os.path.join(parent_dir, 'inklabels_filled.png')
        if not os.path.exists(labels_path):
            labels_path = os.path.join(parent_dir, 'inklabels.png')
            
        mask_path = os.path.join(parent_dir, 'mask.png')
        ds = VesuviusLabeledDataset(uri, labels_path, mask_path if os.path.exists(mask_path) else None, config.patch_size, config.num_layers + 8, seed=42, cache_dir=config.cache_dir, use_ridges=config.use_ridges, ridge_sigma=getattr(config, 'ridge_sigma', 2.0))
        return DataLoader(ds, batch_size=config.batch_size, num_workers=0, pin_memory=True)

    val_data_loader = get_val_dataloader(config.val_uri)
    val_data_iter = iter(val_data_loader)

    if hasattr(v_config, 'architecture') and v_config.architecture == "timesformer":
        print("Instantiating TimeSformer Architecture...")
        model = VesuviusTimeSformer(v_config).to(device)
    elif hasattr(v_config, 'architecture') and v_config.architecture == "resnet3d":
        print("Instantiating ResNet3D-101 Architecture (Grand Prize Variant)...")
        if generate_resnet3d:
            backbone = generate_resnet3d(101, n_input_channels=v_config.in_channels, n_classes=1, forward_features=False)
            # Wrap to match our expected interface if needed, or use directly
            model = backbone.to(device)
        else:
            raise ImportError("ResNet3D model not found in villa submodule.")
    elif hasattr(v_config, 'architecture') and v_config.architecture == "i3d":
        print("Instantiating Inception-I3D Architecture...")
        if InceptionI3d:
            model = InceptionI3d(num_classes=1, in_channels=v_config.in_channels, final_endpoint='Logits', forward_features=False).to(device)
        else:
            raise ImportError("I3D model not found in villa submodule.")
    elif hasattr(v_config, 'architecture') and v_config.architecture == "resenc_unet":
        print(f"Instantiating nnUNet-style ResEnc UNet (base_feat={v_config.base_feat})...")
        if ResidualEncoderUNet:
            # Shallow 3-stage configuration to avoid dimension mismatch on small patches
            n_stages = 3
            features_per_stage = [v_config.base_feat * (2**i) for i in range(n_stages)]
            strides = [[1, 1, 1]] + [[2, 2, 2]] * (n_stages - 1)
            
            backbone = ResidualEncoderUNet(
                input_channels=v_config.in_channels,
                n_stages=n_stages,
                features_per_stage=features_per_stage,
                conv_op=convert_dim_to_conv_op(3),
                kernel_sizes=[[3, 3, 3]] * n_stages,
                strides=strides,
                n_blocks_per_stage=[2] * n_stages,
                num_classes=1,
                n_conv_per_stage_decoder=[2] * (n_stages - 1),
                conv_bias=True,
                norm_op=get_matching_instancenorm(convert_dim_to_conv_op(3)),
                norm_op_kwargs={'eps': 1e-5, 'affine': True},
                dropout_op=None,
                nonlin=nn.LeakyReLU,
                nonlin_kwargs={'inplace': True},
                deep_supervision=False
            )
            model = ResEncUNetWrapper(backbone, features_per_stage).to(device)
        else:
            raise ImportError("ResidualEncoderUNet not found. Please install dynamic-network-architectures.")
    else:
        print("Instantiating Gated UNet-Transformer Architecture...")
        model = InkDetectorOptimized(v_config).to(device)
    
    # Load best model if architecture matches
    best_model_path = 'best_model.pt'
    if os.path.exists(best_model_path):
        try:
            checkpoint = torch.load(best_model_path, map_location=device, weights_only=False)
            best_config = checkpoint.get('config', {})
            
            # Check compatibility (architecture-defining attributes)
            arch_match = True
            for attr in ['num_layers', 'num_blocks', 'num_heads', 'base_feat', 'patch_size']:
                if best_config.get(attr) != getattr(config, attr):
                    arch_match = False
                    break
            
            if arch_match:
                print(f"Loading weights from {best_model_path} (Incremental Progress)...")
                model.load_state_dict(checkpoint['model_state_dict'], strict=False) # strict=False to allow adding projector head
            else:
                print(f"New architecture detected ({best_config.get('base_feat')}->{config.base_feat}). Starting fresh.")
        except Exception as e:
            print(f"Warning: Could not load best model: {e}")
    
    # 1. Linear Scaling Rule for LR
    config.lr = config.lr * (config.batch_size / 16.0)
    
    # 2. Budget-Aware Scheduling
    # Estimate throughput: ~0.2s per step (conservative estimate for base_feat=64)
    estimated_step_time = 0.2 
    max_steps = max(1000, int(config.time_budget / estimated_step_time))
    warmup_steps = int(max_steps * 0.125) # 12.5% warmup
    
    print(f"Budget-Aware Scheduling: max_steps={max_steps}, warmup_steps={warmup_steps}, scaled_lr={config.lr:.2e}")
    
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.lr, weight_decay=config.weight_decay)
    
    def lr_lambda(current_step: int):
        if current_step < warmup_steps: return float(current_step) / float(max(1, warmup_steps))
        clamped_step = min(current_step, max_steps)
        return 0.5 * (1.0 + math.cos(math.pi * (clamped_step - warmup_steps) / float(max(1, max_steps - warmup_steps))))
    
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
    scaler = GradScaler()

    # Initialize auxiliary task tools
    st_computer = StructureTensorComputer(sigma=1.0, component_sigma=1.0, smooth_components=True, device=device) if StructureTensorComputer else None

    print(f"Starting Gated UNet-Transformer Loop (Budget: {config.time_budget}s)...")
    sys.stdout.flush()

    step = 0
    total_training_time = 0
    smooth_loss = 0

    while True:
        t0 = time.time()
        try:
            x_raw, target_ink_raw = next(data_iter)
            x_raw = x_raw.to(device) # [B, 1, Z_buffered, H, W]
            
            # Ensure target_ink has 4 dims [B, 1, H, W]
            if target_ink_raw is not None and target_ink_raw.numel() > 0:
                target_ink = target_ink_raw.to(device)
                if target_ink.dim() == 3: target_ink = target_ink.unsqueeze(1)
            else:
                target_ink = torch.zeros((x_raw.shape[0], 1, x_raw.shape[3], x_raw.shape[4]), device=device)

            # 2. Anisotropic Z-Interpolation
            z_start = np.random.randint(0, 8)
            if np.random.rand() > 0.8:
                max_len = x_raw.shape[2] - z_start
                min_len = max(4, int(config.num_layers * 0.8))
                z_len = min_len
                x_orig = x_raw[:, :, z_start:z_start+z_len]
                if z_len != config.num_layers:
                    x_orig = F.interpolate(x_orig, size=(config.num_layers, config.patch_size, config.patch_size), mode='trilinear', align_corners=False)
            else:
                x_orig = x_raw[:, :, z_start:z_start+config.num_layers]

        except StopIteration:
            data_iter = iter(data_loader); continue

        # 3. Sobel-Z pseudo-labels (BEFORE mixup to avoid boundary artifacts)
        with torch.no_grad():
            grad_z = x_orig[:, :, 1:] - x_orig[:, :, :-1]
            target_fiber = grad_z.abs().mean(dim=2, keepdim=True)
            b_sz = target_fiber.shape[0]
            tf_flat = target_fiber.view(b_sz, -1)
            tf_min = tf_flat.min(dim=1, keepdim=True)[0].view(b_sz, 1, 1, 1, 1)
            tf_max = tf_flat.max(dim=1, keepdim=True)[0].view(b_sz, 1, 1, 1, 1)
            target_fiber = (target_fiber - tf_min) / (tf_max - tf_min + 1e-8)

        if x_orig.size(0) > 1:
            r = np.random.rand()
            if r < 0.2: x_orig, target_ink, target_fiber, _ = mixup_data(x_orig, target_ink, target_fiber)
            elif r < 0.4: x_orig, target_ink, target_fiber, _ = cutmix_data(x_orig, target_ink, target_fiber)

        # Generate two augmented views for DINO-Lite Consistency
        x_aug1, target_ink_aug1, target_fiber_aug1 = apply_augmentations(x_orig, target_ink, target_fiber, step, max_steps, config=config)
        x_aug2, _, _ = apply_augmentations(x_orig, target_ink, target_fiber, step, max_steps, config=config)

        # Compute Structure Tensor targets on the fly for view 1
        with torch.no_grad():
            if st_computer:
                # x_aug1 is [B, 1, D, H, W] or [B, 2, D, H, W]
                # ST computer expects [B, 1, D, H, W]
                st_input = x_aug1[:, :1]
                target_st = st_computer.compute(st_input) # [B, 6, D, H, W]
            else:
                target_st = None

        optimizer.zero_grad(set_to_none=True)
        with autocast(device_type='cuda'):
            # Forward pass for view 1 (full multi-task if supported)
            model_out = model(x_aug1, return_fiber=True, return_qc=True, return_proj=True, return_st=True)
            if isinstance(model_out, tuple):
                out_ink_2d = model_out[0]
                # Map remaining outputs if they exist
                # This is a bit brittle, but works with our current return order
                out_fiber = model_out[1] if len(model_out) > 1 else None
                out_qc = model_out[2] if len(model_out) > 2 else None
                p1 = model_out[3] if len(model_out) > 3 else None
                out_st = model_out[4] if len(model_out) > 4 else None
            else:
                out_ink_2d = model_out
                out_fiber = out_qc = p1 = out_st = None
            
            # Forward pass for view 2 (consistency only)
            if p1 is not None:
                p2_out = model(x_aug2, return_proj=True)
                p2 = p2_out[1] if isinstance(p2_out, tuple) else None # index 1 because return_proj is True? No, look at vesuvius_model.py
                # Wait, look at vesuvius_model.py: [ink_2d, fiber, qc, proj, st]
                # If only return_proj=True: [ink_2d, proj] -> index 1.
            else:
                p2 = None
            
            # Supervised Losses
            loss_ink = F.binary_cross_entropy_with_logits(out_ink_2d, target_ink_aug1, pos_weight=None, reduction='mean')
            if config.label_smoothing > 0:
                smoothed_target = target_ink_aug1 * (1.0 - config.label_smoothing) + 0.5 * config.label_smoothing
                loss_ink = F.binary_cross_entropy_with_logits(out_ink_2d, smoothed_target)
                
            loss_dice = compute_dice_loss(out_ink_2d, target_ink_aug1)
            
            loss_fiber = torch.tensor(0.0, device=device)
            if out_fiber is not None:
                out_fiber_2d = torch.mean(out_fiber, dim=2, keepdim=True)
                loss_fiber = F.binary_cross_entropy_with_logits(out_fiber_2d, target_fiber_aug1)
            
            loss_qc = torch.tensor(0.0, device=device)
            hallucination_penalty = torch.tensor(0.0, device=device)
            if out_qc is not None:
                target_qc = target_fiber_aug1.mean(dim=(-3, -2, -1)).squeeze()
                loss_qc = F.binary_cross_entropy_with_logits(out_qc.squeeze(-1), target_qc)
                B = out_ink_2d.shape[0]
                hallucination_penalty = (torch.sigmoid(out_ink_2d) * (1.0 - torch.sigmoid(out_qc).view(B, 1, 1, 1))).mean()
            
            loss_st_val = torch.tensor(0.0, device=device)
            if out_st is not None and target_st is not None:
                loss_st_val = F.mse_loss(out_st, target_st)
            
            consistency_loss = torch.tensor(0.0, device=device)
            if p1 is not None and p2 is not None:
                consistency_loss = 1.0 - F.cosine_similarity(p1, p2, dim=1).mean()
            
            total_loss = (config.loss_ink_bce * loss_ink + 
                          config.loss_ink_dice * loss_dice + 
                          config.loss_fiber_bce * loss_fiber + 
                          0.1 * loss_qc + 
                          0.02 * hallucination_penalty +
                          config.loss_st * loss_st_val +
                          0.05 * consistency_loss)

        if not torch.isfinite(total_loss) or total_loss.item() > 1e6:
            print(f"\n[WARNING] Numerical Instability at Step {step}: Loss {total_loss.item():.2e}")
            print(f"Ink: {loss_ink.item():.2e}, Dice: {loss_dice.item():.2e}, Fiber: {loss_fiber.item():.2e}, QC: {loss_qc.item():.2e}, ST: {loss_st.item():.2e}, Halluc: {hallucination_penalty.item():.2e}")
            optimizer.zero_grad(set_to_none=True)
            total_loss = torch.tensor(0.0, device=device, requires_grad=True)
        else:
            scaler.scale(total_loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()

        dt = time.time() - t0
        total_training_time += dt
        loss_val = total_loss.item()
        smooth_loss = 0.9 * smooth_loss + 0.1 * loss_val if step > 0 else loss_val

        if step % 10 == 0:
            remaining = max(0, config.time_budget - total_training_time)
            print(f"Step {step:04d} | Loss: {smooth_loss:.6f} | dt: {dt*1000:.0f}ms | Remaining: {remaining:.0f}s")
            sys.stdout.flush()

        step += 1
        if total_training_time >= config.time_budget: break

    print(f"Evaluating metrics on 100 stratified patches...")
    sys.stdout.flush()
    val_losses = []
    val_skel_dists = []
    val_centerline_dices = []
    val_cc_diffs = []
    model.eval()
    torch.manual_seed(42)
    with torch.no_grad():
        for val_idx in range(100):
            try:
                val_x_raw, val_target = next(val_data_iter)
                val_x = val_x_raw[:, :, 4:4+config.num_layers].to(device)
                if val_target is not None and val_target.numel() > 0:
                    val_target = val_target.to(device)
                    if val_target.dim() == 3: val_target = val_target.unsqueeze(1)
                    with autocast(device_type='cuda'): 
                        val_out = model(val_x)
                        if isinstance(val_out, tuple): out_2d = val_out[0]
                        else: out_2d = val_out

                    prob_2d = torch.sigmoid(out_2d)
                    val_dice = compute_official_dice(val_target, prob_2d, threshold=0.5)
                    val_losses.append(1.0 - val_dice)

                    # Per-patch cheap metrics: connected-components diff (~sub-ms)
                    try:
                        gt_bin_b = (val_target > 0.5).cpu().numpy().astype(bool)
                        pred_bin_b = (prob_2d > 0.5).cpu().numpy().astype(bool)
                        for b in range(gt_bin_b.shape[0]):
                            val_cc_diffs.append(compute_cc_diff(gt_bin_b[b, 0], pred_bin_b[b, 0]))
                    except Exception: pass

                    # Expensive topological metrics on a subset (20%): skel_dist + centerline_dice
                    if val_idx % 5 == 0:
                        try:
                            skel_dist = compute_skeleton_dist(val_target.cpu().numpy(), prob_2d.cpu().numpy())
                            if not np.isnan(skel_dist):
                                val_skel_dists.append(skel_dist)
                        except Exception: pass
                        try:
                            # centerline_dice iterates axis-0 as independent 2D slices
                            gt_3d = (val_target > 0.5).cpu().numpy()[:, 0].astype(bool)  # [B, H, W]
                            pred_3d = (prob_2d > 0.5).cpu().numpy()[:, 0].astype(bool)
                            cd = compute_centerline_dice(gt_3d, pred_3d, tolerance_radius=3.0)
                            cd_val = cd.get("centerline_dice", 0.0)
                            if not np.isnan(cd_val):
                                val_centerline_dices.append(cd_val)
                        except Exception: pass

            except StopIteration: val_data_iter = iter(val_data_loader)
            except Exception: continue

    val_bpb = np.mean(val_losses) if val_losses else 1.0
    avg_skel_dist = np.mean(val_skel_dists) if val_skel_dists else 1.0
    avg_centerline_dice = np.mean(val_centerline_dices) if val_centerline_dices else 0.0
    avg_cc_diff = np.mean(val_cc_diffs) if val_cc_diffs else 0.0
    log_file = 'results.tsv'
    is_improvement = True
    if np.isnan(val_bpb): is_improvement = False
    
    best_previous_val_bpb = 1.0
    if os.path.exists('best_model.pt'):
        try:
            chk = torch.load('best_model.pt', map_location='cpu', weights_only=False)
            best_previous_val_bpb = chk.get('val_bpb', 1.0)
        except Exception: pass
        
    if is_improvement and val_bpb >= best_previous_val_bpb:
        is_improvement = False

    peak_vram_mb = torch.cuda.max_memory_allocated() / 1024**2
    num_params_M = sum(p.numel() for p in model.parameters())/1e6
    throughput_Mvps = step * config.batch_size * config.num_layers * config.patch_size**2 / total_training_time / 1e6
    
    print("\n--- Foundation Pretraining Complete ---")
    print(f"val_bpb (Official):    {val_bpb:.6f} {'[NEW BEST]' if is_improvement else ''}")
    print(f"avg_skel_dist:         {avg_skel_dist:.6f}")
    print(f"avg_centerline_dice:   {avg_centerline_dice:.6f}")
    print(f"avg_cc_diff:           {avg_cc_diff:.3f}")
    print(f"train_loss:            {smooth_loss:.6f}")
    print(f"throughput_Mvps:       {throughput_Mvps:.2f}")
    sys.stdout.flush()

    if is_improvement:
        print(f"Saving new best model with val_bpb: {val_bpb:.6f}")
        torch.save({'model_state_dict': model.state_dict(), 'val_bpb': val_bpb, 'avg_skel_dist': avg_skel_dist, 'avg_centerline_dice': avg_centerline_dice, 'avg_cc_diff': avg_cc_diff, 'config': asdict(config)}, 'best_model.pt')

        header = "timestamp\tval_bpb\tavg_skel_dist\tavg_centerline_dice\tavg_cc_diff\ttrain_loss\tthroughput_Mvps\tnum_params_M\tpeak_vram_mb\tconfig\n"
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f:
                f.write(header)
                f.flush()
                os.fsync(f.fileno())

        with open(log_file, 'a') as f:
            cfg_json = json.dumps(asdict(config))
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{val_bpb:.6f}\t{avg_skel_dist:.6f}\t{avg_centerline_dice:.6f}\t{avg_cc_diff:.3f}\t{smooth_loss:.6f}\t{throughput_Mvps:.2f}\t{num_params_M:.3f}\t{peak_vram_mb:.1f}\t{cfg_json}\n")
            f.flush()
            os.fsync(f.fileno())
            
        try:
            from plot_results import plot_results
            plot_results()
        except Exception: pass
        
        # Ensure filesystem sync
        if hasattr(os, 'sync'):
            os.sync()
    
    if not is_improvement: print("\n[RESULT] No improvement detected. Recommended: Revert.")
    else: print("\n[RESULT] Improvement detected! Recommended: Keep changes.")

    result_data = {
        "val_bpb": float(val_bpb),
        "avg_skel_dist": float(avg_skel_dist),
        "avg_centerline_dice": float(avg_centerline_dice),
        "avg_cc_diff": float(avg_cc_diff),
        "train_loss": float(smooth_loss),
        "throughput_Mvps": float(throughput_Mvps),
        "num_params_M": float(num_params_M),
        "peak_vram_mb": float(peak_vram_mb),
        "is_success": bool(is_improvement)
    }
    
    # Write run_result.json as the VERY LAST step
    with open("run_result.json", "w") as f:
        json.dump(result_data, f, indent=4)
        f.flush()
        os.fsync(f.fileno())

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="config.json", help="Path to configuration JSON")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    
    if os.path.exists(args.config):
        config = ExperimentConfig.load(args.config)
    else:
        config = ExperimentConfig()
        config.save(args.config)
        
    if args.test: 
        config.time_budget = 30
        train(config)
    else: 
        train(config)
