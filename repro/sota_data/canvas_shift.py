"""Put a canvas-space ink label onto the tifxyz grid it was drawn beside.

Some released training segments ship a canvas whose shape matches the tifxyz
grid, so a shape check accepts it, while the ink itself sits on the wrong
pixels. A constant offset covers the one-cell and integer shifts. Paris-4-style
segments also change that offset across the sheet. With three or more windows
the fit keeps the cross terms, ``dy = ay + sy * y + cy * x`` and
``dx = ax + cx * y + sx * x``. Dropping those terms leaves up to about half a
pixel on the published segments.

Prior art: villa's ``tifxyz_label_transfer.estimate_canvas_offset`` (villa
#1457) measures this offset by tile phase correlation and already fits a
translation plus linear drift. It reports a drifting field as not a valid
translation, and ``transfer --label-canvas-offset`` applies one constant
(DY, DX). What this module adds is the resample with the drift.

Measurement convention, locked by tests: canvas pixel ``(y, x)`` corresponds
to tifxyz cell ``(y + dy, x + dx)``. Resampling into the tifxyz frame solves
that for the source pixel. ``px_scale`` turns a coarser lattice into level-0
pixels (4 for a level-2 pair). Non-finite samples are tifxyz holes and are
left out of the correlation.

This is not the published measurer's filter. That one subtracts a masked
Gaussian mean (sigma 4 level-2 pixels), divides by the local standard
deviation, and scores NCC on an explicit supervision mask. This one subtracts
a masked box mean (default width 31, holes left as NaN so they do not darken
a neighbour) and does not divide by the local standard deviation. The NCC
mask is "finite", not the supervision zarr. A window with fewer than 100
finite pixels can still be scored here; the published map requires 100.
Integer labels are resampled with nearest neighbor, so 0/255 stays 0/255 and
the result keeps the label's dtype. A float label is blended unless the
caller passes ``nearest=True``. ``resize_grayscale`` follows the same rule:
an integer or bool image defaults to nearest neighbor, because OpenCV's
default bilinear resize invents gray levels between those pixels. A float
image stays bilinear.

``sample_tifxyz`` and ``sample_volume_trilinear`` build the surface the
correlation compares against the canvas: CT sampled at the tifxyz cells.
Fetching the bytes is the caller's job.

One window::

    python -m repro.sota_data.canvas_shift surface.npy canvas.npy \\
        --window Y X H W --max-shift 64 --json

Several windows fit the linear residual. ``--out corrected.npy`` writes the
canvas resampled onto the tifxyz frame, on the surface's grid unless
``--out-shape`` says otherwise. ``--nearest`` keeps label values intact. A
PNG holds only a uint8 or uint16 result; anything else is refused rather
than squeezed to 8 bits. Exit status: 0 aligned within 1 level-0 px, 1 a
shift was measured, 2 usage or input/output error, 3 a shift not located.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from collections.abc import Sequence
from numbers import Integral
from pathlib import Path

import cv2
import numpy as np

MIN_NCC = 0.5
DRIFT_PX = 1.0
# A coefficient whose own change across the measured span is below this is
# numerical dust. The published shorter model loses up to 0.47 px by dropping
# a real cross term, so the floor sits under that and above fit noise.
COEF_FLOOR_PX = 0.25
MAX_SLOPE = 0.5
# When the window centres' y and x are this correlated (r squared), least
# squares cannot tell a y slope from an x slope and splits it: a diagonal of
# windows turned dy = 0.01*y into 0.005*y + 0.005*x. Such windows get the
# per-axis fit that two windows get. 0.9 is a variance inflation factor of 10,
# the usual threshold for collinear predictors.
COLLINEAR_R2 = 0.9


class CanvasShiftNotLocated(ValueError):
    """The search did not find a shift that places the canvas on the surface."""


def _plane(image: np.ndarray, what: str) -> np.ndarray:
    """Return a 2D array. Non-finite values are holes, not data, and are kept."""
    array = np.asarray(image)
    if array.ndim == 3 and array.shape[-1] in (1, 3, 4):
        array = array[..., 0]
    if array.ndim != 2:
        raise ValueError(f"{what} must be a 2D image, got shape {array.shape}")
    if array.size == 0 or not np.isfinite(array).any():
        raise ValueError(f"{what} must contain at least one finite sample")
    if np.isinf(array).any():
        raise ValueError(f"{what} must not contain infinite values")
    return np.ascontiguousarray(array)


def highpass(image: np.ndarray, size: int = 31) -> np.ndarray:
    """Remove a locally linear background. A pure ramp becomes ~0 inside the image.

    The local mean ignores non-finite holes, so a tifxyz ``-1`` that the caller
    has marked as NaN does not darken the neighbourhood.
    """
    if isinstance(size, bool) or not isinstance(size, Integral) or int(size) < 1:
        raise ValueError("high-pass size must be a positive integer")
    size = (
        int(size) | 1
    )  # box filters use an odd window; an even size would shift the phase
    plane = _plane(image, "image").astype(np.float32)
    mask = np.isfinite(plane)
    filled = np.where(mask, plane, 0).astype(np.float32)
    weight = cv2.blur(mask.astype(np.float32), (size, size))
    mean = cv2.blur(filled, (size, size)) / np.maximum(weight, 1e-3)
    return np.where(mask, plane - mean, np.nan).astype(np.float32)


def _highpass_region(
    image: np.ndarray, y0: int, y1: int, x0: int, x1: int, size: int
) -> np.ndarray:
    """``highpass(image, size)[y0:y1, x0:x1]``, filtering only what that region reads.

    The box reaches ``size // 2`` pixels past the region. Where the crop stops
    at the image edge it reflects there as the whole-image filter does, so the
    two agree to float rounding.
    """
    if isinstance(size, bool) or not isinstance(size, Integral) or int(size) < 1:
        raise ValueError("high-pass size must be a positive integer")
    half = (int(size) | 1) // 2
    height, width = image.shape
    top, left = max(0, y0 - half), max(0, x0 - half)
    bottom, right = min(height, y1 + half), min(width, x1 + half)
    crop = image[top:bottom, left:right]
    if not np.isfinite(crop).any():
        return np.full((y1 - y0, x1 - x0), np.nan, np.float32)
    return highpass(crop, size)[y0 - top : y1 - top, x0 - left : x1 - left]


def resize_grayscale(
    image: np.ndarray,
    out_shape: tuple[int, int],
    interpolation: int | None = None,
) -> np.ndarray:
    """Resize a 2D grayscale image to ``out_shape`` (height, width).

    OpenCV's default resize is bilinear, which invents gray levels between
    integer pixels (a 0/200 step becomes 100). An integer or bool image
    therefore defaults to nearest neighbor. A float image defaults to
    bilinear. Pass ``interpolation`` to override either default.
    """
    plane = _plane(image, "image")
    if len(out_shape) != 2 or any(
        isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 1
        for value in out_shape
    ):
        raise ValueError("out_shape must be two positive integers (height, width)")
    height, width = int(out_shape[0]), int(out_shape[1])
    integer = bool(np.issubdtype(plane.dtype, np.integer) or plane.dtype == np.bool_)
    if interpolation is None:
        interpolation = cv2.INTER_NEAREST if integer else cv2.INTER_LINEAR
    elif isinstance(interpolation, bool) or not isinstance(interpolation, Integral):
        raise ValueError("interpolation must be an OpenCV flag")
    work = plane.astype(np.uint8) if plane.dtype == np.bool_ else plane
    resized = cv2.resize(work, (width, height), interpolation=int(interpolation))
    if plane.dtype == np.bool_ and int(interpolation) == cv2.INTER_NEAREST:
        return resized.astype(bool)
    return resized


def level0_centers(indices: np.ndarray, stride: int) -> np.ndarray:
    """Level-0 coordinate of each pixel centre on a ``stride`` lattice.

    A level-2 pixel ``i`` (stride 4) is centred at ``4*i + 1.5``.
    """
    if isinstance(stride, bool) or not isinstance(stride, Integral) or int(stride) < 1:
        raise ValueError("stride must be a positive integer")
    return int(stride) * np.asarray(indices, np.float64) + (int(stride) - 1) / 2.0


def sample_tifxyz(
    z_plane: np.ndarray,
    y_plane: np.ndarray,
    x_plane: np.ndarray,
    rows: np.ndarray,
    cols: np.ndarray,
    scale_y: float,
    scale_x: float,
) -> np.ndarray:
    """Bilinear ZYX at full-res tifxyz cells ``rows``, ``cols``.

    Stored coordinate is ``full_res * scale`` (villa's half=0 convention).
    A corner stored as ``-1``, a non-finite corner, or ``z <= 0`` makes that
    sample NaN. The result has shape ``(len(rows), len(cols), 3)`` in Z, Y, X
    order, which is the order the CT volume is indexed in.
    """
    planes = [np.asarray(plane, np.float64) for plane in (z_plane, y_plane, x_plane)]
    if any(plane.ndim != 2 or plane.shape != planes[0].shape for plane in planes):
        raise ValueError("tifxyz planes must be 2D and the same shape")
    height, width = planes[0].shape
    stored_row = np.asarray(rows, np.float64) * float(scale_y)
    stored_col = np.asarray(cols, np.float64) * float(scale_x)
    row0 = np.floor(stored_row).astype(np.int64)
    col0 = np.floor(stored_col).astype(np.int64)
    row_frac = (stored_row - row0)[:, None]
    col_frac = (stored_col - col0)[None, :]

    def _at(plane: np.ndarray, row: np.ndarray, col: np.ndarray) -> np.ndarray:
        ok = (row >= 0) & (row < height) & (col >= 0) & (col < width)
        gathered = plane[np.clip(row, 0, height - 1), np.clip(col, 0, width - 1)]
        return np.where(ok, gathered, np.nan)

    out = np.empty((len(stored_row), len(stored_col), 3), np.float64)
    valid = np.ones((len(stored_row), len(stored_col)), dtype=bool)
    for index, plane in enumerate(planes):
        corners = [
            _at(plane, row0[:, None], col0[None, :]),
            _at(plane, row0[:, None] + 1, col0[None, :]),
            _at(plane, row0[:, None], col0[None, :] + 1),
            _at(plane, row0[:, None] + 1, col0[None, :] + 1),
        ]
        out[..., index] = (
            corners[0] * (1.0 - row_frac) * (1.0 - col_frac)
            + corners[1] * row_frac * (1.0 - col_frac)
            + corners[2] * (1.0 - row_frac) * col_frac
            + corners[3] * row_frac * col_frac
        )
        finite = np.ones_like(valid)
        for corner in corners:
            finite &= np.isfinite(corner) & (corner != -1)
        if index == 0:
            finite &= corners[0] > 0
            finite &= corners[1] > 0
            finite &= corners[2] > 0
            finite &= corners[3] > 0
        valid &= finite
    out[~valid] = np.nan
    return out


def sample_volume_trilinear(
    volume: np.ndarray, zyx0: np.ndarray, level: int = 0
) -> np.ndarray:
    """Trilinear sample of one pyramid level at level-0 ZYX points.

    ``volume`` is already that level. Level ``k`` voxel ``i`` covers level-0
    ``[2^k * i, 2^k * i + 2^k - 1]``, so its centre is
    ``(p0 - (2^k - 1) / 2) / 2^k``. Points outside the volume are NaN.
    """
    array = np.asarray(volume)
    if array.ndim != 3:
        raise ValueError(f"volume must be 3D ZYX, got shape {array.shape}")
    if isinstance(level, bool) or not isinstance(level, Integral) or int(level) < 0:
        raise ValueError("level must be a non-negative integer")
    points = np.asarray(zyx0, np.float64)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("zyx0 must have shape (N, 3)")
    factor = 2 ** int(level)
    continuous = (points - (factor - 1) / 2.0) / factor
    base = np.floor(continuous)
    frac = continuous - base
    base_i = base.astype(np.int64)
    depth, height, width = array.shape
    inside = np.all(np.isfinite(points), axis=1)
    value = np.zeros(len(points), np.float64)
    for z_off, y_off, x_off in (
        (a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)
    ):
        zz = base_i[:, 0] + z_off
        yy = base_i[:, 1] + y_off
        xx = base_i[:, 2] + x_off
        here = (
            inside
            & (zz >= 0)
            & (yy >= 0)
            & (xx >= 0)
            & (zz < depth)
            & (yy < height)
            & (xx < width)
        )
        inside &= here
        weight = (
            (frac[:, 0] if z_off else 1.0 - frac[:, 0])
            * (frac[:, 1] if y_off else 1.0 - frac[:, 1])
            * (frac[:, 2] if x_off else 1.0 - frac[:, 2])
        )
        value[here] += weight[here] * array[zz[here], yy[here], xx[here]]
    out = np.full(len(points), np.nan, np.float32)
    out[inside] = value[inside]
    return out


def _parabola(left: float, center: float, right: float) -> float:
    denom = left - 2.0 * center + right
    if denom == 0.0 or not np.isfinite(denom):
        return 0.0
    delta = 0.5 * (left - right) / denom
    if not np.isfinite(delta):
        return 0.0
    return float(np.clip(delta, -1.0, 1.0))


def _masked_ncc(
    canvas_window: np.ndarray,
    surface_search: np.ndarray,
    max_shift: int,
    *,
    min_frac: float = 0.5,
) -> np.ndarray:
    """NCC of canvas[y, x] with surface[max_shift + y + dy, max_shift + x + dx].

    Non-finite samples on either image are holes and do not enter the sum.
    The result is NaN where the overlap of finite samples is under half the
    canvas window's finite area.
    """
    height, width = canvas_window.shape
    response = np.full((2 * max_shift + 1, 2 * max_shift + 1), np.nan, np.float64)
    canvas_ok = np.isfinite(canvas_window)
    needed = max(100, int(min_frac * int(canvas_ok.sum())))
    if int(canvas_ok.sum()) < 100 and int(canvas_ok.sum()) < needed:
        needed = max(1, int(min_frac * int(canvas_ok.sum())))
    for dy in range(-max_shift, max_shift + 1):
        y0 = max_shift + dy
        for dx in range(-max_shift, max_shift + 1):
            x0 = max_shift + dx
            patch = surface_search[y0 : y0 + height, x0 : x0 + width]
            overlap = canvas_ok & np.isfinite(patch)
            count = int(overlap.sum())
            if count < needed:
                continue
            left = canvas_window[overlap].astype(np.float64)
            right = patch[overlap].astype(np.float64)
            left -= left.mean()
            right -= right.mean()
            denom = float(np.sqrt((left * left).sum() * (right * right).sum()))
            if denom == 0.0:
                continue
            response[dy + max_shift, dx + max_shift] = (left * right).sum() / denom
    return response


def measure_shift(
    surface: np.ndarray,
    canvas: np.ndarray,
    window: Sequence[int],
    max_shift: int = 64,
    *,
    highpass_size: int = 31,
    min_ncc: float = MIN_NCC,
    px_scale: float = 1.0,
    origin: tuple[float, float] = (0.0, 0.0),
) -> dict[str, float]:
    """Shift that places this canvas window onto the tifxyz-frame surface.

    ``window`` is ``(y, x, height, width)`` in the image's own pixels. Both
    images index from the same pixel 0 but need not be the same size: a
    Paris-4 canvas is not its tifxyz grid's size. The window must lie inside
    the canvas and at least ``max_shift`` pixels inside the surface. ``dy``
    and ``dx`` are in those pixels: canvas ``(y, x)`` matches surface
    ``(y + dy, x + dx)``. ``dy0`` and ``dx0`` are the same shift in level-0
    pixels, ``px_scale`` times the image shift. A level-2 pair uses 4.
    """
    surface_image = _plane(surface, "surface")
    canvas_image = _plane(canvas, "canvas")
    if (
        not isinstance(window, Sequence)
        or isinstance(window, (str, bytes))
        or len(window) != 4
        or any(
            isinstance(value, bool) or not isinstance(value, Integral)
            for value in window
        )
    ):
        raise ValueError("window must be four integers y, x, height, width")
    y, x, height, width = (int(value) for value in window)
    if (
        isinstance(max_shift, bool)
        or not isinstance(max_shift, Integral)
        or int(max_shift) < 1
    ):
        raise ValueError("max_shift must be a positive integer")
    max_shift = int(max_shift)
    if min(height, width) < 2:
        raise ValueError("window must be at least 2 pixels on each side")
    if (
        isinstance(px_scale, bool)
        or not isinstance(px_scale, (int, float))
        or not np.isfinite(px_scale)
        or float(px_scale) <= 0
    ):
        raise ValueError("px_scale must be a positive finite number")
    if len(origin) != 2 or any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not np.isfinite(value)
        for value in origin
    ):
        raise ValueError("origin must be two finite level-0 coordinates")
    canvas_y, canvas_x = canvas_image.shape
    if y < 0 or x < 0 or y + height > canvas_y or x + width > canvas_x:
        raise ValueError(
            f"window {tuple(window)} must lie inside the canvas, shape {canvas_image.shape}"
        )
    limit_y, limit_x = surface_image.shape
    if (
        y < max_shift
        or x < max_shift
        or y + height + max_shift > limit_y
        or x + width + max_shift > limit_x
    ):
        raise ValueError(
            "window must lie at least max_shift pixels inside the surface; "
            "a shift that would leave the image is not reported as zero"
        )
    search_box = (
        y - max_shift,
        y + height + max_shift,
        x - max_shift,
        x + width + max_shift,
    )
    if highpass_size:
        template = _highpass_region(
            canvas_image, y, y + height, x, x + width, highpass_size
        )
        search = _highpass_region(surface_image, *search_box, highpass_size)
    else:
        template = canvas_image[y : y + height, x : x + width]
        search = surface_image[
            search_box[0] : search_box[1], search_box[2] : search_box[3]
        ]
    template = np.asarray(template, dtype=np.float32)
    search = np.asarray(search, dtype=np.float32)
    if not np.isfinite(template).any() or float(np.nanstd(template)) == 0.0:
        raise CanvasShiftNotLocated(
            "canvas window has no contrast after high-pass; the shift is unknown"
        )
    if not np.isfinite(search).any() or float(np.nanstd(search)) == 0.0:
        raise CanvasShiftNotLocated(
            "surface patch has no contrast after high-pass; the shift is unknown"
        )
    response = _masked_ncc(template, search, max_shift)
    if not np.isfinite(response).any():
        raise CanvasShiftNotLocated(
            "no shift had enough finite overlap to score; the shift is not located"
        )
    peak_index = np.unravel_index(int(np.nanargmax(response)), response.shape)
    peak = float(response[peak_index])
    if not np.isfinite(peak) or peak < min_ncc:
        raise CanvasShiftNotLocated(
            f"best correlation is {peak:.3f}, below {min_ncc}; the shift is not located"
        )
    row, col = (int(peak_index[0]), int(peak_index[1]))
    if row in (0, response.shape[0] - 1) or col in (0, response.shape[1] - 1):
        raise CanvasShiftNotLocated(
            f"correlation peaks on the search boundary at {(row - max_shift, col - max_shift)}; "
            f"the shift may exceed +/-{max_shift} px and is not located"
        )
    dy = (row - max_shift) + _parabola(
        float(response[row - 1, col]), peak, float(response[row + 1, col])
    )
    dx = (col - max_shift) + _parabola(
        float(response[row, col - 1]), peak, float(response[row, col + 1])
    )
    scale = float(px_scale)
    # Mean of the integer pixel coordinates in the window. y + height/2 is
    # half a pixel past that mean for every window height, not only even ones.
    center_y = y + (height - 1) / 2.0
    center_x = x + (width - 1) / 2.0
    return {
        "y": center_y,
        "x": center_x,
        "dy": float(dy),
        "dx": float(dx),
        "y0": float(origin[0]) + center_y * scale,
        "x0": float(origin[1]) + center_x * scale,
        "dy0": float(dy) * scale,
        "dx0": float(dx) * scale,
        "ncc": peak,
        "px_scale": scale,
    }


def _drift(slope: float, positions: Sequence[float]) -> float:
    if not positions:
        return 0.0
    return abs(slope) * (max(positions) - min(positions))


def _span(values: np.ndarray) -> float:
    return float(np.max(values) - np.min(values))


def _on_a_line(ys: np.ndarray, xs: np.ndarray) -> str | None:
    """``"axis"`` for a row or column of centres, ``"tilted"`` for a correlated line."""
    sd_y, sd_x = float(ys.std()), float(xs.std())
    if sd_y == 0.0 or sd_x == 0.0:
        return "axis"
    r = float(np.mean((ys - ys.mean()) * (xs - xs.mean()))) / (sd_y * sd_x)
    return "tilted" if r * r >= COLLINEAR_R2 else None


def _separable_slope(positions: np.ndarray, shifts: np.ndarray) -> tuple[float, float]:
    """Intercept and one slope. A drift under one pixel stays a constant."""
    if len(positions) == 1 or _span(positions) == 0.0:
        return float(shifts.mean()), 0.0
    design = np.column_stack([np.ones(len(positions)), positions])
    intercept, slope = np.linalg.lstsq(design, shifts, rcond=None)[0]
    if _drift(float(slope), positions.tolist()) < DRIFT_PX:
        return float(shifts.mean()), 0.0
    if abs(float(slope)) >= MAX_SLOPE:
        raise ValueError(
            f"fitted slope {float(slope):.4g} is outside +/-{MAX_SLOPE}; "
            "this is not a canvas-size residual"
        )
    return float(intercept), float(slope)


def _affine_terms(
    ys: np.ndarray, xs: np.ndarray, shifts: np.ndarray
) -> tuple[float, float, float]:
    """``shift = a + b*y + c*x``. A dropped term is removed and the rest are refit.

    Two points cannot identify both slopes, so the caller uses the separable
    fit there. Three or more points use this fit. If the fitted values only
    wander by under a pixel, the whole axis collapses to their mean. A
    coefficient whose own change across the span is under ``COEF_FLOOR_PX``
    is dropped. Zeroing it and keeping the joint intercept would leave that
    term's mean in the intercept, about a tenth of a pixel, so the remaining
    terms are fit again.
    """
    names: list[str] = []
    columns: list[np.ndarray] = []
    if _span(ys) > 0.0:
        names.append("y")
        columns.append(ys)
    if _span(xs) > 0.0:
        names.append("x")
        columns.append(xs)
    if not names or len(ys) < 1 + len(names):
        intercept, slope = _separable_slope(ys, shifts)
        return intercept, slope, 0.0
    full = np.column_stack([np.ones(len(ys)), *columns])
    coef = np.linalg.lstsq(full, shifts, rcond=None)[0]
    slopes = {name: float(value) for name, value in zip(names, coef[1:], strict=True)}
    by = slopes.get("y", 0.0)
    bx = slopes.get("x", 0.0)
    fitted = float(coef[0]) + by * ys + bx * xs
    if _span(fitted) < DRIFT_PX:
        return float(shifts.mean()), 0.0, 0.0
    keep: list[str] = []
    if "y" in slopes and abs(by) * _span(ys) >= COEF_FLOOR_PX:
        keep.append("y")
    if "x" in slopes and abs(bx) * _span(xs) >= COEF_FLOOR_PX:
        keep.append("x")
    if not keep:
        return float(shifts.mean()), 0.0, 0.0
    if len(keep) != len(names):
        reduced = [np.ones(len(ys))]
        for name in keep:
            reduced.append(ys if name == "y" else xs)
        coef = np.linalg.lstsq(np.column_stack(reduced), shifts, rcond=None)[0]
    intercept = float(coef[0])
    by = 0.0
    bx = 0.0
    for name, value in zip(keep, coef[1:], strict=True):
        if name == "y":
            by = float(value)
        else:
            bx = float(value)
    for name, slope in (("y", by), ("x", bx)):
        if abs(slope) >= MAX_SLOPE:
            raise ValueError(
                f"fitted {name} slope {slope:.4g} is outside +/-{MAX_SLOPE}; "
                "this is not a canvas-size residual"
            )
    return intercept, by, bx


def fit_shift(regions: Sequence[dict[str, float]]) -> dict[str, float | str]:
    """Fit ``dy = ay + sy*y + cy*x`` and ``dx = ax + cx*y + sx*x``.

    Fewer than three points fit each axis on its own and leave the cross terms
    at zero, so two readings of one constant stay a constant. Three or more
    points fit the full model. Centres on one row or column cannot fit the
    slope across it; that slope stays 0, with a warning. Centres on a tilted
    line (see ``COLLINEAR_R2``) cannot tell a y slope from an x slope, so
    they get the per-axis fit, with a warning. A coefficient whose own
    change across the measured span is under ``COEF_FLOOR_PX`` is dropped and the remaining
    terms are fit again. An axis whose fitted peak-to-peak is under one pixel
    collapses to the mean.

    The only keys read are ``y``, ``x``, ``dy``, and ``dx``. ``measure_shift``
    also returns ``y0``, ``x0``, ``dy0``, and ``dx0``; those names are not
    consulted. To fit in level-0 pixels, put the level-0 centres and shifts
    in ``y``, ``x``, ``dy``, and ``dx``.
    """
    if (
        not isinstance(regions, Sequence)
        or isinstance(regions, (str, bytes))
        or not regions
    ):
        raise ValueError("at least one measured region is required")
    rows = []
    for region in regions:
        if not isinstance(region, dict):
            raise ValueError("each region must be a mapping with y, x, dy, dx")
        try:
            rows.append(tuple(float(region[key]) for key in ("y", "x", "dy", "dx")))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("each region needs finite y, x, dy, dx") from exc
    ys, xs, dys, dxs = (
        np.asarray(column, dtype=np.float64) for column in zip(*rows, strict=True)
    )
    if not np.isfinite(np.concatenate([ys, xs, dys, dxs])).all():
        raise ValueError("region coordinates and shifts must be finite")

    line = _on_a_line(ys, xs) if len(rows) >= 3 else None
    if line is not None:
        how = (
            "each axis is fit on its own, since y and x slopes cannot be told apart"
            if line == "tilted"
            else "the slope across it stays 0"
        )
        warnings.warn(
            "the window centres lie on one line, so the offset's change across "
            f"that line is not measured; {how}. Add a window off the line",
            UserWarning,
            stacklevel=2,
        )
    if len(rows) < 3 or line == "tilted":
        ay, sy = _separable_slope(ys, dys)
        ax, sx = _separable_slope(xs, dxs)
        cy, cx = 0.0, 0.0
    else:
        ay, sy, cy = _affine_terms(ys, xs, dys)
        ax, cx, sx = _affine_terms(ys, xs, dxs)
    slopes = (sy, cy, cx, sx)
    if any(slope != 0.0 for slope in slopes):
        model = "affine" if cy != 0.0 or cx != 0.0 else "linear"
    else:
        model = "constant"
    return {
        "model": model,
        "ay": ay,
        "sy": sy,
        "cy": cy,
        "ax": ax,
        "cx": cx,
        "sx": sx,
    }


def resample_to_tifxyz(
    canvas: np.ndarray,
    ay: float,
    sy: float,
    ax: float,
    sx: float,
    out_shape: tuple[int, int] | None = None,
    *,
    cy: float = 0.0,
    cx: float = 0.0,
    nearest: bool | None = None,
) -> np.ndarray:
    """Read the canvas onto the tifxyz frame.

    Output pixel ``(y_t, x_t)`` comes from the canvas pixel ``(y, x)`` that
    satisfies ``y_t = ay + (1+sy)*y + cy*x`` and
    ``x_t = ax + cx*y + (1+sx)*x``. With the cross terms at zero that is
    ``((y_t - ay) / (1 + sy), (x_t - ax) / (1 + sx))``. ``out_shape`` is the
    tifxyz grid, which is not the canvas shape when the two sizes differ.

    ``nearest=None`` uses nearest neighbor for an integer or bool canvas and
    bilinear for a float. ``np.issubdtype(np.bool_, np.integer)`` is false, so
    a mask is matched on its dtype explicitly and is not blended. An integer
    label stays on its values and comes back in its own dtype. Pass
    ``nearest=False`` to blend those values (the result is then float32, as
    it is for a float canvas), or ``nearest=True`` to keep a float label intact.
    """
    source = _plane(canvas, "canvas")
    integer = bool(np.issubdtype(source.dtype, np.integer) or source.dtype == np.bool_)
    if nearest is None:
        nearest = integer
        if nearest:
            warnings.warn(
                "integer label resampled with nearest neighbor so values stay "
                "intact; pass nearest=False to blend them",
                UserWarning,
                stacklevel=2,
            )
    elif not isinstance(nearest, bool):
        raise ValueError("nearest must be True, False, or None")
    # float32 holds every 8- and 16-bit value exactly; wider integers need float64.
    work = np.float64 if integer and source.dtype.itemsize > 2 else np.float32
    image = np.where(np.isfinite(source), source, 0).astype(work)
    for name, slope in (("sy", sy), ("sx", sx), ("cy", cy), ("cx", cx)):
        if (
            isinstance(slope, bool)
            or not isinstance(slope, (int, float))
            or not np.isfinite(slope)
        ):
            raise ValueError(f"{name} must be a finite number")
        if abs(float(slope)) >= MAX_SLOPE:
            raise ValueError(f"{name} must be inside +/-{MAX_SLOPE}")
    for name, intercept in (("ay", ay), ("ax", ax)):
        if (
            isinstance(intercept, bool)
            or not isinstance(intercept, (int, float))
            or not np.isfinite(intercept)
        ):
            raise ValueError(f"{name} must be a finite number")
    if out_shape is None:
        out_h, out_w = image.shape
    else:
        if len(out_shape) != 2 or any(
            isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 1
            for value in out_shape
        ):
            raise ValueError("out_shape must be two positive integers")
        out_h, out_w = int(out_shape[0]), int(out_shape[1])
    y_scale = 1.0 + float(sy)
    x_scale = 1.0 + float(sx)
    det = y_scale * x_scale - float(cy) * float(cx)
    if abs(det) < 1e-6:
        raise ValueError("canvas scale must not collapse an axis")
    yy = np.arange(out_h, dtype=np.float64)[:, None]
    xx = np.arange(out_w, dtype=np.float64)[None, :]
    map_y = (x_scale * (yy - float(ay)) - float(cy) * (xx - float(ax))) / det
    map_x = (y_scale * (xx - float(ax)) - float(cx) * (yy - float(ay))) / det
    interpolation = cv2.INTER_NEAREST if nearest else cv2.INTER_LINEAR
    out = cv2.remap(
        image,
        np.ascontiguousarray(map_x, dtype=np.float32),
        np.ascontiguousarray(map_y, dtype=np.float32),
        interpolation,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    if nearest and integer:
        return out.astype(source.dtype)
    return out.astype(np.float32, copy=False)


def correct_canvas(
    surface: np.ndarray,
    canvas: np.ndarray,
    windows: Sequence[Sequence[int]],
    max_shift: int = 64,
    *,
    nearest: bool | None = None,
    aligned_tolerance: float = 1.0,
    out_shape: tuple[int, int] | None = None,
    px_scale: float = 1.0,
    origin: tuple[float, float] = (0.0, 0.0),
) -> dict[str, object]:
    """Measure each window, fit the shift, and resample onto ``out_shape``.

    ``out_shape`` is the tifxyz grid. It defaults to the surface's shape: the
    surface is sampled on that grid, and the canvas may be another size. An
    integer canvas is resampled with nearest neighbor unless ``nearest`` is
    passed. ``aligned_before`` is True when every window's shift is within
    ``aligned_tolerance`` level-0 pixels (``px_scale`` times the image
    pixels) on both axes.
    """
    if (
        not isinstance(windows, Sequence)
        or isinstance(windows, (str, bytes))
        or not windows
    ):
        raise ValueError("at least one window is required")
    regions = [
        measure_shift(
            surface, canvas, window, max_shift, px_scale=px_scale, origin=origin
        )
        for window in windows
    ]
    fitted = fit_shift(regions)
    if out_shape is None:
        out_shape = _plane(surface, "surface").shape
    corrected = resample_to_tifxyz(
        canvas,
        float(fitted["ay"]),
        float(fitted["sy"]),
        float(fitted["ax"]),
        float(fitted["sx"]),
        out_shape,
        cy=float(fitted["cy"]),
        cx=float(fitted["cx"]),
        nearest=nearest,
    )
    aligned = all(
        abs(float(region["dy0"])) <= aligned_tolerance
        and abs(float(region["dx0"])) <= aligned_tolerance
        for region in regions
    )
    return {
        "regions": regions,
        "fit": fitted,
        "aligned_before": aligned,
        "corrected": corrected,
    }


def _load_array(path: Path) -> np.ndarray:
    if path.suffix == ".npy":
        array = np.load(path)
    else:
        array = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if array is None:
            raise ValueError(f"could not read {path}")
    return _plane(array, str(path))


# What cv2.imwrite stores without changing a value (checked with OpenCV 4.13
# by writing and reading back). A PNG of any other dtype is converted to 8
# bits and imwrite still returns True: int32 70000 becomes 255 and float32
# 0.7 becomes 1.
_TIFF_KINDS = (np.uint8, np.uint16, np.int16, np.int32, np.float32, np.float64)
_WRITABLE = {".png": (np.uint8, np.uint16), ".tif": _TIFF_KINDS, ".tiff": _TIFF_KINDS}


def _check_writable(path: Path, array: np.ndarray) -> None:
    if path.suffix.lower() == ".npy":
        return
    kinds = _WRITABLE.get(path.suffix.lower())
    if kinds is None or array.dtype.type not in kinds:
        raise ValueError(
            f"{path.name} cannot hold a {array.dtype} result without changing its "
            "values; write .npy or .tif (a uint8 or uint16 label can also be .png)"
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Measure how far a canvas sits from its tifxyz grid and resample it onto that grid. "
            "Canvas pixel (y, x) matches tifxyz cell (y + dy, x + dx)."
        ),
        epilog=(
            "Exit status: 0 when every window is within 1 level-0 px; 1 when a shift was "
            "measured; 2 on a usage error, an unreadable input, or an --out format that "
            "cannot hold the result; 3 when a window's shift could not be located."
        ),
    )
    parser.add_argument(
        "surface", type=Path, help="surface sampled on the tifxyz grid (.npy or image)"
    )
    parser.add_argument(
        "canvas", type=Path, help="canvas or label in canvas pixels (.npy or image)"
    )
    parser.add_argument(
        "--window",
        action="append",
        nargs=4,
        type=int,
        metavar=("Y", "X", "H", "W"),
        required=True,
        help="window in the shared index space; repeat for a linear fit",
    )
    parser.add_argument("--max-shift", type=int, default=64)
    parser.add_argument(
        "--px-scale",
        type=float,
        default=1.0,
        help="level-0 pixels per image pixel; 4 when the pair is level 2",
    )
    parser.add_argument(
        "--origin",
        nargs=2,
        type=float,
        metavar=("Y", "X"),
        default=(0.0, 0.0),
        help="level-0 coordinate of image pixel 0 (the centre of that pixel). "
        "A reported level-0 centre is origin + image_centre * --px-scale",
    )
    parser.add_argument(
        "--out-shape",
        nargs=2,
        type=int,
        metavar=("H", "W"),
        help="tifxyz grid the resampled canvas is written on (default: the surface's shape)",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--out", type=Path, help="write the canvas resampled onto the tifxyz frame"
    )
    resample = parser.add_mutually_exclusive_group()
    resample.add_argument(
        "--nearest",
        action="store_true",
        help="nearest-neighbor resample. This is the default for an integer label",
    )
    resample.add_argument(
        "--linear",
        action="store_true",
        help="bilinear resample even for an integer label, which blends 0/255",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        surface = _load_array(args.surface)
        canvas = _load_array(args.canvas)
        if args.linear:
            nearest: bool | None = False
        elif args.nearest:
            nearest = True
        else:
            nearest = None
        result = correct_canvas(
            surface,
            canvas,
            args.window,
            args.max_shift,
            nearest=nearest,
            out_shape=tuple(args.out_shape) if args.out_shape else None,
            px_scale=args.px_scale,
            origin=(args.origin[0], args.origin[1]),
        )
    except CanvasShiftNotLocated as exc:
        print(f"not located: {exc}", file=sys.stderr)
        return 3
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    corrected = result.pop("corrected")
    assert isinstance(corrected, np.ndarray)
    if args.out is not None:
        try:
            _check_writable(args.out, corrected)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if args.out.suffix.lower() == ".npy":
            np.save(args.out, corrected)
        else:
            if not cv2.imwrite(str(args.out), corrected):
                print(f"error: could not write {args.out}", file=sys.stderr)
                return 2
    payload = {
        "aligned_before": result["aligned_before"],
        "fit": result["fit"],
        "regions": result["regions"],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        fit = result["fit"]
        assert isinstance(fit, dict)
        print(
            "model "
            f"{fit['model']} in image pixels "
            "(y and x are image-pixel window centres, not the level-0 centres below): "
            f"dy = {fit['ay']:.3f} + {fit['sy']:.6g} * y + {fit['cy']:.6g} * x, "
            f"dx = {fit['ax']:.3f} + {fit['cx']:.6g} * y + {fit['sx']:.6g} * x"
        )
        print(f"aligned_before: {result['aligned_before']}")
        regions = result["regions"]
        assert isinstance(regions, list)
        for region in regions:
            print(
                f"  image center ({region['y']:.2f}, {region['x']:.2f}) "
                f"shift ({region['dy']:.2f}, {region['dx']:.2f}); "
                f"level-0 center ({region['y0']:.1f}, {region['x0']:.1f}) "
                f"shift ({region['dy0']:.2f}, {region['dx0']:.2f}) "
                f"ncc {region['ncc']:.3f}"
            )
    return 0 if result["aligned_before"] else 1


if __name__ == "__main__":
    sys.exit(main())
