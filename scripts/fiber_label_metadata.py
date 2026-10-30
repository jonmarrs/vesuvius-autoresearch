"""Validate the recorded CT window and serialized-label binding of contract 1.

This checks producer declarations, not registration, CT contents or label quality.
"""

import re
from pathlib import Path

import numpy as np

from scripts.candidate_artifacts import integer
from scripts.labeling.label_artifacts import bounded_number


def _integers(values, name, count, minimum=0):
    if not isinstance(values, list) or len(values) != count:
        raise ValueError(f"fiber metadata {name} must contain {count} integers")
    return [integer(value, name, minimum) for value in values]


def _digest(value, name):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"fiber metadata {name} must be a SHA-256 digest")
    return value


def validate_fiber_metadata(details, candidate, fiber_shape, label_sha256, source_uri):
    if type(details.get("contract")) is not int or details["contract"] != 1:
        raise ValueError("unsupported fiber metadata contract; expected integer 1")
    if details.get("label_kind") != "ct_vesselness_pseudo_label":
        raise ValueError("fiber metadata must describe CT vesselness pseudo-labels")
    if details.get("axes") != ["z", "y", "x"] or len(fiber_shape) != 3:
        raise ValueError("fiber metadata requires a ZYX volume")
    shape = _integers(details.get("shape_zyx"), "shape_zyx", 3, 3)
    if shape != list(fiber_shape):
        raise ValueError("fiber metadata shape contradicts the label TIFF")
    bounds = _integers(details.get("evaluated_bbox_zyx"), "evaluated_bbox_zyx", 6)
    expected = [
        candidate["z"],
        candidate["z"] + shape[0],
        candidate["y"],
        candidate["y"] + candidate["height"],
        candidate["x"],
        candidate["x"] + candidate["width"],
    ]
    if bounds != expected or shape[1:] != [candidate["height"], candidate["width"]]:
        raise ValueError("fiber source window contradicts candidate metadata")
    source_shape = _integers(details.get("source_shape_zyx"), "source_shape_zyx", 3, 1)
    if any(
        stop > limit for stop, limit in zip(bounds[1::2], source_shape, strict=True)
    ):
        raise ValueError("fiber source window exceeds recorded source shape")
    path = details.get("source_path")
    if (
        not isinstance(path, str)
        or not path
        or len(path) > 4096
        or any(ord(char) < 32 for char in path)
        or not Path(path).is_absolute()
        or Path(path).resolve() != Path(source_uri).resolve()
    ):
        raise ValueError("fiber source path contradicts candidate metadata")
    if not isinstance(details.get("source_dtype"), str):
        raise ValueError("fiber metadata must record its source dtype")
    dtype = np.dtype(details["source_dtype"])
    if dtype.kind not in "uif" or dtype.itemsize > 8:
        raise ValueError(
            "fiber metadata source dtype must describe real CT intensities"
        )
    bounded_number(details.get("threshold"), "fiber metadata threshold", 0, 1)
    if details.get("backend") not in ("numpy", "cupy"):
        raise ValueError("fiber metadata must record its numpy/cupy backend")
    if _digest(details.get("label_file_sha256"), "label_file_sha256") != label_sha256:
        raise ValueError("fiber label TIFF does not match its producer hash")
    ct_digest = _digest(details.get("ct_content_sha256"), "ct_content_sha256")
    _digest(details.get("filter_source_sha256"), "filter_source_sha256")
    _digest(details.get("prob_file_sha256"), "prob_file_sha256")
    return bounds, ct_digest
