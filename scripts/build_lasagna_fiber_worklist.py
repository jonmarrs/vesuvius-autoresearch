#!/usr/bin/env python3
"""
Build a Scroll 2/3 Lasagna/fiber worklist from ranked prize candidates.

The goal is to route hard, occupied candidate windows through surface/fiber
preprocessing before more ink inference, matching the official villa #191
opportunity around compressed and highly curved regions.
"""

import argparse
import csv
import html
import json
import math
import shlex
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.candidate_artifacts import integer, write_json
from scripts.inference.run_ranked_inference import (
    build_predict_command,
    read_candidate_table,
    resolve_candidate_paths,
)
from scripts.labeling.label_artifacts import publish_new
from scripts.worklist_publication import publish_pair
from vesuvius_autoresearch.core.prediction_artifacts import validate_plan_paths


def _float(row, key, default=0.0):
    try:
        value = float(row.get(key) or default)
        if not math.isfinite(value):
            raise ValueError
        return value
    except (TypeError, ValueError) as exc:
        raise ValueError(f"candidate {key} must be finite") from exc


def _int(row, key, default=0):
    return integer(row.get(key, default), f"candidate {key}")


def _artifact_stem(row):
    width = _int(row, "width", _int(row, "patch_size", 64))
    height = _int(row, "height", _int(row, "patch_size", 64))
    return (
        row.get("artifact_stem")
        or f"pred_{_int(row, 'z')}_{_int(row, 'y')}_{_int(row, 'x')}_{width}x{height}"
    )


def _priority_components(row):
    review_score = _float(row, "review_score")
    ink_max = _float(row, "ink_max")
    ink_std = _float(row, "ink_std")
    fiber_mean = _float(row, "fiber_mean")
    occupied_bonus = 0.75 if row.get("ct_occupied_status") == "true" else 0.0
    prediction_bonus = 0.35 if row.get("prediction_found") == "true" else 0.0
    core_bonus = 0.25 if row.get("division") in {"div_90", "div_100"} else 0.0
    # Prefer regions with geometry/fiber signal and some ink structure, but keep
    # high-priority unpredicted candidates eligible for first-pass preprocessing.
    return {
        "review_score": review_score,
        "occupied_bonus": occupied_bonus,
        "prediction_bonus": prediction_bonus,
        "core_bonus": core_bonus,
        "weighted_ink_max": 2.0 * ink_max,
        "ink_std": ink_std,
        "weighted_fiber_mean": 0.5 * fiber_mean,
    }


def _candidate_score(row):
    return sum(_priority_components(row).values())


def _work_item(
    row,
    rank,
    output_root,
    python_executable,
    ranked_path,
    candidate_index,
    ranked_sha256,
    input_base_dir,
    checkpoint,
):
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
        str(REPO_ROOT / "scripts/crop_candidate_zarr.py"),
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
        str(REPO_ROOT / "scripts/compute_structure_tensors.py"),
        "--input",
        str(crop_dir),
        "--output",
        str(tensor_dir),
    ]
    evidence_cmd = [
        python_executable,
        str(REPO_ROOT / "scripts/run_villa_prize_evidence_chain.py"),
        "--ranked",
        str(Path(ranked_path).resolve()),
        "--candidate-index",
        str(candidate_index),
        "--ranked-sha256",
        ranked_sha256,
        "--input-base-dir",
        str(input_base_dir),
        "--out-dir",
        str(evidence_dir),
        "--execute",
        "--checkpoint",
        str(checkpoint),
    ]
    for key, flag in (
        ("train_mask_path", "--train-mask"),
        ("predict_mask_path", "--predict-mask"),
    ):
        if row.get(key):
            evidence_cmd.extend([flag, str(Path(row[key]).resolve())])
    lasagna_note = (
        "This worklist prepares CT crops and structure tensors; it does not fit a "
        "surface. Follow villa/lasagna/README.md with an explicit fit configuration. "
        "Optional prize evidence is separate CT prediction, not a fitted-surface evaluation."
    )

    return {
        "rank": rank,
        "candidate_index": candidate_index,
        "ranked_path": str(Path(ranked_path).resolve()),
        "ranked_sha256": ranked_sha256,
        "input_base_dir": str(input_base_dir),
        "priority_score": round(_candidate_score(row), 6),
        "priority_components": _priority_components(row),
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
        "train_mask_path": str(Path(row["train_mask_path"]).resolve())
        if row.get("train_mask_path")
        else None,
        "predict_mask_path": str(Path(row["predict_mask_path"]).resolve())
        if row.get("predict_mask_path")
        else None,
        "lasagna_note": lasagna_note,
    }


def build_worklist(
    ranked_path,
    output_root="reports/lasagna_fiber_candidates",
    limit=12,
    python_executable=sys.executable,
    *,
    checkpoint="best_model.pt",
):
    _, report, _ = _plan_worklist(
        ranked_path, output_root, limit, python_executable, checkpoint
    )
    return report["candidates"]


def _plan_worklist(
    ranked_path,
    output_root,
    limit,
    python_executable,
    checkpoint,
    ranked_reference=None,
):
    limit = integer(limit, "limit", 1)
    source, rows = read_candidate_table(ranked_path)
    source_info = source.provenance()
    input_base_dir = Path.cwd().resolve()
    rows = [resolve_candidate_paths(row, input_base_dir) for row in rows]
    eligible = [
        (index, row)
        for index, row in enumerate(rows)
        if row.get("local_uri")
        and row.get("submittable_window") == "true"
        and row.get("ct_occupied_status", "unknown") != "false"
    ]
    for _, row in eligible:
        build_predict_command(row)  # share strict geometry and artifact-name validation
        integer(row.get("depth", 128), "candidate depth", 1)
        if not math.isfinite(_candidate_score(row)):
            raise ValueError("candidate priority score must be finite")
    eligible.sort(key=lambda item: _candidate_score(item[1]), reverse=True)
    output_root = Path(output_root).resolve()
    checkpoint = Path(checkpoint).resolve()
    python_executable = (
        str(Path(python_executable).absolute())
        if "/" in str(python_executable)
        else str(python_executable)
    )
    items = [
        _work_item(
            row,
            rank,
            output_root,
            python_executable,
            ranked_reference or source.path,
            index,
            source_info["sha256"],
            input_base_dir,
            checkpoint,
        )
        for rank, (index, row) in enumerate(eligible[:limit])
    ]
    return (
        source,
        {
            "contract": 2,
            "ranked_path": str(source.path),
            "source": source_info,
            "input_base_dir": str(input_base_dir),
            "opportunity": "villa-issue-191",
            "scope": "CT preprocessing plan; priority is a heuristic, not model quality or prize eligibility",
            "selection": {
                "source_rows": len(rows),
                "eligible_rows": len(eligible),
                "selected_rows": len(items),
                "limit": limit,
                "rule": "local_uri present, submittable_window=true, ct_occupied_status!=false",
                "selected_unknown_occupancy": sum(
                    item["ct_occupied_status"] not in {"true", "false"}
                    for item in items
                ),
            },
            "candidates": items,
        },
        rows,
    )


def _write_tsv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "rank",
        "candidate_index",
        "ranked_path",
        "ranked_sha256",
        "input_base_dir",
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
        writer = csv.DictWriter(
            f, fieldnames=fields, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _validate_paths(outputs, source, rows, items, checkpoint):
    reads = [
        (source.path, "ranked table"),
        (checkpoint, "checkpoint"),
        (REPO_ROOT / "autoresearch.lock", "research lock"),
    ]
    for row in rows:
        for key in ("local_uri", "train_mask_path", "predict_mask_path"):
            if row.get(key) and "://" not in row[key]:
                reads.append((row[key], f"candidate {key}"))
    writes = [(path, "worklist output") for path in outputs]
    writes += [
        (item["output_dir"], f"candidate {item['rank']} planned artifacts")
        for item in items
    ]
    for path in outputs:
        if Path(path).is_symlink() or (
            Path(path).exists() and not Path(path).is_file()
        ):
            raise ValueError(f"worklist output must be a regular file: {path}")
    validate_plan_paths(writes, reads)


def _readme(report):
    lines = [
        "# CT preprocessing worklist",
        "",
        report["scope"],
        "",
        "Source/evidence paths are resolved from the recorded input base directory.",
        "This bundle plans crops and tensors; it does not fit a surface or run inference.",
        "",
        "| Priority rank | Source candidate index | Artifact | Heuristic priority |",
        "| --- | --- | --- | --- |",
    ]
    for item in report["candidates"]:
        stem = (
            html.escape(item["artifact_stem"])
            .replace("|", "&#124;")
            .replace("`", "&#96;")
        )
        lines.append(
            f"| {item['rank']} | {item['candidate_index']} | <code>{stem}</code> | {item['priority_score']} |"
        )
    lines += [
        "",
        "See worklist.json for score components, selection counts and commands.",
        "The captured sources/ranked.tsv and its SHA-256 pin evidence row identity.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--ranked", default="reports/scroll23_ranked_candidates.tsv")
    parser.add_argument("--out", default=None)
    parser.add_argument("--tsv", default=None)
    parser.add_argument(
        "--bundle-dir",
        type=Path,
        help="Publish a new review bundle containing JSON, TSV, README and captured ranked source",
    )
    parser.add_argument("--checkpoint", default="best_model.pt")
    parser.add_argument("--output-root", default="reports/lasagna_fiber_candidates")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--python-executable", default=sys.executable)
    args = parser.parse_args(argv)
    if args.bundle_dir and (args.out is not None or args.tsv is not None):
        parser.error("--bundle-dir cannot be combined with --out or --tsv")
    bundle = args.bundle_dir.absolute() if args.bundle_dir else None
    source, report, rows = _plan_worklist(
        args.ranked,
        args.output_root,
        args.limit,
        args.python_executable,
        args.checkpoint,
        bundle / "sources/ranked.tsv" if bundle else None,
    )
    if not report["candidates"]:
        raise ValueError("no eligible local candidates; previous worklist retained")
    if bundle:
        _validate_paths(
            [bundle],
            source,
            rows,
            report["candidates"],
            Path(args.checkpoint).resolve(),
        )
        with publish_new(bundle) as staging:
            source.copy_into(staging, "ranked.tsv")
            _write_tsv(staging / "worklist.tsv", report["candidates"])
            write_json(staging / "worklist.json", report)
            (staging / "README.md").write_text(_readme(report), encoding="utf-8")
            source.verify()
        print(
            f"Published {len(report['candidates'])} candidates to review bundle: {bundle}"
        )
        return bundle
    output = Path(args.out or "reports/lasagna_fiber_worklist.json").absolute()
    tsv = Path(args.tsv or "reports/lasagna_fiber_worklist.tsv").absolute()

    def verify():
        _validate_paths(
            [output, tsv],
            source,
            rows,
            report["candidates"],
            Path(args.checkpoint).resolve(),
        )
        source.verify()

    verify()

    def render(json_path, tsv_path):
        write_json(json_path, report)
        _write_tsv(tsv_path, report["candidates"])

    publish_pair([output, tsv], render, verify)
    print(f"Wrote {len(report['candidates'])} candidates to {output} and {tsv}")
    return output


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, csv.Error, RuntimeError) as exc:
        print(f"Worklist planning failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
