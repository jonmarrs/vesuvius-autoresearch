import fnmatch
import os
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from run_autoresearch_loop import (
    VRAM_COMPLEXITY_CAP,
    complexity_score,
    template_weights,
    tweak_proposals,
)
from scripts.loop_control import main as control_main, running_pid
from scripts.process_supervisor import ProcessSupervisor, stops_interrupt
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
    for template in tweak_proposals(config)[0]:
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
    active, excluded = tweak_proposals(config)
    assert {t["attr"]: t["vals"] for t in active}["batch_size"] == [8, 16]
    assert excluded == [("batch_size", 24, pytest.approx(2.0))]
    for template in active:
        for val in template["vals"]:
            candidate = production_like()
            setattr(candidate, template["attr"], val)
            assert complexity_score(candidate) <= VRAM_COMPLEXITY_CAP


def test_a_baseline_over_the_cap_is_offered_only_tweaks_that_bring_it_under():
    config = production_like(batch_size=24)
    active, excluded = tweak_proposals(config)
    assert {t["attr"]: t["vals"] for t in active} == {"batch_size": [8, 16]}
    assert ("lr", 1e-4, pytest.approx(2.0)) in excluded


def test_the_cap_is_read_when_called_not_when_defined(monkeypatch):
    import run_autoresearch_loop as loop

    monkeypatch.setattr(loop, "VRAM_COMPLEXITY_CAP", 2.5)
    batch = {t["attr"]: t["vals"] for t in tweak_proposals(production_like())[0]}
    assert batch["batch_size"] == [8, 16, 24]


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


def _stop_twice_as_the_loop_does(supervisor, command, signal_times, on_stop):
    """Run command under supervisor and deliver SIGUSR1 at signal_times, handled
    as the loop's signal_handler handles a stop: stop the run, act on its files
    (on_stop), exit."""

    def handler(sig, frame):
        supervisor.stop()
        on_stop()
        raise SystemExit(0)

    previous = signal.signal(signal.SIGUSR1, handler)
    timers = [
        threading.Timer(t, os.kill, (os.getpid(), signal.SIGUSR1)) for t in signal_times
    ]
    try:
        for timer in timers:
            timer.start()
        with pytest.raises(SystemExit):
            supervisor.run(command, timeout=30)
    finally:
        for timer in timers:
            timer.cancel()
            timer.join()  # none may fire once SIGUSR1's default (exit) is back
        signal.signal(signal.SIGUSR1, previous)


def test_a_second_stop_kills_the_run_before_the_loop_settles(tmp_path):
    """stop.sh twice, or Ctrl-C twice: the second handler's stop() returned at
    once with the run alive, the loop settled best_model.pt, and the exit cut the
    first stop short before its SIGKILL. A run ignoring SIGTERM then replaced
    best_model.pt after the settle, and outlived the loop."""
    pidfile, written = tmp_path / "leader.pid", tmp_path / "best_model.pt"
    leader = (
        "import os,signal,time; from pathlib import Path; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        f"Path({str(pidfile)!r}).write_text(str(os.getpid())); time.sleep(2.0); "
        f"Path({str(written)!r}).write_text('run'); time.sleep(60)"
    )
    supervisor = ProcessSupervisor(grace_seconds=3)
    alive_at_settle = []
    try:
        _stop_twice_as_the_loop_does(
            supervisor,
            [sys.executable, "-c", leader],
            (0.7, 1.0),
            lambda: alive_at_settle.append(alive(int(pidfile.read_text()))),
        )
        assert alive_at_settle == [False]
        time.sleep(1.5)  # past the moment the run would have written
        assert not written.exists()
        assert supervisor.active is None and supervisor.stopping is None
    finally:
        if pidfile.exists() and alive(int(pidfile.read_text())):
            os.kill(int(pidfile.read_text()), signal.SIGKILL)


def test_a_stop_during_the_runs_clean_up_still_kills_its_survivors(tmp_path):
    """After the leader exits, run() stops what is left of its group, waiting up
    to the grace period. A stop then found nothing active, and the handler's
    exit cut the clean-up short before its SIGKILL: a worker ignoring SIGTERM
    outlived the loop, holding the GPU."""
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
"""
    supervisor = ProcessSupervisor(grace_seconds=3)
    landed = []
    try:
        _stop_twice_as_the_loop_does(
            supervisor,
            [sys.executable, "-c", leader],
            (1.5,),
            lambda: landed.append(supervisor.stopping is not None),
        )
        assert landed == [True]  # during run()'s clean-up, not before it
        pid = int(pidfile.read_text())
        deadline = time.monotonic() + 2
        while alive(pid) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not alive(pid)
    finally:
        if pidfile.exists() and alive(int(pidfile.read_text())):
            os.kill(int(pidfile.read_text()), signal.SIGKILL)


def test_a_second_interrupt_during_the_stop_kills_the_group(tmp_path):
    """The noise probe and the ablation turn SIGTERM into KeyboardInterrupt and
    call no stop() from the handler: a second one landing inside run()'s stop
    used to skip its SIGKILL, leaving a run that ignores SIGTERM alive."""
    pidfile = tmp_path / "leader.pid"
    leader = (
        "import os,signal,time; from pathlib import Path; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        f"Path({str(pidfile)!r}).write_text(str(os.getpid())); time.sleep(60)"
    )
    supervisor = ProcessSupervisor(grace_seconds=3)
    in_stop = []

    def interrupt(sig, frame):
        in_stop.append(supervisor.active is None)
        raise KeyboardInterrupt

    previous = signal.signal(signal.SIGUSR1, interrupt)
    timers = [
        threading.Timer(t, os.kill, (os.getpid(), signal.SIGUSR1)) for t in (0.5, 1.2)
    ]
    try:
        for timer in timers:
            timer.start()
        with pytest.raises(KeyboardInterrupt):
            supervisor.run([sys.executable, "-c", leader], timeout=30)
        assert in_stop == [False, True]  # the second one landed inside stop()
        assert not alive(int(pidfile.read_text()))
        assert supervisor.active is None and supervisor.stopping is None
    finally:
        for timer in timers:
            timer.cancel()
            timer.join()
        signal.signal(signal.SIGUSR1, previous)
        if pidfile.exists() and alive(int(pidfile.read_text())):
            os.kill(int(pidfile.read_text()), signal.SIGKILL)


@pytest.mark.parametrize("sig", [signal.SIGTERM, signal.SIGHUP])
def test_a_stop_or_a_closed_terminal_interrupts_supervised_work(sig):
    """By default SIGTERM (./stop.sh) and SIGHUP (a dropped ssh session) end a
    command at once, before its clean-up, leaving its supervised group running
    and, for the lock holders, releasing the lock with that group still at work."""

    def before(*args):
        raise AssertionError("reached the previous handler")

    previous = signal.signal(sig, before)
    try:
        with pytest.raises(KeyboardInterrupt):
            with stops_interrupt():
                os.kill(os.getpid(), sig)
                time.sleep(1)
        assert signal.getsignal(sig) is before
    finally:
        signal.signal(sig, previous)


def test_an_ignored_hangup_stays_ignored_and_threads_change_nothing():
    """nohup ignores SIGHUP, and that must hold; Python installs handlers only
    in the main thread, so elsewhere the guard does nothing rather than raise."""
    previous = signal.signal(signal.SIGHUP, signal.SIG_IGN)
    try:
        with stops_interrupt():
            assert signal.getsignal(signal.SIGHUP) is signal.SIG_IGN
            os.kill(os.getpid(), signal.SIGHUP)  # ignored
            time.sleep(0.1)
        assert signal.getsignal(signal.SIGHUP) is signal.SIG_IGN
    finally:
        signal.signal(signal.SIGHUP, previous)
    seen = []

    def in_a_thread():
        with stops_interrupt():
            seen.append(signal.getsignal(signal.SIGTERM))

    term = signal.getsignal(signal.SIGTERM)
    worker = threading.Thread(target=in_a_thread)
    worker.start()
    worker.join()
    assert seen == [term]


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


def _fake_run(directory, script, config, leader):
    """A process that looks to /proc like a training run working in directory;
    leader: started in a session of its own, as a supervisor starts its runs."""
    path = directory / script
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("import time\ntime.sleep(120)\n")
    run = subprocess.Popen(
        [sys.executable, "-u", script, "--config", config],
        cwd=directory,
        start_new_session=leader,
    )
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            if script.encode() in Path(f"/proc/{run.pid}/cmdline").read_bytes():
                break
        except FileNotFoundError:
            pass
        time.sleep(0.02)
    return run


@pytest.mark.skipif(not Path("/proc/self/cwd").exists(), reason="reads /proc")
def test_stop_ends_what_a_killed_loop_or_ablation_left_running(tmp_path, capsys):
    """A loop or ablation killed without its handler leaves its run going in a
    session of its own. stop.sh said "No autoresearch work running" and left it;
    it now stops such runs (whole group) and names one started by hand."""
    runs = []
    try:
        runs.append(
            _fake_run(tmp_path, "scripts/training/train.py", "config_temp.json", True)
        )
        runs.append(
            _fake_run(
                tmp_path,
                "scripts/train_with_new_augs.py",
                "config_temp_ablation_baseline_seed0.json",
                True,
            )
        )
        runs.append(
            _fake_run(tmp_path, "scripts/training/train.py", "config.json", False)
        )
        assert control_main(["status", "--repo", str(tmp_path)]) == 1
        status = capsys.readouterr().out
        assert all(f"PID {run.pid} (" in status for run in runs)
        assert control_main(["stop", "--repo", str(tmp_path), "--timeout", "5"]) == 0
        out = capsys.readouterr().out
        assert runs[0].wait(timeout=5) == -signal.SIGTERM
        assert runs[1].wait(timeout=5) == -signal.SIGTERM
        assert runs[2].poll() is None  # started by hand: named, not stopped
        assert f"not stopping: PID {runs[2].pid} (started by hand" in out
        assert "No autoresearch work running. Watchdog paused." in out
        assert (tmp_path / ".loop_paused").exists()
    finally:
        for run in runs:
            run.kill()
            run.wait()


@pytest.mark.skipif(not Path("/proc/self/cwd").exists(), reason="reads /proc")
def test_status_does_not_count_the_running_loops_own_run(tmp_path, capsys):
    holder = tmp_path / "run_autoresearch_loop.py"
    holder.write_text(
        "import subprocess, sys, time\n"
        "from scripts.loop_control import acquire_lock\n"
        "lock = acquire_lock('autoresearch.lock')\n"
        "run = subprocess.Popen([sys.executable, '-u', 'scripts/training/train.py',"
        " '--config', 'config_temp.json'], start_new_session=True)\n"
        "print(run.pid, flush=True)\n"
        "time.sleep(120)\n"
    )
    script = tmp_path / "scripts" / "training" / "train.py"
    script.parent.mkdir(parents=True)
    script.write_text("import time\ntime.sleep(120)\n")
    loop = subprocess.Popen(
        [sys.executable, "-u", str(holder)],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(REPO)},
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert loop.stdout is not None
        run_pid = int(loop.stdout.readline())
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if b"train.py" in Path(f"/proc/{run_pid}/cmdline").read_bytes():
                break
            time.sleep(0.02)
        assert control_main(["status", "--repo", str(tmp_path)]) == 0
        out = capsys.readouterr().out
        assert f"(PID {loop.pid})" in out and "Unsupervised" not in out
    finally:
        loop.kill()
        loop.wait()
        try:
            os.killpg(run_pid, signal.SIGKILL)
        except (ProcessLookupError, UnboundLocalError):
            pass


def _run_as_uv_starts_it(directory):
    """A supervisor's run as `uv run python -u scripts/training/train.py --config
    config_temp.json` makes it: the session leader (uv) and its python child,
    the script and config among both their arguments. Returns (leader, child PID)."""
    script = directory / "scripts" / "training" / "train.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(
        "import os, subprocess, sys, time\n"
        "if 'RUN_CHILD' not in os.environ:\n"
        "    child = subprocess.Popen([sys.executable, *sys.argv],"
        " env={**os.environ, 'RUN_CHILD': '1'})\n"
        "    print(child.pid, flush=True)\n"
        "time.sleep(120)\n"
    )
    leader = subprocess.Popen(
        [
            sys.executable,
            "-u",
            "scripts/training/train.py",
            "--config",
            "config_temp.json",
        ],
        cwd=directory,
        start_new_session=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    assert leader.stdout is not None
    child = int(leader.stdout.readline())
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if b"train.py" in Path(f"/proc/{child}/cmdline").read_bytes():
            break
        time.sleep(0.02)
    return leader, child


def _gone(pid, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
        except FileNotFoundError:
            return True
        if state == "Z":
            return True
        time.sleep(0.02)
    return False


@pytest.mark.skipif(not Path("/proc/self/cwd").exists(), reason="reads /proc")
def test_a_runs_python_child_is_that_run_not_one_started_by_hand(tmp_path, capsys):
    """uv's python child carries the run's arguments too. It was reported as a
    second run "started by hand", "not stopping", and then stopped with its group."""
    leader, child = _run_as_uv_starts_it(tmp_path)
    try:
        assert control_main(["status", "--repo", str(tmp_path)]) == 1
        status = capsys.readouterr().out
        assert f"PID {leader.pid} (started by a loop or ablation" in status
        assert f"PID {child} (" not in status
        assert control_main(["stop", "--repo", str(tmp_path), "--timeout", "5"]) == 0
        out = capsys.readouterr().out
        assert f"stopping: PID {leader.pid} (started by a loop or ablation" in out
        assert "started by hand" not in out and f"PID {child} (" not in out
        assert leader.wait(timeout=5) == -signal.SIGTERM
        assert _gone(child)
    finally:
        try:
            os.killpg(leader.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        leader.wait()


@pytest.mark.skipif(not Path("/proc/self/cwd").exists(), reason="reads /proc")
def test_a_run_whose_session_leader_died_is_still_seen(tmp_path, capsys):
    """uv killed alone leaves its python child training; the child's session
    leader is gone. Main's check saw such a run, so the loop did not start."""
    leader, child = _run_as_uv_starts_it(tmp_path)
    try:
        leader.kill()
        leader.wait()
        assert control_main(["status", "--repo", str(tmp_path)]) == 1
        assert f"PID {child} (" in capsys.readouterr().out
    finally:
        try:
            os.kill(child, signal.SIGKILL)
        except ProcessLookupError:
            pass
        _gone(child)


def _checkout_with_start_sh(directory):
    """start.sh and loop_control.py in a checkout of their own, with a `uv` on
    PATH that launches nothing; returns a function that runs start.sh."""
    (directory / "scripts").mkdir()
    shutil.copy(REPO / "start.sh", directory / "start.sh")
    shutil.copy(REPO / "scripts" / "loop_control.py", directory / "scripts")
    fake = directory / "bin"
    fake.mkdir()
    (fake / "uv").write_text("#!/bin/sh\nexit 0\n")
    (fake / "uv").chmod(0o755)
    env = {**os.environ, "PATH": f"{fake}{os.pathsep}{os.environ['PATH']}"}

    def start():
        return subprocess.run(
            ["bash", str(directory / "start.sh")],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    return start


@pytest.mark.skipif(not Path("/proc/self/cwd").exists(), reason="reads /proc")
def test_start_sh_says_the_loop_will_not_start_beside_an_orphaned_run(
    tmp_path, orphaned_run
):
    """start.sh printed the run `status` listed, then "Autoresearch launcher
    started"; the loop it launched refused at once, which only autoresearch.out
    recorded."""
    start = _checkout_with_start_sh(tmp_path)
    alone = start()
    assert alone.returncode == 0, alone.stderr
    assert "launcher started" in alone.stdout
    assert "without starting a cycle" not in alone.stdout
    run = orphaned_run(tmp_path)
    beside = start()
    assert beside.returncode == 0, beside.stderr
    said = " ".join(beside.stdout.split())  # the note is wrapped
    assert f"PID {run.pid} (started by a loop or ablation" in said
    assert "The loop just launched exits without starting a cycle" in said
    assert "./stop.sh stops the runs a loop or ablation started" in said
    assert "otherwise run ./start.sh again" in said


# What an unidentified holder left in the lock, as hex: "x"; "²", which isdigit()
# takes and int() refuses; bytes that are not UTF-8. The last two ended status in
# a traceback, whose exit 1 start.sh read as nothing running, and launched.
_UNREADABLE_LOCKS = {"unidentified": "78", "superscript two": "c2b2", "not UTF-8": "ff"}


@pytest.mark.parametrize("holder", ["the loop", *_UNREADABLE_LOCKS])
def test_start_sh_keeps_its_exit_codes(tmp_path, holder):
    """Work running: exit 1, as before; a lock status cannot read: its exit 2.
    Neither launches anything."""
    start = _checkout_with_start_sh(tmp_path)
    script = tmp_path / "run_autoresearch_loop.py"
    script.write_text(
        "import fcntl, os, sys, time\n"
        "lock = open('autoresearch.lock', 'wb')\n"
        "fcntl.lockf(lock, fcntl.LOCK_EX)\n"
        "lock.write(bytes.fromhex(sys.argv[1]) if len(sys.argv) > 1\n"
        "           else str(os.getpid()).encode())\n"
        "lock.flush()\n"
        "print('ready', flush=True)\n"
        "time.sleep(60)\n"
    )
    args = [sys.executable, str(script)] + (
        [_UNREADABLE_LOCKS[holder]] if holder in _UNREADABLE_LOCKS else []
    )
    work = subprocess.Popen(args, cwd=tmp_path, stdout=subprocess.PIPE, text=True)
    try:
        assert work.stdout is not None and work.stdout.readline() == "ready\n"
        result = start()
    finally:
        work.kill()
        work.wait()
    if holder == "the loop":
        assert result.returncode == 1
        assert f"Autoresearch work is running (PID {work.pid})" in result.stdout
    else:
        assert result.returncode == 2
        assert "contains no valid PID" in result.stderr
    assert not (tmp_path / "autoresearch.out").exists()  # nothing launched


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
        loop,
        "commit_promotion",
        lambda message: pytest.fail("failed cycle attempted a commit"),
    )
    loop.main()
    assert ExperimentConfig.load(tmp_path / "config.json") == config
    assert not (tmp_path / "config_temp.json").exists()
    assert "CRASHED" in next((tmp_path / "sprint_logs").glob("*.md")).read_text()
    assert json.loads((tmp_path / "autoresearch_history.json").read_text())["lr"] == 1


LOOP_RUNTIME_STATE = (
    "autoresearch.lock",
    ".best_model.pt.held",
    ".current_day_shift_log",
    ".loop_paused",
    "autoresearch.out",
    "watchdog.log",
    "run.log",
    "config_temp.json",
    "run_result.json",
    "cycles.jsonl",
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


def test_make_clean_keeps_the_loops_records():
    """`make clean` deleted run.log as a transient stdout log. It is the cycles' training output, git-ignored and on
    the loop's machine only: the epoch-boundary and cycle-length measurements read each cycle's steps from it, and a
    running cycle writes it. Nor may `make clean` or `make clean-cache` take the loop's other state or records.
    Checked on what make would run, so continuation lines, variables and comments are as make reads them; any
    command but `rm -f` or `find .` fails."""
    if shutil.which("make") is None:
        pytest.skip("make is not installed")
    out = subprocess.run(
        ["make", "-n", "-s", "-C", str(REPO), "clean", "clean-cache"],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    ).stdout
    kept = (*LOOP_RUNTIME_STATE, "run.log.old", "sprint_logs", "results.tsv")

    def removes(word, name):  # the name, by glob, or anything under it
        word = word.removeprefix(f"{REPO}/").removeprefix("./").rstrip("/")
        return fnmatch.fnmatch(name, word) or fnmatch.fnmatch(name, word.split("/")[0])

    lines = out.replace("\\\n", " ").splitlines()
    commands = [words for words in map(shlex.split, lines) if words]
    assert commands
    for words in commands:
        assert words[:2] in (["rm", "-f"], ["find", "."]), words
        if words[0] == "rm":
            targets = words[2:]
        else:  # find . ... -name <pattern>: what it matches, by base name
            targets = [
                w for a, w in zip(words, words[1:], strict=False) if a == "-name"
            ]
        assert not [(w, k) for w in targets for k in kept if removes(w, k)], words


def _one_day_cycle(tmp_path, monkeypatch, returncode, result):
    """Run the loop for one day cycle of lr=0.002 whose training exits returncode after writing result."""
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
    ExperimentConfig().save(tmp_path / "config.json")

    class FakeSupervisor:
        def run(self, command, **kwargs):
            if "--smoke" in command:
                return subprocess.CompletedProcess(command, 0)
            (tmp_path / "run_result.json").write_text(json.dumps(result))
            return subprocess.CompletedProcess(command, returncode)

    monkeypatch.setattr(loop, "supervisor", FakeSupervisor())
    monkeypatch.setattr(loop, "commit_promotion", lambda message: True)
    loop.main()
    lines = (tmp_path / loop.CYCLES_FILE).read_text().splitlines()
    return [json.loads(line) for line in lines]


@pytest.mark.parametrize("returncode", [0, 1])
def test_every_cycle_is_recorded_with_its_tweak_code_and_result(
    tmp_path, monkeypatch, returncode
):
    """Analyses joined the sprint logs to run.log by val_f1 to get a cycle's AUC and lift, and run.log rotates
    at 10 MB (reports/loop_tweak_replication_2026-10-25.md). cycles.jsonl keeps one line per cycle instead."""
    result = {"is_success": False, "val_f1": 0.27, "roc_auc": 0.59, "steps": 980}
    (record,) = _one_day_cycle(tmp_path, monkeypatch, returncode, result)
    log = next((tmp_path / "sprint_logs").glob("*.md"))
    assert record["sprint_log"] == str(Path("sprint_logs") / log.name)
    assert (record["cycle"], record["shift"]) == (1, "DAY SHIFT")
    assert (record["tweak"], record["family"], record["attr"], record["value"]) == (
        "lr_0.002",
        "lr",
        "lr",
        0.002,
    )
    assert record["budget_s"] == 900
    assert record["started"] <= record["logged"]
    assert len(record["started"]) == 19 and record["started"][10] == "T"
    assert (
        record["commit"] is None and record["code_changes"] is None
    )  # not a git checkout
    if returncode == 0:
        assert record["status"] == "REVERTED" and record["failure"] is None
        assert record["result"] == result
    else:
        assert record["status"] == "CRASHED"
        assert record["failure"] == "exited with code 1 after writing run_result.json"
        assert record["result"] is None  # a crash's result is not read
    assert f"## Cycle 1: lr_0.002 ({record['status']})" in log.read_text()


def test_code_state_names_the_commit_and_changes_to_what_a_cycle_runs(
    tmp_path, monkeypatch
):
    import run_autoresearch_loop as loop

    def git(*args, cwd=tmp_path):
        return subprocess.run(
            ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    villa = tmp_path / "villa"  # committed as a gitlink, as the submodule is
    villa.mkdir()
    git("init", "-q", cwd=villa)
    (villa / "aug.py").write_text("a = 1\n")
    git("add", ".", cwd=villa)
    git("commit", "-q", "-m", "v", cwd=villa)
    git("init", "-q")
    (tmp_path / "scripts/training").mkdir(parents=True)
    (tmp_path / "scripts/training/train.py").write_text("a = 1\n")
    (tmp_path / "notes.md").write_text("x\n")
    git("add", ".")
    git("commit", "-q", "-m", "c")
    monkeypatch.chdir(tmp_path)
    assert loop.code_state() == (git("rev-parse", "HEAD"), [])
    (villa / "weights.ckpt").write_text("")  # untracked inside villa: not its code
    (tmp_path / "notes.md").write_text("y\n")  # not what a cycle runs
    assert loop.code_state() == (git("rev-parse", "HEAD"), [])
    (tmp_path / "scripts/training/train.py").write_text("a = 2\n")
    (tmp_path / "uv.lock").write_text("")
    (villa / "aug.py").write_text("a = 2\n")
    commit, changes = loop.code_state()
    assert commit == git("rev-parse", "HEAD")
    assert changes == [" M scripts/training/train.py", " M villa", "?? uv.lock"]


def test_a_record_that_cannot_be_written_does_not_stop_the_loop(tmp_path, capsys):
    import run_autoresearch_loop as loop

    loop.append_cycle_record({"cycle": 1}, path=str(tmp_path / "missing" / "c.jsonl"))
    assert "could not append this cycle" in capsys.readouterr().out
    loop.append_cycle_record(
        {"cycle": 1, "value": {1, 2}}, path=str(tmp_path / "c.jsonl")
    )
    assert (tmp_path / "c.jsonl").read_text() == '{"cycle": 1, "value": "{1, 2}"}\n'
