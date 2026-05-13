#!/usr/bin/env python3
"""
Automates a parameter sweep for the VC3D vc_flatten tool.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
import numpy as np

# Add the project root to path to ensure we can import vesuvius_c_wrapper
sys.path.append(str(Path(__file__).resolve().parents[1]))
from vesuvius_c_wrapper.vesuvius_c import FastLocalVolume

def run_flattening(vc_flatten_bin, input_uri, output_dir, iterations, method):
    """
    Executes vc_flatten as a subprocess.
    """
    output_path = Path(output_dir) / f"flattened_{iterations}_{method}.obj"
    cmd = [
        str(vc_flatten_bin),
        "--input", str(input_uri),
        "--output", str(output_path),
        "--iterations", str(iterations),
        "--method", str(method)
    ]
    
    subprocess.run(cmd, check=True)
    return output_path

def calculate_flatness_score(mesh_path):
    """
    Provides a basic flatness score by calculating the variance of triangle areas or similar.
    This is a dummy implementation placeholder that should be replaced with actual mesh processing.
    """
    # In a real scenario, use trimesh or open3d to calculate mesh properties
    # Here we simulate a score based on file size as a proxy for complexity/deformation
    return Path(mesh_path).stat().st_size

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input volume URI (e.g. Zarr path)")
    parser.add_argument("--output", required=True, help="Output directory")
    args = parser.parse_args()

    # Define paths
    repo_root = Path(__file__).resolve().parents[1]
    vc_flatten_bin = repo_root / "villa" / "volume-cartographer" / "build" / "bin" / "vc_flatten"
    
    if not vc_flatten_bin.exists():
        print(f"Error: {vc_flatten_bin} does not exist.")
        sys.exit(1)

    # Initialize volume
    volume = FastLocalVolume(args.input)
    print(f"Volume shape: {volume.shape}")

    # Parameter grid
    iterations_grid = [10, 50, 100]
    methods = ["LSCM", "ABF++"]

    results = []
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    for iters in iterations_grid:
        for method in methods:
            print(f"Running: iters={iters}, method={method}")
            try:
                mesh_path = run_flattening(vc_flatten_bin, args.input, output_dir, iters, method)
                score = calculate_flatness_score(mesh_path)
                results.append({
                    "iterations": iters,
                    "method": method,
                    "score": score,
                    "path": str(mesh_path)
                })
            except subprocess.CalledProcessError as e:
                print(f"Failed: {e}")

    # Find optimal
    optimal = min(results, key=lambda x: x["score"])
    
    # Save optimal config
    with open(output_dir / "optimal_config.json", "w") as f:
        json.dump(optimal, f, indent=2)

    print(f"Sweep complete. Optimal parameters: {optimal['iterations']} iterations, {optimal['method']} method.")

if __name__ == "__main__":
    main()
