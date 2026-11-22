"""The finding-110 report states the numbers in its record, and the record's verdict follows from them."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_343_mesh_step.md").read_text()
RECORD = json.loads((ROOT / "reports/first_letters_343_mesh_step.json").read_text())


def test_every_step_exited_zero():
    assert RECORD["steps"]
    assert all(step["exit"] == 0 for step in RECORD["steps"].values())
    assert RECORD["steps"]["fit"]["steps"] == 30000


def test_p1_numbers_in_the_report_are_the_records_and_pass_the_registered_threshold():
    for name, score in RECORD["p1_final_windings"].items():
        within = score["fraction_within"]["2"]
        assert within >= 0.50 and score["median"] <= 3
        assert (
            f"| {name} | fitted {name} | {100 * within:.1f}% | {score['median']:.2f} |"
            in REPORT
        )
    for score in RECORD["p1_other_final_winding"].values():
        assert score["fraction_within"]["2"] < 0.2 and score["median"] > 10


def test_p3_numbers_in_the_report_are_the_records_and_pass_the_registered_threshold():
    p3 = RECORD["p3"]
    controls = (p3["control_slid"]["largest_absolute"], abs(p3["control_wrong_side"]))
    assert p3["evaluable"] and p3["letter_box_coverage"] >= 0.5
    assert p3["r"] >= 0.50 and all(p3["r"] >= 2 * c for c in controls)
    assert f"**{p3['r']:.3f}**" in REPORT
    for control in controls:
        assert f"| {control:.3f} |" in REPORT
    assert f"{p3['r'] / max(controls):.1f} times the larger control" in REPORT


def test_the_verdict_follows_from_the_table():
    verdict = RECORD["verdict"]
    assert verdict["verdict"] == "REPRODUCED" and verdict["fit_config"] == "recipe"
    assert all(verdict["p1"].values()) and verdict["p3"]
    assert "**Verdict `REPRODUCED`**" in REPORT
