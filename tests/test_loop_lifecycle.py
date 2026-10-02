import os
import signal
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from run_autoresearch_loop import active_tweaks, template_weights
from scripts.loop_control import main as control_main
from scripts.loop_control import running_pid
from scripts.process_supervisor import ProcessSupervisor
from scripts.training.config import ExperimentConfig

REPO = Path(__file__).resolve().parents[1]


def test_loop_import_is_independent_of_training_runtime():
    code = """
import os, sys
before = dict(os.environ)
import run_autoresearch_loop
assert 'torch' not in sys.modules
assert 'scripts.training.train' not in sys.modules
assert dict(os.environ) == before
"""
    subprocess.run([sys.executable, "-c", code], cwd=REPO, check=True, timeout=10)


def test_config_roundtrip_preserves_nested_settings(tmp_path):
    config = ExperimentConfig(lr=0.0005, use_uamt=True)
    path = tmp_path / "config.json"
    config.save(path)
    assert ExperimentConfig.load(path) == config


def test_noop_and_disabled_tweaks_are_not_sampled():
    config = ExperimentConfig(use_ridges=False, use_uamt=False)
    for template in active_tweaks(config):
        assert getattr(config, template["attr"]) not in template["vals"]
        assert template["attr"] not in {"ridge_sigma", "consistency_weight", "ema_decay"}


def test_family_weight_does_not_depend_on_number_of_axes():
    templates = [{"family": "a"}, {"family": "a"}, {"family": "b"}]
    assert template_weights(templates, defaultdict(lambda: 1, a=4, b=2)) == [2, 2, 2]


def alive(pid):
    try:
        # A dead orphan may remain a zombie until the container's init reaps it.
        return Path(f"/proc/{pid}/stat").read_text().split(") ")[1][0] != "Z"
    except FileNotFoundError:
        return False


@pytest.mark.parametrize("leader_exits", [False, True])
def test_supervisor_reaps_term_resistant_descendants(tmp_path, leader_exits):
    pidfile = tmp_path / "worker.pid"
    worker = (
        "import os,signal,time; from pathlib import Path; "
        "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
        f"Path({str(pidfile)!r}).write_text(str(os.getpid())); time.sleep(60)"
    )
    leader = f"""
import subprocess, sys, time
from pathlib import Path
subprocess.Popen([sys.executable, '-c', {worker!r}])
while not Path({str(pidfile)!r}).exists(): time.sleep(.01)
{'sys.exit(0)' if leader_exits else 'time.sleep(60)'}
"""
    supervisor = ProcessSupervisor(grace_seconds=0.15)
    try:
        if leader_exits:
            assert supervisor.run([sys.executable, "-c", leader], timeout=3).returncode == 0
        else:
            with pytest.raises(subprocess.TimeoutExpired):
                supervisor.run([sys.executable, "-c", leader], timeout=1)
        pid = int(pidfile.read_text())
        deadline = time.monotonic() + 2
        while alive(pid) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not alive(pid)
        assert supervisor.active is None
    finally:
        if pidfile.exists() and alive(int(pidfile.read_text())):
            os.kill(int(pidfile.read_text()), signal.SIGKILL)


def test_stop_targets_lock_owner_with_unbuffered_python(tmp_path):
    script = tmp_path / "run_autoresearch_loop.py"
    script.write_text("""
import time
from scripts.loop_control import acquire_lock
lock = acquire_lock('autoresearch.lock')
while True: time.sleep(.1)
""")
    process = subprocess.Popen(
        [sys.executable, "-u", str(script)], cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(REPO)},
    )
    try:
        deadline = time.monotonic() + 3
        while not (tmp_path / "autoresearch.lock").exists() and time.monotonic() < deadline:
            time.sleep(.01)
        assert running_pid(tmp_path) == process.pid
        # A second acquisition must fail without erasing the live owner's PID.
        duplicate = subprocess.run(
            [sys.executable, "-c", "from scripts.loop_control import acquire_lock; acquire_lock('autoresearch.lock')"],
            cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(REPO)}, capture_output=True,
        )
        assert duplicate.returncode != 0
        assert running_pid(tmp_path) == process.pid
        assert control_main(["stop", "--repo", str(tmp_path), "--timeout", "2"]) == 0
        process.wait(timeout=2)
        assert (tmp_path / ".loop_paused").exists()
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()


def test_stop_pauses_watchdog_even_without_a_running_loop(tmp_path):
    assert control_main(["stop", "--repo", str(tmp_path)]) == 0
    assert (tmp_path / ".loop_paused").exists()


def test_failed_training_cannot_promote_a_success_result(tmp_path, monkeypatch):
    import json
    import run_autoresearch_loop as loop

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(loop, "__file__", str(tmp_path / "run_autoresearch_loop.py"))
    monkeypatch.setattr(loop.signal, "signal", lambda *args: None)
    monkeypatch.setattr(loop.time, "sleep", lambda *args: None)
    hours = iter([12, 12, 20])  # one day cycle, then end the shift
    monkeypatch.setattr(loop.time, "localtime", lambda: SimpleNamespace(tm_hour=next(hours)))
    monkeypatch.setattr(loop, "tweak_templates", [{"family": "lr", "attr": "lr", "vals": [0.002]}])
    config = ExperimentConfig()
    config.save(tmp_path / "config.json")

    class FakeSupervisor:
        def run(self, command, **kwargs):
            if "--smoke" in command:
                return subprocess.CompletedProcess(command, 0)
            (tmp_path / "run_result.json").write_text(json.dumps({"is_success": True, "val_f1": 1}))
            return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(loop, "supervisor", FakeSupervisor())
    monkeypatch.setattr(loop.os, "system", lambda command: pytest.fail("failed cycle attempted a commit"))
    loop.main()
    assert ExperimentConfig.load(tmp_path / "config.json") == config
    assert not (tmp_path / "config_temp.json").exists()
    assert "CRASHED" in next((tmp_path / "sprint_logs").glob("*.md")).read_text()
    assert json.loads((tmp_path / "autoresearch_history.json").read_text())["lr"] == 1
