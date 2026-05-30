#!/usr/bin/env python3
"""
Smoke-test the handoff from Autoresearch checkpoints to villa optimized inference.

This does not claim to run the official container unless --execute-docker is set.
By default it verifies the exported checkpoint structure, records the official
docker command template, and writes a machine-readable report for prize evidence.
"""

import argparse
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import torch

from scripts.export_for_production import (
    ARCHITECTURE_STATE_DICT_PREFIXES,
    export_checkpoint,
)

REQUIRED_TOP_LEVEL_KEYS = {"model_state_dict", "config", "metadata"}
REQUIRED_METADATA_KEYS = {"version", "framework", "val_bpb"}

# Architectures that the villa optimized_inference Docker container can load
# today. Anything outside this set must take the submission_package path
# instead of the Docker path.
DOCKER_SUPPORTED_ARCHITECTURES = {"timesformer", "resnet3d_decoder", "resnet3d-50"}


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
    if model_type not in DOCKER_SUPPORTED_ARCHITECTURES and model_type not in {
        "resnet3d-152-3d-decoder",
    }:
        raise ValueError(
            f"villa optimized_inference does not support MODEL_TYPE={model_type!r}. "
            f"Supported: {sorted(DOCKER_SUPPORTED_ARCHITECTURES | {'resnet3d-152-3d-decoder'})}. "
            "Use build_primus_submission_package() for primus_lejepa instead."
        )
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
    """Build a self-contained submission for a primus_lejepa fine-tuned model.

    Villa's optimized_inference Docker container has no Primus loader (see
    villa/ink-detection/optimized_inference/runtime_contracts.py). Until that
    is added (option A), submissions ship the checkpoint + a villa-native
    inference command using `vesuvius.models.run.inference`, which DOES know
    how to load train_py checkpoints via NetworkFromConfig.
    """
    package_dir = Path(package_dir)
    package_dir.mkdir(parents=True, exist_ok=True)

    pkg_checkpoint = package_dir / "model.pt"
    shutil.copy2(str(checkpoint_path), str(pkg_checkpoint))

    villa_infer = "villa/vesuvius/src/vesuvius/models/run/inference.py"
    predict_manifest = {
        "command": [
            sys.executable,
            villa_infer,
            "--model_path",
            str(pkg_checkpoint),
            "--input_dir",
            "<OME_ZARR_PATH>",
            "--output_dir",
            "<OUTPUT_DIR>",
            "--model-type",
            "train_py",
            "--input_format",
            "zarr",
        ],
        "notes": (
            "Replace <OME_ZARR_PATH> with an OME-Zarr scroll volume and "
            "<OUTPUT_DIR> with the predictions directory. Villa's inference "
            "CLI loads train_py checkpoints via NetworkFromConfig."
        ),
        "expected_patch_size": exported_config.get("patch_size"),
        "architecture": exported_config.get("architecture"),
    }
    (package_dir / "predict_manifest.json").write_text(
        json.dumps(predict_manifest, indent=2) + "\n"
    )

    readme_lines = [
        "# Vesuvius Autoresearch — Primus LeJEPA Fine-tune Submission",
        "",
        f"Architecture: `{exported_config.get('architecture')}`",
        f"Patch size: `{exported_config.get('patch_size')}`",
        f"Pretrained LeJEPA SHA: `{exported_metadata.get('pretrained_lejepa_sha')}`",
        f"Fine-tune config SHA: `{exported_metadata.get('finetune_config_sha')}`",
        "",
        "## Why this package and not the villa Docker container",
        "",
        "`villa/ink-detection/optimized_inference/` currently only registers",
        "MODEL_TYPE in {timesformer, resnet3d-50, resnet3d-152-3d-decoder}. A",
        "Primus loader (`model_primus.py`) is not yet upstream. Until it lands,",
        "this submission uses villa's own `vesuvius.models.run.inference` CLI,",
        "which loads train_py checkpoints via NetworkFromConfig.",
        "",
        "## How to run",
        "",
        "See `predict_manifest.json` for the exact command. Fill in",
        "`<OME_ZARR_PATH>` and `<OUTPUT_DIR>` to match the candidate window",
        "from the Scroll 2/3 worklist.",
    ]
    (package_dir / "README.md").write_text("\n".join(readme_lines) + "\n")

    repro_lines = [
        "# Reproducibility manifest",
        "",
        "Reproduce this submission by:",
        "",
        "1. Pretraining: see `scripts/launch_lejepa.py` and the LeJEPA pretrain checkpoint at the",
        f"   SHA below (`{exported_metadata.get('pretrained_lejepa_sha')}`).",
        "2. Fine-tuning: `scripts/launch_finetune_lejepa.py --execute` using the config at the SHA below",
        f"   (`{exported_metadata.get('finetune_config_sha')}`).",
        "3. Export: `scripts/export_for_production.py --input <best.pt> --output model.pt`.",
        "4. Inference: see `predict_manifest.json`.",
        "",
        "## Pretrain checkpoint",
        f"- path: `{exported_config.get('pretrained_lejepa_checkpoint')}`",
        f"- sha256: `{exported_metadata.get('pretrained_lejepa_sha')}`",
        "",
        "## Fine-tune config",
        f"- path: `{exported_config.get('finetune_config_path')}`",
        f"- sha256: `{exported_metadata.get('finetune_config_sha')}`",
    ]
    (package_dir / "REPRODUCIBILITY.md").write_text("\n".join(repro_lines) + "\n")

    manifest = {
        "package_dir": str(package_dir),
        "checkpoint": str(pkg_checkpoint),
        "predict_manifest": str(package_dir / "predict_manifest.json"),
        "readme": str(package_dir / "README.md"),
        "reproducibility": str(package_dir / "REPRODUCIBILITY.md"),
        "architecture": exported_config.get("architecture"),
        "patch_size": exported_config.get("patch_size"),
        "pretrained_lejepa_sha": exported_metadata.get("pretrained_lejepa_sha"),
        "finetune_config_sha": exported_metadata.get("finetune_config_sha"),
    }
    (package_dir / "submission_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    return manifest


def validate_exported_checkpoint(path):
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    failures = []
    missing_top = sorted(REQUIRED_TOP_LEVEL_KEYS - set(checkpoint.keys()))
    if missing_top:
        failures.append(f"missing top-level keys: {missing_top}")

    metadata = checkpoint.get("metadata", {})
    missing_metadata = sorted(REQUIRED_METADATA_KEYS - set(metadata.keys()))
    if missing_metadata:
        failures.append(f"missing metadata keys: {missing_metadata}")
    if metadata.get("framework") != "vesuvius-autoresearch":
        failures.append("metadata.framework must be vesuvius-autoresearch")

    state_dict = checkpoint.get("model_state_dict")
    if not isinstance(state_dict, dict) or not state_dict:
        failures.append("model_state_dict must be a non-empty dict")
    config = checkpoint.get("config")
    if not isinstance(config, dict):
        failures.append("config must be a dict")

    # Architecture-aware state-dict prefix check. We don't fail if architecture
    # is missing (older checkpoints), but if it's declared we sanity-check.
    if isinstance(state_dict, dict) and state_dict and isinstance(config, dict):
        declared = config.get("architecture")
        if declared in ARCHITECTURE_STATE_DICT_PREFIXES:
            expected_prefix = ARCHITECTURE_STATE_DICT_PREFIXES[declared]
            first_key = next(iter(state_dict.keys()))
            if not first_key.startswith(expected_prefix):
                failures.append(
                    f"state_dict prefix {first_key!r} does not match "
                    f"architecture={declared!r} (expected prefix {expected_prefix!r})"
                )

    if isinstance(metadata, dict) and metadata.get("architecture") == "primus_lejepa":
        if not metadata.get("pretrained_lejepa_sha"):
            failures.append("primus_lejepa metadata is missing pretrained_lejepa_sha")
        if not metadata.get("finetune_config_sha"):
            failures.append("primus_lejepa metadata is missing finetune_config_sha")

    return checkpoint, failures


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
    output_checkpoint = Path(output_checkpoint)
    output_checkpoint.parent.mkdir(parents=True, exist_ok=True)
    export_checkpoint(str(input_checkpoint), str(output_checkpoint))

    exported, failures = validate_exported_checkpoint(output_checkpoint)
    config = exported.get("config", {})
    metadata = exported.get("metadata", {})
    arch = config.get("architecture", "timesformer")
    if arch == "resnet3d_decoder":
        model_type = "resnet3d-152-3d-decoder"
    else:
        model_type = arch

    command_path = Path(command_path)
    command_path.parent.mkdir(parents=True, exist_ok=True)

    docker_cmd = None
    docker_result = {"executed": False}
    submission_manifest = None

    if arch == "primus_lejepa":
        # Villa optimized_inference can't load Primus yet; ship a self-contained
        # submission package that uses villa's models/run/inference CLI instead.
        package_dir = Path(submission_package_dir or "submission_package_primus_lejepa")
        submission_manifest = build_primus_submission_package(
            checkpoint_path=output_checkpoint,
            package_dir=package_dir,
            exported_metadata=metadata,
            exported_config=config,
        )
        command_path.write_text(
            "# primus_lejepa: no Docker command — see submission_package below.\n"
            f"# package: {submission_manifest['package_dir']}\n"
            f"# predict_manifest: {submission_manifest['predict_manifest']}\n"
        )
        if execute_docker:
            failures.append(
                "execute_docker=True is invalid for primus_lejepa (no villa loader)"
            )
    else:
        docker_cmd = build_official_docker_command(
            image=docker_image,
            model=model,
            s3_path=s3_path,
            start_layer=start_layer,
            end_layer=end_layer,
            model_type=model_type,
            tile_size=int(config.get("patch_size", 64)),
        )
        command_path.write_text(shlex.join(docker_cmd) + "\n")
        if execute_docker:
            proc = subprocess.run(docker_cmd, text=True, capture_output=True)
            docker_result = {
                "executed": True,
                "returncode": proc.returncode,
                "stdout_tail": proc.stdout[-4000:],
                "stderr_tail": proc.stderr[-4000:],
            }
            if proc.returncode != 0:
                failures.append(
                    f"official docker command failed with return code {proc.returncode}"
                )

    report = {
        "status": "PASS" if not failures else "FAIL",
        "input_checkpoint": str(input_checkpoint),
        "output_checkpoint": str(output_checkpoint),
        "command_path": str(command_path),
        "official_inference_dir": "villa/ink-detection/optimized_inference",
        "architecture": arch,
        "docker_command": docker_cmd,
        "docker_result": docker_result,
        "submission_package": submission_manifest,
        "exported_metadata": metadata,
        "exported_config": config,
        "failures": failures,
    }

    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="best_model.pt")
    parser.add_argument("--output", default="production_model.pt")
    parser.add_argument(
        "--report", default="reports/villa_optimized_inference_smoke.json"
    )
    parser.add_argument(
        "--command-out", default="reports/villa_optimized_inference_docker.sh"
    )
    parser.add_argument("--docker-image", default="ink-detection-optimized-inference")
    parser.add_argument("--model", default="timesformer-scroll5")
    parser.add_argument("--s3-path", default="s3://bucket/path/to/input")
    parser.add_argument("--start-layer", type=int, default=0)
    parser.add_argument("--end-layer", type=int, default=26)
    parser.add_argument("--execute-docker", action="store_true")
    parser.add_argument(
        "--submission-package-dir",
        default="submission_package_primus_lejepa",
        help="Output dir for the submission_package when architecture is primus_lejepa.",
    )
    args = parser.parse_args()

    report = run_smoke_test(
        input_checkpoint=args.input,
        output_checkpoint=args.output,
        report_path=args.report,
        command_path=args.command_out,
        model=args.model,
        s3_path=args.s3_path,
        start_layer=args.start_layer,
        end_layer=args.end_layer,
        docker_image=args.docker_image,
        execute_docker=args.execute_docker,
        submission_package_dir=args.submission_package_dir,
    )
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
