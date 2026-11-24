"""Which files and slices a training run reads, and for which loss.

UA-MT's unlabeled reader ignored the depth band, although the 2026-10-14 review
and the depth-band test both took the production unlabeled volume (Fr47, also
the training volume) to be read in it; a pseudo-label replaced a fragment's
labels without a trace, in a production config whose pseudo_label_dir has been
set since 2026-05-03. See
docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-14_TRAINING_DATA_SOURCES.md.
"""

from __future__ import annotations

import json
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


@pytest.mark.parametrize("kind", ["labeled", "uamt"])
@pytest.mark.parametrize("linked_level", [False, True])
def test_heldout_overlap_stops_the_real_trainer_before_labels_or_gpu(
    tmp_path, monkeypatch, kind, linked_level
):
    validation = _volume(tmp_path / "heldout")
    candidate = validation
    if linked_level:
        group = tmp_path / "other volume.zarr"
        zarr.open_group(str(group), mode="w")
        (group / "0").symlink_to(validation, target_is_directory=True)
        candidate = group.as_uri()
    selected = _config(
        candidate if kind == "labeled" else _volume(tmp_path / "training"),
        val_uri=validation,
        use_uamt=kind == "uamt",
        unlabeled_uris=[candidate + "/"],
    )

    def too_early(*args, **kwargs):
        pytest.fail("data or GPU setup reached before split validation")

    monkeypatch.setattr(train.torch, "set_float32_matmul_precision", too_early)
    monkeypatch.setattr(train, "resolve_training_labels", too_early)
    with pytest.raises(ValueError, match="overlaps val_uri"):
        train.train(selected)


@pytest.mark.parametrize(
    "target", ["best_model.pt", "training/inklabels.png", "active.json", "linked CT"]
)
def test_checkpoint_collision_stops_the_real_trainer_before_gpu(
    tmp_path, monkeypatch, target
):
    uri = _volume(tmp_path / "training")
    if target == "linked CT":
        chunk = Path(uri) / "0.0.0"
        assert chunk.is_file()
        group = tmp_path / "linked.zarr"
        zarr.open_group(str(group), mode="w")
        (group / "0").symlink_to(uri, target_is_directory=True)
        uri, target = group.as_uri(), str(chunk)
    selected = _config(uri, checkpoint_out=target)
    monkeypatch.chdir(tmp_path)

    def too_early(*args, **kwargs):
        pytest.fail("GPU setup reached before output preflight")

    monkeypatch.setattr(train.torch, "set_float32_matmul_precision", too_early)
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="artifact collision"):
        train.train(selected, config_path="active.json")
    assert {
        str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
    } == before


def test_cycle_checkpoint_helper_cannot_overwrite_incumbent_in_experiment_mode(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    incumbent = tmp_path / "best_model.pt"
    incumbent.write_bytes(b"original incumbent")
    with pytest.raises(ValueError, match="artifact collision"):
        train.save_cycle_checkpoints(
            {"model": "must not be written"}, "best_model.pt", True
        )
    assert incumbent.read_bytes() == b"original incumbent"


def test_visible_symlink_labels_are_protected_before_real_training(
    tmp_path, monkeypatch
):
    uri = _volume(tmp_path / "source")
    visible = tmp_path / "visible"
    visible.mkdir()
    alias = visible / "volume.zarr"
    alias.symlink_to(uri, target_is_directory=True)
    labels = visible / "inklabels.png"
    labels.write_bytes(b"visible labels")
    selected = _config(str(alias), checkpoint_out=str(labels))

    def too_early(*args, **kwargs):
        pytest.fail("GPU setup reached before protecting visible labels")

    monkeypatch.setattr(train.torch, "set_float32_matmul_precision", too_early)
    with pytest.raises(ValueError, match="artifact collision"):
        train.train(selected)
    assert labels.read_bytes() == b"visible labels"


def test_ablation_entrypoint_protects_its_active_config_before_gpu(
    tmp_path, monkeypatch
):
    import json

    from scripts import train_with_new_augs as entry

    uri = _volume(tmp_path / "training")
    path = tmp_path / "experiment.json"
    path.write_text(json.dumps({"uris": [uri], "checkpoint_out": str(path)}))
    before = path.read_bytes()
    monkeypatch.setattr(
        entry.torch.multiprocessing, "set_start_method", lambda *args: None
    )

    def too_early(*args, **kwargs):
        pytest.fail("GPU setup reached before active-config protection")

    monkeypatch.setattr(entry.torch, "set_float32_matmul_precision", too_early)
    monkeypatch.setattr(sys, "argv", ["train_with_new_augs.py", "--config", str(path)])
    with pytest.raises(ValueError, match="artifact collision"):
        entry.main()
    assert path.read_bytes() == before


def test_periodic_checkpoint_checks_the_active_config_before_evaluation(tmp_path):
    selected = _config("train.zarr", checkpoint_out=str(tmp_path / "trial.pt"))
    active = tmp_path / "trial.pt.step3.pt"
    active.write_bytes(b"active configuration")
    with pytest.raises(ValueError, match="artifact collision"):
        train.periodic_pixel_auc_eval(
            object(), object(), selected, "cpu", 3, 1.5, config_path=active
        )
    assert active.read_bytes() == b"active configuration"


def _volume(root, depth=33, labels=True, **array_options):
    """A fragment whose slice z holds the value z, so a read shows its depth."""
    root.mkdir()
    volume = zarr.open(
        str(root / "surface_volume.zarr"),
        mode="w",
        shape=(depth, 32, 32),
        chunks=(depth, 32, 32),
        dtype="u1",
        **array_options,
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


@pytest.mark.parametrize("workers", [0, 2])
def test_fallback_reports_only_count_this_training_run(tmp_path, monkeypatch, workers):
    from vesuvius_autoresearch.core import vesuvius_loader

    class CpuTorch:
        def __getattr__(self, name):
            return getattr(torch, name)

        def device(self, name):
            return torch.device("cpu")

    training_workers = []

    class TrackedLoader(torch.utils.data.DataLoader):
        def __iter__(self):
            iterator = super().__iter__()
            training_workers.extend(getattr(iterator, "_workers", ()))
            return iterator

    collect_validation = train.collect_validation_predictions

    def validate_after_worker_exit(*args, **kwargs):
        assert len(training_workers) == workers
        assert all(not worker.is_alive() for worker in training_workers)
        training_workers.clear()
        return collect_validation(*args, **kwargs)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(train.LOADER_WORKERS_ENV, str(workers))
    monkeypatch.setattr(train, "torch", CpuTorch())
    monkeypatch.setattr(train, "DataLoader", TrackedLoader)
    monkeypatch.setattr(
        train, "collect_validation_predictions", validate_after_worker_exit
    )
    monkeypatch.setattr(
        vesuvius_loader, "_WARNING_COUNTS", vesuvius_loader.defaultdict(int)
    )
    monkeypatch.setattr(train, "AUGMENTATION_FALLBACKS", {"batchgeneratorsv2": 4})
    vesuvius_loader._warn_limited("labeled_zero_patch", "failure from a prior run")
    vesuvius_loader._warn_limited("ridge_fallback", "another warning from a prior run")
    uri = _volume(tmp_path / "train", depth=16, compressor=None)
    chunk = Path(uri) / "0.0.0"
    raw = chunk.read_bytes()
    chunk.write_bytes(raw[:-1])
    config = ExperimentConfig(
        uris=[uri],
        val_uri=_volume(tmp_path / "val", depth=16),
        num_layers=8,
        patch_size=16,
        batch_size=1,
        time_budget=0,
        use_uamt=True,
        unlabeled_uris=[_volume(tmp_path / "unlabeled", depth=16, labels=False)],
        checkpoint_out=str(tmp_path / "trial.pt"),
        cache_dir=str(tmp_path / "cache"),
        disable_augmentation=True,
        use_wandb=False,
    )
    monkeypatch.setattr(
        train,
        "build_model",
        lambda *args: train.GenericMultiTaskWrapper(torch.nn.Conv3d(1, 1, 1)),
    )
    result_path = tmp_path / "run_result.json"
    train.train(config)
    failed_read = json.loads(result_path.read_text())
    assert failed_read["steps"] == 1
    assert set(failed_read["loader_warnings"]) == {"labeled_zero_patch"}
    # A worker may also read prefetched patches from the four-position grid.
    assert (
        1
        <= failed_read["loader_warnings"]["labeled_zero_patch"]
        <= (4 if workers else 1)
    )
    assert failed_read["augmentation_fallbacks"] == {"batchgeneratorsv2": 0}
    assert failed_read["training_ct_reads"] == {
        "labeled": {
            "returned": 0,
            "raised": failed_read["loader_warnings"]["labeled_zero_patch"],
        },
        "unlabeled": {"returned": 1, "raised": 0},
    }

    chunk.write_bytes(raw)
    train.train(config)
    clean = json.loads(result_path.read_text())
    assert clean["steps"] == 1
    assert clean["loader_warnings"] == {}
    assert clean["augmentation_fallbacks"] == {"batchgeneratorsv2": 0}
    labeled = clean["training_ct_reads"]["labeled"]
    assert 1 <= labeled["returned"] <= (4 if workers else 1)
    assert labeled["raised"] == 0
    assert clean["training_ct_reads"]["unlabeled"] == {"returned": 1, "raised": 0}
    assert vesuvius_loader.warning_counts() == {
        "labeled_zero_patch": 1 if workers else 2,
        "ridge_fallback": 1,
    }


@pytest.mark.parametrize("catalog", [False, True])
def test_validation_file_uri_reads_the_same_catalog_and_tensors(tmp_path, catalog):
    from scripts.training.promotion import validation_inputs_fingerprint

    root = tmp_path / "heldout #1"
    uri = _volume(root, depth=24)
    positive = np.zeros((32, 32), dtype=np.uint8)
    positive[:16, :16] = 255
    Image.fromarray(positive).save(root / "inklabels_refined.png")
    Image.fromarray(positive).save(root / "mask.png")
    if catalog:
        (root / "patches.json").write_text('{"patches":[{"y":16,"x":16}]}')
    config = ExperimentConfig(
        val_uri=uri, num_layers=16, patch_size=16, cache_dir=str(tmp_path / "cache")
    )
    plain = train.build_validation_dataset(config)
    config.val_uri = Path(uri).as_uri().replace("file://", "file://localhost", 1)
    linked = train.build_validation_dataset(config)
    assert linked.validation_inputs == plain.validation_inputs
    assert validation_inputs_fingerprint(config.val_uri) == plain.validation_inputs
    np.testing.assert_array_equal(linked.valid_coords, plain.valid_coords)
    assert len(plain) == 1
    assert all(torch.equal(a, b) for a, b in zip(linked[0], plain[0], strict=True))


def test_trainer_reads_sidecars_beside_a_file_uri_volume_alias(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(train.LOADER_WORKERS_ENV, "0")
    stored = _volume(tmp_path / "stored", depth=24)
    visible = tmp_path / "visible #1"
    visible.mkdir()
    alias = visible / "surface_volume.zarr"
    alias.symlink_to(stored, target_is_directory=True)
    (visible / "patches.json").write_text('{"patches":[{"y":16,"x":16}]}')
    pseudo = tmp_path / "pseudo"
    pseudo.mkdir()
    Image.fromarray(np.full((32, 32), 255, np.uint8)).save(
        pseudo / "visible #1_pseudo.png"
    )
    config = ExperimentConfig(
        val_uri=_volume(tmp_path / "heldout", depth=24),
        uris=[alias.as_uri()],
        num_layers=16,
        patch_size=16,
        cache_dir=str(tmp_path / "cache"),
        use_wandb=False,
        pseudo_label_dir=str(pseudo),
        use_confidence_weight=True,
    )

    def check(dataset, *args, **kwargs):
        assert dataset.valid_coords.tolist() == [[16, 16]]
        assert torch.all(dataset[0][1] == 1)
        raise _ReachedTheLoader

    monkeypatch.setattr(train, "shuffled_loader", check)
    monkeypatch.setattr(
        train,
        "build_model",
        lambda *args: train.GenericMultiTaskWrapper(torch.nn.Conv3d(1, 1, 1)),
    )
    with pytest.raises(_ReachedTheLoader):
        train.train(config)


def test_file_uri_pseudo_label_is_protected_before_the_trainer_can_write(
    tmp_path, monkeypatch
):
    root = tmp_path / "training #1"
    uri = _volume(root)
    pseudo = tmp_path / "pseudo"
    pseudo.mkdir()
    label = pseudo / "training #1_pseudo.png"
    label.write_bytes(b"existing pseudo label")
    config = _config(
        Path(uri).as_uri(),
        checkpoint_out=str(label),
        pseudo_label_dir=str(pseudo),
        use_confidence_weight=True,
    )
    monkeypatch.setattr(
        train.torch,
        "set_float32_matmul_precision",
        lambda *args: pytest.fail("reached model setup"),
    )
    with pytest.raises(ValueError, match="artifact collision"):
        train.train(config)
    assert label.read_bytes() == b"existing pseudo label"


@pytest.mark.parametrize("kind", ["refined", "pseudo", "mask"])
@pytest.mark.parametrize("strict", [False, True])
def test_selected_training_images_cannot_disappear_before_loading(
    tmp_path, monkeypatch, kind, strict
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(train.LOADER_WORKERS_ENV, "0")
    root = tmp_path / "training"
    uri = _volume(root, depth=24)
    val = _volume(tmp_path / "heldout", depth=24)
    labeled = Image.fromarray(np.full((32, 32), 255, np.uint8))
    labeled.save(root / "inklabels.png")
    pseudo_dir = tmp_path / "pseudo"
    pseudo_dir.mkdir()
    selected = {
        "refined": root / "inklabels_refined.png",
        "pseudo": pseudo_dir / "training_pseudo.png",
        "mask": root / "mask.png",
    }[kind]
    labeled.save(selected)
    config = ExperimentConfig(
        val_uri=val,
        uris=[uri],
        num_layers=16,
        patch_size=16,
        cache_dir=str(tmp_path / "cache"),
        use_wandb=False,
        strict_training_reads=strict,
        pseudo_label_dir=str(pseudo_dir) if kind == "pseudo" else None,
        use_confidence_weight=kind == "pseudo",
    )
    monkeypatch.setattr(
        train,
        "build_model",
        lambda *args: train.GenericMultiTaskWrapper(torch.nn.Conv3d(1, 1, 1)),
    )
    build_dataset = train.VesuviusLabeledDataset

    def remove_selected_image(volume, labels, mask, *args, **kwargs):
        if volume != uri:
            return build_dataset(volume, labels, mask, *args, **kwargs)
        assert Path(mask if kind == "mask" else labels) == selected
        selected.unlink()
        dataset = build_dataset(volume, labels, mask, *args, **kwargs)
        if kind == "mask":
            assert dataset.mask is None
        else:
            assert torch.count_nonzero(dataset[0][1]).item() == 0
        pytest.fail("the loader silently omitted a selected training image")

    monkeypatch.setattr(train, "VesuviusLabeledDataset", remove_selected_image)
    with pytest.raises(FileNotFoundError) as caught:
        train.train(config)
    assert Path(caught.value.filename) == selected
    assert (root / "inklabels.png").is_file()
    assert not (tmp_path / "run_result.json").exists()


@pytest.mark.parametrize(
    ("mask_kind", "catalog"),
    [("unreadable", True), ("dangling", True), ("dangling", False)],
)
def test_training_checks_the_mask_only_when_it_guides_discovery(
    tmp_path, monkeypatch, mask_kind, catalog
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(train.LOADER_WORKERS_ENV, "0")
    root = tmp_path / "training"
    uri = _volume(root, depth=24)
    mask = root / "mask.png"
    if mask_kind == "dangling":
        mask.symlink_to(root / "missing-mask.png")
    else:
        mask.write_bytes(b"unreadable")
    if catalog:
        (root / "patches.json").write_text('{"patches":[{"y":0,"x":0}]}')
    config = ExperimentConfig(
        val_uri=_volume(tmp_path / "heldout", depth=24),
        uris=[uri],
        num_layers=16,
        patch_size=16,
        cache_dir=str(tmp_path / "cache"),
        use_wandb=False,
    )

    def probe_loader(dataset, *args, **kwargs):
        assert catalog, "the trainer silently omitted the broken mask"
        assert dataset.mask is None
        assert dataset.valid_coords.tolist() == [[0, 0]]
        raise _ReachedTheLoader

    monkeypatch.setattr(train, "shuffled_loader", probe_loader)
    monkeypatch.setattr(
        train,
        "build_model",
        lambda *args: train.GenericMultiTaskWrapper(torch.nn.Conv3d(1, 1, 1)),
    )
    if catalog:
        with pytest.raises(_ReachedTheLoader):
            train.train(config)
    else:
        with pytest.raises(FileNotFoundError) as caught:
            train.train(config)
        assert Path(caught.value.filename) == mask


def test_validation_refuses_a_fragment_shorter_than_the_fixed_window(tmp_path):
    uri = _volume(tmp_path / "heldout", depth=19)
    config = ExperimentConfig(
        val_uri=uri, num_layers=16, patch_size=16, cache_dir=str(tmp_path / "cache")
    )
    with pytest.raises(ValueError, match="19 slices.*requires at least 20"):
        train.build_validation_dataset(config)


def test_uamt_refuses_a_volume_shorter_than_the_model_window(tmp_path):
    training = _volume(tmp_path / "Fr47")
    other = _volume(tmp_path / "other", depth=15)
    with pytest.raises(ValueError, match="15 slices.*requires at least 16"):
        train.unlabeled_dataset(other, _config(training), seed=0)


@pytest.mark.parametrize(
    ("kind", "depths", "diagnostic"),
    [
        ("labeled", [15], "15 slices.*requires at least 16"),
        (
            "labeled",
            [24, 21],
            "cannot batch labeled volumes with different CT read depths",
        ),
        (
            "unlabeled",
            [24, 21],
            "cannot batch unlabeled volumes with different CT read depths",
        ),
    ],
)
def test_real_trainer_refuses_incompatible_volume_depths_before_training(
    tmp_path, monkeypatch, kind, depths, diagnostic
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(train.LOADER_WORKERS_ENV, "0")
    val = _volume(tmp_path / "heldout", depth=24)
    sources = [
        _volume(tmp_path / f"source-{index}", depth=depth)
        for index, depth in enumerate(depths)
    ]
    use_uamt = kind == "unlabeled"
    config = ExperimentConfig(
        val_uri=val,
        uris=[_volume(tmp_path / "labeled", depth=24)] if use_uamt else sources,
        unlabeled_uris=sources if use_uamt else [],
        use_uamt=use_uamt,
        num_layers=16,
        patch_size=16,
        batch_size=2,
        cache_dir=str(tmp_path / "cache"),
        use_wandb=False,
    )
    monkeypatch.setattr(
        train,
        "build_model",
        lambda *args: train.GenericMultiTaskWrapper(torch.nn.Conv3d(1, 1, 1)),
    )
    with pytest.raises(ValueError, match=diagnostic):
        train.train(config)
    assert not (tmp_path / "run_result.json").exists()


def test_a_training_volume_read_by_uamt_is_read_inside_the_band(tmp_path):
    """The production layout: unlabeled_uris is the training volume, 33 slices,
    band [1, 27), 24-slice reads. The band widened by the 4-slice margin is
    [0, 31), so reads start at 0-7; over the whole depth they started at 0-9."""
    uri = _volume(tmp_path / "Fr47 #1")
    group = tmp_path / "linked volume.zarr"
    zarr.open_group(str(group), mode="w")
    (group / "0").symlink_to(uri, target_is_directory=True)
    for spelling in (uri, uri + "/", Path(uri).as_uri(), group.as_uri()):
        dataset = train.unlabeled_dataset(spelling, _config(uri), seed=0)
        assert dataset.depth_range == (0, 31)
    starts = _read_starts(dataset)
    assert starts <= set(range(8)) and len(starts) > 1


@pytest.mark.parametrize("alias", ["checkout fallback", "deprecated uri"])
def test_uamt_only_matches_the_live_labeled_config(tmp_path, monkeypatch, alias):
    from vesuvius_autoresearch.core import inference_constants

    working, other_checkout = tmp_path / "working", tmp_path / "checkout"
    working.mkdir()
    other_checkout.mkdir()
    labeled = _volume(working / "Fr47")
    other = _volume(other_checkout / "Fr47")
    monkeypatch.chdir(working)
    if alias == "checkout fallback":
        monkeypatch.setattr(inference_constants, "_REPO", str(other_checkout))
        selected = _config("Fr47/surface_volume.zarr")
    else:
        selected = ExperimentConfig(
            uris=[labeled], uri=other, num_layers=16, patch_size=16, depth_band=[1, 27]
        )

    assert train.unlabeled_dataset(labeled, selected, seed=0).depth_range == (0, 31)
    different = train.unlabeled_dataset(other, selected, seed=0)
    assert different.depth_range is None
    assert max(_read_starts(different)) > 7


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


@pytest.mark.parametrize("strict", [False, True])
def test_unlabeled_training_read_failure_obeys_configured_policy(
    tmp_path, monkeypatch, strict
):
    uri = _volume(tmp_path / "training")
    dataset = train.unlabeled_dataset(uri, _config(uri, strict_training_reads=strict))
    assert dataset.strict_reads is strict and dataset.volume.strict_reads is strict

    def missing(*args):
        raise OSError("CT chunk unavailable")

    monkeypatch.setattr(dataset.volume.vol, "get_chunk", missing)
    if strict:
        with pytest.raises(RuntimeError, match="failed to read unlabeled patch"):
            dataset[0]
    else:
        patch, _ = dataset[0]
        assert torch.all(patch == 0)


@pytest.mark.parametrize("strict", [False, True])
def test_train_gives_uamt_the_band_for_a_training_volume(
    tmp_path, monkeypatch, capsys, strict
):
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
        strict_training_reads=strict,
    )
    seen = {"labeled": []}

    class Stop(Exception):
        pass

    class Catalogue(torch.utils.data.Dataset):
        validation_inputs = None

        def __len__(self):
            return 10

        def __getitem__(self, i):
            raise AssertionError("not read")

    def labeled(uri, *args, **kwargs):
        seen["labeled"].append(kwargs.get("strict_reads"))
        return Catalogue()

    def unlabeled(uri, *args, **kwargs):
        seen["unlabeled"] = (
            kwargs.get("depth_band"),
            kwargs.get("depth_margin"),
            kwargs.get("strict_reads"),
        )
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
    assert seen == {"labeled": [True, strict], "unlabeled": ([17, 43], 4, strict)}
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


class _ReachedTheLoader(Exception):
    pass


@pytest.mark.parametrize(
    ("kind", "depths", "batch_size", "outcome"),
    [
        ("labeled", [15], 2, r"source-0/surface_volume\.zarr: CT read has 15 slices"),
        ("labeled", [24, 21], 2, "cannot batch labeled volumes"),
        ("unlabeled", [24, 21], 2, "cannot batch unlabeled volumes"),
        ("labeled", [24, 21], 1, None),
    ],
)
def test_the_trainer_s_depth_checks_run_with_explicit_patch_catalogs(
    tmp_path, monkeypatch, kind, depths, batch_size, outcome
):
    # The test above, with a patches.json beside every volume, so that reaching
    # the trainer's depth checks needs no patch discovery. The run stops where
    # the loader under test would be built; with UA-MT, the labeled loader is
    # built first and let through.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(train.LOADER_WORKERS_ENV, "0")

    def volume(name, depth):
        uri = _volume(tmp_path / name, depth=depth)
        (tmp_path / name / "patches.json").write_text('{"patches":[{"y":0,"x":0}]}')
        return uri

    original, calls = train.shuffled_loader, []

    def reached(*args, **kwargs):
        calls.append(args)
        if use_uamt and len(calls) == 1:
            return original(*args, **kwargs)
        raise _ReachedTheLoader

    use_uamt = kind == "unlabeled"
    sources = [volume(f"source-{index}", depth) for index, depth in enumerate(depths)]
    config = ExperimentConfig(
        val_uri=volume("heldout", 24),
        uris=[volume("labeled", 24)] if use_uamt else sources,
        unlabeled_uris=sources if use_uamt else [],
        use_uamt=use_uamt,
        num_layers=16,
        patch_size=16,
        batch_size=batch_size,
        cache_dir=str(tmp_path / "cache"),
        use_wandb=False,
    )
    monkeypatch.setattr(
        train,
        "build_model",
        lambda *args: train.GenericMultiTaskWrapper(torch.nn.Conv3d(1, 1, 1)),
    )
    monkeypatch.setattr(train, "shuffled_loader", reached)
    if outcome is None:
        # With one patch per batch, sources may differ in depth.
        with pytest.raises(_ReachedTheLoader):
            train.train(config)
    else:
        with pytest.raises(ValueError, match=outcome):
            train.train(config)


def test_a_read_may_be_exactly_its_required_depth():
    from vesuvius_autoresearch.core.vesuvius_loader import _read_depth

    assert _read_depth(16, 24, 16, "volume") == 16
    assert _read_depth(40, 24, None, "volume") == 24
    with pytest.raises(ValueError, match="volume: CT read has 15 slices"):
        _read_depth(15, 24, 16, "volume")


def test_positive_integer_returns_a_python_int_and_names_a_nonnegative_rule():
    from vesuvius_autoresearch.core.inference_constants import positive_integer

    value = positive_integer(np.int64(3), "count")
    assert value == 3 and type(value) is int
    assert positive_integer(0, "offset", minimum=0) == 0
    with pytest.raises(ValueError, match="offset must be a nonnegative integer"):
        positive_integer(-1, "offset", minimum=0)


@pytest.mark.parametrize("num_layers", [16.5, True])
def test_validation_needs_an_integer_depth_before_reading(tmp_path, num_layers):
    config = ExperimentConfig(
        val_uri=_volume(tmp_path / "heldout", depth=24),
        num_layers=16,
        patch_size=16,
        cache_dir=str(tmp_path / "cache"),
    )
    # The configuration checks its depth when built. build_validation_dataset
    # checks it again, for a configuration changed after it was built.
    config.num_layers = num_layers
    with pytest.raises(ValueError, match="num_layers must be a positive integer"):
        train.build_validation_dataset(config)


def _catalogued(tmp_path, name, depth=24):
    uri = _volume(tmp_path / name, depth=depth)
    (tmp_path / name / "patches.json").write_text('{"patches":[{"y":0,"x":0}]}')
    return uri


def test_a_supervised_dataset_needs_a_label_path(tmp_path):
    uri = _catalogued(tmp_path, "labeled")
    with pytest.raises(ValueError, match="requires a label image path"):
        train.VesuviusLabeledDataset(
            uri,
            "",
            None,
            16,
            16,
            patches_json=str(tmp_path / "labeled" / "patches.json"),
            require_input_images=True,
        )


@pytest.mark.parametrize("kind", ["labels", "mask"])
def test_a_selected_image_that_is_gone_is_an_error_only_when_required(tmp_path, kind):
    # With an explicit catalog, so building the dataset needs no patch discovery.
    uri = _catalogued(tmp_path, "labeled")
    root = tmp_path / "labeled"
    paths = {"labels": str(root / "inklabels.png"), "mask": None}
    paths[kind] = str(root / "gone.png")
    options = {"patches_json": str(root / "patches.json")}
    loose = train.VesuviusLabeledDataset(
        uri, paths["labels"], paths["mask"], 16, 16, **options
    )
    assert getattr(loose, kind) is None
    with pytest.raises(FileNotFoundError, match="gone"):
        train.VesuviusLabeledDataset(
            uri,
            paths["labels"],
            paths["mask"],
            16,
            16,
            require_input_images=True,
            **options,
        )


@pytest.mark.parametrize("catalog", [True, False])
def test_the_trainer_opens_a_dangling_mask_only_when_it_places_patches(
    tmp_path, monkeypatch, catalog
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(train.LOADER_WORKERS_ENV, "0")
    source = (
        _catalogued(tmp_path, "labeled")
        if catalog
        else _volume(tmp_path / "labeled", depth=24)
    )
    (tmp_path / "labeled" / "mask.png").symlink_to(tmp_path / "absent.png")

    def reached(*args, **kwargs):
        raise _ReachedTheLoader

    config = ExperimentConfig(
        val_uri=_catalogued(tmp_path, "heldout"),
        uris=[source],
        num_layers=16,
        patch_size=16,
        batch_size=1,
        cache_dir=str(tmp_path / "cache"),
        use_wandb=False,
    )
    monkeypatch.setattr(
        train,
        "build_model",
        lambda *args: train.GenericMultiTaskWrapper(torch.nn.Conv3d(1, 1, 1)),
    )
    monkeypatch.setattr(train, "shuffled_loader", reached)
    if catalog:
        # The catalog places the patches, so the mask is not opened.
        with pytest.raises(_ReachedTheLoader):
            train.train(config)
    else:
        # The mask would place them: its broken link is reported before any
        # patch is discovered.
        with pytest.raises(FileNotFoundError, match="mask.png"):
            train.train(config)
