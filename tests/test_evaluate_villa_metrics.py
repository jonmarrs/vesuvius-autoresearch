import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import zarr

REPO = Path(__file__).resolve().parents[1]


def _line_volume(path):
    volume = zarr.open(
        str(path), mode="w", shape=(20, 20, 20), chunks=(10, 10, 10), dtype="u1"
    )
    line = np.zeros((20, 20, 20), np.uint8)
    line[10, 2:18, 10] = 1
    volume[:] = line
    return str(path)


def test_skeleton_distance_is_reported_without_a_wandb_run(tmp_path):
    # villa's skeleton metric calls wandb.log, which raises when no run is
    # active; the script caught that and silently dropped skeleton_distance.
    # A subprocess keeps train.py's process-wide wandb.log patch (applied by
    # any test that imports train) from hiding the bug.
    # Run from outside the checkout: villa is found from the script's own.
    out = tmp_path / "results.json"
    env = {k: v for k, v in os.environ.items() if k != "WANDB_MODE"}
    subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/evaluate_villa_metrics.py"),
            "--gt",
            _line_volume(tmp_path / "gt.zarr"),
            "--pred",
            _line_volume(tmp_path / "pred.zarr"),
            "--out",
            str(out),
        ],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        timeout=300,
    )

    assert json.loads(out.read_text())["skeleton_distance"] == 0.0


def _shadow_metrics(tmp_path, broken):
    """A `metrics` package ahead of villa's: each metric returns one value, and
    those in broken fail to import."""
    shadow = tmp_path / "shadow" / "metrics"
    shadow.mkdir(parents=True)
    (shadow / "__init__.py").write_text("")
    for name in (
        "centerline_dice",
        "connected_components",
        "dice",
        "critical_components_multiclass",
        "dice_multiclass",
        "mean_ap",
        "skeleton_distance_length",
    ):
        body = (
            f"raise ImportError('no {name} here')\n"
            if name in broken
            else f"def compute(*args, **kwargs):\n    return {{'{name}': 1.0}}\n"
        )
        (shadow / f"{name}.py").write_text(body)
    return dict(os.environ, PYTHONPATH=str(shadow.parent))


def _evaluate(tmp_path, env):
    return subprocess.run(
        [sys.executable, str(REPO / "scripts/evaluate_villa_metrics.py")]
        + ["--gt", _line_volume(tmp_path / "gt.zarr")]
        + ["--pred", _line_volume(tmp_path / "pred.zarr")]
        + ["--out", str(tmp_path / "results.json")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )


def test_a_missing_required_metric_stops_before_reading_the_volumes(tmp_path):
    """It printed the import error and went on: both volumes were read, and the
    first metric failed with a NameError."""
    result = _evaluate(tmp_path, _shadow_metrics(tmp_path, {"dice"}))
    assert result.returncode != 0
    assert "Error importing Villa metrics: no dice here" in result.stderr
    assert "Loading Ground Truth" not in result.stdout
    assert "NameError" not in result.stderr


def test_a_missing_optional_metric_leaves_the_others_reported(tmp_path):
    """critical_components_multiclass needs cupy: without it, one import block
    lost every metric, though main() treats that one as optional."""
    result = _evaluate(
        tmp_path, _shadow_metrics(tmp_path, {"critical_components_multiclass"})
    )
    assert result.returncode == 0, result.stderr
    assert "critical_components_multiclass unavailable" in result.stdout
    results = json.loads((tmp_path / "results.json").read_text())
    assert {"dice", "centerline_dice", "connected_components", "mean_ap"} <= set(
        results
    )
    assert "critical_components_multiclass" not in results


def test_slices_predicted_without_ground_truth_are_counted(tmp_path):
    """Villa gives such a slice the whole slice as its tolerance region, so its
    predicted skeleton counts as matching: the count shows whether the
    centerline_dice is inflated."""
    gt = _line_volume(tmp_path / "gt.zarr")  # ink at [10, 2:18, 10] only
    pred = zarr.open(
        str(tmp_path / "pred.zarr"),
        mode="w",
        shape=(20, 20, 20),
        chunks=(10, 10, 10),
        dtype="f4",
    )
    volume = np.zeros((20, 20, 20), np.float32)
    volume[10, 2:18, 10] = 1
    # Predicted on slices with no ground truth, in its column, so only slices
    # along the first axis, villa's, count them.
    volume[3, 2:18, 10] = 1
    volume[15, 5:9, 10] = 1
    volume[7, 2:18, 10] = 0.3  # below the threshold, so not predicted
    pred[:] = volume
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts/evaluate_villa_metrics.py")]
        + ["--gt", gt, "--pred", str(tmp_path / "pred.zarr")]
        + ["--out", str(tmp_path / "results.json")],
        cwd=tmp_path,
        env=_shadow_metrics(tmp_path, set()),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr
    results = json.loads((tmp_path / "results.json").read_text())
    assert results["centerline_slices_predicted_without_ground_truth"] == 2
    assert "2 slices have a prediction and no ground truth" in result.stdout
