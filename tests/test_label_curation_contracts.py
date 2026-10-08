"""Real upstream filtering and fail-before-publication curation contracts."""

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import zarr

from scripts.labeling import curate_training_data as curator


@pytest.fixture
def labels(tmp_path):
    source, output = tmp_path / "source.zarr", tmp_path / "curated.zarr"
    data = np.zeros((4, 4, 4), np.uint16)
    data[0, 0, :2] = 42
    array = zarr.array(data, store=str(source), chunks=(2, 2, 2), overwrite=True)
    array.attrs["frame"] = "test source frame"
    return source, output


def curate(labels, **settings):
    settings.setdefault("chunk_size", 2)
    settings.setdefault("reject_branches", False)
    settings.setdefault("workers", 1)
    return curator.curate_training_data(*labels, **settings)


@pytest.mark.parametrize("group_input", [False, True])
def test_actual_upstream_preserves_retained_ids_and_records_coverage(
    labels, group_input
):
    source, output = labels
    if group_input:
        import shutil

        old = zarr.open(str(source), mode="r")
        values, attrs = old[:], dict(old.attrs)
        shutil.rmtree(source)
        root = zarr.open_group(str(source), mode="w")
        root.attrs["frame"] = "test group frame"
        root.create_dataset("0", data=values, chunks=(2, 2, 2)).attrs.update(attrs)
    result = curate(labels)
    after = zarr.open(str(output), mode="r")
    before = zarr.open(str(source), mode="r")
    array = before["0"] if group_input else before
    np.testing.assert_array_equal(after[:], array[:])
    assert after.dtype == np.uint16
    assert result == {
        "chunks_evaluated": 8,
        "chunks_retained_nonempty": 1,
        "chunks_zero": 7,
        "labeled_voxels": 2,
    }
    completion = after.attrs["label_curation_completion"]
    assert completion["source_path"] == str(source.resolve())
    assert completion["source_array_attrs"]["frame"] == "test source frame"
    assert completion["settings"]["reject_branches"] is False
    assert completion["label_kind"] == "heuristically_curated_segmentation"


def test_actual_upstream_can_reject_every_chunk_without_claiming_ground_truth(labels):
    result = curate(labels, min_percent=80, max_percent=90)
    assert result["chunks_retained_nonempty"] == result["labeled_voxels"] == 0
    assert result["chunks_evaluated"] == 8
    assert not zarr.open(str(labels[1]), mode="r")[:].any()


@pytest.mark.parametrize(
    "settings",
    [
        {"chunk_size": 0},
        {"chunk_size": -1},
        {"chunk_size": 1.5},
        {"chunk_size": 3},
        {"chunk_size": 64},
        {"workers": 0},
        {"workers": -1},
        {"workers": True},
        {"min_percent": -1},
        {"max_percent": 101},
        {"min_percent": float("nan")},
        {"min_percent": 80, "max_percent": 40},
        {"min_cc": -1},
        {"max_cc": 1.5},
        {"min_cc": 5, "max_cc": 1},
        {"reject_branches": "false"},
    ],
)
def test_preflight_rejects_invalid_or_partial_grid_before_calling_upstream(
    labels, settings, monkeypatch
):
    def never():
        pytest.fail("invalid preflight must not load or invoke upstream")

    monkeypatch.setattr(curator, "_load_upstream", never)
    with pytest.raises(ValueError):
        curate(labels, **settings)
    assert not labels[1].exists()


@pytest.mark.parametrize("relation", ["same", "parent", "child", "symlink", "existing"])
def test_curation_does_not_overwrite_source_or_prior_output(labels, relation):
    source, output = labels
    if relation == "same":
        output = source
    elif relation == "parent":
        output = source.parent
    elif relation == "child":
        output = source / "nested.zarr"
    elif relation == "symlink":
        output.symlink_to(source, target_is_directory=True)
    else:
        zarr.array(np.full((4, 4, 4), 99, np.uint16), store=str(output), overwrite=True)
    before = zarr.open(str(source), mode="r")[:]
    with pytest.raises(ValueError):
        curate((source, output))
    np.testing.assert_array_equal(zarr.open(str(source), mode="r")[:], before)
    if relation == "existing":
        np.testing.assert_array_equal(zarr.open(str(output), mode="r")[:], 99)


@pytest.mark.parametrize("dtype", [np.float32, np.complex64])
def test_curation_requires_integer_label_ids(labels, dtype):
    zarr.open(str(labels[0]), mode="w", shape=(4, 4, 4), dtype=dtype)
    with pytest.raises(ValueError, match="integer or boolean"):
        curate(labels)
    assert not labels[1].exists()


def test_curation_rejects_negative_ids_before_publication(labels):
    arr = zarr.open(
        str(labels[0]), mode="w", shape=(4, 4, 4), chunks=(2, 2, 2), dtype="i2"
    )
    arr[:] = 0
    arr[0, 0, 0] = -1
    with pytest.raises(ValueError, match="nonnegative"):
        curate(labels)
    assert not labels[1].exists()


@pytest.mark.parametrize("failure", ["worker", "shape", "labels", "unreadable"])
def test_partial_or_invalid_upstream_output_is_never_published(
    labels, monkeypatch, failure
):
    def fake_process(**kwargs):
        shape = (2, 2, 2) if failure == "shape" else (4, 4, 4)
        output = zarr.open(
            kwargs["output_path"], mode="w", shape=shape, chunks=(2, 2, 2), dtype="u2"
        )
        output[0, 0, 0] = 99
        if failure == "worker":
            raise RuntimeError("worker failed after first write")
        if failure == "unreadable":
            (Path(kwargs["output_path"]) / "0.0.0").write_bytes(
                b"corrupt encoded chunk"
            )

    upstream = SimpleNamespace(process=fake_process)
    monkeypatch.setattr(curator, "_load_upstream", lambda: upstream)
    with pytest.raises((RuntimeError, ValueError)):
        curate(labels)
    assert not labels[1].exists()
    assert sorted(path.name for path in labels[0].parent.iterdir()) == ["source.zarr"]


def test_missing_upstream_does_not_break_help_but_processing_fails(labels, monkeypatch):
    monkeypatch.setattr(curator, "VC_PROOFREADER_PATH", labels[0].parent / "missing")
    with pytest.raises(FileNotFoundError, match="initialize the villa submodule"):
        curate(labels)
    assert not labels[1].exists()


def test_branch_filter_can_be_disabled_from_real_cli(labels):
    script = Path(curator.__file__).resolve()
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input",
            str(labels[0]),
            "--output",
            str(labels[1]),
            "--chunk-size",
            "2",
            "--workers",
            "2",
            "--no-reject-branches",
        ],
        cwd=labels[0].parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 nonempty chunks retained out of 8" in result.stdout
    assert "Gold Standard" not in result.stdout
    completion = zarr.open(str(labels[1]), mode="r").attrs["label_curation_completion"]
    assert completion["settings"]["workers"] == 2
    assert completion["settings"]["reject_branches"] is False


def test_actual_upstream_branch_heuristic_changes_chunk_selection(tmp_path):
    source = tmp_path / "branched.zarr"
    data = np.zeros((8, 8, 8), np.uint8)
    data[4, 1:7, 4] = 23
    data[4, 4, 1:7] = 23
    zarr.array(data, store=str(source), chunks=data.shape, overwrite=True)
    rejected = curator.curate_training_data(
        source, tmp_path / "reject.zarr", chunk_size=8, workers=1
    )
    retained = curator.curate_training_data(
        source, tmp_path / "keep.zarr", chunk_size=8, workers=1, reject_branches=False
    )
    assert rejected["chunks_retained_nonempty"] == 0
    assert retained["chunks_retained_nonempty"] == 1
    np.testing.assert_array_equal(
        zarr.open(str(tmp_path / "keep.zarr"), mode="r")[:], data
    )
