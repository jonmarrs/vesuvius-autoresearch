"""Evidence preparation must agree with execution and preserve its inputs."""

import csv
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from scripts import (
    run_villa_prize_evidence_chain as chain,
    validate_prize_artifact as validator,
)


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    volume = tmp_path / "ct.zarr"
    volume.mkdir()
    checkpoint = tmp_path / "model.pt"
    checkpoint.write_bytes(b"checkpoint contents are not preflighted")
    row = {
        "local_uri": str(volume),
        "x": "0",
        "y": "0",
        "z": "0",
        "width": "64",
        "height": "64",
        "patch_size": "64",
        "voxel_um": "7.91",
        "artifact_stem": "candidate",
    }
    ranked = tmp_path / "ranked.tsv"

    def save(**changes):
        data = dict(row, **changes)
        with ranked.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, list(data), delimiter="\t")
            writer.writeheader()
            writer.writerow(data)
        return ranked

    save()
    return tmp_path, ranked, checkpoint, save


@pytest.mark.parametrize(
    "change",
    [
        {"x": "-1"},
        {"y": "NaN"},
        {"z": "not-a-coordinate"},
        {"patch_size": "1.5"},
        {"width": "32"},
        {"height": "0"},
        {"artifact_stem": "../outside"},
    ],
)
def test_preflight_rejects_geometry_the_predictor_refuses(workspace, change):
    root, ranked, checkpoint, save = workspace
    save(**change)
    report = chain.preflight_evidence_chain(
        ranked, root / "evidence", execute=True, checkpoint=checkpoint
    )
    assert report["status"] == "FAIL"
    assert report["checks"]["candidate_geometry"]["status"] == "FAIL"
    assert not (root / "evidence").exists()


def test_checkpoint_directory_is_not_a_readable_checkpoint(workspace):
    root, ranked, _, _ = workspace
    checkpoint = root / "checkpoint.pt"
    checkpoint.mkdir()
    report = chain.preflight_evidence_chain(
        ranked, root / "evidence", execute=True, checkpoint=checkpoint
    )
    assert report["status"] == "FAIL"


def test_evidence_output_cannot_delete_its_ranked_input(workspace):
    root, ranked, checkpoint, _ = workspace
    out = root / "evidence"
    out.mkdir()
    aliased = out / "manifest.json"
    aliased.write_bytes(ranked.read_bytes())
    before = aliased.read_bytes()
    with pytest.raises(ValueError, match="collision|overlap"):
        chain.build_evidence_chain(aliased, out, checkpoint=checkpoint)
    assert aliased.read_bytes() == before


@pytest.mark.parametrize("target", ["metadata", "train_mask", "discovery_image"])
def test_validator_report_cannot_overwrite_referenced_inputs(
    tmp_path, monkeypatch, target
):
    metadata = tmp_path / "metadata.json"
    mask, image = tmp_path / "mask.npy", tmp_path / "image.png"
    mask.write_bytes(b"must survive invalid mask")
    image.write_bytes(b"must survive invalid image")
    metadata.write_text(
        json.dumps({"train_mask_path": str(mask), "output_image_path": str(image)})
    )
    output = {"metadata": metadata, "train_mask": mask, "discovery_image": image}[
        target
    ]
    before = {p: p.read_bytes() for p in (metadata, mask, image)}
    monkeypatch.setattr(
        sys, "argv", ["validator", "--metadata", str(metadata), "--out", str(output)]
    )
    with pytest.raises(SystemExit) as exc:
        validator.main()
    assert exc.value.code != 0
    assert all(path.read_bytes() == data for path, data in before.items())


@pytest.mark.parametrize(
    "name",
    [
        "PRIZE_READINESS_REPORT.json",
        "manifest.json",
        "candidate.json",
        "predictions/candidate_meta.json",
    ],
)
def test_preflight_report_cannot_replace_evidence(workspace, name):
    root, ranked, checkpoint, _ = workspace
    output = root / "evidence" / name
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('{"status": "PASS"}')
    with pytest.raises(ValueError, match="collision"):
        chain.main(
            [
                "--ranked",
                str(ranked),
                "--checkpoint",
                str(checkpoint),
                "--out-dir",
                str(root / "evidence"),
                "--preflight",
                "--execute",
                "--preflight-report",
                str(output),
            ]
        )
    assert output.read_text() == '{"status": "PASS"}'


def test_preflight_checklist_marks_uninspected_data_and_forwards_masks(
    workspace, capsys
):
    root, ranked, checkpoint, _ = workspace
    output = root / "preflight.json"
    with pytest.raises(SystemExit) as exc:
        chain.main(
            [
                "--ranked",
                str(ranked),
                "--checkpoint",
                str(checkpoint),
                "--out-dir",
                str(root / "evidence"),
                "--preflight",
                "--execute",
                "--train-mask",
                str(root / "missing.npy"),
                "--preflight-report",
                str(output),
            ]
        )
    assert exc.value.code == 1
    report = json.loads(output.read_text())
    assert report["checks"]["train_mask"]["status"] == "FAIL"
    assert report["checks"]["checkpoint_compatibility"]["status"] == "NOT_CHECKED"
    assert report["checks"]["volume_contents"]["status"] == "NOT_CHECKED"
    assert report["prize_eligibility"] == "not_assessed"
    assert report["next_actions"]
    assert json.loads(capsys.readouterr().out) == report
    assert not (root / "evidence").exists()


def test_preflight_success_only_checks_prerequisites(workspace):
    root, ranked, checkpoint, _ = workspace
    report = chain.preflight_evidence_chain(
        ranked, root / "evidence", execute=True, checkpoint=checkpoint
    )
    assert report["status"] == "PASS" and report["next_actions"]
    assert report["checks"]["artifact_validation"]["status"] == "NOT_CHECKED"
    assert report["checks"]["train_mask"]["status"] == "NOT_CHECKED"
    assert not (root / "evidence").exists()


@pytest.mark.parametrize("field", ["local_uri", "source_uri", "train_mask_path"])
def test_invalid_geometry_cannot_invalidate_a_candidate_input(workspace, field):
    root, ranked, checkpoint, save = workspace
    out = root / "evidence"
    out.mkdir()
    candidate_input = out / "manifest.json"
    candidate_input.write_bytes(b"candidate input must survive")
    save(height="0", **{field: str(candidate_input)})
    with pytest.raises(ValueError):
        chain.build_evidence_chain(ranked, out, checkpoint=checkpoint)
    assert candidate_input.read_bytes() == b"candidate input must survive"
    assert not (out / "PRIZE_READINESS_REPORT.json").exists()


@pytest.mark.parametrize("execute", [False, True])
def test_preflight_only_inherits_metadata_masks_for_existing_artifacts(
    workspace, execute
):
    root, ranked, checkpoint, _ = workspace
    out = root / "evidence"
    predictions = out / "predictions"
    predictions.mkdir(parents=True)
    (predictions / "candidate.png").write_bytes(b"existing image")
    mask = root / "mask.npy"
    mask.write_bytes(b"existing mask")
    (predictions / "candidate_meta.json").write_text(
        json.dumps({"train_mask_path": str(mask), "predict_mask_path": str(mask)})
    )
    report = chain.preflight_evidence_chain(
        ranked, out, execute=execute, checkpoint=checkpoint
    )
    for key in ("train_mask", "predict_mask"):
        assert report["checks"][key]["status"] == ("NOT_CHECKED" if execute else "PASS")


@pytest.mark.parametrize("kind", ["explicit", "metadata"])
def test_mask_input_is_checked_before_chain_invalidation(workspace, kind):
    root, ranked, checkpoint, _ = workspace
    out = root / "evidence"
    predictions = out / "predictions"
    predictions.mkdir(parents=True)
    mask = out / "candidate.json"
    mask.write_bytes(b"mask must survive")
    kwargs = {"train_mask": mask} if kind == "explicit" else {}
    if kind == "metadata":
        (predictions / "candidate_meta.json").write_text(
            json.dumps({"train_mask_path": str(mask)})
        )
    with pytest.raises(ValueError, match="collision"):
        chain.build_evidence_chain(ranked, out, checkpoint=checkpoint, **kwargs)
    assert mask.read_bytes() == b"mask must survive"
    assert not (out / "PRIZE_READINESS_REPORT.json").exists()


def test_unpublishable_fail_marker_keeps_previous_package(workspace, monkeypatch):
    root, ranked, checkpoint, _ = workspace
    out = root / "evidence"
    out.mkdir()
    for name in (
        "evidence_metadata.json",
        "manifest.json",
        "PRIZE_READINESS_REPORT.json",
    ):
        (out / name).write_text('{"status": "PASS"}')
    before = {p: p.read_bytes() for p in out.iterdir()}

    def fail(*args, **kwargs):
        raise OSError("disk error")

    monkeypatch.setattr(chain, "_write_json", fail)
    with pytest.raises(OSError, match="disk"):
        chain.build_evidence_chain(ranked, out, checkpoint=checkpoint)
    assert all(p.read_bytes() == data for p, data in before.items())


@pytest.mark.parametrize("kind", ["symlink", "hardlink"])
def test_report_aliases_via_filesystem_identity_are_rejected(tmp_path, kind):
    metadata, output = tmp_path / "meta.json", tmp_path / "report.json"
    metadata.write_text("{}")
    if kind == "symlink":
        output.symlink_to(metadata)
    else:
        os.link(metadata, output)
    with pytest.raises(SystemExit):
        validator.main(["--metadata", str(metadata), "--out", str(output)])
    assert metadata.read_text() == "{}"


def test_a_remote_file_uri_replaces_the_previous_report_with_a_failure(tmp_path):
    """Without --out the record is reported as FAIL; with it, planning the report path raised on the remote URI and
    exited before writing, so an earlier PASS stayed on disk."""
    metadata, output = tmp_path / "meta.json", tmp_path / "report.json"
    metadata.write_text(json.dumps({"train_mask_path": "file://nas/masks/train.npy"}))
    output.write_text(json.dumps({"status": "PASS"}))
    with pytest.raises(SystemExit) as exit_info:
        validator.main(["--metadata", str(metadata), "--out", str(output)])
    assert exit_info.value.code == 1
    assert json.loads(output.read_text())["status"] == "FAIL"


def test_changed_metadata_aborts_report_publication(tmp_path, monkeypatch):
    metadata, output = tmp_path / "meta.json", tmp_path / "report.json"
    metadata.write_text("{}")
    output.write_text("previous report")
    original = validator._validate_metadata

    def mutate(*args, **kwargs):
        report = original(*args, **kwargs)
        metadata.write_text('{"changed": true}')
        return report

    monkeypatch.setattr(validator, "_validate_metadata", mutate)
    with pytest.raises(SystemExit):
        validator.main(["--metadata", str(metadata), "--out", str(output)])
    assert output.read_text() == "previous report"


def test_report_serialization_failure_preserves_previous_file(tmp_path, monkeypatch):
    metadata, output = tmp_path / "meta.json", tmp_path / "report.json"
    metadata.write_text("{}")
    output.write_text("previous report")

    def fail(value, stream, **kwargs):
        stream.write("partial")
        raise RuntimeError("serializer failed")

    monkeypatch.setattr(validator.json, "dump", fail)
    with pytest.raises(SystemExit):
        validator.main(["--metadata", str(metadata), "--out", str(output)])
    assert output.read_text() == "previous report"
    assert {p.name for p in tmp_path.iterdir()} == {"meta.json", "report.json"}


@pytest.mark.parametrize(
    "text",
    ['{"prediction_complete": false, "prediction_complete": true}', '{"value": NaN}'],
)
def test_ambiguous_metadata_is_a_machine_readable_failure(tmp_path, text):
    metadata = tmp_path / "metadata.json"
    metadata.write_text(text)
    report = validator.validate(metadata)
    assert (
        report["status"] == "FAIL"
        and "metadata could not be loaded" in report["failures"][0]
    )


def test_metadata_json_has_a_bounded_capture(tmp_path, monkeypatch):
    metadata = tmp_path / "metadata.json"
    metadata.write_text('{"padding": "long value"}')
    monkeypatch.setattr(validator, "MAX_METADATA_BYTES", 10)
    report = validator.validate(metadata)
    assert report["status"] == "FAIL" and "exceeds" in report["failures"][0]


def valid_metadata(directory):
    directory.mkdir()
    Image.new("L", (64, 64)).save(directory / "image.png")
    np.save(directory / "train.npy", np.zeros((4, 4), bool))
    np.save(directory / "predict.npy", np.ones((4, 4), bool))
    metadata = directory / "metadata.json"
    metadata.write_text(
        json.dumps(
            {
                "prediction_complete": True,
                "inference_recipe": {"ink_probability": "sigmoid(ink)"},
                "source_uri": "ct.zarr",
                "scroll_id": "Scroll 2",
                "position_xyz": [0, 0, 0],
                "width_px": 1600,
                "height_px": 64,
                "patch_size": 64,
                "voxel_size_um": 8,
                "scale_bar_cm": True,
                "output_image_path": "image.png",
                "train_mask_path": "train.npy",
                "predict_mask_path": "predict.npy",
            }
        )
    )
    return metadata


def test_symlink_retarget_cannot_rebase_captured_metadata(tmp_path, monkeypatch):
    metadata = valid_metadata(tmp_path / "first")
    other = tmp_path / "second.json"
    other.write_text("{}")
    link = tmp_path / "current.json"
    link.symlink_to(metadata)
    load_mask = validator._load_mask

    def retarget(path):
        link.unlink()
        link.symlink_to(other)
        return load_mask(path)

    monkeypatch.setattr(validator, "_load_mask", retarget)
    report = validator.validate(link)
    assert report["status"] == "PASS"
    assert report["metadata_source"]["path"] == str(metadata)
    assert (
        report["metadata_source"]["sha256"]
        == hashlib.sha256(metadata.read_bytes()).hexdigest()
    )


def test_large_integer_coverage_is_failure_instead_of_exception(tmp_path):
    metadata = valid_metadata(tmp_path / "valid")
    value = json.loads(metadata.read_text())
    value["coverage_fraction"] = 10**1000
    metadata.write_text(json.dumps(value))
    assert validator.validate(metadata)["status"] == "FAIL"


def test_public_validator_fails_if_captured_source_changes(tmp_path, monkeypatch):
    metadata = valid_metadata(tmp_path / "valid")
    load = validator._load_mask

    def changed(path):
        result = load(path)
        metadata.write_text("{}")
        return result

    monkeypatch.setattr(validator, "_load_mask", changed)
    report = validator.validate(metadata)
    assert report["status"] == "FAIL"
    assert any("changed during validation" in failure for failure in report["failures"])


def test_deeply_nested_json_is_a_reported_input_error(tmp_path):
    metadata = tmp_path / "metadata.json"
    metadata.write_text('{"extra":' + "[" * 2000 + "0" + "]" * 2000 + "}")
    report = validator.validate(metadata)
    assert report["status"] == "FAIL" and "nesting" in report["failures"][0]


def test_overflowing_export_translation_is_a_reported_failure(tmp_path):
    metadata = valid_metadata(tmp_path / "valid")
    export = tmp_path / "export.zarr"
    (export / "0").mkdir(parents=True)
    files = {
        ".zgroup": {"zarr_format": 2},
        "meta.json": {
            "format": "zarr",
            "voxelsize": 8,
            "slices": 1,
            "height": 64,
            "width": 1600,
        },
        "0/.zarray": {
            "zarr_format": 2,
            "shape": [1, 64, 1600],
            "chunks": [1, 64, 64],
            "dtype": "|u1",
        },
        ".zattrs": {
            "multiscales": [
                {
                    "axes": [
                        {"name": axis, "type": "space", "unit": "micrometer"}
                        for axis in "zyx"
                    ],
                    "datasets": [
                        {
                            "path": "0",
                            "coordinateTransformations": [
                                {"type": "scale", "scale": [8, 8, 8]},
                                {
                                    "type": "translation",
                                    "translation": [10**1000, 0, 0],
                                },
                            ],
                        }
                    ],
                }
            ]
        },
    }
    for name, content in files.items():
        (export / name).write_text(json.dumps(content))
    content = json.loads(metadata.read_text())
    content["vc3d_zarr_path"] = str(export)
    metadata.write_text(json.dumps(content))
    report = validator.validate(metadata)
    assert report["status"] == "FAIL" and any(
        "numeric value" in failure for failure in report["failures"]
    )


def test_preflight_report_flag_requires_preflight_mode(workspace, monkeypatch):
    root, ranked, checkpoint, _ = workspace
    monkeypatch.setattr(
        chain.subprocess,
        "run",
        lambda *a, **k: pytest.fail("must not start processing"),
    )
    with pytest.raises(SystemExit) as exc:
        chain.main(
            [
                "--ranked",
                str(ranked),
                "--checkpoint",
                str(checkpoint),
                "--execute",
                "--preflight-report",
                str(root / "report.json"),
            ]
        )
    assert exc.value.code == 2
    assert not (root / "report.json").exists()


@pytest.mark.parametrize("filename", ["train.npy", "image.png"])
def test_special_files_are_rejected_before_opening(tmp_path, filename):
    metadata = valid_metadata(tmp_path / "valid")
    special = metadata.parent / filename
    special.unlink()
    os.mkfifo(special)
    report = validator.validate(metadata)
    assert report["status"] == "FAIL" and any(
        "regular file" in failure for failure in report["failures"]
    )


def test_preflight_requires_finite_physical_window(workspace):
    root, ranked, checkpoint, save = workspace
    save(voxel_um="1e308")
    report = chain.preflight_evidence_chain(
        ranked, root / "evidence", execute=True, checkpoint=checkpoint
    )
    assert report["status"] == "FAIL"
    assert report["checks"]["local_window_contract"]["status"] == "FAIL"


def test_metadata_file_uri_cannot_hide_checkpoint_report_alias(tmp_path):
    checkpoint, metadata = tmp_path / "model.pt", tmp_path / "meta.json"
    checkpoint.write_bytes(b"checkpoint must survive")
    metadata.write_text(json.dumps({"checkpoint_path": checkpoint.as_uri()}))
    with pytest.raises(SystemExit):
        validator.main(["--metadata", str(metadata), "--out", str(checkpoint)])
    assert checkpoint.read_bytes() == b"checkpoint must survive"


def test_local_file_uri_artifact_references_are_supported(tmp_path):
    metadata = valid_metadata(tmp_path / "valid")
    content = json.loads(metadata.read_text())
    for key in ("output_image_path", "train_mask_path", "predict_mask_path"):
        content[key] = (metadata.parent / content[key]).as_uri()
    metadata.write_text(json.dumps(content))
    assert validator.validate(metadata)["status"] == "PASS"


@pytest.mark.parametrize("scheme", ["file", "FILE"])
def test_metadata_uri_and_report_path_cannot_alias(tmp_path, scheme):
    metadata = tmp_path / "meta.json"
    metadata.write_text("{}")
    with pytest.raises(SystemExit):
        validator.main(
            [
                "--metadata",
                metadata.as_uri().replace("file:", scheme + ":", 1),
                "--out",
                str(metadata),
            ]
        )
    assert metadata.read_text() == "{}"


def test_top_level_relative_metadata_path_uses_caller_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    requested = tmp_path / "requested.json"
    requested.write_text("{}")
    other = tmp_path / "other"
    other.mkdir()
    (other / "requested.json").write_text('{"decoy": true}')
    (other / "anchor.json").write_text("{}")
    (tmp_path / "metadata.json").symlink_to(other / "anchor.json")
    report = validator.validate("requested.json")
    assert report["metadata_source"]["path"] == str(requested)
