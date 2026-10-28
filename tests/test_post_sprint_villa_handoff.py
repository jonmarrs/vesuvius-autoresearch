import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import time
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import loop_control, run_post_sprint_villa_handoff as handoff
from scripts.run_post_sprint_villa_handoff import (
    build_handoff_steps,
    resolve_status,
    write_plan,
)


def _args(**overrides):
    data = {
        "python_executable": "python",
        "ranked": "ranked.tsv",
        "queue": "queue.tsv",
        "prediction_dir": "predictions",
        "checkpoint": "best_model.pt",
        "manifest": "commands.sh",
        "evidence_root": "evidence",
        "villa_audit": "villa_audit.json",
        "villa_opportunities": "villa_opportunities.json",
        "villa_pin_review": "villa_pin_review.json",
        "villa_component_coverage_json": "component_coverage.json",
        "villa_component_coverage_md": "component_coverage.md",
        "volume_cartographer_sample_zarr": "sample.zarr",
        "volume_cartographer_readiness_json": "volume_cartographer_readiness.json",
        "volume_cartographer_readiness_md": "volume_cartographer_readiness.md",
        "preflight_summary_json": "preflight_summary.json",
        "preflight_summary_tsv": "preflight_summary.tsv",
        "gpu_queue": "gpu_queue.tsv",
        "villa_action_matrix_json": "action_matrix.json",
        "villa_action_matrix_md": "action_matrix.md",
        "villa_review_manifest_json": "review_manifest.json",
        "villa_review_manifest_md": "review_manifest.md",
        "inference_limit": 8,
        "worklist_limit": 12,
        "evidence_limit": 2,
        "execute_inference": False,
        "execute_evidence": False,
    }
    data.update(overrides)
    return Namespace(**data)


def test_post_sprint_handoff_defaults_to_safe_preflight_commands():
    steps = build_handoff_steps(_args())

    assert [step["name"] for step in steps] == [
        "audit_villa_upstream",
        "plan_villa_prize_opportunities",
        "review_villa_pin",
        "build_villa_component_coverage",
        "build_volume_cartographer_readiness",
        "ranked_inference",
        "rerank_candidates",
        "build_lasagna_fiber_worklist",
        "evidence_candidate_000",
        "evidence_candidate_001",
        "summarize_villa_evidence_preflight",
        "build_villa_prize_action_matrix",
        "build_villa_review_manifest",
    ]
    assert steps[0]["command"][-1] == "villa_audit.json"
    assert steps[1]["command"][-1] == "villa_opportunities.json"
    assert steps[2]["command"][-1] == "villa_pin_review.json"
    assert steps[3]["command"][-1] == "component_coverage.md"
    assert steps[4]["name"] == "build_volume_cartographer_readiness"
    assert steps[4]["command"][-1] == "volume_cartographer_readiness.md"
    assert steps[5]["gpu"] is False
    assert "--execute" not in steps[5]["command"]
    assert "--preflight-report" in steps[8]["command"]
    assert steps[8]["command"][-1] == "evidence/candidate_000/preflight_report.json"
    assert steps[8]["gpu"] is False
    assert "--root" in steps[-3]["command"]
    assert "--out-json" in steps[-3]["command"]
    assert "--out-tsv" in steps[-3]["command"]
    assert steps[-3]["command"][-1] == "gpu_queue.tsv"
    assert steps[-2]["name"] == "build_villa_prize_action_matrix"
    assert "--opportunities" in steps[-2]["command"]
    assert "--preflight" in steps[-2]["command"]
    assert steps[-2]["command"][-1] == "action_matrix.md"
    assert steps[-1]["name"] == "build_villa_review_manifest"
    assert "--gpu-queue" in steps[-1]["command"]
    assert "--action-matrix" in steps[-1]["command"]
    assert "--ranked" in steps[-1]["command"]
    assert steps[-1]["command"][-1] == "python"


def test_post_sprint_handoff_execute_flags_mark_gpu_steps():
    steps = build_handoff_steps(
        _args(execute_inference=True, execute_evidence=True, evidence_limit=1)
    )

    assert steps[5]["gpu"] is True
    assert steps[5]["command"][-1] == "--execute"
    assert steps[8]["gpu"] is True
    assert "--preflight" not in steps[8]["command"]
    assert steps[8]["command"][-1] == "--execute"


def test_post_sprint_handoff_plan_records_active_process_block(tmp_path):
    plan = write_plan(
        tmp_path / "plan.json",
        active_processes=["123 run_autoresearch_loop.py"],
        steps=[{"name": "ranked_inference", "command": ["python"], "gpu": False}],
        status="BLOCKED_ACTIVE_SPRINT",
    )

    assert plan["status"] == "BLOCKED_ACTIVE_SPRINT"
    assert "run_autoresearch_loop.py" in plan["active_processes"][0]
    assert (tmp_path / "plan.json").exists()


def test_post_sprint_handoff_preflight_only_allows_non_gpu_steps_during_active_sprint():
    steps = build_handoff_steps(_args())

    status = resolve_status(
        active_processes=["123 run_autoresearch_loop.py"],
        steps=steps,
        preflight_only=True,
    )

    assert status == "READY_ACTIVE_SPRINT_NON_GPU"


def test_post_sprint_handoff_preflight_only_blocks_gpu_steps_during_active_sprint():
    steps = build_handoff_steps(_args(execute_inference=True))

    status = resolve_status(
        active_processes=["123 run_autoresearch_loop.py"],
        steps=steps,
        preflight_only=True,
    )

    assert status == "BLOCKED_GPU_STEP_ACTIVE_SPRINT"


# --- what counts as research using the GPU --------------------------------------

# Command lines as each lock holder and its training run them. The pattern once
# named only the loop and train.py, and missed the first seven.
_ACTIVE = (
    "python scripts/f1_noise_probe.py --plan plan.json",
    "python -m scripts.f1_noise_probe --plan plan.json",
    "/venv/bin/python /repo/scripts/training/run_noise_probe.py --config c.json",
    "uv run python -u scripts/train_with_new_augs.py --config c.json --seed 1",
    "python -m scripts.reevaluate_best_model --update-stored",
    "python scripts/ablate_scroll_augmentations.py",
    "python -m scripts.ablate_scroll_augmentations",
    "uv run python -u run_autoresearch_loop.py",
    "python scripts/training/train.py --smoke",
    "python -m scripts.training.train",
    "python -m scripts.train_with_new_augs --config config.json",
    "python scripts/run_post_sprint_villa_handoff.py --execute-inference",
    "python -m scripts.run_post_sprint_villa_handoff --execute-evidence",
)
_INACTIVE = (
    "python -m pytest tests/test_f1_noise_probe.py",
    "python scripts/run_post_sprint_villa_handoff.py --preflight-only",
    "vim docs/train.py.md",
)

needs_pgrep = pytest.mark.skipif(
    not sys.platform.startswith("linux") or not shutil.which("pgrep"),
    reason="needs Linux pgrep (-a lists ancestors elsewhere)",
)


def _stand_ins(tmp_path, commands):
    """A sleeping interpreter per command line, carrying its arguments; started
    from sys.executable, as python3 on PATH may not run under a borrowed name."""
    return [
        subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"]
            + shlex.split(cmd)[1:],
            cwd=tmp_path,
        )
        for cmd in commands
    ]


def _pids(lines):
    return {int(line.split()[0]) for line in lines}


@needs_pgrep
def test_the_pattern_finds_every_lock_holder_and_its_training(tmp_path):
    """Through pgrep itself, whose extended regular expressions the pattern is."""
    procs = _stand_ins(tmp_path, _ACTIVE + _INACTIVE)
    try:
        found = _pids(handoff._named_processes())
    finally:
        for proc in procs:
            proc.kill()
            proc.wait()
    for proc, cmd in zip(procs, _ACTIVE + _INACTIVE, strict=True):
        assert (proc.pid in found) == (cmd in _ACTIVE), cmd


@needs_pgrep
def test_the_guard_reports_a_running_noise_probe(monkeypatch, tmp_path):
    """End to end through active_sprint_processes, with the lock elsewhere: a
    probe in another checkout holds that checkout's lock, not this one's."""
    monkeypatch.setattr(loop_control, "running_pid", lambda repo: None)
    monkeypatch.setattr(
        loop_control, "unsupervised_runs", lambda repo, supervisor=None: []
    )
    (probe,) = _stand_ins(tmp_path, _ACTIVE[:1])
    try:
        active = handoff.active_sprint_processes(tmp_path)
    finally:
        probe.kill()
        probe.wait()
    assert probe.pid in _pids(active), active
    assert handoff.resolve_status(active, []) == "BLOCKED_ACTIVE_SPRINT"


@needs_pgrep
@pytest.mark.parametrize("module", sorted(loop_control.RUN_MODULES))
def test_process_scan_detects_actual_module_trainer_in_another_checkout(tmp_path, module):
    other = tmp_path / "other_checkout"
    script = other.joinpath(*module.split(".")).with_suffix(".py")
    script.parent.mkdir(parents=True)
    directory = script.parent
    while directory != other:
        (directory / "__init__.py").touch()
        directory = directory.parent
    script.write_text("import time\nprint('ready',flush=True)\ntime.sleep(60)\n")
    process = subprocess.Popen(
        [sys.executable, "-m", module], cwd=other,
        stdout=subprocess.PIPE, text=True,
    )
    try:
        assert process.stdout.readline().strip() == "ready"
        assert process.pid in _pids(handoff._named_processes())
        assert handoff.resolve_status(handoff._named_processes(), []) == "BLOCKED_ACTIVE_SPRINT"
    finally:
        process.kill()
        process.wait(timeout=2)


def test_the_pattern_names_every_script_that_takes_the_lock():
    for name in loop_control.LOCK_HOLDER_ARGS:
        assert name.replace(".", r"\.") in handoff.ACTIVE_PROCESS_PATTERN, name


def _quiet(monkeypatch, repo, pid=None, runs=(), error=None):
    def running_pid(asked):
        if error:
            raise error
        return pid if asked == repo else None  # this checkout's lock only

    monkeypatch.setattr(loop_control, "running_pid", running_pid)
    monkeypatch.setattr(
        loop_control, "unsupervised_runs", lambda repo, supervisor=None: list(runs)
    )
    monkeypatch.setattr(handoff, "_named_processes", list)


def test_the_lock_holder_counts_as_active(monkeypatch, tmp_path):
    """A noise probe, an ablation or a re-score in this checkout holds the lock."""
    _quiet(monkeypatch, tmp_path, pid=4242)
    active = handoff.active_sprint_processes(tmp_path)
    assert active == [f"4242 holds {tmp_path / 'autoresearch.lock'}"]
    assert handoff.resolve_status(active, []) == "BLOCKED_ACTIVE_SPRINT"


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("loop lock is held but contains no valid PID"),
        PermissionError("autoresearch.lock"),
        ValueError("invalid literal for int()"),
    ],
)
def test_a_lock_that_cannot_be_read_counts_as_active(monkeypatch, tmp_path, error):
    _quiet(monkeypatch, tmp_path, error=error)
    active = handoff.active_sprint_processes(tmp_path)
    assert len(active) == 1 and type(error).__name__ in active[0]


def test_an_unsupervised_training_run_counts_as_active(monkeypatch, tmp_path):
    _quiet(monkeypatch, tmp_path, runs=[(777, 120.0, True)])
    active = handoff.active_sprint_processes(tmp_path)
    assert active == [
        "unsupervised training run: PID 777 (started by a loop or ablation, "
        "running 2 min)"
    ]


def test_nothing_running_is_ready(monkeypatch, tmp_path):
    _quiet(monkeypatch, tmp_path)
    assert handoff.active_sprint_processes(tmp_path) == []


_TAKE_LOCK = """
import fcntl
with open('autoresearch.lock', 'a+') as handle:
    fcntl.lockf(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
"""


def _isolated_handoff(monkeypatch, tmp_path):
    monkeypatch.setattr(handoff, "REPO", tmp_path)
    monkeypatch.setattr(handoff, "_named_processes", list)
    # A second open+close here would silently release our process's POSIX lock.
    def must_not_probe(_):
        raise AssertionError("running_pid must not reopen our held lock")

    monkeypatch.setattr(loop_control, "running_pid", must_not_probe)


def test_gpu_handoff_keeps_lock_through_steps_and_releases_afterward(monkeypatch, tmp_path):
    _isolated_handoff(monkeypatch, tmp_path)
    command = [sys.executable, "-c", """
import fcntl
from pathlib import Path
with open('autoresearch.lock', 'a+') as handle:
    try:
        fcntl.lockf(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        Path('lock_was_held').touch()
    else:
        raise SystemExit('GPU step started without exclusive checkout lock')
"""]
    steps = [{"name": "fake_gpu", "gpu": True, "command": command}]
    assert handoff.execute_handoff(steps, tmp_path / "plan.json") == 0
    assert (tmp_path / "lock_was_held").exists()
    subprocess.run([sys.executable, "-c", _TAKE_LOCK], cwd=tmp_path, check=True)


def test_failed_gpu_step_releases_lock(monkeypatch, tmp_path):
    _isolated_handoff(monkeypatch, tmp_path)
    steps = [{"name": "fake_gpu", "gpu": True, "command": [sys.executable, "-c", "raise SystemExit(7)"]}]
    assert handoff.execute_handoff(steps, tmp_path / "plan.json") == 1
    plan = json.loads((tmp_path / "plan.json").read_text())
    assert plan["status"] == "FAILED_STEP"
    assert plan["failure"]["step"] == "fake_gpu"
    assert plan["failure"]["returncode"] == 7
    subprocess.run([sys.executable, "-c", _TAKE_LOCK], cwd=tmp_path, check=True)


def test_force_cannot_bypass_checkout_lock(monkeypatch, tmp_path):
    _isolated_handoff(monkeypatch, tmp_path)
    holder = subprocess.Popen(
        [sys.executable, "-c", "import fcntl,time; f=open('autoresearch.lock','a+'); fcntl.lockf(f,fcntl.LOCK_EX); print('ready',flush=True); time.sleep(60)"],
        cwd=tmp_path, stdout=subprocess.PIPE, text=True,
    )
    try:
        assert holder.stdout.readline().strip() == "ready"
        marker = tmp_path / "must_not_run"
        steps = [{"name": "fake_gpu", "gpu": True, "command": [sys.executable, "-c", f"open({str(marker)!r}, 'w').close()"]}]
        assert handoff.execute_handoff(steps, tmp_path / "plan.json", force=True) == 2
        assert json.loads((tmp_path / "plan.json").read_text())["status"] == "BLOCKED_LOCAL_LOCK"
        assert not marker.exists()
    finally:
        holder.kill()
        holder.wait(timeout=2)


def test_force_cannot_bypass_local_unsupervised_training(monkeypatch, tmp_path):
    _isolated_handoff(monkeypatch, tmp_path)
    monkeypatch.setattr(loop_control, "unsupervised_runs", lambda repo: [(123, 1, False)])
    monkeypatch.setattr(handoff, "run_steps", lambda steps: pytest.fail("must not execute"))
    steps = [{"name": "fake_gpu", "gpu": True, "command": []}]
    assert handoff.execute_handoff(steps, tmp_path / "plan.json", force=True) == 2
    assert json.loads((tmp_path / "plan.json").read_text())["status"] == "BLOCKED_LOCAL_TRAINING"


@pytest.mark.parametrize("alias", ["direct", "symlink", "hardlink"])
@pytest.mark.parametrize("held_elsewhere", [False, True])
def test_plan_alias_cannot_release_lock_or_corrupt_another_owner(
    monkeypatch, tmp_path, alias, held_elsewhere, capsys
):
    monkeypatch.setattr(handoff, "REPO", tmp_path)
    monkeypatch.setattr(handoff, "run_steps", lambda steps: pytest.fail("aliased report must never run steps"))
    lock = tmp_path / "autoresearch.lock"
    lock.write_text("preserve existing lock metadata\n")
    holder = None
    if held_elsewhere:
        holder = subprocess.Popen(
            [sys.executable, "-c", "import fcntl,os,time; f=open('autoresearch.lock','r+'); fcntl.lockf(f,fcntl.LOCK_EX); f.truncate(); f.write(str(os.getpid())+'\\n'); f.flush(); print('ready',flush=True); time.sleep(60)"],
            cwd=tmp_path, stdout=subprocess.PIPE, text=True,
        )
        assert holder.stdout.readline().strip() == "ready"
    try:
        original = lock.read_bytes()
        output = lock if alias == "direct" else tmp_path / "plan.json"
        if alias == "symlink":
            output.symlink_to(lock)
        elif alias == "hardlink":
            output.hardlink_to(lock)
        steps = [{"name": "fake_gpu", "gpu": True, "command": []}]
        assert handoff.execute_handoff(steps, output, force=True) == 2
        assert "must not alias autoresearch.lock" in capsys.readouterr().err
        assert lock.read_bytes() == original
        competitor = subprocess.run([sys.executable, "-c", _TAKE_LOCK], cwd=tmp_path, capture_output=True)
        assert (competitor.returncode != 0) is held_elsewhere
    finally:
        if holder is not None:
            holder.kill()
            holder.wait(timeout=2)


def test_direct_plan_lock_alias_is_rejected_before_lock_creation(monkeypatch, tmp_path):
    monkeypatch.setattr(handoff, "REPO", tmp_path)
    lock = tmp_path / "autoresearch.lock"
    assert handoff.execute_handoff([{"gpu": True}], lock) == 2
    assert not lock.exists()


def test_uninspectable_plan_path_is_refused_without_writing(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(handoff, "REPO", tmp_path)
    output = tmp_path / "plan.json"
    output.write_text("original report")
    original_stat = Path.stat

    def denied(path, *args, **kwargs):
        if path == output:
            raise PermissionError("cannot inspect output")
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", denied)
    assert handoff.execute_handoff([{"gpu": True}], output) == 2
    assert "cannot inspect output" in capsys.readouterr().err
    assert output.read_text() == "original report"
    assert not (tmp_path / "autoresearch.lock").exists()


def test_non_gpu_preflight_does_not_acquire_lock(monkeypatch, tmp_path):
    monkeypatch.setattr(handoff, "REPO", tmp_path)
    monkeypatch.setattr(handoff, "active_sprint_processes", lambda repo: ["123 active loop"])
    monkeypatch.setattr(loop_control, "acquire_lock", lambda path: pytest.fail("non-GPU preflight must not acquire lock"))
    completed = []
    monkeypatch.setattr(handoff, "run_steps", lambda steps, **kwargs: completed.extend(steps))
    steps = [{"name": "plan", "gpu": False, "command": []}]
    assert handoff.execute_handoff(steps, tmp_path / "plan.json", preflight_only=True) == 0
    assert completed == steps


def test_process_scan_excludes_itself_and_its_handoff_launcher(monkeypatch):
    own, parent, other = os.getpid(), os.getppid(), 999999991
    output = "\n".join(f"{pid} python scripts/run_post_sprint_villa_handoff.py --execute-inference" for pid in (own, parent, other))
    monkeypatch.setattr(handoff.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=output))
    monkeypatch.setattr(loop_control, "_stat_fields", lambda pid: ["S", "1"])
    monkeypatch.setattr(Path, "read_bytes", lambda path: b"python\0scripts/run_post_sprint_villa_handoff.py\0--execute-inference\0")
    assert _pids(handoff._named_processes()) == {other}


def _scan_launcher(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    launcher = tmp_path / "run_post_sprint_villa_handoff.py"
    launcher.write_text("""
import json, os
from scripts import run_post_sprint_villa_handoff as handoff
print(json.dumps({'own':os.getpid(), 'parent':os.getppid(), 'active':handoff._named_processes()}))
""")
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(repo), str(repo / "src"), os.environ.get("PYTHONPATH", "")])}
    return launcher, env


@needs_pgrep
def test_shell_command_launcher_does_not_block_its_own_handoff(tmp_path):
    launcher, env = _scan_launcher(tmp_path)
    command = shlex.join([sys.executable, str(launcher), "--execute-inference"])
    # The trailing command keeps bash alive as the handoff's parent rather
    # than replacing itself with Python. No GPU work is launched.
    result = subprocess.run(
        ["bash", "-c", command + "; :"], cwd=tmp_path, env=env,
        text=True, capture_output=True, check=True, timeout=10,
    )
    report = json.loads(result.stdout)
    assert report["own"] not in _pids(report["active"])
    assert report["parent"] not in _pids(report["active"])


@needs_pgrep
def test_actual_python_training_ancestor_still_blocks_handoff(tmp_path):
    launcher, env = _scan_launcher(tmp_path)
    trainer = tmp_path / "other_checkout/scripts/training/train.py"
    trainer.parent.mkdir(parents=True)
    trainer.write_text(f"""
import subprocess, sys
subprocess.run([sys.executable, {str(launcher)!r}, '--execute-inference'], check=True)
""")
    result = subprocess.run(
        [sys.executable, str(trainer)], cwd=trainer.parent, env=env,
        text=True, capture_output=True, check=True, timeout=10,
    )
    report = json.loads(result.stdout)
    assert report["own"] not in _pids(report["active"])
    assert report["parent"] in _pids(report["active"])


def test_cli_anchors_lock_and_relative_paths_to_its_checkout(monkeypatch, tmp_path):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(handoff, "REPO", checkout)
    monkeypatch.setattr(handoff, "build_handoff_steps", lambda args: [])
    seen = []

    def execute(*args, **kwargs):
        seen.append(Path.cwd())
        return 0

    monkeypatch.setattr(handoff, "execute_handoff", execute)
    assert handoff.main([]) == 0
    assert seen == [checkout]


@needs_pgrep
def test_stop_cleans_gpu_step_and_descendant_before_releasing_lock(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    worker = tmp_path / "worker.py"
    worker.write_text("""
import json, os, subprocess, sys, time
from pathlib import Path
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
Path('children.json').write_text(json.dumps([os.getpid(), child.pid]))
time.sleep(60)
""")
    launcher = tmp_path / "run_post_sprint_villa_handoff.py"
    launcher.write_text(f"""
import sys
from pathlib import Path
from scripts import run_post_sprint_villa_handoff as handoff
handoff.REPO = Path.cwd()
handoff._named_processes = list
try:
    handoff.execute_handoff([{{'name':'fake_gpu','gpu':True,'command':[sys.executable,{str(worker)!r}]}}], Path('plan.json'))
except KeyboardInterrupt:
    raise SystemExit(130)
""")
    process = subprocess.Popen(
        [sys.executable, str(launcher)], cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": os.pathsep.join([str(repo), str(repo / "src"), os.environ.get("PYTHONPATH", "")])},
        stdout=subprocess.DEVNULL,
    )
    children = []
    try:
        deadline = time.monotonic() + 10
        while not (tmp_path / "children.json").exists() and time.monotonic() < deadline:
            assert process.poll() is None
            time.sleep(0.02)
        children = json.loads((tmp_path / "children.json").read_text())
        assert loop_control.running_pid(tmp_path) == process.pid
        assert loop_control.main(["stop", "--repo", str(tmp_path), "--timeout", "15"]) == 0
        assert process.wait(timeout=2) == 130
        assert json.loads((tmp_path / "plan.json").read_text())["status"] == "STOPPED"
        for pid in children:
            try:
                assert loop_control._stat_fields(pid)[0] == "Z"
            except FileNotFoundError:
                pass
        subprocess.run([sys.executable, "-c", _TAKE_LOCK], cwd=tmp_path, check=True)
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=2)
        for pid in children:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
