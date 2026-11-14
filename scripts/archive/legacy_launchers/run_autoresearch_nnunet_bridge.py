#!/usr/bin/env python3
"""
Bridge between Autoresearch Loop and official Villa nnUNet Optimization Framework.
Allows the swarm to evolve nnUNet trainers dynamically.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import yaml

# Add villa paths
VILLA_SEG_DIR = os.path.abspath("villa/segmentation/model_optimization_framework")
if VILLA_SEG_DIR not in sys.path:
    sys.path.append(VILLA_SEG_DIR)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/config_nnunet.yml")
    parser.add_argument("--evolve-attr", help="Attribute to tweak (e.g. initial_lr)")
    parser.add_argument("--evolve-val", help="New value for the attribute")
    parser.add_argument("--variant-name", help="Name for this evolution variant")
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"Error: Base config {args.config} not found.")
        sys.exit(1)

    with open(args.config) as f:
        config = yaml.safe_load(f)

    # Apply evolution
    if args.evolve_attr and args.evolve_val:
        variant = (
            args.variant_name
            or f"evolved_{args.evolve_attr}_{args.evolve_val}".replace(".", "p")
        )
        print(f"Applying Evolution: {args.evolve_attr} = {args.evolve_val}")

        # Assume first configuration is the template
        config["configurations"] = [
            {
                "name": variant,
                "params": {
                    args.evolve_attr: float(args.evolve_val)
                    if "." in args.evolve_val or "e" in args.evolve_val
                    else int(args.evolve_val)
                },
            }
        ]

    tmp_config = "configs/config_nnunet_tmp.yml"
    with open(tmp_config, "w") as f:
        yaml.dump(config, f)

    print(f"Evolved config written to {tmp_config}")

    # In a real run, the Autoresearch loop would now call:
    # python villa/segmentation/model_optimization_framework/generate_trainers.py --config configs/config_nnunet_tmp.yml
    # python villa/segmentation/model_optimization_framework/run_training.py --config configs/config_nnunet_tmp.yml --variants <variant>


if __name__ == "__main__":
    main()
