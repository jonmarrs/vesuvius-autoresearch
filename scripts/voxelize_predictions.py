#!/usr/bin/env python3
"""
Vesuvius Autoresearch: Voxel-to-Mesh Submission Pipeline
Wraps the vesuvius.image_proc.run tools from the ScrollPrize/villa submodule.
This script converts ink-probability predictions into high-fidelity 3D meshes
suitable for Grand Prize submission.

Usage:
  uv run scripts/voxelize_predictions.py --input predictions/pred_..._ink.zarr --output_obj predictions/pred_..._ink.obj
"""

import argparse
import os
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Voxelize Ink Predictions and Prune Noise"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to input ink prediction Zarr volume",
    )
    parser.add_argument(
        "--output_obj",
        type=str,
        required=True,
        help="Output path for the generated 3D OBJ mesh",
    )
    parser.add_argument(
        "--threshold", type=float, default=0.5, help="Ink threshold for voxelization"
    )
    args = parser.parse_args()

    vesuvius_src_path = os.path.abspath("villa/vesuvius/src")
    if not os.path.exists(vesuvius_src_path):
        print("Error: 'villa/vesuvius/src' not found.")
        sys.exit(1)

    print("--- Vesuvius Autoresearch Voxel-to-Mesh Pipeline ---")

    # 1. Prune noise/branching labels
    pruned_path = args.input.replace(".zarr", "_pruned.zarr")
    prune_script = os.path.join(
        vesuvius_src_path, "vesuvius", "image_proc", "run", "filter_branching_labels.py"
    )

    # 2. Voxelize
    voxelize_script = os.path.join(
        vesuvius_src_path, "vesuvius", "image_proc", "run", "voxelize_objs.py"
    )

    # Prepare environment
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{vesuvius_src_path}:{env.get('PYTHONPATH', '')}"

    try:
        print("\nStep 1: Pruning branching noise...")
        # Note: Depending on villa's API, the script might need specific flags
        subprocess.run(
            ["python3", prune_script, "--input", args.input, "--output", pruned_path],
            env=env,
            check=True,
        )

        print("\nStep 2: Voxelizing predictions into OBJ mesh...")
        subprocess.run(
            [
                "python3",
                voxelize_script,
                "--input",
                pruned_path,
                "--output",
                args.output_obj,
                "--threshold",
                str(args.threshold),
            ],
            env=env,
            check=True,
        )

        print(f"\nSuccess! Submission-ready mesh saved to {args.output_obj}")

    except subprocess.CalledProcessError as e:
        print(f"\nPipeline interrupted or failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
