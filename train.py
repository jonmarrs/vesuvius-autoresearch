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
from torch.utils.data import DataLoader
from torch.cuda.amp import GradScaler, autocast

# Import our breakthrough components
from vesuvius_model import InkDetectorOptimized, VesuviusConfig
from vesuvius_loader import VesuviusS3Dataset, VesuviusLabeledDataset

# ---------------------------------------------------------------------------
# Training Configuration
# ---------------------------------------------------------------------------

@dataclass
class TrainConfig:
    # LOCAL paths to ensure NO bandwidth usage
    uri: str = 'local_data/PHercParis2Fr47/surface_volume/'
    val_uri: str = 'local_data/PHercParis2Fr143/surface_volume/'

    batch_size: int = 16 
    patch_size: int = 64
    num_layers: int = 24 

    lr: float = 1e-3
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

def cutmix_data(x, y, alpha=1.0):
    if alpha > 0:
        lam = np.random.beta(alpha, alpha)
    else:
        lam = 1
    batch_size = x.size()[0]
    index = torch.randperm(batch_size).to(x.device)

    W = x.size(4)
    H = x.size(3)
    cut_rat = np.sqrt(1. - lam)
    cut_w = int(W * cut_rat)
    cut_h = int(H * cut_rat)

    cx = np.random.randint(W)
    cy = np.random.randint(H)

    bbx1 = np.clip(cx - cut_w // 2, 0, W)
    bby1 = np.clip(cy - cut_h // 2, 0, H)
    bbx2 = np.clip(cx + cut_w // 2, 0, W)
    bby2 = np.clip(cy + cut_h // 2, 0, H)

    x[:, :, :, bby1:bby2, bbx1:bbx2] = x[index, :, :, bby1:bby2, bbx1:bbx2]
    y[:, :, bby1:bby2, bbx1:bbx2] = y[index, :, bby1:bby2, bbx1:bbx2]
    
    return x, y, lam

def compute_dice_loss(pred, target, smooth=1e-5):
    # pred: [B, 1, Z, H, W] -> collapse Z to 2D
    pred_2d = torch.mean(pred, dim=2)
    pred_2d = torch.sigmoid(pred_2d)
    
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

    def get_dataloader(uri):
        parent_dir = os.path.dirname(uri.rstrip('/'))
        labels_path = os.path.join(parent_dir, 'inklabels.png')
        mask_path = os.path.join(parent_dir, 'mask.png')

        if os.path.exists(labels_path):
            print(f"  Using LABELED dataset for {uri}")
            ds = VesuviusLabeledDataset(
                volume_uri=uri,
                labels_path=labels_path,
                mask_path=mask_path if os.path.exists(mask_path) else None,
                patch_size=t_config.patch_size,
                num_layers=t_config.num_layers + 8 
            )
        else:
            print(f"  Using UNLABELED dataset for {uri}")
            ds = VesuviusS3Dataset(uri=uri, patch_size=t_config.patch_size, num_layers=t_config.num_layers + 8)

        num_workers = min(4, os.cpu_count() or 1)
        return DataLoader(ds, batch_size=t_config.batch_size, num_workers=num_workers, pin_memory=True)

    data_loader = get_dataloader(t_config.uri)
    data_iter = iter(data_loader)

    val_data_loader = get_dataloader(t_config.val_uri)
    val_data_iter = iter(val_data_loader)

    # Initialize Transformer Model
    model = InkDetectorOptimized(v_config, base_feat=32, num_blocks=8).to(device)

    # Step-Consistent Optimizer & Scheduler
    max_steps = 15000 # Tuned for 4090 throughput
    optimizer = torch.optim.AdamW(model.parameters(), lr=t_config.lr, weight_decay=0.01)
    
    # scheduler with 1000 step warmup
    warmup_steps = 1000
    def lr_lambda(current_step: int):
        if current_step < warmup_steps:
            return float(current_step) / float(max(1, warmup_steps))
        return 0.5 * (1.0 + math.cos(math.pi * (current_step - warmup_steps) / float(max(1, max_steps - warmup_steps))))
    
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
    scaler = GradScaler()

    print(f"Starting Scroll Transformer Loop (Budget: {t_config.time_budget}s)...")
    sys.stdout.flush()

    step = 0
    total_training_time = 0
    smooth_loss = 0

    while True:
        t0 = time.time()

        try:
            x_raw, target_ink_raw = next(data_iter)
            x_raw = x_raw.to(device) # [B, 1, Z_buffered, H, W]

            # Z-axis Jitter
            z_start = np.random.randint(0, 8)
            x_orig = x_raw[:, :, z_start:z_start+t_config.num_layers]

            if target_ink_raw is not None and target_ink_raw.numel() > 0:
                target_ink = target_ink_raw.to(device) # [B, 1, H, W]
            else:
                target_ink = torch.zeros((x_orig.shape[0], 1, x_orig.shape[3], x_orig.shape[4]), device=device)
        except StopIteration:
            data_iter = iter(data_loader)
            continue

        # --- Multi-Task Pseudo-Fiber Label (Sobel-Z) ---
        with torch.no_grad():
            grad_z = x_orig[:, :, 1:] - x_orig[:, :, :-1]
            target_fiber = grad_z.abs().mean(dim=2, keepdim=True)
            target_fiber = (target_fiber - target_fiber.min()) / (target_fiber.max() - target_fiber.min() + 1e-8)

        # 2. Augmentations
        if x_orig.size(0) > 1:
            r = np.random.rand()
            if r < 0.2:
                x_orig, target_ink, _ = mixup_data(x_orig, target_ink)
            elif r < 0.4:
                x_orig, target_ink, _ = cutmix_data(x_orig, target_ink)

        # 3. Create Augmented View
        x_aug = x_orig.clone()
        k_rot = np.random.randint(0, 4)
        x_aug = torch.rot90(x_aug, k=k_rot, dims=(3, 4))
        target_ink_aug = torch.rot90(target_ink, k=k_rot, dims=(2, 3))
        target_fiber_aug = torch.rot90(target_fiber, k=k_rot, dims=(3, 4))

        x_aug = x_aug + torch.randn_like(x_aug) * 0.01

        # 4. Forward Pass with AMP
        optimizer.zero_grad(set_to_none=True)
        with autocast():
            out_ink, out_fiber, _, _, _, _ = model(x_aug, return_fiber=True)

            out_ink_2d = torch.mean(out_ink, dim=2)
            loss_ink = F.binary_cross_entropy_with_logits(out_ink_2d, target_ink_aug)
            loss_dice = compute_dice_loss(out_ink, target_ink_aug)
            
            out_fiber_2d = torch.mean(out_fiber, dim=2, keepdim=True)
            loss_fiber = F.mse_loss(torch.sigmoid(out_fiber_2d), target_fiber_aug)

            total_loss = 0.4 * loss_ink + 0.4 * loss_dice + 0.2 * loss_fiber

        # Backward with Scaler
        scaler.scale(total_loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(optimizer)
        scaler.update()
        scheduler.step()

        torch.cuda.synchronize()
        dt = time.time() - t0
        total_training_time += dt

        # Logging
        loss_val = total_loss.item()
        ema_beta = 0.9
        smooth_loss = ema_beta * smooth_loss + (1 - ema_beta) * loss_val if step > 0 else loss_val

        if step % 10 == 0:
            remaining = max(0, t_config.time_budget - total_training_time)
            print(f"Step {step:04d} | Loss: {smooth_loss:.6f} | dt: {dt*1000:.0f}ms | Remaining: {remaining:.0f}s")
            sys.stdout.flush()

        step += 1
        if total_training_time >= t_config.time_budget:
            break

    # Final Summary & Evaluation
    print(f"Evaluating val_bpb (1 - Dice) on validation set...")
    sys.stdout.flush()
    val_losses = []
    model.eval()
    with torch.no_grad():
        for _ in range(50): 
            try:
                val_x_raw, val_target = next(val_data_iter)
                val_x = val_x_raw[:, :, 4:4+t_config.num_layers].to(device)
                if val_target is not None and val_target.numel() > 0:
                    val_target = val_target.to(device)
                    with autocast():
                        val_out = model(val_x)
                    loss_dice = compute_dice_loss(val_out, val_target)
                    val_losses.append(loss_dice.item())
            except StopIteration:
                val_data_iter = iter(val_data_loader)
            except Exception:
                continue

    val_bpb = np.mean(val_losses) if val_losses else 1.0
    
    # Check for improvement
    log_file = 'results.tsv'
    is_improvement = True
    if os.path.exists(log_file):
        try:
            df = pd.read_csv(log_file, sep='\t')
            if len(df) > 0:
                best_val = df['val_bpb'].min()
                if val_bpb >= best_val: is_improvement = False
        except Exception: pass

    # Stats Calculation
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

    # Save Checkpoint & Log Results
    if is_improvement:
        # Save model weights
        checkpoint = {
            'model_state_dict': model.state_dict(),
            'val_bpb': val_bpb,
            'config': asdict(t_config)
        }
        torch.save(checkpoint, 'best_model.pt')
        print(f"Checkpoint saved to best_model.pt")

        header = "timestamp\tval_bpb\ttrain_loss\tthroughput_Mvps\tnum_params_M\tpeak_vram_mb\n"
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f: f.write(header)
        with open(log_file, 'a') as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{val_bpb:.6f}\t{smooth_loss:.6f}\t{throughput_Mvps:.2f}\t{num_params_M:.3f}\t{peak_vram_mb:.1f}\n")
        try:
            from plot_results import plot_results
            plot_results()
        except Exception as e: print(f"Failed to update plot: {e}")
    
    if not is_improvement: print("\n[RESULT] No improvement detected. Recommended: Revert.")
    else: print("\n[RESULT] Improvement detected! Recommended: Keep changes.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    if args.test: train(time_budget=30)
    else: train()
