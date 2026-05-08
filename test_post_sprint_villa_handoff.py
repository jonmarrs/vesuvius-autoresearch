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
        "villa_audit": "villa_audit.json",
        "villa_opportunities": "villa_opportunities.json",
        "villa_pin_review": "villa_pin_review.json",
        "preflight_summary_json": "preflight_summary.json",
        "preflight_summary_tsv": "preflight_summary.tsv",
        "gpu_queue": "gpu_queue.tsv",
        "villa_action_matrix_json": "action_matrix.json",
        "villa_action_matrix_md": "action_matrix.md",
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
        "ranked_inference",
        "rerank_candidates",
        "build_lasagna_fiber_worklist",
        "evidence_candidate_000",
        "evidence_candidate_001",
        "summarize_villa_evidence_preflight",
        "build_villa_prize_action_matrix",
    ]
    assert steps[0]["command"][-1] == "villa_audit.json"
    assert steps[1]["command"][-1] == "villa_opportunities.json"
    assert steps[2]["command"][-1] == "villa_pin_review.json"
    assert steps[3]["gpu"] is False
    assert "--execute" not in steps[3]["command"]
    assert "--preflight-report" in steps[6]["command"]
    assert steps[6]["command"][-1] == "evidence/candidate_000/preflight_report.json"
    assert steps[6]["gpu"] is False
    assert "--root" in steps[-2]["command"]
    assert "--out-json" in steps[-2]["command"]
    assert "--out-tsv" in steps[-2]["command"]
    assert steps[-2]["command"][-1] == "gpu_queue.tsv"
    assert steps[-1]["name"] == "build_villa_prize_action_matrix"
    assert "--opportunities" in steps[-1]["command"]
    assert "--preflight" in steps[-1]["command"]
    assert steps[-1]["command"][-1] == "action_matrix.md"


def test_post_sprint_handoff_execute_flags_mark_gpu_steps():
    steps = build_handoff_steps(_args(execute_inference=True, execute_evidence=True, evidence_limit=1))

    assert steps[3]["gpu"] is True
    assert steps[3]["command"][-1] == "--execute"
    assert steps[6]["gpu"] is True
    assert "--preflight" not in steps[6]["command"]
    assert steps[6]["command"][-1] == "--execute"


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
