"""Local sheet separation against local ink disagreement, within windings.

Implements `docs/preregistration/2026-09-13_separation_within_winding.md`.

The previous attempt binned by (z, theta) and averaged surface radius across bins
holding several windings, so its "separation" was the difference of two
multi-winding averages -- 3.6 vx median, against an independently measured ~24 vx.
`reports/separation_test_was_confounded.md` has the post-mortem.

This works in the strip's own grid, where the ROW index is the across-winding
coordinate (449 rows over 10 windings, ~45 each). A row sits within one winding,
so nothing is averaged across sheets. Separation is then the 3D distance between
the two arms' (x, y, z) at the same cell -- the actual local offset between the
fitted sheets, not a radius difference.

Arms are resampled onto a common grid first: rows agree within 1%, columns differ
by ~3% because each fit flattens its own strip.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compare_ink_in_volume import ink_per_cell, load_xyz  # noqa: E402

BLOCK = 8  # registered, not swept
N_SHUFFLE = 1000
SANITY_VX = (10.0, 30.0)  # median separation must land here or the result is void


def arm_grid(arm_dir: str):
    """(x, y, z, ink) on the arm's own strip grid, invalid cells as nan."""
    xyz = load_xyz(arm_dir)
    if xyz is None:
        return None
    x, y, z = xyz
    ink = ink_per_cell(arm_dir, x.shape)
    if ink is None:
        return None
    bad = ~((x > 0) & (y > 0) & np.isfinite(x) & np.isfinite(y) & np.isfinite(z))
    x, y, z = x.copy(), y.copy(), z.copy()
    for a in (x, y, z):
        a[bad] = np.nan
    return x, y, z, ink.astype(np.float64)


def to_common(arr: np.ndarray, rows: int, cols: int) -> np.ndarray:
    """Nearest-neighbour resample to a common grid. Nearest, not linear: linear
    interpolation across a nan boundary would silently invent surface."""
    r_idx = np.clip(
        (np.arange(rows) * arr.shape[0] / rows).astype(int), 0, arr.shape[0] - 1
    )
    c_idx = np.clip(
        (np.arange(cols) * arr.shape[1] / cols).astype(int), 0, arr.shape[1] - 1
    )
    return arr[np.ix_(r_idx, c_idx)]


def blocks(a: np.ndarray, agg="mean") -> np.ndarray:
    h = a.shape[0] // BLOCK * BLOCK
    w = a.shape[1] // BLOCK * BLOCK
    v = a[:h, :w].reshape(h // BLOCK, BLOCK, w // BLOCK, BLOCK)
    return np.nanmean(v, axis=(1, 3)) if agg == "mean" else np.nansum(v, axis=(1, 3))


def analyse(A, B, rng: np.random.Generator) -> dict:
    from scipy import stats

    rows = min(A[0].shape[0], B[0].shape[0])
    cols = min(A[0].shape[1], B[0].shape[1])
    ax, ay, az, ai = (to_common(v, rows, cols) for v in A)
    bx, by, bz, bi = (to_common(v, rows, cols) for v in B)

    with np.errstate(invalid="ignore"):
        sep = np.sqrt((ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2)
    sep_b = blocks(sep)
    ia, ib = blocks(ai, "sum"), blocks(bi, "sum")

    ok = np.isfinite(sep_b) & ((ia + ib) > 0)
    n = int(ok.sum())
    if n < 100:
        return {"n_blocks": n, "rho": float("nan"), "p": float("nan"), "void": True}
    s = sep_b[ok]
    d = np.abs(ia[ok] - ib[ok]) / (ia[ok] + ib[ok])
    med = float(np.median(s))
    obs = float(stats.spearmanr(s, d).statistic)
    null = np.array(
        [stats.spearmanr(s, rng.permutation(d)).statistic for _ in range(N_SHUFFLE)]
    )
    p = float((np.abs(null) >= abs(obs)).mean())
    void = not (SANITY_VX[0] <= med <= SANITY_VX[1])
    return {
        "n_blocks": n,
        "rho": obs,
        "p": p,
        "sep_median": med,
        "sep_p90": float(np.percentile(s, 90)),
        "dis_median": float(np.median(d)),
        "void": void,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument(
        "--arms", nargs="+", default=["curbase_s1", "curbase_s2", "curbase_s3"]
    )
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    grids = {}
    for tag in args.arms:
        g = arm_grid(f"{args.spiral_out}/outer_{tag}")
        if g is None:
            print(f"{tag}: unusable, skipped")
            continue
        grids[tag] = g
        print(
            f"{tag:<16} grid {g[0].shape[0]} x {g[0].shape[1]}  ink {g[3].sum():>12,.0f}"
        )

    tags = list(grids)
    if len(tags) < 2:
        raise SystemExit("need two usable arms")

    rng = np.random.default_rng(0)
    print(
        f"\nlocal sheet separation vs ink disagreement, {BLOCK}x{BLOCK} blocks, "
        f"{N_SHUFFLE} shuffles"
    )
    print(f"{'pair':<30}{'blocks':>8}{'sep med':>9}{'rho':>8}{'p':>8}  verdict")
    rows = []
    for i, a in enumerate(tags):
        for b in tags[i + 1 :]:
            r = analyse(grids[a], grids[b], rng)
            r.update(a=a, b=b)
            rows.append(r)
            if r["void"]:
                v = f"VOID (sep {r['sep_median']:.1f} outside {SANITY_VX})"
            elif r["p"] < 0.05:
                v = "SUPPORTED" if r["rho"] > 0 else "OPPOSITE (surprise)"
            else:
                v = "not supported"
            print(
                f"{a + ' vs ' + b:<30}{r['n_blocks']:>8,}{r['sep_median']:>9.1f}"
                f"{r['rho']:>8.3f}{r['p']:>8.3f}  {v}"
            )

    live = [r for r in rows if not r["void"]]
    sup = [r for r in live if r["p"] < 0.05 and r["rho"] > 0]
    if not live:
        print(
            "\nALL PAIRS VOID -- the frame is still wrong; this is not a null result."
        )
    else:
        print(f"\n{len(sup)} of {len(live)} non-void pairs support normal displacement")

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "block": BLOCK,
                    "n_shuffle": N_SHUFFLE,
                    "sanity_vx": SANITY_VX,
                    "pairs": rows,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
