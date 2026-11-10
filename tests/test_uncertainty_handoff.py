"""Proofreading masks must identify the current prediction and publish whole."""

import builtins
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import torch
import zarr
from test_volume_inference_contracts import setup_prediction

from scripts import uncertainty_artifacts
from scripts.active_learning_sampler import (
    export_for_proofreader,
    identify_uncertain_patches,
)


def test_export_cannot_silently_discard_channels(tmp_path):
    with pytest.raises(ValueError, match="channel"):
        export_for_proofreader(np.zeros((2, 1, 3, 4), np.float32), tmp_path / "mask")
    assert not (tmp_path / "mask").exists()


def test_failed_chunk_write_preserves_previous_store(tmp_path, monkeypatch):
    path = tmp_path / "mask"
    export_for_proofreader(np.ones((1, 3, 4), np.float32), path)
    write = zarr.Array.__setitem__

    def fail_after_write(self, key, value):
        write(self, key, value)
        raise OSError("simulated chunk write failure")

    monkeypatch.setattr(zarr.Array, "__setitem__", fail_after_write)
    with pytest.raises(OSError, match="chunk write failure"):
        updated = np.ones((1, 3, 4), np.float32)
        updated[:, 0] = 0
        export_for_proofreader(updated, path, overwrite=True)
    np.testing.assert_array_equal(zarr.open(str(path), mode="r")[:], 1)


def test_confident_rerun_cannot_keep_old_uncertainty_mask(tmp_path, monkeypatch):
    run, argv, _, _, checkpoints = setup_prediction(tmp_path, monkeypatch, "single")
    argv.remove("--skip_active_learning")
    run()
    path = tmp_path / "out/pred_1_2_3_13x11_uncertain"
    assert zarr.open(str(path), mode="r")[:].sum() > 0
    checkpoint = torch.load(checkpoints[0], weights_only=False)
    checkpoint["model_state_dict"]["bias"] = torch.full((1,), 20.0)
    torch.save(checkpoint, checkpoints[0])
    run()
    np.testing.assert_array_equal(zarr.open(str(path), mode="r")[:], 0)
    record = json.loads((tmp_path / "out/pred_1_2_3_13x11_meta.json").read_text())
    assert record["uncertainty_export"]["status"] == "EMPTY"
    attrs = zarr.open(str(path), mode="r").attrs.asdict()
    assert attrs["source"]["position_xyz"] == [3, 2, 1]
    assert attrs["source"]["voxel_size_um"] == 2.0
    assert attrs["source"]["checkpoint_sha256"] == record["checkpoint_sha256"]
    assert attrs["source"]["inference_recipe"] == record["inference_recipe"]
    assert attrs["uncertain_voxels"] == 0


@pytest.mark.parametrize("shape", [(3, 4), (2, 3, 4), (1, 2, 3, 4)])
@pytest.mark.parametrize("dtype", [np.bool_, np.uint8, np.float32])
def test_binary_masks_round_trip_with_declared_axes(tmp_path, shape, dtype):
    values = (np.arange(np.prod(shape)).reshape(shape) % 2).astype(dtype)
    path = tmp_path / "mask"
    record = export_for_proofreader(values, path, metadata={"source_uri": "ct.zarr"})
    array = zarr.open(str(path), mode="r")
    expected = values.reshape(record["shape_zyx"])
    np.testing.assert_array_equal(array[:], expected)
    assert array.dtype == np.dtype("f4")
    assert array.chunks == (1, 64, 64)
    assert array.attrs["axes"] == ["z", "y", "x"]
    assert array.attrs["source"] == {"source_uri": "ct.zarr"}
    assert record["uncertain_voxels"] == int(expected.sum())


def test_uint8_255_mask_and_gradient_tensor_are_supported(tmp_path):
    values = np.array([[0, 255], [255, 0]], np.uint8)
    export_for_proofreader(values, tmp_path / "png_mask")
    np.testing.assert_array_equal(
        zarr.open(str(tmp_path / "png_mask"), mode="r")[:], (values > 0)[None]
    )
    tensor = torch.tensor([[0.0, 1.0], [1.0, 0.0]], requires_grad=True)
    export_for_proofreader(tensor, tmp_path / "tensor_mask")
    np.testing.assert_array_equal(
        zarr.open(str(tmp_path / "tensor_mask"), mode="r")[:],
        tensor.detach().numpy()[None],
    )


@pytest.mark.parametrize(
    "values",
    [
        np.zeros((0, 3, 4)),
        np.zeros((3,)),
        np.zeros((1, 1, 1, 1, 1)),
        np.full((2, 2), np.nan),
        np.full((2, 2), 0.5),
        np.array([[0, 1, 255]]),
        np.ones((2, 2), complex),
    ],
)
def test_invalid_masks_fail_before_creating_output(tmp_path, values):
    path = tmp_path / "new/mask"
    with pytest.raises(ValueError):
        export_for_proofreader(values, path)
    assert not path.parent.exists()


def test_existing_store_requires_explicit_replacement_and_preserves_mode(tmp_path):
    path = tmp_path / "mask"
    # Legacy array with no uncertainty contract metadata remains replaceable.
    array = zarr.open(str(path), mode="w", shape=(1, 3, 4), dtype="f4")
    array[:] = 1
    path.chmod(0o750)
    with pytest.raises(ValueError, match="already exists"):
        export_for_proofreader(np.zeros((3, 4)), path)
    np.testing.assert_array_equal(zarr.open(str(path), mode="r")[:], 1)
    record = export_for_proofreader(np.zeros((3, 4)), path, overwrite=True)
    assert record["status"] == "EMPTY"
    assert path.stat().st_mode & 0o777 == 0o750
    np.testing.assert_array_equal(zarr.open(str(path), mode="r")[:], 0)


def test_failed_install_restores_previous_directory(tmp_path, monkeypatch):
    path = tmp_path / "mask"
    export_for_proofreader(np.ones((3, 4)), path)
    rename = Path.rename

    def fail(self, target):
        if self.name == "new.zarr" and Path(target) == path:
            raise OSError("install failed")
        return rename(self, target)

    monkeypatch.setattr(Path, "rename", fail)
    with pytest.raises(OSError, match="install failed"):
        export_for_proofreader(np.zeros((3, 4)), path, overwrite=True)
    np.testing.assert_array_equal(zarr.open(str(path), mode="r")[:], 1)
    assert not list(tmp_path.glob(".mask-*"))


@pytest.mark.parametrize(
    "damage",
    ["root_symlink", "chunk_symlink", "chunk_hardlink", "file", "unrelated_directory"],
)
def test_unsafe_existing_destinations_are_refused(tmp_path, damage):
    path = tmp_path / "mask"
    outside = tmp_path / "external"
    outside.write_bytes(b"source must survive")
    if damage in {"chunk_symlink", "chunk_hardlink"}:
        export_for_proofreader(np.ones((3, 4)), path)
        chunk = path / "0.0.0"
        if damage == "chunk_symlink":
            chunk.unlink()
            chunk.symlink_to(outside)
        else:
            os.link(chunk, tmp_path / "linked_chunk")
    elif damage == "root_symlink":
        path.symlink_to(tmp_path / "elsewhere", target_is_directory=True)
    elif damage == "file":
        path.write_bytes(b"unrelated")
    else:
        path.mkdir()
        (path / "notes.txt").write_text("unrelated")
    with pytest.raises(ValueError):
        export_for_proofreader(np.zeros((3, 4)), path, overwrite=True)
    assert outside.read_bytes() == b"source must survive"
    assert not list(tmp_path.glob(".mask-*"))


def test_source_overlap_and_late_alias_block_publication(tmp_path, monkeypatch):
    source = tmp_path / "ct.zarr"
    source.mkdir()
    with pytest.raises(ValueError, match="collision"):
        export_for_proofreader(np.ones((3, 4)), source / "mask", sources=[source])
    path = tmp_path / "mask"
    write = zarr.Array.__setitem__

    def swap(self, key, values):
        write(self, key, values)
        path.symlink_to(source, target_is_directory=True)

    monkeypatch.setattr(zarr.Array, "__setitem__", swap)
    with pytest.raises(ValueError, match="collision"):
        export_for_proofreader(np.ones((3, 4)), path, overwrite=True, sources=[source])
    assert path.is_symlink()
    assert not list(source.iterdir())


@pytest.mark.parametrize(
    "metadata", [{"bad": float("nan")}, {"bad": object()}, ["not", "an", "object"]]
)
def test_invalid_metadata_leaves_no_output(tmp_path, metadata):
    with pytest.raises(ValueError, match="JSON"):
        export_for_proofreader(
            np.ones((3, 4)), tmp_path / "new/mask", metadata=metadata
        )
    assert not (tmp_path / "new").exists()


def test_budget_applies_before_a_tensor_is_copied_to_cpu(tmp_path, monkeypatch):
    def unexpected(*args):
        raise AssertionError("oversized mask must fail before CPU copy")

    monkeypatch.setattr(torch.Tensor, "cpu", unexpected)
    with pytest.raises(ValueError, match="max_voxels"):
        export_for_proofreader(torch.zeros((3, 4)), tmp_path / "mask", max_voxels=11)
    assert not (tmp_path / "mask").exists()


@pytest.mark.parametrize("threshold", [-0.1, 1.1, np.nan, np.inf, True, "bad"])
def test_invalid_normalized_entropy_thresholds_fail(threshold):
    with pytest.raises(ValueError, match="threshold"):
        identify_uncertain_patches(torch.ones((3, 4)), threshold=threshold)


def test_entropy_mask_shapes_endpoints_and_no_input_mutation():
    probabilities = torch.tensor([[0.0, 0.5, 1.0]], dtype=torch.float16)
    original = probabilities.clone()
    np.testing.assert_array_equal(
        identify_uncertain_patches(probabilities, threshold=0.2), [[0, 1, 0]]
    )
    assert identify_uncertain_patches(probabilities, threshold=1).sum() == 0
    torch.testing.assert_close(probabilities, original)
    with pytest.raises(ValueError, match="H/W"):
        identify_uncertain_patches(torch.zeros((1, 1, 3, 4)))
    with pytest.raises(ValueError, match="real"):
        identify_uncertain_patches(torch.ones((3, 4), dtype=torch.complex64))


def test_skipped_export_is_not_advertised_as_current(tmp_path, monkeypatch):
    run, argv, _, _, _ = setup_prediction(tmp_path, monkeypatch, "single")
    argv.remove("--skip_active_learning")
    run()
    argv.append("--skip_active_learning")
    run()
    record = json.loads((tmp_path / "out/pred_1_2_3_13x11_meta.json").read_text())[
        "uncertainty_export"
    ]
    assert record["status"] == "SKIPPED" and record["path"] is None


def test_partial_shards_do_not_export_uncertainty_as_complete(tmp_path, monkeypatch):
    run, argv, _, _, _ = setup_prediction(tmp_path, monkeypatch, "single")
    argv.remove("--skip_active_learning")
    argv.extend(["--num_parts", "2", "--part_id", "0"])
    run()
    record = json.loads(
        (tmp_path / "out/pred_1_2_3_13x11_part0of2_meta.json").read_text()
    )["uncertainty_export"]
    assert record["status"] == "INCOMPLETE" and record["path"] is None
    assert not list((tmp_path / "out").glob("*_uncertain"))


def test_invalid_uncertainty_destination_fails_before_model_work(tmp_path, monkeypatch):
    run, argv, created, _, _ = setup_prediction(tmp_path, monkeypatch, "single")
    argv.remove("--skip_active_learning")
    path = tmp_path / "out/pred_1_2_3_13x11_uncertain"
    path.parent.mkdir()
    path.symlink_to(tmp_path / "unrelated", target_is_directory=True)
    with pytest.raises(ValueError, match="directory"):
        run()
    assert not created
    assert not list(path.parent.glob("*.npy"))


def test_missing_optional_exporter_is_recorded(tmp_path, monkeypatch):
    run, argv, _, _, _ = setup_prediction(tmp_path, monkeypatch, "single")
    argv.remove("--skip_active_learning")
    original_import = builtins.__import__

    def missing(name, *args, **kwargs):
        if name == "scripts.active_learning_sampler":
            raise ImportError("optional exporter unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing)
    run()
    record = json.loads((tmp_path / "out/pred_1_2_3_13x11_meta.json").read_text())[
        "uncertainty_export"
    ]
    assert record["status"] == "UNAVAILABLE" and record["path"] is None
    assert "optional exporter unavailable" in record["reason"]


def test_prediction_mask_failure_leaves_no_success_metadata(tmp_path, monkeypatch):
    run, argv, _, _, _ = setup_prediction(tmp_path, monkeypatch, "single")
    argv.remove("--skip_active_learning")
    run()
    path = tmp_path / "out/pred_1_2_3_13x11_uncertain"
    before = {
        str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()
    }
    write = zarr.Array.__setitem__

    def fail(self, key, value):
        write(self, key, value)
        if "_uncertain-" in str(self.store.path):
            raise OSError("mask storage failed")

    monkeypatch.setattr(zarr.Array, "__setitem__", fail)
    with pytest.raises(OSError, match="mask storage failed"):
        run()
    after = {
        str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()
    }
    assert after == before
    assert not (tmp_path / "out/pred_1_2_3_13x11_meta.json").exists()


@pytest.mark.parametrize(
    "module", ["scripts.active_learning_sampler", "scripts.inference.predict"]
)
def test_module_launch_uses_its_own_core_with_a_foreign_editable_install(
    tmp_path, module
):
    foreign = tmp_path / "other/src/vesuvius_autoresearch/core"
    foreign.mkdir(parents=True)
    (foreign / "__init__.py").write_text(
        "raise RuntimeError('foreign checkout imported')\n"
    )
    repo = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", module, "--help"],
        cwd=repo,
        env={
            **os.environ,
            "PYTHONPATH": str(tmp_path / "other/src"),
            "CUDA_VISIBLE_DEVICES": "",
        },
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.lower()


@pytest.mark.parametrize("path", ["", " ", "s3://bucket/mask", "file:///tmp/mask"])
def test_export_destinations_are_explicit_local_paths(tmp_path, monkeypatch, path):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="local filesystem"):
        export_for_proofreader(np.ones((3, 4)), path)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("overwrite", ["False", 1, None])
def test_replacement_requires_a_boolean_flag(tmp_path, overwrite):
    with pytest.raises(ValueError, match="boolean"):
        export_for_proofreader(np.ones((3, 4)), tmp_path / "mask", overwrite=overwrite)
    assert not list(tmp_path.iterdir())


def test_a_single_source_path_cannot_be_misread_as_characters(tmp_path):
    with pytest.raises(ValueError, match="sequence"):
        export_for_proofreader(
            np.ones((3, 4)), tmp_path / "mask", sources=str(tmp_path / "ct.zarr")
        )
    assert not list(tmp_path.iterdir())
