"""Checkpoint envelope checks must not certify an unrelated upstream model."""

import json
from pathlib import Path

import pytest
import torch

from scripts.smoke_test_villa_optimized_inference import (
    build_official_docker_command,
    build_primus_submission_package,
    run_smoke_test,
    validate_exported_checkpoint,
)
from vesuvius_autoresearch.core.model_wrappers import build_inference_model


def _write_checkpoint(path, architecture="gated_unet"):
    config = {
        "architecture": architecture,
        "patch_size": 16,
        "num_layers": 4,
        "base_feat": 4,
        "num_blocks": 2,
        "num_heads": 2,
    }
    state = (
        {"shared_encoder.layer.weight": torch.ones(1)}
        if architecture == "primus_lejepa"
        else build_inference_model(**config).state_dict()
    )
    torch.save({"model_state_dict": state, "config": config, "val_bpb": 0.123}, path)


def _smoke(tmp_path, source, **kwargs):
    return run_smoke_test(
        input_checkpoint=source,
        output_checkpoint=tmp_path / "export.pt",
        report_path=tmp_path / "report.json",
        command_path=tmp_path / "command.sh",
        model="timesformer-scroll5",
        s3_path="s3://bucket/segment",
        start_layer=0,
        end_layer=26,
        docker_image="ink-detection-optimized-inference",
        **kwargs,
    )


def test_validate_exported_checkpoint_requires_complete_contract(tmp_path):
    path = tmp_path / "bad.pt"
    torch.save({"model_state_dict": {}}, path)
    _, failures = validate_exported_checkpoint(path)
    assert failures


@pytest.mark.parametrize(
    "model_type",
    ["timesformer", "resnet3d-50", "resnet3d-152", "resnet3d-152-3d-decoder"],
)
def test_build_official_docker_command_records_registry_env_contract(model_type):
    cmd = build_official_docker_command(
        image="image",
        model="registry-model",
        s3_path="s3://bucket/segment",
        start_layer=0,
        end_layer=26,
        model_type=model_type,
    )
    assert cmd[:5] == ["docker", "run", "--rm", "--gpus", "all"]
    for value in (
        "MODEL=registry-model",
        "S3_PATH=s3://bucket/segment",
        "START_LAYER=0",
        "END_LAYER=26",
        f"MODEL_TYPE={model_type}",
    ):
        assert value in cmd


def test_run_smoke_test_validates_local_weights_without_upstream_claim(tmp_path):
    source = tmp_path / "training.pt"
    _write_checkpoint(source)
    report = _smoke(tmp_path, source)
    assert report["status"] == "PASS"
    assert report["scope"] == "checkpoint envelope validation only"
    assert report["inference_verified"] is False
    assert report["submittable"] is None
    assert report["docker_command"] is None
    assert report["docker_result"]["executed"] is False
    exported, failures = validate_exported_checkpoint(tmp_path / "export.pt")
    assert not failures
    assert exported["metadata"]["weights_validation"] == "STRICT_LOCAL_MODEL_LOAD"
    assert json.loads((tmp_path / "report.json").read_text()) == report


def test_build_official_docker_command_refuses_primus_lejepa():
    with pytest.raises(ValueError, match="does not support MODEL_TYPE"):
        build_official_docker_command(
            "image", "primus", "s3://bucket/segment", 0, 26, model_type="primus_lejepa"
        )


def test_validate_exported_checkpoint_flags_wrong_weights(tmp_path):
    path = tmp_path / "bad.pt"
    torch.save(
        {
            "model_state_dict": {"encoder.weight": torch.ones(1)},
            "config": {"architecture": "timesformer", "patch_size": 64},
        },
        path,
    )
    _, failures = validate_exported_checkpoint(path)
    assert failures


def test_run_smoke_test_emits_explicit_primus_archive(tmp_path):
    source = tmp_path / "primus.pt"
    _write_checkpoint(source, "primus_lejepa")
    package = tmp_path / "archive"
    report = _smoke(tmp_path, source, submission_package_dir=package)
    assert report["status"] == "PASS"
    assert report["exported_metadata"]["weights_validation"] == "STRUCTURE_ONLY"
    assert report["inference_verified"] is False
    manifest = report["submission_package"]
    assert manifest["scope"] == "checkpoint archive only"
    assert manifest["submittable"] is None
    assert json.loads(Path(manifest["predict_manifest"]).read_text())["command"] is None
    for name in (
        "model.pt",
        "predict_manifest.json",
        "README.md",
        "REPRODUCIBILITY.md",
        "submission_manifest.json",
    ):
        assert (package / name).is_file()


def test_build_primus_archive_preserves_recorded_provenance_only(tmp_path):
    source = tmp_path / "primus.pt"
    config = {
        "architecture": "primus_lejepa",
        "patch_size": 64,
        "pretrained_lejepa_sha": "recorded-unverified",
    }
    torch.save(
        {
            "model_state_dict": {"shared_encoder.weight": torch.ones(1)},
            "config": config,
        },
        source,
    )
    manifest = build_primus_submission_package(source, tmp_path / "archive", {}, config)
    assert manifest["pretrained_lejepa_sha"] == config["pretrained_lejepa_sha"]
    assert manifest["inference_verified"] is False
    assert manifest["finetune_config_sha"] is None
