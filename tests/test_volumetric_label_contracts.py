"""Checks for geometry, gating, and publication of local 3D pseudo-labels."""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import zarr

from scripts.labeling import generate_3d_ink_labels as ink

REPO = Path(__file__).resolve().parents[1]


def array(path, data):
    return zarr.array(data, store=str(path), chunks=data.shape, overwrite=True)


@pytest.fixture
def inputs(tmp_path):
    ct, pred, output = (
        tmp_path / name for name in ("ct.zarr", "pred.zarr", "ink.zarr")
    )
    array(ct, np.ones((7, 7, 7), np.float32))
    array(pred, np.ones((7, 7), np.float32))
    return ct, pred, output


def generate(inputs, bbox=(0, 7, 0, 7, 0, 7), **settings):
    settings.setdefault("aligned_prediction", True)
    return ink.generate_3d_ink_labels(
        *(str(path) for path in inputs), *bbox, **settings
    )


@pytest.mark.parametrize(
    "bbox",
    [
        (0, 8, 0, 7, 0, 7),
        (-1, 7, 0, 7, 0, 7),
        (0, 7, -1, 6, 0, 7),
        (0, 7, 0, 7, 0.5, 7),
        (0, 0, 0, 7, 0, 7),
    ],
)
def test_invalid_bbox_never_publishes(inputs, bbox):
    with pytest.raises(ValueError):
        generate(inputs, bbox=bbox)
    assert not inputs[2].exists()


@pytest.mark.parametrize(
    "settings",
    [
        {"ink_threshold": np.nan},
        {"ink_threshold": -0.1},
        {"ink_threshold": 1.1},
        {"ct_percentile": np.nan},
        {"ct_percentile": -1},
        {"ct_percentile": 101},
        {"morphological_close": -1},
        {"morphological_close": 1.5},
        {"surface_window": -1},
        {"min_component_voxels": -1},
    ],
)
def test_invalid_settings_never_publishes(inputs, settings):
    with pytest.raises(ValueError):
        generate(inputs, **settings)
    assert not inputs[2].exists()


@pytest.mark.parametrize(
    "data",
    [
        np.ones((2, 7, 7), np.float32),
        np.full((7, 7), np.nan, np.float32),
        np.full((7, 7), 1.1, np.float32),
        np.full((7, 7), -0.1, np.float32),
        np.ones((7, 7), np.uint16),
    ],
)
def test_invalid_prediction_never_publishes(inputs, data):
    array(inputs[1], data)
    with pytest.raises(ValueError):
        generate(inputs)
    assert not inputs[2].exists()


def test_nonfinite_ct_never_publishes(inputs):
    ct = zarr.open(str(inputs[0]), mode="r+")
    ct[0, 0, 0] = np.nan
    with pytest.raises(ValueError):
        generate(inputs)
    assert not inputs[2].exists()


def test_existing_output_is_not_silently_reused(inputs):
    old = array(inputs[2], np.full((7, 7, 7), 19, np.uint8))
    with pytest.raises(ValueError):
        generate(inputs)
    np.testing.assert_array_equal(old[:], 19)


def test_output_cannot_alias_ct(inputs):
    with pytest.raises(ValueError):
        generate((inputs[0], inputs[1], inputs[0]))
    assert zarr.open(str(inputs[0]), mode="r").dtype == np.float32


def test_closing_cannot_label_columns_rejected_by_prediction(inputs):
    pred = zarr.open(str(inputs[1]), mode="r+")
    pred[3, 3] = 0
    generate(inputs, morphological_close=3)
    labels = zarr.open(str(inputs[2]), mode="r")[:]
    assert not labels[:, 3, 3].any()


def test_curator_help_works_from_outside_checkout(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/labeling/curate_training_data.py"),
            "--help",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "--no-reject-branches" in result.stdout


def test_prediction_alignment_requires_explicit_declaration(inputs):
    with pytest.raises(ValueError, match="aligned-prediction"):
        generate(inputs, aligned_prediction=False)
    assert not inputs[2].exists()


@pytest.mark.parametrize("source", [0, 1])
@pytest.mark.parametrize("relation", ["child", "parent", "symlink", "broken_symlink"])
def test_sources_and_output_must_be_separate(inputs, source, relation):
    ct, pred, output = inputs
    target = inputs[source]
    if relation == "child":
        output = target / "new.zarr"
    elif relation == "parent":
        output = target.parent
    elif relation == "symlink":
        output.symlink_to(target, target_is_directory=True)
    else:
        output.symlink_to(target.parent / "missing", target_is_directory=True)
    with pytest.raises(ValueError):
        generate((ct, pred, output))
    np.testing.assert_array_equal(zarr.open(str(ct), mode="r")[:], 1)
    np.testing.assert_array_equal(zarr.open(str(pred), mode="r")[:], 1)


@pytest.mark.parametrize("shape", [(7, 7), (1, 7, 7, 7), (0, 7, 7)])
def test_ct_must_be_nonempty_3d(inputs, shape):
    zarr.open(str(inputs[0]), mode="w", shape=shape, chunks=True, dtype="u1")
    with pytest.raises(ValueError, match="nonempty|3D"):
        generate(inputs)
    assert not inputs[2].exists()


@pytest.mark.parametrize("target", [0, 1])
def test_group_child_is_not_guessed(inputs, target):
    import shutil

    shutil.rmtree(inputs[target])
    group = zarr.open_group(str(inputs[target]), mode="w")
    group.create_dataset("other", data=np.ones((7, 7, 7), np.uint8))
    with pytest.raises(ValueError, match="array '0'"):
        generate(inputs)
    assert not inputs[2].exists()


def test_sparse_labels_retain_exact_nonzero_bbox_and_provenance(tmp_path):
    ct, pred, output = (
        tmp_path / name for name in ("ct.zarr", "pred.zarr", "labels.zarr")
    )
    data = np.broadcast_to(np.arange(8, dtype=np.float32)[:, None, None], (8, 9, 10))
    array(ct, data)
    group = zarr.open_group(str(pred), mode="w")
    probabilities = np.full((1, 3, 4), 255, np.uint8)
    probabilities[0, 1, 2] = 127
    group.create_dataset("0", data=probabilities)
    result = generate((ct, pred, output), bbox=(1, 5, 2, 5, 3, 7))
    labels = zarr.open(str(output), mode="r")
    expected = np.zeros((8, 9, 10), np.uint8)
    expected[4, 2:5, 3:7] = 1
    expected[4, 3, 5] = 0
    np.testing.assert_array_equal(labels[:], expected)
    assert result["labeled_voxels"] == 11
    assert result["voxels"] == 48
    assert result["connected_components_total"] is None
    completion = labels.attrs["ink_label_completion"]
    assert completion["contract"] == 1
    assert completion["ct_path"] == str(ct.resolve())
    assert completion["evaluated_bbox_zyx"] == [1, 5, 2, 5, 3, 7]
    assert "unevaluated" in completion["outside_bbox"]
    assert completion["alignment"]["origin_zyx"] == [1, 2, 3]


def test_global_threshold_uses_active_columns(tmp_path):
    ct, pred, output = (
        tmp_path / name for name in ("ct.zarr", "pred.zarr", "labels.zarr")
    )
    data = np.full((3, 2, 2), 100, np.float32)
    data[:, 0, 0] = [1, 2, 3]
    probabilities = np.zeros((2, 2), np.float32)
    probabilities[0, 0] = 1
    array(ct, data)
    array(pred, probabilities)
    result = generate(
        (ct, pred, output),
        bbox=(0, 3, 0, 2, 0, 2),
        ct_percentile=50,
        global_ct_threshold=True,
    )
    labels = zarr.open(str(output), mode="r")[:]
    assert result["labeled_voxels"] == 2
    np.testing.assert_array_equal(labels[:, 0, 0], [0, 1, 1])
    assert labels.sum() == 2


@pytest.mark.parametrize("global_threshold", [False, True])
def test_no_active_columns_publish_honest_empty_labels(inputs, global_threshold):
    pred = zarr.open(str(inputs[1]), mode="r+")
    pred[:] = 0
    stats = generate(inputs, global_ct_threshold=global_threshold)
    assert stats["active_surface_columns"] == stats["labeled_voxels"] == 0
    assert "ink_label_completion" in zarr.open(str(inputs[2]), mode="r").attrs


def test_closing_preserves_ct_intensity_gate(inputs):
    ct = zarr.open(str(inputs[0]), mode="r+")
    ct[3, 3, 3] = 0
    generate(inputs, morphological_close=1)
    labels = zarr.open(str(inputs[2]), mode="r")[:]
    assert not labels[3, 3, 3]
    assert labels[3, 3, 2]


def test_closing_preserves_ct_peak_depth_gate(inputs):
    ct = zarr.open(str(inputs[0]), mode="r+")
    ct[3, :, :] = 2
    ct[0, 3, 3] = 3
    generate(inputs, ct_percentile=0, surface_window=1, morphological_close=1)
    labels = zarr.open(str(inputs[2]), mode="r")[:]
    assert not labels[2:, 3, 3].any()
    assert labels[3, 3, 2]


def test_close_one_is_a_radius_and_edges_are_disclosed(inputs):
    generate(inputs, morphological_close=1)
    labels = zarr.open(str(inputs[2]), mode="r")[:]
    expected = np.zeros((7, 7, 7), np.uint8)
    expected[1:-1, 1:-1, 1:-1] = 1
    np.testing.assert_array_equal(labels, expected)


def test_connected_components_remove_only_small_islands(inputs):
    ct = zarr.open(str(inputs[0]), mode="r+")
    ct[:] = 0
    ct[3] = 10
    pred = zarr.open(str(inputs[1]), mode="r+")
    pred[:] = 0
    pred[1:3, 1:3] = 1
    pred[5, 5] = 1
    stats = generate(inputs, min_component_voxels=3)
    assert stats["connected_components_total"] == 2
    assert stats["connected_components_kept"] == 1
    assert stats["labeled_voxels"] == 4


@pytest.mark.parametrize("failure", ["read", "write", "debug", "metadata"])
def test_generation_failure_does_not_publish_partial_output(
    inputs, monkeypatch, failure
):
    def fail(*args, **kwargs):
        raise OSError("injected failure")

    settings = {}
    if failure == "read":
        monkeypatch.setattr(ink, "_load_zarr_window", fail)
    elif failure == "write":
        original = zarr.Array.__setitem__

        def write(self, key, value):
            if Path(self.store.path).name == "new.zarr":
                fail()
            return original(self, key, value)

        monkeypatch.setattr(zarr.Array, "__setitem__", write)
    elif failure == "metadata":
        monkeypatch.setattr(zarr.attrs.Attributes, "__setitem__", fail)
    else:
        settings["debug_png"] = str(inputs[2] / "debug.png")
        monkeypatch.setattr(ink, "_write_debug_png", fail)
    with pytest.raises(OSError, match="injected"):
        generate(inputs, **settings)
    assert not inputs[2].exists()
    assert sorted(path.name for path in inputs[0].parent.iterdir()) == [
        "ct.zarr",
        "pred.zarr",
    ]


def test_debug_png_is_part_of_completed_output_and_uses_actual_threshold(
    inputs, monkeypatch
):
    from matplotlib.axes import Axes
    from PIL import Image

    pred = zarr.open(str(inputs[1]), mode="r+")
    pred[:] = np.broadcast_to(np.linspace(0, 1, 7), (7, 7))
    levels = []
    original = Axes.contour

    def capture(self, *args, **kwargs):
        levels.extend(kwargs["levels"])
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Axes, "contour", capture)
    generate(inputs, ink_threshold=0.7, debug_png=str(inputs[2] / "debug.png"))
    with Image.open(inputs[2] / "debug.png") as png:
        assert min(png.size) > 0
    assert levels == [0.7] * 4
    assert (
        zarr.open(str(inputs[2]), mode="r").attrs["ink_label_completion"]["debug_png"]
        == "debug.png"
    )


def test_debug_cannot_write_outside_output(inputs):
    with pytest.raises(ValueError, match="direct .png child"):
        generate(inputs, debug_png=str(inputs[0] / "overwrite.png"))
    assert not inputs[2].exists()


def producer_prediction(inputs, origin=(0, 0, 0)):
    import shutil

    from scripts.inference.predict import save_vc3d_zarr

    shutil.rmtree(inputs[1])
    save_vc3d_zarr(
        inputs[1],
        np.full((7, 7), 255, np.uint8),
        source_uri=str(inputs[0]),
        origin_xyz=list(origin),
    )


def test_actual_prediction_export_is_accepted_with_matching_alignment(inputs):
    producer_prediction(inputs)
    stats = generate(inputs)
    assert stats["labeled_voxels"] == 7**3
    completion = zarr.open(str(inputs[2]), mode="r").attrs["ink_label_completion"]
    assert "matching producer metadata" in completion["alignment"]["basis"]


@pytest.mark.parametrize(
    "change",
    [
        "origin",
        "source",
        "shape",
        "nonfinite",
        "partial",
        "translation",
        "axes",
        "missing_meta",
        "malformed_meta",
    ],
)
def test_contradictory_or_unsupported_prediction_metadata_is_rejected(inputs, change):
    import json

    producer_prediction(inputs)
    metadata_path = inputs[1] / "meta.json"
    metadata = json.loads(metadata_path.read_text())
    if change == "origin":
        metadata["origin_xyz"] = [1, 0, 0]
    elif change == "source":
        metadata["source_uri"] = str(inputs[0].parent / "another.zarr")
    elif change == "shape":
        metadata["width"] = 99
    elif change == "nonfinite":
        metadata["voxelsize"] = float("nan")
    elif change == "partial":
        metadata["prediction_complete"] = False
    elif change in ("translation", "axes"):
        root = zarr.open_group(str(inputs[1]), mode="a")
        frames = root.attrs["multiscales"]
        if change == "translation":
            frames[0]["datasets"][0]["coordinateTransformations"][1]["translation"][
                1
            ] = 7.91
        else:
            frames[0]["axes"][1]["name"] = "u"
        root.attrs["multiscales"] = frames
    elif change == "malformed_meta":
        metadata = ["invalid"]
    metadata_path.write_text(json.dumps(metadata))
    if change == "missing_meta":
        metadata_path.unlink()
    with pytest.raises(ValueError):
        generate(inputs)
    assert not inputs[2].exists()


@pytest.mark.parametrize(
    "script", ["generate_3d_ink_labels.py", "curate_training_data.py"]
)
def test_cli_failure_has_nonzero_exit_and_no_success_message(inputs, script):
    if script == "generate_3d_ink_labels.py":
        args = [
            "--ct",
            str(inputs[0]),
            "--ink-pred",
            str(inputs[1]),
            "--bbox",
            "0",
            "8",
            "0",
            "7",
            "0",
            "7",
            "--aligned-prediction",
        ]
    else:
        args = ["--input", str(inputs[0]), "--chunk-size", "64"]
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/labeling" / script),
            *args,
            "--output",
            str(inputs[2]),
        ],
        cwd=inputs[0].parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "failed" in result.stderr
    assert "# OK" not in result.stdout and "curation complete" not in result.stdout
    assert not inputs[2].exists()


def run_metadata(inputs):
    return {
        "source_uri": str(inputs[0]),
        "vc3d_zarr_path": str(inputs[1]),
        "prediction_complete": True,
        "coverage_fraction": 1.0,
        "num_parts": 1,
        "part_id": 0,
        "position_xyz": [0, 0, 0],
        "height_px": 7,
        "width_px": 7,
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"prediction_complete": False},
        {"num_parts": 2},
        {"coverage_fraction": 0.9},
        {"coverage_fraction": None},
        {"position_xyz": [0, 1, 0]},
        {"width_px": 6},
        {"vc3d_zarr_path": "elsewhere.zarr"},
        {"source_uri": "elsewhere.zarr"},
    ],
)
def test_conventional_prediction_run_metadata_rejects_shards_and_conflicts(
    inputs, changes
):
    import json

    metadata = dict(run_metadata(inputs), **changes)
    (inputs[1].parent / "pred_meta.json").write_text(json.dumps(metadata))
    with pytest.raises(ValueError):
        generate(inputs)
    assert not inputs[2].exists()


def test_custom_prediction_run_metadata_is_checked_and_recorded(inputs):
    import json

    path = inputs[0].parent / "custom-run.json"
    path.write_text(json.dumps(run_metadata(inputs)))
    generate(inputs, prediction_metadata=str(path))
    completion = zarr.open(str(inputs[2]), mode="r").attrs["ink_label_completion"]
    record = completion["alignment"]["run_metadata"]
    assert record["path"] == str(path.resolve())
    assert "matching complete" in record["coverage_basis"]


def test_requested_missing_prediction_metadata_is_not_ignored(inputs):
    with pytest.raises(FileNotFoundError):
        generate(inputs, prediction_metadata=str(inputs[0].parent / "missing.json"))
    assert not inputs[2].exists()
