"""The finding-117 report states the numbers in its record, and the record's verdict follows from them."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_343_tile_gate.md").read_text()
FLAT = " ".join(REPORT.split())
RECORD = json.loads((ROOT / "reports/first_letters_343_tile_gate.json").read_text())
STRATEGY = (ROOT / "docs/RESEARCH_STRATEGY.md").read_text()


def _load():
    path = ROOT / "repro/first_letters/pherc343/tile_gate/tile_gate.py"
    spec = importlib.util.spec_from_file_location("tile_gate_for_report", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


tg = _load()


def _pct(share):
    return f"{100 * share:.1f}%"


def test_the_verdict_follows_from_the_registered_table():
    assert RECORD["script_exit"] == 0
    verdict = tg.verdict(RECORD["raw"])
    assert verdict == RECORD["verdict"] == "LOCAL_GATE_WORKS"
    assert f"**Verdict `{verdict}`**" in REPORT


def test_the_rows_are_the_records():
    raw, four, snapped = (
        RECORD["raw"],
        RECORD["described"]["raw_within_4"],
        RECORD["described"]["snapped"],
    )
    row = (
        f"| {raw['tiles']} | {raw['right']} | {raw['wrong']} | **{raw['auc']:.3f}** | "
        f"{raw['floor']['p95']:.3f} | {_pct(raw['share_right_overall'])} | "
        f"**{_pct(raw['share_right_at_line'])}** ({raw['tiles_at_line']} tiles) |"
    )
    assert row in REPORT, row
    row = (
        f"| {four['tiles']} | {four['right']} | {four['wrong']} | {four['auc']:.3f} | "
        f"{four['floor']['p95']:.3f} | {_pct(four['share_right_overall'])} | "
        f"{_pct(four['share_right_at_line'])} ({four['tiles_at_line']} tiles) |"
    )
    assert row in REPORT, row
    assert snapped["wrong"] == 0 and snapped["auc"] is None
    assert f"| {snapped['tiles']} | {snapped['right']} | 0 | none | none |" in REPORT
    for name, part in RECORD["per_winding"].items():
        assert f"{name} has {part['right']} right tiles of {part['tiles']}" in FLAT or (
            f"{name} {part['right']} of {part['tiles']}" in FLAT
        )


def test_the_floor_by_shift_is_the_records_and_its_two_nearest_shifts_set_the_p95():
    by_shift = RECORD["not_registered"]["floor_by_shift"]
    row = (
        "| AUC | " + " | ".join(f"{by_shift[str(k)]:.3f}" for k in range(1, 11)) + " |"
    )
    assert row in REPORT, row
    values = sorted(by_shift.values())
    assert abs(max(values) - RECORD["raw"]["floor"]["max"]) < 0.001
    middle = [by_shift[str(k)] for k in range(3, 9)]
    assert f"give {min(middle):.2f} to {max(middle):.2f}" in FLAT
    margin = RECORD["raw"]["auc"] - RECORD["raw"]["floor"]["p95"]
    assert f"clears it by {margin:.3f}" in FLAT


def test_the_wrong_tiles_are_the_records():
    wrong, right = (
        RECORD["not_registered"]["wrong_tiles"],
        RECORD["not_registered"]["right_tiles"],
    )
    assert (
        wrong["count"] == RECORD["raw"]["wrong"]
        and right["count"] == RECORD["raw"]["right"]
    )
    assert wrong["excess_max"] < 0
    assert f"**All {wrong['count']} wrong tiles score below zero**" in FLAT
    lo, hi = wrong["within_2_range"]
    assert (
        f"{100 * lo:.0f}% to {100 * hi:.0f}% of a wrong tile's nodes are within 2"
        in FLAT
    )
    lo, hi = wrong["within_4_range"]
    assert f"{100 * lo:.0f}% to {100 * hi:.0f}% within 4" in FLAT
    assert (
        f"Their median is {right['excess_median']:.3f}, and {right['with_negative_excess']} of the 53"
        in FLAT
    )


def test_the_strategy_carries_the_verdict_and_links_the_report():
    assert "reports/first_letters_343_tile_gate.md" in STRATEGY
    assert f"`{RECORD['verdict']}`" in STRATEGY
