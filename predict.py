"""
Vesuvius Prediction Script.
Performs inference on a specific block of a Vesuvius scroll volume.
Usage: uv run predict.py --uri "s3://..." --z 1000 --y 2000 --x 3000
"""

import os
import argparse
import json
import torch
import torch.nn.functional as F
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from vesuvius_model import InkDetectorOptimized, VesuviusConfig
from vesuvius_loader import FastVesuviusVolume

def get_weight_window(patch_size, device):
    """Generates a 2D Hanning window for soft-tiling."""
    h = torch.hann_window(patch_size, periodic=False).to(device)
    window = h.unsqueeze(1) * h.unsqueeze(0)
    return window

def predict():
    parser = argparse.ArgumentParser()
    parser.add_argument("--uri", type=str, required=True, help="S3 or local path to Zarr volume")
    parser.add_argument("--z", type=int, required=True)
    parser.add_argument("--y", type=int, required=True)
    parser.add_argument("--x", type=int, required=True)
    parser.add_argument("--width", type=int, default=None, help="Total width to predict")
    parser.add_argument("--height", type=int, default=None, help="Total height to predict")
    parser.add_argument("--stride", type=int, default=None, help="Stride for soft-tiling")
    parser.add_argument("--patch_size", type=int, default=32)
    parser.add_argument("--num_layers", type=int, default=16)
    parser.add_argument("--base_feat", type=int, default=128)
    parser.add_argument("--output_img", type=str, default=None, help="Force output image path")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading volume from {args.uri}...")

    # Load trained model first to get the correct hyperparameters
    checkpoint_path = "best_model.pt"
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Trained model not found at {checkpoint_path}. Please run training first.")
        
    checkpoint = torch.load(checkpoint_path, map_location=device)
    config_dict = checkpoint.get('config', {})
    
    # Reconstruct VesuviusConfig from checkpoint, overriding args if present
    patch_size = config_dict.get('patch_size', args.patch_size)
    num_layers = config_dict.get('num_layers', args.num_layers)
    base_feat = config_dict.get('base_feat', args.base_feat)
    num_blocks = config_dict.get('num_blocks', 16)
    num_heads = config_dict.get('num_heads', 8)
    dropout = config_dict.get('dropout', 0.0)
    
    v_config = VesuviusConfig(
        patch_size=patch_size, 
        num_layers=num_layers, 
        base_feat=base_feat,
        num_blocks=num_blocks,
        num_heads=num_heads,
        dropout=dropout
    )
    
    model = InkDetectorOptimized(v_config).to(device)
    model.load_state_dict(checkpoint['model_state_dict'], strict=False)
    model.eval()

    # Open the dataset
    dataset = FastVesuviusVolume(args.uri)
    
    # Determine region and tiling parameters
    predict_width = args.width if args.width else patch_size
    predict_height = args.height if args.height else patch_size
    stride = args.stride if args.stride else patch_size // 2 if (args.width or args.height) else patch_size
    
    # Initialize accumulation buffers
    full_prob_ink = torch.zeros((predict_height, predict_width), device=device)
    full_prob_fiber = torch.zeros((predict_height, predict_width), device=device)
    full_weight = torch.zeros((predict_height, predict_width), device=device)
    
    weight_window = get_weight_window(patch_size, device)
    
    print(f"Starting Soft-Tiling Inference: {predict_width}x{predict_height} (stride={stride})...")

    # Tiling Loop
    for y_off in range(0, predict_height - patch_size + 1, stride):
        for x_off in range(0, predict_width - patch_size + 1, stride):
            curr_y = args.y + y_off
            curr_x = args.x + x_off
            
            # Read the block
            block = dataset[
                args.z : args.z + num_layers,
                curr_y : curr_y + patch_size,
                curr_x : curr_x + patch_size
            ]

            # Prepare input
            x = dataset.normalize(block).unsqueeze(0).unsqueeze(0).to(device) # [B, C, Z, H, W]

            with torch.no_grad():
                out_ink_2d, out_fiber, out_qc = model(x, return_fiber=True, return_qc=True)
                
                # Gate ink prediction with QC score
                gate = torch.sigmoid(out_qc / 0.1)
                prob_ink = torch.sigmoid(out_ink_2d).squeeze() * gate.view(-1)
                
                prob_fiber = torch.sigmoid(out_fiber.mean(dim=2)).squeeze()
                
                # Accumulate with weight window
                full_prob_ink[y_off:y_off+patch_size, x_off:x_off+patch_size] += prob_ink * weight_window
                full_prob_fiber[y_off:y_off+patch_size, x_off:x_off+patch_size] += prob_fiber * weight_window
                full_weight[y_off:y_off+patch_size, x_off:x_off+patch_size] += weight_window

    # Normalize by weights
    full_prob_ink /= (full_weight + 1e-8)
    full_prob_fiber /= (full_weight + 1e-8)
    
    prob_ink_final = full_prob_ink.cpu().numpy()
    prob_fiber_final = full_prob_fiber.cpu().numpy()

    # Save results
    os.makedirs("predictions", exist_ok=True)
    base_name = f"pred_{args.z}_{args.y}_{args.x}_{predict_width}x{predict_height}"
    np.save(f"predictions/{base_name}_ink.npy", prob_ink_final)
    np.save(f"predictions/{base_name}_fiber.npy", prob_fiber_final)

    # Save as Crackle-Viewer compatible PNG (8-bit grayscale)
    from PIL import Image
    ink_uint8 = (np.clip(prob_ink_final, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(ink_uint8).save(f"predictions/{base_name}_ink.png")

    # Generate Visualization (using center CT slice of the whole region)
    # Note: For very large regions, we'd need to fetch the CT slice in parts too.
    # For now, we fetch the middle slice of the entire requested area.
    ct_full = dataset[args.z + num_layers // 2, args.y : args.y + predict_height, args.x : args.x + predict_width]
    ct_slice = np.array(ct_full, dtype=np.float32) / 255.0

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes[0].imshow(ct_slice, cmap='gray')
    axes[0].set_title(f"CT Slice (Z={args.z + num_layers // 2})")
    
    axes[1].imshow(prob_fiber_final, cmap='magma')
    axes[1].set_title("Fiber Context (Fused)")
    
    axes[2].imshow(ct_slice, cmap='gray')
    axes[2].imshow(prob_ink_final, cmap='jet', alpha=0.5)
    axes[2].set_title("Gated Ink Overlay (Soft-Tiled)")

    # Add Scale Bar
    pixel_size_um = 8.0
    one_cm_px = 10000 / pixel_size_um
    one_mm_px = 1000 / pixel_size_um
    
    for ax in axes:
        bar_px = one_mm_px if predict_width < one_cm_px else one_cm_px
        label = "1mm" if predict_width < one_cm_px else "1cm"
        rect = Rectangle((10, predict_height - 20), bar_px, 5, facecolor='white', edgecolor='black')
        ax.add_patch(rect)
        ax.text(10, predict_height - 25, label, color='white', fontsize=10, fontweight='bold')
        ax.axis('off')

    plt.tight_layout()
    out_path = args.output_img if args.output_img else f"predictions/{base_name}.png"
    plt.savefig(out_path)
    plt.close()

    print(f"\nPrediction Complete!")
    print(f"Region: {predict_width}x{predict_height} at Z={args.z}, Y={args.y}, X={args.x}")
    print(f"Visualization saved to {out_path}")

if __name__ == "__main__":
    predict()