"""Read/write ownership for evidence preparation and prerequisite reports."""

from pathlib import Path

from scripts.inference.run_ranked_inference import resolve_candidate_paths
from scripts.validate_prize_artifact import artifact_inputs
from vesuvius_autoresearch.core.prediction_artifacts import (
    prediction_paths,
    validate_plan_paths,
)

ROOT = Path(__file__).resolve().parents[1]
MANAGED_FILES = (
    "candidate.json",
    "predict_command.sh",
    "evidence_metadata.json",
    "manifest.json",
    "PRIZE_READINESS_REPORT.json",
    "neural_tracing.json",
    "validation_report.json",
)


def validate_evidence_paths(
    ranked_path,
    out_dir,
    checkpoint,
    row=None,
    command=None,
    execute=False,
    train_mask=None,
    predict_mask=None,
    metadata=None,
    report_path=None,
):
    out = Path(out_dir)
    reads = [
        (ranked_path, "ranked input"),
        (checkpoint, "checkpoint"),
        (ROOT / "autoresearch.lock", "research lock"),
    ]
    for name, value in (("train mask", train_mask), ("predict mask", predict_mask)):
        if value:
            reads.append((value, name))
    if row is not None:
        resolved = resolve_candidate_paths(row, Path.cwd())
        for key in ("local_uri", "source_uri", "train_mask_path", "predict_mask_path"):
            value = resolved.get(key)
            if value and "://" not in value:
                reads.append((value, f"candidate {key}"))
    managed = [(out / name, f"managed evidence {name}") for name in MANAGED_FILES]
    predicted = []
    if command is not None:
        stem = command[command.index("--artifact_stem") + 1]
        predicted = [
            (path, "prediction artifact")
            for path in prediction_paths(out / "predictions", stem)
        ]
        metadata_path = out / "predictions" / f"{stem}_meta.json"
        if metadata is not None:
            # Fresh inference may replace its image/export/sidecar, never supplied masks.
            keys = (
                ("train_mask_path", "predict_mask_path")
                if execute
                else (
                    "output_image_path",
                    "source_image_path",
                    "train_mask_path",
                    "predict_mask_path",
                    "vc3d_zarr_path",
                    "prediction_zarr_path",
                    "fiber_vc3d_zarr_path",
                    "fiber_prediction_zarr_path",
                )
            )
            declared = artifact_inputs(metadata_path, metadata, keys)
            reads.extend(declared[1:] if execute else declared)
        if not execute:
            reads.extend(
                [
                    (metadata_path, "original prediction metadata"),
                    (out / "predictions" / f"{stem}.png", "original discovery image"),
                ]
            )
    if report_path is not None:
        # A prerequisite PASS must never replace final artifact evidence or prediction files.
        reads.extend(managed)
        reads.append((out / "predictions", "prediction directory"))
        writes = [(report_path, "preflight report")]
    else:
        writes = [*managed, *(predicted if execute else [])]
    validate_plan_paths(writes, reads)
