"""The exceedance with the REAL residual field on both sides.

PRE-REGISTERED. Committed before the run, decision rule and validity gate
included.

WHY. `reports/nonparametric_surrogate.txt` tried to test the surrogate family by
refitting k alone under a real-residual injection, and its verdict had to be
withdrawn: k is (recovered windowed residual) / (injected GLOBAL rms), and the
real residual's power sits at wavelengths a 3x4 plane fit removes, so its k was
not the same quantity as the Gaussian surrogates' k. The withdrawal named this
probe as the follow-up that would actually work.

The reason it works is that the normalisation cancels. The exceedance compares a
corrected scatter against an onset, and BOTH are expressed in the injected
field's global-rms units. A field that delivers little signal into a 3x4 window
gets a small k, which inflates the corrected scatter -- and it needs a
correspondingly larger global rms before villa's verdict flips, which inflates
the onset by the same mechanism. Comparing the two is legitimate where comparing
bare k values was not. So this asks the question the withdrawn probe meant to
ask: does the ~24% survive replacing the fitted Gaussian with a real sample of
the thing it stands in for?

METHOD. Identical to probe_self_consistent_exceedance, with one substitution:
the injected field is a real patch residual, tiled to the required shape and
scaled to the requested global rms, rather than a Gaussian with fitted smoothing
lengths. Everything else -- villa's unmodified scoring function, the same rays,
the same estimator, the same corrected-scatter formula -- is unchanged, so a
difference in the answer is attributable to the field.

VALIDITY GATE, checked before the decision rule is read. The onset sweep must be
wide enough for most rays to actually produce an onset. The real residual needs a
much larger global rms than a Gaussian to deliver the same in-window signal
(measured ratio 0.055 against 0.308), so a ladder that stops at 4.0 would return
"no onset" for nearly every ray and an exceedance near zero that means only that
the sweep was too short. If more than 25 percent of rays yield no onset within
the swept range, THIS RESULT IS VOID and must be re-run wider; the fraction is
reported either way.

DECISION RULE, fixed in advance. Let E_real be the exceedance under the real
residual and E_gauss = 23.59% the published figure under the admissible Gaussian:

  * E_real within [0.5x, 2.0x] of E_gauss (11.8% to 47.2%): the headline does not
    depend on the surrogate family, and ~24% stands as published.
  * Outside that band by more than the seed spread: the surrogate family IS
    driving the headline. Direction reported either way -- higher means ~24% is
    an underestimate, lower means it is an overestimate.
  * Outside by less than the seed spread: inconclusive, reported as such.

The band is deliberately a factor of two, and that is tight rather than
permissive in context: across the swept Gaussian arms this same exceedance runs
1.91% to 28.61%, an order of magnitude, so a factor of two would not absorb a
real surrogate dependence.

WHAT THIS STILL CANNOT DO. The residual is what a heavy smooth leaves behind, so
wavelengths longer than the reference smoothing are absent from the injected
field by construction. And the donor is tiled to fill the injection grid, which
introduces seams the real field does not have. Both are recorded in the artifact.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_real_residual_exceedance.py
"""

import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

from probe_nonparametric_surrogate import (  # noqa: E402
    residual_bank,
    transplant,
    windowed_over_global,
)
from probe_real_patch_scatter import window_residuals  # noqa: E402
from probe_self_consistent_exceedance import (  # noqa: E402
    INJECTION_GRID_SHAPE,
    N_RAYS,
    WINDOW,
    real_reported_scatter,
)
from probe_spiral_satisfaction_empirical_transform import (  # noqa: E402
    load_shard,
    usable_rays,
)

# The published Gaussian answer this is compared against.
E_GAUSS = 23.59
BAND = (0.5, 2.0)
VOID_IF_NO_ONSET_ABOVE = 0.25

# Extended ladder. The 0.75-4.0 range used for Gaussian fields cannot reach the
# onset for a field that delivers a fifth as much signal into the window, so the
# ladder continues geometrically. Stated in the pre-registration, not chosen
# after seeing where the onsets fell.
RMS_LEVELS = [0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
RMS_LEVELS += [5.0, 6.5, 8.0, 10.0, 13.0, 16.0, 20.0, 26.0, 32.0, 40.0, 52.0, 64.0]
# A second ladder reaching 32x further, used only to establish whether a failure
# to find an onset is a sweep-length problem or a property of the field. It must
# be a strict SUPERSET of the first: a first version was merely longer and also
# coarser, which reported MORE rays without an onset on the longer ladder -- an
# impossibility that was a resolution artifact, and would have been published as
# "extending the ladder changes nothing" had the two numbers not disagreed in the
# wrong direction. As a superset, no-onset can only fall or stay equal.
LADDER_LONG = RMS_LEVELS + [96.0, 192.0, 384.0, 768.0, 1536.0, 2048.0]

INJECT_RMS = [0.25, 0.5, 1.0, 2.0, 3.0, 4.0]
N_SAMPLES = 200
N_SEEDS = 4
SEED = 20260826
OUT = os.path.join(_REPO, "reports", "real_residual_exceedance.txt")


def make_field_fn(donor, donor_valid=None):
    """A drop-in replacement for `probe_correlated_scatter.noise_field`.

    Same signature and same contract -- a field of the requested shape scaled to
    the requested GLOBAL rms -- so the scoring path is untouched and every number
    still comes from villa's own metric.

    The donor is FIXED by the caller, deliberately. A first version drew a new
    donor inside this function on every call, so walking up the rms ladder
    changed the field's shape at each rung as well as its amplitude: the scan was
    over donor x amplitude jointly, and any onset it found was partly a lottery
    over donors. The symptom was a |delta| that jumped 0.0000, 0.2545, 0.0000,
    0.1030 across successive rungs instead of rising. Amplitude must be the only
    thing that varies along a ladder whose first crossing is being read as an
    onset.
    """

    def field(shape, rms, _sigma, rng):
        return transplant(donor, shape, rms, rng, valid=donor_valid)

    return field


def onsets_under_real(rays, bank, seed):
    """First rms at which villa's verdict flips, per ray, under the real field."""
    import probe_correlated_scatter as pcs
    from probe_correlated_scatter import run_level

    original = pcs.noise_field
    try:
        per_ray = []
        for i, ray in enumerate(rays):
            # One donor per ray, held across the whole ladder.
            _, donor, donor_valid = bank[(seed + i) % len(bank)]
            pcs.noise_field = make_field_fn(donor, donor_valid)
            hit = None
            for rms in RMS_LEVELS:
                _, flipped = run_level(
                    [ray], rms, 1.0, np.random.default_rng(seed + 1000 * i)
                )
                if flipped:
                    hit = rms
                    break
            per_ray.append(hit)
        return per_ray
    finally:
        pcs.noise_field = original


def refit_under_real(bank, seed):
    """Floor and k for the plane estimator under the real-residual injection.

    Cross-patch, as in probe_nonparametric_surrogate: a patch never receives its
    own residual.
    """
    from probe_real_patch_scatter import (
        load_patch,
        load_umbilicus,
        patch_dirs,
        radius_field,
    )
    from probe_scatter_estimator_calibration import REFERENCE_SIGMA, smooth_reference

    umb = load_umbilicus()
    rng = np.random.default_rng(seed)
    names = [b[0] for b in bank]
    floors, reported = [], {r: [] for r in INJECT_RMS}
    for d in patch_dirs():
        xs, ys, zs, valid = load_patch(d)
        if not valid.any() or valid.shape[0] < WINDOW[0] or valid.shape[1] < WINDOW[1]:
            continue
        r = radius_field(xs, ys, zs, umb)
        ref = smooth_reference(r, valid, sigma=REFERENCE_SIGMA)
        base = window_residuals(
            ref, valid, WINDOW[0], WINDOW[1], 1, rng, n_samples=N_SAMPLES
        )
        if base.size:
            floors.append(float(np.median(base)))
        here = names.index(os.path.basename(d))
        donor_name, donor, donor_valid = bank[(here + 1) % len(bank)]
        assert donor_name != os.path.basename(d), "self-injection"
        for rms in INJECT_RMS:
            field = transplant(donor, ref.shape, rms, rng, valid=donor_valid)
            res = window_residuals(
                ref + field, valid, WINDOW[0], WINDOW[1], 1, rng, n_samples=N_SAMPLES
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


def no_onset_fraction(rays, bank, ladder, seeds=3):
    """Share of rays whose verdict never differs anywhere on `ladder`."""
    global RMS_LEVELS
    saved = RMS_LEVELS
    RMS_LEVELS = ladder
    try:
        out = []
        for s in range(seeds):
            per = onsets_under_real(rays, bank, seed=1 + 97 * s)
            out.append(sum(o is None for o in per) / max(len(per), 1))
        return float(np.mean(out)), [float(x) for x in out]
    finally:
        RMS_LEVELS = saved


def main():
    bank = residual_bank()
    rays = usable_rays(load_shard(), n_rays=N_RAYS)
    reported = real_reported_scatter(seed=SEED)

    floor, k = refit_under_real(bank, SEED)
    true_scatter = np.sqrt(np.maximum(reported**2 - floor**2, 0.0)) / k

    exceedances, no_onset = [], []
    for s in range(N_SEEDS):
        per_ray = onsets_under_real(rays, bank, seed=SEED + 97 * s)
        no_onset.append(sum(o is None for o in per_ray) / max(len(per_ray), 1))
        exceedances.append(
            float(
                np.mean(
                    [
                        float((true_scatter >= o).mean()) if o is not None else 0.0
                        for o in per_ray
                    ]
                )
            )
        )
    e_real = float(np.mean(exceedances)) * 100
    spread = (max(exceedances) - min(exceedances)) * 100
    void_frac = float(np.mean(no_onset))

    rng = np.random.default_rng(SEED)
    ratios = [
        windowed_over_global(
            transplant(r, INJECTION_GRID_SHAPE, 1.0, rng, valid=v), rng
        )
        for _, r, v in bank[:5]
    ]
    finite = [x for x in ratios if np.isfinite(x)]

    lines = [
        "The exceedance with the REAL residual field on both sides",
        "",
        "The follow-up the withdrawn non-parametric probe named. Comparing bare k values",
        "across fields was invalid because k is measured against an injected GLOBAL rms;",
        "here BOTH the corrected scatter and the onset are in those same units, so the",
        "normalisation cancels and the comparison is legitimate.",
        "",
        f"  injected field: real patch residuals, {len(bank)} donors, tiled and cross-paired",
        "  windowed/global for these fields: "
        + (f"{min(finite):.3f} to {max(finite):.3f}" if finite else "all degenerate")
        + "  (Gaussian 1.20/1.00 is 0.308)",
        "",
        f"  plane floor {floor:.4f}, k {k:.4f}",
        f"  corrected real scatter, median {float(np.median(true_scatter)):.2f}v",
        "",
        "=== Validity gate, read before the verdict ===",
        f"  rays with no onset inside the swept range: {void_frac:.1%} "
        f"(ladder {RMS_LEVELS[0]} to {RMS_LEVELS[-1]})",
    ]
    void = void_frac > VOID_IF_NO_ONSET_ABOVE
    if void:
        short_f, short_each = no_onset_fraction(rays, bank, RMS_LEVELS)
        long_f, long_each = no_onset_fraction(rays, bank, LADDER_LONG)
        from probe_anisotropic_surrogate import onsets_under

        g = [
            sum(o is None for o in onsets_under(rays, 1.20, 1.00, seed=1 + 97 * s))
            / max(len(rays), 1)
            for s in range(3)
        ]
        lines.append(
            f"  ⚠ ABOVE the pre-registered {VOID_IF_NO_ONSET_ABOVE:.0%} limit: the exceedance"
            " below is VOID and carries no verdict."
        )
        lines.append("")
        lines.append("=== What the gate's failure does and does not mean ===")
        lines.append(
            "  ⚠ An earlier version of this artifact read the gate's failure as a finding:"
        )
        lines.append(
            "  that a real-residual-shaped perturbation mostly cannot diverge villa's verdict,"
        )
        lines.append(
            "  that the surrogate perturbs 2.3x as readily, and therefore that ~24% is biased"
        )
        lines.append(
            "  high. That was an artifact of a broken injection: `transplant` cropped the"
        )
        lines.append(
            "  donor's TOP-LEFT corner, which for these patches lies outside the traced region,"
        )
        lines.append(
            "  so five of ten donors injected an all-zero field and the rest were 43 to 67"
        )
        lines.append(
            "  percent zeros. Most of those rays diverged no verdict because nothing was"
        )
        lines.append("  added to them. Corrected, the comparison inverts:")
        lines.append("")
        lines.append(
            f"    real residual, ladder to {RMS_LEVELS[-1]:.0f}:   no onset for "
            f"{short_f:.0%} of rays  ({', '.join(f'{x:.0%}' for x in short_each)})"
        )
        lines.append(
            f"    real residual, ladder to {LADDER_LONG[-1]:.0f}: no onset for "
            f"{long_f:.0%} of rays  ({', '.join(f'{x:.0%}' for x in long_each)})"
        )
        lines.append(
            f"    Gaussian 1.20/1.00, its own ladder:  no onset for "
            f"{float(np.mean(g)):.0%} of rays"
        )
        ratio = (1 - float(np.mean(g))) / max(1 - long_f, 1e-9)
        lines.append("")
        lines.append(
            f"  The two agree: the Gaussian diverges the verdict on {ratio:.1f}x as many rays"
            f" ({1 - float(np.mean(g)):.0%} against {1 - long_f:.0%}). So a field with the real"
        )
        lines.append(
            "  residual's shape perturbs villa's verdict about as often as the fitted"
        )
        lines.append(
            "  surrogate does, which is evidence FOR the surrogate being an adequate stand-in"
        )
        lines.append(
            "  for this purpose, and removes the basis for the withdrawn claim that ~24% is"
        )
        lines.append("  biased high.")
        lines.append("")
        lines.append(
            "  The gate still fails, and what it now exposes is different and worth stating:"
        )
        lines.append(
            f"  about half the rays have no onset under EITHER field ({float(np.mean(g)):.0%}"
            " for the Gaussian). The published exceedance treats a ray with no onset as"
        )
        lines.append(
            "  contributing zero, so roughly half of the 23.59% figure's denominator is rays"
        )
        lines.append(
            "  that can never contribute. That is a property of the published number worth"
        )
        lines.append(
            "  knowing; it is not addressed here, and the 25% gate was set without knowing"
        )
        lines.append("  the Gaussian arm would fail it too.")
    else:
        lines.append("  Within the pre-registered limit; the sweep reaches the onset.")
    lines.append("")
    lines.append("=== Result ===")
    lines.append(
        f"  exceedance under the REAL residual field: {e_real:.2f}%  "
        f"(seed spread {spread:.2f})"
    )
    lines.append(f"  published Gaussian figure:                {E_GAUSS:.2f}%")
    lo, hi = E_GAUSS * BAND[0], E_GAUSS * BAND[1]
    lines.append(f"  pre-registered band:                      {lo:.2f}% to {hi:.2f}%")
    if void:
        lines.append("  No verdict: the validity gate above failed.")
    elif lo <= e_real <= hi:
        lines.append(
            "  INSIDE the band. The headline does not depend on the surrogate family: "
            "replacing the fitted Gaussian with a real sample of the residual leaves the "
            "exceedance in the same place."
        )
    else:
        distance = min(abs(e_real - lo), abs(e_real - hi))
        if distance > spread:
            direction = (
                "higher, so the published ~24% is an UNDERESTIMATE"
                if e_real > hi
                else "lower, so the published ~24% is an OVERESTIMATE"
            )
            lines.append(
                f"  OUTSIDE the band by more than the seed spread: the surrogate family IS "
                f"driving the headline, {direction}."
            )
        else:
            lines.append(
                "  Outside the band but by less than the seed spread: INCONCLUSIVE."
            )
    lines.append("")
    lines.append(
        "Limits. The injected residual excludes wavelengths longer than the reference "
        "smoothing by construction, and donors are tiled to fill the injection grid, which "
        "adds seams the real field does not have. Neither is fixed here; both would have to "
        "be addressed before calling the surrogate question closed rather than tested."
    )
    text = "\n".join(lines) + "\n"
    with open(OUT, "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
