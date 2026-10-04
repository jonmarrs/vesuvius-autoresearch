"""Strict checkpoint and tensor boundaries for auxiliary research commands."""

import torch

from . import model_wrappers
from .inference import positive_integer, validate_model_settings


def load_tool_checkpoint(path, device):
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
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
    return model.to(device).eval(), settings, checkpoint


def validate_batch(batch, settings, buffered=False):
    layers, size = settings["num_layers"], settings["patch_size"]
    channels = 2 if settings["use_ridges"] else 1
    depth = layers + 8 if buffered else layers
    if (
        not isinstance(batch, torch.Tensor)
        or batch.ndim != 5
        or len(batch) < 1
        or tuple(batch.shape[1:]) != (channels, depth, size, size)
        or not batch.is_floating_point()
        or not torch.isfinite(batch).all()
    ):
        raise ValueError(
            f"input must be finite B/C/Z/H/W with C/Z/H/W={(channels, depth, size, size)}"
        )
    return batch[:, :, 4 : 4 + layers] if buffered else batch


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
