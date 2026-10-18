"""docs/preregistration/2026-10-17_noise_probe_v3_pooled.md -- the registered analysis.

Pools the val_f1 of two identical-config noise-probe batches (each a probe.json written by f1_noise_probe.py),
estimates the run-to-run sigma with its chi-square interval, checks for a shift between batches, and gives
the rate at which a cycle that changes nothing clears a promotion tolerance.

f1_noise_probe.py checks its own trials against each other; this checks the batches against each other
first (`poolable`): one configuration, starting checkpoint and config file, one validation sample, no
repeated seed, and the same probe and training code unless a difference is named with
--allow-code-change after its diff has been read.

Usage: .venv/bin/python scripts/noise_probe_pooled.py --batch B1/probe.json --batch B2/probe.json \
    --incumbent 0.249348 --tolerance 0.01 --out reports/X.json [--allow-code-change PATH ...]

The committed result (reports/noise_probe_v3_pooled_2026-10-17.json) needs
--allow-code-change scripts/training/train.py: the registration names that one difference.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

from scipy import stats

PROTOCOL = "seeded-sample-400-v3+z1-27"
LIFT_GATE = 1.02  # train.LIFT_MARGIN: promotion needs ap_prevalence_lift > 1 + 0.02
SIGMA_AT_FIVE_PERCENT = 0.0043  # prediction 3: 0.01 / (1.645 * sqrt(2)), rounded
MIN_LAST_BATCH = 3
# f1_noise_probe.py's RUNNER and TRAINER, which it hashes beside the checkpoint and config file.
CODE_INPUTS = ("scripts/training/run_noise_probe.py", "scripts/training/train.py")


def _code_input(path: str) -> str | None:
    """The repository path of a hashed code input, or None for the checkpoint or config file."""
    for code in CODE_INPUTS:
        if path == code or path.endswith("/" + code):
            return code
    return None


def completed(probe: dict) -> list[dict]:
    """The trials of one batch that finished, as {val_f1, ap_lift, seed}."""
    if probe.get("protocol") != PROTOCOL:
        raise ValueError(f"protocol {probe.get('protocol')!r}, expected {PROTOCOL}")
    return [
        {
            "val_f1": r["metrics"]["val_f1"],
            "ap_lift": r["metrics"]["ap_prevalence_lift"],
            "seed": r["train_sampling_seed"],
        }
        for r in probe["runs"]
        if r.get("status") == "COMPLETE"
    ]


def poolable(probes: list[dict], allow_code=()) -> list[str]:
    """Raise unless the batches' finished trials are draws of one comparison; return the
    code inputs that differ between them, each of which allow_code must name.

    f1_noise_probe.py requires its trials to share one validation sample and prevalence,
    and checks that only within a batch that finished every trial. Pooling compares
    trials across batches, so the same must hold across all of them. The registration
    also fixes one configuration, starting checkpoint and config file, and fresh
    sampling seeds, and it names the one code difference it accepts."""
    problems = []
    if len(probes) != 2:
        problems.append(
            f"expected two batches, got {len(probes)}: the registered shift test compares two"
        )
    if any(p.get("scope") != "identical_config_repeatability" for p in probes):
        problems.append("a batch is not an identical-config repeatability probe")
    if probes[0].get("contract") is None or any(
        p.get("contract") != probes[0]["contract"] for p in probes
    ):
        problems.append("the batches' probe contracts differ or are missing")
    if any(p.get("config") != probes[0].get("config") for p in probes):
        problems.append("the batches' configurations differ")

    code, fixed = [], []
    for probe in probes:
        hashes = probe.get("input_hashes") or {}
        code.append({_code_input(k): v for k, v in hashes.items() if _code_input(k)})
        # The starting checkpoint's and the config file's, whatever their paths.
        fixed.append(sorted(v for k, v in hashes.items() if not _code_input(k)))
    if any(len(f) != 2 or f != fixed[0] for f in fixed):
        problems.append(
            "the batches' starting checkpoints or config files differ, or a hash is missing"
        )
    changed = []
    for name in CODE_INPUTS:
        values = [c.get(name) for c in code]
        if None in values:
            problems.append(f"a batch has no hash for {name}")
        elif len(set(values)) > 1:
            changed.append(name)
            if name not in allow_code:
                problems.append(
                    f"{name} differs between the batches; read its diff, then pass"
                    f" --allow-code-change {name} if no trial depends on it"
                )

    finished = [r for p in probes for r in p["runs"] if r.get("status") == "COMPLETE"]

    def sample(run):
        return run.get("validation_diag"), run["metrics"].get("val_positive_rate")

    def recorded(run):
        diag, prevalence = sample(run)
        return (
            isinstance(diag, dict)
            and bool(diag.get("inputs_sha256"))
            and isinstance(prevalence, float)
            and math.isfinite(prevalence)
        )

    if not all(recorded(r) for r in finished):
        problems.append("a finished trial does not record its validation sample")
    elif any(sample(r) != sample(finished[0]) for r in finished):
        problems.append(
            "validation inputs, sample counts or prevalence differ between trials"
        )
    seeds = [r["train_sampling_seed"] for r in finished]
    if len(set(seeds)) != len(seeds):
        problems.append("a sampling seed repeats, so a trial replays another")
    if problems:
        raise ValueError("not poolable: " + "; ".join(problems))
    return changed


def sigma_interval(sd: float, df: int, level: float = 0.95) -> tuple[float, float]:
    """Chi-square interval for a normal SD estimated with `df` degrees of freedom."""
    a = (1 - level) / 2
    return (
        sd * math.sqrt(df / stats.chi2.ppf(1 - a, df)),
        sd * math.sqrt(df / stats.chi2.ppf(a, df)),
    )


def false_promotion(tolerance: float, sigma: float) -> float:
    """P(N(0, 2 sigma^2) > tolerance): a no-change cycle against a stored draw."""
    z = tolerance / (math.sqrt(2) * sigma)
    return 0.5 * math.erfc(z / math.sqrt(2))


def july_tolerance(sigma: float) -> float:
    """The 2026-07 derivation: a ~5% one-sided false-promotion rate."""
    return 1.645 * math.sqrt(2) * sigma


def analyse(batches: list[list[dict]], incumbent: float, tolerance: float) -> dict:
    if len(batches) != 2:
        raise ValueError(f"{len(batches)} batches; the registered analysis pools two")
    # Batch 1 needs two trials for its SD, the centre of prediction 1.
    if len(batches[-1]) < MIN_LAST_BATCH or len(batches[0]) < 2:
        return {
            "status": "INSUFFICIENT",
            "completed": [len(b) for b in batches],
        }
    f1 = [[t["val_f1"] for t in b] for b in batches]
    every = [v for b in f1 for v in b]
    sd = statistics.stdev(every)
    df = len(every) - 1
    variances = [statistics.variance(b) for b in f1]
    within_df = sum(len(b) - 1 for b in f1)
    within = math.sqrt(
        sum((len(b) - 1) * v for b, v in zip(f1, variances, strict=True)) / within_df
    )
    first, last = f1[0], f1[-1]
    diff = statistics.mean(last) - statistics.mean(first)
    se = math.sqrt(variances[0] / len(first) + variances[-1] / len(last))
    shifted = abs(diff) > 2 * se
    lead_sd, lead_df = (within, within_df) if shifted else (sd, df)
    lo, hi = sigma_interval(lead_sd, lead_df)
    centre, spread = statistics.mean(first), statistics.stdev(first)
    return {
        "status": "OK",
        "incumbent": incumbent,
        "tolerance": tolerance,
        "batches": [
            {
                "n": len(b),
                "mean": statistics.mean(b),
                "sd": statistics.stdev(b),
                "val_f1": b,
            }
            for b in f1
        ],
        "pooled": {
            "n": len(every),
            "mean": statistics.mean(every),
            "sd": sd,
            "df": df,
            "interval": list(sigma_interval(sd, df)),
        },
        "within_batch": {
            "sd": within,
            "df": within_df,
            "interval": list(sigma_interval(within, within_df)),
        },
        "shift": {"difference": diff, "se": se, "shifted": shifted},
        "lead": {
            "estimate": "within_batch" if shifted else "pooled",
            "sd": lead_sd,
            "df": lead_df,
            "interval": [lo, hi],
        },
        "false_promotion": {
            "point": false_promotion(tolerance, lead_sd),
            "low": false_promotion(tolerance, lo),
            "high": false_promotion(tolerance, hi),
        },
        "july_tolerance": {
            "point": july_tolerance(lead_sd),
            "low": july_tolerance(lo),
            "high": july_tolerance(hi),
        },
        "predictions": {
            "P1_within_3sd_of_batch_1": all(
                abs(v - centre) <= 3 * spread for v in last
            ),
            "P2_all_would_promote": all(
                t["val_f1"] > incumbent + tolerance and t["ap_lift"] > LIFT_GATE
                for t in batches[-1]
            ),
            "P3_pooled_sd_at_most_0.0043": sd <= SIGMA_AT_FIVE_PERCENT,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=Path, action="append", required=True)
    ap.add_argument("--incumbent", type=float, required=True)
    ap.add_argument("--tolerance", type=float, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument(
        "--allow-code-change",
        action="append",
        default=[],
        choices=CODE_INPUTS,
        help="a code input whose hash may differ between the batches (after reading its diff)",
    )
    args = ap.parse_args()
    probes = [json.loads(p.read_text()) for p in args.batch]
    try:
        batches = [completed(p) for p in probes]
        changed = poolable(probes, args.allow_code_change)
    except ValueError as exc:
        ap.error(str(exc))
    for name in changed:
        print(f"allowed: {name} differs between the batches", file=sys.stderr)
    result = analyse(batches, args.incumbent, args.tolerance)
    result["sources"] = [str(p) for p in args.batch]
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))
    return 0 if result["status"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
