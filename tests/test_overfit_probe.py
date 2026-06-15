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
