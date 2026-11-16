"""Finding 112's instrument: the sheet-following score, and the registration's constants."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "repro/first_letters/eligible_band"
REGISTRATION = (
    ROOT / "docs/preregistration/2026-11-13_first_letters_0211_band_fit.md"
).read_text()


def _load():
    spec = importlib.util.spec_from_file_location(
        "band_fit_quality_under_test", HERE / "band_fit_quality.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bq = _load()


class Sheets:
    """Flat sheets 2 voxels thick every 16 voxels in z; distance is positive outside them."""

    def at(self, xyz):
        z = xyz[:, 2]
        return np.abs((z + 8) % 16 - 8) - 1.0


def _plane(z, tilt=0.0, shape=(60, 60)):
    rows, cols = np.indices(shape).astype(float)
    xyz = np.stack([cols * 5, rows * 5, z + tilt * cols * 5], -1)
    return xyz, np.ones(shape, bool)


def test_a_winding_on_a_sheet_beats_its_displaced_copies_and_one_between_sheets_does_not():
    on = bq.score(Sheets(), *_plane(160.0))
    assert on["on_sheet"] == 1.0 and on["displaced"] == 0.0 and on["excess"] == 1.0
    between = bq.score(Sheets(), *_plane(168.0))
    assert between["on_sheet"] == 0.0 and between["excess"] <= 0.0


def test_a_winding_that_cuts_across_sheets_scores_near_zero():
    across = bq.score(Sheets(), *_plane(160.0, tilt=0.37))
    assert abs(across["excess"]) < 0.05


def test_a_winding_with_too_few_nodes_in_the_field_is_not_scored():
    class Empty:
        def at(self, xyz):
            return np.full(len(xyz), np.nan)

    assert bq.score(Empty(), *_plane(160.0)) is None
    assert bq.score(Sheets(), *_plane(160.0, shape=(20, 20))) is None


def test_the_summary_counts_unscored_windings_and_takes_the_median():
    windings = {
        "w010": {"excess": 0.2, "on_sheet": 0.4},
        "w011": {"excess": -0.1, "on_sheet": 0.2},
        "w012": {"excess": 0.1, "on_sheet": 0.3},
        "w013": None,
    }
    summary = bq.summarise(windings)
    assert summary["windings"] == 4 and summary["windings_scored"] == 3
    assert summary["excess_median"] == 0.1
    assert summary["share_of_windings_with_positive_excess"] == round(2 / 3, 4)
    assert bq.summarise({"w010": None}) == {"windings": 1, "windings_scored": 0}


def test_the_registration_states_what_the_scripts_do():
    env = (HERE / "env.sh").read_text()
    assert "PHerc0211) VOLUME_ID=20250821151803" in env and "SENSE=ACW ;;" in env
    assert "Z_BEGIN=${FL_Z_BEGIN:-10250}" in env and "Z_END=${FL_Z_END:-11750}" in env
    assert "z 10250 to 11750" in REGISTRATION
    assert f"moved {bq.DISPLACE:.0f} voxels" in REGISTRATION
    fit = (HERE / "run_fit.sh").read_text()
    assert "STEPS=30000" in fit and "30,000 steps" in REGISTRATION
    assert "exists: an arm is run once" in fit
    assert "exists: this is measured once" in (HERE / "band_fit_quality.py").read_text()
    for verdict in (
        "DOES_NOT_RUN",
        "INSTRUMENT_FAILS",
        "ON_SHEETS",
        "PARTLY_ON_SHEETS",
        "NOT_ON_SHEETS",
    ):
        assert f"`{verdict}`" in REGISTRATION


def test_nothing_in_the_band_scripts_uploads():
    for script in list(HERE.glob("*.sh")) + list((HERE / "setup").glob("*.sh")):
        text = script.read_text()
        for word in ("aws s3 cp", "gh release", "curl -T", "--upload-file", "rsync "):
            assert word not in text, (script.name, word)


def _load_verdict():
    spec = importlib.util.spec_from_file_location(
        "band_fit_verdict_under_test", HERE / "band_fit_verdict.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bv = _load_verdict()
OK = {"a": {"exit": 0}, "b": {"exit": 0}}


def _summary(median, positive, scored=120):
    return {
        "excess_median": median,
        "share_of_windings_with_positive_excess": positive,
        "windings_scored": scored,
    }


def test_the_verdict_table_is_the_registered_one():
    floor = _summary(0.0, 0.5)
    assert bv.verdict(OK, floor, _summary(0.07, 0.80)) == "ON_SHEETS"
    assert bv.verdict(OK, floor, _summary(0.069, 0.99)) == "PARTLY_ON_SHEETS"
    assert bv.verdict(OK, floor, _summary(0.20, 0.79)) == "PARTLY_ON_SHEETS"
    assert bv.verdict(OK, floor, _summary(0.03, 0.65)) == "PARTLY_ON_SHEETS"
    assert bv.verdict(OK, floor, _summary(0.029, 0.99)) == "NOT_ON_SHEETS"
    assert bv.verdict(OK, floor, _summary(0.20, 0.64)) == "NOT_ON_SHEETS"
    assert (
        bv.verdict(OK, _summary(0.031, 0.5), _summary(0.2, 0.9)) == "INSTRUMENT_FAILS"
    )
    assert bv.verdict(OK, floor, _summary(0.2, 0.9, scored=59)) == "DOES_NOT_RUN"
    assert bv.verdict({"a": {"exit": 1}}, floor, _summary(0.2, 0.9)) == "DOES_NOT_RUN"
    assert bv.verdict({"a": None}, floor, _summary(0.2, 0.9)) == "DOES_NOT_RUN"
    assert bv.verdict(OK, floor, None) == "DOES_NOT_RUN"


def test_the_verdict_constants_are_the_registrations():
    assert "median excess of at least 0.07" in REGISTRATION and bv.P1["median"] == 0.07
    assert "at least 80% of windings" in REGISTRATION and bv.P1["positive"] == 0.80
    assert "median excess of at least 0.03" in REGISTRATION and bv.P2["median"] == 0.03
    assert "at least 65% of windings" in REGISTRATION and bv.P2["positive"] == 0.65
    assert "is above 0.03" in REGISTRATION and bv.FLOOR_MAX == 0.03
    assert "fewer than 60 windings" in REGISTRATION and bv.MIN_WINDINGS == 60


def test_the_by_index_summary_cuts_scored_windings_into_equal_parts_and_names_none():
    windings = {
        f"w{i:03d}": {
            "excess": 0.1 if i < 14 else -0.1,
            "on_sheet": 0.3,
            "nodes_scored": 2000 + i,
        }
        for i in range(10, 22)
    }
    windings["w022"] = None
    parts = bv.by_index({"windings": windings})
    assert [(p["first"], p["last"], p["windings"]) for p in parts] == [
        (10, 13, 4),
        (14, 17, 4),
        (18, 21, 4),
    ]
    assert [p["positive"] for p in parts] == [1.0, 0.0, 0.0]
    assert parts[0]["at_least_p1_median"] == 4 and parts[0]["excess_median"] == 0.1
    assert not any(key.startswith("w0") for part in parts for key in part)


def _load_spacing():
    spec = importlib.util.spec_from_file_location(
        "band_fit_spacing_under_test", HERE / "band_fit_spacing.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bs = _load_spacing()


def test_sheet_spacing_is_where_the_profile_rises_again_and_none_when_it_does_not():
    offsets = list(bs.OFFSETS)
    # finding 112's profile of the PHerc. 0211 fit: peak at 0, neighbours near 14
    share = [0.189, 0.1887, 0.1904, 0.195, 0.2006, 0.2061, 0.2036, 0.1928, 0.1796, 0.169, 0.1731, 0.2199,
             0.2674, 0.2278, 0.1785, 0.1736, 0.1829, 0.1975, 0.2104, 0.2154, 0.2122, 0.2077, 0.2056, 0.2057,
             0.2069]  # fmt: skip
    assert bs.sheet_spacing(offsets, share) == 14.0
    summary = bs.summarise(offsets, share, [9.0, 9.5, 10.0])
    assert summary["peak_offset"] == 0 and summary["ratio"] == round(9.5 / 14.0, 3)
    falling = [0.3 - 0.004 * abs(o) for o in offsets]
    assert bs.sheet_spacing(offsets, falling) is None
    assert bs.summarise(offsets, falling, [9.0])["ratio"] is None


def test_the_verdict_reads_the_arms_it_is_given(tmp_path):
    import json

    work = tmp_path / "work"
    for arm, name in (
        ("setup", "distance_field"),
        ("outer80-smoke", "fit"),
        ("outer80", "fit"),
    ):
        (work / f"gate_{arm}").mkdir(parents=True)
        (work / f"gate_{arm}" / f"{name}.json").write_text('{"exit": 0, "seconds": 1}')
    for arm, excess in (("outer80-smoke", 0.0), ("outer80", 0.1)):
        windings = {
            f"w{i:03d}": {"excess": excess, "on_sheet": 0.3, "nodes_scored": 2000}
            for i in range(10, 80)
        }
        summary = {
            "windings": 70,
            "windings_scored": 70,
            "excess_median": excess,
            "share_of_windings_with_positive_excess": float(excess > 0),
        }
        (work / f"quality_{arm}.json").write_text(
            json.dumps({"summary": summary, "windings": windings})
        )
    out = tmp_path / "verdict.json"
    assert bv.main([str(tmp_path), str(out), "outer80-smoke", "outer80"]) == 0
    record = json.loads(out.read_text())
    assert record["verdict"] == "ON_SHEETS" and set(record["steps"]) == {
        "setup/distance_field",
        "outer80-smoke/fit",
        "outer80/fit",
    }
    assert bv.main([str(tmp_path), str(tmp_path / "other.json")]) == 0
    assert (
        json.loads((tmp_path / "other.json").read_text())["verdict"] == "DOES_NOT_RUN"
    )


def test_the_fit_launcher_sets_both_winding_settings_for_an_outer_arm():
    text = (HERE / "run_fit.sh").read_text()
    assert 'overrides["shell_outer_winding_idx"] = int(sys.argv[4])' in text
    assert 'overrides["model_gap_expander_num_windings"] = int(sys.argv[4]) + 3' in text
    assert "outer[1-9]*-smoke) KIND=smoke" in text and "outer[1-9]*) KIND=full" in text


# Added by the design review of 2026-11-16: guards of the two scripts that the tests above do not reach.


def _field(tmp_path, group="1"):
    """A distance field as the score reads it: cell (z, y, x) holds 1 + 100 z + 10 y + x, and one cell holds no value."""
    import zarr

    z, y, x = np.indices((6, 8, 10))
    values = (1 + 100 * z + 10 * y + x).astype(np.uint16)
    values[1, 1, 1] = bq.NODATA
    store = tmp_path / f"sdt_{group}.zarr"
    root = zarr.open_group(str(store), mode="w")
    root.attrs.update(
        {"offset": 100.0, "unit_working_voxels": 0.5, "scale_vs_working": 4.0}
    )
    root.create_dataset(group, data=values, chunks=(4, 4, 4))
    return bq.DistanceField(store, group)


def test_the_distance_field_is_read_at_x_y_z_points_in_working_voxels(tmp_path):
    field = _field(tmp_path)
    points = np.array(
        [
            [28.0, 12.0, 8.0],  # cell z 2, y 3, x 7: (238 - 100) * 0.5
            [30.4, 12.0, 8.0],  # the nearest cell is x 8
            [4.0, 4.0, 4.0],  # the cell without a value
            [40.0, 12.0, 8.0],  # one cell past the far x face
            [-4.0, 12.0, 8.0],  # one cell before the near x face
            [0.0, 0.0, 0.0],
        ]
    )
    assert field.at(points).tolist() == pytest.approx(
        [69.0, 69.5, np.nan, np.nan, np.nan, -49.5], nan_ok=True
    )
    assert np.isnan(field.at(points[3:5])).all()


def test_a_coarser_group_of_the_distance_field_has_cells_twice_the_size(tmp_path):
    field = _field(tmp_path, group="2")
    assert field.at(np.array([[56.0, 24.0, 16.0]])).tolist() == [69.0]


def test_a_winding_is_scored_from_a_thousand_nodes():
    assert bq.score(Sheets(), *_plane(160.0, shape=(22, 52)))["nodes_scored"] == 1000
    assert bq.score(Sheets(), *_plane(160.0, shape=(22, 51))) is None


def test_a_node_on_the_face_of_a_sheet_is_inside_it():
    # one voxel off a sheet's middle the distance is exactly zero
    on_face = bq.score(Sheets(), *_plane(161.0))
    assert on_face["on_sheet"] == 1.0 and on_face["displaced"] == 0.0
    # six voxels above the face only the copy moved back down reaches it
    above = bq.score(Sheets(), *_plane(167.0))
    assert (above["on_sheet"], above["displaced"], above["excess"]) == (0.0, 0.5, -0.5)
    assert bq.score(Sheets(), *_plane(160.5))["abs_distance_median"] == 0.5


class Gap(Sheets):
    """The sheets, with no value where `hole(points)` says so."""

    def __init__(self, hole):
        self.hole = hole

    def at(self, xyz):
        out = super().at(xyz)
        out[self.hole(xyz)] = np.nan
        return out


@pytest.mark.parametrize(
    "hole",
    [
        lambda p: (p[:, 0] >= 150) & (p[:, 2] > 163),  # the copies moved up
        lambda p: (p[:, 0] >= 150) & (p[:, 2] < 157),  # the copies moved down
        lambda p: (p[:, 0] >= 150) & (np.abs(p[:, 2] - 160) < 3),  # the nodes
    ],
)
def test_a_node_is_scored_only_where_it_and_both_copies_have_a_value(hole):
    result = bq.score(Gap(hole), *_plane(160.0))
    assert (result["nodes"], result["nodes_scored"]) == (58 * 58, 58 * 29)
    assert result["on_sheet"] == 1.0 and result["displaced"] == 0.0


def test_an_invalid_node_is_not_scored():
    xyz, valid = _plane(160.0, shape=(90, 90))
    valid[1::3, 1::3] = False
    xyz[~valid, 2] = 168.0  # between two sheets
    whole = (
        valid[1:-1, 1:-1]
        & valid[1:-1, :-2]
        & valid[1:-1, 2:]
        & valid[:-2, 1:-1]
        & valid[2:, 1:-1]
    )
    result = bq.score(Sheets(), xyz, valid)
    assert result["nodes"] == int(whole.sum()) > bq.MIN_NODES
    assert result["on_sheet"] == 1.0


def test_the_summary_gives_both_percentiles_and_does_not_count_zero_as_positive():
    windings = {
        f"w{i:03d}": {"excess": i / 10, "on_sheet": (i / 10) ** 2} for i in range(11)
    }
    summary = bq.summarise(windings)
    assert summary["excess_p10"] == 0.1 and summary["excess_p90"] == 0.9
    assert summary["excess_median"] == 0.5 and summary["on_sheet_median"] == 0.25
    assert summary["share_of_windings_with_positive_excess"] == round(10 / 11, 4)


def test_the_score_command_reads_raw_windings_once(tmp_path, monkeypatch, capsys):
    planes = {"w010": 160.0, "w011": 168.0, "w012_spliced": 160.0, "w013": 160.0}
    meshes = tmp_path / "meshes"
    for name in [*planes, "x999"]:
        (meshes / name).mkdir(parents=True)
        if name != "w013":  # a folder that holds no mesh
            (meshes / name / "x.tif").write_bytes(b"")
    opened = []

    class Field(Sheets):
        def __init__(self, store, group):
            opened.append((str(store), group))

    monkeypatch.setattr(bq, "DistanceField", Field)
    monkeypatch.setattr(
        bq.analysis, "load_tifxyz", lambda folder: _plane(planes[Path(folder).name])
    )
    out = tmp_path / "quality.json"
    assert bq.main([str(out), "sdt.zarr", str(meshes)]) == 0
    result = json.loads(out.read_text())
    assert opened == [("sdt.zarr", "1")]
    assert list(result["windings"]) == ["w010", "w011"]
    assert result["summary"] == bq.summarise(result["windings"])
    assert result["summary"]["windings_scored"] == 2
    assert result["displace_voxels"] == 6.0

    before = out.read_text()
    assert bq.main([str(out), "sdt.zarr", str(meshes)]) == 2
    assert "measured once" in capsys.readouterr().err
    assert out.read_text() == before and len(opened) == 1


def test_the_table_rows_apply_in_the_registered_order_and_at_their_bounds():
    floor, good = _summary(0.0, 0.5), _summary(0.2, 0.9)
    one_failed = {"a": {"exit": 0}, "b": {"exit": 1}, "c": {"exit": 0}}
    assert bv.verdict(one_failed, floor, good) == "DOES_NOT_RUN"
    assert bv.verdict(OK, None, good) == "DOES_NOT_RUN"
    # sixty scored windings are enough, in the smoke fit and in the full fit
    sixty = _summary(0.0, 0.5, scored=60), _summary(0.2, 0.9, scored=60)
    assert bv.verdict(OK, *sixty) == "ON_SHEETS"
    assert bv.verdict(OK, _summary(0.0, 0.5, scored=59), good) == "DOES_NOT_RUN"
    # the floor fails above 0.03, not at it
    assert bv.verdict(OK, _summary(0.03, 0.5), good) == "ON_SHEETS"
    # a run that did not run is not an instrument failure
    high_floor = _summary(0.5, 0.5)
    assert bv.verdict(one_failed, high_floor, good) == "DOES_NOT_RUN"
    assert bv.verdict(OK, _summary(0.5, 0.5, scored=59), good) == "DOES_NOT_RUN"
    assert bv.verdict(OK, high_floor, _summary(0.2, 0.9, scored=59)) == "DOES_NOT_RUN"


def test_the_by_index_summary_rounds_part_sizes_up_and_counts_at_the_lines():
    excess = [0.07, 0.0, -0.02, 0.3, 0.07, 0.01, 0.2, 0.069, 0.5, 0.1]
    windings = {
        f"w{10 + i:03d}": {
            "excess": value,
            "on_sheet": 0.1 * (i + 1),
            "nodes_scored": 1000 + i,
        }
        for i, value in enumerate(excess)
    }
    thirds = bv.by_index({"windings": windings})
    assert [(p["first"], p["last"], p["windings"]) for p in thirds] == [
        (10, 13, 4),
        (14, 17, 4),
        (18, 19, 2),
    ]
    # 0.07 is on the P1 line and counts; a winding at exactly zero is not positive
    assert (thirds[0]["positive"], thirds[0]["at_least_p1_median"]) == (0.5, 2)
    assert thirds[0]["excess_median"] == 0.035
    halves = bv.by_index({"windings": windings}, parts=2)
    assert [p["windings"] for p in halves] == [5, 5]
    assert halves[0]["excess_median"] == 0.07 and halves[0]["on_sheet_median"] == 0.3
    assert halves[0]["nodes_scored_median"] == 1002


GATES = {"setup/distance_field": 0, "smoke/fit": 0, "full/fit": 0}


def _quality(median, positive, scored=120):
    """A score file whose every winding has the same excess."""
    winding = {"excess": median, "on_sheet": 0.3, "nodes_scored": 2000}
    return {
        "summary": {**_summary(median, positive, scored), "windings": scored},
        "windings": {f"w{10 + i:03d}": winding for i in range(scored)},
    }


def _judge(run, smoke, full, gates=GATES):
    """The verdict command on a run directory; a gate or an arm given as None has no file."""
    for step, code in gates.items():
        arm, name = step.split("/")
        (run / "work" / f"gate_{arm}").mkdir(parents=True, exist_ok=True)
        if code is not None:
            record = json.dumps({"exit": code})
            (run / "work" / f"gate_{arm}" / f"{name}.json").write_text(record)
    for arm, quality in (("smoke", smoke), ("full", full)):
        if quality is not None:
            (run / "work" / f"quality_{arm}.json").write_text(json.dumps(quality))
    out = run / "verdict.json"
    assert bv.main([str(run), str(out)]) == 0
    return json.loads(out.read_text())


def test_the_verdict_command_reads_the_three_gates_and_both_arms(tmp_path):
    record = _judge(tmp_path, _quality(0.0, 0.5), _quality(0.05, 0.9))
    assert record["verdict"] == "PARTLY_ON_SHEETS"
    assert (record["p1"], record["p2"]) == (False, True)
    assert record["steps"] == {step: {"exit": 0} for step in GATES}
    assert record["smoke"]["excess_median"] == 0.0
    assert record["full"]["excess_median"] == 0.05
    assert [part["windings"] for part in record["full_by_index"]] == [40, 40, 40]


@pytest.mark.parametrize("step", sorted(GATES))
@pytest.mark.parametrize("code", [None, 1])
def test_the_verdict_command_does_not_run_on_a_missing_or_failed_gate(
    tmp_path, step, code
):
    gates = {**GATES, step: code}
    record = _judge(tmp_path, _quality(0.0, 0.5), _quality(0.2, 0.9), gates)
    assert record["verdict"] == "DOES_NOT_RUN"
    assert record["steps"][step] == (None if code is None else {"exit": 1})
    # the reading is still recorded
    assert (record["p1"], record["p2"]) == (True, True)


def test_the_verdict_command_does_not_run_without_the_full_arm(tmp_path):
    record = _judge(tmp_path, _quality(0.0, 0.5), None)
    assert record["verdict"] == "DOES_NOT_RUN"
    assert record["full"] is None and record["full_by_index"] is None
    assert (record["p1"], record["p2"]) == (False, False)


def test_the_fit_launcher_flips_only_the_direction_for_an_otherhand_arm():
    text = (HERE / "run_fit.sh").read_text()
    lines = text.splitlines()
    first = next(
        i
        for i, line in enumerate(lines)
        if "-otherhand-smoke) KIND=smoke; FLIP=1" in line
    )
    plain = next(
        i for i, line in enumerate(lines) if "outer[1-9]*-smoke) KIND=smoke" in line
    )
    assert first < plain, (
        "the otherhand patterns must be tried before the plain outer ones"
    )
    assert 'case "$SENSE" in ACW) SENSE=CW ;; CW) SENSE=ACW ;;' in text
    assert 'spec["spiral_outward_sense"] = sys.argv[3]' in text
    assert 'fit_spiral.py --dataset "$DATASET" --cache' in text
    assert 'ln -s "$R/dataset/tracks" "$DATASET/tracks"' in text


# Added by the design review of 2026-11-16: guards of the spacing description that the tests above do not reach.


def _profile(values, default):
    """A share at each of the spacing script's offsets: `values[o]` where given, else `default`."""
    return [values.get(o, default) for o in bs.OFFSETS]


def _symmetric(values):
    return {**values, **{-o: v for o, v in values.items()}}


@pytest.mark.parametrize(
    ("values", "default", "expected"),
    [
        # the neighbouring sheet can be at exactly 8, and 6 is still the winding's own sheet
        (_symmetric({0: 1.0, 2: 0.1, 4: 0.1, 6: 0.6, 8: 0.5}), 0.2, 8.0),
        # a dip at 8 is a candidate, not part of what the rise must clear
        (_symmetric({0: 1.0, 2: 0.3, 4: 0.3, 6: 0.3, 8: 0.1}), 0.25, None),
        # nor is a trough at 0
        (_symmetric({0: 0.05, 2: 0.3, 4: 0.3, 6: 0.3}), 0.25, None),
        # the two directions are averaged
        (
            {**_symmetric({0: 1.0, 2: 0.1, 4: 0.1, 6: 0.1}), -10: 0.5, 14: 0.5},
            0.2,
            12.0,
        ),
        # a tie goes to the nearer offset, on the negative side too
        (
            {
                **_symmetric({0: 1.0, 2: 0.1, 4: 0.1, 6: 0.1}),
                -16: 0.5,
                -10: 0.5,
                12: 0.5,
            },
            0.2,
            11.0,
        ),
        # a rise only as high as the dip before it is no rise
        (_symmetric({0: 1.0}), 0.2, None),
    ],
)
def test_sheet_spacing_takes_each_side_from_eight_voxels_out(values, default, expected):
    assert bs.sheet_spacing(list(bs.OFFSETS), _profile(values, default)) == expected


def test_sheet_spacing_needs_offsets_between_zero_and_eight():
    assert bs.sheet_spacing([-16, -8, 0, 8, 16], [0.5, 0.1, 1.0, 0.1, 0.5]) is None


def test_the_spacing_summary_names_its_percentiles_and_rounds_the_profile():
    falling = [0.3 - 0.004 * abs(o) for o in bs.OFFSETS]
    falling[0] = 0.123456
    summary = bs.summarise(list(bs.OFFSETS), falling, [*range(1, 11), 100.0])
    assert summary["share_inside"][0] == 0.1235
    assert summary["pairs"] == 11
    assert summary["winding_spacing_median"] == 6.0
    assert (summary["winding_spacing_p10"], summary["winding_spacing_p90"]) == (
        2.0,
        10.0,
    )


def _spacing_command(tmp_path, monkeypatch, windings, field):
    """The spacing command on stand-in windings; a winding given as None is a folder that holds no mesh."""
    meshes = tmp_path / "meshes"
    for name, nodes in windings.items():
        (meshes / name).mkdir(parents=True)
        if nodes is not None:
            (meshes / name / "x.tif").write_bytes(b"")
    opened = []

    def open_field(store, group):
        opened.append((str(store), group))
        return field

    monkeypatch.setattr(bs.quality, "DistanceField", open_field)
    monkeypatch.setattr(
        bs.analysis, "load_tifxyz", lambda folder: windings[Path(folder).name]
    )
    out = tmp_path / "spacing.json"
    return bs.main([str(out), "sdt.zarr", str(meshes)]), out, opened


def test_the_spacing_command_pools_raw_windings_and_measures_consecutive_ones(
    tmp_path, monkeypatch, capsys
):
    windings = {
        "w010": _plane(160.0),
        "w011": _plane(176.0),
        "w012_spliced": _plane(168.0),
        "w013": None,
        "w014": _plane(192.0),
    }
    code, out, opened = _spacing_command(tmp_path, monkeypatch, windings, Sheets())
    assert code == 0 and opened == [("sdt.zarr", "1")]
    result = json.loads(out.read_text())
    # every winding is on a sheet, and the sheets are 16 voxels apart
    assert result["share_inside"] == [1.0 if o % 16 == 0 else 0.0 for o in bs.OFFSETS]
    assert result["sheet_spacing"] == 16.0 and result["pairs"] == 2
    assert result["winding_spacing_median"] == 16.0 and result["ratio"] == 1.0

    before = out.read_text()
    assert bs.main([str(out), "sdt.zarr", str(tmp_path / "meshes")]) == 2
    assert "measured once" in capsys.readouterr().err
    assert out.read_text() == before and len(opened) == 1


class Recording:
    def __init__(self):
        self.asked = []

    def at(self, xyz):
        self.asked.append(xyz.copy())
        return np.zeros(len(xyz))


def test_the_profile_reads_every_fourth_node_with_a_normal_along_its_own_normal(
    tmp_path, monkeypatch
):
    rows, cols = np.indices((30, 40)).astype(float)
    x = 5 * cols
    curved = np.stack([x, 5 * rows, 160 + 0.01 * (x - 100) ** 2], -1)
    valid = np.ones(rows.shape, dtype=bool)
    valid[10, 10] = False
    curved[10, 10] = -1.0
    field = Recording()
    code, _, _ = _spacing_command(
        tmp_path, monkeypatch, {"w010": (curved, valid)}, field
    )
    assert code == 0
    normals, has_normal = bs.analysis.grid_normals(curved, valid)
    use = valid & has_normal
    points, n = curved[use][::4], normals[use][::4]
    assert len(field.asked) == len(bs.OFFSETS)
    for asked, offset in zip(field.asked, bs.OFFSETS, strict=True):
        assert np.array_equal(asked, points + offset * n)


class Halves:
    """Inside at and above z 160 where x < 150. Where x >= 150: outside, with no value 12 or more voxels below."""

    def at(self, xyz):
        x, z = xyz[:, 0], xyz[:, 2]
        out = np.where(x < 150, 160.0 - z, 5.0)
        out[(x >= 150) & (z <= 148)] = np.nan
        return out


def test_the_profile_counts_a_node_only_where_every_offset_has_a_value(
    tmp_path, monkeypatch
):
    code, out, _ = _spacing_command(
        tmp_path, monkeypatch, {"w010": _plane(160.0)}, Halves()
    )
    assert code == 0
    # the nodes at x 150 and beyond are left out; the rest are inside from offset 0 up, the face included
    share = json.loads(out.read_text())["share_inside"]
    assert share == [1.0 if o >= 0 else 0.0 for o in bs.OFFSETS]


def test_a_pair_of_windings_too_far_apart_sideways_has_no_spacing(
    tmp_path, monkeypatch
):
    far, valid = _plane(176.0)
    far[..., 0] += 5000.0
    windings = {"w010": _plane(160.0), "w011": (far, valid)}
    code, out, _ = _spacing_command(tmp_path, monkeypatch, windings, Sheets())
    result = json.loads(out.read_text())
    assert code == 0 and result["pairs"] == 0
    assert result["winding_spacing_median"] is None and result["ratio"] is None


class Nowhere:
    def at(self, xyz):
        return np.full(len(xyz), np.nan)


def test_the_spacing_command_writes_nothing_when_no_node_is_in_the_field(
    tmp_path, monkeypatch, capsys
):
    code, out, _ = _spacing_command(
        tmp_path, monkeypatch, {"w010": _plane(160.0)}, Nowhere()
    )
    assert code == 1 and not out.exists()
    assert "no node inside the distance field" in capsys.readouterr().err
