import torch

from vesuvius_autoresearch.detector.config import DetectorConfig
from vesuvius_autoresearch.detector.model_resenc import ResEncDetectorModel


def test_resenc_forward_shape_and_finite_loss():
    cfg = DetectorConfig(architecture="resenc")
    model = ResEncDetectorModel(cfg, pred_shape=(64, 64))
    x = torch.randn(2, 1, cfg.in_chans, cfg.size, cfg.size)  # (B,1,C,H,W)
    out = model(x)
    assert out.shape == (2, 1, cfg.size, cfg.size)
    target = torch.rand(2, 1, cfg.size, cfg.size)
    loss = model.loss_func(out, target)
    assert torch.isfinite(loss)
