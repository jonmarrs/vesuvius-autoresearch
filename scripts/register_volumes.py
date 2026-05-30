#!/usr/bin/env python3
"""
Vesuvius Autoresearch: Volume Registration Pipeline
Wraps the foundation/volume-registration tools from the ScrollPrize/villa submodule.
This script aligns multi-resolution or multi-scan Zarr volumes to a fixed coordinate space,
ensuring that training patches from different fragments or depths have perfectly aligned
fiber morphologies before entering the training loop.

Usage:
  uv run scripts/register_volumes.py --fixed path/to/fixed.zarr/ --moving path/to/moving.zarr/ --output_transform local_data/transforms/aligned.json
"""

import argparse
import os
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Register/Align Scroll Volumes")
    parser.add_argument(
        "--fixed",
        type=str,
        required=True,
        help="Path to the fixed (reference) Zarr volume",
    )
    parser.add_argument(
        "--moving",
        type=str,
        required=True,
        help="Path to the moving (source) Zarr volume to be aligned",
    )
    parser.add_argument(
        "--fixed-voxel-size",
        type=float,
        default=7.91,
        help="Voxel size of the fixed volume in microns",
    )
    parser.add_argument(
        "--output-transform",
        type=str,
        required=True,
        help="Output JSON path for the aligned transform matrix",
    )
    args = parser.parse_args()

    villa_path = os.path.abspath("villa/foundation/volume-registration")
    if not os.path.exists(villa_path):
        print(
            "Error: 'villa' submodule not found. Run 'git submodule update --init' first."
        )
        sys.exit(1)

    print("--- Vesuvius Autoresearch Volume Registration ---")
    print(f"Fixed Reference: {args.fixed}")
    print(f"Moving Volume:   {args.moving}")
    print(f"Output Matrix:   {args.output_transform}")

    os.makedirs(os.path.dirname(args.output_transform), exist_ok=True)

    # We call the official foundation registration script
    cmd = [
        "python3",
        "-i",
        os.path.join(villa_path, "find_transform.py"),
        "--fixed",
        args.fixed,
        "--fixed-voxel-size",
        str(args.fixed_voxel_size),
        "--moving",
        args.moving,
        "--output-transform",
        args.output_transform,
    ]

    print("\nExecuting Neuroglancer Alignment Server...")
    print(" ".join(cmd))

    # Add villa to PYTHONPATH for the subprocess
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{villa_path}:{env.get('PYTHONPATH', '')}"

    print(
        "\n[INSTRUCTION] A local HTTP server will now start. Open the provided Neuroglancer link in your browser."
    )
    print(
        "Perform coarse alignment using Alt+WASDQE, add landmarks with Alt+1/2, and the transform will be fit automatically."
    )
    print("Press Ctrl+D when finished to save the transform.\n")

    try:
        subprocess.run(cmd, env=env, check=True)
        print(f"\nSuccess! Registration transform saved to {args.output_transform}")
        print(
            "You can now apply this transform inside vesuvius_loader.py using SimpleITK."
        )
    except subprocess.CalledProcessError as e:
        print(f"\nRegistration interrupted or failed: {e}")


if __name__ == "__main__":
    main()
