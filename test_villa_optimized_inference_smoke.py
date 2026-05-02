import json

import torch

from scripts.smoke_test_villa_optimized_inference import (
    build_official_docker_command,
    run_smoke_test,
    validate_exported_checkpoint,
)


def _write_checkpoint(path):
    torch.save(
        {
            "model_state_dict": {"layer.weight": torch.ones(1)},
            "config": {"architecture": "timesformer", "patch_size": 64},
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
