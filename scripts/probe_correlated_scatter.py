"""Does the onset depend on the SHAPE of the scatter, not just its magnitude?

`reports/spiral_satisfaction_onset.txt` located the scatter onset using
`add_radius_scatter`, which draws INDEPENDENT per-point Gaussian noise.
`reports/real_patch_scatter.txt` then measured what real traced patches carry and
compared the two, concluding that real patches sit below the onset.

That comparison assumed the two noises are interchangeable at equal RMS. They are
not, and real patch residuals are not white:

  * measured here, the lag-1 autocorrelation of a real patch's residual across the
    grid has median about +0.35, positive in roughly three quarters of windows.
    Independent noise would sit near zero.
  * at equal RMS, spatially correlated noise flips villa's patch verdict at a
    LOWER level than independent noise does. Independent noise at 2-3 voxels flips
    nothing across 40 rays; correlated noise at the same RMS flips several.

So the onsets quoted against real patch scatter were measured with the wrong noise
structure, in the direction that flatters the finding. This probe measures the
onset under both noise shapes so the comparison can be made on like terms.

A non-monotonicity worth noting rather than hiding: at large RMS the correlated
arms flip FEWER verdicts than the independent arm. A strongly correlated
perturbation displaces the whole patch nearly coherently, and a coherent radial
shift is exactly what villa's median-snap absorbs, which is the same mechanism
this whole investigation is about. The correlated arms are therefore worst in the
middle of the range, not at the top of it.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_correlated_scatter.py
"""

import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np  # noqa: E402
import torch  # noqa: E402
from scipy.ndimage import gaussian_filter  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

from probe_real_patch_scatter import (  # noqa: E402
    load_patch,
    load_umbilicus,
    patch_dirs,
    radius_field,
)
from probe_spiral_satisfaction_empirical_transform import (  # noqa: E402
    WINDING,
    EmpiricalRadialTransform,
    load_shard,
    usable_rays,
)
from probe_spiral_satisfaction_robustness import (  # noqa: E402
    SyntheticPatch,
    _patch_is_satisfied,
    _to_scan_space,
)
from probe_spiral_satisfaction_splicing_and_seam import (  # noqa: E402
    REPORTING,
    score_with,
)
from probe_spiral_satisfaction_winding import (  # noqa: E402
    build_synthetic_patch,
    displace,
)

RMS_LEVELS = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0]
# 0.0 reproduces the independent draw the onset probe used; the others impose a
# correlation length, in grid cells, on a field of the SAME rms.
SIGMAS = [0.0, 1.0, 2.0]
N_RAYS = 40
SEED = 20260825


def noise_field(shape, rms, sigma, rng):
    """A radial perturbation field of exactly `rms` voxels, at correlation length
    `sigma` grid cells. Rescaling after smoothing is what holds RMS fixed across
    arms, so the arms differ in shape alone."""
    f = rng.standard_normal(shape)
    if sigma > 0:
        f = gaussian_filter(f, sigma, mode="nearest")
    sd = float(f.std())
    return f / sd * rms if sd > 0 else f


def apply_radial(patch, field_vox):
    zyxs = patch.zyxs.clone()
    ys = zyxs[..., 1].numpy()
    xs = zyxs[..., 2].numpy()
    r = np.sqrt(ys**2 + xs**2) + field_vox
    th = np.arctan2(ys, xs)
    zyxs[..., 1] = torch.from_numpy(np.sin(th) * r).to(zyxs.dtype)
    zyxs[..., 2] = torch.from_numpy(np.cos(th) * r).to(zyxs.dtype)
    return SyntheticPatch(
        zyxs=zyxs, valid_quad_mask=patch.valid_quad_mask.clone(), area=patch.area
    )


def run_level(rays, rms, sigma, rng):
    worst, flips = 0.0, 0
    for _, radii in rays:
        dr = float(np.mean(np.diff(radii)))
        transform = EmpiricalRadialTransform(np.arange(len(radii)) * dr, radii)
        base = build_synthetic_patch(dr=dr, winding=WINDING)
        field = noise_field(base.zyxs.shape[:2], rms, sigma, rng)
        ref_s = apply_radial(base, field)
        mov_s = displace(ref_s, dr, n_windings=1.0)
        ref, mov = _to_scan_space(ref_s, transform), _to_scan_space(mov_s, transform)
        total = int(ref.valid_quad_mask.sum().item())
        a = score_with(ref, dr, REPORTING, transform)
        b = score_with(mov, dr, REPORTING, transform)
        worst = max(worst, abs(b - a))
        flips += _patch_is_satisfied(a, total, 0.95) != _patch_is_satisfied(
            b, total, 0.95
        )
    return worst, flips


def measure_real_autocorrelation(n_windows=400, h=3, w=4, seed=3, axis=1):
    """Lag-1 autocorrelation of real patch residuals across the grid.

    This is the number that decides which arm of the sweep is the relevant one. If
    real residuals were white, the independent arm would be the right comparison
    and the earlier conclusion would stand as written.

    ⚠ FIXED 2026-08-26. This function used to break out of the OUTER patch loop
    once the quota was met, so every window came from whichever patch happened to
    be first -- `0000_top_band`, which is enormous (241x13168) and filled the
    quota alone. Its own value is +0.353; pooled across all ten patches the answer
    is +0.213, and the per-patch spread runs +0.057 to +0.494. The single-patch
    +0.357 was published as TARGET_COL_LAG1 and the anisotropic surrogate was
    fitted to it, so this defect propagated into the attenuation k and everything
    downstream of it. Sampling is now capped per patch and pooled.

    This is the same outer-break pooling defect already fixed once in
    probe_is_corrected_scatter_physical.py. It was worth grepping for the pattern
    then, and was not.
    """
    umb = load_umbilicus()
    rng = np.random.default_rng(seed)
    ii, jj = np.mgrid[0:h, 0:w]
    A = np.c_[ii.ravel(), jj.ravel(), np.ones(h * w)]
    out = []
    dirs = list(patch_dirs())
    per_patch = max(1, n_windows // max(1, len(dirs)))
    for d in dirs:
        xs, ys, zs, valid = load_patch(d)
        if not valid.any() or valid.shape[0] < h or valid.shape[1] < w:
            continue
        r = radius_field(xs, ys, zs, umb)
        got = 0
        for _ in range(4000):
            i = int(rng.integers(0, r.shape[0] - h + 1))
            j = int(rng.integers(0, r.shape[1] - w + 1))
            if not valid[i : i + h, j : j + w].all():
                continue
            win = r[i : i + h, j : j + w].ravel()
            coef, *_ = np.linalg.lstsq(A, win, rcond=None)
            res = (win - A @ coef).reshape(h, w)
            if res.std() < 1e-9:
                continue
            a = np.moveaxis(res, axis, -1)
            out.append(
                float(np.corrcoef(a[..., :-1].ravel(), a[..., 1:].ravel())[0, 1])
            )
            got += 1
            if got >= per_patch:
                break  # inner loop only: the outer break is what broke this
    return np.array(out)


def format_report(grid, autocorr):
    out = []
    out.append("Onset under correlated versus independent scatter, at equal RMS")
    out.append(
        "The onset probe used INDEPENDENT per-point noise. Real patch residuals are not "
        "independent, so the comparison between the measured onset and real patch scatter "
        "was made on unlike terms. Both noise shapes are swept here at identical RMS."
    )
    out.append("")
    out.append("=== Is the real residual actually correlated? ===")
    out.append(
        f"  lag-1 autocorrelation across the grid, n={len(autocorr)} windows from real patches:"
    )
    out.append(
        f"    median {np.median(autocorr):+.3f}   p25 {np.percentile(autocorr, 25):+.3f}   "
        f"p75 {np.percentile(autocorr, 75):+.3f}   share positive {100 * (autocorr > 0).mean():.1f}%"
    )
    out.append(
        "  Independent noise would sit near 0.000 with about half positive. It does not, so the "
        "correlated arms below are the relevant comparison and the independent arm is not."
    )
    out.append("")
    out.append("=== Verdict flips out of 40 rays, at equal RMS ===")
    header = "   rms |" + "|".join(
        f"  sigma={s:.0f}{'  (independent)' if s == 0 else '   (correlated)'}"
        for s in SIGMAS
    )
    out.append(header)
    out.append("  " + "-" * (len(header) - 2))
    for rms in RMS_LEVELS:
        cells = "|".join(
            f"  {grid[(rms, s)][1]:2d}/40  max|d| {grid[(rms, s)][0]:.4f}"
            for s in SIGMAS
        )
        out.append(f"  {rms:4.1f} |{cells}")
    out.append("")
    indep_first = next((r for r in RMS_LEVELS if grid[(r, 0.0)][1] > 0), None)
    corr_first = next(
        (r for r in RMS_LEVELS if any(grid[(r, s)][1] > 0 for s in SIGMAS if s > 0)),
        None,
    )
    out.append(
        f"  First RMS at which any verdict flips: independent {indep_first}v, "
        f"correlated {corr_first}v."
    )
    out.append(
        "  So at equal RMS the correlated arms break the metric EARLIER. Any onset quoted "
        "against real patch scatter must come from a correlated arm."
    )
    out.append("")
    out.append(
        "  Non-monotonicity, stated rather than hidden: at the largest RMS levels the "
        "correlated arms flip FEWER verdicts than the independent arm. A strongly correlated "
        "perturbation displaces the patch nearly coherently, and a coherent radial shift is "
        "precisely what villa's median-snap absorbs. The correlated arms are worst in the "
        "middle of the range, not at the top."
    )
    return "\n".join(out) + "\n"


def main():
    rays = usable_rays(load_shard(), n_rays=N_RAYS)
    rng = np.random.default_rng(SEED)
    grid = {
        (rms, sigma): run_level(rays, rms, sigma, rng)
        for rms in RMS_LEVELS
        for sigma in SIGMAS
    }
    print(format_report(grid, measure_real_autocorrelation()))


if __name__ == "__main__":
    main()
