"""Where is the ink maximum relative to the fitted surface?

Implements `docs/preregistration/2026-09-22_ink_maximum_offset.md`. **Written
before any new arm was built**, while the pooled-floor chain held the GPU.

Seven offsets of ONE flattened surface, rendered with the flatten held fixed, so
the floor is F = 0.0014% (24 px) rather than the 3.04% a re-flatten would cost.

The branch worth stating in code: **if the parabola fits badly the vertex is not
reported at all.** A quadratic is a local convenience assumed from two points,
not a law, and this project has watched a per-voxel ratio fail to extrapolate
three times. R^2 < 0.8 means the model, not the hypothesis, is what the data
speak to.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

# offset (vx) -> work dir. -4/0/+4 come from the displacement study.
ARMS = {
    -4.0: "flat_study_in",
    -2.0: "offset_m2",
    0.0: "flat_study_zero",
    1.0: "offset_p1",
    2.0: "offset_p2",
    3.0: "offset_p3",
    4.0: "flat_study_out",
}
F = 0.000141  # measured floor, holding_the_flatten_fixed_collapses_the_floor.md
MARGIN = 3.0  # an effect must clear MARGIN * F
PRED_LO, PRED_HI = 0.4, 2.4  # registered band for the vertex
R2_MIN = 0.8  # below this, no vertex is claimed
INK = "total_fg_pixels"


def ink(so: Path, arm: str) -> float:
    p = so / arm / "ink_metric" / "metrics.json"
    if not p.exists():
        raise SystemExit(
            f"{arm} not scored. All seven offsets are required; a partial sweep is "
            f"refused, not reported."
        )
    return json.loads(p.read_text())["summary"][INK]


def require_all_scored(so: Path) -> None:
    """Refuse a partial sweep BEFORE touching provenance, so a missing arm gives
    the registered refusal rather than a FileNotFoundError from a provenance read."""
    missing = [
        a
        for a in ARMS.values()
        if not (so / a / "ink_metric" / "metrics.json").exists()
    ]
    if missing:
        raise SystemExit(
            f"not scored: {', '.join(missing)}. All seven offsets are required; a "
            f"partial sweep is refused, not reported."
        )


def provenance(so: Path) -> tuple[set[str], set[str]]:
    shas, imgs = set(), set()
    for a in ARMS.values():
        shas.add((so / a / "VILLA_SHA").read_text().strip())
        ri = (so / a / "RENDER_IMAGE").read_text()
        imgs.add(
            next(
                ln.split("=", 1)[1]
                for ln in ri.splitlines()
                if ln.startswith("image_id=")
            )
        )
    return shas, imgs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    so = Path(a.spiral_out)

    require_all_scored(so)
    shas, imgs = provenance(so)
    print("INK MAXIMUM OFFSET: seven displacements of one flattened surface\n")
    print(f"  provenance: {len(shas)} VILLA_SHA, {len(imgs)} image_id")
    if len(shas) != 1 or len(imgs) != 1:
        print("\nVERDICT: VOID -- the offsets were not rendered on one instrument.")
        return 1

    xs = np.array(sorted(ARMS))
    ys = np.array([ink(so, ARMS[x]) for x in xs], dtype=float)
    zero = ys[list(xs).index(0.0)]

    print(f"\n{'offset':>8}{'total_fg':>14}{'vs 0 vx':>10}")
    for x, y in zip(xs, ys, strict=False):
        print(f"{x:>+8.0f}{y:>14,.0f}{(y - zero) / zero:>+10.2%}")

    c = np.polyfit(xs, ys, 2)
    fit = np.polyval(c, xs)
    ss_res = float(((ys - fit) ** 2).sum())
    ss_tot = float(((ys - ys.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot
    print(f"\n  parabola R^2 = {r2:.4f}   (vertex claimed only if >= {R2_MIN})")

    out: dict[str, object] = {
        "offsets": dict(zip(map(float, xs), map(float, ys), strict=False)),
        "r2": r2,
    }

    if r2 < R2_MIN or c[0] >= 0:
        why = (
            "the parabola does not describe the sweep"
            if r2 < R2_MIN
            else "the fitted quadratic opens upward -- there is no maximum"
        )
        print(f"\nVERDICT: NO VERTEX CLAIMED -- {why}.")
        print(
            "  Reported as a curve. The quadratic was assumed from two points and the"
        )
        print(
            "  data refuse it; this is the branch where my model, not the hypothesis,"
        )
        print("  is what the data speak to.")
        out["verdict"] = "NO VERTEX"
        if a.json:
            Path(a.json).write_text(json.dumps(out, indent=1) + "\n")
        return 0

    x0 = -c[1] / (2 * c[0])
    peak = float(np.polyval(c, x0))
    gain = (peak - zero) / zero
    print(f"  vertex x0 = {x0:+.2f} vx     predicted gain over 0 vx = {gain:+.2%}")
    print("  registered prediction: x0 = +1.42 vx, gain 1.36%")

    big = gain >= MARGIN * F
    if abs(x0) <= 1.0 and not big:
        v, read = (
            "NO FREE LEVER",
            (
                "The fit lands on the ink maximum; a global offset cannot move the objective."
            ),
        )
    elif PRED_LO <= x0 <= PRED_HI and big:
        v, read = (
            "LEVER EXISTS, PREDICTION MET",
            (
                "A fixed outward offset buys objective points with no change to the fit -- an "
                "objective-gaming route in the duplicate-coverage class."
            ),
        )
    elif big:
        v, read = (
            "LEVER EXISTS, PREDICTION MISSED",
            ("The offset moves the objective, but not where the quadratic model said."),
        )
    else:
        v, read = (
            "NO FREE LEVER",
            "Any vertex offset buys less than 3x the measured floor.",
        )
    print(f"\nVERDICT: {v}\n  {read}")
    print(
        f"  prediction 1 (vertex in [{PRED_LO}, {PRED_HI}] vx): "
        f"{'MET' if PRED_LO <= x0 <= PRED_HI else 'MISS, recorded as a miss'}"
    )
    print(f"  prediction 2 (gain ~1.4%): observed {gain:+.2%}")
    print(
        "\n  A gain here is the METRIC moving. The scorer reads texture, and this study"
    )
    print("  has no legibility endpoint -- it does not show more text is readable.")

    out.update({"x0": float(x0), "gain": float(gain), "verdict": v})
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1) + "\n")
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
