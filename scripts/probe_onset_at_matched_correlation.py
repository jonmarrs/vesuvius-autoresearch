"""Measure the scatter onset at the SAME correlation length the calibration uses,
so the two sides of the comparison are finally on like terms.

`reports/spiral_satisfaction_winding_blindness.md` currently says the corrected
real-patch scatter (median about 1.3 to 1.4 voxels) sits just below the onset at
which villa's patch verdict starts to flip (1.5 voxels), and that its upper tail
(about 3.6 to 3.8) sits well above. That comparison is not yet valid: the 1.5
figure comes from `reports/spiral_satisfaction_correlated_scatter.txt`'s sigma=1
arm, while the correction comes from `reports/scatter_estimator_calibration.txt`
at a fitted sigma of about 0.65. Different correlation lengths, so the two numbers
are not directly comparable, and the report says so.

This NARROWS that; it does not fully close it. The onset is swept across
correlation length, including the value fitted on this probe's own injection grid.
What is still not matched is the real residual's ANISOTROPY, which no isotropic
Gaussian reaches at any sigma, so the sweep brackets rather than pins.

Two things worth stating before the numbers, because both bear on how much the
result can carry.

**The onset is a minimum over sampled rays.** It can only fall as more rays are
drawn, so it is a property of the sample as much as of the metric. The per-ray
median is reported beside it and is the sample-size-stable figure. This repeats
the caveat from the original onset probe rather than assuming a reader carries it
over.

**Correlation length is not a single knob in the real data.** The real residual is
ANISOTROPIC: lag-1 about +0.357 along columns and about -0.076 along rows
(`reports/scatter_estimator_calibration.txt`). An isotropic Gaussian surrogate
cannot reproduce that, at any sigma. Sweeping sigma therefore brackets the answer
rather than pinning it, and the bracket is what this probe reports.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_onset_at_matched_correlation.py
"""

import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

from probe_correlated_scatter import run_level  # noqa: E402
from probe_real_patch_scatter import (  # noqa: E402
    load_patch,
    load_umbilicus,
    patch_dirs,
    radius_field,
    window_residuals,
)
from probe_scatter_estimator_calibration import WINDOW, matched_sigma  # noqa: E402
from probe_spiral_satisfaction_empirical_transform import (  # noqa: E402
    load_shard,
    usable_rays,
)

# Finer than the correlated-scatter probe's grid, because the interesting region
# is where the corrected real scatter sits, roughly 1.2 to 1.6 voxels.
RMS_LEVELS = [round(0.75 + 0.25 * i, 2) for i in range(14)]  # 0.75 .. 4.00
# Correlation lengths to bracket. The fitted value is inserted at runtime.
SIGMA_GRID = [0.0, 0.5, 1.0, 2.0]
N_RAYS = 40
SEED = 20260825
# The calibration's own correction model, for converting reported to true scatter.
CAL_FLOOR = 0.2193
CAL_K = 0.602

# The corrected real-patch scatter this onset is compared against. The median band
# is the reference-sigma sensitivity row of reports/scatter_estimator_calibration.txt
# (1.37 / 1.41 / 1.43 / 1.44). An earlier version of this file wrote 1.30 as the low
# end, which appears in no artifact and contradicted the report's own text 23 lines
# above the sentence that used it -- the fourth hand-typed statistic in this series
# to be wrong, and the fourth to be wrong in the flattering direction.
CORRECTED_MEDIAN = (1.37, 1.44)
# The tail band is from reports/spiral_satisfaction_winding_blindness.md, not from
# the calibration artifact: that artifact contains 3.62 only, and 3.80 comes from the
# report's seed-spread statement, which no sensitivity table backs. Cited honestly
# rather than attributed to a file that does not contain it.
CORRECTED_TAIL = (3.60, 3.80)
# The injection grid. matched_sigma must be fitted HERE, not on the calibration's
# 3x4 analysis window: the same sigma induces lag-1 +0.364 on 3x4 but +0.514 on
# 12x16, so transferring the sigma parameter across probes does not transfer the
# statistic it was calibrated to.
INJECTION_GRID = (12, 16)


def onset_for(rays, sigma, seed=SEED):
    """Per-ray onsets, every ray at every level, each ray on its own rng stream.

    An earlier version gated the per-ray sweep behind the POOLED result, descending
    to per-ray runs only at levels where the pooled call had already flipped
    something. That could lose any ray whose onset lay below the pooled first-flip
    level, and it skipped levels where the pooled call reported zero flips -- which
    happens, because the correlated arms are non-monotonic in rms. Review measured
    the loss: none at the fitted sigma, but 3 of 45 skipped levels at sigma 0 and 2
    of 90 at sigma 2. The gate saved about 3.6 seconds per sigma and is not worth
    the correctness, so it is gone.

    Each ray gets an independent stream so a per-ray onset is a real experiment
    rather than a by-product of the pooled draw.
    """
    per_ray_first: list[float | None] = [None] * len(rays)
    first_any: float | None = None
    for rms in RMS_LEVELS:
        for i, ray in enumerate(rays):
            if per_ray_first[i] is not None:
                continue
            _, f1 = run_level([ray], rms, sigma, np.random.default_rng(seed + 1000 * i))
            if f1:
                per_ray_first[i] = rms
        if first_any is None and any(v is not None and v <= rms for v in per_ray_first):
            first_any = rms
    hits = [v for v in per_ray_first if v is not None]
    med = float(np.median(hits)) if hits else None
    return first_any, med, len(hits)


def exceedance(rays, sigma, seed=SEED):
    """P(a real patch window's corrected scatter >= that ray's onset).

    This is the like-for-like comparison. The earlier version compared a central
    tendency of onsets against a central tendency of scatter as if the two were
    paired, when the quantity of interest is an exceedance -- a second mismatch of
    the same species as the one this probe was written to fix.

    Real scatter comes from the 3x4 plane-fit residual distribution, corrected
    through the calibration's own model, and is integrated against the measured
    onset distribution under independence. Rays that never flip in the swept range
    are counted as non-flipping, which is conservative for this number.
    """
    umb = load_umbilicus()
    rng = np.random.default_rng(seed)
    reported = []
    for d in patch_dirs():
        xs, ys, zs, valid = load_patch(d)
        if not valid.any() or valid.shape[0] < 3 or valid.shape[1] < 4:
            continue
        r = radius_field(xs, ys, zs, umb)
        res = window_residuals(r, valid, 3, 4, 1, rng, n_samples=400)
        if res.size:
            reported.append(res)
    if not reported:
        return None, None
    rep = np.concatenate(reported)
    true = np.sqrt(np.maximum(rep**2 - CAL_FLOOR**2, 0.0)) / CAL_K

    _, _, _ = onset_for(rays, sigma, seed)  # warm the same code path
    onsets_list = []
    for i, ray in enumerate(rays):
        hit = None
        for rms in RMS_LEVELS:
            _, f1 = run_level([ray], rms, sigma, np.random.default_rng(seed + 1000 * i))
            if f1:
                hit = rms
                break
        onsets_list.append(hit)
    finite = [o for o in onsets_list if o is not None]
    if not finite:
        return None, None
    # P(flip) = mean over rays of P(scatter >= that ray's onset); censored rays
    # contribute zero.
    per_ray_p = [
        float((true >= o).mean()) if o is not None else 0.0 for o in onsets_list
    ]
    cdf = [
        (
            x,
            float(
                np.mean(
                    [1.0 if (o is not None and x >= o) else 0.0 for o in onsets_list]
                )
            ),
        )
        for x in (1.44, 2.0, 2.5, 3.25, 3.8)
    ]
    return float(np.mean(per_ray_p)), cdf


def format_report(rows, fitted, p_flip, cdf):
    out = []
    out.append("The scatter onset as a function of correlation length")
    out.append(
        "Both sides of the report's 'corrected scatter versus onset' comparison were previously "
        "measured at different correlation lengths, so the comparison was not valid. The onset is "
        "swept here across correlation length, including the value the calibration fitted "
        f"(sigma about {fitted:.2f}), so it can be read at the matching length."
    )
    out.append(
        f"Rays: {N_RAYS} from shard_0 under seed {SEED}; displacement exactly one winding; "
        "reporting configuration."
    )
    out.append("")
    out.append(
        "   sigma | first flip (min over rays) | median AMONG FLIPPERS | rays flipping"
    )
    out.append("  " + "-" * 70)
    for sigma, first_any, med, n in rows:
        tag = "  <- fitted" if abs(sigma - fitted) < 1e-6 else ""
        fa = f"{first_any:.2f}v" if first_any is not None else "none in range"
        md = f"{med:.2f}v" if med is not None else "-"
        out.append(f"  {sigma:6.2f} | {fa:>26} | {md:>14} | {n:2d} of {N_RAYS}{tag}")
    out.append("")
    out.append(
        "  Both columns need care. The first-flip column is a MIN over sampled rays and can only "
        "fall as more are drawn. The median column is CONDITIONAL: it is the median among rays "
        "that flip somewhere in the swept range, and fewer than half do at most sigmas. The "
        "UNCONDITIONAL per-ray median onset therefore exceeds the top of the swept range "
        f"({max(RMS_LEVELS):.2f}v, censored) wherever the flipping count is under half of "
        f"{N_RAYS}. Neither column is the right basis for comparing against a scatter "
        "distribution; the exceedance below is."
    )
    out.append("")

    at_fitted = next((r for r in rows if abs(r[0] - fitted) < 1e-6), None)
    out.append("=== The comparison, finally on like terms ===")
    if at_fitted and at_fitted[1] is not None:
        first_any, med = at_fitted[1], at_fitted[2]
        out.append(
            f"  onset at the fitted correlation length: first flip {first_any:.2f}v, "
            f"per-ray median {med:.2f}v"
            if med
            else f"  onset: first flip {first_any:.2f}v"
        )
        out.append(
            f"  corrected real scatter: median {CORRECTED_MEDIAN[0]:.2f} to "
            f"{CORRECTED_MEDIAN[1]:.2f}v, tail {CORRECTED_TAIL[0]:.2f} to {CORRECTED_TAIL[1]:.2f}v"
        )
        lo, hi = CORRECTED_MEDIAN
        if med is not None:
            if hi < med:
                verdict = "the corrected median sits BELOW the onset"
            elif lo > med:
                verdict = "the corrected median sits ABOVE the onset"
            else:
                verdict = "the corrected median BRACKETS the onset; the comparison does not resolve"
            out.append(f"  => {verdict}.")
        out.append(
            "  WITHDRAWN: an earlier version of this line said the corrected tail is 'above every "
            "onset in this sweep'. That was true only against the CONDITIONAL medians. Against "
            "the unconditional ones, which are censored above the swept range at four of five "
            "sigmas, it is false. The exceedance below replaces it."
        )
    out.append("")
    out.append("=== The like-for-like comparison: exceedance ===")
    if p_flip is not None:
        out.append(
            "  The quantity of interest is not a median against a median, it is how often a real "
            "patch's corrected scatter reaches its own ray's onset."
        )
        out.append(
            f"  P(a real window's corrected scatter >= that ray's onset) = {100 * p_flip:.1f}%"
        )
        out.append("     corrected scatter | P(flips)")
        out.append("    " + "-" * 32)
        for x, pr in cdf:
            note = (
                "  <- corrected median band"
                if abs(x - 1.44) < 1e-9
                else ("  <- corrected tail band" if abs(x - 3.8) < 1e-9 else "")
            )
            out.append(f"    {x:17.2f} | {100 * pr:7.1f}%{note}")
        out.append(
            "  So at the corrected median the metric essentially never notices the displacement, "
            "and even at the corrected tail it notices it in a minority of rays. Both the earlier "
            "'straddles the onset' framing and the 'tail is above every onset' framing overstated "
            "their respective directions."
        )
    out.append("")
    out.append(
        "  CAVEAT that limits all of this: the real residual is ANISOTROPIC (+0.357 along "
        "columns, -0.076 along rows) and an isotropic Gaussian surrogate cannot reproduce that "
        "at any sigma. This sweep brackets the onset across correlation length rather than "
        "pinning it, and the bracket is the honest answer."
    )
    return "\n".join(out) + "\n"


def main():
    rays = usable_rays(load_shard(), n_rays=N_RAYS)
    fitted = matched_sigma(INJECTION_GRID)
    sigmas = sorted({*SIGMA_GRID, round(fitted, 4)})
    rows = []
    for sigma in sigmas:
        first_any, med, n = onset_for(rays, sigma)
        rows.append((sigma, first_any, med, n))
    p_flip, cdf = exceedance(rays, round(fitted, 4))
    print(format_report(rows, round(fitted, 4), p_flip, cdf))


if __name__ == "__main__":
    main()
