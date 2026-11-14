"""Finding 112's instrument: the sheet-following score, and the registration's constants."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

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
