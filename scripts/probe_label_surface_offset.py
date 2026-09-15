"""Feasibility probe: are the spiral dataset's labels already ON the surface?

villa names label quality "one of the main unwrapping bottlenecks" and proposes
**label snapping** -- moving approximate labels onto the most plausible surface
using the raw CT signal. Before anyone pre-registers how to validate that, the
cheaper question is whether the condition is REACHABLE here: if the labels already
sit on the surface, snapping is a no-op and the direction closes for free.

That ordering is a lesson this project paid for. The sheet-switch detector was
built and then closed because its premise was unreachable; the rule taken from it
is to ask whether the detected condition can occur before designing the validation.

**The signal.** `lasagna_inputs/las_008_surf_sdt...respool_g1` is a surface signed
distance transform derived from CT -- independent of the spiral fit, so using it is
NOT circular the way selecting on the fit's own residual was
(`reports/patch_bootstrap_verdict.md`).

**The comparison.** The `u8` encoding of that field is undocumented here, so the
absolute value means little. Patch-surface points are therefore compared against
RANDOM points drawn from the same bricks: if labels sit on the surface, their SDT
distribution should be sharply separated from the random one. A weak separation
means either the labels are off-surface or the field does not localise the surface
-- both of which matter before committing to snapping.

Storage is a custom sparse "respool" v2: bricks of 32^3, a (grid) table.npy of row
indices, and one flat u8 file. Patch coords are level 0; the field is level 1, so
indices are halved.
"""

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np
import tifffile


class Respool:
    def __init__(self, root: str):
        self.root = Path(root)
        m = json.loads((self.root / "meta.json").read_text())
        self.shape = tuple(m["array_shape"])
        self.brick = tuple(m["brick_shape"])
        self.table = np.load(self.root / "table.npy", mmap_mode="r")
        self.data = np.memmap(self.root / "channel_0.u8", dtype=np.uint8, mode="r")
        self.bvox = int(np.prod(self.brick))

    def sample(self, zyx: np.ndarray) -> np.ndarray:
        """Values at integer (z,y,x) rows; NaN where the brick is not stored."""
        out = np.full(len(zyx), np.nan, dtype=np.float64)
        bz, by, bx = (zyx // np.array(self.brick)).T
        ok = (
            (bz >= 0)
            & (bz < self.table.shape[0])
            & (by >= 0)
            & (by < self.table.shape[1])
            & (bx >= 0)
            & (bx < self.table.shape[2])
        )
        if not ok.any():
            return out
        rows = np.full(len(zyx), -1, dtype=np.int64)
        rows[ok] = self.table[bz[ok], by[ok], bx[ok]]
        have = ok & (rows >= 0)
        if not have.any():
            return out
        dz, dy, dx = (zyx[have] % np.array(self.brick)).T
        off = rows[have] * self.bvox + (dz * self.brick[1] + dy) * self.brick[2] + dx
        out[have] = self.data[off]
        return out

    def stored_bricks(self) -> np.ndarray:
        return np.load(self.root / "brick_coords.npy", mmap_mode="r")


def patch_points(pdir: Path, n: int, rng: random.Random) -> np.ndarray | None:
    try:
        x, y, z = (tifffile.imread(pdir / f"{c}.tif") for c in "xyz")
    except (FileNotFoundError, ValueError, OSError):
        return None
    m = np.isfinite(x) & np.isfinite(y) & np.isfinite(z) & (x > 0) & (y > 0)
    idx = np.flatnonzero(m.ravel())
    if idx.size == 0:
        return None
    take = rng.sample(list(idx), min(n, idx.size)) if idx.size > n else idx
    return np.stack([z.ravel()[take], y.ravel()[take], x.ravel()[take]], axis=1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dataset", default="/home/jon/openclaw-workspace/Neo-VM/data/spiral_s1"
    )
    ap.add_argument("--patches", type=int, default=20)
    ap.add_argument("--per-patch", type=int, default=400)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    ds = Path(args.dataset)
    field = next(iter(ds.glob("lasagna_inputs/*surf_sdt*")), None)
    if field is None:
        raise SystemExit("no surf_sdt field in this dataset")
    rp = Respool(str(field))
    print(f"field {field.name}\n  shape {rp.shape} brick {rp.brick}")

    rng = random.Random(args.seed)
    names = sorted(p.name for p in (ds / "verified_patches").iterdir() if p.is_dir())
    picked = rng.sample(names, min(args.patches, len(names)))

    pts = []
    for nm in picked:
        p = patch_points(ds / "verified_patches" / nm, args.per_patch, rng)
        if p is not None:
            pts.append(p)
    if not pts:
        raise SystemExit("no usable patch points")
    lab = np.concatenate(pts)
    lab_idx = (lab / 2.0).astype(np.int64)  # level 0 -> level 1
    lab_v = rp.sample(lab_idx)

    # Random points from bricks that are actually stored, so the control samples
    # the same region of the volume rather than empty space.
    bricks = np.asarray(rp.stored_bricks())
    sel = bricks[rng.sample(range(len(bricks)), min(len(lab), len(bricks)))]
    jitter = np.random.default_rng(args.seed).integers(
        0, rp.brick[0], size=(len(sel), 3)
    )
    rnd_v = rp.sample(sel * np.array(rp.brick) + jitter)

    lv, rv = lab_v[np.isfinite(lab_v)], rnd_v[np.isfinite(rnd_v)]
    print(
        f"\n  label points sampled {len(lab)}, resolved {len(lv)} ({len(lv) / len(lab):.0%})"
    )
    print(
        f"  random points        {len(rnd_v)}, resolved {len(rv)} ({len(rv) / max(len(rnd_v), 1):.0%})"
    )
    if len(lv) < 50 or len(rv) < 50:
        print("\n  TOO FEW RESOLVED to say anything. Probe inconclusive.")
        return 2

    for nm, v in (("labels", lv), ("random", rv)):
        q = np.percentile(v, [5, 25, 50, 75, 95])
        print(
            f"  {nm:<8} mean {v.mean():7.2f}  median {np.median(v):6.1f}  "
            f"p5/p25/p75/p95 {q[0]:.0f}/{q[1]:.0f}/{q[3]:.0f}/{q[4]:.0f}"
        )

    # CONCENTRATION, not location. A standardised mean difference was tried first
    # and is the wrong statistic here: it reported |d| = 0.066, "no separation",
    # while the labels were in fact pinned to a single value (IQR 0) inside a field
    # ranging 0-167. Labels sitting ON a surface look like a spike, not a shift, and
    # a location statistic pooled over variance throws exactly that away.
    mode = int(np.bincount(lv.astype(int)).argmax())
    liqr = float(np.percentile(lv, 75) - np.percentile(lv, 25))
    riqr = float(np.percentile(rv, 75) - np.percentile(rv, 25))
    lw = float(np.mean(np.abs(lv - mode) <= 2))
    rw = float(np.mean(np.abs(rv - mode) <= 2))
    print(f"\n  label mode = {mode}")
    print(
        f"  IQR           labels {liqr:.1f}   random {riqr:.1f}"
        f"   -> {riqr / max(liqr, 0.5):.1f}x more concentrated"
    )
    print(
        f"  within +/-2   labels {lw:.3f}   random {rw:.3f}"
        f"   -> {lw / max(rw, 1e-9):.2f}x enriched"
    )
    print("\n  A tight spike at one value = labels already lie on the surface the")
    print("  field encodes, so snapping has little headroom. A broad label")
    print("  distribution = labels are off-surface and snapping has work to do.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
