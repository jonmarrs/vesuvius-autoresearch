"""Apply the outer-winding noise floor to the gap-expander arm's observed deltas.

**Written 2026-09-01, before any of the three seed renders finished**, and it
implements exactly the decision rule fixed in
`docs/preregistration/2026-09-01_outer_winding_noise_floor.md` and nothing else.
Prose can be reinterpreted once the numbers land; code written first cannot.

`scripts/analyse_seed_spread.py` already computes the spread itself, including the
registered quality gate. This script does the one thing that one does not: it takes
the resulting CVs and decides what they do to conclusions already published in
`reports/gap_fix_outer_windings_still_not_established.md`, including the case where
they REVERSE one.

The uncomfortable branch is deliberately the explicit one. If the outer floor comes
back tighter than 11.03%, the gap fix acquires a measured NEGATIVE ink effect and
yesterday's "not established" becomes wrong. That outcome is spelled out here, with
its wording, so it cannot later be softened into a refinement.
"""

import argparse
import json
import math
import statistics
from pathlib import Path

from scipy.stats import chi2

# Observed in reports/gap_fix_outer_windings_still_not_established.md, baseline01
# against gap133 on w120-w129. Constants, not arguments: they are already published,
# and letting them vary would let the rule be re-aimed after the fact.
OBSERVED = {
    "total_fg_pixels": -0.110300,
    "overall_column_score": -0.465748,
    "overall_line_score": -0.023871,
}

# The registered pair that carries a published conclusion. The line score was inside
# every candidate floor and is reported for completeness only.
DECISIVE = "total_fg_pixels"
CANDIDATE = "overall_column_score"

# A CV estimated from n=4 is itself uncertain, so the floor is an interval, not a
# number. The verdict is taken from the interval: only when the WHOLE interval sits
# on one side of the observation is the comparison resolved at this n. This replaced
# a cruder "within a factor of two" band while the renders were still running and
# before any of their numbers existed; the band made STANDS nearly unreachable, since
# a floor twice the observation is a comfortable pass, not a tie.
CI = 0.95

# The arms the pre-registration names, fixed before any of them was rendered. This
# is a SEED spread: pooling anything else makes the "floor" absorb a config effect
# and, since a wider floor is what leaves my published conclusion standing, it
# would fail in the flattering direction. gap133 is the specific trap -- its
# satisfied_area sits 0.0082 from baseline01, inside the 0.01 quality band that
# guards analyse_seed_spread.py, so quality alone would NOT catch it.
REGISTERED_ARMS = ("baseline01", "seed02", "seed03", "seed04")

# Same band analyse_seed_spread.py uses: fits of differing quality are not
# like-for-like members of one seed sample.
QUALITY_BAND = 0.01

# The inner-winding CVs the previous report's floors were transferred from.
INNER_CV = {
    "total_fg_pixels": 0.1086,
    "overall_line_score": 0.0342,
    "overall_column_score": 0.1343,
}


def cv(values: list[float]) -> float:
    if len(values) < 2:
        raise SystemExit(
            f"only {len(values)} arm(s); a CV of 0 from one value would be a fabrication"
        )
    return statistics.stdev(values) / statistics.mean(values)


def cv_interval(point: float, n: int) -> tuple[float, float]:
    """95% interval on a CV from n observations, via the chi distribution on the
    sd. Reported so a point estimate near the line is not read as if it were exact.

    An earlier draft approximated the chi-square quantile with Wilson-Hilferty to
    dodge a scipy dependency; scipy turned out to be a declared dependency already,
    and at df=3 the approximation was 16% out in the lower tail, widening the
    interval to 4.07x the point estimate against a true 3.73x. Being wrong in the
    conservative direction is still being wrong."""
    df = n - 1
    tail = (1 - CI) / 2
    lo = point * math.sqrt(df / chi2.ppf(1 - tail, df))
    hi = point * math.sqrt(df / chi2.ppf(tail, df))
    return lo, hi


def quality_gate(rows: list[dict]) -> list[dict]:
    """Refuse to pool fits of differing quality, the gate analyse_seed_spread.py
    already applies. Optional: it only fires when every arm was given a
    satisfaction json. Outliers are dropped from the pool and named, not silently
    averaged in."""
    sats = [
        r["satisfied_area_fraction"] for r in rows if "satisfied_area_fraction" in r
    ]
    if len(sats) != len(rows) or len(sats) < 2:
        print("quality gate: not all arms carried a satisfaction json, gate SKIPPED")
        return rows
    spread = max(sats) - min(sats)
    if spread <= QUALITY_BAND:
        print(
            f"quality gate: satisfied_area spread {spread:.4f} <= {QUALITY_BAND} -> pooled"
        )
        return rows
    centre = statistics.median(sats)
    keep = [
        r for r in rows if abs(r["satisfied_area_fraction"] - centre) <= QUALITY_BAND
    ]
    dropped = [r["tag"] for r in rows if r not in keep]
    print(
        f"quality gate: satisfied_area spread {spread:.4f} > {QUALITY_BAND}; "
        f"NOT pooling {', '.join(dropped)}"
    )
    return keep


def rule(metric: str, floor: float, n: int, cv_point: float) -> tuple[str, str]:
    """The registered consequence. Returns (verdict_tag, sentence)."""
    observed = abs(OBSERVED[metric])
    cv_lo, cv_hi = cv_interval(cv_point, n)
    floor_lo, floor_hi = 2 * cv_lo, 2 * cv_hi
    # Resolved only when the entire floor interval sits one side of the observation.
    unresolved = floor_lo <= observed <= floor_hi

    if metric == DECISIVE:
        if unresolved:
            return "UNRESOLVED", (
                f"the floor's 95% interval {floor_lo:.1%} to {floor_hi:.1%} straddles the "
                f"observed {observed:.2%}. Registered as UNRESOLVED at n={n}: report it as "
                "unresolved, not as whichever side of the line the point estimate fell."
            )
        if floor > observed:
            return "STANDS", (
                f"the whole floor interval {floor_lo:.1%} to {floor_hi:.1%} exceeds the "
                f"observed {observed:.2%} (point floor {floor:.1%}). The published "
                "conclusion STANDS unchanged, now grounded in the right region instead of "
                "a floor transferred from the inner windings."
            )
        return "REVERSES", (
            f"the whole floor interval {floor_lo:.1%} to {floor_hi:.1%} is below the observed "
            f"{observed:.2%} (point floor {floor:.1%}). The observation CLEARS "
            "the floor and the published conclusion REVERSES: the gap fix has a measured "
            "NEGATIVE ink effect on the windings it acts on. Report as a reversal of "
            "reports/gap_fix_outer_windings_still_not_established.md, prominently, not as a "
            "refinement."
        )

    if metric == CANDIDATE:
        if floor > observed:
            return "RETIRED", (
                f"floor {floor:.1%} exceeds the observed {observed:.2%}. The post-hoc column "
                "observation is RETIRED, not carried forward."
            )
        return "CANDIDATE", (
            f"floor {floor:.1%} is below the observed {observed:.2%}. The column observation "
            "SURVIVES as a candidate only: it was still not pre-registered for that arm, so "
            "this licenses a properly registered arm, not a claim."
        )

    return (
        "REPORTED",
        f"floor {floor:.1%} against observed {observed:.2%}; reported only.",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "arms", nargs="+", help="tag=metrics.json, one per outer seed render"
    )
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = []
    for spec in args.arms:
        tag, _, paths = spec.partition("=")
        mp, _, sp = paths.partition(",")
        if tag not in REGISTERED_ARMS:
            raise SystemExit(
                f"arm {tag!r} is not one of the registered arms {REGISTERED_ARMS}. "
                "This measures SEED noise; pooling a config arm would report a config "
                "effect as noise, widening the floor in the direction that flatters the "
                "published conclusion. Refusing."
            )
        m = json.loads(Path(mp).read_text())["summary"]
        row = {"tag": tag, **{k: m[k] for k in INNER_CV}}
        if sp:
            row["satisfied_area_fraction"] = json.loads(Path(sp).read_text())[
                "summary"
            ]["satisfied_area_fraction"]
        rows.append(row)

    tags = [r["tag"] for r in rows]
    if len(set(tags)) != len(tags):
        raise SystemExit(
            f"an arm was passed twice: {tags}. A duplicate shrinks the CV."
        )

    rows = quality_gate(rows)
    n = len(rows)
    print(f"{'fit':<14}{'total_fg':>12}{'line':>9}{'col':>9}")
    for r in rows:
        print(
            f"{r['tag']:<14}{r['total_fg_pixels']:>12,.0f}"
            f"{r['overall_line_score']:>9.3f}{r['overall_column_score']:>9.3f}"
        )

    results: dict[str, dict] = {}
    cv_points: dict[str, float] = {}
    print(
        f"\n{'metric':<24}{'CV out':>9}{'CV in':>9}{'floor':>9}{'observed':>11}  verdict"
    )
    for metric in INNER_CV:
        values = [r[metric] for r in rows]
        point = cv(values)
        floor = 2 * point
        tag, sentence = rule(metric, floor, n, point)
        cv_points[metric] = point
        lo, hi = cv_interval(point, n)
        results[metric] = {
            "cv_outer": point,
            "cv_outer_95ci": [lo, hi],
            "cv_inner": INNER_CV[metric],
            "floor_outer": floor,
            "observed": OBSERVED[metric],
            "verdict": tag,
            "sentence": sentence,
        }
        print(
            f"{metric:<24}{point:>9.4f}{INNER_CV[metric]:>9.4f}{floor:>9.1%}"
            f"{OBSERVED[metric]:>11.2%}  {tag}"
        )

    print(
        "\nRegistered prediction 2: the outer CV of total_fg_pixels is HIGHER than 0.1086."
    )
    got = cv_points["total_fg_pixels"]
    print(
        f"  outer {got:.4f} vs inner {INNER_CV['total_fg_pixels']:.4f} -> "
        f"{'MET' if got > INNER_CV['total_fg_pixels'] else 'MISS, recorded as a miss'}"
    )

    print("\nConsequences:")
    for metric in (DECISIVE, CANDIDATE):
        point = cv_points[metric]
        lo, hi = cv_interval(point, n)
        print(f"  {metric}: {results[metric]['sentence']}")
        print(f"    CV {point:.4f}, 95% CI {lo:.4f} to {hi:.4f} at n={n}")

    if args.out:
        Path(args.out).write_text(
            json.dumps({"n": n, "arms": rows, "results": results}, indent=1) + "\n"
        )
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
