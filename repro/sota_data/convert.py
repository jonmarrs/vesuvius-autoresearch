"""Adapt a released SOTA surface-volume segment (a directory of tiff depth slices + an ink
label) into the detector's input format: 26 8-bit layers 17..42, plus <seg>_inklabels.png
and <seg>_mask.png resized to the layer grid. Fails loudly on too-few layers or a
label/volume shape mismatch (the cross-scroll misalignment lesson)."""
import glob
import os

import cv2
import numpy as np
import tifffile


def _read_8bit(path):
    arr = tifffile.imread(path)
    if arr.ndim == 3:
        arr = arr[..., 0]
    if arr.dtype == np.uint16:
        arr = (arr // 256).astype(np.uint8)
    elif np.issubdtype(arr.dtype, np.floating):
        if float(arr.max()) <= 1.0:
            arr = arr * 255.0
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    return arr.astype(np.uint8)


def convert_surface_volume(src_dir, seg_id, out_root, n_layers=26, start_idx=17):
    src_layers = sorted(glob.glob(os.path.join(src_dir, "layers", "*.tif")))
    if len(src_layers) < n_layers:
        raise ValueError(
            f"{seg_id}: found {len(src_layers)} source layers, need >= {n_layers}")
    lo = (len(src_layers) - n_layers) // 2
    chosen = src_layers[lo:lo + n_layers]

    out_seg = os.path.join(out_root, seg_id)
    out_layers = os.path.join(out_seg, "layers")
    os.makedirs(out_layers, exist_ok=True)
    h = w = None
    for k, src in enumerate(chosen):
        img = _read_8bit(src)
        h, w = img.shape
        tifffile.imwrite(os.path.join(out_layers, f"{start_idx + k:02d}.tif"), img)

    ink_files = sorted(glob.glob(os.path.join(src_dir, "*inklabels*")))
    if not ink_files:
        raise ValueError(f"{seg_id}: no *inklabels* file in {src_dir}")
    label = cv2.imread(ink_files[0], 0)
    lh, lw = label.shape
    if abs(lh - h) / h > 0.2 or abs(lw - w) / w > 0.2:
        raise ValueError(
            f"{seg_id}: label {lh}x{lw} vs volume {h}x{w} mismatch > 20%")
    label = cv2.resize(label, (w, h), interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(os.path.join(out_seg, f"{seg_id}_inklabels.png"), label)

    mask_files = sorted(glob.glob(os.path.join(src_dir, "*mask*")))
    if mask_files:
        mask = cv2.resize(cv2.imread(mask_files[0], 0), (w, h),
                          interpolation=cv2.INTER_NEAREST)
    else:
        mask = np.full((h, w), 255, np.uint8)
    cv2.imwrite(os.path.join(out_seg, f"{seg_id}_mask.png"), mask)
    return out_seg
