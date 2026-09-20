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

    gate = rel(vals["baseline"], vals["zero"])
    ok = abs(gate) <= PIPELINE_FLOOR
    print(
        f"\nZERO GATE: {gate:+.2%} vs baseline  (allowed +/-{PIPELINE_FLOOR:.2%})  -> "
        f"{'PASS' if ok else 'FAIL'}"
    )
    if not ok:
        print("\nVERDICT: VOID -- the rebuild path does not reproduce its own source.")
        print(
            "  No claim is made about displacement. This is a pipeline defect report."
        )
        if a.out:
            Path(a.out).write_text(
                json.dumps({"verdict": "VOID", "zero_gate": gate}, indent=1) + "\n"
            )
        return 1
    if missing:
        print("\nZERO gate only; IN/OUT not yet scored. No verdict.")
        return 0

    d_in, d_out = rel(vals["baseline"], vals["in"]), rel(vals["baseline"], vals["out"])
    print(f"\n{'arm':<10}{'delta vs baseline':>20}")
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
