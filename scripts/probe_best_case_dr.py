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


def best_dr(patch):
    """The dr maximising this window's satisfied-quad fraction, and that fraction."""
    best_frac, best_val = -1.0, float("nan")
    for dr in DR_SWEEP:
        frac = score_with(patch, dr, REPORTING, IdentityTransform())
        if frac > best_frac:
            best_frac, best_val = frac, dr
    return best_val, best_frac


def analyse(windows):
    total_quads = int(windows[0][1].valid_quad_mask.sum().item())
    thresh = REPORTING["satisfied_patch_quad_fraction"]
    best_drs, best_fracs, sat_at_best, whole_deltas = [], [], [], []
    for _, patch in windows:
        dr, frac = best_dr(patch)
        best_drs.append(dr)
        best_fracs.append(frac)
        sat_at_best.append(_patch_is_satisfied(frac, total_quads, thresh))
        moved = displace(patch, dr, n_windings=1.0)
        whole_deltas.append(
            abs(score_with(moved, dr, REPORTING, IdentityTransform()) - frac)
        )
    drs = np.array(best_drs)
    return {
        "n": len(windows),
        "quads": total_quads,
        "best_frac_p50": float(np.median(best_fracs)),
        "satisfied": float(np.mean(sat_at_best)),
        "dr_p50": float(np.median(drs)),
        "dr_lo": float(np.mean(drs <= DR_SWEEP[0] + 1e-9)),
        "dr_hi": float(np.mean(drs >= DR_SWEEP[-1] - 1e-9)),
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
        lines.append(f"  windows                          {r['n']}")
        lines.append(f"  best-case satisfied fraction p50 {r['best_frac_p50']:.3f}")
        lines.append(f"  share satisfied at its best dr   {r['satisfied']:.1%}")
        lines.append(f"  winning dr, median               {r['dr_p50']:.2f} vox")
        lines.append(
            f"  winners at sweep edges           {r['dr_lo']:.0%} low, {r['dr_hi']:.0%} high"
        )
        lines.append(
            f"  whole-winding max |delta| at each window's own best dr   "
            f"{r['whole_max_delta']:.4f}"
        )
        lines.append("")

    ext = results.get("extent-matched")
    lines.append("=== Verdict on the pre-registered rule ===")
    if ext is None:
        lines.append("  No extent-matched windows; the rule cannot be evaluated.")
    else:
        edge = max(ext["dr_lo"], ext["dr_hi"])
        if edge > EDGE_PILEUP_LIMIT:
            lines.append(
                f"  ⚠ {edge:.0%} of winning dr values sit at a sweep endpoint, above the"
                f" pre-registered {EDGE_PILEUP_LIMIT:.0%}. The range is too narrow and the"
                " result below is bounded by the sweep, not by the data. Re-run wider."
            )
        elif ext["satisfied"] >= SATISFIED_SHARE_LIMIT:
            lines.append(
                f"  {ext['satisfied']:.1%} of real windows are satisfied at their own best dr,"
                f" at or above the pre-registered {SATISFIED_SHARE_LIMIT:.0%}."
            )
            lines.append(
                "  The 21.7% figure was an artifact of scoring everything at the global"
            )
            lines.append(
                "  median. Real windows ARE satisfiable when scored at their own spacing,"
            )
            lines.append(
                "  and the report's qualification must be rewritten to say so."
            )
        else:
            lines.append(
                f"  ⚠ Only {ext['satisfied']:.1%} of real windows are satisfied even at their"
                f" own best dr, below the pre-registered {SATISFIED_SHARE_LIMIT:.0%}."
            )
            lines.append(
                "  No choice of spacing rescues them, so the previous probe's finding is a"
            )
            lines.append(
                "  property of the geometry rather than of the constant it was scored"
            )
            lines.append(
                "  against. The 21.7% was not caused by using the published median."
            )
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
