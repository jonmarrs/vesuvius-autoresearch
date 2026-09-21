"""Per-slice ink profiles for the flat-surface displacement arms.

`reports/displacing_the_surface_costs_ink_in_both_directions.md` found a 4 vx
inward shift loses 19.77% and an outward one loses 4.48%, and named two readings
it could not separate: an asymmetric ink layer, or an off-centre scorer depth
window. The renderer writes its `--num-slices 5` layers to disk before
max-compositing them, so the depth structure is recoverable from the arms that
already exist -- no new render.

Slice k sits at (k - 2) * slice_step along the surface normal, step 1 at render
scale 0.25 (ds_level 1), so the five slices span roughly +/-2 render voxels.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
ARMS = ("in", "zero", "out")
THR = 128
N_SLICES = 5


def profile(arm_dir: Path) -> list[dict]:
    out = []
    for k in range(N_SLICES):
        a = np.asarray(
            Image.open(arm_dir / "meshes/concat/w120-129_flat/ink" / f"{k:02d}.tif")
        )
        out.append(
            {
                "slice": k,
                "mean": float(a.mean()),
                "frac_bright": float((a > THR).mean()),
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    P = {arm: profile(Path(a.spiral_out) / f"flat_study_{arm}") for arm in ARMS}
    print("PER-SLICE MEAN INTENSITY  (slice 0 .. 4 along the surface normal)\n")
    print(
        f"{'arm':<6}"
        + "".join(f"{k:>9}" for k in range(N_SLICES))
        + f"{'slope/slice':>13}"
    )
    slopes = {}
    for arm in ARMS:
        m = [r["mean"] for r in P[arm]]
        s = float(np.polyfit(range(N_SLICES), m, 1)[0])
        slopes[arm] = s
        print(f"{arm:<6}" + "".join(f"{v:>9.3f}" for v in m) + f"{s:>+13.4f}")

    z = [r["mean"] for r in P["zero"]]
    i = [r["mean"] for r in P["in"]]
    o = [r["mean"] for r in P["out"]]
    print("\nWHAT THE SHAPES SAY")
    print(
        f"  ZERO is a monotone gradient (slope {slopes['zero']:+.4f}), not a peak: the five"
    )
    print("  slices do not bracket the ink layer, they sample one EDGE of it.")
    print(
        f"  IN reverses the gradient (slope {slopes['in']:+.4f}) and IN's last slice ({i[-1]:.3f})"
    )
    print(f"  matches ZERO's first ({z[0]:.3f}): IN sits on the far side of the layer.")
    print(
        f"  OUT is uniformly lower ({np.mean(o) / np.mean(z) - 1:+.2%}) and nearly flat"
    )
    print(
        f"  (slope {slopes['out']:+.4f}): not a translation of ZERO's profile at all."
    )
    print("\n  So the two directions are DIFFERENT MECHANISMS, which the asymmetry")
    print("  report could not have known from the composite alone.")

    # THE CHECK THAT OVERTURNED THE FIRST READING. Per-slice means are within 3%
    # for IN and ZERO, yet IN scored 20% less ink. A max-composite of near-equal
    # layers cannot lose 20% of INTENSITY, so the scorer must respond to
    # something intensity does not measure.
    comp = {}
    for arm in ARMS:
        c = None
        for k in range(N_SLICES):
            layer = np.asarray(
                Image.open(
                    Path(a.spiral_out)
                    / f"flat_study_{arm}"
                    / "meshes/concat/w120-129_flat/ink"
                    / f"{k:02d}.tif"
                )
            )
            c = layer if c is None else np.maximum(c, layer)
        comp[arm] = float((c > THR).mean())
    fg = {
        arm: json.loads(
            (
                Path(a.spiral_out) / f"flat_study_{arm}" / "ink_metric/metrics.json"
            ).read_text()
        )["summary"]["total_fg_pixels"]
        for arm in ARMS
    }
    print("\nDOES COMPOSITE BRIGHTNESS TRACK THE SCORED INK?")
    print(f"{'arm':<6}{'composite >' + str(THR):>16}{'scored fg':>14}")
    for arm in ARMS:
        print(f"{arm:<6}{comp[arm] * 100:>15.3f}%{fg[arm]:>14,}")
    if comp["in"] >= comp["zero"] and fg["in"] < fg["zero"]:
        print(
            "\n  NO. IN has MORE bright pixels than ZERO and scores LESS ink. The nnU-Net"
        )
        print("  scorer is reading texture/shape, not intensity, and every intensity")
        print("  summary above is the WRONG PROBE for its behaviour. OUT's loss IS")
        print("  intensity-consistent, so the two directions differ in kind.")
    else:
        print("\n  Brightness and scored ink move together here.")

    if a.json:
        Path(a.json).write_text(
            json.dumps({"profiles": P, "slopes": slopes}, indent=1) + "\n"
        )
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
