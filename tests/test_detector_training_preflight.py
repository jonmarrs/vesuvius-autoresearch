"""Training boundaries exercised with synthetic inputs and CPU-only trainers."""

import importlib
import os

import cv2
import numpy as np
import pytest

from vesuvius_autoresearch.detector import cli, data
from vesuvius_autoresearch.detector.config import DetectorConfig

training = importlib.import_module("vesuvius_autoresearch.detector.train")


def _fragments(tmp_path):
    cfg = DetectorConfig(
        data_root=str(tmp_path),
        train_fragment_ids=["train"],
        valid_fragment_id="valid",
        start_idx=0,
        end_idx=2,
        in_chans=2,
        size=16,
        tile_size=16,
        stride=16,
    )
    for fid in ("train", "valid"):
        root = tmp_path / fid
        (root / "layers").mkdir(parents=True)
        image = np.full((32, 32), 100, np.uint8)
        for index in range(2):
            assert cv2.imwrite(str(root / "layers" / f"{index:02d}.tif"), image)
        assert cv2.imwrite(str(root / f"{fid}_mask.png"), np.full_like(image, 255))
        image[:, ::2] = 255
        image[:, 1::2] = 0
        assert cv2.imwrite(str(root / f"{fid}_inklabels.png"), image)
    return cfg


@pytest.mark.parametrize("kind", ["directory symlink", "file symlink", "hard link"])
def test_aliases_cannot_hide_training_validation_layer_overlap(tmp_path, kind):
    cfg = _fragments(tmp_path)
    source = tmp_path / "train/layers"
    target = tmp_path / "valid/layers"
    if kind == "directory symlink":
        for path in target.iterdir():
            path.unlink()
        target.rmdir()
        target.symlink_to(source, target_is_directory=True)
    else:
        target = target / "01.tif"
        target.unlink()
        # Cross-depth aliases are also overlap, not just matching file names.
        source = source / "00.tif"
        if kind == "file symlink":
            target.symlink_to(source)
        else:
            os.link(source, target)
    with pytest.raises(ValueError, match="CT layer overlap"):
        data.build_datasets(cfg)


def test_duplicate_training_ids_fail_before_any_image_read(tmp_path, monkeypatch):
    reads = []
    monkeypatch.setattr(data, "read_image_mask", lambda *args: reads.append(args))
    cfg = DetectorConfig(data_root=str(tmp_path), train_fragment_ids=["train", "train"])
    with pytest.raises(ValueError, match="duplicate training fragment"):
        data.build_datasets(cfg)
    assert reads == []


def test_all_fragment_names_are_checked_before_any_image_read(tmp_path, monkeypatch):
    reads = []
    monkeypatch.setattr(data, "read_image_mask", lambda *args: reads.append(args))
    cfg = DetectorConfig(data_root=str(tmp_path), valid_fragment_id="../outside")
    with pytest.raises(ValueError, match="filename"):
        data.build_datasets(cfg)
    assert reads == []


def test_a_missing_validation_layer_fails_before_training_images_are_decoded(
    tmp_path, monkeypatch
):
    cfg = _fragments(tmp_path)
    (tmp_path / "valid/layers/01.tif").unlink()
    reads = []
    monkeypatch.setattr(data, "read_image_mask", lambda *args: reads.append(args))
    with pytest.raises((OSError, ValueError), match="valid/layers/01.tif"):
        data.build_datasets(cfg)
    assert reads == []


def test_distinct_files_with_identical_contents_remain_usable(tmp_path):
    cfg = _fragments(tmp_path)
    train, valid, _, shape = data.build_datasets(cfg)
    assert len(train) == len(valid) == 4
    assert shape == (32, 32)


def test_symlinks_to_distinct_ct_sources_remain_usable(tmp_path):
    cfg = _fragments(tmp_path)
    layer = tmp_path / "valid/layers/00.tif"
    source = tmp_path / "separate-source.tif"
    layer.rename(source)
    layer.symlink_to(source)
    train, valid, _, _ = data.build_datasets(cfg)
    assert len(train) == len(valid) == 4


def test_special_layer_files_are_refused_without_opening_them(tmp_path):
    if not hasattr(os, "mkfifo"):
        pytest.skip("POSIX FIFO")
    cfg = _fragments(tmp_path)
    layer = tmp_path / "valid/layers/00.tif"
    layer.unlink()
    os.mkfifo(layer)
    with pytest.raises(ValueError, match="regular file"):
        data.build_datasets(cfg)


@pytest.mark.parametrize(
    "options",
    [
        {"max_epochs": 0},
        {"max_epochs": -1},
        {"max_epochs": True},
        {"max_epochs": 1.5},
        {"limit_batches": 0},
        {"limit_batches": -2},
        {"limit_batches": True},
        {"limit_batches": 1.5},
        {"limit_batches": float("nan")},
        {"limit_batches": float("inf")},
        {"limit_batches": 0.0},
        {"limit_batches": -0.5},
        {"limit_batches": "1"},
    ],
)
def test_invalid_training_overrides_fail_before_data_reads_or_output_creation(
    tmp_path, monkeypatch, options
):
    def unexpected(*args, **kwargs):
        pytest.fail("invalid override reached dataset construction")

    monkeypatch.setattr(training, "build_datasets", unexpected)
    output = tmp_path / "models"
    with pytest.raises(ValueError, match="max_epochs|limit_batches"):
        training.train(DetectorConfig(model_dir=str(output)), **options)
    assert not output.exists()


@pytest.mark.parametrize("max_epochs,limit", [(None, None), (2, 1), (1, 0.5)])
def test_valid_budgets_reach_the_trainer_and_model_config(
    tmp_path, monkeypatch, max_epochs, limit
):
    configurations = []

    def datasets(cfg):
        configurations.append(cfg)
        return [0, 1], [0, 1, 2], [], (32, 32)

    monkeypatch.setattr(training, "build_datasets", datasets)
    monkeypatch.setattr(
        training, "build_model", lambda cfg, **kwargs: configurations.append(cfg)
    )
    options = {}

    class Trainer:
        def __init__(self, **kwargs):
            options.update(kwargs)
            self.callback = kwargs["callbacks"][0]

        def fit(self, *args, **kwargs):
            path = tmp_path / "saved.ckpt"
            path.touch()
            self.callback.best_model_path = str(path)

    monkeypatch.setattr(training.pl, "Trainer", Trainer)
    cfg = DetectorConfig(model_dir=str(tmp_path), train_batch_size=2, num_workers=0)
    training.train(cfg, max_epochs=max_epochs, limit_batches=limit)
    effective = 12 if max_epochs is None else max_epochs
    assert [c.epochs for c in configurations] == [effective, effective]
    assert cfg.epochs == 12
    assert options["max_epochs"] == effective
    assert options["limit_train_batches"] == options["limit_val_batches"] == limit


def test_cli_exposes_bounded_training_without_changing_config_defaults(monkeypatch):
    seen = []

    def train(cfg, **options):
        seen.append((cfg.epochs, options))
        return "small.ckpt"

    monkeypatch.setattr(training, "train", train)
    cli.main(["train", "--max-epochs", "1", "--limit-batches", "2"])
    assert seen == [(12, {"max_epochs": 1, "limit_batches": 2})]


@pytest.mark.parametrize("flag", ["--max-epochs", "--limit-batches"])
@pytest.mark.parametrize("value", ["0", "-1", "1.5"])
def test_cli_rejects_invalid_training_limits_before_work(flag, value, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("invalid CLI limit reached training")

    monkeypatch.setattr(training, "train", unexpected)
    with pytest.raises(SystemExit) as exc:
        cli.main(["train", flag, value])
    assert exc.value.code == 2
