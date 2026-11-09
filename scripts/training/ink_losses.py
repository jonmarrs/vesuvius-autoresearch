"""Supervised ink losses shared by training and small gradient contract tests."""

import torch
import torch.nn.functional as F

CONFIDENCE_INK_RECIPE = "confidence-ink-v2-png128-linear-dice"


def _full_precision(value):
    return value.float() if value.dtype in (torch.float16, torch.bfloat16) else value


def confidence_weight(target):
    """Distance from uncertainty, with PNG 128 treated as the ignore sentinel.

    Labels are normalized to [0, 1]. Both 0.5 and the producer's 128/255 have
    zero weight; binary labels retain unit weight. The small absolute tolerance
    covers float32 PNG decoding followed by dtype conversion. This is computed
    after augmentation, not an independently propagated spatial holdout mask.
    """
    weight = (2.0 * (target - 0.5).abs()).clamp(0.0, 1.0)
    encoded_ignore = torch.isclose(
        target, target.new_tensor(128 / 255), rtol=0, atol=1e-7
    )
    return weight.masked_fill(encoded_ignore, 0)


def _target_shape(logits, target, name):
    if target.dim() == 3:
        target = target.unsqueeze(1)
    if logits.ndim != 4 or target.shape != logits.shape:
        raise ValueError(f"{name} must match ink logits with shape (B, 1, H, W)")
    if logits.shape[1] != 1:
        raise ValueError("ink logits must have one channel")
    return target


def compute_dice_loss(pred_2d, target, smooth=1e-5, weight=None):
    """Per-sample soft Dice; optional weights enter each spatial sum once.

    Weighted samples with no supervision are excluded from the mean. An entirely
    ignored batch returns a differentiable zero. Unweighted reduction is the
    existing mean over every sample, including valid all-background samples.
    """
    target = _target_shape(pred_2d, target, "target")
    probability = torch.sigmoid(pred_2d)
    if weight is None:
        intersection = (probability * target).sum(dim=(-2, -1))
        union = probability.sum(dim=(-2, -1)) + target.sum(dim=(-2, -1))
        dice = (2.0 * intersection + smooth) / (union + smooth)
        return 1.0 - dice.mean()

    weight = _target_shape(pred_2d, weight, "weight")
    probability = _full_precision(probability)
    target, weight = _full_precision(target), _full_precision(weight)
    intersection = (probability * target * weight).sum(dim=(-2, -1))
    union = ((probability + target) * weight).sum(dim=(-2, -1))
    loss = 1.0 - (2.0 * intersection + smooth) / (union + smooth)
    scored = weight.sum(dim=(-2, -1)) > 0
    return (loss * scored).sum() / scored.sum().clamp_min(1)


def confidence_weighted_ink_losses(logits, target):
    """Return confidence-weighted BCE and Dice, matching the training branch."""
    target = _target_shape(logits, target, "target").clamp(0, 1)
    # Recognize a quantized sentinel in its original dtype, before promoting
    # reductions (notably bfloat16's rounded representation of PNG 128).
    weight = _full_precision(confidence_weight(target))
    target, logits = _full_precision(target), _full_precision(logits)
    bce_map = F.binary_cross_entropy_with_logits(logits, target, reduction="none")
    bce = (bce_map * weight).sum() / weight.sum().clamp_min(1.0)
    return bce, compute_dice_loss(logits, target, weight=weight)
