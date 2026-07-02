"""Distillation data prep: crop the released canon ink prediction (the TEACHER -- a model
output, not ground truth) to a zarr-level region, and write a detector-format training
fragment whose label is the binarized teacher. All downstream metrics on these fragments
are agreement-with-teacher, never ground-truth accuracy."""
import os

import cv2
import numpy as np

from .convert import to_uint8
from .qualitative import write_fragment


def teacher_region_for(teacher_full, level_shape, region_box):
    """Crop a full-segment teacher (any scale) to a region given in level coordinates."""
    th, tw = teacher_full.shape[:2]
    lh, lw = level_shape
    sy, sx = th / lh, tw / lw
    y0, x0, y1, x1 = region_box
    return np.asarray(teacher_full[int(round(y0 * sy)):int(round(y1 * sy)),
                                   int(round(x0 * sx)):int(round(x1 * sx))])


def prep_distill_fragment(region_layers, teacher_region, out_root, frag_id, threshold=128):
    region_layers = np.asarray(region_layers)
    h, w = region_layers.shape[1], region_layers.shape[2]
    t = np.asarray(teacher_region)
    if t.ndim == 3:
        t = t[..., 0]
    th, tw = t.shape
    if abs(th - h) / h > 0.2 or abs(tw - w) / w > 0.2:
        raise ValueError(f"{frag_id}: teacher {th}x{tw} vs region {h}x{w} mismatch > 20%")
    t = to_uint8(t)
    if (th, tw) != (h, w):
        t = cv2.resize(t, (w, h), interpolation=cv2.INTER_NEAREST)
    label = np.where(t >= threshold, 255, 0).astype(np.uint8)

    out_seg = write_fragment(region_layers, out_root, frag_id)  # layers + zero label + mask
    cv2.imwrite(os.path.join(out_seg, f"{frag_id}_inklabels.png"), label)  # replace label
    return out_seg
