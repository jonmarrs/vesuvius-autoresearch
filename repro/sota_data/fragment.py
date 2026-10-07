"""Publish complete detector fragments; never overwrite prior data or invent labels."""

import json
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np
import tifffile


def to_uint8(arr):
    """Convert uint8, uint16, or finite floats (unit or byte range) to detector bytes."""
    arr = np.asarray(arr)
    if arr.size == 0 or not np.isfinite(arr).all():
        raise ValueError("pixels must be nonempty and finite")
    if arr.dtype.kind == "u" and arr.dtype.itemsize == 1:
        return arr
    if arr.dtype.kind == "u" and arr.dtype.itemsize == 2:
        return (arr // 256).astype(np.uint8)
    if np.issubdtype(arr.dtype, np.floating):
        if arr.min() < 0 or arr.max() > 255:
            raise ValueError("float pixels must be in [0,1] or [0,255]")
        if arr.max() <= 1:
            arr = arr * 255
        return arr.astype(np.uint8)
    raise ValueError(f"unsupported dtype {arr.dtype}; expected uint8/uint16/float")


def validate_fragment_id(frag_id):
    if (
        not isinstance(frag_id, str)
        or not frag_id.strip()
        or frag_id in (".", "..")
        or any(c in frag_id for c in ("/", "\\", "\x00"))
    ):
        raise ValueError("fragment id must be a single nonempty directory name")
    return frag_id


def write_fragment_artifact(
    layers, valid, out_root, frag_id, *, start_idx=17, label=None, provenance=None
):
    """Stage layers, mask, optional *supplied* label, and metadata beside the destination.

    Publish with one directory rename only after every write succeeds. Existing fragment
    ids are refused, including labeled fragments and broken symlinks. Use a fresh id/root
    for reruns. A crash may leave a hidden staging directory, never a final fragment.
    """
    validate_fragment_id(frag_id)
    layers = np.asarray(layers)
    valid = np.asarray(valid)
    if layers.ndim != 3 or min(layers.shape) == 0:
        raise ValueError("layers must have nonempty shape (depth, height, width)")
    if valid.dtype != np.bool_ or valid.shape != layers.shape[1:]:
        raise ValueError("valid mask must be boolean and match the layer grid")
    if not isinstance(start_idx, (int, np.integer)) or start_idx < 0:
        raise ValueError("start_idx must be a nonnegative integer")
    # Validate before opening staging files; preserve each layer's established scaling.
    for layer in layers:
        to_uint8(layer)
    if label is not None:
        label = np.asarray(label)
        if label.dtype != np.uint8 or label.shape != valid.shape:
            raise ValueError("supplied label must be uint8 and match the layer grid")
    metadata = (
        json.dumps(provenance, indent=2, allow_nan=False, default=float) + "\n"
        if provenance is not None
        else None
    )
    root = Path(out_root)
    destination = root / frag_id
    if os.path.lexists(destination):
        raise FileExistsError(
            f"fragment already exists: {destination}; use a fresh id/root"
        )
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{frag_id}-", dir=root) as temp:
        staged = Path(temp) / frag_id
        (staged / "layers").mkdir(parents=True)
        for k, layer in enumerate(layers):
            tifffile.imwrite(
                staged / "layers" / f"{start_idx + k:02d}.tif", to_uint8(layer)
            )
        images = [(f"{frag_id}_mask.png", valid.astype(np.uint8) * 255)]
        if label is not None:
            images.append((f"{frag_id}_inklabels.png", label))
        for name, pixels in images:
            if not cv2.imwrite(str(staged / name), pixels):
                raise OSError(f"failed to write {name}")
        if metadata is not None:
            (staged / f"{frag_id}_render_provenance.json").write_text(metadata)
        if os.path.lexists(destination):
            raise FileExistsError(f"fragment already exists: {destination}")
        staged.rename(destination)
    return str(destination)
