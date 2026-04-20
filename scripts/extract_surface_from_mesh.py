#!/usr/bin/env python3
"""
Vesuvius Autoresearch: Surface Extraction Pipeline
Wraps the ThaumatoAnakalyptor mesh_to_surface utility from the ScrollPrize/villa submodule.
This script extracts flat 3D volumes (TIF stacks) from raw 3D scroll meshes, eliminating
geometric distortion before the data is ingested by the autoresearch loop.

Usage:
  uv run scripts/extract_surface_from_mesh.py --mesh path/to/mesh.obj --volume path/to/raw_scroll_zarr/ --output local_data/Extracted_Surface/
"""

import os
import sys
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description="Extract Surface Volume from Mesh")
    parser.add_argument("--mesh", type=str, required=True, help="Path to the raw scroll mesh (.obj or .ply)")
    parser.add_argument("--volume", type=str, required=True, help="Path to the original unflattened scroll volume (Zarr or Grid)")
    parser.add_argument("--output", type=str, required=True, help="Output directory for the flattened TIF stack")
    parser.add_argument("--layers", type=int, default=65, help="Total number of layers to extract (depth)")
    args = parser.parse_args()

    villa_path = os.path.abspath("villa/thaumato-anakalyptor/ThaumatoAnakalyptor")
    if not os.path.exists(villa_path):
        print("Error: 'villa' submodule not found. Run 'git submodule update --init' first.")
        sys.exit(1)

    print(f"--- Vesuvius Autoresearch Surface Extraction ---")
    print(f"Mesh: {args.mesh}")
    print(f"Volume: {args.volume}")
    print(f"Output: {args.output}")
    print(f"Layers: {args.layers}")
    
    os.makedirs(args.output, exist_ok=True)
    
    # Calculate radius for mesh_to_surface (r = layers // 2)
    r = args.layers // 2
    
    # We call the official ThaumatoAnakalyptor script
    cmd = [
        "python3", os.path.join(villa_path, "mesh_to_surface.py"),
        "--obj", args.mesh,
        "--grid", args.volume,
        "--out", args.output,
        "--r", str(r),
        "--format", "tif"
    ]
    
    print(f"\nExecuting ThaumatoAnakalyptor pipeline...")
    print(" ".join(cmd))
    
    # Add villa to PYTHONPATH for the subprocess
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{villa_path}:{env.get('PYTHONPATH', '')}"
    
    try:
        subprocess.run(cmd, env=env, check=True)
        print(f"\nSuccess! Flattened surface volume saved to {args.output}")
    except subprocess.CalledProcessError as e:
        print(f"\nError extracting surface: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
