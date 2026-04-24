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
import numpy as np
import cv2

# Add villa path for imports
vesuvius_src_path = os.path.abspath("villa/vesuvius/src")
sys.path.append(vesuvius_src_path)

try:
    from vesuvius.scripts.fill_inner_outer_labels import detect_inner_region, detect_outer_region
except ImportError:
    print("Error: Could not import detection functions from villa submodule.")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Fill holes in Vesuvius ink labels")
    parser.add_argument("--input", type=str, required=True, help="Path to raw inklabels.png")
    parser.add_argument("--output", type=str, required=True, help="Output path for filled labels")
    parser.add_argument("--fill-value", type=int, default=255, help="Value to fill (default 255)")
    parser.add_argument("--alpha", type=float, default=0.005, help="Alpha for outer detection")
    parser.add_argument("--skip-outer", action="store_true", help="Skip outer region filling")
    parser.add_argument("--skip-inner", action="store_true", help="Skip inner region filling")
    args = parser.parse_args()

    print(f"--- Vesuvius Autoresearch Label Hole Filling (Direct PNG) ---")
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    
    label_img = cv2.imread(args.input, cv2.IMREAD_GRAYSCALE)
    if label_img is None:
        print(f"Error: Could not read {args.input}")
        sys.exit(1)

    # Initialize output with original labels
    filled_labels = label_img.copy()
    
    if not args.skip_outer:
        print(f"Detecting outer regions (alpha={args.alpha})...")
        outer_mask = detect_outer_region(label_img, alpha=args.alpha, max_points=10000)
        if outer_mask is not None:
            filled_labels[outer_mask] = args.fill_value
            print(f"  Filled {outer_mask.sum()} outer pixels.")

    if not args.skip_inner:
        print(f"Detecting inner regions...")
        inner_mask = detect_inner_region(label_img)
        if inner_mask is not None:
            filled_labels[inner_mask] = args.fill_value
            print(f"  Filled {inner_mask.sum()} inner pixels.")

    cv2.imwrite(args.output, filled_labels)
    print(f"\nSuccess! Filled labels saved to {args.output}")

if __name__ == "__main__":
    main()
