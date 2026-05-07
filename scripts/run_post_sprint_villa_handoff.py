#!/usr/bin/env python3
"""
Run the Villa-backed Scroll 2/3 handoff after an Autoresearch sprint.

The handoff is intentionally guarded: by default it refuses to run when the
Night/Day Shift training loop is active. Without --execute-* flags it only
refreshes manifests and preflight reports; use --preflight-only to allow that
non-GPU planning path while a sprint is active.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


ACTIVE_PROCESS_PATTERN = "run_autoresearch_loop.py|train.py|uv run python -u train.py"


def active_sprint_processes():
    result = subprocess.run(
        ["pgrep", "-af", ACTIVE_PROCESS_PATTERN],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or "pgrep failed")
    return [line for line in result.stdout.splitlines() if line.strip()]


def build_handoff_steps(args):
    python = args.python_executable
    inference_command = [
        python,
        "scripts/run_ranked_inference.py",
        "--ranked",
        args.ranked,
        "--limit",
        str(args.inference_limit),
        "--prediction-dir",
        args.prediction_dir,
        "--checkpoint",
        args.checkpoint,
        "--manifest",
        args.manifest,
    ]
    if args.execute_inference:
        inference_command.append("--execute")

    steps = [
        {
            "name": "ranked_inference",
            "gpu": bool(args.execute_inference),
            "command": inference_command,
        },
        {
            "name": "rerank_candidates",
            "gpu": False,
            "command": [
                python,
                "scripts/rank_scroll23_candidates.py",
                "--queue",
                args.queue,
                "--prediction-dir",
                args.prediction_dir,
                "--out",
                args.ranked,
            ],
        },
        {
            "name": "build_lasagna_fiber_worklist",
            "gpu": False,
            "command": [
                python,
                "scripts/build_lasagna_fiber_worklist.py",
                "--ranked",
                args.ranked,
                "--limit",
                str(args.worklist_limit),
            ],
        },
    ]

    for index in range(args.evidence_limit):
        out_dir = Path(args.evidence_root) / f"candidate_{index:03d}"
        command = [
            python,
            "scripts/run_villa_prize_evidence_chain.py",
            "--ranked",
            args.ranked,
            "--candidate-index",
            str(index),
            "--out-dir",
            str(out_dir),
            "--checkpoint",
            args.checkpoint,
        ]
        if args.execute_evidence:
            command.append("--execute")
        else:
            command.extend(
                [
                    "--preflight",
                    "--execute",
                    "--preflight-report",
                    str(out_dir / "preflight_report.json"),
                ]
            )
        steps.append(
            {
                "name": f"evidence_candidate_{index:03d}",
                "gpu": bool(args.execute_evidence),
                "command": command,
            }
        )

    return steps


def write_plan(path, active_processes, steps, status):
    payload = {
        "status": status,
        "active_processes": active_processes,
        "steps": steps,
    }
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def resolve_status(active_processes, steps, force=False, preflight_only=False):
    if not active_processes or force:
        return "READY"
    if preflight_only:
        if any(step.get("gpu") for step in steps):
            return "BLOCKED_GPU_STEP_ACTIVE_SPRINT"
        return "READY_ACTIVE_SPRINT_NON_GPU"
    return "BLOCKED_ACTIVE_SPRINT"


def run_steps(steps):
    for step in steps:
        subprocess.run(step["command"], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ranked", default="reports/scroll23_ranked_candidates.tsv")
    parser.add_argument("--queue", default="reports/scroll23_search_queue.tsv")
    parser.add_argument("--prediction-dir", default="predictions")
    parser.add_argument("--checkpoint", default="best_model.pt")
    parser.add_argument("--manifest", default="reports/scroll23_inference_commands.sh")
    parser.add_argument("--evidence-root", default="reports/scroll23_evidence")
    parser.add_argument("--plan-out", default="reports/post_sprint_villa_handoff_plan.json")
    parser.add_argument("--inference-limit", type=int, default=8)
    parser.add_argument("--worklist-limit", type=int, default=12)
    parser.add_argument("--evidence-limit", type=int, default=2)
    parser.add_argument("--execute-inference", action="store_true")
    parser.add_argument("--execute-evidence", action="store_true")
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Allow non-GPU manifest/preflight steps to run while a sprint is active",
    )
    parser.add_argument("--force", action="store_true", help="Allow execution while a sprint process is active")
    parser.add_argument("--python-executable", default=sys.executable)
    args = parser.parse_args()

    active = active_sprint_processes()
    steps = build_handoff_steps(args)
    status = resolve_status(active, steps, force=args.force, preflight_only=args.preflight_only)
    plan = write_plan(args.plan_out, active, steps, status)
    print(json.dumps(plan, indent=2))

    if not status.startswith("READY"):
        raise SystemExit(2)

    run_steps(steps)


if __name__ == "__main__":
    main()
