"""Submission readiness must use supplied evidence and preserve its provenance."""

import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from scripts.inference.predict import prediction_scale_bar, save_vc3d_zarr
from scripts.inference.run_ranked_inference import build_predict_command
from scripts.run_villa_prize_evidence_chain import build_evidence_chain
from scripts.validate_prize_artifact import validate

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def evidence(tmp_path):
    train = np.zeros((64, 64), dtype=bool)
    predict = np.zeros_like(train)
    train[:8, :8] = True
    predict[-8:, -8:] = True
    np.save(tmp_path / "train.npy", train)
    np.save(tmp_path / "predict.npy", predict)
    Image.new("L", (64, 64), 100).save(tmp_path / "prediction.png")
    save_vc3d_zarr(tmp_path / "ink.zarr", np.zeros((64, 64), np.uint8))
    metadata = {
        "scroll_id": "Scroll 2",
        "source_uri": "local_data/scroll.zarr",
        "position_xyz": [1, 2, 3],
        "patch_size": 64,
        "ml_window_px": 64,
        "width_px": 64,
        "height_px": 64,
        "voxel_size_um": 7.91,
        "scale_bar_cm": True,
        "source_image_is_placeholder": False,
        "metadata_is_dry_run": False,
        "output_image_path": str(tmp_path / "prediction.png"),
        "train_mask_path": str(tmp_path / "train.npy"),
        "predict_mask_path": str(tmp_path / "predict.npy"),
        "vc3d_zarr_path": str(tmp_path / "ink.zarr"),
    }
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps(metadata))
    return path, metadata


def _update(evidence, **changes):
    path, metadata = evidence
    metadata.update(changes)
    path.write_text(json.dumps(metadata))
    return path


def test_complete_submission_evidence_passes(evidence):
    assert validate(evidence[0])["status"] == "PASS"


@pytest.mark.parametrize(
    "field", ["train_mask_path", "predict_mask_path", "output_image_path"]
)
def test_missing_required_evidence_fails(evidence, field):
    assert validate(_update(evidence, **{field: None}))["status"] == "FAIL"


@pytest.mark.parametrize("voxel", [0, -1, float("nan"), float("inf"), "bad"])
def test_invalid_voxel_size_returns_finite_failure_report(evidence, voxel):
    report = validate(_update(evidence, voxel_size_um=voxel))
    assert report["status"] == "FAIL"
    json.dumps(report, allow_nan=False)


@pytest.mark.parametrize("window", [0, -64, 1.5, True, "bad"])
def test_invalid_ml_window_fails(evidence, window):
    assert validate(_update(evidence, ml_window_px=window))["status"] == "FAIL"


@pytest.mark.parametrize("position", [[1, 2], [1, 2, float("nan")], "1,2,3"])
def test_invalid_positions_fail(evidence, position):
    assert validate(_update(evidence, position_xyz=position))["status"] == "FAIL"


@pytest.mark.parametrize("value", [None, [], "not an object"])
def test_non_object_metadata_returns_failure(evidence, value):
    evidence[0].write_text(json.dumps(value))
    assert validate(evidence[0])["status"] == "FAIL"


@pytest.mark.parametrize(
    "mask", [np.zeros((64, 64)), np.full((64, 64), np.nan), np.ones((64, 64, 3))]
)
def test_empty_nonfinite_or_nonplanar_prediction_masks_fail(evidence, mask):
    np.save(evidence[1]["predict_mask_path"], mask)
    assert validate(evidence[0])["status"] == "FAIL"


def test_missing_mask_file_is_a_reported_failure(evidence):
    Path(evidence[1]["train_mask_path"]).unlink()
    report = validate(evidence[0])
    assert report["status"] == "FAIL"
    assert any("mask" in failure for failure in report["failures"])


def test_corrupt_discovery_image_is_a_reported_failure(evidence):
    Path(evidence[1]["output_image_path"]).write_bytes(b"not an image")
    report = validate(evidence[0])
    assert report["status"] == "FAIL"
    assert any("discovery image" in failure for failure in report["failures"])


def test_export_dimensions_must_match_prediction_geometry(evidence):
    report = validate(_update(evidence, width_px=128))
    assert report["status"] == "FAIL"
    assert any("dimensions" in failure for failure in report["failures"])


@pytest.mark.parametrize(
    "changes",
    [
        {"voxel_size_um": None},
        {"patch_size": 0},
        {"patch_size": 128},
        {"model_config": {"patch_size": 128}},
    ],
)
def test_geometry_cannot_omit_scale_or_understate_model_window(evidence, changes):
    assert validate(_update(evidence, **changes))["status"] == "FAIL"


@pytest.mark.parametrize("value", [[], "maybe", 1])
def test_ambiguous_placeholder_declarations_fail(evidence, value):
    assert (
        validate(_update(evidence, source_image_is_placeholder=value))["status"]
        == "FAIL"
    )


def test_relative_artifacts_work_outside_repository(evidence, tmp_path, monkeypatch):
    path, metadata = evidence
    for field in (
        "train_mask_path",
        "predict_mask_path",
        "output_image_path",
        "vc3d_zarr_path",
    ):
        metadata[field] = Path(metadata[field]).name
    path.write_text(json.dumps(metadata))
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.chdir(outside)
    assert validate(path)["status"] == "PASS"


@pytest.mark.parametrize(
    "damage", ["axes", "scale", "shape", "voxelsize", "missing_attrs"]
)
def test_incoherent_vc3d_export_fails(evidence, damage):
    root = Path(evidence[1]["vc3d_zarr_path"])
    if damage == "missing_attrs":
        (root / ".zattrs").unlink()
    elif damage in {"shape", "voxelsize"}:
        path = root / ("0/.zarray" if damage == "shape" else "meta.json")
        data = json.loads(path.read_text())
        data["shape" if damage == "shape" else "voxelsize"] = (
            [1, 0, 64] if damage == "shape" else 1.0
        )
        path.write_text(json.dumps(data))
    else:
        path = root / ".zattrs"
        data = json.loads(path.read_text())
        multiscale = data["multiscales"][0]
        if damage == "axes":
            multiscale["axes"] = multiscale["axes"][:1]
        else:
            multiscale["datasets"][0]["coordinateTransformations"][0]["scale"] = []
        path.write_text(json.dumps(data))
    assert validate(evidence[0])["status"] == "FAIL"


def _chain_inputs(evidence):
    path, metadata = evidence
    root = path.parent / "chain"
    predictions = root / "predictions"
    predictions.mkdir(parents=True)
    row = {
        "scroll_id": "Scroll 2",
        "local_uri": metadata["source_uri"],
        "x": "1",
        "y": "2",
        "z": "3",
        "width": "64",
        "height": "64",
        "patch_size": "64",
        "voxel_um": "7.91",
        "artifact_stem": "pred_3_2_1_64x64",
    }
    ranked = path.parent / "ranked.tsv"
    with ranked.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=row, delimiter="\t")
        writer.writeheader()
        writer.writerow(row)
    image = predictions / (row["artifact_stem"] + ".png")
    Image.new("L", (64, 64), 100).save(image)
    metadata["output_image_path"] = str(image)
    original = predictions / (row["artifact_stem"] + "_meta.json")
    original.write_text(json.dumps(metadata))
    return ranked, root, original


def test_chain_preserves_original_and_passes_supplied_evidence(evidence):
    ranked, root, original = _chain_inputs(evidence)
    before = original.read_bytes()
    report = build_evidence_chain(ranked, root)
    assert report["status"] == "PASS"
    assert original.read_bytes() == before
    assert not (root / "train_mask.npy").exists()
    assert not (root / "predict_mask.npy").exists()


def test_chain_does_not_invent_missing_overlap_evidence(evidence):
    _update(evidence, train_mask_path=None, predict_mask_path=None)
    ranked, root, original = _chain_inputs(evidence)
    report = build_evidence_chain(ranked, root)
    assert report["status"] == "FAIL"
    assert not (root / "train_mask.npy").exists()


@pytest.mark.parametrize(
    "changes",
    [
        {"source_image_is_placeholder": True, "evidence_mode": "placeholder_dry_run"},
        {"metadata_is_dry_run": True},
        {"position_xyz": [100, 200, 300]},
        {"patch_size": 128, "ml_window_px": 128},
    ],
)
def test_chain_cannot_relabel_or_replace_prediction_provenance(evidence, changes):
    _update(evidence, **changes)
    ranked, root, original = _chain_inputs(evidence)
    before = original.read_bytes()
    report = build_evidence_chain(ranked, root)
    assert report["status"] == "FAIL"
    assert original.read_bytes() == before
    assert validate(root / "evidence_metadata.json")["status"] == "FAIL"


def test_chain_accepts_explicit_masks_without_writing_prediction_metadata(evidence):
    masks = {key: evidence[1][key] for key in ("train_mask_path", "predict_mask_path")}
    _update(evidence, train_mask_path=None, predict_mask_path=None)
    ranked, root, original = _chain_inputs(evidence)
    before = original.read_bytes()
    report = build_evidence_chain(
        ranked,
        root,
        train_mask=masks["train_mask_path"],
        predict_mask=masks["predict_mask_path"],
    )
    assert report["status"] == "PASS"
    assert original.read_bytes() == before


def test_failed_execution_invalidates_previous_readiness(evidence, monkeypatch):
    from scripts import run_villa_prize_evidence_chain as chain

    ranked, root, original = _chain_inputs(evidence)
    assert build_evidence_chain(ranked, root)["status"] == "PASS"

    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(7, args[0])

    monkeypatch.setattr(chain.subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        build_evidence_chain(ranked, root, execute=True)
    assert (
        json.loads((root / "PRIZE_READINESS_REPORT.json").read_text())["status"]
        == "FAIL"
    )


def test_successful_exit_without_new_artifacts_cannot_reuse_previous_evidence(
    evidence, monkeypatch
):
    from scripts import run_villa_prize_evidence_chain as chain

    ranked, root, original = _chain_inputs(evidence)
    monkeypatch.setattr(chain.subprocess, "run", lambda *args, **kwargs: None)
    with pytest.raises(RuntimeError, match="did not refresh"):
        build_evidence_chain(ranked, root, execute=True)
    assert (
        json.loads((root / "PRIZE_READINESS_REPORT.json").read_text())["status"]
        == "FAIL"
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("width", -1),
        ("patch_size", "bad"),
        ("z", 1.5),
        ("x", -1),
        ("artifact_stem", "../outside"),
    ],
)
def test_ranked_command_rejects_invalid_geometry_or_stem(field, value):
    row = {"local_uri": "local.zarr", "x": "1", "y": "2", "z": "3", field: value}
    with pytest.raises(ValueError):
        build_predict_command(row)


@pytest.mark.parametrize("width,voxel", [(64, 7.91), (256, 7.91), (2000, 7.91)])
def test_prediction_bar_fits_source_width(width, voxel):
    pixels, label = prediction_scale_bar(width, voxel)
    assert pixels <= width * 0.8
    if width == 64:
        assert label == "100 µm"
    if width == 2000:
        assert label == "1 cm"


def test_direct_prediction_launcher_help_works_outside_checkout(tmp_path):
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts/inference/predict.py"), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "--checkpoint" in result.stdout


@pytest.mark.parametrize("bad_weights", ["empty", "shape"])
def test_ensemble_rejects_incomplete_weights_before_reading_volume(
    tmp_path, monkeypatch, bad_weights
):
    import torch

    from scripts.inference import ensemble_predict as ensemble

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    model = torch.nn.Linear(2, 1)
    monkeypatch.setattr(ensemble, "build_inference_model", lambda **kwargs: model)
    monkeypatch.setattr(
        ensemble,
        "FastVesuviusVolume",
        lambda *args, **kwargs: pytest.fail(
            "volume opened before checkpoint validation"
        ),
    )
    checkpoint = tmp_path / "model.pt"
    state = (
        {}
        if bad_weights == "empty"
        else {"weight": torch.ones(2, 2), "bias": torch.ones(1)}
    )
    torch.save({"config": {}, "model_state_dict": state}, checkpoint)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ensemble_predict.py",
            "--uri",
            "missing.zarr",
            "--x",
            "0",
            "--y",
            "0",
            "--z",
            "0",
            "--checkpoints",
            str(checkpoint),
        ],
    )
    with pytest.raises(RuntimeError, match="state_dict"):
        ensemble.ensemble_predict()


def test_ranked_command_points_to_existing_launcher():
    cmd = build_predict_command(
        {"local_uri": "local.zarr", "x": "1", "y": "2", "z": "3"}
    )
    assert Path(cmd[1]).is_file()
    assert Path(cmd[1]) == REPO / "scripts/inference/predict.py"


def test_dry_run_package_cannot_claim_real_evidence(tmp_path):
    source = tmp_path / "source.png"
    Image.new("L", (100, 100), 100).save(source)
    output = tmp_path / "package"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/generate_submission_package.py"),
            "--prediction-image",
            str(source),
            "--scroll-id",
            "Scroll 2",
            "--out-dir",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    metadata = json.loads((output / "metadata.json").read_text())
    assert metadata["metadata_is_dry_run"] is True
    assert metadata["overlap_evidence_mode"] == "illustrative"
    assert result.returncode == 1
    note = (output / "HALLUCINATION_MITIGATION.md").read_text()
    assert "eliminating artifact-based hallucinations" not in note
    assert "illustrative" in note


def test_validator_cli_writes_failure_report_for_corrupt_json(tmp_path):
    metadata = tmp_path / "metadata.json"
    metadata.write_text("{bad json")
    output = tmp_path / "reports/readiness.json"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/validate_prize_artifact.py"),
            "--metadata",
            str(metadata),
            "--out",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert json.loads(output.read_text())["status"] == "FAIL"


@pytest.mark.parametrize("disable_tta", [False, True])
@pytest.mark.parametrize("bad_weights", [None, "empty", "shape"])
def test_prediction_uses_checkpoint_scale_for_both_exports_and_metadata(
    tmp_path, monkeypatch, disable_tta, bad_weights
):
    import torch
    import zarr

    from scripts.inference import predict as predictor

    class ArtifactModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.bias = torch.nn.Parameter(torch.zeros(1))
            self.calls = 0

        def forward(self, x, **kwargs):
            self.calls += 1
            ink = x[:, :1].mean(dim=2) * 0 + self.bias
            fiber = x[:, :1] * 0 + self.bias
            qc = torch.ones((x.shape[0], 1), device=x.device)
            return ink, fiber, qc

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    model = ArtifactModel()
    monkeypatch.setattr(predictor, "build_prediction_model", lambda *args: model)
    volume = tmp_path / "volume.zarr"
    zarr.open(str(volume), mode="w", shape=(4, 8, 8), dtype="u1")[:] = 100
    checkpoint = tmp_path / "model.pt"
    state = model.state_dict()
    if bad_weights == "empty":
        state = {}
    elif bad_weights == "shape":
        state = {"bias": torch.ones(2)}
    torch.save(
        {
            "config": {
                "patch_size": 8,
                "num_layers": 4,
                "base_feat": 4,
                "voxel_size_um": 2.0,
            },
            "model_state_dict": state,
        },
        checkpoint,
    )
    metadata_path = tmp_path / "prediction_meta.json"
    argv = [
        "predict.py",
        "--uri",
        str(volume),
        "--checkpoint",
        str(checkpoint),
        "--x",
        "0",
        "--y",
        "0",
        "--z",
        "0",
        "--skip_active_learning",
        "--output_img",
        str(tmp_path / "prediction.png"),
        "--metadata_out",
        str(metadata_path),
    ]
    if disable_tta:
        argv.append("--disable_tta")
    monkeypatch.setattr(sys, "argv", argv)
    if bad_weights:
        with pytest.raises(RuntimeError):
            predictor.predict()
        assert not metadata_path.exists()
        return
    predictor.predict()
    metadata = json.loads(metadata_path.read_text())
    assert metadata["voxel_size_um"] == 2.0
    assert metadata["scale_bar_cm"] is False
    assert model.calls == (1 if disable_tta else 4)
    for key in ("vc3d_zarr_path", "fiber_vc3d_zarr_path"):
        attrs = json.loads((Path(metadata[key]) / ".zattrs").read_text())
        scale = attrs["multiscales"][0]["datasets"][0]["coordinateTransformations"][0]
        assert scale["scale"] == [2.0, 2.0, 2.0]
