import os
import sys

import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "training"))

from train import compute_dice_loss, confidence_weight  # noqa: E402


def test_confidence_weight_zero_on_uncertain_band():
    target = torch.tensor([[0.0, 0.5, 1.0]])
    w = confidence_weight(target)
    assert torch.allclose(w, torch.tensor([[1.0, 0.0, 1.0]]))


def test_uncertain_pixels_contribute_zero_ink_gradient():
    torch.manual_seed(0)
    logits = torch.randn(1, 1, 4, 4, requires_grad=True)
    target = torch.full((1, 1, 4, 4), 0.5)
    w = confidence_weight(target)
    bce_map = torch.nn.functional.binary_cross_entropy_with_logits(
        logits, target.clamp(0, 1), reduction="none"
    )
    loss = (bce_map * w).sum() / w.sum().clamp_min(1.0)
    loss.backward()
    assert torch.allclose(logits.grad, torch.zeros_like(logits.grad))


def test_dice_loss_weight_is_noop_on_binary_target():
    pred = torch.randn(2, 1, 8, 8)
    target = (torch.rand(2, 1, 8, 8) > 0.5).float()
    w = confidence_weight(target)
    assert torch.allclose(
        compute_dice_loss(pred, target, weight=w), compute_dice_loss(pred, target)
    )
