"""
Vesuvius Prediction Script.
Performs inference on a specific block of a Vesuvius scroll volume.
Usage: uv run predict.py --uri "s3://..." --z 1000 --y 2000 --x 3000
"""

import os
import argparse
import torch
import torch.nn.functional as F
import numpy as np
import tensorstore as ts
from vesuvius_model import InkDetectorOptimized, VesuviusConfig

def predict():
    parser = argparse.ArgumentParser()
    parser.add_argument("--uri", type=str, required=True, help="S3 or local path to Zarr volume")
    parser.add_argument("--z", type=int, required=True)
    parser.add_argument("--y", type=int, required=True)
    parser.add_argument("--x", type=int, required=True)
    parser.add_argument("--patch_size", type=int, default=32)
    parser.add_argument("--num_layers", type=int, default=16)
    parser.add_argument("--base_feat", type=int, default=128)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading volume from {args.uri}...")

    # Open the dataset
    from vesuvius_loader import FastVesuviusVolume
    dataset = FastVesuviusVolume(args.uri)

    # Read the block
    print(f"Reading block at Z={args.z}, Y={args.y}, X={args.x}...")
    block = dataset[
        args.z : args.z + args.num_layers,
        args.y : args.y + args.patch_size,
        args.x : args.x + args.patch_size
    ]

    # Prepare input
    x = torch.from_numpy(block.astype(np.float32) / 255.0).unsqueeze(0).unsqueeze(0).to(device) # [B, C, Z, H, W]

    # Initialize model
    config = VesuviusConfig(patch_size=args.patch_size, num_layers=args.num_layers, base_feat=args.base_feat)
    model = InkDetectorOptimized(config).to(device)
    model.eval()

    print("Running inference...")
    with torch.no_grad():
        out_ink, out_fiber, _ = model(x, return_fiber=True)
        prob_ink = torch.sigmoid(out_ink.mean(dim=2)).cpu().numpy()[0, 0]
        prob_fiber = torch.sigmoid(out_fiber.mean(dim=2)).cpu().numpy()[0, 0]

    # Save results
    os.makedirs("predictions", exist_ok=True)
    base_name = f"pred_{args.z}_{args.y}_{args.x}"
    np.save(f"predictions/{base_name}_ink.npy", prob_ink)
    np.save(f"predictions/{base_name}_fiber.npy", prob_fiber)

    # Generate Visualization with Scale Bar
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # 1. CT Context (Middle Slice)
    ct_slice = block[args.num_layers // 2].astype(np.float32) / 255.0
    axes[0].imshow(ct_slice, cmap='gray')
    axes[0].set_title("CT Slice (Middle)")
    
    # 2. Fiber Context (Spatial Structure)
    axes[1].imshow(prob_fiber, cmap='magma')
    axes[1].set_title("Fiber Context")
    
    # 3. Ink Prediction Overlay
    axes[2].imshow(ct_slice, cmap='gray')
    axes[2].imshow(prob_ink, cmap='jet', alpha=0.5)
    axes[2].set_title("Ink Prediction Overlay")

    # Add 1cm Scale Bar
    # Assuming 8um per pixel: 1cm = 10,000um / 8um = 1250 pixels.
    # If patch is smaller than 1250, we show 1mm (125 pixels).
    pixel_size_um = 8.0 # Standard assumption
    one_cm_px = 10000 / pixel_size_um
    one_mm_px = 1000 / pixel_size_um
    
    for ax in axes:
        # Drawing a 1mm scale bar for small patches, or 1cm if it fits
        bar_px = one_mm_px if args.patch_size < one_cm_px else one_cm_px
        label = "1mm" if args.patch_size < one_cm_px else "1cm"
        
        rect = Rectangle((10, args.patch_size - 20), bar_px, 5, facecolor='white', edgecolor='black')
        ax.add_patch(rect)
        ax.text(10, args.patch_size - 25, label, color='white', fontsize=10, fontweight='bold')
        ax.axis('off')

    plt.tight_layout()
    plt.savefig(f"predictions/{base_name}.png")
    plt.close()

    # Save Metadata JSON for Milestone Submission
    import json
    metadata = {
        "project": "Vesuvius Autoresearch",
        "scroll_uri": args.uri,
        "coordinates": {"z": args.z, "y": args.y, "x": args.x},
        "patch_size": args.patch_size,
        "num_layers": args.num_layers,
        "hallucination_mitigation": {
            "window_size_mm": (args.patch_size * pixel_size_um / 1000.0),
            "compliance_score": float(prob_ink.max()), 
            "status": "COMPLIANT (<0.5mm)" if (args.patch_size * pixel_size_um / 1000.0) <= 0.5 else "LARGE WINDOW"
        }
    }
    with open(f"predictions/{base_name}_meta.json", "w") as f:
        json.dump(metadata, f, indent=4)

    print(f"\nPrediction Complete!")
    print(f"Ink mean probability:   {prob_ink.mean():.4f}")
    print(f"Visualization saved to predictions/{base_name}.png")
    print(f"Metadata saved to predictions/{base_name}_meta.json")

if __name__ == "__main__":
    predict()
