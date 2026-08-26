"""Close the last soft limit: an ANISOTROPIC scatter surrogate.

Every scatter surrogate in this investigation has been an isotropic Gaussian
field, and every probe that used one has carried the same caveat: the real
residual is anisotropic, so no isotropic surrogate reproduces it at any sigma,
and the results bracket rather than pin. Measured on real 3x4 plane-fit residual
windows, the two axes do not merely differ in magnitude, they differ in SIGN:

    across-column lag-1 (axis 1):  median +0.357
    across-row    lag-1 (axis 0):  median -0.076

An earlier version of this file reasoned that a Gaussian smooth only produces
POSITIVE lag-1, so the negative target needed a high-pass filter. That was wrong,
and the fit it produced failed loudly: it converged to the boundary at a=0 while
achieving -0.584 against a -0.076 target.

The reason is that the measurement pipeline itself induces negative row
correlation. The statistic is taken on the residual of a PLANE FIT over a 3x4
window: three rows, three fitted parameters. On pure white noise that pipeline
already returns row lag-1 of about -0.27, and with column smoothing about -0.55.
So the real -0.076 does not indicate anti-correlated data at all -- it indicates
data with POSITIVE intrinsic row correlation that partly cancels the fit's
artifact. Two Gaussian smooths, one per axis, are the right surrogate.

The two axes are also NOT separable through the plane fit: raising sigma_row from
0.5 to 1.0 moves the row statistic from -0.374 to +0.278 while crashing the column
statistic from +0.279 to -0.124. So the fit is a joint 2-D search, not two
independent bisections.

What this probe does with that: refit the surrogate to BOTH measured statistics,
re-run the onset and the exceedance under it, and compare against the isotropic
answer. If the exceedance moves materially, every earlier number that used an
isotropic surrogate is biased and the caveat was load-bearing. If it does not,
the caveat can finally be retired rather than repeated.

The honest prior is that it could go either way. The isotropic surrogate
over-correlates one axis and gets the other's sign wrong, and those two errors do
not obviously cancel.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_anisotropic_surrogate.py
"""

import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np  # noqa: E402
from scipy.ndimage import gaussian_filter1d  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

from probe_correlated_scatter import run_level  # noqa: E402
from probe_onset_at_matched_correlation import (  # noqa: E402
    CAL_FLOOR,
    CAL_K,
    INJECTION_GRID,
    RMS_LEVELS,
)
from probe_real_patch_scatter import (  # noqa: E402
    load_patch,
    load_umbilicus,
    patch_dirs,
    radius_field,
    window_residuals,
)
from probe_spiral_satisfaction_empirical_transform import (  # noqa: E402
    load_shard,
    usable_rays,
)

# The two statistics the surrogate must reproduce, measured on real 3x4 plane-fit
# residual windows. The analysis window, not the injection grid: these are
# properties of the real data, and the fit below targets them on the same shape.
TARGET_COL_LAG1 = 0.357
TARGET_ROW_LAG1 = -0.076
ANALYSIS_WINDOW = (3, 4)

N_RAYS = 40
SEED = 20260826
# The isotropic sigma the onset probe published, applied to both axes.
ISOTROPIC_SIGMA = 0.561


def anisotropic_field(shape, rms, sigma_col, sigma_row, rng):
    """A field with independently smoothed axes.

    Both parameters are Gaussian smooths. The measured row statistic is negative
    only because the plane fit that measures it induces that on any field; what
    distinguishes the real data is POSITIVE intrinsic row correlation, which is
    what `sigma_row` supplies. Rescaled to exactly `rms` after filtering so shape
    and magnitude stay separable.
    """
    f = rng.standard_normal(shape)
    if sigma_col > 0:
        f = gaussian_filter1d(f, sigma_col, axis=1, mode="nearest")
    if sigma_row > 0:
        f = gaussian_filter1d(f, sigma_row, axis=0, mode="nearest")
    sd = float(f.std())
    return f / sd * rms if sd > 0 else f


def white_noise_baseline(shape, seed=11):
    """What the measurement pipeline returns on a field with NO correlation.

    This is the number that makes the negative row target intelligible, and its
    absence is what sent the first version of this probe after a high-pass filter.
    """
    return surrogate_lag1s(shape, 0.0, 0.0, seed=seed)


def measure_lag1(field, axis):
    a = np.moveaxis(field, axis, -1)
    if a.shape[-1] < 2:
        return float("nan")
    return float(np.corrcoef(a[..., :-1].ravel(), a[..., 1:].ravel())[0, 1])


def surrogate_lag1s(shape, sigma_col, a_row, seed=7, trials=400):
    """Both lag-1 statistics of the surrogate, measured the way the real ones were:
    on the residual of a plane fit over the analysis window."""
    rng = np.random.default_rng(seed)
    h, w = ANALYSIS_WINDOW
    ii, jj = np.mgrid[0:h, 0:w]
    A = np.c_[ii.ravel(), jj.ravel(), np.ones(h * w)]
    cols, rows = [], []
    for _ in range(trials):
        f = anisotropic_field(shape, 1.0, sigma_col, a_row, rng)
        win = f[:h, :w].ravel()
        c, *_ = np.linalg.lstsq(A, win, rcond=None)
        res = (win - A @ c).reshape(h, w)
        if res.std() < 1e-9:
            continue
        cols.append(measure_lag1(res, 1))
        rows.append(measure_lag1(res, 0))
    return float(np.median(cols)), float(np.median(rows))


def fit_surrogate(shape, seed=7):
    """Joint 2-D fit of (sigma_col, sigma_row) to both measured targets.

    A joint search rather than two bisections, because the axes interact strongly
    through the plane fit: raising sigma_row moves the row statistic up AND drags
    the column statistic down. Coarse grid, then a local refinement around the
    best cell. The residual cost is reported by the caller rather than hidden, so
    a target that turned out to be unreachable would be visible as a large one.
    """

    def cost(sc, sr):
        c, r = surrogate_lag1s(shape, sc, sr, seed=seed, trials=300)
        return abs(c - TARGET_COL_LAG1) + abs(r - TARGET_ROW_LAG1)

    # Seeded with the (0, 0) corner rather than None so the type is a real tuple
    # from the start; mypy correctly objected to unpacking an Optional.
    best: tuple[float, float, float] = (cost(0.0, 0.0), 0.0, 0.0)
    for sc in np.arange(0.0, 2.51, 0.25):
        for sr in np.arange(0.0, 1.51, 0.15):
            k = cost(float(sc), float(sr))
            if k < best[0]:
                best = (k, float(sc), float(sr))
    _, sc0, sr0 = best
    for step in (0.10, 0.05):
        for sc in (sc0 - step, sc0, sc0 + step):
            for sr in (sr0 - step, sr0, sr0 + step):
                if sc < 0 or sr < 0:
                    continue
                k = cost(sc, sr)
                if k < best[0]:
                    best = (k, float(sc), float(sr))
        _, sc0, sr0 = best
    return best[1], best[2], best[0]


def _patched_run_level(rays, rms, sigma_col, sigma_row, rng):
    """run_level with the anisotropic field substituted for the isotropic one.

    `probe_correlated_scatter.run_level` builds its own field internally, so the
    generator is swapped in place rather than reimplementing the scoring path --
    every number still comes from villa's unmodified metric via that function.
    """
    import probe_correlated_scatter as pcs

    original = pcs.noise_field
    pcs.noise_field = lambda shape, rms_, _sigma, rng_: anisotropic_field(
        shape, rms_, sigma_col, sigma_row, rng_
    )
    try:
        return run_level(rays, rms, 1.0, rng)
    finally:
        pcs.noise_field = original


def onsets_under(rays, sigma_col, sigma_row, seed=SEED):
    per_ray = []
    for i, ray in enumerate(rays):
        hit = None
        for rms in RMS_LEVELS:
            _, f1 = _patched_run_level(
                [ray], rms, sigma_col, sigma_row, np.random.default_rng(seed + 1000 * i)
            )
            if f1:
                hit = rms
                break
        per_ray.append(hit)
    return per_ray


def corrected_real_scatter(seed=SEED):
    umb = load_umbilicus()
    rng = np.random.default_rng(seed)
    chunks = []
    for d in patch_dirs():
        xs, ys, zs, valid = load_patch(d)
        if not valid.any() or valid.shape[0] < 3 or valid.shape[1] < 4:
            continue
        r = radius_field(xs, ys, zs, umb)
        res = window_residuals(r, valid, 3, 4, 1, rng, n_samples=400)
        if res.size:
            chunks.append(res)
    rep = np.concatenate(chunks)
    return np.sqrt(np.maximum(rep**2 - CAL_FLOOR**2, 0.0)) / CAL_K


def exceedance_from(per_ray, true_scatter):
    per_ray_p = [
        float((true_scatter >= o).mean()) if o is not None else 0.0 for o in per_ray
    ]
    return float(np.mean(per_ray_p))


def format_report(
    fit, achieved, baseline, iso_onsets, ani_onsets, iso_p, ani_p, true_scatter
):
    sigma_col, sigma_row, residual = fit
    ach_col, ach_row = achieved
    out = []
    out.append("An anisotropic scatter surrogate, and whether the anisotropy mattered")
    out.append(
        "Every earlier probe used an isotropic Gaussian surrogate and carried the caveat that "
        "the real residual is anisotropic, so no isotropic field reproduces it and the results "
        "bracket rather than pin. That caveat is now testable."
    )
    out.append("")
    out.append("=== The two statistics, and why one was unreachable ===")
    out.append(f"  real across-column lag-1 (axis 1): {TARGET_COL_LAG1:+.3f}")
    out.append(f"  real across-row    lag-1 (axis 0): {TARGET_ROW_LAG1:+.3f}")
    out.append(
        f"  the SAME pipeline on pure white noise returns: column {baseline[0]:+.3f}, "
        f"row {baseline[1]:+.3f}"
    )
    out.append(
        "  That last line is the one that matters and the one an earlier version of this probe "
        "lacked. A plane fit over three rows with three parameters induces negative row "
        "correlation on ANY field, so the real -0.076 does not indicate anti-correlated data; it "
        "indicates positive intrinsic row correlation partly cancelling the fit's own artifact. "
        "Reasoning from the sign alone sent the first attempt after a high-pass filter, which "
        "converged to its boundary and missed the target by half."
    )
    out.append("")
    out.append(
        f"  fitted sigma_col = {sigma_col:.3f}, sigma_row = {sigma_row:.3f} "
        f"(joint 2-D search; residual cost {residual:.3f})"
    )
    out.append(
        f"  achieved: across-column {ach_col:+.3f} (target {TARGET_COL_LAG1:+.3f}), "
        f"across-row {ach_row:+.3f} (target {TARGET_ROW_LAG1:+.3f})"
    )
    out.append("")

    out.append("=== Does it change the answer? ===")
    for label, per_ray, p in (
        ("isotropic (as published)", iso_onsets, iso_p),
        ("anisotropic (this probe)", ani_onsets, ani_p),
    ):
        hits = [o for o in per_ray if o is not None]
        med = f"{np.median(hits):.2f}v" if hits else "-"
        out.append(
            f"  {label:26} rays flipping {len(hits):2d} of {len(per_ray)}, "
            f"median among flippers {med:>6}, exceedance {100 * p:.1f}%"
        )
    out.append("")
    delta = abs(ani_p - iso_p)
    out.append(
        f"  exceedance moves by {100 * delta:.1f} percentage points when the surrogate is "
        "corrected from isotropic to anisotropic."
    )
    if delta < 0.02:
        out.append(
            "  That is small. The anisotropy caveat that every earlier probe carried can be "
            "retired: getting the second axis right, including its sign, does not materially "
            "change the conclusion. The bracket was wider than it needed to be."
        )
    else:
        out.append(
            "  That is NOT small. Every earlier number produced with an isotropic surrogate is "
            "biased by roughly this much, and the anisotropy caveat was load-bearing rather "
            "than precautionary. The anisotropic figure supersedes them."
        )
    out.append("")
    out.append(
        f"  Real corrected scatter used for both: median {np.median(true_scatter):.3f}v, "
        f"p95 {np.percentile(true_scatter, 95):.3f}v, n={true_scatter.size}."
    )
    out.append(
        "  Remaining limit: lag-1 on two axes is still only two numbers describing a 2-D field. "
        "Matching them does not guarantee matching the full correlation structure, and this "
        "probe does not claim it does."
    )
    return "\n".join(out) + "\n"


def main():
    rays = usable_rays(load_shard(), n_rays=N_RAYS)
    sigma_col, sigma_row, residual = fit_surrogate(INJECTION_GRID)
    achieved = surrogate_lag1s(INJECTION_GRID, sigma_col, sigma_row)
    baseline = white_noise_baseline(INJECTION_GRID)
    true_scatter = corrected_real_scatter()

    # The published isotropic arm smooths BOTH axes equally (scipy's gaussian_filter
    # is isotropic), so it is reproduced here as sigma_col == sigma_row. An earlier
    # draft of this comparison passed sigma_row=0, which smooths only one axis and
    # is not the published configuration -- it would have been a strawman, and would
    # have exaggerated the effect this probe is measuring.
    iso = onsets_under(rays, ISOTROPIC_SIGMA, ISOTROPIC_SIGMA)
    ani = onsets_under(rays, sigma_col, sigma_row)
    print(
        format_report(
            (sigma_col, sigma_row, residual),
            achieved,
            baseline,
            iso,
            ani,
            exceedance_from(iso, true_scatter),
            exceedance_from(ani, true_scatter),
            true_scatter,
        )
    )


if __name__ == "__main__":
    main()
