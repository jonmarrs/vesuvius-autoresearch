"""Adapt a released SOTA surface-volume segment (a directory of tiff depth slices + an ink
label) into the detector's input format: 26 8-bit layers 17..42, plus <seg>_inklabels.png
and <seg>_mask.png resized to the layer grid. Fails loudly on too-few layers or a
label/volume shape mismatch (the cross-scroll misalignment lesson)."""

import glob
import os

import cv2
import numpy as np
import tifffile

from .fragment import to_uint8, write_fragment_artifact


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
    lh, lw = label.shape
    if abs(lh - h) / h > 0.2 or abs(lw - w) / w > 0.2:
        raise ValueError(f"{seg_id}: label {lh}x{lw} vs volume {h}x{w} mismatch > 20%")
    label = cv2.resize(label, (w, h), interpolation=cv2.INTER_NEAREST)
    mask_files = sorted(glob.glob(os.path.join(src_dir, "*mask*")))
    if mask_files:
        if len(mask_files) != 1:
            raise ValueError(f"{seg_id}: ambiguous mask files")
        source_mask = cv2.imread(mask_files[0], 0)
        if source_mask is None:
            raise ValueError(f"{seg_id}: mask file unreadable: {mask_files[0]}")
        mh, mw = source_mask.shape
        if abs(mh - h) / h > 0.2 or abs(mw - w) / w > 0.2:
            raise ValueError(f"{seg_id}: mask vs volume shape mismatch > 20%")
        mask = cv2.resize(source_mask, (w, h), interpolation=cv2.INTER_NEAREST)
    else:
        mask = np.full((h, w), 255, np.uint8)
    return write_fragment_artifact(
        np.stack(layers), mask > 0, out_root, seg_id, start_idx=start_idx, label=label
    )
