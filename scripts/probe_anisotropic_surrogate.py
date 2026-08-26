"""What actually moves the exceedance: correlation MAGNITUDE, not anisotropy.

This probe was written to test whether the anisotropy caveat every earlier probe
carried was load-bearing. Its first conclusion was that it was: fitting a
surrogate to both measured axis statistics raised the exceedance from 2.7% to
7.1%, a factor of 2.6, and the report said the caveat had been vindicated.

**That attribution was wrong, and review caught it.** The anisotropic arm uses
sigma_col 1.45 and sigma_row 1.05, both far above the published isotropic arm's
0.561. More smoothing on BOTH axes is more total correlation, and this
investigation had already established that more correlation lowers the onset. So
the comparison confounded the axis ratio with the correlation magnitude.

Holding effective sample size fixed and varying only the ratio separates them:

    A  isotropic 0.561 (as published)          exceedance ~2.8%
    B  isotropic 1.234 (ESS-matched control)   exceedance ~6.4%
    C  anisotropic 1.45 / 1.05                 exceedance ~6.7%

A to C is the 2.4x this probe originally claimed for anisotropy. A to B, which
changes only magnitude, is 2.3x of it. B to C, which changes only the ratio with
ESS held fixed, is 1.05x -- about one seed-sigma. Anisotropy accounts for roughly
six percent of the effect. Sweeping the ratio at fixed ESS is non-monotonic and
spans about 1.3 points across an 8x range, with the MOST anisotropic arm scoring
lower than isotropic. There is no anisotropy trend to find.

**The real finding, which is worth having.** The two arms were fitted to different
statistics, and nothing said so. The published surrogate fitted lag-1 on the RAW
field; this one fits lag-1 on the PLANE-FIT RESIDUAL of a window, which is how the
real target was measured. That difference, not the axis count, is what moved sigma
from 0.56 to about 1.45. Correcting the fitting criterion raises the exceedance
about 2.3x. The anisotropy rides along for the rest.

It also follows that the earlier claim "no isotropic surrogate reproduces the real
statistics at any sigma" is too strong: an isotropic field reaches the +0.357
column target under the residual criterion at sigma about 3.5. What no isotropic
field does is match BOTH statistics at once.

**A disclosed inconsistency this probe does not resolve.** The exceedance divides
real reported scatter by CAL_K, an attenuation fitted under the OLD isotropic
surrogate. Refitting it under this surrogate gives k about 0.257 rather than
0.602, which would put corrected real scatter near 3.2 voxels instead of 1.33 and
push the exceedance well above anything quoted here. So every exceedance below is
a hybrid of two incompatible surrogates and belongs to neither. Resolving that is
its own piece of work; it is flagged rather than papered over.

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
# Number of seeds. A single seed is not a basis for a ratio claim: per-seed ratios
# for the headline comparison span 1.9 to 3.3.
N_SEEDS = 8


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


def effective_sample_size(shape, sigma_col, sigma_row, seed=13, trials=600):
    """1 / Var(grid mean) of a unit-variance field: how many independent cells the
    field behaves like.

    This is the invariant that lets magnitude be held fixed while the anisotropy
    ratio varies. Without it, comparing sigma (0.561, 0.561) against (1.45, 1.05)
    changes both at once, which is exactly the confound this probe first fell into.
    """
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(trials):
        f = anisotropic_field(shape, 1.0, sigma_col, sigma_row, rng)
        means.append(float(f.mean()))
    v = float(np.var(means))
    return float("inf") if v <= 0 else 1.0 / v


def ess_matched_isotropic(shape, sigma_col, sigma_row):
    """The isotropic sigma whose ESS matches a given anisotropic pair.

    The magnitude-only control arm. If this arm reproduces most of the effect, the
    effect is magnitude, not anisotropy.
    """
    target = effective_sample_size(shape, sigma_col, sigma_row)
    lo, hi = 0.0, 4.0
    for _ in range(18):
        mid = 0.5 * (lo + hi)
        if effective_sample_size(shape, mid, mid) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


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


def arm_exceedance(rays, sigma_col, sigma_row, true_scatter, n_seeds=N_SEEDS):
    """Exceedance across seeds. A single seed is not enough for a ratio claim."""
    vals, flips = [], []
    for k in range(n_seeds):
        per_ray = onsets_under(rays, sigma_col, sigma_row, seed=SEED + 97 * k)
        vals.append(exceedance_from(per_ray, true_scatter))
        flips.append(sum(1 for o in per_ray if o is not None))
    return float(np.mean(vals)), float(np.std(vals)), float(np.mean(flips))


def format_report(fit, achieved, baseline, arms, ess, true_scatter):
    sigma_col, sigma_row, residual = fit
    ach_col, ach_row = achieved
    out = []
    out.append("What moves the exceedance: correlation magnitude, not anisotropy")
    out.append(
        "This probe originally concluded that fitting a surrogate to both measured axis "
        "statistics raised the exceedance 2.6x, and attributed that to anisotropy. Review "
        "showed the comparison confounded the axis RATIO with the correlation MAGNITUDE: the "
        "anisotropic arm smooths both axes far harder than the published isotropic one. Holding "
        "effective sample size fixed and varying only the ratio separates them."
    )
    out.append("")
    out.append(
        "=== The two statistics, and the pipeline artifact behind the negative one ==="
    )
    out.append(f"  real across-column lag-1 (axis 1): {TARGET_COL_LAG1:+.3f}")
    out.append(f"  real across-row    lag-1 (axis 0): {TARGET_ROW_LAG1:+.3f}")
    out.append(
        f"  the SAME pipeline on pure white noise:    column {baseline[0]:+.3f}, "
        f"row {baseline[1]:+.3f}"
    )
    out.append(
        "  A plane fit over three rows with three parameters induces negative row correlation on "
        "ANY field, so the real -0.076 indicates POSITIVE intrinsic row correlation partly "
        "cancelling that artifact, not anti-correlated data. Reasoning from the sign alone sent "
        "a first attempt after a high-pass filter, which converged to its boundary."
    )
    out.append("")
    out.append(
        f"  fitted sigma_col = {sigma_col:.3f}, sigma_row = {sigma_row:.3f} "
        f"(joint 2-D search, residual cost {residual:.3f})"
    )
    out.append(
        f"  achieved: across-column {ach_col:+.3f} (target {TARGET_COL_LAG1:+.3f}), "
        f"across-row {ach_row:+.3f} (target {TARGET_ROW_LAG1:+.3f})"
    )
    out.append("")

    out.append("=== Three arms, with a magnitude-only control ===")
    out.append(
        f"  Effective sample size on the {INJECTION_GRID[0]}x{INJECTION_GRID[1]} injection grid "
        "(1/Var of the grid mean; white noise would be the cell count):"
    )
    for label, sc, sr, e in ess:
        out.append(f"    {label:34} sigma ({sc:.3f}, {sr:.3f})   ESS {e:7.2f}")
    out.append("")
    out.append(
        f"  Exceedance, mean +- sd over {N_SEEDS} seeds, same rays and same real scatter:"
    )
    out.append("    arm                                 rays flipping   exceedance")
    out.append("    " + "-" * 58)
    for label, mean, sd, fl in arms:
        out.append(
            f"    {label:34} {fl:6.1f} of {N_RAYS}   {100 * mean:5.2f}% +- {100 * sd:.2f}"
        )
    out.append("")
    a, b, c = (m for _, m, _, _ in arms)
    out.append(f"  A to C (originally claimed for anisotropy): x{c / a:.2f}")
    out.append(f"  A to B (MAGNITUDE alone, ratio fixed at 1): x{b / a:.2f}")
    out.append(f"  B to C (ANISOTROPY alone, ESS fixed):       x{c / b:.2f}")
    share = np.log(c / b) / np.log(c / a) if c > b and c > a else 0.0
    out.append(
        f"  => anisotropy accounts for about {100 * share:.0f}% of the log-effect. The mover is "
        "total correlation."
    )
    out.append("")
    out.append(
        "  Why the magnitude changed at all: the two arms were fitted to DIFFERENT statistics. "
        "The published surrogate fitted lag-1 on the RAW field; this one fits lag-1 on the "
        "PLANE-FIT RESIDUAL, which is how the real target was measured. That, not the axis "
        "count, moved sigma from 0.56 to about 1.45. Correcting the fitting criterion is the "
        "real finding here."
    )
    out.append("")
    out.append("=== What this does NOT settle ===")
    out.append(
        f"  The exceedance divides real reported scatter by CAL_K = {CAL_K}, an attenuation "
        "fitted under the OLD isotropic surrogate. Refitting it under this one gives k near "
        "0.257, which would put corrected real scatter near 3.2 voxels rather than "
        f"{np.median(true_scatter):.2f} and push every exceedance above well past what is quoted. "
        "So these figures are a hybrid of two incompatible surrogates and belong to neither. "
        "Flagged rather than resolved."
    )
    out.append(
        "  Also unresolved: lag-1 on two axes is two numbers describing a 2-D field, and an "
        "isotropic field CAN reach the column target alone at sigma about 3.5 -- so the isotropic "
        "family does not bound this from below. These arms widen a bracket; none supersedes the "
        "others."
    )
    return "\n".join(out) + "\n"


def main():
    rays = usable_rays(load_shard(), n_rays=N_RAYS)
    sigma_col, sigma_row, residual = fit_surrogate(INJECTION_GRID)
    achieved = surrogate_lag1s(INJECTION_GRID, sigma_col, sigma_row, seed=31)
    baseline = white_noise_baseline(INJECTION_GRID)
    true_scatter = corrected_real_scatter()

    control = ess_matched_isotropic(INJECTION_GRID, sigma_col, sigma_row)
    ess = [
        (
            "A isotropic (published fit)",
            ISOTROPIC_SIGMA,
            ISOTROPIC_SIGMA,
            effective_sample_size(INJECTION_GRID, ISOTROPIC_SIGMA, ISOTROPIC_SIGMA),
        ),
        (
            "B isotropic (ESS-matched control)",
            control,
            control,
            effective_sample_size(INJECTION_GRID, control, control),
        ),
        (
            "C anisotropic (both axes fitted)",
            sigma_col,
            sigma_row,
            effective_sample_size(INJECTION_GRID, sigma_col, sigma_row),
        ),
    ]
    arms = [
        (label, *arm_exceedance(rays, sc, sr, true_scatter)) for label, sc, sr, _ in ess
    ]
    print(
        format_report(
            (sigma_col, sigma_row, residual),
            achieved,
            baseline,
            arms,
            ess,
            true_scatter,
        )
    )


if __name__ == "__main__":
    main()
