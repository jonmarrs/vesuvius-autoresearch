"""Finding 119's measurement: the verdict table, the snap list, the band cut, and the choice on known sheets."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load():
    path = ROOT / "repro/first_letters/pherc0211_control/winner_sheet.py"
    spec = importlib.util.spec_from_file_location("winner_sheet_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ws = _load()


def _score(share, median):
    return {"median": median, "fraction_within": {"2": share}}


def test_the_verdict_table():
    assert ws.verdict(None) == "DOES_NOT_RUN"
    assert ws.verdict(_score(0.0, None)) == "DOES_NOT_RUN"
    assert ws.verdict(_score(0.50, 3.0)) == "ON_THE_WINNERS_SHEET"
    assert (
        ws.verdict(_score(0.80, 3.1)) == "PARTLY_ON_IT"
    )  # the median line is part of ON
    assert ws.verdict(_score(0.49, 1.0)) == "PARTLY_ON_IT"
    assert ws.verdict(_score(0.25, 9.0)) == "PARTLY_ON_IT"
    assert ws.verdict(_score(0.249, 9.0)) == "OFF_IT"


def test_the_lines_are_finding_110s():
    assert (ws.ON_SHARE, ws.ON_MEDIAN, ws.WITHIN) == (0.5, 3.0, "2")
    assert (ws.Z_BEGIN, ws.Z_END) == (7650, 9150)


def test_the_snap_list_is_the_chosen_winding_and_its_neighbours_that_exist():
    names = ["w010", "w011", "w012", "w030"]
    assert ws.neighbours("w011", names) == ["w010", "w011", "w012"]
    assert ws.neighbours("w010", names) == ["w010", "w011"]
    assert ws.neighbours("w030", names) == ["w030"]
    with pytest.raises(ValueError):
        ws.neighbours("final", names)


def test_only_the_winners_nodes_inside_the_band_are_measured():
    xyz = np.zeros((3, 1, 3))
    xyz[:, 0, 2] = [7649.9, 8000, 9150]
    valid = np.ones((3, 1), bool)
    assert ws.in_band(xyz, valid)[:, 0].tolist() == [False, True, True]


def _write_tifxyz(path: Path, xyz: np.ndarray) -> None:
    import tifffile

    path.mkdir(parents=True)
    for k, c in enumerate("xyz"):
        tifffile.imwrite(path / f"{c}.tif", xyz[..., k].astype(np.float32))


def _plane(y: float, rows=20, cols=30, z0=8000.0, step=20.0) -> np.ndarray:
    r, c = np.mgrid[0:rows, 0:cols].astype(float)
    return np.stack([2000 + c * step, np.full_like(r, y), z0 + r * step], -1)


def test_the_choice_is_the_winding_on_the_winners_sheet_and_the_verdict_reads_its_snapped_copy(
    tmp_path,
):
    winner = tmp_path / "winner"
    _write_tifxyz(winner, _plane(3000.0))
    fit = tmp_path / "fit"
    for name, y in (("w030", 2988.0), ("w031", 3000.6), ("w032", 3013.0)):
        _write_tifxyz(fit / name, _plane(y, rows=24, cols=34, z0=7960.0))
    chosen = tmp_path / "chosen.json"
    snap_list = tmp_path / "snap.txt"
    assert ws.main(["choose", str(chosen), str(winner), str(fit), str(snap_list)]) == 0
    record = json.loads(chosen.read_text())
    assert record["chosen"] == "w031"
    assert record["chosen_raw"]["fraction_within"]["2"] == 1.0
    assert snap_list.read_text().split() == ["w030", "w031", "w032"]
    assert record["described"]["near_any"]["within_2_of_any_winding"] == 1.0
    # the snap moved the chosen winding onto the neighbouring sheet: the verdict reads the snapped copy
    snap = tmp_path / "snap"
    _write_tifxyz(snap / "w031", _plane(3012.5, rows=24, cols=34, z0=7960.0))
    _write_tifxyz(snap / "w030", _plane(2988.0, rows=24, cols=34, z0=7960.0))
    out = tmp_path / "verdict.json"
    assert ws.main(["verdict", str(out), str(winner), str(chosen), str(snap)]) == 0
    result = json.loads(out.read_text())
    assert result["verdict"] == "OFF_IT"
    assert set(result["snapped_neighbours"]) == {"w030"}
    assert ws.main(["verdict", str(out), str(winner), str(chosen), str(snap)]) == 2


def test_spliced_twins_are_not_raw_windings_and_are_never_chosen(tmp_path):
    """villa writes a wNNN_spliced twin beside each winding. The dry run on the smoke fit counted 240 windings
    (120 and their twins); finding 110's run_select.sh skipped the twins, and so does this."""
    winner = tmp_path / "winner"
    _write_tifxyz(winner, _plane(3000.0))
    fit = tmp_path / "fit"
    for name, y in (
        ("w030", 2988.0),
        ("w031", 3000.6),
        ("w031_spliced", 3000.0),  # nearer than any raw winding
        ("w032", 3013.0),
    ):
        _write_tifxyz(fit / name, _plane(y, rows=24, cols=34, z0=7960.0))
    (fit / "w033").mkdir()  # a folder with no surface in it
    chosen = tmp_path / "chosen.json"
    snap_list = tmp_path / "snap.txt"
    assert ws.main(["choose", str(chosen), str(winner), str(fit), str(snap_list)]) == 0
    record = json.loads(chosen.read_text())
    assert record["windings"] == 3
    assert record["chosen"] == "w031"
    assert snap_list.read_text().split() == ["w030", "w031", "w032"]
    assert ws.raw_windings(fit) == ["w030", "w031", "w032"]


def test_the_chain_after_the_fit_runs_the_registered_steps_in_order_and_uploads_nothing():
    import os

    path = ROOT / "repro/first_letters/pherc0211_control/run_after_fit.sh"
    assert os.access(path, os.X_OK)
    text = path.read_text()
    order = [
        'run_quality.sh" full',
        'winner_sheet.py" choose',
        'run_snap.sh" full',
        'winner_sheet.py" verdict',
    ]
    places = [text.index(step) for step in order]
    assert places == sorted(places)
    # the snap reads the list that choose writes, and verdict reads choose's record and the snap's folder
    assert '"$R/work/windings_full.txt" --sdt "$SDT"' in text
    assert '"$R/work/winner_choose.json" "$R/work/snap_full"' in text
    assert '[ "$rc" -eq 0 ] || exit' in text
    # the winner's tifxyz is LZW-compressed: villa's environment cannot read it, this repository's can
    assert '"$PYW" -I "$HERE/winner_sheet.py" choose' in text
    assert '"$PYW" -I "$HERE/winner_sheet.py" verdict' in text
    assert '"$PY" -I "$HERE/winner_sheet.py"' not in text
    for word in ("aws s3 cp", "gh release", "curl -T", "--upload-file", "rsync "):
        assert word not in text


def test_a_winding_that_covers_too_little_of_the_winners_surface_is_not_chosen(
    tmp_path,
):
    winner = tmp_path / "winner"
    _write_tifxyz(winner, _plane(3000.0))
    fit = tmp_path / "fit"
    _write_tifxyz(
        fit / "w030", _plane(3000.0, rows=5, cols=30)
    )  # a quarter of its rows
    chosen = tmp_path / "chosen.json"
    assert (
        ws.main(["choose", str(chosen), str(winner), str(fit), str(tmp_path / "s.txt")])
        == 0
    )
    record = json.loads(chosen.read_text())
    assert record["chosen"] is None
    out = tmp_path / "verdict.json"
    assert (
        ws.main(["verdict", str(out), str(winner), str(chosen), str(tmp_path / "snap")])
        == 0
    )
    assert json.loads(out.read_text())["verdict"] == "DOES_NOT_RUN"
