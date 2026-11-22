"""The finding-127 report states the numbers in its record, and the record's verdict follows from them."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_343_studio.md").read_text()
FLAT = " ".join(REPORT.split())
RECORD = json.loads((ROOT / "reports/first_letters_343_studio.json").read_text())
STRATEGY = " ".join((ROOT / "docs/RESEARCH_STRATEGY.md").read_text().split())


def _load():
    path = ROOT / "repro/first_letters/pherc343/studio_343.py"
    spec = importlib.util.spec_from_file_location("studio_343_for_report", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


s3 = _load()


def test_every_step_exited_zero_and_the_verdict_follows_from_the_table():
    assert list(RECORD["steps"]) == ["check", "reference", "planes", "infer", "compare"]
    assert all(step["exit"] == 0 for step in RECORD["steps"].values())
    assert RECORD["layers"] == list(range(41, 25, -1))
    assert (
        s3.verdict(RECORD["registered"], RECORD["cell_share"])
        == RECORD["verdict"]
        == RECORD["predicted"]
        == "STUDIO_343_AGREES"
    )
    assert f"**Verdict `{RECORD['verdict']}`**, as predicted" in REPORT
    assert (
        f"{round(100 * RECORD['cell_share'], 2)}% of the area's cells are valid" in FLAT
    )


def test_the_registered_numbers_are_the_records():
    reg = RECORD["registered"]
    slid = reg["control_slid"]
    assert f"| **r, Studio's map against `u`** | **{reg['r']}** |" in REPORT
    assert (
        f"| control: Studio on the same planes in reversed order | {reg['control_wrong_side']} |"
        in REPORT
    )
    assert (
        f"| {slid['largest_absolute']} (down {slid['down']}, up {slid['up']}, right {slid['right']}, "
        f"left {slid['left']}) |" in REPORT
    )
    assert f"| {RECORD['cells']:,} of {RECORD['area_cells']:,} |" in REPORT
    assert reg["control_wrong_side"] < 0.2  # the second registered prediction


def test_the_leave_one_out_table_is_the_registered_one_and_the_records():
    loo = RECORD["described"]["leave_one_out"]
    assert {k: v["r"] for k, v in loo.items()} == s3.REGISTERED_LEAVE_ONE_OUT
    names = {"dnative": "dense_native", "hecate": "Hecate", "ink9-42": "ink_9um seed 42",
             "ink9-43": "ink_9um seed 43"}  # fmt: skip
    for key, label in names.items():
        assert (
            f"| {label} | {loo[key]['r']} | {loo[key]['control_slid_largest_absolute']} |"
            in REPORT
        )
    assert RECORD["registered"]["r"] > max(v["r"] for v in loo.values())


def test_the_described_numbers_are_the_records():
    d = RECORD["described"]
    assert f"With the background in:** r {d['studio']['r_with_background']}" in FLAT
    assert f"(`u` ≥ 0.35): {d['studio']['overlap']}" in FLAT
    assert f"at most {d['studio']['control_overlap_slid']['largest']}" in FLAT
    assert f"reversed planes {d['studio_reversed_planes']['overlap']}" in FLAT
    share = d["studio_ink_share"]
    assert (
        f"Studio {share['forward']} (reversed planes {share['reversed']}); `u` draws {d['u_drawn_share']}"
        in FLAT
    )
    boxes = d["letters"]["boxes"]
    assert len(boxes) == d["letters"]["boxes_scored"] == 18
    assert all(b["studio_above_its_area_share"] for b in boxes)
    lo = min(boxes, key=lambda b: b["studio_ink_share"])
    hi = max(boxes, key=lambda b: b["studio_ink_share"])
    ulo = min(boxes, key=lambda b: b["u_drawn_share"])
    uhi = max(boxes, key=lambda b: b["u_drawn_share"])
    assert (
        f"from {lo['studio_ink_share']} (box {lo['id']}) to {hi['studio_ink_share']} (box {hi['id']}), "
        f"`u`'s from {ulo['u_drawn_share']} (box {ulo['id']}) to {uhi['u_drawn_share']} (box {uhi['id']})"
        in FLAT
    )
    lower = [str(b["id"]) for b in boxes if b["studio_ink_share"] < b["u_drawn_share"]]
    assert f"lower of the two in boxes {', '.join(lower[:-1])} and {lower[-1]}." in FLAT


def test_the_costs_are_the_records():
    steps = RECORD["steps"]
    for name, label in (
        ("check", "checksums"),
        ("planes", "planes, both orders"),
        ("compare", "comparison"),
    ):
        assert f"| {label} | {steps[name]['seconds']} s |" in REPORT
    assert f"| {steps['reference']['seconds']} s |" in REPORT
    assert (
        f"{RECORD['gpu_peak_mib_all_processes']:,} MiB of GPU memory) | {steps['infer']['seconds']} s |"
        in REPORT
    )
    m, s = divmod(sum(v["seconds"] for v in steps.values()), 60)
    assert f"| **all** | **{m} min {s} s**" in REPORT


def test_the_strategy_carries_the_finding():
    assert "reports/first_letters_343_studio.md" in STRATEGY
    assert f"(`{RECORD['verdict']}`, as predicted;" in STRATEGY
    assert f"r {RECORD['registered']['r']} against the" in STRATEGY
