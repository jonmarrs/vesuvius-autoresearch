#!/usr/bin/env python3
"""Batched ink prediction from a project checkpoint into a local VC3D volume.

Uses the shared model factory and normalized volume loader. Checkpoint geometry
is authoritative; tiling covers the requested region, including its boundaries.
"""

import argparse
import math
import os
import time

import numpy as np
import torch
import torch.nn.functional as F
from tqdm.auto import tqdm

from scripts.inference.predict import (
    build_prediction_model,
    save_vc3d_zarr,
    write_prediction_metadata,
)
from vesuvius_autoresearch.core.inference import (
    hann2d,
    normalize_blend,
    prepare_volume_input,
    tile_starts,
    validate_model_settings,
)
from vesuvius_autoresearch.core.vesuvius_loader import FastVesuviusVolume


def production_predict(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uri", required=True, help="Zarr volume URI")
    parser.add_argument("--checkpoint", default="best_model.pt")
    for axis in ("z", "y", "x"):
        parser.add_argument(f"--{axis}", type=int, required=True)
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument(
        "--patch-size", type=int, help="must match the checkpoint; defaults to its size"
    )
    parser.add_argument(
        "--stride", type=int, help="defaults to half the checkpoint patch size"
    )
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--voxel-size-um", type=float, default=7.91)
    parser.add_argument("--out-dir", default="predictions/production")
    args = parser.parse_args(argv)
    args.inference_recipe = {
        "ink_probability": "sigmoid(ink)",
        "tta_mirrors": ["none"],
        "blend_window": "positive_hann",
    }

    # Project checkpoints are trusted training artifacts and may contain objects
    # beyond PyTorch's restricted weights-only format.
    ckpt = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    if not isinstance(ckpt, dict) or not isinstance(ckpt.get("config"), dict):
        raise ValueError("checkpoint must contain a config object")
    config_dict = ckpt["config"]
    size = config_dict.get("patch_size", 64)
    args.num_layers = config_dict.get("num_layers", 16)
    args.base_feat = config_dict.get("base_feat", 128)
    ridge_sigma = validate_model_settings(
        config_dict, size, args.num_layers, args.base_feat
    )
    if args.patch_size is not None and args.patch_size != size:
        parser.error("--patch-size must match the checkpoint")
    args.patch_size = size
    args.stride = max(1, size // 2) if args.stride is None else args.stride
    if args.width < size or args.height < size:
        parser.error("width and height must be at least the checkpoint patch size")
    if not 0 < args.stride <= size or args.batch_size <= 0:
        parser.error(
            "stride must be in [1, patch_size] and batch-size must be positive"
        )
    if min(args.x, args.y, args.z) < 0:
        parser.error("x, y and z must be non-negative")
    args.voxel_size_um = float(
        config_dict.get(
            "voxel_size_um", config_dict.get("voxelsize", args.voxel_size_um)
        )
    )
    if not math.isfinite(args.voxel_size_um) or args.voxel_size_um <= 0:
        parser.error("voxel size must be finite and positive")
    state = ckpt.get("model_state_dict", ckpt.get("model"))
    if not isinstance(state, dict) or not state:
        raise ValueError(
            "checkpoint must contain model_state_dict (or legacy model weights)"
        )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_ridges = config_dict.get("use_ridges", False)
    model = build_prediction_model(config_dict, args, use_ridges=use_ridges)
    model.load_state_dict(state, strict=True)
    model = model.to(device).eval()
    dataset = FastVesuviusVolume(
        args.uri, use_ridges=use_ridges, ridge_sigma=ridge_sigma
    )
    ends = (args.z + args.num_layers, args.y + args.height, args.x + args.width)
    if any(end > limit for end, limit in zip(ends, dataset.shape, strict=True)):
        raise ValueError(f"requested region exceeds volume shape {dataset.shape}")

    ys = tile_starts(args.height, size, args.stride)
    xs = tile_starts(args.width, size, args.stride)
    full_prob = torch.zeros((args.height, args.width), device=device)
    full_count = torch.zeros_like(full_prob)
    window = hann2d(size, size, device=device)
    patches, coords = [], []

    def flush():
        if not patches:
            return
        batch = torch.stack(patches).to(device)
        logits = model(batch)
        if isinstance(logits, tuple):
            logits = logits[0]
        if (
            not isinstance(logits, torch.Tensor)
            or not logits.is_floating_point()
            or not torch.isfinite(logits).all()
        ):
            raise ValueError("model must return finite floating-point ink logits")
        if logits.ndim != 4 or logits.shape[:2] != (len(patches), 1):
            raise ValueError(
                "model must return ink logits with shape (batch, 1, height, width)"
            )
        if logits.shape[-2:] != (size, size):
            logits = F.interpolate(
                logits, size=(size, size), mode="bilinear", align_corners=False
            )
        probs = torch.sigmoid(logits)[:, 0]
        if not torch.isfinite(probs).all():
            raise ValueError("model returned non-finite probabilities")
        for (y, x), prob in zip(coords, probs, strict=True):
            full_prob[y : y + size, x : x + size] += prob * window
            full_count[y : y + size, x : x + size] += window
        patches.clear()
        coords.clear()

    print(f"Starting production inference ({len(ys) * len(xs)} tiles)...")
    start = time.time()
    with torch.inference_mode():
        for y in tqdm(ys, desc="Rows"):
            for x in xs:
                block = dataset[
                    args.z : args.z + args.num_layers,
                    args.y + y : args.y + y + size,
                    args.x + x : args.x + x + size,
                ]
                patch = prepare_volume_input(
                    dataset.normalize(block), use_ridges, args.num_layers, size, "cpu"
                )[0]
                patches.append(patch)
                coords.append((y, x))
                if len(patches) >= args.batch_size:
                    flush()
        flush()
        final_prob = normalize_blend(full_prob, full_count).cpu().numpy()
    args.tiles_total = args.tiles_processed = len(ys) * len(xs)
    final_uint8 = (np.clip(final_prob, 0, 1) * 255).astype(np.uint8)
    print(f"Inference complete in {time.time() - start:.1f}s")

    os.makedirs(args.out_dir, exist_ok=True)
    base = f"prod_pred_{args.z}_{args.y}_{args.x}_{args.width}x{args.height}"
    zarr_path = os.path.join(args.out_dir, f"{base}.zarr")
    save_vc3d_zarr(
        zarr_path,
        final_uint8,
        name="ink",
        voxel_size_um=args.voxel_size_um,
        source_uri=args.uri,
        origin_xyz=[args.x, args.y, args.z],
    )
    write_prediction_metadata(
        os.path.join(args.out_dir, f"{base}_meta.json"),
        args,
        config_dict,
        zarr_path,
        None,
        {"mean": float(final_prob.mean()), "max": float(final_prob.max())},
    )
    print(f"Saved production results to {args.out_dir}")


if __name__ == "__main__":
    production_predict()
