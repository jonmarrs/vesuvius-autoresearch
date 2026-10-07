"""Qualitative SOTA rebase: extract a region of a multiscale OME-Zarr surface volume into
the detector's layer format, so the detector can be run on the new SOTA data. The SOTA
surface volumes are re-flattened (different geometry from our old hand-labeled surfaces), so
no aligned ground-truth label exists -- this path is for a VISUAL comparison against the
released ink prediction, not a val_f1."""

import numpy as np

from .fragment import write_fragment_artifact


def region_to_layers(vol, n_layers=26, z_center=None):
    """vol: (D, H, W) array-like. Return the centered n_layers depth window (n_layers, H, W)."""
    d = vol.shape[0]
    if d < n_layers:
        raise ValueError(f"need >= {n_layers} depth layers, got {d}")
    zc = d // 2 if z_center is None else z_center
    lo = int(np.clip(zc - n_layers // 2, 0, d - n_layers))
    return np.asarray(vol[lo : lo + n_layers])


def write_fragment(layers, out_root, seg_id, start_idx=17, *, label=None):
    """Publish detector layers and a full mask, with an optional caller-supplied label.

    Qualitative fragments stay label-free; teacher/registered-label callers supply their
    actual supervision so it is included in the same complete publication.
    """
    layers = np.asarray(layers)
    if layers.ndim != 3:
        raise ValueError("layers must have shape (depth, height, width)")
    return write_fragment_artifact(
        layers,
        np.ones(layers.shape[1:], bool),
        out_root,
        seg_id,
        start_idx=start_idx,
        label=label,
    )
