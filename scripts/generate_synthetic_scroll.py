#!/usr/bin/env python3
"""
Vesuvius Autoresearch: Synthetic Scroll Builder (Virtual Papyrus)
Procedurally generates 3D volumes of "virtual papyrus" with simulated
ink and fiber structures for model pretraining.

Targets:
- 3D Fiber Morphology (Cross-hatched textures)
- Surface Ink Distribution (Procedural letters)
- Geometric Warping (Z-displacement fields)
- CT Scan Noise (Poisson/Gaussian distribution)
"""

import argparse
import json
import os

import numpy as np
import torch
import torch.nn.functional as F
import zarr
from scipy.ndimage import gaussian_filter
from tqdm import tqdm


def generate_fibers(shape, density=0.05, sigma=1.0):
    """Generates cross-hatched 3D fiber texture."""
    depth, height, width = shape
    vol = np.zeros(shape, dtype=np.float32)

    # Horizontal fibers
    num_h = int(height * width * density / 2)
    for _ in range(num_h):
        y = np.random.randint(0, height)
        z = np.random.randint(0, depth)
        vol[z, y, :] += np.random.rand()

    # Vertical fibers
    num_v = int(height * width * density / 2)
    for _ in range(num_v):
        x = np.random.randint(0, width)
        z = np.random.randint(0, depth)
        vol[z, :, x] += np.random.rand()

    # Smooth to create "vessels"
    vol = gaussian_filter(vol, sigma=sigma)
    vol = (vol - vol.min()) / (vol.max() - vol.min() + 1e-8)
    return vol


def generate_ink(shape, ink_z=None):
    """Generates procedural ink patterns on a specific surface layer."""
    depth, height, width = shape
    if ink_z is None:
        ink_z = depth // 2

    ink_mask = np.zeros((height, width), dtype=np.float32)
    # Simple randomized "letters" (rectangles/lines)
    num_chars = 20
    for _ in range(num_chars):
        char_y = np.random.randint(0, height - 10)
        char_x = np.random.randint(0, width - 10)
        ch_h, ch_w = np.random.randint(4, 10), np.random.randint(4, 10)
        ink_mask[char_y : char_y + ch_h, char_x : char_x + ch_w] = 1.0

    # Smooth ink to match real diffusion
    ink_mask = gaussian_filter(ink_mask, sigma=0.8)

    # Place in volume
    vol_ink = np.zeros(shape, dtype=np.float32)
    vol_ink[ink_z, :, :] = ink_mask
    return vol_ink, ink_mask


def apply_warping(volume, ink_mask, max_warp=4):
    """Applies a 3D displacement field to simulate scroll curvature."""
    depth, height, width = volume.shape
    # Create meshgrid
    z, y, x = torch.meshgrid(
        torch.linspace(-1, 1, depth),
        torch.linspace(-1, 1, height),
        torch.linspace(-1, 1, width),
        indexing="ij",
    )

    # Generate low-frequency warping field
    warp = torch.randn(1, 1, 4, 4, 4) * max_warp / depth
    warp = F.interpolate(
        warp, size=(depth, height, width), mode="trilinear", align_corners=True
    )

    grid = torch.stack([x, y, z + warp[0, 0]], dim=-1).unsqueeze(0)  # [1, D, H, W, 3]

    vol_tensor = torch.from_numpy(volume).unsqueeze(0).unsqueeze(0)  # [1, 1, D, H, W]
    warped_vol = F.grid_sample(
        vol_tensor, grid, mode="bilinear", padding_mode="border", align_corners=True
    )

    return warped_vol.squeeze().numpy()


def main():
    parser = argparse.ArgumentParser(description="Generate Synthetic Scroll Data")
    parser.add_argument(
        "--out", default="local_data/synthetic_scroll", help="Output Zarr directory"
    )
    parser.add_argument(
        "--num-patches", type=int, default=10, help="Number of 64^3 patches to generate"
    )
    parser.add_argument("--patch-size", type=int, default=64)
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    # Create OME-Zarr structure
    store = zarr.DirectoryStore(os.path.join(args.out, "0"))
    # Final volume will be concatenated patches for simplicity in this prototype
    # Shape: [num_patches, patch_size, patch_size, patch_size]
    z_vol = zarr.group(store=store, overwrite=True)

    data_shape = (args.num_patches * args.patch_size, args.patch_size, args.patch_size)
    ct_array = z_vol.zeros(
        "data",
        shape=data_shape,
        chunks=(args.patch_size, args.patch_size, args.patch_size),
        dtype="u1",
    )
    ink_array = z_vol.zeros(
        "ink", shape=(args.num_patches, args.patch_size, args.patch_size), dtype="u1"
    )

    print(f"Generating {args.num_patches} synthetic patches...")
    for i in tqdm(range(args.num_patches)):
        shape = (args.patch_size, args.patch_size, args.patch_size)

        # 1. Base Texture
        fibers = generate_fibers(shape)

        # 2. Ink
        vol_ink, ink_mask = generate_ink(shape)

        # 3. Combine and Warp
        combined = fibers * 0.7 + vol_ink * 0.3
        warped = apply_warping(combined, ink_mask)

        # 4. Add Noise
        noise = np.random.normal(0, 0.05, shape).astype(np.float32)
        final = np.clip(warped + noise, 0, 1)

        # 5. Save
        z_start = i * args.patch_size
        ct_array[z_start : z_start + args.patch_size] = (final * 255).astype(np.uint8)
        ink_array[i] = (ink_mask * 255).astype(np.uint8)

    # Metadata
    metadata = {
        "type": "synthetic_virtual_papyrus",
        "num_patches": args.num_patches,
        "patch_size": args.patch_size,
        "generation_params": {
            "fiber_density": 0.05,
            "ink_layer": "center",
            "warping": "trilinear_displacement",
        },
    }
    with open(os.path.join(args.out, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Synthetic dataset generated at {args.out}")


if __name__ == "__main__":
    main()
