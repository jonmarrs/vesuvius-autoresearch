"""Strict checkpoint and tensor boundaries for auxiliary research commands."""

import os

import torch

from . import model_wrappers
from .inference import (
    DEPTH_MARGIN,
    centre_window,
    positive_integer,
    validate_model_settings,
)

# torch.load's rule, not zipfile.is_zipfile's: a checkpoint is a zip only when
# its first bytes are a local-file header.
_ZIP_LOCAL = b"PK\x03\x04"
NON_ZIP_CHECKPOINT = (
    "refusing a non-zip checkpoint; convert it offline to zip before loading"
)


def _signature(source) -> bytes | None:
    """The first bytes of a path or a seekable buffer, without consuming it.

    None means the path is not there. The loader that follows reports that;
    a missing file is not a legacy checkpoint.
    """
    if isinstance(source, (bytes, bytearray, memoryview)):
        return bytes(source[: len(_ZIP_LOCAL)])
    if isinstance(source, (str, os.PathLike)):
        try:
            with open(source, "rb") as handle:
                return handle.read(len(_ZIP_LOCAL))
        except FileNotFoundError:
            return None
    position = source.tell()
    try:
        return source.read(len(_ZIP_LOCAL))
    finally:
        source.seek(position)


def checkpoint_is_zip(source) -> bool:
    return _signature(source) == _ZIP_LOCAL


def require_zip_checkpoint(source) -> None:
    """Refuse a legacy pickle or a tar before anything unpickles it."""
    signature = _signature(source)
    if signature is None:
        return
    if signature != _ZIP_LOCAL:
        raise ValueError(NON_ZIP_CHECKPOINT)


def _numpy_scalar_types():
    """NumPy scalars recorded in published project checkpoints, and nothing else."""
    import numpy as np

    try:
        from numpy._core.multiarray import scalar
    except ImportError:  # NumPy 1.x
        from numpy.core.multiarray import scalar  # type: ignore[no-redef]
    return [scalar, np.dtype, type(np.dtype("float64")), type(np.dtype("float32"))]


def load_checkpoint(
    source, *, map_location=None, weights_only=True, allow_numpy_scalars=False, **kwargs
):
    """Load a zip checkpoint. A legacy pickle or a tar is refused before torch.load.

    ``weights_only=True`` is the default. ``allow_numpy_scalars`` adds only the
    NumPy scalars a project checkpoint records beside its tensors. A caller that
    passes ``weights_only=False`` still has to clear this zip gate first: the
    file is a torch zip, not a tar or a legacy pickle.
    """
    require_zip_checkpoint(source)
    if weights_only and allow_numpy_scalars:
        with torch.serialization.safe_globals(_numpy_scalar_types()):
            return torch.load(
                source, map_location=map_location, weights_only=True, **kwargs
            )
    return torch.load(
        source, map_location=map_location, weights_only=weights_only, **kwargs
    )


def load_tool_checkpoint(path, device):
    checkpoint = load_checkpoint(
        path, map_location="cpu", weights_only=True, allow_numpy_scalars=True
    )
    model, settings = build_tool_model(checkpoint, device)
    return model, settings, checkpoint


def build_tool_model(checkpoint, device="cpu"):
    """Reconstruct recorded local models with complete weights, without data access."""
    if not isinstance(checkpoint, dict) or not isinstance(
        checkpoint.get("config"), dict
    ):
        raise ValueError("checkpoint must contain a recorded config object")
    config = checkpoint["config"]
    for key in ("architecture", "patch_size", "num_layers", "base_feat"):
        if key not in config:
            raise ValueError(
                f"checkpoint config is missing {key}; verify the training configuration"
            )
    settings = {
        key: config[key]
        for key in ("architecture", "patch_size", "num_layers", "base_feat")
    }
    settings.update(
        {
            key: config.get(key, default)
            for key, default in (
                ("num_blocks", 16),
                ("num_heads", 8),
                ("dropout", 0.0),
                ("use_ridges", False),
                ("multi_task_heads", False),
            )
        }
    )
    sigma = validate_model_settings(
        config, settings["patch_size"], settings["num_layers"], settings["base_feat"]
    )
    for key in ("num_blocks", "num_heads"):
        positive_integer(settings[key], f"checkpoint {key}")
    if not isinstance(settings["multi_task_heads"], bool):
        raise ValueError("checkpoint multi_task_heads must be a boolean")
    state = checkpoint.get("model_state_dict")
    if not isinstance(state, dict) or not state:
        raise ValueError("checkpoint must contain complete model_state_dict weights")
    model = model_wrappers.build_inference_model(**settings)
    model.load_state_dict(state, strict=True)
    settings["ridge_sigma"] = sigma
    return model.to(device).eval(), settings


def validate_batch(batch, settings, buffered=False):
    layers, size = settings["num_layers"], settings["patch_size"]
    channels = 2 if settings["use_ridges"] else 1
    # A buffered read carries training's depth context: num_layers + 2 * margin
    # slices, or fewer from a volume without room for all of it.
    depths = range(layers, layers + 2 * DEPTH_MARGIN + 1) if buffered else [layers]
    if (
        not isinstance(batch, torch.Tensor)
        or batch.ndim != 5
        or len(batch) < 1
        or batch.shape[2] not in depths
        or tuple(batch.shape[1:]) != (channels, batch.shape[2], size, size)
        or not batch.is_floating_point()
        or not torch.isfinite(batch).all()
    ):
        depth = f"{depths[0]}-{depths[-1]}" if buffered else layers
        expected = (channels, depth, size, size)
        raise ValueError(f"input must be finite B/C/Z/H/W with C/Z/H/W={expected}")
    return centre_window(batch, layers) if buffered else batch


def ink_probabilities(model, batch):
    logits = model(batch)
    if isinstance(logits, tuple) and logits:
        logits = logits[0]
    validate_ink_logits(logits, batch)
    return torch.sigmoid(logits).float()


def validate_ink_logits(logits, batch):
    expected = (len(batch), 1, *batch.shape[-2:])
    if (
        not isinstance(logits, torch.Tensor)
        or tuple(logits.shape) != expected
        or not logits.is_floating_point()
        or not torch.isfinite(logits).all()
    ):
        raise ValueError(
            f"ink logits must be finite floating-point tensors with shape {expected}"
        )


def validate_targets(target, probabilities):
    if isinstance(target, torch.Tensor) and target.ndim == 3:
        target = target.unsqueeze(1)
    if (
        not isinstance(target, torch.Tensor)
        or target.shape != probabilities.shape
        or not torch.isfinite(target).all()
        or not ((target >= 0) & (target <= 1)).all()
    ):
        raise ValueError(
            "targets must be finite, in [0,1], and aligned with ink probabilities"
        )
    return target
