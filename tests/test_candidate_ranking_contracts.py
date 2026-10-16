"""Ranking must bind usable probabilities to one complete candidate region."""

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from scripts.rank_scroll23_candidates import rank_candidates, score_row


def prediction(tmp_path):
    row = {
        "local_uri": str(tmp_path / "scroll2.zarr"),
        "x": "3",
        "y": "2",
        "z": "1",
        "width": "4",
        "height": "4",
        "patch_size": "4",
        "voxel_um": "7.91",
        "priority": "1.0",
        "submittable_window": "true",
    }
    directory = tmp_path / "predictions"
    directory.mkdir()
    stem = "pred_1_2_3_4x4"
    ink = directory / f"{stem}_ink.npy"
    fiber = directory / f"{stem}_fiber.npy"
    sidecar = directory / f"{stem}_meta.json"
    np.save(ink, np.full((4, 4), 0.25, dtype=np.float32))
    np.save(fiber, np.full((4, 4), 0.75, dtype=np.float32))
    metadata = {
        "source_uri": row["local_uri"],
        "position_xyz": [3, 2, 1],
        "width_px": 4,
        "height_px": 4,
        "patch_size": 4,
        "voxel_size_um": 7.91,
        "inference_recipe": {"ink_probability": "sigmoid(ink)"},
        "prediction_complete": True,
        "num_parts": 1,
        "part_id": 0,
        "coverage_fraction": 1.0,
        "tiles_total": 1,
        "tiles_processed": 1,
        "fiber_stats": {"mean": 0.75, "std": 0.0, "max": 0.75},
    }
    sidecar.write_text(json.dumps(metadata))
    return row, directory, ink, fiber, sidecar, metadata


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_uri", "s3://another-scroll/volume.zarr"),
        ("source_uri", None),
        ("position_xyz", [30, 2, 1]),
        ("position_xyz", None),
        ("width_px", 8),
        ("height_px", 8),
        ("patch_size", 8),
        ("voxel_size_um", 8.0),
        ("prediction_complete", False),
        ("prediction_complete", "true"),
        ("num_parts", 2),
        ("part_id", 1),
        ("coverage_fraction", 0.75),
        ("tiles_processed", 0),
    ],
)
def test_ranking_refuses_unbound_or_incomplete_predictions(tmp_path, field, value):
    row, directory, _, _, sidecar, metadata = prediction(tmp_path)
    baseline = score_row(row, prediction_dir=tmp_path / "unpredicted")
    metadata[field] = value
    sidecar.write_text(json.dumps(metadata))
    scored = score_row(row, prediction_dir=directory)
    assert scored["prediction_found"] == "false"
    assert scored["metadata_error"]
    assert scored["review_score"] == baseline["review_score"]
    assert float(scored["fiber_mean"]) == 0.0


@pytest.mark.parametrize(
    "bad", ["truncated", "shape", "nan", "inf", "negative", "above_one", "integer"]
)
def test_bad_prediction_arrays_do_not_break_or_bias_ranking(tmp_path, bad):
    row, directory, ink, _, _, _ = prediction(tmp_path)
    baseline = score_row(row, prediction_dir=tmp_path / "unpredicted")
    if bad == "truncated":
        ink.write_bytes(b"incomplete numpy output")
    else:
        values = np.full((4, 4), 0.25, np.float32)
        if bad == "shape":
            values = values[:2]
        elif bad == "integer":
            values = values.astype(np.uint8)
        else:
            values[0, 0] = {
                "nan": np.nan,
                "inf": np.inf,
                "negative": -0.1,
                "above_one": 1.1,
            }[bad]
        np.save(ink, values)
    scored = score_row(row, prediction_dir=directory)
    assert scored["prediction_found"] == "false"
    assert scored["prediction_error"]
    assert scored["review_score"] == baseline["review_score"]
    assert float(scored["fiber_mean"]) == 0.0


def test_ranking_uses_array_statistics_instead_of_stale_metadata(tmp_path):
    row, directory, _, _, sidecar, metadata = prediction(tmp_path)
    original = score_row(row, prediction_dir=directory)
    metadata["ink_stats"] = {"mean": 0.0, "std": 9.0, "max": 1000.0}
    sidecar.write_text(json.dumps(metadata))
    scored = score_row(row, prediction_dir=directory)
    assert scored["prediction_found"] == "true"
    assert scored["review_score"] == original["review_score"]
    assert float(scored["ink_mean"]) == 0.25
    assert float(scored["ink_max"]) == 0.25


def test_missing_ink_never_authorizes_retained_fiber(tmp_path):
    row, directory, ink, _, _, _ = prediction(tmp_path)
    ink.unlink()
    scored = score_row(row, prediction_dir=directory)
    assert scored["prediction_found"] == "false"
    assert float(scored["fiber_mean"]) == 0.0
    assert scored["prediction_error"]


def test_bad_optional_fiber_keeps_valid_ink_but_has_no_fiber_bonus(tmp_path):
    row, directory, _, fiber, _, _ = prediction(tmp_path)
    fiber.write_bytes(b"truncated fiber output")
    scored = score_row(row, prediction_dir=directory)
    assert scored["prediction_found"] == "true"
    assert float(scored["ink_max"]) == 0.25
    assert float(scored["fiber_mean"]) == 0.0
    assert scored["prediction_error"]


def test_ranking_preserves_healthy_rows_when_another_array_is_corrupt(tmp_path):
    row, directory, ink, _, _, _ = prediction(tmp_path)
    ink.write_bytes(b"truncated")
    healthy = dict(row, x="30")
    # Move a second complete, valid prediction into the same artifact directory.
    other = tmp_path / "other"
    other.mkdir()
    _, second_dir, _, _, _, metadata = prediction(other)
    metadata.update(source_uri=row["local_uri"], position_xyz=[30, 2, 1])
    for path in second_dir.iterdir():
        destination = directory / path.name.replace("pred_1_2_3_", "pred_1_2_30_")
        destination.write_bytes(
            json.dumps(metadata).encode()
            if path.suffix == ".json"
            else path.read_bytes()
        )
    queue = tmp_path / "queue.tsv"
    with queue.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row), delimiter="\t")
        writer.writeheader()
        writer.writerows([row, healthy])
    ranked = rank_candidates(queue, tmp_path / "ranked.tsv", directory)
    assert len(ranked) == 2
    assert ranked[0]["x"] == "30"
    assert ranked[0]["prediction_found"] == "true"
    assert ranked[1]["prediction_error"]


@pytest.mark.parametrize("chunks", [None, [], [0, 4, 4], [4, 4], ["bad", 4, 4]])
def test_malformed_ct_metadata_reports_unknown_occupancy(tmp_path, chunks):
    row, directory, _, _, _, _ = prediction(tmp_path)
    source = Path(row["local_uri"])
    source.mkdir()
    (source / ".zarray").write_text(json.dumps({"chunks": chunks}))
    scored = score_row(row, prediction_dir=directory)
    assert scored["ct_occupied_status"] == "unknown"
    assert scored["ct_occupied_error"]
    assert scored["prediction_found"] == "true"


@pytest.mark.parametrize("priority", ["nan", "inf", "-inf", "unknown"])
def test_invalid_queue_priority_is_rejected_before_publishing(tmp_path, priority):
    row, directory, _, _, _, _ = prediction(tmp_path)
    row["priority"] = priority
    queue = tmp_path / "queue.tsv"
    with queue.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row), delimiter="\t")
        writer.writeheader()
        writer.writerow(row)
    output = tmp_path / "ranked.tsv"
    with pytest.raises(ValueError, match="priority"):
        rank_candidates(queue, output, directory)
    assert not output.exists()


@pytest.mark.parametrize("axis", ["x", "y", "z"])
def test_missing_queue_coordinates_preserve_previous_ranking(tmp_path, axis):
    row, directory, _, _, _, _ = prediction(tmp_path)
    del row[axis]
    queue = tmp_path / "queue.tsv"
    with queue.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row), delimiter="\t")
        writer.writeheader()
        writer.writerow(row)
    output = tmp_path / "ranked.tsv"
    output.write_text("previous ranking\n")
    with pytest.raises(ValueError, match=axis):
        rank_candidates(queue, output, directory)
    assert output.read_text() == "previous ranking\n"


@pytest.mark.parametrize("dimension", ["width", "height"])
def test_queue_regions_smaller_than_a_model_patch_are_rejected(tmp_path, dimension):
    row, directory, _, _, _, _ = prediction(tmp_path)
    row[dimension] = "3"
    with pytest.raises(ValueError, match="patch"):
        score_row(row, directory)


def test_oversized_metadata_number_does_not_abort_ranking(tmp_path):
    row, directory, _, _, sidecar, metadata = prediction(tmp_path)
    metadata["voxel_size_um"] = 10**400
    sidecar.write_text(json.dumps(metadata))
    scored = score_row(row, directory)
    assert scored["prediction_found"] == "false"
    assert scored["metadata_error"]
    assert float(scored["fiber_mean"]) == 0.0


def test_unresolvable_metadata_source_does_not_abort_ranking(tmp_path):
    row, directory, _, _, sidecar, metadata = prediction(tmp_path)
    cycle = tmp_path / "cycle"
    cycle.symlink_to(cycle)
    metadata["source_uri"] = str(cycle)
    sidecar.write_text(json.dumps(metadata))
    scored = score_row(row, directory)
    assert scored["prediction_found"] == "false"
    assert "resolve" in scored["metadata_error"]
    assert float(scored["fiber_mean"]) == 0.0


def test_equivalent_local_source_paths_keep_usable_predictions(tmp_path, monkeypatch):
    row, directory, _, _, _, _ = prediction(tmp_path)
    monkeypatch.chdir(tmp_path)
    row["local_uri"] = "scroll2.zarr"
    scored = score_row(row, directory)
    assert scored["prediction_found"] == "true"
    assert not scored["metadata_error"]
    assert not scored["prediction_error"]
    assert float(scored["fiber_mean"]) == 0.75
