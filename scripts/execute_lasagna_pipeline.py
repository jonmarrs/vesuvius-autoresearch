#!/usr/bin/env python3
"""
Vesuvius Autoresearch: Lasagna Surface-Fitting Automation
Executes the full pipeline for high-priority Scroll 2/3 candidates:
1. Build Lasagna worklist
2. Compute structure tensors (GPU)
3. Execute Lasagna surface fitting (from villa submodule)
4. Generate prize evidence chain

Usage:
  uv run scripts/execute_lasagna_pipeline.py --limit 5
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _zarr_array_exists(path):
    return Path(path, ".zarray").exists()


def _structure_tensor_complete(path):
    root = Path(path)
    return _zarr_array_exists(root / "structure_tensor") and _zarr_array_exists(
        root / "normal" / "x" / "0"
    )


def _evidence_passed(evidence_dir, artifact_stem):
    meta = Path(evidence_dir) / "predictions" / f"{artifact_stem}_meta.json"
    if not meta.exists():
        return False
    try:
        data = json.loads(meta.read_text())
    except json.JSONDecodeError:
        return False
    return bool(data.get("vc3d_zarr_path") or data.get("prediction_zarr_path"))


def run_step(name, cmd, env=None):
    print(f"\n>>> Step: {name}")
    print(f"Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True, env=env)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error in step '{name}': {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Lasagna Surface-Fitting Automation")
    parser.add_argument(
        "--limit", type=int, default=3, help="Number of candidates to process"
    )
    parser.add_argument("--ranked", default="reports/scroll23_ranked_candidates.tsv")
    parser.add_argument("--checkpoint", default="best_model.pt")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute crop/ST/evidence even when outputs already exist",
    )
    args = parser.parse_args()

    # 1. Build Worklist
    worklist_json = "reports/lasagna_fiber_worklist.json"
    build_cmd = [
        sys.executable,
        "scripts/build_lasagna_fiber_worklist.py",
        "--ranked",
        args.ranked,
        "--out",
        worklist_json,
        "--limit",
        str(args.limit),
    ]
    if not run_step("Build Worklist", build_cmd):
        sys.exit(1)

    with open(worklist_json) as f:
        worklist = json.load(f)

    for item in worklist["candidates"]:
        rank = item["rank"]
        print(f"\n{'=' * 60}")
        print(f"Processing Candidate Rank {rank}: {item['artifact_stem']}")
        print(f"{'=' * 60}")

        # 2. Crop candidate window, then compute Structure Tensors on the crop.
        crop_output = item.get("cropped_volume_uri") or os.path.join(
            item["output_dir"], "candidate_crop.zarr"
        )
        crop_cmd = [
            sys.executable,
            "scripts/crop_candidate_zarr.py",
            "--input",
            item["local_uri"],
            "--output",
            crop_output,
            "--z",
            str(item["z"]),
            "--y",
            str(item["y"]),
            "--x",
            str(item["x"]),
            "--depth",
            str(item.get("depth", 128)),
            "--height",
            str(item["height"]),
            "--width",
            str(item["width"]),
        ]
        if not args.force and _zarr_array_exists(crop_output):
            print(
                f"Skipping crop for Rank {rank}; existing crop found at {crop_output}"
            )
        elif not run_step(f"Crop candidate window for Rank {rank}", crop_cmd):
            continue

        st_output = item["structure_tensor_output"]
        st_cmd = [
            sys.executable,
            "scripts/compute_structure_tensors.py",
            "--input",
            crop_output,
            "--output",
            st_output,
        ]
        if not args.force and _structure_tensor_complete(st_output):
            print(
                f"Skipping ST for Rank {rank}; complete tensor output found at {st_output}"
            )
        elif not run_step(f"Compute ST for cropped Rank {rank}", st_cmd):
            continue

        # 3. Lasagna Surface Fitting (Official Villa Tool)
        print(f"\n>>> Step: Lasagna Surface Fitting (Rank {rank})")
        lasagna_cmd = [
            sys.executable,
            "villa/lasagna/lasagna_analyze.py",
            "--volume",
            crop_output,
            "--output-dir",
            item["lasagna_output_dir"],
            "--iterations",
            "50",
            "--device",
            "cuda",
        ]
        if not args.force and os.path.exists(
            os.path.join(item["lasagna_output_dir"], "mesh.obj")
        ):
            print(
                f"Skipping Lasagna for Rank {rank}; existing mesh found in {item['lasagna_output_dir']}"
            )
        else:
            run_step(f"Run Lasagna Fitting for Rank {rank}", lasagna_cmd)

        # 4. Generate Prize Evidence Chain
        evidence_dir = item["evidence_output_dir"]
        if not args.force and _evidence_passed(evidence_dir, item["artifact_stem"]):
            print(
                f"Skipping evidence for Rank {rank}; PASS metadata already exists in {evidence_dir}"
            )
            continue
        evidence_cmd = [
            sys.executable,
            "scripts/run_villa_prize_evidence_chain.py",
            "--ranked",
            args.ranked,
            "--candidate-index",
            str(rank),
            "--out-dir",
            evidence_dir,
            "--execute",
            "--checkpoint",
            args.checkpoint,
        ]
        run_step(f"Generate Evidence for Rank {rank}", evidence_cmd)

    print("\nLasagna Pipeline Execution Complete.")


if __name__ == "__main__":
    main()
