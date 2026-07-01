import numpy as np
import torch
import torch.nn as nn

from vesuvius_autoresearch.detector.config import DetectorConfig
from vesuvius_autoresearch.detector.model import DetectorModel
from vesuvius_autoresearch.detector import infer
from vesuvius_autoresearch.detector import train
from test_detector_data import _make_fake_fragment


def test_infer_returns_prob_map_in_range(tmp_path):
    root = str(tmp_path)
    _make_fake_fragment(root, "PHercParis2Fr143", h=320, w=320)
    cfg = DetectorConfig(data_root=root)
    model = DetectorModel(cfg, pred_shape=(320, 320)).eval()
    prob = infer(cfg, checkpoint_path=None, fragment_id="PHercParis2Fr143", model=model)
    assert prob.ndim == 2
    assert prob.shape == (320, 320)  # unpadded fragment label shape, not the tile-padded shape
    assert float(prob.min()) >= 0.0 and float(prob.max()) <= 1.0


def test_infer_normalizes_input_like_training(tmp_path):
    # Root-cause regression: training/valid apply A.Normalize (divide by 255), so the
    # model is trained on inputs in ~[0,1]. infer() must feed the same scale, not raw
    # 0-200 pixel values, or the held-out detector collapses to ~chance.
    root = str(tmp_path)
    _make_fake_fragment(root, "PHercParis2Fr143", h=320, w=320)  # pixels up to ~200
    cfg = DetectorConfig(data_root=root)
    model = DetectorModel(cfg, pred_shape=(320, 320)).eval()
    seen = []
    model.backbone.register_forward_pre_hook(
        lambda m, inp: seen.append(float(inp[0].abs().max())))
    infer(cfg, checkpoint_path=None, fragment_id="PHercParis2Fr143", model=model)
    assert seen, "model was never called"
    assert max(seen) <= 1.5, f"infer fed un-normalized inputs (max={max(seen):.1f})"


def test_infer_batching_matches_single_patch(tmp_path):
    # Batched inference must be numerically equivalent to single-patch (batch_size=1).
    root = str(tmp_path)
    _make_fake_fragment(root, "PHercParis2Fr143", h=192, w=192)
    cfg = DetectorConfig(data_root=root)
    model = DetectorModel(cfg, pred_shape=(192, 192)).eval()
    p1 = infer(cfg, None, "PHercParis2Fr143", model=model, batch_size=1)
    pB = infer(cfg, None, "PHercParis2Fr143", model=model, batch_size=16)
    assert p1.shape == pB.shape
    assert np.allclose(p1, pB, atol=1e-4)


def test_infer_loads_checkpoint_from_path(tmp_path):
    # Regression: the saved checkpoint embeds the LR scheduler, which PyTorch 2.6's
    # weights_only=True default rejects. infer() must load it (weights_only=False).
    root = str(tmp_path / "scrolls")
    _make_fake_fragment(root, "PHercParis2Fr47")
    _make_fake_fragment(root, "PHercParis2Fr143", h=320, w=320)
    cfg = DetectorConfig(data_root=root, model_dir=str(tmp_path / "models"),
                         train_batch_size=2, num_workers=0, seed=0)
    ckpt = train(cfg, max_epochs=1, limit_batches=2)
    prob = infer(cfg, checkpoint_path=ckpt, fragment_id="PHercParis2Fr143")
    assert prob.ndim == 2
    assert float(prob.min()) >= 0.0 and float(prob.max()) <= 1.0


class _FullResStub(nn.Module):
    """Minimal full-resolution model: (B,1,C,H,W) -> (B,1,H,W)."""
    def __init__(self, cfg):
        super().__init__()
        self.conv = nn.Conv2d(cfg.in_chans, 1, 3, padding=1)

    def forward(self, x):
        return self.conv(x[:, 0])


def test_infer_handles_full_resolution_output(tmp_path):
    root = str(tmp_path)
    _make_fake_fragment(root, "PHercParis2Fr143", h=192, w=192)
    cfg = DetectorConfig(data_root=root, architecture="resenc")
    model = _FullResStub(cfg).eval()
    prob = infer(cfg, checkpoint_path=None, fragment_id="PHercParis2Fr143", model=model)
    assert prob.shape == (192, 192)
    assert float(prob.min()) >= 0.0 and float(prob.max()) <= 1.0


def test_infer_loads_resenc_checkpoint_from_path(tmp_path):
    # Regression: infer must load the ResEnc model class for resenc checkpoints, not the
    # TimeSformer DetectorModel (which raises a state_dict mismatch). The full-res test
    # above injects model=, bypassing the checkpoint-load path; this exercises it.
    root = str(tmp_path / "scrolls")
    _make_fake_fragment(root, "PHercParis2Fr47")
    _make_fake_fragment(root, "PHercParis2Fr143", h=320, w=320)
    cfg = DetectorConfig(data_root=root, model_dir=str(tmp_path / "models"),
                         architecture="resenc", train_batch_size=2, num_workers=0, seed=0)
    ckpt = train(cfg, max_epochs=1, limit_batches=2)
    prob = infer(cfg, checkpoint_path=ckpt, fragment_id="PHercParis2Fr143")
    assert prob.ndim == 2
    assert float(prob.min()) >= 0.0 and float(prob.max()) <= 1.0
