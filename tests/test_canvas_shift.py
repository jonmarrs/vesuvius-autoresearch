"""A canvas that shares the tifxyz shape is not yet on the tifxyz grid.

Canvas pixel (y, x) corresponds to tifxyz cell (y + dy, x + dx). A constant
(dy, dx) is the one-cell and integer label shift. A slope is the Paris-4
residual, where the offset grows because the canvas size is not the grid size.
The fit is rejected as a line when that growth stays under one pixel: two noisy
readings of one constant must not become a drift.
"""

import json
import os
import sys

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data.canvas_shift import (
    CanvasShiftNotLocated,
    correct_canvas,
    fit_shift,
    level0_centers,
    main,
    measure_shift,
    resample_to_tifxyz,
    sample_tifxyz,
    sample_volume_trilinear,
)


def _independent_surface(canvas, ay, sy, ax, sx, cy=0.0, cx=0.0):
    """Bilinear read of the same map, not going through cv2.remap."""
    height, width = canvas.shape
    det = (1.0 + sy) * (1.0 + sx) - cy * cx
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float64)
    src_y = ((1.0 + sx) * (yy - ay) - cy * (xx - ax)) / det
    src_x = ((1.0 + sy) * (xx - ax) - cx * (yy - ay)) / det
    y0 = np.floor(src_y).astype(np.int64)
    x0 = np.floor(src_x).astype(np.int64)
    fy = src_y - y0
    fx = src_x - x0

    def _at(row, col):
        ok = (row >= 0) & (row < height) & (col >= 0) & (col < width)
        gathered = canvas[np.clip(row, 0, height - 1), np.clip(col, 0, width - 1)]
        return np.where(ok, gathered, 0.0)

    return (
        _at(y0, x0) * (1.0 - fy) * (1.0 - fx)
        + _at(y0 + 1, x0) * fy * (1.0 - fx)
        + _at(y0, x0 + 1) * (1.0 - fy) * fx
        + _at(y0 + 1, x0 + 1) * fy * fx
    ).astype(np.float32)


def _texture(height: int, width: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    noise = rng.normal(size=(height, width)).astype(np.float32)
    return cv2.GaussianBlur(noise, (0, 0), 1.2)


def test_positive_dy_places_the_canvas_pixel_later_on_the_tifxyz_grid():
    """The sign the resampler and the search have to share.

    Ink drawn at canvas row 30 belongs at tifxyz row 38 when dy is +8, and at
    canvas column 40 belongs at tifxyz column 35 when dx is -5.
    """
    canvas = np.zeros((96, 96), np.float32)
    canvas[30:36, 40:48] = 255
    surface = np.zeros_like(canvas)
    surface[38:44, 35:43] = 255
    found = measure_shift(
        surface, canvas, (16, 16, 48, 48), max_shift=16, highpass_size=0
    )
    assert found["dy"] == pytest.approx(8, abs=0.15)
    assert found["dx"] == pytest.approx(-5, abs=0.15)
    corrected = resample_to_tifxyz(canvas, ay=8, sy=0, ax=-5, sx=0, nearest=True)
    assert corrected[40, 42] == 255  # canvas (32, 47) landed at tifxyz (40, 42)
    assert corrected[30, 40] == 0


def test_a_constant_resample_reads_canvas_at_y_minus_dy():
    rows = np.arange(80, dtype=np.float32)[:, None].repeat(60, axis=1)
    out = resample_to_tifxyz(rows, ay=4.0, sy=0.0, ax=-2.0, sx=0.0)
    assert out[40, 20] == pytest.approx(36.0, abs=0.05)  # source row 40 - 4
    assert out[40, 20] == pytest.approx((40 - 4.0) / 1.0, abs=0.05)
    cols = np.arange(60, dtype=np.float32)[None, :].repeat(80, axis=0)
    out_c = resample_to_tifxyz(cols, ay=0.0, sy=0.0, ax=-2.0, sx=0.0)
    assert out_c[40, 20] == pytest.approx(22.0, abs=0.05)  # source col 20 - (-2)


def test_a_linear_resample_uses_the_canvas_size_residual():
    """output[y] = canvas[(y - ay) / (1 + sy)], the inverse of y_t = ay + (1+sy)*y_c."""
    rows = np.arange(100, dtype=np.float32)[:, None].repeat(40, axis=1)
    out = resample_to_tifxyz(rows, ay=3.0, sy=0.1, ax=0.0, sx=0.0)
    assert out[47, 10] == pytest.approx((47 - 3.0) / 1.1, abs=0.05)


def test_nearest_resample_keeps_a_label_binary():
    label = np.zeros((80, 80), np.uint8)
    label[20:40, 20:40] = 255
    out = resample_to_tifxyz(label, ay=6.4, sy=0.0, ax=-3.2, sx=0.0, nearest=True)
    assert set(np.unique(out)).issubset({0, 255})
    assert out[32, 27] == 255
    assert out[8, 8] == 0


def test_an_identical_canvas_is_already_on_the_grid():
    image = _texture(160, 160)
    found = measure_shift(image, image, (40, 40, 48, 48), max_shift=24)
    assert found["dy"] == pytest.approx(0, abs=0.15)
    assert found["dx"] == pytest.approx(0, abs=0.15)
    result = correct_canvas(image, image, [(40, 40, 48, 48)], max_shift=24)
    assert result["aligned_before"] is True
    assert result["fit"]["model"] == "constant"


def test_same_shape_does_not_mean_aligned():
    """The integer (+30, -50) class of miss: shapes match, content does not."""
    canvas = _texture(180, 180, seed=1)
    surface = resample_to_tifxyz(canvas, ay=30, sy=0, ax=-50, sx=0)
    window = (60, 60, 40, 40)
    found = measure_shift(surface, canvas, window, max_shift=56)
    assert found["dy"] == pytest.approx(30, abs=0.2)
    assert found["dx"] == pytest.approx(-50, abs=0.2)
    result = correct_canvas(surface, canvas, [window], max_shift=56)
    assert result["aligned_before"] is False
    assert result["fit"]["model"] == "constant"
    assert result["fit"]["ay"] == pytest.approx(30, abs=0.25)
    assert result["fit"]["ax"] == pytest.approx(-50, abs=0.25)


def test_half_pixel_shift_is_recovered():
    canvas = _texture(160, 160, seed=2)
    surface = resample_to_tifxyz(canvas, ay=0.5, sy=0.0, ax=-0.4, sx=0.0)
    found = measure_shift(surface, canvas, (40, 40, 64, 64), max_shift=16)
    assert found["dy"] == pytest.approx(0.5, abs=0.15)
    assert found["dx"] == pytest.approx(-0.4, abs=0.15)


def test_a_shared_ramp_does_not_move_the_peak():
    canvas = _texture(180, 180, seed=3)
    surface = resample_to_tifxyz(canvas, ay=6.0, sy=0.0, ax=-4.0, sx=0.0)
    ramp = (np.arange(180, dtype=np.float32)[:, None] * 5.0) + (
        np.arange(180, dtype=np.float32)[None, :] * 2.0
    )
    found = measure_shift(surface + ramp, canvas + ramp, (40, 40, 64, 64), max_shift=20)
    assert found["dy"] == pytest.approx(6.0, abs=0.2)
    assert found["dx"] == pytest.approx(-4.0, abs=0.2)


def test_two_regions_within_a_pixel_stay_a_constant():
    fitted = fit_shift(
        [
            {"y": 50.0, "x": 40.0, "dy": 6.0, "dx": -4.0},
            {"y": 150.0, "x": 140.0, "dy": 6.2, "dx": -3.8},
        ]
    )
    assert fitted["model"] == "constant"
    assert fitted["sy"] == 0.0 and fitted["sx"] == 0.0
    assert fitted["ay"] == pytest.approx(6.1)
    assert fitted["ax"] == pytest.approx(-3.9)


def test_a_twelve_pixel_drift_across_the_span_is_a_line():
    fitted = fit_shift(
        [
            {"y": 50.0, "x": 40.0, "dy": 8.0, "dx": -2.6},
            {"y": 150.0, "x": 140.0, "dy": 20.0, "dx": -4.4},
        ]
    )
    assert fitted["model"] == "linear"
    assert fitted["sy"] == pytest.approx(0.12)
    assert fitted["ay"] == pytest.approx(2.0)
    assert fitted["sx"] == pytest.approx(-0.018)
    assert fitted["ax"] == pytest.approx(-1.88, abs=1e-9)
    assert fitted["cy"] == 0.0 and fitted["cx"] == 0.0


def test_one_region_is_only_a_constant():
    fitted = fit_shift([{"y": 80.0, "x": 90.0, "dy": 4.5, "dx": -1.25}])
    assert fitted == {
        "model": "constant",
        "ay": 4.5,
        "sy": 0.0,
        "cy": 0.0,
        "ax": -1.25,
        "cx": 0.0,
        "sx": 0.0,
    }


def test_a_slope_past_a_half_is_not_a_canvas_size_residual():
    with pytest.raises(ValueError, match="slope"):
        fit_shift(
            [
                {"y": 0.0, "x": 0.0, "dy": 0.0, "dx": 0.0},
                {"y": 10.0, "x": 0.0, "dy": 20.0, "dx": 0.0},
            ]
        )


def test_linear_drift_is_measured_fitted_and_put_back():
    """Three windows on a known map. The surface is built without cv2.remap."""
    canvas = _texture(220, 220, seed=4)
    ay, sy, ax, sx = 3.0, 0.02, -2.0, -0.015
    surface = _independent_surface(canvas, ay, sy, ax, sx)
    windows = [
        (32, 32, 32, 32),
        (32, 150, 32, 32),
        (150, 32, 32, 32),
        (150, 150, 32, 32),
    ]
    result = correct_canvas(surface, canvas, windows, max_shift=16)
    fit = result["fit"]
    assert fit["model"] == "linear"
    assert fit["ay"] == pytest.approx(ay, abs=0.35)
    assert fit["sy"] == pytest.approx(sy, abs=0.004)
    assert fit["ax"] == pytest.approx(ax, abs=0.35)
    assert fit["sx"] == pytest.approx(sx, abs=0.004)
    corrected = result["corrected"]
    assert isinstance(corrected, np.ndarray)
    # The border is the remap's constant fill. Compare the interior the windows saw.
    interior = np.s_[48:172, 48:172]
    residual = np.abs(corrected[interior] - surface[interior])
    assert float(np.percentile(residual, 95)) < 0.15


def test_three_regions_keep_a_subpixel_cross_term():
    """The term that is under a pixel on its own is still part of the fit.

    Dropping it is the half-pixel miss on the published w00 segments. Two
    points never get a cross term; this needs a third region.
    """

    def _dy(y, x):
        return 1.5 + 0.01 * y + 0.00002 * x

    def _dx(y, x):
        return -3.0 + 0.00047 * y - 0.008 * x

    points = [(100.0, 200.0), (1100.0, 200.0), (100.0, 20200.0), (1100.0, 20200.0)]
    fitted = fit_shift(
        [{"y": y, "x": x, "dy": _dy(y, x), "dx": _dx(y, x)} for y, x in points]
    )
    assert fitted["model"] == "affine"
    assert fitted["sy"] == pytest.approx(0.01)
    assert fitted["cy"] == pytest.approx(0.00002)
    assert fitted["cx"] == pytest.approx(0.00047)
    assert fitted["sx"] == pytest.approx(-0.008)
    assert fitted["ay"] == pytest.approx(1.5, abs=1e-9)
    assert fitted["ax"] == pytest.approx(-3.0, abs=1e-6)


def test_a_level2_shift_is_reported_in_level0_pixels():
    canvas = _texture(96, 96, seed=9)
    surface = _independent_surface(canvas, ay=3, sy=0, ax=-2, sx=0)
    found = measure_shift(
        surface,
        canvas,
        (16, 16, 48, 48),
        max_shift=12,
        px_scale=4,
        origin=(1000.0, 2000.0),
    )
    assert found["dy"] == pytest.approx(3, abs=0.2)
    assert found["dx"] == pytest.approx(-2, abs=0.2)
    assert found["dy0"] == pytest.approx(found["dy"] * 4)
    assert found["dx0"] == pytest.approx(found["dx"] * 4)
    assert found["y0"] == pytest.approx(1000.0 + found["y"] * 4)
    assert found["x0"] == pytest.approx(2000.0 + found["x"] * 4)


def test_a_tifxyz_hole_does_not_pull_the_shift():
    canvas = _texture(120, 120, seed=10)
    surface = _independent_surface(canvas, ay=5, sy=0, ax=-4, sx=0)
    surface = surface.copy()
    surface[30:70, 30:80] = np.nan
    found = measure_shift(
        surface, canvas, (20, 20, 64, 64), max_shift=16, highpass_size=0
    )
    assert found["dy"] == pytest.approx(5, abs=0.25)
    assert found["dx"] == pytest.approx(-4, abs=0.25)


def test_correct_canvas_writes_the_tifxyz_shape():
    canvas = _texture(80, 90, seed=11)
    surface = _independent_surface(canvas, ay=4, sy=0, ax=-3, sx=0)
    # The tifxyz grid is a different shape from the canvas.
    wider = np.pad(surface, ((0, 10), (0, 0)))
    result = correct_canvas(
        wider[:80, :],
        canvas,
        [(16, 16, 40, 40)],
        max_shift=12,
        out_shape=(90, 90),
    )
    corrected = result["corrected"]
    assert isinstance(corrected, np.ndarray)
    assert corrected.shape == (90, 90)


def test_ct_sampled_at_a_tifxyz_cell_reads_that_voxel():
    """Level-2 voxel i is centred on level-0 coordinate 4*i + 1.5."""
    assert level0_centers(np.array([0, 10]), 4).tolist() == [1.5, 41.5]
    volume = np.zeros((6, 6, 6), np.float32)
    volume[2, 2, 2] = 7
    # stored grid is the full-res grid at scale 1; cell (9.5, 9.5) would be
    # outside this tiny plane, so the plane stores the level-0 point directly.
    plane = np.full((4, 4), -1.0)
    plane[1, 1] = 9.5
    plane[1, 2] = 9.5
    plane[2, 1] = 9.5
    plane[2, 2] = 9.5
    zyx = sample_tifxyz(plane, plane, plane, np.array([1.0]), np.array([1.0]), 1.0, 1.0)
    assert zyx[0, 0].tolist() == pytest.approx([9.5, 9.5, 9.5])
    sampled = sample_volume_trilinear(volume, zyx.reshape(-1, 3), level=2)
    assert sampled[0] == pytest.approx(7.0)
    plane[2, 2] = -1
    holed = sample_tifxyz(
        plane, plane, plane, np.array([1.0]), np.array([1.0]), 1.0, 1.0
    )
    assert np.isnan(holed[0, 0]).all()


def test_a_shift_on_the_search_boundary_is_not_reported():
    """A peak at exactly +/- max_shift may be larger still, so it is not a result."""
    canvas = _texture(120, 120, seed=5)
    surface = resample_to_tifxyz(canvas, ay=8, sy=0, ax=0, sx=0)
    with pytest.raises(CanvasShiftNotLocated, match="boundary"):
        measure_shift(surface, canvas, (16, 16, 40, 40), max_shift=8)


def test_a_window_that_is_not_inset_is_rejected():
    image = _texture(80, 80)
    with pytest.raises(ValueError, match="max_shift"):
        measure_shift(image, image, (0, 10, 40, 40), max_shift=8)


def test_a_shape_mismatch_is_rejected():
    with pytest.raises(ValueError, match="shape"):
        measure_shift(_texture(40, 40), _texture(40, 48), (8, 8, 16, 16), max_shift=4)


def test_a_flat_canvas_does_not_pretend_to_be_centered():
    image = np.full((80, 80), 3.0, np.float32)
    with pytest.raises(CanvasShiftNotLocated, match="contrast"):
        measure_shift(image, image, (16, 16, 32, 32), max_shift=8)


def test_cli_writes_the_canvas_resampled_onto_the_tifxyz_grid(tmp_path, capsys):
    canvas = _texture(140, 140, seed=6)
    surface = resample_to_tifxyz(canvas, ay=5, sy=0, ax=-3, sx=0)
    surface_path = tmp_path / "surface.npy"
    canvas_path = tmp_path / "canvas.npy"
    out_path = tmp_path / "corrected.npy"
    np.save(surface_path, surface)
    np.save(canvas_path, canvas)
    code = main(
        [
            str(surface_path),
            str(canvas_path),
            "--window",
            "36",
            "36",
            "48",
            "48",
            "--max-shift",
            "16",
            "--out",
            str(out_path),
        ]
    )
    assert code == 1
    assert "aligned_before: False" in capsys.readouterr().out
    saved = np.load(out_path)
    interior = np.s_[24:116, 24:116]
    assert float(np.percentile(np.abs(saved[interior] - surface[interior]), 95)) < 0.15


def test_cli_json_names_the_constant_shift(tmp_path, capsys):
    canvas = _texture(140, 140, seed=7)
    surface = resample_to_tifxyz(canvas, ay=5, sy=0, ax=-3, sx=0)
    surface_path = tmp_path / "surface.npy"
    canvas_path = tmp_path / "canvas.npy"
    np.save(surface_path, surface)
    np.save(canvas_path, canvas)
    code = main(
        [
            str(surface_path),
            str(canvas_path),
            "--window",
            "36",
            "36",
            "48",
            "48",
            "--max-shift",
            "16",
            "--json",
        ]
    )
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["aligned_before"] is False
    assert payload["fit"]["model"] == "constant"
    assert payload["fit"]["ay"] == pytest.approx(5, abs=0.25)
    assert payload["fit"]["ax"] == pytest.approx(-3, abs=0.25)
    assert "corrected" not in payload


def test_cli_aligned_pair_exits_zero(tmp_path, capsys):
    image = _texture(120, 120, seed=8)
    path = tmp_path / "image.npy"
    np.save(path, image)
    code = main(
        [str(path), str(path), "--window", "32", "32", "40", "40", "--max-shift", "12"]
    )
    assert code == 0
    assert "aligned_before: True" in capsys.readouterr().out


def test_cli_usage_and_unreadable_exit_two(tmp_path, capsys):
    with pytest.raises(SystemExit) as missing:
        main([])
    assert missing.value.code == 2
    missing_path = tmp_path / "missing.npy"
    code = main(
        [
            str(missing_path),
            str(missing_path),
            "--window",
            "8",
            "8",
            "8",
            "8",
        ]
    )
    assert code == 2
    assert "error:" in capsys.readouterr().err


def test_cli_help_exits_zero():
    with pytest.raises(SystemExit) as help_exit:
        main(["--help"])
    assert help_exit.value.code == 0
