#!/usr/bin/env python3
"""
Run the Villa-backed Scroll 2/3 handoff after an Autoresearch sprint.

The handoff is intentionally guarded: by default it refuses to run while
research work is using the GPU (the loop, a noise probe, an ablation or a
re-score; see active_sprint_processes). Without --execute-* flags it only
refreshes manifests and preflight reports; use --preflight-only to allow that
non-GPU planning path while a sprint is active.
Use --step-timeout SECONDS to bound each command, plus worker cleanup; the
plan records completion, interruption, or the first named failure.

An executing GPU handoff holds this checkout's research lock until its child
process groups have ended. --force can override the other-checkout name scan,
but cannot bypass this checkout's lock or unsupervised training runs.
"""

import argparse
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):  # run as a script: make `scripts` importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import loop_control  # noqa: E402
from scripts.process_supervisor import ProcessSupervisor, stops_interrupt  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
HANDOFF_ARGS = {
    "run_post_sprint_villa_handoff.py",
    "scripts.run_post_sprint_villa_handoff",
}
HANDOFF_COMMAND_PATTERN = re.compile(
    r"(^|[\s/\"'])(?:run_post_sprint_villa_handoff\.py|scripts\.run_post_sprint_villa_handoff)(?=$|[\s\"'])"
)

# By name, in any checkout, since the GPU is shared: what takes the loop's lock,
# and the training each runs (the noise probe's trials train in-process in
# run_noise_probe.py). After a space or "/" and up to a space or the end, so
# tests/test_f1_noise_probe.py in a pytest run is not one.
_ACTIVE_NAMES = sorted(
    loop_control.LOCK_HOLDER_ARGS
    | {Path(script).name for script in loop_control.RUN_SCRIPTS}
    | loop_control.RUN_MODULES
    | {"run_noise_probe.py"}
)
ACTIVE_PROCESS_PATTERN = (
    "(^|[ /])(" + "|".join(re.escape(name) for name in _ACTIVE_NAMES) + ")( |$)"
)


def active_sprint_processes(repo=REPO):
    """What is using the GPU for research: this checkout's lock holder (the
    loop, a noise probe, an ablation or a re-score), a training run going in
    it that no supervisor owns, and any process of theirs in any checkout. The
    pattern once named only the loop and train.py, so a noise probe, an
    ablation or a re-score let the GPU steps start beside it."""
    active = []
    try:
        pid = loop_control.running_pid(repo)
    except Exception as exc:  # a lock that cannot be read blocks, as one held
        pid = None
        active.append(f"{repo / 'autoresearch.lock'}: {exc!r}")
    if pid is not None:
        active.append(f"{pid} holds {repo / 'autoresearch.lock'}")
    for run in loop_control.unsupervised_runs(repo, supervisor=pid):
        active.append(f"unsupervised training run: {loop_control.describe_run(*run)}")
    return active + _named_processes()


def _named_processes():
    """pgrep's lines for the pattern, in any checkout."""
    result = subprocess.run(
        ["pgrep", "-af", ACTIVE_PROCESS_PATTERN],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or "pgrep failed")
    # pgrep sees this command and possibly its `uv run` launcher. Neither is
    # competing work. Other handoffs count only when they request GPU steps.
    ancestors = {os.getpid()}
    parent = os.getppid()
    while parent > 1 and parent not in ancestors:
        ancestors.add(parent)
        try:
            parent = int(loop_control._stat_fields(parent)[1])
        except (OSError, ValueError, IndexError):
            break
    active = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        try:
            pid = int(line.split()[0])
        except (ValueError, IndexError):
            active.append(line)  # uncertain scan output must not mean idle
            continue
        if pid == os.getpid():
            continue
        try:
            args = [
                os.fsdecode(a)
                for a in Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
                if a
            ]
        except FileNotFoundError:
            continue
        except OSError:
            active.append(line)
            continue
        if pid in ancestors and _shell_handoff_launcher(args):
            continue
        if any(Path(arg).name in HANDOFF_ARGS for arg in args):
            if pid in ancestors or not any(
                arg in {"--execute-inference", "--execute-evidence"} for arg in args
            ):
                continue
        active.append(line)
    return active


def _shell_handoff_launcher(args):
    """A shell waiting on our launch, not a Python research supervisor.

    With ``bash -c 'python .../handoff.py --execute-inference; :'`` the entire
    command is one argv token. pgrep matches it, although the shell itself is
    only waiting. Restrict this exception to shell -c command strings and our
    ancestors; actual research processes remain visible to the normal scan.
    """
    if not args or Path(args[0]).name not in {
        "sh",
        "bash",
        "dash",
        "zsh",
        "ksh",
        "fish",
    }:
        return False
    for index, arg in enumerate(args[1:], 1):
        if not arg.startswith("-") or arg == "--":
            break  # a shell script's later arguments are not interpreter flags
        if not arg.startswith("--") and "c" in arg[1:]:
            return (
                index + 1 < len(args)
                and HANDOFF_COMMAND_PATTERN.search(args[index + 1]) is not None
            )
    return False


def build_handoff_steps(args):
    python = args.python_executable
    steps = [
        {
            "name": "audit_villa_upstream",
            "gpu": False,
            "command": [
                python,
                "scripts/archive/audit_villa_upstream.py",
                "--out",
                args.villa_audit,
            ],
        },
        {
            "name": "plan_villa_prize_opportunities",
            "gpu": False,
            "command": [
                python,
                "scripts/plan_villa_prize_opportunities.py",
                "--audit",
                args.villa_audit,
                "--out",
                args.villa_opportunities,
            ],
        },
        {
            "name": "review_villa_pin",
            "gpu": False,
            "command": [
                python,
                "scripts/review_villa_pin.py",
                "--audit",
                args.villa_audit,
                "--out",
                args.villa_pin_review,
            ],
        },
        {
            "name": "build_villa_component_coverage",
            "gpu": False,
            "command": [
                python,
                "scripts/build_villa_component_coverage.py",
                "--out-json",
                args.villa_component_coverage_json,
                "--out-md",
                args.villa_component_coverage_md,
            ],
        },
        {
            "name": "build_volume_cartographer_readiness",
            "gpu": False,
            "command": [
                python,
                "scripts/build_volume_cartographer_readiness.py",
                "--sample-zarr",
                args.volume_cartographer_sample_zarr,
                "--out-json",
                args.volume_cartographer_readiness_json,
                "--out-md",
                args.volume_cartographer_readiness_md,
            ],
        },
    ]

    inference_command = [
        python,
        "scripts/inference/run_ranked_inference.py",
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

    steps.extend(
        [
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
    )

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

    steps.append(
        {
            "name": "summarize_villa_evidence_preflight",
            "gpu": False,
            "command": [
                python,
                "scripts/summarize_villa_evidence_preflight.py",
                "--root",
                args.evidence_root,
                "--out-json",
                args.preflight_summary_json,
                "--out-tsv",
                args.preflight_summary_tsv,
                "--gpu-queue",
                args.gpu_queue,
            ],
        }
    )
    steps.append(
        {
            "name": "build_villa_prize_action_matrix",
            "gpu": False,
            "command": [
                python,
                "scripts/build_villa_prize_action_matrix.py",
                "--opportunities",
                args.villa_opportunities,
                "--preflight",
                args.preflight_summary_json,
                "--out-json",
                args.villa_action_matrix_json,
                "--out-md",
                args.villa_action_matrix_md,
            ],
        }
    )
    steps.append(
        {
            "name": "build_villa_review_manifest",
            "gpu": False,
            "command": [
                python,
                "scripts/build_villa_review_manifest.py",
                "--gpu-queue",
                args.gpu_queue,
                "--action-matrix",
                args.villa_action_matrix_json,
                "--ranked",
                args.ranked,
                "--evidence-root",
                args.evidence_root,
                "--checkpoint",
                args.checkpoint,
                "--out-json",
                args.villa_review_manifest_json,
                "--out-md",
                args.villa_review_manifest_md,
                "--python-executable",
                python,
            ],
        }
    )

    return steps


def write_plan(
    path, active_processes, steps, status, *, step_timeout=None, failure=None
):
    payload = {
        "status": status,
        "active_processes": active_processes,
        "steps": steps,
        "step_timeout_seconds": step_timeout,
        "failure": failure,
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


def positive_seconds(value):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise argparse.ArgumentTypeError(
            "step timeout must be positive and finite"
        ) from exc
    if isinstance(value, bool) or not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("step timeout must be positive and finite")
    return number


class HandoffStepError(RuntimeError):
    def __init__(self, step, kind, message, *, timeout=None, returncode=None):
        super().__init__(f"Handoff step {step!r}: {message}")
        self.details = {
            "step": step,
            "kind": kind,
            "message": message,
            "timeout_seconds": timeout,
            "returncode": returncode,
        }


def run_steps(steps, *, step_timeout=None):
    if step_timeout is not None:
        step_timeout = positive_seconds(step_timeout)
    supervisor = ProcessSupervisor()
    with stops_interrupt():
        for step in steps:
            try:
                supervisor.run(
                    step["command"], check=True, timeout=step_timeout, cwd=REPO
                )
            except subprocess.TimeoutExpired as exc:
                raise HandoffStepError(
                    step["name"],
                    "timeout",
                    f"timed out after {step_timeout:g} seconds; worker group cleaned up",
                    timeout=step_timeout,
                ) from exc
            except subprocess.CalledProcessError as exc:
                raise HandoffStepError(
                    step["name"],
                    "exit",
                    f"command exited with code {exc.returncode}",
                    returncode=exc.returncode,
                ) from exc
            except OSError as exc:
                raise HandoffStepError(step["name"], "launch", str(exc)) from exc


def _validate_plan_path(path):
    """A report must never open the research lock, even through an alias.

    Closing any descriptor for that inode releases this process's POSIX lock.
    On a blocked launch it would instead erase the other holder's PID record.
    Check before acquiring the lock as well as before writing a refusal plan.
    """
    output = Path(path)
    lock = REPO / "autoresearch.lock"
    if output.resolve() == lock.resolve():
        raise ValueError("plan output must not alias autoresearch.lock")
    identities = []
    for candidate in (output, lock):
        try:
            info = candidate.stat()
        except FileNotFoundError:
            identities.append(None)
        else:
            identities.append((info.st_dev, info.st_ino))
    if identities[0] is not None and identities[0] == identities[1]:
        raise ValueError("plan output must not alias autoresearch.lock")


def execute_handoff(
    steps, plan_out, *, force=False, preflight_only=False, step_timeout=None
):
    """Keep GPU steps mutually exclusive with this checkout's research work."""
    try:
        if step_timeout is not None:
            step_timeout = positive_seconds(step_timeout)
        _validate_plan_path(plan_out)
    except (OSError, RuntimeError, ValueError, argparse.ArgumentTypeError) as exc:
        print(f"Cannot prepare handoff: {exc}", file=sys.stderr)
        return 2
    lock = None
    try:
        if any(step.get("gpu") for step in steps):
            try:
                lock = loop_control.acquire_lock(REPO / "autoresearch.lock")
            except OSError as exc:
                plan = write_plan(
                    plan_out,
                    [f"checkout lock: {exc}"],
                    steps,
                    "BLOCKED_LOCAL_LOCK",
                    step_timeout=step_timeout,
                )
                print(json.dumps(plan, indent=2))
                return 2
            # Not running_pid: with our lock held, the holder it names is us.
            local_runs = loop_control.unsupervised_runs(REPO)
            active = [
                f"unsupervised training run: {loop_control.describe_run(*run)}"
                for run in local_runs
            ]
            active += _named_processes()
            status = (
                "BLOCKED_LOCAL_TRAINING"
                if local_runs
                else resolve_status(
                    active, steps, force=force, preflight_only=preflight_only
                )
            )
        else:
            active = active_sprint_processes(REPO)
            status = resolve_status(
                active, steps, force=force, preflight_only=preflight_only
            )
        plan = write_plan(plan_out, active, steps, status, step_timeout=step_timeout)
        print(json.dumps(plan, indent=2))
        if not status.startswith("READY"):
            return 2
        try:
            run_steps(steps, step_timeout=step_timeout)
        except HandoffStepError as exc:
            status = (
                "FAILED_TIMEOUT" if exc.details["kind"] == "timeout" else "FAILED_STEP"
            )
            write_plan(
                plan_out,
                active,
                steps,
                status,
                step_timeout=step_timeout,
                failure=exc.details,
            )
            print(f"{exc}. Report: {plan_out}", file=sys.stderr)
            return 124 if status == "FAILED_TIMEOUT" else 1
        except KeyboardInterrupt:
            write_plan(plan_out, active, steps, "STOPPED", step_timeout=step_timeout)
            raise
        write_plan(plan_out, active, steps, "COMPLETE", step_timeout=step_timeout)
        print(f"Handoff complete. Report: {plan_out}")
        return 0
    finally:
        # ProcessSupervisor cleans the child group before run_steps unwinds,
        # so a watchdog cannot acquire this lock before GPU workers are stopped.
        if lock is not None:
            lock.close()


def main(argv=None):
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--ranked", default="reports/scroll23_ranked_candidates.tsv")
    parser.add_argument("--queue", default="reports/scroll23_search_queue.tsv")
    parser.add_argument("--prediction-dir", default="predictions")
    parser.add_argument("--checkpoint", default="best_model.pt")
    parser.add_argument("--manifest", default="reports/scroll23_inference_commands.sh")
    parser.add_argument("--evidence-root", default="reports/scroll23_evidence")
    parser.add_argument(
        "--plan-out", default="reports/post_sprint_villa_handoff_plan.json"
    )
    parser.add_argument("--villa-audit", default="reports/villa_upstream_audit.json")
    parser.add_argument(
        "--villa-opportunities", default="reports/villa_prize_opportunities.json"
    )
    parser.add_argument("--villa-pin-review", default="reports/villa_pin_review.json")
    parser.add_argument(
        "--villa-component-coverage-json",
        default="reports/villa_component_coverage.json",
    )
    parser.add_argument(
        "--villa-component-coverage-md", default="reports/villa_component_coverage.md"
    )
    parser.add_argument(
        "--volume-cartographer-sample-zarr",
        default="local_data/PHercParis2Fr47/surface_volume.zarr/0",
    )
    parser.add_argument(
        "--volume-cartographer-readiness-json",
        default="reports/volume_cartographer_readiness.json",
    )
    parser.add_argument(
        "--volume-cartographer-readiness-md",
        default="reports/volume_cartographer_readiness.md",
    )
    parser.add_argument(
        "--preflight-summary-json",
        default="reports/scroll23_evidence_preflight_summary.json",
    )
    parser.add_argument(
        "--preflight-summary-tsv",
        default="reports/scroll23_evidence_preflight_summary.tsv",
    )
    parser.add_argument(
        "--gpu-queue", default="reports/scroll23_gpu_inference_queue.tsv"
    )
    parser.add_argument(
        "--villa-action-matrix-json", default="reports/villa_prize_action_matrix.json"
    )
    parser.add_argument(
        "--villa-action-matrix-md", default="reports/villa_prize_action_matrix.md"
    )
    parser.add_argument(
        "--villa-review-manifest-json", default="reports/villa_review_manifest.json"
    )
    parser.add_argument(
        "--villa-review-manifest-md", default="reports/villa_review_manifest.md"
    )
    parser.add_argument("--inference-limit", type=int, default=8)
    parser.add_argument("--worklist-limit", type=int, default=12)
    parser.add_argument("--evidence-limit", type=int, default=12)
    parser.add_argument("--execute-inference", action="store_true")
    parser.add_argument("--execute-evidence", action="store_true")
    parser.add_argument(
        "--step-timeout",
        type=positive_seconds,
        metavar="SECONDS",
        help="Maximum seconds for each command, plus worker cleanup; timeout stops the handoff (default: no deadline)",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Allow non-GPU manifest/preflight steps to run while a sprint is active",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Override the other-checkout process scan; never bypass this checkout's lock or training runs",
    )
    parser.add_argument("--python-executable", default=sys.executable)
    args = parser.parse_args(argv)
    # Lock ownership is verified against /proc/<pid>/cwd. Relative commands,
    # data paths and the lock must all refer to this same checkout.
    os.chdir(REPO)
    steps = build_handoff_steps(args)
    try:
        return execute_handoff(
            steps,
            args.plan_out,
            force=args.force,
            preflight_only=args.preflight_only,
            step_timeout=args.step_timeout,
        )
    except KeyboardInterrupt:
        print(
            "Handoff stopped; supervised child processes have been cleaned up.",
            file=sys.stderr,
        )
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
