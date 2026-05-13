import json
from pathlib import Path

from scripts.execute_lasagna_pipeline import _evidence_passed, _structure_tensor_complete, _zarr_array_exists


def test_zarr_array_exists_checks_zarray_marker(tmp_path):
    zarr_dir = tmp_path / "crop.zarr"
    zarr_dir.mkdir()
    assert not _zarr_array_exists(zarr_dir)
    (zarr_dir / ".zarray").write_text("{}")
    assert _zarr_array_exists(zarr_dir)


def test_structure_tensor_complete_requires_tensor_and_normal_output(tmp_path):
    output = tmp_path / "structure_tensors.zarr"
    (output / "structure_tensor").mkdir(parents=True)
    (output / "structure_tensor" / ".zarray").write_text("{}")
    assert not _structure_tensor_complete(output)

    (output / "normal" / "x" / "0").mkdir(parents=True)
    (output / "normal" / "x" / "0" / ".zarray").write_text("{}")
    assert _structure_tensor_complete(output)


def test_evidence_passed_requires_prediction_metadata(tmp_path):
    evidence = tmp_path / "evidence"
    predictions = evidence / "predictions"
    predictions.mkdir(parents=True)
    assert not _evidence_passed(evidence, "candidate")

    meta = predictions / "candidate_meta.json"
    meta.write_text(json.dumps({"status": "PASS"}))
    assert not _evidence_passed(evidence, "candidate")

    meta.write_text(json.dumps({"vc3d_zarr_path": "candidate_ink.zarr"}))
    assert _evidence_passed(evidence, "candidate")
