"""docs/preregistration/2026-10-17_noise_probe_v3_pooled.md -- the registered analysis.

Pools the val_f1 of identical-config noise-probe batches (each a probe.json written by f1_noise_probe.py),
estimates the run-to-run sigma with its chi-square interval, checks for a shift between batches, and gives
the rate at which a cycle that changes nothing clears a promotion tolerance.

Usage: .venv/bin/python scripts/noise_probe_pooled.py --batch B1/probe.json --batch B2/probe.json \
    --incumbent 0.249348 --tolerance 0.01 --out reports/X.json
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

from scipy import stats

PROTOCOL = "seeded-sample-400-v3+z1-27"
LIFT_GATE = 1.02  # train.LIFT_MARGIN: promotion needs ap_prevalence_lift > 1 + 0.02
SIGMA_AT_FIVE_PERCENT = 0.0043  # prediction 3: 0.01 / (1.645 * sqrt(2)), rounded
MIN_LAST_BATCH = 3


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
    if len(batches[-1]) < MIN_LAST_BATCH:
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
    args = ap.parse_args()
    batches = [completed(json.loads(p.read_text())) for p in args.batch]
    result = analyse(batches, args.incumbent, args.tolerance)
    result["sources"] = [str(p) for p in args.batch]
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))
    return 0 if result["status"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
