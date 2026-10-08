#!/usr/bin/env python3
"""Inspect or explicitly launch the pinned Mutex trainer after data/runtime checks.

Dry-run is the default. Prepared artifacts establish pairing and target schema;
actual loader compatibility is probed on CPU before --execute starts training.
Patch dimensions alone do not establish submission eligibility.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.candidate_artifacts import (
    ARTIFACT_ERRORS,
    integer,
    separate_paths,
    write_json,
)
from scripts.training.mutex_data import (
    fragment_name,
    graph_tools,
    validate_prepared_data,
)

VILLA_SRC = PROJECT_ROOT / "villa/vesuvius/src"
VILLA_TRAINING_CLI = VILLA_SRC / "vesuvius/models/training/cli.py"
RUNTIME_PROBE = PROJECT_ROOT / "scripts/training/probe_mutex_runtime.py"


def _has_prepared_data(data_path: Path) -> bool:
    try:
        validate_prepared_data(data_path)
    except (*ARTIFACT_ERRORS, RuntimeError, ImportError):
        return False
    return True


def build_config(model_name: str, data_path: Path, patch: int, max_epoch: int) -> dict:
    attractive, repulsive, _ = graph_tools().build_offset_sets()
    return {
        "tr_setup": {
            "model_name": model_name,
            "ckpt_out_base": "./checkpoints/instance_seg/",
            "tr_val_split": 0.9,
        },
        "model_config": {"patch_embed_size": [8, 8, 8]},
        "tr_config": {
            "trainer": "mutex_affinity",
            "initial_lr": 1.0e-4,
            "weight_decay": 0.01,
            "batch_size": 4,
            "patch_size": [patch] * 3,
            "max_epoch": max_epoch,
            "num_dataloader_workers": 0,
            "affinity_label_smoothing": 0.05,
        },
        "dataset_config": {
            "data_format": "zarr",
            "data_path": str(data_path),
            "image_dirname": "images",
            "affinity_dirname": "affinity_graph",
            "num_workers": 0,
            "targets": {
                "attractive": {"out_channels": len(attractive)},
                "repulsive": {"out_channels": len(repulsive)},
            },
            "affinity_targets": {
                "attractive": {
                    "affinity_key": "affinities/attractive",
                    "mask_key": "mask/attractive",
                    "invert": True,
                },
                "repulsive": {
                    "affinity_key": "affinities/repulsive",
                    "mask_key": "mask/repulsive",
                    "invert": False,
                },
            },
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--data-path", default=str(PROJECT_ROOT / "local_data/curated_fragments")
    )
    parser.add_argument("--model-name", default="mutex_affinity_v1")
    parser.add_argument(
        "--patch",
        type=int,
        default=64,
        help="Positive cubic training patch size in voxels",
    )
    parser.add_argument("--max-epoch", type=int, default=20)
    parser.add_argument(
        "--config-out",
        help="Config JSON (also valid YAML); defaults to a unique local run folder",
    )
    parser.add_argument(
        "--marker-out",
        help="Run status JSON; defaults to the same unique local run folder",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Probe the pinned runtime on CPU, then explicitly start training",
    )
    args = parser.parse_args(argv)
    marker: dict | None = None
    marker_path: Path | None = None
    try:
        patch, epochs = (
            integer(args.patch, "patch", 1),
            integer(args.max_epoch, "max_epoch", 1),
        )
        model_name = fragment_name(args.model_name)
        data_path = Path(args.data_path).resolve()
        run_dir = PROJECT_ROOT / "local_data/mutex_launch" / uuid.uuid4().hex
        config_path = (
            Path(args.config_out).resolve()
            if args.config_out
            else run_dir / "config.json"
        )
        marker_path = (
            Path(args.marker_out).resolve() if args.marker_out else run_dir / "run.json"
        )
        separate_paths(data_path, config_path)
        separate_paths(data_path, marker_path)
        separate_paths(config_path, marker_path)
        marker = {
            "model_name": model_name,
            "data_path": str(data_path),
            "config_path": str(config_path),
            "patch_size": [patch] * 3,
            "submittable": None,
            "window_px_within_limit": patch <= 64,
            "data_prepared": False,
            "execute_requested": args.execute,
            "executed": False,
            "runtime_verified": False,
            "state": "preflight",
            "success": None,
        }
        write_json(marker_path, marker)
        if not VILLA_TRAINING_CLI.is_file():
            raise FileNotFoundError(
                f"pinned training CLI missing: {VILLA_TRAINING_CLI}"
            )
        try:
            details = validate_prepared_data(data_path, patch)
            marker["data_prepared"] = True
            marker["data_contract"] = details["completion"]
        except (*ARTIFACT_ERRORS, RuntimeError, ImportError) as exc:
            marker["data_error"] = str(exc)
        cfg = build_config(model_name, data_path, patch, epochs)
        write_json(config_path, cfg)
        cmd = [
            sys.executable,
            str(VILLA_TRAINING_CLI),
            "--config",
            str(config_path),
            "--trainer",
            "mutex_affinity",
            "--max-epoch",
            str(epochs),
        ]
        marker["command"] = cmd
        marker["state"] = "dry_run"
        write_json(marker_path, marker)
        print(f"Mutex config: {config_path}")
        print(f"Artifact validated: {marker['data_prepared']}; runtime verified: False")
        print(f"Run status: {marker_path}")
        if not args.execute:
            if not marker["data_prepared"]:
                print(
                    f"Data check: {marker['data_error']}. Prepare with scripts/training/prepare_mutex_training.py and explicit raw/label pairing."
                )
            print(
                "Dry run. Use --execute to probe runtime compatibility and start training."
            )
            return 0
        if not marker["data_prepared"]:
            marker.update(state="refused", success=False)
            write_json(marker_path, marker)
            print(f"Refusing --execute: {marker['data_error']}", file=sys.stderr)
            return 2
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            filter(None, (str(VILLA_SRC), str(PROJECT_ROOT), env.get("PYTHONPATH")))
        )
        marker["state"] = "runtime_probe"
        write_json(marker_path, marker)
        probe = subprocess.run(
            [sys.executable, str(RUNTIME_PROBE), "--config", str(config_path)],
            env=env,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        marker["runtime_probe"] = {
            "returncode": probe.returncode,
            "stdout": probe.stdout[-4000:],
            "stderr": probe.stderr[-4000:],
        }
        if probe.returncode != 0:
            marker.update(state="runtime_failed", success=False)
            write_json(marker_path, marker)
            print(
                f"Refusing --execute: CPU data-loader probe failed. {probe.stdout.strip()} {probe.stderr.strip()}",
                file=sys.stderr,
            )
            return 2
        result = json.loads(probe.stdout)
        if (
            not isinstance(result, dict)
            or result.get("contract") != 1
            or result.get("status") != "PASS"
        ):
            raise ValueError("CPU runtime probe did not report verified compatibility")
        marker.update(runtime_verified=True, state="launching")
        write_json(marker_path, marker)
        # Keep execution false if the OS refuses to start the process.
        training = subprocess.Popen(cmd, env=env, cwd=PROJECT_ROOT)
        try:
            marker.update(executed=True, state="running", pid=training.pid)
            write_json(marker_path, marker)
            returncode = training.wait()
        except BaseException:
            training.terminate()
            training.wait()
            raise
        marker.update(
            executed=True,
            state="completed" if returncode == 0 else "training_failed",
            success=returncode == 0,
            returncode=returncode,
        )
        write_json(marker_path, marker)
        return returncode if returncode >= 0 else 128 - returncode
    except (*ARTIFACT_ERRORS, RuntimeError, ImportError) as exc:
        if marker is not None and marker_path is not None:
            marker.update(state="failed", success=False, error=str(exc))
            write_json(marker_path, marker)
        print(f"Mutex launch failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
