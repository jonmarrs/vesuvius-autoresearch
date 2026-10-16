"""Distillation data prep: crop the released canon ink prediction (the TEACHER -- a model
output, not ground truth) to a zarr-level region, and write a detector-format training
fragment whose label is the binarized teacher. All downstream metrics on these fragments
are agreement-with-teacher, never ground-truth accuracy."""

import cv2
import numpy as np

from .convert import to_uint8
from .qualitative import write_fragment


def same_integer_scale(a, b):
    """Whether shapes ``a`` and ``b`` (h, w) are one integer scale k of each other on
    both axes: the larger within k px a side of k times the smaller, as a pyramid's
    rounding leaves them. A 1.2x or per-axis-different scale is another crop or scan."""
    (ah, aw), (bh, bw) = a, b
    if min(ah, aw, bh, bw) <= 0:
        return False
    if ah < bh:
        (ah, aw), (bh, bw) = (bh, bw), (ah, aw)
    k = max(1, round(ah / bh))
    return abs(ah - k * bh) <= k and abs(aw - k * bw) <= k


def teacher_region_for(teacher_full, level_shape, region_box):
    """Crop a full-segment teacher, at an integer scale of the level, to a region
    given in level coordinates."""
    th, tw = teacher_full.shape[:2]
    lh, lw = level_shape
    if not same_integer_scale((th, tw), (lh, lw)):
        # Until 2026-10-16 each axis was scaled separately, and the crop then stretched.
        raise ValueError(
            f"teacher {th}x{tw} vs level {lh}x{lw} mismatch: not one integer scale on "
            "both axes, so it is not this volume's teacher at a pyramid level"
        )
    sy, sx = th / lh, tw / lw
    y0, x0, y1, x1 = region_box
    return np.asarray(
        teacher_full[
            int(round(y0 * sy)) : int(round(y1 * sy)),
            int(round(x0 * sx)) : int(round(x1 * sx)),
        ]
    )


def prep_distill_fragment(
    region_layers, teacher_region, out_root, frag_id, threshold=128
):
    region_layers = np.asarray(region_layers)
    h, w = region_layers.shape[1], region_layers.shape[2]
    if h == 0 or w == 0:
        raise ValueError(
            f"{frag_id}: empty region {region_layers.shape} -- the region offset likely "
            "falls outside the segment's extent; adjust y0/x0"
        )
    t = np.asarray(teacher_region)
    if t.ndim == 3:
        t = t[..., 0]
    th, tw = t.shape
    # The teacher may be at another pyramid level than the region (e.g. a level-0
    # teacher for a level-2 region): one integer scale on both axes, which the resize
    # below undoes. Anything else (until 2026-10-16, up to 20% between the axes) is
    # another crop or an axis swap, and resizing would stretch it over the region.
    if not same_integer_scale((th, tw), (h, w)):
        raise ValueError(
            f"{frag_id}: teacher {th}x{tw} vs region {h}x{w} mismatch: not one "
            "integer scale on both axes"
        )
    t = to_uint8(t)
    if (th, tw) != (h, w):
        t = cv2.resize(t, (w, h), interpolation=cv2.INTER_NEAREST)
    label = np.where(t >= threshold, 255, 0).astype(np.uint8)

    return write_fragment(region_layers, out_root, frag_id, label=label)
