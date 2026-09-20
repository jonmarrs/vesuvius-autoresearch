"""Radial displacement on the FLAT surface: does displacement cause the ink loss?

Implements `docs/preregistration/2026-09-20_radial_displacement_on_the_flat_surface.md`
and nothing else. **Written while the ZERO arm was still rendering**, so no arm had
a score and no threshold could be fitted to one.

Two rules this encodes, both earned:

* **The floor F is MEASURED, never assumed.** The previous design took 1.42% from
  a report that attributed the spread to the nnU-Net scorer; the scorer is
  0.0032% and the flatten was the real source, which invalidated that study
  (`reports/the_radial_study_design_is_invalid.md`). Here F = |ZERO - rad0|, two
  renders of one byte-identical flat surface, and every threshold is a multiple
  of it.
* **A large F is a RESULT, not a nuisance.** If removing the flatten did not buy a
  tight floor, `vc_render` itself is noisy; that is worth reporting, and IN/OUT
  must not be interpreted at n=1. The script refuses rather than softening the
  threshold.

`3F` is a margin against a measured floor, **not a significance test** — one arm
per condition has no sampling distribution. The output says so.
"""

import argparse
import json
import sys
from pathlib import Path

F_MAX = 0.015  # above this the redesign failed; do not interpret IN/OUT
MARGIN = 3.0  # an effect must clear MARGIN * F
IN_LO, IN_HI = 0.05, 0.15  # the gap fix's loss band
INK = "total_fg_pixels"


def ink(spec: str) -> tuple[str, float]:
    tag, _, path = spec.partition("=")
    if not path:
        raise SystemExit(f"expected tag=path, got {spec!r}")
    return tag, json.loads(Path(path).read_text())["summary"][INK]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "arms", nargs="+", help="rad0=<json> zero=<json> [in=<json> out=<json>]"
    )
    ap.add_argument("--out", default=None)
    ap.add_argument(
        "--floor-only", action="store_true", help="report F alone, before IN/OUT exist"
    )
    a = ap.parse_args()

    v = dict(ink(s) for s in a.arms)
    for need in ("rad0", "zero"):
        if need not in v:
            raise SystemExit(f"missing {need!r}: F cannot be measured without it")

    F = abs(v["zero"] - v["rad0"]) / v["rad0"]
    print("RADIAL DISPLACEMENT ON THE FLAT SURFACE\n")
    for k in ("rad0", "zero", "in", "out"):
        if k in v:
            print(f"  {k:<6}{v[k]:>14,.0f}")
    print(f"\nFLOOR F = |zero - rad0| / rad0 = {F:.3%}")
    print("  two renders of ONE byte-identical flat surface: render + scorer only,")
    print("  with the stochastic flatten held fixed.")

    # Annotated: it later carries the verdict string alongside the numbers.
    res: dict[str, object] = {"F": F, "rad0": v["rad0"], "zero": v["zero"]}

    if F > F_MAX:
        print(f"\nVERDICT: REDESIGN FAILED  (F = {F:.2%} > {F_MAX:.1%})")
        print("  Removing the flatten did not buy a tight floor, so vc_render itself")
        print("  is noisy. F is the finding. IN/OUT are NOT interpreted at n=1.")
        res["verdict"] = "REDESIGN FAILED"
        if a.out:
            Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
        return 0

    print(f"  F <= {F_MAX:.1%}: the floor is tight enough to interpret single arms.")
    missing = [k for k in ("in", "out") if k not in v]
    if a.floor_only or missing:
        print(f"\nFloor only; {', '.join(missing) or 'IN/OUT'} not scored. No verdict.")
        if a.out:
            Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
        return 0

    d_in = (v["in"] - v["zero"]) / v["zero"]
    d_out = (v["out"] - v["zero"]) / v["zero"]
    loss = -d_in
    need = MARGIN * F
    print(f"\n{'arm':<12}{'vs ZERO':>12}{'margin needed':>16}")
    print(f"{'IN  (-4vx)':<12}{d_in:>11.2%}{need:>15.2%}")
    print(f"{'OUT (+4vx)':<12}{d_out:>11.2%}{need:>15.2%}")

    if loss < need:
        verdict, why = (
            "NOT THE CAUSE",
            (
                f"IN moved less than {MARGIN:g}x the measured floor. Displacement at this "
                f"magnitude does not produce the gap fix's loss."
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
                "displacement moves ink, but not by the gap fix's amount -- a separate "
                "effect, NOT its mechanism."
            ),
        )
    print(f"\nVERDICT: {verdict}\n  {why}")
    print(
        f"\n  {MARGIN:g}F is a margin against a MEASURED floor, not a significance test:"
    )
    print("  one arm per condition has no sampling distribution.")
    print("  OUT carried no registered prediction and is reported as found.")
    print("  This isolates ONE channel; the gap fix also changes the fit itself.")

    res.update({"in": d_in, "out": d_out, "verdict": verdict, "margin": need})
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
