"""The finding-120 report states the numbers in its record, and the record's verdict follows from them."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_0211_reader_v3.md").read_text()
FLAT = REPORT.replace("\n", " ")
RECORD = json.loads((ROOT / "reports/first_letters_0211_reader_v3.json").read_text())
F118 = json.loads((ROOT / "reports/first_letters_0211_reader_control.json").read_text())
STRATEGY = (ROOT / "docs/RESEARCH_STRATEGY.md").read_text()


def _load():
    path = ROOT / "repro/first_letters/pherc0211_control/compare_readers.py"
    spec = importlib.util.spec_from_file_location("compare_readers_for_report", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


cr = _load()


def _n(value) -> str:
    """A number as the report prints it: a minus sign, not a hyphen."""
    return str(value).replace("-", "−")


def test_the_run_exited_zero_on_finding_118s_cells():
    assert RECORD["steps"]["reader_v3"]["exit"] == 0
    assert RECORD["cell_share"] >= cr.f118.MIN_CELL_SHARE
    shared = F118["alignment"].keys() & RECORD["alignment"].keys()
    assert {"layer", "shift_pixels", "r_at_shift", "aligned"} <= shared
    assert all(RECORD["alignment"][k] == F118["alignment"][k] for k in shared)
    assert RECORD["cells"] == F118["cells"] and RECORD["depth"] == cr.DEPTH == 1
    assert RECORD["checkpoint"]["sha256"].startswith("ea405417")


def test_the_verdict_follows_from_the_registered_table():
    reg = RECORD["registered"]
    assert (
        cr.verdict(reg["ensemble"], reg["reader_v3"], RECORD["cell_share"])
        == RECORD["verdict"]
    )
    assert RECORD["verdict"] == "V3_NO_CLOSER" and RECORD["predicted"] == "V3_CLOSER"
    assert reg["delta_r"] < cr.R_MARGIN <= reg["delta_r"] + 0.003
    assert reg["delta_overlap"] >= cr.OVERLAP_MARGIN
    assert f"**Verdict `{RECORD['verdict']}`**" in REPORT
    assert f"I had predicted `{RECORD['predicted']}`" in FLAT


def test_the_ensemble_is_finding_118s():
    e = RECORD["registered"]["ensemble"]
    reg = F118["registered"]
    assert (e["r"], e["control_wrong_side"], e["control_slid"]) == (
        reg["r"],
        reg["control_wrong_side"],
        reg["control_slid"],
    )


def test_the_registered_numbers_in_the_report_are_the_records():
    reg = RECORD["registered"]
    e, v = reg["ensemble"], reg["reader_v3"]
    assert f"| {e['r']} | {v['r']} | **+{reg['delta_r']}** (margin +0.10) |" in REPORT
    assert (
        f"| {_n(e['control_wrong_side'])} | {_n(v['control_wrong_side'])} |" in REPORT
    )
    assert (
        f"| {e['control_slid']['largest_absolute']} | {v['control_slid']['largest_absolute']} |"
        in REPORT
    )
    assert (
        f"| {e['overlap']} | {v['overlap']} | **+{reg['delta_overlap']}** (margin +0.05) |"
        in REPORT
    )
    assert (
        f"| {e['control_overlap_slid']['largest']} | {v['control_overlap_slid']['largest']} |"
        in REPORT
    )
    slid = v["control_slid"]
    assert (
        f"down {slid['down']}, up {slid['up']}, right {slid['right']}, left {slid['left']}"
        in FLAT
    )
    assert f"{RECORD['winner_ink_cells']:,}" in REPORT
    assert (
        f"short of the 0.10 margin by {round(cr.R_MARGIN - reg['delta_r'], 4)}" in FLAT
    )


def test_the_described_numbers_in_the_report_are_the_records():
    d = RECORD["described"]
    by = d["v3_by_depth"]
    depths = [f"{x:+d}" for x in cr.DEPTHS]
    for key, label in (
        ("r", "r"),
        ("control_wrong_side", "other side"),
        ("overlap", "overlap"),
    ):
        cells = " | ".join(_n(by[x][key]) for x in depths)
        assert f"| {label} | {cells} |" in REPORT, key
    boot = d["r_difference_bootstrap"]
    assert f"is {boot['low']} to {boot['high']}" in FLAT
    assert f"{boot['blocks']} blocks of 64 by 64 cells" in FLAT
    assert boot["low"] < cr.R_MARGIN < boot["high"]
    assert f"r {d['v3_r_with_ensemble']}:" in FLAT


def test_the_unregistered_depth_differences_are_the_records():
    nr = RECORD["not_registered"]
    ens = nr["ensemble_r_by_depth_finding_118"]
    for x, delta in nr["delta_r_by_depth"].items():
        assert ens[x] == F118["not_registered"]["by_depth_and_side"][f"{x}_reading"]
        assert delta == round(RECORD["described"]["v3_by_depth"][x]["r"] - ens[x], 4)
        assert f"{_n(x)} +{delta}" in FLAT, x
    assert all(delta > 0 for delta in nr["delta_r_by_depth"].values())
    assert nr["depths_with_delta_r_at_least_the_margin"] == ["-1", "-2", "-3"]
    assert min(nr["delta_r_by_depth"], key=nr["delta_r_by_depth"].get) == "+1"


def test_the_costs_in_the_report_are_the_records():
    gate = RECORD["steps"]["reader_v3"]
    assert (
        f"| {gate['seconds'] // 60} min {gate['seconds'] % 60} s | {gate['gpu_peak_mib_all_processes']:,} MiB |"
        in REPORT
    )
    t = RECORD["steps"]["seconds_by_depth"]
    later = [s for x, s in t.items() if x != "-3"]
    assert f"took {t['-3']} s and each later one {min(later)} to {max(later)} s" in FLAT


def test_the_strategy_carries_the_verdict_and_links_the_report():
    assert "reports/first_letters_0211_reader_v3.md" in STRATEGY
    assert f"`{RECORD['verdict']}`" in STRATEGY
