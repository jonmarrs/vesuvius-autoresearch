"""Put a canvas-space ink label onto the tifxyz grid it was drawn beside.

Some released training segments ship a canvas whose shape matches the tifxyz
grid, so a shape check accepts it, while the ink itself sits on the wrong
pixels. A constant offset covers the one-cell and integer shifts. Paris-4-style
segments also change that offset across the sheet: ``dy = ay + sy * y`` and
the same in x, with the slope the residual of a canvas that is not the same
size as the grid.

Measurement convention, locked by tests: canvas pixel ``(y, x)`` corresponds
to tifxyz cell ``(y + dy, x + dx)``. Resampling into the tifxyz frame therefore
reads the canvas at ``((y - ay) / (1 + sy), (x - ax) / (1 + sx))``.

The inputs are two same-shaped images you already have: the surface sampled on
the tifxyz grid, and the canvas (or a label painted on it). This module does
not fetch scroll volumes.

One window::

    python -m repro.sota_data.canvas_shift surface.npy canvas.npy \\
        --window Y X H W --max-shift 64 --json

Several windows fit the linear residual. ``--out corrected.npy`` writes the
canvas resampled onto the tifxyz frame. ``--nearest`` keeps label values intact.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from numbers import Integral
from pathlib import Path

import cv2
import numpy as np

MIN_NCC = 0.5
DRIFT_PX = 1.0
MAX_SLOPE = 0.5


class CanvasShiftNotLocated(ValueError):
    """The search did not find a shift that places the canvas on the surface."""


def _plane(image: np.ndarray, what: str) -> np.ndarray:
    array = np.asarray(image)
    if array.ndim == 3 and array.shape[-1] in (1, 3, 4):
        array = array[..., 0]
    if array.ndim != 2:
        raise ValueError(f"{what} must be a 2D image, got shape {array.shape}")
    if array.size == 0 or not np.isfinite(array.astype(np.float64, copy=False)).all():
        raise ValueError(f"{what} must be a nonempty finite image")
    return np.ascontiguousarray(array)


def highpass(image: np.ndarray, size: int = 31) -> np.ndarray:
    """Remove a locally linear background. A pure ramp becomes ~0 inside the image."""
    if isinstance(size, bool) or not isinstance(size, Integral) or int(size) < 1:
        raise ValueError("high-pass size must be a positive integer")
    size = (
        int(size) | 1
    )  # box filters use an odd window; an even size would shift the phase
    plane = _plane(image, "image").astype(np.float32)
    blurred = cv2.blur(plane, (size, size))
    return plane - blurred


def _parabola(left: float, center: float, right: float) -> float:
    denom = left - 2.0 * center + right
    if denom == 0.0 or not np.isfinite(denom):
        return 0.0
    delta = 0.5 * (left - right) / denom
    if not np.isfinite(delta):
        return 0.0
    return float(np.clip(delta, -1.0, 1.0))


def measure_shift(
    surface: np.ndarray,
    canvas: np.ndarray,
    window: Sequence[int],
    max_shift: int = 64,
    *,
    highpass_size: int = 31,
    min_ncc: float = MIN_NCC,
) -> dict[str, float | int]:
    """Shift that places this canvas window onto the tifxyz-frame surface.

    ``window`` is ``(y, x, height, width)`` in the shared index space. The
    window must sit at least ``max_shift`` pixels inside both images. The
    returned ``dy, dx`` are subpixel: canvas ``(y, x)`` matches surface
    ``(y + dy, x + dx)``.
    """
    surface_image = _plane(surface, "surface")
    canvas_image = _plane(canvas, "canvas")
    if surface_image.shape != canvas_image.shape:
        raise ValueError(
            f"surface shape {surface_image.shape} and canvas shape {canvas_image.shape} differ"
        )
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
    limit_y, limit_x = surface_image.shape
    if (
        y < max_shift
        or x < max_shift
        or y + height + max_shift > limit_y
        or x + width + max_shift > limit_x
    ):
        raise ValueError(
            "window must lie at least max_shift pixels inside both images; "
            "a shift that would leave the image is not reported as zero"
        )
    if highpass_size:
        surface_image = highpass(surface_image, highpass_size)
        canvas_image = highpass(canvas_image, highpass_size)
    template = np.ascontiguousarray(
        canvas_image[y : y + height, x : x + width], dtype=np.float32
    )
    search = np.ascontiguousarray(
        surface_image[
            y - max_shift : y + height + max_shift,
            x - max_shift : x + width + max_shift,
        ],
        dtype=np.float32,
    )
    if float(np.std(template)) == 0.0 or float(np.std(search)) == 0.0:
        raise CanvasShiftNotLocated(
            "canvas window or surface patch has no contrast after high-pass; the shift is unknown"
        )
    response = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
    if response.shape != (2 * max_shift + 1, 2 * max_shift + 1):
        raise CanvasShiftNotLocated(
            f"correlation search returned shape {response.shape}, expected "
            f"{(2 * max_shift + 1, 2 * max_shift + 1)}"
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
    return {
        "y": y + height / 2.0,
        "x": x + width / 2.0,
        "dy": float(dy),
        "dx": float(dx),
        "ncc": peak,
    }


def _drift(slope: float, positions: Sequence[float]) -> float:
    if not positions:
        return 0.0
    return abs(slope) * (max(positions) - min(positions))


def fit_shift(regions: Sequence[dict[str, float]]) -> dict[str, float | str]:
    """Fit ``dy = ay + sy * y`` and ``dx = ax + sx * x`` to measured regions.

    A slope is kept only when the offset changes by at least one pixel across
    the observed positions. Two noisy readings of one constant therefore stay
    a constant. ``y`` and ``x`` are the window centers from ``measure_shift``.
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

    def _axis(positions: np.ndarray, shifts: np.ndarray) -> tuple[float, float]:
        if len(positions) == 1 or float(np.ptp(positions)) == 0.0:
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

    ay, sy = _axis(ys, dys)
    ax, sx = _axis(xs, dxs)
    model = "linear" if sy != 0.0 or sx != 0.0 else "constant"
    return {"model": model, "ay": ay, "sy": sy, "ax": ax, "sx": sx}


def resample_to_tifxyz(
    canvas: np.ndarray,
    ay: float,
    sy: float,
    ax: float,
    sx: float,
    out_shape: tuple[int, int] | None = None,
    *,
    nearest: bool = False,
) -> np.ndarray:
    """Read the canvas onto the tifxyz frame.

    Output pixel ``(y, x)`` comes from canvas
    ``((y - ay) / (1 + sy), (x - ax) / (1 + sx))``. ``nearest`` is the label
    path: thresholded ink stays intact.
    """
    image = _plane(canvas, "canvas")
    for name, slope in (("sy", sy), ("sx", sx)):
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
    if abs(y_scale) < 1e-6 or abs(x_scale) < 1e-6:
        raise ValueError("canvas scale must not collapse an axis")
    rows = (np.arange(out_h, dtype=np.float32) - np.float32(ay)) / np.float32(y_scale)
    cols = (np.arange(out_w, dtype=np.float32) - np.float32(ax)) / np.float32(x_scale)
    map_y = np.broadcast_to(rows[:, None], (out_h, out_w)).copy()
    map_x = np.broadcast_to(cols[None, :], (out_h, out_w)).copy()
    interpolation = cv2.INTER_NEAREST if nearest else cv2.INTER_LINEAR
    return cv2.remap(
        image,
        map_x,
        map_y,
        interpolation,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )


def correct_canvas(
    surface: np.ndarray,
    canvas: np.ndarray,
    windows: Sequence[Sequence[int]],
    max_shift: int = 64,
    *,
    nearest: bool = False,
    aligned_tolerance: float = 1.0,
) -> dict[str, object]:
    """Measure each window, fit the shift, and resample the canvas."""
    if (
        not isinstance(windows, Sequence)
        or isinstance(windows, (str, bytes))
        or not windows
    ):
        raise ValueError("at least one window is required")
    regions = [measure_shift(surface, canvas, window, max_shift) for window in windows]
    fitted = fit_shift(regions)
    corrected = resample_to_tifxyz(
        canvas,
        float(fitted["ay"]),
        float(fitted["sy"]),
        float(fitted["ax"]),
        float(fitted["sx"]),
        nearest=nearest,
    )
    aligned = all(
        abs(float(region["dy"])) <= aligned_tolerance
        and abs(float(region["dx"])) <= aligned_tolerance
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Measure how far a canvas sits from its tifxyz grid and resample it onto that grid. "
            "Canvas pixel (y, x) matches tifxyz cell (y + dy, x + dx)."
        )
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
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--out", type=Path, help="write the canvas resampled onto the tifxyz frame"
    )
    parser.add_argument(
        "--nearest",
        action="store_true",
        help="nearest-neighbor resample, for a binary or indexed label",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        surface = _load_array(args.surface)
        canvas = _load_array(args.canvas)
        result = correct_canvas(
            surface,
            canvas,
            args.window,
            args.max_shift,
            nearest=args.nearest,
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    corrected = result.pop("corrected")
    assert isinstance(corrected, np.ndarray)
    if args.out is not None:
        if args.out.suffix == ".npy":
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
            f"model {fit['model']}: dy = {fit['ay']:.3f} + {fit['sy']:.6g} * y, "
            f"dx = {fit['ax']:.3f} + {fit['sx']:.6g} * x"
        )
        print(f"aligned_before: {result['aligned_before']}")
        regions = result["regions"]
        assert isinstance(regions, list)
        for region in regions:
            print(
                f"  center ({region['y']:.1f}, {region['x']:.1f}) "
                f"shift ({region['dy']:.2f}, {region['dx']:.2f}) ncc {region['ncc']:.3f}"
            )
    return 0 if result["aligned_before"] else 1


if __name__ == "__main__":
    sys.exit(main())
