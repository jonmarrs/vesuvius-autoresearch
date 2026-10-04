"""Regional CT prediction by averaging compatible models' probabilities.

Usage: uv run python -m scripts.inference.ensemble_predict --uri local.zarr \
    --z 0 --y 0 --x 0 --checkpoints best_model.pt other_model.pt

Ensembling does not guarantee the absence of hallucinations or establish accuracy.
"""

import os
import sys
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import matplotlib.pyplot as plt
import numpy as np
import torch
from matplotlib.patches import Rectangle
from PIL import Image
from tap import Tap

from scripts.inference.predict import (
    get_weight_window,
    prediction_scale_bar,
    save_vc3d_zarr,
    write_prediction_metadata,
)
from vesuvius_autoresearch.core.inference import (
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


class EnsembleArgs(Tap):
    uri: str  # Local path to the source CT Zarr volume
    z: int
    y: int
    x: int
    width: int | None = None
    height: int | None = None
    stride: int | None = None
    checkpoints: list[str]
    patch_size: int = 64
    output_img: str | None = None
    metadata_out: str | None = None
    voxel_size_um: float = 7.91
    disable_tta: bool = False
    num_parts: int = 1
    part_id: int = 0
    gaussian_blend: bool = True

    def configure(self):
        self.add_argument("--gaussian_blend", action="store_true", default=True)
        self.add_argument(
            "--no-gaussian_blend",
            dest="gaussian_blend",
            action="store_false",
            default=True,
            help="Use positive Hann blending instead of Gaussian blending",
        )


def ensemble_predict():
    args = EnsembleArgs().parse_args()
    args.inference_recipe = multitask_inference_recipe(
        args.disable_tta, args.gaussian_blend
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if not args.checkpoints:
        raise ValueError("at least one checkpoint is required")

    models, configs, scales, ridge_sigmas = [], [], [], []
    for checkpoint_path in args.checkpoints:
        if not os.path.isfile(checkpoint_path):
            raise FileNotFoundError(
                f"requested ensemble checkpoint not found: {checkpoint_path}"
            )
        checkpoint = torch.load(
            checkpoint_path, map_location=device, weights_only=False
        )
        if not isinstance(checkpoint, dict) or not isinstance(
            checkpoint.get("config", {}), dict
        ):
            raise ValueError("checkpoint config must be an object")
        config = checkpoint.get("config", {})
        patch_size = config.get("patch_size", args.patch_size)
        layers = config.get("num_layers", 16)
        base_feat = config.get("base_feat", 64)
        ridge_sigma = validate_model_settings(config, patch_size, layers, base_feat)
        scale = positive_number(
            config.get("voxel_size_um", config.get("voxelsize", args.voxel_size_um)),
            "voxel_size_um",
        )
        use_ridges = config.get("use_ridges", False)
        model = build_inference_model(
            architecture=config.get("architecture", "gated_unet"),
            patch_size=patch_size,
            num_layers=layers,
            base_feat=base_feat,
            num_blocks=config.get("num_blocks", 16),
            num_heads=config.get("num_heads", 8),
            dropout=config.get("dropout", 0.0),
            use_ridges=use_ridges,
            multi_task_heads=config.get("multi_task_heads", False),
        ).to(device)
        model.load_state_dict(checkpoint["model_state_dict"], strict=True)
        models.append((model.eval(), use_ridges, layers, patch_size))
        configs.append(config)
        scales.append(scale)
        if use_ridges:
            ridge_sigmas.append(ridge_sigma)

    # Spatial pixels from different contexts cannot be combined by slicing the
    # upper-left corner or by resizing without changing their coordinate frame.
    patch_size = models[0][3]
    if any(member[3] != patch_size for member in models):
        raise ValueError("ensemble checkpoint patch_size must match")
    if any(scale != scales[0] for scale in scales):
        raise ValueError("ensemble checkpoint voxel_size_um must match")
    if ridge_sigmas and any(sigma != ridge_sigmas[0] for sigma in ridge_sigmas):
        raise ValueError("ensemble ridge_sigma must match for ridge-enabled models")
    max_layers = max(member[2] for member in models)
    if any(ridges and layers != max_layers for _, ridges, layers, _ in models):
        raise ValueError(
            "ridge-enabled ensemble num_layers must match the maximum depth; ridge filtering depends on the full depth context"
        )
    use_ridges_any = any(member[1] for member in models)
    args.patch_size = patch_size
    args.voxel_size_um = scales[0]
    validate_region(args, patch_size, max_layers)
    dataset = FastVesuviusVolume(
        args.uri,
        use_ridges=use_ridges_any,
        ridge_sigma=ridge_sigmas[0] if ridge_sigmas else 2.0,
    )
    validate_region(args, patch_size, max_layers, dataset.shape)
    tiles = region_tiles(args, patch_size)
    full_ink = torch.zeros((args.height, args.width), device=device)
    full_fiber, weights = torch.zeros_like(full_ink), torch.zeros_like(full_ink)
    if args.gaussian_blend:
        from vesuvius_autoresearch.core.villa_inference import GaussianBlender

        window = GaussianBlender(patch_size).get_weight_window(device)
    else:
        window = get_weight_window(patch_size, device)

    print(
        f"Ensemble inference: {len(models)} models, {len(tiles)}/{args.tiles_total} tiles"
    )
    with torch.no_grad():
        for y, x in tiles:
            block = dataset[
                args.z : args.z + max_layers,
                args.y + y : args.y + y + patch_size,
                args.x + x : args.x + x + patch_size,
            ]
            batch = prepare_volume_input(
                dataset.normalize(block), use_ridges_any, max_layers, patch_size, device
            )
            ink_sum, fiber_sum = torch.zeros_like(window), torch.zeros_like(window)
            for model, use_ridges, layers, _ in models:
                model_input = batch[:, : 2 if use_ridges else 1, :layers]
                ink, fiber = multitask_probabilities(
                    model, model_input, args.disable_tta
                )
                ink_sum += ink[0]
                fiber_sum += fiber[0]
            full_ink[y : y + patch_size, x : x + patch_size] += (
                ink_sum / len(models) * window
            )
            full_fiber[y : y + patch_size, x : x + patch_size] += (
                fiber_sum / len(models) * window
            )
            weights[y : y + patch_size, x : x + patch_size] += window

    ink = normalize_blend(full_ink, weights, args.num_parts == 1).cpu().numpy()
    fiber = normalize_blend(full_fiber, weights, args.num_parts == 1).cpu().numpy()
    args.coverage_fraction = int((weights > 0).sum().item()) / weights.numel()
    base = f"ensemble_pred_{args.z}_{args.y}_{args.x}_{args.width}x{args.height}"
    if args.num_parts > 1:
        base += f"_part{args.part_id}of{args.num_parts}"
    output_img = args.output_img or f"predictions/{base}.png"
    output_dir = os.path.dirname(output_img) or "."
    os.makedirs(output_dir, exist_ok=True)
    if args.num_parts > 1:
        args.blend_weight_path = os.path.join(output_dir, f"{base}_weight.npy")
        np.save(args.blend_weight_path, weights.cpu().numpy())
    exports = []
    for name, array in (("ink", ink), ("fiber", fiber)):
        np.save(os.path.join(output_dir, f"{base}_{name}.npy"), array)
        image = (np.clip(array, 0, 1) * 255).astype(np.uint8)
        Image.fromarray(image).save(os.path.join(output_dir, f"{base}_{name}.png"))
        export = os.path.join(output_dir, f"{base}_{name}.zarr")
        save_vc3d_zarr(
            export,
            image,
            name=f"Ensemble {name}",
            voxel_size_um=args.voxel_size_um,
            source_uri=args.uri,
            origin_xyz=[args.x, args.y, args.z],
        )
        exports.append(export)

    z_mid = args.z + max_layers // 2
    ct = dataset[
        z_mid : z_mid + 1, args.y : args.y + args.height, args.x : args.x + args.width
    ]
    if ct.ndim == 4:
        ct = ct[0]
    ct_slice = ct[0].detach().cpu().numpy().astype(np.float32, copy=False)
    figure, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes[0].imshow(ct_slice, cmap="gray")
    axes[0].set_title(f"CT Slice (Z={z_mid})")
    axes[1].imshow(fiber, cmap="magma")
    axes[1].set_title("Ensemble Fiber Context")
    axes[2].imshow(ct_slice, cmap="gray")
    axes[2].imshow(ink, cmap="jet", alpha=0.5)
    axes[2].set_title("Ensemble Gated Ink Overlay")
    bar_px, label = prediction_scale_bar(args.width, args.voxel_size_um)
    for ax in axes:
        ax.add_patch(
            Rectangle(
                (args.width * 0.1, args.height * 0.85),
                bar_px,
                max(0.5, args.height * 0.02),
                facecolor="white",
                edgecolor="black",
            )
        )
        ax.text(
            args.width * 0.1,
            args.height * 0.75,
            label,
            color="white",
            fontsize=10,
            fontweight="bold",
        )
        ax.axis("off")
    figure.tight_layout()
    figure.savefig(output_img)
    plt.close(figure)
    metadata_path = args.metadata_out or os.path.join(output_dir, f"{base}_meta.json")
    write_prediction_metadata(
        metadata_path,
        args,
        configs[0],
        exports[0],
        output_img,
        {"mean": float(ink.mean()), "std": float(ink.std()), "max": float(ink.max())},
        fiber_zarr_path=exports[1],
        fiber_stats={
            "mean": float(fiber.mean()),
            "std": float(fiber.std()),
            "max": float(fiber.max()),
        },
        extra_metadata={
            "ensemble_checkpoints": [
                str(Path(path).resolve()) for path in args.checkpoints
            ],
            "ensemble_model_configs": configs,
            "ensemble_max_layers": max_layers,
            "model_config_scope": "first_ensemble_member",
        },
    )
    print(
        f"Ensemble prediction {'complete' if args.num_parts == 1 else 'shard complete (partial region)'}. Metadata: {metadata_path}"
    )


if __name__ == "__main__":
    ensemble_predict()
