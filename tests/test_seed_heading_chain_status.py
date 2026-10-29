"""Exercise the real shell chain with a stub tracer, never native code or a GPU."""

import fcntl
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from scripts import seed_heading_chain_status as status

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "repro/fibers/run_villa_seed_heading_rerun.sh"
VOLUME = "vesuvius/src/vesuvius/neural_tracing/tracers/fibers/tracing/volume.py"
CUBE = status.CUBES[0]


def outputs(run):
    (run / "tiles").mkdir(parents=True, exist_ok=True)
    (run / "run.json").write_text('{"grid_scale": 2}\n')
    (run / "tiles.jsonl").write_text('{"tile": "test"}\n')
    (run / "tiles/one.npz").write_bytes(b"presence only, never decoded")


def test_latest_attempt_and_outputs_are_both_required(tmp_path):
    run = tmp_path / "before" / CUBE
    outputs(run)
    log = tmp_path / "chain.log"
    log.write_text(f"DONE before {CUBE}  t\n")
    assert status.inspect_run(tmp_path, "before", CUBE)["status"] == "COMPLETE"
    with log.open("a") as stream:
        stream.write(f"SKIP_DONE before {CUBE}  t\n")
    assert status.inspect_run(tmp_path, "before", CUBE)["status"] == "COMPLETE"
    with log.open("a") as stream:
        stream.write(f"TRACE before {CUBE}  t\nFAILED before {CUBE} rc=7  t\n")
    report = status.inspect_run(tmp_path, "before", CUBE)
    assert report["status"] == "INCOMPLETE" and report["last_event"] == "FAILED"
    log.write_text(f"DONE before {CUBE}  t\nTRACE before {CUBE}  t\n")
    assert status.inspect_run(tmp_path, "before", CUBE)["status"] == "INCOMPLETE"


@pytest.mark.parametrize("missing", ["run.json", "tiles.jsonl", "tiles/one.npz"])
def test_old_done_does_not_certify_deleted_outputs(tmp_path, missing):
    run = tmp_path / "before" / CUBE
    outputs(run)
    (tmp_path / "chain.log").write_text(f"DONE before {CUBE}  t\n")
    (run / missing).unlink()
    assert status.inspect_run(tmp_path, "before", CUBE)["status"] == "INCOMPLETE"


def test_partial_empty_and_legacy_export_checks(tmp_path):
    outputs(tmp_path)
    assert status.output_problems(tmp_path) == []
    assert status.output_problems(tmp_path, require_afv=True) == [
        "missing or empty fibers.afv"
    ]
    (tmp_path / "fibers.afv").write_bytes(b"not decoded")
    assert status.output_problems(tmp_path, require_afv=True) == []
    (tmp_path / "tiles/one.partial.npz").write_bytes(b"interrupted")
    assert "interrupted .partial.npz tiles remain" in status.output_problems(tmp_path)
    (tmp_path / "tiles/one.partial.npz").unlink()
    (tmp_path / "tiles/one.npz").write_bytes(b"")
    assert (
        "finished tile path is not a nonempty regular file"
        in status.output_problems(tmp_path)
    )


def test_status_cli_is_json_read_only_and_refuses_unknown_log(tmp_path, capsys):
    for side in status.SIDES:
        for cube in status.CUBES:
            outputs(tmp_path / side / cube)
    log = tmp_path / "chain.log"
    log.write_text(
        "".join(
            f"DONE {side} {cube}  t\n" for side in status.SIDES for cube in status.CUBES
        )
    )
    before = {
        p: (p.read_bytes(), p.stat().st_mtime_ns)
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    assert status.main(["status", "--work", str(tmp_path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert len(report["runs"]) == 4 and "unverified" in report["scope"]
    assert {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before} == before
    log.write_text("DONE before\n")
    assert status.main(["status", "--work", str(tmp_path)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "UNKNOWN"


@pytest.fixture
def chain(tmp_path):
    repo, work, tracer, villa, native = [
        tmp_path / n for n in ("repo", "work", "tracer", "villa", "native")
    ]
    for path in (
        repo / ".venv/bin",
        repo / "scripts",
        repo / "repro/fibers",
        tracer / "venv/bin",
        villa,
        native / "vc_object_store",
        work,
    ):
        path.mkdir(parents=True)
    (repo / ".venv/bin/python").symlink_to(sys.executable)
    (repo / "scripts/loop_control.py").write_text("raise SystemExit(1)\n")
    shutil.copyfile(
        ROOT / "scripts/seed_heading_chain_status.py",
        repo / "scripts/seed_heading_chain_status.py",
    )
    shutil.copyfile(
        ROOT / "repro/fibers/villa_volume_seed_heading.patch",
        repo / "repro/fibers/villa_volume_seed_heading.patch",
    )
    (native / "vc_object_store/__init__.py").touch()
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    for directory in (repo, villa):
        subprocess.run(["git", "init", "-q", str(directory)], check=True, env=env)
        subprocess.run(
            [
                "git",
                "-C",
                str(directory),
                "-c",
                "user.name=test",
                "-c",
                "user.email=test@example.com",
                "commit",
                "--allow-empty",
                "-qm",
                "fixture",
            ],
            check=True,
            env=env,
        )
    sha = subprocess.check_output(
        ["git", "-C", str(villa), "rev-parse", "HEAD"], text=True, env=env
    ).strip()
    (work / "villa_sha").write_text(sha + "\n")
    for side in status.SIDES:
        path = work / f"src_{side}" / VOLUME
        path.parent.mkdir(parents=True)
        path.write_text(
            "'--no-fibers'\n" + ("np.cos(np.radians(35))\n" if side == "before" else "")
        )
    test = (
        work
        / "src_after/vesuvius/src/vesuvius/neural_tracing/tracers/fibers/tests/test_volume_seed_heading.py"
    )
    test.parent.mkdir(parents=True)
    test.touch()
    executable = tracer / "venv/bin/python"
    executable.write_text(
        f"#!{sys.executable}\n"
        + """
import json,os,sys,time
from pathlib import Path
if '-c' in sys.argv:
    code=sys.argv[-1]
    if 'vc_object_store' in code:
        print(str(Path(os.environ['VC_SITE'])/'vc_object_store/__init__.py'))
    else:
        print(str(Path(os.environ['PYTHONPATH'].split(':')[0])/'vesuvius/neural_tracing/tracers/fibers/tracing/volume.py'))
    raise SystemExit(int(os.environ.get('PROBE_EXIT','0')))
out=Path(sys.argv[sys.argv.index('--out')+1])
with (Path(os.environ['W'])/'calls').open('a') as f:
    f.write(str(out)+'\\n')
mode=os.environ.get('TRACE_MODE','ok')
if mode == 'wait':
    (Path(os.environ['W'])/'worker_pid').write_text(str(os.getpid()))
    time.sleep(60)
if mode != 'missing':
    (out/'tiles').mkdir(parents=True,exist_ok=True)
    (out/'run.json').write_text('{"grid_scale":2}\\n')
    (out/'tiles.jsonl').write_text('{}\\n')
    (out/'tiles/one.npz').write_bytes(b'fixture-not-decoded')
    if mode == 'partial':
        (out/'tiles/one.partial.npz').write_bytes(b'partial')
raise SystemExit(7 if mode == 'exit' else 0)
"""
    )
    executable.chmod(0o755)
    env.update(
        REPO=str(repo),
        LOOPDIR=str(repo),
        VILLA_GIT=str(villa),
        VILLA_SHA=sha,
        W=str(work),
        T=str(tracer),
        VC_SITE=str(native),
        DRY_RUN="0",
    )

    def launch(**changes):
        return subprocess.run(
            ["bash", str(LAUNCHER)],
            env={**env, **changes},
            capture_output=True,
            text=True,
            timeout=30,
        )

    def start(**changes):
        return subprocess.Popen(
            ["bash", str(LAUNCHER)],
            env={**env, **changes},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    launch.start = start
    return work, launch


@pytest.mark.parametrize("mode", ["exit", "missing", "partial"])
def test_failed_or_incomplete_trace_never_reports_chain_complete(chain, mode):
    work, launch = chain
    result = launch(TRACE_MODE=mode)
    assert result.returncode == 1, result.stdout + result.stderr
    log = (work / "chain.log").read_text()
    assert "CHAIN_FAILED 4" in log and "CHAIN_COMPLETE" not in log
    assert len((work / "calls").read_text().splitlines()) == 4
    assert status.main(["status", "--work", str(work)]) == 1


def test_success_resumes_only_with_done_and_present_outputs(chain):
    work, launch = chain
    result = launch()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CHAIN_COMPLETE" in result.stdout
    assert len((work / "calls").read_text().splitlines()) == 4
    assert launch().returncode == 0
    assert len((work / "calls").read_text().splitlines()) == 4
    (work / "before" / CUBE / "tiles/one.npz").unlink()
    assert launch().returncode == 0
    assert len((work / "calls").read_text().splitlines()) == 5


def test_relative_symlink_work_path_with_spaces_is_resolved_before_tracing(chain):
    work, launch = chain
    alias = work.parent / "work alias"
    alias.symlink_to(work, target_is_directory=True)
    result = launch(W=os.path.relpath(alias, ROOT))
    assert result.returncode == 0, result.stdout + result.stderr
    assert len((work / "calls").read_text().splitlines()) == 4
    assert status.main(["status", "--work", str(work)]) == 0


def test_outputs_from_failed_attempt_are_retried(chain):
    work, launch = chain
    assert launch(TRACE_MODE="exit").returncode == 1
    assert launch().returncode == 0
    assert len((work / "calls").read_text().splitlines()) == 8


def test_import_probe_exit_is_checked_even_if_it_prints_expected_path(chain):
    work, launch = chain
    result = launch(PROBE_EXIT="9")
    assert result.returncode == 3
    assert "import check failed" in result.stdout
    assert not (work / "calls").exists()


def test_log_write_failure_refuses_before_tracing(chain):
    work, launch = chain
    tools = work / "fake-bin"
    tools.mkdir()
    tee = tools / "tee"
    tee.write_text("#!/bin/sh\nexit 1\n")
    tee.chmod(0o755)
    result = launch(PATH=str(tools) + os.pathsep + os.environ["PATH"])
    assert result.returncode == 3 and "cannot append" in result.stderr
    assert not (work / "calls").exists()


def test_concurrent_work_lease_refuses_without_editing_chain_log(chain):
    work, launch = chain
    log = work / "chain.log"
    log.write_text("existing history\n")
    with (work / "chain.lock").open("w") as stream:
        stream.write("existing lease contents\n")
        stream.flush()
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = launch()
    assert result.returncode == 3 and "another launcher or worker" in result.stderr
    assert log.read_text() == "existing history\n"
    assert (work / "chain.lock").read_text() == "existing lease contents\n"
    assert not (work / "calls").exists()


@pytest.mark.parametrize("kind", ["symlink", "directory"])
def test_nonregular_lease_path_is_refused_before_logging(chain, kind):
    work, launch = chain
    lease = work / "chain.lock"
    if kind == "symlink":
        target = work / "preserved"
        target.write_text("keep")
        lease.symlink_to(target)
    else:
        lease.mkdir()
    result = launch()
    assert result.returncode == 3 and "must be a regular file" in result.stderr
    assert not (work / "calls").exists()
    if kind == "symlink":
        assert target.read_text() == "keep"


def test_malformed_resume_history_refuses_before_any_trace(chain):
    work, launch = chain
    (work / "chain.log").write_text("DONE before\n")
    result = launch()
    assert result.returncode == 3 and "cannot inspect" in result.stdout
    assert not (work / "calls").exists()


def test_worker_retains_lease_if_launcher_is_killed(chain):
    work, launch = chain
    parent = launch.start(TRACE_MODE="wait")
    try:
        deadline = time.monotonic() + 10
        while (
            not (work / "worker_pid").exists()
            and parent.poll() is None
            and time.monotonic() < deadline
        ):
            time.sleep(0.01)
        assert (work / "worker_pid").exists()
        os.kill(parent.pid, signal.SIGKILL)
        assert parent.wait(timeout=3) == -signal.SIGKILL
        before = (work / "chain.log").read_bytes()
        retry = launch()
        assert retry.returncode == 3 and "another launcher or worker" in retry.stderr
        assert (work / "chain.log").read_bytes() == before
    finally:
        try:
            os.killpg(parent.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        parent.wait(timeout=3)
