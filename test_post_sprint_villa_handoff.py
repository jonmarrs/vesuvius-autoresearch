from argparse import Namespace

from scripts.run_post_sprint_villa_handoff import build_handoff_steps, resolve_status, write_plan


def _args(**overrides):
    data = {
        "python_executable": "python",
        "ranked": "ranked.tsv",
        "queue": "queue.tsv",
        "prediction_dir": "predictions",
        "checkpoint": "best_model.pt",
        "manifest": "commands.sh",
        "evidence_root": "evidence",
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
        "ranked_inference",
        "rerank_candidates",
        "build_lasagna_fiber_worklist",
        "evidence_candidate_000",
        "evidence_candidate_001",
    ]
    assert steps[0]["gpu"] is False
    assert "--execute" not in steps[0]["command"]
    assert "--preflight-report" in steps[3]["command"]
    assert steps[3]["command"][-1] == "evidence/candidate_000/preflight_report.json"
    assert steps[3]["gpu"] is False


def test_post_sprint_handoff_execute_flags_mark_gpu_steps():
    steps = build_handoff_steps(_args(execute_inference=True, execute_evidence=True, evidence_limit=1))

    assert steps[0]["gpu"] is True
    assert steps[0]["command"][-1] == "--execute"
    assert steps[3]["gpu"] is True
    assert "--preflight" not in steps[3]["command"]
    assert steps[3]["command"][-1] == "--execute"


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
