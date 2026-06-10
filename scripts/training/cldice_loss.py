"""Differentiable soft-clDice topology loss (Shit et al., CVPR 2021).

Targets centerline overlap directly — the same notion the villa centerline_dice
gate measures — via a fully differentiable soft-skeletonization (iterated
min/max pooling). Unlike the C++ BettiLoss in this repo, gradients flow to the
model, so it can actually train continuity into thin ink strokes.

Operates on 2D ink maps shaped (B, 1, H, W): logits in, scalar loss out.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


def _soft_erode(img: torch.Tensor) -> torch.Tensor:
    p1 = -F.max_pool2d(-img, (3, 1), (1, 1), (1, 0))
    p2 = -F.max_pool2d(-img, (1, 3), (1, 1), (0, 1))
    return torch.min(p1, p2)


def _soft_dilate(img: torch.Tensor) -> torch.Tensor:
    return F.max_pool2d(img, (3, 3), (1, 1), (1, 1))


def _soft_open(img: torch.Tensor) -> torch.Tensor:
    return _soft_dilate(_soft_erode(img))


def soft_skeletonize(img: torch.Tensor, iters: int = 10) -> torch.Tensor:
    """Differentiable morphological skeleton of a [0,1] map, shape (B, 1, H, W)."""
    img1 = _soft_open(img)
    skel = F.relu(img - img1)
    for _ in range(iters):
        img = _soft_erode(img)
        img1 = _soft_open(img)
        delta = F.relu(img - img1)
        skel = skel + F.relu(delta - skel * delta)
    return skel


class SoftClDiceLoss(nn.Module):
    """1 - soft clDice between a predicted ink map and a binary target."""

    def __init__(self, iters: int = 10, smooth: float = 1.0):
        super().__init__()
        self.iters = iters
        self.smooth = smooth

    def forward(self, logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        prob = torch.sigmoid(logits)
        target = target.to(prob.dtype)

        skel_pred = soft_skeletonize(prob, self.iters)
        skel_true = soft_skeletonize(target, self.iters)

        dims = (1, 2, 3)  # reduce per sample, average over the batch
        tprec = (torch.sum(skel_pred * target, dims) + self.smooth) / (
            torch.sum(skel_pred, dims) + self.smooth
        )
        tsens = (torch.sum(skel_true * prob, dims) + self.smooth) / (
            torch.sum(skel_true, dims) + self.smooth
        )
        cl_dice = 2.0 * (tprec * tsens) / (tprec + tsens)
        return (1.0 - cl_dice).mean()
