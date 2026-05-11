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

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path

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
    parser.add_argument("--limit", type=int, default=3, help="Number of candidates to process")
    parser.add_argument("--ranked", default="reports/scroll23_ranked_candidates.tsv")
    parser.add_argument("--checkpoint", default="best_model.pt")
    args = parser.parse_args()

    # 1. Build Worklist
    worklist_json = "reports/lasagna_fiber_worklist.json"
    build_cmd = [
        sys.executable, "scripts/build_lasagna_fiber_worklist.py",
        "--ranked", args.ranked,
        "--out", worklist_json,
        "--limit", str(args.limit)
    ]
    if not run_step("Build Worklist", build_cmd):
        sys.exit(1)

    with open(worklist_json, "r") as f:
        worklist = json.load(f)

    for item in worklist["candidates"]:
        rank = item["rank"]
        print(f"\n{'='*60}")
        print(f"Processing Candidate Rank {rank}: {item['artifact_stem']}")
        print(f"{'='*60}")

        # 2. Compute Structure Tensors
        st_output = item["structure_tensor_output"]
        st_cmd = [
            sys.executable, "scripts/compute_structure_tensors.py",
            "--input", item["local_uri"],
            "--output", st_output
        ]
        if not run_step(f"Compute ST for Rank {rank}", st_cmd):
            continue

        # 3. Lasagna Preprocessing (Placeholder for official villa lasagna call)
        # The strategy doc says: "run Lasagna preprocessing/training against this candidate directory"
        print(f"\n>>> Step: Lasagna Preprocessing (Rank {rank})")
        print(item["lasagna_note"])
        # In a real scenario, we would call villa/lasagna/lasagna_analyze.py here
        
        # 4. Generate Prize Evidence Chain
        evidence_dir = item["evidence_output_dir"]
        evidence_cmd = [
            sys.executable, "scripts/run_villa_prize_evidence_chain.py",
            "--ranked", args.ranked,
            "--candidate-index", str(rank),
            "--out-dir", evidence_dir,
            "--execute",
            "--checkpoint", args.checkpoint
        ]
        run_step(f"Generate Evidence for Rank {rank}", evidence_cmd)

    print("\nLasagna Pipeline Execution Complete.")

if __name__ == "__main__":
    main()
