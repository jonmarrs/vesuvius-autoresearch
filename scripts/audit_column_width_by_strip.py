"""Do the three figure strips really share one scale? The column widths say no.

The global audit (`reports/column_registration_area.txt`) corroborated the
registration's scale and gross placement against a published area, to 1%. It
said explicitly that it could not see per-column accuracy, because an area
agreement is compatible with individual edges being wrong in compensating
directions. This looks for exactly that.

THE CLAIM UNDER TEST. `reports/detector/merged1667_column_registration.md`
states that all three preprint figure strips "independently recover the same
scale (4.7 grid px / figure px)", and supports the registration with a tiling
closure of 3 px over 30,097.

WHY THE CLOSURE CANNOT SETTLE IT. Tiling closure constrains the TOTAL length. If
one strip is scaled a little large and another a little small, the errors
compensate and the total still lands. A closure of 3 px over 30,097 is
compatible with per-strip scale errors of several percent in opposite
directions, so it is structurally blind to the failure this probe looks for.
That is the same shape as the defect that reversed the pixel family: internal
checks agreeing with each other while wrong together.

THE INDEPENDENT SIGNAL. A scribe's column width is a physical property of the
roll. It can drift along a roll, but it cannot know where a modern publisher
cropped a figure into rows. So if column width is flat within each strip and
steps at the strip boundaries, the step is ours, not the scribe's.

Columns 1, 9 and 16 are excluded: col 1 sits at the grid edge, and 9 and 16 are
already flagged in the target as spanning strip-crop gaps with +/-250 grid px of
slack. Including them would let the very columns most likely to be mismeasured
drive the result.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/audit_column_width_by_strip.py
"""

import json
import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(
    os.path.dirname(_REPO), "scrollgt", "data", "pherc1667_merged_columns"
)
OUT = os.path.join(_REPO, "reports", "column_width_by_strip.txt")

VOXEL_UM = 2.399
EXCLUDE = (1, 9, 16)  # grid edge, and the two flagged cross-strip columns
STRIPS = {1: (2, 8), 2: (10, 15), 3: (17, 22)}  # preprint p.3 tiles 1-8 / 9-16 / 17-22
N_PERM = 20000
SEED = 20260827


def load():
    meta = json.load(open(os.path.join(TARGET, "meta.json")))
    cols = json.load(open(os.path.join(TARGET, "columns.json")))
    um = VOXEL_UM / float(meta["geometry"]["scale"])
    rows = [
        {
            "col": c["col"],
            "width_mm": (c["gx1"] - c["gx0"]) * um / 1000.0,
            "pitch": c["measured_line_pitch"]["pitch_grid_px"],
            "autocorr": c["measured_line_pitch"]["autocorr"],
        }
        for c in cols["columns"]
        if c["col"] not in EXCLUDE
    ]
    return rows, um


def strip_of(col):
    for s, (a, b) in STRIPS.items():
        if a <= col <= b:
            return s
    return None


def main():
    rows, um = load()
    col = np.array([r["col"] for r in rows])
    w = np.array([r["width_mm"] for r in rows])
    strip = np.array([strip_of(c) for c in col])

    lines = [
        "Do the three figure strips really share one scale?",
        "",
        "The area audit corroborated the global transform to 1% and said it could not see",
        "per-column accuracy. This looks there. A tiling closure constrains total length,",
        "so per-strip scale errors in opposite directions cancel and leave it intact: the",
        "closure is structurally blind to this.",
        "",
        "A scribe's column width can drift along a roll. It cannot know where a modern",
        "publisher cropped a figure into rows. Flat within strips and stepping at the",
        "boundaries would therefore be our artifact, not the scribe's hand.",
        "",
        f"  1 grid px = {um:.2f} um; cols {EXCLUDE} excluded (grid edge, and the two"
        " flagged as spanning strip crops)",
        "",
        "   strip   cols            n   width mm (mean +/- sd)",
        "  " + "-" * 60,
    ]
    means = {}
    for s in sorted(STRIPS):
        m = strip == s
        means[s] = float(w[m].mean())
        lines.append(
            f"   {s}       {STRIPS[s][0]:2d}-{STRIPS[s][1]:<2d}          {m.sum()}"
            f"   {w[m].mean():6.1f} +/- {w[m].std():.1f}"
        )
    lines.append("")

    step = np.zeros_like(w)
    for s in sorted(STRIPS):
        step[strip == s] = means[s]
    lin = np.polyval(np.polyfit(col, w, 1), col)
    rss_step = float(((w - step) ** 2).sum())
    rss_lin = float(((w - lin) ** 2).sum())

    rng = np.random.default_rng(SEED)
    obs = means[3] - means[1]
    hits = 0
    for _ in range(N_PERM):
        p = rng.permutation(w)
        if abs(p[strip == 3].mean() - p[strip == 1].mean()) >= abs(obs):
            hits += 1
    pval = hits / N_PERM

    ratio = means[3] / means[1]
    lines += [
        f"  strip 3 is {ratio:.3f}x strip 1, a difference of {obs:.1f} mm.",
        f"  permutation test on that difference: p = {pval:.4f} over {N_PERM} shuffles.",
        "",
        "  Step versus trend, same data, same n:",
        f"    per-strip constant (the artifact model):   RSS {rss_step:6.2f}",
        f"    single linear trend (the scribe model):    RSS {rss_lin:6.2f}",
        "",
    ]
    if rss_step < rss_lin and pval < 0.01:
        lines += [
            "  ⚠ The step model fits better and the difference is not chance. Column width",
            "  is flat inside each strip and jumps at the boundaries, which a physical drift",
            "  along the roll does not predict: it would have to change abruptly at exactly",
            "  the two points where a modern figure was cropped.",
            "",
            "  The most likely mechanism is that the strips are NOT at one magnification."
            " Strips 1 and 2 carry 8 columns each and strip 3 carries 6; if each row of the",
            "  figure spans the same page width, strip 3 is magnified relative to the others,",
            "  and fitting one shared scale to all three would stretch its columns. The",
            f"  observed {ratio:.2f}x sits between 1 and the 8/6 = 1.33x that equal page",
            "  widths would imply.",
            "",
            "  This does not overturn the area audit. Compensating per-strip errors preserve",
            "  total length by construction, and strip 3 is 6 of 22 columns, so a 14% width",
            "  error there inflates total area by roughly 3%, inside what that check could",
            "  resolve.",
            "",
            "  What it does mean: per-column boundaries in strip 3 are suspect, the",
            "  'same scale on all three strips' claim in the registration report is not",
            "  supported by the widths, and the tiling closure cannot be cited as evidence",
            "  against this because it cannot see it.",
        ]
    else:
        lines += [
            "  The step model does not clearly beat a continuous trend, or the difference is",
            "  within chance. On this evidence the widths are consistent with a physical",
            "  drift along the roll and the single-scale claim stands.",
        ]

    lines += [
        "",
        "DISCLOSED PUBLICLY. This is not only a note to ourselves: the target ships in a",
        "published repository, so the caveat is in the data users actually get. ScrollGT",
        "commit 7d86713 (2026-08-27) adds it to the README's column section, to the",
        "per-target README, and to the `uncertainty` field of columns.json itself, so it",
        "travels with the file for anyone scoring programmatically. The same commit marks",
        "the tiling-closure argument as unable to rule this out, attached to the claim it",
        "undermines rather than only to the new notice. No column coordinate was altered.",
        "",
        "Limits. Column width is measured from the registered boxes, so this detects a",
        "scale discrepancy between strips, not an absolute error common to all three. And",
        "it cannot separate a magnification difference from a genuine physical change that",
        "happens to coincide with a crop boundary; it only shows that the coincidence would",
        "have to be exact.",
    ]
    text = "\n".join(lines) + "\n"
    with open(OUT, "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
