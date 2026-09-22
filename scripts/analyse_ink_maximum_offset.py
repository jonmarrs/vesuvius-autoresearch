"""Where is the ink maximum relative to the fitted surface?

Implements `docs/preregistration/2026-09-22_ink_maximum_offset.md`. **Written
before any new arm was built**, while the pooled-floor chain held the GPU.

Seven offsets of ONE flattened surface, rendered with the flatten held fixed, so
the floor is F = 0.0014% (24 px) rather than the 3.04% a re-flatten would cost.

**Amended 2026-09-22, before any new arm was built** (see the registration's
amendment): the lever verdict is read off the OBSERVED arms -- does any displaced
offset out-score 0 vx by MARGIN * F? The parabola is kept as description only.
The registered rule took the gain from the fitted vertex, and a symmetric
quadratic through the known-asymmetric response (-19.77% in, -4.48% out) puts
its vertex outward even when the true maximum is exactly 0 vx: on such a curve it
returned LEVER EXISTS, PREDICTION MET with every displaced arm below 0 vx
(tests/test_analyse_ink_maximum_offset.py::test_asymmetry_alone_is_not_a_lever).

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
F = 1.4127e-05  # 24 px / 1,698,831 -- reports/flat_displacement_floor.json (was typed 10x too big)
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

    # ---- the decision: model-free, on the observed arms ----------------------
    displaced = [(x, y) for x, y in zip(xs, ys, strict=True) if x != 0.0]
    best_x, best_y = max(displaced, key=lambda p: p[1])
    obs_gain = (best_y - zero) / zero
    lever = obs_gain >= MARGIN * F
    print(
        f"\n  best displaced arm: {best_x:+.0f} vx at {obs_gain:+.4%} vs 0 vx "
        f"(lever needs >= {MARGIN * F:+.4%} = {MARGIN:g} x F)"
    )

    # ---- the parabola: DESCRIPTION ONLY ----------------------------------------
    c = np.polyfit(xs, ys, 2)
    fit = np.polyval(c, xs)
    ss_res = float(((ys - fit) ** 2).sum())
    ss_tot = float(((ys - ys.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot
    print(f"  parabola R^2 = {r2:.4f}   (vertex described only if >= {R2_MIN})")
    out: dict[str, object] = {
        "offsets": dict(zip(map(float, xs), map(float, ys), strict=True)),
        "best_displaced_offset": float(best_x),
        "observed_gain": float(obs_gain),
        "margin": MARGIN * F,
        "r2": r2,
    }
    x0 = None
    if r2 < R2_MIN or c[0] >= 0:
        why = (
            "the parabola does not describe the sweep"
            if r2 < R2_MIN
            else "the fitted quadratic opens upward -- there is no maximum"
        )
        print(f"  NO VERTEX CLAIMED -- {why}; the sweep is reported as a curve.")
    else:
        x0 = float(-c[1] / (2 * c[0]))
        model_gain = float((np.polyval(c, x0) - zero) / zero)
        print(
            f"  vertex x0 = {x0:+.2f} vx, model gain {model_gain:+.2%} "
            f"(registered: +1.42 vx, 1.36%) -- NOT used for the verdict"
        )
        out.update({"x0": x0, "model_gain": model_gain})

    if lever:
        v = "LEVER EXISTS"
        read = (
            f"Rendering at {best_x:+.0f} vx scores {obs_gain:+.2%} over the fitted surface "
            f"with no change to the fit -- an objective-gaming route in the "
            f"duplicate-coverage class."
        )
    else:
        v = "NO FREE LEVER"
        read = (
            f"No displaced offset beats the fitted surface by {MARGIN:g} x F; a global "
            f"offset cannot move the objective at this resolution."
        )
    print(f"\nVERDICT: {v}\n  {read}")
    if x0 is not None:
        met = PRED_LO <= x0 <= PRED_HI
        print(
            f"  prediction 1 (vertex in [{PRED_LO}, {PRED_HI}] vx): "
            f"{'in band' if met else 'MISS, recorded as a miss'} -- but asymmetry alone"
        )
        print("  puts a symmetric fit's vertex outward, so this does not discriminate.")
    print(f"  prediction 2 (gain ~1.4%): best observed arm {obs_gain:+.2%}")
    print(
        "\n  A gain here is the METRIC moving. The scorer reads texture, and this study"
    )
    print("  has no legibility endpoint -- it does not show more text is readable.")

    out["verdict"] = v
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1) + "\n")
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
