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


def test_smaller_window_preserves_batch_and_matches_label_grid():
    cfg = DetectorConfig(size=32, in_chans=8, start_idx=0, end_idx=8)
    model = DetectorModel(cfg, pred_shape=(32, 32))
    output = model(torch.randn(2, 1, 8, 32, 32))
    assert output.shape == (2, 1, 2, 2)
    assert torch.isfinite(model.loss_func(output, torch.zeros_like(output)))
