"""
Vesuvius Prediction Script.
Performs inference on a specific block of a Vesuvius scroll volume.
Usage: uv run python -m scripts.inference.predict --uri local.zarr --z 1000 --y 2000 --x 3000
"""

import hashlib
import io
import json
import os
import stat
import sys
from contextlib import ExitStack, contextmanager
from pathlib import Path
from shutil import copy2, copyfile, copytree, rmtree
from tempfile import TemporaryDirectory, mkdtemp
from urllib.parse import unquote, urlsplit

# Both direct and -m launches must use this checkout's src; the shared editable
# installation may currently point at a different worktree.
root = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(root), str(root / "src")]

import matplotlib.pyplot as plt
import numpy as np
import torch
from matplotlib.patches import Rectangle
from tap import Tap

from scripts.regional_prediction_artifacts import (
    RegionalArtifactPlan,
    validate_checkpoint_metadata,
)
from scripts.uncertainty_artifacts import (
    mask_shape,
    stage_mask,
    validate_destination,
)
from vesuvius_autoresearch.core.checkpoint_tools import load_checkpoint
from vesuvius_autoresearch.core.file_modes import replacement_mode
from vesuvius_autoresearch.core.inference import (
    blend_coverage_fraction,
    depth_band_for,
    hann2d,
    multitask_inference_recipe,
    multitask_probabilities,
    normalize_blend,
    positive_number,
    prepare_volume_input,
    quantize_probabilities,
    read_model_block,
    region_tiles,
    ridge_depth_context,
    validate_model_settings,
    validate_region,
)
from vesuvius_autoresearch.core.model_wrappers import build_inference_model, task_heads
from vesuvius_autoresearch.core.new_artifacts import staged_directory, staged_file
from vesuvius_autoresearch.core.prediction_artifacts import (
    prediction_paths,
    prediction_stem,
    validate_output_file,
    validate_output_tree,
)
from vesuvius_autoresearch.core.regional_memory import RegionalMemoryProfile
from vesuvius_autoresearch.core.regional_resources import (
    MAX_ACCUMULATOR_BYTES,
    plan_regional_accumulators,
)
from vesuvius_autoresearch.core.vesuvius_loader import FastVesuviusVolume
from volume_cartographer_wrapper.volume import (
    local_volume_array_path,
    local_volume_path,
)


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


@contextmanager
def regional_preview_figure():
    """Release rendered preview data and close the figure."""
    figure = plt.figure(figsize=(15, 5))
    try:
        yield figure, figure.subplots(1, 3)
        # Closing the window alone leaves image arrays attached to its axes.
        figure.clear()
    finally:
        plt.close(figure)


def draw_empty_fiber_panel(axis, width, height):
    """Draw one black pixel across the regional panel's source coordinates."""
    origin = plt.rcParams["image.origin"]
    bottom, top = -0.5, height - 0.5
    if origin == "upper":
        bottom, top = top, bottom
    return axis.imshow(
        np.zeros((1, 1), dtype=np.float32),
        cmap="gray",
        vmin=0,
        vmax=1,
        origin=origin,
        extent=(-0.5, width - 0.5, bottom, top),
    )


@contextmanager
def _stage_prediction_file(destination, *, suffix=""):
    with staged_file(destination, suffix=suffix) as temporary:
        yield temporary
        if os.path.lexists(destination):
            validate_output_file(destination)


def _retain_vc3d_entries(destination, staging, metadata_files):
    """Keep entries outside the store's generated level and metadata."""
    validate_output_tree(destination)
    for entry in destination.iterdir():
        if entry.name == "0":
            if not entry.is_dir():
                raise ValueError("existing VC3D level 0 must be a directory")
        elif entry.name in metadata_files:
            validate_output_file(entry)
        elif entry.is_dir():
            copytree(entry, staging / entry.name)
        else:
            copy2(entry, staging / entry.name)


@contextmanager
def stage_vc3d_zarr(
    base_path,
    array_uint8,
    name="prediction",
    voxel_size_um=7.91,
    source_uri=None,
    origin_xyz=None,
):
    """Build a 2D uint8 store and publish it on successful context exit.

    OME axes are z/y/x and their units are micrometers, so translation reverses
    the caller's x/y/z order and converts indices to physical coordinates.
    """
    import uuid

    import zarr

    destination = Path(base_path)
    with staged_directory(destination, prefix=".prediction-zarr-") as staging:
        metadata_files = [".zattrs", "meta.json"]
        consolidated = os.path.lexists(destination / ".zmetadata")
        if consolidated:
            metadata_files.append(".zmetadata")
        if os.path.lexists(destination):
            _retain_vc3d_entries(destination, staging, metadata_files)

        # A resolution array plus .zattrs is not a Zarr group without .zgroup.
        zarr.open_group(str(staging), mode="a")
        # Create Zarr group/array at scale '0'
        z = zarr.open(
            str(staging / "0"),
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
        with (staging / ".zattrs").open("w", encoding="utf-8") as f:
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
        with (staging / "meta.json").open("w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        if consolidated:
            zarr.consolidate_metadata(str(staging))

        del array_uint8
        yield

        if os.path.lexists(destination):
            validate_output_tree(destination)
            for filename in metadata_files:
                previous = destination / filename
                if os.path.lexists(previous):
                    validate_output_file(previous)
                    (staging / filename).chmod(replacement_mode(previous))
            staging.chmod(stat.S_IMODE(destination.stat().st_mode))


def save_vc3d_zarr(
    base_path,
    array_uint8,
    name="prediction",
    voxel_size_um=7.91,
    source_uri=None,
    origin_xyz=None,
):
    """Build and publish one standalone VC3D store."""
    with stage_vc3d_zarr(
        base_path, array_uint8, name, voxel_size_um, source_uri, origin_xyz
    ):
        pass


@contextmanager
def stage_regional_outputs(
    artifacts,
    outputs,
    preview_files,
    *,
    blend_weights,
    voxel_size_um,
    source_uri,
    origin_xyz,
):
    """Prepare regional files and stores, then publish on successful exit."""
    from PIL import Image

    # Exit order installs numeric files, then stores, then previews.
    with ExitStack() as previews, ExitStack() as stores, ExitStack() as arrays:
        for destination, source in preview_files.items():
            temporary = previews.enter_context(_stage_prediction_file(destination))
            copyfile(source, temporary)

        zarr_paths = {}
        for kind, (probability, label) in outputs.items():
            base = artifacts.directory / f"{artifacts.stem}_{kind}"
            npy = arrays.enter_context(
                _stage_prediction_file(f"{base}.npy", suffix=".npy")
            )
            np.save(npy, probability, allow_pickle=False)

            image = quantize_probabilities(probability)
            png = arrays.enter_context(_stage_prediction_file(f"{base}.png"))
            Image.fromarray(image).save(png, format="PNG")

            destination = f"{base}.zarr"
            stores.enter_context(
                stage_vc3d_zarr(
                    destination,
                    image,
                    name=label,
                    voxel_size_um=voxel_size_um,
                    source_uri=source_uri,
                    origin_xyz=origin_xyz,
                )
            )
            zarr_paths[kind] = destination
            del image

        if blend_weights is not None:
            destination = artifacts.directory / f"{artifacts.stem}_weight.npy"
            npy = arrays.enter_context(
                _stage_prediction_file(destination, suffix=".npy")
            )
            np.save(npy, blend_weights, allow_pickle=False)
            del blend_weights

        yield zarr_paths


def invalidate_prediction_metadata(output_dir, base_name, metadata_out=None):
    """Invalidate every known sidecar before replacing a region's shared arrays.

    Rankers discover the canonical sidecar even when this run selects a custom
    one. Leaving it intact would authorize the old run's retained fiber files.
    """
    canonical = Path(output_dir) / f"{base_name}_meta.json"
    selected = metadata_out or str(canonical)
    paths = [
        path
        for path in dict.fromkeys((canonical, Path(selected)))
        if os.path.lexists(path)
    ]
    for path in paths:
        validate_output_file(path)
    if len(paths) < 2:
        for path in paths:
            os.remove(path)
        return selected

    first, second = paths
    workspace = Path(mkdtemp(dir=first.parent, prefix=".prediction-sidecars-"))
    backup = workspace / "previous.json"
    invalidated = False
    try:
        first.rename(backup)
        try:
            os.remove(second)
        except BaseException:
            try:
                backup.rename(first)
            except OSError as exc:
                raise RuntimeError(
                    f"sidecar rollback failed; previous record retained at {backup}"
                ) from exc
            raise
        invalidated = True
    finally:
        if invalidated or not backup.exists():
            rmtree(workspace, ignore_errors=True)
    return selected


@contextmanager
def stage_prediction_metadata(
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
    memory_profile=None,
):
    """Prepare the prediction record and install it on successful exit."""
    voxel_size_um = float(
        config_dict.get(
            "voxel_size_um", config_dict.get("voxelsize", args.voxel_size_um)
        )
    )
    patch_size = int(config_dict.get("patch_size", args.patch_size))
    checkpoint_path = getattr(args, "resolved_checkpoint_path", None)
    if checkpoint_path is None and getattr(args, "checkpoint", None):
        checkpoint_path = str(Path(args.checkpoint).resolve())
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
        "checkpoint_path": checkpoint_path,
        "checkpoint_sha256": getattr(args, "checkpoint_sha256", None),
        "inference_recipe": getattr(args, "inference_recipe", None),
        "resource_plan": getattr(args, "resource_plan", None),
        "ink_stats": ink_stats,
        "fiber_stats": fiber_stats or {},
        "fiber_coherence": fiber_coherence,
        "uncertainty_export": getattr(args, "uncertainty_export", None),
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
    if memory_profile is not None:
        memory_profile.sample("metadata_ready")
        metadata["memory_profile"] = memory_profile.report()
    if extra_metadata:
        if metadata.keys() & extra_metadata.keys():
            raise ValueError("extra metadata must not overwrite prediction facts")
        metadata.update(extra_metadata)
    encoded = json.dumps(metadata, indent=2, allow_nan=False)
    with _stage_prediction_file(path) as temporary:
        temporary.write_text(encoded + "\n", encoding="utf-8")
        yield


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
    memory_profile=None,
):
    """Prepare and publish the record for standalone writers."""
    with stage_prediction_metadata(
        path,
        args,
        config_dict,
        zarr_path,
        output_img,
        ink_stats,
        fiber_zarr_path=fiber_zarr_path,
        fiber_stats=fiber_stats,
        fiber_coherence=fiber_coherence,
        extra_metadata=extra_metadata,
        memory_profile=memory_profile,
    ):
        pass


def _prediction_output(args):
    base = prediction_stem(
        f"pred_{args.z}_{args.y}_{args.x}_{args.width}x{args.height}",
        getattr(args, "artifact_stem", None),
    )
    if args.num_parts > 1:
        base += f"_part{args.part_id}of{args.num_parts}"
    image = args.output_img or f"predictions/{base}.png"
    return base, image, os.path.dirname(image) or "."


def _uncertainty_sources(args, base, directory, image):
    target = Path(directory) / f"{base}_uncertain"
    sources = [
        args.checkpoint,
        args.resolved_checkpoint_path,
        image,
        *(p for p in prediction_paths(directory, base) if p != target),
    ]
    if args.metadata_out:
        sources.append(args.metadata_out)
    uri = urlsplit(args.uri)
    if os.path.exists(args.uri) or not uri.scheme:
        sources.append(args.uri)
    elif uri.scheme == "file":
        if uri.netloc not in {"", "localhost"}:
            raise ValueError("file URI must refer to the local host")
        sources.append(unquote(uri.path))
    return target, sources


class PredictionArgs(Tap):
    uri: str  # Local path or local file URI to a Zarr volume
    z: int | None = (
        None  # first slice; default: centred in the checkpoint's depth_band on its own volumes, else the volume
    )
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
    artifact_stem: str | None = None  # Shared basename for arrays, previews and exports
    voxel_size_um: float = 7.91
    checkpoint: str = "best_model.pt"  # Model checkpoint to use for prediction
    num_parts: int = 1
    part_id: int = 0
    disable_tta: bool = False
    skip_active_learning: bool = False  # Skip optional proofreader uncertainty export
    max_accumulator_bytes: int = MAX_ACCUMULATOR_BYTES  # Blend-plane budget in bytes
    profile_memory: bool = False  # Record process RSS and selected-device PyTorch allocator peaks in metadata
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
    prediction_stem("unused", getattr(args, "artifact_stem", None))
    args.inference_recipe = multitask_inference_recipe(
        args.disable_tta, args.gaussian_blend
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading volume from {args.uri}...")

    # Load trained model first to get the correct hyperparameters
    if not os.path.exists(args.checkpoint):
        raise FileNotFoundError(
            f"Trained model not found at {args.checkpoint}. Please run training first."
        )

    # Bind the read, artifact protection and provenance to the same target.
    checkpoint_path = Path(args.checkpoint).resolve()
    checkpoint_bytes = checkpoint_path.read_bytes()
    args.resolved_checkpoint_path = str(checkpoint_path)
    args.checkpoint_sha256 = hashlib.sha256(checkpoint_bytes).hexdigest()
    checkpoint = load_checkpoint(
        io.BytesIO(checkpoint_bytes),
        map_location="cpu",
        weights_only=True,
        allow_numpy_scalars=True,
    )
    del checkpoint_bytes
    if not isinstance(checkpoint, dict) or not isinstance(
        checkpoint.get("config", {}), dict
    ):
        raise ValueError("checkpoint and checkpoint config must be objects")
    config_dict = checkpoint.get("config", {})
    validate_checkpoint_metadata(config_dict)
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
    args.resource_plan = plan_regional_accumulators(
        patch_size if args.width is None else args.width,
        patch_size if args.height is None else args.height,
        args.max_accumulator_bytes,
    )
    validate_region(args, patch_size, num_layers, allow_auto_z=True)
    my_chunks = region_tiles(args, patch_size)
    args.inference_recipe["ridge_depth_context"] = ridge_depth_context(use_ridges)
    volume_options = {
        "use_ridges": use_ridges,
        "ridge_sigma": ridge_sigma,
        "strict_reads": True,
    }
    dataset = None
    auto_source_selection = None
    if args.z is None:
        # Centre the window in the depth band the checkpoint was trained on, on
        # the volumes it was trained or validated on (the band is in their slice
        # numbers); otherwise in the volume (surface volumes are built around the
        # segment surface at their middle layer). Pass --z to choose.
        auto_source_root = local_volume_path(args.uri).resolve()
        auto_source_array = local_volume_array_path(auto_source_root)
        auto_source_selection = (auto_source_root, auto_source_array)
        dataset = FastVesuviusVolume(str(auto_source_array), **volume_options)
        depth = dataset.shape[0]
        band = depth_band_for(config_dict, auto_source_array)
        if band and 0 <= band[0] < band[1] <= depth:
            centre = band[0] + band[1]
        else:
            centre = depth
        args.z = min(max(0, (centre - num_layers) // 2), max(0, depth - num_layers))
    base_name, out_path, output_dir = _prediction_output(args)
    artifacts = RegionalArtifactPlan.create(
        base_name,
        out_path,
        args.metadata_out,
        args.uri,
        [checkpoint_path, args.checkpoint],
    )
    if auto_source_selection is not None and auto_source_selection != (
        artifacts.source,
        artifacts.source_array,
    ):
        raise RuntimeError("CT source selection changed during automatic depth selection")
    out_path, output_dir = str(artifacts.image), str(artifacts.directory)
    uncertainty_path, uncertainty_sources = _uncertainty_sources(
        args, base_name, output_dir, out_path
    )
    args.uncertainty_export = {
        "status": "SKIPPED",
        "path": None,
        "reason": "--skip_active_learning requested",
    }
    if not args.skip_active_learning:
        if args.num_parts > 1:
            args.uncertainty_export = {
                "status": "INCOMPLETE",
                "path": None,
                "reason": "combine inference parts before proofreading",
            }
        else:
            mask_shape((1, args.height, args.width))
            validate_destination(
                uncertainty_path, overwrite=True, sources=uncertainty_sources
            )
            args.uncertainty_export = {"status": "PLANNED", "path": None}

    if dataset is None:
        dataset = FastVesuviusVolume(str(artifacts.source_array), **volume_options)
    if dataset.vol.path != artifacts.source_array:
        raise RuntimeError("CT source selection changed while opening the regional volume")
    artifacts.validate_source_selection(args.uri)
    validate_region(args, patch_size, num_layers, dataset.shape)

    memory_profile = RegionalMemoryProfile(device) if args.profile_memory else None
    model = build_prediction_model(config_dict, args, use_ridges)
    # Check complete weights on CPU before allocating the model on the device.
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    del checkpoint
    model = model.to(device).eval()
    # A model without a fiber head returns its ink logits as "fiber": exported,
    # that was the ink map under the fiber prediction's name.
    heads = sorted(task_heads(model))
    has_fiber = "fiber" in heads
    if memory_profile is not None:
        memory_profile.sample("models_loaded")

    # Determine region and tiling parameters
    predict_width, predict_height, stride = args.width, args.height, args.stride

    # Initialize accumulation buffers
    full_prob_ink = torch.zeros(
        (predict_height, predict_width), device=device, dtype=torch.float32
    )
    full_prob_fiber = torch.zeros_like(full_prob_ink) if has_fiber else None
    full_weight = torch.zeros_like(full_prob_ink)

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

    if args.num_parts > 1:
        print(
            f"Distributed Inference: processing part {args.part_id}/{args.num_parts} ({len(my_chunks)}/{args.tiles_total} chunks)"
        )

    for y_off, x_off in my_chunks:
        curr_y = args.y + y_off
        curr_x = args.x + x_off

        # Read the block, with training's depth context for the ridge channel
        block = read_model_block(
            dataset, args.z, curr_y, curr_x, num_layers, patch_size
        )

        # Prepare input
        x = prepare_volume_input(
            dataset.normalize(block), use_ridges, num_layers, patch_size, device
        )

        with torch.no_grad():
            ink_batch, fiber_batch = multitask_probabilities(model, x, args.disable_tta)
            prob_ink = ink_batch[0]

            # Accumulate with weight window
            full_prob_ink[y_off : y_off + patch_size, x_off : x_off + patch_size] += (
                prob_ink * weight_window
            )
            if full_prob_fiber is not None:
                full_prob_fiber[
                    y_off : y_off + patch_size, x_off : x_off + patch_size
                ] += fiber_batch[0] * weight_window
            full_weight[y_off : y_off + patch_size, x_off : x_off + patch_size] += (
                weight_window
            )

    # Blend normalization only needs the accumulated predictions.
    del model
    complete = args.num_parts == 1
    full_prob_ink = normalize_blend(full_prob_ink, full_weight, complete)
    if full_prob_fiber is not None:
        full_prob_fiber = normalize_blend(full_prob_fiber, full_weight, complete)
    args.coverage_fraction = blend_coverage_fraction(full_weight, complete=complete)
    blend_weights = None if complete else full_weight.cpu().numpy()
    del full_weight

    prob_ink_final = full_prob_ink.cpu().numpy()
    prob_fiber_final = (
        full_prob_fiber.cpu().numpy() if full_prob_fiber is not None else None
    )
    if memory_profile is not None:
        memory_profile.sample("inference_complete")

    def stage_metadata(exports, fiber_coherence=None):
        return stage_prediction_metadata(
            artifacts.metadata,
            args,
            config_dict,
            exports["ink"],
            out_path,
            {
                "mean": float(prob_ink_final.mean()),
                "std": float(prob_ink_final.std()),
                "max": float(prob_ink_final.max()),
            },
            fiber_zarr_path=exports.get("fiber"),
            fiber_stats={
                "mean": float(prob_fiber_final.mean()),
                "std": float(prob_fiber_final.std()),
                "max": float(prob_fiber_final.max()),
            }
            if prob_fiber_final is not None
            else None,
            fiber_coherence=fiber_coherence,
            extra_metadata={"task_heads": heads},
            memory_profile=memory_profile,
        )

    # The full preview can reach damaged chunks outside this shard's tiles.
    z_mid = args.z + num_layers // 2
    ct_slice = dataset.read_ct(z_mid, args.y, args.x, 1, predict_height, predict_width)[
        0
    ]
    with TemporaryDirectory(prefix="regional-preview-") as directory:
        staging = Path(directory)
        with regional_preview_figure() as (figure, axes):
            axes[0].imshow(ct_slice, cmap="gray")
            axes[0].set_title(f"CT Slice (Z={z_mid})")

            if prob_fiber_final is not None:
                axes[1].imshow(prob_fiber_final, cmap="magma")
                axes[1].set_title("Fiber Context (Fused)")
            else:
                draw_empty_fiber_panel(axes[1], predict_width, predict_height)
                axes[1].set_title("No fiber head")

            axes[2].imshow(ct_slice, cmap="gray")
            axes[2].imshow(prob_ink_final, cmap="jet", alpha=0.5)
            axes[2].set_title("Ink Overlay (Soft-Tiled)")

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

            figure.tight_layout()
            figure.savefig(
                str(staging / artifacts.image.name), format=artifacts.image_format
            )
        coherence_slice = ct_slice if args.compute_coherence else None
        del ct_slice
        preview_files = artifacts.preview_files(staging)
        artifacts.validate_source_selection(args.uri)
        # Protect the current checkpoint link target as well as the file we read.
        artifacts.validate(
            checkpoint_aliases=(args.checkpoint,), preview_paths=preview_files
        )
        outputs = {"ink": (prob_ink_final, f"Ink Prediction {base_name}")}
        if prob_fiber_final is not None:
            outputs["fiber"] = (prob_fiber_final, f"Fiber Prediction {base_name}")
        if args.num_parts > 1:
            args.blend_weight_path = os.path.join(output_dir, f"{base_name}_weight.npy")
        export_uncertainty = args.uncertainty_export["status"] == "PLANNED"
        with (
            ExitStack() as pending_metadata,
            ExitStack() as pending_mask,
            stage_regional_outputs(
                artifacts,
                outputs,
                preview_files,
                blend_weights=blend_weights,
                voxel_size_um=args.voxel_size_um,
                source_uri=args.uri,
                origin_xyz=[int(args.x), int(args.y), int(args.z)],
            ) as exports,
        ):
            if export_uncertainty:
                try:
                    from scripts.active_learning_sampler import (
                        identify_uncertain_patches,
                    )

                    mask = identify_uncertain_patches(full_prob_ink, threshold=0.2)
                    args.uncertainty_export = pending_mask.enter_context(
                        stage_mask(
                            mask.detach().cpu().numpy(),
                            uncertainty_path,
                            overwrite=True,
                            sources=uncertainty_sources,
                            metadata={
                                "source_uri": args.uri,
                                "position_xyz": [args.x, args.y, args.z],
                                "voxel_size_um": args.voxel_size_um,
                                "model_num_layers": num_layers,
                                "artifact_stem": base_name,
                                "checkpoint_sha256": args.checkpoint_sha256,
                                "normalized_entropy_threshold": 0.2,
                                "score_kind": "normalized_binary_entropy",
                                "inference_recipe": args.inference_recipe,
                                "coverage_fraction": args.coverage_fraction,
                            },
                        )
                    )
                    del mask
                    args.uncertainty_export["normalized_entropy_threshold"] = 0.2
                except ImportError as exc:
                    args.uncertainty_export = {
                        "status": "UNAVAILABLE",
                        "path": None,
                        "reason": str(exc),
                    }
                    print(f"Warning: skipping active-learning export: {exc}")

            pending_metadata.enter_context(stage_metadata(exports))

            # Recheck source selection and aliases after all preparation.
            artifacts.validate_source_selection(args.uri)
            artifacts.validate(
                checkpoint_aliases=(args.checkpoint,), preview_paths=preview_files
            )
            if export_uncertainty:
                validate_destination(
                    uncertainty_path, overwrite=True, sources=uncertainty_sources
                )
            metadata_path = invalidate_prediction_metadata(
                output_dir, base_name, str(artifacts.metadata)
            )
        if args.uncertainty_export["path"] is not None:
            print(f"Exported uncertainty mask for proofreading: {uncertainty_path}")

    # Automated Fiber Coherence Evaluation (Villa ST): the structure tensor of the
    # CT slice shown in the figure, independent of the model's heads.
    if coherence_slice is not None:
        try:
            from scripts.compute_fiber_coherence import compute_coherence

            print("Computing Fiber Coherence score (Villa ST)...", flush=True)
            fiber_coherence = compute_coherence(coherence_slice, device=str(device))
            del coherence_slice
            print(f"Fiber Coherence Score: {fiber_coherence:.6f}")
            with stage_metadata(exports, fiber_coherence):
                pass
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
