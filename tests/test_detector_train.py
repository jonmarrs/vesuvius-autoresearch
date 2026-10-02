import os
import importlib
import pytest

from test_detector_data import _make_fake_fragment

from vesuvius_autoresearch.detector import train
from vesuvius_autoresearch.detector.config import DetectorConfig


def test_smoke_train_returns_checkpoint(tmp_path):
    root = str(tmp_path / "scrolls")
    _make_fake_fragment(root, "PHercParis2Fr47")
    _make_fake_fragment(root, "PHercParis2Fr143")
    cfg = DetectorConfig(
        data_root=root,
        model_dir=str(tmp_path / "models"),
        train_batch_size=2,
        num_workers=0,
        seed=0,
    )
    ckpt = train(cfg, max_epochs=1, limit_batches=2)
    assert os.path.exists(ckpt)


def test_validation_keeps_the_incomplete_batch(tmp_path, monkeypatch):
    module = importlib.import_module("vesuvius_autoresearch.detector.train")
    monkeypatch.setattr(module, "build_datasets", lambda cfg: ([0, 1], [0, 1, 2], [], (64, 64)))
    monkeypatch.setattr(module, "build_model", lambda *args, **kwargs: None)
    seen = []

    class Trainer:
        def __init__(self, **kwargs):
            self.checkpoint = kwargs["callbacks"][0]

        def fit(self, model, *, train_dataloaders, val_dataloaders):
            for batch in val_dataloaders:
                seen.extend(batch.tolist())
            path = tmp_path / "saved.ckpt"
            path.touch()
            self.checkpoint.best_model_path = str(path)

    monkeypatch.setattr(module.pl, "Trainer", Trainer)
    module.train(DetectorConfig(model_dir=str(tmp_path), train_batch_size=2, num_workers=0))
    assert seen == [0, 1, 2]


def test_training_rejects_batch_size_that_drops_all_samples(tmp_path, monkeypatch):
    module = importlib.import_module("vesuvius_autoresearch.detector.train")
    monkeypatch.setattr(module, "build_datasets", lambda cfg: ([0], [0], [], (64, 64)))
    with pytest.raises(ValueError, match="train_batch_size"):
        module.train(DetectorConfig(model_dir=str(tmp_path), train_batch_size=2, num_workers=0))


def test_training_does_not_return_a_nonexistent_checkpoint(tmp_path, monkeypatch):
    module = importlib.import_module("vesuvius_autoresearch.detector.train")
    monkeypatch.setattr(module, "build_datasets", lambda cfg: ([0, 1], [0], [], (64, 64)))
    monkeypatch.setattr(module, "build_model", lambda *args, **kwargs: None)

    class Trainer:
        def __init__(self, **kwargs):
            pass

        def fit(self, *args, **kwargs):
            pass  # e.g. a run with no training batches enabled

    monkeypatch.setattr(module.pl, "Trainer", Trainer)
    with pytest.raises(RuntimeError, match="without a checkpoint"):
        module.train(DetectorConfig(model_dir=str(tmp_path), train_batch_size=2, num_workers=0))
