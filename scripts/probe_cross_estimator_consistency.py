"""Do two estimators with different attenuations agree after correction?

PRE-REGISTERED. This docstring, including the decision rule below, is committed
before the probe is run. (An earlier probe in this series committed its
preregistration after the run and had to disclose that; this one does not.)

WHY THIS EXISTS. The exceedance of about 30 percent rests on correcting the
real plane-fit residual by a fitted attenuation k: true = sqrt(reported^2 -
floor^2) / k. With the admissible anisotropic surrogate, k = 0.263, so the
correction multiplies the observed residual by roughly 3.8.

The check that was supposed to test this compared the corrected value against
directly observed deviation at the same window and reported a "4.1x gap,
unexplained". That comparison is vacuous, and I should have seen it sooner: the
corrected value IS the observed residual divided by k, so their ratio is 1/k by
construction. Arithmetic: 1/0.263 = 3.80, times the 2.179/2.025 sampling
difference between two measurements of the same quantity = 4.09, against the
4.07 "gap" reported. It was not an unexplained discrepancy. It was the
definition, restated.

So the open question was never "is the corrected number bigger than what we
see". It is "is k right".

THE TEST. The same real windows can be measured with a second estimator. The
quadratic fit has a very different attenuation (0.378 against the plane's 0.602
under the isotropic calibration) and a floor an order of magnitude smaller, and
it reports a very different raw number on real data: median 0.255 against the
plane's 0.846, p95 0.633 against 2.179. If the correction model is right, both
estimators are measuring the same physical scatter through different amounts of
attenuation, so after correction they must land on the same value. That is a
genuine test of k, because nothing in the correction of one estimator uses the
other.

DECISION RULE, fixed in advance:

  * Compute R = corrected(plane) / corrected(quadratic) on real data, under
    each surrogate, with both k's refit under THAT surrogate.
  * Sampling spread is estimated by re-running the whole chain over
    N_SEEDS independent seeds and taking the spread of R.
  * If R is within 1.25 of unity in either direction (0.80 <= R <= 1.25) under
    the admissible surrogate, the correction model survives this test, and the
    30 percent figure keeps its main support.
  * If R falls outside that band by more than the seed spread, the model that
    the exceedance depends on -- constant k above a floor, one k per estimator
    -- is falsified as a description of these data, and the corrected scatter
    (and therefore the ~30 percent) cannot be defended on it.
  * A third possibility is that R is outside the band but the seed spread is
    comparable to the deviation, in which case the test is inconclusive and
    must be reported as such rather than read in whichever direction suits.

WHAT THIS CANNOT DO. It cannot confirm that either corrected value is the true
scatter. Two estimators sharing a wrong assumption -- for instance, if the
injected surrogate misrepresents the real field's correlation structure in a
way that biases both fits in the same direction -- would agree and both be
wrong. Agreement is necessary, not sufficient. Disagreement, however, is
decisive: one number cannot be two.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_cross_estimator_consistency.py
"""

import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

from probe_anisotropic_surrogate import (  # noqa: E402
    ISOTROPIC_SIGMA,
    anisotropic_field,
)
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
SURROGATES = [
    ("isotropic 0.561 (published)", ISOTROPIC_SIGMA, ISOTROPIC_SIGMA),
    ("anisotropic 1.45 / 1.05 (admissible)", 1.45, 1.05),
]
INJECT_RMS = [0.25, 0.5, 1.0, 2.0, 3.0, 4.0]
N_SAMPLES = 200
N_SEEDS = 4
SEED = 20260826
BAND = (0.80, 1.25)
OUT = os.path.join(_REPO, "reports", "cross_estimator_consistency.txt")


def refit(order, sigma_col, sigma_row, seed):
    """Floor and attenuation k for one estimator under one surrogate.

    Deliberately the same injection-recovery design as the calibration this is
    testing, with `order` as the only new degree of freedom, so a difference in
    the answer cannot be attributed to a difference in method.
    """
    umb = load_umbilicus()
    rng = np.random.default_rng(seed)
    floors, reported = [], {r: [] for r in INJECT_RMS}
    for d in patch_dirs():
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
        for rms in INJECT_RMS:
            field = anisotropic_field(ref.shape, rms, sigma_col, sigma_row, rng)
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
    """What the estimator returns on real patches. Surrogate-independent."""
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


def corrected(reported_value, floor, k):
    return float(np.sqrt(max(reported_value**2 - floor**2, 0.0)) / k)


def one_seed(sigma_col, sigma_row, seed):
    row = {}
    for name, order in ORDERS.items():
        floor, k = refit(order, sigma_col, sigma_row, seed)
        rep = real_reported(order, seed + 1)
        row[name] = {
            "floor": floor,
            "k": k,
            "reported_p50": float(np.median(rep)),
            "corrected_p50": corrected(float(np.median(rep)), floor, k),
            "reported_p95": float(np.percentile(rep, 95)),
            "corrected_p95": corrected(float(np.percentile(rep, 95)), floor, k),
        }
    row["ratio"] = row["plane"]["corrected_p50"] / max(
        row["quadratic"]["corrected_p50"], 1e-12
    )
    row["ratio_p95"] = row["plane"]["corrected_p95"] / max(
        row["quadratic"]["corrected_p95"], 1e-12
    )
    return row


def main():
    lines = [
        "Do two estimators with different attenuations agree after correction?",
        "Pre-registered decision rule (committed before the run): if the corrected",
        f"plane / corrected quadratic ratio R lies in [{BAND[0]}, {BAND[1]}] under the",
        "admissible surrogate, the constant-k-above-a-floor correction survives this",
        "test. Outside it by more than the seed spread, the model the ~30 percent",
        "exceedance depends on is falsified as a description of these data. Outside it",
        "by less than the seed spread, the test is inconclusive and says so.",
        "",
        "First, why the previous physicality check could not have worked: the corrected",
        "value IS the observed residual divided by k, so comparing the two recovers 1/k",
        "and nothing else. The '4.1x unexplained gap' was 1/0.263 = 3.80 times a 1.08",
        "sampling difference between two measurements of the same quantity. Definition,",
        "not discrepancy.",
        "",
    ]
    for label, sc, sr in SURROGATES:
        seeds = [one_seed(sc, sr, SEED + 100 * i) for i in range(N_SEEDS)]
        lines.append(f"=== {label} ===")
        lines.append(
            "  estimator   |  floor |      k | rep p50 | corr p50 | rep p95 | corr p95"
        )
        lines.append("  " + "-" * 74)
        for name in ORDERS:
            f = np.median([s[name]["floor"] for s in seeds])
            k = np.median([s[name]["k"] for s in seeds])
            rep = np.median([s[name]["reported_p50"] for s in seeds])
            cor = np.median([s[name]["corrected_p50"] for s in seeds])
            r95 = np.median([s[name]["reported_p95"] for s in seeds])
            c95 = np.median([s[name]["corrected_p95"] for s in seeds])
            lines.append(
                f"  {name:11s} | {f:6.4f} | {k:6.4f} | {rep:7.4f} | {cor:8.4f} "
                f"| {r95:7.4f} | {c95:8.4f}"
            )
        ratios = np.array([s["ratio"] for s in seeds])
        r_med = float(np.median(ratios))
        spread = float(ratios.max() - ratios.min())
        lines.append(
            f"  R = corrected(plane) / corrected(quadratic) = {r_med:.3f}"
            f"   (seed range {ratios.min():.3f} to {ratios.max():.3f}, spread {spread:.3f})"
        )
        inside = BAND[0] <= r_med <= BAND[1]
        distance = 0.0 if inside else min(abs(r_med - BAND[0]), abs(r_med - BAND[1]))
        if inside:
            verdict = "PASSES the pre-registered band: the two estimators agree."
        elif distance > spread:
            verdict = (
                "FAILS the pre-registered band by more than the seed spread: the two "
                "estimators do NOT measure the same corrected scatter, so a single k "
                "per estimator above a floor does not describe these data."
            )
        else:
            verdict = (
                "OUTSIDE the band but by less than the seed spread: INCONCLUSIVE. "
                "Do not read this in either direction."
            )
        lines.append(f"  {verdict}")

        # Supplementary, and NOT pre-registered: the rule above was fixed on the
        # median before the run and is reported as such. The exceedance actually
        # uses the upper tail, so the same ratio is shown at p95, added after
        # seeing the p50 result. It is reported whichever way it comes out, but
        # it must not be described as having been pre-registered.
        r95s = np.array([s["ratio_p95"] for s in seeds])
        r95_med = float(np.median(r95s))
        lines.append(
            f"  Supplementary (not pre-registered): the same ratio at p95, the "
            f"quantile the exceedance actually uses, is {r95_med:.3f} "
            f"(seed range {r95s.min():.3f} to {r95s.max():.3f}). "
            + (
                "Also inside the band."
                if BAND[0] <= r95_med <= BAND[1]
                else "OUTSIDE the band, so the agreement above does not extend to "
                "the tail the exceedance is computed from."
            )
        )
        lines.append("")

    lines.append(
        "Reminder of what this cannot show: two estimators sharing a wrong assumption "
        "would agree and both be wrong, so agreement is necessary and not sufficient. "
        "Disagreement is the decisive direction, because one quantity cannot be two."
    )
    text = "\n".join(lines) + "\n"
    with open(OUT, "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
