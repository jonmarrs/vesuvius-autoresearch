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

# Import our breakthrough components
from vesuvius_model import InkDetectorOptimized, VesuviusConfig
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
    
    # Training Loop
    batch_size: int = 16 
    patch_size: int = 64
    num_layers: int = 24 
    lr: float = 1e-3
    weight_decay: float = 0.01
    time_budget: int = 900 
    
    # Loss Weights
    loss_ink_bce: float = 0.4
    loss_ink_dice: float = 0.4
    loss_fiber_bce: float = 0.2

    # Model Architecture
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

def apply_augmentations(x, target_ink, target_fiber, step, max_steps):
    """Applies randomized 3D augmentations to a volume patch."""
    k_rot = np.random.randint(0, 4)
    x_aug = torch.rot90(x, k=k_rot, dims=(-2, -1))
    target_ink_aug = torch.rot90(target_ink, k=k_rot, dims=(-2, -1)).clamp(0, 1)
    target_fiber_aug = torch.rot90(target_fiber, k=k_rot, dims=(-2, -1)).clamp(0, 1)

    # Z-Axis Random Flip
    if np.random.rand() > 0.5:
        x_aug = torch.flip(x_aug, dims=[2])
        
    # Intensity Jitter
    if np.random.rand() > 0.5:
        brightness = 1.0 + (np.random.rand() - 0.5) * 0.2
        contrast = 1.0 + (np.random.rand() - 0.5) * 0.2
        x_aug = (x_aug * contrast) + (brightness - 1.0)
        
    # Dynamic Gaussian Noise
    noise_level = 0.01 + 0.02 * (min(step, max_steps) / max_steps)
    x_aug = x_aug + torch.randn_like(x_aug) * noise_level
    
    return x_aug, target_ink_aug, target_fiber_aug

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
        dropout=config.dropout
    )

    print(f"Initializing LOCAL TRANSFORMER Training on {config.uri}...")
    sys.stdout.flush()

    def get_dataloader(uri, seed=None):
        parent_dir = os.path.dirname(uri.rstrip('/'))
        labels_path = os.path.join(parent_dir, 'inklabels.png')
        mask_path = os.path.join(parent_dir, 'mask.png')
        if os.path.exists(labels_path):
            ds = VesuviusLabeledDataset(uri, labels_path, mask_path if os.path.exists(mask_path) else None, config.patch_size, config.num_layers + 8, seed=seed, cache_dir=config.cache_dir)
        else:
            ds = VesuviusS3Dataset(uri, config.patch_size, config.num_layers + 8, seed=seed, cache_dir=config.cache_dir)
        return DataLoader(ds, batch_size=config.batch_size, num_workers=min(4, os.cpu_count() or 1), pin_memory=True)

    data_loader = get_dataloader(config.uri)
    data_iter = iter(data_loader)
    # Use fixed seed and num_workers=0 for validation to ensure absolute determinism
    def get_val_dataloader(uri):
        parent_dir = os.path.dirname(uri.rstrip('/'))
        labels_path = os.path.join(parent_dir, 'inklabels.png')
        mask_path = os.path.join(parent_dir, 'mask.png')
        ds = VesuviusLabeledDataset(uri, labels_path, mask_path if os.path.exists(mask_path) else None, config.patch_size, config.num_layers + 8, seed=42, cache_dir=config.cache_dir)
        return DataLoader(ds, batch_size=config.batch_size, num_workers=0, pin_memory=True)

    val_data_loader = get_val_dataloader(config.val_uri)
    val_data_iter = iter(val_data_loader)

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
                z_len = np.random.randint(min_len, max_len + 1)
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
        x_aug1, target_ink_aug1, target_fiber_aug1 = apply_augmentations(x_orig, target_ink, target_fiber, step, max_steps)
        x_aug2, _, _ = apply_augmentations(x_orig, target_ink, target_fiber, step, max_steps)

        optimizer.zero_grad(set_to_none=True)
        with autocast(device_type='cuda'):
            # Forward pass for view 1 (full multi-task)
            out_ink_2d, out_fiber, out_qc, p1 = model(x_aug1, return_fiber=True, return_qc=True, return_proj=True)
            
            # Forward pass for view 2 (projection only)
            _, p2 = model(x_aug2, return_proj=True)
            
            # Supervised Losses (on view 1)
            loss_ink = F.binary_cross_entropy_with_logits(out_ink_2d, target_ink_aug1)
            loss_dice = compute_dice_loss(out_ink_2d, target_ink_aug1)
            out_fiber_2d = torch.mean(out_fiber, dim=2, keepdim=True)
            loss_fiber = F.binary_cross_entropy_with_logits(out_fiber_2d, target_fiber_aug1)
            
            target_qc = target_fiber_aug1.mean(dim=(-3, -2, -1)).squeeze()
            loss_qc = F.binary_cross_entropy_with_logits(out_qc.squeeze(-1), target_qc)
            
            B = out_ink_2d.shape[0]
            hallucination_penalty = (torch.sigmoid(out_ink_2d) * (1.0 - torch.sigmoid(out_qc).view(B, 1, 1, 1))).mean()
            
            # Self-Supervised Consistency Loss (DINO-Lite)
            consistency_loss = 1.0 - F.cosine_similarity(p1, p2, dim=1).mean()
            
            total_loss = (config.loss_ink_bce * loss_ink + 
                          config.loss_ink_dice * loss_dice + 
                          config.loss_fiber_bce * loss_fiber + 
                          0.1 * loss_qc + 
                          0.2 * hallucination_penalty +
                          0.1 * consistency_loss)

        if not torch.isfinite(total_loss) or total_loss.item() > 1e6:
            print(f"\n[WARNING] Numerical Instability at Step {step}: Loss {total_loss.item():.2e}")
            print(f"Ink: {loss_ink.item():.2e}, Dice: {loss_dice.item():.2e}, Fiber: {loss_fiber.item():.2e}, QC: {loss_qc.item():.2e}, Halluc: {hallucination_penalty.item():.2e}")
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

    # 4. Stratified 100-patch validation
    print(f"Evaluating val_bpb (1 - Dice) on 100 stratified patches...")
    sys.stdout.flush()
    val_losses = []
    model.eval()
    torch.manual_seed(42) 
    with torch.no_grad():
        for _ in range(100): 
            try:
                val_x_raw, val_target = next(val_data_iter)
                val_x = val_x_raw[:, :, 4:4+config.num_layers].to(device)
                if val_target is not None and val_target.numel() > 0:
                    val_target = val_target.to(device)
                    if val_target.dim() == 3: val_target = val_target.unsqueeze(1)
                    with autocast(device_type='cuda'): out_2d = model(val_x)
                    val_losses.append(1.0 - compute_hard_dice(out_2d, val_target).item())
            except StopIteration: val_data_iter = iter(val_data_loader)
            except Exception: continue

    val_bpb = np.mean(val_losses) if val_losses else 1.0
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
    print(f"val_bpb:          {val_bpb:.6f} {'[NEW BEST]' if is_improvement else ''}")
    print(f"train_loss:       {smooth_loss:.6f}")
    print(f"throughput_Mvps:  {throughput_Mvps:.2f}")
    sys.stdout.flush()

    if is_improvement:
        print(f"Saving new best model with val_bpb: {val_bpb:.6f}")
        torch.save({'model_state_dict': model.state_dict(), 'val_bpb': val_bpb, 'config': asdict(config)}, 'best_model.pt')
        
        header = "timestamp\tval_bpb\ttrain_loss\tthroughput_Mvps\tnum_params_M\tpeak_vram_mb\tconfig\n"
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f: 
                f.write(header)
                f.flush()
                os.fsync(f.fileno())
        
        with open(log_file, 'a') as f:
            cfg_json = json.dumps(asdict(config))
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{val_bpb:.6f}\t{smooth_loss:.6f}\t{throughput_Mvps:.2f}\t{num_params_M:.3f}\t{peak_vram_mb:.1f}\t{cfg_json}\n")
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
