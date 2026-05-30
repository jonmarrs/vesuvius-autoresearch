#!/usr/bin/env python3
"""
Vesuvius Autoresearch: Automated Label Curation Pipeline

This script utilizes the `extract_good_labels` tool from the official VC Proofreader
repository to automatically curate our 3D segmentation datasets. It filters out noisy,
crushed, or branched papyrus sheets before they enter the training pipeline (e.g.,
before feeding them to Mutex-Affinity trainers).

Usage:
  python scripts/curate_training_data.py --input <path_to_labeled_zarr> --output <path_to_curated_zarr>
"""

import argparse
import os
import sys

# Add the vc_proofreader directory to the path so we can import it
VC_PROOFREADER_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../villa/segmentation/vc_proofreader")
)
if VC_PROOFREADER_PATH not in sys.path:
    sys.path.insert(0, VC_PROOFREADER_PATH)

try:
    from extract_good_labels import process
except ImportError as e:
    print(f"Error importing extract_good_labels: {e}")
    print("Ensure the villa submodule is initialized and the path is correct.")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Curate 3D papyrus sheet segmentation labels."
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Input 3D OME-Zarr containing segmentation labels (e.g., from Thaumato)",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output path for the curated 'Gold Standard' Zarr",
    )
    parser.add_argument(
        "--chunk-size", type=int, default=64, help="Chunk size for curation evaluation"
    )
    parser.add_argument(
        "--min-percent",
        type=float,
        default=1.0,
        help="Minimum percentage of voxels labeled to keep chunk",
    )
    parser.add_argument(
        "--max-percent",
        type=float,
        default=95.0,
        help="Maximum percentage (avoids completely solid false-positive chunks)",
    )
    parser.add_argument(
        "--min-cc", type=int, default=1, help="Minimum number of connected components"
    )
    parser.add_argument(
        "--max-cc",
        type=int,
        default=5,
        help="Maximum connected components (rejects highly fragmented/crushed regions)",
    )
    parser.add_argument(
        "--reject-branches",
        action="store_true",
        default=True,
        help="Reject chunks with 2D skeletal branches (folds/merges)",
    )
    parser.add_argument(
        "--workers", type=int, default=4, help="Number of worker processes"
    )

    args = parser.parse_args()

    print("--- Vesuvius Autoresearch: Automated Label Curation ---")
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    print("Criteria:")
    print(f"  - Chunk Size: {args.chunk_size}^3")
    print(f"  - Labeled Density: {args.min_percent}% to {args.max_percent}%")
    print(f"  - Connected Components: {args.min_cc} to {args.max_cc}")
    print(f"  - Reject Branches/Folds: {args.reject_branches}")

    # We leave target_value=None to consider ANY labeled voxel (since instance IDs vary).
    # If the user provides a binary mask, target_value=255 or 1 can be passed if modified.
    try:
        process(
            input_path=args.input,
            output_path=args.output,
            chunk_size=(args.chunk_size, args.chunk_size, args.chunk_size),
            array_key="0",  # Default OME-Zarr multiscale level
            min_cc=args.min_cc,
            max_cc=args.max_cc,
            min_percent=args.min_percent,
            max_percent=args.max_percent,
            require_nonzero=True,
            target_value=None,
            connectivity=26,
            write_empty_chunks=False,
            reject_branches=args.reject_branches,
            workers=args.workers,
        )
        print("\nCuration Complete! Gold Standard dataset is ready for training.")
    except Exception as e:
        print(f"\nCuration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
