import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "training"))

import train  # noqa: E402


def _line():
    volume = np.zeros((20, 20, 20), dtype=bool)
    volume[10, 2:18, 10] = True
    return volume


def test_validation_skeleton_histograms_stay_out_of_cwd(tmp_path, monkeypatch):
    # villa's skeleton_distance_length.compute saves a histogram PNG on every
    # call to its output_folder, which defaults to "."; validation calls it on
    # every 10th sample, so training runs filled the repo root with them.
    if not train.SKELETON_DISTANCE_AVAILABLE:
        pytest.skip(train.SKELETON_DISTANCE_IMPORT_ERROR)
    monkeypatch.setattr("metrics.skeleton_distance_length.wandb", None)
    hists = tmp_path / "hists"
    monkeypatch.setattr(train, "SKELETON_HIST_DIR", str(hists), raising=False)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    train.compute_skeleton_dist(_line(), _line())

    assert list(cwd.iterdir()) == []
    assert len(list(hists.glob("skeleton_branch_length_hist_sample_*.png"))) == 1
