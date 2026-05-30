#!/usr/bin/env python3
import argparse
import glob
import os
import subprocess
import sys

import yaml


def main():
    """
    Launcher for official LeJEPA pretraining.
    Builds a foundation model from all unlabeled scroll data (Scrolls 1-4).
    """
    parser = argparse.ArgumentParser(
        description="Launch LeJEPA Foundation Model Pretraining."
    )
    parser.add_argument(
        "--execute", action="store_true", help="Actually execute the training command."
    )
    args = parser.parse_args()

    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    VILLA_PATH = os.path.join(PROJECT_ROOT, "villa/vesuvius/src")
    sys.path.append(VILLA_PATH)

    # Target all unlabeled volumes (Scrolls 1-4)
    local_data_dir = os.path.join(PROJECT_ROOT, "local_data")
    search_patterns = [
        os.path.join(local_data_dir, "PHerc0125_Divisions", "div_*", "0"),
        os.path.join(local_data_dir, "PHerc0332_Divisions", "div_*", "0"),
        os.path.join(local_data_dir, "RealScroll_1", "0"),
        os.path.join(local_data_dir, "RealScroll_4_Large", "0"),
    ]

    UNLABELED_VOLUMES = []
    for pattern in search_patterns:
        # Exclude the nested /0/0 directory edge case
        matches = [
            m for m in glob.glob(pattern) if os.path.isdir(m) and not m.endswith("/0/0")
        ]
        UNLABELED_VOLUMES.extend(matches)

    # Sort and deduplicate
    UNLABELED_VOLUMES = sorted(list(set(UNLABELED_VOLUMES)))

    if not UNLABELED_VOLUMES:
        print("Warning: No unlabeled volumes found in local_data.")
        sys.exit(1)

    print(
        f"Found {len(UNLABELED_VOLUMES)} unlabeled volumes for Foundation Pretraining."
    )

    config = {
        "tr_setup": {
            "model_name": "lejepa_foundation_v1",
            "ckpt_out_base": "./checkpoints/self_supervised/",
            "tr_val_split": 0.95,
        },
        "model_config": {"patch_embed_size": [8, 8, 8]},
        "tr_config": {
            "trainer": "lejepa",
            "initial_lr": 5e-4,
            "weight_decay": 0.05,
            "batch_size": 2,
            "patch_size": [32, 128, 128],
            "max_epoch": 10,
            "lejepa_lambda": 0.02,
            "num_dataloader_workers": 4,
        },
        "dataset_config": {
            "data_format": "zarr",
            "num_workers": 4,
            "volumes": [{"image": v} for v in UNLABELED_VOLUMES],
        },
    }

    os.makedirs("./configs/self_supervised", exist_ok=True)
    config_path = "./configs/self_supervised/lejepa_config.yaml"

    with open(config_path, "w") as f:
        yaml.dump(config, f)

    print(f"LeJEPA Config written to {config_path}")
    print("Launching official Vesuvius LeJEPA trainer...")

    # Command to run the official trainer CLI
    cmd = [
        sys.executable,
        "villa/vesuvius/src/vesuvius/models/training/cli.py",
        "--config",
        config_path,
        "--trainer",
        "lejepa",
        "--max-epoch",
        "10",
    ]

    if args.execute:
        print("Executing training command...")
        subprocess.run(cmd, check=True)
    else:
        print(f"Dry run. Use --execute to start pretraining:\n{' '.join(cmd)}")


if __name__ == "__main__":
    main()
