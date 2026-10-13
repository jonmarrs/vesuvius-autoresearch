import os
import signal
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from run_autoresearch_loop import (
    VRAM_COMPLEXITY_CAP,
    active_tweaks,
    complexity_score,
    template_weights,
    vram_exclusions,
)
from scripts.loop_control import main as control_main, running_pid
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
        assert template["attr"] not in {
            "ridge_sigma",
            "consistency_weight",
            "ema_decay",
        }


def production_like(**overrides):
    # config.json's structure: batch 4, num_layers 16, base_feat 64, patch 64.
    fields = {"batch_size": 4, "num_layers": 16, "base_feat": 64, "num_blocks": 16}
    return ExperimentConfig(**{**fields, **overrides})


def test_reference_config_scores_one():
    assert complexity_score(ExperimentConfig()) == pytest.approx(1.0)
    assert complexity_score(production_like()) == pytest.approx(1 / 3)


def test_values_over_the_vram_cap_are_never_proposed():
    """batch_size 24 scores 2.0 here. It used to be sampled, then skipped after it
    had taken a cycle number, a recent_configs slot and a decay step."""
    config = production_like()
    batch = {t["attr"]: t["vals"] for t in active_tweaks(config)}["batch_size"]
    assert batch == [8, 16]
    assert vram_exclusions(config) == [("batch_size", 24, pytest.approx(2.0))]
    for template in active_tweaks(config):
        for val in template["vals"]:
            candidate = production_like()
            setattr(candidate, template["attr"], val)
            assert complexity_score(candidate) <= VRAM_COMPLEXITY_CAP


def test_baseline_over_the_cap_still_tweaks_axes_that_do_not_raise_it():
    config = production_like(batch_size=24)
    active = {t["attr"]: t["vals"] for t in active_tweaks(config)}
    assert active["lr"] and active["weight_decay"]
    assert active["batch_size"] == [8, 16]
    assert vram_exclusions(config) == []


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
{"sys.exit(0)" if leader_exits else "time.sleep(60)"}
"""
    supervisor = ProcessSupervisor(grace_seconds=0.15)
    try:
        if leader_exits:
            assert (
                supervisor.run([sys.executable, "-c", leader], timeout=3).returncode
                == 0
            )
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
        [sys.executable, "-u", str(script)],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(REPO)},
    )
    try:
        # open('a+') creates the file before the child acquires and populates
        # its lock. File existence is not a readiness acknowledgement.
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and process.poll() is None:
            try:
                if running_pid(tmp_path) == process.pid:
                    break
            except RuntimeError as exc:
                if str(exc) != "loop lock is held but contains no valid PID":
                    raise
            time.sleep(0.01)
        assert running_pid(tmp_path) == process.pid
        # A second acquisition must fail without erasing the live owner's PID.
        duplicate = subprocess.run(
            [
                sys.executable,
                "-c",
                "from scripts.loop_control import acquire_lock; acquire_lock('autoresearch.lock')",
            ],
            cwd=tmp_path,
            env={**os.environ, "PYTHONPATH": str(REPO)},
            capture_output=True,
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
    monkeypatch.setattr(
        loop.time, "localtime", lambda: SimpleNamespace(tm_hour=next(hours))
    )
    monkeypatch.setattr(
        loop, "tweak_templates", [{"family": "lr", "attr": "lr", "vals": [0.002]}]
    )
    config = ExperimentConfig()
    config.save(tmp_path / "config.json")

    class FakeSupervisor:
        def run(self, command, **kwargs):
            if "--smoke" in command:
                return subprocess.CompletedProcess(command, 0)
            (tmp_path / "run_result.json").write_text(
                json.dumps({"is_success": True, "val_f1": 1})
            )
            return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(loop, "supervisor", FakeSupervisor())
    monkeypatch.setattr(
        loop.os,
        "system",
        lambda command: pytest.fail("failed cycle attempted a commit"),
    )
    loop.main()
    assert ExperimentConfig.load(tmp_path / "config.json") == config
    assert not (tmp_path / "config_temp.json").exists()
    assert "CRASHED" in next((tmp_path / "sprint_logs").glob("*.md")).read_text()
    assert json.loads((tmp_path / "autoresearch_history.json").read_text())["lr"] == 1


LOOP_RUNTIME_STATE = (
    "autoresearch.lock",
    ".current_day_shift_log",
    ".loop_paused",
    "autoresearch.out",
    "config_temp.json",
    "run_result.json",
)


def test_loop_runtime_state_is_never_tracked():
    """Ownership is an fcntl lock on the lock file's inode. While it was tracked, a
    running loop left it modified, and `git checkout -- .`, `git stash` or
    `git restore .` replaced the file: the lock stayed on the orphaned inode, a
    second loop acquired the new file, and stop.sh could no longer find the first.
    Process state therefore lives outside version control."""
    if not (REPO / ".git").exists():
        pytest.skip("not a git checkout")

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(REPO), *args], capture_output=True, timeout=10
        ).returncode

    tracked = [
        p for p in LOOP_RUNTIME_STATE if git("ls-files", "--error-unmatch", p) == 0
    ]
    unignored = [
        p for p in LOOP_RUNTIME_STATE if git("check-ignore", "-q", "--no-index", p)
    ]
    assert not tracked, f"runtime state tracked by git: {tracked}"
    assert not unignored, f"runtime state not ignored by git: {unignored}"
