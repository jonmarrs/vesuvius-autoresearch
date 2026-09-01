"""Reachability check: do distinct spliced winding meshes cover the same 3D papyrus?

WHY THIS AND NOT SOMETHING ELSE. villa's spiral-fitting autoresearch loop
(spiral-fitting/autoresearch.md) optimises `total_fg_pixels`, the count of
ink-foreground pixels across rendered winding strips, and names one anti-gaming
guard: `overall_fg_fraction`, which "will collapse" if a change inflates the
surface with garbage geometry. That guard catches surface added over BLANK
papyrus. It cannot catch surface added over INKED papyrus that is already
counted, because duplicated coverage raises numerator and denominator together
and leaves the fraction flat. The doc calls a flat fraction with rising total
"a real win".

So the question is whether duplicate coverage is REACHABLE, asked before
building anything to exploit or detect it -- the lesson from the sheet-switch
detector, which was pre-registered before anyone checked its premise.

Two candidate mechanisms, one already ruled out:
  * plain vs `_spliced` variants of the same winding -- NOT a defect, render_ink.py
    filters to `'_spliced' in name`, so only one variant is ever rendered;
  * two DISTINCT spliced windings landing on the same papyrus -- what this measures.

Adjacent windings sit ~dr_per_winding apart (16.17 voxels in this fit), so they
should not share voxels at a quantisation well below that. The signal that
matters is overlap between windings FAR apart in index, which cannot be
explained by sheet spacing or by quantisation.
"""

import argparse
import json
import os
from collections import Counter

import numpy as np
import tifffile


def load_winding(d):
    """Return the (N,3) valid surface points of one tifxyz mesh. Invalid is -1."""
    xyz = [tifffile.imread(os.path.join(d, f"{c}.tif")) for c in "xyz"]
    ok = np.ones(xyz[0].shape, bool)
    for a in xyz:
        ok &= a > -0.5
    return np.stack([a[ok] for a in xyz], 1).astype(np.float64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("meshes_dir")
    ap.add_argument("--quant", type=int, nargs="+", default=[4, 8, 16])
    ap.add_argument("--out", default=None)
    ap.add_argument(
        "--dump-windings",
        default=None,
        help="save an (N,3) array of [cell_id, winding_min, winding_max] for the "
        "gap>=2 cells at the FIRST --quant value, answering WHICH windings overlap "
        "rather than inferring it from radius.",
    )
    ap.add_argument(
        "--dump-cells",
        default=None,
        help="save the gap>=2 multiply-claimed cell ids at the FIRST "
        "--quant value, for cross-seed comparison",
    )
    args = ap.parse_args()

    names = sorted(n for n in os.listdir(args.meshes_dir) if "_spliced" in n)
    if not names:
        raise SystemExit(f"no _spliced meshes in {args.meshes_dir}")
    widx, pts = [], []
    for n in names:
        p = load_winding(os.path.join(args.meshes_dir, n))
        if len(p):
            widx.append(int(n[1:4]))
            pts.append(p)
    print(
        f"{len(pts)} spliced windings, w{min(widx):03d}..w{max(widx):03d}, "
        f"{sum(len(p) for p in pts):,} valid surface points"
    )

    res = {"meshes_dir": args.meshes_dir, "n_windings": len(pts), "quant": {}}
    for Q in args.quant:
        cells, owner = [], []
        for w, p in zip(widx, pts, strict=False):
            q = np.floor(p / Q).astype(np.int64)
            k = (q[:, 2] * 1_000_003 + q[:, 1]) * 1_000_003 + q[:, 0]
            u = np.unique(k)  # one vote per winding per cell
            cells.append(u)
            owner.append(np.full(u.size, w, np.int64))
        cells = np.concatenate(cells)
        owner = np.concatenate(owner)
        order = np.argsort(cells, kind="mergesort")
        cells, owner = cells[order], owner[order]

        # a cell is multiply claimed if consecutive equal cell ids carry >1 winding
        starts = np.flatnonzero(np.r_[True, cells[1:] != cells[:-1]])
        counts = np.diff(np.r_[starts, cells.size])
        n_occ = starts.size
        multi = counts > 1
        gaps = Counter()
        for s, c in zip(starts[multi], counts[multi], strict=False):
            ws = owner[s : s + c]
            gaps[int(ws.max() - ws.min())] += 1
        far = sum(v for g, v in gaps.items() if g >= 2)
        if args.dump_windings and args.quant[0] == Q:
            rows = [
                (
                    int(cells[s]),
                    int(owner[s : s + c].min()),
                    int(owner[s : s + c].max()),
                )
                for s, c in zip(starts[multi], counts[multi], strict=False)
                if (owner[s : s + c].max() - owner[s : s + c].min()) >= 2
            ]
            np.save(args.dump_windings, np.array(rows, np.int64))
            print(
                f"      dumped {len(rows):,} [cell, wmin, wmax] rows -> {args.dump_windings}"
            )
        if args.dump_cells and args.quant[0] == Q:
            far_ids = [
                int(cells[s])
                for s, c in zip(starts[multi], counts[multi], strict=False)
                if (owner[s : s + c].max() - owner[s : s + c].min()) >= 2
            ]
            np.save(args.dump_cells, np.array(sorted(far_ids), np.int64))
            print(f"      dumped {len(far_ids):,} gap>=2 cell ids -> {args.dump_cells}")
        print(
            f"\nquant {Q:>3} vx   occupied cells {n_occ:>10,}   "
            f"multi-claimed {multi.sum():>9,} ({multi.sum() / n_occ * 100:5.2f}%)   "
            f"gap>=2 {far:>8,} ({far / n_occ * 100:5.2f}%)"
        )
        for g in sorted(gaps)[:8]:
            print(f"      winding gap {g:>3}: {gaps[g]:>9,} cells")
        res["quant"][Q] = {
            "occupied": int(n_occ),
            "multi": int(multi.sum()),
            "multi_frac": float(multi.sum() / n_occ),
            "far_gap2": int(far),
            "far_frac": float(far / n_occ),
            "gap_hist": {str(k): int(v) for k, v in sorted(gaps.items())},
        }
    if args.out:
        json.dump(res, open(args.out, "w"), indent=2)
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
