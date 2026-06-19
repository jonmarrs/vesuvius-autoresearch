# tests/test_ink_repro_losses.py
import torch

from repro.ink_segformer.losses import bce_dice_loss
from repro.ink_segformer.model import InkSegformer


def test_bce_dice_zero_on_perfect_prediction():
    target = (torch.rand(2, 1, 16, 16) > 0.5).float()
    logits = torch.where(target > 0.5, 12.0, -12.0)  # near-perfect logits
    assert bce_dice_loss(logits, target).item() < 0.05


def test_overfits_a_tiny_separable_batch():
    # ink = whether the depth-mean pixel exceeds 0.5 -> learnable from the input
    torch.manual_seed(0)
    x = torch.rand(2, 1, 8, 64, 64)
    target = (x[:, 0].mean(1, keepdim=True) > 0.5).float()  # [2,1,64,64]
    model = InkSegformer(stem_channels=8, encoder="mit_b3", encoder_weights=None)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)
    for _ in range(60):
        opt.zero_grad()
        loss = bce_dice_loss(model(x), target)
        loss.backward()
        opt.step()
    with torch.no_grad():
        acc = ((torch.sigmoid(model(x)) > 0.5).float() == target).float().mean()
    assert acc.item() > 0.85  # the clean-room pipeline can learn
