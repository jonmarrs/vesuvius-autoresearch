"""Finding 138's rules: the glyph triage's windows and scores, the place on our windings, and the registered table."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


glyph = _load("glyph", "repro/first_letters/triage/glyph.py")
bt = _load("band_triage", "repro/first_letters/pherc0211_control/band_triage.py")


def test_constants_are_the_registered_ones():
    assert (glyph.WIN, glyph.STEP, glyph.MIN_ON, glyph.GWIN, glyph.GSTEP, glyph.ONSHEET, glyph.UM50) == (
        2600, 1300, 0.3, 128, 16, 0.7, 50.0,
    )  # fmt: skip
    assert glyph.COMMIT == "feabff6c54f95bd8e52a90e0a7a76881ee67d4cc"
    assert (
        glyph.WEIGHTS_SHA
        == "36ae0d6d9fdaac9d8681af75ec9be17e9317f7f77aa9422ea8ff8d09dd6f19ad"
    )
    assert (bt.MIN_PLACE_CELLS, bt.FIRST, bt.HIGH_SHARE) == (1000, 10, 0.05)


@pytest.mark.parametrize(
    "width, expected",
    [
        (2000, [0]),  # narrower than a window: one window, as theirs
        (2600, [0]),
        (3900, [0, 1300]),  # the second window ends at the winding's end
        (
            4580,
            [0, 1300, 1980],
        ),  # ours: a last window ending at the end, which theirs leaves unscored
        (5200, [0, 1300, 2600]),
    ],
)
def test_window_starts(width, expected):
    assert glyph.starts(width) == expected


@pytest.mark.parametrize(
    "rank, windows, places, expected",
    [
        (1, 600, 3, "TRIAGE_FINDS_THE_TEXT"),
        (10, 600, 3, "TRIAGE_FINDS_THE_TEXT"),
        (11, 600, 3, "TRIAGE_RANKS_THE_TEXT_HIGH"),
        (30, 600, 3, "TRIAGE_RANKS_THE_TEXT_HIGH"),  # 5% of 600
        (31, 600, 3, "TRIAGE_MISSES_THE_TEXT"),
        (
            11,
            100,
            3,
            "TRIAGE_MISSES_THE_TEXT",
        ),  # 5% of 100 is under ten: the line is ten
        (None, 600, 0, "BAND_READ_MISSES_THE_PLACE"),
        (None, 600, 2, "DOES_NOT_RUN"),  # place windows with no score
    ],
)
def test_the_registered_table(rank, windows, places, expected):
    assert bt.verdict(rank, windows, places) == expected


def test_a_window_holds_the_place_by_the_cells_in_its_columns():
    # winding 0's lattice is 10 cells wide: its cells 3 and 7 are lattice columns 3 and 7, render pixels 14 and 30;
    # the cell winding 1 gives and the point no winding reaches are not winding 0's
    which = np.array([[0, 0, 1, -1]])
    cell = np.array([[3, 7, 5, 0]])
    inside = np.array([[True, True, True, True]])
    columns = bt.place_cells(which, cell, inside, 0, 10)
    assert sorted(columns.tolist()) == [3 * 4 + 2, 7 * 4 + 2]
    counts = bt.window_counts(np.array([10] * 1500 + [3000] * 999), 4600)
    assert counts == [
        {"x0": 0, "place_cells": 1500},
        {"x0": 1300, "place_cells": 999},
        {"x0": 2000, "place_cells": 999},
    ]
    place = {"windows": {"w035": {"by_window": counts}}}
    assert bt.holds_place(place) == {("w035", 0)}  # 999 cells is under the 1,000 line


def test_the_rank_of_the_best_place_window():
    record = {"windings": {
        "w010": [{"x0": 0, "glyph": 15.0, "rows": 1.0}, {"x0": 1300, "glyph": None, "rows": None}],
        "w035": [{"x0": 0, "glyph": 14.0, "rows": 9.0}, {"x0": 1300, "glyph": 13.0, "rows": 2.0}],
        "w050": [{"x0": 0, "glyph": 14.0, "rows": 0.5}],
    }}  # fmt: skip
    order = bt.ranked(record)
    assert [(x["winding"], x["x0"]) for x in order] == [
        ("w010", 0),
        ("w035", 0),
        ("w050", 0),
        ("w035", 1300),
    ]
    assert bt.best_rank(order, {("w035", 1300)}) == 4
    assert bt.best_rank(order, {("w099", 0)}) is None


def test_the_verdict_record(tmp_path):
    record = {
        "windings": {
            f"w{n:03d}": [{"x0": 0, "glyph": float(n), "rows": 0.0}]
            for n in range(10, 40)
        }
    }
    place = {
        "windows": {
            "w035": {"place_cells": 5000, "by_window": [{"x0": 0, "place_cells": 5000}]}
        }
    }
    (tmp_path / "g.json").write_text(json.dumps(record))
    (tmp_path / "p.json").write_text(json.dumps(place))
    assert (
        bt.main(
            [
                "verdict",
                str(tmp_path / "t.json"),
                str(tmp_path / "g.json"),
                str(tmp_path / "p.json"),
            ]
        )
        == 0
    )
    out = json.loads((tmp_path / "t.json").read_text())
    assert out["registered"]["best_place_rank"] == 5  # w039..w035
    assert out["verdict"] == "TRIAGE_FINDS_THE_TEXT"
    assert out["described"]["place_windings_rank_by_best_window"] == {"w035": 5}


def test_a_winding_far_from_the_winner_is_not_carried():
    xyz = np.zeros((2, 2, 3))
    xyz[..., 0] = 500.0
    valid = np.ones((2, 2), bool)
    assert not bt.near_box(
        xyz, valid, np.array([0.0, 0, 0]), np.array([100.0, 100, 100])
    )
    xyz[0, 0] = [50, 50, 50]
    assert bt.near_box(xyz, valid, np.array([0.0, 0, 0]), np.array([100.0, 100, 100]))


def test_the_overlay_and_sub_windows():
    prob = np.zeros((900, 1300), np.float32)
    sheet = np.zeros(prob.shape, bool)
    sheet[:, :800] = True
    prob[sheet] = np.random.default_rng(0).random(sheet.sum())
    z = glyph.zscore(prob, sheet)
    assert abs(z[sheet].mean()) < 1e-4 and (z[~sheet] == 0).all()
    a, m = glyph.overlay(z, sheet, 9.362)
    assert a.shape == m.shape and ((a >= 0) & (a <= 1)).all() and not a[~m].any()
    ws = glyph.sub_windows(m)
    assert ws and all(m[y : y + 128, x : x + 128].mean() >= 0.7 for y, x in ws)


def test_the_row_score_needs_tiles():
    assert glyph.row_score(np.zeros((300, 300), np.float32), 9.362) == 0.0  # no sheet
    rows = np.zeros((1200, 2600), np.float32)
    rows[(np.arange(1200) // 25) % 20 < 4] = (
        3.0  # bands about 4.7 mm apart: rows of "ink"
    )
    rows += np.random.default_rng(1).normal(0, 0.3, rows.shape).astype(np.float32)
    assert glyph.row_score(rows, 9.362) > 3.0


def test_the_weights_are_checked(tmp_path):
    bad = tmp_path / "gA.pt"
    bad.write_bytes(b"not the weights")
    with pytest.raises(SystemExit, match="is not gA.pt"):
        glyph.load_model(bad)


def test_the_network_scores_every_sub_window_with_its_augmentation():
    torch = pytest.importorskip("torch")
    torch.manual_seed(0)
    net = glyph.glyph_net().eval()
    a = np.random.default_rng(2).random((140, 300)).astype(np.float32)
    m = np.ones(a.shape, bool)
    ws = glyph.sub_windows(m)
    s = glyph.logits(net, a, m, ws, bs=7)
    assert s.shape == (len(ws),) and np.isfinite(s).all()
    with torch.no_grad():  # the first sub-window by hand: the mean of five views
        A = torch.from_numpy(a[None, None, :128, :128].copy())
        M = torch.ones_like(A)
        views = [net(A, M)] + [
            net(torch.rot90(A, k, (2, 3)), torch.rot90(M, k, (2, 3))) for k in (1, 2, 3)
        ]
        views.append(net(A.flip(3), M.flip(3)))
        assert abs(float(sum(views) / 5) - float(s[ws.index((0, 0))])) < 1e-4
