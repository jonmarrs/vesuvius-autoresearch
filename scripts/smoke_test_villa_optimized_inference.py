#!/usr/bin/env python3
"""Validate a checkpoint envelope and record the limits of its inference handoff.

PASS covers envelope/local weight checks only. Registry Docker templates do not
load the exported file; execution through this command is refused. Legacy Primus
packages are archives without a runnable native inference command.
"""

import argparse
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.export_for_production import (
    CHECKPOINT_ERRORS,
    checkpoint_contract,
    export_checkpoint,
    sha256_file,
    validate_envelope,
)
from scripts.labeling.label_artifacts import new_output, publish_new, publish_new_file
from vesuvius_autoresearch.core.inference import positive_integer

DOCKER_SUPPORTED_ARCHITECTURES = {
    "timesformer",
    "resnet3d-50",
    "resnet3d-152",
    "resnet3d-152-3d-decoder",
}
DOCKER_REFUSAL = (
    "Docker execution refused: MODEL selects a registry model; the command does "
    "not load the exported checkpoint and cannot verify its inference handoff"
)
PRIMUS_BLOCKER = (
    "This legacy envelope has model_state_dict/config, while the pinned train_py "
    "loader reads model/model_config (and optional EMA/normalization). A native "
    "checkpoint and actual compatible model load are required; no conversion or "
    "inference verification was performed."
)


def build_official_docker_command(
    image,
    model,
    s3_path,
    start_layer,
    end_layer,
    model_type="timesformer",
    tile_size=64,
    stride=16,
):
    """Registry-model command template, independent of any local checkpoint."""
    if model_type not in DOCKER_SUPPORTED_ARCHITECTURES:
        raise ValueError(
            f"villa optimized_inference does not support MODEL_TYPE={model_type!r}"
        )
    positive_integer(start_layer, "start_layer", minimum=0)
    positive_integer(end_layer, "end_layer")
    positive_integer(tile_size, "tile_size")
    positive_integer(stride, "stride")
    if end_layer <= start_layer or stride > tile_size:
        raise ValueError("require start_layer < end_layer and stride <= tile_size")
    if not all(
        isinstance(value, str) and value.strip() for value in (image, model, s3_path)
    ):
        raise ValueError("image, registry model, and s3_path must be nonempty strings")
    if (
        not s3_path.startswith("s3://")
        or len(s3_path[5:].split("/", 1)) != 2
        or not all(s3_path[5:].split("/", 1))
    ):
        raise ValueError("s3_path must identify a bucket and segment prefix")
    return [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "-e",
        f"MODEL={model}",
        "-e",
        f"S3_PATH={s3_path}",
        "-e",
        f"START_LAYER={start_layer}",
        "-e",
        f"END_LAYER={end_layer}",
        "-e",
        f"MODEL_TYPE={model_type}",
        "-e",
        f"TILE_SIZE={tile_size}",
        "-e",
        f"STRIDE={stride}",
        image,
    ]


def build_primus_submission_package(
    checkpoint_path, package_dir, exported_metadata, exported_config
):
    """Legacy API name: publish an immutable Primus archive, not a submission."""
    source = Path(checkpoint_path).resolve()
    destination = new_output(package_dir, source)
    digest = sha256_file(source)
    loaded = torch.load(source, map_location="cpu", weights_only=False)
    _, config, _, _ = checkpoint_contract(loaded)
    if config["architecture"] != "primus_lejepa":
        raise ValueError("Primus archive requires primus_lejepa weights")
    metadata = loaded.get("metadata", {})
    if config != exported_config or metadata != exported_metadata:
        raise ValueError("archive declarations must match the actual checkpoint")
    json.dumps(metadata, allow_nan=False)
    manifest = {
        "scope": "checkpoint archive only",
        "package_dir": str(destination),
        "checkpoint": str(destination / "model.pt"),
        "predict_manifest": str(destination / "predict_manifest.json"),
        "readme": str(destination / "README.md"),
        "reproducibility": str(destination / "REPRODUCIBILITY.md"),
        "architecture": config["architecture"],
        "patch_size": config["patch_size"],
        "checkpoint_sha256": digest,
        "pretrained_lejepa_sha": config.get("pretrained_lejepa_sha"),
        "finetune_config_sha": config.get("finetune_config_sha"),
        "inference_verified": False,
        "submittable": None,
        "blockers": [PRIMUS_BLOCKER],
    }
    with publish_new(destination) as staging:
        shutil.copy2(source, staging / "model.pt")
        if sha256_file(staging / "model.pt") != digest or sha256_file(source) != digest:
            raise ValueError("checkpoint changed while building its archive")
        predict = {
            "command": None,
            "inference_verified": False,
            "blockers": [PRIMUS_BLOCKER],
        }
        for name, payload in (
            ("predict_manifest.json", predict),
            ("submission_manifest.json", manifest),
        ):
            (staging / name).write_text(
                json.dumps(payload, indent=2, allow_nan=False) + "\n"
            )
        (staging / "README.md").write_text(
            "# Primus checkpoint archive\n\n" + PRIMUS_BLOCKER + "\n\n"
            "This archive records a legacy research envelope. Inference compatibility "
            "and submission eligibility remain unverified.\n"
        )
        (staging / "REPRODUCIBILITY.md").write_text(
            "# Recorded checkpoint provenance\n\n"
            f"Checkpoint SHA-256: `{digest}`\n\n"
            "Config is copied from this checkpoint; no run marker or external "
            "pretrain/config file was read. Recorded lineage is unverified.\n"
        )
    return manifest


def validate_exported_checkpoint(path):
    try:
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
        validate_envelope(checkpoint)
        return checkpoint, []
    except CHECKPOINT_ERRORS as exc:
        return {}, [str(exc)]


def run_smoke_test(
    input_checkpoint,
    output_checkpoint,
    report_path,
    command_path,
    model,
    s3_path,
    start_layer,
    end_layer,
    docker_image,
    execute_docker=False,
    submission_package_dir=None,
):
    source = Path(input_checkpoint).resolve()
    outputs = [Path(output_checkpoint), Path(report_path), Path(command_path)]
    if submission_package_dir is not None:
        outputs.append(Path(submission_package_dir))
    # Preflight every destination before any export, report, or archive write.
    resolved = [
        new_output(path, source, *outputs[:index], *outputs[index + 1 :])
        for index, path in enumerate(outputs)
    ]
    output, report_output, command_output = resolved[:3]
    package_output = resolved[3] if len(resolved) > 3 else None
    report = {
        "scope": "checkpoint envelope validation only",
        "status": "FAIL",
        "input_checkpoint": str(source),
        "output_checkpoint": str(output),
        "command_path": str(command_output),
        "official_inference_dir": str(
            REPO_ROOT / "villa/ink-detection/optimized_inference"
        ),
        "architecture": None,
        "docker_command": None,
        "docker_command_scope": "registry model only; does not load the exported checkpoint",
        "docker_result": {"executed": False},
        "submission_package": None,
        "inference_verified": False,
        "submittable": None,
        "exported_metadata": {},
        "exported_config": {},
        "failures": [],
    }
    try:
        if execute_docker:
            raise ValueError(DOCKER_REFUSAL)
        exported = export_checkpoint(source, output)
        # Read the published envelope through the same shared validator.
        exported, failures = validate_exported_checkpoint(output)
        if failures:
            raise ValueError("; ".join(failures))
        config, metadata = exported["config"], exported["metadata"]
        arch = config["architecture"]
        report.update(
            architecture=arch, exported_metadata=metadata, exported_config=config
        )
        if package_output is not None and arch != "primus_lejepa":
            raise ValueError(
                "--submission-package-dir is only supported for legacy Primus archives"
            )
        command_text = "# No verified inference command for this exported checkpoint.\n"
        if arch == "primus_lejepa":
            if package_output is not None:
                report["submission_package"] = build_primus_submission_package(
                    output, package_output, metadata, config
                )
            report["handoff_blockers"] = [PRIMUS_BLOCKER]
        else:
            model_type = (
                "resnet3d-152-3d-decoder" if arch == "resnet3d_decoder" else arch
            )
            if model_type in DOCKER_SUPPORTED_ARCHITECTURES:
                docker_cmd = build_official_docker_command(
                    docker_image,
                    model,
                    s3_path,
                    start_layer,
                    end_layer,
                    model_type=model_type,
                    tile_size=config["patch_size"],
                    stride=min(16, config["patch_size"]),
                )
                report["docker_command"] = docker_cmd
                command_text += (
                    "# Registry-model template; it does not load this exported checkpoint.\n"
                    + shlex.join(docker_cmd)
                    + "\n"
                )
            report["handoff_blockers"] = [
                "The exported checkpoint has not been loaded by an upstream inference consumer."
            ]
        with publish_new_file(command_output, source, output) as staging:
            staging.write_text(command_text)
        report["status"] = "PASS"
    except CHECKPOINT_ERRORS as exc:
        report["failures"].append(str(exc))
    with publish_new_file(report_output, source, output, command_output) as staging:
        staging.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="best_model.pt")
    parser.add_argument("--output", required=True, help="New checkpoint envelope")
    parser.add_argument(
        "--report", required=True, help="New envelope-validation report"
    )
    parser.add_argument(
        "--command-out", required=True, help="New command-template file"
    )
    parser.add_argument("--docker-image", default="ink-detection-optimized-inference")
    parser.add_argument("--model", default="timesformer-scroll5")
    parser.add_argument("--s3-path", default="s3://bucket/path/to/input")
    parser.add_argument("--start-layer", type=int, default=0)
    parser.add_argument("--end-layer", type=int, default=26)
    parser.add_argument(
        "--execute-docker",
        action="store_true",
        help="Refused: registry command does not load the exported file",
    )
    parser.add_argument(
        "--submission-package-dir", help="Optional new legacy Primus archive directory"
    )
    args = parser.parse_args(argv)
    try:
        report = run_smoke_test(
            args.input,
            args.output,
            args.report,
            args.command_out,
            args.model,
            args.s3_path,
            args.start_layer,
            args.end_layer,
            args.docker_image,
            args.execute_docker,
            args.submission_package_dir,
        )
    except CHECKPOINT_ERRORS as exc:
        parser.exit(1, f"Checkpoint handoff preflight failed: {exc}\n")
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
