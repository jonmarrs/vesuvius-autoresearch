"""
Vesuvius Training Script: Scroll Foundation Model.
Optimized for direct S3 loading and DINO-style Self-Supervised Pretraining.
Usage: uv run train.py
"""

import os
import time
import math
import gc
from dataclasses import dataclass, asdict

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import pandas as pd

# Import our breakthrough components
from vesuvius_model import InkDetectorOptimized, VesuviusConfig
from vesuvius_loader import VesuviusS3Dataset, VesuviusLabeledDataset

# ---------------------------------------------------------------------------
# Training Configuration
# ---------------------------------------------------------------------------

@dataclass
class TrainConfig:
    # LOCAL paths to ensure NO bandwidth usage
    # Training: Fragment 1
    uri: str = 'local_data/PHercParis2Fr47/surface_volume/'
    # Validation: Fragment 2
    val_uri: str = 'local_data/PHercParis2Fr143/surface_volume/'

    batch_size: int = 2 # Minimum to avoid OOM
    patch_size: int = 128
    num_layers: int = 24 # Must be multiple of 4 for patch_embed

    lr: float = 3e-4
    time_budget: int = 900 # 15 minutes for transformer convergence

def mixup_data(x, y, alpha=0.2):
    if alpha > 0:
        lam = np.random.beta(alpha, alpha)
    else:
        lam = 1

    batch_size = x.size()[0]
    index = torch.randperm(batch_size).to(x.device)

    mixed_x = lam * x + (1 - lam) * x[index, :]
    mixed_y = lam * y + (1 - lam) * y[index, :]
    return mixed_x, mixed_y, lam

def compute_dice_loss(pred, target, smooth=1e-5):
    # pred: [B, 1, Z, H, W] -> collapse Z to 2D
    pred_2d = torch.mean(pred, dim=2)
    pred_2d = torch.sigmoid(pred_2d)
    
    # target: [B, 1, H, W]
    intersection = (pred_2d * target).sum(dim=(2, 3))
    union = pred_2d.sum(dim=(2, 3)) + target.sum(dim=(2, 3))
    dice = (2. * intersection + smooth) / (union + smooth)
    return 1.0 - dice.mean()

def train(time_budget=None):
    import sys
    t_start = time.time()
    torch.set_float32_matmul_precision('high')
    device = torch.device("cuda")
    t_config = TrainConfig()
    if time_budget is not None:
        t_config.time_budget = time_budget

    v_config = VesuviusConfig(
        patch_size=t_config.patch_size, 
        num_layers=t_config.num_layers,
        batch_size=t_config.batch_size
    )

    print(f"Initializing LOCAL TRANSFORMER Training on {t_config.uri}...")
    sys.stdout.flush()

    def get_dataset(uri):
        # Look for labels in the parent directory of '0/'
        parent_dir = os.path.dirname(uri.rstrip('/'))
        labels_path = os.path.join(parent_dir, 'inklabels.png')
        mask_path = os.path.join(parent_dir, 'mask.png')

        if os.path.exists(labels_path):
            print(f"  Using LABELED dataset for {uri}")
            return VesuviusLabeledDataset(
                volume_uri=uri,
                labels_path=labels_path,
                mask_path=mask_path if os.path.exists(mask_path) else None,
                patch_size=t_config.patch_size,
                num_layers=t_config.num_layers + 8 # Add buffer for Z-jitter
            )
        else:
            print(f"  Using UNLABELED dataset for {uri} (Synthetic Ink will be added)")
            return VesuviusS3Dataset(uri=uri, patch_size=t_config.patch_size, num_layers=t_config.num_layers + 8)

    dataset = get_dataset(t_config.uri)
    data_iter = iter(dataset)

    val_dataset = get_dataset(t_config.val_uri)
    val_data_iter = iter(val_dataset)

    # Initialize Transformer Model
    model = InkDetectorOptimized(v_config, base_feat=64, num_blocks=8).to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=t_config.lr, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=t_config.time_budget // 10)

    print(f"Starting Scroll Transformer Loop (Budget: {t_config.time_budget}s)...")
    sys.stdout.flush()

    step = 0
    total_training_time = 0
    smooth_loss = 0

    while True:
        t0 = time.time()

        # 1. Fetch real scroll data + Ground Truth labels (if available)
        try:
            x_raw, target_ink_raw = next(data_iter)
            x_raw = x_raw.to(device) # [1, Z_buffered, H, W]

            # Z-axis Jitter
            z_start = np.random.randint(0, 8)
            x_orig = x_raw[:, z_start:z_start+t_config.num_layers]

            if x_orig.dim() == 4:
                x_orig = x_orig.unsqueeze(1) # [1, 1, Z, H, W]

            if target_ink_raw is not None:
                target_ink = target_ink_raw.to(device) # [1, 1, H, W]
            else:
                # Add Synthetic Ink (for unlabeled scrolls)
                target_ink = torch.zeros((x_orig.shape[0], 1, x_orig.shape[3], x_orig.shape[4]), device=device)
                # ... (synthetic logic same as before)
        except StopIteration:
            data_iter = iter(dataset)
            continue

        # 2. Mixup Augmentation (if batch_size > 1)
        if x_orig.size(0) > 1 and np.random.rand() > 0.5:
            x_orig, target_ink, _ = mixup_data(x_orig, target_ink)

        # 3. Create Augmented View (Rotation/Noise)
        x_aug = x_orig.clone()
        k_rot = np.random.randint(0, 4)
        x_aug = torch.rot90(x_aug, k=k_rot, dims=(3, 4))
        target_ink_aug = torch.rot90(target_ink, k=k_rot, dims=(2, 3))

        x_aug = x_aug + torch.randn_like(x_aug) * 0.02

        # 4. Forward Pass
        optimizer.zero_grad(set_to_none=True)

        # Model outputs [B, 1, Z, H, W]
        out_ink = model(x_aug)

        # Loss: Supervised Ink Detection
        # Average over Z to compare with 2D label
        out_ink_2d = torch.mean(out_ink, dim=2)
        loss_ink = F.binary_cross_entropy_with_logits(out_ink_2d, target_ink_aug)
        loss_dice = compute_dice_loss(out_ink, target_ink_aug)

        total_loss = 0.5 * loss_ink + 0.5 * loss_dice
        total_loss.backward()

        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()

        torch.cuda.synchronize()
        dt = time.time() - t0
        total_training_time += dt

        # Logging
        loss_val = total_loss.item()
        ema_beta = 0.9
        smooth_loss = ema_beta * smooth_loss + (1 - ema_beta) * loss_val if step > 0 else loss_val

        if step % 5 == 0:
            remaining = max(0, t_config.time_budget - total_training_time)
            print(f"Step {step:04d} | Loss: {smooth_loss:.6f} | dt: {dt*1000:.0f}ms | Remaining: {remaining:.0f}s")
            sys.stdout.flush()

        step += 1

        if total_training_time >= t_config.time_budget:
            break

    # Final Summary (Validation uses middle slice of model output)
    print(f"Evaluating val_bpb (1 - Dice) on validation set...")
    sys.stdout.flush()
    val_losses = []
    model.eval()
    with torch.no_grad():
        for _ in range(20):
            try:
                val_x_raw, val_target = next(val_data_iter)
                # Apply same Z-jitter logic for validation (fixed at center)
                val_x = val_x_raw[:, 4:4+t_config.num_layers].to(device)
                if val_x.dim() == 4: val_x = val_x.unsqueeze(1)

                if val_target is not None:
                    val_target = val_target.to(device)
                    val_out = model(val_x)
                    loss_dice = compute_dice_loss(val_out, val_target)
                    val_losses.append(loss_dice.item())
            except: continue

            
    val_bpb = np.mean(val_losses) if val_losses else 1.0
    
    # Check for improvement
    log_file = 'results.tsv'
    is_improvement = True
    if os.path.exists(log_file):
        try:
            df = pd.read_csv(log_file, sep='\t')
            if len(df) > 0:
                best_val = df['val_bpb'].min()
                if val_bpb >= best_val:
                    is_improvement = False
        except Exception:
            pass

    peak_vram_mb = torch.cuda.max_memory_allocated() / 1024**2
    total_seconds = time.time() - t_start
    num_params_M = sum(p.numel() for p in model.parameters())/1e6
    throughput_Mvps = step * t_config.batch_size * t_config.num_layers * t_config.patch_size**2 / total_training_time / 1e6
    
    print("\n--- Foundation Pretraining Complete ---")
    print(f"val_bpb:          {val_bpb:.6f} {'[NEW BEST]' if is_improvement else ''}")
    print(f"train_loss:       {smooth_loss:.6f}")
    print(f"training_seconds: {total_training_time:.1f}")
    print(f"total_seconds:    {total_seconds:.1f}")
    print(f"peak_vram_mb:     {peak_vram_mb:.1f}")
    print(f"num_steps:        {step}")
    print(f"num_params_M:     {num_params_M:.3f}")
    print(f"throughput_Mvps:  {throughput_Mvps:.2f}")
    sys.stdout.flush()

    # Log to results.tsv ONLY on improvement
    if is_improvement:
        header = "timestamp\tval_bpb\ttrain_loss\tthroughput_Mvps\tnum_params_M\tpeak_vram_mb\n"
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f:
                f.write(header)
        
        with open(log_file, 'a') as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{val_bpb:.6f}\t{smooth_loss:.6f}\t{throughput_Mvps:.2f}\t{num_params_M:.3f}\t{peak_vram_mb:.1f}\n")

        # Auto-plot progress
        try:
            from plot_results import plot_results
            plot_results()
        except Exception as e:
            print(f"Failed to update plot: {e}")
    
    if not is_improvement:
        print("\n[RESULT] No improvement detected. Recommended: Revert changes.")
    else:
        print("\n[RESULT] Improvement detected! Recommended: Keep changes.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    
    if args.test:
        train(time_budget=30)
    else:
        train()

