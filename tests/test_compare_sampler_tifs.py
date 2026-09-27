"""compare_sampler_tifs: identical, differing and incomparable slices are told apart."""

import sys
from pathlib import Path

import numpy as np

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
