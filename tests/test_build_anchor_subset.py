"""Tests for the reduced-anchor dataset builder.

The bug this exists to prevent is not a crash. `data/spiral_s1_anchor10` was
built by hand and looked like a clean "59 -> 10 anchors" manipulation. It was
not: nine anchors lie outside the fit's z-ROI, and the ten it keeps all sit on
one z-plane, so it cuts 80% of the count AND 100% of the longitudinal spread at
the same time. A study run on it could not tell those apart.

So the tests are mostly about the SELECTION being what it claims.
"""

import json
import os
import sys
from pathlib import Path

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import build_anchor_subset as mod  # noqa: E402

_SRC = Path("/home/jon/openclaw-workspace/Neo-VM/data/spiral_s1")
_HAND = Path("/home/jon/openclaw-workspace/Neo-VM/data/spiral_s1_anchor10")


def _anchors(planes):
    """planes: {z: count} -> flat anchor list on those z values."""
    out, n = [], 0
    for z, c in planes.items():
        for _ in range(c):
            out.append(
                {"collection": "1", "point_id": f"p{n}", "xyz": [0.0, 0.0, float(z)]}
            )
            n += 1
    return out


def test_coverage_keeps_every_populated_plane():
    a = _anchors({100: 48, 200: 1, 300: 1})
    got = mod.select(a, 10, "coverage")
    assert len(got) == 10
    assert {round(x["xyz"][2]) for x in got} == {100, 200, 300}


def test_coverage_fills_the_remainder_from_the_most_populated_plane():
    a = _anchors({100: 48, 200: 1, 300: 1})
    got = mod.select(a, 10, "coverage")
    counts = {}
    for x in got:
        counts[round(x["xyz"][2])] = counts.get(round(x["xyz"][2]), 0) + 1
    assert counts == {100: 8, 200: 1, 300: 1}


def test_crowded_drops_whole_planes_which_is_the_confound():
    a = _anchors({100: 48, 200: 1, 300: 1})
    got = mod.select(a, 10, "crowded")
    assert {round(x["xyz"][2]) for x in got} == {100}, (
        "the 'crowded' strategy must reproduce the confounded hand-built set"
    )


def test_coverage_refuses_rather_than_silently_dropping_planes():
    a = _anchors({100: 5, 200: 5, 300: 5, 400: 5})
    with pytest.raises(ValueError, match="coverage cannot be preserved"):
        mod.select(a, 3, "coverage")


def test_selection_is_deterministic():
    a = _anchors({100: 48, 200: 1, 300: 1})
    ids = [
        tuple(x["point_id"] for x in mod.select(a, 10, "coverage")) for _ in range(3)
    ]
    assert len(set(ids)) == 1


def test_keeping_more_than_exists_returns_everything():
    a = _anchors({100: 3})
    assert len(mod.select(a, 99, "coverage")) == 3


def test_in_roi_excludes_out_of_range_anchors():
    a = _anchors({8000: 2, 15000: 3, 20000: 1})
    assert len(mod.in_roi(a, 13056, 18432)) == 3


@pytest.mark.skipif(not _SRC.is_dir(), reason="dataset not present")
def test_the_real_dataset_has_nine_anchors_outside_the_roi():
    """Pins the fact that made the registration's '59 -> 10' wrong."""
    a = mod.load_anchors(_SRC / "abs_winding.json")
    assert len(a) == 59
    assert len(mod.in_roi(a, 13056, 18432)) == 50


@pytest.mark.skipif(not _SRC.is_dir(), reason="dataset not present")
def test_the_in_roi_anchors_are_concentrated_on_one_plane():
    """48 of 50 on z=15694 is why 'keep the first 10' loses all z-spread."""
    a = mod.in_roi(mod.load_anchors(_SRC / "abs_winding.json"), 13056, 18432)
    planes = {}
    for x in a:
        planes[round(x["xyz"][2])] = planes.get(round(x["xyz"][2]), 0) + 1
    assert planes == {14268: 1, 15694: 48, 15976: 1}


@pytest.mark.skipif(
    not (_SRC.is_dir() and _HAND.is_dir()), reason="datasets not present"
)
def test_positive_control_crowded_reproduces_the_hand_built_dataset(tmp_path):
    """If the builder cannot recreate the artifact whose provenance it is
    documenting, it is not documenting it."""
    pool = mod.in_roi(mod.load_anchors(_SRC / "abs_winding.json"), 13056, 18432)
    got = {(x["collection"], x["point_id"]) for x in mod.select(pool, 10, "crowded")}
    hand = {
        (x["collection"], x["point_id"])
        for x in mod.load_anchors(_HAND / "abs_winding.json")
    }
    assert got == hand


@pytest.mark.skipif(not _SRC.is_dir(), reason="dataset not present")
def test_write_subset_symlinks_everything_else_and_never_touches_the_source(tmp_path):
    dst = tmp_path / "farm"
    pool = mod.in_roi(mod.load_anchors(_SRC / "abs_winding.json"), 13056, 18432)
    before = (_SRC / "abs_winding.json").read_text()
    mod.write_subset(_SRC, dst, mod.select(pool, 10, "coverage"))
    assert (_SRC / "abs_winding.json").read_text() == before, "source was modified"
    assert not (dst / "abs_winding.json").is_symlink(), "the varied file must be real"
    others = [e for e in os.listdir(_SRC) if e != "abs_winding.json"]
    assert all((dst / e).is_symlink() for e in others)
    assert len(json.loads((dst / "abs_winding.json").read_text())["collections"]) >= 1
