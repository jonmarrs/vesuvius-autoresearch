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
import torch.nn as nn
from vesuvius_model import InkDetectorOptimized, VesuviusConfig
from vesuvius_loader import FastVesuviusVolume
from scripts.swarm_voter import SwarmVoter

try:
    from dynamic_network_architectures.architectures.unet import ResidualEncoderUNet
    from dynamic_network_architectures.building_blocks.helper import convert_dim_to_conv_op, get_matching_instancenorm
except ImportError as exc:
    print(f"Warning: ResidualEncoderUNet unavailable in predict.py; resenc_unet checkpoints cannot be loaded: {exc}")
    ResidualEncoderUNet = None


def load_compatible_state_dict(model, state_dict):
    model_state = model.state_dict()
    compatible = {}
    skipped = []
    for key, value in state_dict.items():
        if key in model_state and model_state[key].shape == value.shape:
            compatible[key] = value
        else:
            skipped.append(key)
    model.load_state_dict(compatible, strict=False)
    if skipped:
        print(f"Warning: skipped {len(skipped)} incompatible checkpoint tensors: {', '.join(skipped[:8])}")
    return skipped


class GenericMultiTaskWrapper(nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.projector = nn.Sequential(
            nn.AdaptiveAvgPool3d(1),
            nn.Flatten(),
            nn.Linear(1, 128),
        )

    def forward(self, x, return_fiber=False, return_qc=False, return_proj=False, return_st=False, **kwargs):
        out = self.model(x)
        if isinstance(out, (list, tuple)):
            out = out[0]
        if out.dim() == 5:
            ink_2d = torch.mean(out, dim=2)
        elif out.dim() == 2:
            ink_2d = out.view(out.shape[0], out.shape[1], 1, 1).expand(-1, -1, x.shape[3], x.shape[4])
        else:
            ink_2d = out

        results = [ink_2d]
        if return_fiber:
            results.append(out if out.dim() == 5 else out.unsqueeze(2))
        if return_qc:
            results.append(torch.zeros((x.shape[0], 1), device=x.device, dtype=ink_2d.dtype))
        if return_proj:
            proj_in = out if out.dim() == 5 else out.unsqueeze(2).unsqueeze(-1).unsqueeze(-1)
            results.append(self.projector(proj_in))
        if return_st:
            results.append(torch.zeros((x.shape[0], 6, *x.shape[2:]), device=x.device, dtype=ink_2d.dtype))
        return tuple(results) if len(results) > 1 else results[0]


def build_prediction_model(config_dict, args, use_ridges):
    architecture = config_dict.get("architecture", "gated_unet")
    base_feat = config_dict.get("base_feat", args.base_feat)
    v_config = VesuviusConfig(
        patch_size=config_dict.get("patch_size", args.patch_size),
        num_layers=config_dict.get("num_layers", args.num_layers),
        base_feat=base_feat,
        num_blocks=config_dict.get("num_blocks", 16),
        num_heads=config_dict.get("num_heads", 8),
        dropout=config_dict.get("dropout", 0.0),
        in_channels=2 if use_ridges else 1,
    )
    if architecture == "resenc_unet":
        if ResidualEncoderUNet is None:
            raise ImportError("ResidualEncoderUNet is required for resenc_unet checkpoints")
        n_stages = 3
        features_per_stage = [base_feat * (2**i) for i in range(n_stages)]
        strides = [[1, 1, 1]] + [[2, 2, 2]] * (n_stages - 1)
        backbone = ResidualEncoderUNet(
            input_channels=v_config.in_channels,
            n_stages=n_stages,
            features_per_stage=features_per_stage,
            conv_op=convert_dim_to_conv_op(3),
            kernel_sizes=[[3, 3, 3]] * n_stages,
            strides=strides,
            n_blocks_per_stage=[2] * n_stages,
            num_classes=1,
            n_conv_per_stage_decoder=[2] * (n_stages - 1),
            conv_bias=True,
            norm_op=get_matching_instancenorm(convert_dim_to_conv_op(3)),
            norm_op_kwargs={"eps": 1e-5, "affine": True},
            dropout_op=None,
            nonlin=nn.LeakyReLU,
            nonlin_kwargs={"inplace": True},
            deep_supervision=False,
        )
        return GenericMultiTaskWrapper(backbone)
    elif architecture == "timesformer":
        from vesuvius_model import VesuviusTimeSformer
        return VesuviusTimeSformer(v_config)
    elif architecture == "resnet3d_decoder":
        from vesuvius_model import VesuviusResNet3DDecoder
        return VesuviusResNet3DDecoder(v_config)
    return InkDetectorOptimized(v_config)

def get_weight_window(patch_size, device):
    """Generates a 2D Hanning window for soft-tiling."""
    h = torch.hann_window(patch_size, periodic=False).to(device)
    window = h.unsqueeze(1) * h.unsqueeze(0)
    return window

def save_vc3d_zarr(base_path, array_uint8, name="prediction", voxel_size_um=7.91, source_uri=None, origin_xyz=None):
    """Saves a 2D uint8 array as a VC3D-compatible OME-Zarr volume."""
    import zarr
    import uuid
    import json
    import os
    
    os.makedirs(base_path, exist_ok=True)
    
    # Create Zarr group/array at scale '0'
    z = zarr.open(os.path.join(base_path, "0"), mode='w', shape=(1, *array_uint8.shape), chunks=(1, 256, 256), dtype='|u1')
    z[0] = array_uint8

    zattrs = {
        "multiscales": [
            {
                "name": name,
                "axes": [
                    {"name": "z", "type": "space", "unit": "micrometer"},
                    {"name": "y", "type": "space", "unit": "micrometer"},
                    {"name": "x", "type": "space", "unit": "micrometer"},
                ],
                "datasets": [
                    {
                        "path": "0",
                        "coordinateTransformations": [
                            {
                                "type": "scale",
                                "scale": [float(voxel_size_um), float(voxel_size_um), float(voxel_size_um)],
                            },
                            {
                                "type": "translation",
                                "translation": [float(v) for v in (origin_xyz or [0, 0, 0])],
                            },
                        ],
                    }
                ],
                "version": "0.4",
            }
        ]
    }
    with open(os.path.join(base_path, ".zattrs"), "w") as f:
        json.dump(zattrs, f, indent=2)
    
    # Create VC3D meta.json
    meta = {
        "height": array_uint8.shape[0],
        "max": 255.0,
        "min": 0.0,
        "name": name,
        "slices": 1,
        "type": "vol",
        "uuid": str(uuid.uuid4()),
        "voxelsize": float(voxel_size_um),
        "width": array_uint8.shape[1],
        "format": "zarr",
        "source_uri": source_uri,
        "origin_xyz": origin_xyz,
    }
    with open(os.path.join(base_path, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

def write_prediction_metadata(path, args, config_dict, zarr_path, output_img, ink_stats, fiber_zarr_path=None, fiber_stats=None):
    voxel_size_um = float(config_dict.get("voxel_size_um", config_dict.get("voxelsize", args.voxel_size_um)))
    patch_size = int(config_dict.get("patch_size", args.patch_size))
    metadata = {
        "scroll_id": config_dict.get("scroll_id", "unknown"),
        "source_uri": args.uri,
        "segmentation_id": config_dict.get("segmentation_id"),
        "position_xyz": [int(args.x), int(args.y), int(args.z)],
        "x": int(args.x),
        "y": int(args.y),
        "z": int(args.z),
        "width_px": int(args.width if args.width else patch_size),
        "height_px": int(args.height if args.height else patch_size),
        "patch_size": patch_size,
        "ml_window_px": patch_size,
        "voxel_size_um": voxel_size_um,
        "ml_window_mm": patch_size * voxel_size_um / 1000.0,
        "scale_bar_cm": True,
        "vc3d_zarr_path": zarr_path,
        "fiber_vc3d_zarr_path": fiber_zarr_path,
        "output_image_path": output_img,
        "model_config": config_dict,
        "ink_stats": ink_stats,
        "fiber_stats": fiber_stats or {},
    }
    with open(path, "w") as f:
        json.dump(metadata, f, indent=2)

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
    parser.add_argument("--use_ridges", action="store_true", help="Use 3D Ridge/Frangi feature channel")
    parser.add_argument("--output_img", type=str, default=None, help="Force output image path")
    parser.add_argument("--metadata_out", type=str, default=None, help="Force prediction metadata JSON path")
    parser.add_argument("--voxel_size_um", type=float, default=7.91)
    parser.add_argument("--checkpoint", type=str, default="best_model.pt", help="Model checkpoint to use for prediction")
    parser.add_argument("--skip_active_learning", action="store_true", help="Skip optional proofreader uncertainty export")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading volume from {args.uri}...")

    # Load trained model first to get the correct hyperparameters
    checkpoint_path = args.checkpoint
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Trained model not found at {checkpoint_path}. Please run training first.")
        
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    config_dict = checkpoint.get('config', {})
    
    # Reconstruct VesuviusConfig from checkpoint, overriding args if present
    patch_size = config_dict.get('patch_size', args.patch_size)
    num_layers = config_dict.get('num_layers', args.num_layers)
    base_feat = config_dict.get('base_feat', args.base_feat)
    num_blocks = config_dict.get('num_blocks', 16)
    num_heads = config_dict.get('num_heads', 8)
    dropout = config_dict.get('dropout', 0.0)
    use_ridges = config_dict.get('use_ridges', args.use_ridges)
    
    v_config = VesuviusConfig(
        patch_size=patch_size, 
        num_layers=num_layers, 
        base_feat=base_feat,
        num_blocks=num_blocks,
        num_heads=num_heads,
        dropout=dropout,
        in_channels=2 if use_ridges else 1
    )
    
    # Initialize Ensemble
    checkpoint_paths = [checkpoint_path]
    ensemble_models = []
    
    for path in checkpoint_paths:
        checkpoint = torch.load(path, map_location=device, weights_only=False)
        config_dict = checkpoint.get('config', {})
        model = build_prediction_model(config_dict, args, use_ridges).to(device)
        skipped = load_compatible_state_dict(model, checkpoint['model_state_dict'])
        if len(skipped) > 8:
            raise RuntimeError(f"checkpoint/model mismatch: skipped {len(skipped)} tensors")
        model.eval()
        ensemble_models.append(model)
    
    model = SwarmVoter(ensemble_models)
    model.eval()

    # Open the dataset
    dataset = FastVesuviusVolume(args.uri, use_ridges=use_ridges)
    
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
            x = dataset.normalize(block).unsqueeze(0).to(device) # [B, C, Z, H, W]
            if not use_ridges:
                x = x.unsqueeze(1) # [B, 1, Z, H, W]

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

    base_name = f"pred_{args.z}_{args.y}_{args.x}_{predict_width}x{predict_height}"
    out_path = args.output_img if args.output_img else f"predictions/{base_name}.png"
    output_dir = os.path.dirname(out_path) or "predictions"
    os.makedirs(output_dir, exist_ok=True)
    np.save(os.path.join(output_dir, f"{base_name}_ink.npy"), prob_ink_final)
    np.save(os.path.join(output_dir, f"{base_name}_fiber.npy"), prob_fiber_final)

    # Save as Crackle-Viewer compatible PNG (8-bit grayscale)
    from PIL import Image
    ink_uint8 = (np.clip(prob_ink_final, 0, 1) * 255).astype(np.uint8)
    fiber_uint8 = (np.clip(prob_fiber_final, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(ink_uint8).save(os.path.join(output_dir, f"{base_name}_ink.png"))
    Image.fromarray(fiber_uint8).save(os.path.join(output_dir, f"{base_name}_fiber.png"))
    # Save as VC3D OME-Zarr
    zarr_path = os.path.join(output_dir, f"{base_name}_ink.zarr")
    save_vc3d_zarr(
        zarr_path,
        ink_uint8,
        name=f"Ink Prediction {base_name}",
        voxel_size_um=args.voxel_size_um,
        source_uri=args.uri,
        origin_xyz=[int(args.x), int(args.y), int(args.z)],
    )
    fiber_zarr_path = os.path.join(output_dir, f"{base_name}_fiber.zarr")
    save_vc3d_zarr(
        fiber_zarr_path,
        fiber_uint8,
        name=f"Fiber Prediction {base_name}",
        voxel_size_um=args.voxel_size_um,
        source_uri=args.uri,
        origin_xyz=[int(args.x), int(args.y), int(args.z)],
    )

    # Active Learning: optional proofreader export. Prize evidence generation
    # should not fail if this auxiliary tool is not available.
    if not args.skip_active_learning:
        try:
            from scripts.active_learning_sampler import identify_uncertain_patches, export_for_proofreader
            uncertain_mask = identify_uncertain_patches(full_prob_ink, threshold=0.2)
            if uncertain_mask.sum() > 0:
                export_for_proofreader(uncertain_mask.unsqueeze(0), os.path.join(output_dir, f"{base_name}_uncertain"))
        except ImportError as exc:
            print(f"Warning: skipping active-learning export: {exc}")

    # Generate Visualization (using center CT slice of the whole region)
    # ...

    # Note: For very large regions, we'd need to fetch the CT slice in parts too.
    # For now, we fetch the middle slice of the entire requested area.
    z_mid = args.z + num_layers // 2
    ct_full = dataset[z_mid : z_mid + 1, args.y : args.y + predict_height, args.x : args.x + predict_width]
    ct_slice = np.array(ct_full[0], dtype=np.float32)

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
    plt.savefig(out_path)
    plt.close()

    metadata_path = args.metadata_out if args.metadata_out else f"predictions/{base_name}_meta.json"
    write_prediction_metadata(
        metadata_path,
        args,
        config_dict,
        zarr_path,
        out_path,
        {
            "mean": float(prob_ink_final.mean()),
            "std": float(prob_ink_final.std()),
            "max": float(prob_ink_final.max()),
        },
        fiber_zarr_path=fiber_zarr_path,
        fiber_stats={
            "mean": float(prob_fiber_final.mean()),
            "std": float(prob_fiber_final.std()),
            "max": float(prob_fiber_final.max()),
        },
    )

    print(f"\nPrediction Complete!")
    print(f"Region: {predict_width}x{predict_height} at Z={args.z}, Y={args.y}, X={args.x}")
    print(f"Visualization saved to {out_path}")
    print(f"Metadata saved to {metadata_path}")

if __name__ == "__main__":
    predict()
