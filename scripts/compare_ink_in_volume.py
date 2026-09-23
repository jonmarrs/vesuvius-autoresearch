"""Compare where the ink is in VOLUME coordinates, not strip coordinates.

`compare_ink_placement.py` found that fits differing only by RNG seed agree on
the ink COUNT to ~1% while their along-strip ink profiles correlate ~0.66. It
could not say whether the ink genuinely moved or whether the two flattenings warp
differently, because it compared in strip space and each fit makes its own strip.

This removes that ambiguity. Every fit's flattened strip has a tifxyz beside it
giving the volume (x, y, z) of each strip cell, so ink can be placed in the
scroll's own frame, which is common to all arms.

The grids line up exactly: the prediction masks are 10x the tifxyz in both axes
(4490x89820 against 449x8982), so mask cell (r, c) belongs to tifxyz cell
(r//10, c//10). That is verified per arm rather than assumed, and an arm whose
ratio is not 10 is skipped rather than silently mis-mapped.

Ink is then binned by (z, theta) around the scroll axis -- a frame no flattening
can rotate -- and the binned maps are compared between arms. A high correlation
here means the arms really do put ink in the same places and the strip-space
disagreement was the flattening; a low one means the ink itself moves.

The axis is taken as the centroid of the strip's own points, which is a
convention, not a measurement: it is identical for every arm only because the
arms cover nearly the same surface. Arms are therefore binned against ONE shared
axis, computed once from the reference arm.
"""

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np

try:
    import tifffile
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = None
except ImportError:  # pragma: no cover
    tifffile = Image = None

SCALE = 10  # mask pixels per tifxyz cell, per axis; verified per arm
NZ, NTHETA = 96, 256


def arm_path(spiral_out: str, tag: str, prefix: str = "outer_") -> str:
    """The corpus arms are named outer_<tag>; other work dirs (detfit_*, radial_work_*)
    are not, so the prefix is an option rather than baked into every lookup."""
    return f"{spiral_out}/{prefix}{tag}"


def tile_index(path: str) -> int:
    return int(Path(path).stem.split(".")[-1])


def ink_per_cell(arm_dir: str, shape: tuple[int, int]) -> np.ndarray | None:
    """Ink pixel count per tifxyz cell, by summing SCALE x SCALE mask blocks."""
    fs = sorted(
        glob.glob(f"{arm_dir}/ink_metric/predictions/*mask*.png"), key=tile_index
    )
    if not fs:
        return None
    h, w = shape
    # Rows may be blocked per tile (every tile has the full height), but COLUMNS
    # may not: tiles are 16384 wide, which is not divisible by SCALE=10, so
    # truncating each tile independently loses a cell or two per tile and silently
    # shifts everything after it. Concatenate at pixel resolution first, then block.
    rows = []
    for f in fs:
        a = np.array(Image.open(f)) > 127
        if a.shape[0] != h * SCALE:
            return None
        rows.append(
            a[: h * SCALE].reshape(h, SCALE, a.shape[1]).sum(axis=1).astype(np.int32)
        )
    full = np.concatenate(rows, axis=1)  # (h, total_mask_width)
    if full.shape[1] != w * SCALE:
        return None
    return full.reshape(h, w, SCALE).sum(axis=2)


def load_xyz(arm_dir: str):
    """Eager, not a generator.

    This returned a generator expression, so the try/except never fired: nothing
    was read inside the try, and the FileNotFoundError escaped later when a
    caller consumed it. An arm that had not been rendered yet crashed the script
    instead of being reported as missing -- which only surfaced when
    `analyse_consensus_forward.py` was run against a study still in flight.
    """
    d = f"{arm_dir}/meshes/concat/w120-129_flat"
    try:
        return tuple(tifffile.imread(f"{d}/{c}.tif").astype(np.float64) for c in "xyz")
    except (FileNotFoundError, ValueError, OSError):
        return None


def volume_map(arm_dir: str, axis: tuple[float, float] | None):
    """(z, theta) histogram of ink, plus the axis used."""
    xyz = load_xyz(arm_dir)
    if xyz is None:
        return None, axis
    x, y, z = xyz
    ink = ink_per_cell(arm_dir, x.shape)
    if ink is None:
        return None, axis
    m = (x > 0) & (y > 0) & np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    if not m.any():
        return None, axis
    if axis is None:
        axis = (float(x[m].mean()), float(y[m].mean()))
    cx, cy = axis
    th = np.arctan2(y[m] - cy, x[m] - cx)
    zz, w = z[m], ink[m].astype(np.float64)
    H, _, _ = np.histogram2d(
        zz,
        th,
        bins=[NZ, NTHETA],
        range=[[13056, 18432], [-np.pi, np.pi]],
        weights=w,
    )
    return H, axis


def corr(a: np.ndarray, b: np.ndarray) -> float:
    a, b = a.ravel(), b.ravel()
    keep = (a > 0) | (b > 0)
    if keep.sum() < 50:
        return float("nan")
    return float(np.corrcoef(a[keep], b[keep])[0, 1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument("--arms", nargs="+", required=True)
    ap.add_argument(
        "--prefix",
        default="outer_",
        help="work-dir prefix; '' for dirs named exactly as the tag",
    )
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    if tifffile is None:
        raise SystemExit("needs tifffile and Pillow")

    maps, axis = {}, None
    for tag in args.arms:
        H, axis = volume_map(arm_path(args.spiral_out, tag, args.prefix), axis)
        if H is None:
            print(
                f"{tag}: unusable (missing artifacts or bad mask/tifxyz ratio), skipped"
            )
            continue
        maps[tag] = H
        print(
            f"{tag:<20} ink in map {H.sum():>12,.0f}  occupied bins {int((H > 0).sum()):>6,}"
        )
    tags = list(maps)
    if len(tags) < 2 or axis is None:
        raise SystemExit("need two usable arms")
    print(f"shared axis (from {tags[0]}): ({axis[0]:.0f}, {axis[1]:.0f})")

    def grp(t: str) -> str:
        return t.rsplit("_s", 1)[0].replace("_pilot", "")

    print(f"\npairwise correlation of the (z, theta) ink map  [{NZ} x {NTHETA} bins]")
    print(f"{'pair':<46}{'r':>8}  kind")
    rows = []
    for i, a in enumerate(tags):
        for b in tags[i + 1 :]:
            r = corr(maps[a], maps[b])
            kind = "within" if grp(a) == grp(b) else "between"
            rows.append({"a": a, "b": b, "r": r, "kind": kind})
            print(f"{a + ' vs ' + b:<46}{r:>8.3f}  {kind}")

    for kind in ("within", "between"):
        v = [r["r"] for r in rows if r["kind"] == kind and np.isfinite(r["r"])]
        if v:
            print(f"  mean {kind:<8} r = {np.mean(v):.3f}  (n={len(v)})")

    # null: rotate one map in theta, which no flattening can do
    a0 = maps[tags[0]]
    nulls = [
        corr(a0, np.roll(maps[tags[1]], k, axis=1)) for k in (NTHETA // 4, NTHETA // 2)
    ]
    print(f"\nnull (theta-rotated): {', '.join(f'{n:.3f}' for n in nulls)}")

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "bins": [NZ, NTHETA],
                    "axis": axis,
                    "pairs": rows,
                    "null_rotated": nulls,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
