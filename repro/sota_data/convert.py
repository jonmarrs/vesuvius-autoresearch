"""Adapt a released SOTA surface-volume segment (a directory of tiff depth slices + an ink
label) into the detector's input format: 26 8-bit layers 17..42, plus <seg>_inklabels.png
and <seg>_mask.png fitted to the layer grid. Fails loudly on too-few layers or a
label/volume shape mismatch (the cross-scroll misalignment lesson)."""

import glob
import os

import cv2
import numpy as np
import tifffile

from .fragment import to_uint8, write_fragment_artifact

# Largest per-axis size difference accepted between the label (or mask) and the layers:
# export rounding, not a different crop or scale. The labeled dataset's
# LABEL_SHAPE_TOLERANCE_PX; released segments differ by 0 or 1 px.
SHAPE_TOLERANCE_PX = 2


def _fit_to_grid(image, h, w, seg_id, what):
    """Crop or zero-pad ``image`` onto the (h, w) layer grid, keeping its origin.

    Until 2026-10-16 a label up to 20% off was resized onto the grid, which stretches
    one of another crop or scale across the volume, misregistered everywhere.
    """
    ih, iw = image.shape
    if abs(ih - h) > SHAPE_TOLERANCE_PX or abs(iw - w) > SHAPE_TOLERANCE_PX:
        raise ValueError(
            f"{seg_id}: {what} {ih}x{iw} vs volume {h}x{w} mismatch > "
            f"{SHAPE_TOLERANCE_PX} px: a different crop or scale; register it to the "
            "layer grid first"
        )
    fitted = np.zeros((h, w), image.dtype)
    fitted[: min(ih, h), : min(iw, w)] = image[:h, :w]
    return fitted


def _read_8bit(path):
    arr = tifffile.imread(path)
    if arr.ndim != 2:
        raise ValueError(
            f"layer must be a 2D grayscale TIFF: {path}, shape {arr.shape}"
        )
    return to_uint8(arr)


def convert_surface_volume(src_dir, seg_id, out_root, n_layers=26, start_idx=17):
    if not isinstance(n_layers, int) or n_layers < 1:
        raise ValueError("n_layers must be a positive integer")
    src_layers = glob.glob(os.path.join(src_dir, "layers", "*.tif"))
    try:
        src_layers.sort(key=lambda p: int(os.path.splitext(os.path.basename(p))[0]))
    except ValueError as exc:
        raise ValueError("layer filenames must be integer depth indices") from exc
    indices = [int(os.path.splitext(os.path.basename(p))[0]) for p in src_layers]
    if len(set(indices)) != len(indices):
        raise ValueError("duplicate layer depth indices")
    if len(src_layers) < n_layers:
        raise ValueError(
            f"{seg_id}: found {len(src_layers)} source layers, need >= {n_layers}"
        )
    lo = (len(src_layers) - n_layers) // 2
    chosen = src_layers[lo : lo + n_layers]

    if any(
        b - a != 1
        for a, b in zip(
            indices[lo : lo + n_layers], indices[lo + 1 : lo + n_layers], strict=False
        )
    ):
        raise ValueError("selected source depth indices must be consecutive")
    layers = [_read_8bit(src) for src in chosen]
    h, w = layers[0].shape
    if any(layer.shape != (h, w) for layer in layers):
        raise ValueError("source layer shape mismatch")

    ink_files = sorted(glob.glob(os.path.join(src_dir, "*inklabels*")))
    if not ink_files:
        raise ValueError(f"{seg_id}: no *inklabels* file in {src_dir}")
    if len(ink_files) != 1:
        raise ValueError(f"{seg_id}: ambiguous inklabels files")
    label = cv2.imread(ink_files[0], 0)
    if label is None:
        raise ValueError(f"{seg_id}: label file unreadable: {ink_files[0]}")
    label = _fit_to_grid(label, h, w, seg_id, "label")
    mask_files = sorted(glob.glob(os.path.join(src_dir, "*mask*")))
    if mask_files:
        if len(mask_files) != 1:
            raise ValueError(f"{seg_id}: ambiguous mask files")
        source_mask = cv2.imread(mask_files[0], 0)
        if source_mask is None:
            raise ValueError(f"{seg_id}: mask file unreadable: {mask_files[0]}")
        mask = _fit_to_grid(source_mask, h, w, seg_id, "mask")
    else:
        mask = np.full((h, w), 255, np.uint8)
    return write_fragment_artifact(
        np.stack(layers), mask > 0, out_root, seg_id, start_idx=start_idx, label=label
    )
