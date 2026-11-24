"""The count of open-data volumes the PHerc. 343 recipe's orientation rule turns the wrong way."""

import gzip
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


cf = _load("catalog_flags", "repro/first_letters/submission/catalog_flags.py")
bi = _load("band_index", "repro/first_letters/eligible_band/band_index.py")


@pytest.mark.parametrize(
    "ttb, lh, expected",
    [
        (False, False, "rule_holds"),
        (True, False, "turned_180"),
        (False, True, "mirrored_left_right"),
        (True, True, "mirrored_top_bottom"),
        (None, False, "unknown"),
        (True, None, "unknown"),
        ("true", False, "unknown"),  # only real booleans count
    ],
)
def test_each_pair_of_flags(ttb, lh, expected):
    assert cf.case(ttb, lh) == expected


def _sheet(
    theta_along_cols: float, z_down_rows: float
) -> tuple[np.ndarray, np.ndarray]:
    """A patch of a cylinder of radius 500 around the z axis: theta grows by theta_along_cols per column, z by
    z_down_rows per row."""
    i, j = np.mgrid[0:20, 0:30].astype(np.float64)
    theta = 0.3 + j * theta_along_cols
    z = 1000 + i * z_down_rows
    xyz = np.stack([500 * np.cos(theta), 500 * np.sin(theta), z], axis=-1)
    return xyz, np.ones(i.shape, bool)


@pytest.mark.parametrize("ttb", [False, True])
@pytest.mark.parametrize("lh", [False, True])
def test_the_cases_agree_with_band_index(ttb, lh):
    """The recipe's rule is band_index.orientation with both flags false; a case names which of its flips differ."""
    xyz, valid = _sheet(0.002, 2.0)
    axis = np.array(
        [[0.0, 5000.0], [0.0, 0.0], [0.0, 0.0]]
    )  # rows z, x, y, as band_index.axis returns
    recipe = bi.orientation(xyz, valid, axis, False, False)
    general = bi.orientation(xyz, valid, axis, ttb, lh)
    wrong = (
        recipe["flip_lr"] != general["flip_lr"],
        recipe["flip_ud"] != general["flip_ud"],
    )
    expected = {
        "rule_holds": (False, False),
        "turned_180": (True, True),
        "mirrored_left_right": (True, False),
        "mirrored_top_bottom": (False, True),
    }[cf.case(ttb, lh)]
    assert wrong == expected


def _catalog():
    def vol(ttb, lh):
        return {
            "properties": {
                "z_direction_is_top_to_bottom": ttb,
                "left_handed_coordinates": lh,
            }
        }

    return {
        "samples": {
            "A": {"volumes": {"1": vol(False, False), "2": vol(True, False)}},
            "B": {"volumes": {"3": vol(True, False)}},
            "C": {"volumes": {"4": vol(None, False)}},
            "D": {"volumes": {"5": vol(False, True), "6": vol(True, True)}},
            "E": {},  # a sample without volumes
        }
    }


def test_count_over_volumes_and_samples():
    out = cf.count(_catalog())
    assert out["volumes"] == 6
    assert out["volumes_by_case"] == {
        "rule_holds": 1,
        "turned_180": 2,
        "mirrored_left_right": 1,
        "mirrored_top_bottom": 1,
        "unknown": 1,
    }
    assert out["volumes_with_both_flags"] == 5
    assert out["volumes_the_rule_turns_wrong"] == 4
    assert out["share_of_known_turned_wrong"] == 0.8
    assert out["samples_by_case"]["turned_180"] == ["A", "B"]


def test_main_reads_a_gzipped_catalog(tmp_path):
    path = tmp_path / "metadata.json"
    path.write_bytes(gzip.compress(json.dumps(_catalog()).encode()))
    out = tmp_path / "flags.json"
    assert cf.main([str(path), str(out), "--source", "snapshot X"]) == 0
    record = json.loads(out.read_text())
    assert record["source"] == "snapshot X" and record["volumes"] == 6


# --- the flags' types, null entries, the share's edges, every case listed, and what the command prints -------------


@pytest.mark.parametrize(("ttb", "lh"), [(True, "yes"), (1, False), (False, 0)])
def test_a_flag_that_is_not_a_boolean_is_unknown(ttb, lh):
    assert cf.case(ttb, lh) == "unknown"


def test_null_volumes_and_null_properties_are_counted_as_unknown_not_failed():
    catalog = {
        "samples": {
            "A": {"volumes": None},
            "B": {"volumes": {"1": {"properties": None}, "2": {}}},
        }
    }
    out = cf.count(catalog)
    assert (out["volumes"], out["volumes_by_case"]["unknown"]) == (2, 2)


def test_every_case_is_listed_even_at_zero_and_no_known_volume_gives_no_share():
    out = cf.count({"samples": {"A": {"volumes": {"1": {"properties": {}}}}}})
    assert out["volumes_by_case"] == {"rule_holds": 0, "turned_180": 0, "mirrored_left_right": 0,
                                      "mirrored_top_bottom": 0, "unknown": 1}  # fmt: skip
    assert out["samples_by_case"]["rule_holds"] == [] and out["samples_by_case"][
        "unknown"
    ] == ["A"]
    assert (out["volumes_with_both_flags"], out["share_of_known_turned_wrong"]) == (
        0,
        None,
    )


def test_the_share_is_kept_to_four_decimals():
    catalog = _catalog()
    del catalog["samples"]["D"]  # known: rule_holds 1, turned_180 2
    assert cf.count(catalog)["share_of_known_turned_wrong"] == 0.6667


def test_main_reads_a_plain_catalog_and_prints_the_counts_by_case(tmp_path, capsys):
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps(_catalog()))
    assert cf.main([str(path), str(tmp_path / "flags.json")]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed == {"volumes": 6, "volumes_by_case": cf.count(_catalog())["volumes_by_case"],
                       "share_of_known_turned_wrong": 0.8}  # fmt: skip
    assert json.loads((tmp_path / "flags.json").read_text())["source"] is None
