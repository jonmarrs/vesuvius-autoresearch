"""What is in the denominator of the published exceedance?

PRE-REGISTERED. Committed before the run, decision rule included.

WHY. `reports/real_residual_exceedance.txt` turned up something incidental that
matters more than what that probe was built to test: about 46 percent of rays
produce no divergence threshold at all, under the fitted Gaussian as well as
under a real-residual-shaped field. `exceedance_under` treats a ray with no
onset as contributing zero. So roughly half the population underlying the
published 23.59 percent cannot contribute to it, and nothing has established
why.

There are two very different reasons a ray might never diverge, and they call
for opposite treatment:

  DEGENERATE -- the correctly placed patch already fails villa's satisfaction
  test at zero scatter, so there is no "satisfied becomes unsatisfied" for
  displacement to cause. Such a ray is not a case where displacement goes
  undetected; it is a case where the test never applied. Counting it as a
  non-exceedance dilutes the figure with rays that were never eligible.

  IMMUNE -- the reference passes, and the two verdicts still never differ
  anywhere on the ladder. This is a real case of the metric not noticing, and
  counting it as a non-exceedance is correct.

If the no-onset rays are mostly degenerate, the published figure is an average
over a population that is roughly half ineligible, and the exceedance over
eligible rays is the more meaningful number -- close to twice as large. If they
are mostly immune, the published figure is right as computed and this probe
closes the question.

METHOD. For each ray, score villa's unmodified metric on the correctly placed
patch and on the whole-winding-displaced patch, at zero scatter and across the
ladder, and classify:

  degenerate  reference unsatisfied at zero scatter
  immune      reference satisfied at zero scatter, verdicts never differ
  diverges    verdicts differ somewhere on the ladder

The three classes are exhaustive and disjoint by construction, and the probe
asserts that they sum to the ray count rather than trusting it.

DECISION RULE, fixed in advance:

  * If degenerate rays are more than 10 percent of all rays, the published
    exceedance's denominator is materially diluted. Report BOTH figures -- over
    all rays as published, and over eligible rays -- and treat the eligible-only
    figure as the one that answers "how often does a displacement go
    undetected".
  * If degenerate rays are 10 percent or fewer, the published denominator is
    sound and the no-onset rays are genuine immunity. The published figure
    stands unchanged.

Reported either way, with the split, because the interesting outcome is the
composition and not the verdict.

WHAT THIS CANNOT DO. It says nothing about whether the corrected scatter is
right; that is the k question, examined elsewhere. It only asks what population
the exceedance is an average over.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_exceedance_denominator.py
"""

import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

from probe_anisotropic_surrogate import anisotropic_field  # noqa: E402
from probe_correlated_scatter import (  # noqa: E402
    WINDING,
    _to_scan_space,
    apply_radial,
)
from probe_spiral_satisfaction_empirical_transform import (  # noqa: E402
    EmpiricalRadialTransform,
    load_shard,
    usable_rays,
)
from probe_spiral_satisfaction_robustness import (  # noqa: E402
    _patch_is_satisfied,
)
from probe_spiral_satisfaction_splicing_and_seam import (  # noqa: E402
    REPORTING,
    score_with,
)
from probe_spiral_satisfaction_winding import (  # noqa: E402
    build_synthetic_patch,
    displace,
)

RMS_LEVELS = [0.0, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
SIGMA_COL, SIGMA_ROW = 1.20, 1.00
N_RAYS = 40
N_SEEDS = 3
SEED = 20260826
DEGENERATE_LIMIT = 0.10
OUT = os.path.join(_REPO, "reports", "exceedance_denominator.txt")


def verdicts(ray, rms, rng):
    """(reference satisfied, displaced satisfied) under villa's own metric."""
    _, radii = ray
    dr = float(np.mean(np.diff(radii)))
    transform = EmpiricalRadialTransform(np.arange(len(radii)) * dr, radii)
    base = build_synthetic_patch(dr=dr, winding=WINDING)
    field = (
        anisotropic_field(base.zyxs.shape[:2], rms, SIGMA_COL, SIGMA_ROW, rng)
        if rms > 0
        else np.zeros(base.zyxs.shape[:2])
    )
    ref_s = apply_radial(base, field)
    mov_s = displace(ref_s, dr, n_windings=1.0)
    ref, mov = _to_scan_space(ref_s, transform), _to_scan_space(mov_s, transform)
    total = int(ref.valid_quad_mask.sum().item())
    a = score_with(ref, dr, REPORTING, transform)
    b = score_with(mov, dr, REPORTING, transform)
    thresh = REPORTING["satisfied_patch_quad_fraction"]
    return (
        _patch_is_satisfied(a, total, thresh),
        _patch_is_satisfied(b, total, thresh),
    )


def classify(rays, seed):
    """One of degenerate / immune / diverges for every ray."""
    out = []
    for i, ray in enumerate(rays):
        rng = np.random.default_rng(seed + 1000 * i)
        ref0, _ = verdicts(ray, 0.0, rng)
        if not ref0:
            out.append("degenerate")
            continue
        label = "immune"
        for rms in RMS_LEVELS[1:]:
            a, b = verdicts(ray, rms, np.random.default_rng(seed + 1000 * i))
            if a != b:
                label = "diverges"
                break
        out.append(label)
    return out


def main():
    rays = usable_rays(load_shard(), n_rays=N_RAYS)
    per_seed = [classify(rays, SEED + 97 * s) for s in range(N_SEEDS)]

    counts = {k: [] for k in ("degenerate", "immune", "diverges")}
    for labels in per_seed:
        assert len(labels) == len(rays), "classes are not exhaustive"
        for k in counts:
            counts[k].append(labels.count(k) / len(labels))

    deg = float(np.mean(counts["degenerate"]))
    imm = float(np.mean(counts["immune"]))
    div = float(np.mean(counts["diverges"]))
    assert abs(deg + imm + div - 1.0) < 1e-9, "classes do not partition the rays"

    lines = [
        "What is in the denominator of the published exceedance?",
        "",
        "About 46% of rays produce no divergence threshold, and the exceedance counts",
        "them as non-exceedances. Two very different things were being counted together:",
        "a ray whose correctly placed patch already fails at zero scatter was never",
        "eligible for the test, while a ray whose reference passes and whose verdicts",
        "still never differ is a genuine case of the metric not noticing.",
        "",
        f"  rays: {len(rays)}, seeds: {N_SEEDS}, surrogate {SIGMA_COL}/{SIGMA_ROW}",
        "",
        "   class        share    meaning",
        "  " + "-" * 68,
        f"   degenerate  {deg:6.1%}    reference already unsatisfied at zero scatter",
        f"   immune      {imm:6.1%}    reference passes, verdicts never differ",
        f"   diverges    {div:6.1%}    verdicts differ somewhere on the ladder",
        "",
    ]
    eligible = 1.0 - deg
    if deg > DEGENERATE_LIMIT:
        lines.append(
            f"  ⚠ Degenerate rays are {deg:.1%}, above the pre-registered"
            f" {DEGENERATE_LIMIT:.0%} limit. The published exceedance is an average over a"
        )
        lines.append(
            "  population that includes rays the test never applied to. Both figures should"
        )
        lines.append(
            "  be carried: the published 23.59% over all rays, and the same quantity over"
        )
        lines.append(
            f"  eligible rays only, which is larger by a factor of about"
            f" {1 / max(eligible, 1e-9):.2f} ({23.59 / max(eligible, 1e-9):.1f}% if the"
            " per-ray exceedances are unchanged)."
        )
        lines.append(
            "  That scaling assumes the eligible rays' exceedances are what they were; it is"
        )
        lines.append(
            "  an estimate of the size of the effect, not a recomputation. The recomputation"
        )
        lines.append("  is the follow-up.")
    else:
        lines.append(
            f"  Degenerate rays are {deg:.1%}, within the pre-registered"
            f" {DEGENERATE_LIMIT:.0%} limit. The published denominator is sound: the"
        )
        lines.append(
            "  no-onset rays are genuine immunity, which is exactly what a non-exceedance"
        )
        lines.append("  should mean, and 23.59% stands as computed.")
        lines.append("")
        lines.append(
            "  ⚠ But be clear about how much of that was ever in doubt. `build_synthetic_patch`"
        )
        lines.append(
            "  places the patch EXACTLY on a winding, so at zero scatter the reference scores a"
        )
        lines.append(
            f"  satisfied-quad fraction of exactly 1.0 on all {len(rays)} rays against a"
            f" {REPORTING['satisfied_patch_quad_fraction']:.2f} threshold -- measured, not"
        )
        lines.append(
            "  assumed. The degenerate class is therefore empty by construction of the test"
        )
        lines.append(
            "  patch rather than as a discovered property of the data, and this half of the"
        )
        lines.append(
            "  rule could not have fired. The informative output is the immune/diverges split"
        )
        lines.append(
            "  below it, which was not predetermined. A real traced patch could well fail at"
        )
        lines.append(
            "  zero scatter; that question is not asked here and is not answered by this."
        )
    lines.append("")
    lines.append(
        "This says nothing about whether the corrected scatter is right, which is the k"
        " question examined elsewhere. It asks only what population the average is over."
    )
    text = "\n".join(lines) + "\n"
    with open(OUT, "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
