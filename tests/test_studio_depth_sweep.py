"""Finding 135's analysis: shifted planes, the chosen shift, and the registered verdict with its failure branches."""

import importlib.util
import json
import sys
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
