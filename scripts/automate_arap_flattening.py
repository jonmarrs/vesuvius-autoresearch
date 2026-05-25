#!/usr/bin/env python3
"""
Automates a parameter sweep for the VC3D vc_flatten tool with enhanced reliability.
"""

import argparse
import json
import subprocess
import sys
import os
from pathlib import Path
import tempfile

sys.path.append(str(Path(__file__).resolve().parents[1]))
from volume_cartographer_wrapper.volume import FastLocalVolume

def run_flattening(vc_flatten_bin, input_uri, output_path, iterations, method):
    """Executes vc_flatten as a subprocess with robust error handling."""
    cmd = [
        str(vc_flatten_bin),
        "--input", str(input_uri),
        "--output", str(output_path),
        "--iterations", str(iterations),
        "--method", str(method)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"vc_flatten failed: {result.stderr}")
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(f"vc_flatten failed to produce a valid output file at {output_path}")
    return output_path

def calculate_flatness_score(mesh_path):
    """
    Validates mesh and calculates a heuristic flatness score.
    Requires 'trimesh' library.
    """
    try:
        import trimesh
        mesh = trimesh.load(mesh_path, force='mesh')
        if not mesh.is_manifold:
            return float('inf') # Penalty for non-manifold meshes
        # Simplified score: lower is flatter (e.g., ratio of bounding box to surface area)
        return mesh.bounding_box.volume / mesh.area
    except Exception:
        # Fallback to file size if mesh library fails or input is malformed
        return Path(mesh_path).stat().st_size

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input volume URI")
    parser.add_argument("--output", required=True, help="Output directory")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    vc_flatten_bin = repo_root / "villa" / "volume-cartographer" / "build" / "bin" / "vc_flatten"
    
    if not vc_flatten_bin.exists():
        print(f"Error: {vc_flatten_bin} does not exist.")
        sys.exit(1)

    volume = FastLocalVolume(args.input)
    print(f"Volume shape: {volume.shape}")

    iterations_grid = [10, 50, 100]
    methods = ["LSCM", "ABF++"]
    results = []
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        for iters in iterations_grid:
            for method in methods:
                tmp_out = Path(tmp_dir) / f"flattened_{iters}_{method}.obj"
                try:
                    run_flattening(vc_flatten_bin, args.input, tmp_out, iters, method)
                    score = calculate_flatness_score(tmp_out)
                    results.append({
                        "iterations": iters,
                        "method": method,
                        "score": score,
                        "path": str(tmp_out)
                    })
                except Exception as e:
                    print(f"Skipping iters={iters}, method={method}: {e}")

    if not results:
        print("No successful flattenings.")
        sys.exit(1)

    optimal = min(results, key=lambda x: x["score"])
    with open(output_dir / "optimal_config.json", "w") as f:
        json.dump(optimal, f, indent=2)

    print(f"Sweep complete. Optimal: {optimal['iterations']} iterations, {optimal['method']} method.")

if __name__ == "__main__":
    main()
