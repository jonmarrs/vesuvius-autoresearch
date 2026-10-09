"""Bounded, aligned label artifacts; ignore is an encoding, not missing evidence."""

from pathlib import Path

import numpy as np
from PIL import Image

from scripts.candidate_artifacts import integer
from scripts.labeling.label_artifacts import volume

MAX_LABEL_PIXELS = 2048**2


def aligned_array(values, name, shape=None):
    values = np.asarray(values)
    if (
        values.ndim != 2
        or not values.size
        or (shape is not None and values.shape != tuple(shape))
    ):
        raise ValueError(f"{name} must be a nonempty aligned 2D array")
    return values


def binary_array(values, name="binary labels", shape=None):
    values = aligned_array(values, name, shape)
    if values.dtype.kind not in "biuf":
        raise ValueError(f"{name} must contain real binary values")
    # Accept either binary encoding; mixtures of 1 and 255 are ambiguous.
    if not (np.isin(values, [0, 1]).all() or np.isin(values, [0, 255]).all()):
        raise ValueError(f"{name} must use binary 0/1 or 0/255 values")
    return values != 0


def pseudo_array(values, shape=None):
    values = aligned_array(values, "pseudo labels", shape)
    if values.dtype != np.uint8 or not np.isin(values, [0, 128, 255]).all():
        raise ValueError("pseudo labels must be uint8 with values 0, 128, 255")
    return values


def read_png(path, *, kind, shape=None, max_pixels=MAX_LABEL_PIXELS):
    limit = integer(max_pixels, "max_pixels", 1)
    with Image.open(path) as image:
        if image.format != "PNG" or image.mode not in {"1", "L"}:
            raise ValueError(f"expected a binary or grayscale PNG: {path}")
        if image.width * image.height > limit:
            raise ValueError(f"PNG exceeds max_pixels={limit}: {path}")
        if shape is not None and (image.height, image.width) != tuple(shape):
            raise ValueError(f"PNG must match shape {tuple(shape)}: {path}")
        values = np.asarray(image)
    if kind == "pseudo":
        return pseudo_array(values, shape)
    if kind == "binary":
        return binary_array(values, str(path), shape)
    raise ValueError(f"unknown PNG kind: {kind}")


def merge_labels(pseudo, manual=None, manual_mask=None):
    pseudo = pseudo_array(pseudo)
    if (manual is None) != (manual_mask is None):
        raise ValueError("manual labels require an explicit known-pixel mask")
    result = pseudo.copy()
    if manual is not None:
        labels = binary_array(manual, "manual labels", pseudo.shape)
        known = binary_array(manual_mask, "manual mask", pseudo.shape)
        result[known] = labels[known].astype(np.uint8) * 255
    return result


def fragment_inputs(fragment, region_mask, settings, max_pixels=MAX_LABEL_PIXELS):
    """Read metadata and bounded masks, never materialize the CT volume."""
    fragment = Path(fragment).resolve()
    uri = fragment / "surface_volume.zarr"
    if not uri.exists():
        uri = fragment / "0"
    uri = uri.resolve()
    _, array = volume(uri)
    depth, height, width = array.shape
    if height * width > integer(max_pixels, "max_pixels", 1):
        raise ValueError(
            "fragment exceeds max_pixels; prepare an explicit bounded crop"
        )
    if (
        depth < settings["num_layers"] + 8
        or min(height, width) < settings["patch_size"]
    ):
        raise ValueError(
            "fragment cannot supply the checkpoint patch and buffered depth"
        )
    region = read_png(
        region_mask, kind="binary", shape=(height, width), max_pixels=max_pixels
    )
    if not region.any():
        raise ValueError("region mask must contain requested pixels")
    return uri, tuple(array.shape), region
