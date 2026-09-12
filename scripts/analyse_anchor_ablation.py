"""Anchor-count ablation: how many absolute winding anchors does READING need?

**Written 2026-09-12, before the pilot gate was read and before any arm existed.**
Implements `docs/preregistration/2026-09-12_anchor_ablation.md`.

villa asks people to draw winding annotations by hand and names automating them
the fastest path to unrolling at scale. Every project in villa's catalogue that
produces them validates on GEOMETRY. This measures 59 anchors against 10 on
RECOVERED INK.

Two things differ from `analyse_same_winding_current.py`, and both matter:

1. **`satisfied_area_fraction` IS an endpoint here, not report-only.** That study
   had to exclude it because the manipulation removed 5,413 of the patches the
   metric is computed against, so a rise could mean "less left to satisfy". This
   manipulation touches `abs_winding.json` only; the patch set is unchanged at
   38,442 in both arms (verified in the fit logs). Satisfaction is therefore
   like-for-like and is allowed to carry weight.

2. **Every arm must pass the winding-identity gate.** The strip is selected by
   winding NAME, and thinning anchors could make w120 denote a different wrap.
   An arm whose numbering shifted is comparing different papyrus, so it is
   EXCLUDED and reported as excluded -- never silently dropped, and never used to
   reselect the anchor count.

The noise constant is the CURRENT tier's measured value, not the pinned tree's
0.0421 that earlier studies inherited. See `reports/noise_floor_by_tier.md`.
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

# Tags match the dataset they use (spiral_s1_anchor10cov) and the pilot tag.
# The bare "anchor10" name belongs to the SUPERSEDED z-collapsed dataset and
# must not be reused, or an arm from the wrong dataset would analyse cleanly.
ABLATED_ARMS = ("anchor10cov_s1", "anchor10cov_s2", "anchor10cov_s3")
BASELINE_ARMS = ("curbase_s1", "curbase_s2", "curbase_s3")
REQUIRED_ABLATED = 3
REQUIRED_BASELINE = 3

# reports/noise_floor_by_tier.md -- CURRENT tier, pooled within-arm, df=4.
CURRENT_CV = 0.0125
# 59 anchors exist but 9 lie outside the fit's z-ROI and are never used;
# the manipulation is 50 -> 10. See the 2026-09-12 amendment.
N_ANCHORS_FULL = 50
N_ANCHORS_ABLATED = 10

PREDICTION = "NONE registered on either endpoint"


def load(spec: str) -> dict:
    tag, _, paths = spec.partition("=")
    mp, _, sp = paths.partition(",")
    m = json.loads(Path(mp).read_text())["summary"]
    row = {"tag": tag, INK: m[INK], **{k: m[k] for k in SECONDARY}}
    if sp:
        row[GEOM] = json.loads(Path(sp).read_text())["summary"][GEOM]
    return row


def mde(n_a: int, n_b: int, cv: float = CURRENT_CV) -> float:
    return 2.802 * cv * (1 / n_a + 1 / n_b) ** 0.5


def verdict(ink: dict, geom: dict | None) -> tuple[str, str]:
    """The registered rule.

    Ink decides. Geometry is reported and, unlike the same-winding study, is
    interpretable -- but a geometry move with a null ink result is NOT a reason
    to call thinning anchors harmless for reading, and is not allowed to upgrade
    the verdict.
    """
    ink_sig = (not ink["degenerate"]) and ink["p"] < ALPHA
    if ink_sig and ink["rel_diff"] < 0:
        return "ANCHORS MATTER FOR READING", (
            f"cutting {N_ANCHORS_FULL} anchors to {N_ANCHORS_ABLATED} significantly "
            "REDUCED recovered ink. The hand-drawn annotations villa asks for are "
            "buying reading, and this quantifies how much."
        )
    if ink_sig and ink["rel_diff"] > 0:
        return "FEWER ANCHORS READ BETTER", (
            "cutting anchors significantly INCREASED recovered ink. Surprising, and "
            "the first thing to check is whether the retained anchors are better "
            "placed rather than fewer being better in itself."
        )
    return "NULL", (
        f"no reading effect from cutting {N_ANCHORS_FULL} anchors to "
        f"{N_ANCHORS_ABLATED}. Bounded, not zero. If it holds, the annotation "
        "effort villa asks for is buying geometry rather than reading, which is "
        "worth knowing before automating the production of more of them."
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("arms", nargs="+", help="tag=metrics.json[,satisfaction.json]")
    ap.add_argument(
        "--excluded",
        nargs="*",
        default=[],
        help="arms excluded by the winding-identity gate; reported, not hidden",
    )
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = [load(s) for s in args.arms]
    tags = [r["tag"] for r in rows]
    if len(set(tags)) != len(tags):
        raise SystemExit(f"an arm was passed twice: {tags}")
    known = ABLATED_ARMS + BASELINE_ARMS
    unknown = [t for t in tags if t not in known]
    if unknown:
        raise SystemExit(f"unregistered arm(s) {unknown}")

    abl = [r for r in rows if r["tag"] in ABLATED_ARMS]
    base = [r for r in rows if r["tag"] in BASELINE_ARMS]
    if len(abl) != REQUIRED_ABLATED or len(base) != REQUIRED_BASELINE:
        raise SystemExit(
            f"needs exactly {REQUIRED_ABLATED} ablated and {REQUIRED_BASELINE} "
            f"baseline arms, got {len(abl)} and {len(base)}. A partial sample is "
            "refused, not reported."
        )

    print(f"ANCHOR ABLATION {N_ANCHORS_FULL} -> {N_ANCHORS_ABLATED}, alpha = {ALPHA}.")
    if args.excluded:
        print(
            f"EXCLUDED by the winding-identity gate: {', '.join(args.excluded)} "
            "(numbering shifted; those arms compare different papyrus)"
        )
    print(f"\n{'arm':<16}{'satisfied_area':>16}{'total_fg':>14}")
    for r in abl + base:
        g = r.get(GEOM)
        print(
            f"{r['tag']:<16}{(f'{g:.4f}' if g is not None else '-'):>16}"
            f"{r[INK]:>14,.0f}"
        )

    m = mde(len(abl), len(base))
    print(
        f"\nn = {len(abl)} vs {len(base)}; smallest ink effect at 80% power: "
        f"{m:.1%}  (current-tier CV {CURRENT_CV})"
    )

    ink = welch([r[INK] for r in base], [r[INK] for r in abl])
    geom = None
    if all(GEOM in r for r in abl + base):
        geom = welch([r[GEOM] for r in base], [r[GEOM] for r in abl])

    print(f"\n{'endpoint':<30}{'BASELINE':>13}{'ABLATED':>13}{'rel':>9}{'p':>9}")
    print(
        f"{'ink  ' + INK:<30}{ink['mean_base']:>13,.4g}{ink['mean_gap']:>13,.4g}"
        f"{ink['rel_diff']:>9.2%}{ink['p']:>9.4f}"
    )
    if geom:
        print(
            f"{'geom ' + GEOM:<30}{geom['mean_base']:>13.4f}{geom['mean_gap']:>13.4f}"
            f"{geom['rel_diff']:>9.2%}{geom['p']:>9.4f}"
        )
        print("  geometry IS interpretable here: the patch set is identical in both")
        print("  arms, so this is not the same-winding study's 'less left to satisfy'.")
    print(
        f"  ink separation: {separation([r[INK] for r in base], [r[INK] for r in abl])}"
    )

    tag, why = verdict(ink, geom)
    print(f"\nVERDICT: {tag}\n  {why}")
    if not ((not ink["degenerate"]) and ink["p"] < ALPHA):
        print(f"  NULL READING on ink: no effect larger than about {m:.1%}.")
        print("  Post-hoc, quote the CI on the observed effect rather than this MDE.")
    print(f"\nregistered prediction: {PREDICTION}")

    if args.out:
        Path(args.out).write_text(
            json.dumps(
                {
                    "alpha": ALPHA,
                    "mde": m,
                    "cv": CURRENT_CV,
                    "ink": ink,
                    "geometry": geom,
                    "verdict": tag,
                    "excluded_arms": args.excluded,
                    "n_anchors": [N_ANCHORS_FULL, N_ANCHORS_ABLATED],
                },
                indent=1,
            )
            + "\n"
        )
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
