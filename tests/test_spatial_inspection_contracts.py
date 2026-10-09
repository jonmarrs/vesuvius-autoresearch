"""Spatial artifacts and diagnostics must reflect the real dataset contract."""

import sys
from pathlib import Path

import numpy as np
import pytest
import zarr
from PIL import Image

from scripts import (
    scan_dataset as train_scan,
    scan_ink_density as density_scan,
    scan_val_dataset as val_scan,
    spatial_split_mask as split,
)


def png(path, values):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.asarray(values, np.uint8)).save(path)
    return path


def test_odd_buffer_removes_exact_requested_width():
    source = np.ones((4, 20), bool)
    u, v = split.split_mask(source, buffer=3)
    assert int((~(u | v))[0].sum()) == 3


def test_negative_buffer_cannot_create_overlapping_regions():
    with pytest.raises(ValueError):
        split.split_mask(np.ones((4, 20), bool), buffer=-4)


def test_large_buffer_cannot_wrap_numpy_slices():
    with pytest.raises(ValueError):
        split.split_mask(np.ones((4, 20), bool), buffer=24)


def test_split_rejects_three_dimensional_input():
    with pytest.raises(ValueError):
        split.split_mask(np.ones((4, 20, 20), bool), buffer=2)


def test_split_requires_positive_pixels_on_both_sides():
    mask = np.zeros((4, 20), bool)
    mask[:, :3] = True
    with pytest.raises(ValueError):
        split.split_mask(mask, buffer=2)


def test_legacy_file_pair_cannot_overwrite_source(tmp_path, monkeypatch):
    source = png(tmp_path / "source.png", np.full((4, 20), 255))
    before = source.read_bytes()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "spatial_split_mask",
            "--mask",
            str(source),
            "--out-u",
            str(source),
            "--out-v",
            str(tmp_path / "v.png"),
            "--buffer",
            "2",
        ],
    )
    with pytest.raises((ValueError, SystemExit)):
        split.main()
    assert source.read_bytes() == before
    assert not (tmp_path / "v.png").exists()


@pytest.fixture
def real_fragments(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for segment in ("PHercParis2Fr47", "PHercParis2Fr143"):
        fragment = tmp_path / "local_data" / segment
        fragment.mkdir(parents=True)
        ct = zarr.open(
            str(fragment / "surface_volume.zarr"),
            mode="w",
            shape=(16, 64, 256),
            chunks=(4, 32, 64),
            dtype="u1",
        )
        ct[:] = 64
        labels = np.zeros((64, 256), np.uint8)
        labels[:, ::2] = 255
        png(fragment / "inklabels.png", labels)
        png(fragment / "mask.png", np.full((64, 256), 255))
    return tmp_path / "local_data"


def test_training_scan_consumes_actual_three_value_samples(real_fragments):
    train_scan.scan_dataset()


def test_validation_scan_consumes_actual_three_value_samples(real_fragments):
    val_scan.scan_val_dataset()


def test_density_scan_consumes_actual_three_value_samples(real_fragments):
    density_scan.scan_ink_density()


def test_visualization_consumes_actual_samples_and_preserves_depth_axis(real_fragments):
    from scripts.visualize_training_data import visualize_training_samples

    fragment = real_fragments / "PHercParis2Fr47"
    result = visualize_training_samples(
        str(fragment / "surface_volume.zarr"),
        str(fragment / "inklabels.png"),
        str(fragment / "mask.png"),
        num_samples=1,
        patch_size=64,
        num_layers=16,
    )
    assert Path(result).is_file()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"axis": -1},
        {"axis": 2},
        {"axis": True},
        {"fraction": 0},
        {"fraction": 1},
        {"fraction": float("nan")},
        {"fraction": float("inf")},
        {"fraction": True},
        {"buffer": True},
        {"buffer": 1.5},
    ],
)
def test_invalid_partition_parameters_are_refused(kwargs):
    arguments = {"buffer": 2, **kwargs}
    with pytest.raises(ValueError):
        split.split_mask(np.ones((8, 24), bool), **arguments)


@pytest.mark.parametrize(
    "mask",
    [
        np.zeros((0, 8), bool),
        np.ones(8, bool),
        np.full((8, 24), 128),
        np.full((8, 24), np.nan),
        np.zeros((8, 24), bool),
    ],
)
def test_invalid_source_masks_are_not_silent_empty_partitions(mask):
    with pytest.raises(ValueError):
        split.split_mask(mask, buffer=2)


@pytest.mark.parametrize(
    "axis,buffer", [(0, 0), (0, 3), (0, 4), (1, 0), (1, 3), (1, 4)]
)
def test_partition_preserves_mask_and_exact_gap_on_each_axis(axis, buffer):
    source = np.ones((24, 24), bool)
    source[3:7, 2:4] = False
    u, v = split.split_mask(source, axis=axis, buffer=buffer)
    assert not (u & v).any()
    assert not ((u | v) & ~source).any()
    actual = (~(u | v)).all(axis=1 - axis)
    assert int(actual.sum()) == buffer
    assert u.any() and v.any()


def test_partition_pair_cli_publishes_finite_provenance_outside_checkout(tmp_path):
    import json
    import subprocess

    from scripts.export_for_production import sha256_file

    root = Path(__file__).resolve().parents[1]
    source = png(tmp_path / "mask.png", np.full((8, 24), 255))
    output = tmp_path / "new" / "pair"
    process = subprocess.run(
        [
            sys.executable,
            str(root / "scripts/spatial_split_mask.py"),
            "--mask",
            str(source),
            "--out",
            str(output),
            "--buffer",
            "3",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert process.returncode == 0, process.stderr
    result = json.loads(process.stdout)
    assert json.loads((output / "split.json").read_text()) == result
    assert result["buffer_width"] == 3
    assert result["gap_indices"] == [11, 14]
    assert result["source_sha256"] == sha256_file(source)
    assert result["mask_pixels_disjoint"] is True
    assert result["patch_independence_verified"] is False
    assert (
        sum(
            result[key]
            for key in (
                "u_positive_pixels",
                "v_positive_pixels",
                "discarded_positive_pixels",
            )
        )
        == result["source_positive_pixels"]
    )
    for name in ("u.png", "v.png"):
        assert sha256_file(output / name) == result["outputs"][name]["sha256"]


@pytest.mark.parametrize(
    "mode", ["existing", "source", "alias", "rgb", "grey", "oversize"]
)
def test_invalid_partition_destinations_and_pngs_never_publish(tmp_path, mode):
    source = png(tmp_path / "mask.png", np.full((8, 24), 255))
    before = source.read_bytes()
    output = tmp_path / "pair"
    kwargs = {}
    if mode == "existing":
        output.mkdir()
        (output / "keep").write_text("original")
    elif mode == "source":
        output = source
    elif mode == "alias":
        output.symlink_to(source)
    elif mode == "rgb":
        Image.fromarray(np.zeros((8, 24, 3), np.uint8)).save(source)
    elif mode == "grey":
        png(source, np.full((8, 24), 127))
    elif mode == "oversize":
        kwargs["max_pixels"] = 191
    with pytest.raises((ValueError, OSError)):
        split.prepare_split(source, output, buffer=2, **kwargs)
    if mode == "existing":
        assert (output / "keep").read_text() == "original"
    elif mode not in {"source", "alias"}:
        assert not output.exists()
    if mode not in {"rgb", "grey"}:
        assert source.read_bytes() == before


@pytest.mark.parametrize("mode", ["second_write", "corrupt_write", "changed_source"])
def test_partition_pair_rolls_back_failed_or_changed_writes(
    tmp_path, monkeypatch, mode
):
    source = png(tmp_path / "source.png", np.full((8, 24), 255))
    output = tmp_path / "pair"
    save = Image.Image.save
    writes = []

    def write(image, path, *args, **kwargs):
        path = Path(path)
        writes.append(path.name)
        if mode == "second_write" and path.name == "v.png":
            raise OSError("simulated second write failure")
        if mode == "corrupt_write":
            save(Image.fromarray(np.zeros((8, 24), np.uint8)), path, *args, **kwargs)
        else:
            save(image, path, *args, **kwargs)
        if mode == "changed_source" and path.name == "u.png":
            save(Image.fromarray(np.zeros((8, 24), np.uint8)), source)

    monkeypatch.setattr(Image.Image, "save", write)
    with pytest.raises((OSError, ValueError)):
        split.prepare_split(source, output, buffer=2)
    assert not output.exists()
    assert not list(tmp_path.glob(".pair-*"))


def test_disjoint_masks_can_still_sample_the_same_ct_context(real_fragments, tmp_path):
    from scripts.dataset_inspection import inspection_dataset

    fragment = real_fragments / "PHercParis2Fr47"
    output = tmp_path / "split"
    metadata = split.prepare_split(
        fragment / "mask.png", output, fraction=0.375, buffer=0
    )
    masks = [np.asarray(Image.open(output / name)) > 0 for name in ("u.png", "v.png")]
    assert not (masks[0] & masks[1]).any()
    catalogs = []
    for name in ("u.png", "v.png"):
        with inspection_dataset(
            fragment / "surface_volume.zarr", fragment / "inklabels.png", output / name
        ) as (dataset, _):
            catalogs.append(set(map(tuple, dataset.valid_coords)))
    assert catalogs[0] & catalogs[1] == {(0, 64)}
    assert metadata["patch_independence_verified"] is False


def test_scans_report_actual_sample_count_and_no_cache_side_effects(
    real_fragments, tmp_path
):
    result = train_scan.scan_dataset(samples=1000)
    assert result["requested_samples"] == 1000
    assert result["sampled_samples"] == result["available_samples"] == 4
    assert result["samples_with_ink_in_mask"] == 4
    assert result["masked_ink_pixels"]["mean"] == 2048
    assert result["full_volume_statistics"] is False
    assert result["jitter"] is False and result["strict_reads"] is True
    assert not list(tmp_path.glob("*.npy"))
    assert not list(real_fragments.rglob("*.npy"))


def test_density_fallback_does_not_claim_at_least_one_ink_pixel(real_fragments):
    fragment = real_fragments / "PHercParis2Fr143"
    png(fragment / "inklabels.png", np.zeros((64, 256), np.uint8))
    result = density_scan.scan_ink_density()
    assert result["require_ink"] is True
    assert result["masked_ink_pixels"]["max"] == 0
    assert result["samples_with_ink_in_mask"] == 0


@pytest.mark.parametrize(
    "mode",
    [
        "mask_shape",
        "label_shape",
        "rgb",
        "pseudo_labels",
        "empty_mask",
        "oversize",
        "shallow",
        "missing_labels",
    ],
)
def test_invalid_dataset_inputs_fail_before_sampling(real_fragments, monkeypatch, mode):
    from scripts.dataset_inspection import inspect_fragment
    from vesuvius_autoresearch.core import vesuvius_loader

    fragment = real_fragments / "PHercParis2Fr47"
    kwargs = {}
    if mode == "mask_shape":
        png(fragment / "mask.png", np.full((64, 255), 255))
    elif mode == "label_shape":
        png(fragment / "inklabels.png", np.full((64, 255), 255))
    elif mode == "rgb":
        Image.fromarray(np.zeros((64, 256, 3), np.uint8)).save(fragment / "mask.png")
    elif mode == "pseudo_labels":
        png(fragment / "inklabels.png", np.full((64, 256), 128))
    elif mode == "empty_mask":
        png(fragment / "mask.png", np.zeros((64, 256), np.uint8))
    elif mode == "oversize":
        kwargs["max_pixels"] = 16383
    elif mode == "shallow":
        kwargs["num_layers"] = 17
    elif mode == "missing_labels":
        (fragment / "inklabels.png").unlink()

    def unexpected(*args, **kwargs):
        pytest.fail("invalid inputs reached the dataset")

    monkeypatch.setattr(vesuvius_loader, "VesuviusLabeledDataset", unexpected)
    with pytest.raises((OSError, ValueError)):
        inspect_fragment(
            fragment / "surface_volume.zarr",
            fragment / "inklabels.png",
            fragment / "mask.png",
            **kwargs,
        )


class TinySamples:
    jitter = False
    strict_reads = True
    patch_size = 4
    num_layers = 1
    shape = (1, 4, 4)
    valid_coords = np.array([[0, 0]])
    mask = np.zeros((4, 4), np.uint8)
    mask[0, 0] = 1

    def __len__(self):
        return 1

    def __getitem__(self, index):
        import torch

        ct = torch.ones(1, 1, 4, 4)
        ct[:, :, 0, 0] = 0
        target = torch.ones(4, 4)
        target[0, 0] = 0
        return ct, target, torch.zeros(1, 1, 4, 4)


def test_statistics_restrict_ink_and_ct_means_to_requested_mask():
    from scripts.dataset_inspection import sample_report

    result = sample_report(TinySamples(), {}, 10)
    assert result["samples_with_ink_in_mask"] == 0
    assert result["samples_with_masked_ct_mean_above_0_01"] == 0
    assert result["masked_ink_pixels"]["mean"] == 0
    assert result["sampled_samples"] == 1
    assert result["context_yx_pixels_outside_mask_across_samples"] == 15


@pytest.mark.parametrize(
    "mode",
    [
        "jitter",
        "fallback_reads",
        "bad_coords",
        "shape",
        "nan",
        "not_binary",
        "short_depth",
        "empty",
    ],
)
def test_invalid_sample_contracts_cannot_look_like_success(mode):
    import torch

    from scripts.dataset_inspection import sample_report

    class Bad(TinySamples):
        def __getitem__(self, index):
            ct, target, fiber = super().__getitem__(index)
            if mode == "shape":
                target = target[:3]
            elif mode == "nan":
                ct[:] = float("nan")
            elif mode == "not_binary":
                target[:] = 0.5
            elif mode == "short_depth":
                ct = ct[:, :0]
            return ct, target, fiber

        def __len__(self):
            return 0 if mode == "empty" else 1

    dataset = Bad()
    if mode == "jitter":
        dataset.jitter = True
    elif mode == "fallback_reads":
        dataset.strict_reads = False
    elif mode == "bad_coords":
        dataset.valid_coords = np.array([[0, 1]])
    with pytest.raises((ValueError, RuntimeError)):
        sample_report(dataset, {}, 1)


@pytest.mark.parametrize("count", [0, -1, True, 0.5, float("nan"), 10001])
def test_sample_budget_is_explicit_and_finite(count):
    from scripts.dataset_inspection import sample_report

    with pytest.raises(ValueError):
        sample_report(TinySamples(), {}, count)


@pytest.mark.parametrize(
    "script", ["scan_dataset.py", "scan_val_dataset.py", "scan_ink_density.py"]
)
def test_scan_cli_outputs_machine_readable_sample_report(
    real_fragments, tmp_path, script
):
    import json
    import subprocess

    root = Path(__file__).resolve().parents[1]
    fragment = real_fragments / "PHercParis2Fr47"
    process = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / script),
            "--uri",
            str(fragment / "surface_volume.zarr"),
            "--labels",
            str(fragment / "inklabels.png"),
            "--mask",
            str(fragment / "mask.png"),
            "--samples",
            "3",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    result = json.loads(process.stdout)
    assert result["requested_samples"] == result["sampled_samples"] == 3
    assert result["available_samples"] == 4
    assert result["require_ink"] == (script == "scan_ink_density.py")


def test_visualization_handles_one_layer_and_embeds_snapshot(real_fragments, tmp_path):
    import json

    from scripts.visualize_training_data import visualize_training_samples

    fragment = real_fragments / "PHercParis2Fr47"
    output = tmp_path / "view.png"
    result = visualize_training_samples(
        fragment / "surface_volume.zarr",
        fragment / "inklabels.png",
        fragment / "mask.png",
        num_samples=5,
        patch_size=64,
        num_layers=1,
        output_path=output,
    )
    assert result == output
    with Image.open(output) as image:
        assert image.width > 100 and image.height > 100
        metadata = json.loads(image.info["Description"])
    assert metadata["num_layers"] == 1
    assert metadata["sampled_samples"] == 4
    assert metadata["requested_samples"] == 5


@pytest.mark.parametrize(
    "mode", ["existing", "source", "source_volume", "render_failure"]
)
def test_visualization_preserves_sources_and_old_artifacts(
    real_fragments, tmp_path, monkeypatch, mode
):
    from matplotlib.figure import Figure

    from scripts.visualize_training_data import visualize_training_samples

    fragment = real_fragments / "PHercParis2Fr47"
    source = fragment / "inklabels.png"
    before = source.read_bytes()
    output = tmp_path / "view.png"
    if mode == "existing":
        png(output, [[255, 0]])
        previous = output.read_bytes()
    elif mode == "source":
        output = source
    elif mode == "source_volume":
        output = fragment / "surface_volume.zarr/view.png"
    elif mode == "render_failure":

        def fail(self, path, **kwargs):
            Path(path).write_bytes(b"partial figure")
            raise OSError("simulated render failure")

        monkeypatch.setattr(Figure, "savefig", fail)
    with pytest.raises((ValueError, OSError)):
        visualize_training_samples(
            fragment / "surface_volume.zarr",
            source,
            fragment / "mask.png",
            num_samples=1,
            patch_size=64,
            num_layers=1,
            output_path=output,
        )
    assert source.read_bytes() == before
    if mode == "existing":
        assert output.read_bytes() == previous
    elif mode != "source":
        assert not output.exists()
    assert not list(tmp_path.glob(".view-*"))


def test_real_ct_read_failure_does_not_become_a_zero_sample(
    real_fragments, monkeypatch
):
    from vesuvius_autoresearch.core.vesuvius_loader import FastVesuviusVolume

    def fail(*args, **kwargs):
        raise OSError("simulated corrupt CT chunk")

    monkeypatch.setattr(FastVesuviusVolume, "get_raw_patch", fail)
    with pytest.raises(RuntimeError, match="failed to read labeled patch"):
        train_scan.scan_dataset()


def test_changed_labels_prevent_an_inspection_result(real_fragments, monkeypatch):
    from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset

    source = real_fragments / "PHercParis2Fr47/inklabels.png"
    read = VesuviusLabeledDataset.__getitem__

    def mutate(dataset, index):
        result = read(dataset, index)
        if index == 0:
            png(source, np.zeros((64, 256), np.uint8))
        return result

    monkeypatch.setattr(VesuviusLabeledDataset, "__getitem__", mutate)
    with pytest.raises(ValueError, match="changed"):
        train_scan.scan_dataset()


def test_patch_memory_budget_is_checked_before_ct_access(real_fragments, monkeypatch):
    from scripts.dataset_inspection import inspection_dataset
    from vesuvius_autoresearch.core import vesuvius_loader

    fragment = real_fragments / "PHercParis2Fr47"

    def unexpected(*args, **kwargs):
        pytest.fail("oversized request reached dataset")

    monkeypatch.setattr(vesuvius_loader, "VesuviusLabeledDataset", unexpected)
    with pytest.raises(ValueError, match="voxels"):
        with inspection_dataset(
            fragment / "surface_volume.zarr",
            fragment / "inklabels.png",
            fragment / "mask.png",
            patch_size=256,
            num_layers=16,
        ):
            pytest.fail("oversized request yielded a dataset")
