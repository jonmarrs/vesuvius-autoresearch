import torch

from scripts.overfit_probe import brightness_control_target


def test_brightness_control_target_thresholds_zmean_vs_patch_mean():
    x = torch.zeros(1, 1, 2, 2, 2)
    x[0, 0, :, 0, 0] = 0.9
    x[0, 0, :, 0, 1] = 0.1
    x[0, 0, :, 1, 0] = 0.1
    x[0, 0, :, 1, 1] = 0.1
    t = brightness_control_target(x)
    assert t.shape == (1, 1, 2, 2)
    assert t[0, 0, 0, 0] == 1.0
    assert t[0, 0, 0, 1] == 0.0 and t[0, 0, 1, 0] == 0.0 and t[0, 0, 1, 1] == 0.0


from torch import nn

from scripts.overfit_probe import overfit


class _TinyNet(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.conv = nn.Conv3d(c, 1, 1)

    def forward(self, x):  # [K,C,nl,H,W] -> [K,1,H,W]
        return self.conv(x).mean(dim=2)


def test_overfit_drives_separable_target_auc_high():
    torch.manual_seed(0)
    K, C, nl, H, W = 2, 1, 4, 8, 8
    x = torch.rand(K, C, nl, H, W)
    target = (x[:, 0].mean(dim=1, keepdim=True) > 0.5).float()  # [K,1,H,W], learnable
    model = _TinyNet(C)
    curve = overfit(model, x, target, steps=500, lr=3e-2, log_every=100)
    assert curve[-1][0] == 500
    assert curve[-1][1] > 0.9
