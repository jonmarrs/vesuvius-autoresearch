#!/usr/bin/env python3
import os
import sys

import yaml


def main():
    """
    Launcher for official Vesuvius Uncertainty-Aware Mean Teacher.
    Trains on labeled Fragment 1 data and unlabeled Scroll 2/3 volumes to solve the Domain Gap.
    """
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    VILLA_PATH = os.path.join(PROJECT_ROOT, "villa/vesuvius/src")
    sys.path.append(VILLA_PATH)

    LABELED_VOLUMES = [
        os.path.join(PROJECT_ROOT, "local_data/PHercParis2Fr47/surface_volume.zarr")
    ]

    UNLABELED_VOLUMES = [
        os.path.join(PROJECT_ROOT, "local_data/PHerc0125_Divisions/div_90/0"),
        os.path.join(PROJECT_ROOT, "local_data/PHerc0125_Divisions/div_100/0"),
    ]

    config = {
        "tr_setup": {
            "model_name": "uamt_domain_adaptation",
            "ckpt_out_base": "./checkpoints/semi_supervised/",
            "tr_val_split": 0.95,
        },
        "model_config": {"patch_embed_size": [8, 8, 8]},
        "tr_config": {
            "trainer": "TrainUncertaintyAwareMeanTeacher",
            "initial_lr": 1e-4,
            "weight_decay": 0.01,
            "batch_size": 2,
            "patch_size": [32, 128, 128],
            "max_epoch": 20,
            "ema_decay": 0.99,
            "consistency": 0.1,
            "consistency_rampup": 200,
            "num_dataloader_workers": 0,
        },
        "dataset_config": {
            "data_format": "zarr",
            "num_workers": 0,
            "labeled_volumes": [{"image": v} for v in LABELED_VOLUMES],
            "unlabeled_volumes": [{"image": v} for v in UNLABELED_VOLUMES],
        },
    }

    os.makedirs(os.path.join(PROJECT_ROOT, "configs/semi_supervised"), exist_ok=True)
    config_path = os.path.join(PROJECT_ROOT, "configs/semi_supervised/uamt_config.yaml")

    with open(config_path, "w") as f:
        yaml.dump(config, f)

    print(f"UAMT Config written to {config_path}")
    print("Launching official Vesuvius UAMT trainer...")

    cmd = [
        sys.executable,
        "villa/vesuvius/src/vesuvius/models/training/cli.py",
        "--config",
        config_path,
        "--trainer",
        "TrainUncertaintyAwareMeanTeacher",
        "--max-epoch",
        "20",
    ]

    print(
        f"Run this command to start semi-supervised domain adaptation:\n{' '.join(cmd)}"
    )


if __name__ == "__main__":
    main()
