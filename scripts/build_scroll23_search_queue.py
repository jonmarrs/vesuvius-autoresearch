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
            except Exception as exc:
                print(
                    "Warning: failed to read prediction score "
                    f"from {path}: {type(exc).__name__}: {exc}"
                )
                return 0.0
    return 0.0


def _local_uri(short_id, div_name):
    path = Path("local_data") / f"{short_id}_Divisions" / div_name / "0"
    if path.exists():
        return str(path)
    return ""


def _read_zarr_array_info(local_uri):
    zarray_path = Path(local_uri) / ".zarray"
    if not zarray_path.exists():
        return None
    with open(zarray_path) as f:
        meta = json.load(f)
    return {
        "shape": tuple(int(v) for v in meta["shape"]),
        "chunks": tuple(int(v) for v in meta["chunks"]),
        "dimension_separator": meta.get("dimension_separator", "."),
    }


def _occupied_chunk_coords(local_uri, limit=5000):
    info = _read_zarr_array_info(local_uri)
    if not info:
        return []
    root = Path(local_uri)
    coords = []
    if info["dimension_separator"] == "/":
        for z_dir in root.iterdir():
            if not z_dir.is_dir() or not z_dir.name.isdigit():
                continue
            for y_dir in z_dir.iterdir():
                if not y_dir.is_dir() or not y_dir.name.isdigit():
                    continue
                for x_file in y_dir.iterdir():
                    if x_file.is_file() and x_file.name.isdigit():
                        coords.append(
                            (int(z_dir.name), int(y_dir.name), int(x_file.name))
                        )
                        if len(coords) >= limit:
                            return coords
    else:
        for chunk_file in root.iterdir():
            if not chunk_file.is_file():
                continue
            parts = chunk_file.name.split(".")
            if len(parts) == 3 and all(part.isdigit() for part in parts):
                coords.append(tuple(int(part) for part in parts))
                if len(coords) >= limit:
                    return coords
    return coords


def _occupied_windows(local_uri, windows_per_division, patch_size):
    info = _read_zarr_array_info(local_uri)
    coords = _occupied_chunk_coords(local_uri)
    if not info or not coords:
        return []

    chunks = info["chunks"]
    shape = info["shape"]
    center = tuple(
        sum(coord[axis] for coord in coords) / len(coords) for axis in range(3)
    )
    coords = sorted(
        coords,
        key=lambda coord: sum((coord[axis] - center[axis]) ** 2 for axis in range(3)),
    )
    windows = []
    seen = set()
    for zc, yc, xc in coords:
        z = min(max(0, zc * chunks[0]), max(0, shape[0] - 1))
        y = min(
            max(0, yc * chunks[1] + chunks[1] // 2 - patch_size // 2),
            max(0, shape[1] - patch_size),
        )
        x = min(
            max(0, xc * chunks[2] + chunks[2] // 2 - patch_size // 2),
            max(0, shape[2] - patch_size),
        )
        key = (z, y, x)
        if key in seen:
            continue
        seen.add(key)
        windows.append(key)
        if len(windows) >= windows_per_division:
            break
    return windows


def build_queue(
    divisions, windows_per_division, patch_size, voxel_um, prediction_dir=None
):
    rows = []
    window_mm = patch_size * voxel_um / 1000.0
    submittable_window = patch_size <= 64 or window_mm <= 0.5 + 1e-9

    for scroll_key, scroll in SCROLLS.items():
        for div in divisions:
            div_name = f"div_{int(div * 100)}"
            local_uri = _local_uri(scroll["short_id"], div_name)
            local_bonus = 0.25 if local_uri else 0.0
            pred_score = _prediction_score(prediction_dir, scroll_key, div_name)

            occupied_windows = (
                _occupied_windows(local_uri, windows_per_division, patch_size)
                if local_uri
                else []
            )
            for rank_in_div in range(windows_per_division):
                if rank_in_div < len(occupied_windows):
                    z, y, x = occupied_windows[rank_in_div]
                else:
                    # Fallback deterministic center-biased grid when no local
                    # zarr occupancy is available.
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

    divisions = [
        float(part.strip()) / 100.0
        for part in args.divisions.split(",")
        if part.strip()
    ]
    rows = build_queue(
        divisions,
        args.windows_per_division,
        args.patch_size,
        args.voxel_um,
        args.prediction_dir,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=list(rows[0].keys()), delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "queue_path": str(out_path),
        "num_candidates": len(rows),
        "patch_size": args.patch_size,
        "voxel_um": args.voxel_um,
        "submittable_window": args.patch_size <= 64
        or args.patch_size * args.voxel_um / 1000.0 <= 0.5 + 1e-9,
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
