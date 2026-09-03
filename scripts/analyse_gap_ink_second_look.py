"""Second look at the gap-expander ink question, n=6 per arm, alpha = 0.0294.

**Written 2026-09-02 while seed05 was still fitting**, before any of the five new
arms produced a number. Implements
`docs/preregistration/2026-09-02_gap_ink_second_look.md` and nothing else.

Two things it does that the first-look script deliberately does not:

* **alpha is 0.0294, not 0.05.** This is the second look at one question. Two
  looks at 0.05 spend about 8% type I error; the Pocock boundary for two looks
  puts each at 0.0294. Testing the enlarged sample at 0.05 would be the fishing
  expedition the registration exists to prevent.
* **it REFUSES anything but a complete 6 and 6.** The registration says no
  interim analysis and no peeking at five per arm. Relying on myself not to run
  it early is weaker than making it impossible, so a partial sample is an error,
  not a smaller result. The first-look script accepted >=2 per arm, and by the
  end of that arm the guard no longer bit -- I had to decline by hand.

The statistic is imported from the first-look script so the two looks cannot
silently diverge in how they compute the same quantity.
"""

import argparse
import json
import sys
from math import comb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyse_gap_ink_arm import (  # noqa: E402
    METRICS,
    PRIMARY,
    QUALITY_BAND,
    quality_gate,
    separation,
    welch,
)

# Pocock two-look boundary. Fixed in the registration before any new fit started.
ALPHA = 0.0294
LOOK1 = "-9.25%, p = 0.0637 at 4 vs 3 (reports/gap_fix_ink_six_fits.md)"

BASE_ARMS = ("baseline01", "seed02", "seed03", "seed04", "seed05", "seed06")
GAP_ARMS = ("gap133", "gap133s2", "gap133s3", "gap133s4", "gap133s5", "gap133s6")
REQUIRED_PER_ARM = 6

PREDICTION = "p < 0.0294 with a NEGATIVE difference, i.e. the effect is real and established here"


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


def main() -> int:
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
        raise SystemExit(f"unregistered arm(s) {unknown}")

    base = [r for r in rows if r["tag"] in BASE_ARMS]
    gap = [r for r in rows if r["tag"] in GAP_ARMS]
    if len(base) != REQUIRED_PER_ARM or len(gap) != REQUIRED_PER_ARM:
        raise SystemExit(
            f"this is the SECOND LOOK: it requires exactly {REQUIRED_PER_ARM} per arm, "
            f"got BASE={len(base)} GAP={len(gap)}. The registration forbids an interim "
            "analysis, so a partial sample is refused rather than reported. Wait for "
            "every arm to be scored."
        )

    print(f"SECOND LOOK, alpha = {ALPHA} (Pocock, two looks). Look 1 was {LOOK1}")
    print(
        f"\n{'fit':<12}{'arm':<6}{'sat':>8}{'total_fg':>12}{'fg_frac':>10}{'line':>8}{'col':>8}"
    )
    for r in base + gap:
        sa = r.get("satisfied_area_fraction")
        print(
            f"{r['tag']:<12}{'BASE' if r['tag'] in BASE_ARMS else 'GAP':<6}"
            f"{(f'{sa:.4f}' if sa is not None else '-'):>8}"
            f"{r['total_fg_pixels']:>12,.0f}{r['overall_fg_fraction']:>10.5f}"
            f"{r['overall_line_score']:>8.3f}{r['overall_column_score']:>8.3f}"
        )

    print(f"\nquality gates, per arm (band {QUALITY_BAND}, never pooled across arms)")
    base, gap = quality_gate(base, "BASE"), quality_gate(gap, "GAP")
    if len(base) != REQUIRED_PER_ARM or len(gap) != REQUIRED_PER_ARM:
        print(
            "\nWARNING: the quality gate dropped a fit, so this is no longer the 6-and-6 "
            "sample the alpha was sized for. Report the reduced power explicitly."
        )

    results = {}
    print(
        f"\n{'metric':<24}{'BASE mean':>13}{'GAP mean':>13}{'rel':>9}{'p':>9}  verdict"
    )
    for metric in METRICS:
        w = welch([r[metric] for r in base], [r[metric] for r in gap])
        if w["degenerate"]:
            verdict = "degenerate"
        elif w["p"] < ALPHA:
            verdict = "REDUCES" if w["rel_diff"] < 0 else "INCREASES"
        else:
            verdict = "not established"
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
    n_sep = 1 / comb(len(base) + len(gap), len(gap))
    print(
        f"\nPRIMARY {PRIMARY}: rel {p['rel_diff']:.2%}, 95% CI {p['ci'][0]:.2%} to "
        f"{p['ci'][1]:.2%}, t={p['t']:.3f}, df={p['df']:.2f}, p={p['p']:.4f}"
    )
    print(f"  complete separation: {p['separation']}  (null probability {n_sep:.3%})")
    print("  separation is CONFIRMATORY ONLY and never replaces the test above")

    met = (not p["degenerate"]) and p["p"] < ALPHA and p["rel_diff"] < 0
    print(f"\nregistered prediction: {PREDICTION}")
    print(f"  -> {'MET' if met else 'MISS, recorded as a miss'}")
    if p["p"] >= ALPHA:
        print(
            f"\n  NOT ESTABLISHED at alpha {ALPHA}. Per the registration the question is now\n"
            "  CLOSED at this budget: a third look would spend ~11% type I error and would\n"
            "  be fishing. Report the CI and stop."
        )

    if args.out:
        Path(args.out).write_text(
            json.dumps(
                {
                    "alpha": ALPHA,
                    "base": [r["tag"] for r in base],
                    "gap": [r["tag"] for r in gap],
                    "results": results,
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
