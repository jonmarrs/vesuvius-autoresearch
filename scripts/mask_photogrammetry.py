#!/usr/bin/env python3
"""
Vesuvius Autoresearch: Photogrammetry Masking Pipeline
Wraps the sam2-photogrammetry tools from the ScrollPrize/villa submodule.
This script uses a fine-tuned SAM 2 model to automatically mask out the background
and rulers from raw scroll photographs. This ensures that the resulting 3D mesh
is perfectly clean, leading to pristine surface extraction via ThaumatoAnakalyptor.

Usage:
  uv run scripts/mask_photogrammetry.py --input path/to/photogrammetry_session/
"""

import argparse
import os
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Segment Scroll and Ruler in Photogrammetry Images"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Root directory containing the scroll photos (must follow SAM2 folder structure)",
    )
    args = parser.parse_args()

    villa_sam2_path = os.path.abspath("villa/sam2-photogrammetry")
    if not os.path.exists(villa_sam2_path):
        print("Error: 'villa' submodule not found or path incorrect.")
        sys.exit(1)

    print("--- Vesuvius Autoresearch Photogrammetry Masking ---")
    print(f"Input Directory: {args.input}")

    # 1. Convert RAW to JPG (if needed)
    raw2jpg_cmd = ["python3", "raw2jpg.py", args.input]

    # 2. Run Segmentation
    segment_cmd = ["python3", "segment.py", "--root_dir", args.input]

    # 3. Fix Predictions
    fix_cmd = ["python3", "cc-fix.py", args.input]

    # 4. Apply Masks
    apply_cmd = ["python3", "mask-applier.py", "--root_dir", args.input]

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{villa_sam2_path}:{env.get('PYTHONPATH', '')}"

    try:
        print("\nStep 1: Checking for RAW images to convert...")
        subprocess.run(raw2jpg_cmd, cwd=villa_sam2_path, env=env, check=True)

        print("\nStep 2: Running SAM 2 Segmentation (this may take a while)...")
        subprocess.run(segment_cmd, cwd=villa_sam2_path, env=env, check=True)

        print("\nStep 3: Fixing connected component predictions...")
        subprocess.run(fix_cmd, cwd=villa_sam2_path, env=env, check=True)

        print("\nStep 4: Applying masks to images...")
        subprocess.run(apply_cmd, cwd=villa_sam2_path, env=env, check=True)

        print(f"\nSuccess! Masked images are ready in {args.input}")
        print(
            "You can now run your preferred Photogrammetry software (e.g. OpenMVG + OpenMVS) on these masked images to build a pristine 3D mesh."
        )
        print(
            "Once the mesh is built, use scripts/extract_surface_from_mesh.py to generate the final Zarr volume."
        )

    except subprocess.CalledProcessError as e:
        print(f"\nPipeline interrupted or failed: {e}")
        print(
            "Please ensure you have downloaded the fine-tuned SAM2 checkpoint (photo2_ruler_t_1000.torch) into villa/sam2-photogrammetry/checkpoints/"
        )


if __name__ == "__main__":
    main()
