import os
import sys
import time

import cupy as cp
import numpy as np
import zarr
from PIL import Image

# Add villa to path
sys.path.insert(
    0, os.path.join(os.getcwd(), "villa/foundation/datasets/fibers-dataset")
)
import tools


def generate_evidence():
    zarr_path = "local_data/PHerc0332_div_100_1GB/0"
    output_dir = "reports/real_scroll_evidence"
    os.makedirs(output_dir, exist_ok=True)

    print(f"Opening Zarr at {zarr_path}...")
    z = zarr.open(zarr_path, mode="r")

    # Extract a 256^3 chunk from the center
    # Shape is (1024, 1024, 1024)
    start = (512 - 128, 512 - 128, 512 - 128)
    end = (512 + 128, 512 + 128, 512 + 128)

    print(f"Extracting chunk from {start} to {end}...")
    chunk_np = z[start[0] : end[0], start[1] : end[1], start[2] : end[2]].astype(
        np.float32
    )

    # Normalize input
    chunk_np = (chunk_np - chunk_np.min()) / (chunk_np.max() - chunk_np.min() + 1e-8)

    print("Running GPU-accelerated vesselness detection (tiled)...")
    chunk_cp = cp.array(chunk_np)

    start_time = time.time()
    # Using small block size to demonstrate tiling even on this 256^3 volume
    vesselness_cp = tools.detect_vesselness_tiled(chunk_cp, block_size=128, halo=16)
    cp.cuda.Stream.null.synchronize()
    duration = time.time() - start_time

    print(f"Detection completed in {duration:.2f}s")

    vesselness_np = cp.asnumpy(vesselness_cp)

    # Generate a contact sheet of slices
    print("Generating contact sheet...")
    num_slices = 8
    slice_indices = np.linspace(0, 255, num_slices, dtype=int)

    # Collect slices
    slices = []
    for idx in slice_indices:
        # Source slice
        src_slice = (chunk_np[idx] * 255).astype(np.uint8)
        # Vesselness slice (normalized)
        v_slice = vesselness_np[idx]
        v_slice = (v_slice / (v_slice.max() + 1e-8) * 255).astype(np.uint8)

        # Stack them vertically
        combined = np.vstack([src_slice, v_slice])
        slices.append(combined)

    # Combine all slices horizontally
    contact_sheet_np = np.hstack(slices)
    contact_sheet = Image.fromarray(contact_sheet_np)
    contact_sheet.save(os.path.join(output_dir, "vesselness_contact_sheet.png"))

    print(
        f"Contact sheet saved to {os.path.join(output_dir, 'vesselness_contact_sheet.png')}"
    )

    # Save a summary report
    with open(os.path.join(output_dir, "summary.txt"), "w") as f:
        f.write("Scroll: PHerc0332_div_100_1GB\n")
        f.write(f"Chunk Size: {chunk_np.shape}\n")
        f.write(f"GPU Time: {duration:.4f}s\n")
        f.write(f"Max Vesselness: {vesselness_np.max():.4f}\n")
        f.write(f"Mean Vesselness: {vesselness_np.mean():.4f}\n")


if __name__ == "__main__":
    generate_evidence()
