"""Probe whether villa's `skeleton_distance_length` (the loop's `skel_dist` prize gate)
measures ink-detection quality, or only the *distribution of skeleton branch lengths*.

`skeleton_distance_length.compute` skeletonizes label and prediction, histograms the
branch lengths of each, and returns the symmetric-KL divergence between those two
histograms. It never compares *where* the skeletons are. This script demonstrates the
consequence on four synthetic predictions of a 5-stroke "ink" label:

    perfect copy                         -> skel_dist 0.0   (pass)
    shifted entirely off (same lengths)  -> skel_dist 0.0   (pass)  <- zero spatial overlap
    60% recall (3 of 5 strokes, correct) -> skel_dist ~0    (pass)  <- blind to recall
    spatially correct but fragmented     -> skel_dist ~40+  (fail)  <- punishes fragmentation

Run:
    CUDA_VISIBLE_DEVICES="" WANDB_MODE=disabled uv run python scripts/probe_skel_dist_validity.py
"""

import os
import sys

os.environ.setdefault("WANDB_MODE", "disabled")
import numpy as np

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "villa", "segmentation", "evaluation"))
import wandb

if wandb.run is None:
    wandb.init(mode="disabled")
from metrics.skeleton_distance_length import compute as skel_dist  # noqa: E402

H, W = 400, 600
YS = [60, 140, 200, 280, 340]


def blank():
    return np.zeros((H, W), np.uint8)


def make_label():
    a = blank()
    for y in YS:
        a[y - 1 : y + 2, 40:560] = 1
    return a


def to3d(a):
    return a[None].astype(np.uint8)


def main():
    label = make_label()

    yshift = blank()  # same stroke lengths, shifted down 30px -> zero overlap
    for y in YS:
        yshift[y + 29 : y + 32, 40:560] = 1

    partial = blank()  # 3 of 5 strokes, each spatially correct
    for y in YS[:3]:
        partial[y - 1 : y + 2, 40:560] = 1

    frag = blank()  # spatially-correct pixels broken into 20px pieces
    for y in YS:
        for x0 in range(40, 560, 40):
            frag[y - 1 : y + 2, x0 : x0 + 20] = 1

    cases = [
        ("perfect", label),
        ("shifted_off", yshift),
        ("recall_60pct", partial),
        ("fragmented", frag),
    ]

    def overlap(a):
        return float((a & label).sum()) / float(label.sum())

    print(f"{'case':14s} {'pixel_overlap':>13s} {'skel_dist':>12s}")
    for name, pred in cases:
        d = skel_dist(to3d(label), to3d(pred))
        print(f"{name:14s} {overlap(pred):13.2f} {d:12.4f}")


if __name__ == "__main__":
    main()
