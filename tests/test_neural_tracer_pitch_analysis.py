"""scripts/neural_tracer_pitch_analysis.py: the frame back to the cube, the identity check, and the registered reading."""

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import neural_tracer_analysis as f91  # noqa: E402
import neural_tracer_pitch_analysis as pa  # noqa: E402

PEN = pa.PEN


def test_resampled_fibers_land_in_the_cube_frame():
    """A fiber traced at resampled x (xyz) is at x * 9.6/7.91 in the cube, in zyx order."""
    fibers = {7: np.array([[10.0, 20.0, 30.0], [11.0, 20.0, 30.0]])}
    out = pa.scale_back(fibers, "s1_00497_01497_03997_256")
    np.testing.assert_allclose(
        out[7], np.array([[30.0, 20.0, 10.0], [30.0, 20.0, 11.0]]) * pa.R
    )


def _record(cube):
    n = pa.grid_size(cube)
    return {
        **pa.SETTINGS,
        "checkpoint_sha256": f91.CHECKPOINT_SHA256,
        "box": {"lo": [0.0, 0.0, 0.0], "hi": [n, n, n]},
        "ct": f"/x/ct_9p6/{cube}.zarr",
        "presence": f"/x/presence_9p6/{cube}_presence.zarr/1",
    }


def test_the_registered_run_passes_and_finding_91s_does_not():
    cube = "s3_00994_00494_01994_512"
    assert pa.grid_size(cube) == 211 and pa.grid_size("s1_00497_01497_03997_256") == 106
    assert pa.identity_problems(_record(cube), cube) == []
    native = {**_record(cube), "base_um": 7.91, "box": {"lo": [0.0] * 3, "hi": [256.0] * 3},
              "ct": f"/x/ct/{cube}.zarr", "presence": f"/x/presence/{cube}_presence.zarr/1"}  # fmt: skip
    problems = " ".join(pa.identity_problems(native, cube))
    for field in ("base_um", "box", "ct", "presence"):
        assert field in problems


def _rows(pen_by_group):
    """Rows for all 21 cubes, our tracer at 10 everywhere."""
    rows, native, comp = {}, {}, {}
    for group, cubes in (("in", f91.IN_SAMPLE), ("s3", f91.S3), ("s5", f91.S5_HELDOUT)):
        for c in cubes:
            new, old = pen_by_group[group]
            rows[c], native[c] = {PEN: new}, {PEN: old}
            comp[c] = {"tracer": {PEN: 10.0}}
    return rows, native, comp


def test_unchanged_rows_read_as_registered():
    """Finding 91's pattern kept: trails in sample, leads on Scroll 3, no change; pitch is not the cause."""
    v = pa.verdict(*_rows({"in": (5.0, 5.0), "s3": (12.0, 12.0), "s5": (4.0, 4.0)}))
    assert all(v["predictions"].values())
    assert (
        v["median_pen_ratio_pitch_over_native"] == 1.0
        and v["flips_against_tracer"] == 0
    )
    assert v["published_row_moves_materially"] is False
    assert (
        v["in_sample_reading"] == "pitch is not the main cause of the in-sample deficit"
    )


def test_closing_the_in_sample_deficit_reads_as_a_material_cause():
    v = pa.verdict(*_rows({"in": (12.0, 5.0), "s3": (12.0, 12.0), "s5": (4.0, 4.0)}))
    assert v["predictions"]["P1_in_sample_trails_tracer_on_9_of_11"] is False
    assert (
        v["in_sample_reading"] == "pitch is a material cause of the in-sample deficit"
    )
    assert (
        v["flips_against_tracer"] == 11 and v["published_row_moves_materially"] is True
    )


def test_a_uniform_shift_beyond_15_percent_is_material():
    v = pa.verdict(
        *_rows(
            {"in": (5.0 * 1.2, 5.0), "s3": (12.0 * 1.2, 12.0), "s5": (4.0 * 1.2, 4.0)}
        )
    )
    assert v["predictions"]["P3_median_pen_ratio_within_0.85_1.15"] is False
    assert math.isclose(v["median_pen_ratio_pitch_over_native"], 1.2)
    assert (
        v["published_row_moves_materially"] is True and v["flips_against_tracer"] == 0
    )


def test_too_few_rows_leave_a_prediction_unevaluated():
    rows, native, comp = _rows({"in": (5.0, 5.0), "s3": (12.0, 12.0), "s5": (4.0, 4.0)})
    for c in f91.S3[:3]:
        del rows[c]
    v = pa.verdict(rows, native, comp)
    assert v["predictions"]["P2_s3_leads_tracer_on_6_of_8"] is None
    assert v["predictions"]["P1_in_sample_trails_tracer_on_9_of_11"] is True
