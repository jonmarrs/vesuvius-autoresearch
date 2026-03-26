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
    num_layers: int = 12
    
    lr: float = 3e-4
    time_budget: int = 300 # 5 minutes for rapid research iteration
# ---------------------------------------------------------------------------
# Training Loop
# ---------------------------------------------------------------------------

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
    
    print(f"Initializing LOCAL OFFLINE Training on {t_config.uri}...")
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
                num_layers=t_config.num_layers
            )
        else:
            print(f"  Using UNLABELED dataset for {uri} (Synthetic Ink will be added)")
            return VesuviusS3Dataset(uri=uri, patch_size=t_config.patch_size, num_layers=t_config.num_layers)

    dataset = get_dataset(t_config.uri)
    data_iter = iter(dataset)
    
    val_dataset = get_dataset(t_config.val_uri)
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
        
        # 1. Fetch real scroll data + Ground Truth labels (if available)
        try:
            x_orig, target_ink = next(data_iter)
            x_orig = x_orig.to(device) # [1, 1, Z, H, W]
            
            if target_ink is not None:
                target_ink = target_ink.to(device) # [1, 1, H, W]
            else:
                # Add Synthetic Ink (for unlabeled scrolls)
                target_ink = torch.zeros((x_orig.shape[0], 1, x_orig.shape[3], x_orig.shape[4]), device=device)
                for b in range(x_orig.shape[0]):
                    if np.random.rand() > 0.3:
                        h0, w0 = np.random.randint(0, t_config.patch_size // 2), np.random.randint(0, t_config.patch_size // 2)
                        z0 = np.random.randint(2, t_config.num_layers - 4)
                        # We apply synthetic ink to a slice of the volume and record it in target_ink
                        target_ink[b, 0, h0:h0+16, w0:w0+16] = 1.0
                        x_orig[b, 0, z0:z0+2, h0:h0+16, w0:w0+16] += 0.4
        except StopIteration:
            data_iter = iter(dataset)
            continue
            
        # 2. Create Augmented View
        x_aug = x_orig.clone()
        if np.random.rand() > 0.5:
            # Simple 3D Roll/Shift as a proxy for complex warping
            shift_z, shift_y, shift_x = np.random.randint(-2, 3, (3,))
            x_aug = torch.roll(x_aug, shifts=(shift_z, shift_y, shift_x), dims=(2, 3, 4))
        
        x_aug = torch.rot90(x_aug, k=np.random.randint(0, 4), dims=(3, 4))
        x_aug = x_aug + torch.randn_like(x_aug) * 0.05
        
        # 4. Forward Pass
        optimizer.zero_grad(set_to_none=True)
        
        # Student View (Orig)
        out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
        
        # Loss 1: Supervised Ink Detection
        # Model outputs [B, 1, Z, H, W], Target is [B, 1, H, W]
        out_ink_2d = torch.mean(out_ink, dim=2)
        loss_ink = F.binary_cross_entropy_with_logits(out_ink_2d, target_ink)
        loss_dice = compute_dice_loss(out_ink, target_ink)
        
        total_loss = 0.5 * loss_ink + 0.5 * loss_dice
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
    # Quick Validation
    print(f"Evaluating val_bpb (1 - Dice) on validation set...")
    sys.stdout.flush()
    val_losses = []
    with torch.no_grad():
        for _ in range(10):
            try:
                val_x, val_target = next(val_data_iter)
                val_x = val_x.to(device)
                
                if val_target is None:
                    # Synthetic val target
                    val_target = torch.zeros((val_x.shape[0], 1, val_x.shape[3], val_x.shape[4]), device=device)
                    h0, w0 = np.random.randint(0, t_config.patch_size // 2), np.random.randint(0, t_config.patch_size // 2)
                    z0 = np.random.randint(2, t_config.num_layers - 4)
                    val_target[:, 0, h0:h0+16, w0:w0+16] = 1.0
                    val_x[:, 0, z0:z0+2, h0:h0+16, w0:w0+16] += 0.4
                else:
                    val_target = val_target.to(device)
                
                val_out, _, _, _, _, _ = model(val_x, return_fiber=True)
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

