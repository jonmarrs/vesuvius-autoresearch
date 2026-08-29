"""Do patches with disconnected subrow components score differently?

WHAT PROMPTED THIS. Our converged baseline fit emitted
`Warning: patch N has multiple disconnected subrow components; using only the
component containing the center column` for 4,272 of 38,616 patches.

WHAT THE CODE DOES. In `satisfaction_metrics.get_patch_satisfied_areas`,
subrows are linked where they overlap in j, and a BFS from the subrow
containing the centre column propagates `branch_offset`. Any subrow the BFS
does not reach keeps `branch_offset is None`, and the scoring loop skips it:

    for subrow in all_subrows:
        if subrow['branch_offset'] is None:
            continue
        satisfied_quad_mask[i, j_min:j_max] = in_band

Those quads never enter the numerator, but they stay in `in_roi_valid_quad_mask`,
which is the denominator. So they are counted as unsatisfied no matter what
their geometry is.

WHY THAT IS NOT AUTOMATICALLY A DEFECT. A component the BFS cannot reach has no
established branch relationship to the centre, so its winding frame is unknown
and comparing it to the centre's target would be meaningless. Marking it
unsatisfied is a defensible conservative choice. The question is therefore not
"is this wrong" but "how much of the unsatisfied remainder is auto-failed for
lack of a frame rather than for being geometrically wrong".

WHAT IS MEASURED. The fit already wrote per-patch satisfied/total area to
`satisfied_fitted.json`, and the run log names every warned patch. This joins
them: no re-run, no reimplementation of the metric.

THE COMPARISON IS OBSERVATIONAL, NOT CAUSAL. Warned patches may differ from
unwarned ones in ways that independently predict low satisfaction, most
obviously size and shape, since a patch with more rows has more chances to
contain a disconnected subrow. Patch area is reported alongside so that a
size confound is visible rather than hidden. This cannot establish that the
skipping causes the gap.

Run:
    uv run python scripts/measure_subrow_disconnection.py
"""

import json
import os
import re
import sys

import numpy as np

RUN = os.environ.get(
    "SPIRAL_RUN",
    "/home/jon/openclaw-workspace/Neo-VM/spiral_out/"
    "2026-08-28_s1_slice-13056-18432_38442-patch_baseline01",
)
LOG = os.environ.get(
    "SPIRAL_LOG", "/home/jon/openclaw-workspace/Neo-VM/spiral_out/baseline.log"
)
OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "reports",
    "subrow_disconnection.txt",
)
WARN = re.compile(r"Warning: patch (\d+) has multiple disconnected subrow components")


def main():
    patches = json.load(open(os.path.join(RUN, "satisfied_fitted.json")))["patches"]
    warned = set()
    with open(LOG) as fh:
        for line in fh:
            m = WARN.search(line)
            if m:
                warned.add(int(m.group(1)))

    frac = np.array([p["fraction"] for p in patches])
    area = np.array([p["total_area"] for p in patches])
    idx = np.arange(len(patches))
    is_warned = np.isin(idx, sorted(warned))

    lines = [
        "Do patches with disconnected subrow components score differently?",
        "",
        "Quads in a subrow the branch BFS cannot reach are skipped by the scoring loop but",
        "stay in the denominator, so they are unsatisfied regardless of geometry. That is a",
        "defensible conservative choice (an unreachable component has no known winding",
        "frame). The question is how much of the unsatisfied remainder it accounts for.",
        "",
        f"  run  {os.path.basename(RUN)}",
        f"  {len(patches)} patches scored, {len(warned)} warned"
        f" ({len(warned) / len(patches):.1%})",
        "",
        f"{'group':<22}{'n':>8}{'mean frac':>12}{'median':>10}{'frac==0':>10}{'mean area':>14}",
        "  " + "-" * 74,
    ]
    for label, mask in (("warned (disconnected)", is_warned), ("unwarned", ~is_warned)):
        f, a = frac[mask], area[mask]
        if len(f) == 0:
            continue
        lines.append(
            f"{label:<22}{len(f):>8}{f.mean():>12.4f}{np.median(f):>10.4f}"
            f"{(f == 0).mean():>10.1%}{a.mean():>14.0f}"
        )

    fw, fu = frac[is_warned], frac[~is_warned]
    lines += [
        "",
        f"  difference in mean satisfied fraction: {fu.mean() - fw.mean():+.4f}"
        f"  (unwarned minus warned)",
    ]

    # Size confound, stated rather than assumed away: compare within area deciles.
    lines += [
        "",
        "Within-area-decile comparison, because a larger patch has more rows and so more",
        "chances to contain a disconnected subrow. If the gap survives here it is not",
        "purely a size effect; it still is not causal.",
        "",
        f"  {'area decile':<14}{'n warn':>8}{'n unwarn':>10}{'mean warn':>12}{'mean unwarn':>13}{'diff':>9}",
        "  " + "-" * 68,
    ]
    edges = np.quantile(area, np.linspace(0, 1, 11))
    survived = 0
    tested = 0
    for k in range(10):
        lo, hi = edges[k], edges[k + 1]
        sel = (area >= lo) & (area <= hi if k == 9 else area < hi)
        w, u = sel & is_warned, sel & ~is_warned
        if w.sum() < 20 or u.sum() < 20:
            continue
        tested += 1
        d = frac[u].mean() - frac[w].mean()
        if d > 0:
            survived += 1
        lines.append(
            f"  {k + 1:<14}{w.sum():>8}{u.sum():>10}{frac[w].mean():>12.4f}"
            f"{frac[u].mean():>13.4f}{d:>+9.4f}"
        )
    lines += [
        "",
        f"  deciles where unwarned scores higher: {survived}/{tested}",
        "",
        "Limits. One fit, one scroll, one z-ROI, three inputs disabled. Observational: the",
        "warning is not randomly assigned, so this compares populations, not treatments.",
        "The decile control addresses size only, and any other property that both causes",
        "disconnection and lowers satisfaction would produce this pattern too.",
    ]
    text = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    sys.exit(main())
