#!/usr/bin/env python3
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import torch
from PIL import Image
from tqdm import tqdm

from predict import load_compatible_state_dict
from vesuvius_loader import FastVesuviusVolume
from vesuvius_model import InkDetectorOptimized, VesuviusConfig, VesuviusTimeSformer


def get_weight_window(patch_size, device):
    h = torch.hann_window(patch_size, periodic=False).to(device)
    window = h.unsqueeze(1) * h.unsqueeze(0)
    return window


def generate_pseudo_labels():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--uris", nargs="+", required=True, help="URIs of unlabeled volumes"
    )
    parser.add_argument("--model_path", type=str, default="best_model.pt")
    parser.add_argument("--threshold", type=float, default=0.85)
    parser.add_argument("--out_dir", type=str, default="local_data/pseudo_labels")
    parser.add_argument("--patch_size", type=int, default=None)
    parser.add_argument("--stride", type=int, default=None)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    os.makedirs(args.out_dir, exist_ok=True)

    print(f"Loading model from {args.model_path}...")
    checkpoint = torch.load(args.model_path, map_location=device, weights_only=False)
    config_dict = checkpoint.get("config", {})

    # Architecture mapping
    arch_type = config_dict.get("architecture", "gated_unet")
    v_config = VesuviusConfig(
        patch_size=config_dict.get("patch_size", 64),
        num_layers=config_dict.get("num_layers", 16),
        base_feat=config_dict.get("base_feat", 64),
        num_blocks=config_dict.get("num_blocks", 8),
        num_heads=config_dict.get("num_heads", 4),
        dropout=config_dict.get("dropout", 0.1),
        in_channels=config_dict.get("in_channels", 1),
    )

    if arch_type == "timesformer":
        model = VesuviusTimeSformer(v_config).to(device)
    elif arch_type == "resnet3d_decoder":
        from vesuvius_model import VesuviusResNet3DDecoder

        model = VesuviusResNet3DDecoder(v_config).to(device)
    else:
        model = InkDetectorOptimized(v_config).to(device)

    load_compatible_state_dict(model, checkpoint["model_state_dict"])
    model.eval()

    patch_size = args.patch_size or v_config.patch_size
    stride = args.stride or patch_size // 2
    weight_window = get_weight_window(patch_size, device)

    for uri in args.uris:
        segment_name = os.path.basename(os.path.dirname(uri.rstrip("/")))
        print(f"Processing {segment_name}...")

        dataset = FastVesuviusVolume(uri)
        D, H, W = dataset.shape

        # Determine center Z for prediction if num_layers < D
        num_layers = v_config.num_layers
        z0 = (D - num_layers) // 2

        full_prob = torch.zeros((H, W), device=device)
        full_weight = torch.zeros((H, W), device=device)

        # Tiling Loop (Simplified for whole volume)
        for y in tqdm(range(0, H - patch_size + 1, stride), desc="Y-tiles"):
            for x in range(0, W - patch_size + 1, stride):
                block = dataset[
                    z0 : z0 + num_layers, y : y + patch_size, x : x + patch_size
                ]
                x_in = dataset.normalize(block).unsqueeze(0).to(device)
                if x_in.dim() == 4:
                    x_in = x_in.unsqueeze(1)  # [B, 1, Z, H, W]

                with torch.no_grad():
                    out = model(x_in)
                    if isinstance(out, tuple):
                        out = out[0]
                    prob = torch.sigmoid(out).squeeze()

                full_prob[y : y + patch_size, x : x + patch_size] += (
                    prob * weight_window
                )
                full_weight[y : y + patch_size, x : x + patch_size] += weight_window

        full_prob /= full_weight + 1e-8
        mask = (full_prob > args.threshold).cpu().numpy().astype(np.uint8) * 255

        out_path = os.path.join(args.out_dir, f"{segment_name}_pseudo.png")
        Image.fromarray(mask).save(out_path)
        print(f"Saved pseudo-label to {out_path}")


if __name__ == "__main__":
    generate_pseudo_labels()
