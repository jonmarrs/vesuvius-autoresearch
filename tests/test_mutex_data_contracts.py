"""Checks for explicit raw/label pairing, instance affinities, and launcher state."""

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import tifffile
import yaml  # type: ignore[import-untyped]
import zarr

from scripts import build_villa_prize_action_matrix as action_matrix
from scripts.training import (
    launch_mutex as launcher,
    mutex_data,
    prepare_mutex_training as prepare,
    probe_mutex_runtime,
)

REPO = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("group", [False, True])
def test_label_tiff_export_preserves_large_integer_ids(tmp_path, group):
    source, target = tmp_path / "labels.zarr", tmp_path / "labels.tif"
    labels = np.zeros((3, 4, 5), np.uint32)
    labels[1, 1, 1:3] = [2**24, 2**24 + 1]
    if group:
        zarr.open_group(str(source), mode="w").create_dataset("0", data=labels)
    else:
        zarr.array(labels, store=str(source), overwrite=True)
    prepare.export_zarr_to_tiff(str(source), str(target))
    actual = tifffile.imread(target)
    assert actual.dtype == np.uint32
    np.testing.assert_array_equal(actual, labels)


def test_export_never_takes_first_channel_implicitly(tmp_path):
    source, target = tmp_path / "labels.zarr", tmp_path / "labels.tif"
    zarr.open_group(str(source), mode="w").create_dataset(
        "0", data=np.ones((2, 3, 4, 5), np.uint16)
    )
    with pytest.raises(ValueError):
        prepare.export_zarr_to_tiff(str(source), str(target))
    assert not target.exists()


def test_preparer_missing_input_has_nonzero_cli_exit(tmp_path):
    raw = tmp_path / "raw.zarr"
    zarr.array(np.ones((8, 8, 8), np.uint16), store=str(raw))
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/training/prepare_mutex_training.py"),
            "--curated_zarr",
            str(tmp_path / "missing.zarr"),
            "--raw-zarr",
            str(raw),
            "--aligned-labels",
            "--output_dir",
            str(tmp_path / "output"),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert not (tmp_path / "output").exists()


def test_nonempty_folders_are_not_prepared_training_data(tmp_path):
    for folder in ("images", "affinity_graph"):
        path = tmp_path / folder
        path.mkdir()
        (path / "unrelated.txt").write_text("not a training artifact")
    assert not launcher._has_prepared_data(tmp_path)


def test_config_declares_affinity_heads_and_correct_complement_key(tmp_path):
    config = launcher.build_config("test", tmp_path, 64, 1)
    dataset = config["dataset_config"]
    assert set(dataset["targets"]) == {"attractive", "repulsive"}
    assert dataset["targets"]["attractive"]["out_channels"] == 6
    assert dataset["affinity_targets"]["attractive"]["invert"] is True
    assert dataset["affinity_targets"]["repulsive"]["invert"] is False


def test_checked_in_config_matches_pinned_target_contract():
    source = REPO / "configs/instance_seg/mutex_config.yaml"
    config = yaml.safe_load(source.read_text())
    generated = launcher.build_config("test", REPO, 64, 20)
    for key in ("targets", "affinity_targets"):
        assert config["dataset_config"][key] == generated["dataset_config"][key]
    assert not Path(config["dataset_config"]["data_path"]).is_absolute()


def test_execute_refusal_does_not_mark_training_as_executed(tmp_path):
    marker = tmp_path / "run.json"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/training/launch_mutex.py"),
            "--data-path",
            str(tmp_path / "missing"),
            "--execute",
            "--config-out",
            str(tmp_path / "config.yaml"),
            "--marker-out",
            str(marker),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert json.loads(marker.read_text())["executed"] is False


def test_compatibility_entrypoint_reaches_current_launcher(tmp_path):
    result = subprocess.run(
        [sys.executable, str(REPO / "train_mutex.py"), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "--data-path" in result.stdout


def sources(tmp_path, *, dtype=np.uint32, shape=(8, 8, 8)):
    labels = np.ones(shape, dtype=dtype)
    labels[:, :, shape[2] // 2 :] = 2
    raw = np.arange(np.prod(shape), dtype=np.uint16).reshape(shape)
    label_path, raw_path = tmp_path / "labels.zarr", tmp_path / "raw.zarr"
    zarr.array(labels, store=str(label_path))
    zarr.array(raw, store=str(raw_path))
    return label_path, raw_path, labels, raw


def prepared(tmp_path):
    label_path, raw_path, _, _ = sources(tmp_path)
    output = tmp_path / "prepared"
    prepare.prepare_mutex_data(label_path, raw_path, output, aligned_labels=True)
    return output


@pytest.mark.parametrize("dtype,base", [(np.uint32, 2**24), (np.uint64, 2**54)])
def test_instance_graph_preserves_touching_ids_and_pinned_affinities(
    tmp_path, dtype, base
):
    label_path, raw_path, labels, raw = sources(tmp_path, dtype=dtype)
    labels = labels + dtype(base)
    labels[0] = 0  # rejected/unknown voxels cannot supervise negatives
    zarr.open(str(label_path), mode="r+")[:] = labels
    zarr.open(str(label_path), mode="r+").attrs["origin"] = [3, 5, 7]
    output = tmp_path / "prepared"
    completion = prepare.prepare_mutex_data(
        label_path, raw_path, output, aligned_labels=True, name="fragment"
    )
    np.testing.assert_array_equal(
        zarr.open(str(output / "images/fragment.zarr"))[:], raw
    )
    graph = zarr.open_group(str(output / "affinity_graph/fragment.zarr"), mode="r")
    np.testing.assert_array_equal(graph["labels"][:], labels)
    assert graph["labels"].dtype == dtype
    assert completion["label_root_attrs"]["origin"] == [3, 5, 7]
    tools = mutex_data.graph_tools()
    attractive, repulsive, long_range = tools.build_offset_sets()
    for kind, offsets in (("attractive", attractive), ("repulsive", repulsive)):
        values, mask = tools.compute_affinities(
            labels,
            offsets,
            mode=kind,
            ignore_background=True,
            stride=2 if kind == "repulsive" else 1,
            stride_applicable_offsets=long_range if kind == "repulsive" else None,
        )
        np.testing.assert_array_equal(graph[f"affinities/{kind}"][:], values)
        np.testing.assert_array_equal(graph[f"mask/{kind}"][:], mask)
        assert not np.any(graph[f"mask/{kind}"][:, 0])
    cross = attractive.index((0, 0, 1))
    assert graph["mask/attractive"][cross, 2, 2, 3] == 1
    assert graph["affinities/attractive"][cross, 2, 2, 3] == 0
    cross = repulsive.index((0, 1, 1))
    assert graph["mask/repulsive"][cross, 2, 2, 3] == 1
    assert graph["affinities/repulsive"][cross, 2, 2, 3] == 1
    assert launcher._has_prepared_data(output)


def test_raw_origin_selects_exact_zyx_window(tmp_path):
    label_path, raw_path, labels, _ = sources(tmp_path)
    raw = np.arange(12 * 13 * 14, dtype=np.int16).reshape(12, 13, 14)
    zarr.array(raw, store=str(raw_path), overwrite=True)
    output = tmp_path / "prepared"
    result = prepare.prepare_mutex_data(
        label_path, raw_path, output, aligned_labels=True, raw_start=(2, 3, 4)
    )
    actual = zarr.open(str(output / "images/labels.zarr"), mode="r")
    np.testing.assert_array_equal(actual[:], raw[2:10, 3:11, 4:12])
    assert actual.dtype == np.int16
    assert result["raw_start_zyx"] == [2, 3, 4]
    assert result["shape_zyx"] == list(labels.shape)
    assert result["raw_source_shape_zyx"] == [12, 13, 14]


@pytest.mark.parametrize(
    "settings",
    [
        {"aligned_labels": False},
        {"raw_start": (-1, 0, 0)},
        {"raw_start": (1, 0, 0)},
        {"raw_start": (0, 0)},
        {"raw_start": (0, 0, 0.5)},
        {"name": "../escape"},
        {"name": ""},
        {"long_range_stride": 0},
        {"long_range_stride": True},
        {"max_voxels": 1},
        {"label_mode": "guess"},
    ],
)
def test_invalid_preparation_contracts_publish_nothing(tmp_path, settings):
    label_path, raw_path, labels, raw = sources(tmp_path)
    output = tmp_path / "prepared"
    options = {"aligned_labels": True, **settings}
    with pytest.raises(ValueError):
        prepare.prepare_mutex_data(label_path, raw_path, output, **options)
    assert not output.exists()
    np.testing.assert_array_equal(zarr.open(str(label_path))[:], labels)
    np.testing.assert_array_equal(zarr.open(str(raw_path))[:], raw)


@pytest.mark.parametrize(
    "bad", ["float_ids", "negative_ids", "nan_ct", "4d", "unequal"]
)
def test_invalid_payloads_publish_nothing(tmp_path, bad):
    label_path, raw_path, labels, raw = sources(tmp_path)
    if bad == "float_ids":
        zarr.array(labels.astype(np.float32), store=str(label_path), overwrite=True)
    elif bad == "negative_ids":
        zarr.array(-labels.astype(np.int16), store=str(label_path), overwrite=True)
    elif bad == "nan_ct":
        raw = raw.astype(np.float32)
        raw[0, 0, 0] = np.nan
        zarr.array(raw, store=str(raw_path), overwrite=True)
    elif bad == "4d":
        zarr.array(labels[np.newaxis], store=str(label_path), overwrite=True)
    else:
        zarr.array(np.ones((9, 8, 8), np.uint16), store=str(raw_path), overwrite=True)
    output = tmp_path / "prepared"
    with pytest.raises(ValueError):
        prepare.prepare_mutex_data(label_path, raw_path, output, aligned_labels=True)
    assert not output.exists()


def test_oversized_sparse_labels_rejected_before_voxel_reads(tmp_path, monkeypatch):
    label_path = tmp_path / "labels.zarr"
    zarr.open(
        str(label_path), mode="w", shape=(1024,) * 3, chunks=(64,) * 3, dtype="u2"
    )

    def no_read(*args, **kwargs):
        pytest.fail("oversized fragment was read before checking its bound")

    monkeypatch.setattr(zarr.Array, "__getitem__", no_read)
    with pytest.raises(ValueError, match="max_voxels"):
        prepare.prepare_mutex_data(
            label_path, tmp_path / "raw", tmp_path / "output", aligned_labels=True
        )


@pytest.mark.parametrize("where", ["same", "child", "parent", "symlink", "existing"])
def test_outputs_cannot_replace_or_overlap_sources(tmp_path, where):
    label_path, raw_path, labels, raw = sources(tmp_path)
    if where == "same":
        output = label_path
    elif where == "child":
        output = raw_path / "nested"
    elif where == "parent":
        output = tmp_path
    elif where == "symlink":
        output = tmp_path / "link"
        output.symlink_to(raw_path, target_is_directory=True)
    else:
        output = tmp_path / "existing"
        output.mkdir()
        (output / "keep").write_text("old result")
    with pytest.raises(ValueError):
        prepare.prepare_mutex_data(label_path, raw_path, output, aligned_labels=True)
    np.testing.assert_array_equal(zarr.open(str(label_path))[:], labels)
    np.testing.assert_array_equal(zarr.open(str(raw_path))[:], raw)
    if where == "existing":
        assert (output / "keep").read_text() == "old result"


@pytest.mark.parametrize("boundary", ["graph", "write", "metadata", "verify"])
def test_preparation_failure_discards_staging(tmp_path, monkeypatch, boundary):
    label_path, raw_path, labels, raw = sources(tmp_path)

    def fail(*args, **kwargs):
        raise OSError("injected artifact failure")

    if boundary == "graph":
        monkeypatch.setattr(mutex_data.graph_tools(), "compute_affinities", fail)
    elif boundary == "write":
        monkeypatch.setattr(zarr.Group, "create_dataset", fail)
    elif boundary == "metadata":
        monkeypatch.setattr(prepare, "write_json", fail)
    else:
        monkeypatch.setattr(prepare, "validate_prepared_data", fail)
    output = tmp_path / "prepared"
    with pytest.raises(OSError):
        prepare.prepare_mutex_data(label_path, raw_path, output, aligned_labels=True)
    assert not output.exists()
    assert {p.name for p in tmp_path.iterdir()} == {"labels.zarr", "raw.zarr"}
    np.testing.assert_array_equal(zarr.open(str(label_path))[:], labels)
    np.testing.assert_array_equal(zarr.open(str(raw_path))[:], raw)


def test_failed_tiff_write_leaves_no_partial_output(tmp_path, monkeypatch):
    label_path, _, _, _ = sources(tmp_path)

    def fail(path, *args, **kwargs):
        Path(path).write_bytes(b"partial")
        raise OSError("interrupted TIFF")

    monkeypatch.setattr(prepare.tifffile, "imwrite", fail)
    with pytest.raises(OSError):
        prepare.export_zarr_to_tiff(label_path, tmp_path / "labels.tif")
    assert not (tmp_path / "labels.tif").exists()
    assert not list(tmp_path.glob("*.tif"))


def test_component_mode_requires_binary_semantics_and_retains_source_ids(tmp_path):
    label_path, raw_path, labels, _ = sources(tmp_path)
    with pytest.raises(ValueError, match="binary"):
        prepare.prepare_mutex_data(
            label_path,
            raw_path,
            tmp_path / "invalid",
            aligned_labels=True,
            label_mode="foreground-components",
        )
    labels[:] = 0
    labels[1:3, 1:3, 1:3] = 9
    labels[5:7, 5:7, 5:7] = 9
    zarr.open(str(label_path), mode="r+")[:] = labels
    output = tmp_path / "prepared"
    prepare.prepare_mutex_data(
        label_path,
        raw_path,
        output,
        aligned_labels=True,
        label_mode="foreground-components",
    )
    graph = zarr.open_group(str(output / "affinity_graph/labels.zarr"), mode="r")
    np.testing.assert_array_equal(graph["source_labels"][:], labels)
    assert graph["labels"][1, 1, 1] != graph["labels"][5, 5, 5]
    assert (
        mutex_data.validate_prepared_data(output)["completion"]["label_mode"]
        == "foreground-components"
    )


@pytest.mark.parametrize(
    "corruption",
    [
        "contract",
        "coverage",
        "offset",
        "extra",
        "missing",
        "binary",
        "mask",
        "nan",
        "labels",
        "empty_edges",
    ],
)
def test_readiness_inspects_payload_not_just_completion(tmp_path, corruption):
    output = prepared(tmp_path)
    graph = zarr.open_group(str(output / "affinity_graph/labels.zarr"), mode="r+")
    completion_path = output / "mutex_data_completion.json"
    completion = json.loads(completion_path.read_text())
    if corruption == "contract":
        completion["contract"] = 999
    elif corruption == "coverage":
        completion["valid_edges"]["attractive"] += 1
    elif corruption == "offset":
        graph.attrs["attractive_offsets"] = [[0, 0, 0]] * 6
    elif corruption == "extra":
        (output / "images/extra.tif").write_bytes(b"extra")
    elif corruption == "missing":
        del graph["mask/repulsive"]
    elif corruption == "binary":
        graph["affinities/attractive"][0, 1, 1, 1] = 2
    elif corruption == "mask":
        graph["affinities/attractive"][:, 0, 0, 0] = 1
        graph["mask/attractive"][:, 0, 0, 0] = 0
    elif corruption == "nan":
        zarr.array(
            np.full((8,) * 3, np.nan, np.float32),
            store=str(output / "images/labels.zarr"),
            overwrite=True,
        )
        completion["raw_dtype"] = "float32"
    elif corruption == "labels":
        del graph["labels"]
        graph.create_dataset("labels", data=np.full((8,) * 3, -1, np.int32))
        completion["label_dtype"] = "int32"
    else:
        graph["mask/attractive"][:] = 0
        graph["affinities/attractive"][:] = 0
        completion["valid_edges"]["attractive"] = 0
    completion_path.write_text(json.dumps(completion))
    assert not launcher._has_prepared_data(output)


def test_requested_patch_must_fit_prepared_fragment(tmp_path):
    output = prepared(tmp_path)
    mutex_data.validate_prepared_data(output, patch=8)
    with pytest.raises(ValueError, match="smaller"):
        mutex_data.validate_prepared_data(output, patch=9)


def launch_args(tmp_path, output):
    return [
        "--data-path",
        str(output),
        "--patch",
        "4",
        "--execute",
        "--config-out",
        str(tmp_path / "config.json"),
        "--marker-out",
        str(tmp_path / "run.json"),
    ]


@pytest.mark.parametrize(
    "returncode,stdout",
    [
        (1, '{"status":"FAIL"}'),
        (0, "noise"),
        (0, '{"status":"PASS"}'),
        (0, '{"contract":1,"status":"FAIL"}'),
    ],
)
def test_failed_or_unverified_runtime_probe_never_starts_training(
    tmp_path, monkeypatch, returncode, stdout
):
    output = prepared(tmp_path)

    def run(cmd, **kwargs):
        assert Path(cmd[1]) == launcher.RUNTIME_PROBE
        assert str(launcher.VILLA_SRC) in kwargs["env"]["PYTHONPATH"]
        return subprocess.CompletedProcess(
            cmd, returncode, stdout, "dependency failure"
        )

    def forbidden(*args, **kwargs):
        pytest.fail("training started without a verified loader")

    monkeypatch.setattr(launcher.subprocess, "run", run)
    monkeypatch.setattr(launcher.subprocess, "Popen", forbidden)
    assert launcher.main(launch_args(tmp_path, output)) != 0
    marker = json.loads((tmp_path / "run.json").read_text())
    assert marker["executed"] is False
    assert marker["runtime_verified"] is False
    assert marker["success"] is False


@pytest.mark.parametrize("exit_code", [0, 3, -15, "oserror"])
def test_execution_status_records_actual_process_start(
    tmp_path, monkeypatch, exit_code
):
    output = prepared(tmp_path)

    def probe(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, '{"contract":1,"status":"PASS"}', "")

    class Training:
        pid = 12345

        def __init__(self, cmd, **kwargs):
            assert Path(cmd[1]) == launcher.VILLA_TRAINING_CLI
            assert json.loads((tmp_path / "run.json").read_text())["executed"] is False
            if exit_code == "oserror":
                raise OSError("cannot start process")

        def wait(self):
            marker = json.loads((tmp_path / "run.json").read_text())
            assert marker["state"] == "running"
            assert marker["executed"] is True
            assert marker["pid"] == self.pid
            return exit_code

    monkeypatch.setattr(launcher.subprocess, "run", probe)
    monkeypatch.setattr(launcher.subprocess, "Popen", Training)
    result = launcher.main(launch_args(tmp_path, output))
    marker = json.loads((tmp_path / "run.json").read_text())
    assert marker["runtime_verified"] is True
    assert marker["executed"] is (exit_code != "oserror")
    assert marker["success"] is (exit_code == 0)
    assert result == (
        1 if exit_code == "oserror" else 128 - exit_code if exit_code < 0 else exit_code
    )
    assert marker["submittable"] is None


@pytest.mark.parametrize("option", ["--patch", "--max-epoch"])
@pytest.mark.parametrize("value", ["0", "-1"])
def test_invalid_training_sizes_do_not_write_run_artifacts(tmp_path, option, value):
    marker = tmp_path / "run.json"
    assert launcher.main([option, value, "--marker-out", str(marker)]) != 0
    assert not marker.exists()


@pytest.mark.parametrize("alias", ["inside_data", "same_outputs", "symlink_data"])
def test_launch_outputs_cannot_alias_data_or_each_other(tmp_path, alias):
    data = tmp_path / "data"
    data.mkdir()
    config, marker = tmp_path / "config.json", tmp_path / "run.json"
    if alias == "inside_data":
        config = data / "config.json"
    elif alias == "same_outputs":
        marker = config
    else:
        config.symlink_to(data, target_is_directory=True)
    assert (
        launcher.main(
            [
                "--data-path",
                str(data),
                "--config-out",
                str(config),
                "--marker-out",
                str(marker),
            ]
        )
        != 0
    )
    assert not marker.exists()
    assert not list(data.iterdir())


def test_default_dry_runs_use_unique_local_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "PROJECT_ROOT", tmp_path)
    for _ in range(2):
        assert launcher.main(["--data-path", str(tmp_path / "missing")]) == 0
    markers = list((tmp_path / "local_data/mutex_launch").glob("*/run.json"))
    assert len(markers) == 2
    for source in markers:
        status = json.loads(source.read_text())
        assert status["state"] == "dry_run"
        assert status["executed"] is False
        assert status["runtime_verified"] is False
        assert source.with_name("config.json").is_file()


@pytest.mark.parametrize(
    "state",
    ["dry_run", "runtime_failed", "running", "completed", "training_failed", "refused"],
)
def test_action_matrix_uses_current_mutex_state_instead_of_readiness_guess(
    tmp_path, monkeypatch, state
):
    monkeypatch.setattr(action_matrix, "REPO_ROOT", tmp_path)
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "mutex_affinity_run.json").write_text(
        json.dumps({"executed": True, "submittable": True})
    )
    older = tmp_path / "local_data/mutex_launch/old/run.json"
    current = tmp_path / "local_data/mutex_launch/current/run.json"
    for path in (older, current):
        path.parent.mkdir(parents=True)
    older.write_text(json.dumps({"state": "completed"}))
    current.write_text(
        json.dumps(
            {
                "state": state,
                "data_prepared": True,
                "runtime_verified": False,
                "executed": False,
                "submittable": None,
            }
        )
    )
    os.utime(older, ns=(1, 1))
    row = next(
        item
        for item in action_matrix._collect_baselines()
        if item["id"] == "mutex_affinity"
    )
    assert row["status"] == state
    assert Path(row["marker_path"]) == current
    assert row["details"]["submittable"] is None
    assert row["launcher"] == "scripts/training/launch_mutex.py"
    selected = next(
        item
        for item in action_matrix._collect_baselines(older)
        if item["id"] == "mutex_affinity"
    )
    assert selected["status"] == "completed"


def test_action_matrix_does_not_use_historical_mutex_marker_when_no_run_exists(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(action_matrix, "REPO_ROOT", tmp_path)
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports/mutex_affinity_run.json").write_text(
        json.dumps({"executed": True, "submittable": True})
    )
    row = next(
        item
        for item in action_matrix._collect_baselines()
        if item["id"] == "mutex_affinity"
    )
    assert row["status"] == "missing"
    assert row["marker_path"] is None


def test_runtime_probe_reports_import_or_loader_failure_as_json(monkeypatch, capsys):
    def fail(*args):
        print("incidental upstream logging")
        raise ImportError("optional runtime dependency absent")

    monkeypatch.setattr(probe_mutex_runtime, "probe", fail)
    assert probe_mutex_runtime.main(["--config", "unused.json"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "FAIL"
    assert result["error"] == "ImportError: optional runtime dependency absent"


@pytest.mark.xfail(
    strict=True,
    reason="pinned Mutex loader slices C/Z/Y instead of preserving channels and slicing Z/Y/X",
)
def test_pinned_loader_reads_channel_leading_affinity_windows(tmp_path):
    # Execute the actual pinned class, without bootstrapping unrelated optional
    # package dependencies. No upstream implementation is copied or patched.
    path = launcher.VILLA_SRC / "vesuvius/models/datasets/mutex_affinity_dataset.py"
    tree = ast.parse(path.read_text())
    node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ZarrArrayHandle"
    )
    module = ast.Module(
        body=[
            ast.ImportFrom(
                module="__future__", names=[ast.alias(name="annotations")], level=0
            ),
            node,
        ],
        type_ignores=[],
    )
    namespace = {"np": np}
    exec(compile(ast.fix_missing_locations(module), str(path), "exec"), namespace)
    handle_type = namespace["ZarrArrayHandle"]
    array = zarr.array(
        np.arange(6 * 8 * 9 * 10).reshape(6, 8, 9, 10),
        store=str(tmp_path / "affinities.zarr"),
    )
    actual = handle_type(array).read_window((2, 3, 4), (3, 3, 3))
    np.testing.assert_array_equal(actual, array[:, 2:5, 3:6, 4:7])
