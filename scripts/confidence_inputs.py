"""Paired saved ink masks/probabilities and the registered re-score count gate."""

import json
import re
import stat
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from scripts.text_snapshot import Snapshot

SCALE = 10
BLOCK_COLUMNS = 5120
MAX_BLOCK_PIXELS = 8_388_608
MAX_MASK_TILE_PIXELS = 134_217_728
MAX_GRID_CELLS = 16_777_216


def probability_path(arm_dir):
    paths = sorted((Path(arm_dir) / "ink_metric_prob/predictions").glob("*_prob.npy"))
    if not paths:
        return None
    if len(paths) != 1:
        raise ValueError(
            f"{arm_dir}: expected exactly one probability map, found {len(paths)}"
        )
    return paths[0]


def mask_paths(probability):
    name = probability.name.removesuffix("_flat_prob.npy")
    pattern = re.compile(re.escape(name) + r"_mask(?:\.([0-9]+))?\.png")
    paths = list(probability.parent.glob("*mask*.png"))
    indexed = []
    for path in paths:
        match = pattern.fullmatch(path.name)
        if match is None:
            raise ValueError(f"mask does not belong to probability strip: {path}")
        indexed.append((None if match[1] is None else int(match[1]), path))
    if not indexed:
        raise ValueError(f"no paired saved ink masks for {probability}")
    if len(indexed) == 1 and indexed[0][0] is None:
        return [indexed[0][1]]
    if any(index is None for index, _ in indexed):
        raise ValueError("cannot mix tiled and untiled masks")
    indexed.sort()
    if [index for index, _ in indexed] != list(range(len(indexed))):
        raise ValueError("mask tile indices must be unique and contiguous from zero")
    return [path for _, path in indexed]


def _shape(shape):
    if len(shape) != 2 or any(type(n) is not int or n < 1 for n in shape):
        raise ValueError("coordinate grid must be a nonempty 2D shape")
    if shape[0] * shape[1] > MAX_GRID_CELLS:
        raise ValueError(f"coordinate grid exceeds {MAX_GRID_CELLS} cells")
    if shape[0] * SCALE > MAX_BLOCK_PIXELS:
        raise ValueError("coordinate grid is too tall; use a bounded crop")


def probability_sums(probability, masks, shape):
    """Ink counts and probability sums over ink pixels, in 10x10 grid cells.

    Reduce rows, then accumulate globally indexed column groups. Mask tile or
    block boundaries need not be multiples of ten. The NPY stays memory mapped;
    allocation is bounded by a mask tile and a column block, not the whole strip.
    """
    _shape(shape)
    h, w = shape
    a = np.load(probability, mmap_mode="r", allow_pickle=False)
    if a.shape != (h * SCALE, w * SCALE):
        raise ValueError("probability shape must be exactly 10x the coordinate grid")
    if a.dtype.kind != "f" or a.dtype.itemsize > 8:
        raise ValueError("probabilities must have a real floating dtype")
    ink = np.zeros(shape, np.int64)
    sums = np.zeros(shape, np.float64)
    offset = 0
    for path in masks:
        with Image.open(path) as image:
            width, height = image.size
            if height * width > MAX_MASK_TILE_PIXELS:
                raise ValueError(
                    f"mask tile exceeds {MAX_MASK_TILE_PIXELS} pixels: {path}"
                )
            if height != h * SCALE or width < 1 or offset + width > w * SCALE:
                raise ValueError(
                    f"mask tiles must exactly cover the probability strip: {path}"
                )
            values = np.asarray(image)
            if values.ndim != 2 or values.dtype.kind not in "bui":
                raise ValueError(
                    f"saved ink mask must be a scalar binary image: {path}"
                )
            if not (
                np.all((values == 0) | (values == 1))
                or np.all((values == 0) | (values == 255))
            ):
                raise ValueError(f"saved ink mask must contain 0/1 or 0/255: {path}")
            mask = values > 0
        columns = min(BLOCK_COLUMNS, MAX_BLOCK_PIXELS // (h * SCALE))
        for c0 in range(0, width, columns):
            c1 = min(c0 + columns, width)
            first, last = offset + c0, offset + c1
            block = np.asarray(a[:, first:last], dtype=np.float64)
            if not np.isfinite(block).all() or np.any((block < 0) | (block > 1)):
                raise ValueError("probabilities must be finite in [0, 1]")
            selected = mask[:, c0:c1]
            counts = selected.reshape(h, SCALE, c1 - c0).sum(axis=1)
            weighted = (block * selected).reshape(h, SCALE, c1 - c0).sum(axis=1)
            cells = np.arange(first, last) // SCALE
            starts = np.r_[0, np.flatnonzero(np.diff(cells)) + 1]
            target = slice(cells[0], cells[-1] + 1)
            ink[:, target] += np.add.reduceat(counts, starts, axis=1)
            sums[:, target] += np.add.reduceat(weighted, starts, axis=1)
        offset += width
    if offset != w * SCALE:
        raise ValueError("mask tiles must exactly cover the probability strip")
    return ink, sums


def metrics_counts(path):
    snapshot = Snapshot.read(path, 1024**2)
    record = json.loads(snapshot.text())
    if not isinstance(record, dict) or not isinstance(record.get("summary"), dict):
        raise ValueError(f"missing metrics summary: {path}")

    def counts(row, key):
        if not isinstance(row, dict):
            raise ValueError(f"invalid pixel counts: {path}")
        total, fg = row.get("total_pixels"), row.get(key)
        if (
            type(total) is not int
            or total < 1
            or type(fg) is not int
            or not 0 <= fg <= total
        ):
            raise ValueError(f"invalid pixel counts: {path}")
        return total, fg

    total, fg = counts(record["summary"], "total_fg_pixels")
    strips = record.get("strips")
    if (
        not isinstance(strips, list)
        or len(strips) != 1
        or counts(strips[0], "fg_pixels") != (total, fg)
    ):
        raise ValueError(
            f"expected one complete scored strip matching the summary: {path}"
        )
    return total, fg, snapshot.provenance()


def count_gate(arm_dir, pixels, foreground, tolerance):
    root = Path(arm_dir)
    total, original, original_source = metrics_counts(root / "ink_metric/metrics.json")
    rescored_total, rescored, rescored_source = metrics_counts(
        root / "ink_metric_prob/metrics.json"
    )
    if total != pixels or rescored_total != pixels or rescored != foreground:
        raise ValueError(
            f"{root}: metrics pixel counts do not match the paired artifacts"
        )
    relative = (
        abs(rescored - original) / original
        if original
        else (0.0 if rescored == 0 else None)
    )
    if relative is None or relative > tolerance:
        raise ValueError(
            f"{root}: re-scored foreground count exceeds the registered {tolerance:.1%} tolerance"
        )
    return {
        "passed": True,
        "original_foreground": original,
        "rescored_foreground": rescored,
        "total_pixels": pixels,
        "relative_change": relative,
        "tolerance": tolerance,
        "original_metrics": original_source,
        "rescored_metrics": rescored_source,
    }


def file_state(path):
    info = Path(path).stat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"analysis input must be a regular file: {path}")
    return {
        "device": info.st_dev,
        "inode": info.st_ino,
        "bytes": info.st_size,
        "mtime_ns": info.st_mtime_ns,
        "ctime_ns": info.st_ctime_ns,
    }


@dataclass
class ArmData:
    xyz: tuple
    ink: np.ndarray
    probability_sum: np.ndarray
    gate: dict
    sources: dict

    def verify(self):
        if any(file_state(path) != state for path, state in self.sources.items()):
            raise ValueError(
                "analysis input changed while measuring; rerun with stable inputs"
            )
