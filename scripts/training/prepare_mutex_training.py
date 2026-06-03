import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import tifffile
import zarr

# Add villa to path
sys.path.append(os.path.abspath("villa/vesuvius/src"))


def export_zarr_to_tiff(zarr_path, tiff_path):
    """Converts a curated Zarr fragment to 3D TIFF for affinity generation."""
    print(f"Exporting {zarr_path} to {tiff_path}...")
    z = zarr.open(zarr_path, mode="r")
    if "0" in z:
        data = z["0"][:]
    else:
        data = z[:]

    # Ensure 3D
    if data.ndim == 4:
        data = data[0]  # Take first channel

    tifffile.imwrite(tiff_path, data.astype(np.float32))


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--curated_zarr",
        type=str,
        required=True,
        help="Path to curated Gold Standard Zarr",
    )
    parser.add_argument(
        "--output_dir", type=str, default="local_data/curated_fragments"
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    images_dir = os.path.join(args.output_dir, "images")
    temp_tiff_dir = os.path.join(args.output_dir, "temp_tiffs")
    affinity_dir = os.path.join(args.output_dir, "affinity_graph")

    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(temp_tiff_dir, exist_ok=True)
    os.makedirs(affinity_dir, exist_ok=True)

    # 1. Prepare raw image volume (as Zarr for the trainer)
    # For now we assume the curated zarr is already the labels,
    # we need the corresponding raw image too.
    # ... logic to find raw image ...

    # 2. Convert Curated Labels to TIFF for Graph Generation
    frag_name = Path(args.curated_zarr).stem
    label_tiff = os.path.join(temp_tiff_dir, f"{frag_name}_labels.tif")
    export_zarr_to_tiff(args.curated_zarr, label_tiff)

    # 3. Run official Mutex Graph Generator
    print("Generating Affinity Graph...")
    gen_script = "villa/vesuvius/src/vesuvius/image_proc/run/generate_mutex_graph.py"
    cmd = [
        "python3",
        gen_script,
        temp_tiff_dir,
        affinity_dir,
        "--pattern",
        f"{frag_name}_labels.tif",
        "--foreground-threshold",
        "0.5",  # Curation produced clean binary/instance masks
        "--overwrite",
    ]
    subprocess.run(cmd, check=True)

    print(f"\nMutex Training Data Ready at {args.output_dir}")
    print(f"To train: python3 train_mutex.py --data_path {args.output_dir}")


if __name__ == "__main__":
    main()
