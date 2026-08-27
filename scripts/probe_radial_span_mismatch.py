"""How many windings does a real window span, and how many does the test patch?

Diagnostic, not a hypothesis test: there is no decision rule here because the
quantity is measured directly rather than inferred, and the answer is a property
of the published data rather than of anything this project chose.

WHY. `reports/best_case_dr.txt` found that quad-matched real windows are
satisfied at 0.0 percent of spacings tried, and no choice of dr rescues them.
The obvious candidate explanation is that villa's metric snaps a patch to the
NEAREST INTEGER winding, so a window whose points straddle more than one winding
contains points belonging to different windings and cannot be satisfied at any
spacing. That is checkable directly, by measuring radial span.

It also bears on a claim this report has carried since section 9: that a
3x4-cell window is "comparable to the synthetic patch". That has already been
corrected once, when the quad count turned out to differ by 55x at matched
extent. Radial span is a third axis on which the two can fail to match, and it
is the axis the satisfaction metric actually cares about.

WHAT THIS IS NOT. The "real windows" here are windows of published traced
surfaces (`verified_patches` tifxyz grids), NOT villa spiral-fit patches. No
fitted spiral checkpoint is published, so villa's own patches cannot be
measured, and they may well be small sub-winding objects that look nothing like
these. What this establishes is narrower and still worth knowing: what the
published data can and cannot be used to build. A test patch that no available
real window resembles is a test patch whose representativeness rests on
something other than measurement.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_radial_span_mismatch.py
"""

import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

from probe_correlated_scatter import WINDING  # noqa: E402
from probe_real_patch_satisfaction import REAL_DR, real_windows  # noqa: E402
from probe_spiral_satisfaction_winding import build_synthetic_patch  # noqa: E402

SHAPES = [(2, 2), (2, 4), (3, 4), (4, 6), (6, 8), (12, 16)]
N_WINDOWS = 40
OUT = os.path.join(_REPO, "reports", "radial_span_mismatch.txt")


def radial_span(patch):
    r = np.sqrt(patch.zyxs[..., 1].numpy() ** 2 + patch.zyxs[..., 2].numpy() ** 2)
    return float(r.max() - r.min())


def main():
    synth = build_synthetic_patch(dr=REAL_DR, winding=WINDING)
    s_span = radial_span(synth)

    rows = []
    for shape in SHAPES:
        windows = real_windows(shape, n_windows=N_WINDOWS)
        if not windows:
            continue
        spans = np.array([radial_span(p) for _, p in windows])
        rows.append((shape, len(windows), float(np.median(spans))))

    lines = [
        "How many windings does a real window span, and how many does the test patch?",
        "",
        "villa's metric snaps a patch to the NEAREST INTEGER winding. A window whose",
        "points straddle more than one winding contains points belonging to different",
        "windings, so it cannot be satisfied at any spacing. Spans below are at dr =",
        f"{REAL_DR} voxels.",
        "",
        "   window                  radial span (vox)   in windings",
        "  " + "-" * 62,
        f"   synthetic 12x16 cells   {s_span:16.2f}   {s_span / REAL_DR:11.3f}",
        "",
    ]
    for shape, n, span in rows:
        lines.append(
            f"   real {shape[0]:2d}x{shape[1]:<2d} cells (n={n:2d})   {span:16.2f}"
            f"   {span / REAL_DR:11.2f}"
        )
    lines.append("")

    smallest = min(rows, key=lambda r: r[2]) if rows else None
    if smallest is not None:
        ratio = smallest[2] / s_span
        lines.append(
            f"  The smallest real window available, {smallest[0][0]}x{smallest[0][1]} cells,"
            f" spans {smallest[2] / REAL_DR:.2f} windings."
        )
        lines.append(
            f"  The synthetic test patch spans {s_span / REAL_DR:.3f}. That is a factor of"
            f" {ratio:.1f}, and it is not a"
        )
        lines.append(
            "  sampling choice: real traced surfaces step about 20 voxels per grid cell, so"
        )
        lines.append(
            "  a two-by-two window is the smallest object that has any quads at all."
        )
        lines.append("")
        lines.append(
            "  So no window of the published traced surfaces resembles the test patch on the"
        )
        lines.append(
            "  axis the satisfaction metric cares about. That explains the 0% satisfied at"
        )
        lines.append(
            "  the quad-matched scale, which spans about"
            f" {[r for r in rows if r[0] == (12, 16)][0][2] / REAL_DR:.1f} windings, without"
            " needing any"
        )
        lines.append("  appeal to noise or to the choice of dr.")
    lines.append("")
    lines.append(
        "Read this narrowly. These are windows of published traced surfaces, not villa"
        " spiral-fit patches, and no fitted spiral checkpoint is published, so villa's own"
        " patches cannot be measured here. They may be small sub-winding objects that look"
        " nothing like these. What is established is what the published data can be used to"
        " build, and that the report's description of a 3x4-cell window as comparable to the"
        " synthetic patch is wrong on this axis by a factor of"
        f" {[r for r in rows if r[0] == (3, 4)][0][2] / s_span:.0f}."
    )
    text = "\n".join(lines) + "\n"
    with open(OUT, "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
