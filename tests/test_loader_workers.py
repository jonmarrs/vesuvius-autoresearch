"""Training batches prepared in worker processes must be the batches the
training process would have prepared itself, in the same order."""

import functools
import multiprocessing
import os

import pytest
import torch
import train
from loader_worker_data import Finalized, IndexSeeded, NotRead, Unread

from vesuvius_autoresearch.core import vesuvius_loader


def _batches(loader, count):
    batches, it = [], iter(loader)
    for _ in range(count):
        try:
            batches.append(next(it))
        except StopIteration:  # train.py re-iterates: a fresh permutation
            it = iter(loader)
            batches.append(next(it))
    return batches


def test_workers_prepare_the_same_batches_in_the_same_order():
    data = IndexSeeded(40)
    inline = _batches(train.shuffled_loader(data, 4, seed=7), 14)
    spawned = _batches(train.shuffled_loader(data, 4, seed=7, workers=2), 14)
    for (x0, i0, _), (x1, i1, _) in zip(inline, spawned, strict=True):
        assert torch.equal(i0, i1) and torch.equal(x0, x1)
    # 14 batches of 4 cross one pass of 40: the second pass reshuffles.
    assert [int(i) for i in inline[10][1]] != [int(i) for i in inline[0][1]]


def test_the_workers_warnings_reach_the_training_process(monkeypatch):
    monkeypatch.setattr(
        vesuvius_loader, "_WARNING_COUNTS", vesuvius_loader.defaultdict(int)
    )
    manager = multiprocessing.get_context("spawn").Manager()
    shared = manager.dict()
    share = functools.partial(
        vesuvius_loader.share_warning_counts, shared, manager.Lock()
    )
    loader = train.shuffled_loader(
        IndexSeeded(30), 5, seed=1, workers=2, worker_init_fn=share
    )
    assert sum(len(batch[1]) for batch in loader) == 30
    assert dict(shared) == {"test_fallback": 10}  # indices 0, 3, ..., 27
    assert vesuvius_loader.warning_counts() == {}  # none in this process
    manager.shutdown()


def test_workers_exit_without_finalizing(tmp_path):
    """Stopping mid-pass left a worker's queue thread releasing a batch, and
    interpreter finalization ended it inside PyTorch's C++: SIGABRT
    ("terminate called without an active exception"), 1 in 3 stops on Fr47."""
    loader = train.shuffled_loader(Finalized(40, str(tmp_path)), 4, seed=3, workers=2)
    it = iter(loader)
    for _ in range(3):  # mid-pass, batches in flight
        next(it)
    pids = sorted(w.pid for w in it._workers)
    del it
    assert len(pids) == 2
    assert sorted(os.listdir(tmp_path)) == []  # no worker ran its exit handlers
    assert sum(len(b[1]) for b in loader) == 40  # and a pass read to the end
    assert os.listdir(tmp_path) == []


@pytest.mark.parametrize(
    "value,cpus,expected",
    [(None, 4, 3), (None, 16, 3), (None, 2, 1), (None, 1, 0), ("0", 4, 0), ("5", 4, 5)],
)
def test_the_worker_count(monkeypatch, value, cpus, expected):
    monkeypatch.setattr(train.os, "cpu_count", lambda: cpus)
    if value is None:
        monkeypatch.delenv(train.LOADER_WORKERS_ENV, raising=False)
    else:
        monkeypatch.setenv(train.LOADER_WORKERS_ENV, value)
    assert train.loader_workers() == expected


@pytest.mark.parametrize("value", ["-1", "two"])
def test_a_bad_worker_count_is_refused(monkeypatch, value):
    monkeypatch.setenv(train.LOADER_WORKERS_ENV, value)
    with pytest.raises(ValueError, match="integer >= 0"):
        train.loader_workers()


def test_train_prepares_its_training_batches_in_spawned_workers(
    tmp_path, monkeypatch, capsys
):
    """Through train.train: the labeled training loader ships its dataset and
    the warning-sharing init to spawned workers, which read its first batch."""
    monkeypatch.chdir(tmp_path)  # no incumbent to warm-start from
    monkeypatch.setenv(train.LOADER_WORKERS_ENV, "2")
    for fragment in ("train", "val"):
        (tmp_path / fragment).mkdir()
        (tmp_path / fragment / "inklabels.png").write_bytes(b"")
    config = train.ExperimentConfig(
        num_layers=16,
        uris=[str(tmp_path / "train" / "surface_volume.zarr")],
        val_uri=str(tmp_path / "val" / "surface_volume.zarr"),
        use_wandb=False,
    )
    monkeypatch.setattr(train, "VesuviusLabeledDataset", lambda *a, **k: Unread())
    monkeypatch.setattr(train, "probe_validation_read", lambda dataset: None)
    monkeypatch.setattr(train, "check_validation_inputs", lambda *args: None)
    monkeypatch.setattr(
        train,
        "build_model",
        lambda *args: train.GenericMultiTaskWrapper(torch.nn.Conv3d(1, 1, 1)),
    )
    with pytest.raises(NotRead, match="in DataLoader worker process"):
        train.train(config)
    assert "Training loader workers: 2" in capsys.readouterr().out


def test_each_run_draws_its_training_crops_from_its_own_seed(
    tmp_path, monkeypatch, capsys
):
    """The labeled and UA-MT datasets draw entry i's crop (lateral jitter, read
    depth) from RandomState(i + seed). Built without a seed, entry i had the
    same crop in every run: Fr47's 7,345 fixed crops held 74.8% of its
    labelled ink pixels (reports/training_crop_coverage.json)."""
    monkeypatch.chdir(tmp_path)
    for fragment in ("train", "val"):
        (tmp_path / fragment).mkdir()
        (tmp_path / fragment / "inklabels.png").write_bytes(b"")
    train_uri = str(tmp_path / "train" / "surface_volume.zarr")
    config = train.ExperimentConfig(
        num_layers=16,
        uris=[train_uri],
        val_uri=str(tmp_path / "val" / "surface_volume.zarr"),
        use_wandb=False,
        use_uamt=True,
        unlabeled_uris=[train_uri],
    )
    labeled, unlabeled = [], []

    def labeled_dataset(*args, **kwargs):
        labeled.append(kwargs.get("seed"))
        return Unread()

    def unlabeled_dataset(uri, config, seed=None):
        unlabeled.append(seed)
        return Unread()

    monkeypatch.setattr(train, "VesuviusLabeledDataset", labeled_dataset)
    monkeypatch.setattr(train, "unlabeled_dataset", unlabeled_dataset)
    monkeypatch.setattr(train, "probe_validation_read", lambda dataset: None)
    monkeypatch.setattr(train, "check_validation_inputs", lambda *args: None)
    monkeypatch.setattr(
        train,
        "build_model",
        lambda *args: train.GenericMultiTaskWrapper(torch.nn.Conv3d(1, 1, 1)),
    )
    seeds = []
    for _ in range(2):
        with pytest.raises(NotRead):
            train.train(config)
        out = capsys.readouterr().out
        seeds.append(int(out.split("Training sampling seed: ")[1].split()[0]))
    assert seeds[0] != seeds[1]
    # Validation's fixed draw (seed 42) first, then the run's training draw.
    assert labeled == [42, seeds[0], 42, seeds[1]]
    assert unlabeled == [seeds[0] + 1, seeds[1] + 1]
