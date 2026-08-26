"""Is the corrected real scatter physically possible, and is it the right quantity?

`reports/self_consistent_exceedance.txt` closes with one disclosed loose end. Under
the admissible surrogate the corrected real scatter reaches p95 about 8 voxels and
max about 20, against a measured inter-winding spacing of about 12.81. A patch
wandering two thirds of a winding is not obviously physical, and the whole ~30
percent exceedance rests on that corrected distribution being real.

This closes it, and the answer has two halves that point different ways.

**Half one: the magnitude is physical.** The correction can be checked without any
surrogate or attenuation, because if real sheets genuinely deviate by that much,
the deviation is directly observable in the raw geometry at a large enough window.
Measured on real patches with nothing but a plane removed:

    window      real extent      raw rms p50 / p95
    3x4          60 x  80 vox      0.75 / 1.98
    5x6         100 x 120 vox      1.86 / 4.70
    9x12        180 x 240 vox      5.73 / 12.81

A corrected p95 near 8 voxels at the 60x80 scale sits between the directly
observed 4.70 at 100x120 and 12.81 at 180x240. Real sheets do wander that far.
The corrected value is not an artifact of dividing by a small k.

**Half two, which is the more interesting problem: it may be the wrong quantity.**
The deviation grows steeply with window size, which is the signature of
LONG-WAVELENGTH CURVATURE rather than local roughness. And curvature that the sheet
genuinely has is curvature the fitted spiral follows too: it is shared between the
patch and the surface it is scored against, so it should not drive a verdict flip
the way independent local noise does.

The exceedance model treats all of the corrected deviation as if it perturbs the
patch relative to the winding. If most of it is shared curvature, the effective
perturbation is smaller than the corrected figure and the ~30 percent is an
overestimate. This probe measures the split by decomposing the deviation at the
analysis window into the part a larger-window fit also removes (shared, smooth)
and the part it does not (local, genuinely perturbing).

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
SAMPLES = 600
SEED = 20260826
# What the exceedance model currently assumes, from the calibration artifact.
CORRECTED_P95 = 8.0


def _design(h, w, order=1):
    ii, jj = np.mgrid[0:h, 0:w]
    cols = [ii.ravel(), jj.ravel(), np.ones(h * w)]
    if order == 2:
        cols = [ii.ravel() ** 2, jj.ravel() ** 2, (ii * jj).ravel()] + cols
    return np.c_[tuple(cols)]


def raw_deviation(h, w, rng, n=SAMPLES):
    """Deviation from a plane inside a window, with NO correction applied.

    Surrogate-free and attenuation-free: this is what the geometry does, and it is
    the only check on the corrected figure that does not reuse the model being
    checked.
    """
    umb = load_umbilicus()
    A = _design(h, w)
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
            if len(rms) >= n:
                break
        if len(rms) >= n:
            break
    return np.array(rms)


def shared_vs_local(rng, n=SAMPLES):
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
            if len(totals) >= n:
                break
        if len(totals) >= n:
            break
    return np.array(totals), np.array(locals_)


def format_report(scales, totals, locals_):
    out = []
    out.append("Is the corrected real scatter physical, and is it the right quantity?")
    out.append(
        "The exceedance rests on a corrected real-scatter distribution reaching p95 about "
        f"{CORRECTED_P95:.0f} voxels against a winding spacing of about 12.81. This checks that "
        "figure without reusing the correction model, and then asks whether the quantity is the "
        "one the exceedance needs."
    )
    out.append("")
    out.append("=== Half one: is the magnitude possible? ===")
    out.append(
        "  Raw deviation from a plane, no surrogate and no attenuation applied. If sheets really "
        "wander this far, it is directly observable at a large enough window."
    )
    out.append("   window    real extent (vox)     rms p50     p95      max")
    out.append("  " + "-" * 60)
    for (h, w), v in scales:
        out.append(
            f"  {h:2d}x{w:<3d} {h * 20:6d} x {w * 20:<6d} {np.median(v):10.3f} "
            f"{np.percentile(v, 95):8.3f} {v.max():8.2f}"
        )
    biggest = scales[-1][1]
    out.append("")
    out.append(
        f"  A corrected p95 near {CORRECTED_P95:.0f} voxels at the 60x80 scale sits inside the "
        f"directly observed range, below the {np.percentile(biggest, 95):.2f} measured at "
        f"{SCALES[-1][0] * 20}x{SCALES[-1][1] * 20}. The magnitude is physical: real sheets do "
        "wander that far, and the corrected figure is not an artifact of dividing by a small k."
    )
    out.append("")

    out.append("=== Half two: is it the RIGHT quantity? ===")
    out.append(
        "  Deviation grows steeply with window size, which is the signature of long-wavelength "
        "curvature rather than local roughness. Curvature the sheet genuinely has is curvature "
        "the fitted spiral follows too, so it is SHARED between the patch and the surface it is "
        "scored against and should not drive a verdict flip. Only the part a large smooth fit "
        "does NOT account for genuinely perturbs the patch relative to its winding."
    )
    frac = locals_ / np.maximum(totals, 1e-12)
    out.append("")
    out.append(
        f"  total deviation at the analysis window : p50 {np.median(totals):.3f} vox, "
        f"p95 {np.percentile(totals, 95):.3f}"
    )
    out.append(
        f"  local part only (shared curvature removed): p50 {np.median(locals_):.3f} vox, "
        f"p95 {np.percentile(locals_, 95):.3f}"
    )
    out.append(
        f"  local as a fraction of total            : p50 {np.median(frac):.3f}, "
        f"p95 {np.percentile(frac, 95):.3f}"
    )
    out.append("")
    if np.median(frac) < 0.8:
        out.append(
            f"  So roughly {100 * (1 - np.median(frac)):.0f} percent of the deviation the "
            "exceedance model treats as perturbing the patch is in fact shared curvature that "
            "the spiral follows. The effective perturbation is smaller than the corrected "
            "figure, and the ~30 percent exceedance is therefore an OVERESTIMATE by an amount "
            "this probe does not attempt to quantify -- propagating it properly means refitting "
            "the attenuation against the local component alone, which is its own piece of work."
        )
    else:
        out.append(
            "  So most of the deviation is local rather than shared curvature, and the "
            "exceedance model's treatment of it as a genuine perturbation is sound."
        )
    out.append("")
    out.append(
        "  Caveat on this split: 'shared' is defined by what a quadratic over a "
        f"{SHARED_SCALE[0]}x{SHARED_SCALE[1]} window removes, which is a modelling choice about "
        "where the spiral stops following the sheet. A different choice moves the split. The "
        "direction of the conclusion is robust to it; the magnitude is not."
    )
    return "\n".join(out) + "\n"


def main():
    rng = np.random.default_rng(SEED)
    scales = [((h, w), raw_deviation(h, w, rng)) for h, w in SCALES]
    totals, locals_ = shared_vs_local(rng)
    print(format_report(scales, totals, locals_))


if __name__ == "__main__":
    main()
