"""The label producer's source geometry and file binding survive reporting."""

import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import tifffile
import zarr

from scripts import cross_scroll_validation as report
from scripts.labeling import generate_fiber_labels as generator


@pytest.fixture
def produced(tmp_path):
    source = tmp_path / "ct.zarr"
    zarr.array(
        np.random.default_rng(20).integers(0, 255, (8, 9, 10), dtype=np.uint8),
        store=str(source),
        chunks=(4, 3, 5),
    )
    table = tmp_path / "ranked.tsv"
    row = {
        "artifact_stem": "sample",
        "local_uri": str(source),
        "z": 1,
        "y": 2,
        "x": 3,
        "width": 5,
        "height": 4,
        "scroll_id": "s1",
        "short_id": "cube",
        "division": "test",
    }
    with table.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row), delimiter="\t")
        writer.writeheader()
        writer.writerow(row)
    root = tmp_path / "labels"
    assert (
        generator.main(
            [
                "--candidates",
                str(table),
                "--evidence-root",
                str(root),
                "--depth",
                "3",
                "--top-n",
                "1",
            ]
        )
        == 0
    )
    directory = root / "candidate_000"
    zarr.array(
        np.full((1, 4, 5), 0.25, np.float32),
        store=str(directory / "predictions/sample_ink.zarr/0"),
    )
    (directory / "predictions/sample_meta.json").write_text(
        json.dumps(
            {
                "source_uri": str(source),
                "position_xyz": [3, 2, 1],
                "width_px": 5,
                "height_px": 4,
                "prediction_complete": True,
                "coverage_fraction": 1.0,
                "num_parts": 1,
            }
        )
    )
    return root, directory


@pytest.mark.parametrize(
    "field,value",
    [
        ("evaluated_bbox_zyx", [2, 5, 2, 6, 3, 8]),
        ("source_path", "/other/ct.zarr"),
        ("shape_zyx", [3, 5, 4]),
        ("source_shape_zyx", [2, 9, 10]),
        ("axes", ["x", "y", "z"]),
        ("contract", True),
        ("contract", 2),
        ("label_kind", "annotation_derived_orientation_heuristic"),
        ("ct_content_sha256", "not a digest"),
        ("label_file_sha256", "0" * 64),
        ("threshold", 1.5),
        ("source_dtype", None),
        ("backend", "unknown"),
    ],
)
def test_present_contradictory_sidecar_cannot_enter_metrics(produced, field, value):
    _, directory = produced
    path = directory / "fiber_labels_meta.json"
    details = json.loads(path.read_text())
    details[field] = value
    path.write_text(json.dumps(details))
    record = report._process_candidate(directory, 0.001)
    assert record.status == "INVALID_FIBER_METADATA", record.note
    assert record.ink_pred_mean is None


def test_same_shape_replacement_is_rejected_by_the_producer_hash(produced):
    _, directory = produced
    path = directory / "fiber_label.tif"
    labels = tifffile.imread(path)
    labels[0, 0, 0] = 1 - labels[0, 0, 0]
    tifffile.imwrite(path, labels, photometric="minisblack", metadata={"axes": "ZYX"})
    record = report._process_candidate(directory, 0.001)
    assert record.status == "INVALID_FIBER_METADATA", record.note
    assert record.fiber_mean is None


def test_valid_producer_sidecar_checks_recorded_geometry_without_claiming_registration(
    produced,
):
    _, directory = produced
    record = report._process_candidate(directory, 0.001, require_fiber_metadata=True)
    assert record.status == "INSPECTED", record.note
    assert record.fiber_metadata_checked and record.recorded_geometry_agrees
    assert record.fiber_bbox_zyx == [1, 4, 2, 6, 3, 8]
    assert not record.alignment_verified
    assert len(record.source_files_sha256) == 4


def test_metadata_requirement_is_explicit_and_legacy_absence_is_visible(
    produced, tmp_path
):
    root, directory = produced
    (directory / "fiber_labels_meta.json").unlink()
    legacy = report._process_candidate(directory, 0.001)
    assert legacy.status == "INSPECTED" and not legacy.fiber_metadata_checked
    assert len(legacy.absent_fiber_metadata) == 1
    summary = report.inspect_candidates(
        root, tmp_path / "strict", require_fiber_metadata=True
    )
    assert summary["status"] == "PARTIAL"
    assert summary["candidates"][0]["status"] == "MISSING_FIBER_METADATA"
    assert summary["aggregate"]["total_candidates_inspected"] == 0


@pytest.mark.parametrize("change", ["modify", "appear"])
def test_sidecar_changes_during_render_block_publication(
    produced, tmp_path, monkeypatch, change
):
    root, directory = produced
    path = directory / "fiber_labels_meta.json"
    original = path.read_bytes()
    if change == "appear":
        path.unlink()
    render = report._render_markdown

    def mutate(summary, destination):
        render(summary, destination)
        path.write_bytes(original + b" ")

    monkeypatch.setattr(report, "_render_markdown", mutate)
    with pytest.raises(ValueError, match="changed|appeared"):
        report.inspect_candidates(root, tmp_path / "report")
    assert not (tmp_path / "report").exists()


def test_real_strict_cli_without_pythonpath_from_foreign_directory(produced, tmp_path):
    root, _ = produced
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["CUDA_VISIBLE_DEVICES"] = ""
    output = tmp_path / "report"
    result = subprocess.run(
        [
            sys.executable,
            str(Path(report.__file__).resolve()),
            "--evidence-root",
            str(root),
            "--out",
            str(output),
            "--require-fiber-metadata",
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads((output / "summary.json").read_text())
    assert summary["fiber_metadata_checked_candidates"] == 1
    assert summary["recorded_geometry_agreement_candidates"] == 1
    assert summary["fiber_metadata_required"] is True
    assert not summary["alignment_verified"]
    text = (output / "summary.md").read_text()
    assert "fiber origin is unrecorded" not in text
    assert "Recorded geometry" in text


def test_tiff_hash_and_decode_use_the_same_captured_bytes(tmp_path, monkeypatch):
    directory = tmp_path
    path = directory / "fiber_label.tif"
    # Exceed the file handle's small read-ahead buffer, so the old path reader
    # actually fetches replaced payload bytes during decoding.
    values = np.zeros((8, 64, 80), np.uint8)
    values[:, :, :40] = 1
    tifffile.imwrite(path, values, photometric="minisblack", metadata={"axes": "ZYX"})
    original_bytes = path.read_bytes()
    expected = tifffile.imread(path) != 0
    asarray = tifffile.TiffPageSeries.asarray

    def rewrite_during_decode(series, *args, **kwargs):
        # Reproduce a transient replacement between header/hash and decoding.
        # The file is restored before the end-of-run hash recheck.
        tifffile.imwrite(
            path,
            (~expected).astype(np.uint8),
            photometric="minisblack",
            metadata={"axes": "ZYX"},
        )
        try:
            return asarray(series, *args, **kwargs)
        finally:
            path.write_bytes(original_bytes)

    monkeypatch.setattr(tifffile.TiffPageSeries, "asarray", rewrite_during_decode)
    np.testing.assert_array_equal(report._load_fiber_label(directory), expected)
    hashes = {}
    actual = report._load_fiber_label(directory, source_hashes=hashes)
    np.testing.assert_array_equal(actual, expected)
    assert hashes[str(path)] == report.sha256_file(path)


def test_json_hash_and_parse_use_the_same_bounded_capture(produced, monkeypatch):
    import hashlib

    _, directory = produced
    path = directory / "candidate.json"
    captured = path.read_bytes()
    read = report.Snapshot.read

    def rewrite_after_capture(source_path, limit):
        result = read(source_path, limit)
        changed = json.loads(captured)
        changed["division"] = "changed-after-capture"
        path.write_text(json.dumps(changed))
        return result

    monkeypatch.setattr(report.Snapshot, "read", rewrite_after_capture)
    value, digest = report._json_snapshot(path)
    assert value == json.loads(captured)
    assert digest == hashlib.sha256(captured).hexdigest()
    assert digest != report.sha256_file(path)


def test_metadata_fifo_is_rejected_without_opening_it(tmp_path):
    path = tmp_path / "metadata.json"
    os.mkfifo(path)
    with pytest.raises(ValueError, match="regular file"):
        report._json_object(path)


def test_report_does_not_read_the_ct_or_certify_its_recorded_digest(
    produced, monkeypatch
):
    _, directory = produced
    source = json.loads((directory / "candidate.json").read_text())["local_uri"]
    getitem = zarr.Array.__getitem__

    def no_ct_read(array, selection):
        assert str(array.store.path) != source, "report unexpectedly read CT"
        return getitem(array, selection)

    monkeypatch.setattr(zarr.Array, "__getitem__", no_ct_read)
    record = report._process_candidate(directory, 0.001)
    assert record.status == "INSPECTED", record.note
    assert record.fiber_ct_content_sha256_recorded
    assert "CT content not independently verified" in record.alignment_scope


def test_missing_prediction_sidecars_do_not_become_recorded_agreement(produced):
    _, directory = produced
    (directory / "predictions/sample_meta.json").unlink()
    record = report._process_candidate(directory, 0.001, require_fiber_metadata=True)
    assert record.status == "INSPECTED", record.note
    assert record.fiber_metadata_checked
    assert not record.recorded_geometry_agrees
    assert "prediction_origin_unknown" in record.alignment_scope


def test_prediction_metadata_symlink_retargeting_blocks_publication(
    produced, tmp_path, monkeypatch
):
    root, directory = produced
    path = directory / "predictions/sample_meta.json"
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_bytes(path.read_bytes())
    second.write_bytes(path.read_bytes() + b" ")
    path.unlink()
    path.symlink_to(first)
    render = report._render_markdown

    def retarget(summary, destination):
        render(summary, destination)
        path.unlink()
        path.symlink_to(second)

    monkeypatch.setattr(report, "_render_markdown", retarget)
    with pytest.raises(ValueError, match="changed"):
        report.inspect_candidates(root, tmp_path / "out")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("field", ["shape_zyx", "evaluated_bbox_zyx"])
def test_boolean_coordinates_in_fiber_metadata_are_not_numbers(produced, field):
    _, directory = produced
    path = directory / "fiber_labels_meta.json"
    details = json.loads(path.read_text())
    details[field][0] = True
    path.write_text(json.dumps(details))
    record = report._process_candidate(directory, 0.001)
    assert record.status == "INVALID_FIBER_METADATA"


@pytest.mark.parametrize(
    "text",
    [
        "null",
        "[]",
        "{",
        '{"contract": 1, "contract": 1}',
        '{"unused": 1e999}',
        "[" * 2000 + "0" + "]" * 2000,
    ],
)
def test_malformed_nonfinite_or_deep_metadata_is_a_failure_record(produced, text):
    _, directory = produced
    (directory / "fiber_labels_meta.json").write_text(text)
    record = report._process_candidate(directory, 0.001)
    assert record.status == "INVALID_FIBER_METADATA"
    assert record.ink_pred_mean is None


def test_mixed_provenance_counts_only_eligible_candidates(produced, tmp_path):
    root, directory = produced
    other = root / "candidate_001"
    shutil.copytree(directory, other)
    (other / "fiber_labels_meta.json").unlink()
    default = report.inspect_candidates(root, tmp_path / "legacy-allowed")
    assert default["inspected_candidates"] == 2
    assert default["fiber_metadata_checked_candidates"] == 1
    assert default["recorded_geometry_agreement_candidates"] == 1
    group = default["aggregate"]["groups"][0]
    assert group["n_candidates"] == 2 and group["n_fiber_metadata_checked"] == 1
    strict = report.inspect_candidates(
        root, tmp_path / "strict", require_fiber_metadata=True
    )
    assert strict["status"] == "PARTIAL" and strict["inspected_candidates"] == 1
    assert strict["aggregate"]["groups"][0]["n_candidates"] == 1
    assert strict["fiber_metadata_checked_candidates"] == 1


def test_disappearing_sidecar_never_silently_downgrades_to_legacy(
    produced, monkeypatch
):
    _, directory = produced
    path = directory / "fiber_labels_meta.json"
    load = report._load_fiber_label

    def remove_before_decode(*args, **kwargs):
        path.unlink()
        return load(*args, **kwargs)

    monkeypatch.setattr(report, "_load_fiber_label", remove_before_decode)
    record = report._process_candidate(directory, 0.001)
    assert record.status == "INVALID_INPUT_STABILITY"
    assert record.ink_pred_mean is None


@pytest.mark.parametrize("replacement", ["fifo", "oversized"])
def test_final_tiff_rechecks_are_regular_and_bounded(
    produced, tmp_path, monkeypatch, replacement
):
    root, directory = produced
    path = directory / "fiber_label.tif"
    render = report._render_markdown

    def replace_after_measurement(summary, destination):
        render(summary, destination)
        path.unlink()
        if replacement == "fifo":
            os.mkfifo(path)
        else:
            path.write_bytes(b"0" * (16 * 60 + report.MAX_METADATA_BYTES + 1))

    monkeypatch.setattr(report, "_render_markdown", replace_after_measurement)
    with pytest.raises(ValueError, match="regular file|byte budget"):
        report.inspect_candidates(root, tmp_path / "out", max_voxels=60)
    assert not (tmp_path / "out").exists()
