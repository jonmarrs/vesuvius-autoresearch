"""Test whether the gap-expander fix changes recovered ink, BASE n=4 vs GAP n=3.

**Written 2026-09-02 while gap133s3 was still fitting and before either new outer
render existed.** It implements the rule in
`docs/preregistration/2026-09-02_gap_fix_ink_six_fits.md` and nothing else.

Two things it refuses to do, both of which would be easy and wrong:

* pool the two arms for the satisfaction quality gate. The arms are SUPPOSED to
  differ on satisfied_area -- that difference is finding 12 -- so a pooled gate
  would test the effect that defines the arms. Pooled, the seven fits span 0.0098
  against a 0.01 band and would scrape through by 0.0002. Gates are per arm.
* report a null as "no effect". At the measured outer CV the arm can only see
  effects of about 9% or larger, so a null is "no effect larger than ~9%" and the
  script prints the detectable size next to it.
"""

import argparse
import json
import math
import statistics
from pathlib import Path

from scipy import stats

METRICS = (
    "total_fg_pixels",
    "overall_fg_fraction",
    "overall_line_score",
    "overall_column_score",
)
PRIMARY = "total_fg_pixels"

BASE_ARMS = ("baseline01", "seed02", "seed03", "seed04")
GAP_ARMS = ("gap133", "gap133s2", "gap133s3")

QUALITY_BAND = 0.01  # within an arm, never pooled across arms
BASE_SAT_MAX = 0.8404  # the control gap133s3 should clear, from finding 12
ALPHA = 0.05
OUTER_CV = 0.0421  # reports/outer_winding_noise_floor.md


def detectable_effect(n_base: int, n_gap: int, cv: float = OUTER_CV) -> float:
    """Smallest relative difference this arm has ~80% power to see, two-sided."""
    se = cv * math.sqrt(1 / n_base + 1 / n_gap)
    return (stats.norm.ppf(1 - ALPHA / 2) + stats.norm.ppf(0.80)) * se


def welch(base: list[float], gap: list[float]) -> dict:
    mb, mg = statistics.mean(base), statistics.mean(gap)
    rel = (mg - mb) / mb
    vb, vg = statistics.variance(base), statistics.variance(gap)
    se = math.sqrt(vb / len(base) + vg / len(gap))
    if se == 0.0:
        # Both arms constant. Welch's df is 0/0 here, and a metric with no spread
        # supports no inference either way: say so rather than crash seven hours
        # of compute on a division, or emit a p-value the data cannot carry.
        return {
            "mean_base": mb,
            "mean_gap": mg,
            "rel_diff": rel,
            "ci": [float("nan"), float("nan")],
            "t": float("nan"),
            "p": float("nan"),
            "df": float("nan"),
            "degenerate": True,
        }
    t, p = stats.ttest_ind(gap, base, equal_var=False)
    # CI on the difference of means, Welch df, expressed relative to the base mean
    df = (vb / len(base) + vg / len(gap)) ** 2 / (
        (vb / len(base)) ** 2 / (len(base) - 1) + (vg / len(gap)) ** 2 / (len(gap) - 1)
    )
    crit = stats.t.ppf(1 - ALPHA / 2, df)
    lo, hi = ((mg - mb) - crit * se) / mb, ((mg - mb) + crit * se) / mb
    return {
        "mean_base": mb,
        "mean_gap": mg,
        "rel_diff": rel,
        "ci": [lo, hi],
        "t": float(t),
        "p": float(p),
        "df": df,
        "degenerate": False,
    }


def separation(base: list[float], gap: list[float]) -> str:
    """Assumption-free confirmatory check. 1/C(7,3) = 2.86% in a named direction."""
    if max(gap) < min(base):
        return "COMPLETE, all GAP below all BASE (p=2.86% one direction)"
    if min(gap) > max(base):
        return "COMPLETE, all GAP above all BASE (p=2.86% one direction)"
    return "none"


def quality_gate(rows: list[dict], arm: str) -> list[dict]:
    """Per arm. Pooling the arms here would test finding 12, not fit quality."""
    sats = [
        r["satisfied_area_fraction"] for r in rows if "satisfied_area_fraction" in r
    ]
    if len(sats) != len(rows) or len(sats) < 2:
        print(
            f"  {arm}: quality gate SKIPPED, not every fit carried a satisfaction json"
        )
        return rows
    spread = max(sats) - min(sats)
    if spread <= QUALITY_BAND:
        print(
            f"  {arm}: satisfied_area spread {spread:.4f} <= {QUALITY_BAND} -> pooled"
        )
        return rows
    centre = statistics.median(sats)
    keep = [
        r for r in rows if abs(r["satisfied_area_fraction"] - centre) <= QUALITY_BAND
    ]
    dropped = [r["tag"] for r in rows if r not in keep]
    print(
        f"  {arm}: spread {spread:.4f} > {QUALITY_BAND}; NOT pooling {', '.join(dropped)}"
    )
    return keep


def load(spec: str) -> dict:
    tag, _, paths = spec.partition("=")
    mp, _, sp = paths.partition(",")
    m = json.loads(Path(mp).read_text())["summary"]
    row = {"tag": tag, **{k: m[k] for k in METRICS}}
    if sp:
        row["satisfied_area_fraction"] = json.loads(Path(sp).read_text())["summary"][
            "satisfied_area_fraction"
        ]
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arms", nargs="+", help="tag=metrics.json[,satisfaction.json]")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = [load(s) for s in args.arms]
    tags = [r["tag"] for r in rows]
    if len(set(tags)) != len(tags):
        raise SystemExit(f"an arm was passed twice: {tags}")
    unknown = [t for t in tags if t not in BASE_ARMS + GAP_ARMS]
    if unknown:
        raise SystemExit(
            f"unregistered arm(s) {unknown}; registered are {BASE_ARMS + GAP_ARMS}"
        )

    base = [r for r in rows if r["tag"] in BASE_ARMS]
    gap = [r for r in rows if r["tag"] in GAP_ARMS]
    if len(base) < 2 or len(gap) < 2:
        raise SystemExit(f"need >=2 fits per arm, have BASE={len(base)} GAP={len(gap)}")

    print(
        f"{'fit':<12}{'arm':<6}{'sat':>8}{'total_fg':>12}{'fg_frac':>10}{'line':>8}{'col':>8}"
    )
    for r in base + gap:
        sa = r.get("satisfied_area_fraction")
        print(
            f"{r['tag']:<12}{'BASE' if r['tag'] in BASE_ARMS else 'GAP':<6}"
            f"{(f'{sa:.4f}' if sa is not None else '-'):>8}"
            f"{r['total_fg_pixels']:>12,.0f}{r['overall_fg_fraction']:>10.5f}"
            f"{r['overall_line_score']:>8.3f}{r['overall_column_score']:>8.3f}"
        )

    print(
        "\nquality gates, per arm (never pooled: the arms differ on satisfaction by design)"
    )
    base, gap = quality_gate(base, "BASE"), quality_gate(gap, "GAP")

    s3 = next((r for r in gap if r["tag"] == "gap133s3"), None)
    if s3 and "satisfied_area_fraction" in s3:
        ok = s3["satisfied_area_fraction"] > BASE_SAT_MAX
        print(
            f"\ncontrol: gap133s3 satisfied_area {s3['satisfied_area_fraction']:.4f} vs BASE max "
            f"{BASE_SAT_MAX} -> {'reproduces finding 12' if ok else 'DOES NOT reproduce finding 12, arm FLAGGED'}"
        )

    mde = detectable_effect(len(base), len(gap))
    print(
        f"\nn = {len(base)} BASE vs {len(gap)} GAP; smallest effect at 80% power: {mde:.1%}"
    )

    results = {}
    print(
        f"\n{'metric':<24}{'BASE mean':>13}{'GAP mean':>13}{'rel':>9}{'p':>9}  verdict"
    )
    for metric in METRICS:
        w = welch([r[metric] for r in base], [r[metric] for r in gap])
        if w["degenerate"]:
            verdict = "degenerate, zero variance in both arms"
        elif w["p"] < ALPHA:
            verdict = "REDUCES" if w["rel_diff"] < 0 else "INCREASES"
        else:
            verdict = f"not established (>{mde:.0%} only)"
        w["verdict"] = verdict
        w["separation"] = separation(
            [r[metric] for r in base], [r[metric] for r in gap]
        )
        results[metric] = w
        star = " <- PRIMARY" if metric == PRIMARY else ""
        print(
            f"{metric:<24}{w['mean_base']:>13,.4g}{w['mean_gap']:>13,.4g}"
            f"{w['rel_diff']:>9.2%}{w['p']:>9.4f}  {verdict}{star}"
        )

    p = results[PRIMARY]
    if p["degenerate"]:
        raise SystemExit(
            f"{PRIMARY} has zero variance in both arms; no inference is possible"
        )
    print(
        f"\nPRIMARY {PRIMARY}: rel {p['rel_diff']:.2%}, 95% CI {p['ci'][0]:.2%} to {p['ci'][1]:.2%}, "
        f"t={p['t']:.3f}, df={p['df']:.2f}, p={p['p']:.4f}"
    )
    print(f"  complete separation: {p['separation']}")
    print(
        f"\nregistered prediction: the difference of means is NEGATIVE -> "
        f"{'MET' if p['rel_diff'] < 0 else 'MISS, recorded as a miss'}"
    )
    if p["p"] >= ALPHA:
        print(
            f"  NULL READING: no effect larger than about {mde:.0%}. NOT 'no effect'."
        )

    if args.out:
        Path(args.out).write_text(
            json.dumps(
                {
                    "base": [r["tag"] for r in base],
                    "gap": [r["tag"] for r in gap],
                    "mde": mde,
                    "results": results,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
