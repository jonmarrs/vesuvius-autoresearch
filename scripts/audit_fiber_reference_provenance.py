"""Audit VC3D fiber annotation provenance without running or changing a scorer.

Usage: python scripts/audit_fiber_reference_provenance.py FOLDER --out audit.json

FOLDER must contain the complete downloaded JSON files to audit. Lengths are
straight-line distances between consecutive control points in the recorded
coordinate frame, not the arc length of interpolated line_points. Missing
interpolation metadata is counted as unknown, never inferred from the file's
optimization_mode. Input hashes bind the report to the bytes actually parsed.
Length shares are reported separately for each recorded coordinate frame;
files without one remain in an explicitly unknown group.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path


def _position(point):
    values = point["position"]
    if len(values) != 3 or any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
        for v in values
    ):
        raise ValueError("control point position must contain three finite numbers")
    return values


def audit_folder(folder: Path) -> dict:
    files = sorted(folder.glob("*.json"))
    if not files:
        raise ValueError(f"no annotation JSON files in {folder}")
    by_frame = defaultdict(lambda: {
        "file_count": 0,
        "by_interp_mode": defaultdict(lambda: {"spans": 0, "control_chord_length": 0.0}),
    })
    mode_spans = Counter()
    settings = Counter()
    predictions = Counter()
    frames = Counter()
    resolutions = Counter()
    inputs = []
    control_points = line_points = 0
    for path in files:
        captured = path.read_bytes()
        annotation = json.loads(captured)
        if annotation.get("type") != "vc3d_fiber":
            raise ValueError(f"{path}: expected a vc3d_fiber annotation")
        points = annotation["control_points"]
        positions = [_position(p) for p in points]
        frame = annotation.get("vc_open_data_coordinate_space") or "unknown"
        frames[frame] += 1
        by_frame[frame]["file_count"] += 1
        modes = by_frame[frame]["by_interp_mode"]
        resolutions[str(annotation.get("vc_open_data_source_original_resolution", "unknown"))] += 1
        control_points += len(points)
        line_points += len(annotation.get("line_points", []))
        for index, (start, end) in enumerate(zip(positions, positions[1:])):
            metadata = points[index].get("segment_to_next") or {}
            mode = metadata.get("interp_mode") or "unknown"
            distance = math.dist(start, end)
            if not math.isfinite(distance):
                raise ValueError(f"{path}: non-finite control chord length")
            modes[mode]["spans"] += 1
            modes[mode]["control_chord_length"] += distance
            mode_spans[mode] += 1
            if mode == "trace":
                # Keep the whole recorded config; comparing only three fields
                # cannot establish equality to all current tracer defaults.
                settings[json.dumps(metadata.get("config"), sort_keys=True)] += 1
                predictions[metadata.get("fiber_manifest") or "unknown"] += 1
        inputs.append({
            "name": path.name,
            "bytes": len(captured),
            "sha256": hashlib.sha256(captured).hexdigest(),
        })
    for group in by_frame.values():
        modes = group["by_interp_mode"]
        total = sum(row["control_chord_length"] for row in modes.values())
        group["total_control_chord_length"] = total
        for row in modes.values():
            row["control_chord_share"] = row["control_chord_length"] / total if total else None
        group["by_interp_mode"] = dict(sorted(modes.items()))
    return {
        "schema_version": 1,
        "measurement": "Euclidean distance between consecutive control points; not line_points arc length",
        "file_count": len(files),
        "control_point_count": control_points,
        "line_point_count": line_points,
        "coordinate_frame_files": dict(sorted(frames.items())),
        "source_original_resolution_files": dict(sorted(resolutions.items())),
        "interp_mode_span_counts": dict(sorted(mode_spans.items())),
        "by_coordinate_frame": dict(sorted(by_frame.items())),
        "trace_configs": [
            {"config": json.loads(config), "spans": count}
            for config, count in sorted(settings.items())
        ],
        "trace_fiber_manifest_spans": dict(sorted(predictions.items())),
        "inputs": inputs,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    # Putting the output in the input folder would contaminate the next audit.
    if args.out.resolve().parent == args.folder.resolve():
        parser.error("--out must be outside the annotation folder")
    report = audit_folder(args.folder)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: report[k] for k in (
        "file_count", "control_point_count", "line_point_count", "interp_mode_span_counts", "by_coordinate_frame"
    )}, indent=2))


if __name__ == "__main__":
    main()
