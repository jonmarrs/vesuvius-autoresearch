"""Compute the seed spread of `total_fg_pixels` over several fits.

**Written before the data existed**, on 2026-08-31, while seeds 3 and 4 were still
fitting. It implements exactly the statistics fixed in
`docs/preregistration/2026-08-31_seed_spread_n4.md` and nothing else. That is the
point: a pre-registration that says "CV is the headline" is prose, and prose can
be reinterpreted once the numbers are in. Code written first cannot.

The headline is the coefficient of variation, sd/mean, because it is scale free
and does not depend on which fit is nominated as the reference. The 18.93% figure
in `reports/objective_seed_noise_floor.md` does depend on that choice, being one
pairwise difference against baseline01, which is part of why it needed replacing.

Also enforced here is the registered quality gate: the fits must be of
indistinguishable quality to be pooled at all. A fit whose satisfied-area fraction
sits outside the band is NOT a like-for-like member of the sample, and pooling it
would report fit-quality differences as seed noise. This script refuses to pool it
and says so.
"""

import argparse
import json
import statistics
from itertools import combinations
from pathlib import Path

# Registered in the pre-registration, before any of the four values were known.
QUALITY_BAND = 0.01  # max spread in satisfied_area_fraction for fits to be pooled
CV_FLOOR_OVERSTATED = 0.05
CV_VERY_NOISY = 0.10

METRICS = (
    "total_fg_pixels",
    "overall_fg_fraction",
    "overall_line_score",
    "overall_column_score",
)


def load_arm(tag: str, metrics_json: Path, satisfaction_json: Path | None) -> dict:
    m = json.loads(Path(metrics_json).read_text())["summary"]
    row = {"tag": tag, **{k: m[k] for k in METRICS}}
    if satisfaction_json is not None:
        s = json.loads(Path(satisfaction_json).read_text())["summary"]
        row["satisfied_area_fraction"] = s["satisfied_area_fraction"]
    return row


MIN_POOLED = 3  # below this a "spread" is not one; see spread()


def spread(values: list[float]) -> dict:
    """A single value has sd 0, which would print CV 0.0000 and read as "no spread
    at all". That is the opposite of the truth: one value tells you nothing about
    variation. Refuse rather than emit a confident zero."""
    if len(values) < 2:
        raise SystemExit(
            f"only {len(values)} fit(s) left to pool; a spread cannot be computed from that "
            "and a CV of 0 would be a fabrication, not a measurement"
        )
    mean = statistics.fmean(values)
    sd = statistics.stdev(values)
    pair = [abs(a - b) / ((a + b) / 2) for a, b in combinations(values, 2)]
    return {
        "n": len(values),
        "mean": mean,
        "sd": sd,
        "cv": (sd / mean) if mean else float("nan"),
        "pairwise_rel": sorted(pair),
        "pair_min": min(pair) if pair else float("nan"),
        "pair_median": statistics.median(pair) if pair else float("nan"),
        "pair_max": max(pair) if pair else float("nan"),
    }


def verdict(cv: float) -> str:
    """The consequences fixed in the pre-registration, not chosen afterwards."""
    if cv <= CV_FLOOR_OVERSTATED:
        return (
            "CV <= 0.05: the single 18.93% pair OVERSTATED the floor. Fit-to-fit comparison is "
            "tighter than reported and objective_seed_noise_floor.md must be amended."
        )
    if cv >= CV_VERY_NOISY:
        return (
            f"CV >= 0.10: the objective is very noisy across seeds. A single-run gain below "
            f"about 2*CV = {2 * cv:.1%} is uninterpretable."
        )
    return "0.05 < CV < 0.10: an intermediate spread, reported as such and not rounded either way."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "arms", nargs="+", help="tag=metrics.json[,satisfaction.json], one per fit"
    )
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = []
    for spec in args.arms:
        tag, _, paths = spec.partition("=")
        mp, _, sp = paths.partition(",")
        rows.append(load_arm(tag, Path(mp), Path(sp) if sp else None))

    print(
        f"{'fit':<14}{'sat_area':>10}{'total_fg':>11}{'fg_frac':>10}{'line':>8}{'col':>8}"
    )
    for r in rows:
        sa = r.get("satisfied_area_fraction")
        print(
            f"{r['tag']:<14}{(f'{sa:.4f}' if sa is not None else '-'):>10}"
            f"{r['total_fg_pixels']:>11,.0f}{r['overall_fg_fraction']:>10.5f}"
            f"{r['overall_line_score']:>8.3f}{r['overall_column_score']:>8.3f}"
        )

    # Registered quality gate: refuse to pool fits of differing quality.
    sats = [
        r["satisfied_area_fraction"] for r in rows if "satisfied_area_fraction" in r
    ]
    pooled = list(rows)
    if len(sats) == len(rows) and len(sats) > 1:
        rng = max(sats) - min(sats)
        ok = rng <= QUALITY_BAND
        print(
            f"\nquality gate: satisfied_area spread {rng:.4f} "
            f"(band {QUALITY_BAND}) -> {'pooled' if ok else 'NOT COMPARABLE'}"
        )
        if not ok:
            # MEDIAN, not mean: a wild outlier drags the mean far enough that every
            # member looks like an outlier and nothing survives to pool. Found by
            # tests/test_analyse_seed_spread.py before any real data existed.
            centre = statistics.median(sats)
            outliers = [
                r["tag"]
                for r in rows
                if abs(r["satisfied_area_fraction"] - centre) > QUALITY_BAND
            ]
            print(
                f"  outliers, reported separately and NOT pooled: {', '.join(outliers)}"
            )
            pooled = [r for r in rows if r["tag"] not in outliers]
            if not pooled:
                raise SystemExit(
                    "every fit falls outside the quality band around the median; there is "
                    "no like-for-like sample to pool and no spread can be reported"
                )

    result = {
        "arms": rows,
        "quality_band": QUALITY_BAND,
        "pooled": [r["tag"] for r in pooled],
    }
    print(
        f"\n{'metric':<24}{'n':>3}{'mean':>13}{'sd':>12}{'CV':>9}"
        f"{'pair min':>10}{'pair med':>10}{'pair max':>10}"
    )
    for k in METRICS:
        s = spread([r[k] for r in pooled])
        result[k] = s
        print(
            f"{k:<24}{s['n']:>3}{s['mean']:>13,.5g}{s['sd']:>12,.5g}{s['cv']:>9.4f}"
            f"{s['pair_min']:>10.4f}{s['pair_median']:>10.4f}{s['pair_max']:>10.4f}"
        )

    n_pooled = result["total_fg_pixels"]["n"]
    if n_pooled < MIN_POOLED:
        print(
            f"\nWARNING: only {n_pooled} fits pooled. The registered design is four. A CV from "
            f"fewer than {MIN_POOLED} has uncertainty comparable to the number itself and the "
            "verdict below should not be relied on."
        )
    cv = result["total_fg_pixels"]["cv"]
    print(f"\nHEADLINE  total_fg_pixels CV = {cv:.4f}")
    print(f"VERDICT   {verdict(cv)}")
    print(
        "\nSame-fit arms (B, C, D, E in the duplicate-coverage report) are NOT governed by this\n"
        "spread: they share one fit. Their floor is pipeline non-determinism, 1.42%."
    )
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2))
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
