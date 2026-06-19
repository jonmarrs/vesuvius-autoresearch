# tests/test_ink_repro_losses.py
import torch

from repro.ink_segformer.losses import bce_dice_loss
from repro.ink_segformer.model import InkSegformer


def test_bce_dice_zero_on_perfect_prediction():
    target = (torch.rand(2, 1, 16, 16) > 0.5).float()
    logits = torch.where(target > 0.5, 12.0, -12.0)  # near-perfect logits
    assert bce_dice_loss(logits, target).item() < 0.05


def test_overfits_a_tiny_separable_batch():
    # ink = a centered square that is BRIGHT in the volume -> a spatially coherent,
    # SegFormer-fittable signal (per-pixel random targets are not learnable through
    # a downsampling encoder, so they make a useless overfit proof).
    torch.manual_seed(0)
    x = torch.rand(2, 1, 8, 64, 64) * 0.2
    target = torch.zeros(2, 1, 64, 64)
    target[:, :, 16:48, 16:48] = 1.0
    x[:, :, :, 16:48, 16:48] += 0.8  # bright where ink
    model = InkSegformer(stem_channels=8, encoder="mit_b3", encoder_weights=None)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)
    for _ in range(60):
        opt.zero_grad()
        loss = bce_dice_loss(model(x), target)
        loss.backward()
        opt.step()
    with torch.no_grad():
        acc = ((torch.sigmoid(model(x)) > 0.5).float() == target).float().mean()
    assert acc.item() > 0.95  # the clean-room pipeline can learn
