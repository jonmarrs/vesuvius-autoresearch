#!/usr/bin/env python3
"""
Build a Scroll 2/3 Lasagna/fiber worklist from ranked prize candidates.

The goal is to route hard, occupied candidate windows through surface/fiber
preprocessing before more ink inference, matching the official villa #191
opportunity around compressed and highly curved regions.
"""
import argparse
import csv
import json
import shlex
from pathlib import Path


def _float(row, key, default=0.0):
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def _int(row, key, default=0):
    try:
        return int(float(row.get(key, default)))
    except (TypeError, ValueError):
        return default


def _artifact_stem(row):
    width = _int(row, "width", _int(row, "patch_size", 64))
    height = _int(row, "height", _int(row, "patch_size", 64))
    return row.get("artifact_stem") or f"pred_{_int(row, 'z')}_{_int(row, 'y')}_{_int(row, 'x')}_{width}x{height}"


def _candidate_score(row):
    review_score = _float(row, "review_score")
    ink_max = _float(row, "ink_max")
    ink_std = _float(row, "ink_std")
    fiber_mean = _float(row, "fiber_mean")
    occupied_bonus = 0.75 if row.get("ct_occupied_status") == "true" else 0.0
    prediction_bonus = 0.35 if row.get("prediction_found") == "true" else 0.0
    core_bonus = 0.25 if row.get("division") in {"div_90", "div_100"} else 0.0
    # Prefer regions with geometry/fiber signal and some ink structure, but keep
    # high-priority unpredicted candidates eligible for first-pass preprocessing.
    return review_score + occupied_bonus + prediction_bonus + core_bonus + 2.0 * ink_max + ink_std + 0.5 * fiber_mean


def _load_rows(ranked_path):
    with open(ranked_path, "r", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _work_item(row, rank, output_root, python_executable):
    stem = _artifact_stem(row)
    out_dir = Path(output_root) / f"{rank:03d}_{stem}"
    crop_dir = out_dir / "candidate_crop.zarr"
    tensor_dir = out_dir / "structure_tensors.zarr"
    lasagna_dir = out_dir / "lasagna"
    evidence_dir = out_dir / "evidence"
    z = _int(row, "z")
    y = _int(row, "y")
    x = _int(row, "x")
    width = _int(row, "width", _int(row, "patch_size", 64))
    height = _int(row, "height", _int(row, "patch_size", 64))
    depth = _int(row, "depth", 128)

    crop_cmd = [
        python_executable,
        "scripts/crop_candidate_zarr.py",
        "--input",
        row.get("local_uri", ""),
        "--output",
        str(crop_dir),
        "--z",
        str(z),
        "--y",
        str(y),
        "--x",
        str(x),
        "--depth",
        str(depth),
        "--height",
        str(height),
        "--width",
        str(width),
    ]
    structure_tensor_cmd = [
        python_executable,
        "scripts/compute_structure_tensors.py",
        "--input",
        str(crop_dir),
        "--output",
        str(tensor_dir),
    ]
    evidence_cmd = [
        python_executable,
        "scripts/run_villa_prize_evidence_chain.py",
        "--ranked",
        "reports/scroll23_ranked_candidates.tsv",
        "--candidate-index",
        str(rank),
        "--out-dir",
        str(evidence_dir),
        "--execute",
        "--checkpoint",
        "best_model.pt",
    ]
    lasagna_note = (
        "After updating the villa submodule to an upstream commit with lasagna/, "
        "run Lasagna preprocessing/training against this candidate directory and "
        "export VC3D-compatible OME-Zarr overlays for review."
    )

    return {
        "rank": rank,
        "priority_score": round(_candidate_score(row), 6),
        "official_issue": "https://github.com/ScrollPrize/villa/issues/191",
        "scroll_id": row.get("scroll_id"),
        "short_id": row.get("short_id"),
        "division": row.get("division"),
        "z": z,
        "y": y,
        "x": x,
        "width": width,
        "height": height,
        "depth": depth,
        "local_uri": row.get("local_uri", ""),
        "cropped_volume_uri": str(crop_dir),
        "artifact_stem": stem,
        "ct_occupied_status": row.get("ct_occupied_status", "unknown"),
        "ct_chunk_coord": row.get("ct_chunk_coord", ""),
        "ink_max": _float(row, "ink_max"),
        "ink_std": _float(row, "ink_std"),
        "fiber_mean": _float(row, "fiber_mean"),
        "output_dir": str(out_dir),
        "structure_tensor_output": str(tensor_dir),
        "lasagna_output_dir": str(lasagna_dir),
        "evidence_output_dir": str(evidence_dir),
        "crop_command": shlex.join(crop_cmd),
        "structure_tensor_command": shlex.join(structure_tensor_cmd),
        "evidence_command": shlex.join(evidence_cmd),
        "lasagna_note": lasagna_note,
    }


def build_worklist(ranked_path, output_root="reports/lasagna_fiber_candidates", limit=12, python_executable=".venv/bin/python"):
    rows = _load_rows(ranked_path)
    eligible = [
        row
        for row in rows
        if row.get("local_uri")
        and row.get("submittable_window") == "true"
        and row.get("ct_occupied_status", "unknown") != "false"
    ]
    eligible.sort(key=_candidate_score, reverse=True)
    return [_work_item(row, rank, output_root, python_executable) for rank, row in enumerate(eligible[:limit])]


def _write_tsv(path, rows):
    if not rows:
        Path(path).write_text("")
        return
    fields = [
        "rank",
        "priority_score",
        "official_issue",
        "scroll_id",
        "short_id",
        "division",
        "z",
        "y",
        "x",
        "width",
        "height",
        "depth",
        "local_uri",
        "cropped_volume_uri",
        "artifact_stem",
        "ct_occupied_status",
        "ct_chunk_coord",
        "ink_max",
        "ink_std",
        "fiber_mean",
        "output_dir",
        "structure_tensor_output",
        "lasagna_output_dir",
        "evidence_output_dir",
    ]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ranked", default="reports/scroll23_ranked_candidates.tsv")
    parser.add_argument("--out", default="reports/lasagna_fiber_worklist.json")
    parser.add_argument("--tsv", default="reports/lasagna_fiber_worklist.tsv")
    parser.add_argument("--output-root", default="reports/lasagna_fiber_candidates")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--python-executable", default=".venv/bin/python")
    args = parser.parse_args()

    rows = build_worklist(args.ranked, args.output_root, args.limit, args.python_executable)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump({"ranked_path": args.ranked, "opportunity": "villa-issue-191", "candidates": rows}, f, indent=2)
    _write_tsv(args.tsv, rows)
    print(f"Wrote {len(rows)} Lasagna/fiber candidates to {args.out}")
    print(f"Wrote TSV to {args.tsv}")


if __name__ == "__main__":
    main()
