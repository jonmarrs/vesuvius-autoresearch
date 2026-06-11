import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.cldice_loss import SoftClDiceLoss, soft_skeletonize


def _cross_target(n=32):
    """A thin '+' shaped structure in a single (1,1,n,n) batch."""
    t = torch.zeros(1, 1, n, n)
    t[0, 0, n // 2, :] = 1.0
    t[0, 0, :, n // 2] = 1.0
    return t


def test_perfect_prediction_gives_near_zero_loss():
    target = _cross_target()
    logits = torch.where(target > 0.5, 8.0, -8.0)  # sigmoid ~= target
    loss = SoftClDiceLoss()(logits, target)
    assert loss.item() < 0.05


def test_broken_prediction_loses_more_than_perfect():
    target = _cross_target()
    perfect = torch.where(target > 0.5, 8.0, -8.0)
    broken = perfect.clone()
    # sever the horizontal bar in the middle -> fragmented centerline
    broken[0, 0, 16, 10:22] = -8.0
    loss_perfect = SoftClDiceLoss()(perfect, target).item()
    loss_broken = SoftClDiceLoss()(broken, target).item()
    assert loss_broken > loss_perfect + 0.05


def test_gradient_flows_to_logits():
    # The critical property the old BettiLoss lacked: a real gradient.
    target = _cross_target()
    logits = torch.where(target > 0.5, 2.0, -2.0).clone().requires_grad_(True)
    loss = SoftClDiceLoss()(logits, target)
    loss.backward()
    assert logits.grad is not None
    assert logits.grad.abs().sum().item() > 0.0


def test_soft_skeletonize_thins_a_solid_block():
    block = torch.zeros(1, 1, 16, 16)
    block[0, 0, 4:12, 4:12] = 1.0  # 8x8 solid square, mass 64
    skel = soft_skeletonize(block, iters=5)
    # The skeleton must carry less mass than the solid block.
    assert skel.sum().item() < block.sum().item()
    assert skel.sum().item() > 0.0


def test_loss_is_scalar_and_in_unit_range():
    target = _cross_target()
    logits = torch.randn(1, 1, 32, 32)
    loss = SoftClDiceLoss()(logits, target)
    assert loss.dim() == 0
    assert -1e-4 <= loss.item() <= 1.0 + 1e-4
