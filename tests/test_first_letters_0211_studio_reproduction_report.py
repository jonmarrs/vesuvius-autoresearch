"""The finding-123 report states the numbers in its record, and the record's verdict follows from them."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_0211_studio_reproduction.md").read_text()
FLAT = " ".join(REPORT.split())
RECORD = json.loads(
    (ROOT / "reports/first_letters_0211_studio_reproduction.json").read_text()
)
STRATEGY = (ROOT / "docs/RESEARCH_STRATEGY.md").read_text()


def _load():
    path = ROOT / "repro/first_letters/pherc0211_control/studio_reproduce.py"
    spec = importlib.util.spec_from_file_location("studio_reproduce_for_report", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sr = _load()


def test_every_step_of_the_second_attempt_exited_zero_and_the_first_stopped_at_the_environment():
    assert all(step["exit"] == 0 for step in RECORD["steps"].values())
    first = RECORD["first_attempt"]["steps"]
    assert (
        first["fetch"]["exit"] == 0
        and first["env"]["exit"] == 1
        and "infer" not in first
    )
    assert (
        "2.14.0+cu130" in RECORD["environment"] and "RTX 4090" in RECORD["environment"]
    )


def test_the_verdict_follows_from_the_registered_table():
    numbers = RECORD["registered"]
    assert (
        RECORD["exact"] is (RECORD["output_sha256"] == sr.RECORDED_NPY_SHA256) is False
    )
    assert (
        sr.verdict(0, RECORD["exact"], numbers)
        == RECORD["verdict"]
        == RECORD["predicted"]
        == "REPRODUCED"
    )
    assert f"**Verdict `{RECORD['verdict']}`**, as predicted" in REPORT


def test_the_registered_numbers_in_the_report_are_the_records():
    n = RECORD["registered"]
    d = n["abs_difference"]
    assert f"| {n['r']} |" in REPORT and f"{n['pixels']:,} pixels" in FLAT
    assert f"| {d['p50']:.6f} / {d['p99']:.6f} / {d['max']:.6f} |" in REPORT
    assert f"| {n['mean_ours']} / {n['mean_winner']} |" in REPORT
    assert f"| {100 * n['share_same_side_of_half']:.4f}% |" in REPORT


def test_the_costs_in_the_report_are_the_records():
    s, first = RECORD["steps"], RECORD["first_attempt"]["steps"]
    assert f"| {first['fetch']['seconds']} s |" in REPORT
    assert f"| {s['env']['seconds']} s |" in REPORT
    assert (
        f"| {s['infer']['seconds']} s |" in REPORT
        and f"It took {s['infer']['seconds']} s" in FLAT
    )
    assert f"{RECORD['gpu_peak_mib_all_processes']:,} MiB" in REPORT


def test_the_strategy_carries_the_verdict_and_links_the_report():
    assert "reports/first_letters_0211_studio_reproduction.md" in STRATEGY
    assert f"`{RECORD['verdict']}`" in STRATEGY
