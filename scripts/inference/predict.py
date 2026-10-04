"""
Vesuvius Prediction Script.
Performs inference on a specific block of a Vesuvius scroll volume.
Usage: uv run python -m scripts.inference.predict --uri "s3://..." --z 1000 --y 2000 --x 3000
"""

import json
import os
import sys
from pathlib import Path

# Direct launchers are also used from evidence directories outside the checkout.
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import matplotlib.pyplot as plt
import numpy as np
import torch
from matplotlib.patches import Rectangle
from tap import Tap

from vesuvius_autoresearch.core.inference import (
    hann2d,
    multitask_inference_recipe,
    multitask_probabilities,
    normalize_blend,
    positive_number,
    prepare_volume_input,
    region_tiles,
    validate_model_settings,
    validate_region,
)
from vesuvius_autoresearch.core.model_wrappers import build_inference_model
from vesuvius_autoresearch.core.vesuvius_loader import FastVesuviusVolume


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
        print(
            f"Warning: skipped {len(skipped)} incompatible checkpoint tensors: {', '.join(skipped[:8])}"
        )
    return skipped


def build_prediction_model(config_dict, args, use_ridges):
    """Build a model for prediction from a checkpoint's config dict.

    Thin wrapper around model_wrappers.build_inference_model that pulls
    fallback defaults from the CLI args.
    """
    return build_inference_model(
        architecture=config_dict.get("architecture", "gated_unet"),
        patch_size=config_dict.get("patch_size", args.patch_size),
        num_layers=config_dict.get("num_layers", args.num_layers),
        base_feat=config_dict.get("base_feat", args.base_feat),
        num_blocks=config_dict.get("num_blocks", 16),
        num_heads=config_dict.get("num_heads", 8),
        dropout=config_dict.get("dropout", 0.0),
        use_ridges=use_ridges,
        multi_task_heads=config_dict.get("multi_task_heads", False),
    )


def get_weight_window(patch_size, device):
    """Positive Hanning weights, including the requested region's outer edges."""
    return hann2d(patch_size, patch_size, device)


def prediction_scale_bar(width, voxel_size_um):
    """Return a physical bar that fits in the source image, with its label."""
    for length_um, label in (
        (10000, "1 cm"),
        (1000, "1 mm"),
        (100, "100 µm"),
        (10, "10 µm"),
        (1, "1 µm"),
    ):
        pixels = length_um / voxel_size_um
        if pixels <= width * 0.8:
            return pixels, label
    return width * 0.5, f"{width * 0.5 * voxel_size_um:g} µm"


def save_vc3d_zarr(
    base_path,
    array_uint8,
    name="prediction",
    voxel_size_um=7.91,
    source_uri=None,
    origin_xyz=None,
):
    """Save a 2D uint8 array; origin_xyz is a position in source voxel indices.

    OME axes are z/y/x and their units are micrometers, so translation reverses
    the caller's x/y/z order and converts indices to physical coordinates.
    """
    import json
    import os
    import uuid

    import zarr

    os.makedirs(base_path, exist_ok=True)

    # A resolution array plus .zattrs is not a Zarr group without .zgroup.
    zarr.open_group(str(base_path), mode="a")
    # Create Zarr group/array at scale '0'
    z = zarr.open(
        os.path.join(base_path, "0"),
        mode="w",
        shape=(1, *array_uint8.shape),
        chunks=(1, 256, 256),
        dtype="|u1",
    )
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
                                "scale": [
                                    float(voxel_size_um),
                                    float(voxel_size_um),
                                    float(voxel_size_um),
                                ],
                            },
                            {
                                "type": "translation",
                                "translation": [
                                    float(v) * float(voxel_size_um)
                                    for v in reversed(
                                        origin_xyz
                                        if origin_xyz is not None
                                        else [0, 0, 0]
                                    )
                                ],
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


def write_prediction_metadata(
    path,
    args,
    config_dict,
    zarr_path,
    output_img,
    ink_stats,
    fiber_zarr_path=None,
    fiber_stats=None,
    fiber_coherence=None,
    extra_metadata=None,
):
    voxel_size_um = float(
        config_dict.get(
            "voxel_size_um", config_dict.get("voxelsize", args.voxel_size_um)
        )
    )
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
        "scale_bar_cm": bool(output_img)
        and prediction_scale_bar(args.width or patch_size, voxel_size_um)[1] == "1 cm",
        "vc3d_zarr_path": str(Path(zarr_path).resolve()),
        "fiber_vc3d_zarr_path": str(Path(fiber_zarr_path).resolve())
        if fiber_zarr_path
        else None,
        "output_image_path": str(Path(output_img).resolve()) if output_img else None,
        "model_config": config_dict,
        "checkpoint_path": str(Path(args.checkpoint).resolve())
        if getattr(args, "checkpoint", None)
        else None,
        "inference_recipe": getattr(args, "inference_recipe", None),
        "ink_stats": ink_stats,
        "fiber_stats": fiber_stats or {},
        "fiber_coherence": fiber_coherence,
        "num_parts": getattr(args, "num_parts", 1),
        "part_id": getattr(args, "part_id", 0),
        "prediction_complete": getattr(args, "num_parts", 1) == 1,
        "coverage_fraction": getattr(args, "coverage_fraction", 1.0),
        "tiles_total": getattr(args, "tiles_total", None),
        "tiles_processed": getattr(args, "tiles_processed", None),
        "blend_weight_path": str(Path(args.blend_weight_path).resolve())
        if getattr(args, "blend_weight_path", None)
        else None,
    }
    if extra_metadata:
        if metadata.keys() & extra_metadata.keys():
            raise ValueError("extra metadata must not overwrite prediction facts")
        metadata.update(extra_metadata)
    encoded = json.dumps(metadata, indent=2, allow_nan=False)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(encoded + "\n")


class PredictionArgs(Tap):
    uri: str  # S3 or local path to Zarr volume
    z: int
    y: int
    x: int
    width: int | None = None  # Total width to predict
    height: int | None = None  # Total height to predict
    stride: int | None = None  # Stride for soft-tiling
    patch_size: int = 32
    num_layers: int = 16
    base_feat: int = 128
    use_ridges: bool = False  # Use 3D Ridge/Frangi feature channel
    output_img: str | None = None  # Force output image path
    metadata_out: str | None = None  # Force prediction metadata JSON path
    voxel_size_um: float = 7.91
    checkpoint: str = "best_model.pt"  # Model checkpoint to use for prediction
    num_parts: int = 1
    part_id: int = 0
    disable_tta: bool = False
    skip_active_learning: bool = False  # Skip optional proofreader uncertainty export
    compute_coherence: bool = (
        False  # Enable automated fiber coherence evaluation (Villa ST)
    )
    gaussian_blend: bool = True  # Use Gaussian blending instead of Hanning window

    def configure(self):
        self.add_argument("--gaussian_blend", action="store_true", default=True)
        self.add_argument(
            "--no-gaussian_blend",
            dest="gaussian_blend",
            action="store_false",
            default=True,
            help="Use positive Hann blending instead of Gaussian blending",
        )


def predict():
    args = PredictionArgs().parse_args()
    args.inference_recipe = multitask_inference_recipe(
        args.disable_tta, args.gaussian_blend
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading volume from {args.uri}...")

    # Load trained model first to get the correct hyperparameters
    checkpoint_path = args.checkpoint
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(
            f"Trained model not found at {checkpoint_path}. Please run training first."
        )

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    if not isinstance(checkpoint, dict) or not isinstance(
        checkpoint.get("config", {}), dict
    ):
        raise ValueError("checkpoint and checkpoint config must be objects")
    config_dict = checkpoint.get("config", {})
    args.voxel_size_um = positive_number(
        config_dict.get(
            "voxel_size_um", config_dict.get("voxelsize", args.voxel_size_um)
        ),
        "voxel_size_um",
    )

    # Reconstruct VesuviusConfig from checkpoint, overriding args if present
    patch_size = config_dict.get("patch_size", args.patch_size)
    num_layers = config_dict.get("num_layers", args.num_layers)
    base_feat = config_dict.get("base_feat", args.base_feat)
    use_ridges = config_dict.get("use_ridges", args.use_ridges)
    ridge_sigma = validate_model_settings(
        config_dict, patch_size, num_layers, base_feat
    )
    if not isinstance(use_ridges, bool):
        raise ValueError("use_ridges must be a boolean")
    validate_region(args, patch_size, num_layers)
    model = build_prediction_model(config_dict, args, use_ridges).to(device)
    # Partial warm starts are appropriate for training, not evidence export.
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    model.eval()

    # Open the dataset
    dataset = FastVesuviusVolume(
        args.uri, use_ridges=use_ridges, ridge_sigma=ridge_sigma
    )
    validate_region(args, patch_size, num_layers, dataset.shape)

    # Determine region and tiling parameters
    predict_width, predict_height, stride = args.width, args.height, args.stride

    # Initialize accumulation buffers
    full_prob_ink = torch.zeros((predict_height, predict_width), device=device)
    full_prob_fiber = torch.zeros((predict_height, predict_width), device=device)
    full_weight = torch.zeros((predict_height, predict_width), device=device)

    # Choose weight window: Gaussian (smoother) or Hanning (default)
    if args.gaussian_blend:
        from vesuvius_autoresearch.core.villa_inference import GaussianBlender

        print("Using Gaussian blending window...")
        _blender = GaussianBlender(patch_size)
        weight_window = _blender.get_weight_window(device)
    else:
        weight_window = get_weight_window(patch_size, device)

    print(
        f"Starting Soft-Tiling Inference: {predict_width}x{predict_height} (stride={stride})..."
    )

    # Tiling Loop Setup
    my_chunks = region_tiles(args, patch_size)

    if args.num_parts > 1:
        print(
            f"Distributed Inference: processing part {args.part_id}/{args.num_parts} ({len(my_chunks)}/{args.tiles_total} chunks)"
        )

    for y_off, x_off in my_chunks:
        curr_y = args.y + y_off
        curr_x = args.x + x_off

        # Read the block
        block = dataset[
            args.z : args.z + num_layers,
            curr_y : curr_y + patch_size,
            curr_x : curr_x + patch_size,
        ]

        # Prepare input
        x = prepare_volume_input(
            dataset.normalize(block), use_ridges, num_layers, patch_size, device
        )

        with torch.no_grad():
            ink_batch, fiber_batch = multitask_probabilities(model, x, args.disable_tta)
            prob_ink, prob_fiber = ink_batch[0], fiber_batch[0]

            # Accumulate with weight window
            full_prob_ink[y_off : y_off + patch_size, x_off : x_off + patch_size] += (
                prob_ink * weight_window
            )
            full_prob_fiber[y_off : y_off + patch_size, x_off : x_off + patch_size] += (
                prob_fiber * weight_window
            )
            full_weight[y_off : y_off + patch_size, x_off : x_off + patch_size] += (
                weight_window
            )

    # Normalize by weights
    full_prob_ink = normalize_blend(full_prob_ink, full_weight, args.num_parts == 1)
    full_prob_fiber = normalize_blend(full_prob_fiber, full_weight, args.num_parts == 1)
    args.coverage_fraction = int((full_weight > 0).sum().item()) / full_weight.numel()

    prob_ink_final = full_prob_ink.cpu().numpy()
    prob_fiber_final = full_prob_fiber.cpu().numpy()

    base_name = f"pred_{args.z}_{args.y}_{args.x}_{predict_width}x{predict_height}"
    if args.num_parts > 1:
        base_name += f"_part{args.part_id}of{args.num_parts}"
    out_path = args.output_img if args.output_img else f"predictions/{base_name}.png"
    output_dir = os.path.dirname(out_path) or "."
    os.makedirs(output_dir, exist_ok=True)
    np.save(os.path.join(output_dir, f"{base_name}_ink.npy"), prob_ink_final)
    np.save(os.path.join(output_dir, f"{base_name}_fiber.npy"), prob_fiber_final)
    if args.num_parts > 1:
        args.blend_weight_path = os.path.join(output_dir, f"{base_name}_weight.npy")
        np.save(args.blend_weight_path, full_weight.cpu().numpy())

    # Save as Crackle-Viewer compatible PNG (8-bit grayscale)
    from PIL import Image

    ink_uint8 = (np.clip(prob_ink_final, 0, 1) * 255).astype(np.uint8)
    fiber_uint8 = (np.clip(prob_fiber_final, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(ink_uint8).save(os.path.join(output_dir, f"{base_name}_ink.png"))
    Image.fromarray(fiber_uint8).save(
        os.path.join(output_dir, f"{base_name}_fiber.png")
    )
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
            from scripts.active_learning_sampler import (
                export_for_proofreader,
                identify_uncertain_patches,
            )

            uncertain_mask = identify_uncertain_patches(full_prob_ink, threshold=0.2)
            if uncertain_mask.sum() > 0:
                export_for_proofreader(
                    uncertain_mask.unsqueeze(0),
                    os.path.join(output_dir, f"{base_name}_uncertain"),
                )
        except ImportError as exc:
            print(f"Warning: skipping active-learning export: {exc}")

    # Generate Visualization (using center CT slice of the whole region)
    # ...

    # Note: For very large regions, we'd need to fetch the CT slice in parts too.
    # For now, we fetch the middle slice of the entire requested area.
    z_mid = args.z + num_layers // 2
    ct_full = dataset[
        z_mid : z_mid + 1,
        args.y : args.y + predict_height,
        args.x : args.x + predict_width,
    ]
    # FastVesuviusVolume returns (D, H, W) for use_ridges=False or
    # (C, D, H, W) for use_ridges=True. The visualization wants a 2D
    # (H, W) CT slice. Drop the channel dim if present (taking the CT
    # channel at index 0), then drop the singleton z dim.
    if (
        hasattr(ct_full, "dim")
        and ct_full.dim() == 4
        or hasattr(ct_full, "ndim")
        and ct_full.ndim == 4
    ):
        ct_full = ct_full[0]
    ct_slice = ct_full[0].detach().cpu().numpy().astype(np.float32, copy=False)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes[0].imshow(ct_slice, cmap="gray")
    axes[0].set_title(f"CT Slice (Z={args.z + num_layers // 2})")

    axes[1].imshow(prob_fiber_final, cmap="magma")
    axes[1].set_title("Fiber Context (Fused)")

    axes[2].imshow(ct_slice, cmap="gray")
    axes[2].imshow(prob_ink_final, cmap="jet", alpha=0.5)
    axes[2].set_title("Gated Ink Overlay (Soft-Tiled)")

    # Add Scale Bar — uses args.voxel_size_um (same source as the OME-Zarr
    # metadata + per-axis scale) to avoid the previous ~1.1% scale-bar
    # miscalibration (was hardcoded to 8.0 µm despite the rest of the file
    # using 7.91 µm). Reviewers eyeball the PNG scale bar when judging prize
    # submissions; the bar's label needs to match the voxel-size declared in
    # the OME-Zarr metadata that ships alongside the PNG.
    pixel_size_um = args.voxel_size_um
    bar_px, bar_label = prediction_scale_bar(predict_width, pixel_size_um)

    for ax in axes:
        rect = Rectangle(
            (predict_width * 0.1, predict_height * 0.85),
            bar_px,
            max(0.5, predict_height * 0.02),
            facecolor="white",
            edgecolor="black",
        )
        ax.add_patch(rect)
        ax.text(
            predict_width * 0.1,
            predict_height * 0.75,
            bar_label,
            color="white",
            fontsize=10,
            fontweight="bold",
        )
        ax.axis("off")

    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()

    metadata_path = (
        args.metadata_out
        if args.metadata_out
        else os.path.join(output_dir, f"{base_name}_meta.json")
    )
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

    # Automated Fiber Coherence Evaluation (Villa ST)
    fiber_coherence = None
    if args.compute_coherence:
        try:
            from scripts.compute_fiber_coherence import compute_coherence

            print("Computing Fiber Coherence score (Villa ST)...", flush=True)
            # Fetch raw volume data for ST computation (center region)
            # Using the same data as for prediction visualization for consistency
            fiber_coherence = compute_coherence(ct_slice, device=str(device))
            print(f"Fiber Coherence Score: {fiber_coherence:.6f}")

            # Re-write metadata with coherence score
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
                fiber_coherence=fiber_coherence,
            )
        except Exception as exc:
            print(f"Warning: fiber coherence evaluation failed: {exc}")

    print(
        "\nPrediction complete."
        if args.num_parts == 1
        else "\nPartial prediction shard complete."
    )
    print(
        f"Region: {predict_width}x{predict_height} at Z={args.z}, Y={args.y}, X={args.x}"
    )
    print(f"Visualization saved to {out_path}")
    print(f"Metadata saved to {metadata_path}")


if __name__ == "__main__":
    predict()
