"""The finding-118 report states the numbers in its record, and the record's verdict follows from them."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_0211_reader_control.md").read_text()
RECORD = json.loads(
    (ROOT / "reports/first_letters_0211_reader_control.json").read_text()
)
STRATEGY = (ROOT / "docs/RESEARCH_STRATEGY.md").read_text()


def _load():
    path = ROOT / "repro/first_letters/pherc0211_control/compare.py"
    spec = importlib.util.spec_from_file_location("compare_for_report", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


cmp = _load()


def _n(value) -> str:
    """A number as the report prints it: a minus sign, not a hyphen."""
    return str(value).replace("-", "\u2212")


def test_every_step_exited_zero_and_the_rasters_are_the_same():
    assert all(step["exit"] == 0 for step in RECORD["steps"].values())
    assert RECORD["steps"]["render"]["flipped"] is False
    assert RECORD["alignment"]["aligned"] and RECORD["shift_applied_pixels"] == [0, 0]
    assert RECORD["cell_share"] >= cmp.MIN_CELL_SHARE
    assert RECORD["depth"] == cmp.DEPTH == 1


def test_the_verdict_follows_from_the_registered_table():
    numbers = RECORD["registered"]
    assert cmp.verdict(numbers, RECORD["cell_share"]) == RECORD["verdict"]
    assert f"**Verdict `{RECORD['verdict']}`**" in REPORT
    assert f"I had predicted\n`{RECORD['predicted']}`" in REPORT


def test_the_registered_numbers_in_the_report_are_the_records():
    numbers = RECORD["registered"]
    slid = numbers["control_slid"]
    assert f"| **{numbers['r']}** |" in REPORT
    assert f"| {_n(numbers['control_wrong_side'])} |" in REPORT
    assert (
        f"| {slid['largest_absolute']} (down {slid['down']}, up {slid['up']}, "
        f"right {slid['right']}, left {slid['left']}) |" in REPORT
    )
    assert f"{RECORD['cells']:,} of {RECORD['mask_cells']:,}" in REPORT
    align = RECORD["alignment"]
    assert f"{align['layer']} (the mesh layer), r = {align['r_at_shift']}" in REPORT


def test_the_depth_table_is_the_rechecks_and_the_first_records_defect_is_stated():
    depths = RECORD["not_registered"]["by_depth_and_side"]
    for side, label in (
        ("reading", "reading side (`_reverse`)"),
        ("other", "other side"),
    ):
        cells = " | ".join(_n(depths[f"{d:+d}_{side}"]) for d in cmp.DEPTHS)
        assert f"| {label} | {cells} |" in REPORT
    first = RECORD["not_registered"]["other_side_as_first_recorded"]
    assert len(set(first.values())) == 1  # the defect: every depth read at +1
    assert f"came out the\nsame ({_n(next(iter(first.values())))})" in REPORT
    assert depths["+1_other"] == RECORD["registered"]["control_wrong_side"]
    assert RECORD["not_registered"]["recheck"]["registered_reproduces"] is True


def test_the_unregistered_numbers_in_the_report_are_the_records():
    nr = RECORD["not_registered"]
    per = nr["per_model_r"]
    assert (
        f"dense_native {per['dnative']}, Hecate {per['hecate']}, ink_9um seed 42 "
        f"{per['hybrid_3d2d-seed42']}, ink_9um seed 43 {per['hybrid_3d2d-seed43']}"
        in REPORT.replace("\n", " ")
    )
    pairs = nr["our_models_pairwise_r"].values()
    assert f"r {min(pairs)} to {max(pairs)}" in REPORT
    assert f"r = {nr['r_with_background']}" in REPORT
    assert f"r = {nr['row_profile_r']}" in REPORT
    assert f"{nr['rows_in_profile']} rows" in REPORT
    assert f"is\n{nr['control_slid_256px']['largest_absolute']}" in REPORT


def test_the_costs_in_the_report_are_the_records():
    ink, render = RECORD["steps"]["ink"], RECORD["steps"]["render"]
    assert f"{ink['seconds'] // 60} min {ink['seconds'] % 60} s" in REPORT
    assert f"{render['seconds'] // 60} min {render['seconds'] % 60} s" in REPORT
    assert f"{ink['gpu_peak_mib_all_processes']:,} MiB" in REPORT


def test_the_strategy_carries_the_verdict_and_links_the_report():
    assert "reports/first_letters_0211_reader_control.md" in STRATEGY
    assert f"`{RECORD['verdict']}`: r {RECORD['registered']['r']}" in STRATEGY
