"""What z-ROI of villa's spiral fit fits on one 24 GB GPU, and in whose coordinates?

WHY. villa deprecated ink-detection and moved to spiral-fitting, which runs its
own LLM research loop (`spiral-fitting/autoresearch.md`) against a frozen
ink-coverage objective. That loop assumes an 8-GPU box: two concurrent runs on
four GPUs each. We have one RTX 4090. Before any of that work is worth planning,
two numbers have to be measured rather than guessed:

  1. how much of the scroll's z range fits in 24 GB, and
  2. what coordinate space the patch bboxes are in, since they do not match the
     resident-pool array.

WHAT IS MEASURED. Nothing is assumed about occupancy. The resident pool is a
flat packed brick array; `brick_coords.npy` lists the (z,y,x) brick index of
every occupied brick, so summing bricks per z-slab gives the exact bytes per z.
Row 0 is a [-1,-1,-1] no-data sentinel and is dropped.

TWO CORRECTIONS THIS SCRIPT ENCODES, both caught by re-reading a first answer:

  * A window search over the FULL z axis reports a wider window than the data
    supports, because the pool's first ~1800 z voxels are empty and the search
    happily counts them as coverage. Windows are therefore searched only over
    the occupied range.
  * Sizing against the SDT pool alone overstates what fits. SDT is 32.58 of the
    47.48 GiB payload; nx/ny and grad_mag share the same VRAM.

THE COORDINATE QUESTION. Patch bboxes run to z 18669 while the pool array is
9473 z, so they are not the same space. Rather than assume a factor, each
candidate is scored on two things: what fraction of patches map in-range, and
how well patch area correlates with pool occupancy across z.

LIMITS. The correlation is computed over whatever patch metas have been fetched,
which is a name-ordered prefix of 89,237, not a random sample. The in-range
fraction is the decisive signal here and the correlation is corroboration. This
sizes the resident pools only; model, activations and optimizer state also live
on the card, which is why the budget is swept rather than fixed.

Run:
    uv run python scripts/size_spiral_roi.py
"""

import glob
import json
import os

import numpy as np

DATA = os.environ.get(
    "SPIRAL_DATA", "/home/jon/openclaw-workspace/Neo-VM/data/spiral_s1"
)
SDT = os.path.join(DATA, "lasagna_inputs/las_008_surf_sdt.ome.zarr.respool_g1")
PAYLOAD_GIB = 47.48  # sdt 32.58 + nx 5.07 + ny 5.07 + grad_mag 4.75, measured
SDT_GIB = 32.58


def pool_profile():
    """GiB of SDT resident pool per brick-z slab, and the occupied range."""
    meta = json.load(open(os.path.join(SDT, "meta.json")))
    coords = np.load(os.path.join(SDT, "brick_coords.npy"))
    bs, nz = meta["brick_shape"][0], meta["grid_shape"][0]
    valid = coords[(coords >= 0).all(axis=1)]  # drop the no-data sentinel row
    gib = np.bincount(valid[:, 0], minlength=nz).astype(np.int64) * bs**3 / 2**30
    occ = np.nonzero(gib)[0]
    return gib, bs, nz, occ[0], occ[-1] + 1


def widest_window(gib, lo, hi, budget):
    """Widest contiguous brick-z window inside [lo,hi) whose GiB fits `budget`."""
    best, run, j = (0, lo, lo), 0.0, lo
    for i in range(lo, hi):
        while j < hi and run + gib[j] <= budget:
            run += gib[j]
            j += 1
        if j - i > best[0]:
            best = (j - i, i, j)
        run -= gib[i]
    return best


def main():
    gib, bs, nz, lo, hi = pool_profile()
    print(
        f"SDT pool {gib.sum():.2f} GiB over occupied brick-z {lo}-{hi} "
        f"(z voxels {lo * bs}-{hi * bs}, {(hi - lo) * bs} slices)"
    )
    frac = SDT_GIB / PAYLOAD_GIB
    print(
        f"SDT is {frac:.1%} of the {PAYLOAD_GIB} GiB payload; budgets below are TOTAL pool VRAM\n"
    )
    print(
        f"{'pool VRAM':>10} | {'widest occupied z window (pool coords)':^40} | % of z"
    )
    print("-" * 74)
    for total in (8.0, 10.0, 12.0, 14.0, 16.0, 18.0):
        n, i, j = widest_window(gib, lo, hi, total * frac)
        print(
            f"{total:7.1f} GiB | z {i * bs:5d}-{j * bs:5d} = {n * bs:5d} slices"
            f" ({gib[i:j].sum():5.2f} GiB SDT) | {100 * n / (hi - lo):4.1f}%"
        )

    metas = glob.glob(os.path.join(DATA, "metas", "*.json"))
    if not metas:
        print("\n(no patch metas fetched yet; skipping the coordinate check)")
        return
    cent, area = [], []
    for f in metas:
        b = json.load(open(f))
        bb = b["bbox"]
        cent.append((bb[0][2] + bb[1][2]) / 2.0)
        area.append(b.get("area_vx2", 0.0))
    cent, area = np.array(cent), np.array(area)
    pool = gib / max(gib.max(), 1e-9)
    print(
        f"\nPatch bbox z runs {cent.min():.0f}-{cent.max():.0f}; pool array is {nz * bs} z."
        f" Which scale maps patches into pool coords?  (n={len(cent)})"
    )
    for k in (1, 2, 4):
        zb = (cent / k / bs).astype(int)
        ok = (zb >= 0) & (zb < nz)
        if not ok.any():
            continue
        h = np.bincount(zb[ok], weights=area[ok], minlength=nz)
        c = np.corrcoef(pool, h)[0, 1] if h.sum() else float("nan")
        print(f"  {k}x : in-range {ok.mean():6.1%}   corr(pool, patch area) {c:+.3f}")
    print("\n  in-range is the decisive column; correlation corroborates.")


if __name__ == "__main__":
    main()
