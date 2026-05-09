"""
Vesuvius Autoresearch: Ensemble Prediction Script.
Performs inference on a specific block of a Vesuvius scroll volume using a "Voter Swarm" 
of multiple architectures to eliminate hallucinations (Sprint 012).

Usage: uv run ensemble_predict.py --uri "s3://..." --z 1000 --y 2000 --x 3000 --checkpoints best_model.pt other_model.pt
"""

import os
import argparse
import json
import torch
import torch.nn.functional as F
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from vesuvius_model import InkDetectorOptimized, VesuviusTimeSformer, VesuviusConfig
from vesuvius_loader import FastVesuviusVolume
from predict import get_weight_window, load_compatible_state_dict, save_vc3d_zarr

def ensemble_predict():
    parser = argparse.ArgumentParser()
    parser.add_argument("--uri", type=str, required=True, help="S3 or local path to Zarr volume")
    parser.add_argument("--z", type=int, required=True)
    parser.add_argument("--y", type=int, required=True)
    parser.add_argument("--x", type=int, required=True)
    parser.add_argument("--width", type=int, default=None, help="Total width to predict")
    parser.add_argument("--height", type=int, default=None, help="Total height to predict")
    parser.add_argument("--stride", type=int, default=None, help="Stride for soft-tiling")
    parser.add_argument("--checkpoints", nargs='+', required=True, help="List of checkpoint paths to ensemble")
    parser.add_argument("--patch_size", type=int, default=64)
    parser.add_argument("--output_img", type=str, default=None, help="Force output image path")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading volume from {args.uri}...")

    models = []
    
    # Load all models
    for cp_path in args.checkpoints:
        if not os.path.exists(cp_path):
            print(f"Warning: Checkpoint {cp_path} not found, skipping...")
            continue
            
        print(f"Loading checkpoint {cp_path}...")
        checkpoint = torch.load(cp_path, map_location=device, weights_only=False)
        config_dict = checkpoint.get('config', {})
        
        # Reconstruct VesuviusConfig
        patch_size = config_dict.get('patch_size', args.patch_size)
        num_layers = config_dict.get('num_layers', 16)
        base_feat = config_dict.get('base_feat', 64)
        num_blocks = config_dict.get('num_blocks', 16)
        num_heads = config_dict.get('num_heads', 8)
        dropout = config_dict.get('dropout', 0.0)
        use_ridges = config_dict.get('use_ridges', False)
        architecture = config_dict.get('architecture', 'gated_unet')
        
        v_config = VesuviusConfig(
            patch_size=patch_size, 
            num_layers=num_layers, 
            base_feat=base_feat,
            num_blocks=num_blocks,
            num_heads=num_heads,
            dropout=dropout,
            in_channels=2 if use_ridges else 1,
            architecture=architecture
        )
        
        if architecture == "timesformer":
            model = VesuviusTimeSformer(v_config).to(device)
        elif architecture == "resnet3d_decoder":
            from vesuvius_model import VesuviusResNet3DDecoder
            model = VesuviusResNet3DDecoder(v_config).to(device)
        else:
            model = InkDetectorOptimized(v_config).to(device)
        load_compatible_state_dict(model, checkpoint['model_state_dict'])
        model.eval()
        models.append((model, use_ridges, num_layers, patch_size))

    if not models:
        raise ValueError("No valid models loaded for ensemble!")

    # Assuming all models are evaluated on the same patch size for simplicity in this version
    # The max patch size is used for stride and tiling
    max_patch_size = max([m[3] for m in models])
    max_layers = max([m[2] for m in models])
    
    # We will use dataset logic compatible with the largest required context
    # Usually in ensembles, all models expect the same input volume size or are resampled internally
    use_ridges_any = any([m[1] for m in models])
    dataset = FastVesuviusVolume(args.uri, use_ridges=use_ridges_any)
    
    predict_width = args.width if args.width else max_patch_size
    predict_height = args.height if args.height else max_patch_size
    stride = args.stride if args.stride else max_patch_size // 2
    
    # Initialize accumulation buffers
    full_prob_ink = torch.zeros((predict_height, predict_width), device=device)
    full_prob_fiber = torch.zeros((predict_height, predict_width), device=device)
    full_weight = torch.zeros((predict_height, predict_width), device=device)
    
    weight_window = get_weight_window(max_patch_size, device)
    
    print(f"Starting Ensemble Inference ({len(models)} models): {predict_width}x{predict_height}...")

    # Tiling Loop
    for y_off in range(0, predict_height - max_patch_size + 1, stride):
        for x_off in range(0, predict_width - max_patch_size + 1, stride):
            curr_y = args.y + y_off
            curr_x = args.x + x_off
            
            # Read block capable of satisfying max_layers
            block = dataset[
                args.z : args.z + max_layers,
                curr_y : curr_y + max_patch_size,
                curr_x : curr_x + max_patch_size
            ]

            x_norm = dataset.normalize(block).unsqueeze(0).to(device) # [B, C, Z, H, W]
            
            ensemble_ink = 0.0
            ensemble_fiber = 0.0
            
            with torch.no_grad():
                for model, use_ridges, n_layers, p_size in models:
                    # Slice input to match model requirements
                    model_x = x_norm[:, :, :n_layers, :p_size, :p_size]
                    if not use_ridges:
                        model_x = model_x[:, :1, :, :, :] # Take only CT channel if ridges not used
                    
                    if len(model_x.shape) == 4:
                        # shape is [B, Z, H, W], we need [B, 1, Z, H, W]
                        model_x = model_x.unsqueeze(1)
                        
                    out_ink_2d, out_fiber, out_qc = model(model_x, return_fiber=True, return_qc=True)
                    
                    gate = torch.sigmoid(out_qc / 0.1)
                    prob_ink = torch.sigmoid(out_ink_2d).squeeze() * gate.view(-1)
                    prob_fiber = torch.sigmoid(out_fiber.mean(dim=2)).squeeze()
                    
                    ensemble_ink += prob_ink
                    ensemble_fiber += prob_fiber
                    
                # Average probabilities
                ensemble_ink /= len(models)
                ensemble_fiber /= len(models)
                
                # Accumulate with weight window
                full_prob_ink[y_off:y_off+max_patch_size, x_off:x_off+max_patch_size] += ensemble_ink * weight_window
                full_prob_fiber[y_off:y_off+max_patch_size, x_off:x_off+max_patch_size] += ensemble_fiber * weight_window
                full_weight[y_off:y_off+max_patch_size, x_off:x_off+max_patch_size] += weight_window

    # Normalize by weights
    full_prob_ink /= (full_weight + 1e-8)
    full_prob_fiber /= (full_weight + 1e-8)
    
    prob_ink_final = full_prob_ink.cpu().numpy()
    prob_fiber_final = full_prob_fiber.cpu().numpy()

    # Save results
    os.makedirs("predictions", exist_ok=True)
    base_name = f"ensemble_pred_{args.z}_{args.y}_{args.x}_{predict_width}x{predict_height}"
    np.save(f"predictions/{base_name}_ink.npy", prob_ink_final)
    np.save(f"predictions/{base_name}_fiber.npy", prob_fiber_final)

    from PIL import Image
    ink_uint8 = (np.clip(prob_ink_final, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(ink_uint8).save(f"predictions/{base_name}_ink.png")
    
    zarr_path = f"predictions/{base_name}_ink.zarr"
    save_vc3d_zarr(zarr_path, ink_uint8, name=f"Ensemble Ink Prediction {base_name}")

    ct_full = dataset[args.z + max_layers // 2, args.y : args.y + predict_height, args.x : args.x + predict_width]
    ct_slice = np.array(ct_full, dtype=np.float32) / 255.0

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes[0].imshow(ct_slice, cmap='gray')
    axes[0].set_title(f"CT Slice (Z={args.z + max_layers // 2})")
    
    axes[1].imshow(prob_fiber_final, cmap='magma')
    axes[1].set_title("Ensemble Fiber Context")
    
    axes[2].imshow(ct_slice, cmap='gray')
    axes[2].imshow(prob_ink_final, cmap='jet', alpha=0.5)
    axes[2].set_title("Ensemble Gated Ink Overlay")

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

    print(f"\nEnsemble Prediction Complete!")
    print(f"Visualization saved to {out_path}")

if __name__ == "__main__":
    ensemble_predict()
