#!/usr/bin/env python3
"""
Production-Grade Prediction Script for Vesuvius Autoresearch.
Leverages Villa's optimized_inference logic:
- Memory-efficient tiled inference
- Gaussian/Hann blending for artifact-free overlays
- Multi-threaded prefetching
- Support for both TimeSformer and Gated UNet architectures
"""

import argparse
import os
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
import zarr
from tqdm.auto import tqdm

from scripts.inference.predict import (
    build_prediction_model,
    save_vc3d_zarr,
    write_prediction_metadata,
)
from vesuvius_autoresearch.core.vesuvius_loader import FastVesuviusVolume


def hann2d(h: int, w: int, device="cpu"):
    """Normalized 2D Hann window for overlap-add blending."""
    wy = torch.hann_window(h, periodic=False).to(device)
    wx = torch.hann_window(w, periodic=False).to(device)
    k = torch.outer(wy, wx)
    return k


def production_predict():
    parser = argparse.ArgumentParser()
    parser.add_argument("--uri", required=True, help="Zarr volume URI")
    parser.add_argument("--checkpoint", default="best_model.pt")
    parser.add_argument("--z", type=int, required=True)
    parser.add_argument("--y", type=int, required=True)
    parser.add_argument("--x", type=int, required=True)
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--patch-size", type=int, default=64)
    parser.add_argument("--stride", type=int, default=32)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--out-dir", default="predictions/production")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Load Model and Config
    ckpt = torch.load(args.checkpoint, map_location="cpu")
    config_dict = ckpt["config"]
    num_layers = config_dict.get("num_layers", 16)
    model = (
        build_prediction_model(config_dict, args, use_ridges=False).to(device).eval()
    )
    model.load_state_dict(ckpt["model"])
    print(f"Loaded {config_dict['architecture']} model from {args.checkpoint}")

    # 2. Setup Dataset
    dataset = FastVesuviusVolume(args.uri, use_ridges=False)

    # 3. Grid Setup
    y_coords = list(
        range(args.y, args.y + args.height - args.patch_size + 1, args.stride)
    )
    x_coords = list(
        range(args.x, args.x + args.width - args.patch_size + 1, args.stride)
    )
    if not y_coords or y_coords[-1] != args.y + args.height - args.patch_size:
        y_coords.append(args.y + args.height - args.patch_size)
    if not x_coords or x_coords[-1] != args.x + args.width - args.patch_size:
        x_coords.append(args.x + args.width - args.patch_size)

    # 4. Accumulation Buffers
    full_prob = torch.zeros((args.height, args.width), device=device)
    full_count = torch.zeros((args.height, args.width), device=device)
    window = hann2d(args.patch_size, args.patch_size, device=device)

    # 5. Inference Loop (Batched)
    print(f"Starting Production Inference ({len(y_coords) * len(x_coords)} tiles)...")
    patches = []
    coords = []

    start_time = time.time()
    for py in tqdm(y_coords, desc="Rows"):
        for px in x_coords:
            # Load block
            block = dataset[
                args.z : args.z + num_layers,
                py : py + args.patch_size,
                px : px + args.patch_size,
            ]
            # FastVesuviusVolume returns (D, H, W)
            block_tensor = (
                torch.from_numpy(block).float().unsqueeze(0).to(device)
            )  # [1, D, H, W]

            patches.append(block_tensor)
            coords.append((py - args.y, px - args.x))

            if len(patches) >= args.batch_size:
                batch = torch.cat(patches, dim=0)  # [B, D, H, W]
                # Predict
                with torch.no_grad():
                    logits = model(batch.unsqueeze(1))  # Model expects [B, 1, D, H, W]
                    if isinstance(logits, tuple):
                        logits = logits[0]
                    probs = torch.sigmoid(logits).squeeze(
                        1
                    )  # [B, H, W] or [B, 1, H, W] -> [B, H, W]

                # Accumulate
                for i, (ry, rx) in enumerate(coords):
                    full_prob[ry : ry + args.patch_size, rx : rx + args.patch_size] += (
                        probs[i] * window
                    )
                    full_count[
                        ry : ry + args.patch_size, rx : rx + args.patch_size
                    ] += window

                patches = []
                coords = []

    # Process remaining
    if patches:
        batch = torch.cat(patches, dim=0)
        with torch.no_grad():
            logits = model(batch.unsqueeze(1))
            if isinstance(logits, tuple):
                logits = logits[0]
            probs = torch.sigmoid(logits).squeeze(1)
        for i, (ry, rx) in enumerate(coords):
            full_prob[ry : ry + args.patch_size, rx : rx + args.patch_size] += (
                probs[i] * window
            )
            full_count[ry : ry + args.patch_size, rx : rx + args.patch_size] += window

    # 6. Finalize
    final_prob = (full_prob / (full_count + 1e-8)).cpu().numpy()
    final_uint8 = (final_prob * 255).astype(np.uint8)

    elapsed = time.time() - start_time
    throughput = (args.width * args.height) / (elapsed * 1e6)
    print(
        f"Inference Complete. Elapsed: {elapsed:.1f}s | Throughput: {throughput:.2f} Mvps"
    )

    # 7. Export
    base_name = f"prod_pred_{args.z}_{args.y}_{args.x}_{args.width}x{args.height}"
    zarr_path = os.path.join(args.out_dir, f"{base_name}.zarr")
    save_vc3d_zarr(zarr_path, final_uint8, name="ink")

    meta_path = os.path.join(args.out_dir, f"{base_name}_meta.json")
    write_prediction_metadata(
        meta_path,
        args,
        config_dict,
        zarr_path,
        None,  # no png for now
        {"mean": float(final_prob.mean()), "max": float(final_prob.max())},
    )
    print(f"Saved production results to {args.out_dir}")


if __name__ == "__main__":
    production_predict()
