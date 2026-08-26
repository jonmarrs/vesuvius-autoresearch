"""Is the corrected real scatter physical? The loose end stays OPEN.

`reports/self_consistent_exceedance.txt` disclosed a loose end: the ~30 percent
exceedance rests on a corrected real-scatter distribution reaching p95 about 8
voxels and max about 20, against a measured inter-winding spacing of about 12.81.

An earlier version of this file claimed to CLOSE that. Review showed the closure
was invalid on both of its halves, and this file now reports the concern as open.

**Why half one failed: it compared across scales.** The corrected p95 is not an
independent quantity -- it IS the 3x4 plane-fit residual, inflated by dividing by
the attenuation. So it is a statement about deviation inside a 60x80 voxel window,
and the directly observed deviation at that same window is about 1.8 to 2.2. The
corrected value is roughly 4x larger than anything measured at its own scale. The
earlier version answered that by pointing at 12.05 measured over 180x240, a nine
times larger area, which is a different quantity.

Three things make that fatal rather than merely loose. The threshold is a free
parameter: with the largest window set to 7x9 instead of 9x12 the physicality
check FAILS. Half two refutes half one, because the 12.05 is exactly the
long-wavelength curvature that half two argues the spiral follows and which
therefore cannot perturb anything -- applying this file's own shared-removal to
its own evidence drops it below 8. And the only thing reconciling 1.9-observed
with 8-corrected at the same scale is the attenuation model itself, which a
large-window measurement does not test.

**Why half two failed: the statistic has no power.** Calibrated against fields of
KNOWN composition (see `statistic_power`), the local-fraction statistic saturates:
a field that is 95 percent shared curvature reports about 0.83, against the 0.84
observed on real data. The branch this file carried for "most of it is shared
curvature, so the exceedance is an overestimate" did not fail to fire -- it could
not fire. An observed 0.84 is consistent with almost any true composition.

What survives, and is worth keeping: the raw deviation-versus-window table below
is a clean, surrogate-free, attenuation-free measurement of what real sheets
actually do. It just does not license the conclusion that was drawn from it.

Also corrected here: every sample previously came from a single patch, because the
sampling loop broke out of the outer patch loop rather than the inner one. That
patch was the second-highest of eight for this statistic, and one of the eight
would have failed the physicality check outright. Sampling is now capped per patch.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_is_corrected_scatter_physical.py
"""

import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

from probe_real_patch_scatter import (  # noqa: E402
    load_patch,
    load_umbilicus,
    patch_dirs,
    radius_field,
)

# (rows, cols) in grid cells. One grid step is about 20 voxels.
SCALES = [(3, 4), (5, 6), (9, 12)]
ANALYSIS = (3, 4)
# The larger window whose fit defines "smooth enough that the spiral follows it".
SHARED_SCALE = (9, 12)
SAMPLES = 2000
SEED = 20260826
# Derived, not typed. An earlier version hardcoded 8.0 from the prose "around 8
# voxels" in another artifact; the computable value is 8.24. Four hand-typed
# cross-file statistics in this series have been wrong, all flatteringly.
CAL_FLOOR_REF = 0.2159
CAL_K_REF = 0.263
REPORTED_P95_REF = 2.179  # reports/real_patch_scatter.txt, 3x4 plane row


def corrected_p95():
    return float(np.sqrt(max(REPORTED_P95_REF**2 - CAL_FLOOR_REF**2, 0.0)) / CAL_K_REF)


def _design(h, w, order=1):
    ii, jj = np.mgrid[0:h, 0:w]
    cols = [ii.ravel(), jj.ravel(), np.ones(h * w)]
    if order == 2:
        cols = [ii.ravel() ** 2, jj.ravel() ** 2, (ii * jj).ravel()] + cols
    return np.c_[tuple(cols)]


def raw_deviation(h, w, rng, n=SAMPLES, per_patch=None):
    """Deviation from a plane inside a window, with NO correction applied.

    Surrogate-free and attenuation-free: this is what the geometry does, and it is
    the only check on the corrected figure that does not reuse the model being
    checked.
    """
    umb = load_umbilicus()
    A = _design(h, w)
    # Cap PER PATCH, not globally. An earlier version broke out of the outer patch
    # loop once the global count was reached, so every one of 600 samples came from
    # a single patch -- and that patch was the second-highest of eight for this
    # statistic. One of the eight would have failed the physicality test outright.
    per_patch = per_patch or max(1, n // max(1, len(patch_dirs())))
    rms = []
    for d in patch_dirs():
        xs, ys, zs, valid = load_patch(d)
        if not valid.any() or valid.shape[0] < h or valid.shape[1] < w:
            continue
        r = radius_field(xs, ys, zs, umb)
        for _ in range(4000):
            i = int(rng.integers(0, r.shape[0] - h + 1))
            j = int(rng.integers(0, r.shape[1] - w + 1))
            if not valid[i : i + h, j : j + w].all():
                continue
            win = r[i : i + h, j : j + w].ravel()
            c, *_ = np.linalg.lstsq(A, win, rcond=None)
            rms.append(float(np.sqrt(np.mean((win - A @ c) ** 2))))
            if len(rms) >= per_patch:
                break
    return np.array(rms)


def shared_vs_local(rng, n=SAMPLES, per_patch=None):
    """Split the analysis-window deviation into shared curvature and local wander.

    Inside a large window, fit a quadratic: that surface is smooth on the scale the
    fitted spiral also follows, so deviation FROM it is what genuinely displaces a
    patch relative to its winding. Deviation the large fit already accounts for is
    shared with the spiral and should not drive a verdict flip.

    Returns (total, local) rms at the analysis window, per sample.
    """
    umb = load_umbilicus()
    ah, aw = ANALYSIS
    sh, sw = SHARED_SCALE
    A_small = _design(ah, aw)
    A_big = _design(sh, sw, order=2)
    per_patch = per_patch or max(1, n // max(1, len(patch_dirs())))
    totals, locals_ = [], []
    for d in patch_dirs():
        xs, ys, zs, valid = load_patch(d)
        if not valid.any() or valid.shape[0] < sh or valid.shape[1] < sw:
            continue
        r = radius_field(xs, ys, zs, umb)
        for _ in range(4000):
            i = int(rng.integers(0, r.shape[0] - sh + 1))
            j = int(rng.integers(0, r.shape[1] - sw + 1))
            if not valid[i : i + sh, j : j + sw].all():
                continue
            big = r[i : i + sh, j : j + sw]
            cb, *_ = np.linalg.lstsq(A_big, big.ravel(), rcond=None)
            residual_big = (big.ravel() - A_big @ cb).reshape(sh, sw)
            # analysis-window sub-block, inside the same large window
            oi = int(rng.integers(0, sh - ah + 1))
            oj = int(rng.integers(0, sw - aw + 1))
            tot = big[oi : oi + ah, oj : oj + aw].ravel()
            loc = residual_big[oi : oi + ah, oj : oj + aw].ravel()
            ct, *_ = np.linalg.lstsq(A_small, tot, rcond=None)
            cl, *_ = np.linalg.lstsq(A_small, loc, rcond=None)
            totals.append(float(np.sqrt(np.mean((tot - A_small @ ct) ** 2))))
            locals_.append(float(np.sqrt(np.mean((loc - A_small @ cl) ** 2))))
            if len(totals) >= per_patch:
                break
    return np.array(totals), np.array(locals_)


def statistic_power(rng, fractions=(0.02, 0.05, 0.10, 0.20, 0.50), trials=300):
    """What does the local-fraction statistic report on fields of KNOWN composition?

    This is the check that was missing, and its absence is why an earlier version of
    this probe read 0.841 as "84 percent genuinely perturbs". Build a field that is
    a known mixture of long-wavelength shared curvature and short-wavelength local
    wander, run it through the same decomposition, and see what comes back. If the
    statistic saturates, an observed 0.841 is consistent with almost any true
    composition and carries no information about the one that matters.
    """
    from scipy.ndimage import gaussian_filter

    ah, aw = ANALYSIS
    sh, sw = SHARED_SCALE
    A_small = _design(ah, aw)
    A_big = _design(sh, sw, order=2)
    out = []
    for frac in fractions:
        reported = []
        for _ in range(trials):
            shared = gaussian_filter(rng.standard_normal((sh, sw)), 6.0, mode="nearest")
            local = gaussian_filter(rng.standard_normal((sh, sw)), 1.2, mode="nearest")
            shared = shared / max(shared.std(), 1e-12) * (1.0 - frac)
            local = local / max(local.std(), 1e-12) * frac
            big = shared + local
            cb, *_ = np.linalg.lstsq(A_big, big.ravel(), rcond=None)
            resid = (big.ravel() - A_big @ cb).reshape(sh, sw)
            oi = int(rng.integers(0, sh - ah + 1))
            oj = int(rng.integers(0, sw - aw + 1))
            tot = big[oi : oi + ah, oj : oj + aw].ravel()
            loc = resid[oi : oi + ah, oj : oj + aw].ravel()
            ct, *_ = np.linalg.lstsq(A_small, tot, rcond=None)
            cl, *_ = np.linalg.lstsq(A_small, loc, rcond=None)
            t = float(np.sqrt(np.mean((tot - A_small @ ct) ** 2)))
            l_ = float(np.sqrt(np.mean((loc - A_small @ cl) ** 2)))
            if t > 1e-12:
                reported.append(l_ / t)
        out.append((frac, float(np.median(reported)) if reported else float("nan")))
    return out


def format_report(scales, totals, locals_, power):
    out = []
    out.append("Is the corrected real scatter physical, and is it the right quantity?")
    out.append(
        "The exceedance rests on a corrected real-scatter distribution reaching p95 about "
        f"{corrected_p95():.0f} voxels against a winding spacing of about 12.81. This checks that "
        "figure without reusing the correction model, and then asks whether the quantity is the "
        "one the exceedance needs."
    )
    out.append("")
    out.append("=== The raw geometry, which is the part worth keeping ===")
    out.append(
        "  Deviation from a plane, no surrogate and no attenuation applied, pooled across patches."
    )
    out.append("   window    real extent (vox)     rms p50     p95      max        n")
    out.append("  " + "-" * 70)
    for (h, w), v in scales:
        out.append(
            f"  {h:2d}x{w:<3d} {h * 20:6d} x {w * 20:<6d} {np.median(v):10.3f} "
            f"{np.percentile(v, 95):8.3f} {v.max():8.2f} {len(v):8d}"
        )
    analysis = next(v for (h, w), v in scales if (h, w) == ANALYSIS)
    out.append("")
    out.append("=== The concern is NOT closed ===")
    out.append(
        f"  The corrected p95 under scrutiny is {corrected_p95():.2f} voxels. It is not an "
        "independent quantity: it IS the analysis-window plane-fit residual, divided by the "
        "attenuation. So it describes deviation inside a "
        f"{ANALYSIS[0] * 20}x{ANALYSIS[1] * 20} voxel window."
    )
    out.append(
        f"  Directly observed deviation at that SAME window: p95 {np.percentile(analysis, 95):.3f}."
    )
    out.append(
        f"  Gap: {corrected_p95() / max(np.percentile(analysis, 95), 1e-9):.1f}x, unexplained by "
        "anything measured here."
    )
    out.append(
        "  An earlier version answered this by pointing at the largest window's p95, over a nine "
        "times larger area. That is a different quantity, and the comparison is a category "
        "error. It is also unstable: with the largest window at 7x9 rather than 9x12 the same "
        "argument fails outright. The concern stands."
    )
    out.append("")
    out.append("=== And the shared-vs-local statistic has no power ===")
    frac = locals_ / np.maximum(totals, 1e-12)
    out.append(
        f"  Observed on real data: local as a fraction of total, p50 {np.median(frac):.3f}."
    )
    out.append(
        "  Calibrated against fields of KNOWN composition, the same statistic reports:"
    )
    out.append("     true local amplitude fraction | statistic reports")
    out.append("    " + "-" * 46)
    for f, rep in power:
        out.append(f"    {f:29.2f} | {rep:17.3f}")
    obs = float(np.median(frac))
    bracket = None
    for (f0, r0), (f1, r1) in zip(power, power[1:], strict=False):
        if r0 <= obs <= r1:
            bracket = (f0, f1)
            break
    out.append(
        "  It saturates, and steeply. Inverting the curve at the observed value puts the TRUE "
        + (
            f"local fraction between {bracket[0]:.2f} and {bracket[1]:.2f}"
            if bracket
            else "local fraction outside the calibrated range"
        )
        + " -- not at the observed number itself. Reading 0.81 as 'about 80 percent genuinely "
        "perturbs' inverts the answer: most of the deviation is shared curvature after all."
    )
    out.append(
        "  So the branch this probe carried for 'most of it is shared curvature, therefore the "
        "exceedance is an overestimate' did not fail to fire. It could not fire, and its silence "
        "was not evidence. On this calibration it should have fired."
    )
    out.append(
        f"  Note also that the split is not a partition: {100 * float((locals_ > totals).mean()):.1f} "
        "percent of samples have local exceeding total, which an orthogonal decomposition cannot "
        "do. 'X percent of the deviation' has no variance interpretation here."
    )
    out.append("")
    out.append(
        "  Both halves of the earlier closure are withdrawn. The exceedance still rests on a "
        "corrected distribution roughly 4x larger than anything observed at its own scale, and "
        "whether that is physical is unresolved. Resolving it needs the attenuation validated "
        "against a quantity measured at the analysis window, not at a larger one."
    )
    return "\n".join(out) + "\n"


def main():
    rng = np.random.default_rng(SEED)
    scales = [((h, w), raw_deviation(h, w, rng)) for h, w in SCALES]
    totals, locals_ = shared_vs_local(rng)
    power = statistic_power(rng)
    print(format_report(scales, totals, locals_, power))


if __name__ == "__main__":
    main()
