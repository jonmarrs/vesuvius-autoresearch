"""Shared contracts for regional CT-volume inference.

Coordinates are source voxel indices in z/y/x order; model inputs are B/C/Z/H/W.
The multitask probability path retains its existing QC gate and mirror recipe.
"""

import math
from numbers import Integral, Real

import torch


def positive_integer(value, name, minimum=1):
    if not isinstance(value, Integral) or isinstance(value, bool) or value < minimum:
        requirement = "positive" if minimum == 1 else "nonnegative"
        raise ValueError(f"{name} must be a {requirement} integer")
    return int(value)


def positive_number(value, name):
    if (
        not isinstance(value, Real)
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"{name} must be positive and finite")
    return float(value)


def validate_model_settings(config, patch_size, num_layers, base_feat):
    """Validate effective shape and ridge settings before constructing a model."""
    if not isinstance(config, dict):
        raise ValueError("checkpoint config must be an object")
    for name, value in (
        ("patch_size", patch_size),
        ("num_layers", num_layers),
        ("base_feat", base_feat),
    ):
        positive_integer(value, f"checkpoint {name}")
    if not isinstance(config.get("use_ridges", False), bool):
        raise ValueError("checkpoint use_ridges must be a boolean")
    return positive_number(config.get("ridge_sigma", 2.0), "checkpoint ridge_sigma")


def validate_region(args, patch_size, num_layers, shape=None):
    """Resolve explicit defaults and require a complete in-bounds source region."""
    positive_integer(patch_size, "patch_size")
    positive_integer(num_layers, "num_layers")
    explicit_region = args.width is not None or args.height is not None
    args.width = patch_size if args.width is None else args.width
    args.height = patch_size if args.height is None else args.height
    for name in ("width", "height"):
        positive_integer(getattr(args, name), name)
        if getattr(args, name) < patch_size:
            raise ValueError(f"{name} must be at least the checkpoint patch_size")
    if args.stride is None:
        args.stride = max(1, patch_size // 2) if explicit_region else patch_size
    positive_integer(args.stride, "stride")
    if args.stride > patch_size:
        raise ValueError("stride must be <= patch_size to avoid gaps")
    for name in ("x", "y", "z", "part_id"):
        positive_integer(getattr(args, name), name, minimum=0)
    positive_integer(args.num_parts, "num_parts")
    if args.part_id >= args.num_parts:
        raise ValueError("part_id must be smaller than num_parts")
    if shape is not None:
        ends = (args.z + num_layers, args.y + args.height, args.x + args.width)
        if len(shape) != 3 or any(
            end > limit for end, limit in zip(ends, shape, strict=True)
        ):
            raise ValueError(f"requested region exceeds volume shape {shape}")


def tile_starts(length, size, stride):
    positive_integer(length, "length")
    positive_integer(size, "size")
    positive_integer(stride, "stride")
    if length < size or stride > size:
        raise ValueError("tiling requires length >= size and stride <= size")
    starts = list(range(0, length - size + 1, stride))
    if starts[-1] != length - size:
        starts.append(length - size)
    return starts


def region_tiles(args, patch_size):
    all_tiles = [
        (y, x)
        for y in tile_starts(args.height, patch_size, args.stride)
        for x in tile_starts(args.width, patch_size, args.stride)
    ]
    my_tiles = all_tiles[args.part_id :: args.num_parts]
    if not my_tiles:
        raise ValueError(
            "requested inference shard contains no tiles; reduce num_parts"
        )
    args.tiles_total = len(all_tiles)
    args.tiles_processed = len(my_tiles)
    return my_tiles


def hann2d(height, width, device="cpu"):
    """Positive Hann weights so outer edges receive predictions too."""
    positive_integer(height, "height")
    positive_integer(width, "width")
    wy = torch.hann_window(height + 2, periodic=False, device=device)[1:-1]
    wx = torch.hann_window(width + 2, periodic=False, device=device)[1:-1]
    return torch.outer(wy, wx)


def prepare_volume_input(block, use_ridges, layers, size, device):
    """Convert a normalized loader result to one validated B/C/Z/H/W batch."""
    if not isinstance(block, torch.Tensor):
        raise ValueError("volume patch must be a tensor")
    if not use_ridges:
        block = block.unsqueeze(0)
    expected = (2 if use_ridges else 1, layers, size, size)
    if (
        tuple(block.shape) != expected
        or not block.is_floating_point()
        or not torch.isfinite(block).all()
    ):
        raise ValueError(f"volume patch must be finite with shape {expected}")
    return block.unsqueeze(0).to(device)


def multitask_probabilities(model, batch, disable_tta=False):
    """QC-gated ink and depth-collapsed fiber probabilities, with optional TTA."""
    mirrors = ((),) if disable_tta else ((), (-1,), (-2,), (-2, -1))
    result_ink = result_fiber = None
    b, _, _, height, width = batch.shape
    for dims in mirrors:
        outputs = model(
            batch.flip(dims) if dims else batch, return_fiber=True, return_qc=True
        )
        if not isinstance(outputs, tuple) or len(outputs) != 3:
            raise ValueError("model output must contain ink, fiber, and QC logits")
        ink, fiber, qc = outputs
        for output in outputs:
            if (
                not isinstance(output, torch.Tensor)
                or not output.is_floating_point()
                or not torch.isfinite(output).all()
            ):
                raise ValueError(
                    "model output logits must be finite floating-point tensors"
                )
        if (
            tuple(ink.shape) != (b, 1, height, width)
            or fiber.ndim != 5
            or tuple(fiber.shape[:2]) != (b, 1)
            or fiber.shape[2] < 1
            or tuple(fiber.shape[-2:]) != (height, width)
            or tuple(qc.shape) != (b, 1)
        ):
            raise ValueError(
                "model output dimensions do not match the input batch and region"
            )
        prob_ink = torch.sigmoid(ink) * torch.sigmoid(qc / 0.1).view(b, 1, 1, 1)
        prob_fiber = torch.sigmoid(fiber.mean(dim=2))
        if dims:
            prob_ink, prob_fiber = prob_ink.flip(dims), prob_fiber.flip(dims)
        result_ink = prob_ink if result_ink is None else result_ink + prob_ink
        result_fiber = prob_fiber if result_fiber is None else result_fiber + prob_fiber
    return result_ink[:, 0] / len(mirrors), result_fiber[:, 0] / len(mirrors)


def multitask_inference_recipe(disable_tta, gaussian_blend):
    """Record probability transforms separately from the training configuration."""
    return {
        "ink_probability": "sigmoid(ink) * sigmoid(qc / 0.1)",
        "fiber_probability": "sigmoid(mean(fiber, z))",
        "tta_mirrors": ["none"] if disable_tta else ["none", "x", "y", "xy"],
        "blend_window": "gaussian" if gaussian_blend else "positive_hann",
    }


def normalize_blend(values, weights, complete=True):
    """Divide by actual positive weights, leaving unprocessed shard pixels zero."""
    if not torch.isfinite(values).all() or not torch.isfinite(weights).all():
        raise ValueError("prediction blend must be finite")
    covered = weights > 0
    if complete and not covered.all():
        raise ValueError("complete prediction has uncovered pixels")
    return values / torch.where(covered, weights, torch.ones_like(weights))
