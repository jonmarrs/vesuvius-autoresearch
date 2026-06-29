import numpy as np
import torch

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
    assert float(prob.min()) >= 0.0 and float(prob.max()) <= 1.0


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
