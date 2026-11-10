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
import warnings
from pathlib import Path

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
    resize_grayscale,
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
    with pytest.warns(UserWarning, match="nearest"):
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


def test_a_canvas_of_another_size_is_measured_in_the_shared_index_space():
    """Paris-4 canvases are not their tifxyz grid's size; both start at pixel 0."""
    canvas = _texture(80, 96, seed=21)
    surface = np.pad(
        _independent_surface(canvas, ay=4, sy=0, ax=-3, sx=0), ((0, 12), (0, 0))
    )
    found = measure_shift(surface, canvas, (16, 16, 40, 40), max_shift=12)
    assert surface.shape != canvas.shape
    assert found["dy"] == pytest.approx(4, abs=0.2)
    assert found["dx"] == pytest.approx(-3, abs=0.2)


def test_a_window_outside_the_canvas_is_rejected():
    surface = _texture(96, 96)
    with pytest.raises(ValueError, match="inside the canvas"):
        measure_shift(surface, _texture(40, 96), (16, 16, 40, 40), max_shift=8)


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


def test_window_centre_is_the_mean_of_its_pixel_indices():
    """y + height/2 is half a pixel past the mean for every window height."""
    image = _texture(80, 80, seed=13)
    found = measure_shift(image, image, (10, 12, 20, 8), max_shift=8)
    assert found["y"] == pytest.approx(10 + (20 - 1) / 2.0)
    assert found["x"] == pytest.approx(12 + (8 - 1) / 2.0)


def test_a_dropped_cross_term_is_refit_into_the_intercept():
    """Zeroing cy and keeping the joint intercept would leave its 0.1 px mean out."""

    def _dy(y, x):
        return 5.0 + 0.01 * y + 0.00001 * x

    points = [(0.0, 0.0), (0.0, 10000.0), (1000.0, 0.0), (1000.0, 10000.0)]
    fitted = fit_shift(
        [{"y": y, "x": x, "dy": _dy(y, x), "dx": 1.0} for y, x in points]
    )
    assert fitted["model"] == "linear"
    assert fitted["cy"] == 0.0
    assert fitted["sy"] == pytest.approx(0.01)
    assert fitted["ay"] == pytest.approx(5.05)
    assert fitted["ax"] == pytest.approx(1.0)
    assert fitted["sx"] == 0.0 and fitted["cx"] == 0.0


def test_nonzero_cross_terms_round_trip_through_the_remap():
    """A label pixel and a float texture both come back with cy and cx set."""
    canvas = np.zeros((64, 64), np.uint8)
    canvas[10, 20] = 255
    with pytest.warns(UserWarning, match="nearest"):
        out = resample_to_tifxyz(
            canvas, ay=1.0, sy=0.0, ax=2.0, sx=0.0, cy=0.05, cx=0.1, nearest=True
        )
    assert out[12, 23] == 255
    assert int(out.sum()) == 255

    texture = _texture(80, 80, seed=14)
    ay, sy, cy = 1.5, 0.01, 0.004
    ax, sx, cx = -1.0, -0.008, 0.003
    surface = _independent_surface(texture, ay, sy, ax, sx, cy=cy, cx=cx)
    warped = resample_to_tifxyz(texture, ay, sy, ax, sx, cy=cy, cx=cx)
    interior = np.s_[8:72, 8:72]
    residual = np.abs(warped[interior] - surface[interior])
    assert float(np.percentile(residual, 95)) < 0.15


def test_a_large_correction_leaves_only_the_held_out_subpixel():
    """Held-out w01's second search was -1.31 level-0 px, which is 0.33 px at level 2.

    A synthetic sheet with a large constant shift must come back inside that
    leftover. The second peak is not another undiscovered offset.
    """
    canvas = _texture(140, 140, seed=15)
    surface = _independent_surface(canvas, ay=28, sy=0, ax=-16, sx=0)
    window = (36, 36, 40, 40)
    found = measure_shift(surface, canvas, window, max_shift=32, px_scale=4)
    assert found["dy"] == pytest.approx(28, abs=0.35)
    assert found["dx"] == pytest.approx(-16, abs=0.35)
    corrected = resample_to_tifxyz(
        canvas, ay=float(found["dy"]), sy=0.0, ax=float(found["dx"]), sx=0.0
    )
    again = measure_shift(surface, corrected, window, max_shift=32, px_scale=4)
    assert abs(float(again["dy0"])) < 1.5
    assert abs(float(again["dx0"])) < 1.5
    assert again["ncc"] > 0.9


def test_uint8_and_uint16_shift_matches_bilinear():
    """Intensity defaults to bilinear. Integer dtype is not a label."""
    smooth = _texture(40, 40, seed=40)
    for dtype, scale in ((np.uint8, 200.0), (np.uint16, 40000.0)):
        image = np.clip(smooth * scale + 10, 0, np.iinfo(dtype).max).astype(dtype)
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            out = resample_to_tifxyz(image, ay=0.0, sy=0.0, ax=0.5, sx=0.0)
        reference = resample_to_tifxyz(
            image.astype(np.float32), ay=0.0, sy=0.0, ax=0.5, sx=0.0
        )
        assert out.dtype == dtype
        assert float(np.max(np.abs(out.astype(np.float64) - reference))) <= 0.5
        with pytest.warns(UserWarning, match="nearest"):
            nearest = resample_to_tifxyz(
                image, ay=0.0, sy=0.0, ax=0.5, sx=0.0, nearest=True
            )
        assert nearest.dtype == dtype
        assert not np.array_equal(out, nearest)


def test_an_integer_grayscale_resize_interpolates():
    """uint8 and uint16 intensity resize is bilinear, then rounded back."""
    image = np.zeros((8, 8), np.uint8)
    image[:, 4:] = 200
    out = resize_grayscale(image, (8, 5))
    assert out.shape == (8, 5)
    assert out.dtype == np.uint8
    assert 100 in set(np.unique(out))
    wider = image.astype(np.uint16) * 10
    kept = resize_grayscale(wider, (8, 5))
    assert kept.dtype == np.uint16
    assert 1000 in set(np.unique(kept))
    sharp = resize_grayscale(image, (8, 5), interpolation=cv2.INTER_NEAREST)
    assert set(np.unique(sharp)).issubset({0, 200})


def test_a_float_grayscale_resize_interpolates():
    image = np.zeros((8, 8), np.float32)
    image[:, 4:] = 200
    out = resize_grayscale(image, (8, 5))
    assert out.dtype == np.float32
    assert np.any((out > 0) & (out < 200))


def test_correct_canvas_and_the_cli_bilinear_a_uint8_canvas(tmp_path):
    canvas = np.clip(_texture(96, 96, seed=41) * 180 + 20, 0, 255).astype(np.uint8)
    surface = resample_to_tifxyz(
        canvas.astype(np.float32), ay=0.5, sy=0.0, ax=-0.4, sx=0.0
    )
    window = (24, 24, 40, 40)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = correct_canvas(surface, canvas, [window], max_shift=8)
    corrected = result["corrected"]
    fit = result["fit"]
    reference = resample_to_tifxyz(
        canvas.astype(np.float32),
        ay=float(fit["ay"]),
        sy=float(fit["sy"]),
        ax=float(fit["ax"]),
        sx=float(fit["sx"]),
        cy=float(fit["cy"]),
        cx=float(fit["cx"]),
    )
    assert corrected.dtype == np.uint8
    assert float(np.max(np.abs(corrected.astype(np.float64) - reference))) <= 0.5
    np.save(tmp_path / "surface.npy", surface)
    np.save(tmp_path / "canvas.npy", canvas)
    out = tmp_path / "out.npy"
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        code = main(
            [
                str(tmp_path / "surface.npy"),
                str(tmp_path / "canvas.npy"),
                "--window",
                "24",
                "24",
                "40",
                "40",
                "--max-shift",
                "8",
                "--out",
                str(out),
            ]
        )
    assert code == 0
    assert np.array_equal(np.load(out), corrected)


def test_an_explicit_nearest_flag_keeps_an_integer_label_binary():
    label = np.zeros((32, 32), np.uint8)
    label[:, 16:] = 255
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        blended = resample_to_tifxyz(label, ay=0.0, sy=0.0, ax=0.5, sx=0.0)
    assert blended.dtype == np.uint8
    assert not set(np.unique(blended)).issubset({0, 255})
    with pytest.warns(UserWarning, match="nearest"):
        kept = resample_to_tifxyz(label, ay=0.0, sy=0.0, ax=0.5, sx=0.0, nearest=True)
    assert set(np.unique(kept)).issubset({0, 255})


def test_a_boolean_mask_defaults_to_nearest():
    """A bool mask is nearest, and that default does not warn."""
    mask = np.zeros((32, 32), dtype=bool)
    mask[:, 16:] = True
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        kept = resample_to_tifxyz(mask, ay=0.0, sy=0.0, ax=0.5, sx=0.0)
        resized = resize_grayscale(mask, (32, 20))
        explicit = resample_to_tifxyz(
            mask, ay=0.0, sy=0.0, ax=0.5, sx=0.0, nearest=True
        )
    assert kept.dtype == np.bool_
    assert set(np.unique(kept)).issubset({False, True})
    assert explicit.dtype == np.bool_
    assert np.array_equal(explicit, kept)
    blended = resample_to_tifxyz(mask, ay=0.0, sy=0.0, ax=0.5, sx=0.0, nearest=False)
    assert blended.dtype == np.float32
    assert np.any((blended > 0) & (blended < 1))
    assert resized.dtype == np.bool_
    assert set(np.unique(resized)).issubset({False, True})


def test_cli_labels_the_image_space_fit_beside_level0_centres(tmp_path, capsys):
    image = _texture(96, 96, seed=16)
    path = tmp_path / "image.npy"
    np.save(path, image)
    code = main(
        [
            str(path),
            str(path),
            "--window",
            "20",
            "24",
            "32",
            "32",
            "--max-shift",
            "8",
            "--px-scale",
            "4",
            "--origin",
            "1000",
            "2000",
        ]
    )
    assert code == 0
    text = capsys.readouterr().out
    assert "in image pixels" in text
    assert "not the level-0 centres" in text
    assert "image center (35.50, 39.50)" in text
    assert "level-0 center (1142.0, 2158.0)" in text


def test_cli_resamples_an_integer_label_with_nearest(tmp_path):
    label = np.clip(_texture(96, 96, seed=17) * 40 + 128, 0, 255).astype(np.uint8)
    surface = resample_to_tifxyz(label.astype(np.float32), ay=4, sy=0, ax=-3, sx=0)
    surface_path = tmp_path / "surface.npy"
    label_path = tmp_path / "label.npy"
    out_path = tmp_path / "out.npy"
    np.save(surface_path, surface)
    np.save(label_path, label)
    with pytest.warns(UserWarning, match="nearest"):
        code = main(
            [
                str(surface_path),
                str(label_path),
                "--window",
                "20",
                "20",
                "40",
                "40",
                "--max-shift",
                "12",
                "--nearest",
                "--out",
                str(out_path),
            ]
        )
    assert code == 1
    saved = np.load(out_path)
    # Nearest keeps label values whole. The border fill is 0. Bilinear would
    # put fractional gray on the half-pixel edges of this shift.
    assert np.all(np.mod(saved, 1) == 0)


# Second review (2026-11-09). Each test below failed on dd0803df.


def test_windows_on_one_line_get_the_separable_fit():
    """Collinear centres cannot tell a y slope from an x slope.

    On dd0803df the least-squares fit split a true ``dy = 0.01*y`` into
    ``sy = cy = 0.005``, 4 px wrong at (900, 100). The size residual is per
    axis, so these windows get the fit two windows get.
    """
    for points in (
        [(100.0, 100.0), (500.0, 500.0), (900.0, 900.0)],
        [(100.0, 100.0), (500.0, 520.0), (900.0, 900.0)],
    ):
        with pytest.warns(UserWarning, match="one line"):
            fitted = fit_shift(
                [{"y": y, "x": x, "dy": 0.01 * y, "dx": -0.005 * x} for y, x in points]
            )
        assert fitted["model"] == "linear"
        assert fitted["cy"] == 0.0 and fitted["cx"] == 0.0
        assert fitted["sy"] == pytest.approx(0.01)
        assert fitted["sx"] == pytest.approx(-0.005)


def test_a_row_of_windows_keeps_its_fit_and_warns():
    """A row cannot see the change across it; along it the fit is unambiguous."""
    points = [(100.0, 100.0), (100.0, 5100.0), (100.0, 10100.0)]
    with pytest.warns(UserWarning, match="slope across it stays 0"):
        fitted = fit_shift(
            [
                {"y": y, "x": x, "dy": 2.0 + 0.0001 * x, "dx": -0.004 * x}
                for y, x in points
            ]
        )
    assert fitted["cy"] == pytest.approx(0.0001) and fitted["sy"] == 0.0
    assert fitted["sx"] == pytest.approx(-0.004)


def test_an_elongated_rectangle_of_windows_is_not_a_line():
    import warnings

    points = [(100.0, 200.0), (1100.0, 200.0), (100.0, 20200.0), (1100.0, 20200.0)]
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        fitted = fit_shift(
            [
                {"y": y, "x": x, "dy": 0.01 * y + 0.00002 * x, "dx": 0.0}
                for y, x in points
            ]
        )
    assert fitted["model"] == "affine"


def test_the_w01_window_layout_still_identifies_a_cross_term():
    """The probe's four w01 centres: three on one column and one off it."""
    centres = [
        (14081.5, 16129.5),
        (18001.5, 16129.5),
        (22001.5, 16129.5),
        (18001.5, 28001.5),
    ]
    fitted = fit_shift(
        [
            {
                "y": y,
                "x": x,
                "dy": 11.5 + 0.00426 * y + 0.0001 * x,
                "dx": 11.8 - 0.00388 * x,
            }
            for y, x in centres
        ]
    )
    assert fitted["model"] == "affine"
    assert fitted["cy"] == pytest.approx(0.0001)
    assert fitted["sy"] == pytest.approx(0.00426)


def test_a_nearest_resample_returns_the_label_dtype():
    label = np.zeros((32, 32), np.uint16)
    label[8:20, 8:20] = 1000
    with pytest.warns(UserWarning, match="nearest"):
        out = resample_to_tifxyz(label, ay=2.0, sy=0.0, ax=-3.0, sx=0.0, nearest=True)
    assert out.dtype == np.uint16
    assert set(np.unique(out)) == {0, 1000}
    wide = np.zeros((16, 16), np.int32)
    wide[4:8, 4:8] = 20_000_001  # not exact in float32
    with pytest.warns(UserWarning, match="nearest"):
        out = resample_to_tifxyz(wide, ay=1.0, sy=0.0, ax=0.0, sx=0.0, nearest=True)
    assert out.dtype == np.int32 and int(out.max()) == 20_000_001


def test_cli_keeps_a_16_bit_label_in_a_png(tmp_path):
    label = np.zeros((96, 96), np.uint16)
    label[30:60, 30:60] = 1000
    texture = (_texture(96, 96, seed=22) * 3000 + 30000).astype(np.uint16)
    canvas = np.maximum(label, texture)
    surface = resample_to_tifxyz(canvas.astype(np.float32), ay=4, sy=0, ax=-3, sx=0)
    np.save(tmp_path / "surface.npy", surface)
    np.save(tmp_path / "canvas.npy", canvas)
    out = tmp_path / "out.png"
    with pytest.warns(UserWarning, match="nearest"):
        code = main(
            [str(tmp_path / "surface.npy"), str(tmp_path / "canvas.npy"),
             "--window", "20", "20", "40", "40", "--max-shift", "12",
             "--nearest", "--out", str(out)]
        )  # fmt: skip
    assert code == 1
    saved = cv2.imread(str(out), cv2.IMREAD_UNCHANGED)
    assert saved.dtype == np.uint16 and int(saved.max()) == int(canvas.max())


def test_cli_refuses_to_write_a_float_result_as_png(tmp_path, capsys):
    canvas = _texture(96, 96, seed=23)
    surface = resample_to_tifxyz(canvas, ay=4, sy=0, ax=-3, sx=0)
    np.save(tmp_path / "surface.npy", surface)
    np.save(tmp_path / "canvas.npy", canvas)
    out = tmp_path / "out.png"
    code = main(
        [str(tmp_path / "surface.npy"), str(tmp_path / "canvas.npy"),
         "--window", "20", "20", "40", "40", "--max-shift", "12", "--out", str(out)]
    )  # fmt: skip
    assert code == 2
    assert not out.exists()
    assert ".npy or .tif" in capsys.readouterr().err


def test_correct_canvas_reads_a_canvas_of_another_size_onto_the_surface_grid():
    canvas = _texture(80, 96, seed=24)
    surface = np.pad(
        _independent_surface(canvas, ay=4, sy=0, ax=-3, sx=0), ((0, 12), (0, 0))
    )
    result = correct_canvas(surface, canvas, [(16, 16, 40, 40)], max_shift=12)
    corrected = result["corrected"]
    assert isinstance(corrected, np.ndarray)
    assert corrected.shape == surface.shape
    interior = np.s_[12:70, 12:80]
    assert (
        float(np.percentile(np.abs(corrected[interior] - surface[interior]), 95)) < 0.15
    )


def test_aligned_is_judged_in_level0_pixels():
    """0.6 image px is 2.4 level-0 px on a level-2 pair: not aligned."""
    canvas = _texture(96, 96, seed=25)
    surface = _independent_surface(canvas, ay=0.6, sy=0, ax=0, sx=0)
    windows = [(20, 20, 48, 48)]
    assert (
        correct_canvas(surface, canvas, windows, max_shift=8)["aligned_before"] is True
    )
    level2 = correct_canvas(surface, canvas, windows, max_shift=8, px_scale=4)
    assert level2["aligned_before"] is False


def test_cli_exits_three_when_the_shift_is_not_located(tmp_path, capsys):
    flat = np.full((80, 80), 3.0, np.float32)
    path = tmp_path / "flat.npy"
    np.save(path, flat)
    code = main(
        [str(path), str(path), "--window", "16", "16", "32", "32", "--max-shift", "8"]
    )
    assert code == 3
    assert "not located:" in capsys.readouterr().err


def test_the_highpass_of_a_window_is_the_highpass_of_the_image():
    """measure_shift filters the window plus a margin, not the whole image each time."""
    from repro.sota_data.canvas_shift import _highpass_region, highpass

    image = _texture(120, 140, seed=26)
    image[40:50, 60:90] = np.nan
    full = highpass(image, 31)
    for y0, y1, x0, x1 in ((0, 40, 0, 50), (30, 90, 50, 110), (100, 120, 100, 140)):
        part = _highpass_region(image, y0, y1, x0, x1, 31)
        np.testing.assert_allclose(part, full[y0:y1, x0:x1], atol=1e-5, equal_nan=True)


sys.path.insert(0, os.path.abspath("scripts"))
import probe_canvas_frame_shift as probe  # noqa: E402


def test_a_level1_canvas_is_bilinear_intensity(monkeypatch):
    fine = np.arange(16, dtype=np.uint8).reshape(4, 4) * 10

    def _region(*_args, **kwargs):
        assert kwargs["dtype"] == np.uint8
        return fine

    monkeypatch.setattr(probe, "_zarr_region", _region)
    out = probe._canvas_on_level2("base", 1, 0, 2, 0, 2)
    bilinear = resize_grayscale(fine, (2, 2), interpolation=cv2.INTER_LINEAR)
    nearest = resize_grayscale(fine, (2, 2), interpolation=cv2.INTER_NEAREST)
    assert out.dtype == np.uint8
    assert np.array_equal(out, bilinear)
    assert not np.array_equal(out, nearest)


def test_the_probe_replaces_only_the_rows_of_the_run_it_repeats():
    previous = [
        {"name": n} for n in ("w018 r0", "w01 inside-a", "w01-fit", "w01 held-out")
    ]
    names = lambda rows: [r["name"] for r in rows]  # noqa: E731
    merged = probe.merge_rows(
        previous, [{"name": "w01 inside-a"}, {"name": "w01-fit"}], "w01"
    )
    assert names(merged) == ["w018 r0", "w01 held-out", "w01 inside-a", "w01-fit"]
    merged = probe.merge_rows(previous, [{"name": "w01 held-out"}], "w01-heldout")
    assert names(merged) == ["w018 r0", "w01 inside-a", "w01-fit", "w01 held-out"]
    assert names(probe.merge_rows(previous, [{"name": "w018 r0"}], "all")) == [
        "w018 r0"
    ]


def test_the_probe_writes_artifacts_beside_its_cache_by_default(monkeypatch, tmp_path):
    import tempfile

    monkeypatch.delenv("CANVAS_SHIFT_ARTIFACTS", raising=False)
    assert (
        probe.artifact_dir() == Path(tempfile.gettempdir()) / "canvas_shift_artifacts"
    )
    monkeypatch.setenv("CANVAS_SHIFT_ARTIFACTS", str(tmp_path / "a"))
    assert probe.artifact_dir() == tmp_path / "a"


def test_the_probe_checks_its_arguments_and_output_before_any_download(
    monkeypatch, tmp_path
):
    def _no_network(*args, **kwargs):
        raise AssertionError("fetched before the arguments were checked")

    monkeypatch.setattr(probe, "_fetch", _no_network)
    assert probe.main(["w99"]) == 2
    blocked = tmp_path / "file"
    blocked.write_text("")
    monkeypatch.setenv("CANVAS_SHIFT_ARTIFACTS", str(blocked / "artifacts"))
    assert probe.main(["w018"]) == 2


def _serve(monkeypatch, blob: bytes) -> list:
    seen: list = []

    def _fetch(url, rng=None):
        seen.append((url, rng))
        if rng is None:
            return blob
        return blob[rng[0] : rng[1] + 1]

    monkeypatch.setattr(probe, "_fetch", _fetch)
    return seen


def test_the_probe_tiff_reader_reads_float32_strips(monkeypatch, tmp_path):
    import tifffile

    plane = np.arange(40 * 30, dtype=np.float32).reshape(40, 30)
    path = tmp_path / "x.tif"
    tifffile.imwrite(path, plane, rowsperstrip=7)
    _serve(monkeypatch, path.read_bytes())
    np.testing.assert_array_equal(
        probe._Tiff("x").rows(3, 20, 5, 25), plane[3:20, 5:25]
    )


@pytest.mark.parametrize(
    "kwargs, words",
    [
        ({"compression": "zlib"}, "compressed"),
        ({"tile": (16, 16)}, "tiled"),
        ({"dtype": np.uint16}, "float32"),
    ],
)
def test_the_probe_tiff_reader_refuses_what_it_cannot_decode(
    monkeypatch, tmp_path, kwargs, words
):
    import tifffile

    dtype = kwargs.pop("dtype", np.float32)
    path = tmp_path / "x.tif"
    tifffile.imwrite(path, np.ones((32, 32), dtype), **kwargs)
    _serve(monkeypatch, path.read_bytes())
    with pytest.raises(ValueError, match=words):
        probe._Tiff("x")


def test_the_probe_reads_a_v2_zarr_chunk_with_the_default_separator(monkeypatch):
    meta = json.dumps(
        {"compressor": None, "chunks": [128, 128, 128], "shape": [256, 256, 256]}
    )
    seen = []

    def _fetch(url, rng=None):
        seen.append(url)
        if url.endswith(".zarray"):
            return meta.encode()
        return bytes(rng[1] - rng[0] + 1)

    monkeypatch.setattr(probe, "_fetch", _fetch)
    probe._volume_at("base", np.array([[40.0, 40.0, 40.0]]))
    assert {u for u in seen if not u.endswith(".zarray")} == {"base/2/0.0.0"}


def test_the_probe_cache_refetches_a_short_ranged_entry(monkeypatch, tmp_path):
    import hashlib
    import io

    monkeypatch.setattr(probe, "CACHE", tmp_path)
    url, rng = "https://example.invalid/x", (0, 9)
    key = hashlib.sha1(f"{url}|{rng}".encode()).hexdigest()
    (tmp_path / key[:2]).mkdir()
    (tmp_path / key[:2] / key).write_bytes(b"abc")  # an interrupted earlier write
    monkeypatch.setattr(
        probe.urllib.request,
        "urlopen",
        lambda request, timeout: io.BytesIO(b"0123456789"),
    )
    assert probe._fetch(url, rng) == b"0123456789"
    assert (tmp_path / key[:2] / key).read_bytes() == b"0123456789"
    assert not list(tmp_path.glob("**/*.part"))
