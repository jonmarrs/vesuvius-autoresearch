"""Canvas correction must preserve its inputs and exact categorical identities."""

import os
from pathlib import Path

import numpy as np
import pytest

from repro.sota_data import canvas_shift as canvas


def _inputs(tmp_path):
    values = np.random.default_rng(10).normal(size=(64, 64)).astype(np.float32)
    surface, source = tmp_path / "surface.npy", tmp_path / "canvas.npy"
    np.save(source, values)
    np.save(surface, np.roll(values, 2, axis=0))
    return surface, source


def _args(surface, source, output):
    return [
        str(surface),
        str(source),
        "--window",
        "16",
        "16",
        "24",
        "24",
        "--max-shift",
        "6",
        "--out",
        str(output),
    ]


@pytest.mark.parametrize("alias", ["surface", "canvas", "symlink", "hardlink"])
def test_cli_cannot_replace_either_input(tmp_path, alias):
    surface, source = _inputs(tmp_path)
    if alias == "surface":
        output = surface
    elif alias == "canvas":
        output = source
    else:
        output = tmp_path / "alias.npy"
        if alias == "symlink":
            output.symlink_to(source)
        else:
            os.link(source, output)
    originals = {p: p.read_bytes() for p in (surface, source)}
    assert canvas.main(_args(surface, source, output)) == 2
    assert {p: p.read_bytes() for p in originals} == originals


@pytest.mark.parametrize("dtype", [np.int64, np.uint64])
def test_nearest_neighbor_preserves_exact_64_bit_labels(dtype):
    values = np.arange(36, dtype=dtype).reshape(6, 6) + dtype(2**60)
    values[0, 0] = np.iinfo(dtype).max
    if dtype == np.int64:
        values[1, 0] = np.iinfo(dtype).min
    with pytest.warns(UserWarning, match="nearest"):
        corrected = canvas.resample_to_tifxyz(
            values, ay=0, sy=0, ax=0, sx=0, nearest=True
        )
    np.testing.assert_array_equal(corrected, values)


def test_uppercase_npy_output_uses_the_exact_requested_path(tmp_path):
    surface, source = _inputs(tmp_path)
    output = tmp_path / "corrected.NPY"
    assert canvas.main(_args(surface, source, output)) == 1
    assert output.is_file()
    assert not Path(str(output) + ".npy").exists()
    assert np.load(output).shape == (64, 64)


def test_failed_npy_write_preserves_previous_output(tmp_path, monkeypatch):
    surface, source = _inputs(tmp_path)
    output = tmp_path / "corrected.npy"
    np.save(output, np.full((64, 64), 0.25, np.float32))
    original = output.read_bytes()

    def fail(target, *args, **kwargs):
        if hasattr(target, "write"):
            target.write(b"partial new output")
        else:
            Path(target).write_bytes(b"partial new output")
        raise OSError("simulated write failure")

    monkeypatch.setattr(np, "save", fail)
    assert canvas.main(_args(surface, source, output)) == 2
    assert output.read_bytes() == original


@pytest.mark.parametrize("dtype", [np.int64, np.uint64])
@pytest.mark.parametrize(
    "interpolation", [canvas.cv2.INTER_NEAREST, canvas.cv2.INTER_NEAREST_EXACT]
)
def test_nearest_resize_preserves_exact_64_bit_labels(dtype, interpolation):
    indices = np.arange(24, dtype=np.float64).reshape(4, 6)
    values = indices.astype(dtype) + dtype(2**60)
    expected_indices = canvas.cv2.resize(
        indices, (11, 9), interpolation=interpolation
    ).astype(np.intp)
    corrected = canvas.resize_grayscale(values, (9, 11), interpolation=interpolation)
    np.testing.assert_array_equal(corrected, values.ravel()[expected_indices])


@pytest.mark.parametrize("offset", [0.5, -0.5, 1.50001, -2.49999])
def test_64_bit_sampling_matches_opencv_geometry_and_zero_border(offset):
    small = np.arange(1, 37, dtype=np.float64).reshape(6, 6)
    values = small.astype(np.uint64) + np.uint64(2**60)
    yy, xx = np.mgrid[:6, :6].astype(np.float32)
    selected = canvas.cv2.remap(
        small,
        xx + offset,
        yy - offset,
        canvas.cv2.INTER_NEAREST,
        borderMode=canvas.cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    expected = np.zeros((6, 6), np.uint64)
    inside = selected > 0
    expected[inside] = values.ravel()[selected[inside].astype(np.intp) - 1]
    with pytest.warns(UserWarning, match="nearest"):
        corrected = canvas.resample_to_tifxyz(
            values, ay=offset, sy=0, ax=-offset, sx=0, nearest=True
        )
    np.testing.assert_array_equal(corrected, expected)


@pytest.mark.parametrize("dtype", [np.int64, np.uint64])
@pytest.mark.parametrize("operation", ["warp", "resize"])
def test_linear_intensity_resampling_saturates_without_integer_wrap(dtype, operation):
    maximum = np.iinfo(dtype).max
    values = np.full((6, 7), maximum, dtype)
    if operation == "warp":
        corrected = canvas.resample_to_tifxyz(
            values, ay=0, sy=0, ax=0, sx=0, nearest=False
        )
    else:
        corrected = canvas.resize_grayscale(values, (12, 14))
    np.testing.assert_array_equal(corrected, np.full(corrected.shape, maximum, dtype))


@pytest.mark.parametrize("module_mode", [False, True])
def test_cli_uses_its_own_checkout_helpers(tmp_path, module_mode):
    import subprocess
    import sys

    surface, source = _inputs(tmp_path)
    foreign = tmp_path / "foreign"
    # Like another editable checkout: a namespace root and a regular core package.
    package = foreign / "vesuvius_autoresearch" / "core"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(
        "raise RuntimeError('foreign checkout imported')\n"
    )
    root = Path(canvas.__file__).resolve().parents[2]
    invocation = (
        ["-m", "repro.sota_data.canvas_shift"]
        if module_mode
        else [str(Path(canvas.__file__).resolve())]
    )
    output = tmp_path / "corrected.npy"
    result = subprocess.run(
        [sys.executable, *invocation, *_args(surface, source, output)],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": os.pathsep.join((str(foreign), str(root)))},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert output.is_file(), result.stdout + result.stderr


def test_opencv_decode_errors_use_the_documented_cli_error_status(
    tmp_path, monkeypatch, capsys
):
    def bad_decode(*args, **kwargs):
        raise canvas.cv2.error("simulated decode error")

    monkeypatch.setattr(canvas.cv2, "imread", bad_decode)
    output = tmp_path / "corrected.npy"
    assert (
        canvas.main(_args(tmp_path / "surface.png", tmp_path / "canvas.png", output))
        == 2
    )
    assert "simulated decode error" in capsys.readouterr().err
    assert not output.exists()
