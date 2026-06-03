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

    # 1. Prepare raw image volume
    # Pair curated zarr (e.g., local_data/Curated/PHercXXX_div_YYY.zarr)
    # with raw volume (e.g., local_data/PHercXXX_Divisions/div_YYY/0)
    frag_name = Path(args.curated_zarr).stem
    # Heuristic for pairing: find a local_data folder matching frag_name prefix
    raw_vol_path = None
    for root, dirs, files in os.walk("local_data"):
        if frag_name.replace("_", "-") in root or frag_name in root:
            # Look for a numeric folder '0' within this division folder
            if "0" in dirs and os.path.exists(os.path.join(root, "0", ".zarray")):
                raw_vol_path = os.path.join(root, "0")
                break

    if not raw_vol_path:
        print(f"Error: Could not find raw volume for {frag_name}", file=sys.stderr)
        return 1

    print(f"Paired curated zarr with raw volume: {raw_vol_path}")
    export_zarr_to_tiff(raw_vol_path, os.path.join(images_dir, f"{frag_name}_raw.tif"))

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
