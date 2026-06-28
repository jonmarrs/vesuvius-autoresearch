import torch

from vesuvius_autoresearch.detector.config import DetectorConfig
from vesuvius_autoresearch.detector.model import DetectorModel


def test_forward_shape_and_finite_loss():
    cfg = DetectorConfig()
    model = DetectorModel(cfg, pred_shape=(64, 64))
    x = torch.randn(2, 1, cfg.in_chans, cfg.size, cfg.size)  # (B,1,C,H,W)
    out = model(x)
    assert out.shape == (2, 1, 4, 4)
    target = torch.rand(2, 1, 4, 4)
    loss = model.loss_func(out, target)
    assert torch.isfinite(loss)
