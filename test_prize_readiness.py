import json
from pathlib import Path

import numpy as np

from scripts.build_scroll23_search_queue import build_queue
from scripts.validate_prize_artifact import validate


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)


def test_validate_prize_artifact_passes_with_masks_and_vc3d_metadata(tmp_path):
    train_mask = np.zeros((8, 8), dtype=bool)
    predict_mask = np.zeros((8, 8), dtype=bool)
    train_mask[:2, :2] = True
    predict_mask[-2:, -2:] = True
    train_mask_path = tmp_path / "train_mask.npy"
    predict_mask_path = tmp_path / "predict_mask.npy"
    np.save(train_mask_path, train_mask)
    np.save(predict_mask_path, predict_mask)

    zarr_path = tmp_path / "prediction.zarr"
    _write_json(
        zarr_path / "meta.json",
        {
            "format": "zarr",
            "voxelsize": 7.91,
            "height": 64,
            "width": 64,
            "slices": 1,
        },
    )
    _write_json(zarr_path / "0" / ".zarray", {"shape": [1, 64, 64], "chunks": [1, 64, 64]})

    metadata_path = tmp_path / "metadata.json"
    _write_json(
        metadata_path,
        {
            "scroll_id": "Scroll 2",
            "source_uri": "local_data/PHerc0125_Divisions/div_100/0",
            "position_xyz": [2048, 2048, 9000],
            "patch_size": 64,
            "width_px": 64,
            "height_px": 64,
            "voxel_size_um": 7.91,
            "scale_bar_cm": True,
            "train_mask_path": str(train_mask_path),
            "predict_mask_path": str(predict_mask_path),
            "vc3d_zarr_path": str(zarr_path),
        },
    )

    report = validate(metadata_path)

    assert report["status"] == "PASS"
    assert report["failures"] == []


def test_validate_prize_artifact_fails_on_train_predict_overlap(tmp_path):
    train_mask = np.zeros((8, 8), dtype=bool)
    predict_mask = np.zeros((8, 8), dtype=bool)
    train_mask[:4, :4] = True
    predict_mask[2:6, 2:6] = True
    train_mask_path = tmp_path / "train_mask.npy"
    predict_mask_path = tmp_path / "predict_mask.npy"
    np.save(train_mask_path, train_mask)
    np.save(predict_mask_path, predict_mask)

    metadata_path = tmp_path / "metadata.json"
    _write_json(
        metadata_path,
        {
            "scroll_id": "Scroll 3",
            "source_uri": "local_data/PHerc0332_Divisions/div_100/0",
            "position_xyz": [2048, 2048, 9000],
            "patch_size": 64,
            "width_px": 64,
            "height_px": 64,
            "voxel_size_um": 7.91,
            "scale_bar_cm": True,
            "train_mask_path": str(train_mask_path),
            "predict_mask_path": str(predict_mask_path),
        },
    )

    report = validate(metadata_path)

    assert report["status"] == "FAIL"
    assert any("overlap" in failure for failure in report["failures"])


def test_build_scroll23_search_queue_marks_64px_windows_submittable():
    rows = build_queue(divisions=[1.0], windows_per_division=1, patch_size=64, voxel_um=7.91)

    assert len(rows) == 2
    assert {row["short_id"] for row in rows} == {"PHerc0125", "PHerc0332"}
    assert all(row["submittable_window"] == "true" for row in rows)
    assert all(row["division"] == "div_100" for row in rows)
