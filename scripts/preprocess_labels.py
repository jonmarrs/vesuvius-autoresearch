#!/usr/bin/env python3
"""
Vesuvius Autoresearch: Label Hole Filling Pipeline
Wraps the vesuvius/scripts/fill_inner_outer_labels.py from the ScrollPrize/villa submodule.
This script cleans and fills gaps in our ink labels (inklabels.png) to ensure
the training swarm optimizes against high-quality, continuous strokes.

Usage:
  uv run scripts/preprocess_labels.py --input path/to/inklabels.png --output path/to/filled_labels.png
"""

import os
import sys
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description="Fill holes in Vesuvius ink labels")
    parser.add_argument("--input", type=str, required=True, help="Path to raw inklabels.png")
    parser.add_argument("--output", type=str, required=True, help="Output path for filled labels")
    args = parser.parse_args()

    vesuvius_src_path = os.path.abspath("villa/vesuvius/src")
    if not os.path.exists(vesuvius_src_path):
        print("Error: 'villa/vesuvius/src' not found.")
        sys.exit(1)

    fill_script = os.path.join(vesuvius_src_path, "vesuvius", "scripts", "fill_inner_outer_labels.py")
    if not os.path.exists(fill_script):
        print(f"Error: {fill_script} not found.")
        sys.exit(1)

    print(f"--- Vesuvius Autoresearch Label Hole Filling ---")
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    
    # Run the official label filler
    # Usage: python fill_inner_outer_labels.py <input> <output>
    cmd = ["python3", fill_script, args.input, args.output]
    
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{vesuvius_src_path}:{env.get('PYTHONPATH', '')}"
    
    try:
        subprocess.run(cmd, env=env, check=True)
        print(f"\nSuccess! Filled labels saved to {args.output}")
    except subprocess.CalledProcessError as e:
        print(f"\nLabel filling failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
