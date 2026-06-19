# repro/ink_segformer/losses.py
import torch
import torch.nn.functional as F


def bce_dice_loss(logits, target, mask=None, smooth=1.0):
    """BCE + soft Dice on ink logits. Optional papyrus `mask` restricts both terms
    to masked pixels (background excluded)."""
    if mask is None:
        bce = F.binary_cross_entropy_with_logits(logits, target)
    else:
        bce_map = F.binary_cross_entropy_with_logits(logits, target, reduction="none")
        bce = (bce_map * mask).sum() / mask.sum().clamp_min(1.0)
    p = torch.sigmoid(logits)
    if mask is not None:
        p, target = p * mask, target * mask
    inter = (p * target).sum(dim=(-2, -1))
    union = p.sum(dim=(-2, -1)) + target.sum(dim=(-2, -1))
    dice = 1.0 - (2.0 * inter + smooth) / (union + smooth)
    return bce + dice.mean()
