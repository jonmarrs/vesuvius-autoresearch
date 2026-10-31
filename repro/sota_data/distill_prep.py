"""Distillation data prep: crop the released canon ink prediction (the TEACHER -- a model
output, not ground truth) to a zarr-level region, and write a detector-format training
fragment whose label is the binarized teacher. All downstream metrics on these fragments
are agreement-with-teacher, never ground-truth accuracy."""

from numbers import Integral

import cv2
import numpy as np

from .convert import to_uint8
from .fragment import resolve_float_encoding, write_fragment_artifact


def same_integer_scale(a, b):
    """Whether shapes ``a`` and ``b`` (h, w) are one pyramid scale k (a power of two)
    of each other on both axes: the larger within k px a side of k times the smaller,
    as a pyramid's rounding leaves them. A 1.2x or per-axis-different scale is another
    crop or scan."""
    (ah, aw), (bh, bw) = a, b
    if min(ah, aw, bh, bw) <= 0:
        return False
    if ah * aw < bh * bw:
        (ah, aw), (bh, bw) = (bh, bw), (ah, aw)
    # k from the smaller shape's longer axis, where the ratio is best resolved.
    k = max(1, round(ah / bh) if bh >= bw else round(aw / bw))
    if k & (k - 1):
        return False
    return abs(ah - k * bh) <= k and abs(aw - k * bw) <= k


def teacher_region_for(teacher_full, level_shape, region_box):
    """Crop a full-segment teacher, at an integer scale of the level, to a region
    given in level coordinates."""
    teacher_full = np.asarray(teacher_full)
    if teacher_full.ndim != 2 or min(teacher_full.shape) <= 0:
        raise ValueError("teacher must be a nonempty scalar 2D image")
    if len(level_shape) != 2 or any(
        not isinstance(v, Integral) or isinstance(v, bool) or v <= 0
        for v in level_shape
    ):
        raise ValueError("level_shape must contain two positive integer dimensions")
    if len(region_box) != 4 or any(
        not isinstance(v, Integral) or isinstance(v, bool) for v in region_box
    ):
        raise ValueError("region_box must contain four integer coordinates")
    y0, x0, y1, x1 = region_box
    if not (0 <= y0 < y1 <= level_shape[0] and 0 <= x0 < x1 <= level_shape[1]):
        raise ValueError("region_box must fit entirely inside level_shape; no clipping")
    th, tw = teacher_full.shape
    lh, lw = level_shape
    if not same_integer_scale((th, tw), (lh, lw)):
        # Until 2026-10-16 each axis was scaled separately, and the crop then stretched.
        raise ValueError(
            f"teacher {th}x{tw} vs level {lh}x{lw} mismatch: not one integer scale on "
            "both axes, so it is not this volume's teacher at a pyramid level"
        )
    sy, sx = th / lh, tw / lw
    cropped = np.asarray(
        teacher_full[
            int(round(y0 * sy)) : int(round(y1 * sy)),
            int(round(x0 * sx)) : int(round(x1 * sx)),
        ]
    )
    if min(cropped.shape) == 0:
        raise ValueError("region maps to an empty teacher crop at this pyramid level")
    return cropped


def prep_distill_fragment(
    region_layers,
    teacher_region,
    out_root,
    frag_id,
    threshold=128,
    *,
    teacher_encoding="auto",
    teacher_source=None,
):
    region_layers = np.asarray(region_layers)
    if region_layers.ndim != 3:
        raise ValueError("region_layers must have shape (depth, height, width)")
    h, w = region_layers.shape[1], region_layers.shape[2]
    if min(region_layers.shape) == 0:
        raise ValueError(
            f"{frag_id}: empty region {region_layers.shape} -- the region offset likely "
            "falls outside the segment's extent; adjust y0/x0"
        )
    if (
        not isinstance(threshold, Integral)
        or isinstance(threshold, bool)
        or not 0 <= threshold <= 255
    ):
        raise ValueError("threshold must be an integer byte value from 0 to 255")
    t = np.asarray(teacher_region)
    if t.ndim != 2 or min(t.shape) == 0:
        raise ValueError(
            "teacher must be a nonempty scalar 2D image; select a channel explicitly"
        )
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
    mode = resolve_float_encoding(t, teacher_encoding)
    teacher_dtype = str(t.dtype)
    t = to_uint8(t, float_encoding=mode)
    if (th, tw) != (h, w):
        t = cv2.resize(t, (w, h), interpolation=cv2.INTER_NEAREST)
    label = np.where(t >= threshold, 255, 0).astype(np.uint8)

    provenance = {
        "kind": "TEACHER_PSEUDOLABEL",
        "ground_truth": False,
        "binarize_threshold": int(threshold),
        "teacher_shape": [th, tw],
        "teacher_dtype": teacher_dtype,
        "teacher_encoding_requested": teacher_encoding,
        "teacher_encoding_applied": mode
        if np.asarray(teacher_region).dtype.kind == "f"
        else None,
        "teacher_source": teacher_source,
        "alignment_verified": False,
        "label_quality_verified": False,
        "training_ready": False,
    }
    return write_fragment_artifact(
        region_layers,
        np.ones((h, w), bool),
        out_root,
        frag_id,
        label=label,
        provenance=provenance,
    )
