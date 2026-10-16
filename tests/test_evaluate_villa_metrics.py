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
    out = tmp_path / "results.json"
    env = {k: v for k, v in os.environ.items() if k != "WANDB_MODE"}
    subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_villa_metrics.py",
            "--gt",
            _line_volume(tmp_path / "gt.zarr"),
            "--pred",
            _line_volume(tmp_path / "pred.zarr"),
            "--out",
            str(out),
        ],
        cwd=REPO,
        env=env,
        check=True,
        capture_output=True,
        timeout=300,
    )

    assert json.loads(out.read_text())["skeleton_distance"] == 0.0


def test_a_missing_villa_metric_stops_before_reading_the_volumes(tmp_path):
    """It printed the import error and went on: both volumes were read, and the
    first metric failed with a NameError."""
    shadow = tmp_path / "shadow" / "metrics"
    shadow.mkdir(parents=True)
    (shadow / "__init__.py").write_text("raise ImportError('no cupy here')\n")
    env = dict(os.environ, PYTHONPATH=str(shadow.parent))
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts/evaluate_villa_metrics.py")]
        + ["--gt", "missing_gt.zarr", "--pred", "missing_pred.zarr"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "Error importing Villa metrics: no cupy here" in result.stderr
    assert "Loading Ground Truth" not in result.stdout
    assert "NameError" not in result.stderr
