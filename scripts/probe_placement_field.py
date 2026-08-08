#!/usr/bin/env python3
"""Is a target's placement error a uniform shift, or does it vary across the region?

This distinguishes the two remaining explanations for the residual offsets:

  * **uniform** translation  -> a constant convention bug, worth hunting and fixable;
  * **spatially varying**    -> the cross-scan surface disagreement (the 2023 and 2026
    segmentations are different surfaces), which is non-rigid and cannot be fixed by any
    global transform. See reports/detector/registration_offset_2026-08-07.md.

Method: split the region into tiles, run `placement_peak` per tile, and fit a plane to the
resulting offset field. A pure translation gives a flat field (small residual scatter, near
zero gradient). A scale/stretch error gives a strong linear gradient. Non-rigid surface
disagreement gives a large scatter that a plane does not explain.

    uv run python scripts/probe_placement_field.py
    uv run python scripts/probe_placement_field.py --tile 512 --max-shift 96
"""

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data.register import placement_peak

Image.MAX_IMAGE_PIXELS = None

TARGETS = [
    (
        "train-exposed 20230702185753",
        "local_data/sota_registration/orig/registered_label_l2region.png",
        "local_data/sota_xscroll/scroll1_20230702185753_y4000_x2500/"
        "scroll1_20230702185753_y4000_x2500_inklabels.png",
    ),
    (
        "held-out 20231210121321",
        "local_data/sota_registration/heldout/registered_label_l2region.png",
        "local_data/sota_distill/20231210121321_y4000_x2500/"
        "20231210121321_y4000_x2500_inklabels.png",
    ),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tile", type=int, default=768)
    ap.add_argument("--max-shift", type=int, default=96)
    ap.add_argument(
        "--min-ink",
        type=float,
        default=0.04,
        help="skip tiles with less than this ink fraction in either image",
    )
    ap.add_argument("--json-out")
    args = ap.parse_args()

    out = []
    for name, lab_path, ref_path in TARGETS:
        if not (os.path.exists(lab_path) and os.path.exists(ref_path)):
            print(f"{name}: inputs missing, skipped")
            continue
        lab = np.array(Image.open(lab_path))
        ref = np.array(Image.open(ref_path))
        lab_m, ref_m = lab > 127, ref > 127
        H, W = lab.shape
        T, M = args.tile, args.max_shift
        step = T
        rows = []
        for y in range(M, H - T - M + 1, step):
            for x in range(M, W - T - M + 1, step):
                a = lab_m[y : y + T, x : x + T]
                # reference tile is grown by the search margin so shifts stay in-bounds
                if a.mean() < args.min_ink:
                    continue
                # compare the tile against its co-located reference tile; placement_peak's
                # own interior margin does the searching
                bb = ref_m[y : y + T, x : x + T]
                if bb.mean() < args.min_ink:
                    continue
                dy, dx, d0, dpk = placement_peak(a, bb, max_shift=M, coarse=2, refine=4)
                rows.append((y + T // 2, x + T // 2, dy, dx, d0, dpk))

        if len(rows) < 6:
            print(f"{name}: only {len(rows)} usable tiles, skipping fit")
            continue
        arr = np.array(rows, float)
        cy, cx, dy, dx = arr[:, 0], arr[:, 1], arr[:, 2], arr[:, 3]

        print(f"\n{name}   {len(rows)} tiles of {T}px")
        print(
            f"  dy: mean {dy.mean():+7.1f}  sd {dy.std():6.1f}  "
            f"range [{dy.min():+.0f}, {dy.max():+.0f}]"
        )
        print(
            f"  dx: mean {dx.mean():+7.1f}  sd {dx.std():6.1f}  "
            f"range [{dx.min():+.0f}, {dx.max():+.0f}]"
        )

        # plane fit: d = a + b*row + c*col. Strong gradient => scale error.
        A = np.c_[np.ones(len(arr)), cy, cx]
        fit = {}
        for comp, vals in (("dy", dy), ("dx", dx)):
            coef, *_ = np.linalg.lstsq(A, vals, rcond=None)
            resid = vals - A @ coef
            print(
                f"  {comp} plane: const {coef[0]:+.1f}  d/drow {coef[1] * 1000:+.2f}"
                f"  d/dcol {coef[2] * 1000:+.2f}  (px per 1000px)   "
                f"unexplained sd {resid.std():.1f}"
            )
            fit[comp] = {
                "const": coef[0],
                "d_drow_per1000": coef[1] * 1000,
                "d_dcol_per1000": coef[2] * 1000,
                "residual_sd": float(resid.std()),
            }

        uniform = max(dy.std(), dx.std()) < 8.0
        print(
            f"  => {'UNIFORM (constant offset -- look for a convention bug)' if uniform else 'VARIES ACROSS THE REGION (non-rigid; no global transform fixes it)'}"
        )
        out.append(
            {
                "target": name,
                "n_tiles": len(rows),
                "tile_px": T,
                "dy_mean": dy.mean(),
                "dx_mean": dx.mean(),
                "dy_sd": dy.std(),
                "dx_sd": dx.std(),
                "uniform": bool(uniform),
                "plane_fit": fit,
                "tiles": [
                    dict(
                        zip(
                            ("row", "col", "dy", "dx", "dice0", "dice_peak"),
                            r,
                            strict=False,
                        )
                    )
                    for r in rows
                ],
            }
        )

    if args.json_out and out:
        with open(args.json_out, "w") as f:
            json.dump(out, f, indent=2)
        print(f"\nwrote {args.json_out}")


if __name__ == "__main__":
    main()
