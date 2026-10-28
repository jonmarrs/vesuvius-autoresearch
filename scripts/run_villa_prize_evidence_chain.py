#!/usr/bin/env python3
"""
Build a villa-compatible prize evidence directory for one ranked candidate.

The chain is intentionally conservative: it can run predict.py, but it will not
mark placeholders as ready. The output directory contains the command manifest,
candidate row, separate evidence metadata referencing supplied overlap masks, and a
PRIZE_READINESS_REPORT.json from scripts.validate_prize_artifact.
"""

import argparse
import json
import math
import shlex
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.candidate_artifacts import write_json
from scripts.evidence_paths import validate_evidence_paths
from scripts.inference.run_ranked_inference import (
    build_predict_command,
    load_candidates,
    read_candidate_table,
    resolve_candidate_paths,
)
from scripts.validate_prize_artifact import _load_json, resolve_artifact_path, validate


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


def select_candidate(
    ranked_path, index=0, *, expected_sha256=None, input_base_dir=None
):
    _, rows = read_candidate_table(ranked_path, expected_sha256)
    if not rows:
        raise ValueError(f"no candidates found in {ranked_path}")
    if index < 0 or index >= len(rows):
        raise IndexError(f"candidate index {index} outside 0..{len(rows) - 1}")
    return (
        resolve_candidate_paths(rows[index], input_base_dir)
        if input_base_dir is not None
        else rows[index]
    )


def _write_json(path, data):
    write_json(path, data)


def patch_prediction_metadata(
    metadata_path, row, train_mask_path=None, predict_mask_path=None, *, captured=None
):
    """Enrich a copy; never replace prediction geometry or clear evidence flags."""
    metadata_path = Path(metadata_path)
    metadata = dict(_load_json(metadata_path) if captured is None else captured)
    metadata["candidate"] = dict(row)
    if metadata.get("scroll_id") in (None, "", "unknown"):
        metadata["scroll_id"] = row.get("scroll_id")
    for key in (
        "output_image_path",
        "source_image_path",
        "train_mask_path",
        "predict_mask_path",
        "vc3d_zarr_path",
        "prediction_zarr_path",
        "fiber_vc3d_zarr_path",
        "fiber_prediction_zarr_path",
    ):
        if metadata.get(key):
            metadata[key] = str(resolve_artifact_path(metadata[key], metadata_path))
    if train_mask_path:
        metadata["train_mask_path"] = str(Path(train_mask_path).resolve())
    if predict_mask_path:
        metadata["predict_mask_path"] = str(Path(predict_mask_path).resolve())
    return metadata


def _attach_neural_tracing_plan(out_dir, row, python_executable):
    """Optionally produce a neural_tracing trace_service plan for this candidate.

    Calls scripts/inference/launch_neural_tracing.py to resolve the candidate's OME-zarr
    volume + checkpoint, then copies the resulting marker into the candidate
    evidence directory so reviewers can see whether trace_service is launchable
    for this submission window. Tracing itself is not executed; this only adds
    the readiness marker, matching the chain's conservative "no placeholders"
    posture.
    """
    out_dir = Path(out_dir)
    tracing_marker = out_dir / "neural_tracing.json"
    launcher = REPO_ROOT / "scripts" / "inference" / "launch_neural_tracing.py"
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

    # The chain removed any earlier marker before this run; one written by a
    # launcher that then failed is not a plan either.
    if subprocess.run(cmd, check=False).returncode != 0:
        tracing_marker.unlink(missing_ok=True)
        return None
    if tracing_marker.exists():
        try:
            return json.loads(tracing_marker.read_text())
        except json.JSONDecodeError:
            return None
    return None


def _invalidate_evidence(out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # No processing starts unless the FAIL marker has been published.
    _write_json(
        out_dir / "PRIZE_READINESS_REPORT.json",
        {
            "status": "FAIL",
            "failures": ["evidence chain has not completed"],
            "warnings": [],
        },
    )
    for stale in (
        "evidence_metadata.json",
        "manifest.json",
        "neural_tracing.json",
        "validation_report.json",
    ):
        (out_dir / stale).unlink(missing_ok=True)


def build_evidence_chain(
    ranked_path,
    out_dir,
    candidate_index=0,
    execute=False,
    python_executable=sys.executable,
    checkpoint="best_model.pt",
    neural_tracing=False,
    train_mask=None,
    predict_mask=None,
    ranked_sha256=None,
    input_base_dir=None,
):
    out_dir = Path(out_dir)
    prediction_dir = out_dir / "predictions"
    validate_evidence_paths(
        ranked_path,
        out_dir,
        checkpoint,
        train_mask=train_mask,
        predict_mask=predict_mask,
    )
    try:
        row = select_candidate(
            ranked_path,
            candidate_index,
            expected_sha256=ranked_sha256,
            input_base_dir=input_base_dir,
        )
        cmd = build_predict_command(
            row,
            python_executable=python_executable,
            prediction_dir=str(prediction_dir),
            checkpoint=checkpoint,
        )
    except (OSError, ValueError, IndexError):
        # Preserve the previous directory on a rejected pinned plan. Legacy
        # attempts still invalidate stale readiness after safe path preflight.
        if ranked_sha256 is None:
            _invalidate_evidence(out_dir)
        raise
    stem = cmd[cmd.index("--artifact_stem") + 1]
    image_path = prediction_dir / f"{stem}.png"
    metadata_path = prediction_dir / f"{stem}_meta.json"
    captured, metadata_error = None, None
    if metadata_path.is_file():
        try:
            captured = _load_json(metadata_path)
        except (OSError, ValueError, TypeError) as exc:
            metadata_error = exc
    validate_evidence_paths(
        ranked_path,
        out_dir,
        checkpoint,
        row,
        cmd,
        execute,
        train_mask,
        predict_mask,
        captured,
    )
    _invalidate_evidence(out_dir)
    prediction_dir.mkdir(parents=True, exist_ok=True)
    if not execute and metadata_error is not None:
        raise metadata_error

    _write_json(out_dir / "candidate.json", row)
    (out_dir / "predict_command.sh").write_text(shlex.join(cmd) + "\n")

    if execute:
        before = {
            path: path.stat() if path.exists() else None
            for path in (image_path, metadata_path)
        }
        subprocess.run(cmd, check=True)
        for path, previous in before.items():
            if previous is not None and path.exists() and path.stat() == previous:
                raise RuntimeError(f"prediction did not refresh its artifact: {path}")
    if not metadata_path.exists():
        raise FileNotFoundError(
            f"{metadata_path} does not exist. Re-run with --execute or provide existing prediction artifacts."
        )
    if not image_path.exists():
        raise FileNotFoundError(
            f"{image_path} does not exist; prize evidence requires the static prediction image"
        )

    if execute:
        captured = _load_json(metadata_path)
        validate_evidence_paths(
            ranked_path,
            out_dir,
            checkpoint,
            row,
            cmd,
            execute,
            train_mask,
            predict_mask,
            captured,
        )
    metadata = patch_prediction_metadata(
        metadata_path, row, train_mask, predict_mask, captured=captured
    )
    metadata["ranked_sha256"] = ranked_sha256
    metadata["candidate_input_base_dir"] = str(
        Path(input_base_dir or Path.cwd()).resolve()
    )
    metadata["candidate"]["output_image_path"] = str(image_path.resolve())
    evidence_metadata_path = out_dir / "evidence_metadata.json"
    _write_json(evidence_metadata_path, metadata)
    report = validate(evidence_metadata_path)
    _write_json(out_dir / "PRIZE_READINESS_REPORT.json", report)

    tracing_plan = None
    if neural_tracing:
        tracing_plan = _attach_neural_tracing_plan(out_dir, row, python_executable)

    _write_json(
        out_dir / "manifest.json",
        {
            "candidate_index": candidate_index,
            "ranked_sha256": ranked_sha256,
            "candidate_input_base_dir": str(
                Path(input_base_dir or Path.cwd()).resolve()
            ),
            "candidate": row,
            "prediction_image": str(image_path),
            "prediction_metadata": str(metadata_path),
            "evidence_metadata": str(evidence_metadata_path),
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
    ranked_path,
    out_dir,
    candidate_index=0,
    execute=False,
    checkpoint="best_model.pt",
    ranked_sha256=None,
    input_base_dir=None,
    train_mask=None,
    predict_mask=None,
    preflight_report=None,
):
    out_dir = Path(out_dir)
    prediction_dir = out_dir / "predictions"
    checks, failures, warnings, actions = {}, [], [], []

    def add(name, passed, message, action=None):
        checks[name] = {
            "status": "NOT_CHECKED" if passed is None else "PASS" if passed else "FAIL",
            "message": message,
        }
        if passed is False:
            failures.append(message)
            if action and action not in actions:
                actions.append(action)

    def readable_file(path):
        try:
            path = Path(path)
            if not path.is_file() or path.stat().st_size == 0:
                return False
            with path.open("rb"):
                return True
        except (OSError, TypeError, ValueError):
            return False

    row, command, image_path, metadata_path, metadata = {}, None, None, None, None
    try:
        row = select_candidate(
            ranked_path,
            candidate_index,
            expected_sha256=ranked_sha256,
            input_base_dir=input_base_dir,
        )
        command = build_predict_command(
            row, prediction_dir=str(prediction_dir), checkpoint=checkpoint
        )
        stem = command[command.index("--artifact_stem") + 1]
        image_path, metadata_path = (
            prediction_dir / f"{stem}.png",
            prediction_dir / f"{stem}_meta.json",
        )
        add(
            "candidate_geometry",
            True,
            "Candidate geometry passes the prediction command's checks.",
        )
    except (OSError, ValueError, TypeError, IndexError) as exc:
        add(
            "candidate_geometry",
            False,
            str(exc),
            "Correct the ranked table or candidate index and regenerate the plan.",
        )

    local_uri = row.get("local_uri")
    if local_uri:
        exists = Path(local_uri).exists()
        add(
            "local_volume",
            exists,
            f"Candidate local_uri {'exists' if exists else 'does not exist'}: {local_uri}",
            "Provide the candidate's local CT path.",
        )
    elif execute:
        add(
            "local_volume",
            False,
            "candidate has no local_uri; execute mode cannot run predict.py locally",
            "Provide a local_uri before executing inference.",
        )
    else:
        add(
            "local_volume",
            None,
            "No local_uri supplied; existing artifacts will need validation.",
        )

    if execute:
        readable = readable_file(checkpoint)
        add(
            "checkpoint_file",
            readable,
            f"{checkpoint} is missing or is not a nonempty readable regular file"
            if not readable
            else "Checkpoint file is readable; weights and compatibility are not checked.",
            "Provide a nonempty readable checkpoint file.",
        )
    else:
        add(
            "checkpoint_file",
            None,
            "Existing-artifact mode does not load a checkpoint.",
        )

    if metadata_path is not None and metadata_path.is_file():
        try:
            metadata = _load_json(metadata_path)
        except (OSError, ValueError, TypeError) as exc:
            if not execute:
                add(
                    "prediction_metadata",
                    False,
                    f"Existing prediction metadata is invalid: {exc}",
                    "Regenerate or repair the original prediction metadata.",
                )
    if not execute:
        if image_path is not None:
            readable = readable_file(image_path)
            add(
                "prediction_image",
                readable,
                f"Existing prediction image {'is present' if readable else 'is missing or empty'}: {image_path}",
                "Generate or supply the original prediction image.",
            )
        if "prediction_metadata" not in checks and metadata_path is not None:
            add(
                "prediction_metadata",
                metadata is not None,
                f"Existing prediction metadata {'parses' if metadata is not None else 'is missing'}: {metadata_path}",
                "Generate or supply the original prediction metadata.",
            )

    for key, explicit in (("train_mask", train_mask), ("predict_mask", predict_mask)):
        # Fresh predictions replace old metadata and do not inherit its masks.
        declared = (metadata or {}).get(key + "_path") if not execute else None
        path = explicit or (
            resolve_artifact_path(declared, metadata_path)
            if isinstance(declared, str) and declared and metadata_path
            else None
        )
        if path is None:
            add(
                key,
                None,
                "No mask supplied; content, alignment and overlap remain unverified.",
            )
        else:
            readable = readable_file(path)
            add(
                key,
                readable,
                f"{key} {'is readable' if readable else 'is missing or empty'}: {path}",
                f"Provide a readable {key} file in the intended coordinate frame.",
            )

    if command is not None:
        patch_size, voxel_um = (
            int(command[command.index("--patch_size") + 1]),
            float(row.get("voxel_um") or 7.91),
        )
        window_mm = patch_size * voxel_um / 1000.0
        fits = math.isfinite(window_mm) and (
            patch_size <= 64 or window_mm <= 0.5 + 1e-9
        )
        add(
            "local_window_contract",
            fits,
            f"Candidate window: {patch_size}px at {voxel_um:g}um; this checks the local artifact contract, not prize eligibility.",
            "Use a window supported by the local artifact contract.",
        )
        if fits and window_mm > 0.5:
            warnings.append(
                f"Candidate window is {window_mm:.4f}mm; the local contract accepts its <=64px size. Prize eligibility remains unassessed."
            )
    try:
        validate_evidence_paths(
            ranked_path,
            out_dir,
            checkpoint,
            row,
            command,
            execute,
            train_mask,
            predict_mask,
            metadata,
        )
        add(
            "output_paths",
            True,
            "Planned evidence outputs are separate from declared inputs.",
        )
    except (OSError, ValueError) as exc:
        add(
            "output_paths",
            False,
            str(exc),
            "Choose evidence output paths separate from inputs.",
        )
    if preflight_report is not None:
        validate_evidence_paths(
            ranked_path,
            out_dir,
            checkpoint,
            row,
            command,
            execute,
            train_mask,
            predict_mask,
            metadata,
            report_path=preflight_report,
        )

    add(
        "checkpoint_compatibility",
        None,
        "Weights, architecture and warm-start compatibility are not inspected.",
    )
    add(
        "volume_contents",
        None,
        "Volume contents and coordinate bounds are not inspected.",
    )
    add(
        "artifact_validation",
        None,
        "Image content, masks, exports and submission evidence need artifact validation.",
    )
    if not failures:
        actions.append(
            "Run inference, then validate its artifacts with actual overlap masks."
            if execute
            else "Validate the existing artifacts and actual overlap masks before using their evidence."
        )

    return {
        "status": "PASS" if not failures else "FAIL",
        "scope": "inference prerequisites; submission evidence is validated after prediction",
        "mode": "preflight",
        "prize_eligibility": "not_assessed",
        "checks": checks,
        "next_actions": actions,
        "ranked_path": str(ranked_path),
        "ranked_sha256": ranked_sha256,
        "candidate_input_base_dir": str(Path(input_base_dir or Path.cwd()).resolve()),
        "out_dir": str(out_dir),
        "candidate_index": candidate_index,
        "candidate": row,
        "execute": execute,
        "checkpoint": str(checkpoint),
        "expected_prediction_image": str(image_path)
        if image_path is not None
        else None,
        "expected_prediction_metadata": str(metadata_path)
        if metadata_path is not None
        else None,
        "failures": failures,
        "warnings": warnings,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--ranked", default="reports/scroll23_ranked_candidates.tsv")
    parser.add_argument(
        "--ranked-sha256",
        help="Require the exact ranked table captured by a generated worklist",
    )
    parser.add_argument(
        "--input-base-dir",
        type=Path,
        help="Base directory for relative candidate volume and mask paths",
    )
    parser.add_argument("--candidate-index", type=int, default=0)
    parser.add_argument("--out-dir", default="submission_evidence/candidate_000")
    parser.add_argument(
        "--execute", action="store_true", help="Run predict.py before validating"
    )
    parser.add_argument("--checkpoint", default="best_model.pt")
    parser.add_argument(
        "--train-mask",
        help="Actual training-region mask; defaults to prediction metadata",
    )
    parser.add_argument(
        "--predict-mask",
        help="Actual prediction-region mask in the same coordinate frame",
    )
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
    args = parser.parse_args(argv)
    if args.preflight_report and not args.preflight:
        parser.error("--preflight-report requires --preflight")

    if args.preflight:
        report = preflight_evidence_chain(
            ranked_path=args.ranked,
            out_dir=args.out_dir,
            candidate_index=args.candidate_index,
            execute=args.execute,
            checkpoint=args.checkpoint,
            ranked_sha256=args.ranked_sha256,
            input_base_dir=args.input_base_dir,
            train_mask=args.train_mask,
            predict_mask=args.predict_mask,
            preflight_report=args.preflight_report,
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
        train_mask=args.train_mask,
        predict_mask=args.predict_mask,
        ranked_sha256=args.ranked_sha256,
        input_base_dir=args.input_base_dir,
    )
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    try:
        main()
    except (
        OSError,
        ValueError,
        IndexError,
        RuntimeError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"Evidence preparation failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
