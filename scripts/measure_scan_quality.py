"""Does a CT-only statistic predict how separable papyrus layers are?

EXPLORATORY. No pre-registration, no decision rule. This asks whether any simple
CT-only statistic tracks a label-derived measure of layer separability at all. If
none does, that is the finding and nothing further gets built.

THE OUTCOME (uses labels, so it exists only on annotated cubes).
`separability_auc` is the ROC-AUC of raw CT intensity discriminating
sheet-interior voxels from the gaps between sheets. Where the scan is clean,
papyrus and gap have distinct intensities and the AUC is high. Where the
compressed-region haze described in villa's open-problems doc has blurred the
boundaries, the two distributions overlap and the AUC falls toward 0.5. This is a
direct reading of "papyrus layers that should be cleanly separable become hard to
tell apart".

Sheet voxels are ERODED before sampling, and gap voxels are taken at a distance
from any sheet, so the measure is about the bulk of each population rather than
about the transition zone, which is partial-volume by construction and would
otherwise dominate.

THE PREDICTORS (CT only, so they generalise to unlabelled volume). Deliberately
simple, because a complicated predictor that works is hard to distinguish from
one that has been fitted to 12 cubes:

  * `intensity_std`      spread of raw intensity;
  * `grad_median`        median gradient magnitude, an edge-strength proxy;
  * `grad_p90_over_p50`  how much stronger the strong edges are than the typical
                         one. Haze should compress this ratio;
  * `tensor_anisotropy`  mean structure-tensor anisotropy, high where the volume
                         is locally layered and low where it is foggy.

WHAT THIS CANNOT SHOW. The cubes are hand-annotated and were therefore selected
for being annotatable, so the worst compressed regions are plausibly absent.
Any relationship measured here sits on the tractable end of the range.

Run:
    uv run python scripts/measure_scan_quality.py --data <cube_dir> [--out report.json]
"""

import argparse
import json
import os

import numpy as np


def outcome_separability(vol, mask):
    """ROC-AUC of CT intensity, sheet interior vs inter-sheet gap."""
    from scipy import ndimage

    lab = mask > 0
    interior = ndimage.binary_erosion(lab, iterations=2)
    dist = ndimage.distance_transform_edt(~lab)
    gap = (dist >= 2) & (dist <= 6)  # between sheets, off the transition
    if interior.sum() < 1000 or gap.sum() < 1000:
        return float("nan"), int(interior.sum()), int(gap.sum())
    rng = np.random.default_rng(0)
    n = min(interior.sum(), gap.sum(), 200_000)
    a = rng.choice(vol[interior].astype(np.float32), n, replace=False)
    b = rng.choice(vol[gap].astype(np.float32), n, replace=False)
    # AUC via rank statistic
    both = np.concatenate([a, b])
    order = np.argsort(both, kind="mergesort")
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(1, both.size + 1)
    auc = (ranks[: a.size].sum() - a.size * (a.size + 1) / 2) / (a.size * b.size)
    return float(max(auc, 1 - auc)), int(interior.sum()), int(gap.sum())


def predictors(vol):
    """CT-only statistics. No labels are touched here, by construction."""
    from scipy import ndimage

    v = vol.astype(np.float32)
    gz, gy, gx = np.gradient(v)
    g = np.sqrt(gz * gz + gy * gy + gx * gx)
    gm = g[g > 0]
    # structure tensor anisotropy on a coarse grid, cheap and orientation-free
    s = 2.0
    jzz = ndimage.gaussian_filter(gz * gz, s)
    jyy = ndimage.gaussian_filter(gy * gy, s)
    jxx = ndimage.gaussian_filter(gx * gx, s)
    tr = jzz + jyy + jxx
    top = np.maximum.reduce([jzz, jyy, jxx])
    aniso = np.where(tr > 1e-6, top / np.maximum(tr, 1e-6), 0.0)
    return {
        "intensity_std": float(v.std()),
        "grad_median": float(np.median(gm)) if gm.size else float("nan"),
        "grad_p90_over_p50": float(
            np.percentile(gm, 90) / max(np.percentile(gm, 50), 1e-6)
        )
        if gm.size
        else float("nan"),
        "tensor_anisotropy": float(aniso.mean()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--data", default="/home/jon/openclaw-workspace/Neo-VM/data/scroll1_cubes"
    )
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    import nrrd

    cubes = sorted(
        d
        for d in os.listdir(args.data)
        if d[:1].isdigit() and os.path.isdir(os.path.join(args.data, d))
    )
    rows = []
    for c in cubes:
        vp = os.path.join(args.data, c, f"{c}_volume.nrrd")
        mp = os.path.join(args.data, c, f"{c}_mask.nrrd")
        if not (os.path.exists(vp) and os.path.exists(mp)):
            continue
        vol, _ = nrrd.read(vp)
        msk, _ = nrrd.read(mp)
        auc, n_int, n_gap = outcome_separability(vol, msk)
        row = {"cube": c, "separability_auc": auc, "n_interior": n_int, "n_gap": n_gap}
        row.update(predictors(vol))
        rows.append(row)
        print(
            f"  {c}  AUC {auc:.4f}  "
            + "  ".join(
                f"{k} {row[k]:.4f}"
                for k in (
                    "intensity_std",
                    "grad_median",
                    "grad_p90_over_p50",
                    "tensor_anisotropy",
                )
            ),
            flush=True,
        )

    if len(rows) < 4:
        print("\ntoo few cubes to correlate")
        return
    y = np.array([r["separability_auc"] for r in rows])
    ok = np.isfinite(y)
    print(
        f"\noutcome separability_auc over {ok.sum()} cubes: "
        f"min {y[ok].min():.4f}  median {np.median(y[ok]):.4f}  max {y[ok].max():.4f}"
    )
    print("\ncorrelation of each CT-only predictor with the outcome:")
    for k in ("intensity_std", "grad_median", "grad_p90_over_p50", "tensor_anisotropy"):
        x = np.array([r[k] for r in rows])
        m = ok & np.isfinite(x)
        if m.sum() < 4:
            continue
        r = np.corrcoef(x[m], y[m])[0, 1]
        xr = np.argsort(np.argsort(x[m])).astype(float)
        yr = np.argsort(np.argsort(y[m])).astype(float)
        rho = np.corrcoef(xr, yr)[0, 1]
        print(f"  {k:<20} pearson {r:+.3f}   spearman {rho:+.3f}   (n={m.sum()})")
    print("\nExploratory, on hand-annotated cubes selected for being annotatable.")
    if args.out:
        json.dump(rows, open(args.out, "w"), indent=2)
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
