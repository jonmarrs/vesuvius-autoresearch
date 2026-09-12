"""Same-winding ablation ON CURRENT VILLA: does the decoupling reproduce?

**Written before the first arm was started**, implementing
`docs/preregistration/2026-09-11_decoupling_on_current_code.md`.

Same rule as the original study on the pinned tree, retargeted at current-code
arms. The question is no longer "do these constraints help reading" but "does the
ANSWER still hold now that upstream recovers 67.6% more ink through a
byte-identical scorer".

The rule differs from the two previous studies in one deliberate way, and the
difference is the point: **`satisfied_area_fraction` is NOT an endpoint here.**

Satisfaction measures how well a fit satisfies the inputs it was given. This
study removes 5,413 of those inputs, so the metric can rise simply because there
is less left to satisfy -- the 200-step smoke already showed it rising, 0.13466
to 0.13766. Comparing it across arms with different input sets is not
like-for-like, and a verdict function that rewarded a rise would be measuring the
manipulation rather than its effect. It is therefore printed, flagged, and
excluded from the decision.

What decides: `total_fg_pixels` on w120-w129, ABLATED vs the six existing
full-input baselines.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyse_gap_ink_arm import separation, welch  # noqa: E402

ALPHA = 0.05
INK = "total_fg_pixels"
GEOM = "satisfied_area_fraction"
SECONDARY = ("overall_fg_fraction", "overall_line_score", "overall_column_score")

ABLATED_ARMS = ("nosamecur_s1", "nosamecur_s2", "nosamecur_s3")
BASELINE_ARMS = ("curbase_s1", "curbase_s2", "curbase_s3")
REQUIRED_ABLATED = 3
REQUIRED_BASELINE = 3

# SUPERSEDED CONSTANT -- do not copy into new code.
# This is the PINNED tier's CV used in a CURRENT-code study, which is the exact
# error that made this study's published bound 3x too loose (9.6% where the data
# exclude +/-3%). Current-tier CV is 0.0125. Retained only to reproduce the
# registered MDE; the report quotes the observed CI instead.
# reports/noise_floor_by_tier.md, reports/decoupling_does_not_cleanly_reproduce.md
OUTER_CV = 0.0421
PREDICTION = (
    "ink NULL and satisfied_area FALLS — the decoupling reproduces on current code"
)


def load(spec: str) -> dict:
    tag, _, paths = spec.partition("=")
    mp, _, sp = paths.partition(",")
    m = json.loads(Path(mp).read_text())["summary"]
    row = {"tag": tag, INK: m[INK], **{k: m[k] for k in SECONDARY}}
    if sp:
        row[GEOM] = json.loads(Path(sp).read_text())["summary"][GEOM]
    return row


def mde(n_a: int, n_b: int, cv: float = OUTER_CV) -> float:
    return 2.802 * cv * (1 / n_a + 1 / n_b) ** 0.5


def verdict(ink: dict) -> tuple[str, str]:
    """The registered rule. Geometry is deliberately not an input to it."""
    if ink["degenerate"] or ink["p"] >= ALPHA:
        return "NULL", (
            "no reading effect from removing 5,413 same-winding constraints. Bounded, "
            "not zero. Directly relevant to how much winding evidence is necessary, "
            "and a further case of geometry and ink not moving together."
        )
    if ink["rel_diff"] < 0:
        return "CONSTRAINTS HELP READING", (
            "removing them costs ink: the constraints earn their cost on the endpoint "
            "that matters, validating villa's emphasis with reading rather than "
            "geometry. This is a MISS against my registered prediction."
        )
    return "REMOVING THEM HELPS", (
        "ink rose when constraints were removed. Surprising; needs a mechanism "
        "before it is believed, and is a MISS against my registered prediction."
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("arms", nargs="+", help="tag=metrics.json[,satisfaction.json]")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = [load(s) for s in args.arms]
    tags = [r["tag"] for r in rows]
    if len(set(tags)) != len(tags):
        raise SystemExit(f"an arm was passed twice: {tags}")
    unknown = [t for t in tags if t not in ABLATED_ARMS + BASELINE_ARMS]
    if unknown:
        raise SystemExit(f"unregistered arm(s) {unknown}")

    abl = [r for r in rows if r["tag"] in ABLATED_ARMS]
    base = [r for r in rows if r["tag"] in BASELINE_ARMS]
    if len(abl) != REQUIRED_ABLATED or len(base) != REQUIRED_BASELINE:
        raise SystemExit(
            f"needs exactly {REQUIRED_ABLATED} ABLATED and {REQUIRED_BASELINE} BASELINE "
            f"arms, got {len(abl)} and {len(base)}. A partial sample is refused."
        )

    print(
        f"SAME-WINDING ABLATION on CURRENT villa, alpha = {ALPHA}. 5,413 constraints removed."
    )
    print(f"\n{'fit':<12}{'arm':<10}{'geometry':>10}{'total_fg':>12}")
    for r in abl + base:
        g = r.get(GEOM)
        arm = "ABLATED" if r["tag"] in ABLATED_ARMS else "baseline"
        print(
            f"{r['tag']:<12}{arm:<10}{(f'{g:.4f}' if g is not None else '-'):>10}"
            f"{r[INK]:>12,.0f}"
        )

    m = mde(len(abl), len(base))
    print(f"\nn = {len(abl)} vs {len(base)}; smallest ink effect at 80% power: {m:.1%}")

    ink = welch([r[INK] for r in base], [r[INK] for r in abl])
    print(f"\n{'endpoint':<26}{'BASELINE':>13}{'ABLATED':>13}{'rel':>9}{'p':>9}")
    print(
        f"{'ink  ' + INK:<26}{ink['mean_base']:>13,.4g}{ink['mean_gap']:>13,.4g}"
        f"{ink['rel_diff']:>9.2%}{ink['p']:>9.4f}"
    )
    if all(GEOM in r for r in abl + base):
        g = welch([r[GEOM] for r in base], [r[GEOM] for r in abl])
        print(
            f"{'geom ' + GEOM:<26}{g['mean_base']:>13.4f}{g['mean_gap']:>13.4f}"
            f"{g['rel_diff']:>9.2%}{g['p']:>9.4f}"
        )
        print(
            "  REPORT ONLY, NOT AN ENDPOINT: satisfaction measures how well a fit "
            "satisfies the inputs it was given, and this study removed 5,413 of them. "
            "A rise can mean 'less left to satisfy', not 'better geometry'."
        )
    print(
        f"  ink separation: {separation([r[INK] for r in base], [r[INK] for r in abl])}"
    )

    tag, why = verdict(ink)
    print(f"\nVERDICT: {tag}\n  {why}")
    if ink["degenerate"] or ink["p"] >= ALPHA:
        print(f"  NULL READING: no effect larger than about {m:.0%}. NOT 'no effect'.")

    met = tag == "NULL"
    print(
        f"\nregistered prediction: {PREDICTION}\n  -> "
        f"{'MET on the ink half' if met else 'MISS, recorded as a miss'}"
    )

    if args.out:
        Path(args.out).write_text(
            json.dumps(
                {
                    "alpha": ALPHA,
                    "mde": m,
                    "ink": ink,
                    "verdict": tag,
                    "prediction_met": met,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
