"""Qualitative SOTA rebase: extract a region of a multiscale OME-Zarr surface volume into
the detector's layer format, so the detector can be run on the new SOTA data. The SOTA
surface volumes are re-flattened (different geometry from our old hand-labeled surfaces), so
no aligned ground-truth label exists -- this path is for a VISUAL comparison against the
released ink prediction, not a val_f1."""
import os

import cv2
import numpy as np
import tifffile


def region_to_layers(vol, n_layers=26, z_center=None):
    """vol: (D, H, W) array-like. Return the centered n_layers depth window (n_layers, H, W)."""
    d = vol.shape[0]
    if d < n_layers:
        raise ValueError(f"need >= {n_layers} depth layers, got {d}")
    zc = d // 2 if z_center is None else z_center
    lo = int(np.clip(zc - n_layers // 2, 0, d - n_layers))
    return np.asarray(vol[lo:lo + n_layers])


def write_fragment(layers, out_root, seg_id, start_idx=17):
    """Write a detector-format fragment (layers/{17..42}.tif + zero label + full mask).
    The label is a placeholder (qualitative path: the detector needs it to load, but there
    is no aligned ground truth), so metrics from it are meaningless -- render the prob map."""
    out_seg = os.path.join(out_root, seg_id)
    out_layers = os.path.join(out_seg, "layers")
    os.makedirs(out_layers, exist_ok=True)
    for k in range(layers.shape[0]):
        arr = layers[k]
        if arr.dtype != np.uint8:
            arr = np.clip(arr, 0, 255).astype(np.uint8)
        tifffile.imwrite(os.path.join(out_layers, f"{start_idx + k:02d}.tif"), arr)
    h, w = layers.shape[1], layers.shape[2]
    cv2.imwrite(os.path.join(out_seg, f"{seg_id}_inklabels.png"), np.zeros((h, w), np.uint8))
    cv2.imwrite(os.path.join(out_seg, f"{seg_id}_mask.png"), np.full((h, w), 255, np.uint8))
    return out_seg
