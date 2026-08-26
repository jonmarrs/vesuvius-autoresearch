#!/usr/bin/env python3
"""Launcher for villa's Mutex-Affinity instance-segmentation trainer.

Trains the MutexAffinityTrainer on a curated_fragments dataset whose
``images/`` and ``affinity_graph/`` subdirs have been prepared by
``scripts/prepare_mutex_training.py``. Patch size is fixed to 64**3 so the
resulting model is submittable under the 0.5x0.5 mm hallucination-mitigation
rule.

This is the Grand-Prize-aligned lane: papyrus sheet instance segmentation,
not ink. Use the dry-run by default to inspect the resolved CLI command, then
re-run with ``--execute`` to actually train.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VILLA_TRAINING_CLI = (
    PROJECT_ROOT
    / "villa"
    / "vesuvius"
    / "src"
    / "vesuvius"
    / "models"
    / "training"
    / "cli.py"
)


def _resolve_data_path(data_path: Path) -> Path:
    images = data_path / "images"
    affinity = data_path / "affinity_graph"
    return data_path if images.is_dir() and affinity.is_dir() else data_path


def _has_prepared_data(data_path: Path) -> bool:
    images = data_path / "images"
    affinity = data_path / "affinity_graph"
    if not (images.is_dir() and affinity.is_dir()):
        return False
    return any(images.iterdir()) and any(affinity.iterdir())


def build_config(model_name: str, data_path: Path, patch: int, max_epoch: int) -> dict:
    return {
        "tr_setup": {
            "model_name": model_name,
            "ckpt_out_base": "./checkpoints/instance_seg/",
            "tr_val_split": 0.9,
        },
        "model_config": {
            "patch_embed_size": [8, 8, 8],
        },
        "tr_config": {
            "trainer": "mutex_affinity",
            "initial_lr": 1.0e-4,
            "weight_decay": 0.01,
            "batch_size": 4,
            "patch_size": [patch, patch, patch],
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
            "affinity_targets": {
                "attractive": {
                    "affinity_key": "affinities/attractive",
                    "mask_key": "mask/attractive",
                    "invert_for_loss": True,
                },
                "repulsive": {
                    "affinity_key": "affinities/repulsive",
                    "mask_key": "mask/repulsive",
                    "invert_for_loss": False,
                },
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch villa's MutexAffinityTrainer for sheet instance segmentation."
    )
    parser.add_argument(
        "--data-path",
        default=str(PROJECT_ROOT / "local_data" / "curated_fragments"),
        help="Directory containing images/ and affinity_graph/ subdirs (output of prepare_mutex_training.py).",
    )
    parser.add_argument("--model-name", default="mutex_affinity_v1")
    parser.add_argument(
        "--patch",
        type=int,
        default=64,
        help="Cubic patch size in px. Keep ≤64 for submittable models.",
    )
    parser.add_argument("--max-epoch", type=int, default=20)
    parser.add_argument(
        "--config-out",
        default=str(PROJECT_ROOT / "configs" / "instance_seg" / "mutex_config.yaml"),
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually run the trainer (otherwise dry-run).",
    )
    args = parser.parse_args()

    if not VILLA_TRAINING_CLI.exists():
        print(
            f"ERROR: villa training CLI not found at {VILLA_TRAINING_CLI}",
            file=sys.stderr,
        )
        return 1

    data_path = _resolve_data_path(Path(args.data_path).resolve())
    if args.patch > 64:
        print(
            f"WARNING: patch={args.patch} > 64. Resulting model is NOT submittable "
            "under the 0.5x0.5 mm hallucination-mitigation rule.",
            file=sys.stderr,
        )

    cfg = build_config(args.model_name, data_path, args.patch, args.max_epoch)
    config_path = Path(args.config_out)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.safe_dump(cfg, f)

    cmd = [
        sys.executable,
        str(VILLA_TRAINING_CLI),
        "--config",
        str(config_path),
        "--trainer",
        "mutex_affinity",
        "--max-epoch",
        str(args.max_epoch),
    ]

    marker_path = PROJECT_ROOT / "reports" / "mutex_affinity_run.json"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker = {
        "model_name": args.model_name,
        "data_path": str(data_path),
        "config_path": str(config_path),
        "patch_size": [args.patch, args.patch, args.patch],
        "submittable": args.patch <= 64,
        "data_prepared": _has_prepared_data(data_path),
        "command": cmd,
        "executed": bool(args.execute),
    }
    with open(marker_path, "w") as f:
        json.dump(marker, f, indent=2)

    print(f"Mutex config written: {config_path}")
    print(f"Data path resolved: {data_path}  (prepared: {marker['data_prepared']})")
    print(f"Marker: {marker_path}")

    if not marker["data_prepared"]:
        print(
            "NOTE: images/ or affinity_graph/ is empty. Populate them first with "
            "`scripts/prepare_mutex_training.py --curated_zarr <path>`. --execute "
            "will be refused until data is prepared.",
            file=sys.stderr,
        )

    if args.execute:
        if not marker["data_prepared"]:
            print(
                "Refusing --execute: mutex training data is not prepared.",
                file=sys.stderr,
            )
            return 2
        env = os.environ.copy()
        return subprocess.call(cmd, cwd=str(PROJECT_ROOT), env=env)

    print("Dry run. Use --execute to start training:")
    print(" ", " ".join(cmd))
    return 0


if __name__ == "__main__":
    sys.exit(main())
