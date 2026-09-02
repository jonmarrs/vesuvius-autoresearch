"""EXPLORATORY: does `col_gap_contrast` discriminate where the objective cannot?

**Written 2026-09-02, before gap133s2 and gap133s3 were rendered**, so the
prediction below is a prediction. Registered in
`docs/preregistration/2026-09-02_gap_fix_ink_six_fits.md`, addendum A.

Origin, stated plainly because it matters: this hypothesis is POST HOC. Having
found that the outer column score's noise is entirely its `col_width_conformity`
term, I looked at the other term and noticed that across the four base seeds and
`gap133` it was the only quantity whose gap-vs-base delta cleared its own floor:

    quantity               BASE CV   floor    gap133 delta   clears
    col_gap_contrast        0.0082    1.6%          -3.9%      YES
    col_width_conformity    0.2151   43.0%         -29.2%      no
    col_score               0.2139   42.8%         -32.0%      no
    line_score              0.0356    7.1%          -3.8%      no
    overall_fg_fraction     0.0521   10.4%          -7.4%      no
    total_fg_pixels         0.0421    8.4%          -6.7%      no

Six quantities were looked at and one cleared, on a single gap fit. That is weak
evidence and could easily be selection: this script exists to test it on three
gap fits instead of one, with the rule fixed first.

It reuses `analyse_gap_ink_arm.welch` so the statistic is literally the same code
as the registered primary. It is SECONDARY to that primary and cannot change it.
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyse_gap_ink_arm import (  # noqa: E402
    ALPHA,
    BASE_ARMS,
    GAP_ARMS,
    separation,
    welch,
)

# Lives in strips[0], not in summary, which is why the registered script does not
# carry it: nothing in this work had looked below the summary before today.
METRIC = "col_gap_contrast"

# Fixed now, before the two new renders finish.
PREDICTION = "GAP shows a REDUCTION in col_gap_contrast, significant at alpha=0.05"


def load(spec: str) -> dict:
    tag, _, path = spec.partition("=")
    strip = json.loads(Path(path).read_text())["strips"][0]
    return {"tag": tag, METRIC: strip[METRIC]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("arms", nargs="+", help="tag=metrics.json")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = [load(s) for s in args.arms]
    tags = [r["tag"] for r in rows]
    if len(set(tags)) != len(tags):
        raise SystemExit(f"an arm was passed twice: {tags}")
    unknown = [t for t in tags if t not in BASE_ARMS + GAP_ARMS]
    if unknown:
        raise SystemExit(f"unregistered arm(s) {unknown}")

    base = [r[METRIC] for r in rows if r["tag"] in BASE_ARMS]
    gap = [r[METRIC] for r in rows if r["tag"] in GAP_ARMS]
    if len(base) < 2 or len(gap) < 2:
        raise SystemExit(f"need >=2 per arm, have BASE={len(base)} GAP={len(gap)}")

    print(f"EXPLORATORY, secondary to the registered primary: {METRIC}")
    for r in rows:
        arm = "BASE" if r["tag"] in BASE_ARMS else "GAP"
        print(f"  {r['tag']:<12}{arm:<6}{r[METRIC]:.4f}")

    w = welch(base, gap)
    base_cv = statistics.stdev(base) / statistics.mean(base)
    print(
        f"\nBASE mean {w['mean_base']:.4f}  CV {base_cv:.4f}  (floor 2*CV = {2 * base_cv:.1%})"
    )
    print(f"GAP  mean {w['mean_gap']:.4f}")
    print(
        f"rel {w['rel_diff']:.2%}, 95% CI {w['ci'][0]:.2%} to {w['ci'][1]:.2%}, p={w['p']:.4f}"
    )
    print(f"separation: {separation(base, gap)}")

    sig = (not w["degenerate"]) and w["p"] < ALPHA
    met = sig and w["rel_diff"] < 0
    print(f"\nprediction: {PREDICTION}")
    print(f"  -> {'MET' if met else 'MISS, recorded as a miss'}")
    if sig:
        print(
            "  A metric the scorer already writes, free, discriminating where the\n"
            "  objective cannot. Still ONE config on ONE dataset, and the hypothesis\n"
            "  was post hoc; it licenses a registered arm on a different change, not\n"
            "  a recommendation to villa."
        )
    else:
        print(
            "  The n=1 observation does not survive three gap fits. Most likely it was\n"
            "  selection across the six quantities looked at. Retired."
        )

    if args.out:
        Path(args.out).write_text(
            json.dumps(
                {
                    "metric": METRIC,
                    "base": base,
                    "gap": gap,
                    "base_cv": base_cv,
                    "result": w,
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
