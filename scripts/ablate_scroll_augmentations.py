#!/usr/bin/env python3
"""Phase 3 of ScrollPrize/villa #201 work: controlled short-train ablation
of the scroll-specific augmentations defined in scroll_augmentations.py.

Each (condition, seed) is a separate train.py subprocess started from a
*pristine* copy of the current best_model.pt. Configs differ only in
which single scroll augmentation is forced on (probability=1.0); all
other scroll-aug probabilities are forced off. The final val_bpb from
each run goes into a CSV and a per-condition summary table.

Six conditions:
    baseline, decohesion, warping, squeeze, z_dropout, intensity_drift

The harness:
  - backs up best_model.pt before the ablation begins
  - restores it before every individual run (so no run sees the previous
    one's promoted weights)
  - restores the original backup at the end (in case a run promoted)
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
  - no autoresearch loop currently using the GPU (the harness assumes the
    full GPU is available for short-train cycles).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from train import ExperimentConfig  # noqa: E402

AUGS = ["decohesion", "warping", "squeeze", "z_dropout", "intensity_drift"]
CONDITIONS = ["baseline"] + AUGS


def _build_condition_config(base_config_path: str, condition: str, budget: int) -> ExperimentConfig:
    """Load config.json, force exactly one scroll aug on (or none for baseline)."""
    cfg = ExperimentConfig.load(base_config_path)
    for a in AUGS:
        setattr(cfg, f"aug_scroll_{a}_p", 0.0)
    if condition != "baseline":
        setattr(cfg, f"aug_scroll_{condition}_p", 1.0)
    cfg.time_budget = budget
    cfg.pinned = False
    cfg.enforce_prize_gates = False  # never block on prize gates during ablation
    return cfg


def _run_one(
    cfg_path: str,
    seed: int,
    budget: int,
    log_path: str,
) -> dict:
    """Run one short-train subprocess. Returns a dict with val_bpb etc."""
    t0 = time.perf_counter()
    cmd = [
        "uv", "run", "python", "-u",
        "scripts/train_with_new_augs.py",
        "--config", cfg_path,
        "--seed", str(seed),
    ]
    timeout_s = budget + 240  # +4 min for imports / validation / IO
    with open(log_path, "w") as logf:
        try:
            subprocess.run(cmd, check=True, stdout=logf, stderr=subprocess.STDOUT, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            return {"status": "TIMEOUT", "elapsed_s": time.perf_counter() - t0}
        except subprocess.CalledProcessError as exc:
            return {"status": "FAILED", "elapsed_s": time.perf_counter() - t0, "rc": exc.returncode}
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
    p.add_argument("--budget", type=int, default=300, help="Per-run time budget in seconds (default 300).")
    p.add_argument("--seeds", type=int, default=3, help="Number of seeds per condition (default 3).")
    p.add_argument("--config", default="config.json", help="Base config to derive each ablation cell from.")
    p.add_argument("--out", default=None, help="Output CSV path (default reports/ablation_<timestamp>.csv).")
    p.add_argument("--conditions", nargs="*", default=None,
                   help="Limit to these conditions (e.g. --conditions baseline decohesion).")
    p.add_argument("--dry-run", action="store_true",
                   help="Print the plan and exit without running anything.")
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

    backup = Path("best_model.pt.ablation_backup")
    out_path = args.out or f"reports/ablation_{time.strftime('%Y-%m-%d_%H-%M-%S')}.csv"
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    log_dir = Path("reports/ablation_logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    total_runs = len(chosen) * args.seeds
    eta_s = total_runs * (args.budget + 60)
    print(f"# conditions: {chosen}")
    print(f"# seeds: {args.seeds}, budget: {args.budget}s")
    print(f"# total runs: {total_runs}, rough wall-clock ETA: {eta_s/60:.0f} min")
    print(f"# csv:  {out_path}")
    print(f"# logs: {log_dir}/")

    if args.dry_run:
        print("# --dry-run: not executing")
        return 0

    print(f"# backing up best_model.pt -> {backup}")
    shutil.copy("best_model.pt", backup)

    rows: list[dict] = []
    t_start = time.perf_counter()
    try:
        for cond in chosen:
            for seed in range(args.seeds):
                run_id = f"{cond}_seed{seed}"
                print(f"\n--- {run_id} ---")

                # Restore pristine checkpoint
                shutil.copy(backup, "best_model.pt")

                # Build condition-specific config
                cfg = _build_condition_config(args.config, cond, args.budget)
                cfg_path = f"config_temp_ablation_{run_id}.json"
                cfg.save(cfg_path)

                log_path = str(log_dir / f"{run_id}.log")
                result = _run_one(cfg_path, seed, args.budget, log_path)
                result["condition"] = cond
                result["seed"] = seed
                result["run_id"] = run_id
                rows.append(result)

                vb = result.get("val_bpb")
                vb_s = f"{vb:.6f}" if isinstance(vb, float) and not math.isnan(vb) else "n/a"
                print(f"  status={result['status']}  val_bpb={vb_s}  elapsed={result['elapsed_s']:.0f}s")

                # Cleanup temp config
                try:
                    os.remove(cfg_path)
                except OSError:
                    pass
    finally:
        print(f"\n# restoring best_model.pt from {backup}")
        shutil.copy(backup, "best_model.pt")

    total_elapsed = time.perf_counter() - t_start

    # Write CSV
    fieldnames = [
        "run_id", "condition", "seed", "status",
        "val_bpb", "train_loss", "avg_skel_dist",
        "avg_centerline_dice", "avg_cc_diff",
        "is_success", "elapsed_s",
    ]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\n# wrote {out_path}  ({len(rows)} rows, {total_elapsed/60:.1f} min total)")

    # Per-condition summary
    summary = _summarize(rows)
    if summary:
        # Sort by mean val_bpb (lower = better)
        ranked = sorted(summary.items(), key=lambda kv: kv[1]["mean"])
        print(f"\n{'condition':<20s} {'n':>3s} {'mean':>10s} {'stdev':>10s} {'min':>10s} {'max':>10s}")
        print("-" * 64)
        for cond, s in ranked:
            print(f"{cond:<20s} {s['n']:>3d} {s['mean']:>10.6f} {s['stdev']:>10.6f} {s['min']:>10.6f} {s['max']:>10.6f}")

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
