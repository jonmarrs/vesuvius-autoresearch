#!/usr/bin/env python3
import argparse
import json
import os

from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset


def main():
    parser = argparse.ArgumentParser(description="Intelligent Patch Extraction")
    parser.add_argument("--input", required=True, help="Path to volume zarr")
    parser.add_argument(
        "--labels", required=True, help="Path to labels (inklabels.png)"
    )
    parser.add_argument("--mask", default=None, help="Path to mask (mask.png)")
    parser.add_argument("--output", required=True, help="Path to output patches.json")
    parser.add_argument("--patch_size", type=int, default=64, help="Patch size")
    parser.add_argument("--num_layers", type=int, default=16, help="Number of z layers")
    parser.add_argument(
        "--min_mask_ratio", type=float, default=0.05, help="Minimum mask area ratio"
    )
    parser.add_argument(
        "--min_ink_ratio", type=float, default=0.01, help="Minimum ink area ratio"
    )
    parser.add_argument(
        "--require_ink", action="store_true", help="Filter patches that have low ink"
    )
    args = parser.parse_args()

    print(f"Extracting patches from {args.input}...")
    dataset = VesuviusLabeledDataset(
        volume_uri=args.input,
        labels_path=args.labels,
        mask_path=args.mask,
        patch_size=args.patch_size,
        num_layers=args.num_layers,
        require_ink=args.require_ink,
        min_mask_ratio=args.min_mask_ratio,
        min_ink_ratio=args.min_ink_ratio,
    )

    valid_coords = dataset.valid_coords.tolist()

    out_data = {
        "volume": args.input,
        "labels": args.labels,
        "patch_size": args.patch_size,
        "num_patches": len(valid_coords),
        "patches": [{"y": y, "x": x} for y, x in valid_coords],
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(out_data, f, indent=4)

    print(f"Extracted {len(valid_coords)} valid patches to {args.output}")


if __name__ == "__main__":
    main()
