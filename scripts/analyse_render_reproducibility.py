"""Is the render reproducible on one villa tree? Decides the registered bands.

Implements `docs/preregistration/2026-09-20_is_the_noise_floor_actually_the_render.md`,
written while the repeat was at band ~10/34 and committed before it scored.

The pair: `radial_work_rad0` and `radial_work_rad0b`. Same mesh set (hash
`4576eacfa2d40cdd`), same pinned villa `be09a8503`, byte-identical
`render_ink.py`, same machine. They differ in nothing but being run twice.

This matters beyond the radial study. Every arm in the corpus is a separate fit
AND a separate render+score, so the "seed CV" of 0.0514 contains both and has
never been decomposed. If the render alone contributes several percent, extra fit
seeds buy much less than assumed, because the variance is downstream of the fit.
"""

import argparse
import json
import sys
from pathlib import Path

SEED_CV_PINNED = 0.0514  # reports/noise_floor_by_tier.md, df=18
CLAIMED_FLOOR = 0.0142  # reports/the_determinism_floor_rests_on_one_draw.md
SCORER_ONLY = 0.000032  # repro/spiral_render/score_arms.sh header, 3 runs, one strip


def summary(p: str) -> dict:
    return json.loads(Path(p).read_text())["summary"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    A, B = summary(args.a), summary(args.b)
    ink = (B["total_fg_pixels"] - A["total_fg_pixels"]) / A["total_fg_pixels"]
    area = (B["total_pixels"] - A["total_pixels"]) / A["total_pixels"]
    frac = (B["overall_fg_fraction"] - A["overall_fg_fraction"]) / A[
        "overall_fg_fraction"
    ]
    d = abs(ink)

    print("RENDER REPRODUCIBILITY: same meshes, same tree, run twice\n")
    print(f"{'quantity':<26}{'run A':>16}{'run B':>16}{'rel':>10}")
    print(
        f"{'total_fg_pixels':<26}{A['total_fg_pixels']:>16,}{B['total_fg_pixels']:>16,}{ink:>+9.2%}"
    )
    print(
        f"{'total_pixels (canvas)':<26}{A['total_pixels']:>16,}{B['total_pixels']:>16,}{area:>+9.2%}"
    )
    print(
        f"{'overall_fg_fraction':<26}{A['overall_fg_fraction']:>16.6f}{B['overall_fg_fraction']:>16.6f}{frac:>+9.2%}"
    )

    if d >= 0.03:
        band, reading = (
            "RENDER DOMINATES",
            (
                "The render stage is the dominant noise source. The 1.42% floor is wrong, "
                "this study needs a floor near the measured value, and extra fit seeds buy "
                "far less than assumed because the variance is downstream of the fit."
            ),
        )
    elif d > CLAIMED_FLOOR:
        band, reading = (
            "RENDER MATERIAL",
            (
                "Render noise is material but not dominant. The floor needs revising and the "
                "seed CV is partly render, not purely fit RNG."
            ),
        )
    else:
        band, reading = (
            "RENDER REPRODUCIBLE",
            (
                "The render reproduces on one tree. The ZERO-vs-baseline -5.05% is then "
                "render-code DRIFT between 2026-09-01 and be09a8503 -- its own finding, since "
                "comparisons spanning a villa bump would be unreliable at that scale."
            ),
        )
    print(f"\nBAND: {band}  (|dT| = {d:.2%})\n  {reading}")
    print(
        f"\nregistered prediction: >=3% (RENDER DOMINATES)  -> "
        f"{'MET' if d >= 0.03 else 'MISS, recorded as a miss'}"
    )

    print("\nfor context, all on total_fg_pixels:")
    print(f"  scorer alone, one fixed strip      {SCORER_ONLY:.4%}")
    print(f"  THIS pair (render+score, one tree) {d:.2%}")
    print(f"  claimed 'pipeline determinism'     {CLAIMED_FLOOR:.2%}")
    print(f"  pinned-tier 'seed' CV              {SEED_CV_PINNED:.2%}")
    if d > 0:
        print(
            f"\n  render/scorer ratio: {d / SCORER_ONLY:,.0f}x -- the scorer is not the source"
        )
        print(
            f"  this pair explains {min(d / SEED_CV_PINNED, 1.0):.0%} of the pinned 'seed' CV"
        )

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "ink": ink,
                    "canvas": area,
                    "fg_fraction": frac,
                    "band": band,
                    "prediction_met": d >= 0.03,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
