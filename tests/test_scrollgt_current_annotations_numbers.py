"""Bind finding 82's report (reports/scrollgt_current_annotations.md) to the JSON its registered analysis wrote."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPORTS = Path(__file__).resolve().parents[1] / "reports"
CC, TB, TF = "floor_connected_components", "tracer_baseline", "tracer_frozen"


@pytest.fixture(scope="module")
def data() -> tuple[str, dict]:
    p = REPORTS / "scrollgt_current_annotations.json"
    if not p.exists():
        pytest.skip("scrollgt_current_annotations.json not present")
    return (REPORTS / "scrollgt_current_annotations.md").read_text(), json.loads(
        p.read_text()
    )


def _arrow(o: dict, n: dict, key: str, fmt: str) -> str:
    return f"{o[key]:{fmt}} → {n[key]:{fmt}}"


def test_every_table_row_matches(data):
    report, r = data
    for cube, v in r["cubes"].items():
        o, n = v["old"], v["current"]
        stem = cube.rsplit("_", 1)[0]
        row = (
            f"| {stem} | {o['oracle']['n_gt_fibers']} → {n['oracle']['n_gt_fibers']} | "
            f"{_arrow(o['oracle'], n['oracle'], 'erl', '.2f')} | {_arrow(o[CC], n[CC], 'erl', '.2f')} | "
            f"{_arrow(o[TB], n[TB], 'erl', '.2f')} | {_arrow(o[CC], n[CC], 'erl_merge_penalized', '.2f')} | "
            f"{_arrow(o[TB], n[TB], 'erl_merge_penalized', '.2f')} | "
            f"{_arrow(o[TF], n[TF], 'erl_merge_penalized', '.2f')} | {_arrow(o[CC], n[CC], 'coverage', '.4f')} | "
            f"{_arrow(o[TB], n[TB], 'coverage', '.4f')} |"
        )
        assert row in report, row
        row2 = (
            f"| {stem} | {o[CC]['merges']} → {n[CC]['merges']} | {o[TB]['merges']} → {n[TB]['merges']} | "
            f"{_arrow(o[CC], n[CC], 'precision', '.4f')} | {_arrow(o[TB], n[TB], 'precision', '.4f')} |"
        )
        assert row2 in report, row2


def test_derived_figures(data):
    report, r = data
    c = r["cubes"]
    ratios = [c[k]["current"][CC]["erl"] / c[k]["current"][TB]["erl"] for k in c]
    assert (
        f"{min(ratios):.1f}–{max(ratios):.1f}×" == "3.7–3.9×"
        and "(3.7–3.9× on current" in report
    )
    s5 = c["s5_14997_01497_01497_256"]
    lead_old = (
        s5["old"][TB]["erl_merge_penalized"] / s5["old"][CC]["erl_merge_penalized"] - 1
    )
    lead_new = (
        s5["current"][TB]["erl_merge_penalized"]
        / s5["current"][CC]["erl_merge_penalized"]
        - 1
    )
    assert f"+{100 * lead_old:.1f}% to +{100 * lead_new:.1f}%" in report
    drops = [
        100 * (c[k]["old"][CC]["coverage"] - c[k]["current"][CC]["coverage"]) for k in c
    ]
    assert f"by {min(drops):.1f} to {max(drops):.1f} points" in report
    grew, covered, share = [], [], []
    for k in c:
        o, n = c[k]["old"], c[k]["current"]
        g = n["oracle"]["gt_length"] - o["oracle"]["gt_length"]
        cv = round(n[CC]["coverage"] * n["oracle"]["gt_length"]) - round(
            o[CC]["coverage"] * o["oracle"]["gt_length"]
        )
        grew.append(f"{g:,.0f}")
        covered.append(f"{cv:,}")
        share.append(f"{100 * cv / g:.0f}%")
    assert f"grew by {grew[0]}, {grew[1]} and {grew[2]} voxels" in report
    assert (
        f"grew by only {covered[0]}, {covered[1]} and {covered[2]}, which is {share[0]}, {share[1]} and {share[2]}"
        in report
    )
    cc_fall = [
        100
        * (
            1
            - c[k]["current"][CC]["erl_merge_penalized"]
            / c[k]["old"][CC]["erl_merge_penalized"]
        )
        for k in c
    ]
    tb_fall = [
        100
        * (
            1
            - c[k]["current"][TB]["erl_merge_penalized"]
            / c[k]["old"][TB]["erl_merge_penalized"]
        )
        for k in c
    ]
    assert (
        f"falls by {min(cc_fall):.0f}–{max(cc_fall):.0f}%, the tracer's by {min(tb_fall):.0f}–{max(tb_fall):.0f}%"
        in report
    )
    s1 = [k for k in c if k.startswith("s1")]
    lead = {
        w: [
            c[k][w][CC]["erl_merge_penalized"] / c[k][w][TB]["erl_merge_penalized"]
            for k in s1
        ]
        for w in ("old", "current")
    }
    assert (f"from {min(lead['old']):.1f}–{max(lead['old']):.1f}× to "
            f"{min(lead['current']):.1f}–{max(lead['current']):.1f}×") in report  # fmt: skip


def test_verdict_and_fidelity(data):
    report, r = data
    assert r["status"] == "OK" and all(r["predictions"].values())
    assert all(v["mismatches"] == [] for v in r["cubes"].values())
    for p in ("P1 HELD, 3 of 3", "P2 HELD, 3 of 3", "P3 HELD, 3 of 3", "P4 HELD"):
        assert f"**{p}.**" in report
    d = r["descriptive"]
    assert not any(
        v["tracer_pen_above_cc"]["old"] != v["tracer_pen_above_cc"]["current"]
        for v in d.values()
    )
    assert all(v["frozen_pen_above_baseline"]["current"] for v in d.values())
