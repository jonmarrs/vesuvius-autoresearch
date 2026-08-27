"""Does the registered column geometry reproduce the published writing-surface area?

The registration's own evidence is internal: three figure strips fitted the same
way agreeing with each other, and a tiling closure. If the fitting procedure were
systematically wrong, all of that could agree and all of it be wrong together.

The obvious external check is circular and is deliberately NOT used here. The
registration was fitted by template matching onto the valid mask, so
"gutters land in the wrap-damage notches" is a consequence of the fit.

This uses a quantity the fit never saw: the published reading reports
approximately 860 cm2 of preserved writing surface across 22 columns. Summing
the valid mask inside the registered boxes, converted through the scan's own
voxel size, is independent of the strips entirely.

Area is quadratic in the scale, which is what makes it a tight constraint rather
than a loose sanity check.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/audit_column_registration_area.py
"""

import json
import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(
    os.path.dirname(_REPO), "scrollgt", "data", "pherc1667_merged_columns"
)
OUT = os.path.join(_REPO, "reports", "column_registration_area.txt")

VOXEL_UM = 2.399  # from the volume name: 20251217075048-2.399um-0.2m-78keV-masked
PUBLISHED_CM2 = 860.0  # scrollprize.org/firstscroll: ~860 cm2 over 22 columns
PUBLISHED_COLUMNS = 22


def load():
    meta = json.load(open(os.path.join(TARGET, "meta.json")))
    cols = json.load(open(os.path.join(TARGET, "columns.json")))
    shape = tuple(meta["geometry"]["grid_shape"])
    im = Image.open(os.path.join(TARGET, "valid_mask.png")).convert("L")
    if im.size != (shape[1], shape[0]):
        im = im.resize((shape[1], shape[0]), Image.NEAREST)
    return meta, cols, np.array(im) > 0, shape


def um_per_grid_px(meta):
    """Grid pixel size in microns, from the scan's voxel size and the grid scale."""
    return VOXEL_UM / float(meta["geometry"]["scale"])


def areas(meta, cols, valid):
    um = um_per_grid_px(meta)
    cm2_per_px = (um * 1e-4) ** 2
    entries = cols["columns"]
    inside = sum(int(valid[:, int(c["gx0"]) : int(c["gx1"])].sum()) for c in entries)
    return {
        "um_per_grid_px": um,
        "n_columns": len(entries),
        "whole_grid_cm2": float(valid.sum()) * cm2_per_px,
        "in_columns_cm2": float(inside) * cm2_per_px,
    }


def main():
    meta, cols, valid, shape = load()
    a = areas(meta, cols, valid)
    ratio = a["in_columns_cm2"] / PUBLISHED_CM2

    lines = [
        "Does the registered column geometry reproduce the published area?",
        "",
        "The registration's own checks are internal: three strips fitted the same way",
        "agreeing, and a tiling closure. The mask-correspondence check that looks external",
        "is circular, because the registration was FITTED onto that mask. This uses the",
        "published writing-surface area, which the fit never saw.",
        "",
        f"  voxel size {VOXEL_UM} um, grid scale {meta['geometry']['scale']}"
        f"  ->  1 grid px = {a['um_per_grid_px']:.2f} um",
        f"  grid {shape[0]} x {shape[1]}, {a['n_columns']} registered columns"
        f" (published: {PUBLISHED_COLUMNS})",
        "",
        f"  valid mask, whole grid             {a['whole_grid_cm2']:7.0f} cm2",
        f"  valid mask, inside the columns     {a['in_columns_cm2']:7.0f} cm2",
        f"  published preserved writing surface{PUBLISHED_CM2:8.0f} cm2",
        f"  ratio                              {ratio:7.2f}x",
        "",
        "Area is quadratic in the scale, so this is a tight constraint:",
        "",
        "   scale error   implied area   ratio to published",
    ]
    for err in (0.80, 0.90, 0.95, 1.00, 1.05, 1.10, 1.20):
        A = a["in_columns_cm2"] * err**2
        lines.append(
            f"   {(err - 1) * 100:+6.0f}%      {A:8.0f} cm2   {A / PUBLISHED_CM2:8.2f}x"
        )
    tol = 100 * (np.sqrt(1.10) - 1)
    lines += [
        "",
        f"  Landing within 10% of the published area requires the scale to be right to"
        f" about {tol:.1f}%.",
        "",
        "What this does not establish: per-column boundary accuracy. An area agreement is",
        "compatible with individual edges being off in compensating directions, and the",
        "registration report already flags cols 9 and 16 as spanning strip-crop gaps with",
        "bbox edges +/-250 grid px. This is about the global transform.",
        "",
        "Exploratory, not pre-registered: the numbers were computed to see whether they",
        "were plausible. The strength is in the size of the agreement, not in a threshold",
        "chosen in advance.",
    ]
    text = "\n".join(lines) + "\n"
    with open(OUT, "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
