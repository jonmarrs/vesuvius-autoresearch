"""Measure seed-to-seed noise in `total_fg_pixels`, per code tier, from the fits.

Every analysis script in this repo hardcodes `OUTER_CV = 0.0421`. That number is
real -- `reports/outer_winding_noise_floor.md`, and this script reproduces it
exactly from its own four fits -- but it carries **df = 3**, and a CV at df = 3
has a 95% CI spanning a factor of six. It has since been used to state the power
of studies on a *different* tree.

This replaces the constant with a measurement:

* **pooled WITHIN-ARM relative deviations**, so arms with different manipulations
  contribute their seed noise without their effects. This is the pooled-variance
  step of a one-way ANOVA, written out.
* **per tier**. Pinned villa-spiral `6847063f` and current villa are different
  instruments; `reports/corpus_is_on_superseded_code.md`. Pooling them would
  average a quiet instrument with a noisy one and describe neither.

Pooling the two tiers is **not offered**, for the reason `correlate_geometry_ink.py`
learned the hard way: an option to do the invalid thing eventually gets used.

Usage:  measure_noise_floor.py [--spiral-out DIR] [--json OUT]
"""

import argparse
import glob
import json
import statistics as st
import sys
from pathlib import Path

try:
    from scipy import stats
except ImportError:  # pragma: no cover
    stats = None

INK = "total_fg_pixels"
Z = 2.802  # two-sided 0.05, 80% power

# Arms grouped by the manipulation they share. Seeds WITHIN a group differ only
# by RNG, so their spread is noise; BETWEEN groups is signal and never pooled.
PINNED_GROUPS = {
    "baselines": ("baseline01", "seed02", "seed03", "seed04", "seed05", "seed06"),
    "gap133": ("gap133", "gap133s2", "gap133s3", "gap133s4", "gap133s5", "gap133s6"),
    "boot090": ("boot090s1", "boot090s2", "boot090s3"),
    "rand090": ("rand090s1", "rand090s2", "rand090s3"),
    "nosame": ("nosame_s1", "nosame_s2", "nosame_s3"),
    "strip090": ("strip090s1", "strip090s2", "strip090s3"),
}
CURRENT_GROUPS = {
    "curbase": ("curbase_s1", "curbase_s2", "curbase_s3"),
    "nosamecur": ("nosamecur_s1", "nosamecur_s2", "nosamecur_s3"),
    # Registered but not yet run; contributes nothing until three exist, and a
    # group with fewer than two fits is skipped rather than counted.
    "anchor10cov": ("anchor10cov_pilot", "anchor10cov_s2", "anchor10cov_s3"),
}
TIERS = {"pinned": PINNED_GROUPS, "current": CURRENT_GROUPS}

# The published df=3 figure, kept so the script can show what it is replacing.
PUBLISHED_PINNED_CV = 0.0421


def load(spiral_out: str) -> dict[str, float]:
    out = {}
    for p in glob.glob(f"{spiral_out}/outer_*/ink_metric/metrics.json"):
        tag = p.split("/outer_")[1].split("/")[0]
        out[tag] = json.loads(Path(p).read_text())["summary"][INK]
    return out


def pooled_cv(values_by_group: dict[str, list[float]]) -> tuple[float, int]:
    """Pooled within-group CV and its degrees of freedom.

    Relative deviations, so groups at different means contribute comparably --
    the current tier sits 68% higher than the pinned one on this metric.
    """
    devs: list[float] = []
    df = 0
    for v in values_by_group.values():
        if len(v) < 2:
            continue
        m = st.mean(v)
        devs += [(x - m) / m for x in v]
        df += len(v) - 1
    if df == 0:
        raise ValueError("no group had two or more fits; nothing to estimate")
    return (sum(d * d for d in devs) / df) ** 0.5, df


def cv_ci(cv: float, df: int, alpha: float = 0.05) -> tuple[float, float]:
    """Chi-square CI. A CV is an interval, not a number -- the lesson of
    `outer_winding_noise_floor.md`, which resolved UNRESOLVED for exactly this."""
    if stats is None:
        return (float("nan"), float("nan"))
    return (
        cv * (df / stats.chi2.ppf(1 - alpha / 2, df)) ** 0.5,
        cv * (df / stats.chi2.ppf(alpha / 2, df)) ** 0.5,
    )


def mde(cv: float, n_a: int, n_b: int) -> float:
    return Z * cv * (1 / n_a + 1 / n_b) ** 0.5


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    D = load(args.spiral_out)
    if not D:
        raise SystemExit(f"no metrics under {args.spiral_out}/outer_*/ink_metric/")

    result = {}
    for tier, groups in TIERS.items():
        by_group = {g: [D[t] for t in ts if t in D] for g, ts in groups.items()}
        by_group = {g: v for g, v in by_group.items() if len(v) >= 2}
        if not by_group:
            print(f"{tier}: no fits found, skipped")
            continue
        cv, df = pooled_cv(by_group)
        lo, hi = cv_ci(cv, df)
        result[tier] = {
            "cv": cv,
            "df": df,
            "ci95": [lo, hi],
            "n_fits": sum(len(v) for v in by_group.values()),
            "groups": {
                g: {"n": len(v), "mean": st.mean(v), "cv": st.stdev(v) / st.mean(v)}
                for g, v in by_group.items()
            },
            "mde_3v3": mde(cv, 3, 3),
        }
        print(
            f"\n=== tier: {tier}  ({result[tier]['n_fits']} fits, {len(by_group)} arms)"
        )
        print(f"{'arm':<14}{'n':>3}{'mean':>13}{'CV':>9}")
        for g, v in by_group.items():
            print(
                f"{g:<14}{len(v):>3}{st.mean(v):>13,.0f}{st.stdev(v) / st.mean(v):>9.4f}"
            )
        print(f"  pooled within-arm CV {cv:.4f}  df={df}  95% CI [{lo:.4f}, {hi:.4f}]")
        print(
            f"  -> smallest detectable relative effect at 3v3, 80% power: {mde(cv, 3, 3):.1%}"
        )

    if "pinned" in result:
        p = result["pinned"]
        print(
            f"\nthe hardcoded constant is {PUBLISHED_PINNED_CV:.4f} at df=3; this tier's "
            f"pooled estimate is {p['cv']:.4f} at df={p['df']}"
        )
        print(
            f"  MDE at 3v3: hardcoded {mde(PUBLISHED_PINNED_CV, 3, 3):.1%} vs "
            f"measured {p['mde_3v3']:.1%} -- the hardcoded one is OPTIMISTIC, so "
            f"pinned-tier nulls bound LESS than they claimed"
        )

    if {"pinned", "current"} <= result.keys() and stats is not None:
        a, b = result["pinned"], result["current"]
        F = (a["cv"] ** 2) / (b["cv"] ** 2)
        pv = 2 * min(stats.f.cdf(F, a["df"], b["df"]), stats.f.sf(F, a["df"], b["df"]))
        result["tier_comparison"] = {
            "F": F,
            "df": [a["df"], b["df"]],
            "p": pv,
            "ratio": a["cv"] / b["cv"],
        }
        print(
            f"\ncurrent vs pinned: CV ratio {a['cv'] / b['cv']:.1f}x  "
            f"F({a['df']},{b['df']})={F:.2f}  p={pv:.4f}"
        )
        print(
            "  POST-HOC: noticed in the data, not registered. Reported as a "
            "refinement, never as a result."
        )

    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=1) + "\n")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
