#!/usr/bin/env python3
"""Phase 3 of ScrollPrize/villa #201 work: controlled short-train ablation
of the scroll-specific augmentations defined in scroll_augmentations.py.

Each (condition, seed) is a separate train.py subprocess that warm-starts
from the current best_model.pt. Configs differ only in which single scroll
augmentation is forced on (probability=1.0); all other scroll-aug
probabilities are forced off. The final val_bpb from each run goes into a
CSV and a per-condition summary table.

Six conditions:
    baseline, decohesion, warping, squeeze, z_dropout, intensity_drift

The harness:
  - runs each cell as an experiment run (checkpoint_out), so no run writes
    the loop's files (best_model.pt, last_model.pt, history.tsv,
    results.tsv, prize_readiness.tsv) and every run starts from the same
    incumbent. It used to promote into best_model.pt and copy a backup
    back, leaving its rows in the loop's logs and, at the end, putting back
    a backup over any promotion the loop had made meanwhile.
  - holds this checkout's lock (autoresearch.lock) for the whole ablation,
    as the noise probe does, so it refuses to start beside the loop and the
    watchdog cannot start the loop under it; both write and read
    run_result.json here. ./stop.sh stops it, and its cell, between runs or
    mid-run
  - clears run_result.json before each run, so a run that writes none is
    not credited with the previous run's result
  - runs each cell in its own process group, so a timeout or a stop ends
    the trainer itself, not just its `uv run` launcher
  - never modifies train.py — the wrapper script monkey-patches at import

Usage:
    # Quick smoke (one seed per condition, very short budget)
    uv run python scripts/ablate_scroll_augmentations.py --budget 60 --seeds 1

    # Real ablation (3 seeds, 5-minute budget per run; ~100 min total)
    uv run python scripts/ablate_scroll_augmentations.py --budget 300 --seeds 3

    # Custom output path
    uv run python scripts/ablate_scroll_augmentations.py --out reports/ablation_v1.csv

Prerequisites:
  - best_model.pt present in cwd
  - the loop stopped (./stop.sh); the harness refuses to start otherwise.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import os
import signal
import statistics
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.loop_control import acquire_lock, running_pid  # noqa: E402
from scripts.process_supervisor import ProcessSupervisor  # noqa: E402
from scripts.training.train import ExperimentConfig  # noqa: E402

AUGS = [
    "decohesion",
    "warping",
    "squeeze",
    "z_dropout",
    "intensity_drift",
    "sheet_compression",
    "thick_slice",
    "rician_noise",
    "blank_rectangles",
]
CONDITIONS = ["baseline"] + AUGS


def _build_condition_config(
    base_config_path: str, condition: str, budget: int, checkpoint_out: str
) -> ExperimentConfig:
    """Load config.json, force exactly one scroll aug on (or none for baseline).
    checkpoint_out makes the run an experiment run: it leaves the loop's
    files alone (train.save_cycle_checkpoints)."""
    cfg = ExperimentConfig.load(base_config_path)
    cfg.checkpoint_out = checkpoint_out
    for a in AUGS:
        setattr(cfg, f"aug_scroll_{a}_p", 0.0)
    if condition != "baseline":
        setattr(cfg, f"aug_scroll_{condition}_p", 1.0)
    cfg.time_budget = budget
    cfg.pinned = False
    cfg.enforce_prize_gates = False  # never block on prize gates during ablation
    return cfg


def _interrupt(*args):
    raise KeyboardInterrupt


def _run_one(
    cfg_path: str,
    seed: int,
    budget: int,
    log_path: str,
    supervisor: ProcessSupervisor,
) -> dict:
    """Run one short-train subprocess. Returns a dict with val_bpb etc.

    The supervisor starts it in a new session and ends the whole group on a
    timeout or a stop: killing only `uv run` left the trainer running, on the
    GPU and writing run_result.json during later cells."""
    t0 = time.perf_counter()
    cmd = [
        "uv",
        "run",
        "python",
        "-u",
        "scripts/train_with_new_augs.py",
        "--config",
        cfg_path,
        "--seed",
        str(seed),
    ]
    timeout_s = budget + 240  # +4 min for imports / validation / IO
    with open(log_path, "w") as logf:
        try:
            supervisor.run(
                cmd,
                check=True,
                stdout=logf,
                stderr=subprocess.STDOUT,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            return {"status": "TIMEOUT", "elapsed_s": time.perf_counter() - t0}
        except subprocess.CalledProcessError as exc:
            return {
                "status": "FAILED",
                "elapsed_s": time.perf_counter() - t0,
                "rc": exc.returncode,
            }
    elapsed = time.perf_counter() - t0

    result_path = PROJECT_ROOT / "run_result.json"
    if not result_path.exists():
        return {"status": "NO_RESULT", "elapsed_s": elapsed}

    with result_path.open() as f:
        res = json.load(f)
    return {
        "status": "OK",
        "elapsed_s": elapsed,
        "val_bpb": res.get("val_bpb"),
        "train_loss": res.get("train_loss"),
        "avg_skel_dist": res.get("avg_skel_dist"),
        "avg_centerline_dice": res.get("avg_centerline_dice"),
        "avg_cc_diff": res.get("avg_cc_diff"),
        "is_success": res.get("is_success", False),
    }


def _summarize(rows: list[dict]) -> dict[str, dict]:
    """Aggregate per-condition: count, mean, stdev, min/max val_bpb."""
    by_condition: dict[str, list[float]] = {}
    for r in rows:
        if r["status"] != "OK" or r.get("val_bpb") is None:
            continue
        by_condition.setdefault(r["condition"], []).append(r["val_bpb"])

    out = {}
    for cond, vals in by_condition.items():
        out[cond] = {
            "n": len(vals),
            "mean": statistics.mean(vals),
            "stdev": statistics.stdev(vals) if len(vals) >= 2 else float("nan"),
            "min": min(vals),
            "max": max(vals),
        }
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--budget",
        type=int,
        default=300,
        help="Per-run time budget in seconds (default 300).",
    )
    p.add_argument(
        "--seeds",
        type=int,
        default=3,
        help="Number of seeds per condition (default 3).",
    )
    p.add_argument(
        "--config",
        default="config.json",
        help="Base config to derive each ablation cell from.",
    )
    p.add_argument(
        "--out",
        default=None,
        help="Output CSV path (default reports/ablation_<timestamp>.csv).",
    )
    p.add_argument(
        "--conditions",
        nargs="*",
        default=None,
        help="Limit to these conditions (e.g. --conditions baseline decohesion).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan and exit without running anything.",
    )
    args = p.parse_args()

    os.chdir(PROJECT_ROOT)  # so relative paths work the same as run_autoresearch_loop

    chosen = args.conditions if args.conditions else CONDITIONS
    invalid = [c for c in chosen if c not in CONDITIONS]
    if invalid:
        print(f"error: unknown conditions: {invalid}", file=sys.stderr)
        return 2

    if not Path("best_model.pt").exists():
        print("error: best_model.pt not found", file=sys.stderr)
        return 1
    try:
        pid = running_pid(PROJECT_ROOT)
        holder = f"PID {pid}" if pid else None
    except (OSError, RuntimeError) as exc:
        holder = f"unidentified: {exc}"
    if holder:
        print(
            f"error: autoresearch work ({holder}) runs in this checkout; "
            "stop it first (./stop.sh): the loop and these runs share "
            "run_result.json and best_model.pt",
            file=sys.stderr,
        )
        return 1

    out_path = args.out or f"reports/ablation_{time.strftime('%Y-%m-%d_%H-%M-%S')}.csv"
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    log_dir = Path("reports/ablation_logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    total_runs = len(chosen) * args.seeds
    eta_s = total_runs * (args.budget + 60)
    print(f"# conditions: {chosen}")
    print(f"# seeds: {args.seeds}, budget: {args.budget}s")
    print(f"# total runs: {total_runs}, rough wall-clock ETA: {eta_s / 60:.0f} min")
    print(f"# csv:  {out_path}")
    print(f"# logs: {log_dir}/")

    if args.dry_run:
        print("# --dry-run: not executing")
        return 0

    # Held until the end: the watchdog restarts a loop that is down but not
    # paused, and start.sh refuses while the lock is held. loop_control knows
    # this script, so ./stop.sh can stop it (SIGTERM ends the current cell).
    try:
        lock = acquire_lock(str(PROJECT_ROOT / "autoresearch.lock"))
    except BlockingIOError:
        print(
            "error: autoresearch work took this checkout's lock; stop it first "
            "(./stop.sh)",
            file=sys.stderr,
        )
        return 1
    supervisor = ProcessSupervisor()
    previous = signal.signal(signal.SIGTERM, _interrupt)
    rows: list[dict] = []
    t_start = time.perf_counter()
    try:
        for cond in chosen:
            for seed in range(args.seeds):
                run_id = f"{cond}_seed{seed}"
                print(f"\n--- {run_id} ---")

                # A run that writes no result must not read the previous one's.
                if os.path.exists("run_result.json"):
                    os.remove("run_result.json")

                # Build condition-specific config
                checkpoint = str(log_dir / f"{run_id}.pt")
                cfg = _build_condition_config(
                    args.config, cond, args.budget, checkpoint
                )
                cfg_path = f"config_temp_ablation_{run_id}.json"
                cfg.save(cfg_path)

                log_path = str(log_dir / f"{run_id}.log")
                try:
                    result = _run_one(cfg_path, seed, args.budget, log_path, supervisor)
                finally:
                    # The temp config, and the run's checkpoints (only its
                    # metrics are used; eval_every_steps adds .step<N>.pt).
                    for path in [
                        cfg_path,
                        checkpoint,
                        *glob.glob(f"{checkpoint}.step*.pt"),
                    ]:
                        try:
                            os.remove(path)
                        except OSError:
                            pass
                result["condition"] = cond
                result["seed"] = seed
                result["run_id"] = run_id
                rows.append(result)

                vb = result.get("val_bpb")
                vb_s = (
                    f"{vb:.6f}"
                    if isinstance(vb, float) and not math.isnan(vb)
                    else "n/a"
                )
                print(
                    f"  status={result['status']}  val_bpb={vb_s}  elapsed={result['elapsed_s']:.0f}s"
                )
    except KeyboardInterrupt:
        print(f"\n# stopped after {len(rows)} of {total_runs} runs", file=sys.stderr)
    finally:
        signal.signal(signal.SIGTERM, previous)
        try:
            supervisor.stop()
        finally:
            lock.close()

    total_elapsed = time.perf_counter() - t_start

    # Write CSV
    fieldnames = [
        "run_id",
        "condition",
        "seed",
        "status",
        "val_bpb",
        "train_loss",
        "avg_skel_dist",
        "avg_centerline_dice",
        "avg_cc_diff",
        "is_success",
        "elapsed_s",
    ]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(
        f"\n# wrote {out_path}  ({len(rows)} rows, {total_elapsed / 60:.1f} min total)"
    )

    # Per-condition summary
    summary = _summarize(rows)
    if summary:
        # Sort by mean val_bpb (lower = better)
        ranked = sorted(summary.items(), key=lambda kv: kv[1]["mean"])
        print(
            f"\n{'condition':<20s} {'n':>3s} {'mean':>10s} {'stdev':>10s} {'min':>10s} {'max':>10s}"
        )
        print("-" * 64)
        for cond, s in ranked:
            print(
                f"{cond:<20s} {s['n']:>3d} {s['mean']:>10.6f} {s['stdev']:>10.6f} {s['min']:>10.6f} {s['max']:>10.6f}"
            )

        baseline_mean = summary.get("baseline", {}).get("mean")
        if baseline_mean is not None:
            print(f"\nbaseline mean: {baseline_mean:.6f}")
            print("delta vs baseline (negative = augmentation helps):")
            for cond, s in ranked:
                if cond == "baseline":
                    continue
                delta = s["mean"] - baseline_mean
                print(f"  {cond:<20s} {delta:+.6f}")
    else:
        print("no successful runs to summarize")

    return 0


if __name__ == "__main__":
    sys.exit(main())
