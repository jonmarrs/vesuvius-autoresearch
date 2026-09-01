import os

from test_detector_data import _make_fake_fragment

from vesuvius_autoresearch.detector import train
from vesuvius_autoresearch.detector.config import DetectorConfig


def test_resenc_smoke_train_returns_checkpoint(tmp_path):
    root = str(tmp_path / "scrolls")
    _make_fake_fragment(root, "PHercParis2Fr47")
    _make_fake_fragment(root, "PHercParis2Fr143")
    cfg = DetectorConfig(
        data_root=root,
        model_dir=str(tmp_path / "models"),
        architecture="resenc",
        train_batch_size=2,
        num_workers=0,
        seed=0,
    )
    ckpt = train(cfg, max_epochs=1, limit_batches=2)
    assert os.path.exists(ckpt)
