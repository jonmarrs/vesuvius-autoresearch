"""Radial displacement study: does moving the surface CAUSE the ink loss?

**Written 2026-09-19 while the ZERO arm was still rendering**, before any arm
produced a score. Implements `docs/preregistration/2026-09-19_radial_displacement_causes_ink_loss.md`
and nothing else.

The rule worth stating in code rather than prose: **ZERO is a gate, not a data
point.** It re-renders `baseline01`'s own meshes displaced by 0 voxels, so it must
reproduce `baseline01`'s existing score. If it does not, the rebuild path is
broken and IN/OUT say nothing about displacement -- the study is VOID and this
script refuses to report an effect.

The floor here is the PIPELINE floor (1.42%), not the seed floor, because every
arm derives from one fit's meshes with no refitting. That is the whole reason the
study costs three renders instead of eighteen fits, and it is also why a mistake
in the ZERO gate would be invisible: at this floor almost anything looks
significant.
"""

import argparse
import json
import sys
from pathlib import Path

# reports/the_determinism_floor_rests_on_one_draw.md -- the CONSERVATIVE of the two
# measurements (1.42% and 0.0016%). Using the tighter one would overstate every result.
PIPELINE_FLOOR = 0.0142
IN_LO, IN_HI = 0.05, 0.15  # registered band for the IN arm's loss
INK = "total_fg_pixels"
REQUIRED = ("baseline", "zero", "in", "out")


def load(spec: str) -> tuple[str, float]:
    tag, _, path = spec.partition("=")
    if not path:
        raise SystemExit(f"expected tag=path, got {spec!r}")
    return tag, json.loads(Path(path).read_text())["summary"][INK]


def rel(a: float, b: float) -> float:
    return (b - a) / a


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "arms", nargs="+", help="baseline=<metrics.json> zero=... in=... out=..."
    )
    ap.add_argument("--out", default=None)
    ap.add_argument(
        "--allow-partial",
        action="store_true",
        help="report the ZERO gate alone, before IN/OUT exist",
    )
    a = ap.parse_args()

    vals = dict(load(s) for s in a.arms)
    missing = [k for k in REQUIRED if k not in vals]
    if missing and not (a.allow_partial and {"baseline", "zero"} <= set(vals)):
        raise SystemExit(
            f"missing arm(s) {missing}. A partial sample is refused, not reported "
            f"(--allow-partial reports the ZERO gate only)."
        )

    print(f"RADIAL DISPLACEMENT STUDY. pipeline floor {PIPELINE_FLOOR:.2%}\n")
    for k in REQUIRED:
        if k in vals:
            print(f"  {k:<10}{vals[k]:>14,.0f}")

    # DIAGNOSTIC, not a void gate. Amended 2026-09-19 BEFORE any arm was scored.
    # The registration called this a hard gate; that was wrong. `baseline` was
    # rendered 2026-09-01 on an older villa tree, so a mismatch here can mean
    # render-code drift rather than a broken rebuild, and this number alone cannot
    # separate them. It is reported and interpreted, never used to void IN/OUT --
    # those are measured against ZERO on one pinned tree and do not depend on it.
    gate = rel(vals["baseline"], vals["zero"])
    ok = abs(gate) <= PIPELINE_FLOOR
    print(
        f"\nDRIFT CHECK: ZERO vs baseline {gate:+.2%} (pipeline floor {PIPELINE_FLOOR:.2%})"
    )
    if ok:
        print("  within the floor: the rebuild reproduces a render from 2026-09-01,")
        print("  so no render-code drift is detectable across that interval either.")
    else:
        print("  OUTSIDE the floor. Two explanations, NOT separable from this number:")
        print(
            "    (a) render code changed since 2026-09-01 -- rerender_test_verdict.md"
        )
        print("        measured +1.44% from one such change, wider than this floor; or")
        print("    (b) the rebuild path alters the surface even at delta=0.")
        print("  IN/OUT remain interpretable: all three arms rendered today on one")
        print("  pinned tree and are compared against ZERO, never against baseline.")
    if missing:
        print("\nDrift check only; IN/OUT not yet scored. No verdict.")
        return 0

    # AGAINST ZERO, NOT BASELINE. Amended 2026-09-19 before any arm was scored.
    # `baseline` was rendered 2026-09-01 on an older villa tree; ZERO, IN and OUT
    # all render today on pinned be09a8503. Comparing to `baseline` would import a
    # render-code difference -- reports/rerender_test_verdict.md measured +1.44%
    # from exactly such a change, larger than this study's whole floor. ZERO is the
    # same-tree, same-day, same-meshes control, so it is the only valid reference.
    d_in, d_out = rel(vals["zero"], vals["in"]), rel(vals["zero"], vals["out"])
    print(f"\n{'arm':<10}{'delta vs ZERO':>20}")
    print(f"{'IN  (-4vx)':<10}{d_in:>19.2%}")
    print(f"{'OUT (+4vx)':<10}{d_out:>19.2%}")

    loss = -d_in
    if loss < PIPELINE_FLOOR:
        verdict, why = (
            "NOT THE CAUSE",
            (
                "IN moved less than the pipeline floor. The gap fix's 10.35% comes from "
                "something else that changed with it; the radial shift is a side effect."
            ),
        )
    elif IN_LO <= loss <= IN_HI:
        verdict, why = (
            "SUFFICIENT",
            (
                "IN reproduces the gap fix's loss from displacement ALONE. Where the "
                "surface sits explains the cost, not what the fix does to the fit."
            ),
        )
    else:
        verdict, why = (
            "DIFFERENT EFFECT",
            (
                "displacement moves ink, but not by the gap fix's amount -- reported as a "
                "separate effect, NOT as its mechanism."
            ),
        )
    print(f"\nVERDICT: {verdict}\n  {why}")
    print(
        f"\nOUT carried NO registered prediction; it moved {d_out:+.2%} and is reported as found."
    )
    print("\nThis isolates ONE channel. The gap fix also changes the fit itself, so a")
    print("SUFFICIENT verdict does not make displacement the only mechanism.")

    if a.out:
        Path(a.out).write_text(
            json.dumps(
                {
                    "zero_gate": gate,
                    "in": d_in,
                    "out": d_out,
                    "verdict": verdict,
                    "floor": PIPELINE_FLOOR,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
