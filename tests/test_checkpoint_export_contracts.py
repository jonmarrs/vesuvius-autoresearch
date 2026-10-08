"""Exports must preserve weights and evidence without inventing consumer proof."""

import hashlib
import json
from pathlib import Path

import pytest
import torch

from scripts import (
    export_for_production as export,
    smoke_test_villa_optimized_inference as handoff,
)
from vesuvius_autoresearch.core.model_wrappers import build_inference_model


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture
def checkpoint(tmp_path):
    config = {
        "architecture": "gated_unet",
        "patch_size": 16,
        "num_layers": 4,
        "base_feat": 4,
        "num_blocks": 2,
        "num_heads": 2,
        "dropout": 0.0,
        "use_ridges": False,
        "multi_task_heads": False,
    }
    model = build_inference_model(**config).eval()
    saved = {
        "model_state_dict": model.state_dict(),
        "config": config,
        "val_f1": 0.4,
        "ap_prevalence_lift": 2.0,
        "roc_auc": 0.7,
    }
    path = tmp_path / "training.pt"
    torch.save(saved, path)
    return path, saved, model


def test_source_checkpoint_cannot_be_overwritten(checkpoint):
    source, _, _ = checkpoint
    before = sha(source)
    with pytest.raises(ValueError):
        export.export_checkpoint(source, source)
    assert sha(source) == before


def test_partial_weights_cannot_be_exported(checkpoint, tmp_path):
    source, saved, _ = checkpoint
    saved["model_state_dict"].pop(next(iter(saved["model_state_dict"])))
    torch.save(saved, source)
    with pytest.raises((ValueError, RuntimeError)):
        export.export_checkpoint(source, tmp_path / "export.pt")
    assert not (tmp_path / "export.pt").exists()


def test_declared_architecture_must_match_actual_weights(checkpoint, tmp_path):
    source, saved, _ = checkpoint
    saved["config"]["architecture"] = "timesformer"
    torch.save(saved, source)
    with pytest.raises((ValueError, RuntimeError)):
        export.export_checkpoint(source, tmp_path / "export.pt")
    assert not (tmp_path / "export.pt").exists()


def test_missing_metric_is_unknown_and_recorded_metrics_survive(checkpoint, tmp_path):
    source, saved, _ = checkpoint
    result = export.export_checkpoint(source, tmp_path / "export.pt")
    assert result["metadata"]["val_bpb"] is None
    for name in ("val_f1", "ap_prevalence_lift", "roc_auc"):
        assert result[name] == saved[name]
    assert result["metadata"]["inference_verified"] is False
    assert result["metadata"]["source_sha256"] == sha(source)


def test_ambient_marker_cannot_supply_checkpoint_provenance(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pretrain = tmp_path / "unrelated-pretrain.pt"
    pretrain.write_bytes(b"unrelated model")
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "finetune_lejepa_run.json").write_text(
        json.dumps(
            {"pretrained_lejepa_checkpoint": str(pretrain), "patch_size": [8, 8, 8]}
        )
    )
    source = tmp_path / "primus.pt"
    torch.save(
        {
            "model_state_dict": {"shared_encoder.weight": torch.ones(1)},
            "config": {"architecture": "primus_lejepa", "patch_size": 64},
        },
        source,
    )
    result = export.export_checkpoint(source, tmp_path / "export.pt")
    assert result["config"].get("pretrained_lejepa_checkpoint") is None
    assert result["metadata"].get("pretrained_lejepa_sha") is None


def test_docker_cannot_verify_a_checkpoint_it_never_loads(tmp_path, monkeypatch):
    source = tmp_path / "timesformer.pt"
    torch.save(
        {
            "model_state_dict": {"backbone.weight": torch.ones(1)},
            "config": {"architecture": "timesformer", "patch_size": 64},
        },
        source,
    )
    calls = []
    monkeypatch.setattr(
        handoff.subprocess, "run", lambda *args, **kwargs: calls.append(args)
    )
    report = handoff.run_smoke_test(
        input_checkpoint=source,
        output_checkpoint=tmp_path / "export.pt",
        report_path=tmp_path / "report.json",
        command_path=tmp_path / "command.sh",
        model="timesformer-scroll5",
        s3_path="s3://bucket/segment",
        start_layer=0,
        end_layer=26,
        docker_image="image",
        execute_docker=True,
    )
    assert not calls
    assert report["status"] == "FAIL"
    assert report["docker_result"]["executed"] is False


def test_primus_archive_does_not_publish_an_incompatible_inference_command(tmp_path):
    source = tmp_path / "primus.pt"
    torch.save(
        {
            "model_state_dict": {"shared_encoder.weight": torch.ones(1)},
            "config": {"architecture": "primus_lejepa", "patch_size": 64},
        },
        source,
    )
    package = tmp_path / "package"
    manifest = handoff.build_primus_submission_package(
        source, package, {}, {"architecture": "primus_lejepa", "patch_size": 64}
    )
    predict = json.loads(Path(manifest["predict_manifest"]).read_text())
    assert predict["command"] is None
    assert predict["inference_verified"] is False
    assert sha(package / "model.pt") == sha(source)


def test_nonfinite_weights_cannot_be_exported(checkpoint, tmp_path):
    source, saved, _ = checkpoint
    key = next(
        key
        for key, value in saved["model_state_dict"].items()
        if value.is_floating_point()
    )
    saved["model_state_dict"][key].view(-1)[0] = float("nan")
    torch.save(saved, source)
    with pytest.raises(ValueError, match="finite"):
        export.export_checkpoint(source, tmp_path / "export.pt")
    assert not (tmp_path / "export.pt").exists()


def test_real_model_round_trip_preserves_dtype_weights_and_predictions(
    checkpoint, tmp_path
):
    from vesuvius_autoresearch.core.checkpoint_tools import build_tool_model

    source, saved, model = checkpoint
    before = sha(source)
    output = tmp_path / "nested" / "export.pt"
    export.export_checkpoint(source, output)
    reloaded = torch.load(output, map_location="cpu", weights_only=False)
    rebuilt, _ = build_tool_model(reloaded)
    for key, tensor in saved["model_state_dict"].items():
        assert reloaded["model_state_dict"][key].dtype == tensor.dtype
        torch.testing.assert_close(
            reloaded["model_state_dict"][key], tensor, rtol=0, atol=0
        )
    inputs = torch.linspace(0, 1, 4 * 16 * 16).reshape(1, 1, 4, 16, 16)
    with torch.no_grad():
        torch.testing.assert_close(rebuilt(inputs), model(inputs), rtol=0, atol=0)
    assert sha(source) == before
    assert not list(output.parent.glob(".export-*"))


@pytest.mark.parametrize(
    "kind",
    [
        "empty",
        "not-object",
        "config-list",
        "missing-architecture",
        "unknown-architecture",
        "bad-tensor",
        "nonstring-key",
        "ambiguous-keys",
        "nan-metric",
        "bool-metric",
        "nan-config",
        "missing-settings",
    ],
)
def test_malformed_checkpoints_fail_before_publication(checkpoint, tmp_path, kind):
    source, saved, _ = checkpoint
    if kind == "empty":
        saved["model_state_dict"] = {}
    elif kind == "not-object":
        saved = ["checkpoint"]
    elif kind == "config-list":
        saved["config"] = []
    elif kind == "missing-architecture":
        saved["config"].pop("architecture")
    elif kind == "unknown-architecture":
        saved["config"]["architecture"] = "typo"
    elif kind == "bad-tensor":
        saved["model_state_dict"]["bad"] = [1.0]
    elif kind == "nonstring-key":
        saved["model_state_dict"][0] = torch.ones(1)
    elif kind == "ambiguous-keys":
        saved["state_dict"] = saved["model_state_dict"]
    elif kind == "nan-metric":
        saved["roc_auc"] = float("nan")
    elif kind == "bool-metric":
        saved["val_f1"] = True
    elif kind == "nan-config":
        saved["config"]["dropout"] = float("nan")
    else:
        saved["config"].pop("num_layers")
    torch.save(saved, source)
    before = sha(source)
    with pytest.raises(export.CHECKPOINT_ERRORS):
        export.export_checkpoint(source, tmp_path / "export.pt")
    assert sha(source) == before
    assert not (tmp_path / "export.pt").exists()
    assert not list(tmp_path.glob(".export-*"))


def test_legacy_weight_key_is_explicitly_normalized(checkpoint, tmp_path):
    source, saved, _ = checkpoint
    saved["state_dict"] = saved.pop("model_state_dict")
    torch.save(saved, source)
    result = export.export_checkpoint(source, tmp_path / "export.pt")
    assert result["model_state_dict"].keys() == saved["state_dict"].keys()


def test_weight_key_order_does_not_determine_architecture(checkpoint, tmp_path):
    source, saved, _ = checkpoint
    saved["model_state_dict"] = dict(reversed(list(saved["model_state_dict"].items())))
    torch.save(saved, source)
    result = export.export_checkpoint(source, tmp_path / "export.pt")
    assert result["config"]["architecture"] == "gated_unet"


@pytest.mark.parametrize(
    "kind", ["existing", "symlink", "broken-symlink", "hardlink", "parent"]
)
def test_export_refuses_unsafe_destinations(checkpoint, tmp_path, kind):
    source, _, _ = checkpoint
    output = tmp_path / "export.pt"
    if kind == "existing":
        output.write_bytes(b"previous result")
    elif kind == "symlink":
        output.symlink_to(source)
    elif kind == "broken-symlink":
        output.symlink_to(tmp_path / "absent")
    elif kind == "hardlink":
        output.hardlink_to(source)
    else:
        output = tmp_path
    before = sha(source)
    with pytest.raises(ValueError):
        export.export_checkpoint(source, output)
    assert sha(source) == before
    if kind == "existing":
        assert output.read_bytes() == b"previous result"
    if kind in {"symlink", "broken-symlink"}:
        assert output.is_symlink()


@pytest.mark.parametrize("kind", ["write", "corrupt-write", "rename"])
def test_export_failure_cleans_staging_and_preserves_input(
    checkpoint, tmp_path, monkeypatch, kind
):
    source, _, _ = checkpoint
    output = tmp_path / "export.pt"
    before = sha(source)
    if kind in {"write", "corrupt-write"}:

        def fail_save(payload, path):
            Path(path).write_bytes(b"truncated checkpoint")
            if kind == "write":
                raise OSError("injected disk failure")

        monkeypatch.setattr(export.torch, "save", fail_save)
    else:
        original = Path.rename

        def fail_rename(path, destination):
            if Path(destination) == output:
                raise OSError("injected publication failure")
            return original(path, destination)

        monkeypatch.setattr(Path, "rename", fail_rename)
    with pytest.raises(export.CHECKPOINT_ERRORS):
        export.export_checkpoint(source, output)
    assert sha(source) == before
    assert not output.exists()
    assert not list(tmp_path.glob(".export-*"))


def test_source_change_during_validation_is_detected(checkpoint, tmp_path, monkeypatch):
    source, _, _ = checkpoint
    original = export.torch.load

    def changing_load(path, *args, **kwargs):
        result = original(path, *args, **kwargs)
        with source.open("ab") as stream:
            stream.write(b"changed")
        return result

    monkeypatch.setattr(export.torch, "load", changing_load)
    with pytest.raises(ValueError, match="changed"):
        export.export_checkpoint(source, tmp_path / "export.pt")
    assert not (tmp_path / "export.pt").exists()


def smoke(checkpoint, tmp_path, **kwargs):
    arguments = {
        "input_checkpoint": checkpoint,
        "output_checkpoint": tmp_path / "export.pt",
        "report_path": tmp_path / "report.json",
        "command_path": tmp_path / "command.sh",
        "model": "registry-model",
        "s3_path": "s3://bucket/segment",
        "start_layer": 0,
        "end_layer": 26,
        "docker_image": "image",
    }
    arguments.update(kwargs)
    return handoff.run_smoke_test(**arguments)


@pytest.mark.parametrize(
    "kind",
    [
        "report-is-source",
        "command-is-source",
        "report-is-export",
        "package-contains-source",
        "existing-report",
    ],
)
def test_handoff_preflight_protects_all_artifacts(checkpoint, tmp_path, kind):
    source, _, _ = checkpoint
    extra = {}
    if kind == "report-is-source":
        extra["report_path"] = source
    elif kind == "command-is-source":
        extra["command_path"] = source
    elif kind == "report-is-export":
        extra["report_path"] = tmp_path / "export.pt"
    elif kind == "package-contains-source":
        extra["submission_package_dir"] = tmp_path
    else:
        (tmp_path / "report.json").write_text('{"status":"PASS","old":true}')
    before = sha(source)
    with pytest.raises(ValueError):
        smoke(source, tmp_path, **extra)
    assert sha(source) == before
    assert not (tmp_path / "export.pt").exists()
    assert not (tmp_path / "command.sh").exists()
    if kind == "existing-report":
        assert json.loads((tmp_path / "report.json").read_text())["old"] is True


@pytest.mark.parametrize("kind", ["missing", "corrupt", "not-object", "bad-weights"])
def test_handoff_failure_gets_a_finite_failure_report(tmp_path, kind):
    source = tmp_path / "training.pt"
    if kind == "corrupt":
        source.write_bytes(b"not a torch checkpoint")
    elif kind == "not-object":
        torch.save([1], source)
    elif kind == "bad-weights":
        torch.save(
            {"config": {"architecture": "gated_unet"}, "model_state_dict": {}}, source
        )
    report = smoke(source, tmp_path)
    assert report["status"] == "FAIL"
    assert report["failures"]
    assert report["inference_verified"] is False
    assert report["docker_result"]["executed"] is False
    assert json.loads((tmp_path / "report.json").read_text()) == report
    assert not (tmp_path / "export.pt").exists()
    assert not (tmp_path / "command.sh").exists()


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        {"config": []},
        {"config": {"architecture": "gated_unet"}, "model_state_dict": {}},
    ],
)
def test_export_validator_reports_malformed_objects_without_crashing(tmp_path, value):
    source = tmp_path / "bad.pt"
    torch.save(value, source)
    _, failures = handoff.validate_exported_checkpoint(source)
    assert failures


@pytest.mark.parametrize(
    "change",
    [
        "source_sha256",
        "weights_validation",
        "inference_verified",
        "architecture",
        "metrics",
    ],
)
def test_export_metadata_must_agree_with_actual_envelope(checkpoint, tmp_path, change):
    source, _, _ = checkpoint
    output = tmp_path / "export.pt"
    result = export.export_checkpoint(source, output)
    result["metadata"][change] = True if change == "inference_verified" else "incorrect"
    torch.save(result, output)
    _, failures = handoff.validate_exported_checkpoint(output)
    assert failures


def test_primus_requires_explicit_shape_and_keeps_recorded_lineage(tmp_path):
    source = tmp_path / "primus.pt"
    config = {
        "architecture": "primus_lejepa",
        "pretrained_lejepa_sha": "recorded",
        "pretrained_lejepa_checkpoint": "/absent/pretrain.pt",
    }
    saved = {
        "model_state_dict": {"shared_encoder.weight": torch.ones(1)},
        "config": config,
    }
    torch.save(saved, source)
    with pytest.raises(ValueError, match="patch_size"):
        export.export_checkpoint(source, tmp_path / "failed.pt")
    config["patch_size"] = 64
    torch.save(saved, source)
    result = export.export_checkpoint(source, tmp_path / "export.pt")
    assert result["metadata"]["pretrained_lejepa_sha"] == "recorded"
    assert result["config"] == config
    assert result["metadata"]["weights_validation"] == "STRUCTURE_ONLY"


@pytest.mark.parametrize(
    "kind", ["existing", "wrong-config", "wrong-metadata", "copy-failure"]
)
def test_primus_archive_never_publishes_partial_or_misbound_outputs(
    tmp_path, monkeypatch, kind
):
    source = tmp_path / "primus.pt"
    config = {"architecture": "primus_lejepa", "patch_size": 64}
    torch.save(
        {
            "model_state_dict": {"shared_encoder.weight": torch.ones(1)},
            "config": config,
        },
        source,
    )
    package = tmp_path / "archive"
    metadata = {}
    if kind == "existing":
        package.mkdir()
        (package / "previous.txt").write_text("keep")
    elif kind == "wrong-config":
        config = {**config, "patch_size": 32}
    elif kind == "wrong-metadata":
        metadata = {"pretrained_lejepa_sha": "unrelated"}
    else:

        def fail_copy(*args, **kwargs):
            raise OSError("injected archive disk failure")

        monkeypatch.setattr(handoff.shutil, "copy2", fail_copy)
    before = sha(source)
    with pytest.raises((ValueError, OSError)):
        handoff.build_primus_submission_package(source, package, metadata, config)
    assert sha(source) == before
    if kind == "existing":
        assert (package / "previous.txt").read_text() == "keep"
    else:
        assert not package.exists()
    assert not list(tmp_path.glob(".archive-*"))


@pytest.mark.parametrize(
    "updates",
    [
        {"start_layer": -1},
        {"start_layer": True},
        {"end_layer": 0},
        {"end_layer": 0.5},
        {"end_layer": 1, "start_layer": 2},
        {"tile_size": 0},
        {"stride": 65},
        {"model": ""},
        {"s3_path": "s3://bucket"},
    ],
)
def test_registry_template_rejects_invalid_settings(updates):
    args = {
        "image": "image",
        "model": "registered",
        "s3_path": "s3://bucket/segment",
        "start_layer": 0,
        "end_layer": 26,
    }
    args.update(updates)
    with pytest.raises(ValueError):
        handoff.build_official_docker_command(**args)


@pytest.mark.parametrize(
    "script", ["export_for_production.py", "smoke_test_villa_optimized_inference.py"]
)
def test_export_clis_work_outside_checkout(checkpoint, tmp_path, script):
    import subprocess
    import sys

    source, _, _ = checkpoint
    repo = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        str(repo / "scripts" / script),
        "--input",
        str(source),
        "--output",
        str(tmp_path / "export.pt"),
    ]
    if script.startswith("smoke"):
        cmd += [
            "--report",
            str(tmp_path / "report.json"),
            "--command-out",
            str(tmp_path / "command.sh"),
        ]
    proc = subprocess.run(cmd, cwd=tmp_path, text=True, capture_output=True)
    assert proc.returncode == 0, proc.stderr
    payload = torch.load(tmp_path / "export.pt", map_location="cpu", weights_only=False)
    assert payload["metadata"]["inference_verified"] is False
    if script.startswith("smoke"):
        assert json.loads((tmp_path / "report.json").read_text())["status"] == "PASS"


def test_cli_refuses_registry_execution_with_nonzero_status(tmp_path):
    import subprocess
    import sys

    repo = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [
            sys.executable,
            str(repo / "scripts/smoke_test_villa_optimized_inference.py"),
            "--input",
            str(tmp_path / "missing.pt"),
            "--output",
            str(tmp_path / "export.pt"),
            "--report",
            str(tmp_path / "report.json"),
            "--command-out",
            str(tmp_path / "command.sh"),
            "--execute-docker",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 1
    report = json.loads((tmp_path / "report.json").read_text())
    assert "does not load" in report["failures"][0]
    assert report["docker_result"]["executed"] is False
    assert not (tmp_path / "export.pt").exists()


def test_actual_pinned_train_py_selector_cannot_read_this_legacy_envelope(tmp_path):
    import ast

    repo = Path(__file__).resolve().parents[1]
    source_code = (
        repo / "villa/vesuvius/src/vesuvius/models/run/inference.py"
    ).read_text()
    names = {"_legacy_checkpoint_uses_ema_for_inference", "_select_train_py_state_dict"}
    definitions = [
        node
        for node in ast.parse(source_code).body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    assert {node.name for node in definitions} == names
    namespace = {}
    exec(
        compile(
            ast.Module(body=definitions, type_ignores=[]),
            "pinned_train_py_selector",
            "exec",
        ),
        namespace,
    )
    envelope = {
        "config": {"architecture": "primus_lejepa", "patch_size": 64},
        "model_state_dict": {"shared_encoder.weight": torch.ones(1)},
    }
    selected, key = namespace["_select_train_py_state_dict"](envelope)
    assert selected is envelope
    assert key == "model"
    assert selected is not envelope["model_state_dict"]
    native = {
        "model": envelope["model_state_dict"],
        "model_config": {"train_patch_size": [4, 16, 16]},
    }
    selected, _ = namespace["_select_train_py_state_dict"](native)
    assert selected is native["model"]


def test_resenc_export_uses_real_local_wrapper_contract(tmp_path):
    config = {
        "architecture": "resenc_unet",
        "patch_size": 16,
        "num_layers": 4,
        "base_feat": 4,
        "multi_task_heads": True,
        "use_ridges": True,
    }
    model = build_inference_model(**config)
    assert next(iter(model.state_dict())).startswith("model.encoder.")
    source = tmp_path / "resenc.pt"
    torch.save({"config": config, "model_state_dict": model.state_dict()}, source)
    result = export.export_checkpoint(source, tmp_path / "export.pt")
    assert result["metadata"]["weights_validation"] == "STRICT_LOCAL_MODEL_LOAD"
    assert result["config"] == config


@pytest.mark.parametrize("dtype", [torch.float16, torch.float64])
def test_tensor_precision_is_preserved_in_export(checkpoint, tmp_path, dtype):
    source, saved, _ = checkpoint
    for key, value in saved["model_state_dict"].items():
        if value.is_floating_point():
            saved["model_state_dict"][key] = value.to(dtype)
    torch.save(saved, source)
    output = tmp_path / "export.pt"
    export.export_checkpoint(source, output)
    reloaded = torch.load(output, weights_only=False)
    for key, value in saved["model_state_dict"].items():
        assert reloaded["model_state_dict"][key].dtype == value.dtype
        torch.testing.assert_close(
            reloaded["model_state_dict"][key], value, rtol=0, atol=0
        )


def test_saved_artifact_must_still_have_complete_weights(
    checkpoint, tmp_path, monkeypatch
):
    source, _, _ = checkpoint
    original = export.torch.save

    def incomplete_save(payload, path):
        payload = {**payload, "model_state_dict": dict(payload["model_state_dict"])}
        payload["model_state_dict"].pop(next(iter(payload["model_state_dict"])))
        original(payload, path)

    monkeypatch.setattr(export.torch, "save", incomplete_save)
    with pytest.raises(RuntimeError):
        export.export_checkpoint(source, tmp_path / "export.pt")
    assert not (tmp_path / "export.pt").exists()
    assert not list(tmp_path.glob(".export-*"))


def test_archive_hash_binds_declarations_before_loading_source(tmp_path, monkeypatch):
    source = tmp_path / "primus.pt"
    config = {"architecture": "primus_lejepa", "patch_size": 64}
    torch.save(
        {
            "model_state_dict": {"shared_encoder.weight": torch.ones(1)},
            "config": config,
        },
        source,
    )
    original = handoff.torch.load

    def changing_load(path, *args, **kwargs):
        result = original(path, *args, **kwargs)
        with source.open("ab") as stream:
            stream.write(b"changed")
        return result

    monkeypatch.setattr(handoff.torch, "load", changing_load)
    with pytest.raises(ValueError, match="changed"):
        handoff.build_primus_submission_package(
            source, tmp_path / "archive", {}, config
        )
    assert not (tmp_path / "archive").exists()
    assert not list(tmp_path.glob(".archive-*"))
