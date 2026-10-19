import shlex
import shutil
import subprocess
import time
from argparse import Namespace

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
# named only the loop and train.py, and missed the first five.
_ACTIVE = (
    "python scripts/f1_noise_probe.py --plan plan.json",
    "/venv/bin/python /repo/scripts/training/run_noise_probe.py --config c.json",
    "uv run python -u scripts/train_with_new_augs.py --config c.json --seed 1",
    "python -m scripts.reevaluate_best_model --update-stored",
    "python scripts/ablate_scroll_augmentations.py",
    "uv run python -u run_autoresearch_loop.py",
    "python scripts/training/train.py --smoke",
)
_INACTIVE = (
    "python -m pytest tests/test_f1_noise_probe.py",
    "python scripts/run_post_sprint_villa_handoff.py --preflight-only",
)


@pytest.mark.skipif(not shutil.which("pgrep"), reason="needs pgrep")
def test_the_pattern_finds_every_lock_holder_and_its_training():
    """Through pgrep itself, whose extended regular expressions the pattern is."""
    procs = []
    try:
        for i, cmd in enumerate(_ACTIVE + _INACTIVE):
            args = " ".join(shlex.quote(a) for a in shlex.split(cmd)[1:])
            procs.append(
                subprocess.Popen(
                    [
                        "bash",
                        "-c",
                        f'exec -a handoff-probe-{i} python3 -c "'
                        f'import time; time.sleep(30)" {args}',
                    ]  # fmt: skip
                )
            )
        time.sleep(1)
        found = subprocess.run(
            ["pgrep", "-af", handoff.ACTIVE_PROCESS_PATTERN],
            capture_output=True,
            text=True,
        ).stdout
    finally:
        for proc in procs:
            proc.kill()
            proc.wait()
    for i, cmd in enumerate(_ACTIVE + _INACTIVE):
        assert (f"handoff-probe-{i} " in found) == (cmd in _ACTIVE), cmd


def test_the_pattern_names_every_script_that_takes_the_lock():
    for name in loop_control.LOCK_HOLDER_ARGS:
        assert name.replace(".", r"\.") in handoff.ACTIVE_PROCESS_PATTERN, name


def _quiet(monkeypatch, pid=None, runs=(), error=None):
    def running_pid(repo):
        if error:
            raise error
        return pid

    monkeypatch.setattr(loop_control, "running_pid", running_pid)
    monkeypatch.setattr(
        loop_control, "unsupervised_runs", lambda repo, supervisor=None: list(runs)
    )
    monkeypatch.setattr(handoff, "ACTIVE_PROCESS_PATTERN", "^no-such-process-ever$")


def test_the_lock_holder_counts_as_active(monkeypatch, tmp_path):
    """A noise probe, an ablation or a re-score in this checkout holds the lock."""
    _quiet(monkeypatch, pid=4242)
    active = handoff.active_sprint_processes(tmp_path)
    assert active == [f"4242 holds {tmp_path / 'autoresearch.lock'}"]
    assert handoff.resolve_status(active, []) == "BLOCKED_ACTIVE_SPRINT"


def test_a_lock_held_by_something_unidentified_counts_as_active(monkeypatch, tmp_path):
    _quiet(
        monkeypatch, error=RuntimeError("loop lock is held but contains no valid PID")
    )
    active = handoff.active_sprint_processes(tmp_path)
    assert len(active) == 1 and "no valid PID" in active[0]


def test_an_unsupervised_training_run_counts_as_active(monkeypatch, tmp_path):
    _quiet(monkeypatch, runs=[(777, 120.0, True)])
    active = handoff.active_sprint_processes(tmp_path)
    assert active == ["unsupervised training run: PID 777 (started by a loop or "
                      "ablation, running 2 min)"]  # fmt: skip


def test_nothing_running_is_ready(monkeypatch, tmp_path):
    _quiet(monkeypatch)
    assert handoff.active_sprint_processes(tmp_path) == []
