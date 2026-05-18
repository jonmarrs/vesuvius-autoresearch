#!/usr/bin/env python3
"""
Vesuvius Autoresearch: Active Learning Flywheel
Wraps the vc_proofreader from the ScrollPrize/villa submodule.
This script launches the Napari-based interactive proofreading tool. It allows
you to review low-confidence patches from the model's predictions, manually
correct them, and export the approved patches back into the training dataset.

Usage:
  uv run scripts/launch_proofreader.py --volume path/to/raw_volume.zarr --predictions path/to/predictions/
"""

import os
import sys
import argparse
import subprocess
import json

def generate_config(volume_path, predictions_path, config_out_path):
    """Generates the config file expected by the vc_proofreader."""
    config = {
        "dataset_out_path": "local_data/Proofread_Patches",
        "patch_size": [16, 64, 64], # [Z, Y, X]
        "min_label_percentage": 1.0,
        "volumes": {
            "Autoresearch_Prediction": {
                "image_zarr": volume_path,
                "label_zarr": predictions_path
            }
        }
    }
    with open(config_out_path, 'w') as f:
        json.dump(config, f, indent=4)
    return config_out_path

def main():
    parser = argparse.ArgumentParser(description="Launch Active Learning Proofreader")
    parser.add_argument("--volume", type=str, required=True, help="Path to the original CT volume (Zarr format)")
    parser.add_argument("--predictions", type=str, required=True, help="Path to the model's predictions (Zarr format)")
    args = parser.parse_args()

    villa_proofreader_path = os.path.abspath("villa/segmentation/vc_proofreader/main.py")
    if not os.path.exists(villa_proofreader_path):
        print("Error: 'villa' submodule not found or path incorrect.")
        sys.exit(1)

    print("--- Vesuvius Autoresearch Active Learning Flywheel ---")
    
    # Generate config for the proofreader
    config_path = "proofreader_config.json"
    generate_config(args.volume, args.predictions, config_path)
    
    # Use sys.executable rather than bare "python3" so we inherit the
    # active venv (uv run sets sys.executable to .venv/bin/python). Bare
    # python3 resolves to the system interpreter which lacks napari and
    # the rest of the project's deps.
    cmd = [
        sys.executable, villa_proofreader_path,
        "--config", config_path
    ]
    
    print(f"\nLaunching VC Proofreader...")
    print(" ".join(cmd))
    print("\n[INSTRUCTION] A Napari window will open.")
    print("1. Review the model's predictions overlaid on the CT data.")
    print("2. Press 'a' to approve a patch or 'spacebar' to skip.")
    print("3. Approved patches are automatically saved to local_data/Proofread_Patches/")
    print("   and can be used in the next Vesuvius Autoresearch training cycle.\n")
    
    # Add villa to PYTHONPATH
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{os.path.abspath('villa')}:{env.get('PYTHONPATH', '')}"
    
    try:
        subprocess.run(cmd, env=env, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\nProofreader interrupted or failed: {e}")

if __name__ == "__main__":
    main()
