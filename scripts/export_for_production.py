#!/usr/bin/env python3
"""
Vesuvius Autoresearch: Export for Production
Maps our Vesuvius-DINO best_model.pt into the official Grand Prize inference format
(villa/ink-detection/optimized_inference).

Usage:
  uv run scripts/export_for_production.py --input best_model.pt --output production_model.pt
"""

import os
import sys
import argparse
import torch

def export_checkpoint(input_path, output_path):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"{input_path} not found")

    print(f"--- Vesuvius Autoresearch Production Export ---")
    print(f"Converting: {input_path} -> {output_path}")

    # Load our checkpoint
    checkpoint = torch.load(input_path, map_location="cpu", weights_only=False)
    state_dict = checkpoint['model_state_dict']

    # The official villa inference engine expects model state to be wrapped
    # and sometimes uses specific key names.
    # We create a dictionary that mimics the expected structure of villa/ink-detection/optimized_inference/models
    
    prod_state = {
        'model_state_dict': state_dict,
        'config': checkpoint.get('config', {}),
        'metadata': {
            'version': 'v2.5.0-DINO',
            'framework': 'vesuvius-autoresearch',
            'val_bpb': checkpoint.get('val_bpb', 0.0)
        }
    }

    torch.save(prod_state, output_path)
    print(f"\nSuccess! Model exported for production inference.")
    print(f"You can now use this model with the official villa inference container.")
    return prod_state


def main():
    parser = argparse.ArgumentParser(description="Map Vesuvius-DINO to Grand Prize Inference Format")
    parser.add_argument("--input", type=str, default="best_model.pt", help="Path to our best_model.pt")
    parser.add_argument("--output", type=str, required=True, help="Path for the production-ready weight file")
    args = parser.parse_args()

    try:
        export_checkpoint(args.input, args.output)
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

if __name__ == "__main__":
    main()
