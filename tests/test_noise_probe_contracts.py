"""Repeatability reports require isolated execution and complete finite evidence."""

from __future__ import annotations

import hashlib
import json
import math
import os
import pickle
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType

import pytest

from scripts import f1_noise_probe as probe
from scripts.loop_control import acquire_lock, running_pid

REPO = Path(__file__).resolve().parents[1]


def result(value=0.6, *, protocol=probe.VALIDATION_PROTOCOL):
    return {
        "val_f1": value,
        "val_f1_threshold": 0.4,
        "ap_prevalence_lift": 1.5,
        "roc_auc": 0.7,
        "val_positive_rate": 0.4,
        "val_protocol": protocol,
        "train_sampling_seed": 42,
        "is_success": False,  # a valid trial need not improve on the incumbent
        "validation_diag": {
            "protocol": protocol,
            "complete": True,
            "requested_patches": 4,
            "usable_patches": 3,
            "empty_target_patches": 1,
            "batch_errors": 0,
            "inputs_sha256": "f" * 64,
        },
        "avg_skel_dist": float("nan"),  # legacy reported-only field
    }


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    config = project / "config.json"
    config.write_text(
        json.dumps(
            {
                "time_budget": 1,
                "uris": ["data/train/ct.zarr"],
                "val_uri": "data/val/ct.zarr",
                "unlabeled_uris": [],
            }
        )
    )
    checkpoint = project / "best_model.pt"
    checkpoint.write_bytes(b"fake starting checkpoint; no model execution")
    prior = project / "run_result.json"
    prior.write_text('{"prior": "loop result"}')
    monkeypatch.setattr(probe, "REPO", project)
    return project, config, checkpoint, tmp_path / "probe"


def fake_runner(
    inputs,
    monkeypatch,
    *,
    code=0,
    invalid=None,
    extra="",
    protocol=probe.VALIDATION_PROTOCOL,
):
    project, _, _, _ = inputs
    payload = result(protocol=protocol)
    if invalid:
        payload.update(invalid)
    runner = project / "fake_trainer.py"
    runner.write_text(
        "import json, os, sys\nfrom pathlib import Path\n"
        "config = json.loads(Path(sys.argv[2]).read_text())\n"
        f"payload = json.loads({json.dumps(payload)!r})\n"
        "if Path.cwd().name.endswith('02'): payload['val_f1'] = 0.8\n"
        "assert Path(config['checkpoint_out']).parent == Path.cwd()\n"
        "assert Path(config['cache_dir']).parent == Path.cwd()\n"
        "assert config['use_wandb'] is False\n"
        "assert os.environ['WANDB_MODE'] == 'disabled'\n"
        "Path(config['checkpoint_out']).write_bytes(b'candidate')\n"
        "Path('run_result.json').write_text(json.dumps(payload))\n"
        + extra
        + f"raise SystemExit({code})\n"
    )
    monkeypatch.setattr(probe, "RUNNER", runner)
    return runner


def plan(inputs, **kwargs):
    _, config, checkpoint, output = inputs
    return probe.make_plan(config, checkpoint, output, runs=2, **kwargs)


def test_import_is_read_only_outside_checkout_without_gpu_imports(tmp_path):
    code = f"""
import sys
sys.path.insert(0, {str(REPO)!r})
class BlockTrainingImports:
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] in {{'torch', 'cupy', 'wandb'}}:
            raise AssertionError('training import during probe import: ' + fullname)
sys.meta_path.insert(0, BlockTrainingImports())
import scripts.f1_noise_probe
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert list(tmp_path.iterdir()) == []


def test_default_cli_only_plans(inputs, capsys):
    project, config, checkpoint, output = inputs
    before = {str(p): p.read_bytes() for p in project.iterdir()}
    assert (
        probe.main(
            [
                "--config",
                str(config),
                "--checkpoint",
                str(checkpoint),
                "--out",
                str(output),
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "DRY_RUN" and report["training_executed"] is False
    assert not output.exists()
    assert {str(p): p.read_bytes() for p in project.iterdir()} == before


def test_config_rewrite_while_planning_cannot_bind_new_hash_to_old_values(
    inputs, monkeypatch
):
    original = probe.ExperimentConfig.__post_init__

    def rewrite_after_parsing(config):
        original(config)
        rewritten = json.loads(inputs[1].read_text())
        rewritten["lr"] = 0.002
        inputs[1].write_text(json.dumps(rewritten))

    monkeypatch.setattr(probe.ExperimentConfig, "__post_init__", rewrite_after_parsing)
    with pytest.raises(ValueError, match="input changed"):
        plan(inputs)
    assert not inputs[3].exists()
    assert not (inputs[0] / "autoresearch.lock").exists()


def test_plan_hash_identifies_the_captured_config_and_preserves_nested_settings(inputs):
    data = json.loads(inputs[1].read_text())
    data.update(
        lr=0.001, auxiliary_config={"enabled": False, "weights": {"ridge": 0.3}}
    )
    contents = json.dumps(data).encode()
    inputs[1].write_bytes(contents)
    prepared = plan(inputs)
    assert prepared.input_hashes[str(inputs[1])] == hashlib.sha256(contents).hexdigest()
    assert prepared.config["lr"] == 0.001
    assert prepared.config["auxiliary_config"]["weights"] == {"ridge": 0.3}


@pytest.mark.parametrize("count", [0, 1, 17, True, 2.5])
def test_invalid_run_counts_do_not_create_outputs(inputs, count):
    _, config, checkpoint, output = inputs
    with pytest.raises(ValueError, match="runs"):
        probe.make_plan(config, checkpoint, output, runs=count)
    assert not output.exists()


@pytest.mark.parametrize("timeout", [0, -1, True, float("nan"), float("inf")])
def test_invalid_timeouts_do_not_create_outputs(inputs, timeout):
    with pytest.raises(ValueError, match="timeout"):
        plan(inputs, timeout=timeout)
    assert not inputs[3].exists()


def test_existing_or_source_overlapping_outputs_are_refused(inputs):
    project, config, checkpoint, output = inputs
    output.mkdir()
    with pytest.raises(ValueError, match="exists"):
        plan(inputs)
    output.rmdir()
    with pytest.raises(ValueError, match="separate|overlap"):
        probe.make_plan(config, checkpoint, project / "data/train/new", runs=2)


@pytest.mark.parametrize("tree", ["scripts", "src", "villa"])
def test_output_cannot_be_published_into_source_code(inputs, tree):
    project, config, checkpoint, _ = inputs
    source = probe.VILLA if tree == "villa" else project / tree
    with pytest.raises(ValueError, match="overlap"):
        probe.make_plan(config, checkpoint, source / "new_probe", runs=2)


def test_complete_runs_preserve_loop_files_and_compute_sample_spread(
    inputs, monkeypatch
):
    fake_runner(inputs, monkeypatch)
    project = inputs[0]
    before = {
        name: (project / name).read_bytes()
        for name in ("config.json", "best_model.pt", "run_result.json")
    }
    report = probe.execute(plan(inputs))
    assert report["status"] == "COMPLETE"
    assert report["f1_spread"]["n"] == 2
    assert report["f1_spread"]["mean"] == pytest.approx(0.7)
    assert report["f1_spread"]["sample_std"] == pytest.approx(math.sqrt(0.02))
    assert report["tolerance_calibrated"] is False
    for name, content in before.items():
        assert (project / name).read_bytes() == content
    assert running_pid(project) is None
    assert all(
        (inputs[3] / f"run_{i:02d}" / "run_result.json").exists() for i in (1, 2)
    )
    # Raw reported-only NaNs remain inspectable; the summary is strict JSON.
    json.loads(
        (inputs[3] / "probe.json").read_text(),
        parse_constant=lambda value: pytest.fail(value),
    )


def test_failed_exit_cannot_contribute_emitted_scores(inputs, monkeypatch):
    fake_runner(inputs, monkeypatch, code=7)
    report = probe.execute(plan(inputs))
    assert report["status"] == "FAILED" and report["f1_spread"] is None
    assert len(report["runs"]) == 1 and report["runs"][0]["returncode"] == 7
    assert "metrics" not in report["runs"][0]
    assert "ineligible" in report["runs"][0]["error"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("val_f1", float("nan")),
        ("roc_auc", float("inf")),
        ("val_f1", True),
        ("ap_prevalence_lift", "1.5"),
        ("val_positive_rate", 1),
        ("val_f1_threshold", -0.1),
        ("ap_prevalence_lift", 5),
    ],
)
def test_invalid_scores_cannot_produce_a_spread(inputs, monkeypatch, field, value):
    fake_runner(inputs, monkeypatch, invalid={field: value})
    report = probe.execute(plan(inputs))
    assert report["status"] == "FAILED" and report["f1_spread"] is None
    json.loads(
        (inputs[3] / "probe.json").read_text(),
        parse_constant=lambda value: pytest.fail(value),
    )


@pytest.mark.parametrize(
    "updates",
    [
        {"complete": False},
        {"batch_errors": 1},
        {"usable_patches": 2},
        {"usable_patches": 0},
        {"protocol": "old"},
        {"inputs_sha256": None},  # no record of what the sample was drawn from
    ],
)
def test_incomplete_or_inconsistent_sample_is_not_evidence(tmp_path, updates):
    payload = result()
    payload["validation_diag"].update(updates)
    path = tmp_path / "run_result.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        probe.read_result(path, probe.VALIDATION_PROTOCOL)


@pytest.mark.parametrize("band", [None, [1, 27]])
def test_plan_and_execution_follow_the_config_depth_protocol(inputs, monkeypatch, band):
    config = json.loads(inputs[1].read_text())
    config.update(depth_band=band, num_layers=16)
    inputs[1].write_text(json.dumps(config))
    expected = probe.validation_protocol(band)
    fake_runner(inputs, monkeypatch, protocol=expected)
    prepared = plan(inputs)
    assert prepared.protocol == expected
    report = probe.execute(prepared)
    assert report["status"] == "COMPLETE" and report["protocol"] == expected
    assert all(row["validation_diag"]["protocol"] == expected for row in report["runs"])


@pytest.mark.parametrize(
    "wrong",
    [
        probe.VALIDATION_PROTOCOL,
        probe.validation_protocol([17, 43]),
        "seeded-sample-400-v2+z1-27",  # the ink-only sample, same band
    ],
)
def test_another_depth_protocol_cannot_enter_the_probe_estimate(
    inputs, monkeypatch, wrong
):
    config = json.loads(inputs[1].read_text())
    config.update(depth_band=[1, 27], num_layers=16)
    inputs[1].write_text(json.dumps(config))
    fake_runner(inputs, monkeypatch, protocol=wrong)
    report = probe.execute(plan(inputs))
    assert report["status"] == "FAILED" and report["f1_spread"] is None
    assert len(report["runs"]) == 1


def test_changed_input_refuses_execution_before_launch(inputs):
    prepared = plan(inputs)
    inputs[2].write_bytes(b"changed checkpoint")
    with pytest.raises(ValueError, match="input changed"):
        probe.execute(prepared)
    assert not inputs[3].exists()
    assert running_pid(inputs[0]) is None


def test_active_research_lock_refuses_execution(inputs):
    ready = inputs[0] / "ready"
    code = f"""
import time
from pathlib import Path
from scripts.loop_control import acquire_lock
held = acquire_lock({str(inputs[0] / "autoresearch.lock")!r})
Path({str(ready)!r}).touch()
time.sleep(60)
"""
    holder = subprocess.Popen([sys.executable, "-c", code], cwd=REPO)
    try:
        deadline = time.monotonic() + 5
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready.exists()
        with pytest.raises(ValueError, match="another research process"):
            probe.execute(plan(inputs))
        assert not inputs[3].exists()
    finally:
        holder.terminate()
        holder.wait(timeout=5)


@pytest.mark.skipif(not Path("/proc/self/cwd").exists(), reason="reads /proc")
def test_a_run_no_loop_supervises_refuses_execution(inputs, monkeypatch, orphaned_run):
    """Each trial's time budget assumes the GPU to itself. A run a killed loop
    left training in the checkout gave trials fewer steps, and so inflated the
    spread the probe measures."""
    fake_runner(inputs, monkeypatch)
    run = orphaned_run(inputs[0])
    with pytest.raises(
        ValueError, match=rf"not starting: .* PID {run.pid} \(started"
    ) as refused:
        probe.execute(plan(inputs))
    assert not inputs[3].exists()
    # Released, not just dropped: while `refused` keeps the traceback, and so
    # execute's frame, alive, only its own close can have freed the lock. Taken
    # from another process: POSIX record locks do not exclude their own.
    taken = subprocess.run(
        [
            sys.executable,
            "-c",
            "from scripts.loop_control import acquire_lock; "
            "acquire_lock('autoresearch.lock')",
        ],
        cwd=inputs[0],
        env={**os.environ, "PYTHONPATH": str(REPO)},
    )
    assert taken.returncode == 0, refused.value
    assert run.poll() is None


def test_cli_reports_execution_failure_nonzero(inputs, monkeypatch, capsys):
    fake_runner(inputs, monkeypatch, code=3)
    _, config, checkpoint, output = inputs
    assert (
        probe.main(
            [
                "--config",
                str(config),
                "--checkpoint",
                str(checkpoint),
                "--out",
                str(output),
                "--runs",
                "2",
                "--execute",
            ]
        )
        == 1
    )
    assert json.loads(capsys.readouterr().out)["status"] == "FAILED"


def test_source_change_during_run_invalidates_all_statistics(inputs, monkeypatch):
    fake_runner(
        inputs, monkeypatch, extra=f"Path({str(inputs[1])!r}).write_text('{{}}')\n"
    )
    report = probe.execute(plan(inputs))
    assert report["status"] == "FAILED" and report["f1_spread"] is None
    assert "input changed" in report["input_error"]


def test_changed_sample_prevalence_invalidates_the_repeatability_estimate(
    inputs, monkeypatch
):
    fake_runner(
        inputs,
        monkeypatch,
        extra="if Path.cwd().name.endswith('02'):\n    payload['val_positive_rate'] = 0.5\n    Path('run_result.json').write_text(json.dumps(payload))\n",
    )
    report = probe.execute(plan(inputs))
    assert report["status"] == "FAILED" and report["f1_spread"] is None
    assert "prevalence changed" in report["input_error"]


def test_changed_validation_inputs_invalidate_the_repeatability_estimate(
    inputs, monkeypatch
):
    """Equal counts and prevalence from another label file are another sample."""
    fake_runner(
        inputs,
        monkeypatch,
        extra="payload['validation_diag']['inputs_sha256'] = Path.cwd().name * 4\nPath('run_result.json').write_text(json.dumps(payload))\n",
    )
    report = probe.execute(plan(inputs))
    assert report["status"] == "FAILED" and report["f1_spread"] is None
    assert "inputs" in report["input_error"]


def test_timeout_stops_worker_group_before_publishing_failure(inputs, monkeypatch):
    worker = inputs[0] / "worker.pid"
    extra = (
        "import subprocess, time\n"
        f"child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\nPath({str(worker)!r}).write_text(str(child.pid))\n"
        "time.sleep(60)\n"
    )
    fake_runner(inputs, monkeypatch, extra=extra)
    report = probe.execute(plan(inputs, timeout=1))
    assert report["status"] == "FAILED" and report["f1_spread"] is None
    assert "TimeoutExpired" in report["runs"][0]["error"]
    if worker.exists():
        pid = int(worker.read_text())
        status = Path(f"/proc/{pid}/stat")
        assert not status.exists() or status.read_text().split()[2] == "Z"


def test_interruption_stops_execution_and_keeps_a_failed_report(inputs, monkeypatch):
    monkeypatch.setattr(
        probe.ProcessSupervisor,
        "run",
        lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    report = probe.execute(plan(inputs))
    assert report["status"] == "INTERRUPTED" and report["f1_spread"] is None
    assert running_pid(inputs[0]) is None


@pytest.mark.parametrize("fails", [False, True])
def test_trial_wrapper_delegates_and_restores_private_context(
    inputs, monkeypatch, fails
):
    from scripts import training
    from scripts.training import run_noise_probe as runner, train as real_train
    from vesuvius_autoresearch.core import checkpoint_tools

    workspace = inputs[3]
    config = dict(plan(inputs).config)
    workspace.mkdir()
    config.update(
        checkpoint_out=str(workspace / "candidate.pt"),
        cache_dir=str(workspace / "cache"),
        use_wandb=False,
    )
    path = workspace / "config.json"
    path.write_text(json.dumps(config))
    (workspace / "best_model.pt").write_bytes(b"fixture checkpoint")
    settings = {
        key: config[key]
        for key in (
            "architecture",
            "patch_size",
            "num_layers",
            "base_feat",
            "num_blocks",
            "num_heads",
            "dropout",
            "use_ridges",
            "multi_task_heads",
            "ridge_sigma",
        )
    }
    monkeypatch.setattr(
        checkpoint_tools,
        "load_tool_checkpoint",
        lambda *args: (object(), settings, {"config": config}),
    )
    fake = ModuleType("scripts.training.train")
    fake.SKELETON_HIST_DIR = "original"
    fake.warm_start_mismatch = real_train.warm_start_mismatch
    calls = []

    def train(cfg, *, strict_warm_start=False):
        assert strict_warm_start is True
        assert Path.cwd() == workspace
        assert str(workspace / "skeleton_hists") == fake.SKELETON_HIST_DIR
        assert cfg.checkpoint_out == str(workspace / "candidate.pt")
        calls.append(cfg)
        if fails:
            raise RuntimeError("trial failed")

    fake.train = train
    monkeypatch.setitem(sys.modules, "scripts.training.train", fake)
    monkeypatch.setattr(training, "train", fake, raising=False)
    before = Path.cwd()
    if fails:
        with pytest.raises(RuntimeError, match="trial failed"):
            runner.run(path)
    else:
        runner.run(path)
    assert len(calls) == 1 and Path.cwd() == before
    assert fake.SKELETON_HIST_DIR == "original"


@pytest.mark.parametrize("missing", [None, "use_ridges", "num_blocks", "num_heads"])
def test_real_wrapper_requires_recorded_fields_and_loads_weights_before_optimizer(
    tmp_path, monkeypatch, missing
):
    from dataclasses import asdict

    import torch

    from scripts.training import run_noise_probe as runner, train

    config = probe.ExperimentConfig(
        architecture="resenc_unet",
        patch_size=8,
        num_layers=4,
        base_feat=2,
        uris=["fake/ct.zarr"],
        val_uri="fake_val/ct.zarr",
        unlabeled_uris=[],
        checkpoint_out=str(tmp_path / "candidate.pt"),
        cache_dir=str(tmp_path / "cache"),
    )
    build = train.build_model
    source = build(config, train.build_vconfig(config), "cpu")
    with torch.no_grad():
        for value in source.state_dict().values():
            if value.is_floating_point():
                value.fill_(0.25)
    recorded = asdict(config)
    saved_config = dict(recorded)
    if missing is not None:
        saved_config.pop(missing)
    torch.save(
        {"config": saved_config, "model_state_dict": source.state_dict()},
        tmp_path / "best_model.pt",
    )
    recorded.pop("max_prize_skel_dist")
    path = tmp_path / "config.json"
    path.write_text(json.dumps(recorded))

    class BeforeOptimizer(RuntimeError):
        pass

    target = build(config, train.build_vconfig(config), "cpu")
    validation_attempts = []

    def validation_fixture(cfg):
        validation_attempts.append(True)
        return object()

    monkeypatch.setattr(train, "build_validation_dataset", validation_fixture)
    monkeypatch.setattr(train, "probe_validation_read", lambda dataset: None)
    monkeypatch.setattr(train, "training_label_path", lambda *a: "fake/labels.png")
    monkeypatch.setattr(train, "VesuviusLabeledDataset", lambda *a, **k: object())
    monkeypatch.setattr(train, "shuffled_loader", lambda *a, **k: [])
    monkeypatch.setattr(train, "build_model", lambda *a: target)
    monkeypatch.setattr(train.wandb_tracking, "init_run", lambda *a: None)
    monkeypatch.setattr(train.wandb_tracking, "watch_model", lambda *a: None)
    optimizer_attempts = []

    def stop_before_optimizer(*args, **kwargs):
        optimizer_attempts.append(True)
        assert all(
            torch.equal(value, source.state_dict()[key])
            for key, value in target.state_dict().items()
        )
        raise BeforeOptimizer("no optimizer or training steps executed")

    monkeypatch.setattr(torch.optim, "AdamW", stop_before_optimizer)
    cwd, hist = Path.cwd(), train.SKELETON_HIST_DIR
    if missing is not None:
        with pytest.raises(ValueError, match=missing):
            runner.run(path)
        assert not optimizer_attempts
        assert not validation_attempts
    else:
        with pytest.raises(BeforeOptimizer):
            runner.run(path)
        assert optimizer_attempts == [True]
        assert validation_attempts == [True]
    assert Path.cwd() == cwd and hist == train.SKELETON_HIST_DIR


@pytest.mark.parametrize("damage", ["missing", "shape", "extra", "unreadable"])
def test_required_starting_load_cannot_swallow_bad_weights(tmp_path, damage):
    from dataclasses import asdict

    import torch

    from scripts.training import train

    config = probe.ExperimentConfig(unlabeled_uris=[])
    source = torch.nn.Linear(2, 1)
    state = source.state_dict()
    if damage == "missing":
        state.pop("bias")
    elif damage == "shape":
        state["weight"] = torch.zeros(2, 2)
    elif damage == "extra":
        state["unknown"] = torch.zeros(1)
    path = tmp_path / "checkpoint.pt"
    if damage == "unreadable":
        path.write_bytes(b"not a torch checkpoint")
    else:
        torch.save({"config": asdict(config), "model_state_dict": state}, path)
    expected_error = pickle.UnpicklingError if damage == "unreadable" else RuntimeError
    with pytest.raises(expected_error):
        train.load_required_starting_checkpoint(torch.nn.Linear(2, 1), config, path)


def test_loop_control_can_stop_a_registered_probe_cli(tmp_path):
    from scripts.loop_control import main as control

    script = tmp_path / "f1_noise_probe.py"
    script.write_text(
        "from scripts.loop_control import acquire_lock\nimport time\nheld = acquire_lock('autoresearch.lock')\ntime.sleep(60)\n"
    )
    process = subprocess.Popen(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(REPO)},
    )
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                if running_pid(tmp_path) == process.pid:
                    break
            except RuntimeError:
                pass
            time.sleep(0.01)
        assert running_pid(tmp_path) == process.pid
        assert control(["stop", "--repo", str(tmp_path), "--timeout", "2"]) == 0
        process.wait(timeout=2)
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
