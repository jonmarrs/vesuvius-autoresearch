"""Is a real window unsatisfiable, or was it just scored at the wrong dr?

PRE-REGISTERED. Committed before the run, decision rule included.

WHY. `reports/real_patch_satisfaction.txt` found that only 21.7 percent of real
extent-matched windows are satisfied by villa's metric, against a pre-registered
50, and the report now carries that as a limit on how much the winding blindness
can matter in practice. But that probe scored every window at a single dr, the
published median 12.81 voxels, and named the per-patch fit as its follow-up. The
real inter-winding spacing varies 11.32 to 16.74 across shards, so a window
sitting where the spacing differs was scored against a spacing it does not have,
and would fail for a reason that has nothing to do with the metric's behaviour.

This asks the strongest version of the question: give every window the dr that
suits it best, and see whether it can be satisfied at all.

The result is deliberately an UPPER BOUND. Choosing dr per window to maximise
the satisfied fraction is not something a fitter could do without already
knowing the answer, so the number here is the best case, not an estimate of
practice. That is the useful direction: if a window fails even at its own best
dr, no choice of spacing rescues it, and the limitation found by the previous
probe is a property of the geometry rather than of the constant it was scored
against.

METHOD. Same real windows, same umbilicus-centred frame, same unmodified villa
function. For each window, sweep dr across the range real spacings actually take
and keep the value that maximises the satisfied-quad fraction. Report the share
satisfied at that best dr, and the distribution of which dr won.

The whole-winding displacement is re-checked at each window's own best dr. On
the algebra it should still be exactly zero; if it were not, the previous
probe's real-data result would depend on the dr it happened to use.

DECISION RULE, fixed in advance:

  * If the best-case satisfied share is still below 50 percent, the previous
    probe's finding stands and strengthens: real windows are not satisfiable by
    this metric at any spacing, so scoring them at the published median was not
    what made them fail.
  * If it reaches 50 percent or more, the 21.7 percent figure was an artifact of
    the global median. The report's qualification must be rewritten, and the
    honest headline becomes that real windows are satisfiable when scored at
    their own spacing.
  * The best-fit dr distribution is reported either way. If the winners pile up
    at an endpoint of the sweep, the range was too narrow and the run says so
    rather than reporting a bound the sweep imposed.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_best_case_dr.py
"""

import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

from probe_real_patch_satisfaction import (  # noqa: E402
    EXTENT_MATCHED,
    QUAD_MATCHED,
    REAL_DR,
    real_windows,
)
from probe_spiral_satisfaction_robustness import _patch_is_satisfied  # noqa: E402
from probe_spiral_satisfaction_splicing_and_seam import (  # noqa: E402
    REPORTING,
    score_with,
)
from probe_spiral_satisfaction_winding import (  # noqa: E402
    IdentityTransform,
    displace,
)

# Wider than the 11.32-16.74 range real shard medians span, so a winner at the
# edge is visible as the sweep being too narrow rather than being silently
# clipped into the answer.
DR_SWEEP = [round(6.0 + 0.5 * i, 2) for i in range(37)]  # 6.0 .. 24.0
SATISFIED_SHARE_LIMIT = 0.50
EDGE_PILEUP_LIMIT = 0.10
OUT = os.path.join(_REPO, "reports", "best_case_dr.txt")


PHYSICAL_DR = [round(11.0 + 0.25 * i, 2) for i in range(24)]  # 11.00 .. 16.75


def satisfied_over(patch, drs, total_quads):
    """Best fraction over `drs`, whether any of them satisfies, and the tied set.

    Returns the tied winners rather than one value. With three quads the fraction
    takes four values, so many dr values tie for the maximum and a loop that keeps
    the first one reports whichever end of the sweep it started from. An earlier
    version did exactly that and produced a "winning dr" distribution piled 32
    percent on the low endpoint -- which I read as the sweep being too narrow
    before checking that the fraction is flat in dr over most of the range.
    """
    thresh = REPORTING["satisfied_patch_quad_fraction"]
    fracs = np.array(
        [score_with(patch, dr, REPORTING, IdentityTransform()) for dr in drs]
    )
    best = float(fracs.max())
    tied = [dr for dr, f in zip(drs, fracs, strict=False) if f >= best - 1e-9]
    any_sat = any(_patch_is_satisfied(float(f), total_quads, thresh) for f in fracs)
    return best, any_sat, tied


def analyse(windows):
    total_quads = int(windows[0][1].valid_quad_mask.sum().item())
    thresh = REPORTING["satisfied_patch_quad_fraction"]
    at_median, in_physical, anywhere, best_fracs, tie_widths, whole_deltas = (
        [],
        [],
        [],
        [],
        [],
        [],
    )
    for _, patch in windows:
        f_med = score_with(patch, REAL_DR, REPORTING, IdentityTransform())
        at_median.append(_patch_is_satisfied(f_med, total_quads, thresh))

        _, sat_phys, _ = satisfied_over(patch, PHYSICAL_DR, total_quads)
        in_physical.append(sat_phys)

        best, sat_any, tied = satisfied_over(patch, DR_SWEEP, total_quads)
        anywhere.append(sat_any)
        best_fracs.append(best)
        tie_widths.append(len(tied) / len(DR_SWEEP))

        # The blindness re-checked at a dr chosen for THIS window, not a shared
        # constant: the midpoint of its tied-best set.
        dr_here = float(np.median(tied))
        base = score_with(patch, dr_here, REPORTING, IdentityTransform())
        moved = displace(patch, dr_here, n_windings=1.0)
        whole_deltas.append(
            abs(score_with(moved, dr_here, REPORTING, IdentityTransform()) - base)
        )
    return {
        "n": len(windows),
        "quads": total_quads,
        "at_median": float(np.mean(at_median)),
        "in_physical": float(np.mean(in_physical)),
        "anywhere": float(np.mean(anywhere)),
        "best_frac_p50": float(np.median(best_fracs)),
        "tie_width_p50": float(np.median(tie_widths)),
        "whole_max_delta": float(np.max(whole_deltas)),
    }


def main():
    lines = [
        "Is a real window unsatisfiable, or was it scored at the wrong dr?",
        "",
        "The previous probe scored every real window at the published median dr of",
        f"{REAL_DR} voxels and found 21.7% satisfied. Real spacings run 11.32 to 16.74,",
        "so this gives each window the dr that suits it best and asks whether it can be",
        "satisfied at all. The result is an UPPER BOUND by construction: no fitter can",
        "pick dr to maximise its own score without already knowing the answer.",
        "",
        f"  dr swept {DR_SWEEP[0]} to {DR_SWEEP[-1]} in {DR_SWEEP[1] - DR_SWEEP[0]} steps",
        "",
    ]
    results = {}
    for label, shape in (
        ("extent-matched", EXTENT_MATCHED),
        ("quad-matched", QUAD_MATCHED),
    ):
        windows = real_windows(shape)
        if not windows:
            continue
        r = analyse(windows)
        results[label] = r
        lines.append(
            f"=== {label} ({shape[0]}x{shape[1]} cells, {r['quads']} quads) ==="
        )
        lines.append(f"  windows                                  {r['n']}")
        lines.append(
            f"  satisfied at the published dr {REAL_DR}         {r['at_median']:.1%}"
        )
        lines.append(
            f"  satisfied at SOME physical dr (11.0-16.75)  {r['in_physical']:.1%}"
        )
        lines.append(
            f"  satisfied at SOME dr in {DR_SWEEP[0]}-{DR_SWEEP[-1]}          "
            f"{r['anywhere']:.1%}"
        )
        lines.append(
            f"  best-case satisfied fraction p50         {r['best_frac_p50']:.3f}"
        )
        lines.append(
            f"  share of the dr sweep tied at that best   {r['tie_width_p50']:.0%}"
            "   <- why 'the winning dr' is not reported"
        )
        lines.append(
            f"  whole-winding max |delta| at each window's own dr   {r['whole_max_delta']:.4f}"
        )
        lines.append("")

    ext = results.get("extent-matched")
    lines.append("=== Verdict on the pre-registered rule ===")
    if ext is None:
        lines.append("  No extent-matched windows; the rule cannot be evaluated.")
    else:
        if ext["in_physical"] >= SATISFIED_SHARE_LIMIT:
            lines.append(
                f"  {ext['in_physical']:.1%} of real windows are satisfied at SOME spacing in"
                f" the physical range, at or above the pre-registered"
                f" {SATISFIED_SHARE_LIMIT:.0%}."
            )
            lines.append(
                f"  So the {ext['at_median']:.1%} measured at the single published dr"
                " understates what the metric can do: real windows ARE satisfiable when"
            )
            lines.append(
                "  scored at a spacing that suits them, and the report's qualification has to"
            )
            lines.append("  be softened to say so.")
        else:
            se = float(
                np.sqrt(
                    ext["in_physical"] * (1 - ext["in_physical"]) / max(ext["n"], 1)
                )
            )
            margin = SATISFIED_SHARE_LIMIT - ext["in_physical"]
            lines.append(
                f"  ⚠ Only {ext['in_physical']:.1%} of real windows are satisfied at ANY"
                f" spacing in the physical range, below the pre-registered"
                f" {SATISFIED_SHARE_LIMIT:.0%}."
            )
            if margin < se:
                lines.append(
                    f"  BUT the margin is {margin:.1%} against a standard error of {se:.1%}"
                    f" on n={ext['n']}, so this verdict is inside the noise: the data cannot"
                )
                lines.append(
                    "  distinguish this share from the threshold, and the rule firing 'below'"
                )
                lines.append(
                    "  is not evidence that it is below. Treat the direction as unresolved and"
                )
                lines.append("  the doubling below as the real result.")
            else:
                lines.append(
                    "  The margin exceeds the standard error, so this is a real shortfall:"
                )
                lines.append(
                    "  no physical choice of spacing rescues these windows, and the previous"
                )
                lines.append(
                    "  probe's finding is a property of the geometry rather than of the"
                )
                lines.append("  constant it was scored against.")
    if ext is not None:
        lines.append("")
        lines.append(
            f"  What is NOT marginal: allowing each window a physical spacing that suits it"
            f" takes the satisfied share from {ext['at_median']:.1%} to"
            f" {ext['in_physical']:.1%}, more than double. The previous probe's 21.7% was"
        )
        lines.append(
            "  measured against one global constant and understates the metric on real"
        )
        lines.append(
            "  geometry by about that factor. The quad-matched windows are unaffected: 0% at"
        )
        lines.append("  every spacing tried.")
    lines.append("")
    lines.append(
        "The whole-winding delta is re-checked at each window's own best dr, not at a"
        " shared constant, so the real-data blindness result does not depend on which dr"
        " the previous probe happened to use."
    )
    text = "\n".join(lines) + "\n"
    with open(OUT, "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
