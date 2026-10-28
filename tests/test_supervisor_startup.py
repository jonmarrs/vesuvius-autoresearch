"""Interrupting Popen must not leave an unregistered research process alive."""

import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import process_supervisor as module


def alive(process):
    return process.poll() is None


@pytest.mark.parametrize("sig", [signal.SIGTERM, signal.SIGHUP, signal.SIGINT])
def test_interrupt_between_spawn_and_registration_cleans_child(monkeypatch, sig):
    original = subprocess.Popen
    children = []
    supervisor = module.ProcessSupervisor(grace_seconds=0.1)

    def start_then_interrupt(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        assert child.stdout.readline().strip() == "ready"
        os.kill(os.getpid(), sig)
        return child

    monkeypatch.setattr(module.subprocess, "Popen", start_then_interrupt)
    try:
        with module.stops_interrupt():
            previous = {
                s: signal.getsignal(s) for s in (*module.STOP_SIGNALS, signal.SIGINT)
            }
            with pytest.raises(KeyboardInterrupt):
                supervisor.run(
                    [
                        sys.executable,
                        "-c",
                        "import time; print('ready', flush=True); time.sleep(60)",
                    ],
                    timeout=5,
                    stdout=subprocess.PIPE,
                    text=True,
                )
            assert {s: signal.getsignal(s) for s in previous} == previous
        assert not alive(children[0])
        assert supervisor.active is None and supervisor.stopping is None
    finally:
        for child in children:
            if alive(child):
                os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=3)


def test_loop_style_handler_sees_registered_child_before_settling(monkeypatch):
    original = subprocess.Popen
    children, observations = [], []
    supervisor = module.ProcessSupervisor(grace_seconds=0.1)

    def stop_and_settle(sig, frame):
        supervisor.stop()
        observations.append(all(not alive(child) for child in children))
        raise SystemExit(0)

    def start_then_interrupt(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        os.kill(os.getpid(), signal.SIGTERM)
        return child

    monkeypatch.setattr(module.subprocess, "Popen", start_then_interrupt)
    previous = signal.signal(signal.SIGTERM, stop_and_settle)
    try:
        with pytest.raises(SystemExit):
            supervisor.run(
                [sys.executable, "-c", "import time; time.sleep(60)"], timeout=5
            )
        assert observations == [True]
        assert signal.getsignal(signal.SIGTERM) is stop_and_settle
    finally:
        signal.signal(signal.SIGTERM, previous)
        for child in children:
            if alive(child):
                os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=3)


def test_spawn_failure_restores_handlers_and_supervisor_can_be_reused(tmp_path):
    supervisor = module.ProcessSupervisor(grace_seconds=0.1)
    with module.stops_interrupt():
        previous = {
            s: signal.getsignal(s) for s in (*module.STOP_SIGNALS, signal.SIGINT)
        }
        with pytest.raises(FileNotFoundError):
            supervisor.run([str(tmp_path / "missing-executable")], timeout=1)
        assert {s: signal.getsignal(s) for s in previous} == previous
    assert supervisor.active is None
    assert supervisor.run([sys.executable, "-c", "pass"], timeout=3).returncode == 0


def test_returning_handler_receives_registered_worker_and_keeps_running(monkeypatch):
    original = subprocess.Popen
    supervisor = module.ProcessSupervisor(grace_seconds=0.1)
    observed = []

    def handler(sig, frame):
        observed.append(supervisor.active.pid if supervisor.active else None)

    def spawn(*args, **kwargs):
        child = original(*args, **kwargs)
        os.kill(os.getpid(), signal.SIGTERM)
        return child

    previous = signal.signal(signal.SIGTERM, handler)
    monkeypatch.setattr(module.subprocess, "Popen", spawn)
    try:
        result = supervisor.run([sys.executable, "-c", "pass"], timeout=3)
        assert result.returncode == 0
        assert len(observed) == 1 and observed[0] is not None
        assert signal.getsignal(signal.SIGTERM) is handler
    finally:
        signal.signal(signal.SIGTERM, previous)


def test_ignored_hangup_and_child_signal_mask_are_preserved(monkeypatch, tmp_path):
    original = subprocess.Popen
    supervisor = module.ProcessSupervisor(grace_seconds=0.1)
    mask_before = signal.pthread_sigmask(signal.SIG_BLOCK, [])
    result = tmp_path / "signals.txt"

    def spawn(*args, **kwargs):
        assert signal.getsignal(signal.SIGHUP) is signal.SIG_IGN
        os.kill(os.getpid(), signal.SIGHUP)
        return original(*args, **kwargs)

    previous = signal.signal(signal.SIGHUP, signal.SIG_IGN)
    monkeypatch.setattr(module.subprocess, "Popen", spawn)
    try:
        with module.stops_interrupt():
            supervisor.run(
                [
                    sys.executable,
                    "-c",
                    f"""
import signal
from pathlib import Path
Path({str(result)!r}).write_text(repr((sorted(int(s) for s in signal.pthread_sigmask(signal.SIG_BLOCK, [])), signal.getsignal(signal.SIGHUP) == signal.SIG_IGN)))
""",
                ],
                timeout=3,
            )
        assert result.read_text() == repr((sorted(int(s) for s in mask_before), True))
    finally:
        signal.signal(signal.SIGHUP, previous)
