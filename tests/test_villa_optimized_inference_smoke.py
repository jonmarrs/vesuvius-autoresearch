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


# State-dict prefixes the exporter / validator expect per architecture.
_PREFIX_BY_ARCH = {
    "timesformer": "backbone.layer.weight",
    "resnet3d_decoder": "encoder.layer.weight",
    "primus_lejepa": "shared_encoder.layer.weight",
}


def _write_checkpoint(path, architecture="timesformer"):
    key = _PREFIX_BY_ARCH.get(architecture, "layer.weight")
    torch.save(
        {
            "model_state_dict": {key: torch.ones(1)},
            "config": {"architecture": architecture, "patch_size": 64},
            "val_bpb": 0.123,
        },
        path,
    )


def test_validate_exported_checkpoint_requires_contract_keys(tmp_path):
    ckpt_path = tmp_path / "bad.pt"
    torch.save({"model_state_dict": {}}, ckpt_path)

    _, failures = validate_exported_checkpoint(ckpt_path)

    assert any("missing top-level keys" in failure for failure in failures)


def test_build_official_docker_command_records_villa_env_contract():
    cmd = build_official_docker_command(
        image="ink-detection-optimized-inference",
        model="timesformer-scroll5",
        s3_path="s3://bucket/segment",
        start_layer=0,
        end_layer=26,
    )

    assert cmd[:5] == ["docker", "run", "--rm", "--gpus", "all"]
    assert "MODEL=timesformer-scroll5" in cmd
    assert "S3_PATH=s3://bucket/segment" in cmd
    assert "START_LAYER=0" in cmd
    assert "END_LAYER=26" in cmd


def test_run_smoke_test_exports_and_reports_without_docker(tmp_path):
    input_path = tmp_path / "best_model.pt"
    output_path = tmp_path / "production_model.pt"
    report_path = tmp_path / "report.json"
    command_path = tmp_path / "command.sh"
    _write_checkpoint(input_path)

    report = run_smoke_test(
        input_checkpoint=input_path,
        output_checkpoint=output_path,
        report_path=report_path,
        command_path=command_path,
        model="timesformer-scroll5",
        s3_path="s3://bucket/segment",
        start_layer=0,
        end_layer=26,
        docker_image="ink-detection-optimized-inference",
        execute_docker=False,
    )

    assert report["status"] == "PASS"
    assert output_path.exists()
    assert command_path.exists()
    assert json.loads(report_path.read_text())["docker_result"]["executed"] is False

    exported, failures = validate_exported_checkpoint(output_path)
    assert failures == []
    assert exported["metadata"]["framework"] == "vesuvius-autoresearch"


def test_run_smoke_test_exports_resnet3d_decoder_contract(tmp_path):
    input_path = tmp_path / "best_model_resnet.pt"
    output_path = tmp_path / "production_model_resnet.pt"
    report_path = tmp_path / "report_resnet.json"
    command_path = tmp_path / "command_resnet.sh"
    _write_checkpoint(input_path, architecture="resnet3d_decoder")

    report = run_smoke_test(
        input_checkpoint=input_path,
        output_checkpoint=output_path,
        report_path=report_path,
        command_path=command_path,
        model="resnet3d-scroll5",
        s3_path="s3://bucket/segment",
        start_layer=0,
        end_layer=62,
        docker_image="ink-detection-optimized-inference",
        execute_docker=False,
    )

    assert report["status"] == "PASS"
    assert command_path.exists()
    
    cmd_text = command_path.read_text()
    assert "MODEL_TYPE=resnet3d-152-3d-decoder" in cmd_text
    assert "START_LAYER=0" in cmd_text
    assert "END_LAYER=62" in cmd_text


def test_build_official_docker_command_refuses_primus_lejepa():
    with pytest.raises(ValueError, match="does not support MODEL_TYPE"):
        build_official_docker_command(
            image="ink-detection-optimized-inference",
            model="primus-lejepa",
            s3_path="s3://bucket/segment",
            start_layer=0,
            end_layer=26,
            model_type="primus_lejepa",
        )


def test_validate_exported_checkpoint_flags_state_dict_prefix_mismatch(tmp_path):
    bad_path = tmp_path / "bad.pt"
    # Declared timesformer but state_dict uses encoder.* keys.
    torch.save(
        {
            "model_state_dict": {"encoder.layer.weight": torch.ones(1)},
            "config": {"architecture": "timesformer", "patch_size": 64},
            "metadata": {"version": "v1", "framework": "vesuvius-autoresearch", "val_bpb": 0.0},
        },
        bad_path,
    )
    _, failures = validate_exported_checkpoint(bad_path)
    assert any("does not match" in f for f in failures)


def test_run_smoke_test_emits_submission_package_for_primus_lejepa(tmp_path):
    input_path = tmp_path / "best_primus.pt"
    output_path = tmp_path / "production_primus.pt"
    report_path = tmp_path / "report_primus.json"
    command_path = tmp_path / "command_primus.sh"
    package_dir = tmp_path / "submission_pkg"
    _write_checkpoint(input_path, architecture="primus_lejepa")

    report = run_smoke_test(
        input_checkpoint=input_path,
        output_checkpoint=output_path,
        report_path=report_path,
        command_path=command_path,
        model="primus-lejepa-ink",
        s3_path="s3://bucket/segment",
        start_layer=0,
        end_layer=26,
        docker_image="ink-detection-optimized-inference",
        execute_docker=False,
        submission_package_dir=package_dir,
    )

    assert report["status"] == "PASS"
    assert report["architecture"] == "primus_lejepa"
    assert report["docker_command"] is None
    pkg = report["submission_package"]
    assert pkg is not None
    assert (package_dir / "model.pt").exists()
    assert (package_dir / "predict_manifest.json").exists()
    assert (package_dir / "README.md").exists()
    assert (package_dir / "REPRODUCIBILITY.md").exists()
    assert (package_dir / "submission_manifest.json").exists()

    predict_manifest = json.loads((package_dir / "predict_manifest.json").read_text())
    assert "--model-type" in predict_manifest["command"]
    assert "train_py" in predict_manifest["command"]


def test_build_primus_submission_package_writes_all_artifacts(tmp_path):
    src_checkpoint = tmp_path / "src.pt"
    torch.save({"model_state_dict": {"shared_encoder.layer.weight": torch.ones(1)}}, src_checkpoint)
    package_dir = tmp_path / "pkg"

    manifest = build_primus_submission_package(
        checkpoint_path=src_checkpoint,
        package_dir=package_dir,
        exported_metadata={
            "pretrained_lejepa_sha": "abc123",
            "finetune_config_sha": "def456",
        },
        exported_config={
            "architecture": "primus_lejepa",
            "patch_size": 64,
            "pretrained_lejepa_checkpoint": "/path/to/lejepa.pth",
            "finetune_config_path": "/path/to/config.yaml",
        },
    )

    assert manifest["architecture"] == "primus_lejepa"
    assert manifest["pretrained_lejepa_sha"] == "abc123"
    assert manifest["finetune_config_sha"] == "def456"
    for key in ("checkpoint", "predict_manifest", "readme", "reproducibility"):
        assert Path(manifest[key]).exists()

