#!/usr/bin/env python3
"""
Wrapper script to train the Neural Tracing Pipeline's trace-ODE model.
This integrates Villa's built-in tracing module by running train_rowcol_cond.py
so that we can produce the required checkpoint for trace_service.py.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VILLA_TRAINER = (
    PROJECT_ROOT
    / "villa"
    / "vesuvius"
    / "src"
    / "vesuvius"
    / "neural_tracing"
    / "trainers"
    / "train_rowcol_cond.py"
)
OUT_DIR = PROJECT_ROOT / "checkpoints" / "neural_tracing"
CONFIG_PATH = PROJECT_ROOT / "reports" / "neural_tracing_train_config.json"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate the minimal configuration to start training
    config = {
        "out_dir": str(OUT_DIR),
        "seed": 42,
        "batch_size": 2,
        "num_workers": 2,
        "val_num_workers": 0,
        "learning_rate": 1e-4,
        "num_iterations": 10000,
        "log_frequency": 50,
        "ckpt_frequency": 1000,
        "compile_model": False,
        "training_mode": "rowcol_hidden",
        "datasets": [
            {
                "volume_path": str(
                    PROJECT_ROOT / "local_data" / "PHerc0125_Divisions" / "div_90" / "0"
                ),
                "volume_scale": 0,
                "segments_path": str(
                    PROJECT_ROOT
                    / "local_data"
                    / "PHerc0125_Divisions"
                    / "div_90"
                    / "segments"
                ),
            }
        ],
    }

    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    print(f"Generated Neural Tracing training config at {CONFIG_PATH}")
    print(f"Launching Villa trainer: {VILLA_TRAINER}")

    cmd = [sys.executable, str(VILLA_TRAINER), str(CONFIG_PATH)]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Training failed with exit code {e.returncode}")
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
