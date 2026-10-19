"""scripts/ablate_scroll_augmentations.py runs its cells as experiment runs.

It used to train each cell as a loop cycle in the main checkout: a run could
promote into best_model.pt and append to the loop's logs, and the harness
copied a backup of best_model.pt back afterwards, over any promotion the loop
had made meanwhile. See docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-15_OPERATOR_SCRIPTS.md.
"""

import ast
import csv
import inspect
import json
import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

import scripts.ablate_scroll_augmentations as ablation
from scripts.process_supervisor import ProcessSupervisor
from scripts.training import train
from scripts.training.config import ExperimentConfig

REPO = Path(__file__).resolve().parents[1]
ENV = {**os.environ, "PYTHONPATH": str(REPO)}


def _project(tmp_path, monkeypatch):
    # main() chdirs to PROJECT_ROOT; monkeypatch puts the cwd back afterwards.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ablation, "PROJECT_ROOT", tmp_path)
    ExperimentConfig().save(tmp_path / "config.json")
    (tmp_path / "best_model.pt").write_bytes(b"incumbent")
    (tmp_path / "run_result.json").write_text(json.dumps({"val_bpb": 9.0}))
    argv = ["ablate", "--seeds", "1", "--conditions", "baseline", "squeeze"]
    argv += ["--out", str(tmp_path / "ablation.csv")]
    monkeypatch.setattr(sys, "argv", argv)


def _lock_is_free(repo):
    """What the loop's start does: take the checkout's lock (in another process;
    POSIX record locks do not exclude their own process)."""
    return (
        subprocess.run(
            [
                sys.executable,
                "-c",
                "from scripts.loop_control import acquire_lock; "
                "acquire_lock('autoresearch.lock')",
            ],
            cwd=repo,
            env=ENV,
            capture_output=True,
        ).returncode
        == 0
    )


def _alive(pid):
    try:
        return Path(f"/proc/{pid}/stat").read_text().split()[2] not in "ZX"
    except FileNotFoundError:
        return False


def test_the_ablation_leaves_the_loops_files_alone(tmp_path, monkeypatch):
    _project(tmp_path, monkeypatch)
    seen = []

    def run(cfg_path, seed, budget, log_path, supervisor):
        cfg = ExperimentConfig.load(cfg_path)
        result = tmp_path / "run_result.json"
        seen.append((cfg.checkpoint_out, result.exists(), _lock_is_free(tmp_path)))
        # train.py's writes: its checkpoint (and step checkpoints with
        # eval_every_steps), and a result the next cell must not read.
        Path(cfg.checkpoint_out).write_bytes(b"candidate")
        Path(f"{cfg.checkpoint_out}.step100.pt").write_bytes(b"step")
        result.write_text(json.dumps({"val_bpb": 0.5}))
        return {"status": "OK", "elapsed_s": 1.0, "val_bpb": 0.5}

    monkeypatch.setattr(ablation, "_run_one", run)
    assert ablation.main() == 0
    assert len(seen) == 2
    # Each run is an experiment run, starts without the previous result, and
    # holds the checkout's lock, so the watchdog cannot start the loop.
    for out, stale, free in seen:
        assert out and out.endswith(".pt")
        assert not stale
        assert not free
    assert _lock_is_free(tmp_path)  # released at the end
    assert (tmp_path / "best_model.pt").read_bytes() == b"incumbent"
    assert not list(tmp_path.glob("best_model.pt.*"))  # no backup any more
    assert not list((tmp_path / "reports" / "ablation_logs").glob("*.pt"))
    assert not list(tmp_path.glob("config_temp_ablation_*"))


@pytest.mark.parametrize(
    "holder,message",
    [("run_autoresearch_loop.py", "(PID {pid}) runs"), ("other.py", "(unidentified:")],
)
def test_the_ablation_will_not_run_beside_other_work(
    tmp_path, monkeypatch, capsys, holder, message
):
    _project(tmp_path, monkeypatch)
    monkeypatch.setattr(
        ablation, "_run_one", lambda *a: (_ for _ in ()).throw(AssertionError("ran"))
    )
    (tmp_path / holder).write_text(
        "import time\n"
        "from scripts.loop_control import acquire_lock\n"
        "lock = acquire_lock('autoresearch.lock')\n"
        "print('ready', flush=True)\n"
        "while True: time.sleep(.1)\n"
    )
    work = subprocess.Popen(
        [sys.executable, "-u", holder],
        cwd=tmp_path,
        env=ENV,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert work.stdout is not None and work.stdout.readline() == "ready\n"
        assert ablation.main() == 1
    finally:
        work.kill()
        work.wait()
    err = capsys.readouterr().err
    assert message.format(pid=work.pid) in err
    assert "stop it first (./stop.sh)" in err


@pytest.mark.skipif(not Path("/proc/self/cwd").exists(), reason="reads /proc")
def test_the_ablation_will_not_run_beside_a_run_no_loop_supervises(
    tmp_path, monkeypatch, capsys, orphaned_run
):
    """A loop killed without its handler leaves its run training here. A cell
    beside it shared the GPU, so trained fewer steps in its budget, and its
    result was read from the run_result.json both write."""
    _project(tmp_path, monkeypatch)
    monkeypatch.setattr(
        ablation, "_run_one", lambda *a: (_ for _ in ()).throw(AssertionError("ran"))
    )
    run = orphaned_run(tmp_path)
    assert ablation.main() == 1
    err = capsys.readouterr().err
    assert "not starting: a training run no loop supervises" in err
    assert f"PID {run.pid} (started by a loop or ablation" in err
    assert "./stop.sh stops the runs a loop or ablation started" in err
    assert _lock_is_free(tmp_path)
    assert run.poll() is None  # named, not stopped
    assert json.loads((tmp_path / "run_result.json").read_text()) == {"val_bpb": 9.0}
    assert not (tmp_path / "ablation.csv").exists()


def test_a_stop_ends_the_ablation_between_its_cells(tmp_path, monkeypatch, capsys):
    """./stop.sh sends SIGTERM to the lock's PID: the cell in flight ends, the
    lock is released, and the runs so far are written."""
    _project(tmp_path, monkeypatch)
    calls = []

    def run(cfg_path, seed, budget, log_path, supervisor):
        calls.append(cfg_path)
        if len(calls) == 2:
            os.kill(os.getpid(), signal.SIGTERM)
        return {"status": "OK", "elapsed_s": 1.0, "val_bpb": 0.5}

    monkeypatch.setattr(ablation, "_run_one", run)
    before = signal.getsignal(signal.SIGTERM)
    assert ablation.main() == 0
    assert signal.getsignal(signal.SIGTERM) is before
    assert len(calls) == 2
    assert "stopped after 1 of 2 runs" in capsys.readouterr().err
    with open(tmp_path / "ablation.csv") as f:
        assert [row["run_id"] for row in csv.DictReader(f)] == ["baseline_seed0"]
    assert _lock_is_free(tmp_path)
    assert not list(tmp_path.glob("config_temp_ablation_*"))


def test_a_timed_out_cell_ends_its_trainer_too(tmp_path, monkeypatch):
    """subprocess.run's timeout killed only `uv run`; the trainer it launched
    kept the GPU and wrote run_result.json during later cells."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    trainer_pid = tmp_path / "trainer.pid"
    uv = bin_dir / "uv"
    uv.write_text(f"#!/bin/sh\nsleep 600 &\necho $! > {trainer_pid}\nwait\n")
    uv.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    log = tmp_path / "cell.log"
    # The harness allows budget + 240 s; a budget of -238 times out in 2 s.
    result = ablation._run_one("cfg.json", 0, -238, str(log), ProcessSupervisor())
    assert result["status"] == "TIMEOUT"
    pid = int(trainer_pid.read_text())
    deadline = time.monotonic() + 5
    while _alive(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not _alive(pid)


def test_train_writes_the_loops_logs_only_outside_an_experiment_run():
    """history.tsv, results.tsv and prize_readiness.tsv are the loop's; an
    experiment run (checkpoint_out) writes none of them. Checked on train()'s
    source, as no test runs train() to its end."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(train.train)))
    parents = {
        child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)
    }
    writes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", None) == "append_tsv_row"
    ]
    assert len(writes) == 3
    for write in writes:
        guards, node = [], write
        while node in parents:
            node = parents[node]
            if isinstance(node, ast.If):
                guards.append(ast.unparse(node.test))
        assert "not getattr(config, 'checkpoint_out', None)" in guards or (
            "promoted" in guards
        ), ast.unparse(write)[:60]
    (promoted,) = [
        ast.unparse(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and [ast.unparse(t) for t in node.targets] == ["promoted"]
    ]
    assert promoted == "is_improvement and (not ckpt_out)"


def test_a_cell_records_what_the_loop_selects_on(tmp_path, monkeypatch):
    """The harness predates selection on val_f1 (2026-07-11) and recorded only
    val_bpb and topology, which the loop reports but no longer decides on; nor
    whether the cell warm-started from the incumbent as each is meant to."""
    _project(tmp_path, monkeypatch)
    result = {
        "val_f1": 0.27,
        "val_f1_threshold": 0.4,
        "ap_prevalence_lift": 1.6,
        "roc_auc": 0.81,
        "val_bpb": 0.26,
        "warm_start": {"loaded": 280, "model_tensors": 288, "reason": None},
        "is_success": False,
    }

    class Supervisor:
        def run(self, cmd, **kwargs):
            (tmp_path / "run_result.json").write_text(json.dumps(result))

    got = ablation._run_one("cfg.json", 0, 60, str(tmp_path / "cell.log"), Supervisor())
    assert got["status"] == "OK"
    assert (got["val_f1"], got["val_f1_threshold"]) == (0.27, 0.4)
    assert (got["ap_prevalence_lift"], got["roc_auc"]) == (1.6, 0.81)
    assert (got["warm_start_loaded"], got["warm_start_tensors"]) == (280, 288)

    monkeypatch.setattr(ablation, "_run_one", lambda *a: dict(got))
    assert ablation.main() == 0
    rows = list(csv.DictReader(open(tmp_path / "ablation.csv")))
    assert [(r["condition"], r["val_f1"], r["warm_start_loaded"]) for r in rows] == [
        ("baseline", "0.27", "280"),
        ("squeeze", "0.27", "280"),
    ]


@pytest.mark.parametrize("payload", [{}, {"warm_start": "malformed"}])
def test_a_result_without_a_warm_start_record_is_still_read(
    tmp_path, monkeypatch, payload
):
    """A run_result.json from before the record, or a malformed one."""
    monkeypatch.setattr(ablation, "PROJECT_ROOT", tmp_path)

    class Supervisor:
        def run(self, cmd, **kwargs):
            (tmp_path / "run_result.json").write_text(
                json.dumps({"val_f1": 0.27, **payload})
            )

    got = ablation._run_one("c.json", 0, 60, str(tmp_path / "c.log"), Supervisor())
    assert got["status"] == "OK" and got["val_f1"] == 0.27
    assert got["warm_start_loaded"] is None and got["warm_start_tensors"] is None
