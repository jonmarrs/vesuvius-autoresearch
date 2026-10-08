"""Contracts shared by local Mutex data preparation and launch preflight."""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

import numpy as np
import zarr

from scripts.candidate_artifacts import integer, spatial_blocks
from scripts.labeling.label_artifacts import volume
from scripts.validate_prize_artifact import _load_json

REPO_ROOT = Path(__file__).resolve().parents[2]
GRAPH_DIR = REPO_ROOT / "villa/vesuvius/src/vesuvius/image_proc/run"
MAX_VOXELS = 128**3


def graph_tools():
    """Import the pinned numerical helpers without bootstrapping the ML package."""
    script = GRAPH_DIR / "generate_mutex_graph.py"
    if not script.is_file():
        raise FileNotFoundError(f"missing pinned graph tool: {script}")
    if str(GRAPH_DIR) not in sys.path:
        sys.path.insert(0, str(GRAPH_DIR))
    module = importlib.import_module("generate_mutex_graph")
    if Path(module.__file__).resolve() != script.resolve():
        raise RuntimeError("graph tool resolved to a different source")
    return module


def fragment_name(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.-]*", value
    ):
        raise ValueError("fragment name must be a single safe filename stem")
    return value


def bounded_volume(path, max_voxels=MAX_VOXELS):
    root, array = volume(path)
    limit = integer(max_voxels, "max_voxels", 1)
    if int(np.prod(array.shape, dtype=object)) > limit:
        raise ValueError(
            f"fragment shape {array.shape} exceeds max_voxels={limit}; make an explicit bounded crop"
        )
    return root, array


def label_values(values):
    if values.dtype.kind not in "uib" or (
        values.dtype.kind == "i" and np.any(values < 0)
    ):
        raise ValueError(
            "segmentation labels must be nonnegative integer or boolean IDs"
        )


def validate_prepared_data(path, patch=None):
    """Inspect the actual paired payloads; a directory name is not completion."""
    path = Path(path)
    completion = _load_json(path / "mutex_data_completion.json")
    if completion.get("contract") != 1 or completion.get("axes") != ["z", "y", "x"]:
        raise ValueError("missing or unsupported Mutex preparation contract")
    name = fragment_name(completion.get("fragment"))
    if completion.get("label_mode") not in {"instances", "foreground-components"}:
        raise ValueError("unknown label semantics")
    if completion.get("ignore_background_edges") is not True:
        raise ValueError("unreviewed background edges must be masked")
    stride = integer(completion.get("long_range_stride"), "long_range_stride", 1)
    for folder in ("images", "affinity_graph"):
        entries = {
            item.name
            for item in (path / folder).iterdir()
            if item.suffix.lower() in {".zarr", ".tif", ".tiff"}
        }
        if entries != {f"{name}.zarr"}:
            raise ValueError(
                f"{folder} must contain exactly the declared paired fragment"
            )
    _, image = volume(path / "images" / f"{name}.zarr")
    if (
        image.dtype.kind not in "uif"
        or list(image.shape) != completion.get("shape_zyx")
        or str(image.dtype) != completion.get("raw_dtype")
    ):
        raise ValueError("raw image shape or dtype disagrees with completion")
    if patch is not None and min(image.shape) < integer(patch, "patch", 1):
        raise ValueError("prepared fragment is smaller than the requested patch")
    graph = zarr.open_group(str(path / "affinity_graph" / f"{name}.zarr"), mode="r")
    if (
        graph.attrs.get("ignore_background_edges") is not True
        or graph.attrs.get("long_range_stride") != stride
        or graph.attrs.get("label_mode") != completion["label_mode"]
    ):
        raise ValueError("graph settings disagree with completion")
    labels = graph["labels"]
    original = (
        graph["source_labels"]
        if completion["label_mode"] == "foreground-components"
        else labels
    )
    if (
        original.shape != image.shape
        or str(original.dtype) != completion.get("label_dtype")
        or labels.shape != image.shape
    ):
        raise ValueError("label payload disagrees with raw image or completion")
    expected = graph_tools().build_offset_sets()
    channels, valid_edges = {}, {}
    targets = {}
    for kind, offsets in zip(("attractive", "repulsive"), expected[:2], strict=True):
        recorded = graph.attrs.get(f"{kind}_offsets", [])
        if len(recorded) != len(offsets) or {
            tuple(offset) for offset in recorded
        } != set(offsets):
            raise ValueError(f"{kind} offsets disagree with the pinned graph recipe")
        affinity, mask = graph[f"affinities/{kind}"], graph[f"mask/{kind}"]
        if (
            affinity.shape != (len(recorded), *image.shape)
            or mask.shape != affinity.shape
            or affinity.dtype != np.uint8
            or mask.dtype != np.uint8
        ):
            raise ValueError(f"invalid {kind} affinity or mask schema")
        targets[kind] = affinity, mask
        channels[kind] = len(recorded)
        valid_edges[kind] = 0
    for selection in spatial_blocks(image.shape):
        if not np.isfinite(image[selection]).all():
            raise ValueError("raw image contains nonfinite values")
        label_values(original[selection])
        label_values(labels[selection])
        for kind, (affinity, mask) in targets.items():
            values, valid = (
                affinity[(slice(None), *selection)],
                mask[(slice(None), *selection)],
            )
            if np.any(values > 1) or np.any(valid > 1) or np.any(values[valid == 0]):
                raise ValueError(f"invalid binary values or unmasked {kind} affinities")
            valid_edges[kind] += int(np.count_nonzero(valid))
    if any(count == 0 for count in valid_edges.values()):
        raise ValueError("each affinity target needs at least one supervised edge")
    if channels != completion.get("channels") or valid_edges != completion.get(
        "valid_edges"
    ):
        raise ValueError("graph coverage disagrees with completion")
    return {"completion": completion, "channels": channels, "valid_edges": valid_edges}
