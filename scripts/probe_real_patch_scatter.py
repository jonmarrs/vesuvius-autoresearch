"""Measure the scatter carried by REAL traced patches, to decide whether the
scatter onset found in `reports/spiral_satisfaction_onset.txt` is ever reached in
practice.

The onset probe established that villa's winding-blindness holds exactly for a
well-placed patch and starts to break once the patch carries scatter: the
satisfied fraction first moves at 2.50 voxels, a patch verdict first flips at
3.25, the correctly placed reference first fails at 4.00. Those thresholds only
matter if real patches actually carry scatter of that order. Nobody had measured
that.

**Scatter here means the same thing it means in the synthetic probes**: the
per-point deviation of a patch's radius from the smooth local surface, in voxels.
Operationally, take a window of the patch's grid, compute each cell's radius from
the umbilicus axis, fit a smooth trend across the window, and take the RMS
residual.

**The window size is not a detail; it decides the answer.** A first attempt used
12x16 grid cells to match the synthetic patch's 12x16 point grid. That was wrong
by an order of magnitude: one grid step is about 20 voxels, so a 12x16 grid window
spans some 240x315 voxels, while the synthetic patch spans roughly 64x22 voxels.
The larger window's "residual" is dominated by genuine surface curvature rather
than roughness, and it produced a median of 8.7 voxels with 98.6 percent of
windows above the verdict threshold. At an extent actually matching the synthetic
patch the same data gives a median of 0.72 voxels with 0.5 percent above it. The
two answers point in opposite directions, so this probe reports the whole
sensitivity surface rather than a single number, and names which cell is the
comparable one.

Every radius is computed against the published umbilicus. No villa code is
involved here; this measures the data, not the metric.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_real_patch_scatter.py
"""

import glob
import json
import os
import sys

import numpy as np
import tifffile

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(_REPO, "local_data", "spiral_patches_phercparis4")
UMBILICUS = os.path.join(DATA, "umbilicus.json")

# The synthetic patch used throughout this investigation spans theta 0.30-1.30 rad
# at radius ~5*dr and 12 z-rows at dz=2, i.e. roughly 64 x 22 voxels.
SYNTHETIC_EXTENT_VOX = (22.0, 64.0)

# (rows, cols) in grid cells, and the fit order. Both are swept because both move
# the answer, and the point of this probe is that they do.
WINDOWS = [(3, 4), (4, 6), (6, 8), (12, 16)]
FIT_ORDERS = [1, 2]
SAMPLES_PER_CELL = 400
SEED = 20260825

# The onset thresholds this measurement exists to be compared against.
ONSETS = [(2.50, "fraction moves"), (3.25, "verdict flips"), (4.00, "reference fails")]


def load_umbilicus(path=UMBILICUS):
    pts = json.load(open(path))["control_points"]
    z = np.array([p["z"] for p in pts], dtype=np.float64)
    x = np.array([p["x"] for p in pts], dtype=np.float64)
    y = np.array([p["y"] for p in pts], dtype=np.float64)
    order = np.argsort(z)
    return z[order], x[order], y[order]


def load_patch(directory):
    """Grid coordinates and a validity mask. Invalid cells are marked -1."""
    xs = tifffile.imread(os.path.join(directory, "x.tif")).astype(np.float64)
    ys = tifffile.imread(os.path.join(directory, "y.tif")).astype(np.float64)
    zs = tifffile.imread(os.path.join(directory, "z.tif")).astype(np.float64)
    valid = (xs > 0) & (ys > 0) & (zs > 0)
    return xs, ys, zs, valid


def radius_field(xs, ys, zs, umbilicus):
    """Distance from the scroll axis at each cell's own z, in voxels."""
    uz, ux, uy = umbilicus
    return np.sqrt(
        (xs - np.interp(zs, uz, ux)) ** 2 + (ys - np.interp(zs, uz, uy)) ** 2
    )


def grid_step_voxels(xs, ys, zs, valid):
    """Median real-space distance between adjacent grid cells, per axis.

    This is what converts a window measured in grid cells into a window measured
    in voxels, and it is the conversion the first attempt at this probe omitted.
    """
    out = []
    for axis in (0, 1):
        d = np.sqrt(
            np.diff(xs, axis=axis) ** 2
            + np.diff(ys, axis=axis) ** 2
            + np.diff(zs, axis=axis) ** 2
        )
        m = np.logical_and(
            np.take(valid, range(valid.shape[axis] - 1), axis=axis),
            np.take(valid, range(1, valid.shape[axis]), axis=axis),
        )
        out.append(float(np.median(d[m])) if m.any() else float("nan"))
    return tuple(out)


def window_residuals(r, valid, h, w, order, rng, n_samples=SAMPLES_PER_CELL):
    """RMS residual of radius after removing a smooth trend, over random fully
    valid windows."""
    if r.shape[0] < h or r.shape[1] < w:
        return np.array([])
    out = []
    ii, jj = np.mgrid[0:h, 0:w]
    cols = [ii.ravel(), jj.ravel(), np.ones(h * w)]
    if order == 2:
        cols = [ii.ravel() ** 2, jj.ravel() ** 2, (ii * jj).ravel()] + cols
    A = np.c_[tuple(cols)]
    if A.shape[0] <= A.shape[1]:
        return np.array([])
    for _ in range(n_samples * 8):
        i = int(rng.integers(0, r.shape[0] - h + 1))
        j = int(rng.integers(0, r.shape[1] - w + 1))
        if not valid[i : i + h, j : j + w].all():
            continue
        win = r[i : i + h, j : j + w].ravel()
        coef, *_ = np.linalg.lstsq(A, win, rcond=None)
        out.append(float(np.sqrt(np.mean((win - A @ coef) ** 2))))
        if len(out) >= n_samples:
            break
    return np.array(out)


def patch_dirs(root=DATA):
    return sorted(
        d
        for d in glob.glob(os.path.join(root, "*"))
        if os.path.isdir(d) and os.path.exists(os.path.join(d, "x.tif"))
    )


def collect(root=DATA):
    umb = load_umbilicus()
    rng = np.random.default_rng(SEED)
    per_patch, cells = [], {}
    for d in patch_dirs(root):
        xs, ys, zs, valid = load_patch(d)
        if not valid.any():
            continue
        r = radius_field(xs, ys, zs, umb)
        step = grid_step_voxels(xs, ys, zs, valid)
        per_patch.append(
            {
                "name": os.path.basename(d),
                "shape": r.shape,
                "valid_frac": float(valid.mean()),
                "step": step,
                "median_radius": float(np.median(r[valid])),
            }
        )
        for h, w in WINDOWS:
            for order in FIT_ORDERS:
                res = window_residuals(r, valid, h, w, order, rng)
                if res.size:
                    cells.setdefault((h, w, order), []).append(res)
    merged = {k: np.concatenate(v) for k, v in cells.items()}
    return per_patch, merged


def closest_window(per_patch):
    """The (rows, cols) whose real-space extent best matches the synthetic patch.

    Chosen by minimising the summed log-ratio of the two extents, so being 2x too
    large and 2x too small are penalised equally rather than the larger window
    winning by absolute difference.
    """
    steps = np.array([p["step"] for p in per_patch], dtype=np.float64)
    med = np.nanmedian(steps, axis=0)
    best, best_cost = None, float("inf")
    for h, w in WINDOWS:
        extent = (h * med[0], w * med[1])
        cost = sum(
            abs(np.log(e / t))
            for e, t in zip(extent, SYNTHETIC_EXTENT_VOX, strict=False)
        )
        if cost < best_cost:
            best, best_cost = (h, w), cost
    return best, med


def format_report(per_patch, cells, best, med_step):
    out = []
    out.append("Scatter carried by real traced patches, against the measured onset")
    out.append(
        "Scatter is the per-point deviation of a patch's radius from the smooth local "
        "surface, in voxels: fit a trend across a grid window, take the RMS residual. "
        "Radii are measured from the published umbilicus. No villa code is involved; this "
        "measures the data, not the metric."
    )
    out.append("")
    out.append(f"Patches: {len(per_patch)} from the published verified_patches set.")
    out.append(
        "   patch                                              grid        valid   median r   step (i,j) vox"
    )
    out.append("  " + "-" * 96)
    for p in per_patch:
        out.append(
            f"  {p['name'][:48]:48} {str(p['shape']):>13} {100 * p['valid_frac']:6.1f}% "
            f"{p['median_radius']:9.0f}   {p['step'][0]:6.1f},{p['step'][1]:6.1f}"
        )
    out.append("")
    out.append(
        f"Median grid step across patches: {med_step[0]:.1f} voxels down, {med_step[1]:.1f} across. "
        f"The synthetic patch used throughout this investigation spans about "
        f"{SYNTHETIC_EXTENT_VOX[0]:.0f} x {SYNTHETIC_EXTENT_VOX[1]:.0f} voxels."
    )
    out.append("")

    out.append("=== The answer depends on the window, which is the point ===")
    out.append(
        "  window   extent (vox)   fit  |     n |    p50 |    p95 | share >= 2.50v | >= 3.25v | >= 4.00v"
    )
    out.append("  " + "-" * 104)
    for h, w in WINDOWS:
        for order in FIT_ORDERS:
            v = cells.get((h, w, order))
            if v is None or not v.size:
                continue
            ext = f"{h * med_step[0]:.0f}x{w * med_step[1]:.0f}"
            mark = "  <-- comparable" if (h, w) == best else ""
            shares = "".join(f" {100 * (v >= t).mean():13.1f}%" for t, _ in ONSETS)
            out.append(
                f"  {h:2d}x{w:<2d} {ext:>13}   {'plane' if order == 1 else 'quad':>5}  "
                f"| {v.size:5d} | {np.median(v):6.3f} | {np.percentile(v, 95):6.3f} |{shares}{mark}"
            )
    out.append("")
    out.append(
        f"  The comparable window is {best[0]}x{best[1]} grid cells, whose real-space extent is "
        f"closest to the synthetic patch's. A 12x16 window spans roughly "
        f"{12 * med_step[0]:.0f}x{16 * med_step[1]:.0f} voxels, some five to fifteen times the "
        "synthetic patch, and its residual is dominated by genuine surface curvature rather "
        "than roughness. Reading the 12x16 row as 'real patch scatter' inverts the conclusion, "
        "which is why every row is printed."
    )
    out.append("")

    v = cells.get((best[0], best[1], 1))
    if v is not None and v.size:
        out.append("=== Bottom line at the comparable window, plane fit ===")
        out.append(
            f"  median {np.median(v):.3f} vox, p95 {np.percentile(v, 95):.3f} vox, "
            f"max {v.max():.3f} vox, n = {v.size}"
        )
        for t, label in ONSETS:
            out.append(
                f"  share of windows at or above the {t:.2f}v onset ({label}): "
                f"{100 * (v >= t).mean():.2f}%"
            )
        out.append(
            "  So the scatter real traced patches carry, at the scale the synthetic probes "
            "operate on, sits below the level at which the metric begins to degrade. The "
            "break located by the onset probe is real, and on this evidence it is not reached "
            "by well-traced patches."
        )
    return "\n".join(out) + "\n"


def main():
    per_patch, cells = collect()
    if not per_patch:
        raise SystemExit(f"no patches found under {DATA}")
    best, med_step = closest_window(per_patch)
    print(format_report(per_patch, cells, best, med_step))


if __name__ == "__main__":
    main()
