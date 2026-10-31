"""Binary evaluation contracts; stub adapters are distinct from pinned-source tests."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import tifffile
import zarr

from scripts import evaluate_villa_metrics as evaluation
from scripts.evaluation_artifacts import VolumeSource


@pytest.fixture(autouse=True)
def session_environment():
    """main() hides CUDA (--device cpu, the default) and sets MPLBACKEND for its process, as a command should. Called
    here, that process is the test session: put both back after each test, or every later test runs CPU-only
    (tests/test_fibers.py's test_cpu_gpu_vesselness_parity fails on a machine with a GPU)."""
    names = ("CUDA_VISIBLE_DEVICES", "MPLBACKEND")
    saved = {name: os.environ.get(name) for name in names}
    yield
    for name, value in saved.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


@pytest.fixture
def metric_root(tmp_path):
    """Small adapter fixtures, not implementations of the upstream metrics."""
    root = tmp_path / "villa"
    directory = root / "segmentation/evaluation/metrics"
    directory.mkdir(parents=True)
    sources = {
        "dice": "import numpy as np\ndef compute(label, prediction, threshold=0.5):\n    hard = prediction >= threshold\n    return float(2 * (label * hard).sum() / (label.sum() + hard.sum() + 1e-12))\n",
        "centerline_dice": "import numpy as np\ndef compute(label, prediction, **kwargs):\n    return {'centerline_dice': float(np.array_equal(label, prediction))}\n",
        "connected_components": "def compute(label, prediction, **kwargs):\n    return {'connected_components_difference_total': float(abs(int(label.sum()) - int(prediction.sum())))}\n",
        "mean_ap": "def compute(label, prediction, **kwargs):\n    return {'mean_ap': float(prediction.max())}\n",
        "dice_multiclass": "def compute(label, prediction, **kwargs):\n    return 1.0\n",
        "critical_components_multiclass": "def compute(label, prediction, **kwargs):\n    return 0.0\n",
        "skeleton_distance_length": "from pathlib import Path\nfrom PIL import Image\nwandb = object()\ndef compute(label, prediction, output_folder):\n    assert wandb is None\n    directory=Path(output_folder)\n    directory.mkdir(parents=True)\n    Image.new('RGB', (8,8)).save(directory/'histogram.png')\n    return 0.0\n",
    }
    for name, source in sources.items():
        (directory / f"{name}.py").write_text(source)
    return root


@pytest.fixture
def inputs(tmp_path, metric_root):
    gt = np.zeros((4, 5, 6), np.uint8)
    gt[:, 2:4, 2:4] = 1
    pred = np.where(gt, 0.6, 0.1).astype(np.float64)
    for name, values in (("gt", gt), ("pred", pred)):
        tifffile.imwrite(
            tmp_path / f"{name}.tif",
            values,
            photometric="minisblack",
            metadata={"axes": "ZYX"},
        )
    return tmp_path, metric_root


def argv(inputs, *extra, output="report"):
    root, metrics = inputs
    return [
        "--gt",
        str(root / "gt.tif"),
        "--pred",
        str(root / "pred.tif"),
        "--villa-root",
        str(metrics),
        "--out",
        str(root / output),
        "--aligned-inputs",
        *extra,
    ]


def summary(inputs, output="report"):
    return json.loads((inputs[0] / output / "summary.json").read_text())


def metric_file(inputs, name):
    return inputs[1] / f"segmentation/evaluation/metrics/{name}.py"


def test_complete_report_captures_exact_metric_sources_and_input_digests(
    inputs, capsys
):
    assert evaluation.main(argv(inputs)) == 0
    result = summary(inputs)
    assert json.loads(capsys.readouterr().out)["status"] == "COMPLETE"
    assert result["status"] == "COMPLETE" and len(result["metrics"]) == 4
    assert result["reference"]["bbox_zyx"] == [0, 4, 0, 5, 0, 6]
    assert result["prediction"]["decoded_region_sha256"]
    assert not result["alignment_verified"] and not result["label_quality_verified"]
    for name, record in result["metric_sources"].items():
        captured = inputs[0] / "report" / record["captured_source"]
        assert captured.read_bytes() == metric_file(inputs, name).read_bytes()
        assert hashlib.sha256(captured.read_bytes()).hexdigest() == record["sha256"]


@pytest.mark.parametrize("threshold,expected", [(0.8, 0), (0.6, 1), (0.5, 1)])
def test_all_hard_metrics_use_one_recorded_threshold_rule(inputs, threshold, expected):
    assert evaluation.main(argv(inputs, "--threshold", str(threshold))) == 0
    result = summary(inputs)
    assert result["metrics"]["dice"]["values"] == pytest.approx(expected)
    assert result["metrics"]["centerline_dice"]["values"]["centerline_dice"] == expected
    assert (result["prediction_positive_voxels"] > 0) == bool(expected)
    assert result["settings"]["threshold_rule"] == ">="


def test_mismatched_shapes_are_not_cropped(inputs):
    path = inputs[0] / "pred.tif"
    tifffile.imwrite(
        path, np.ones((3, 5, 6)), photometric="minisblack", metadata={"axes": "ZYX"}
    )
    assert evaluation.main(argv(inputs)) == 1
    assert not (inputs[0] / "report").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("gt", 2),
        ("gt", 128),
        ("gt", float("nan")),
        ("pred", float("nan")),
        ("pred", float("inf")),
        ("pred", -0.1),
        ("pred", 1.1),
    ],
)
def test_invalid_labels_or_probabilities_publish_no_report(inputs, field, value):
    path = inputs[0] / f"{field}.tif"
    tifffile.imwrite(
        path,
        np.full((4, 5, 6), value),
        photometric="minisblack",
        metadata={"axes": "ZYX"},
    )
    assert evaluation.main(argv(inputs)) == 1
    assert not (inputs[0] / "report").exists()


@pytest.mark.parametrize(
    "extra",
    [
        ("--num_classes", "3"),
        ("--threshold", "nan"),
        ("--max-voxels", "0"),
        ("--hist_dir", "old-hist-directory"),
        ("--metric", "critical_components_multiclass"),
        ("--ap-input", "binary", "--soft_pred"),
    ],
)
def test_invalid_settings_stop_before_volume_data_reads(inputs, monkeypatch, extra):
    monkeypatch.setattr(
        VolumeSource, "read", lambda *a: pytest.fail("materialized input")
    )
    assert evaluation.main(argv(inputs, *extra)) == 1
    assert not (inputs[0] / "report").exists()


def test_alignment_declaration_is_required_before_reading(inputs, monkeypatch):
    monkeypatch.setattr(VolumeSource, "inspect", lambda *a: pytest.fail("read input"))
    command = argv(inputs)
    command.remove("--aligned-inputs")
    assert evaluation.main(command) == 1


@pytest.mark.parametrize("target", ["gt.tif", "pred.tif", "existing", "alias"])
def test_existing_outputs_and_input_aliases_are_preserved(inputs, target):
    root, _ = inputs
    (root / "existing").mkdir()
    (root / "existing/prior.txt").write_text("keep")
    (root / "alias").symlink_to(root / "gt.tif")
    original = (root / "gt.tif").read_bytes()
    assert evaluation.main(argv(inputs, output=target)) == 1
    assert (root / "gt.tif").read_bytes() == original
    assert (root / "existing/prior.txt").read_text() == "keep"


def test_dry_run_does_not_import_metrics_probe_cuda_or_write(
    inputs, monkeypatch, capsys
):
    monkeypatch.setattr(
        evaluation, "load_villa_leaf", lambda *a, **kw: pytest.fail("imported metric")
    )
    monkeypatch.setattr(VolumeSource, "read", lambda *a: pytest.fail("decoded array"))
    assert evaluation.main(argv(inputs, "--dry-run", "--device", "cuda")) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PLANNED"
    assert not (inputs[0] / "report").exists()


@pytest.mark.parametrize("grouped", [False, True])
def test_zarr_crop_is_bounded_and_accepts_only_explicit_level_zero(
    inputs, monkeypatch, grouped
):
    root, _ = inputs
    for name in ("gt", "pred"):
        path = root / f"{name}.zarr"
        if grouped:
            zarr.open_group(str(path), mode="w").create_dataset(
                "0", data=np.ones((20, 20, 20), np.uint8), chunks=(4, 4, 4)
            )
        else:
            zarr.array(
                np.ones((20, 20, 20), np.uint8), store=str(path), chunks=(4, 4, 4)
            )
    getitem = zarr.Array.__getitem__

    def bounded(array, selection):
        result = getitem(array, selection)
        assert result.size <= 64
        return result

    monkeypatch.setattr(zarr.Array, "__getitem__", bounded)
    command = argv(inputs, "--max-voxels", "64", "--bbox", "2", "6", "3", "7", "4", "8")
    command[command.index("--gt") + 1] = str(root / "gt.zarr")
    command[command.index("--pred") + 1] = str(root / "pred.zarr")
    assert evaluation.main(command) == 0
    assert summary(inputs)["reference"]["bbox_zyx"] == [2, 6, 3, 7, 4, 8]


@pytest.mark.parametrize(
    "attrs,level",
    [
        ({"axes": ["c", "y", "x"]}, "root"),
        ({"_ARRAY_DIMENSIONS": ["c", "y", "x"]}, "array"),
        ({"axes": ["x", "y", "z"]}, "array"),
        (
            {
                "multiscales": [
                    {
                        "axes": [
                            {"name": "c", "type": "channel"},
                            {"name": "y", "type": "space"},
                            {"name": "x", "type": "space"},
                        ]
                    }
                ]
            },
            "root",
        ),
        (
            {"axes": [{"name": "z", "type": "channel"}, {"name": "y"}, {"name": "x"}]},
            "array",
        ),
    ],
)
def test_named_channel_or_reordered_zarr_axes_fail_before_value_reads(
    inputs, monkeypatch, attrs, level
):
    path = inputs[0] / "pred.zarr"
    group = zarr.open_group(str(path), mode="w")
    array = group.create_dataset("0", data=tifffile.imread(inputs[0] / "pred.tif"))
    (group if level == "root" else array).attrs.update(attrs)
    monkeypatch.setattr(
        VolumeSource,
        "read",
        lambda *a: pytest.fail("read channel data as spatial voxels"),
    )
    command = argv(inputs)
    command[command.index("--pred") + 1] = str(path)
    assert evaluation.main(command) == 1
    assert not (inputs[0] / "report").exists()


@pytest.mark.parametrize(
    "attrs,level",
    [
        ({"axes": "ZYX"}, "root"),
        ({"_ARRAY_DIMENSIONS": ["z", "y", "x"]}, "array"),
        (
            {
                "multiscales": [
                    {
                        "axes": [
                            {"name": "z", "type": "space"},
                            {"name": "y", "type": "space"},
                            {"name": "x", "type": "space"},
                        ]
                    }
                ]
            },
            "root",
        ),
    ],
)
def test_valid_named_spatial_zarr_axes_are_preserved_and_evaluated(
    inputs, attrs, level
):
    path = inputs[0] / "pred.zarr"
    group = zarr.open_group(str(path), mode="w")
    array = group.create_dataset("0", data=tifffile.imread(inputs[0] / "pred.tif"))
    (group if level == "root" else array).attrs.update(attrs)
    command = argv(inputs)
    command[command.index("--pred") + 1] = str(path)
    assert evaluation.main(command) == 0
    assert summary(inputs)["prediction"][f"{level}_attrs"] == attrs


def test_in_place_metric_mutation_cannot_change_other_metrics_or_counts(inputs):
    metric_file(inputs, "centerline_dice").write_text(
        "def compute(label, prediction, **kwargs):\n"
        "    label[:]=0\n    prediction[:]=0\n    return {'centerline_dice': 0.0}\n"
    )
    assert evaluation.main(argv(inputs)) == 0
    result = summary(inputs)
    assert result["reference_positive_voxels"] == 16
    assert result["prediction_positive_voxels"] == 16
    assert result["metrics"]["mean_ap"]["status"] == "OK"


def test_tiff_header_budget_is_checked_before_decompression(inputs, monkeypatch):
    monkeypatch.setattr(
        tifffile.TiffPageSeries, "asarray", lambda *a, **kw: pytest.fail("decompressed")
    )
    assert evaluation.main(argv(inputs, "--max-voxels", "119")) == 1


@pytest.mark.parametrize("kind", ["rgb", "2d", "multiseries"])
def test_ambiguous_or_nonvolumetric_tiffs_are_refused(inputs, kind):
    path = inputs[0] / "pred.tif"
    if kind == "rgb":
        tifffile.imwrite(path, np.zeros((4, 5, 3), np.uint8), photometric="rgb")
    elif kind == "2d":
        tifffile.imwrite(path, np.zeros((5, 6), np.uint8))
    else:
        with tifffile.TiffWriter(path) as writer:
            writer.write(np.zeros((4, 5, 6), np.uint8), photometric="minisblack")
            writer.write(np.zeros((3, 5, 6), np.uint8), photometric="minisblack")
    assert evaluation.main(argv(inputs)) == 1


def test_a_missing_required_metric_stops_before_reading_the_volumes(
    inputs, monkeypatch, capsys
):
    metric_file(inputs, "dice").write_text(
        "raise ImportError('fixture dependency missing')\n"
    )
    monkeypatch.setattr(VolumeSource, "read", lambda *a: pytest.fail("read values"))
    assert evaluation.main(argv(inputs)) == 1
    assert "Required Villa metric dice unavailable" in capsys.readouterr().err
    assert not (inputs[0] / "report").exists()


def test_a_missing_optional_metric_leaves_others_with_explicit_partial_status(inputs):
    metric_file(inputs, "mean_ap").write_text(
        "raise ImportError('fixture dependency missing')\n"
    )
    assert evaluation.main(argv(inputs)) == 2
    result = summary(inputs)
    assert result["metrics"]["dice"]["status"] == "OK"
    assert result["metrics"]["mean_ap"]["status"] == "UNAVAILABLE"


def test_upstream_ap_error_log_cannot_be_mistaken_for_a_measured_zero(inputs):
    metric_file(inputs, "mean_ap").write_text(
        "def compute(*args, **kwargs):\n"
        "    print('Error computing AP for class 1: backend failed')\n"
        "    return {'mean_ap': 0.0}\n"
    )
    assert evaluation.main(argv(inputs)) == 2
    record = summary(inputs)["metrics"]["mean_ap"]
    assert record["status"] == "FAILED" and record["values"] is None
    assert "backend failed" in record["log"]


@pytest.mark.parametrize(
    "body,status",
    [
        ("return float('nan')", "UNDEFINED"),
        ("return {}", "UNDEFINED"),
        ("raise RuntimeError('compute failed')", "FAILED"),
        ("raise ValueError('bad computation')", "FAILED"),
    ],
)
def test_failed_or_undefined_metrics_are_not_silently_omitted(inputs, body, status):
    metric_file(inputs, "mean_ap").write_text(
        f"def compute(*args, **kwargs):\n    {body}\n"
    )
    assert evaluation.main(argv(inputs)) == 2
    result = summary(inputs)
    assert result["metrics"]["mean_ap"]["status"] == status
    assert result["metrics"]["mean_ap"]["values"] is None
    json.dumps(result, allow_nan=False)


def test_skeleton_histogram_and_tracking_are_confined_to_the_bundle(inputs):
    assert (
        evaluation.main(
            argv(inputs, "--metric", "dice", "--metric", "skeleton_distance_length")
        )
        == 0
    )
    result = summary(inputs)
    assert result["metrics"]["skeleton_distance_length"]["values"] == 0
    assert (inputs[0] / "report/artifacts/skeleton/histogram.png").exists()


def test_slices_predicted_without_ground_truth_are_counted_and_warned(inputs):
    path = inputs[0] / "gt.tif"
    values = tifffile.imread(path)
    values[2] = 0
    tifffile.imwrite(path, values, photometric="minisblack", metadata={"axes": "ZYX"})
    assert evaluation.main(argv(inputs)) == 2
    result = summary(inputs)
    assert result["centerline_slices_predicted_without_ground_truth"] == 1
    assert result["metrics"]["centerline_dice"]["status"] == "WARNING"


def test_centerline_above_one_is_preserved_and_warned_without_empty_slices(inputs):
    metric_file(inputs, "centerline_dice").write_text(
        "def compute(*args, **kwargs):\n    return {'centerline_dice': 1.25}\n"
    )
    assert evaluation.main(argv(inputs)) == 2
    result = summary(inputs)
    assert result["centerline_slices_predicted_without_ground_truth"] == 0
    assert result["metrics"]["centerline_dice"]["values"]["centerline_dice"] == 1.25
    assert result["metrics"]["centerline_dice"]["status"] == "WARNING"


def test_probability_ap_and_uint8_encoding_are_explicit(inputs):
    path = inputs[0] / "pred.tif"
    labels = tifffile.imread(inputs[0] / "gt.tif")
    values = np.where(labels, 160, 25).astype(np.uint8)
    tifffile.imwrite(path, values, photometric="minisblack", metadata={"axes": "ZYX"})
    assert evaluation.main(argv(inputs, output="invalid")) == 1
    assert evaluation.main(argv(inputs, "--prediction-encoding", "uint8")) == 0
    assert summary(inputs)["metrics"]["mean_ap"]["values"]["mean_ap"] == pytest.approx(
        160 / 255
    )
    assert (
        evaluation.main(
            argv(
                inputs,
                "--prediction-encoding",
                "uint8",
                "--ap-input",
                "binary",
                output="hard-ap",
            )
        )
        == 0
    )
    assert summary(inputs, "hard-ap")["metrics"]["mean_ap"]["values"]["mean_ap"] == 1


@pytest.mark.parametrize("changed", ["reference", "metric", "summary_write"])
def test_changed_inputs_or_sources_prevent_completed_publication(
    inputs, monkeypatch, changed
):
    if changed == "summary_write":
        write = evaluation.write_json

        def mutate_write(path, report):
            write(path, report)
            with (inputs[0] / "gt.tif").open("ab") as stream:
                stream.write(b"changed")

        monkeypatch.setattr(evaluation, "write_json", mutate_write)
    else:
        call = evaluation._call_metric

        def mutate_metric(*args, **kwargs):
            result = call(*args, **kwargs)
            path = (
                inputs[0] / "gt.tif"
                if changed == "reference"
                else metric_file(inputs, "dice")
            )
            with path.open("ab") as stream:
                stream.write(b" ")
            return result

        monkeypatch.setattr(evaluation, "_call_metric", mutate_metric)
    assert evaluation.main(argv(inputs)) == 1
    assert not (inputs[0] / "report").exists()
    assert not list(inputs[0].glob(".report-*"))


def test_repeated_calls_do_not_reuse_stale_sources_or_module_globals(inputs):
    assert evaluation.main(argv(inputs, "--metric", "dice", output="first")) == 0
    metric_file(inputs, "dice").write_text(
        "def compute(*args, **kwargs):\n    return 0.25\n"
    )
    assert evaluation.main(argv(inputs, "--metric", "dice", output="second")) == 0
    assert summary(inputs, "second")["metrics"]["dice"]["values"] == 0.25
    assert (
        summary(inputs, "first")["metric_sources"]["dice"]["sha256"]
        != summary(inputs, "second")["metric_sources"]["dice"]["sha256"]
    )


def test_cli_help_and_source_resolution_ignore_ambient_metrics(inputs, tmp_path):
    shadow = tmp_path / "shadow/metrics"
    shadow.mkdir(parents=True)
    (shadow / "__init__.py").write_text(
        "raise RuntimeError('ambient metrics must not load')\n"
    )
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="", PYTHONPATH=str(shadow.parent))
    command = [sys.executable, str(Path(evaluation.__file__).resolve())]
    result = subprocess.run(
        command + argv(inputs),
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    env.pop("PYTHONPATH")
    help_result = subprocess.run(
        command + ["--help"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert help_result.returncode == 0 and "--dry-run" in help_result.stdout


@pytest.mark.parametrize("threshold,expected", [(0.5, 1.0), (0.8, 0.0)])
def test_real_pinned_cpu_metrics_use_the_same_threshold(tmp_path, threshold, expected):
    configured = os.environ.get("VESUVIUS_EVAL_METRICS_ROOT")
    if not configured:
        pytest.skip(
            "set VESUVIUS_EVAL_METRICS_ROOT for exact pinned-source integration"
        )
    root = Path(configured)
    manifest = json.loads((root / "source-manifest.json").read_text())
    assert manifest["villa_commit"] == "ccb431818fa68059138f2c964ae299fc474ff116"
    for name, record in manifest["files"].items():
        data = (root / name).read_bytes()
        assert (
            hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            == record["git_blob_sha1"]
        )
    gt = np.zeros((3, 8, 8), np.uint8)
    gt[:, 2:6, 4] = 1
    pred = np.where(gt, 0.6, 0.1)
    for name, values in (("gt", gt), ("pred", pred)):
        tifffile.imwrite(
            tmp_path / f"{name}.tif",
            values,
            photometric="minisblack",
            metadata={"axes": "ZYX"},
        )
    command = [
        sys.executable,
        str(Path(evaluation.__file__).resolve()),
        "--gt",
        str(tmp_path / "gt.tif"),
        "--pred",
        str(tmp_path / "pred.tif"),
        "--villa-root",
        str(root),
        "--out",
        str(tmp_path / "report"),
        "--aligned-inputs",
        "--threshold",
        str(threshold),
    ]
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="")
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        command, cwd=tmp_path, env=env, text=True, capture_output=True, timeout=90
    )
    assert result.returncode == 0, result.stderr
    report = json.loads((tmp_path / "report/summary.json").read_text())
    assert report["metrics"]["dice"]["values"] == pytest.approx(expected)
    assert report["metrics"]["centerline_dice"]["values"][
        "centerline_dice"
    ] == pytest.approx(expected)
    assert (
        report["metrics"]["connected_components"]["values"][
            "connected_components_difference_total"
        ]
        == 1 - expected
    )
    assert report["metrics"]["mean_ap"]["values"]["mean_ap"] == 1.0


def test_cuda_request_has_no_silent_cpu_fallback(inputs, monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False)),
    )
    monkeypatch.setattr(VolumeSource, "read", lambda *a: pytest.fail("decoded inputs"))
    assert evaluation.main(argv(inputs, "--device", "cuda")) == 1
    assert not (inputs[0] / "report").exists()


def test_missing_positive_reference_leaves_ap_undefined(inputs):
    tifffile.imwrite(
        inputs[0] / "gt.tif",
        np.zeros((4, 5, 6), np.uint8),
        photometric="minisblack",
        metadata={"axes": "ZYX"},
    )
    assert evaluation.main(argv(inputs, "--metric", "mean_ap")) == 2
    result = summary(inputs)["metrics"]["mean_ap"]
    assert result["status"] == "UNDEFINED" and result["values"] is None


def test_corrupt_skeleton_histogram_is_not_published_as_a_valid_artifact(inputs):
    metric_file(inputs, "skeleton_distance_length").write_text(
        "from pathlib import Path\ndef compute(*args, output_folder, **kwargs):\n"
        "    folder=Path(output_folder)\n    folder.mkdir(parents=True)\n"
        "    (folder/'corrupt.png').write_bytes(b'partial')\n    return 0.0\n"
    )
    assert (
        evaluation.main(
            argv(inputs, "--metric", "dice", "--metric", "skeleton_distance_length")
        )
        == 2
    )
    assert summary(inputs)["metrics"]["skeleton_distance_length"]["status"] == "FAILED"
    assert not (inputs[0] / "report/artifacts/skeleton").exists()


def test_artifact_changes_during_summary_write_abort_publication(inputs, monkeypatch):
    write = evaluation.write_json

    def corrupt(path, report):
        write(path, report)
        (Path(path).parent / "artifacts/skeleton/histogram.png").write_bytes(b"changed")

    monkeypatch.setattr(evaluation, "write_json", corrupt)
    assert (
        evaluation.main(
            argv(inputs, "--metric", "dice", "--metric", "skeleton_distance_length")
        )
        == 1
    )
    assert not (inputs[0] / "report").exists()


@pytest.mark.parametrize("changed", ["values", "attributes"])
def test_zarr_changes_during_evaluation_abort_publication(inputs, monkeypatch, changed):
    path = inputs[0] / "pred.zarr"
    zarr.array(
        tifffile.imread(inputs[0] / "pred.tif"), store=str(path), chunks=(2, 5, 6)
    )
    call = evaluation._call_metric

    def mutate(*args, **kwargs):
        result = call(*args, **kwargs)
        array = zarr.open(str(path), mode="r+")
        if changed == "values":
            array[0, 0, 0] += 0.01
        else:
            array.attrs["frame"] = "changed"
        return result

    monkeypatch.setattr(evaluation, "_call_metric", mutate)
    command = argv(inputs)
    command[command.index("--pred") + 1] = str(path)
    assert evaluation.main(command) == 1
    assert not (inputs[0] / "report").exists()


def test_failed_markdown_cannot_publish_half_of_a_report(inputs, monkeypatch):
    def fail(report, path):
        path.write_text("partial")
        raise OSError("render failed")

    monkeypatch.setattr(evaluation, "_render_markdown", fail)
    assert evaluation.main(argv(inputs)) == 1
    assert not (inputs[0] / "report").exists()


def test_dry_run_can_inspect_before_alignment_is_declared(inputs, capsys):
    command = argv(inputs, "--dry-run")
    command.remove("--aligned-inputs")
    assert evaluation.main(command) == 0
    assert (
        "not declared"
        in json.loads(capsys.readouterr().out)["settings"]["alignment_basis"]
    )
    assert not (inputs[0] / "report").exists()


def test_skeleton_adapter_caps_only_its_local_backend_reference(inputs):
    metric_file(inputs, "skeleton_distance_length").write_text(
        "from types import SimpleNamespace\nfrom pathlib import Path\nfrom PIL import Image\n"
        "kimimaro=SimpleNamespace(skeletonize=lambda *args, **kwargs: kwargs['parallel'])\n"
        "def compute(label, prediction, output_folder):\n"
        "    folder=Path(output_folder)\n    folder.mkdir(parents=True)\n"
        "    Image.new('RGB',(8,8)).save(folder/'histogram.png')\n"
        "    return float(kimimaro.skeletonize(label, parallel=0))\n"
    )
    assert evaluation.main(argv(inputs, "--metric", "skeleton_distance_length")) == 0
    assert summary(inputs)["metrics"]["skeleton_distance_length"]["values"] == 1
    assert summary(inputs)["settings"]["skeleton_parallel"] == 1


def test_real_pinned_skeleton_metric_writes_verified_histogram_without_tracking(
    tmp_path,
):
    configured = os.environ.get("VESUVIUS_EVAL_METRICS_ROOT")
    if not configured:
        pytest.skip(
            "set VESUVIUS_EVAL_METRICS_ROOT for exact pinned-source integration"
        )
    pytest.importorskip("kimimaro")
    gt = np.zeros((20, 20, 20), np.uint8)
    gt[10, 2:18, 10] = 1
    for name in ("gt", "pred"):
        tifffile.imwrite(
            tmp_path / f"{name}.tif",
            gt,
            photometric="minisblack",
            metadata={"axes": "ZYX"},
        )
    command = [
        sys.executable,
        str(Path(evaluation.__file__).resolve()),
        "--gt",
        str(tmp_path / "gt.tif"),
        "--pred",
        str(tmp_path / "pred.tif"),
        "--villa-root",
        configured,
        "--out",
        str(tmp_path / "report"),
        "--aligned-inputs",
        "--metric",
        "dice",
        "--metric",
        "skeleton_distance_length",
    ]
    env = dict(
        os.environ, CUDA_VISIBLE_DEVICES="", MPLCONFIGDIR=str(tmp_path / "mpl-cache")
    )
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        command, cwd=tmp_path, env=env, text=True, capture_output=True, timeout=90
    )
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((tmp_path / "report/summary.json").read_text())
    skeleton = report["metrics"]["skeleton_distance_length"]
    assert skeleton["values"] == 0.0
    assert len(skeleton["artifacts"]) == 1
    for relative, record in skeleton["artifacts"].items():
        data = (tmp_path / "report" / relative).read_bytes()
        assert hashlib.sha256(data).hexdigest() == record["sha256"]
