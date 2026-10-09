"""Candidate reports must not silently align, truncate, or validate predictions."""

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import tifffile
import zarr

from scripts import cross_scroll_validation as report


def candidate(root, index=0, *, ink=True, fiber=True):
    directory = Path(root) / f"candidate_{index:03d}"
    directory.mkdir(parents=True)
    meta = {
        "artifact_stem": f"pred_{index}",
        "scroll_id": "Scroll 2",
        "short_id": "PHerc0125",
        "division": "div_90",
        "local_uri": str(Path(root) / "ct.zarr"),
        "z": "4",
        "y": "8",
        "x": "12",
        "width": "4",
        "height": "4",
        "review_score": "1.2",
    }
    (directory / "candidate.json").write_text(json.dumps(meta))
    if ink:
        array = zarr.open(
            str(directory / "predictions" / f"pred_{index}_ink.zarr" / "0"),
            mode="w",
            shape=(1, 4, 4),
            chunks=(1, 4, 4),
            dtype="u1",
        )
        array[:] = 64
    if fiber:
        values = np.zeros((2, 4, 4), np.uint8)
        values[:, :, :2] = 1
        tifffile.imwrite(
            directory / "fiber_label.tif", values, photometric="minisblack"
        )
    return directory


def test_different_shapes_cannot_be_cropped_into_alignment():
    with pytest.raises(ValueError, match="shape"):
        report._compute_metrics(np.ones((4, 4)), np.ones((3, 4)), 0.1)


@pytest.mark.parametrize("threshold", [float("nan"), float("inf"), -0.1, 1.1])
def test_threshold_must_be_finite_and_in_range(threshold):
    with pytest.raises(ValueError, match="threshold"):
        report._compute_metrics(np.ones((4, 4)), np.ones((4, 4)), threshold)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.1, 1.1])
def test_non_probability_predictions_cannot_be_reported_as_valid(value):
    with pytest.raises(ValueError, match="ink"):
        report._compute_metrics(np.full((4, 4), value), np.ones((4, 4)), 0.1)


def test_binary_255_fiber_encoding_is_normalized_before_depth_projection():
    labels = np.zeros((2, 4, 4), np.uint8)
    labels[0] = 1
    np.testing.assert_array_equal(
        report._project_fiber_to_surface(labels),
        report._project_fiber_to_surface(labels * 255),
    )


def test_volumetric_prediction_cannot_silently_use_its_first_slice(tmp_path):
    directory = candidate(tmp_path)
    array = zarr.open(
        str(directory / "predictions" / "pred_0_ink.zarr" / "0"),
        mode="w",
        shape=(2, 4, 4),
        dtype="u1",
    )
    array[:] = 64
    with pytest.raises(ValueError, match="surface"):
        report._load_ink_prediction(directory, "pred_0")


def test_zero_denominator_ratio_stays_finite_json():
    ink = np.zeros((4, 4), np.float32)
    ink[:, 2:] = 0.75
    fibers = np.zeros((4, 4), np.float32)
    fibers[:, :2] = 1
    metrics = report._compute_metrics(ink, fibers, 0.1)
    assert metrics["ink_anti_fiber_ratio"] is None
    json.dumps(metrics, allow_nan=False)


def test_invalid_coordinates_become_a_failed_candidate_record(tmp_path):
    directory = candidate(tmp_path)
    path = directory / "candidate.json"
    meta = json.loads(path.read_text())
    meta["z"] = "not a coordinate"
    path.write_text(json.dumps(meta))
    assert report._process_candidate(directory, 0.1).status == "INVALID_METADATA"


def test_missing_inputs_cannot_exit_success(tmp_path):
    root = tmp_path / "evidence"
    candidate(root, ink=False, fiber=False)
    status = report.main(
        [
            "--evidence-root",
            str(root),
            "--out",
            str(tmp_path / "summary"),
        ]
    )
    assert status == 2
    summary = json.loads((tmp_path / "summary" / "summary.json").read_text())
    assert summary["status"] == "PARTIAL"
    assert summary["failed_candidates"] == 1


def test_report_destinations_cannot_overwrite_candidate_metadata(tmp_path):
    root = tmp_path / "evidence"
    directory = candidate(root)
    path = directory / "candidate.json"
    before = path.read_bytes()
    try:
        report.main(
            [
                "--evidence-root",
                str(root),
                "--output-json",
                str(path),
                "--output-md",
                str(tmp_path / "summary.md"),
            ]
        )
    except (ValueError, SystemExit):
        pass
    assert path.read_bytes() == before


def prediction_metadata(directory, **overrides):
    meta = json.loads((directory / "candidate.json").read_text())
    details = {
        "source_uri": meta["local_uri"],
        "position_xyz": [12, 8, 4],
        "width_px": 4,
        "height_px": 4,
        "prediction_complete": True,
        "coverage_fraction": 1.0,
        "num_parts": 1,
        **overrides,
    }
    path = directory / "predictions" / f"{meta['artifact_stem']}_meta.json"
    path.write_text(json.dumps(details))
    return path


def write_ink(directory, values):
    meta = json.loads((directory / "candidate.json").read_text())
    array = zarr.open(
        str(directory / "predictions" / f"{meta['artifact_stem']}_ink.zarr" / "0"),
        mode="w",
        shape=values.shape,
        dtype=values.dtype,
    )
    array[:] = values
    return array


def test_actual_exporter_artifact_and_metadata_are_consumed(tmp_path):
    from scripts.inference.predict import save_vc3d_zarr

    directory = candidate(tmp_path)
    meta = json.loads((directory / "candidate.json").read_text())
    save_vc3d_zarr(
        directory / "predictions" / "pred_0_ink.zarr",
        np.full((4, 4), 128, np.uint8),
        source_uri=meta["local_uri"],
        origin_xyz=[12, 8, 4],
    )
    prediction_metadata(directory)
    record = report._process_candidate(directory, 0.1)
    assert record.status == "INSPECTED", record.note
    assert record.ink_pred_mean == pytest.approx(128 / 255)
    assert record.fiber_mean == 0.5
    assert record.ink_anti_fiber_ratio == 1.0
    assert record.ratio_status == "defined"
    assert record.prediction_geometry_checked
    assert record.prediction_completeness_recorded
    assert not record.alignment_verified
    assert len(record.source_files_sha256) == 4


def test_missing_provenance_remains_unknown(tmp_path):
    record = report._process_candidate(candidate(tmp_path), 0.1)
    assert record.status == "INSPECTED"
    assert not record.prediction_geometry_checked
    assert not record.prediction_completeness_recorded
    assert not record.alignment_verified
    assert len(record.absent_prediction_metadata) == 2


@pytest.mark.parametrize(
    "overrides",
    [
        {"source_uri": "/different/ct.zarr"},
        {"width_px": 5},
        {"height_px": True},
        {"position_xyz": [12, 9, 4]},
        {"position_xyz": [12, 8]},
        {"position_xyz": [12.5, 8, 4]},
        {"prediction_complete": False},
        {"prediction_complete": "true"},
        {"coverage_fraction": 0.5},
        {"coverage_fraction": float("nan")},
        {"num_parts": 2},
        {"x": 13},
        {"z": False},
    ],
)
def test_contradictory_or_partial_prediction_metadata_fails(tmp_path, overrides):
    directory = candidate(tmp_path)
    prediction_metadata(directory, **overrides)
    record = report._process_candidate(directory, 0.1)
    assert record.status == "INVALID_INK_PREDICTION"
    assert record.ink_pred_mean is None


@pytest.mark.parametrize(
    "key,value",
    [
        ("z", -1),
        ("z", True),
        ("x", "1.5"),
        ("y", float("inf")),
        ("width", 0),
        ("height", False),
        ("artifact_stem", "../outside"),
        ("artifact_stem", "/outside"),
        ("artifact_stem", ".."),
        ("scroll_id", []),
        ("short_id", ""),
        ("division", "bad\nrow"),
        ("local_uri", None),
        ("review_score", float("nan")),
    ],
)
def test_invalid_candidate_metadata_has_an_explicit_failure(tmp_path, key, value):
    directory = candidate(tmp_path)
    path = directory / "candidate.json"
    meta = json.loads(path.read_text())
    meta[key] = value
    path.write_text(json.dumps(meta))
    record = report._process_candidate(directory, 0.1)
    assert record.status == "INVALID_METADATA"
    assert record.note


@pytest.mark.parametrize("text", ["null", "[]", "{", '{"z": 1, "z": 2}', '{"z": NaN}'])
def test_malformed_candidate_json_is_recorded_instead_of_crashing(tmp_path, text):
    directory = candidate(tmp_path)
    (directory / "candidate.json").write_text(text)
    assert report._process_candidate(directory, 0.1).status == "INVALID_METADATA"


@pytest.mark.parametrize(
    "values",
    [
        np.full((2, 4, 4), 0.5),
        np.full((2, 4, 4), np.nan),
        np.full((2, 4, 4), 2, np.uint8),
        np.full((2, 4, 4), -1, np.int16),
    ],
)
def test_fiber_labels_cannot_be_probabilities_or_multiclass(values):
    with pytest.raises(ValueError, match="binary"):
        report._project_fiber_to_surface(values)


def test_mixed_binary_encodings_are_ambiguous():
    with pytest.raises(ValueError, match="encoding"):
        report._project_fiber_to_surface(np.array([[0, 1, 255]], np.uint8))


@pytest.mark.parametrize("dtype", ["u2", "i2", "complex64", "bool"])
def test_ink_zarr_rejects_unknown_integer_and_non_probability_encodings(
    tmp_path, dtype
):
    directory = candidate(tmp_path)
    write_ink(directory, np.ones((1, 4, 4), dtype=dtype))
    assert report._process_candidate(directory, 0.1).status == "INVALID_INK_PREDICTION"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_values_from_real_ink_zarr_fail(tmp_path, value):
    directory = candidate(tmp_path)
    write_ink(directory, np.full((1, 4, 4), value, np.float32))
    assert report._process_candidate(directory, 0.1).status == "INVALID_INK_PREDICTION"


def test_two_dimensional_surface_and_fibers_are_supported(tmp_path):
    directory = candidate(tmp_path)
    write_ink(directory, np.full((4, 4), 0.25, np.float32))
    tifffile.imwrite(directory / "fiber_label.tif", np.zeros((4, 4), np.uint8))
    record = report._process_candidate(directory, 0.1)
    assert record.status == "INSPECTED", record.note
    assert record.fiber_shape == [4, 4]
    assert record.ratio_status == "no_fiber_pixels"


def test_rgb_tiff_cannot_be_interpreted_as_depth(tmp_path):
    directory = candidate(tmp_path)
    tifffile.imwrite(
        directory / "fiber_label.tif", np.zeros((4, 4, 3), np.uint8), photometric="rgb"
    )
    assert report._process_candidate(directory, 0.1).status == "INVALID_FIBER_LABEL"


def test_multiple_tiff_series_are_not_silently_discarded(tmp_path):
    directory = candidate(tmp_path)
    with tifffile.TiffWriter(directory / "fiber_label.tif") as writer:
        writer.write(np.zeros((4, 4), np.uint8))
        writer.write(np.zeros((3, 4), np.uint8))
    assert report._process_candidate(directory, 0.1).status == "INVALID_FIBER_LABEL"


def test_shape_mismatch_is_a_failure_record(tmp_path):
    directory = candidate(tmp_path)
    tifffile.imwrite(
        directory / "fiber_label.tif",
        np.ones((2, 3, 4), np.uint8),
        photometric="minisblack",
    )
    record = report._process_candidate(directory, 0.1)
    assert record.status == "INVALID_SHAPE"
    assert record.ink_pred_mean is None


@pytest.mark.parametrize(
    "density,status",
    [
        (np.zeros((4, 4)), "no_fiber_pixels"),
        (np.ones((4, 4)), "no_nonfiber_pixels"),
    ],
)
def test_absent_region_has_explicit_undefined_ratio(density, status):
    result = report._compute_metrics(np.ones((4, 4)), density, 0.1)
    assert result["ratio_status"] == status
    assert result["ink_anti_fiber_ratio"] is None
    json.dumps(result, allow_nan=False)


def test_threshold_is_strict_and_does_not_mean_any_positive_voxel():
    labels = np.zeros((1001, 2, 2), np.uint8)
    labels[0] = 1
    result = report._compute_metrics(
        np.ones((2, 2)), report._project_fiber_to_surface(labels), 0.001
    )
    assert result["fiber_region_pixel_count"] == 0


def test_overflowing_ratio_is_undefined_and_json_stays_finite():
    ink = np.ones((2, 2))
    ink[:, 0] = np.nextafter(0.0, 1.0) * 2
    density = np.zeros((2, 2))
    density[:, 0] = 1
    result = report._compute_metrics(ink, density, 0.1)
    assert result["ink_anti_fiber_ratio"] is None
    assert result["ratio_status"] == "nonfinite_ratio"
    json.dumps(result, allow_nan=False)


def test_group_statistics_show_the_actual_ratio_denominator(tmp_path):
    good = report._process_candidate(candidate(tmp_path, index=0), 0.1)
    undefined = replace(
        good,
        candidate_index=1,
        ink_anti_fiber_ratio=None,
        ratio_status="zero_fiber_mean",
    )
    failed = replace(good, candidate_index=2, status="MISSING_FIBER_LABEL")
    other_scroll = replace(good, candidate_index=3, scroll_id="Scroll 3")
    result = report._aggregate([good, undefined, failed, other_scroll])
    assert result["total_candidates_inspected"] == 3
    assert len(result["groups"]) == 2
    group = result["groups"][0]
    assert group["n_candidates"] == 2
    assert group["n_defined_ratios"] == 1
    assert group["mean_anti_fiber_ratio"] == 1
    assert group["ratio_status_counts"] == {"defined": 1, "zero_fiber_mean": 1}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"top_n": 0},
        {"top_n": 257},
        {"top_n": True},
        {"top_n": np.bool_(True)},
        {"top_n": 1.5},
        {"max_pixels": 0},
        {"max_voxels": -1},
        {"fiber_threshold": float("nan")},
        {"fiber_threshold": True},
    ],
)
def test_invalid_report_settings_fail_before_artifact_reads(
    tmp_path, monkeypatch, kwargs
):
    root = tmp_path / "evidence"
    candidate(root)

    def unexpected(*args, **kw):
        pytest.fail("invalid setting reached artifact reads")

    monkeypatch.setattr(report, "_process_candidate", unexpected)
    with pytest.raises(ValueError):
        report.inspect_candidates(root, tmp_path / "out", **kwargs)
    assert not (tmp_path / "out").exists()


def test_declared_ink_budget_is_checked_before_zarr_materialization(
    tmp_path, monkeypatch
):
    directory = candidate(tmp_path)

    def unexpected(*args, **kwargs):
        pytest.fail("oversize array was materialized")

    monkeypatch.setattr(zarr.Array, "__getitem__", unexpected)
    with pytest.raises(ValueError, match="max_pixels"):
        report._load_ink_prediction(directory, "pred_0", max_pixels=15)


def test_tiff_header_budget_is_checked_before_decompression(tmp_path, monkeypatch):
    directory = candidate(tmp_path)

    def unexpected(*args, **kwargs):
        pytest.fail("oversize TIFF was decompressed")

    monkeypatch.setattr(tifffile.TiffPageSeries, "asarray", unexpected)
    with pytest.raises(ValueError, match="max_voxels"):
        report._load_fiber_label(directory, max_voxels=31)


def test_metadata_size_is_checked_before_hashing_large_file(tmp_path, monkeypatch):
    directory = candidate(tmp_path)
    (directory / "candidate.json").write_bytes(b" " * (report.MAX_METADATA_BYTES + 1))
    monkeypatch.setattr(
        report, "sha256_file", lambda path: pytest.fail("oversize metadata was hashed")
    )
    record = report._process_candidate(directory, 0.1)
    assert record.status == "INVALID_METADATA"
    assert "MiB" in record.note


def test_read_failure_is_not_disguised_as_missing_or_zero_prediction(
    tmp_path, monkeypatch
):
    directory = candidate(tmp_path)

    def failed_read(*args, **kwargs):
        raise RuntimeError("chunk read failed")

    monkeypatch.setattr(zarr.Array, "__getitem__", failed_read)
    record = report._process_candidate(directory, 0.1)
    assert record.status == "INVALID_INK_PREDICTION"
    assert "chunk read failed" in record.note
    assert record.ink_pred_mean is None


def test_numeric_candidate_selection_and_successful_paired_publication(tmp_path):
    root = tmp_path / "evidence"
    for index in (10, 2, 1):
        candidate(root, index=index)
    output = tmp_path / "new_report"
    summary = report.inspect_candidates(root, output, top_n=2)
    assert summary["status"] == "INSPECTED"
    assert summary["discovered_candidates"] == 3
    assert summary["selected_candidates"] == summary["inspected_candidates"] == 2
    assert [r["candidate_index"] for r in summary["candidates"]] == [1, 2]
    assert sorted(p.name for p in output.iterdir()) == ["summary.json", "summary.md"]
    assert json.loads((output / "summary.json").read_text()) == summary
    assert summary["scope"] == "array_cooccurrence_descriptive"
    assert not summary["alignment_verified"]
    assert not summary["independent_validation"]
    assert not summary["accuracy_measured"]
    assert not summary["prediction_completeness_verified"]
    text = (output / "summary.md").read_text()
    assert "fiber origin is unrecorded" in text
    assert "not pooled pixel ratios" in text
    assert "(consistent)" not in text
    assert "(inconsistent)" not in text


@pytest.mark.parametrize(
    "kind", ["existing", "inside_source", "source_parent", "symlink", "dangling"]
)
def test_report_output_aliases_and_existing_outputs_are_refused(tmp_path, kind):
    root = tmp_path / "evidence"
    directory = candidate(root)
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "prior.txt").write_text("keep me")
    outputs = {
        "existing": existing,
        "inside_source": directory / "out",
        "source_parent": tmp_path,
        "symlink": tmp_path / "alias",
        "dangling": tmp_path / "dangling",
    }
    outputs["symlink"].symlink_to(root, target_is_directory=True)
    outputs["dangling"].symlink_to(tmp_path / "absent", target_is_directory=True)
    before = (directory / "candidate.json").read_bytes()
    with pytest.raises(ValueError):
        report.inspect_candidates(root, outputs[kind])
    assert (directory / "candidate.json").read_bytes() == before
    assert (existing / "prior.txt").read_text() == "keep me"


@pytest.mark.parametrize(
    "kind", ["file", "nonnumeric", "duplicate", "symlink", "empty", "too_many"]
)
def test_bad_candidate_directory_catalog_is_refused(tmp_path, monkeypatch, kind):
    root = tmp_path / "evidence"
    root.mkdir()
    if kind == "file":
        (root / "candidate_000").write_text("not a directory")
    elif kind == "nonnumeric":
        (root / "candidate_bad").mkdir()
    elif kind == "duplicate":
        (root / "candidate_0").mkdir()
        (root / "candidate_000").mkdir()
    elif kind == "symlink":
        (root / "candidate_000").symlink_to(tmp_path, target_is_directory=True)
    elif kind == "too_many":
        monkeypatch.setattr(report, "MAX_DISCOVERED_CANDIDATES", 1)
        (root / "candidate_0").mkdir()
        (root / "candidate_1").mkdir()
    with pytest.raises(ValueError):
        report.inspect_candidates(root, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_failed_markdown_render_cannot_publish_half_a_pair(tmp_path, monkeypatch):
    root = tmp_path / "evidence"
    candidate(root)

    def failed_render(summary, path):
        path.write_text("partial")
        raise OSError("render failed")

    monkeypatch.setattr(report, "_render_markdown", failed_render)
    with pytest.raises(OSError, match="render failed"):
        report.inspect_candidates(root, tmp_path / "out")
    assert not (tmp_path / "out").exists()
    assert not list(tmp_path.glob(".out-*"))


@pytest.mark.parametrize("kind", ["candidate", "fiber", "ink", "appearing_metadata"])
def test_changed_source_prevents_completed_publication(tmp_path, monkeypatch, kind):
    root = tmp_path / "evidence"
    directory = candidate(root)
    render = report._render_markdown

    def change_after_measurement(summary, path):
        render(summary, path)
        if kind == "candidate":
            with (directory / "candidate.json").open("a") as stream:
                stream.write(" ")
        elif kind == "fiber":
            tifffile.imwrite(
                directory / "fiber_label.tif",
                np.zeros((2, 4, 4), np.uint8),
                photometric="minisblack",
            )
        elif kind == "ink":
            write_ink(directory, np.full((1, 4, 4), 128, np.uint8))
        else:
            prediction_metadata(directory)

    monkeypatch.setattr(report, "_render_markdown", change_after_measurement)
    with pytest.raises(ValueError, match="changed|appeared"):
        report.inspect_candidates(root, tmp_path / "out")
    assert not (tmp_path / "out").exists()
    assert not list(tmp_path.glob(".out-*"))


def test_corrupt_summary_write_is_not_published(tmp_path, monkeypatch):
    root = tmp_path / "evidence"
    candidate(root)
    monkeypatch.setattr(
        report, "write_json", lambda path, value: Path(path).write_text("{}")
    )
    with pytest.raises(ValueError, match="differs"):
        report.inspect_candidates(root, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_markdown_escapes_candidate_text_instead_of_injecting_table_cells(tmp_path):
    root = tmp_path / "evidence"
    directory = candidate(root)
    path = directory / "candidate.json"
    meta = json.loads(path.read_text())
    meta["scroll_id"] = "<script>bad</script>|extra"
    path.write_text(json.dumps(meta))
    report.inspect_candidates(root, tmp_path / "out")
    text = (tmp_path / "out" / "summary.md").read_text()
    assert "<script>" not in text
    assert "&lt;script&gt;bad&lt;/script&gt;\\|extra" in text


@pytest.mark.parametrize("partial", [False, True])
def test_cli_outside_checkout_returns_machine_readable_status(tmp_path, partial):
    root = tmp_path / "evidence"
    candidate(root, ink=not partial)
    output = tmp_path / "report"
    run = subprocess.run(
        [
            sys.executable,
            str(Path(report.__file__).resolve()),
            "--evidence-root",
            str(root),
            "--out",
            str(output),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert run.returncode == (2 if partial else 0), run.stderr
    result = json.loads(run.stdout)
    assert result["status"] == ("PARTIAL" if partial else "INSPECTED")
    assert result["scope"] == "array_cooccurrence_descriptive"
    assert (output / "summary.json").exists()
    assert (output / "summary.md").exists()


def test_retired_auto_generation_flag_never_launches_a_producer(tmp_path, monkeypatch):
    root = tmp_path / "evidence"
    candidate(root, fiber=False)
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **kw: pytest.fail("report launched a producer")
    )
    with pytest.raises(SystemExit) as exc:
        report.main(
            [
                "--evidence-root",
                str(root),
                "--out",
                str(tmp_path / "out"),
                "--auto-generate-fiber-labels",
            ]
        )
    assert exc.value.code == 2
    assert not (tmp_path / "out").exists()


def test_mixed_success_and_failure_reports_keep_each_candidate(tmp_path):
    root = tmp_path / "evidence"
    candidate(root, index=0)
    candidate(root, index=1, ink=False)
    candidate(root, index=2, fiber=False)
    bad = candidate(root, index=3)
    (bad / "candidate.json").write_text("null")
    summary = report.inspect_candidates(root, tmp_path / "out")
    assert summary["status"] == "PARTIAL"
    assert summary["selected_candidates"] == 4
    assert summary["inspected_candidates"] == 1
    assert summary["failed_candidates"] == 3
    assert [record["status"] for record in summary["candidates"]] == [
        "INSPECTED",
        "MISSING_INK_PREDICTION",
        "MISSING_FIBER_LABEL",
        "INVALID_METADATA",
    ]
    assert summary["aggregate"]["total_candidates_inspected"] == 1
    assert summary["aggregate"]["groups"][0]["n_candidates"] == 1


def test_corrupt_zarr_chunk_has_an_invalid_read_record(tmp_path):
    directory = candidate(tmp_path)
    array = zarr.open(
        str(directory / "predictions" / "pred_0_ink.zarr" / "0"), mode="r+"
    )
    array.store[array._chunk_key((0, 0, 0))] = b"corrupt compressed chunk"
    record = report._process_candidate(directory, 0.1)
    assert record.status == "INVALID_INK_PREDICTION"
    assert record.ink_pred_mean is None
    assert record.note


def test_binary_255_tiff_matches_01_tiff_through_the_real_reader(tmp_path):
    directory = candidate(tmp_path)
    expected = report._process_candidate(directory, 0.1)
    labels = tifffile.imread(directory / "fiber_label.tif")
    tifffile.imwrite(
        directory / "fiber_label.tif", labels * 255, photometric="minisblack"
    )
    actual = report._process_candidate(directory, 0.1)
    assert actual.status == "INSPECTED"
    assert actual.fiber_mean == expected.fiber_mean
    assert actual.ink_anti_fiber_ratio == expected.ink_anti_fiber_ratio
    assert actual.fiber_region_pixel_count == expected.fiber_region_pixel_count


def test_external_input_symlink_cannot_become_a_report_destination(tmp_path):
    root = tmp_path / "evidence"
    directory = candidate(root)
    labels = directory / "fiber_label.tif"
    external = tmp_path / "external" / "source.tif"
    external.parent.mkdir()
    labels.rename(external)
    labels.symlink_to(external)
    with pytest.raises(ValueError):
        report.inspect_candidates(root, external.parent / "source.tif" / "out")
    assert external.is_file()


def test_appearing_destination_preserves_prior_files_and_cleans_staging(
    tmp_path, monkeypatch
):
    root = tmp_path / "evidence"
    candidate(root)
    output = tmp_path / "out"
    render = report._render_markdown

    def appear(summary, path):
        render(summary, path)
        output.mkdir()
        (output / "prior.txt").write_text("keep me")

    monkeypatch.setattr(report, "_render_markdown", appear)
    with pytest.raises(ValueError, match="appeared"):
        report.inspect_candidates(root, output)
    assert sorted(p.name for p in output.iterdir()) == ["prior.txt"]
    assert (output / "prior.txt").read_text() == "keep me"
    assert not list(tmp_path.glob(".out-*"))
