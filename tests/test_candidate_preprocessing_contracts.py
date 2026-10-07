"""Regression checks at the candidate/ST workflow's artifact boundaries."""

import csv
import json
import shlex
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import zarr

from scripts import (
    compute_structure_tensors as tensors,
    evaluate_deformation_metric as deformation,
    execute_lasagna_pipeline as pipeline,
)
from scripts.build_lasagna_fiber_worklist import build_worklist
from scripts.candidate_artifacts import crop_matches, staged_directory, tensor_matches
from scripts.crop_candidate_zarr import crop_candidate_zarr
from scripts.execute_lasagna_pipeline import (
    _evidence_passed,
    _structure_tensor_complete,
)


def ranked_file(tmp_path, **changes):
    base = {
        "artifact_stem": "low",
        "local_uri": "source.zarr",
        "submittable_window": "true",
        "ct_occupied_status": "true",
        "z": "0",
        "y": "0",
        "x": "0",
        "width": "64",
        "height": "64",
        "depth": "128",
        "review_score": "1",
    }
    rows = [dict(base, **changes), dict(base, artifact_stem="high", review_score="2")]
    path = tmp_path / "custom-ranked.tsv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    return path


def volume(path, shape=(6, 8, 10)):
    array = zarr.open(str(path), mode="w", shape=shape, chunks=shape, dtype="u1")
    array[:] = 7
    return array


@pytest.mark.parametrize("first_eligible", ["true", "false"])
def test_reranking_keeps_original_candidate_index_and_ranked_path(
    tmp_path, first_eligible
):
    path = ranked_file(tmp_path, submittable_window=first_eligible)
    items = build_worklist(path)
    assert items[0]["artifact_stem"] == "high"
    assert items[0]["candidate_index"] == 1
    command = shlex.split(items[0]["evidence_command"])
    assert command[command.index("--candidate-index") + 1] == "1"
    assert command[command.index("--ranked") + 1] == str(path.resolve())


@pytest.mark.parametrize(
    "change",
    [
        {"x": "1.5"},
        {"y": "-1"},
        {"z": "nan"},
        {"width": "0"},
        {"depth": "-1"},
        {"artifact_stem": "../escape"},
        {"review_score": "nan"},
        {"review_score": "1e308", "ink_max": "1e308"},
    ],
)
def test_worklist_rejects_invalid_eligible_candidate(tmp_path, change):
    with pytest.raises(ValueError):
        build_worklist(ranked_file(tmp_path, **change))


@pytest.mark.parametrize("limit", [-1, 0, 1.5, True])
def test_worklist_rejects_invalid_limit(tmp_path, limit):
    with pytest.raises(ValueError):
        build_worklist(ranked_file(tmp_path), limit=limit)


@pytest.mark.parametrize("relation", ["same", "parent", "child", "symlink"])
def test_crop_rejects_source_output_aliases(tmp_path, relation):
    source = tmp_path / "source.zarr"
    src = volume(source)
    output = {
        "same": source,
        "parent": tmp_path,
        "child": source / "nested.zarr",
        "symlink": tmp_path / "alias.zarr",
    }[relation]
    if relation == "symlink":
        output.symlink_to(source, target_is_directory=True)
    with pytest.raises(ValueError, match="overlap|source|alias"):
        crop_candidate_zarr(source, output, 0, 0, 0, 2, 2, 2)
    np.testing.assert_array_equal(src[:], 7)


def test_failed_crop_read_preserves_previous_output(tmp_path, monkeypatch):
    source = tmp_path / "source.zarr"
    destination = tmp_path / "crop.zarr"
    volume(source)
    old = volume(destination, (2, 2, 2))
    old[:] = 19
    original = zarr.Array.__getitem__

    def failed_read(self, selection):
        if str(source) == str(getattr(self.store, "path", "")):
            raise OSError("source read failed")
        return original(self, selection)

    monkeypatch.setattr(zarr.Array, "__getitem__", failed_read)
    with pytest.raises(OSError, match="source read failed"):
        crop_candidate_zarr(source, destination, 0, 0, 0, 2, 2, 2)
    np.testing.assert_array_equal(zarr.open(str(destination), mode="r")[:], 19)


@pytest.mark.parametrize("coordinate", [1.5, True, float("nan")])
def test_crop_rejects_noninteger_coordinates(tmp_path, coordinate):
    source = tmp_path / "source.zarr"
    volume(source)
    with pytest.raises(ValueError):
        crop_candidate_zarr(source, tmp_path / "crop.zarr", coordinate, 0, 0, 2, 2, 2)


def test_tensor_metadata_markers_are_not_completion(tmp_path):
    path = tmp_path / "tensor.zarr"
    for part in ["structure_tensor", "normal/x/0"]:
        directory = path / part
        directory.mkdir(parents=True)
        (directory / ".zarray").write_text("{}")
    assert not _structure_tensor_complete(path)


def test_prediction_path_is_not_readiness_pass(tmp_path):
    prediction = tmp_path / "predictions"
    prediction.mkdir()
    (prediction / "candidate_meta.json").write_text(
        json.dumps({"vc3d_zarr_path": "nonexistent.zarr"})
    )
    assert not _evidence_passed(tmp_path, "candidate")


@pytest.mark.parametrize("scale", [1e-30, 1e30])
def test_fractional_anisotropy_is_scale_invariant(scale):
    actual = deformation.compute_fractional_anisotropy(np.array([[scale, 0, 0]]))
    np.testing.assert_allclose(actual, [1.0])


def test_deformation_cli_measures_supplied_tensor(tmp_path, monkeypatch, capsys):
    path = tmp_path / "tensor.zarr"
    data = zarr.open(
        str(path), mode="w", shape=(6, 2, 2, 2), chunks=(6, 2, 2, 2), dtype="f4"
    )
    data[:] = 0
    data[0] = 1  # rank-one tensor: FA = 1, in upstream zz/zy/zx/yy/yx/xx order
    monkeypatch.setattr(sys, "argv", ["evaluate", "--st-zarr", str(path)])
    deformation.main()
    assert "Mean FA: 1.0000" in capsys.readouterr().out


def tensor_group(path, shape):
    root = zarr.open_group(str(path), mode="w")
    st = root.create_dataset(
        "structure_tensor", shape=(6, *shape), chunks=(6, *shape), dtype="f4"
    )
    st[:] = 0
    st[0] = 1
    for component in ("normal", "first_component", "second_component"):
        for axis in ("z", "y", "x"):
            root.create_dataset(f"{component}/{axis}/0", shape=shape, dtype="u1")[:] = (
                127
            )
    root.create_dataset("confidence/0", shape=shape, dtype="u1")[:] = 255
    return root


@pytest.mark.parametrize(
    "packed, expected",
    [
        ([1, 0, 0, 1, 0, 1], 0.0),
        ([9, 6, 3, 4, 2, 1], 1.0),
        ([0, 0, 0, 1, 0, 1], np.sqrt(0.5)),
        ([0, 0, 0, 0, 0, 0], 0.0),
    ],
)
def test_tensor_fa_matches_analytic_matrices(packed, expected):
    fa, _, _ = deformation.tensor_fa(np.array(packed).reshape(6, 1, 1, 1))
    np.testing.assert_allclose(fa, expected, atol=1e-7)


@pytest.mark.parametrize(
    "packed",
    [
        [1, 2, 0, 1, 0, 1],
        [1, float("nan"), 0, 1, 0, 1],
        [1, float("inf"), 0, 1, 0, 1],
    ],
)
def test_invalid_tensors_fail(packed):
    with pytest.raises(ValueError):
        deformation.tensor_fa(np.array(packed).reshape(6, 1, 1, 1))


@pytest.mark.parametrize("step", [0, -1, 1.5, True])
def test_measurement_rejects_invalid_subsampling(tmp_path, step):
    root = tensor_group(tmp_path / "tensor.zarr", (2, 2, 2))
    with pytest.raises(ValueError):
        deformation.measure_structure_tensor(root.store.path, step)


def test_measurement_subsampling_stays_anchored_across_blocks(tmp_path):
    path = tmp_path / "tensor.zarr"
    shape = (131, 3, 5)
    root = tensor_group(path, shape)
    # Only odd z planes are isotropic; stride 2 should always select rank one.
    root["structure_tensor"][3, 1::2] = 1
    root["structure_tensor"][5, 1::2] = 1
    report = deformation.measure_structure_tensor(path, 2)
    assert report["sampled_voxels"] == 66 * 2 * 3
    assert report["mean_fa"] == 1.0
    assert report["std_fa"] == 0.0


def test_zero_tensor_coverage_is_explicit(tmp_path):
    path = tmp_path / "tensor.zarr"
    root = tensor_group(path, (2, 2, 2))
    root["structure_tensor"][:] = 0
    report = deformation.measure_structure_tensor(path)
    assert report["sampled_voxels"] == report["zero_tensor_voxels"] == 8
    assert report["nonzero_mean_fa"] is None


def test_tensor_wrapper_uses_current_interpreter_and_publishes_completion(
    tmp_path, monkeypatch
):
    source = tmp_path / "source.zarr"
    volume(source)
    destination = tmp_path / "tensor.zarr"
    calls = []

    def upstream(command, **kwargs):
        calls.append((command, kwargs))
        assert command[0] == sys.executable
        assert kwargs["cwd"] == tensors.REPO_ROOT
        assert command[command.index("--input_dir") + 1] == str(source)
        tensor_group(command[command.index("--output_dir") + 1], (6, 8, 10))

    monkeypatch.setattr(tensors.subprocess, "run", upstream)
    tensors.compute_structure_tensors(source, destination, sigma=3, gpus="0,1")
    assert len(calls) == 1
    assert tensor_matches(destination, source, 3)
    assert not tensor_matches(destination, source, 2)


@pytest.mark.parametrize(
    "failure", ["exit", "missing_axis", "bad_shape", "nonfinite", "source_changed"]
)
def test_tensor_wrapper_preserves_previous_output_on_failure(
    tmp_path, monkeypatch, failure
):
    source = tmp_path / "source.zarr"
    volume(source)
    destination = tmp_path / "tensor.zarr"
    destination.mkdir()
    (destination / "old.txt").write_text("keep")

    def upstream(command, **kwargs):
        if failure == "exit":
            raise subprocess.CalledProcessError(2, command)
        output = command[command.index("--output_dir") + 1]
        root = tensor_group(output, (6, 8, 9) if failure == "bad_shape" else (6, 8, 10))
        if failure == "missing_axis":
            del root["normal/y/0"]
        elif failure == "nonfinite":
            root["structure_tensor"][0, 0, 0, 0] = float("nan")
        elif failure == "source_changed":
            zarr.open(str(source), mode="r+").attrs["generation"] = "changed"

    monkeypatch.setattr(tensors.subprocess, "run", upstream)
    with pytest.raises(
        (ValueError, KeyError, RuntimeError, subprocess.CalledProcessError)
    ):
        tensors.compute_structure_tensors(source, destination)
    assert (destination / "old.txt").read_text() == "keep"
    assert not list(tmp_path.glob(".tensor.zarr-*"))


@pytest.mark.parametrize(
    "settings", [{"rho": 2}, {"sigma": float("nan")}, {"sigma": -1}, {"gpus": "0;bad"}]
)
def test_tensor_wrapper_rejects_unsupported_or_invalid_settings(tmp_path, settings):
    with pytest.raises(ValueError):
        tensors.compute_structure_tensors(
            tmp_path / "source", tmp_path / "output", **settings
        )


def test_rebuilt_crop_invalidates_tensor_resume(tmp_path, monkeypatch):
    source = tmp_path / "source.zarr"
    crop = tmp_path / "crop.zarr"
    output = tmp_path / "tensor.zarr"
    volume(source)
    crop_candidate_zarr(source, crop, 0, 0, 0, 2, 2, 2)

    def upstream(command, **kwargs):
        tensor_group(command[command.index("--output_dir") + 1], (2, 2, 2))

    monkeypatch.setattr(tensors.subprocess, "run", upstream)
    tensors.compute_structure_tensors(crop, output)
    assert tensor_matches(output, crop)
    crop_candidate_zarr(source, crop, 0, 0, 0, 2, 2, 2)
    assert not tensor_matches(output, crop)
    assert crop_matches(crop, source, (0, 0, 0), (2, 2, 2))
    assert not crop_matches(crop, source, (1, 0, 0), (2, 2, 2))


def pipeline_item(tmp_path):
    source = tmp_path / "source.zarr"
    volume(source, (128, 64, 64))
    ranked = ranked_file(tmp_path, local_uri=str(source))
    # Limit to the lower-scored first row to exercise original index 0.
    return build_worklist(
        ranked, tmp_path / "work", limit=2, python_executable=sys.executable
    )[1]


def recording_worker(calls, success):
    def worker(name, command):
        calls.append(name)
        return success

    return worker


def test_pipeline_crop_failure_stops_dependent_stages(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline, "run_step", recording_worker(calls, False))
    result = pipeline.process_candidate(pipeline_item(tmp_path), with_evidence=True)
    assert result["status"] == "FAIL"
    assert calls == ["Crop"]


def test_pipeline_rejects_success_exit_with_no_matching_output(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline, "run_step", recording_worker(calls, True))
    result = pipeline.process_candidate(pipeline_item(tmp_path))
    assert result["status"] == "FAIL"
    assert calls == ["Crop"]


def test_pipeline_reports_partial_failure_and_invalidates_previous_pass(
    tmp_path, monkeypatch
):
    path = ranked_file(tmp_path)
    report_path = tmp_path / "execution.json"
    report_path.write_text(json.dumps({"status": "PASS"}))
    monkeypatch.setattr(pipeline, "run_step", lambda name, command: False)
    with pytest.raises(SystemExit) as error:
        pipeline.main(
            [
                "--ranked",
                str(path),
                "--output-root",
                str(tmp_path / "work"),
                "--report",
                str(report_path),
            ]
        )
    assert error.value.code == 1
    report = json.loads(report_path.read_text())
    assert report["status"] == "FAIL"
    assert len(report["candidates"]) == 2


def test_pipeline_evidence_requires_supplied_masks_before_processing(
    tmp_path, monkeypatch
):
    path = ranked_file(tmp_path)
    calls = []
    monkeypatch.setattr(pipeline, "run_step", recording_worker(calls, True))
    report_path = tmp_path / "execution.json"
    with pytest.raises(SystemExit):
        pipeline.main(
            ["--ranked", str(path), "--report", str(report_path), "--with-evidence"]
        )
    assert not calls
    assert json.loads(report_path.read_text())["status"] == "FAIL"


def test_directory_publication_rolls_back_rename_failure(tmp_path, monkeypatch):
    output = tmp_path / "output.zarr"
    output.mkdir()
    (output / "previous").write_text("keep")
    rename = Path.rename

    def fail_publication(self, destination):
        if self.name == "new.zarr":
            raise OSError("publication failed")
        return rename(self, destination)

    monkeypatch.setattr(Path, "rename", fail_publication)
    with pytest.raises(OSError, match="publication failed"):
        with staged_directory(output) as staging:
            (staging / "new").write_text("new")
    assert (output / "previous").read_text() == "keep"


def test_pipeline_success_resume_and_force_use_real_artifact_contracts(
    tmp_path, monkeypatch
):
    item = pipeline_item(tmp_path)
    calls = []

    def upstream(command, **kwargs):
        tensor_group(command[command.index("--output_dir") + 1], (128, 64, 64))

    def worker(name, command):
        calls.append(name)
        if name == "Crop":
            crop_candidate_zarr(
                item["local_uri"], item["cropped_volume_uri"], 0, 0, 0, 128, 64, 64
            )
        elif name == "Structure tensors":
            tensors.compute_structure_tensors(
                item["cropped_volume_uri"], item["structure_tensor_output"]
            )
        else:
            pytest.fail(f"unsupported stage launched: {name}")
        return True

    monkeypatch.setattr(tensors.subprocess, "run", upstream)
    monkeypatch.setattr(pipeline, "run_step", worker)
    first = pipeline.process_candidate(item)
    assert first["status"] == "PASS"
    assert calls == ["Crop", "Structure tensors"]
    generation = zarr.open(item["cropped_volume_uri"], mode="r").attrs[
        "crop_generation"
    ]
    calls.clear()
    second = pipeline.process_candidate(item)
    assert second["status"] == "PASS"
    assert second["stages"] == {"crop": "REUSED", "structure_tensor": "REUSED"}
    assert not calls
    assert pipeline.process_candidate(item, force=True)["status"] == "PASS"
    assert calls == ["Crop", "Structure tensors"]
    assert (
        zarr.open(item["cropped_volume_uri"], mode="r").attrs["crop_generation"]
        != generation
    )


def test_tensor_failure_blocks_evidence_even_with_old_outputs(tmp_path, monkeypatch):
    item = pipeline_item(tmp_path)
    crop_candidate_zarr(
        item["local_uri"], item["cropped_volume_uri"], 0, 0, 0, 128, 64, 64
    )
    tensor_group(item["structure_tensor_output"], (128, 64, 64))
    calls = []
    monkeypatch.setattr(pipeline, "run_step", recording_worker(calls, False))
    result = pipeline.process_candidate(item, with_evidence=True)
    assert result["status"] == "FAIL"
    assert calls == ["Structure tensors"]


def test_readiness_resume_revalidates_actual_evidence(evidence):
    path, metadata = evidence
    root = path.parent
    metadata["candidate"] = {
        "artifact_stem": "candidate",
        "x": "1",
        "y": "2",
        "z": "3",
        "width": "64",
        "height": "64",
        "local_uri": metadata["source_uri"],
        "output_image_path": metadata["output_image_path"],
    }
    (root / "evidence_metadata.json").write_text(json.dumps(metadata))
    (root / "PRIZE_READINESS_REPORT.json").write_text(json.dumps({"status": "PASS"}))
    (root / "manifest.json").write_text(json.dumps({"candidate_index": 2}))
    item = {
        "candidate_index": 2,
        "x": 1,
        "y": 2,
        "z": 3,
        "width": 64,
        "height": 64,
        "local_uri": metadata["source_uri"],
    }
    assert _evidence_passed(root, "candidate", item)
    assert not _evidence_passed(root, "candidate", dict(item, candidate_index=0))
    assert not _evidence_passed(root, "candidate", dict(item, x=10))
    Path(metadata["predict_mask_path"]).unlink()
    assert not _evidence_passed(root, "candidate", item)


def test_readiness_resume_rejects_different_checkpoint(evidence, tmp_path):
    path, metadata = evidence
    metadata["candidate"] = {"artifact_stem": "candidate"}
    checkpoint = tmp_path / "new.pt"
    checkpoint.write_bytes(b"weights")
    metadata["checkpoint_path"] = str(tmp_path / "previous.pt")
    (tmp_path / "evidence_metadata.json").write_text(json.dumps(metadata))
    (tmp_path / "PRIZE_READINESS_REPORT.json").write_text(
        json.dumps({"status": "PASS"})
    )
    assert not _evidence_passed(path.parent, "candidate", checkpoint=checkpoint)


@pytest.mark.parametrize(
    "script",
    [
        "compute_structure_tensors.py",
        "execute_lasagna_pipeline.py",
        "evaluate_deformation_metric.py",
    ],
)
def test_preprocessing_cli_help_works_outside_checkout(tmp_path, script):
    result = subprocess.run(
        [sys.executable, str(pipeline.REPO_ROOT / "scripts" / script), "--help"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout
