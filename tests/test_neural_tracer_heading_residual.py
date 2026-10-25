"""scripts/neural_tracer_heading_residual.py: villa's seed-heading tests told apart, in villa's order."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))
import neural_tracer_heading_residual as hr  # noqa: E402

TRACERS = _REPO / "villa/vesuvius/src/vesuvius/neural_tracing/tracers"


class _Err(ValueError):
    pass


SHEET_Y = (
    0.1,
    1.0,
    0.2,
)  # an xyz tensor's diagonal: the sheet normal is y, the relative gap (1.0 - 0.2) / 1.0


def _modules(context_error=None, tensor=SHEET_Y, ambiguous=False, axis=(1.0, 0.0, 0.0)):
    """Stand-ins for villa's frames/ct.py and shared/ct_structure.py, each failing as asked."""
    calls = []

    def _ct_context(vol, xyz):
        calls.append("context")
        if context_error:
            raise _Err(context_error)
        return "window", "centre"

    def ct_structure_tensor(window, centre, *, derivative_sigma, integration_sigma):
        calls.append("normal")
        assert (derivative_sigma, integration_sigma) == (2.0, 8.0)
        return np.diag(np.asarray(tensor, float))

    def sheet_heading(normal, family):
        calls.append("heading")
        if ambiguous:
            raise _Err("H/V is ambiguous for this sheet orientation")
        return np.asarray(axis, float)

    ct = types.SimpleNamespace(_ct_context=_ct_context, sheet_heading=sheet_heading)
    cs = types.SimpleNamespace(SeedHeadingError=_Err, ct_structure_tensor=ct_structure_tensor,
                               CT_DERIVATIVE_SIGMA=2.0, CT_INTEGRATION_SIGMA=8.0)  # fmt: skip
    return ct, cs, calls


def _classify(direction=(1.0, 0.0, 0.0), **kw):
    ct, cs, calls = _modules(**kw)
    reason, axis, sheet = hr.classify(
        None, np.zeros(3), "H", np.asarray(direction, float), ct, cs
    )
    return reason, axis, calls, sheet


def test_each_reason_in_villas_order():
    assert _classify(context_error=hr.EDGE_MESSAGE)[::2] == ("edge", ["context"])
    assert _classify(tensor=(0.0, 0.0, 0.0))[::2] == (
        "no_normal",
        ["context", "normal"],
    )
    assert _classify(tensor=(1.0, 1.0, 0.1))[::2] == (
        "no_normal",
        ["context", "normal"],
    )  # two equal largest
    assert _classify(ambiguous=True)[::2] == (
        "ambiguous",
        ["context", "normal", "heading"],
    )
    assert _classify(direction=(0.0, 1.0, 0.0))[::2] == (
        "disagree",
        ["context", "normal", "heading"],
    )
    reason, axis, _, sheet = _classify()
    assert reason == "ok" and np.allclose(axis, [1, 0, 0])
    assert (
        np.allclose(np.abs(sheet["normal"]), [0, 1, 0])
        and abs(sheet["gap"] - 0.8) < 1e-12
    )


def test_the_sheet_evidence_rides_along():
    assert _classify(context_error=hr.EDGE_MESSAGE)[3] == {"normal": None, "gap": None}
    assert _classify(tensor=(0.0, 0.0, 0.0))[3] == {"normal": None, "gap": None}
    assert _classify(tensor=(1.0, 1.0, 0.1))[3] == {"normal": None, "gap": 0.0}
    sheet = _classify(tensor=(1.0, 0.98, 0.1))[
        3
    ]  # a sheet villa accepts, though not a clear one
    assert abs(sheet["gap"] - 0.02) < 1e-12 and sheet["gap"] < hr.MIN_EIGENGAP
    assert np.allclose(
        np.abs(_classify(direction=(0.0, 1.0, 0.0))[3]["normal"]), [0, 1, 0]
    )


def test_out_of_plane():
    assert hr.out_of_plane([1, 0, 0], [0, 0, 1]) == 0.0
    assert hr.out_of_plane([0, 0, -2], [0, 0, 1]) == 90.0
    assert abs(hr.out_of_plane([1, 0, 1], [0, 0, 1]) - 45.0) < 1e-9
    assert (
        hr.out_of_plane(None, [0, 0, 1]) is None
        and hr.out_of_plane([1, 0, 0], None) is None
    )
    # the sheet's tilt from vertical: a normal across the scroll's axis is a vertical sheet
    assert (
        hr.out_of_plane([1, 0, 0], hr.Z) == 0.0
        and hr.out_of_plane([0, 0, -1], hr.Z) == 90.0
    )


def test_another_context_error_is_not_counted_as_the_edge():
    with pytest.raises(_Err, match="finite"):
        _classify(context_error="Seed position must be a finite xyz vector")


@pytest.mark.parametrize("degrees, reason", [(0.0, "ok"), (34.9, "ok"), (35.1, "disagree"), (140.0, "disagree"), (150.0, "ok"),
                                             (180.0, "ok"), (90.0, "disagree")])  # fmt: skip
def test_the_35_degree_test_is_sign_free(degrees, reason):
    r = np.radians(degrees)
    assert _classify(direction=(np.cos(r), np.sin(r), 0.0))[0] == reason


def test_the_constants_are_villas():
    volume = (TRACERS / "fibers/tracing/volume.py").read_text()
    assert (
        "if abs(h @ direction) < np.cos(np.radians(35)):\n        return None" in volume
    )
    assert hr.AGREE_DEGREES == 35.0
    frames = (TRACERS / "fibers/frames/ct.py").read_text()
    structure = (TRACERS / "shared/ct_structure.py").read_text()
    # classify's normal is ct_sheet_normal's, from the same tensor, at the seed headings' min_gap
    assert (
        "def ct_sheet_normal(cube, center_zyx, *, min_gap=1e-6):" in structure
        and hr.SEED_MIN_GAP == 1e-6
    )
    assert (
        "if values[-1] <= 1e-12 or values[-1]-values[-2] <= min_gap*values[-1]:"
        in structure
    )
    assert "return vectors[::-1, -1]" in structure
    assert (
        "derivative_sigma=CT_DERIVATIVE_SIGMA, integration_sigma=CT_INTEGRATION_SIGMA)[::-1, ::-1])"
        in structure
    )
    assert "MIN_EIGENGAP = .05" in structure and hr.MIN_EIGENGAP == 0.05
    assert f"raise SeedHeadingError('{hr.EDGE_MESSAGE}')" in frames
    # villa's own order: the window, then the normal, then the family's axis, then the agreement
    body = volume.split("def _seed_heading(task):")[1].split("\ndef ")[0]
    assert body.index("ct_seed_heading(") < body.index("np.cos(np.radians(35))")
    assert "return sheet_heading(ct_normal(vol, pos_xyz), family)" in frames
    assert "return ct_sheet_normal(*_ct_context(vol, pos_xyz))" in frames


@pytest.mark.parametrize("size, hi", [(256, 192.0), (512, 320.0)])
def test_the_padded_box_maps_onto_the_cube(size, hi):
    assert np.allclose(hr.to_cube_zyx([64.0, 64.0, 64.0], 2.0), 0)
    assert np.allclose(hr.to_cube_zyx([hi, hi, hi], 2.0), size)
    assert np.allclose(
        hr.to_cube_zyx([65.0, 70.0, 80.0], 2.0), [32, 12, 2]
    )  # xyz -> zyx


def test_angle_is_between_lines():
    assert hr.angle([1, 0, 0], [-1, 0, 0]) == 0.0
    assert hr.angle([1, 0, 0], [0, 2, 0]) == 90.0
    assert abs(hr.angle([1, 1, 0], [1, 0, 0]) - 45.0) < 1e-9


def test_near_gt_summary():
    def row(
        reason, presence, axis, gap=None, gt_out=None, presence_out=None, tilt=None
    ):
        return {"reason": reason, "gt_tangent_angle_presence": presence, "gt_tangent_angle_ct_axis": axis, "gap": gap,
                "gt_out_of_ct_sheet": gt_out, "presence_out_of_ct_sheet": presence_out, "sheet_tilt": tilt}  # fmt: skip

    rows = [row("disagree", 60.0, 10.0, 0.01, 50.0, 5.0, 80.0), row("disagree", 50.0, 70.0, 0.20, 40.0, 6.0, 10.0),
            row("disagree", 40.0, 5.0, 0.03, 30.0, 7.0, 60.0), row("disagree", None, None, 0.30, None, None, 50.0),
            row("ambiguous", 20.0, None, 0.5, 1.0, 2.0), row("ok", 3.0, 4.0, 0.6, 2.0, 3.0, 5.0)]  # fmt: skip
    s = hr.near_gt_summary(rows)
    assert s["disagree"] == {"near": 3, "median_presence_to_gt": 50.0, "median_ct_axis_to_gt": 10.0,
                             "median_gap": (0.03 + 0.20) / 2, "median_sheet_tilt": 55.0, "steep_sheet_share": 0.75,
                             "unclear_sheet_share": 0.5,
                             "median_gt_out_of_ct_sheet": 40.0, "median_presence_out_of_ct_sheet": 6.0,
                             "ct_axis_closer_share": 2 / 3}  # fmt: skip
    assert (
        s["ambiguous"]["near"] == 1 and s["ambiguous"]["ct_axis_closer_share"] is None
    )
    assert s["edge"] == {"near": 0, "median_presence_to_gt": None, "median_ct_axis_to_gt": None, "median_gap": None,
                         "median_sheet_tilt": None, "steep_sheet_share": None,
                         "unclear_sheet_share": None, "median_gt_out_of_ct_sheet": None,
                         "median_presence_out_of_ct_sheet": None, "ct_axis_closer_share": None}  # fmt: skip
    # pass 1's rows carry no sheet fields: they summarise as before
    old = [
        {k: v for k, v in r.items() if k.startswith("gt_tangent") or k == "reason"}
        for r in rows
    ]
    assert hr.near_gt_summary(old)["disagree"]["median_ct_axis_to_gt"] == 10.0


def test_last_tile(tmp_path):
    lines = [{"tile": "a", "dots": 1}, {"tile": "a", "dots": 7}]
    (tmp_path / "tiles.jsonl").write_text(
        "\n".join(json.dumps(x) for x in lines) + "\n\n"
    )
    assert hr.last_tile(tmp_path)["dots"] == 7
    (tmp_path / "tiles.jsonl").write_text(
        json.dumps({"tile": "a"}) + "\n" + json.dumps({"tile": "b"}) + "\n"
    )
    with pytest.raises(ValueError, match="2 tiles"):
        hr.last_tile(tmp_path)


def test_the_held_out_256_cubes():
    assert sorted(hr.HELD_256) == sorted(
        c for c in hr.pl.f91.S5_HELDOUT if c.endswith("_256")
    )
    assert hr.MARGIN == 128 and hr.REASONS[-1] == "ok"
