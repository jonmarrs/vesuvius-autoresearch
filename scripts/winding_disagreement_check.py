"""The report proposes a fix. This is the fix, implemented and demonstrated.

`reports/spiral_satisfaction_winding_blindness.md` ends by proposing the
cheapest remedy for the blindness it documents: for patches reachable from an
absolute-winding annotation, compare the winding the satisfaction metric snapped
to against the winding the annotations imply, and report the disagreement
alongside the existing figure. Report-only, no change to what the metric
accepts.

Proposing a fix without implementing it leaves the reader to judge whether it
would work. This implements it in one function, demonstrates that it fires
exactly where the metric is blind, and pins that with tests. It is a
demonstration rather than a patch: villa's own code is pinned and untouched.

WHAT IT REPLICATES. `satisfaction_metrics.py` derives its target by taking the
median shifted radius of the patch's centre-column component and snapping it to
the nearest multiple of dr. The block is at lines 242-248 in our pin
`ced62390e` and at lines 551-555 upstream as of `6847063f` (2026-08-26); cite it
by name rather than by line, because the file has grown 714 -> 1092 lines in
three days and moved directory once:

    modulus = median_shifted_radius % dr
    target  = median - modulus            if modulus < dr/2
              median + dr - modulus       otherwise

`snapped_winding` reproduces that arithmetic rather than substituting `round()`,
because the two are not the same function. Swept over 120,060 medians they
disagree 52 times, and every disagreement is at an exact half-winding tie. Which
way villa falls at a tie is not a stated rule and not "rounds up": it is decided
by whether `median % dr` lands a hair below or above `dr/2` in floating point,
so at w+0.5 it can go either way (w=1 gives 1, w=2 gives 1). That is measure-zero
on real data. It is reproduced exactly anyway, because a detector that disagreed
with the metric at the boundary would report a disagreement the metric does not
have, and this is a tool for telling those apart.

WHAT IT ADDS. Nothing about the patch's own geometry, which is the whole point.
The snapped winding is derived from the patch; the expected winding must come
from somewhere else -- an absolute annotation, or a propagation from one, which
is what `find_inconsistent_windings.py` already computes. The check is the
comparison between the two, and it is exactly the comparison the metric never
makes.

LIMIT, stated plainly. This cannot be validated end-to-end here: no fitted
spiral checkpoint is published, so there are no real annotated patches to run it
against. What is demonstrated is that the check fires on the displacement the
metric scores identically, and stays silent on a patch that is merely noisy.
Whether annotations reach enough patches in practice is a question for someone
with the fit.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/winding_disagreement_check.py
"""

import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

OUT = os.path.join(_REPO, "reports", "winding_disagreement_check.txt")


def shifted_radius(radius, theta, dr):
    """villa's shifted radius: radius with the spiral's own advance removed.

    A point on winding w has shifted radius w*dr regardless of where it sits
    around the turn, which is what makes the median meaningful.
    """
    return radius - theta / (2 * np.pi) * dr


def snapped_target(median_shifted, dr):
    """The target villa snaps to, by villa's arithmetic rather than by rounding.

    Kept in this form deliberately. It is not `round()`: the two disagree at exact
    half-winding ties, where villa's outcome is decided by floating-point residue
    rather than by a rule. Reproducing the arithmetic means the detector cannot
    report a disagreement the metric does not have.
    """
    modulus = median_shifted % dr
    return np.where(
        modulus < dr / 2, median_shifted - modulus, median_shifted + dr - modulus
    )


def snapped_winding(radii, thetas, dr):
    """The integer winding the satisfaction metric will score this patch against."""
    med = float(np.median(shifted_radius(np.asarray(radii), np.asarray(thetas), dr)))
    return int(round(float(snapped_target(med, dr)) / dr))


def disagreement(radii, thetas, dr, expected_winding):
    """Windings between where the metric will score this patch and where it belongs.

    Zero means the metric's self-derived target agrees with the annotation. Any
    other value is the number of whole windings the patch is misplaced by, and it
    is precisely the quantity the satisfied-quad fraction cannot see.
    """
    return snapped_winding(radii, thetas, dr) - int(expected_winding)


def radii_thetas_of(patch):
    """Polar coordinates of a patch, so both columns below describe one object."""
    ys = patch.zyxs[..., 1].numpy()
    xs = patch.zyxs[..., 2].numpy()
    return np.sqrt(ys**2 + xs**2).ravel(), (np.arctan2(ys, xs) % (2 * np.pi)).ravel()


def main():
    from probe_spiral_satisfaction_robustness import add_radius_scatter, draw_unit_noise
    from probe_spiral_satisfaction_splicing_and_seam import REPORTING, score_with
    from probe_spiral_satisfaction_winding import (
        IdentityTransform,
        build_synthetic_patch,
        displace,
    )

    dr = 12.81
    winding = 5
    base = build_synthetic_patch(dr=dr, winding=winding)
    noise = draw_unit_noise(base.zyxs.shape[0], base.zyxs.shape[1])
    noisy = add_radius_scatter(base, noise, 2.0 / dr, dr)

    cases = [
        ("correctly placed", base, 0.0),
        ("displaced one whole winding", base, 1.0),
        ("displaced two whole windings", base, 2.0),
        ("displaced 23 whole windings", base, 23.0),
        ("correctly placed, 2.0 vox scatter", noisy, 0.0),
        ("displaced one winding, 2.0 vox scatter", noisy, 1.0),
    ]

    lines = [
        "The proposed fix, implemented and demonstrated",
        "",
        "The report proposes comparing the winding the metric snapped to against the",
        "winding an absolute annotation implies. This is that comparison. It adds nothing",
        "about the patch's own geometry, which is the point: the snapped winding comes",
        "from the patch, the expected winding must come from an annotation, and the check",
        "is the comparison the metric never makes.",
        "",
        f"  dr = {dr} voxels, patch belongs on winding {winding}",
        "  villa's column is scored by its own unmodified function, not asserted.",
        "",
        "   case                                     villa says   the check says",
        "  " + "-" * 74,
    ]
    villa_scores = []
    for label, patch, nw in cases:
        moved = patch if nw == 0.0 else displace(patch, dr, n_windings=nw)
        frac = score_with(moved, dr, REPORTING, IdentityTransform())
        villa_scores.append(frac)
        radii, thetas = radii_thetas_of(moved)
        d = disagreement(radii, thetas, dr, winding)
        verdict = "agrees" if d == 0 else f"DISAGREES by {d:+d}"
        lines.append(f"   {label:38s}   {frac:10.6f}   {verdict}")

    identical = max(villa_scores) - min(villa_scores) < 1e-12
    lines += [
        "",
        f"  villa's scores across every row: {'IDENTICAL' if identical else 'NOT identical'}"
        f" (spread {max(villa_scores) - min(villa_scores):.2e}).",
    ]
    if identical:
        lines.append(
            "  That is the finding this check answers, and it is computed here rather than"
        )
        lines.append(
            "  quoted: one number for a patch in the right place and for the same patch 23"
        )
        lines.append(
            "  windings away. The check separates them without looking at the patch's shape."
        )
    else:
        lines.append(
            "  ⚠ Not identical, so the demonstration does not hold as written and the rows"
        )
        lines.append("  above must be read individually.")
    lines += [
        "",
        "  The scatter rows matter as much as the displaced ones. A noisy patch in the",
        "  right place still reports agreement, so the check does not fire on noise, and a",
        "  noisy patch in the wrong place still reports the displacement.",
        "",
        "Limit. This cannot be validated end to end here: no fitted spiral checkpoint is",
        "published, so there are no real annotated patches to run it against. What is",
        "shown is that the check fires on the displacement the metric scores identically",
        "and stays silent on a patch that is merely noisy. Whether annotations reach",
        "enough patches in practice is a question for someone with the fit.",
    ]
    text = "\n".join(lines) + "\n"
    with open(OUT, "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
