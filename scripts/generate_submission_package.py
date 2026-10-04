#!/usr/bin/env python3
"""
Vesuvius Autoresearch: First Letters Submission Package Dry-Run
Generates a compliant submission package for the First Letters/Title Prize.
"""

import argparse
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts.validate_prize_artifact import validate


def main():
    parser = argparse.ArgumentParser(
        description="Generate a First Letters/Title submission package."
    )
    parser.add_argument("--prediction-image", default="predictions/pred_10_20_30.png")
    parser.add_argument("--out-dir", default="submission_package_dry_run")
    parser.add_argument("--scroll-id", default="Scroll 1 (Dry Run)")
    parser.add_argument("--segmentation-id", default="20230509172439")
    parser.add_argument("--position-xyz", default="1000,2000,3000")
    parser.add_argument("--voxel-resolution-um", type=float, default=8.0)
    parser.add_argument("--ml-window-px", type=int, default=64)
    args = parser.parse_args()

    if not math.isfinite(args.voxel_resolution_um) or args.voxel_resolution_um <= 0:
        parser.error("--voxel-resolution-um must be positive and finite")
    if args.ml_window_px <= 0:
        parser.error("--ml-window-px must be positive")
    try:
        position_xyz = [int(part.strip()) for part in args.position_xyz.split(",")]
        if len(position_xyz) != 3 or any(value < 0 for value in position_xyz):
            raise ValueError
    except ValueError:
        parser.error(
            "--position-xyz must contain three nonnegative integer voxel indices"
        )

    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)

    print("--- Generating First Letters Submission Package Dry-Run ---")

    # 1. Discovery Image with Scale Bar
    # Use a prediction image if available, else create a dummy
    src_img_path = args.prediction_image
    source_image_is_placeholder = False
    if os.path.exists(src_img_path):
        img = Image.open(src_img_path).convert("RGBA")
        print(f"Loaded source image {src_img_path}")
    else:
        print(
            f"Source image {src_img_path} not found. Creating placeholder dry-run image."
        )
        img = Image.new("RGBA", (2000, 1000), (50, 50, 50, 255))
        source_image_is_placeholder = True

    # Draw Scale Bar
    # 1 cm = 10,000 um. At 8 um/voxel, 1 cm = 1250 pixels.
    draw = ImageDraw.Draw(img)
    scale_px = round(10000.0 / args.voxel_resolution_um)
    # This template is illustrative; keep its declared bar inside the image.
    bar_x_start = 50
    bar_y = img.height - 50
    scale_bar_cm = img.width >= scale_px + 2 * bar_x_start and img.height >= 100
    bar_x_end = bar_x_start + scale_px

    # Add text
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except OSError:
        font = ImageFont.load_default()

    if scale_bar_cm:
        draw.line(
            [(bar_x_start, bar_y), (bar_x_end, bar_y)],
            fill=(255, 255, 255, 255),
            width=10,
        )
        draw.text(
            (bar_x_start, bar_y - 50),
            "1 cm (illustrative)",
            fill=(255, 255, 255, 255),
            font=font,
        )

    out_img_path = os.path.join(out_dir, "discovery_image_with_scale.png")
    img.save(out_img_path)
    print(f"Saved discovery image to {out_img_path}")

    # 2. Metadata (Segmentation ID, 3D Position, Window Size)
    window_mm = args.ml_window_px * args.voxel_resolution_um / 1000.0
    metadata = {
        "scroll_id": args.scroll_id,
        "segmentation_id": args.segmentation_id,
        "3d_position_xyz": position_xyz,
        "patch_size": args.ml_window_px,
        "window_width_px": args.ml_window_px,
        "window_height_px": args.ml_window_px,
        "ml_window_px": args.ml_window_px,
        "voxel_resolution_um": args.voxel_resolution_um,
        "window_size_mm": f"{window_mm:.3f} x {window_mm:.3f} mm",
        "scale_bar_cm": scale_bar_cm,
        "source_image_path": os.path.abspath(src_img_path),
        "output_image_path": os.path.abspath(out_img_path),
        "source_image_is_placeholder": source_image_is_placeholder,
        "metadata_is_dry_run": True,
        "evidence_mode": "placeholder_dry_run",
        "overlap_evidence_mode": "illustrative",
        "train_mask_path": os.path.abspath(os.path.join(out_dir, "train_mask.npy")),
        "predict_mask_path": os.path.abspath(os.path.join(out_dir, "predict_mask.npy")),
    }
    metadata_path = os.path.join(out_dir, "metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=4)
    print("Saved metadata.json")

    # 3. Train/Predict Mask
    # Create an explicit mask showing zero overlap between training data and prediction region
    mask_img = Image.new("RGB", (1000, 1000), (0, 0, 0))
    mask_draw = ImageDraw.Draw(mask_img)
    # Draw training region (red)
    mask_draw.rectangle([50, 50, 400, 400], fill=(255, 0, 0))
    # Draw prediction region (blue)
    mask_draw.rectangle([600, 600, 950, 950], fill=(0, 0, 255))
    mask_img.save(os.path.join(out_dir, "train_predict_mask.png"))
    train_mask = np.zeros((1000, 1000), dtype=bool)
    predict_mask = np.zeros((1000, 1000), dtype=bool)
    train_mask[50:401, 50:401] = True
    predict_mask[600:951, 600:951] = True
    np.save(os.path.join(out_dir, "train_mask.npy"), train_mask)
    np.save(os.path.join(out_dir, "predict_mask.npy"), predict_mask)
    print(
        "Saved illustrative train/predict masks; these do not verify training overlap."
    )

    # 4. Hallucination Mitigation Note
    hallucination_note = """# Hallucination Mitigation — Dry-Run Template

This package contains illustrative masks and operator-supplied geometry. It does
not establish that the source image is a calibrated CT prediction, that the
model obeys the declared window, or that training and prediction are disjoint.

For a real candidate, retain checkpoint and input provenance, provide actual
training/prediction masks in a common coordinate frame, and verify the discovery
image's physical scale. Report held-out ground-truth metrics and their limits.
Ensemble predictions and auxiliary supervision require evidence from the actual
model; neither guarantees that apparent letters are ink. The inherited skeleton
distance gate was withdrawn and must not be used as evidence of text detection.
"""
    with open(os.path.join(out_dir, "HALLUCINATION_MITIGATION.md"), "w") as f:
        f.write(hallucination_note)
    print("Saved HALLUCINATION_MITIGATION.md")

    readiness_report = validate(metadata_path)
    with open(os.path.join(out_dir, "PRIZE_READINESS_REPORT.json"), "w") as f:
        json.dump(readiness_report, f, indent=2)
    print(f"Saved PRIZE_READINESS_REPORT.json ({readiness_report['status']})")

    if readiness_report["status"] == "PASS":
        print("\nSubmission package passed mechanical readiness checks.")
    else:
        print("\nSubmission package built, but it is NOT ready for submission.")
        for failure in readiness_report["failures"]:
            print(f" [!] {failure}")
    print(
        "Dry-run files created. Actual provenance, overlap, scale, and scientific evidence remain unverified."
    )
    raise SystemExit(0 if readiness_report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
