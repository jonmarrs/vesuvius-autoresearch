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
from vesuvius_loader import VesuviusS3Dataset

# ---------------------------------------------------------------------------
# Training Configuration
# ---------------------------------------------------------------------------

@dataclass
class TrainConfig:
    # Full URI for Scroll 1 (PHerc0139) - Training
    uri: str = 's3://vesuvius-challenge-open-data/PHerc0139/volumes/20260102150214-2.399um-0.2m-78keV-masked.zarr/0/'
    # Full URI for Scroll 5 (PHerc0172) - Validation
    val_uri: str = 's3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/'
    
    batch_size: int = 2 # Minimum to avoid OOM
    patch_size: int = 64
    num_layers: int = 12
    
    lr: float = 3e-4
    time_budget: int = 300 # 5 minutes for rapid research iteration
    
# ---------------------------------------------------------------------------
# Training Loop
# ---------------------------------------------------------------------------

def compute_dice_loss(pred, target, smooth=1e-5):
    pred = torch.sigmoid(pred)
    intersection = (pred * target).sum(dim=(2, 3, 4))
    union = pred.sum(dim=(2, 3, 4)) + target.sum(dim=(2, 3, 4))
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
    
    print(f"Initializing Vesuvius Autoresearch Training on {t_config.uri}...")
    sys.stdout.flush()
    
    # Initialize Loader (Streams from AWS)
    dataset = VesuviusS3Dataset(uri=t_config.uri, patch_size=t_config.patch_size, num_layers=t_config.num_layers)
    data_iter = iter(dataset)
    
    print(f"Initializing Validation Loader on {t_config.val_uri}...")
    val_dataset = VesuviusS3Dataset(uri=t_config.val_uri, patch_size=t_config.patch_size, num_layers=t_config.num_layers)
    val_data_iter = iter(val_dataset)
    
    # Initialize Model with larger base_feat and more blocks
    model = InkDetectorOptimized(v_config, base_feat=32, num_blocks=10).to(device)
    # model = torch.compile(model) # Disabled for stability in multi-task mode
    
    optimizer = torch.optim.AdamW(model.parameters(), lr=t_config.lr, weight_decay=0.001)
    
    print(f"Starting Scroll Foundation Loop (Budget: {t_config.time_budget}s)...")
    sys.stdout.flush()
    
    step = 0
    total_training_time = 0
    smooth_loss = 0
    
    while True:
        t0 = time.time()
        
        # 1. Fetch real scroll data from S3 (Standard View)
        batch_x = []
        for _ in range(t_config.batch_size):
            batch_x.append(next(data_iter))
        x_orig = torch.stack(batch_x).to(device) # [B, 1, Z, H, W]
        
        # 2. Create Augmented View (for DINO self-distillation)
        # Scroll-Specific Augmentations (Addressing Community Issue #201)
        x_aug = x_orig.clone()
        
        # A. Random Non-Rigid Warping (mimics crinkled papyrus)
        if np.random.rand() > 0.5:
            # Simple 3D Roll/Shift as a proxy for complex warping in this budget
            shift_z, shift_y, shift_x = np.random.randint(-2, 3, (3,))
            x_aug = torch.roll(x_aug, shifts=(shift_z, shift_y, shift_x), dims=(2, 3, 4))
            
        # B. Layer Ghosting (mimics interlayer crosstalk)
        if np.random.rand() > 0.3:
            ghost = torch.roll(x_orig, shifts=(np.random.randint(1, 4),), dims=(2,))
            x_aug = x_aug + ghost * 0.2
            
        # C. Standard Augs
        x_aug = torch.rot90(x_aug, k=np.random.randint(0, 4), dims=(3, 4))
        x_aug = x_aug + torch.randn_like(x_aug) * 0.05
        if np.random.rand() > 0.5:
            drop_idx = np.random.randint(0, t_config.num_layers, (2,))
            x_aug[:, :, drop_idx] = 0.0
            
        # 3. Add Synthetic Ink to BOTH views (Supervised Component)
        target_ink = torch.zeros_like(x_orig)
        for b in range(t_config.batch_size):
            if np.random.rand() > 0.3:
                h0, w0 = np.random.randint(0, t_config.patch_size // 2), np.random.randint(0, t_config.patch_size // 2)
                z0 = np.random.randint(2, t_config.num_layers - 4)
                target_ink[b, :, z0:z0+2, h0:h0+16, w0:w0+16] = 1.0
                x_orig[b] = x_orig[b] + target_ink[b] * 0.4
        
        # 4. Forward Pass
        optimizer.zero_grad(set_to_none=True)
        
        # Student View (Orig)
        out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
        # Teacher View (Augmented)
        with torch.no_grad():
            _, feat_teacher, _, _, _, _ = model(x_aug, return_fiber=True)
            
        # Loss 1: Supervised Ink Detection
        loss_ink = F.binary_cross_entropy_with_logits(out_ink, target_ink)
        
        # Loss 2: DINO Feature Consistency (Self-Supervised)
        loss_dino = F.mse_loss(feat_student, feat_teacher)
        
        total_loss = loss_ink + 0.5 * loss_dino
        total_loss.backward()
        
        optimizer.step()
        
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
            
    # Final Summary
    # Quick Validation on a separate chunk (Scroll 5)
    print("Evaluating val_bpb (1 - Dice) on validation chunk (PHerc. 0172)...")
    sys.stdout.flush()
    val_losses = []
    with torch.no_grad():
        for _ in range(5):
            val_x = next(val_data_iter).to(device).unsqueeze(0)
            
            # Use synthetic target for simplicity in baseline evaluation
            val_target = torch.zeros_like(val_x)
            for b in range(val_x.shape[0]):
                if np.random.rand() > 0.3:
                    h0, w0 = np.random.randint(0, t_config.patch_size // 2), np.random.randint(0, t_config.patch_size // 2)
                    z0 = np.random.randint(2, t_config.num_layers - 4)
                    val_target[b, :, z0:z0+2, h0:h0+16, w0:w0+16] = 1.0
                    val_x[b] = val_x[b] + val_target[b] * 0.4
                    
            val_out, _, _, _, _, _ = model(val_x, return_fiber=True)
            loss_dice = compute_dice_loss(val_out, val_target)
            val_losses.append(loss_dice.item())
            
    val_bpb = np.mean(val_losses)
    
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

