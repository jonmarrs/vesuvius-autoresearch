"""Handoff deadlines clean real process groups before releasing the lock."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import process_supervisor, run_post_sprint_villa_handoff as handoff


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(handoff, "REPO", tmp_path)
    monkeypatch.setattr(handoff, "_named_processes", list)
    monkeypatch.setattr(
        handoff,
        "ProcessSupervisor",
        lambda: process_supervisor.ProcessSupervisor(grace_seconds=0.1),
    )
    return tmp_path


def test_timeout_kills_resistant_group_records_step_and_stops_pipeline(isolated):
    worker = isolated / "worker.py"
    worker.write_text("""
import json, os, signal, subprocess, sys, time
from pathlib import Path
signal.signal(signal.SIGTERM, signal.SIG_IGN)
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
Path('children.json').write_text(json.dumps([os.getpid(), child.pid]))
time.sleep(60)
""")
    marker = isolated / "later-step"
    steps = [
        {
            "name": "tracer_export",
            "gpu": True,
            "command": [sys.executable, str(worker)],
        },
        {
            "name": "later",
            "gpu": False,
            "command": [sys.executable, "-c", f"open({str(marker)!r},'w').close()"],
        },
    ]
    output = isolated / "plan.json"
    assert handoff.execute_handoff(steps, output, step_timeout=1) == 124
    plan = json.loads(output.read_text())
    assert plan["status"] == "FAILED_TIMEOUT"
    assert plan["step_timeout_seconds"] == 1
    assert plan["failure"]["step"] == "tracer_export"
    assert plan["failure"]["kind"] == "timeout"
    assert not marker.exists()
    for pid in json.loads((isolated / "children.json").read_text()):
        stat = Path(f"/proc/{pid}/stat")
        assert not stat.exists() or stat.read_text().rsplit(")", 1)[1].split()[0] == "Z"
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import fcntl; f=open('autoresearch.lock','a+'); fcntl.lockf(f,fcntl.LOCK_EX|fcntl.LOCK_NB)",
        ],
        cwd=isolated,
        check=True,
    )


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), "NaN", True])
def test_invalid_deadline_refuses_before_lock_or_report_writes(isolated, timeout):
    output = isolated / "plan.json"
    assert handoff.execute_handoff([{"gpu": True}], output, step_timeout=timeout) == 2
    assert not output.exists()
    assert not (isolated / "autoresearch.lock").exists()


def test_launch_error_is_a_named_failure_with_actionable_output(isolated, capsys):
    output = isolated / "plan.json"
    steps = [
        {"name": "missing_tool", "gpu": True, "command": [str(isolated / "missing")]}
    ]
    assert handoff.execute_handoff(steps, output, step_timeout=10) == 1
    assert json.loads(output.read_text())["failure"]["kind"] == "launch"
    assert "missing_tool" in capsys.readouterr().err


def test_success_records_completion_and_effective_deadline(isolated):
    output = isolated / "plan.json"
    steps = [{"name": "noop", "gpu": True, "command": [sys.executable, "-c", "pass"]}]
    assert handoff.execute_handoff(steps, output, step_timeout=5) == 0
    plan = json.loads(output.read_text())
    assert plan["status"] == "COMPLETE" and plan["failure"] is None
    assert plan["step_timeout_seconds"] == 5


def test_cli_rejects_invalid_timeout_before_building_steps(monkeypatch):
    monkeypatch.setattr(
        handoff, "build_handoff_steps", lambda args: pytest.fail("must not plan")
    )
    with pytest.raises(SystemExit) as exc:
        handoff.main(["--step-timeout", "nan"])
    assert exc.value.code == 2


def test_cli_carries_deadline_into_the_recorded_plan(isolated, monkeypatch):
    monkeypatch.chdir(isolated)
    monkeypatch.setattr(
        handoff,
        "build_handoff_steps",
        lambda args: [
            {"name": "plan", "gpu": False, "command": [sys.executable, "-c", "pass"]}
        ],
    )
    output = isolated / "plan.json"
    assert (
        handoff.main(
            ["--preflight-only", "--step-timeout", "12.5", "--plan-out", str(output)]
        )
        == 0
    )
    plan = json.loads(output.read_text())
    assert plan["step_timeout_seconds"] == 12.5
    assert plan["status"] == "COMPLETE"
