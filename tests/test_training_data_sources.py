"""Which files and slices a training run reads, and for which loss.

UA-MT's unlabeled reader ignored the depth band, although the 2026-10-14 review
and the depth-band test both took the production unlabeled volume (Fr47, also
the training volume) to be read in it; a pseudo-label replaced a fragment's
labels without a trace, in a production config whose pseudo_label_dir has been
set since 2026-05-03. See
docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-14_TRAINING_DATA_SOURCES.md.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest
import torch
import zarr
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "training"))

import train  # noqa: E402

from scripts.training.config import ExperimentConfig  # noqa: E402


def _volume(root, depth=33, labels=True):
    """A fragment whose slice z holds the value z, so a read shows its depth."""
    root.mkdir()
    volume = zarr.open(
        str(root / "surface_volume.zarr"),
        mode="w",
        shape=(depth, 32, 32),
        chunks=(depth, 32, 32),
        dtype="u1",
    )
    volume[:] = np.broadcast_to(
        np.arange(depth, dtype=np.uint8)[:, None, None], (depth, 32, 32)
    )
    if labels:
        Image.fromarray(np.zeros((32, 32), np.uint8)).save(root / "inklabels.png")
    return str(root / "surface_volume.zarr")


def _read_starts(dataset):
    return {round(float(dataset[i][0][0, 0, 0, 0]) * 255) for i in range(len(dataset))}


def _config(uri, **kwargs):
    return ExperimentConfig(
        num_layers=16, patch_size=16, depth_band=[1, 27], uris=[uri], **kwargs
    )


def test_a_training_volume_read_by_uamt_is_read_inside_the_band(tmp_path):
    """The production layout: unlabeled_uris is the training volume, 33 slices,
    band [1, 27), 24-slice reads. The band widened by the 4-slice margin is
    [0, 31), so reads start at 0-7; over the whole depth they started at 0-9."""
    uri = _volume(tmp_path / "Fr47")
    for spelling in (uri, uri + "/"):  # one volume, matched as inference matches
        dataset = train.unlabeled_dataset(spelling, _config(uri), seed=0)
        assert dataset.depth_range == (0, 31)
    starts = _read_starts(dataset)
    assert starts <= set(range(8)) and len(starts) > 1


@pytest.mark.parametrize("depth, labels", [(33, False), (33, True), (21, True)])
def test_any_other_unlabeled_volume_is_read_over_its_whole_depth(
    tmp_path, depth, labels
):
    """The band names the training volumes' slices; another volume, labeled or
    not, may number its own differently. A labeled 21-slice volume, which the
    band [1, 27) would not fit, trains as before."""
    training = _volume(tmp_path / "Fr47")
    other = _volume(tmp_path / "other", depth=depth, labels=labels)
    dataset = train.unlabeled_dataset(other, _config(training), seed=0)
    assert dataset.depth_range is None
    assert _read_starts(dataset) <= set(range(max(depth - 24, 0) + 1))
    if depth == 33:
        assert max(_read_starts(dataset)) > 7  # past the band's reads


def test_without_a_band_the_unlabeled_draws_are_unchanged(tmp_path):
    from vesuvius_autoresearch.core.vesuvius_loader import VesuviusS3Dataset

    uri = _volume(tmp_path / "Fr47")
    config = ExperimentConfig(num_layers=16, patch_size=16, uris=[uri])
    dataset = train.unlabeled_dataset(uri, config, seed=5)
    for i in range(len(dataset)):
        rng = np.random.RandomState(i + 5)  # the draw before depth ranges
        expected = rng.randint(0, 33 - 24 + 1)
        assert round(float(dataset[i][0][0, 0, 0, 0]) * 255) == expected
    assert isinstance(dataset, VesuviusS3Dataset)


def test_train_gives_uamt_the_band_for_a_training_volume(tmp_path, monkeypatch, capsys):
    """Through train.train: UA-MT's reader of the training volume gets the band,
    and the label file each training volume is read with is printed."""
    for fragment in ("train", "val"):
        (tmp_path / fragment).mkdir()
        (tmp_path / fragment / "inklabels.png").write_bytes(b"")
    uri = str(tmp_path / "train" / "surface_volume.zarr")
    config = ExperimentConfig(
        num_layers=16,
        depth_band=[17, 43],
        uris=[uri],
        val_uri=str(tmp_path / "val" / "surface_volume.zarr"),
        use_uamt=True,
        unlabeled_uris=[uri],
    )
    seen = {}

    class Stop(Exception):
        pass

    class Catalogue(torch.utils.data.Dataset):
        validation_inputs = None

        def __len__(self):
            return 10

        def __getitem__(self, i):
            raise AssertionError("not read")

    def labeled(uri, *args, **kwargs):
        return Catalogue()

    def unlabeled(uri, *args, **kwargs):
        seen["unlabeled"] = (kwargs.get("depth_band"), kwargs.get("depth_margin"))
        raise Stop

    monkeypatch.setattr(train, "VesuviusLabeledDataset", labeled)
    monkeypatch.setattr(train, "VesuviusS3Dataset", unlabeled)
    monkeypatch.setattr(train, "probe_validation_read", lambda dataset: None)
    monkeypatch.setattr(train, "check_validation_inputs", lambda *args: None)
    monkeypatch.setattr(
        train,
        "build_model",
        lambda *args: train.GenericMultiTaskWrapper(torch.nn.Conv3d(1, 1, 1)),
    )
    with pytest.raises(Stop):
        train.train(config)
    assert seen == {"unlabeled": ([17, 43], 4)}
    labels = os.path.join(str(tmp_path / "train"), "inklabels.png")
    assert f"Training labels for {uri}: {labels}" in capsys.readouterr().out


def test_a_pseudo_label_needs_confidence_weighting(tmp_path):
    """A <segment>_pseudo.png takes precedence over the fragment's labels; its
    uncertain band (PNG 128) is a target unless confidence weighting
    down-weights it."""
    uri = _volume(tmp_path / "Fr47")
    pseudo_dir = tmp_path / "pseudo_labels"
    pseudo_dir.mkdir()
    config = _config(uri, pseudo_label_dir=str(pseudo_dir))
    own = str(tmp_path / "Fr47" / "inklabels.png")
    assert train.training_label_path(uri, config) == own  # no pseudo-label yet

    pseudo = pseudo_dir / "Fr47_pseudo.png"
    Image.fromarray(np.full((32, 32), 128, np.uint8)).save(pseudo)
    with pytest.raises(ValueError, match="use_confidence_weight"):
        train.training_label_path(uri, config)
    weighted = _config(
        uri, pseudo_label_dir=str(pseudo_dir), use_confidence_weight=True
    )
    assert train.training_label_path(uri, weighted) == str(pseudo)


def test_a_training_volume_without_labels_is_refused(tmp_path):
    """It used to fall back to the unlabeled reader, whose two-item batches
    then failed to unpack at the first training step, after the model was built."""
    uri = _volume(tmp_path / "Fr47", labels=False)
    with pytest.raises(FileNotFoundError, match="no label file for training volume"):
        train.training_label_path(uri, _config(uri))


@pytest.mark.parametrize("problem", ["no labels", "unweighted pseudo-label"])
def test_train_refuses_a_label_file_before_validation_and_the_model(
    tmp_path, monkeypatch, problem
):
    """The label files are resolved first: a refusal comes in seconds, before
    the validation catalogue, the model or any reader is built."""
    uri = _volume(tmp_path / "Fr47", labels=problem != "no labels")
    pseudo_dir = tmp_path / "pseudo_labels"
    pseudo_dir.mkdir()
    if problem == "unweighted pseudo-label":
        Image.fromarray(np.zeros((32, 32), np.uint8)).save(
            pseudo_dir / "Fr47_pseudo.png"
        )

    def built_first(*args, **kwargs):
        raise AssertionError("built before the label files were checked")

    for name in (
        "build_validation_dataset",
        "build_model",
        "VesuviusLabeledDataset",
        "VesuviusS3Dataset",
    ):
        monkeypatch.setattr(train, name, built_first)
    expected = FileNotFoundError if problem == "no labels" else ValueError
    with pytest.raises(expected):
        train.train(_config(uri, pseudo_label_dir=str(pseudo_dir)))


def test_resolving_the_training_labels_prints_each(tmp_path, capsys):
    first, second = _volume(tmp_path / "Fr47"), _volume(tmp_path / "Fr53")
    config = ExperimentConfig(uris=[first, second])
    labels = train.resolve_training_labels(config)
    assert labels == {
        first: str(tmp_path / "Fr47" / "inklabels.png"),
        second: str(tmp_path / "Fr53" / "inklabels.png"),
    }
    out = capsys.readouterr().out
    assert all(f"Training labels for {u}: {p}" in out for u, p in labels.items())
