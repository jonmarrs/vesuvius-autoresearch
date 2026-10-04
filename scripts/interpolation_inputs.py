"""Shared input checks for the registered interpolation smoke and window study.

Kept alongside the analysis scripts so the launcher can freeze their complete
Python dependency set without importing the mutable repository during a run.
"""

from pathlib import Path

import numpy as np
import tifffile

SLICE_NAMES = tuple(f"{index:02d}.tif" for index in range(5))


def read_slices(directory: Path, *, shape=None, crop=None) -> list[np.ndarray]:
    """Read all five named sampler slices, rejecting truncation and broadcasting.

    Crop each full-render layer before retaining it, rather than retaining five
    full-strip images just to compare a small smoke window.
    """
    names = {path.name for path in directory.glob("*.tif")}
    if names != set(SLICE_NAMES):
        raise ValueError(
            f"{directory}: expected slices {', '.join(SLICE_NAMES)}, found {sorted(names)}"
        )
    layers = []
    expected_dtype = None
    for name in SLICE_NAMES:
        layer = tifffile.imread(directory / name)
        if layer.ndim != 2 or layer.dtype.kind != "u" or layer.dtype.itemsize > 2:
            raise ValueError(
                f"{directory / name}: expected a 2D uint8 or uint16 intensity image"
            )
        if crop is not None:
            x, y, width, height = crop
            if (
                min(x, y) < 0
                or min(width, height) <= 0
                or y + height > layer.shape[0]
                or x + width > layer.shape[1]
            ):
                raise ValueError(
                    f"{directory / name}: crop exceeds slice dimensions {layer.shape}"
                )
            layer = layer[y : y + height, x : x + width].copy()
        if shape is None:
            shape = layer.shape
        if layer.shape != shape:
            raise ValueError(
                f"{directory / name}: shape {layer.shape}, expected {shape}"
            )
        if expected_dtype is None:
            expected_dtype = layer.dtype
        if layer.dtype != expected_dtype:
            raise ValueError(
                f"{directory / name}: dtype {layer.dtype}, expected {expected_dtype}"
            )
        layers.append(layer)
    return layers
