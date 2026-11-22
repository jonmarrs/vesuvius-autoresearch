"""compare_sampler_tifs: identical, differing and incomparable slices are told apart."""

import json
import subprocess
import sys
import warnings
from pathlib import Path

import numpy as np
import pytest
import tifffile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compare_sampler_tifs import compare_slice, verdict  # noqa: E402


def test_identical_slices():
    a = np.arange(100, dtype=np.uint8).reshape(10, 10)
    s = compare_slice(a, a.copy())
    assert s["identical"] and s["max_abs_diff"] == 0
    assert verdict({"00.tif": s}) == "BYTE-IDENTICAL SAMPLING"


def test_a_one_level_change_is_not_identical():
    a = np.full((10, 10), 50, np.uint8)
    b = a.copy()
    b[3, 3] = 51
    s = compare_slice(a, b)
    assert not s["identical"] and s["max_abs_diff"] == 1 and s["frac_px_differ"] == 0.01
    assert verdict({"00.tif": s}) == "SAMPLED VALUES DIFFER"


def test_shape_mismatch_or_missing_slice_is_not_comparable():
    s = compare_slice(np.zeros((4, 4), np.uint8), np.zeros((4, 5), np.uint8))
    assert not s["comparable"]
    good = compare_slice(np.zeros((2, 2), np.uint8), np.zeros((2, 2), np.uint8))
    assert verdict({"00.tif": good, "01.tif": s}) == "NOT COMPARABLE"
    assert verdict({}) == "NOT COMPARABLE"


@pytest.mark.parametrize("left,right", [(0, 65535), (65535, 0), (0, 32768), (32768, 0)])
def test_uint16_differences_do_not_wrap(left, right):
    s = compare_slice(
        np.full((2, 2), left, np.uint16), np.full((2, 2), right, np.uint16)
    )
    expected = abs(left - right)
    assert s["comparable"] and not s["identical"]
    assert s["max_abs_diff"] == expected
    assert s["mean_abs_diff_covered"] == expected
    assert s["frac_px_differ"] == 1
    assert verdict({"00.tif": s}) == "SAMPLED VALUES DIFFER"


@pytest.mark.parametrize("dtype", ["u1", "<u2", ">u2"])
def test_unsigned_grayscale_slices_still_compare_identically(dtype):
    a = np.arange(4, dtype=dtype).reshape(2, 2)
    s = compare_slice(a, a.copy())
    assert s["comparable"] and s["identical"]
    assert s["max_abs_diff"] == s["mean_abs_diff_covered"] == 0


def test_uint16_storage_byte_order_does_not_change_sample_values():
    a = np.array([[0, 32768], [1, 65535]], dtype="<u2")
    b = a.astype(">u2")
    assert compare_slice(a, b)["identical"]


@pytest.mark.parametrize(
    "dtype,left,right",
    [
        (np.float32, 0.25, 0.75),
        (np.uint32, 0, 65536),
        (np.int16, -1, 1),
        (np.bool_, False, True),
        (np.complex64, 1 + 1j, 1 + 2j),
    ],
)
def test_other_sample_types_are_not_certified_after_integer_cast(dtype, left, right):
    # Fractional changes previously disappeared in the int16 conversion.
    a = np.full((2, 2), left, dtype=dtype)
    b = np.full((2, 2), right, dtype=dtype)
    s = compare_slice(a, b)
    assert not s["comparable"]
    assert "uint8 or uint16" in s["reason"]
    assert verdict({"00.tif": s}) == "NOT COMPARABLE"


def test_changed_bit_depth_is_not_byte_identical_sampling():
    a = np.zeros((2, 2), np.uint8)
    s = compare_slice(a, a.astype(np.uint16))
    assert not s["comparable"]
    assert verdict({"00.tif": s}) == "NOT COMPARABLE"


@pytest.mark.parametrize("shape", [(0, 2), (2,), (), (2, 2, 3)])
def test_empty_or_non_grayscale_slices_are_not_comparable(shape):
    a = np.zeros(shape, np.uint8)
    s = compare_slice(a, a.copy())
    assert not s["comparable"]
    assert verdict({"00.tif": s}) == "NOT COMPARABLE"


def test_cli_preserves_full_uint16_difference_in_tiff_report(tmp_path):
    ref, test = tmp_path / "ref", tmp_path / "test"
    ref.mkdir()
    test.mkdir()
    a = np.array([[0, 1], [32768, 65535]], np.uint16)
    b = np.array([[65535, 1], [32768, 0]], np.uint16)
    tifffile.imwrite(ref / "00.tif", a)
    tifffile.imwrite(test / "00.tif", b)
    inputs = {path: path.read_bytes() for path in (ref / "00.tif", test / "00.tif")}
    output = tmp_path / "report.json"
    result = subprocess.run(
        [
            sys.executable,
            str(
                Path(__file__).resolve().parents[1]
                / "scripts"
                / "compare_sampler_tifs.py"
            ),
            str(ref),
            str(test),
            "--json",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text())
    assert report["verdict"] == "SAMPLED VALUES DIFFER"
    s = report["slices"]["00.tif"]
    assert s["max_abs_diff"] == 65535
    assert s["mean_abs_diff_covered"] == 32767.5
    assert s["frac_px_differ"] == 0.5
    assert inputs == {path: path.read_bytes() for path in inputs}


def test_each_slice_s_sample_type_is_checked():
    a = np.zeros((2, 2), np.uint8)
    assert not compare_slice(a, np.zeros((2, 2), np.int8))["comparable"]
    assert not compare_slice(np.zeros((2, 2), np.int8), a)["comparable"]


def test_the_mean_difference_is_over_covered_pixels_only():
    a = np.array([[0, 0], [10, 0]], np.uint8)
    s = compare_slice(a, np.zeros((2, 2), np.uint8))
    assert s["mean_abs_diff_covered"] == 10.0 and s["frac_px_differ"] == 0.25


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ([[0, 0], [0, 0]], [[0, 0], [0, 0]]),
        ([[5, 5], [5, 5]], [[1, 2], [3, 4]]),
        ([[1, 2], [3, 4]], [[5, 5], [5, 5]]),
    ],
    ids=["nothing_covered", "constant_reference", "constant_test"],
)
def test_constant_or_empty_coverage_has_no_correlation_and_no_warning(left, right):
    a, b = np.array(left, np.uint8), np.array(right, np.uint8)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        s = compare_slice(a, b)
    assert np.isnan(s["r_covered"])
    if not (a.any() or b.any()):
        assert s["mean_abs_diff_covered"] == 0.0


def test_one_differing_slice_makes_the_sampling_differ():
    a = np.full((2, 2), 7, np.uint8)
    b = a.copy()
    b[0, 0] = 8
    same, other = compare_slice(a, a.copy()), compare_slice(a, b)
    assert verdict({"00.tif": same, "01.tif": other}) == "SAMPLED VALUES DIFFER"


@pytest.mark.parametrize("only_in", ["ref", "test"])
def test_cli_reports_a_slice_present_in_only_one_run(tmp_path, only_in):
    ref, test = tmp_path / "ref", tmp_path / "test"
    ref.mkdir()
    test.mkdir()
    a = np.full((2, 2), 3, np.uint8)
    tifffile.imwrite(ref / "00.tif", a)
    tifffile.imwrite(test / "00.tif", a)
    tifffile.imwrite((ref if only_in == "ref" else test) / "01.tif", a)
    output = tmp_path / "report.json"
    script = Path(__file__).resolve().parents[1] / "scripts" / "compare_sampler_tifs.py"
    result = subprocess.run(
        [sys.executable, str(script), str(ref), str(test), "--json", str(output)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text())
    assert report["verdict"] == "NOT COMPARABLE"
    assert report["slices"]["00.tif"]["identical"]
    missing = report["slices"]["01.tif"]
    assert not missing["comparable"] and "FileNotFoundError" in missing["reason"]
