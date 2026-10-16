"""The registered verdict and identity logic of scripts/neural_tracer_analysis.py, on synthetic rows."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import neural_tracer_analysis as a  # noqa: E402


def _row(pen=30.0, cov=0.45) -> dict:
    return {"erl": pen + 5, "erl_merge_penalized": pen, "coverage": cov}


def _setup():
    rows = {c: _row() for c in a.ALL}
    for c in a.S5_HELDOUT:
        rows[c] = _row(cov=0.20)
    comp = {
        c: {
            "cc": _row(pen=15.0, cov=0.85),
            "tracer": _row(pen=22.0, cov=0.55),
            "generator": _row(pen=18.0, cov=0.27),
        }
        for c in a.ALL
    }
    return rows, comp


def _record(cube: str) -> dict:
    n = a.grid_size(cube)
    return dict(
        a.SETTINGS,
        checkpoint_sha256=a.CHECKPOINT_SHA256,
        box={"lo": [0.0, 0.0, 0.0], "hi": [n, n, n]},
        ct=f"/data/zarr/{cube}.zarr",
        presence=f"/data/presence/{cube}_presence.zarr/1",
        out=f"/work/{cube}",
        rows=512,  # speed-only settings are not compared
        device="cuda",
    )


def test_all_hold_on_constructed_rows():
    v = a.verdict(*_setup())
    assert v["status"] == "OK" and all(v["predictions"].values())


@pytest.mark.parametrize(
    "key,change,prediction",
    [
        (
            "generator",
            {"erl_merge_penalized": 99.0},
            "P1_s3_pen_above_generator_on_75pct",
        ),
        ("tracer", {"erl_merge_penalized": 99.0}, "P2_s3_pen_above_tracer_on_60pct"),
        ("tracer", {"coverage": 0.10}, "P3_s3_coverage_below_tracer_on_75pct"),
    ],
)
def test_each_s3_prediction_fails_when_its_comparator_wins(key, change, prediction):
    rows, comp = _setup()
    # The comparator wins on 3 of 8 (5 of 8 = 62.5% < 75%) or, for P2, on 4 (50% < 60%).
    for c in a.S3[: 4 if prediction.startswith("P2") else 3]:
        comp[c][key] = dict(comp[c][key], **change)
    v = a.verdict(rows, comp)
    assert v["predictions"][prediction] is False
    assert all(ok for name, ok in v["predictions"].items() if name != prediction)


def test_thresholds_are_inclusive():
    rows, comp = _setup()
    for c in a.S3[:2]:  # 6 of 8 = 75% still hold P1 and P3
        comp[c]["generator"] = dict(comp[c]["generator"], erl_merge_penalized=99.0)
        comp[c]["tracer"] = dict(comp[c]["tracer"], coverage=0.10)
    for c in a.S3[2:5]:  # 5 of 8 = 62.5% >= 60% for P2
        comp[c]["tracer"] = dict(comp[c]["tracer"], erl_merge_penalized=99.0)
    p = a.verdict(rows, comp)["predictions"]
    assert all(p.values())


def test_p4_fails_if_either_heldout_s5_cube_reaches_the_s3_median():
    rows, comp = _setup()
    rows[a.S5_HELDOUT[1]] = _row(cov=0.45)
    assert (
        a.verdict(rows, comp)["predictions"]["P4_heldout_s5_coverage_below_s3_median"]
        is False
    )


def test_too_few_s3_runs_leave_s3_predictions_unevaluated():
    rows, comp = _setup()
    for c in a.S3[:3]:
        rows[c] = None
    v = a.verdict(rows, comp)
    assert v["status"] == "INCOMPLETE"
    assert v["predictions"]["P2_s3_pen_above_tracer_on_60pct"] is None
    assert v["failed_runs"] == sorted(a.S3[:3])


def test_a_missing_generator_row_drops_that_cube_from_p1_only():
    rows, comp = _setup()
    comp[a.S3[0]]["generator"] = None
    v = a.verdict(rows, comp)
    assert v["status"] == "OK" and a.S3[0] not in v["s3_cubes_with_generator"]
    assert a.S3[0] in v["s3_cubes"]


def test_a_missing_heldout_s5_run_leaves_p4_unevaluated():
    rows, comp = _setup()
    rows[a.S5_HELDOUT[0]] = None
    v = a.verdict(rows, comp)
    assert v["predictions"]["P4_heldout_s5_coverage_below_s3_median"] is None
    assert v["status"] == "INCOMPLETE"


@pytest.mark.parametrize(
    "cube", ["s1_00497_01497_03997_256", "s3_00994_00494_01994_512"]
)
def test_the_registered_record_passes_identity(cube):
    assert a.identity_problems(_record(cube), cube) == []


@pytest.mark.parametrize(
    "change",
    [
        {"checkpoint_sha256": "0" * 64},
        {"checkpoint": "scrollprize/fiber_single_small"},  # unpinned revision
        {"threshold": 100.0},
        {"min_length": 24},
        {"grid_scale": 8.0},
        {"precision": "fp32"},
        {"box": {"lo": [0.0, 0.0, 0.0], "hi": [64.0, 64.0, 64.0]}},
        {"ct": "/data/zarr/s3_00994_01994_00494_512.zarr"},  # another cube's CT
        {"presence": "/data/presence/s3_00994_00494_01994_512_presence.zarr/2"},
    ],
)
def test_identity_refuses_any_registered_difference(change):
    cube = "s3_00994_00494_01994_512"
    assert a.identity_problems(dict(_record(cube), **change), cube)


def test_identity_refuses_an_absent_setting():
    cube = "s3_00994_00494_01994_512"
    record = _record(cube)
    del record["n_commit"]  # a None default must still be recorded as None
    assert a.identity_problems(record, cube) == ["n_commit='<absent>'"]


def test_grid_size_is_half_the_cube():
    assert a.grid_size("s1_00497_01497_03997_256") == 128.0
    assert a.grid_size("s3_00994_00494_01994_512") == 256.0
