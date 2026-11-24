"""Finding 135's analysis: shifted planes, the chosen shift, and the registered verdict with its failure branches."""

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "repro/first_letters/pherc0211_control"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ds = _load("depth_sweep_under_test", CONTROL / "depth_sweep.py")


def _render(path: Path, layers: int) -> Path:
    import zarr

    first = (
        (66 - layers) // 2
    )  # a centred render holds these layers of the 66-layer frame (render_frame.py)
    data = np.zeros((layers, 4, 5), np.uint8)
    for i in range(layers):
        data[i] = first + i  # each layer carries its 66-frame number
    zarr.open(str(path), mode="w").create_dataset("0", data=data, chunks=(layers, 4, 5))
    return path


def _curves(e2e=None, dense=None):
    flat = {d: 0.80 for d in ds.SHIFTS}
    return {"e2e": {**flat, **(e2e or {})}, "dense2s3": {**flat, **(dense or {})}}


SHARES = {"e2e": 0.83, "dense2s3": 0.83}


def test_shift_zero_is_finding_124s_planes_and_a_shift_moves_every_plane(tmp_path):
    assert ds.shifted_layers(0) == ds.f124.LAYERS
    render = _render(tmp_path / "w_66.zarr", 66)
    ds.planes_cmd(render, tmp_path / "p.npy", 2)
    planes = np.load(tmp_path / "p.npy")
    assert [int(p[0, 0]) for p in planes] == list(range(43, 27, -1))


def test_a_shift_outside_the_render_is_refused(tmp_path):
    with pytest.raises(ValueError):
        ds.shifted_layers(25)  # layer 66 is past the frame
    thin = _render(
        tmp_path / "w_18.zarr", 18
    )  # layers 24 to 41: the band reads' render
    ds.planes_cmd(thin, tmp_path / "zero.npy", 0)
    with pytest.raises(SystemExit, match="not in a 18-layer render"):
        ds.planes_cmd(thin, tmp_path / "out.npy", 1)


def test_the_best_shift_breaks_ties_toward_zero_then_outward():
    assert ds.best_shift(_curves()) == 0
    assert ds.best_shift(_curves({2: 0.81, -2: 0.81})) == 2
    assert ds.best_shift(_curves({-1: 0.83}, {-1: 0.82})) == -1
    missing = _curves()
    missing["e2e"][4] = None
    assert ds.best_shift(missing) is None


def test_a_shift_reads_better_only_when_both_arms_gain_the_line():
    v, d, gains = ds.verdict(_curves({2: 0.82}, {2: 0.82}), SHARES, True)
    assert (v, d, gains) == (
        "DEPTH_SHIFT_READS_BETTER",
        2,
        {"e2e": 0.02, "dense2s3": 0.02},
    )  # exactly at the line
    v, d, gains = ds.verdict(_curves({2: 0.85}, {2: 0.819}), SHARES, True)
    assert v == "DEPTH_SHIFT_WITHIN_MARGIN" and d == 2 and gains["dense2s3"] == 0.019
    assert (
        ds.verdict(_curves({1: 0.79}, {1: 0.79}), SHARES, True)[0] == "DEPTH_ZERO_BEST"
    )


def test_the_failure_branch_gives_no_verdict_even_with_a_clear_gain():
    clear = _curves({2: 0.9}, {2: 0.9})
    assert ds.verdict(clear, SHARES, False) == (
        "DOES_NOT_RUN",
        None,
        None,
    )  # finding 124 not reproduced
    assert (
        ds.verdict(clear, {"e2e": 0.83, "dense2s3": 0.49}, True)[0] == "DOES_NOT_RUN"
    )  # too few cells
    assert ds.verdict(None, SHARES, True)[0] == "DOES_NOT_RUN"


def test_a_partial_sweep_is_refused():
    one_arm = {"e2e": _curves()["e2e"]}
    assert ds.verdict(one_arm, SHARES, True)[0] == "DOES_NOT_RUN"
    short = _curves()
    del short["dense2s3"][8]
    assert ds.verdict(short, SHARES, True)[0] == "DOES_NOT_RUN"
    unscored = _curves()
    unscored["dense2s3"][-8] = None
    assert ds.verdict(unscored, SHARES, True)[0] == "DOES_NOT_RUN"


def test_half_widths_are_the_nearest_shift_at_half_of_zero_on_each_side():
    curve = {d: 0.8 for d in ds.SHIFTS}
    curve.update({-4: 0.41, -6: 0.40, -8: 0.1, 4: 0.5, 6: 0.3, 8: 0.2})
    assert ds.half_widths(curve) == {"inward": 6, "outward": 6}
    assert ds.half_widths({d: 0.8 for d in ds.SHIFTS}) == {
        "inward": None,
        "outward": None,
    }
    assert (
        ds.shift_dir(-2) == "d-2"
        and ds.shift_dir(0) == "d+0"
        and ds.shift_dir(4) == "d+4"
    )


# --- the edges of the frame, the sum and the share; compare and compare343 run, with finding 110's side and transfer
# stood in for as rounds #217 and #221 tested findings 131 and 134; carry_arm with its readers stood in for; main ---


def test_the_deepest_inward_shift_reaches_layer_0_and_no_further():
    assert ds.shifted_layers(-26)[-1] == 0
    with pytest.raises(ValueError, match="leaves the 66-layer frame"):
        ds.shifted_layers(-27)


def test_a_16_bit_render_is_refused(tmp_path):
    import zarr

    zarr.open(str(tmp_path / "w_66.zarr"), mode="w").create_dataset(
        "0", data=np.zeros((66, 4, 5), np.uint16), chunks=(66, 4, 5)
    )
    with pytest.raises(SystemExit, match="not 8-bit"):
        ds.planes_cmd(tmp_path / "w_66.zarr", tmp_path / "p.npy", 0)


def test_the_summed_r_is_compared_at_four_decimals():
    curves = {arm: dict.fromkeys(ds.SHIFTS, 0.0) for arm in ds.ARMS}
    curves["e2e"][0] = 0.3
    curves["e2e"][1], curves["dense2s3"][1] = (
        0.1,
        0.2,
    )  # 0.30000000000000004 in floating point: a tie with D = 0
    assert ds.best_shift(curves) == 0


def test_the_verdict_runs_at_exactly_half_the_mask():
    shares = {"e2e": 0.5, "dense2s3": 0.5}
    assert (
        ds.verdict(_curves({2: 0.82}, {2: 0.82}), shares, True)[0]
        == "DEPTH_SHIFT_READS_BETTER"
    )


def test_an_arms_cells_need_a_winding_a_reversed_map_and_every_shifts_map():
    which = np.zeros((3, 4), int)
    which[0, 0] = -1
    other = np.ones((3, 4))
    other[1, 1] = np.nan
    carried = {d: np.ones((3, 4)) for d in ds.SHIFTS}
    carried[6][2, 2] = np.nan
    cells = ds.arm_cells({"which": which, "other": other, "carried": carried})
    assert np.argwhere(~cells).tolist() == [[0, 0], [1, 1], [2, 2]]


def test_an_arm_is_carried_once_and_reads_each_shifts_maps_from_its_own_folder(
    tmp_path, monkeypatch
):
    transfers = []

    def transfer(points, ok, sides):
        transfers.append(sides)
        return 1, 2, 3

    monkeypatch.setattr(ds.f131, "side", lambda final, render: {"points": final.name, "ok": render.name,
                                                                 "canvas": (8, 8), "mesh": str(final)})  # fmt: skip
    monkeypatch.setattr(ds.analysis, "transfer", transfer)
    monkeypatch.setattr(
        ds.f124, "read_studio", lambda path, canvas: str(path)
    )  # each map is named by its file
    monkeypatch.setattr(
        ds.f121, "carry", lambda maps, which, cell: {"s": [m["s"] for m in maps]}
    )
    monkeypatch.setattr(
        ds.analysis, "normals_agree", lambda wp, sp, which, cell, k: -0.9 - k / 100
    )
    arm = ds.carry_arm({"points": "winner", "ok": "ok"}, ["w033", "w034"], tmp_path / "finals",
                       tmp_path / "renders", tmp_path / "zero", tmp_path / "sweep")  # fmt: skip
    assert transfers == [
        [("w033.tifxyz", "w033_66.zarr"), ("w034.tifxyz", "w034_66.zarr")]
    ]
    assert sorted(arm["carried"]) == sorted(ds.SHIFTS)
    for d, folder in ((0, "zero"), (-2, "sweep/d-2"), (4, "sweep/d+4")):
        assert arm["carried"][d] == [
            str(tmp_path / folder / "w033.npy"),
            str(tmp_path / folder / "w034.npy"),
        ]
    assert arm["other"] == [
        str(tmp_path / "zero/w033_reversed.npy"),
        str(tmp_path / "zero/w034_reversed.npy"),
    ]
    assert arm["cosines"] == [-0.9, -0.91]
    assert arm["meshes"] == [
        str(tmp_path / "finals/w033.tifxyz"),
        str(tmp_path / "finals/w034.tifxyz"),
    ]


H, W = 48, 48  # the winner's lattice cells


def _compare(tmp_path, monkeypatch, cosines=None, shares=None):
    """A Studio map, mask and our render's map on the winner's 192 x 192-pixel canvas, and both arms with a carried
    map for every shift. e2e lacks row 0 (no winding), row 3 (no reversed map) and, at D = -8 only, row 4; dense2s3
    lacks row 2 at D = +8 only. The mask leaves out the first one and a half columns of cells, and our render's map
    row 5. In dense2s3, winding w034 has exactly finding 121's 1,000 cells (rows 10 to 34, columns 6 to 45)."""
    import argparse

    import cv2
    import tifffile

    tmp_path.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(9)
    px = rng.random((H * 4, W * 4))
    tifffile.imwrite(tmp_path / "studio.tif", px.astype(np.float32))
    mask = np.full(px.shape, 255, np.uint8)
    mask[:, :6] = 0
    cv2.imwrite(str(tmp_path / "mask.png"), mask)
    own = px.copy()
    own[20:24] = np.nan  # our render's map has no value on cell row 5
    np.save(tmp_path / "own.npy", own.astype(np.float32))
    studio = ds.analysis.block_mean(px)
    monkeypatch.setattr(
        ds.tm, "side", lambda *a, **k: {"ok": np.ones((H, W), bool), "points": None}
    )
    arms = {}
    for k, name in enumerate(ds.ARMS):
        which = np.zeros((H, W), int)
        other = rng.random((H, W))
        carried = {
            d: studio + rng.normal(0, 0.05 + 0.02 * abs(d), (H, W)) for d in ds.SHIFTS
        }
        if name == "e2e":
            which[0] = -1
            other[3] = np.nan
            carried[-8][4] = np.nan
        else:
            which[10:35, 6:46] = 1
            carried[8][2] = np.nan
        dist = (
            np.repeat(np.arange(H, dtype=float)[:, None], W, axis=1) + k
        )  # each cell's row, plus the arm's index
        arms[name] = {"which": which, "dist": dist, "cosines": (cosines or {}).get(name, [-0.99, -0.99]),
                      "carried": carried, "other": other, "meshes": [name]}  # fmt: skip
    monkeypatch.setattr(
        ds,
        "carry_arm",
        lambda winner, windings, finals, renders, zero, sweep: arms[finals.name],
    )
    monkeypatch.setattr(
        ds.f131,
        "sheet_share",
        lambda sdt, finals, windings: None
        if sdt is None
        else (shares or {})[finals.name],
    )
    arm = [[n, *[str(tmp_path / n)] * 4] for n in arms]
    args = argparse.Namespace(winner_mesh=tmp_path, winner_maps=tmp_path, winner_render=tmp_path,
                              studio=tmp_path / "studio.tif", studio_mask=tmp_path / "mask.png",
                              ours_render_map=tmp_path / "own.npy", windings=["w033", "w034"],
                              sdt=tmp_path / "sdt" if shares else None, arm=arm)  # fmt: skip
    return args, studio, arms


def test_both_arms_are_scored_at_every_shift_on_the_cells_each_reaches_at_all_of_them(
    tmp_path, monkeypatch
):
    args, studio, arms = _compare(tmp_path, monkeypatch)
    result = ds.compare_cmd(args)
    # the mask's whole cells: columns 2 to 47; our render's map and every shift of the arm reach the rest of them
    assert result["mask_cells"] == 48 * 46
    assert result["cells"] == {"e2e": 44 * 46, "dense2s3": 46 * 46}
    assert result["cell_share"] == {
        "e2e": round(44 / 48, 4),
        "dense2s3": round(46 / 48, 4),
    }
    assert sorted(result["registered"]["r"]["dense2s3"]) == sorted(
        ds.shift_dir(d) for d in ds.SHIFTS
    )
    # finding 124's own cells: e2e at D = 0, which another shift's missing row does not narrow
    own_cells = np.ones((H, W), bool)
    own_cells[[0, 3, 5]] = False
    own_cells[:, :2] = False
    e2e = arms["e2e"]
    assert (
        result["f124_r_on_its_own_cells"]
        == ds.score_one(studio, e2e["carried"][0], e2e["other"], own_cells)["r"]
    )
    assert result["f124_reproduced"] is False and result["verdict"] == "DOES_NOT_RUN"
    d = result["described"]
    assert {w: v["cells"] for w, v in d["by_winding"]["dense2s3"].items()} == {
        "w033": 46 * 46 - 1000,
        "w034": 1000,
    }
    assert (
        d["by_winding"]["dense2s3"]["w034"]["r"]["d+0"] is not None
    )  # exactly 1,000 cells are enough
    assert d["by_winding"]["e2e"]["w034"] == {
        "cells": 0,
        "r": {ds.shift_dir(s): None for s in ds.SHIFTS},
    }
    rows = {
        "e2e": [r for r in range(H) if r not in (0, 3, 4, 5)],
        "dense2s3": [r for r in range(H) if r not in (2, 5)],
    }
    for k, name in enumerate(ds.ARMS):  # over each arm's cells only
        p50, p95 = np.percentile(
            np.repeat(np.array(rows[name], float) + k, 46), [50, 95]
        )
        assert d["transfer_distance_voxels"][name] == {
            "p50": round(p50, 2),
            "p95": round(p95, 2),
        }
    assert d["final_nodes_within_2_of_the_predicted_sheet"] == {
        "e2e": None,
        "dense2s3": None,
    }


def test_the_verdict_runs_once_finding_124s_r_is_given_again_and_the_sheet_share_is_the_fields(
    tmp_path, monkeypatch
):
    shares = {
        "e2e": {"w033": 0.9, "w034": 0.8},
        "dense2s3": {"w033": 0.95, "w034": 0.85},
    }
    first = ds.compare_cmd(_compare(tmp_path / "a", monkeypatch, shares=shares)[0])
    monkeypatch.setattr(ds, "F124_R", first["f124_r_on_its_own_cells"])
    again = ds.compare_cmd(_compare(tmp_path / "b", monkeypatch, shares=shares)[0])
    r = {
        arm: {d: again["registered"]["r"][arm][ds.shift_dir(d)] for d in ds.SHIFTS}
        for arm in ds.ARMS
    }
    assert again["f124_reproduced"] is True
    assert (
        again["verdict"],
        again["registered"]["best_shift"],
        again["registered"]["gain_over_zero"],
    ) == ds.verdict(r, again["cell_share"], True)
    assert again["verdict"] != "DOES_NOT_RUN"
    assert again["described"]["final_nodes_within_2_of_the_predicted_sheet"] == shares


@pytest.mark.parametrize(
    ("cosines", "stops"),
    [
        ({"dense2s3": [-0.99, 0.0]}, True),
        ({"e2e": [None, -0.99]}, True),
        ({"e2e": [-0.01, -0.99]}, False),
    ],
    ids=[
        "a-zero-cosine-stops",
        "a-winding-with-no-cells-stops",
        "any-negative-cosine-does-not",
    ],
)
def test_a_winding_with_no_cells_or_a_render_against_the_winners_normals_stops_the_comparison(
    tmp_path, monkeypatch, cosines, stops
):
    result = ds.compare_cmd(_compare(tmp_path, monkeypatch, cosines)[0])
    assert (
        result.get("why") == "a render samples against the winner's normals"
    ) is stops
    assert ("cells" in result) is not stops


def test_an_unreadable_mask_stops_the_comparison(tmp_path, monkeypatch):
    args = _compare(tmp_path, monkeypatch)[0]
    args.studio_mask.write_text("not an image")
    with pytest.raises(SystemExit, match="cannot read"):
        ds.compare_cmd(args)


def _compare343(tmp_path):
    """PHerc. 343: a 66-layer render whose layer 10 is empty over the first cell of the sidecar's area, the recipe's
    ink image with cells at exactly 0.35 and at 89.5 / 255, and Studio's maps: the ink plus noise that grows with
    |D - 2|."""
    import argparse

    import cv2
    import zarr

    rng = np.random.default_rng(11)
    data = np.full((66, 100, 132), 50, np.uint8)
    data[10, 2:6, 2:6] = 0
    zarr.open(str(tmp_path / "r_66.zarr"), mode="w").create_dataset(
        "0", data=data, chunks=(66, 100, 132)
    )
    sidecar = {"area": {"raw_render_px": {"row0": 2, "row1": 98, "col0": 2, "col1": 130}},
               "orientation": {"flip_ud": False, "flip_lr": False}}  # fmt: skip
    (tmp_path / "sidecar.json").write_text(json.dumps(sidecar))
    ink = np.kron(rng.integers(0, 256, (24, 32)), np.ones((4, 4))).astype(np.uint8)
    ink[0:4, 8:12] = np.array([89] * 12 + [90] * 4).reshape(
        4, 4
    )  # its cell's mean is 0.35 exactly
    ink[4:24, 16:32] = np.tile(
        np.array([[89, 90], [90, 89]], np.uint8), (10, 8)
    )  # 89.5: drawn at / 255, not / 256
    cv2.imwrite(str(tmp_path / "ink.png"), ink)
    reference = ink / 255.0
    sweep = tmp_path / "sweep"

    def raw(reading):
        out = np.zeros((100, 132))
        out[2:98, 2:130] = reading
        return out

    maps = {}
    for d in ds.SHIFTS:
        maps[d] = raw(reference + rng.normal(0, 0.05 + 0.1 * abs(d - 2), (96, 128)))
        path = (
            tmp_path / "zero.npy" if d == 0 else sweep / ds.shift_dir(d) / "forward.npy"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, maps[d])
    np.save(tmp_path / "zero_reversed.npy", raw(rng.random((96, 128))))
    args = argparse.Namespace(render=tmp_path / "r_66.zarr", sidecar=tmp_path / "sidecar.json",
                              ink_png=tmp_path / "ink.png", zero=tmp_path / "zero.npy",
                              zero_reversed=tmp_path / "zero_reversed.npy", sweep=sweep)  # fmt: skip
    return args, ink, maps


def test_finding_127s_statistic_is_given_for_every_shift_on_the_cells_every_layer_renders(
    tmp_path, monkeypatch
):
    args, ink, maps = _compare343(tmp_path)
    result = ds.compare343_cmd(args)
    cells = np.ones((24, 32), bool)
    cells[0, 0] = False  # layer 10 is empty there
    a = ds.analysis
    reference = a.block_mean(ink / 255.0)
    theirs = a.highpass(reference, cells)
    drawn = (reference >= 0.35) & cells
    other = a.block_mean(np.load(args.zero_reversed)[2:98, 2:130])
    expected = {ds.shift_dir(d): ds.f124.score(theirs, drawn, a.block_mean(maps[d][2:98, 2:130]), cells, other)
                for d in ds.SHIFTS}  # fmt: skip
    assert result["cells"] == 24 * 32 - 1
    assert result["each_shift"] == expected
    assert result["r"] == {k: v["r"] for k, v in expected.items()}
    assert result["best_shift"] == 2 and result["described_only"] is True
    assert result["half_widths"] == ds.half_widths(
        {d: result["r"][ds.shift_dir(d)] for d in ds.SHIFTS}
    )
    assert result["f127_reproduced"] is False
    monkeypatch.setattr(ds, "F127_R", result["r"]["d+0"])
    assert ds.compare343_cmd(args)["f127_reproduced"] is True


def test_an_unscored_shift_is_never_the_best_at_343(tmp_path, monkeypatch):
    args = _compare343(tmp_path)[0]
    r = {
        d: None if d == 8 else (-0.1 if d == 2 else -0.5) for d in ds.SHIFTS
    }  # every scored shift reads negative
    order = iter(ds.SHIFTS)
    monkeypatch.setattr(ds.f124, "score", lambda *a: {"r": r[next(order)]})
    assert ds.compare343_cmd(args)["best_shift"] == 2


@pytest.mark.parametrize(
    ("arrange", "message"),
    [
        ("layers", "has 65 layers, not 66"),
        ("unreadable", "cannot read"),
        ("ink_shape", "the area"),
        ("map_shape", "the render"),
    ],  # fmt: skip
)
def test_a_render_ink_image_or_map_that_does_not_fit_is_refused_at_343(
    tmp_path, arrange, message
):
    import cv2
    import zarr

    args = _compare343(tmp_path)[0]
    if arrange == "layers":
        zarr.open(str(args.render), mode="w").create_dataset(
            "0", data=np.full((65, 100, 132), 50, np.uint8)
        )
    elif arrange == "unreadable":
        args.ink_png.write_text("not an image")
    elif arrange == "ink_shape":
        cv2.imwrite(str(args.ink_png), np.zeros((96, 124), np.uint8))
    else:
        np.save(args.sweep / "d+4" / "forward.npy", np.zeros((100, 128)))
    with pytest.raises(SystemExit, match=message):
        ds.compare343_cmd(args)


def test_the_command_needs_both_arms_writes_once_prints_the_registered_part_and_exits_1_when_it_does_not_run(
    tmp_path, monkeypatch, capsys
):
    record = {
        "finding": 135,
        "verdict": "DOES_NOT_RUN",
        "registered": {"best_shift": None},
        "described": {"x": 1},
    }
    monkeypatch.setattr(ds, "compare_cmd", lambda args: record)
    argv = ["compare", str(tmp_path / "o.json")]
    for flag in (
        "--winner-mesh",
        "--winner-maps",
        "--winner-render",
        "--studio",
        "--studio-mask",
        "--ours-render-map",
    ):
        argv += [flag, str(tmp_path)]
    argv += ["--windings", "w033"]
    arm = lambda name: ["--arm", name, *[str(tmp_path)] * 4]  # noqa: E731
    with pytest.raises(SystemExit, match="the arms are e2e, dense2s3"):
        ds.main(argv + arm("e2e") + arm("e2e"))
    assert ds.main(argv + arm("e2e") + arm("dense2s3")) == 1
    assert json.loads(capsys.readouterr().out) == {
        k: v for k, v in record.items() if k != "described"
    }
    assert json.loads((tmp_path / "o.json").read_text()) == record
    assert ds.main(argv + arm("e2e") + arm("dense2s3")) == 2  # written once
    described = {
        "finding": 135,
        "described_only": True,
        "r": {"d+0": 0.6},
        "each_shift": {"d+0": {}},
    }
    monkeypatch.setattr(ds, "compare343_cmd", lambda args: described)
    argv343 = ["compare343", str(tmp_path / "h.json")]
    for flag in (
        "--render",
        "--sidecar",
        "--ink-png",
        "--zero",
        "--zero-reversed",
        "--sweep",
    ):
        argv343 += [flag, str(tmp_path)]
    capsys.readouterr()
    assert ds.main(argv343) == 0  # described only: no verdict to fail
    assert json.loads(capsys.readouterr().out) == {
        "finding": 135,
        "described_only": True,
        "r": {"d+0": 0.6},
    }


# --- run_depth_sweep.sh: each block taken from the script's text and run under bash -u with stand-in commands ------

SCRIPT = CONTROL / "run_depth_sweep.sh"
ARRAYS = 'declare -A RENDERS=([e2e]={t}/renders/e2e [dense2s3]={t}/renders/dense2s3)\n' \
         'declare -A ZERO=([e2e]={t}/zero/e2e [dense2s3]={t}/zero/dense2s3)\n' \
         'declare -A FINALS=([e2e]={t}/finals/e2e [dense2s3]={t}/finals/dense2s3)\n'  # fmt: skip


def _block(start, end):
    """The script's text from the line holding START to the end of the line holding END after it."""
    text = SCRIPT.read_text()
    a = text.rindex("\n", 0, text.index(start)) + 1
    return text[a : text.index("\n", text.index(end, a)) + 1]


def _function(name):
    text = SCRIPT.read_text()
    a = text.index(f"\n{name}() {{") + 1
    return text[a : text.index("\n}\n", a) + 3]


def _bash(script, path=None):
    env = {"PATH": f"{path}:/usr/bin:/bin" if path else "/usr/bin:/bin"}
    return subprocess.run(
        ["bash", "-uc", script], capture_output=True, text=True, env=env
    )


def _stub(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\n" + body)
    path.chmod(0o755)
    return path


def _inputs(t):
    """The run's inputs on disk: every arm's renders and D = 0 maps, and PHerc. 343's render and forward map."""
    for arm in ds.ARMS:
        for w in ("w033", "w034"):
            (t / "renders" / arm / f"{w}_66.zarr" / "0").mkdir(parents=True)
            for name in (f"{w}.npy", f"{w}_reversed.npy"):
                (t / "zero" / arm).mkdir(parents=True, exist_ok=True)
                (t / "zero" / arm / name).write_text("")
    (t / "b343" / "N_66.zarr" / "0").mkdir(parents=True)
    (t / "b343" / "studio_343" / "maps").mkdir(parents=True)
    (t / "b343" / "studio_343" / "maps" / "forward.npy").write_text("")
    _stub(t / "env" / "bin" / "python", "")


@pytest.mark.parametrize(
    ("arrange", "message"),
    [
        (None, None),
        ("out", "exists: finding 135 runs once"),
        ("env", "finding 123's Studio environment is missing"),
        ("renders/e2e/w034_66.zarr/0", "e2e w034: render or D = 0 maps missing"),
        (
            "zero/dense2s3/w034_reversed.npy",
            "dense2s3 w034: render or D = 0 maps missing",
        ),
        (
            "b343/studio_343/maps/forward.npy",
            "finding 110's render or finding 127's maps are missing",
        ),
    ],
)
def test_the_renders_and_d0_maps_are_required_before_anything_runs(
    tmp_path, arrange, message
):
    import shutil

    _inputs(tmp_path)
    if arrange == "out":
        (tmp_path / "out").mkdir()
    elif arrange == "env":
        shutil.rmtree(tmp_path / "env")
    elif arrange:
        target = tmp_path / arrange
        shutil.rmtree(target) if target.is_dir() else target.unlink()
    run = _bash(
        f"OUT={tmp_path}/out ENV={tmp_path}/env WINDINGS=(w033 w034) B343={tmp_path}/b343 N343=N\n"
        + ARRAYS.format(t=tmp_path)
        + _block(
            '[ -e "$OUT" ] &&', "finding 110's render or finding 127's maps are missing"
        )
        + "echo checked\n"
    )
    if message is None:
        assert (run.returncode, run.stdout) == (0, "checked\n")
    else:
        assert (run.returncode, run.stdout) == (2, "")
        assert message in run.stderr


def test_a_failed_step_records_its_gate_and_stops_the_run(tmp_path):
    (tmp_path / "logs").mkdir()
    run = _bash(
        f"OUT={tmp_path}\n"
        f'control_gate() {{ echo "GATE $1 $2" >> {tmp_path}/gates; }}\n'
        + _function("step")
        + "step one true\nstep two false\necho after\n"
    )
    assert run.returncode == 1 and "after" not in run.stdout
    assert (
        tmp_path / "gates"
    ).read_text() == "GATE depth_sweep_one 0\nGATE depth_sweep_two 1\n"


def _sweep(tmp_path, fail_shift=None, compare_rc=0, compare343_rc=0):
    """Stand-ins: PYW makes a shift's planes (failing at FAIL_SHIFT) and exits as told for compare and compare343;
    Studio writes its output and logs its working folder and arguments."""
    _inputs(tmp_path)
    _stub(
        tmp_path / "pyw",
        f"""echo "$*" >> {tmp_path}/pyw.log
case "$3" in
  planes) [ "${{@: -1}}" = "{fail_shift}" ] && exit 1; : > "$5" ;;
  compare) exit {compare_rc} ;;
  compare343) exit {compare343_rc} ;;
esac
""",
    )
    _stub(
        tmp_path / "env" / "bin" / "python",
        f'echo "$PWD $*" >> {tmp_path}/studio.log\n: > "$5"\n',
    )
    (tmp_path / "code").mkdir()
    (tmp_path / "out" / "planes").mkdir(parents=True)
    return (
        f"OUT={tmp_path}/out ENV={tmp_path}/env PYW={tmp_path}/pyw HERE={tmp_path}/here CODE={tmp_path}/code "
        f"WEIGHTS=/w.safetensors WINDINGS=(w033) SHIFTS=(-2 1) B343={tmp_path}/b343 N343=N\n"
        + ARRAYS.format(t=tmp_path)
        + _function("studio")
        + _function("one")
        + _function("sweep211")
        + _function("sweep343")
    )


def test_every_arm_winding_and_shift_is_read_with_the_winners_command_into_its_shifts_folder(
    tmp_path,
):
    run = _bash(_sweep(tmp_path) + "sweep211 && sweep343")
    assert run.returncode == 0, run.stderr
    out = tmp_path / "out"
    maps = sorted(str(p.relative_to(out)) for p in (out / "maps").rglob("*.npy"))
    assert maps == ["maps/343/d+1/forward.npy", "maps/343/d-2/forward.npy", "maps/dense2s3/d+1/w033.npy",
                    "maps/dense2s3/d-2/w033.npy", "maps/e2e/d+1/w033.npy", "maps/e2e/d-2/w033.npy"]  # fmt: skip
    assert (
        list((out / "planes").iterdir()) == []
    )  # each shift's planes are deleted once read
    planes = [line.split() for line in (tmp_path / "pyw.log").read_text().splitlines()]
    assert planes[0] == ["-I", f"{tmp_path}/here/depth_sweep.py", "planes", f"{tmp_path}/renders/e2e/w033_66.zarr",
                         f"{out}/planes/w033.npy", "--shift", "-2"]  # fmt: skip
    assert [p[-1] for p in planes] == ["-2", "1", "-2", "1", "-2", "1"]
    studio = (tmp_path / "studio.log").read_text().splitlines()[0].split()
    assert studio == [str(tmp_path / "code"), "inference.py", "--input", f"{out}/planes/w033.npy", "--output",
                      f"{out}/maps/e2e/d-2/w033.npy", "--checkpoint", "/w.safetensors", "--stride", "64", "--blend",
                      "hann", "--batch-size", "32"]  # fmt: skip


def test_a_shift_whose_planes_fail_stops_the_sweep_before_studio_reads_it(tmp_path):
    run = _bash(_sweep(tmp_path, fail_shift=1) + "sweep211")
    assert run.returncode == 1
    out = tmp_path / "out"
    assert sorted(str(p.relative_to(out)) for p in (out / "maps").rglob("*.npy")) == [
        "maps/e2e/d-2/w033.npy"
    ]
    assert not (out / "maps" / "dense2s3").exists()


@pytest.mark.parametrize(
    ("compare_rc", "compare343_rc", "rc"), [(0, 0, 0), (1, 0, 1), (0, 1, 1)],
    ids=["both-run", "no-verdict-still-describes-343", "343-fails"],
)  # fmt: skip
def test_compare_describes_343_even_without_a_verdict_and_fails_if_either_fails(
    tmp_path, compare_rc, compare343_rc, rc
):
    (tmp_path / "r" / "work" / "surf_sdt" / "a_surf_sdt.ome.zarr").mkdir(parents=True)
    run = _bash(
        _sweep(tmp_path, compare_rc=compare_rc, compare343_rc=compare343_rc)
        + f"C={tmp_path}/c R={tmp_path}/r SEG=seg MAPS=maps RENDER=render WINNER={tmp_path}/winner\n"
        + _function("compare")
        + "compare"
    )
    assert run.returncode == rc
    calls = [
        line.split()[2] for line in (tmp_path / "pyw.log").read_text().splitlines()
    ]
    assert calls == ["compare", "compare343"]
    first = (tmp_path / "pyw.log").read_text().splitlines()[0].split()
    assert (
        first[first.index("--sdt") + 1]
        == f"{tmp_path}/r/work/surf_sdt/a_surf_sdt.ome.zarr"
    )


def test_the_repeat_compares_studio_again_with_finding_124s_own_map(tmp_path):
    _inputs(tmp_path)
    np.save(tmp_path / "zero" / "e2e" / "w035.npy", np.zeros((2, 3), np.float32))
    again = np.zeros((2, 3), np.float32)
    again[1, 2] = 0.25
    np.save(tmp_path / "again.npy", again)
    _stub(
        tmp_path / "pyw",
        f'[ "$2" = -c ] && exec {sys.executable} "$@"\n: > "${{@: -1}}"\n',
    )
    _stub(tmp_path / "env" / "bin" / "python", f'cp {tmp_path}/again.npy "$5"\n')
    (tmp_path / "code").mkdir()
    (tmp_path / "out" / "planes").mkdir(
        parents=True
    )  # as the script makes it before its steps
    run = _bash(
        f"OUT={tmp_path}/out ENV={tmp_path}/env PYW={tmp_path}/pyw HERE={tmp_path}/here CODE={tmp_path}/code "
        "WEIGHTS=/w.safetensors\n"
        + ARRAYS.format(t=tmp_path)
        + _function("studio")
        + _function("repeat")
        + "repeat"
    )
    assert run.returncode == 0, run.stderr
    assert json.loads((tmp_path / "out" / "repeat.json").read_text()) == {"max_abs_difference": 0.25,
                                                                          "identical": False}  # fmt: skip


@pytest.mark.parametrize(
    ("csv", "peak"),
    [("t, 900 MiB, 50 %\nt, 12000 MiB, 99 %\nt, 3000 MiB, 10 %\n", 12000), ("", None)],
)
def test_the_gpu_peak_is_the_largest_sample(tmp_path, csv, peak):
    (tmp_path / "gpu.csv").write_text(csv)
    run = _bash(f"OUT={tmp_path}\n" + _block("peak=$(", '> "$OUT/gpu_peak.json"'))
    assert run.returncode == 0, run.stderr
    assert json.loads((tmp_path / "gpu_peak.json").read_text()) == {
        "gpu_peak_mib_all_processes": peak
    }


@pytest.mark.xfail(
    strict=True,
    reason="run_depth_sweep.sh has no EXIT trap: a failed step leaves its nvidia-smi sampler running "
    "(run_snap_passes.sh stops it with a trap). Registered script, not changed.",
)
def test_a_failed_step_stops_the_gpu_sampler(tmp_path):
    (tmp_path / "logs").mkdir()
    _stub(
        tmp_path / "bin" / "nvidia-smi",
        f"exec 2>/dev/null\necho $$ > {tmp_path}/sampler.pid\nexec sleep 30\n",
    )
    run = _bash(
        f"OUT={tmp_path}\ncontrol_gate() {{ :; }}\nsweep211() {{ return 3; }}\n"
        + _function("step")
        + _block("nvidia-smi --query-gpu", "step sweep211 sweep211"),
        path=tmp_path / "bin",
    )
    assert run.returncode == 3
    for _ in range(100):
        if (tmp_path / "sampler.pid").exists() and (
            tmp_path / "sampler.pid"
        ).read_text().strip():
            break
        time.sleep(0.05)
    pid = int((tmp_path / "sampler.pid").read_text())
    try:
        os.kill(pid, 0)
        running = True
    except ProcessLookupError:
        running = False
    finally:
        try:
            os.kill(pid, 9)
        except ProcessLookupError:
            pass
    assert not running
