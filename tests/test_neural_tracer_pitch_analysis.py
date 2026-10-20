"""scripts/neural_tracer_pitch_analysis.py: the frame back to the cube, the identity check, and the registered reading."""

import json
import math
import sys
import types
from pathlib import Path

import numpy as np
import pytest

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


def test_a_median_inside_p3_moves_nothing_without_flips():
    """The registered rule: the row moves if P3 fails or the comparison flips on 2+
    cubes. A threshold of |log 1.15| put the lower edge at 0.87, so a median of
    0.86, inside P3's 0.85-1.15, read as material."""
    v = pa.verdict(
        *_rows(
            {
                "in": (5.0 * 0.86, 5.0),
                "s3": (12.0 * 0.86, 12.0),
                "s5": (4.0 * 0.86, 4.0),
            }
        )
    )
    assert math.isclose(v["median_pen_ratio_pitch_over_native"], 0.86)
    assert v["predictions"]["P3_median_pen_ratio_within_0.85_1.15"] is True
    assert v["flips_against_tracer"] == 0
    assert v["published_row_moves_materially"] is False


def test_a_cube_traced_to_nothing_is_a_ratio_of_zero():
    """Not a cube left out: the 11 in-sample cubes at 0 make the median 0."""
    v = pa.verdict(*_rows({"in": (0.0, 5.0), "s3": (12.0, 12.0), "s5": (4.0, 4.0)}))
    assert v["median_pen_ratio_pitch_over_native"] == 0.0
    assert v["predictions"]["P3_median_pen_ratio_within_0.85_1.15"] is False
    assert v["published_row_moves_materially"] is True


def _custom(ratios, native=5.0):
    """Rows for the given cubes at pitch-over-native ratios; every native score,
    and so every pitch-matched one up to ratio 2, below our tracer's 10."""
    rows = {c: {PEN: native * r} for c, r in ratios.items()}
    nat = {c: {PEN: native} for c in f91.ALL}
    comp = {c: {"tracer": {PEN: 10.0}} for c in f91.ALL}
    return rows, nat, comp


def test_two_flips_move_the_row_when_p3_holds():
    """The rule's other half: every ratio 1.0, but cubes that now lead our
    tracer. Two flips move the row; one does not."""
    for flipped, moves in ((2, True), (1, False)):
        ratios = dict.fromkeys(f91.ALL, 1.0)
        for c in f91.S3[:flipped]:
            ratios[c] = 2.2  # 11.0 against the tracer's 10
        v = pa.verdict(*_custom(ratios))
        assert v["predictions"]["P3_median_pen_ratio_within_0.85_1.15"] is True
        assert v["flips_against_tracer"] == flipped
        assert v["published_row_moves_materially"] is moves


def test_flips_decide_even_when_p3_cannot_be_evaluated():
    """With 16 rows P3 is unevaluated, but 2+ flips already move the row."""
    cubes = f91.ALL[:16]
    ratios = dict.fromkeys(cubes, 1.0)
    v = pa.verdict(*_custom(ratios))
    assert v["predictions"]["P3_median_pen_ratio_within_0.85_1.15"] is None
    assert v["published_row_moves_materially"] is None
    for c in cubes[:2]:
        ratios[c] = 2.2
    v = pa.verdict(*_custom(ratios))
    assert v["predictions"]["P3_median_pen_ratio_within_0.85_1.15"] is None
    assert v["published_row_moves_materially"] is True


def test_the_median_of_an_even_count_is_the_mean_of_the_middle_two():
    """20 rows (one run failed), half at 0.5 and half at 1.3: the median is 0.9,
    inside P3; their geometric mean, 0.81, would not be."""
    cubes = f91.ALL[:20]
    ratios = {c: (0.5 if i < 10 else 1.3) for i, c in enumerate(cubes)}
    v = pa.verdict(*_custom(ratios))
    assert math.isclose(v["median_pen_ratio_pitch_over_native"], 0.9)
    assert v["predictions"]["P3_median_pen_ratio_within_0.85_1.15"] is True


def test_p3_includes_its_bounds_and_needs_17_rows():
    for r in (0.85, 1.15):
        v = pa.verdict(*_custom(dict.fromkeys(f91.ALL, r)))
        assert v["predictions"]["P3_median_pen_ratio_within_0.85_1.15"] is True
    for n, evaluated in ((17, True), (16, False)):
        v = pa.verdict(*_custom(dict.fromkeys(f91.ALL[:n], 1.0)))
        p3 = v["predictions"]["P3_median_pen_ratio_within_0.85_1.15"]
        assert (p3 is not None) is evaluated


def test_a_native_score_of_zero_is_refused():
    rows, native, comp = _custom(dict.fromkeys(f91.ALL, 1.0))
    native[f91.S3[0]] = {PEN: 0.0}
    with pytest.raises(ValueError, match="native score of 0"):
        pa.verdict(rows, native, comp)


def test_a_failed_run_is_incomplete_only_below_the_row_minimums():
    """The registration ties INCOMPLETE to the row minimums. The status read
    INCOMPLETE after any failed run, though 20 rows evaluate every prediction."""
    rows, native, comp = _custom(dict.fromkeys(f91.ALL, 1.0))
    rows[f91.S5_HELDOUT[0]] = None  # main() records a failed run as None
    status, reading = pa.outcome({}, rows, native, comp)
    assert status == "OK" and reading is not None
    for c in f91.S3[:3]:  # 5 Scroll-3 rows: P2 unevaluated
        rows[c] = None
    status, reading = pa.outcome({}, rows, native, comp)
    assert status == "INCOMPLETE"
    assert reading["predictions"]["P2_s3_leads_tracer_on_6_of_8"] is None
    assert pa.outcome({"x": ["box"]}, rows, native, comp) == ("IDENTITY_FAILED", None)


def _run_main(tmp_path, monkeypatch, failed=(), bad_identity=()):
    """main() end to end, with ScrollGT's scorer and the .afv reader stubbed: every
    scored cube at 5.0 against a native 5.0 and our tracer's 10.0."""

    class Score:
        def as_row(self):
            return {PEN: 5.0, pa.COV: 0.5}

    ev = types.ModuleType("scrollgt.fibers.eval_trace")
    ev.SCORING_VERSION = 3  # type: ignore[attr-defined]
    ev.score_tracing = lambda skel, labels, tolerance: Score()  # type: ignore[attr-defined]
    tg = types.ModuleType("scrollgt.fibers.target")
    tg.load_fiber_target = lambda target: (None, None, None)  # type: ignore[attr-defined]
    for name, module in (("scrollgt", types.ModuleType("scrollgt")),
                         ("scrollgt.fibers", types.ModuleType("scrollgt.fibers")),
                         ("scrollgt.fibers.eval_trace", ev), ("scrollgt.fibers.target", tg)):  # fmt: skip
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(sys, "path", list(sys.path))  # main() prepends ScrollGT's src
    monkeypatch.setattr(pa.afv_to_labels, "read_afv", lambda path: {})
    monkeypatch.setattr(pa.afv_to_labels, "rasterize", lambda fibers, shape: None)
    monkeypatch.setattr(f91, "stop_reasons", lambda afv: {})
    monkeypatch.setattr(f91, "SG", tmp_path / "sg")
    native = {}
    for c in f91.ALL:
        meta = tmp_path / "sg" / "data" / f"fibers_{c}" / "meta.json"
        meta.parent.mkdir(parents=True)
        meta.write_text(
            json.dumps({"floors": {f91.TRACER: {PEN: 10.0}, f91.CC: {PEN: 1.0}}})
        )
        native[c] = {PEN: 5.0, pa.COV: 0.5}
        if c in failed:
            continue
        run = tmp_path / "work" / c
        run.mkdir(parents=True)
        (run / "fibers.afv").write_text("")
        record = _record(c)
        if c in bad_identity:
            record["base_um"] = 7.91
        (run / "run.json").write_text(json.dumps(record))
    (tmp_path / "native.json").write_text(json.dumps({"neural_rows": native}))
    out = tmp_path / "out.json"
    argv = [
        "pa",
        "--work",
        str(tmp_path / "work"),
        "--native",
        str(tmp_path / "native.json"),
    ]
    monkeypatch.setattr(sys, "argv", [*argv, "--out", str(out)])
    rc = pa.main()
    return rc, json.loads(out.read_text())


def test_main_writes_the_registered_status_and_exits_by_it(tmp_path, monkeypatch):
    rc, out = _run_main(tmp_path / "all", monkeypatch)
    assert (rc, out["status"], out["failed_runs"]) == (0, "OK", [])
    assert out["published_row_moves_materially"] is False

    one = f91.S5_HELDOUT[0]
    rc, out = _run_main(tmp_path / "one", monkeypatch, failed=(one,))
    assert (rc, out["status"], out["failed_runs"]) == (0, "OK", [one])

    rc, out = _run_main(tmp_path / "three", monkeypatch, failed=tuple(f91.S3[:3]))
    assert (rc, out["status"]) == (1, "INCOMPLETE")
    assert out["predictions"]["P2_s3_leads_tracer_on_6_of_8"] is None

    rc, out = _run_main(tmp_path / "id", monkeypatch, bad_identity=(f91.S3[0],))
    assert (rc, out["status"]) == (1, "IDENTITY_FAILED")
    assert "predictions" not in out and f91.S3[0] in out["identity_problems"]
