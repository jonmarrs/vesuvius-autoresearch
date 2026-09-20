"""Build a mesh set displaced RADIALLY by a controlled amount, for a causal test.

`reports/the_gap_fix_moves_the_surface_radially.md` found the gap-expander fix
moves the scored surface inward ~3.96 voxels while losing 10.35% of the ink, and
said plainly that the co-occurrence is **observational**: the fix changes a
config, and both follow. Isolating displacement as the cause needs a manipulation
that moves the surface radially and changes NOTHING else.

That is what this builds. It takes an existing fit's `_spliced` meshes, pushes
every valid point along its radial direction from a derived axis, and writes a new
tifxyz mesh set the render pipeline accepts. **No refitting**, so the geometry is
otherwise bit-identical to its source -- which is exactly the control the
observational finding lacks.

The axis is derived from the SOURCE arm's own points, once, and reused for every
displacement, so arms differ only in `--delta`.

Sentinel points (`z <= 0`) are left untouched and stay invalid: they carry garbage
`x,y` that displaced the derived axis by ~200 voxels when included
(`reports/the_gap_fix_moves_the_surface_radially.md`), so they must not be moved
or counted.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import tifffile


def valid_mask(x, y, z):
    return ((x != 0) | (y != 0) | (z != 0)) & (z > 0) & np.isfinite(x) & np.isfinite(y)


def derive_axis(src: Path, pattern: str) -> tuple[float, float]:
    xs, ys = [], []
    for d in sorted(src.glob(pattern)):
        x = tifffile.imread(d / "x.tif")
        y = tifffile.imread(d / "y.tif")
        z = tifffile.imread(d / "z.tif")
        m = valid_mask(x, y, z)
        xs.append(x[m])
        ys.append(y[m])
    return float(np.concatenate(xs).mean()), float(np.concatenate(ys).mean())


def displace_one(
    d: Path, out: Path, cx: float, cy: float, delta: float, tag: str
) -> dict:
    x = tifffile.imread(d / "x.tif").astype(np.float32)
    y = tifffile.imread(d / "y.tif").astype(np.float32)
    z = tifffile.imread(d / "z.tif").astype(np.float32)
    m = valid_mask(x, y, z)

    dx, dy = x[m] - cx, y[m] - cy
    r = np.hypot(dx, dy)
    r_safe = np.where(r > 1e-6, r, 1.0)  # a point ON the axis has no radial direction
    x[m] = cx + dx / r_safe * (r + delta)
    y[m] = cy + dy / r_safe * (r + delta)

    out.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(out / "x.tif", x)
    tifffile.imwrite(out / "y.tif", y)
    tifffile.imwrite(out / "z.tif", z)

    meta = json.loads((d / "meta.json").read_text())
    # bbox MUST be recomputed: the render trims to it, so a stale bbox silently
    # clips the displaced surface.
    meta["bbox"] = [
        [float(x[m].min()), float(y[m].min()), float(z[m].min())],
        [float(x[m].max()), float(y[m].max()), float(z[m].max())],
    ]
    meta["uuid"] = d.name.replace(
        tag, f"{tag}_rad{delta:+g}".replace("+", "p").replace("-", "m")
    )
    meta["source"] = (
        f"radial displacement {delta:+g} vx of {d.name} about ({cx:.1f},{cy:.1f})"
    )
    (out / "meta.json").write_text(json.dumps(meta, indent=4))
    return {
        "n_valid": int(m.sum()),
        "mean_r_before": float(r.mean()),
        "mean_r_after": float(np.hypot(x[m] - cx, y[m] - cy).mean()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="a fit's meshes/<fitted_*> directory")
    ap.add_argument("--out", required=True)
    ap.add_argument(
        "--delta", type=float, required=True, help="radial shift in voxels, +outward"
    )
    ap.add_argument("--pattern", default="w1[23]*_spliced_*")
    ap.add_argument("--tag", default="baseline01")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    src, out = Path(a.src), Path(a.out)
    dirs = sorted(src.glob(a.pattern))
    if not dirs:
        raise SystemExit(f"no meshes matched {a.pattern} under {src}")
    cx, cy = derive_axis(src, a.pattern)
    print(f"axis derived from {len(dirs)} source meshes: cx={cx:.1f} cy={cy:.1f}")
    print(f"displacing {len(dirs)} windings by {a.delta:+g} voxels\n")

    if out.exists():
        shutil.rmtree(out)
    rows = {}
    for d in dirs:
        o = out / d.name
        rows[d.name] = displace_one(d, o, cx, cy, a.delta, a.tag)
        r = rows[d.name]
        print(
            f"  {d.name:<32} r {r['mean_r_before']:8.2f} -> {r['mean_r_after']:8.2f}"
            f"  ({r['mean_r_after'] - r['mean_r_before']:+.2f})"
        )

    achieved = np.mean([r["mean_r_after"] - r["mean_r_before"] for r in rows.values()])
    print(f"\nachieved mean shift {achieved:+.3f} vx (requested {a.delta:+g})")
    if abs(achieved - a.delta) > 0.01:
        raise SystemExit(
            "ACHIEVED SHIFT DOES NOT MATCH REQUEST -- the manipulation is not doing what it says"
        )
    print("wrote", out)
    if a.json:
        Path(a.json).write_text(
            json.dumps(
                {
                    "axis": [cx, cy],
                    "delta": a.delta,
                    "achieved": float(achieved),
                    "windings": rows,
                },
                indent=1,
            )
            + "\n"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
