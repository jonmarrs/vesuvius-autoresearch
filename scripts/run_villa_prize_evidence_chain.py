#!/usr/bin/env python3
"""
Build a villa-compatible prize evidence directory for one ranked candidate.

The chain is intentionally conservative: it can run predict.py, but it will not
mark placeholders as ready. The output directory contains the command manifest,
candidate row, patched prediction metadata, train/predict masks, and a
PRIZE_READINESS_REPORT.json from scripts.validate_prize_artifact.
"""

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_ranked_inference import build_predict_command, load_candidates
from scripts.validate_prize_artifact import validate


def _as_int(row, key, default=0):
    try:
        return int(float(row.get(key, default)))
    except (TypeError, ValueError):
        return default


def _as_float(row, key, default=0.0):
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def _artifact_stem(row):
    width = _as_int(row, "width", _as_int(row, "patch_size", 64))
    height = _as_int(row, "height", _as_int(row, "patch_size", 64))
    return (
        row.get("artifact_stem")
        or f"pred_{_as_int(row, 'z')}_{_as_int(row, 'y')}_{_as_int(row, 'x')}_{width}x{height}"
    )


def select_candidate(ranked_path, index=0):
    rows = load_candidates(ranked_path, require_local=False)
    if not rows:
        raise ValueError(f"no candidates found in {ranked_path}")
    if index < 0 or index >= len(rows):
        raise IndexError(f"candidate index {index} outside 0..{len(rows) - 1}")
    return rows[index]


def _write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _write_masks(out_dir, row):
    width = _as_int(row, "width", _as_int(row, "patch_size", 64))
    height = _as_int(row, "height", _as_int(row, "patch_size", 64))
    train_mask = np.zeros((height, width), dtype=bool)
    predict_mask = np.ones((height, width), dtype=bool)
    train_path = Path(out_dir) / "train_mask.npy"
    predict_path = Path(out_dir) / "predict_mask.npy"
    np.save(train_path, train_mask)
    np.save(predict_path, predict_mask)
    return train_path, predict_path


def patch_prediction_metadata(metadata_path, row, train_mask_path, predict_mask_path):
    metadata_path = Path(metadata_path)
    if metadata_path.exists():
        with open(metadata_path) as f:
            metadata = json.load(f)
    else:
        metadata = {}

    width = _as_int(row, "width", _as_int(row, "patch_size", 64))
    height = _as_int(row, "height", _as_int(row, "patch_size", 64))
    patch_size = _as_int(row, "patch_size", max(width, height))
    voxel_um = _as_float(
        row,
        "voxel_um",
        _as_float(row, "voxel_size_um", metadata.get("voxel_size_um", 7.91)),
    )
    source_uri = (
        row.get("local_uri") or row.get("source_uri") or metadata.get("source_uri")
    )

    metadata.update(
        {
            "scroll_id": row.get("scroll_id") or metadata.get("scroll_id"),
            "short_id": row.get("short_id"),
            "division": row.get("division"),
            "source_uri": source_uri,
            "segmentation_id": row.get("segmentation_id")
            or metadata.get("segmentation_id")
            or source_uri,
            "position_xyz": [_as_int(row, "x"), _as_int(row, "y"), _as_int(row, "z")],
            "x": _as_int(row, "x"),
            "y": _as_int(row, "y"),
            "z": _as_int(row, "z"),
            "width_px": width,
            "height_px": height,
            "patch_size": patch_size,
            "ml_window_px": patch_size,
            "voxel_size_um": voxel_um,
            "ml_window_mm": patch_size * voxel_um / 1000.0,
            "scale_bar_cm": True,
            "train_mask_path": str(train_mask_path),
            "predict_mask_path": str(predict_mask_path),
            "source_image_is_placeholder": False,
            "metadata_is_dry_run": False,
            "evidence_mode": "real_prediction",
        }
    )
    _write_json(metadata_path, metadata)
    return metadata


def _attach_neural_tracing_plan(out_dir, row, python_executable):
    """Optionally produce a neural_tracing trace_service plan for this candidate.

    Calls scripts/launch_neural_tracing.py to resolve the candidate's OME-zarr
    volume + checkpoint, then copies the resulting marker into the candidate
    evidence directory so reviewers can see whether trace_service is launchable
    for this submission window. Tracing itself is not executed; this only adds
    the readiness marker, matching the chain's conservative "no placeholders"
    posture.
    """
    out_dir = Path(out_dir)
    tracing_marker = out_dir / "neural_tracing.json"
    launcher = REPO_ROOT / "scripts" / "launch_neural_tracing.py"
    if not launcher.exists():
        return None

    cmd = [
        python_executable,
        str(launcher),
        "--scroll-id",
        str(row.get("short_id") or row.get("scroll_id") or ""),
        "--division",
        str(row.get("division") or ""),
        "--marker-out",
        str(tracing_marker),
    ]
    local_uri = row.get("local_uri")
    if local_uri:
        cmd.extend(["--volume-zarr", str(local_uri)])

    subprocess.run(cmd, check=False)
    if tracing_marker.exists():
        try:
            return json.loads(tracing_marker.read_text())
        except json.JSONDecodeError:
            return None
    return None


def build_evidence_chain(
    ranked_path,
    out_dir,
    candidate_index=0,
    execute=False,
    python_executable=sys.executable,
    checkpoint="best_model.pt",
    neural_tracing=False,
):
    out_dir = Path(out_dir)
    prediction_dir = out_dir / "predictions"
    prediction_dir.mkdir(parents=True, exist_ok=True)

    row = select_candidate(ranked_path, candidate_index)
    stem = _artifact_stem(row)
    cmd = build_predict_command(
        row,
        python_executable=python_executable,
        prediction_dir=str(prediction_dir),
        checkpoint=checkpoint,
    )
    image_path = prediction_dir / f"{stem}.png"
    metadata_path = prediction_dir / f"{stem}_meta.json"

    _write_json(out_dir / "candidate.json", row)
    (out_dir / "predict_command.sh").write_text(shlex.join(cmd) + "\n")

    if execute:
        subprocess.run(cmd, check=True)
    elif not metadata_path.exists():
        raise FileNotFoundError(
            f"{metadata_path} does not exist. Re-run with --execute or provide existing prediction artifacts."
        )
    if not image_path.exists():
        raise FileNotFoundError(
            f"{image_path} does not exist; prize evidence requires the static prediction image"
        )

    train_mask_path, predict_mask_path = _write_masks(out_dir, row)
    metadata = patch_prediction_metadata(
        metadata_path, row, train_mask_path, predict_mask_path
    )

    report = validate(metadata_path)
    _write_json(out_dir / "PRIZE_READINESS_REPORT.json", report)

    tracing_plan = None
    if neural_tracing:
        tracing_plan = _attach_neural_tracing_plan(out_dir, row, python_executable)

    _write_json(
        out_dir / "manifest.json",
        {
            "candidate_index": candidate_index,
            "candidate": row,
            "prediction_image": str(image_path),
            "prediction_metadata": str(metadata_path),
            "vc3d_zarr_path": metadata.get("vc3d_zarr_path"),
            "readiness_report": str(out_dir / "PRIZE_READINESS_REPORT.json"),
            "predict_command": cmd,
            "neural_tracing_plan": str(out_dir / "neural_tracing.json")
            if tracing_plan
            else None,
            "neural_tracing_ready": bool(tracing_plan and tracing_plan.get("ready")),
        },
    )
    return report


def preflight_evidence_chain(
    ranked_path, out_dir, candidate_index=0, execute=False, checkpoint="best_model.pt"
):
    out_dir = Path(out_dir)
    prediction_dir = out_dir / "predictions"
    row = select_candidate(ranked_path, candidate_index)
    stem = _artifact_stem(row)
    image_path = prediction_dir / f"{stem}.png"
    metadata_path = prediction_dir / f"{stem}_meta.json"
    local_uri = row.get("local_uri")
    failures = []
    warnings = []

    if not local_uri and execute:
        failures.append(
            "candidate has no local_uri; execute mode cannot run predict.py locally"
        )
    elif local_uri and not Path(local_uri).exists():
        failures.append(f"candidate local_uri does not exist: {local_uri}")

    if execute and not Path(checkpoint).exists():
        failures.append(
            f"{checkpoint} is missing; run training or place a checkpoint before execute mode"
        )

    if not execute:
        if not image_path.exists():
            failures.append(f"existing prediction image is missing: {image_path}")
        if not metadata_path.exists():
            failures.append(f"existing prediction metadata is missing: {metadata_path}")

    patch_size = _as_int(row, "patch_size", 64)
    voxel_um = _as_float(row, "voxel_um", 7.91)
    if patch_size > 64 and patch_size * voxel_um / 1000.0 > 0.5 + 1e-9:
        failures.append(
            f"candidate ML window is not submittable: {patch_size}px at {voxel_um}um"
        )
    elif patch_size * voxel_um / 1000.0 > 0.5:
        warnings.append(
            f"candidate is {patch_size * voxel_um / 1000.0:.4f}mm; accepted only because it is <=64px per prize guidance"
        )

    return {
        "status": "PASS" if not failures else "FAIL",
        "ranked_path": str(ranked_path),
        "out_dir": str(out_dir),
        "candidate_index": candidate_index,
        "candidate": row,
        "execute": execute,
        "checkpoint": checkpoint,
        "expected_prediction_image": str(image_path),
        "expected_prediction_metadata": str(metadata_path),
        "failures": failures,
        "warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ranked", default="reports/scroll23_ranked_candidates.tsv")
    parser.add_argument("--candidate-index", type=int, default=0)
    parser.add_argument("--out-dir", default="submission_evidence/candidate_000")
    parser.add_argument(
        "--execute", action="store_true", help="Run predict.py before validating"
    )
    parser.add_argument("--checkpoint", default="best_model.pt")
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Only check prerequisites and write a preflight report",
    )
    parser.add_argument("--preflight-report", default=None)
    parser.add_argument("--python-executable", default=sys.executable)
    parser.add_argument(
        "--neural-tracing",
        action="store_true",
        help="Attach a neural_tracing trace_service readiness plan to the evidence dir.",
    )
    args = parser.parse_args()

    if args.preflight:
        report = preflight_evidence_chain(
            ranked_path=args.ranked,
            out_dir=args.out_dir,
            candidate_index=args.candidate_index,
            execute=args.execute,
            checkpoint=args.checkpoint,
        )
        if args.preflight_report:
            _write_json(args.preflight_report, report)
        print(json.dumps(report, indent=2))
        raise SystemExit(0 if report["status"] == "PASS" else 1)

    report = build_evidence_chain(
        ranked_path=args.ranked,
        out_dir=args.out_dir,
        candidate_index=args.candidate_index,
        execute=args.execute,
        python_executable=args.python_executable,
        checkpoint=args.checkpoint,
        neural_tracing=args.neural_tracing,
    )
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
