#!/usr/bin/env python3
"""
Vesuvius Autoresearch: Review Promotion Tool
Packages a high-confidence candidate for manual verification in Crackle Viewer.
"""

import argparse
import json
import os
import shutil
from pathlib import Path


def promote_to_review(metadata_path, review_dir="reports/review_queue"):
    with open(metadata_path) as f:
        meta = json.load(f)

    candidate_id = Path(metadata_path).stem.replace("_meta", "")
    target_dir = Path(review_dir) / candidate_id
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"Promoting {candidate_id} to manual review...")

    # 1. Copy Metadata
    shutil.copy(metadata_path, target_dir / "metadata.json")

    # 2. Copy Visualization
    if meta.get("visualization_path") and os.path.exists(meta["visualization_path"]):
        shutil.copy(meta["visualization_path"], target_dir / "preview.png")

    # 3. Generate Crackle Project File
    crackle_project = {
        "volume": meta.get("source_uri"),
        "prediction": meta.get("vc3d_zarr_path"),
        "fiber_prediction": meta.get("fiber_vc3d_zarr_path"),
        "position": meta.get("position_xyz"),
        "status": "UNREVIEWED",
    }
    with open(target_dir / "crackle_project.json", "w") as f:
        json.dump(crackle_project, f, indent=2)

    print(f"Review package ready at: {target_dir}")
    print(
        f"Run: uv run scripts/launch_crackle_viewer.py --project {target_dir}/crackle_project.json"
    )


def main():
    parser = argparse.ArgumentParser(description="Promote candidate to manual review")
    parser.add_argument(
        "--metadata", required=True, help="Path to prediction metadata JSON"
    )
    args = parser.parse_args()

    promote_to_review(args.metadata)


if __name__ == "__main__":
    main()
