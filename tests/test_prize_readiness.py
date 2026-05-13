import json
from pathlib import Path

import numpy as np

from scripts.build_scroll23_search_queue import build_queue, _occupied_windows
from scripts.rank_scroll23_candidates import rank_candidates, score_row
from scripts.run_ranked_inference import build_predict_command, load_candidates
from scripts.run_villa_prize_evidence_chain import build_evidence_chain, preflight_evidence_chain
from scripts.validate_prize_artifact import validate


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)


def _write_vc3d_zarr(path: Path, scale=7.91):
    _write_json(
        path / "meta.json",
        {
            "format": "zarr",
            "voxelsize": 7.91,
            "height": 64,
            "width": 64,
            "slices": 1,
        },
    )
    _write_json(path / "0" / ".zarray", {"shape": [1, 64, 64], "chunks": [1, 64, 64]})
    _write_json(
        path / ".zattrs",
        {
            "multiscales": [
                {
                    "axes": [
                        {"name": "z", "type": "space", "unit": "micrometer"},
                        {"name": "y", "type": "space", "unit": "micrometer"},
                        {"name": "x", "type": "space", "unit": "micrometer"},
                    ],
                    "datasets": [
                        {
                            "path": "0",
                            "coordinateTransformations": [{"type": "scale", "scale": [scale, scale, scale]}],
                        }
                    ],
                }
            ]
        },
    )


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
    _write_vc3d_zarr(zarr_path)

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


def test_validate_prize_artifact_checks_paired_ink_and_fiber_vc3d_metadata(tmp_path):
    train_mask = np.zeros((8, 8), dtype=bool)
    predict_mask = np.zeros((8, 8), dtype=bool)
    train_mask[:2, :2] = True
    predict_mask[-2:, -2:] = True
    train_mask_path = tmp_path / "train_mask.npy"
    predict_mask_path = tmp_path / "predict_mask.npy"
    np.save(train_mask_path, train_mask)
    np.save(predict_mask_path, predict_mask)

    ink_zarr_path = tmp_path / "ink.zarr"
    fiber_zarr_path = tmp_path / "fiber.zarr"
    _write_vc3d_zarr(ink_zarr_path)
    _write_vc3d_zarr(fiber_zarr_path)

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
            "vc3d_zarr_path": str(ink_zarr_path),
            "fiber_vc3d_zarr_path": str(fiber_zarr_path),
        },
    )

    report = validate(metadata_path)

    assert report["status"] == "PASS"
    assert report["checked_zarr_paths"] == [str(ink_zarr_path), str(fiber_zarr_path)]


def test_validate_prize_artifact_passes_on_known_good_local_fixture():
    metadata_path = Path("predictions/pred_10_1000_1000_64x64_meta.json")
    if not metadata_path.exists():
        import pytest
        pytest.skip("Known-good fixture not available")

    report = validate(metadata_path)
    assert report["status"] == "PASS"
    assert report["failures"] == []
    assert "reports/pred_10_1000_1000_64x64_ink.zarr" in report["checked_zarr_paths"]
    assert "reports/pred_10_1000_1000_64x64_fiber.zarr" in report["checked_zarr_paths"]

def test_validate_prize_artifact_fails_on_mismatched_fiber_ome_zarr_scale(tmp_path):
    train_mask = np.zeros((8, 8), dtype=bool)
    predict_mask = np.zeros((8, 8), dtype=bool)
    train_mask[:2, :2] = True
    predict_mask[-2:, -2:] = True
    train_mask_path = tmp_path / "train_mask.npy"
    predict_mask_path = tmp_path / "predict_mask.npy"
    np.save(train_mask_path, train_mask)
    np.save(predict_mask_path, predict_mask)

    ink_zarr_path = tmp_path / "ink.zarr"
    fiber_zarr_path = tmp_path / "fiber.zarr"
    _write_vc3d_zarr(ink_zarr_path)
    _write_vc3d_zarr(fiber_zarr_path, scale=1.0)

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
            "vc3d_zarr_path": str(ink_zarr_path),
            "fiber_vc3d_zarr_path": str(fiber_zarr_path),
        },
    )

    report = validate(metadata_path)

    assert report["status"] == "FAIL"
    assert any("spatial scale" in failure for failure in report["failures"])


def test_validate_prize_artifact_fails_on_mismatched_ome_zarr_scale(tmp_path):
    train_mask = np.zeros((8, 8), dtype=bool)
    predict_mask = np.zeros((8, 8), dtype=bool)
    train_mask[:2, :2] = True
    predict_mask[-2:, -2:] = True
    train_mask_path = tmp_path / "train_mask.npy"
    predict_mask_path = tmp_path / "predict_mask.npy"
    np.save(train_mask_path, train_mask)
    np.save(predict_mask_path, predict_mask)

    zarr_path = tmp_path / "prediction.zarr"
    _write_vc3d_zarr(zarr_path, scale=1.0)
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

    assert report["status"] == "FAIL"
    assert any("spatial scale" in failure for failure in report["failures"])


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


def test_validate_prize_artifact_fails_on_placeholder_evidence(tmp_path):
    train_mask = np.zeros((8, 8), dtype=bool)
    predict_mask = np.zeros((8, 8), dtype=bool)
    train_mask[:2, :2] = True
    predict_mask[-2:, -2:] = True
    train_mask_path = tmp_path / "train_mask.npy"
    predict_mask_path = tmp_path / "predict_mask.npy"
    np.save(train_mask_path, train_mask)
    np.save(predict_mask_path, predict_mask)

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
            "source_image_is_placeholder": True,
            "evidence_mode": "placeholder_dry_run",
        },
    )

    report = validate(metadata_path)

    assert report["status"] == "FAIL"
    assert any("placeholder" in failure for failure in report["failures"])


def test_validate_prize_artifact_fails_on_dry_run_metadata(tmp_path):
    train_mask = np.zeros((8, 8), dtype=bool)
    predict_mask = np.zeros((8, 8), dtype=bool)
    train_mask[:2, :2] = True
    predict_mask[-2:, -2:] = True
    train_mask_path = tmp_path / "train_mask.npy"
    predict_mask_path = tmp_path / "predict_mask.npy"
    np.save(train_mask_path, train_mask)
    np.save(predict_mask_path, predict_mask)

    metadata_path = tmp_path / "metadata.json"
    _write_json(
        metadata_path,
        {
            "scroll_id": "Scroll 1 (Dry Run)",
            "segmentation_id": "20230509172439",
            "position_xyz": [1000, 2000, 3000],
            "patch_size": 64,
            "width_px": 64,
            "height_px": 64,
            "voxel_size_um": 8,
            "scale_bar_cm": True,
            "train_mask_path": str(train_mask_path),
            "predict_mask_path": str(predict_mask_path),
            "metadata_is_dry_run": True,
        },
    )

    report = validate(metadata_path)

    assert report["status"] == "FAIL"
    assert any("dry-run" in failure for failure in report["failures"])


def test_build_scroll23_search_queue_marks_64px_windows_submittable():
    rows = build_queue(divisions=[1.0], windows_per_division=1, patch_size=64, voxel_um=7.91)

    assert len(rows) == 2
    assert {row["short_id"] for row in rows} == {"PHerc0125", "PHerc0332"}
    assert all(row["submittable_window"] == "true" for row in rows)
    assert all(row["division"] == "div_100" for row in rows)


def test_occupied_windows_uses_local_zarr_chunks(tmp_path):
    zarr_path = tmp_path / "vol.zarr"
    _write_json(
        zarr_path / ".zarray",
        {
            "shape": [512, 512, 512],
            "chunks": [128, 128, 128],
            "dtype": "|u1",
            "fill_value": 0,
            "order": "C",
            "filters": None,
            "dimension_separator": "/",
            "compressor": None,
            "zarr_format": 2,
        },
    )
    chunk_path = zarr_path / "2" / "3" / "1"
    chunk_path.parent.mkdir(parents=True)
    chunk_path.write_bytes(b"chunk")

    windows = _occupied_windows(str(zarr_path), windows_per_division=1, patch_size=64)

    assert windows == [(256, 416, 160)]


def test_rank_scroll23_candidates_prefers_high_confidence_prediction(tmp_path):
    prediction_dir = tmp_path / "predictions"
    prediction_dir.mkdir()
    row = {
        "priority": "1.0",
        "scroll_id": "Scroll 2",
        "short_id": "PHerc0125",
        "division": "div_100",
        "z": "9000",
        "y": "2048",
        "x": "2048",
        "width": "64",
        "height": "64",
        "patch_size": "64",
        "submittable_window": "true",
        "local_uri": "local_data/PHerc0125_Divisions/div_100/0",
    }
    arr = np.zeros((64, 64), dtype=np.float32)
    arr[20:24, 20:24] = 0.95
    np.save(prediction_dir / "pred_9000_2048_2048_64x64_ink.npy", arr)

    scored = score_row(row, prediction_dir=prediction_dir)

    assert scored["prediction_found"] == "true"
    assert float(scored["ink_max"]) == 0.95
    assert float(scored["review_score"]) > 1.0


def test_rank_scroll23_candidates_reports_corrupt_metadata(tmp_path):
    prediction_dir = tmp_path / "predictions"
    prediction_dir.mkdir()
    row = {
        "priority": "1.0",
        "scroll_id": "Scroll 2",
        "short_id": "PHerc0125",
        "division": "div_100",
        "z": "9000",
        "y": "2048",
        "x": "2048",
        "width": "64",
        "height": "64",
        "patch_size": "64",
        "submittable_window": "true",
        "local_uri": "",
    }
    (prediction_dir / "pred_9000_2048_2048_64x64_meta.json").write_text("{bad json")

    scored = score_row(row, prediction_dir=prediction_dir)

    assert scored["metadata_found"] == "true"
    assert "JSONDecodeError" in scored["metadata_error"]


def test_rank_candidates_writes_ranked_tsv(tmp_path):
    queue_path = tmp_path / "queue.tsv"
    out_path = tmp_path / "ranked.tsv"
    rows = build_queue(divisions=[1.0], windows_per_division=1, patch_size=64, voxel_um=7.91)
    with open(queue_path, "w") as f:
        f.write("\t".join(rows[0].keys()) + "\n")
        for row in rows:
            f.write("\t".join(str(row[key]) for key in rows[0].keys()) + "\n")

    ranked = rank_candidates(queue_path, out_path, prediction_dir=tmp_path / "predictions")

    assert out_path.exists()
    assert len(ranked) == 2
    assert float(ranked[0]["review_score"]) >= float(ranked[1]["review_score"])


def test_rank_scroll23_candidates_penalizes_empty_local_zarr_window(tmp_path):
    zarr_path = tmp_path / "vol.zarr"
    _write_json(
        zarr_path / ".zarray",
        {
            "shape": [512, 512, 512],
            "chunks": [128, 128, 128],
            "dtype": "|u1",
            "fill_value": 0,
            "order": "C",
            "filters": None,
            "dimension_separator": "/",
            "compressor": None,
            "zarr_format": 2,
        },
    )
    (zarr_path / "2" / "3").mkdir(parents=True)
    (zarr_path / "2" / "3" / "1").write_bytes(b"chunk")
    occupied = {
        "priority": "1.0",
        "scroll_id": "Scroll 2",
        "short_id": "PHerc0125",
        "division": "div_100",
        "z": "256",
        "y": "416",
        "x": "160",
        "width": "64",
        "height": "64",
        "patch_size": "64",
        "submittable_window": "true",
        "local_uri": str(zarr_path),
    }
    empty = dict(occupied, z="128", y="160", x="160")

    occupied_scored = score_row(occupied, prediction_dir=tmp_path / "predictions")
    empty_scored = score_row(empty, prediction_dir=tmp_path / "predictions")

    assert occupied_scored["ct_occupied_status"] == "true"
    assert empty_scored["ct_occupied_status"] == "false"
    assert float(empty_scored["review_score"]) < float(occupied_scored["review_score"])


def test_build_predict_command_uses_ranked_candidate_fields():
    row = {
        "artifact_stem": "pred_9000_2048_2048_64x64",
        "local_uri": "local_data/PHerc0125_Divisions/div_100/0",
        "z": "9000",
        "y": "2048",
        "x": "2048",
        "width": "64",
        "height": "64",
        "patch_size": "64",
    }

    cmd = build_predict_command(row, python_executable="python", prediction_dir="predictions")

    assert cmd[:4] == ["python", "predict.py", "--uri", "local_data/PHerc0125_Divisions/div_100/0"]
    assert "--output_img" in cmd
    assert "predictions/pred_9000_2048_2048_64x64.png" in cmd
    assert "predictions/pred_9000_2048_2048_64x64_meta.json" in cmd
    assert "--checkpoint" in cmd
    assert "best_model.pt" in cmd


def test_load_candidates_filters_missing_local_uri(tmp_path):
    ranked_path = tmp_path / "ranked.tsv"
    rows = [
        {"review_score": "2", "local_uri": "local_data/a", "z": "1", "y": "2", "x": "3"},
        {"review_score": "1", "local_uri": "", "z": "4", "y": "5", "x": "6"},
    ]
    with open(ranked_path, "w") as f:
        f.write("\t".join(rows[0].keys()) + "\n")
        for row in rows:
            f.write("\t".join(row[key] for key in rows[0].keys()) + "\n")

    loaded = load_candidates(ranked_path)

    assert len(loaded) == 1
    assert loaded[0]["local_uri"] == "local_data/a"


def test_villa_prize_evidence_chain_validates_existing_prediction_artifacts(tmp_path):
    ranked_path = tmp_path / "ranked.tsv"
    out_dir = tmp_path / "evidence"
    prediction_dir = out_dir / "predictions"
    prediction_dir.mkdir(parents=True)
    row = {
        "review_score": "2.0",
        "scroll_id": "Scroll 2",
        "short_id": "PHerc0125",
        "division": "div_100",
        "local_uri": "local_data/PHerc0125_Divisions/div_100/0",
        "z": "9000",
        "y": "2048",
        "x": "2048",
        "width": "64",
        "height": "64",
        "patch_size": "64",
        "voxel_um": "7.91",
        "artifact_stem": "pred_9000_2048_2048_64x64",
    }
    with open(ranked_path, "w") as f:
        f.write("\t".join(row.keys()) + "\n")
        f.write("\t".join(row.values()) + "\n")

    zarr_path = tmp_path / "prediction.zarr"
    _write_json(
        zarr_path / "meta.json",
        {"format": "zarr", "voxelsize": 7.91, "height": 64, "width": 64, "slices": 1},
    )
    _write_json(zarr_path / "0" / ".zarray", {"shape": [1, 64, 64], "chunks": [1, 64, 64]})
    (prediction_dir / "pred_9000_2048_2048_64x64.png").write_bytes(b"not-a-real-png-but-present")
    _write_json(
        prediction_dir / "pred_9000_2048_2048_64x64_meta.json",
        {
            "scroll_id": "unknown",
            "source_uri": row["local_uri"],
            "position_xyz": [0, 0, 0],
            "patch_size": 64,
            "width_px": 64,
            "height_px": 64,
            "voxel_size_um": 7.91,
            "scale_bar_cm": True,
            "vc3d_zarr_path": str(zarr_path),
        },
    )

    report = build_evidence_chain(ranked_path, out_dir, execute=False)

    assert report["status"] == "PASS"
    assert (out_dir / "candidate.json").exists()
    assert (out_dir / "predict_command.sh").exists()
    assert (out_dir / "manifest.json").exists()
    assert (out_dir / "PRIZE_READINESS_REPORT.json").exists()


def test_villa_prize_evidence_chain_preflight_reports_missing_checkpoint_for_execute(tmp_path):
    ranked_path = tmp_path / "ranked.tsv"
    out_dir = tmp_path / "evidence"
    row = {
        "review_score": "2.0",
        "scroll_id": "Scroll 2",
        "short_id": "PHerc0125",
        "division": "div_100",
        "local_uri": str(tmp_path / "volume.zarr" / "0"),
        "z": "9000",
        "y": "2048",
        "x": "2048",
        "width": "64",
        "height": "64",
        "patch_size": "64",
        "voxel_um": "7.91",
        "artifact_stem": "pred_9000_2048_2048_64x64",
    }
    Path(row["local_uri"]).mkdir(parents=True)
    with open(ranked_path, "w") as f:
        f.write("\t".join(row.keys()) + "\n")
        f.write("\t".join(row.values()) + "\n")

    missing_checkpoint = tmp_path / "missing_last_model.pt"
    report = preflight_evidence_chain(ranked_path, out_dir, execute=True, checkpoint=str(missing_checkpoint))

    assert report["status"] == "FAIL"
    assert any("missing_last_model.pt is missing" in failure for failure in report["failures"])
