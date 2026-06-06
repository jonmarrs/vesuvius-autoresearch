#!/usr/bin/env python3
"""
Automates a parameter sweep for the VC3D vc_flatten tool with enhanced reliability.
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
import os


def run_flattening(vc_flatten_bin, input_uri, output_path, iterations, method):
    """Executes vc_flatten as a subprocess with robust error handling."""
    cmd = [
        str(vc_flatten_bin),
        "--input",
        str(input_uri),
        "--output",
        str(output_path),
        "--iterations",
        str(iterations),
        "--method",
        str(method),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"vc_flatten failed: {result.stderr}")
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(
            f"vc_flatten failed to produce a valid output file at {output_path}"
        )
    return output_path


def run_slim_flattening(input_uri, output_path, iterations):
    """Executes ThaumatoAnakalyptor slim_uv as a subprocess."""
    import shutil

    # slim_uv operates in the same directory as the input file and appends _flatboi
    # To avoid polluting the source, we copy the input to the output_path's directory
    tmp_input = output_path.with_name(f"slim_input_{iterations}.obj")
    shutil.copy2(input_uri, tmp_input)

    cmd = [
        sys.executable,
        "-m",
        "ThaumatoAnakalyptor.slim_uv",
        "--path",
        str(tmp_input),
        "--iter",
        str(iterations),
        "--ic",
        "arap",
    ]

    # We must set PYTHONPATH to find ThaumatoAnakalyptor
    env = os.environ.copy()
    repo_root = Path(__file__).resolve().parents[1]
    thaumato_dir = repo_root / "villa" / "thaumato-anakalyptor"
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = f"{thaumato_dir}:{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = str(thaumato_dir)

    result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"slim_uv failed: {result.stderr}\n{result.stdout}")

    expected_output = tmp_input.with_name(f"{tmp_input.stem}_flatboi.obj")
    if not expected_output.exists() or expected_output.stat().st_size == 0:
        raise RuntimeError(f"slim_uv failed to produce {expected_output}")

    # Move to the requested output path
    shutil.move(expected_output, output_path)
    # Cleanup
    if tmp_input.exists():
        tmp_input.unlink()
    return output_path


def calculate_flatness_score(mesh_path):
    """
    Validates mesh and calculates a heuristic flatness score.
    Requires 'trimesh' library.
    """
    try:
        import trimesh

        mesh = trimesh.load(mesh_path, force="mesh")
        if not mesh.is_manifold:
            return float("inf")  # Penalty for non-manifold meshes
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
    vc_flatten_bin = (
        repo_root / "villa" / "volume-cartographer" / "build" / "bin" / "vc_flatten"
    )

    if not vc_flatten_bin.exists():
        print(f"Error: {vc_flatten_bin} does not exist.")
        sys.exit(1)

    # FastLocalVolume doesn't make sense for .obj meshes and often errors, skip it.
    print(f"Flattening mesh: {args.input}")

    iterations_grid = [10, 50, 100]
    methods = ["LSCM", "ABF++", "SLIM"]
    results = []

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        for iters in iterations_grid:
            for method in methods:
                tmp_out = Path(tmp_dir) / f"flattened_{iters}_{method}.obj"
                try:
                    if method == "SLIM":
                        run_slim_flattening(args.input, tmp_out, iters)
                    else:
                        run_flattening(
                            vc_flatten_bin, args.input, tmp_out, iters, method
                        )

                    score = calculate_flatness_score(tmp_out)
                    results.append(
                        {
                            "iterations": iters,
                            "method": method,
                            "score": score,
                            "path": str(tmp_out),
                        }
                    )
                except Exception as e:
                    print(f"Skipping iters={iters}, method={method}: {e}")

    if not results:
        print("No successful flattenings.")
        sys.exit(1)

    optimal = min(results, key=lambda x: x["score"])
    with open(output_dir / "optimal_config.json", "w") as f:
        json.dump(optimal, f, indent=2)

    print(
        f"Sweep complete. Optimal: {optimal['iterations']} iterations, {optimal['method']} method."
    )


if __name__ == "__main__":
    main()
