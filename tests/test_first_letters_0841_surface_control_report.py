"""The finding-111 report states the numbers in its record, and the record's verdict follows from them."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_0841_surface_control.md").read_text()
RECORD = json.loads(
    (ROOT / "reports/first_letters_0841_surface_control.json").read_text()
)
STRATEGY = (ROOT / "docs/RESEARCH_STRATEGY.md").read_text()


def _load():
    path = ROOT / "repro/first_letters/pherc0841/surface_control.py"
    spec = importlib.util.spec_from_file_location("surface_control_for_report", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sc = _load()


def test_every_step_exited_zero():
    assert len(RECORD["steps"]) == 6
    assert all(step["exit"] == 0 for step in RECORD["steps"].values())


def test_the_choice_is_the_tables_best_and_was_made_on_the_development_segment():
    development = RECORD["development"]
    assert development["segment"] == "20260220213127-w00"
    assert len(development["table"]) == 34
    assert sc.choose(development["table"]) == RECORD["chosen"]
    assert f"depth −{abs(RECORD['chosen']['depth'])}, `_reverse`" in REPORT
    assert RECORD["chosen"]["side"] == "reverse"
    for held_out in RECORD["steps"]:
        if held_out.startswith("ink_") and "213127" not in held_out:
            depth = RECORD["chosen"]["depth"]
            assert RECORD["steps"][held_out]["depths"] == [depth, depth]


def test_the_verdict_follows_from_the_registered_table():
    names = [name for name in RECORD["steps"] if "213127" not in name]
    gate = {name: RECORD["steps"][name] for name in names}
    readings = RECORD["held_out"]
    assert len(readings) == 2
    for reading in readings.values():
        assert reading["p1"] == sc.p1_holds(reading)
        assert reading["p2"] == sc.p2_holds(reading)
    assert sc.verdict(gate, readings)["verdict"] == RECORD["verdict"]
    assert f"**Verdict `{RECORD['verdict']}`**" in REPORT


def test_the_readings_in_the_report_are_the_records():
    for reading in RECORD["held_out"].values():
        cells = f"{reading['scored_cells']:,} ({reading['ink_cells']:,})"
        row = (
            f"| {cells} | **{reading['auc']:.3f}** | "
            f"{reading['slid_floor']['largest']:.3f} | {reading['other_side_auc']:.3f} |"
        )
        assert row in REPORT, row
    development = RECORD["development"]
    assert f"{development['scored_cells']:,} ({development['ink_cells']:,})" in REPORT
    assert f"| {RECORD['chosen']['auc']:.3f} | not measured |" in REPORT


def test_the_unregistered_numbers_in_the_report_are_the_records():
    for name, entry in RECORD["not_registered"]["segments"].items():
        spread = entry["block_bootstrap"]
        text = (
            f"{spread['low']:.3f} to {spread['high']:.3f} ({spread['blocks']} blocks)"
        )
        assert text in REPORT, text
        shift = entry["shift_scan"]
        assert (
            f"| {shift['best_auc']:.3f} | ({shift['rows']}, {shift['cols']}) |"
            in REPORT
        )
        if name in RECORD["held_out"]:
            assert entry["auc"] == RECORD["held_out"][name]["auc"]
            assert spread["low"] < sc.P2_AUC < spread["high"]
    columns = list(RECORD["not_registered"]["segments"].values())
    for model, label in {
        "dnative": "dense_native",
        "hecate": "Hecate 9.6 µm",
        "hybrid_3d2d-seed42": "ink_9um seed 42",
        "hybrid_3d2d-seed43": "ink_9um seed 43",
    }.items():
        cells = " | ".join(f"{c['per_model'][model]:.3f}" for c in columns)
        assert f"| {label} | {cells} |" in REPORT


def test_the_strategy_carries_the_verdict_and_links_the_report():
    assert "reports/first_letters_0841_surface_control.md" in STRATEGY
    assert f"`{RECORD['verdict']}`" in STRATEGY
    aucs = [reading["auc"] for reading in RECORD["held_out"].values()]
    assert f"AUC {max(aucs):.2f} and {min(aucs):.2f}" in STRATEGY
    for figure in ("s20260220214732", "s20260221022814"):
        assert (ROOT / f"reports/first_letters_0841_{figure}.png").exists()
        assert f"first_letters_0841_{figure}.png" in REPORT
