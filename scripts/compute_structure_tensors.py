#!/usr/bin/env python3
"""
Vesuvius Autoresearch: Structure Tensor Pipeline
Wraps the vesuvius/structure_tensor tools from the ScrollPrize/villa submodule.
This script computes the 3D structure tensors (fiber directionality, eigenvalues)
for a given Zarr volume. This provides a massive structural feature channel for
our models to differentiate between cracks and ink.

Usage:
  uv run scripts/compute_structure_tensors.py --input path/to/volume.zarr --output path/to/output_st.zarr
"""

import os
import sys
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description="Compute Structure Tensors for Vesuvius Volumes")
    parser.add_argument("--input", type=str, required=True, help="Path to the input Zarr volume")
    parser.add_argument("--output", type=str, required=True, help="Path to save the output Structure Tensor Zarr")
    parser.add_argument("--sigma", type=float, default=2.0, help="Sigma for Gaussian smoothing (controls scale of fibers)")
    parser.add_argument("--rho", type=float, default=2.0, help="Rho for integration scale")
    parser.add_argument("--gpus", type=str, default="all", help="Comma separated list of GPUs to use, or 'all'")
    args = parser.parse_args()

    # The official vesuvius library is inside villa/vesuvius/src
    vesuvius_src_path = os.path.abspath("villa/vesuvius/src")
    if not os.path.exists(vesuvius_src_path):
        print("Error: 'villa/vesuvius/src' not found. Run 'git submodule update --init' first.")
        sys.exit(1)

    run_script = os.path.join(vesuvius_src_path, "vesuvius", "structure_tensor", "run_create_st.py")
    if not os.path.exists(run_script):
        print(f"Error: {run_script} not found.")
        sys.exit(1)

    print(f"--- Vesuvius Autoresearch Structure Tensor Computation ---")
    print(f"Input Volume:  {args.input}")
    print(f"Output Tensor: {args.output}")
    print(f"Sigma: {args.sigma}, Rho: {args.rho}")
    
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # We call the official structure tensor script
    cmd = [
        "python3", run_script,
        "--input", args.input,
        "--output", args.output,
        "--sigma", str(args.sigma),
        "--rho", str(args.rho),
        "--gpus", args.gpus
    ]
    
    print(f"\nExecuting Structure Tensor pipeline...")
    print(" ".join(cmd))
    
    # Add vesuvius src to PYTHONPATH for the subprocess
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{vesuvius_src_path}:{env.get('PYTHONPATH', '')}"
    
    try:
        subprocess.run(cmd, env=env, check=True)
        print(f"\nSuccess! Structure Tensors saved to {args.output}")
        print("You can now feed this as an additional input channel to the Vesuvius-DINO model.")
    except subprocess.CalledProcessError as e:
        print(f"\nStructure Tensor computation interrupted or failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
