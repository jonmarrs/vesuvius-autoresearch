#!/usr/bin/env python3
"""
Build a reproducible Scroll 2/3 candidate search queue.

The queue is intentionally metadata-first: it ranks deterministic windows by
location, patch-size compliance, local-data availability, and optional model
prediction scores without downloading anything.
"""
import argparse
import csv
import json
import os
from pathlib import Path


SCROLLS = {
    "Scroll2": {
        "scroll_id": "Scroll 2",
        "short_id": "PHerc0125",
        "priority": 1.0,
        "notes": "First Letters / First Title target",
    },
    "Scroll3": {
        "scroll_id": "Scroll 3",
        "short_id": "PHerc0332",
        "priority": 1.0,
        "notes": "First Letters / First Title target",
    },
}


def _prediction_score(prediction_dir, scroll_key, div_name):
    if not prediction_dir:
        return 0.0
    pred_dir = Path(prediction_dir)
    candidates = [
        pred_dir / f"{scroll_key}_{div_name}_ink.npy",
        pred_dir / f"{SCROLLS[scroll_key]['short_id']}_{div_name}_ink.npy",
    ]
    for path in candidates:
        if path.exists():
            try:
                import numpy as np

                arr = np.load(path)
                return float(arr.mean() + 2.0 * arr.std() + arr.max())
            except Exception:
                return 0.0
    return 0.0


def _local_uri(short_id, div_name):
    path = Path("local_data") / f"{short_id}_Divisions" / div_name / "0"
    if path.exists():
        return str(path)
    return ""


def build_queue(divisions, windows_per_division, patch_size, voxel_um, prediction_dir=None):
    rows = []
    window_mm = patch_size * voxel_um / 1000.0
    submittable_window = patch_size <= 64 or window_mm <= 0.5 + 1e-9

    for scroll_key, scroll in SCROLLS.items():
        for div in divisions:
            div_name = f"div_{int(div * 100)}"
            local_uri = _local_uri(scroll["short_id"], div_name)
            local_bonus = 0.25 if local_uri else 0.0
            pred_score = _prediction_score(prediction_dir, scroll_key, div_name)

            # Use a deterministic center-biased grid. Actual shape-specific
            # clipping is done at inference time by the loader.
            for rank_in_div in range(windows_per_division):
                offset = rank_in_div - (windows_per_division // 2)
                z = int(1000 + div * 8000)
                y = int(2048 + offset * patch_size)
                x = int(2048 - offset * patch_size)
                core_bonus = 0.35 if div >= 0.9 else 0.0
                score = scroll["priority"] + core_bonus + local_bonus + pred_score
                rows.append(
                    {
                        "priority": f"{score:.4f}",
                        "scroll_key": scroll_key,
                        "scroll_id": scroll["scroll_id"],
                        "short_id": scroll["short_id"],
                        "division": div_name,
                        "z": z,
                        "y": y,
                        "x": x,
                        "width": patch_size,
                        "height": patch_size,
                        "patch_size": patch_size,
                        "voxel_um": voxel_um,
                        "ml_window_mm": f"{window_mm:.4f}",
                        "submittable_window": str(submittable_window).lower(),
                        "local_uri": local_uri,
                        "notes": scroll["notes"],
                    }
                )

    rows.sort(key=lambda row: float(row["priority"]), reverse=True)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="reports/scroll23_search_queue.tsv")
    parser.add_argument("--manifest", default="reports/scroll23_search_queue.json")
    parser.add_argument("--windows-per-division", type=int, default=5)
    parser.add_argument("--patch-size", type=int, default=64)
    parser.add_argument("--voxel-um", type=float, default=7.91)
    parser.add_argument("--prediction-dir", default=None)
    parser.add_argument("--divisions", default="0,10,20,30,40,50,60,70,80,90,100")
    args = parser.parse_args()

    divisions = [float(part.strip()) / 100.0 for part in args.divisions.split(",") if part.strip()]
    rows = build_queue(divisions, args.windows_per_division, args.patch_size, args.voxel_um, args.prediction_dir)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "queue_path": str(out_path),
        "num_candidates": len(rows),
        "patch_size": args.patch_size,
        "voxel_um": args.voxel_um,
        "submittable_window": args.patch_size <= 64 or args.patch_size * args.voxel_um / 1000.0 <= 0.5 + 1e-9,
        "scrolls": SCROLLS,
    }
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Wrote {len(rows)} candidates to {out_path}")
    print(f"Wrote manifest to {manifest_path}")


if __name__ == "__main__":
    main()
