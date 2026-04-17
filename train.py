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
    
    # 1. Step-Consistent Scheduler
    max_steps = 15000 
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.lr, weight_decay=config.weight_decay)
    
    warmup_steps = 1000
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

        k_rot = np.random.randint(0, 4)
        x_aug = torch.rot90(x_orig, k=k_rot, dims=(-2, -1))
        target_ink_aug = torch.rot90(target_ink, k=k_rot, dims=(-2, -1)).clamp(0, 1)
        target_fiber_aug = torch.rot90(target_fiber, k=k_rot, dims=(-2, -1)).clamp(0, 1)
        x_aug = x_aug + torch.randn_like(x_aug) * 0.01

        optimizer.zero_grad(set_to_none=True)
        with autocast(device_type='cuda'):
            # InkDetectorOptimized forward returns (ink_2d, fiber, qc)
            out_ink_2d, out_fiber, out_qc = model(x_aug, return_fiber=True, return_qc=True)
            loss_ink = F.binary_cross_entropy_with_logits(out_ink_2d, target_ink_aug)
            loss_dice = compute_dice_loss(out_ink_2d, target_ink_aug)
            out_fiber_2d = torch.mean(out_fiber, dim=2, keepdim=True)
            loss_fiber = F.binary_cross_entropy_with_logits(out_fiber_2d, target_fiber_aug)
            
            # QC Head Supervision: Predict the mean structural complexity of the patch
            target_qc = target_fiber_aug.mean(dim=(-3, -2, -1)).squeeze()
            loss_qc = F.binary_cross_entropy_with_logits(out_qc.squeeze(-1), target_qc)
            
            total_loss = config.loss_ink_bce * loss_ink + config.loss_ink_dice * loss_dice + config.loss_fiber_bce * loss_fiber + 0.1 * loss_qc

        if not torch.isfinite(total_loss) or total_loss.item() > 1e6:
            print(f"\n[WARNING] Numerical Instability at Step {step}: Loss {total_loss.item():.2e}")
            print(f"Ink: {loss_ink.item():.2e}, Dice: {loss_dice.item():.2e}, Fiber: {loss_fiber.item():.2e}, QC: {loss_qc.item():.2e}")
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
    
    if is_improvement and os.path.exists(log_file):
        try:
            df = pd.read_csv(log_file, sep='\t')
            if len(df) > 0 and val_bpb >= df['val_bpb'].dropna().min(): is_improvement = False
        except Exception: pass

    peak_vram_mb = torch.cuda.max_memory_allocated() / 1024**2
    num_params_M = sum(p.numel() for p in model.parameters())/1e6
    throughput_Mvps = step * config.batch_size * config.num_layers * config.patch_size**2 / total_training_time / 1e6
    
    print("\n--- Foundation Pretraining Complete ---")
    print(f"val_bpb:          {val_bpb:.6f} {'[NEW BEST]' if is_improvement else ''}")
    print(f"train_loss:       {smooth_loss:.6f}")
    print(f"throughput_Mvps:  {throughput_Mvps:.2f}")
    sys.stdout.flush()

    if is_improvement:
        torch.save({'model_state_dict': model.state_dict(), 'val_bpb': val_bpb, 'config': asdict(config)}, 'best_model.pt')
        header = "timestamp\tval_bpb\ttrain_loss\tthroughput_Mvps\tnum_params_M\tpeak_vram_mb\tconfig\n"
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f: f.write(header)
        with open(log_file, 'a') as f:
            cfg_json = json.dumps(asdict(config))
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{val_bpb:.6f}\t{smooth_loss:.6f}\t{throughput_Mvps:.2f}\t{num_params_M:.3f}\t{peak_vram_mb:.1f}\t{cfg_json}\n")
        try:
            from plot_results import plot_results
            plot_results()
        except Exception: pass
    
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
    with open("run_result.json", "w") as f:
        json.dump(result_data, f, indent=4)

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
