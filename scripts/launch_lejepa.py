#!/usr/bin/env python3
import os
import sys
import yaml
import subprocess

def main():
    """
    Launcher for official LeJEPA pretraining.
    Builds a foundation model from unlabeled scroll data.
    """
    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
    VILLA_PATH = os.path.join(PROJECT_ROOT, "villa/vesuvius/src")
    sys.path.append(VILLA_PATH)
    
    # Target unlabeled volumes (Scroll 2/3)
    UNLABELED_VOLUMES = [
        "local_data/PHerc0125_Divisions/div_90/0",
        "local_data/PHerc0125_Divisions/div_100/0"
    ]
    
    config = {
        "tr_setup": {
            "model_name": "lejepa_foundation_v1",
            "ckpt_out_base": "./checkpoints/self_supervised/",
            "tr_val_split": 0.95
        },
        "tr_config": {
            "trainer": "lejepa",
            "initial_lr": 5e-4,
            "weight_decay": 0.05,
            "batch_size": 2,
            "patch_size": [64, 192, 192],
            "max_epoch": 100,
            "lejepa_lambda": 0.02
        },
        "dataset_config": {
            "volume_paths": [{"input": v} for v in UNLABELED_VOLUMES]
        }
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
        "--config", config_path
    ]
    
    # In a real environment, we'd run this:
    # subprocess.run(cmd)
    print(f"Run this command to start pretraining:\n{' '.join(cmd)}")

if __name__ == "__main__":
    main()
