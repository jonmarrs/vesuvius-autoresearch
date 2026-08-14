#!/usr/bin/env python3
"""Is the registered ground truth actually placed correctly?

Motivation (2026-08-07): villa PR #1280 was closed with the objection that "the provided
ink registration example doesn't show the alignment working". The shipped visual
(`overlay_vs_canon.png`) paints GT over a *model prediction* that is itself near chance on
the held-out target, so it cannot show alignment either way. This probe replaces the
visual argument with a measurement.

Method: the registration is only correct if GT-vs-prediction agreement is **maximised at
zero shift**. So scan Dice over pure translations and report where the peak actually is.
The comparison surface is the distillation pipeline's own region-cropped teacher
(`local_data/sota_distill/<frag>/<frag>_inklabels.png`), which was produced by
`repro/sota_data/distill_prep.py` for exactly the target region -- using it keeps this
probe's own crop conventions out of the result.

Two things this probe deliberately does NOT do:
  * it does not use np.roll -- wrapped content would contaminate the score, so every
    shift is evaluated on a common interior crop (margin M);
  * it does not claim the peak offset is the physically correct placement. The peak is fit
    against a model output, so it localises *disagreement*, not truth. What it establishes
    is that GT and prediction do not agree where they are supposed to.

Interpretation: a peak far from (0, 0) means the two artifacts disagree by a systematic
translation. Which of them carries the error (register_run.py's obj/tifxyz bridge vs
distill_prep.py's `sy = th/lh` teacher crop) is a separate question this probe cannot
settle -- but any leaderboard comparing exactly these two artifacts is affected.

Usage:
    uv run python scripts/probe_registration_offset.py
    uv run python scripts/probe_registration_offset.py --margin 1000 --coarse 16
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

SCROLLGT_DATA = os.environ.get(
    "SCROLLGT_DATA",
    os.path.join(os.path.dirname(__file__), "..", "..", "scrollgt", "data"),
)
DISTILL_ROOT = "local_data/sota_distill"

# (scrollgt target dir, distill fragment id, role)
PAIRS = [
    ("scroll1_20230702185753", "20230702185753_y4000_x2500", "train-exposed"),
    ("scroll1_20231210121321", "20231210121321_y4000_x2500", "held-out flagship"),
]


def binary_stats(g, p):
    """Confusion-matrix metrics for a binary predictor.

    roc_auc here is (sensitivity + specificity) / 2, the AUC of a single-threshold
    predictor. It is NOT comparable to the threshold-swept AUC in the published
    leaderboard -- but it IS comparable between the two rows below, which is the point.
    """
    tp = int((g & p).sum())
    fp = int((~g & p).sum())
    fn = int((g & ~p).sum())
    tn = int((~g & ~p).sum())
    sens = tp / max(tp + fn, 1)
    spec = tn / max(tn + fp, 1)
    prec = tp / max(tp + fp, 1)
    return {
        "roc_auc": (sens + spec) / 2,
        "f1": 2 * prec * sens / max(prec + sens, 1e-9),
        "precision": prec,
        "recall": sens,
        "prevalence_lift": prec / max(float(g.mean()), 1e-9),
    }


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--margin",
        type=int,
        default=1000,
        help="search half-width AND edge crop, in level-2 px (default 1000). "
        "Too small and the peak clamps to the boundary and under-reports.",
    )
    ap.add_argument(
        "--coarse", type=int, default=16, help="coarse grid step (default 16)"
    )
    ap.add_argument("--json-out", help="write results here")
    args = ap.parse_args()

    results = []
    for gt_name, frag, role in PAIRS:
        gt_path = os.path.join(SCROLLGT_DATA, gt_name, "gt_ink.png")
        pred_path = os.path.join(DISTILL_ROOT, frag, f"{frag}_inklabels.png")
        for p in (gt_path, pred_path):
            if not os.path.exists(p):
                sys.exit(
                    f"missing input: {p}\n(set SCROLLGT_DATA, and run from the repo root)"
                )

        gt = np.array(Image.open(gt_path)) > 127
        pred = np.array(Image.open(pred_path)) > 127
        if gt.shape != pred.shape:
            sys.exit(f"{frag}: shape mismatch {gt.shape} vs {pred.shape}")

        # placement_peak is the single implementation, shared with the cmd_validate gate.
        # This script used to carry its own copy of the scan, which is exactly the
        # duplicate-implementation hazard that let a second hardcoded LEVEL0_SHAPE survive.
        by, bx, zd, bd = placement_peak(gt, pred, max_shift=args.margin)
        if max(abs(by), abs(bx)) >= args.margin:
            print(
                "  !! peak hit the search boundary -- rerun with a larger --margin",
                file=sys.stderr,
            )

        H, W = gt.shape
        M = args.margin
        core = gt[M : H - M, M : W - M]
        s_zero = binary_stats(core, pred[M : H - M, M : W - M])
        s_best = binary_stats(core, pred[M + by : H - M + by, M + bx : W - M + bx])

        print(f"\n{gt_name}  [{role}]")
        print(f"  Dice @ zero shift : {zd:.4f}")
        print(
            f"  Dice @ peak       : {bd:.4f}  at (dy={by}, dx={bx}) level-2 px"
            f"  ~= {np.hypot(by, bx) * 4:.0f} level-0 voxels"
        )
        print(f"  relative gain     : {(bd - zd) / zd * 100:+.1f}%")
        print(f"  {'metric':<18}{'as published':>14}{'shift-corrected':>18}")
        for k in ("roc_auc", "f1", "precision", "recall", "prevalence_lift"):
            print(f"  {k:<18}{s_zero[k]:>14.4f}{s_best[k]:>18.4f}")

        results.append(
            {
                "target": gt_name,
                "role": role,
                "dice_zero_shift": zd,
                "dice_peak": bd,
                "peak_shift_level2_px": [by, bx],
                "peak_displacement_level0_vx": float(np.hypot(by, bx) * 4),
                "metrics_zero_shift": s_zero,
                "metrics_shift_corrected": s_best,
            }
        )

    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(
                {
                    "margin": args.margin,
                    "coarse": args.coarse,
                    "predictor": "binarised canon teacher (distill_prep crop)",
                    "results": results,
                },
                f,
                indent=2,
            )
        print(f"\nwrote {args.json_out}")


if __name__ == "__main__":
    main()
