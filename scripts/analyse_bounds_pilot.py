"""Strip-extent pilot: does the bounds knob move extent more than seed noise?

Implements `docs/preregistration/2026-09-19_strip_extent_pilot.md` and nothing else.
**Written while `bounds_lo` is still fitting and neither arm has a number**, for the
reason findings 38-43 taught the hard way: five of those were computed in heredocs,
were unreproducible, and were skipped by the claims auditor because no artifact
existed. This writes `reports/bounds_pilot_verdict.json`.

The pilot asks ONE question and this module refuses to answer any other: does
`model_flow_bounds_radius` move `total_pixels` materially more than reseeding does?
It says nothing about ink. Two arms cannot.

The floor is not invented here. `reports/outer_winding_noise_floor.md` measured strip
area CV at **0.0199** across fits differing only in seed, and that is what a
deliberate manipulation has to beat.
"""

import argparse
import json
import statistics as st
import sys
from pathlib import Path

SPIRAL_OUT = "/home/jon/openclaw-workspace/Neo-VM/spiral_out"
ARMS = ("bounds_lo", "bounds_hi")
RADIUS = {"bounds_lo": 2720, "bounds_hi": 3680}  # default 3200, -/+15%
SEED_AREA_CV = 0.0199
# curbase_s1-s9: the seed-only distribution this manipulation is measured against.
REFERENCE = tuple(f"curbase_s{i}" for i in range(1, 10))

GO, MARGINAL = 0.15, 0.06


def area_of(root: str, tag: str) -> float | None:
    p = Path(root) / f"outer_{tag}" / "ink_metric" / "metrics.json"
    if not p.exists():
        return None
    return float(json.loads(p.read_text())["summary"]["total_pixels"])


def verdict(delta: float) -> tuple[str, str]:
    if delta >= GO:
        return "GO", (
            f"{delta:.1%} is about {delta / SEED_AREA_CV:.0f}x the seed-noise CV and more than "
            "twice the incidental spread that made the arm-level study uninformative. The "
            "six-arm study is worth its ~33h."
        )
    if delta >= MARGINAL:
        return "MARGINAL", (
            f"{delta:.1%} beats the 6.5% incidental spread but not decisively. The six-arm "
            "study would need more arms than budgeted -- a FRESH decision, not an automatic go."
        )
    return "NO GO", (
        f"{delta:.1%} is no more than fitting already produces by accident. The question is not "
        "answerable by this route, and the direction closes for ~11h instead of ~33h."
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spiral-out", default=SPIRAL_OUT)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    areas = {t: area_of(args.spiral_out, t) for t in ARMS}
    missing = [t for t, v in areas.items() if v is None]
    if missing:
        raise SystemExit(
            f"not scored yet: {', '.join(missing)}. A partial sample is refused, not reported."
        )

    ref = [v for v in (area_of(args.spiral_out, t) for t in REFERENCE) if v is not None]
    print(f"{'arm':<14}{'radius':>8}{'total_pixels':>16}")
    for t in ARMS:
        print(f"{t:<14}{RADIUS[t]:>8}{areas[t]:>16,.0f}")

    lo, hi = areas["bounds_lo"], areas["bounds_hi"]
    delta = abs(hi - lo) / ((hi + lo) / 2)
    print(f"\n|delta area| = {delta:.2%}   (seed-noise CV {SEED_AREA_CV:.2%})")
    print(f"  ratio to seed noise: {delta / SEED_AREA_CV:.1f}x")

    if len(ref) >= 3:
        cv = st.stdev(ref) / st.mean(ref)
        print(f"  reference curbase area CV over {len(ref)} seed-only arms: {cv:.2%}")
        print(
            "    (the registered floor came from a different set; this is a live check)"
        )

    tag, why = verdict(delta)
    print(f"\nVERDICT: {tag}\n  {why}")
    print(
        "\nThis says NOTHING about ink. Two arms cannot, and the registration does not claim it."
    )

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "arms": {
                        t: {"radius": RADIUS[t], "total_pixels": areas[t]} for t in ARMS
                    },
                    "delta_area": round(delta, 5),
                    "seed_area_cv": SEED_AREA_CV,
                    "ratio_to_seed_noise": round(delta / SEED_AREA_CV, 3),
                    "verdict": tag,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
