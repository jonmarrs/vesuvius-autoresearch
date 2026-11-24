"""Finding 137's rules: the registered verdict table, the orientation check, the flip record and the winding choice."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import tifffile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "wrong_hand", ROOT / "repro/first_letters/pherc0211_control/wrong_hand.py"
)
wh = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = wh
spec.loader.exec_module(wh)

RIGHT = {
    "r": 0.8247,
    "control_wrong_side": -0.0471,
    "control_slid": {"largest_absolute": 0.1141},
    "cell_share": 0.8309,
}


def arm(r, share, wrong_side=-0.05, slid=0.11):
    return {
        "r": r,
        "control_wrong_side": wrong_side,
        "control_slid": {"largest_absolute": slid},
        "cell_share": share,
    }


@pytest.mark.parametrize(
    "wrong, expected",
    [
        (
            arm(0.8205, 0.8312),
            "WRONG_HAND_READS_ALIKE",
        ),  # finding 131's rerun as a stand-in
        (
            arm(0.7747, 0.665),
            "WRONG_HAND_READS_ALIKE",
        ),  # both edges: r - 0.05, 0.8 of the share
        (arm(0.7746, 0.80), "WRONG_HAND_READS_PARTLY"),  # just below the margin
        (
            arm(0.82, 0.66),
            "WRONG_HAND_READS_PARTLY",
        ),  # reads alike where it reaches, reaches less
        (arm(0.40, 0.30), "WRONG_HAND_READS_PARTLY"),
        (arm(0.39, 0.80), "WRONG_HAND_DOES_NOT_READ"),
        (
            arm(0.80, 0.24),
            "WRONG_HAND_DOES_NOT_READ",
        ),  # reaches under a quarter of the winner's cells
        (
            arm(0.80, 0.80, slid=0.41),
            "WRONG_HAND_DOES_NOT_READ",
        ),  # a control within half of r
        (arm(0.80, 0.80, wrong_side=-0.41), "WRONG_HAND_DOES_NOT_READ"),
        (arm(None, 0.80), "WRONG_HAND_DOES_NOT_READ"),
    ],
)
def test_the_registered_table(wrong, expected):
    assert wh.verdict(RIGHT, wrong, True) == expected


def test_no_verdict_without_finding_124_again_or_without_numbers():
    assert wh.verdict(RIGHT, arm(0.82, 0.83), False) == "DOES_NOT_RUN"
    assert wh.verdict(None, arm(0.82, 0.83), True) == "DOES_NOT_RUN"
    assert wh.verdict(RIGHT, None, True) == "DOES_NOT_RUN"
    assert wh.verdict(RIGHT, arm(0.82, None), True) == "DOES_NOT_RUN"


def test_constants_are_the_registered_ones():
    assert (wh.MARGIN, wh.SHARE_ALIKE, wh.SHARE_PARTLY, wh.PARTLY, wh.RATIO, wh.F124_R) == (
        0.05, 0.8, 0.25, 0.40, 2.0, 0.8247,
    )  # fmt: skip
    assert (wh.Z_BEGIN, wh.Z_END, wh.N_READ) == (7650, 9150, 4)


@pytest.mark.parametrize(
    "cosines, flipped, ok",
    [
        ([-0.99, -0.98], [True, True], True),
        (
            [-0.99, 0.97],
            [True, False],
            True,
        ),  # a kept render whose normals already agree
        (
            [0.99],
            [True],
            False,
        ),  # flipped although the normals agree: samples against the winner
        ([-0.99], [False], False),
        ([None], [True], False),
    ],
)
def test_every_render_must_sample_along_the_winners_normals(cosines, flipped, ok):
    assert wh.sampled_along_the_winner(cosines, flipped) is ok


def test_the_flip_record(tmp_path):
    assert wh.flips("-", ["w033", "w034"]) == {"w033": True, "w034": True}
    record = {
        "w040.tifxyz": {"render": "flip"},
        "w041.tifxyz": {"render": "keep"},
        "w042.tifxyz": {"render": None},
    }
    (tmp_path / "o.json").write_text(json.dumps(record))
    assert wh.flips(str(tmp_path / "o.json"), ["w040", "w041"]) == {
        "w040": True,
        "w041": False,
    }
    with pytest.raises(SystemExit, match="no render decision for w042"):
        wh.flips(str(tmp_path / "o.json"), ["w042"])


def _mesh(path: Path, xyz: np.ndarray) -> None:
    path.mkdir(parents=True)
    for i, a in enumerate("xyz"):
        tifffile.imwrite(path / f"{a}.tif", xyz[..., i].astype(np.float32))
    (path / "meta.json").write_text(json.dumps({"scale": [0.05, 0.05]}))


def _sheet(rows: int, cols: int, y: float, col0: int = 0) -> np.ndarray:
    """A flat sheet at height y, nodes 20 voxels apart, inside the band (z from 8000)."""
    i, j = np.mgrid[0:rows, 0:cols].astype(np.float64)
    return np.stack([(j + col0) * 20.0, np.full_like(i, y), 8000 + i * 20.0], axis=-1)


def test_choose_takes_the_windings_that_reach_the_winner_most(tmp_path):
    _mesh(tmp_path / "winner", _sheet(6, 12, 100.0))
    fit = tmp_path / "fitted"
    _mesh(fit / "w010", _sheet(6, 12, 101.0))  # on the winner, all of it
    _mesh(fit / "w011", _sheet(6, 6, 103.0))  # 3 voxels off, half of it
    _mesh(fit / "w012", _sheet(6, 12, 110.0))  # 10 voxels off: beyond 4
    _mesh(
        fit / "w010_spliced", _sheet(6, 12, 100.0)
    )  # villa's copy, not a winding of the fit
    out = wh.choose(fit, tmp_path / "winner", n=4)
    assert out["windings"] == 3
    assert out["chosen"] == ["w010", "w011"]  # w012 reaches nothing and is not read
    counts = out["points_within_accept"]
    assert counts["w010"] > counts["w011"] > 0 and counts["w012"] == 0
    assert out["described"]["winner_points_within_accept_of_any_winding"] == 1.0
    assert (
        out["described"]["winner_points_within_2_of_any_winding"] == 1.0
    )  # w010 is 1 voxel off everywhere


def test_an_arm_that_reaches_almost_nothing_gets_a_share_and_no_r():  # amendment 1
    cells = np.zeros((40, 40), bool)
    cells[:10, :10] = (
        True  # 100 cells, under the 1,000 that finding 121 asks of a winding
    )
    numbers = wh.arm_numbers(np.zeros((40, 40)), {}, cells, mask_cells=1000)
    assert numbers == {
        "cells": 100,
        "r": None,
        "control_wrong_side": None,
        "control_slid": None,
        "cell_share": 0.1,
    }
    assert wh.verdict(RIGHT, numbers, True) == "WRONG_HAND_DOES_NOT_READ"


def test_a_fit_that_never_reaches_the_winner_is_recorded_as_not_reading(
    tmp_path,
):  # amendment 1
    _mesh(tmp_path / "winner", _sheet(6, 12, 100.0))
    fit = tmp_path / "fitted"
    _mesh(fit / "w010", _sheet(6, 12, 150.0))
    listing, out = tmp_path / "list.txt", tmp_path / "choose.json"
    assert (
        wh.main(["choose", str(fit), str(tmp_path / "winner"), str(out), str(listing)])
        == 0
    )
    assert listing.read_text() == "" and json.loads(out.read_text())["chosen"] == []
    record = tmp_path / "compare.json"
    assert wh.main(["unreached", str(record), str(out)]) == 0
    result = json.loads(record.read_text())
    assert result["verdict"] == "WRONG_HAND_DOES_NOT_READ"
    assert result["registered"]["wrong"]["cell_share"] == 0.0
