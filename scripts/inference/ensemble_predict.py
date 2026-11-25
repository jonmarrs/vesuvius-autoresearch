"""Regional CT prediction by averaging compatible models' probabilities.

Usage: uv run python -m scripts.inference.ensemble_predict --uri local.zarr \
    --z 0 --y 0 --x 0 --checkpoints best_model.pt other_model.pt

Ensembling does not guarantee the absence of hallucinations or establish accuracy.
"""

import os
import sys
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory

# "src" too: the shared .venv's editable install may point at another checkout.
if not __package__:
    root = Path(__file__).resolve().parents[2]
    sys.path[:0] = [str(root), str(root / "src")]

import numpy as np
import torch
from matplotlib.patches import Rectangle
from tap import Tap

from scripts.inference.predict import (
    get_weight_window,
    invalidate_prediction_metadata,
    prediction_scale_bar,
    regional_preview_figure,
    stage_prediction_metadata,
    stage_regional_outputs,
)
from scripts.regional_prediction_artifacts import (
    RegionalArtifactPlan,
    validate_checkpoint_metadata,
)
from vesuvius_autoresearch.core.checkpoint_refusal import require_zip_checkpoint
from vesuvius_autoresearch.core.checkpoint_tools import load_checkpoint
from vesuvius_autoresearch.core.inference import (
    blend_coverage_fraction,
    multitask_inference_recipe,
    multitask_probabilities,
    normalize_blend,
    positive_number,
    prepare_volume_input,
    read_model_block,
    region_tiles,
    ridge_depth_context,
    validate_model_settings,
    validate_region,
)
from vesuvius_autoresearch.core.model_wrappers import build_inference_model, task_heads
from vesuvius_autoresearch.core.prediction_artifacts import prediction_stem
from vesuvius_autoresearch.core.regional_memory import RegionalMemoryProfile
from vesuvius_autoresearch.core.regional_resources import (
    MAX_ACCUMULATOR_BYTES,
    plan_regional_accumulators,
)
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
    artifact_stem: str | None = None  # Shared basename for arrays, previews and exports
    voxel_size_um: float = 7.91
    disable_tta: bool = False
    num_parts: int = 1
    part_id: int = 0
    gaussian_blend: bool = True
    max_accumulator_bytes: int = MAX_ACCUMULATOR_BYTES  # Byte cap for the three float32 blend planes; not peak RAM/VRAM
    profile_memory: bool = False  # Record process RSS and selected-device PyTorch allocator peaks in metadata

    def configure(self):
        self.add_argument("--gaussian_blend", action="store_true", default=True)
        self.add_argument(
            "--no-gaussian_blend",
            dest="gaussian_blend",
            action="store_false",
            default=True,
            help="Use positive Hann blending instead of Gaussian blending",
        )


def _plan_region(args, patch_size, layers, checkpoint_paths):
    args.resource_plan = plan_regional_accumulators(
        patch_size if args.width is None else args.width,
        patch_size if args.height is None else args.height,
        args.max_accumulator_bytes,
    )
    validate_region(args, patch_size, layers)
    base = prediction_stem(
        f"ensemble_pred_{args.z}_{args.y}_{args.x}_{args.width}x{args.height}",
        args.artifact_stem,
    )
    if args.num_parts > 1:
        base += f"_part{args.part_id}of{args.num_parts}"
    return RegionalArtifactPlan.create(
        base,
        args.output_img or f"predictions/{base}.png",
        args.metadata_out,
        args.uri,
        [*checkpoint_paths, *args.checkpoints],
    )


def ensemble_predict():
    args = EnsembleArgs().parse_args()
    prediction_stem("unused", getattr(args, "artifact_stem", None))
    args.inference_recipe = multitask_inference_recipe(
        args.disable_tta, args.gaussian_blend
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if not args.checkpoints:
        raise ValueError("at least one checkpoint is required")

    checkpoint_paths = []
    for requested_path in args.checkpoints:
        if not os.path.isfile(requested_path):
            raise FileNotFoundError(
                f"requested ensemble checkpoint not found: {requested_path}"
            )
        # Check the original path spelling before resolving aliases.
        require_zip_checkpoint(requested_path)
        checkpoint_paths.append(Path(requested_path).resolve())

    models, configs = [], []
    memory_profile = None
    patch_size, voxel_size_um = args.patch_size, args.voxel_size_um
    ridge_settings: tuple[float, int] | None = None
    max_layers = 0
    for checkpoint_path in checkpoint_paths:
        # The loader checks the signature and reads weights on this same handle.
        with checkpoint_path.open("rb") as handle:
            checkpoint = load_checkpoint(
                handle,
                map_location="cpu",
                weights_only=True,
                allow_numpy_scalars=True,
            )
        if not isinstance(checkpoint, dict) or not isinstance(
            checkpoint.get("config", {}), dict
        ):
            raise ValueError("checkpoint config must be an object")
        config = checkpoint.get("config", {})
        validate_checkpoint_metadata(config)
        member_patch_size = config.get("patch_size", args.patch_size)
        layers = config.get("num_layers", 16)
        base_feat = config.get("base_feat", 64)
        ridge_sigma = validate_model_settings(
            config, member_patch_size, layers, base_feat
        )
        scale = positive_number(
            config.get("voxel_size_um", config.get("voxelsize", args.voxel_size_um)),
            "voxel_size_um",
        )
        use_ridges = config.get("use_ridges", False)
        if models:
            if member_patch_size != patch_size:
                raise ValueError("ensemble checkpoint patch_size must match")
            if scale != voxel_size_um:
                raise ValueError("ensemble checkpoint voxel_size_um must match")
        else:
            patch_size, voxel_size_um = member_patch_size, scale
            artifacts = _plan_region(args, patch_size, layers, checkpoint_paths)
            tiles = region_tiles(args, patch_size)
        max_layers = max(max_layers, layers)
        if use_ridges:
            if ridge_settings is not None and ridge_sigma != ridge_settings[0]:
                raise ValueError(
                    "ensemble ridge_sigma must match for ridge-enabled models"
                )
            ridge_settings = ridge_settings or (ridge_sigma, layers)
        if ridge_settings is not None and (
            ridge_settings[1] != max_layers or (use_ridges and layers != max_layers)
        ):
            raise ValueError(
                "ridge-enabled ensemble num_layers must match the maximum depth; ridge filtering depends on the full depth context"
            )
        if args.profile_memory and memory_profile is None:
            memory_profile = RegionalMemoryProfile(device)
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
        )
        model.load_state_dict(checkpoint["model_state_dict"], strict=True)
        del checkpoint
        models.append((model.to(device).eval(), use_ridges, layers))
        configs.append(config)

    # A member without a fiber head returns its ink logits as "fiber"; the
    # ensemble's fiber is exported only when every member has one. Asked before
    # inference, so a member that declares no heads fails before the volume is read.
    member_heads = [sorted(task_heads(member[0])) for member in models]
    has_fiber = all("fiber" in heads for heads in member_heads)
    use_ridges_any = ridge_settings is not None
    if memory_profile is not None:
        memory_profile.sample("models_loaded")
    args.inference_recipe["ridge_depth_context"] = ridge_depth_context(use_ridges_any)
    args.patch_size = patch_size
    args.voxel_size_um = voxel_size_um
    artifacts.validate_source_selection(args.uri)
    base = artifacts.stem
    output_img, output_dir = str(artifacts.image), str(artifacts.directory)
    dataset = FastVesuviusVolume(
        str(artifacts.source_array),
        use_ridges=use_ridges_any,
        ridge_sigma=ridge_settings[0] if ridge_settings is not None else 2.0,
        strict_reads=True,
    )
    if dataset.vol.path != artifacts.source_array:
        raise RuntimeError("CT source selection changed while opening the ensemble volume")
    validate_region(args, patch_size, max_layers, dataset.shape)
    full_ink = torch.zeros(
        (args.height, args.width), device=device, dtype=torch.float32
    )
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
            block = read_model_block(
                dataset, args.z, args.y + y, args.x + x, max_layers, patch_size
            )
            batch = prepare_volume_input(
                dataset.normalize(block), use_ridges_any, max_layers, patch_size, device
            )
            ink_sum, fiber_sum = torch.zeros_like(window), torch.zeros_like(window)
            for model, use_ridges, layers in models:
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

    complete = args.num_parts == 1
    ink = normalize_blend(full_ink, weights, complete).cpu().numpy()
    fiber = normalize_blend(full_fiber, weights, complete).cpu().numpy()
    args.coverage_fraction = blend_coverage_fraction(weights, complete=complete)
    if memory_profile is not None:
        memory_profile.sample("inference_complete")

    # The full preview can reach damaged chunks outside this shard's tiles.
    z_mid = args.z + max_layers // 2
    ct_slice = dataset.read_ct(z_mid, args.y, args.x, 1, args.height, args.width)[0]
    with TemporaryDirectory(prefix="regional-preview-") as directory:
        staging = Path(directory)
        with regional_preview_figure() as (figure, axes):
            axes[0].imshow(ct_slice, cmap="gray")
            axes[0].set_title(f"CT Slice (Z={z_mid})")
            if has_fiber:
                axes[1].imshow(fiber, cmap="magma")
                axes[1].set_title("Ensemble Fiber Context")
            else:
                axes[1].imshow(np.zeros_like(ink), cmap="gray", vmin=0, vmax=1)
                axes[1].set_title("No fiber head in every member")
            axes[2].imshow(ct_slice, cmap="gray")
            axes[2].imshow(ink, cmap="jet", alpha=0.5)
            axes[2].set_title("Ensemble Ink Overlay")
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
            figure.savefig(
                str(staging / artifacts.image.name), format=artifacts.image_format
            )
        preview_files = artifacts.preview_files(staging)
        artifacts.validate_source_selection(args.uri)
        artifacts.validate(
            checkpoint_aliases=args.checkpoints, preview_paths=preview_files
        )
        outputs = {"ink": (ink, "Ensemble ink")}
        if has_fiber:
            outputs["fiber"] = (fiber, "Ensemble fiber")
        if args.num_parts > 1:
            args.blend_weight_path = os.path.join(output_dir, f"{base}_weight.npy")
        with (
            ExitStack() as pending_metadata,
            stage_regional_outputs(
                artifacts,
                outputs,
                preview_files,
                blend_weights=weights.cpu().numpy() if args.num_parts > 1 else None,
                voxel_size_um=args.voxel_size_um,
                source_uri=args.uri,
                origin_xyz=[args.x, args.y, args.z],
            ) as exports,
        ):
            pending_metadata.enter_context(
                stage_prediction_metadata(
                    artifacts.metadata,
                    args,
                    configs[0],
                    exports["ink"],
                    output_img,
                    {
                        "mean": float(ink.mean()),
                        "std": float(ink.std()),
                        "max": float(ink.max()),
                    },
                    fiber_zarr_path=exports.get("fiber"),
                    fiber_stats={
                        "mean": float(fiber.mean()),
                        "std": float(fiber.std()),
                        "max": float(fiber.max()),
                    }
                    if has_fiber
                    else None,
                    extra_metadata={
                        "ensemble_checkpoints": [
                            str(path) for path in checkpoint_paths
                        ],
                        "ensemble_model_configs": configs,
                        "ensemble_max_layers": max_layers,
                        "model_config_scope": "first_ensemble_member",
                        "ensemble_task_heads": member_heads,
                    },
                    memory_profile=memory_profile,
                )
            )
            artifacts.validate_source_selection(args.uri)
            artifacts.validate(
                checkpoint_aliases=args.checkpoints, preview_paths=preview_files
            )
            metadata_path = invalidate_prediction_metadata(
                output_dir, base, str(artifacts.metadata)
            )

    print(
        f"Ensemble prediction {'complete' if args.num_parts == 1 else 'shard complete (partial region)'}. Metadata: {metadata_path}"
    )


if __name__ == "__main__":
    ensemble_predict()
