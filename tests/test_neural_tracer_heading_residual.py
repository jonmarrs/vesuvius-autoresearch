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


def _modules(
    context_error=None, normal_error=False, ambiguous=False, axis=(1.0, 0.0, 0.0)
):
    """Stand-ins for villa's frames/ct.py and shared/ct_structure.py, each failing as asked."""
    calls = []

    def _ct_context(vol, xyz):
        calls.append("context")
        if context_error:
            raise _Err(context_error)
        return "window", "centre"

    def ct_sheet_normal(window, centre):
        calls.append("normal")
        if normal_error:
            raise _Err("CT seed context has no identifiable sheet normal")
        return np.array([0.0, 1.0, 0.0])

    def sheet_heading(normal, family):
        calls.append("heading")
        if ambiguous:
            raise _Err("H/V is ambiguous for this sheet orientation")
        return np.asarray(axis, float)

    ct = types.SimpleNamespace(_ct_context=_ct_context, sheet_heading=sheet_heading)
    cs = types.SimpleNamespace(SeedHeadingError=_Err, ct_sheet_normal=ct_sheet_normal)
    return ct, cs, calls


def _classify(direction=(1.0, 0.0, 0.0), **kw):
    ct, cs, calls = _modules(**kw)
    reason, axis = hr.classify(
        None, np.zeros(3), "H", np.asarray(direction, float), ct, cs
    )
    return reason, axis, calls


def test_each_reason_in_villas_order():
    assert _classify(context_error=hr.EDGE_MESSAGE)[::2] == ("edge", ["context"])
    assert _classify(normal_error=True)[::2] == ("no_normal", ["context", "normal"])
    assert _classify(ambiguous=True)[::2] == (
        "ambiguous",
        ["context", "normal", "heading"],
    )
    assert _classify(direction=(0.0, 1.0, 0.0))[::2] == (
        "disagree",
        ["context", "normal", "heading"],
    )
    reason, axis, _ = _classify()
    assert reason == "ok" and np.allclose(axis, [1, 0, 0])


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
    def row(reason, presence, axis):
        return {
            "reason": reason,
            "gt_tangent_angle_presence": presence,
            "gt_tangent_angle_ct_axis": axis,
        }

    rows = [row("disagree", 60.0, 10.0), row("disagree", 50.0, 70.0), row("disagree", 40.0, 5.0),
            row("disagree", None, None), row("ambiguous", 20.0, None), row("ok", 3.0, 4.0)]  # fmt: skip
    s = hr.near_gt_summary(rows)
    assert s["disagree"] == {"near": 3, "median_presence_to_gt": 50.0, "median_ct_axis_to_gt": 10.0,
                             "ct_axis_closer_share": 2 / 3}  # fmt: skip
    assert (
        s["ambiguous"]["near"] == 1 and s["ambiguous"]["ct_axis_closer_share"] is None
    )
    assert s["edge"] == {"near": 0, "median_presence_to_gt": None, "median_ct_axis_to_gt": None,
                         "ct_axis_closer_share": None}  # fmt: skip


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
