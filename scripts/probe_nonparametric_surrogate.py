"""Does k survive replacing the Gaussian surrogate with the real residual field?

PRE-REGISTERED. Committed before the run, decision rule included.

WHY. Everything the ~30 percent exceedance rests on passes through an
attenuation k fitted by injection recovery, and every injection so far has been
a Gaussian field with smoothing parameters chosen to match a statistic of the
real residual. `reports/cross_estimator_consistency.txt` gave that k independent
support, but its own stated limit is that both estimators share the same
surrogate FAMILY: a field wrong in a way that biases both fits together would
produce agreement and still be wrong.

This removes the family. Instead of generating a field, it injects the real
residual itself -- what is left of a real patch's radius field after the same
heavy smoothing that builds the curvature-only reference. That carries the real
anisotropy, the real correlation lengths at every scale below the smoothing
scale, and whatever non-Gaussianity the data has, none of it fitted to anything.

CIRCULARITY, and how it is avoided. Injecting a patch's own residual into its
own reference would be close to reconstructing the patch, and the estimator
would then be measuring something it had already seen. Every injection here is
CROSS-PATCH: patch A's residual is injected into patch B's reference, A != B,
and the pairing is fixed by index so it cannot be reshuffled after seeing a
result. Shapes differ between patches, so the donor residual is tiled and
cropped to the recipient's grid; that tiling is a seam artifact and is
disclosed rather than hidden, since it can only ADD high-frequency content,
which would bias k UPWARD (less apparent attenuation), i.e. against the
conclusion this probe would otherwise support.

DECISION RULE, fixed in advance. For the plane estimator, let k_np be the
attenuation refit under the non-parametric injection and k_par the published
anisotropic value (0.265):

  * If k_np is within 25 percent of k_par (0.199 to 0.331), the Gaussian
    surrogate is an adequate stand-in for the real field as far as this
    correction is concerned, and the ~30 percent figure keeps its support.
  * If k_np is outside that interval by more than the seed spread, the
    surrogate family IS driving the correction, and every exceedance computed
    through k inherits that dependence. The direction matters and is reported
    either way: k_np > k_par means the true correction is SMALLER and ~30
    percent is an overestimate; k_np < k_par means it is larger and ~30 percent
    is an underestimate.
  * Outside the interval by less than the seed spread: inconclusive, reported
    as such.

The cross-estimator ratio R is recomputed under this injection as a secondary
output with the same [0.80, 1.25] band, because a surrogate that changes k
should be asked the consistency question too.

WHAT THIS CANNOT DO. The residual is what a heavy smooth leaves behind, so
content at wavelengths longer than the reference smoothing is absent from the
injected field by construction -- the same choice the reference makes, now
appearing on both sides. This tests the SHAPE of the roughness against a real
sample of it; it does not test the separation of roughness from curvature,
which is a different assumption examined in the calibration probe's reference
sigma sweep.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_nonparametric_surrogate.py
"""

import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

from probe_cross_estimator_consistency import BAND, corrected  # noqa: E402
from probe_real_patch_scatter import (  # noqa: E402
    load_patch,
    load_umbilicus,
    patch_dirs,
    radius_field,
    window_residuals,
)
from probe_scatter_estimator_calibration import (  # noqa: E402
    REFERENCE_SIGMA,
    smooth_reference,
)

WINDOW = (3, 4)
ORDERS = {"plane": 1, "quadratic": 2}
INJECT_RMS = [0.25, 0.5, 1.0, 2.0, 3.0, 4.0]
N_SAMPLES = 200
N_SEEDS = 4
SEED = 20260826
K_PAR = 0.265  # plane, anisotropic 1.45/1.05, reports/cross_estimator_consistency.txt
K_TOLERANCE = 0.25
OUT = os.path.join(_REPO, "reports", "nonparametric_surrogate.txt")


def residual_bank():
    """Real residual fields, one per patch: radius minus the heavy smooth.

    This is the injected field's source. No parameter is fitted to it and no
    distributional form is assumed; it is a sample of the thing itself.
    """
    umb = load_umbilicus()
    bank = []
    for d in patch_dirs():
        xs, ys, zs, valid = load_patch(d)
        if not valid.any() or valid.shape[0] < WINDOW[0] or valid.shape[1] < WINDOW[1]:
            continue
        r = radius_field(xs, ys, zs, umb)
        ref = smooth_reference(r, valid, sigma=REFERENCE_SIGMA)
        resid = np.where(valid, r - ref, 0.0)
        bank.append((os.path.basename(d), resid, valid))
    return bank


def transplant(donor, shape, rms, rng):
    """Donor residual tiled and cropped to `shape`, rescaled to `rms`.

    Tiling introduces seams the real field does not have. Disclosed, and it cuts
    against this probe's favourable direction: added high-frequency content
    raises apparent recovery, which would make k look LARGER and the correction
    smaller.
    """
    reps = (
        int(np.ceil(shape[0] / donor.shape[0])),
        int(np.ceil(shape[1] / donor.shape[1])),
    )
    tiled = np.tile(donor, reps)[: shape[0], : shape[1]]
    # A random roll so a fixed pairing does not always present the same corner.
    tiled = np.roll(
        tiled,
        (int(rng.integers(0, shape[0])), int(rng.integers(0, shape[1]))),
        axis=(0, 1),
    )
    sd = float(tiled.std())
    return tiled / sd * rms if sd > 0 else tiled


def refit_nonparametric(order, bank, seed):
    """Floor and k for one estimator, injecting real residuals cross-patch."""
    rng = np.random.default_rng(seed)
    floors, reported = [], {r: [] for r in INJECT_RMS}
    umb = load_umbilicus()
    dirs = list(patch_dirs())
    for idx, d in enumerate(dirs):
        xs, ys, zs, valid = load_patch(d)
        if not valid.any() or valid.shape[0] < WINDOW[0] or valid.shape[1] < WINDOW[1]:
            continue
        r = radius_field(xs, ys, zs, umb)
        ref = smooth_reference(r, valid, sigma=REFERENCE_SIGMA)
        base = window_residuals(
            ref, valid, WINDOW[0], WINDOW[1], order, rng, n_samples=N_SAMPLES
        )
        if base.size:
            floors.append(float(np.median(base)))
        if len(bank) < 2:
            continue
        # Fixed pairing: the next patch in the bank, never the patch itself.
        donor = bank[(idx + 1) % len(bank)][1]
        for rms in INJECT_RMS:
            field = transplant(donor, ref.shape, rms, rng)
            res = window_residuals(
                ref + field,
                valid,
                WINDOW[0],
                WINDOW[1],
                order,
                rng,
                n_samples=N_SAMPLES,
            )
            if res.size:
                reported[rms].append(float(np.median(res)))
    floor = float(np.median(floors)) if floors else float("nan")
    ks = []
    for rms in INJECT_RMS:
        if not reported[rms]:
            continue
        rep = float(np.median(reported[rms]))
        resid = rep**2 - floor**2
        if resid > 0:
            ks.append(np.sqrt(resid) / rms)
    return floor, (float(np.median(ks)) if ks else float("nan"))


def real_reported(order, seed):
    """Estimator output on real patches. Injection-independent by construction."""
    umb = load_umbilicus()
    rng = np.random.default_rng(seed)
    out = []
    for d in patch_dirs():
        xs, ys, zs, valid = load_patch(d)
        if not valid.any() or valid.shape[0] < WINDOW[0] or valid.shape[1] < WINDOW[1]:
            continue
        r = radius_field(xs, ys, zs, umb)
        res = window_residuals(
            r, valid, WINDOW[0], WINDOW[1], order, rng, n_samples=N_SAMPLES
        )
        out.extend(res.tolist())
    return np.array(out)


def main():
    bank = residual_bank()
    lo, hi = K_PAR * (1 - K_TOLERANCE), K_PAR * (1 + K_TOLERANCE)
    lines = [
        "Does k survive replacing the Gaussian surrogate with the real residual?",
        "",
        "Pre-registered: the injected field is a REAL residual, taken cross-patch (patch",
        "A's residual into patch B's reference, fixed pairing) so nothing is measured",
        "against a field it has already seen. No parameter is fitted to the real data.",
        f"Rule fixed in advance: plane k within {K_TOLERANCE:.0%} of the published",
        f"{K_PAR} (that is {lo:.3f} to {hi:.3f}) and the Gaussian surrogate is an",
        "adequate stand-in. Outside by more than the seed spread and the surrogate",
        "family is driving the correction; the direction is reported either way.",
        "",
        f"Residual bank: {len(bank)} real patches.",
        "",
    ]
    per = {}
    for name, order in ORDERS.items():
        rows = []
        for i in range(N_SEEDS):
            floor, k = refit_nonparametric(order, bank, SEED + 100 * i)
            rep = real_reported(order, SEED + 100 * i + 1)
            rows.append(
                {
                    "floor": floor,
                    "k": k,
                    "p50": float(np.median(rep)),
                    "corr": corrected(float(np.median(rep)), floor, k),
                }
            )
        per[name] = rows

    lines.append("  estimator   |  floor |      k | reported p50 | corrected p50")
    lines.append("  " + "-" * 64)
    for name in ORDERS:
        rows = per[name]
        lines.append(
            f"  {name:11s} | {np.median([r['floor'] for r in rows]):6.4f} "
            f"| {np.median([r['k'] for r in rows]):6.4f} "
            f"| {np.median([r['p50'] for r in rows]):12.4f} "
            f"| {np.median([r['corr'] for r in rows]):13.4f}"
        )
    lines.append("")

    ks = np.array([r["k"] for r in per["plane"]])
    k_np = float(np.median(ks))
    spread = float(ks.max() - ks.min())
    inside = lo <= k_np <= hi
    distance = 0.0 if inside else min(abs(k_np - lo), abs(k_np - hi))
    lines.append(
        f"  plane k under the real-residual injection: {k_np:.4f} "
        f"(seed range {ks.min():.4f} to {ks.max():.4f}, spread {spread:.4f})"
    )
    lines.append(f"  published Gaussian-surrogate k: {K_PAR}")
    if inside:
        lines.append(
            "  INSIDE the pre-registered interval: the Gaussian surrogate is an adequate "
            "stand-in for the real field as far as this correction is concerned."
        )
    elif distance > spread:
        direction = (
            "LARGER k means less attenuation, so the true correction is SMALLER and the "
            "~30 percent exceedance is an OVERESTIMATE."
            if k_np > K_PAR
            else "SMALLER k means more attenuation, so the true correction is LARGER and "
            "the ~30 percent exceedance is an UNDERESTIMATE."
        )
        lines.append(
            f"  OUTSIDE the pre-registered interval by more than the seed spread. "
            f"The surrogate family is driving the correction. {direction}"
        )
    else:
        lines.append(
            "  Outside the interval but by less than the seed spread: INCONCLUSIVE. "
            "Not to be read in either direction."
        )

    r = np.median([r["corr"] for r in per["plane"]]) / max(
        np.median([r["corr"] for r in per["quadratic"]]), 1e-12
    )
    lines.append("")
    lines.append(
        f"  Secondary, same band [{BAND[0]}, {BAND[1]}]: cross-estimator ratio under this "
        f"injection R = {r:.3f} -> "
        + ("consistent." if BAND[0] <= r <= BAND[1] else "INCONSISTENT.")
    )
    lines.append("")
    lines.append(
        "Limits, stated before the run: tiling a donor residual to the recipient's grid "
        "introduces seams the real field does not have, which can only add high-frequency "
        "content and so biases k upward, against the direction that would support the "
        "published figure. And the residual excludes wavelengths longer than the reference "
        "smoothing by construction, so this tests the SHAPE of the roughness against a real "
        "sample, not the separation of roughness from curvature."
    )
    text = "\n".join(lines) + "\n"
    with open(OUT, "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
