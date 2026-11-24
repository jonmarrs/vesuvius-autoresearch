"""Finding 131: the denser snap's reading at the winning PHerc. 211 place. The verdict table, the arms, the script."""

import importlib.util
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "repro/first_letters/pherc0211_control"
REG = ROOT / "docs/preregistration/2026-11-20_first_letters_0211_dense_read.md"


def _load():
    spec = importlib.util.spec_from_file_location(
        "dense_read_under_test", CONTROL / "dense_read.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


dr = _load()


@pytest.mark.parametrize(
    ("f124", "rerun", "dense", "expected"),
    [
        (
            0.8247,
            0.8247,
            0.8447,
            "DENSE_READS_BETTER",
        ),  # +0.02 with no noise: the 0.02 floor
        (0.8247, 0.8247, 0.8446, "DENSE_READS_SAME"),
        (0.8247, 0.8247, 0.8047, "DENSE_READS_WORSE"),
        (0.8247, 0.8147, 0.8346, "DENSE_READS_SAME"),  # noise 0.01: the margin is 0.02
        (
            0.8247,
            0.8047,
            0.8446,
            "DENSE_READS_SAME",
        ),  # noise 0.02: the margin is 0.04, the change 0.0399
        (0.8247, 0.8047, 0.8448, "DENSE_READS_BETTER"),
        (
            0.8247,
            0.8447,
            0.8048,
            "DENSE_READS_SAME",
        ),  # noise +0.02 counts as much as -0.02
        (0.8247, 0.8447, 0.8047, "DENSE_READS_WORSE"),  # exactly at the margin counts
    ],
)
def test_the_verdict_table(f124, rerun, dense, expected):
    assert dr.verdict(f124, rerun, dense, 0.83, True) == expected


@pytest.mark.parametrize(
    ("share", "reproduces", "dense"),
    [(0.49, True, 0.9), (0.83, False, 0.9), (0.83, True, None), (None, True, 0.9)],
)
def test_it_does_not_run_without_half_the_mask_finding_124_again_or_every_r(
    share, reproduces, dense
):
    assert dr.verdict(0.8247, 0.8247, dense, share, reproduces) == "DOES_NOT_RUN"


def test_the_lines_are_the_registrations():
    assert (dr.LINE, dr.F124_R, dr.NEAR) == (0.02, 0.8247, 2.0)
    text = " ".join(REG.read_text().split())
    assert "the larger of 0.02 and 2 × |noise|" in text
    assert "does not give r 0.8247" in text
    for name in (
        "DENSE_READS_BETTER",
        "DENSE_READS_WORSE",
        "DENSE_READS_SAME",
        "DOES_NOT_RUN",
    ):
        assert f"`{name}`" in text


def test_the_arms_must_be_named_as_registered(tmp_path):
    base = ["compare", str(tmp_path / "o.json")]
    for flag in (
        "--winner-mesh",
        "--winner-maps",
        "--winner-render",
        "--studio",
        "--studio-mask",
        "--ours-render-map",
    ):
        base += [flag, str(tmp_path)]
    base += ["--windings", "w033"]
    arms = []
    for name in ("f124", "rerun", "other"):
        arms += ["--arm", name, str(tmp_path), str(tmp_path), str(tmp_path)]
    with pytest.raises(SystemExit):
        dr.main(base + arms)
    assert not (tmp_path / "o.json").exists()


def test_the_run_reads_both_arms_as_finding_124_did_and_uploads_nothing():
    path = CONTROL / "run_dense_read.sh"
    assert os.access(path, os.X_OK)
    text = path.read_text()
    for word in ("aws s3 cp", "gh release", "curl", "--upload-file", "rsync "):
        assert word not in text
    assert (
        "ARMS=(e2e_rerun e2e_dense2)" in text
        and "WINDINGS=(w033 w034 w035 w036)" in text
    )
    assert '"$BAND/densify_winding.py" "$base/$w" "$dest/$w" --factor 2' in text
    assert 'ln -sfn fit_full "$R/work/fit_e2e_rerun"' in text
    assert (
        "RENDER_SLICES" not in text
    )  # 66 layers: finding 124's validity mask reads all of them
    assert text.count("--stride 64 --blend hann") == 1 and "--batch-size 32" in text
    assert '"$HERE/end_to_end.py" orient' in text
    assert (
        '--arm f124 "$R/work/final_e2e" "$R/work/render_e2e" "$C/work/studio_e2e/maps"'
        in text
    )
    order = [text.index(f'step {s}') for s in ("check", "prepare", '"snap_', '"flatten_', '"orient_', '"render_',
                                                '"studio_', "compare")]  # fmt: skip
    assert order == sorted(order)
    shas = dict(re.findall(r"^(W_SHA|CODE_SHA)=(\w+)", text, flags=re.M))
    f124 = dict(
        re.findall(
            r"^(W_SHA|CODE_SHA)=(\w+)",
            (CONTROL / "run_studio_e2e.sh").read_text(),
            flags=re.M,
        )
    )
    assert shas == f124 and len(shas) == 2


# --- the comparison's own reckoning, with finding 110's surfaces stood in for; the sheet share; the command line ----

H, W = 24, 32  # the winner's lattice cells


def _compare(tmp_path, monkeypatch, cosines=None):
    """A Studio map, mask and our render's map on the winner's 96 x 128-pixel canvas, and three arms whose carried maps
    are the winner's plus noise. finding 110's side and transfer are stand-ins, so only the comparison's reckoning runs.
    Each arm lacks a different row of cells: f124 row 0 (no winding), rerun rows 1 (no winding) and 3 (no other side),
    dense2 row 2 (no map). The mask leaves out the first one and a half columns of cells, and our render's map row 5."""
    import argparse

    import cv2
    import tifffile

    rng = np.random.default_rng(5)
    px = rng.random((H * 4, W * 4))
    tifffile.imwrite(tmp_path / "studio.tif", px.astype(np.float32))
    mask = np.full(px.shape, 255, np.uint8)
    mask[:, :6] = 0
    cv2.imwrite(str(tmp_path / "mask.png"), mask)
    own = px.copy()
    own[20:24] = np.nan  # our render's map has no value on cell row 5
    np.save(tmp_path / "own.npy", own.astype(np.float32))
    studio = dr.analysis.block_mean(px)
    monkeypatch.setattr(
        dr.tm, "side", lambda *a, **k: {"ok": np.ones((H, W), bool), "points": None}
    )
    arms = {}
    for k, name in enumerate(("f124", "rerun", "dense2")):
        which = np.zeros((H, W), int)
        carried = studio + rng.normal(0, 0.05 * (k + 1), (H, W))
        other = rng.random((H, W))
        if name == "f124":
            which[0] = -1
        elif name == "rerun":
            which[1] = -1
            other[3] = np.nan
        else:
            carried[2] = np.nan
        dist = (
            np.repeat(np.arange(H, dtype=float)[:, None], W, axis=1) + k
        )  # each cell's row, plus the arm's index
        arms[name] = {"which": which, "dist": dist, "cosines": (cosines or {}).get(name, [-0.99]),
                      "carried": carried, "other": other, "meshes": [name]}  # fmt: skip
    monkeypatch.setattr(
        dr,
        "carry_arm",
        lambda winner, windings, finals, renders, maps: arms[finals.name],
    )
    arm = [[n, str(tmp_path / n), str(tmp_path / n), str(tmp_path / n)] for n in arms]
    args = argparse.Namespace(winner_mesh=tmp_path, winner_maps=tmp_path, winner_render=tmp_path,
                              studio=tmp_path / "studio.tif", studio_mask=tmp_path / "mask.png",
                              ours_render_map=tmp_path / "own.npy", windings=["w033"], sdt=None, arm=arm)  # fmt: skip
    return args


def test_the_arms_are_scored_on_the_cells_every_arm_reaches_and_f124_on_its_own(
    tmp_path, monkeypatch
):
    result = dr.compare_cmd(_compare(tmp_path, monkeypatch))
    # the mask's whole cells: columns 2 to 31; every arm, and our render's map, reach rows 4 and 6 to 23 of them;
    # the share is of the mask's cells
    assert (result["mask_cells"], result["cells"], result["cell_share"]) == (
        24 * 30,
        19 * 30,
        round(19 / 24, 4),
    )
    d = result["described"]
    assert {
        n: a["cells"] for n, a in d["each_arm_on_the_common_cells"].items()
    } == dict.fromkeys(("f124", "rerun", "dense2"), 570)
    assert {n: a["cells"] for n, a in d["each_arm_on_its_own_cells"].items()} == {
        "f124": 22 * 30, "rerun": 21 * 30, "dense2": 22 * 30,
    }  # fmt: skip
    # transfer distances over the common cells only: rows 4 and 6 to 23, plus the arm's index
    assert d["transfer_distance_voxels"]["dense2"] == {"p50": 16.0, "p95": 25.0}
    assert d["final_nodes_within_2_of_the_predicted_sheet"] == dict.fromkeys(
        ("f124", "rerun", "dense2")
    )
    reg = result["registered"]
    assert reg["noise_rerun_minus_f124"] == round(
        reg["r"]["rerun"] - reg["r"]["f124"], 4
    )
    assert reg["change_dense2_minus_rerun"] == round(
        reg["r"]["dense2"] - reg["r"]["rerun"], 4
    )
    # finding 124's r is not given again on its own cells here, so the comparison does not run
    assert (
        result["f124_reproduced_on_its_own_cells"] is False
        and result["verdict"] == "DOES_NOT_RUN"
    )


def test_the_comparison_runs_once_finding_124s_r_is_given_again_on_its_own_cells(
    tmp_path, monkeypatch
):
    (tmp_path / "a").mkdir()
    first = dr.compare_cmd(_compare(tmp_path / "a", monkeypatch))
    own_r = first["described"]["each_arm_on_its_own_cells"]["f124"]["r"]
    assert (
        own_r != first["registered"]["r"]["f124"]
    )  # its own cells are not the common ones
    monkeypatch.setattr(dr, "F124_R", own_r)
    (tmp_path / "b").mkdir()
    again = dr.compare_cmd(_compare(tmp_path / "b", monkeypatch))
    r = again["registered"]["r"]
    assert again["f124_reproduced_on_its_own_cells"] is True
    assert again["verdict"] == dr.verdict(
        r["f124"], r["rerun"], r["dense2"], again["cell_share"], True
    )


@pytest.mark.parametrize(
    ("cosines", "stops"),
    [({"dense2": [-0.99, 0.0]}, True), ({"f124": [None, -0.99]}, False)],
    ids=["a-zero-cosine-stops", "a-winding-without-a-cosine-does-not"],
)
def test_a_render_that_samples_against_the_winners_normals_stops_the_comparison(
    tmp_path, monkeypatch, cosines, stops
):
    result = dr.compare_cmd(_compare(tmp_path, monkeypatch, cosines))
    assert (
        result.get("why") == "a render samples against the winner's normals"
    ) is stops
    assert ("cells" in result) is not stops


def test_an_unreadable_mask_stops_the_comparison(tmp_path, monkeypatch):
    args = _compare(tmp_path, monkeypatch)
    args.studio_mask.write_text("not an image")
    with pytest.raises(SystemExit, match="cannot read"):
        dr.compare_cmd(args)


def test_the_verdict_runs_at_exactly_half_the_mask():
    assert dr.verdict(0.8247, 0.8247, 0.8447, 0.5, True) == "DENSE_READS_BETTER"


def test_the_sheet_share_counts_nodes_within_2_voxels_of_the_field_it_has(
    tmp_path, monkeypatch
):
    import band_fit_quality
    import tifffile

    class _Field:
        def __init__(self, distances):
            self.distances = np.asarray(distances, float)

        def at(self, xyz):
            return self.distances[: len(xyz)]

    finals = tmp_path / "finals"
    (finals / "w033.tifxyz").mkdir(parents=True)
    for c in "xyz":
        tifffile.imwrite(
            finals / "w033.tifxyz" / f"{c}.tif", np.full((1, 4), 100.0, np.float32)
        )
    assert dr.sheet_share(None, finals, ["w033"]) is None
    monkeypatch.setattr(
        band_fit_quality,
        "DistanceField",
        lambda store, group: _Field([2.0, 2.0, 3.0, np.nan]),
    )
    assert dr.sheet_share(tmp_path / "sdt", finals, ["w033"]) == {
        "w033": 0.6667
    }  # exactly 2 voxels counts
    monkeypatch.setattr(
        band_fit_quality, "DistanceField", lambda store, group: _Field([np.nan] * 4)
    )
    assert dr.sheet_share(tmp_path / "sdt", finals, ["w033"]) == {"w033": None}


@pytest.mark.parametrize(
    ("verdict", "code"), [("DENSE_READS_SAME", 0), ("DOES_NOT_RUN", 1)]
)
def test_the_command_writes_its_record_once_and_exits_1_when_it_does_not_run(
    tmp_path, monkeypatch, verdict, code
):
    monkeypatch.setattr(
        dr,
        "compare_cmd",
        lambda args: {"finding": 131, "verdict": verdict, "described": {}},
    )
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
    for name in ("f124", "rerun", "dense2"):
        argv += ["--arm", name, str(tmp_path), str(tmp_path), str(tmp_path)]
    assert dr.main(argv) == code
    assert json.loads((tmp_path / "o.json").read_text())["verdict"] == verdict
    assert dr.main(argv) == 2
