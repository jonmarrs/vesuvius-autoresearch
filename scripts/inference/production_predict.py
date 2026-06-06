#!/usr/bin/env python3
"""
Vesuvius Autoresearch: Production Prediction Pipeline (Distributed Inference + TTA + Blending)
Wraps the official Villa production inference pipeline for full-scroll inference.
This script performs:
1. Distributed inference with TTA (mirroring/rotation) over a large Zarr volume.
2. Gaussian logit blending to seamlessly stitch overlapping sliding-window tiles.
3. Finalization into a standardized unsigned 8-bit prediction volume.

Usage:
  uv run scripts/inference/production_predict.py --model best_model.pt --input data/scroll.zarr --output data/predictions/ --num_parts 4 --part_id 0
"""

import argparse
import os
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Run Production Inference on Full Scroll"
    )
    parser.add_argument(
        "--model", type=str, required=True, help="Path to best_model.pt checkpoint"
    )
    parser.add_argument(
        "--input", type=str, required=True, help="Path to input Zarr volume"
    )
    parser.add_argument(
        "--output", type=str, required=True, help="Path to output directory"
    )
    parser.add_argument(
        "--num_parts",
        type=int,
        default=1,
        help="Total number of distributed inference shards",
    )
    parser.add_argument(
        "--part_id", type=int, default=0, help="Shard ID to run (0 to num_parts-1)"
    )
    parser.add_argument(
        "--disable_tta", action="store_true", help="Disable Test-Time Augmentation"
    )
    parser.add_argument(
        "--overlap", type=float, default=0.5, help="Sliding window overlap fraction"
    )

    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    logits_dir = os.path.join(args.output, "logits")
    blended_dir = os.path.join(args.output, "blended")
    final_dir = os.path.join(args.output, "final")

    print("--- Vesuvius Autoresearch: Production Inference Pipeline ---")
    print(f"Model: {args.model}")
    print(f"Input: {args.input}")
    print(f"Part: {args.part_id}/{args.num_parts}")

    # 1. Distributed Inference + TTA
    print("\n[1/3] Running Inference...")
    cmd_infer = [
        "vesuvius.predict",
        "--model_path",
        args.model,
        "--input_dir",
        args.input,
        "--output_dir",
        logits_dir,
        "--num_parts",
        str(args.num_parts),
        "--part_id",
        str(args.part_id),
        "--overlap",
        str(args.overlap),
        "--save_softmax",
    ]
    if args.disable_tta:
        cmd_infer.append("--disable_tta")

    subprocess.run(cmd_infer, check=True)

    # In a distributed setting, blending and finalization should only occur
    # once ALL parts have finished. If num_parts > 1, we exit here and let the
    # user/orchestrator run blending separately after all shards complete.
    if args.num_parts > 1:
        print(
            f"\n[!] Part {args.part_id} finished. Skipping blending because num_parts > 1."
        )
        print(f"Run vesuvius.blend_logits once all {args.num_parts} parts are done.")
        sys.exit(0)

    # 2. Gaussian Blending
    print("\n[2/3] Running Gaussian Blending...")
    cmd_blend = [
        "vesuvius.blend_logits",
        "--input_dir",
        logits_dir,
        "--output_dir",
        blended_dir,
    ]
    subprocess.run(cmd_blend, check=True)

    # 3. Finalization
    print("\n[3/3] Finalizing Output...")
    cmd_finalize = [
        "vesuvius.finalize_outputs",
        "--input_dir",
        blended_dir,
        "--output_dir",
        final_dir,
        "--method",
        "softmax",
    ]
    subprocess.run(cmd_finalize, check=True)

    print(f"\nProduction inference complete. Final output at: {final_dir}")


if __name__ == "__main__":
    main()
