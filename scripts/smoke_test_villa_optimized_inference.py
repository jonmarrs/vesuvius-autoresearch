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
import subprocess
from pathlib import Path

import torch

from scripts.export_for_production import export_checkpoint


REQUIRED_TOP_LEVEL_KEYS = {"model_state_dict", "config", "metadata"}
REQUIRED_METADATA_KEYS = {"version", "framework", "val_bpb"}


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
):
    output_checkpoint = Path(output_checkpoint)
    output_checkpoint.parent.mkdir(parents=True, exist_ok=True)
    export_checkpoint(str(input_checkpoint), str(output_checkpoint))

    exported, failures = validate_exported_checkpoint(output_checkpoint)
    docker_cmd = build_official_docker_command(
        image=docker_image,
        model=model,
        s3_path=s3_path,
        start_layer=start_layer,
        end_layer=end_layer,
        model_type=exported.get("config", {}).get("architecture", "timesformer"),
        tile_size=int(exported.get("config", {}).get("patch_size", 64)),
    )

    command_path = Path(command_path)
    command_path.parent.mkdir(parents=True, exist_ok=True)
    command_path.write_text(shlex.join(docker_cmd) + "\n")

    docker_result = {"executed": False}
    if execute_docker:
        proc = subprocess.run(docker_cmd, text=True, capture_output=True)
        docker_result = {
            "executed": True,
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
        }
        if proc.returncode != 0:
            failures.append(f"official docker command failed with return code {proc.returncode}")

    report = {
        "status": "PASS" if not failures else "FAIL",
        "input_checkpoint": str(input_checkpoint),
        "output_checkpoint": str(output_checkpoint),
        "command_path": str(command_path),
        "official_inference_dir": "villa/ink-detection/optimized_inference",
        "docker_command": docker_cmd,
        "docker_result": docker_result,
        "exported_metadata": exported.get("metadata", {}),
        "exported_config": exported.get("config", {}),
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
    parser.add_argument("--report", default="reports/villa_optimized_inference_smoke.json")
    parser.add_argument("--command-out", default="reports/villa_optimized_inference_docker.sh")
    parser.add_argument("--docker-image", default="ink-detection-optimized-inference")
    parser.add_argument("--model", default="timesformer-scroll5")
    parser.add_argument("--s3-path", default="s3://bucket/path/to/input")
    parser.add_argument("--start-layer", type=int, default=0)
    parser.add_argument("--end-layer", type=int, default=26)
    parser.add_argument("--execute-docker", action="store_true")
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
    )
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
