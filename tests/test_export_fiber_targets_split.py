"""The cross-scroll split must be derived, not hardcoded to one cube.

`CROSS_SCROLL_SPLIT` was a single stem, so `split` was "cross_scroll" only for
`s5_03997_01497_03997_256`. Shipping five more Scroll-5 cubes through that would label
them "primary" -- cross-scroll cubes marked same-scroll, corrupting the axis this work
exists to expand. That is an n=1 assumption living in code rather than in data.
"""

import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from export_fiber_targets import size_class_for_stem, split_for_stem  # noqa: E402


@pytest.mark.parametrize(
    "stem",
    [
        "s5_03997_01497_03997_256",
        "s5_06494_01994_03994_512",
        "s5_06994_00994_04994_512",
        "s5_07994_01994_05494_512",
        "s5_07997_02997_05497_256",
        "s5_14997_01497_01497_256",
    ],
)
def test_every_scroll5_cube_is_cross_scroll(stem):
    assert split_for_stem(stem) == "cross_scroll"


@pytest.mark.parametrize(
    "stem",
    [
        "s1_00497_01497_03997_256",
        "s1_00497_02497_02997_256",
        "s1_00997_02497_02997_256",
        "s1_08997_02997_02497_256",
        "s1_10997_02997_02997_256",
    ],
)
def test_every_scroll1_cube_is_primary(stem):
    assert split_for_stem(stem) == "primary"


def test_an_unknown_scroll_is_refused_rather_than_defaulted():
    """Defaulting to "primary" is how a cross-scroll cube gets silently mislabelled."""
    with pytest.raises(ValueError, match="scroll"):
        split_for_stem("s9_00001_00002_00003_256")


@pytest.mark.parametrize(
    "stem,expected",
    [
        ("s1_00497_01497_03997_256", 256),
        ("s5_06494_01994_03994_512", 512),
    ],
)
def test_size_class_comes_from_the_cube_name(stem, expected):
    assert size_class_for_stem(stem) == expected
