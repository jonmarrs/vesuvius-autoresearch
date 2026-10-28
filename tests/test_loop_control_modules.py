"""Module-launched trainers must block competing work just like script paths."""

import signal
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import loop_control


@pytest.mark.parametrize(
    "prefix",
    [
        ["python", "-m"],
        ["python3.10", "-u", "-m"],
        ["/venv/bin/python", "-Bu", "-m"],
        ["python", "-W", "ignore", "-X", "dev", "-m"],
        ["python", "-Wignore", "-Xdev", "-m"],
        ["python", "--check-hash-based-pycs", "always", "-m"],
        ["python", "-um"],
        ["uv", "run", "python", "-u", "-m"],
        ["uv", "run", "--", "python", "-m"],
    ],
)
def test_python_module_entrypoint_options(prefix):
    module = "scripts.training.train"
    assert loop_control._python_module([*prefix, module, "--config", "x"]) == module


@pytest.mark.parametrize(
    "args",
    [
        ["vim", "-m", "scripts.training.train"],
        ["python", "other.py", "-m", "scripts.training.train"],
        ["python", "--", "-m", "scripts.training.train"],
        ["python", "-c", "pass", "-m", "scripts.training.train"],
        ["python", "-uc", "pass", "-m", "scripts.training.train"],
        ["python", "-W", "-m", "scripts.training.train"],
        ["python", "-X", "-m", "scripts.training.train"],
        ["python", "-m"],
        ["python", "-V", "-m", "scripts.training.train"],
        ["uv", "tool", "run", "python", "-m", "scripts.training.train"],
        ["uv", "run", "other.py", "-m", "scripts.training.train"],
    ],
)
def test_script_arguments_and_non_execution_are_not_module_launches(args):
    assert loop_control._python_module(args) is None


@pytest.mark.skipif(not Path("/proc/self/cwd").exists(), reason="reads /proc")
@pytest.mark.parametrize("module", sorted(loop_control.RUN_MODULES))
@pytest.mark.parametrize("supervised", [False, True])
def test_actual_module_process_is_reported_and_blocks_competing_work(
    tmp_path, module, supervised, capsys
):
    # All modules are harmless sleepers in an isolated fake checkout. Never
    # launch the actual trainer or read its data/checkpoints.
    path = tmp_path.joinpath(*module.split(".")).with_suffix(".py")
    path.parent.mkdir(parents=True)
    parent = path.parent
    while parent != tmp_path:
        (parent / "__init__.py").touch()
        parent = parent.parent
    path.write_text("import time\nprint('ready', flush=True)\ntime.sleep(60)\n")
    config = "config_temp.json" if supervised else "config.json"
    run = subprocess.Popen(
        [sys.executable, "-u", "-m", module, "--config", config],
        cwd=tmp_path,
        start_new_session=supervised,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert run.stdout is not None
        assert run.stdout.readline().strip() == "ready"
        runs = loop_control.unsupervised_runs(tmp_path)
        assert len(runs) == 1 and runs[0][0] == run.pid
        assert runs[0][2] is supervised
        assert f"PID {run.pid}" in loop_control.unsupervised_runs_refusal(tmp_path)
        assert loop_control.main(["status", "--repo", str(tmp_path)]) == 1
        assert f"PID {run.pid}" in capsys.readouterr().out
        # A module-launched orphan gets the same cleanup as a path-launched
        # orphan. Hand-started jobs remain for the operator to stop explicitly.
        assert loop_control.stop_unsupervised_runs(tmp_path, timeout=2)
        if supervised:
            assert run.wait(timeout=2) == -signal.SIGTERM
        else:
            assert run.poll() is None
    finally:
        if run.poll() is None:
            run.kill()
        run.wait(timeout=2)


@pytest.mark.skipif(not Path("/proc/self/cwd").exists(), reason="reads /proc")
def test_module_job_outside_checkout_is_not_reported(tmp_path):
    elsewhere = tmp_path / "other"
    elsewhere.mkdir()
    path = elsewhere / "scripts/training/train.py"
    path.parent.mkdir(parents=True)
    (elsewhere / "scripts/__init__.py").touch()
    (path.parent / "__init__.py").touch()
    path.write_text("import time\nprint('ready', flush=True)\ntime.sleep(60)\n")
    run = subprocess.Popen(
        [sys.executable, "-m", "scripts.training.train"],
        cwd=elsewhere,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert run.stdout is not None
        assert run.stdout.readline().strip() == "ready"
        assert loop_control.unsupervised_runs(tmp_path) == []
    finally:
        run.kill()
        run.wait(timeout=2)
